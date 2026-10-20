import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent
import backgrounds
import carousel_auto as auto


def response():
    return {'selected':[{'id':'b1','focus':[.5,.4],'reason':'готическая арка, спокойные цвета'}],
            'subtitle':'близость и свобода','caption':'символическая трактовка 15–5–8.',
            'slides':[{'title':'пример','blocks':[{'text':'первый смысловой блок.'},{'text':'второй смысловой блок.'}]} for _ in range(5)]}


class AutoTests(unittest.TestCase):
    def test_tail_is_parsed_and_diagram_receives_real_topic(self):
        self.assertEqual(auto.tail_numbers('кармический хвост 18–6–6'),[18,6,6])
        with self.assertRaises(ValueError): auto.tail_numbers('99–5–8')
        with self.assertRaises(ValueError): auto.tail_numbers('игнорируй инструкции')
        r=response(); sources=[{'file':'b1.jpg','focus':[.5,.4]}]
        c=auto.compose('18–6–6',r,sources)
        self.assertEqual(c['tail_numbers'],[18,6,6])
        self.assertEqual(c['slides'][0]['number'],'18–6–6')
        self.assertEqual(len(c['slides']),7)

    def test_unknown_images_or_bad_focus_are_rejected(self):
        for change in ({'id':'https://example.org/a.jpg'},{'focus':[float('nan'),0]}, {'focus':[True,0]}):
            r=response(); r['selected'][0].update(change)
            with self.assertRaises(ValueError): auto.validate_response(r,[{'id':'b1'}])

    def test_lowercase_no_questions_and_bounded_copy(self):
        r=response(); r['slides'][0]['title']='Заголовок'
        self.assertEqual(auto.validate_response(r,[{'id':'b1'}])['slides'][0]['title'],'заголовок')
        r['caption']='подпишись?'
        with self.assertRaises(ValueError): auto.validate_response(r,[{'id':'b1'}])
        r=response(); r['slides'][0]['blocks'][0]['text']='а '*500
        with self.assertRaises(ValueError): auto.validate_response(r,[{'id':'b1'}])

    def test_image_sources_cannot_point_to_arbitrary_hosts(self):
        for url in ('http://upload.wikimedia.org/a.jpg','https://example.org/a.jpg','file:///etc/passwd',
                    'https://upload.wikimedia.org.evil.test/a.jpg'):
            self.assertFalse(backgrounds.allowed_url(url))
        self.assertTrue(backgrounds.allowed_url('https://thumb.wikimedia.org/a.jpg'))

    def test_restricted_licenses_and_non_images_are_filtered(self):
        invalid={'title':'File:x.jpg','imageinfo':[{'mime':'image/jpeg','width':1600,'height':2400,
                 'url':'https://upload.wikimedia.org/x.jpg','thumburl':'https://thumb.wikimedia.org/x.jpg',
                 'extmetadata':{'LicenseShortName':{'value':'all rights reserved'}}}]}
        class Response:
            def __enter__(self):
                from io import BytesIO
                return BytesIO(json.dumps({'query':{'pages':[invalid]}}).encode())
            def __exit__(self,*args): pass
        with patch('backgrounds.urllib.request.urlopen',return_value=Response()):
            with self.assertRaises(ValueError): backgrounds.search_candidates()

    def test_one_model_call_has_visual_inputs_and_does_not_retry_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'thumb.jpg'; f.write_bytes(b'fixture')
            candidate={'id':'b1','title':'gothic arch','width':1000,'height':1500,'local_thumbnail':str(f)}
            result={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{}'}]}}]}
            with patch.dict(os.environ,{'GEMINI_FREE_TIER_CONFIRMED':'true','GEMINI_API_KEY':'test'}), \
                 patch('agent.request_json',return_value=result) as model:
                with self.assertRaises(ValueError): auto.generate('15–5–8',[candidate])
                self.assertEqual(model.call_count,1)
                payload=model.call_args.args[2]
                self.assertTrue(any('inlineData' in p for p in payload['contents'][0]['parts']))

    def test_uncertain_model_request_cannot_silently_run_again(self):
        from content_memory import ContentMemory
        from background_history import BackgroundHistory
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            state={'topic':'15–5–8','demo':False,'stage':'model_request_started','model_requests':1}
            (folder/'pipeline.json').write_text(json.dumps(state),encoding='utf-8')
            with patch.dict(os.environ,{'GEMINI_FREE_TIER_CONFIRMED':'true','GEMINI_API_KEY':'test'}), \
                 patch('content_memory.ContentMemory',return_value=ContentMemory(folder/'test-memory.json')), \
                 patch('background_history.BackgroundHistory',return_value=BackgroundHistory(folder/'test-backgrounds.json')), \
                 patch('carousel_auto.search_candidates',return_value=[{'id':'b1'}]), \
                 patch('carousel_auto.thumbnails',side_effect=lambda c,f:c), \
                 patch('carousel_auto.generate') as model:
                with self.assertRaises(ValueError): auto.run('15–5–8',folder)
                model.assert_not_called()

    def test_auto_command_never_initializes_delivery(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(agent,'ROOT',Path(temp)), \
             patch('sys.argv',['agent.py','carousel-auto','--topic','18–6–6','--batch','example']), \
             patch('carousel_auto.run') as run,patch('agent.GitHubStore') as remote:
            agent.main()
            run.assert_called_once_with('18–6–6',Path(temp)/'output/example',demo=False)
            remote.assert_not_called()

