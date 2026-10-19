import os
import unittest
from unittest.mock import patch
import check_telegram
from agent import SafeError


class TelegramCheckTests(unittest.TestCase):
    def test_mutation_is_refused_before_network(self):
        with patch('check_telegram.request_json') as network:
            with self.assertRaises(SafeError):
                check_telegram.read_telegram('sendPhoto', {})
            network.assert_not_called()

    def test_read_only_check_verifies_posting_right(self):
        responses = [{'id': 123, 'username': 'example_bot'},
                     {'id': -100123, 'username': 'quantafate', 'type': 'channel'},
                     {'status': 'administrator', 'can_post_messages': True}]
        with patch.dict(os.environ, {'TELEGRAM_CHANNEL_ID': '@quantafate'}), \
             patch('check_telegram.read_telegram', side_effect=responses) as read:
            result = check_telegram.check()
            self.assertTrue(result['can_post_messages'])
            self.assertEqual([call.args[0] for call in read.call_args_list],
                             ['getMe', 'getChat', 'getChatMember'])

    def test_admin_without_post_permission_is_refused(self):
        responses = [{'id': 123}, {'id': -100123, 'username': 'quantafate', 'type': 'channel'},
                     {'status': 'administrator', 'can_post_messages': False}]
        with patch.dict(os.environ, {'TELEGRAM_CHANNEL_ID': '@quantafate'}), \
             patch('check_telegram.read_telegram', side_effect=responses):
            with self.assertRaises(SafeError):
                check_telegram.check()
