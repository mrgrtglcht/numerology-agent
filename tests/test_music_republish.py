import copy
import unittest
from unittest.mock import patch
import music_republish as m
from agent import SafeError


class Store:
    def __init__(self,state):self.state=state
    def read_state(self,path):return copy.deepcopy(self.state)
    def save_state(self,path,state):self.state=copy.deepcopy(state)


class MusicReplacementTests(unittest.TestCase):
    def test_no_network_without_both_authorizations(self):
        with patch.dict('os.environ',{'ALLOW_MUSIC_REPLACEMENT':'true','OLD_POSTS_REMOVED':'false'}),patch('postwire.api') as api:
            with self.assertRaises(SafeError):m.publish(1,Store({}))
            api.assert_not_called()

    def test_accepted_or_unknown_send_cannot_be_repeated(self):
        for stage in ['sending','accepted','published','needs_review']:
            with patch.dict('os.environ',{'ALLOW_MUSIC_REPLACEMENT':'true','OLD_POSTS_REMOVED':'true'}),patch('postwire.api') as api:
                with self.assertRaises(SafeError):m.publish(1,Store({'stage':stage}))
                api.assert_not_called()

    def test_unknown_send_is_durable_and_not_retried(self):
        store=Store({'stage':'prepared','payload':{'brand_id':'brand'}})
        with patch.dict('os.environ',{'ALLOW_MUSIC_REPLACEMENT':'true','OLD_POSTS_REMOVED':'true'}),patch('postwire.creator',return_value={'brand_id':'brand'}),patch('postwire.api',side_effect=TimeoutError) as api:
            with self.assertRaises(TimeoutError):m.publish(1,store)
            self.assertEqual(store.state['stage'],'needs_review')
            with self.assertRaises(SafeError):m.publish(1,store)
            self.assertEqual(api.call_count,1)

    def test_http_success_without_network_success_is_not_accepted(self):
        store=Store({'stage':'prepared','payload':{'brand_id':'brand'}})
        with patch.dict('os.environ',{'ALLOW_MUSIC_REPLACEMENT':'true','OLD_POSTS_REMOVED':'true'}),patch('postwire.creator',return_value={'brand_id':'brand'}),patch('postwire.api',return_value={'posted':0,'results':[{'platform':'tiktok','ok':False,'code':'quota'}]}):
            with self.assertRaises(SafeError):m.publish(1,store)
            self.assertEqual(store.state['stage'],'needs_review')

    def test_sanitized_receipt_never_contains_credentials(self):
        result=m.summarize({'token':'secret','results':[{'platform':'tiktok','ok':True,'access_token':'secret','id':'post'}]})
        self.assertNotIn('secret',str(result))
