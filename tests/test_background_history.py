import tempfile
import unittest
from pathlib import Path
from background_history import BackgroundHistory
import arcana_series as series
from matrix_rules import series_plan

class BackgroundHistoryTests(unittest.TestCase):
    def test_history_survives_restart_and_blocks_other_posts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'history.json'
            first={'page':'commons/one','url':'image/one','sha256':'abc'}
            h=BackgroundHistory(path);h.reserve('batch-a',{1:first})
            restarted=BackgroundHistory(path)
            self.assertFalse(restarted.available(first,'batch-b'))
            restarted.reserve('batch-a',{1:first})
            for batch,part in [('batch-a',2),('batch-b',1)]:
                with self.assertRaises(ValueError): restarted.reserve(batch,{part:first})
            with self.assertRaises(ValueError): restarted.reserve('batch-b',{1:{'page':'other','sha256':'abc'}})

    def test_remote_store_persists_shared_history(self):
        class Store:
            data=None
            def read_state(self,path): return self.data
            def save_state(self,path,data): self.data=data
        store=Store();BackgroundHistory(store=store).reserve('a',{1:{'page':'source'}})
        self.assertFalse(BackgroundHistory(store=store).available({'page':'source'},'b'))

    def test_similar_image_is_rejected_even_under_another_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=BackgroundHistory(Path(tmp)/'history.json')
            h.reserve('a',{1:{'page':'first','visual_hash':'aabbccdd00112233'}})
            with self.assertRaises(ValueError): h.reserve('b',{1:{'page':'second','visual_hash':'aabbccdd00112232'}})

    def test_frame_or_crop_variant_cannot_bypass_image_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=BackgroundHistory(Path(tmp)/'history.json')
            h.reserve('a',{1:{'page':'original','visual_hash':'aabbccdd00112233'}})
            with self.assertRaises(ValueError):
                h.reserve('b',{1:{'page':'framed','visual_hash':'0000000000000000','visual_hashes':['0000000000000000','aabbccdd00112233']}})

    def test_each_carousel_has_one_background_and_parts_are_distinct(self):
        plan=series_plan('profession')
        response={'caption':'пример','entries':[{'number':n,'paragraphs':['абзац','абзац']} for n in plan['allowed']]}
        covers=[]
        for part in range(1,6):
            config=series.compose('profession',part,plan,response,[{'file':f'b{part}.jpg','focus':[.5,.5]}])
            self.assertEqual({s['background'] for s in config['slides']},{f'b{part}.jpg'})
            covers.append(config['slides'][0]['background'])
        self.assertEqual(len(set(covers)),5)

    def test_used_artwork_is_filtered_before_model_selection(self):
        from PIL import Image
        from backgrounds import fresh_thumbnails
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'candidate.png'
            im=Image.new('RGB',(90,80),'white');im.save(path)
            history=BackgroundHistory(Path(tmp)/'history.json')
            history.reserve('old',{1:{'page':'old-url','visual_hash':'0000000000000000'}})
            candidate={'id':'b1','page':'alternate-scan','local_thumbnail':str(path)}
            with self.assertRaises(ValueError):fresh_thumbnails([candidate],history,'new')
            self.assertEqual(fresh_thumbnails([candidate],history,'old'),[candidate])
