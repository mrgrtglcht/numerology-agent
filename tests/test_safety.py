import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import agent
from check_buffer import query_buffer


class SafetyTests(unittest.TestCase):
    def test_connection_check_rejects_mutation(self):
        with patch('urllib.request.urlopen') as network:
            with self.assertRaises(RuntimeError):
                query_buffer('fake-secret', 'mutation Create { createPost { id } }')
            network.assert_not_called()

    def test_publication_guard_precedes_network(self):
        with patch.dict(os.environ, {'ALLOW_PUBLISH': 'false'}), \
             patch('sys.argv', ['agent.py', 'publish']), patch('agent.GitHubStore') as store:
            with self.assertRaises(agent.SafeError):
                agent.main()
            store.assert_not_called()

    def test_pinterest_has_one_image_tiktok_three_and_drafts_cannot_publish(self):
        urls = {name: 'https://example.org/' + name for name in
                ['pinterest-pin.jpg', 'tiktok-01.jpg', 'tiktok-02.jpg', 'tiktok-03.jpg']}
        env = {'BUFFER_TIKTOK_CHANNEL_ID': 'tt', 'BUFFER_PINTEREST_CHANNEL_ID': 'pin', 'PINTEREST_BOARD_ID': 'board'}
        with patch.dict(os.environ, env):
            for target, count in [('pinterest', 1), ('tiktok', 3)]:
                data = agent.post_input(target, agent.DEMO, urls, 'draft')
                self.assertIs(data['saveToDraft'], True)
                self.assertEqual(data['mode'], 'addToQueue')
                self.assertEqual(len(data['assets']), count)

    def test_http_error_never_exposes_request_or_body(self):
        secret = 'FAKE_SECRET_MUST_NOT_APPEAR'
        error = urllib.error.HTTPError('https://example.org/' + secret, 401, secret, {}, io.BytesIO(secret.encode()))
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(agent.SafeError) as caught:
                agent.request_json('Test', 'https://example.org/' + secret)
            self.assertNotIn(secret, str(caught.exception))

    def test_gemini_billing_guard_precedes_network(self):
        with patch.dict(os.environ, {'GEMINI_FREE_TIER_CONFIRMED': 'false'}), patch('agent.request_json') as network:
            with self.assertRaises(agent.SafeError):
                agent.generate('test')
            network.assert_not_called()

    def test_existing_uncertain_delivery_is_not_retried(self):
        state = {'targets': ['tiktok'], 'deliveries': {'tiktok': {'state': 'sending'}}}
        with patch('sys.argv', ['agent.py', 'draft']), patch('agent.GitHubStore') as store, \
             patch('agent.send_buffer') as send, redirect_stdout(io.StringIO()):
            store.return_value.read_state.return_value = state
            with self.assertRaises(agent.SafeError):
                agent.main()
            send.assert_not_called()

    def test_cards_render_with_cyrillic(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp, patch.object(agent, 'ROOT', Path(temp)):
            files = agent.render(agent.DEMO, 'test', test=True)
            self.assertEqual(len(files), 4)
            for index, file in enumerate(files):
                with Image.open(file) as image:
                    self.assertEqual(image.size, (1080, 1920) if index < 3 else (1000, 1500))
                    self.assertLess(file.stat().st_size, 20 * 1024 * 1024)

    def test_invalid_gemini_output_is_rejected(self):
        content = copy.deepcopy(agent.DEMO)
        content['slides'][0]['body'] = 'x' * 171
        with self.assertRaises(agent.SafeError):
            agent.validate_content(content)


if __name__ == '__main__':
    unittest.main()
