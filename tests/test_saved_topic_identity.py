"""Saved generated themes retain their identity after a clean worker restart."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from content_memory import ContentMemory, units
from matrix_rules import THEMES
from prepared_carousels import prepare

class SavedTopicIdentityTests(unittest.TestCase):
    def setUp(self):
        self.themes = patch.dict(THEMES, {k:v for k,v in THEMES.items() if not k.startswith('explore_')}, clear=True)
        self.themes.start()
        self.addCleanup(self.themes.stop)

    def config(self):
        return {'type':'arcana_series','theme':'explore_E1_motivation',
                'position':'E1','part':1,'part_arcana':[3,4,5,6],
                'slides':[{'layout':'arcana','paragraphs':['интерес к делу поддерживают ясные задачи']} ]}

    def test_identity_does_not_depend_on_planner_import_order(self):
        config=self.config()
        expected=[f'arcana:position:E1:angle:motivation:E1:{n}' for n in config['part_arcana']]
        self.assertNotIn(config['theme'],THEMES)
        self.assertEqual(units(config),expected)
        from topic_planner import register_topics
        register_topics()
        self.assertEqual(units(config),expected)

    def test_saved_part_reaches_background_preparation_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ContentMemory(Path(tmp)/'memory.json')
            memory.reserve('saved/part-01',self.config())
            for key in list(THEMES):
                if key.startswith('explore_'):THEMES.pop(key)
            memory=ContentMemory(Path(tmp)/'memory.json')
            with patch('background_history.BackgroundHistory'), patch('backgrounds.search_candidates',side_effect=RuntimeError('background reached')) as search:
                with self.assertRaisesRegex(RuntimeError,'background reached'):
                    prepare('saved/part-01',memory,Path(tmp)/'render')
                search.assert_called_once()

    def test_changed_text_or_position_is_still_refused_before_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ContentMemory(Path(tmp)/'memory.json')
            memory.reserve('saved/part-01',self.config())
            original=copy.deepcopy(memory.data['posts']['saved/part-01'])
            for change in ('text','position'):
                record=copy.deepcopy(original)
                if change=='text':record['content']['slides'][0]['paragraphs']=['другой текст']
                else:record['content']['position']='C'
                memory.data['posts']['saved/part-01']=record
                with patch('backgrounds.search_candidates') as search:
                    with self.assertRaisesRegex(ValueError,'Сохранённый текст повреждён'):
                        prepare('saved/part-01',memory,Path(tmp)/change)
                    search.assert_not_called()
