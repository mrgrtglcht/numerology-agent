import copy
import os
import unittest
from unittest.mock import patch
from content_memory import ContentMemory,body,digest
from matrix_rules import ARCANA
from cloud_agent import validate_telegram_response
from telegram_series import brief
from telegram_title_fix import apply,STATE,OWNER,OLD_TITLE,NEW_TITLE

class Store:
    def __init__(self):self.data={}
    def read_state(self,key):return copy.deepcopy(self.data.get(key))
    def save_state(self,key,value):self.data[key]=copy.deepcopy(value)

class TelegramNameTests(unittest.TestCase):
    def article(self):
        return '\n\n'.join(['в символической трактовке матрицы важны привычки и личные границы. '*6]*5)

    def test_every_single_arcana_title_uses_catalog_instead_of_model_alias(self):
        for number,name in ARCANA.items():
            topic={'article_kind':'single_arcana','number':number,'editorial_key':f'test:{number}',
                   'theme':'centre','position':'I','arcana':[number]}
            response={'title':'название из источника','text':self.article(),
                      'arcana_number':number,'source_ids':['position',f'arcana-{number}']}
            config=validate_telegram_response(response,topic,[{'id':'position'},{'id':f'arcana-{number}'}],'reference')
            self.assertTrue(config['title'].startswith(f'{number} аркан — {name}:'))
            self.assertIn(name,brief(topic))

    def store(self):
        store=Store();memory=ContentMemory(store=store)
        text=self.article()+'\n\nее часто называют образом хозяина или императора. внутренний хозяин.'
        config={'theme':'telegram_article','topic':'emperor-test','title':OLD_TITLE,'arcana_number':4,
                'caption':text,'slides':[{'body':text}]}
        memory.reserve(OWNER,config);memory.delivery(OWNER,'telegram','published',{'message_id':10})
        return store

    def test_existing_message_is_edited_once_and_memory_follows_verified_text(self):
        store=self.store()
        def edit(label,url,payload):
            self.assertTrue(url.endswith('/editMessageText'))
            self.assertEqual(payload['message_id'],10)
            self.assertEqual(payload['chat_id'],'@quantafate')
            self.assertTrue(payload['text'].startswith(NEW_TITLE))
            self.assertNotIn('хозяин',payload['text'])
            return {'ok':True,'result':{'message_id':10,'text':payload['text']}}
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHANNEL_ID':'@quantafate'}),patch('telegram_title_fix.request_json',side_effect=edit) as request:
            apply(store);apply(store)
            request.assert_called_once()
        self.assertEqual(store.data[STATE]['stage'],'complete')
        record=ContentMemory(store=store).data['posts'][OWNER]
        self.assertEqual(record['title'],NEW_TITLE)
        self.assertEqual(record['fingerprint'],digest(body(record['content'])))
        self.assertEqual(record['deliveries']['telegram']['receipt']['message_id'],10)

    def test_unknown_edit_result_is_not_retried(self):
        store=self.store()
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHANNEL_ID':'@quantafate'}),patch('telegram_title_fix.request_json',side_effect=TimeoutError) as request:
            with self.assertRaises(TimeoutError):apply(store)
            apply(store)
            request.assert_called_once()
        self.assertEqual(store.data[STATE]['stage'],'editing')
