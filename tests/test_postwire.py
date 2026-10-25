import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import postwire as p
from agent import SafeError
from content_memory import ContentMemory, digest


class PostWireTests(unittest.TestCase):
    def test_schedule_keeps_warsaw_time_across_dst(self):
        class Memory: data={'posts':{}}
        slot=p.next_slot(Memory(),datetime(2026,10,24,10,tzinfo=timezone.utc))
        self.assertEqual(slot,'2026-10-25T08:46:00+00:00')
        slot=p.next_slot(Memory(),datetime(2026,7,3,21,tzinfo=timezone.utc))
        self.assertEqual(slot,'2026-07-05T07:46:00+00:00')

    def test_private_or_wrong_creator_is_rejected(self):
        for name, privacy in [('other',[p.PUBLIC]),('quanta.aura',['SELF_ONLY'])]:
            with patch.object(p,'api',return_value={'ok':True,'creator_username':name,'privacy_level_options':privacy,'brand_id':'brand'}):
                with self.assertRaises(SafeError):p.creator()

    def test_free_queue_hold_is_never_accepted(self):
        with patch.object(p,'api',return_value={'ok':True,'held':True,'scheduled':{'id':'abc','status':'held'}}) as api:
            with self.assertRaises(SafeError):p.enqueue({})
            self.assertEqual(api.call_count,1)

    def test_lost_response_is_not_retried(self):
        with patch.object(p,'api',side_effect=TimeoutError) as api:
            with self.assertRaises(TimeoutError):p.enqueue({})
            self.assertEqual(api.call_count,1)

    def test_readback_must_preserve_music_publicity_and_all_slides(self):
        data={'text':'caption','media':[{'url':'https://example.com/1.jpg'},{'url':'https://example.com/2.jpg'}]}
        row={'status':'queued','text':'caption','media':data['media'],'options':{'tiktok':{'privacy_level':p.PUBLIC,'auto_add_music':True}}}
        with patch.object(p,'api',return_value={'scheduled':row}):
            self.assertEqual(p.verify({'id':'abc'},data),{'id':'abc'})
            row['options']['tiktok']['auto_add_music']=False
            with self.assertRaises(SafeError):p.verify({'id':'abc'},data)

    def test_buffer_cannot_reconcile_an_unknown_postwire_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ContentMemory(path=Path(tmp)/'memory.json')
            memory.reserve('post',{'topic':'new','caption':'body'})
            memory.delivery('post','tiktok','needs_review',{'provider':'postwire','expected_text_hash':digest('caption'),'expected_asset_count':2})
            memory.import_buffer([{'id':'buffer','channelService':'tiktok','text':'caption','status':'scheduled','assets':[{},{}]}])
            self.assertEqual(memory.data['posts']['post']['deliveries']['tiktok']['status'],'needs_review')

    def test_actual_nested_schedule_payload_is_verified_without_resending(self):
        data={'text':'caption','media':[{'url':'https://example.com/1.jpg'}],
          'options':{'tiktok':{'privacy_level':p.PUBLIC,'auto_add_music':True}}}
        with patch.object(p,'api',return_value={'scheduled':{'id':'abc','status':'queued','payload':data}}) as api:
            p.verify({'id':'abc'},data)
            api.assert_called_once_with('/api/schedule/abc')

    def test_music_requirement_blocks_buffer_before_any_network(self):
        from cloud_agent import deliver_tiktok
        with patch.dict('os.environ',{'TIKTOK_REQUIRE_MUSIC':'true','TIKTOK_PUBLISHER':'buffer'}),patch('cloud_agent.buffer') as api:
            with self.assertRaises(SafeError):deliver_tiktok(None,None,None,None)
            api.assert_not_called()
