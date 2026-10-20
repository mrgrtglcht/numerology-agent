import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import pinterest_carousel as pin
from matrix_rules import series_plan
from arcana_series import compose

class PinterestTests(unittest.TestCase):
    def example(self):
        p=series_plan('profession')
        response={'caption':'пример','entries':[{'number':n,'paragraphs':['профессии и рабочие задачи для размышления.','практические способы проявить способности.']} for n in p['allowed']]}
        return compose('profession',1,p,response,[{'file':'bg.jpg','focus':[.5,.5]}])

    def test_adaptation_keeps_all_arcana_and_bot_within_five_images(self):
        pages=pin.plan(self.example())
        self.assertEqual(len(pages),5)
        self.assertEqual([p['arcana_number'] for p in pages if p['layout']=='arcana'],[3,4,5,6])
        self.assertEqual(pages[0]['layout'],'pin_overview')
        self.assertTrue(pages[-1]['bot_footer'])

    def test_native_render_size_and_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);Image.new('RGB',(700,1100),'#405044').save(r/'bg.jpg')
            cards={}
            for n in range(3,7):
                path=r/f'card{n}.png';Image.new('RGBA',(156,299),'#c4b48c').save(path);cards[n]=path
            files=pin.render(self.example(),r/'out',r,cards)
            self.assertEqual(len(files),5)
            for path in files:
                with Image.open(path) as im:self.assertEqual(im.size,(1000,1500))
            manifest=json.loads((r/'out/content.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['size'],[1000,1500])

