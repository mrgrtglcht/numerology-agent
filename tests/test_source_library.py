import copy
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from source_library import lookup,PATH
from web_research import evidence,research
from cloud_checkpoint import preparation_failed
from preparation_errors import diagnostic


class SourceLibraryTests(unittest.TestCase):
    def test_every_card_and_position_source_has_dated_verified_evidence(self):
        from topic_planner import register_topics
        from matrix_rules import THEMES
        register_topics()
        manifest=json.loads((PATH.parent.parent/'tarot/source-manifest.json').read_text(encoding='utf-8'))
        urls={c['page'] for c in manifest}|{p['source'] for p in THEMES.values() if p.get('source')}
        for url in urls:
            for group in ('work','love','talent','character'):
                record=lookup(url,group)
                self.assertIsNotNone(record,(url,group))
                self.assertTrue(record['checked_at']);self.assertLessEqual(len(record['excerpt']),850)

    def test_broken_star_url_is_replaced_by_actual_discovered_link(self):
        from topic_planner import register_topics
        from matrix_rules import series_plan
        register_topics();topic=series_plan('explore_E1_motivation')
        topic={**topic,'part':4,'arcana':[15,16,17,18],'source':'https://axvii.ru/blog/kak-chitat-matritsu-sudby'}
        with tempfile.TemporaryDirectory() as tmp,patch('web_research.fetch',side_effect=urllib.error.URLError('offline')) as fetch:
            result=research(topic,tmp)
        star=next(s for s in result['sources'] if s['id']=='arcana-17')
        self.assertEqual(star['url'],'https://numerolog.ru/tarot/17-arkan-taro-zvezda.html')
        self.assertEqual(star['evidence_mode'],'verified_library')
        required={s['url'] for s in result['sources'] if s['id']!='related'}
        self.assertTrue(all(c.args[0] not in required for c in fetch.call_args_list))

    def test_corrupt_evidence_is_not_silently_accepted(self):
        data=json.loads(PATH.read_text(encoding='utf-8'));url=next(iter(data['records']))
        data['records'][url]['excerpts']['work']='invented replacement'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'library.json';path.write_text(json.dumps(data),encoding='utf-8')
            with patch('source_library.PATH',path):
                with self.assertRaises(ValueError):lookup(url,'work')

    def test_unknown_source_is_not_replaced_with_unrelated_evidence(self):
        self.assertIsNone(lookup('https://axvii.ru/blog/not-in-library','work'))

    def test_network_preparation_can_resume_after_three_days_without_send_retry(self):
        class Store:
            def save_state(self,key,value):self.value=value
        store=Store();error=urllib.error.HTTPError('https://example.org/page?secret=hidden',503,'down',{},io.BytesIO())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cloud-tiktok-2026-10-24';path.mkdir();previous=None
            for _ in range(4):previous=preparation_failed(store,'tiktok',path,'2026-10-24',previous,error=error)
        self.assertEqual(previous['stage'],'preparation_failed')
        self.assertEqual(previous['diagnostic']['http_status'],503)
        self.assertNotIn('hidden',json.dumps(previous))
