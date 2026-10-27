import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from content_memory import ContentMemory,units
from tiktok_formats import next_format,choice_count
from oracle_posts import validate

class OracleTests(unittest.TestCase):
    def test_alternation_uses_scheduled_order_and_preserves_matrix_parts(self):
        def post(kind,date,status='accepted'):
            return {'content':{'type':kind},'deliveries':{'tiktok':{'status':status,
              'receipt':{'provider':'postwire','run_at':date}}}}
        memory=SimpleNamespace(data={'posts':{'later':post('oracle_pick','2026-11-01T10:00:00Z'),
          'earlier':post('arcana_series','2026-10-30T10:00:00Z')}})
        self.assertEqual(next_format(memory),'matrix')
        memory.data['posts']['last']=post('arcana_series','2026-11-06T10:00:00Z')
        self.assertEqual(next_format(memory),'oracle')

    def test_card_count_varies_between_three_and_six(self):
        memory=SimpleNamespace(data={'posts':{}});counts=[]
        for i in range(4):
            counts.append(choice_count(memory));memory.data['posts'][str(i)]={'content':{'type':'oracle_pick'},'status':'prepared'}
        self.assertEqual(set(counts),{3,4,5,6})

    def test_same_question_cannot_reappear_under_new_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ContentMemory(path=Path(tmp)/'memory.json')
            config={'type':'oracle_pick','question_id':'between','title':'что между вами','slides':[{'paragraphs':['свой текст первого поста']} ]}
            memory.reserve('first',config)
            changed=copy.deepcopy(config);changed['title']='что происходит между вами';changed['slides'][0]['paragraphs']=['совсем другой текст']
            with self.assertRaises(ValueError):memory.reserve('second',changed)

    def test_unrelated_or_duplicate_cards_are_rejected(self):
        option={'card_id':'fl-03','visual_reason':'на карте видна взрослая пара, сцена связана с романтическим интересом'}
        base={'question':'что он чувствует к тебе','question_id':'his_feelings'}
        with self.assertRaises(ValueError):validate({**base,'options':[option]*3},[{'id':'fl-03'}],3)
        other=copy.deepcopy(option);other['card_id']='invented-card'
        with self.assertRaises(ValueError):validate({**base,'options':[option,other,{**option,'card_id':'fl-14'}]},[{'id':'fl-03'},{'id':'fl-14'}],3)

    def test_different_visual_questions_do_not_collide_on_same_caption(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory=ContentMemory(path=Path(tmp)/'memory.json')
            for key,title in [('feelings','что он чувствует к тебе'),('future','что будет дальше между вами')]:
                memory.reserve(key,{'type':'oracle_pick','question_id':key,'title':title,'caption':'больше в тгк @quantafate',
                  'options':[{'card_id':'fl-14'}],'slides':[]})
            self.assertEqual(len(memory.data['posts']),2)

    def test_visual_render_keeps_five_equal_square_panels(self):
        from PIL import Image
        from oracle_posts import deck,DECK
        from oracle_layout import render
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bg=root/'bg.jpg';Image.new('RGB',(1200,1600),'#304232').save(bg)
            manifest=deck()
            for count in (3,4,5,6):
                folder=root/str(count)
                render({'title':'что он чувствует к тебе','options':[{'card_id':c['id']} for c in manifest['cards'][:count]]},folder,bg,DECK,manifest,seed='test')
                paths=sorted((folder/'slides').glob('*.png'));self.assertEqual(len(paths),5)
                for path in paths:
                    with Image.open(path) as im:
                        self.assertEqual(im.size,(1080,1920))
                        self.assertEqual(im.getpixel((0,419)),(0,0,0))
                        self.assertEqual(im.getpixel((0,1500)),(0,0,0))
