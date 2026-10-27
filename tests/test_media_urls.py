import unittest
from media_urls import trusted_media_url

class MediaUrlTests(unittest.TestCase):
    def test_old_queued_urls_and_new_uploads_remain_trusted(self):
        for repo in ('quantafate-agent','numerology-agent'):
            self.assertTrue(trusted_media_url('https://raw.githubusercontent.com/mrgrtglcht/'+repo+'/commit/media/01.jpg'))

    def test_lookalike_repositories_and_hosts_are_rejected(self):
        for url in ('https://raw.githubusercontent.com/mrgrtglcht/numerology-agent-evil/x.jpg',
          'https://raw.githubusercontent.com/other/numerology-agent/x.jpg',
          'https://raw.githubusercontent.com.evil.test/mrgrtglcht/numerology-agent/x.jpg',None):
            self.assertFalse(trusted_media_url(url))

