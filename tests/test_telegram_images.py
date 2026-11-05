import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import cloud_agent as cloud


class TelegramImageTests(unittest.TestCase):
    def deliver(self,license):
        memory=Mock();memory.data={'posts':{'article':{}}}
        store=Mock();store.put.return_value='https://example.org/illustration.jpg'
        config={'title':'5 аркан — иерофант','caption':'подробный текст',
                'image_source':{'license':license,'file':'image.jpg','id':'b1','focus':[.5,.5]}}
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'backgrounds').mkdir();(folder/'backgrounds/image.jpg').write_bytes(b'image')
            with patch.dict('os.environ',{'TELEGRAM_BOT_TOKEN':'fake','TELEGRAM_CHANNEL_ID':'@test'}), \
                    patch.object(cloud,'request_json',return_value={'ok':True,'result':{'message_id':10}}) as photo, \
                    patch.object(cloud,'send_article',return_value={'message_id':11}) as text:
                receipt=cloud.deliver_article(config,'article',folder,store,memory)
                return receipt,photo,text,store,memory

    def test_optional_image_has_no_duplicate_title_or_source_caption(self):
        receipt,photo,text,store,memory=self.deliver('Public domain')
        payload=photo.call_args.args[2]
        self.assertEqual(set(payload),{'chat_id','photo'})
        text.assert_called_once()
        self.assertEqual(receipt,{'message_id':11,'image_message_id':10})
        store.save_state.assert_called_once()
        memory.delivery.assert_called_with('article','telegram','published',receipt)

    def test_legacy_attribution_image_is_omitted_instead_of_removing_required_credit(self):
        for license in ('CC BY-SA 2.0','',None):
            receipt,photo,text,store,_=self.deliver(license)
            photo.assert_not_called();store.put.assert_not_called();text.assert_called_once()
            self.assertEqual(receipt,{'message_id':11})
