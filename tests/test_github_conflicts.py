import base64
import unittest
from unittest.mock import patch
from agent import GitHubStore,SafeError

class GitHubConflictTests(unittest.TestCase):
    def store(self):
        s=GitHubStore.__new__(GitHubStore);s.repo='owner/repo';s.base='https://api.github.com/repos/owner/repo';s.branch='main';s.headers={};return s

    def test_branch_tip_race_retries_same_file_without_resending_any_post(self):
        s=self.store()
        with patch.object(s,'get',return_value={'sha':'unchanged'}),patch('agent.time.sleep'),patch('agent.request_json',side_effect=[SafeError('GitHub: HTTP 409. Ответ скрыт.'),{'commit':{'sha':'commit'}}]) as call:
            self.assertIn('/commit/',s.put('state/memory.json',b'new'))
            self.assertEqual(call.call_count,2)

    def test_changed_history_is_never_overwritten(self):
        s=self.store()
        with patch.object(s,'get',side_effect=[{'sha':'before'},{'sha':'changed','encoding':'base64','content':base64.b64encode(b'other').decode()}]),patch('agent.time.sleep'),patch('agent.request_json',side_effect=SafeError('GitHub: HTTP 409. Ответ скрыт.')) as call:
            with self.assertRaisesRegex(SafeError,'другим запуском'):s.put('state/memory.json',b'new')
            self.assertEqual(call.call_count,1)

