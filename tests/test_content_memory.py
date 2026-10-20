import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from content_memory import ContentMemory,units
import arcana_series

def config(numbers=(3,4),theme='profession'):
    return {'type':'arcana_series','theme':theme,'position':'FR','part':1,'part_arcana':list(numbers),
      'slides':[{'layout':'arcana','paragraphs':[f'содержание арканов {numbers} темы {theme}','другая мысль']} ]}

class ContentMemoryTests(unittest.TestCase):
    def test_restart_blocks_repeat_even_after_regrouping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.json';m=ContentMemory(path);m.reserve('a',config())
            m=ContentMemory(path)
            self.assertFalse(m.available('b',units(config((4,5)))))
            with self.assertRaises(ValueError): m.reserve('b',config((4,5)))
            m.reserve('a',config())

    def test_platform_adaptation_is_same_post_and_not_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ContentMemory(Path(tmp)/'memory.json');m.reserve('a',config())
            m.format_ready('a','tiktok');m.format_ready('a','pinterest')
            self.assertEqual(len(m.data['posts']),1)
            self.assertEqual(m.data['posts']['a']['status'],'prepared')
            m.delivery('a','pinterest','accepted',{'status':'scheduled'})
            self.assertEqual(m.data['posts']['a']['status'],'prepared')
            m.delivery('a','pinterest','published',{'status':'sent'})
            self.assertEqual(m.data['posts']['a']['status'],'published')

    def test_same_arcana_on_another_topic_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ContentMemory(Path(tmp)/'memory.json');m.reserve('a',config())
            m.reserve('b',config(theme='talents'))
            self.assertEqual(len(m.data['posts']),2)

    def test_identical_text_with_new_title_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ContentMemory(Path(tmp)/'memory.json');a=config();m.reserve('a',a)
            b=copy.deepcopy(a);b['theme']='talents'
            with self.assertRaises(ValueError): m.reserve('b',b)

    def test_duplicate_part_is_refused_before_model_or_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('content_memory.ROOT',Path(tmp)):
                m=ContentMemory();m.reserve('previous',config((3,4,5,6)))
                with patch('arcana_series.generate_visual') as model,patch('arcana_series.search_candidates') as search:
                    with self.assertRaises(ValueError): arcana_series.run('profession',Path(tmp)/'new',part=1)
                    model.assert_not_called();search.assert_not_called()

    def test_buffer_draft_import_is_idempotent_and_sent_is_confirmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ContentMemory(Path(tmp)/'memory.json')
            p={'id':'one','text':'тестовый пост','status':'draft','channelService':'tiktok','sentAt':None,'externalLink':None}
            m.import_buffer([p]);m.import_buffer([p]);self.assertEqual(len(m.data['posts']),1)
            self.assertEqual(m.data['posts']['buffer/one']['status'],'prepared')
            p['status']='sent';m.import_buffer([p])
            self.assertEqual(m.data['posts']['buffer/one']['status'],'published')

