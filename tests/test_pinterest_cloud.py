import copy
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
import pinterest_cloud as pin
from agent import SafeError
from content_memory import ContentMemory


class Store:
    def __init__(self,ledger):self.ledger=ledger
    def read_state(self,path):return copy.deepcopy(self.ledger)
    def save_state(self,path,state):self.ledger=copy.deepcopy(state)


class PinterestCloudTests(unittest.TestCase):
    def test_unknown_send_is_not_repeated_after_restart(self):
        store=Store({'version':1,'days':{},'pins':{'key':{'stage':'prepared','caption':'text'}}})
        now=datetime(2026,10,25,12,tzinfo=timezone.utc)
        with patch.object(pin,'check_channel',return_value=('channel','org')),patch.object(pin,'sync'),patch.object(pin,'send',side_effect=TimeoutError) as send:
            with self.assertRaises(TimeoutError):pin.run('publish',store,now)
            self.assertEqual(store.ledger['pins']['key']['stage'],'needs_review')
            pin.run('publish',store,now)
            self.assertEqual(send.call_count,1)

    def test_queue_acceptance_is_not_publication(self):
        store=Store({'version':1,'days':{},'pins':{'key':{'stage':'prepared','title':'title'}}})
        with patch.object(pin,'check_channel',return_value=('channel','org')),patch.object(pin,'sync'),patch.object(pin,'send',return_value={'id':'id','status':'scheduled','asset_count':1}):
            pin.run('publish',store,datetime(2026,10,25,12,tzinfo=timezone.utc))
        self.assertEqual(store.ledger['pins']['key']['stage'],'accepted')

    def test_no_image_cannot_be_accepted(self):
        post={'caption':'x','image_url':'https://example.com/pin.jpg','board':'board','title':'title'}
        with patch.object(pin,'buffer',return_value={'createPost':{'__typename':'PostActionSuccess','post':{'id':'id','status':'scheduled','assets':[]}}}):
            with self.assertRaises(SafeError):pin.send(post,'channel')

    def test_rejected_and_unpublished_copy_are_not_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ContentMemory(path=Path(tmp)/'memory.json')
            config={'type':'arcana_series','theme':'facts','position':None,'part_arcana':[3],
              'slides':[{'layout':'arcana','arcana_number':3,'paragraphs':['описание аркана']} ]}
            memory.reserve('owner',config)
            self.assertIsNone(pin.select(memory,{'pins':{}}))
            memory.delivery('owner','tiktok','published',{'id':'original'})
            selected=pin.select(memory,{'pins':{}})
            self.assertEqual(selected['number'],3)
            self.assertIsNone(pin.select(memory,{'pins':{selected['key']:{'stage':'published'}}}))

    def test_first_dst_trigger_cannot_publish_before_local_time(self):
        store=Store({'version':1,'days':{},'pins':{}})
        with patch.object(pin,'check_channel',return_value=('channel','org')),patch.object(pin,'sync'),patch.object(pin,'prepare') as prepare:
            pin.run('scheduled',store,datetime(2026,10,27,16,30,tzinfo=timezone.utc))
            prepare.assert_not_called()
