import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from matrix_rules import THEMES,domains,series_plan
from position_catalog import catalog
from topic_planner import register_topics,choose,check_focus
from content_memory import ContentMemory,units
from web_research import Article,excerpt,safe
import arcana_series

class EditorTests(unittest.TestCase):
    def test_all_bot_positions_have_formula_domain_and_source(self):
        positions=catalog()
        self.assertEqual(set(positions),set(domains()['positions']))
        self.assertEqual(len(positions),32)
        for p in positions.values():
            self.assertTrue(p['formula']);self.assertTrue(p['source'].startswith('https://'))
            self.assertEqual(p['allowed'],domains()['positions'][p['id']])
        for key in ('A3','C3','I1','I2'):
            self.assertFalse(positions[key]['auto_topic_enabled'])
        self.assertEqual(positions['C']['allowed'],list(range(1,13)))

    def test_stable_semantic_identity_survives_title_change(self):
        register_topics();key='explore_C_learning';profile=THEMES[key]
        c={'type':'arcana_series','theme':key,'position':'C','part_arcana':[1,2]}
        before=units(c)
        with patch.dict(profile,{'title':'совсем другая обложка'}):self.assertEqual(units(c),before)

    def test_planner_continues_unused_parts(self):
        register_topics();key='explore_C_learning'
        with tempfile.TemporaryDirectory() as tmp:
            m=ContentMemory(Path(tmp)/'memory.json')
            m.reserve('earlier',{'type':'arcana_series','theme':key,'position':'C','part_arcana':[1,2,3,4],
                      'slides':[{'layout':'arcana','paragraphs':['сохранённая часть','пример']} ]})
            topic=choose(m,'next-post')
            self.assertEqual(topic['theme'],key);self.assertEqual(topic['part'],2)
            self.assertEqual(topic['arcana'],[5,6,7,8])

    def test_unsafe_sources_and_prediction_excerpts_are_excluded(self):
        for url in ('http://axvii.ru/blog/x','https://evil.example/x','https://axvii.ru@evil.example/x','https://axvii.ru:8443/x'):
            self.assertFalse(safe(url))
        good='работа и творчество — символические темы для размышления о привычках и способностях. '
        page={'lines':['карта предвещает благополучную беременность и гарантирует здоровье. '*3,good*3]}
        self.assertNotIn('беременность',excerpt(page,['работа']))

    def test_html_instructions_are_only_data_and_scripts_are_removed(self):
        page=Article();page.feed('<nav>меню</nav><h1>тема</h1><p>полезный текст</p><script>steal_secret()</script>')
        self.assertNotIn('steal_secret',''.join(page.text));self.assertIn('полезный текст',''.join(page.text))

    def test_researched_entries_require_position_and_own_arcana_source(self):
        register_topics();key='explore_C_learning';p=series_plan(key)
        p['allowed']=[1,2,3,4];p['background_count']=1
        research=[{'id':'position'}]+[{'id':f'arcana-{n}'} for n in p['allowed']]
        data={'selected':[{'id':'b1','focus':[.5,.5],'reason':'готическое окно'}],'caption':'пример',
          'entries':[{'number':n,'paragraphs':['учиться помогает практика','второй абзац'],'source_ids':['position',f'arcana-{n}']} for n in p['allowed']]}
        with patch.dict(THEMES[key],{'research_context':research}):
            self.assertEqual(len(arcana_series.validate_response(data,p,[{'id':'b1'}])['entries']),4)
            data['entries'][0]['source_ids']=['position','arcana-2']
            with self.assertRaises(ValueError):arcana_series.validate_response(data,p,[{'id':'b1'}])

    def test_new_motivation_title_cannot_mask_a_profession_list(self):
        with self.assertRaises(ValueError):check_focus('motivation','подходят дизайн, преподавание и управление проектами.')
        check_focus('motivation','тебя вдохновляет видимый результат и возможность создать что-то своё.')

    def test_rejected_unpublished_draft_is_retained_but_does_not_occupy_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ContentMemory(Path(tmp)/'memory.json')
            c={'topic':'тема','caption':'неудачный текст'};m.reserve('a',c)
            m.reject('a','не отвечает теме')
            self.assertTrue(m.available('b',units(c)));self.assertIn('a',m.data['posts'])
            m.reserve('b',c);m.delivery('b','tiktok','published')
            with self.assertRaises(ValueError):m.reject('b','нельзя забыть публикацию')

