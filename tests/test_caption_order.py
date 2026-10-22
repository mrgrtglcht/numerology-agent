import unittest
from types import SimpleNamespace
from cloud_agent import tiktok_caption,tiktok_input,public_caption
from prepared_carousels import check_order,select


class CaptionOrderTests(unittest.TestCase):
    def test_short_caption_uses_topic_not_model_instructions_or_urls(self):
        text=tiktok_caption({'theme':'explore_E1_motivation','part':2,'total_parts':5,
          'caption':'разбор арканов серии e1 через призму мотивации https://t.me/quantafate'})
        self.assertEqual(text,'что поддерживает твою мотивацию · часть 2/5\n\nбольше разборов в тгк @quantafate')
        self.assertLess(len(text),140)

    def test_short_caption_cannot_silently_strip_required_credit(self):
        config=public_caption({'caption':'текст'},[{'license':'CC BY 4.0','creator':'author','page':'source','license_url':'license'}])
        with self.assertRaises(ValueError):tiktok_input(config,['a','b'])

    def test_part_two_cannot_be_sent_before_part_one(self):
        memory=SimpleNamespace(data={'posts':{}})
        with self.assertRaises(ValueError):check_order({'type':'arcana_series','theme':'test','part':2},memory)
        memory.data['posts']['one']={'theme':'test','part':1,'deliveries':{'tiktok':{'status':'accepted'}}}
        check_order({'type':'arcana_series','theme':'test','part':2},memory)

    def test_active_series_missing_first_preview_is_reused(self):
        posts={}
        for owner,theme,part,status in [('other','other',1,None),('two','active',2,'accepted'),('first','active',1,None),('fourth','active',4,None)]:
            posts[owner]={'theme':theme,'part':part,'status':'prepared','formats':['tiktok'],
              'content':{'type':'arcana_series','theme':theme,'part':part},
              'deliveries':{'tiktok':{'status':status}} if status else {}}
        self.assertEqual(select(SimpleNamespace(data={'posts':posts})),'first')

    def test_generate_next_active_part_before_switching_to_old_other_series(self):
        memory=SimpleNamespace(data={'posts':{
          'one':{'theme':'active','part':1,'content':{'total_parts':5},'deliveries':{'tiktok':{'status':'accepted'}}},
          'other':{'theme':'other','part':1,'status':'prepared','formats':['tiktok'],'content':{'type':'arcana_series','theme':'other','part':1},'deliveries':{}}
        }})
        self.assertIsNone(select(memory))
