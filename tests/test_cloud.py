import json
import os
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
import cloud_agent as cloud
from agent import SafeError
from content_memory import ContentMemory


class Store:
    def __init__(self):self.data={}
    def read_state(self,key):return self.data.get(key)
    def save_state(self,key,value):self.data[key]=json.loads(json.dumps(value))


class CloudTests(unittest.TestCase):
    def test_known_public_intro_import_is_idempotent(self):
        s=Store();cloud.bootstrap_telegram_history(s);cloud.bootstrap_telegram_history(s)
        memory=ContentMemory(store=s)
        self.assertEqual(len(memory.data['posts']),1)
        post=memory.data['posts']['telegram/quantafate/3']
        self.assertEqual(post['status'],'published')
        self.assertEqual(post['deliveries']['telegram']['receipt']['message_id'],3)

    def test_summer_winter_one_local_slot(self):
        for month,utc_hour in ((7,16),(10,17)):
            day=1 if month==7 else 28 # both Wednesdays in 2026
            yes=datetime(2026,month,day,utc_hour,30,tzinfo=timezone.utc).astimezone(cloud.ZONE)
            no=datetime(2026,month,day,utc_hour-1,30,tzinfo=timezone.utc).astimezone(cloud.ZONE)
            self.assertTrue(cloud.due_telegram(yes));self.assertFalse(cloud.due_telegram(no))
        self.assertTrue(cloud.due_telegram(datetime(2026,10,21,20,5,tzinfo=cloud.ZONE)))

    def test_all_seven_slides_automatic_queue_not_share_now(self):
        with patch.dict(os.environ,{'BUFFER_TIKTOK_CHANNEL_ID':'tt'}):
            data=cloud.tiktok_input({'title':'тема','caption':'подпись'},['https://example.org/'+str(n) for n in range(7)])
        self.assertEqual(len(data['assets']),7);self.assertEqual(data['mode'],'addToQueue')
        self.assertEqual(data['schedulingType'],'automatic');self.assertFalse(data['saveToDraft'])
        self.assertIn('https://t.me/quantafate',data['text'])
        with self.assertRaises(ValueError):cloud.tiktok_input({},['x']*11)

    def test_uncertain_day_never_calls_model_or_sender(self):
        s=Store();now=datetime(2026,10,21,18,30,tzinfo=cloud.ZONE)
        s.data['state/cloud/telegram-2026-10-21.json']={'stage':'started'}
        with patch('cloud_agent.generate_telegram') as model,patch('cloud_agent.send_article') as send:
            with self.assertRaises(SafeError):cloud.run_target('telegram',s,now=now)
            model.assert_not_called();send.assert_not_called()

    def test_unknown_tiktok_attempt_blocks_replenishment(self):
        class Memory: data={'posts':{'a':{'deliveries':{'tiktok':{'status':'needs_review'}}}}}
        with self.assertRaises(SafeError):cloud.pending_tiktok(Memory())

    def test_long_article_single_message_and_no_added_promotion(self):
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHANNEL_ID':'@test'}),patch('cloud_agent.request_json',return_value={'ok':True,'result':{'message_id':42}}) as request:
            receipt=cloud.send_article({'title':'тема','caption':'содержание '*230})
        self.assertEqual(receipt['message_id'],42)
        self.assertEqual(request.call_args.args[2]['text'],'тема\n\n'+'содержание '*230)
        self.assertNotIn('parse_mode',request.call_args.args[2])

    def test_queue_success_requires_actual_automatic_and_all_media(self):
        for automatic,count in (('notification',7),('automatic',3)):
            result={'createPost':{'__typename':'PostActionSuccess','post':{'id':'p','status':'scheduled','schedulingType':automatic,'assets':[{}]*count}}}
            with patch('cloud_agent.buffer',return_value=result):
                with self.assertRaises(SafeError):cloud.queue_tiktok({'assets':[{}]*7})

    def test_public_domain_deck_matches_matrix_numbering(self):
        records=json.loads((cloud.ROOT/'assets/tarot/public-domain-manifest.json').read_text(encoding='utf-8'))
        lookup={r['number']:r for r in records}
        self.assertEqual(set(lookup),set(range(1,23)))
        self.assertIn('Justice',lookup[8]['title']);self.assertIn('Strength',lookup[11]['title']);self.assertIn('Fool',lookup[22]['title'])
        self.assertTrue(all(r['license']=='Public domain' and len(r['sha1'])==40 for r in records))

    def test_failed_article_never_marked_published_or_retried(self):
        s=Store();now=datetime(2026,10,21,18,30,tzinfo=cloud.ZONE)
        config={'title':'тема','topic':'test','caption':'текст','slides':[{'body':'текст'}]}
        with tempfile.TemporaryDirectory() as tmp,patch.object(cloud,'ROOT',Path(tmp)),patch('cloud_agent.generate_telegram',return_value=config),patch('cloud_agent.send_article',side_effect=SafeError('timeout')) as send:
            with self.assertRaises(SafeError):cloud.run_target('telegram',s,now=now)
            m=ContentMemory(store=s);r=next(iter(m.data['posts'].values()))
            self.assertEqual(r['deliveries']['telegram']['status'],'needs_review');self.assertNotEqual(r['status'],'published')
            with self.assertRaises(SafeError):cloud.run_target('telegram',s,now=now)
            self.assertEqual(send.call_count,1)


if __name__=='__main__':unittest.main()

