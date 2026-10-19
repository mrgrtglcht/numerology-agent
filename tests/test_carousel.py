import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import agent
import carousel
from PIL import Image


class CarouselTests(unittest.TestCase):
    def test_local_command_never_calls_generation_or_delivery(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(agent,'ROOT',Path(temp)), \
             patch('sys.argv',['agent.py','carousel','--batch','style']), \
             patch('carousel.render') as render, \
             patch('agent.request_json') as network, \
             patch('agent.generate') as generate, \
             patch('agent.GitHubStore') as store, redirect_stdout(io.StringIO()):
            agent.main()
            render.assert_called_once_with(config_path=None,output=Path(temp)/'output/style')
            network.assert_not_called()
            generate.assert_not_called()
            store.assert_not_called()

    def test_oversized_content_stops_instead_of_exporting_clipped_slide(self):
        content=json.loads((carousel.ROOT/'examples/15-5-8.json').read_text(encoding='utf-8'))
        slide=copy.deepcopy(content['slides'][2])
        slide['blocks']=[{'text':'длинный текст '*2000}]
        slide['background']='test.png'
        content['slides']=[slide]
        with tempfile.TemporaryDirectory() as temp:
            config=Path(temp)/'content.json'
            Image.new('RGB',(700,1200),'#111511').save(Path(temp)/'test.png')
            config.write_text(json.dumps(content,ensure_ascii=False),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'overflows'):
                carousel.render(config,Path(temp)/'out',Path(temp))
            self.assertFalse((Path(temp)/'out/slides/01.png').exists())

    def test_background_cannot_escape_asset_directory(self):
        content=json.loads((carousel.ROOT/'examples/15-5-8.json').read_text(encoding='utf-8'))
        content['slides'][0]['background']='../../.env'
        with tempfile.TemporaryDirectory() as temp:
            config=Path(temp)/'content.json'
            config.write_text(json.dumps(content),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'каталоге фонов'):
                carousel.render(config,Path(temp)/'out')


if __name__=='__main__': unittest.main()

