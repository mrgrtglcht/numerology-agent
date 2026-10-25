import copy
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
import pinterest_upload_cloud as pin

class Store:
    def __init__(self):self.data={'version':1,'days':{},'posts':{'key':{'stage':'prepared','title':'title'}}}
    def read_state(self,path):return copy.deepcopy(self.data)
    def save_state(self,path,data):self.data=copy.deepcopy(data)

class UploadPinterestTests(unittest.TestCase):
    def test_pinterest_analysis_has_no_cover_or_bot_footer(self):
        from pinterest_carousel import plan
        config={'pinterest_analysis_only':True,'slides':[{'layout':'series_cover'},{'layout':'location'},
          {'layout':'arcana','arcana_number':3},{'layout':'arcana','arcana_number':4},{'layout':'bot'}]}
        pages=plan(config)
        self.assertEqual([s['layout'] for s in pages],['arcana','arcana'])
        self.assertFalse(any(p.get('bot_footer') for p in pages))
    def test_status_handles_async_list_without_confusing_acceptance_and_publication(self):
        self.assertEqual(pin.result_state({'success':True,'request_id':'key'})[0],'accepted')
        self.assertEqual(pin.result_state({'status':'completed','results':[{'platform':'pinterest','success':True,'post_url':'https://www.pinterest.com/pin/123/'}]})[0],'published')
        self.assertEqual(pin.result_state({'results':{'pinterest':{'success':False,'skipped':True}}})[0],'needs_review')

    def test_timeout_is_durable_and_never_reposted(self):
        store=Store();now=datetime(2026,10,25,12,tzinfo=timezone.utc)
        store.data['posts']['key']['design_version']=2
        with patch.object(pin.upload_post,'connection',return_value={}),patch.object(pin,'sync'),patch.object(pin.upload_post,'publish',side_effect=TimeoutError) as send:
            with self.assertRaises(TimeoutError):pin.run('publish',store,now)
            self.assertEqual(store.data['posts']['key']['stage'],'needs_review')
            pin.run('publish',store,now)
            self.assertEqual(send.call_count,1)

    def test_clickable_channel_link_is_sent_for_every_slide(self):
        import upload_post
        post={'image_urls':['https://raw.githubusercontent.com/mrgrtglcht/quantafate-agent/sha/1.png']*5,'title':'title','caption':'caption'}
        with patch.object(upload_post,'required',return_value='dummy'),patch.object(upload_post.urllib.request,'urlopen',side_effect=TimeoutError) as send:
            with self.assertRaises(Exception):upload_post.publish(post,{'profile':'default','board':'board'},'key')
        req=send.call_args.args[0]
        self.assertEqual(req.data.count(b'https://t.me/quantafate'),6)
        self.assertEqual(req.get_header('Idempotency-key'),'key')
