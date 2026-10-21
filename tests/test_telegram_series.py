import unittest
from telegram_series import select
from matrix_rules import allowed

class Memory:
    def __init__(self):self.data={'posts':{}}
    def add(self,key,status='published'):
        self.data['posts'][key]={'status':'published' if status=='published' else 'prepared',
          'content':{'editorial_key':key},'deliveries':{'telegram':{'status':status}}}

class TelegramSequenceTests(unittest.TestCase):
    def test_intro_precedes_every_single_valid_centre_arcana(self):
        memory=Memory();p=select(memory)
        self.assertEqual((p['theme'],p['article_kind'],p['arcana']),('centre','intro',[]))
        memory.add(p['editorial_key'])
        seen=[]
        for n in allowed('I'):
            p=select(memory);self.assertEqual(p['arcana'],[n]);self.assertEqual(p['position'],'I')
            seen.append(n);memory.add(p['editorial_key'])
        self.assertNotIn(1,seen);self.assertNotIn(2,seen)
        p=select(memory);self.assertEqual((p['theme'],p['article_kind']),('talents','intro'))

    def test_unconfirmed_delivery_blocks_series(self):
        for status in ('sending','needs_review','accepted'):
            memory=Memory();memory.add('telegram-series:centre:intro',status)
            with self.assertRaises(ValueError):select(memory)

    def test_prepared_preview_is_reused_without_advancing(self):
        memory=Memory();memory.add('telegram-series:centre:intro','draft')
        p=select(memory)
        self.assertEqual(p['cached_owner'],'telegram-series:centre:intro')
        self.assertEqual(p['article_kind'],'intro')

    def test_tiktok_publication_does_not_advance_telegram(self):
        memory=Memory();memory.data['posts']['tt']={'status':'published','content':{'theme':'centre'},'deliveries':{'tiktok':{'status':'published'}}}
        self.assertEqual(select(memory)['article_kind'],'intro')

