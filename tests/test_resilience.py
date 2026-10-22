import io
import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch,Mock
import agent
import cloud_agent as cloud
from cloud_checkpoint import snapshot,restore,preparation_failed,pointer
from content_memory import ContentMemory,digest
from editor_recovery import normalize,validated
from read_retry import read_retry
from topic_planner import check_focus


class Store:
    def __init__(self):self.data={}
    def read_state(self,key):return self.data.get(key)
    def save_state(self,key,value):self.data[key]=json.loads(json.dumps(value))


class ResilienceTests(unittest.TestCase):
    def test_actual_motivation_synonym_is_not_rejected_but_profession_list_is(self):
        check_focus('motivation','движет потребность в глубоких трансформациях, обновлении привычных подходов и отказе от устаревшего.')
        with self.assertRaises(ValueError):check_focus('motivation','профессии: врач, учитель, редактор.')

    def test_normalization_preserves_source_ids_and_urls(self):
        result=normalize({'text':'  ТЕКСТ\\n\\nАБЗАЦ  ','source_ids':['arcana-13'],
          'url':'https://example.org/CASE','entries':[{'paragraphs':[' ПРИМЕР ']}]})
        self.assertEqual(result['text'],'текст\n\nабзац');self.assertEqual(result['url'],'https://example.org/CASE')
        self.assertEqual(result['source_ids'],['arcana-13'])

    def test_one_correction_is_reused_across_process_restarts(self):
        def check(value):
            if value.get('text')!='готово':raise ValueError('нужен текст')
            return value
        repair=Mock(return_value={'text':'ГОТОВО'})
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'AUTO_EDITOR_REPAIR':'true'}):
            for _ in range(2):self.assertEqual(validated({},check,tmp,repair),{'text':'готово'})
            self.assertEqual(repair.call_count,1)

    def test_unknown_correction_result_is_not_repeated(self):
        def bad(value):raise ValueError('не подходит')
        repair=Mock(side_effect=TimeoutError())
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'AUTO_EDITOR_REPAIR':'true'}):
            with self.assertRaises(TimeoutError):validated({},bad,tmp,repair)
            with self.assertRaises(ValueError):validated({},bad,tmp,repair)
        self.assertEqual(repair.call_count,1)

    def test_cached_only_cannot_start_a_model_correction(self):
        repair=Mock()
        def bad(value):raise ValueError('не подходит')
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'AUTO_EDITOR_REPAIR':'true'}):
            with self.assertRaises(ValueError):validated({},bad,tmp,repair,allow_repair=False)
        repair.assert_not_called()

    def test_checkpoint_has_no_binary_files_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'cloud-tiktok-2026-10-22';folder.mkdir()
            (folder/'model-response.json').write_text('{"entries":[]}',encoding='utf-8')
            (folder/'image.png').write_bytes(b'fake image')
            files=snapshot(folder);self.assertEqual(set(files),{'model-response.json'})
            with self.assertRaises(ValueError):restore({'folder':folder.name,'files':{'../outside':'bad'}},Path(tmp)/'restored')

    def test_repeated_preparation_failures_are_bounded(self):
        store=Store()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'cloud-tiktok-2026-10-22';p.mkdir();previous=None
            for _ in range(3):previous=preparation_failed(store,'tiktok',p,'2026-10-22',previous)
        self.assertEqual(previous['stage'],'needs_review');self.assertEqual(previous['attempts'],3)

    def test_failed_preparation_resumes_same_content_next_day(self):
        store=Store();now=datetime(2026,10,22,8,tzinfo=cloud.ZONE)
        calls=[]
        def prepare(folder):
            calls.append(folder.name)
            raw=folder/'model-response.json'
            if not raw.exists():raw.write_text('{"cached":true}');raise ValueError('temporary source error')
            self.assertEqual(json.loads(raw.read_text()),{'cached':True})
            config={'topic':'cached example','caption':'saved body','slides':[{'body':'saved body'}]}
            part=folder/'part-01';part.mkdir(exist_ok=True)
            (part/'content.json').write_text(json.dumps(config),encoding='utf-8')
            ContentMemory(store=store).reserve(folder.name+'/part-01',config)
        with tempfile.TemporaryDirectory() as tmp,patch.object(cloud,'ROOT',Path(tmp)),patch('cloud_agent.channel_info'),patch('cloud_agent.pending_tiktok',return_value=0),patch('editor_auto.run',side_effect=prepare),patch('cloud_agent.deliver_tiktok',return_value={'id':'post'}) as send:
            with self.assertRaises(ValueError):cloud.run_target('tiktok',store,now=now)
            self.assertEqual(store.data[pointer('tiktok')]['stage'],'preparation_failed')
            cloud.run_target('tiktok',store,now=now+timedelta(days=1))
            self.assertEqual(send.call_count,1);self.assertEqual(calls,[calls[0],calls[0]])
            self.assertEqual(store.data[pointer('tiktok')]['stage'],'complete')

    def test_post_request_is_never_retried_on_http_503(self):
        error=urllib.error.HTTPError('https://example.org',503,'temporary',{},io.BytesIO())
        with patch('urllib.request.urlopen',side_effect=error) as send,patch('read_retry.time.sleep'):
            with self.assertRaises(agent.SafeError):agent.request_json('send','https://example.org',{'post':True})
        self.assertEqual(send.call_count,1)

    def test_transient_read_retries_but_permanent_denial_does_not(self):
        error=lambda code:urllib.error.HTTPError('https://example.org',code,'temporary',{},io.BytesIO())
        with patch('read_retry.time.sleep'):
            read=Mock(side_effect=[error(503),TimeoutError(),{'ok':True}])
            self.assertEqual(read_retry(read),{'ok':True});self.assertEqual(read.call_count,3)
            denied=Mock(side_effect=error(401))
            with self.assertRaises(urllib.error.HTTPError):read_retry(denied)
            self.assertEqual(denied.call_count,1)

    def test_lost_buffer_receipt_is_reconciled_without_resending(self):
        store=Store();m=ContentMemory(store=store)
        m.reserve('owner',{'topic':'unique','caption':'text','slides':[{'body':'text'}]})
        m.delivery('owner','tiktok','needs_review',{'expected_text_hash':digest('full caption'),'expected_asset_count':7})
        m.import_buffer([{'id':'real-id','text':'full caption','status':'scheduled','channelService':'tiktok','assets':[{}]*7}])
        self.assertEqual(len(m.data['posts']),1)
        self.assertEqual(m.data['posts']['owner']['deliveries']['tiktok']['receipt']['id'],'real-id')
        self.assertEqual(m.data['posts']['owner']['deliveries']['tiktok']['status'],'accepted')

    def test_wrong_buffer_asset_count_cannot_clear_unknown_send(self):
        store=Store();m=ContentMemory(store=store)
        m.reserve('owner',{'topic':'unique','caption':'text','slides':[{'body':'text'}]})
        m.delivery('owner','tiktok','needs_review',{'expected_text_hash':digest('full caption'),'expected_asset_count':7})
        m.import_buffer([{'id':'other','text':'full caption','status':'scheduled','channelService':'tiktok','assets':[{}]*3}])
        self.assertEqual(m.data['posts']['owner']['deliveries']['tiktok']['status'],'needs_review')

    def test_all_publication_cards_work_without_network(self):
        from tarot_assets import prepare_public_domain
        with patch('backgrounds.read_bytes',side_effect=AssertionError('network forbidden')):
            cards=prepare_public_domain(range(1,23))
        self.assertEqual(set(cards),set(range(1,23)))

    def test_corrupted_bundled_card_is_rejected_without_download(self):
        import tarot_assets
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'assets/tarot/public-domain';folder.mkdir(parents=True)
            source=tarot_assets.ROOT/'assets/tarot/public-domain-manifest.json'
            (folder.parent/source.name).write_bytes(source.read_bytes())
            (folder/'03.png').write_bytes(b'corrupted')
            with patch.object(tarot_assets,'ROOT',root),patch('backgrounds.read_bytes',side_effect=AssertionError('network forbidden')):
                with self.assertRaises(ValueError):tarot_assets.prepare_public_domain([3])
