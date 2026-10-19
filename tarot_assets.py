"""User-selected rounded tarot cutouts, preserved exactly from site banners."""
import hashlib
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parent

def prepare(numbers):
    root=ROOT/'assets/tarot'; root.mkdir(exist_ok=True)
    records=json.loads((root/'source-manifest.json').read_text(encoding='utf-8'))
    lookup={r['number']:r for r in records}; paths={}
    for number in numbers:
        record=lookup[number]; target=root/f'{number:02}.png'
        if not target.exists():
            url=record['banner_url']; parsed=urllib.parse.urlparse(url)
            if parsed.scheme!='https' or parsed.hostname!='numerolog.ru': raise ValueError('Неизвестный источник карты.')
            req=urllib.request.Request(url,headers={'User-Agent':'QuantaFate/1.0'})
            with urllib.request.urlopen(req,timeout=35) as response: data=response.read(2*1024*1024)
            if hashlib.sha256(data).hexdigest()!=record['banner_sha256']:
                raise ValueError('Баннер карты изменился; требуется проверить контур.')
            source=Image.open(io.BytesIO(data)).convert('RGB')
            if source.size!=(870,400): raise ValueError('Изменился размер баннера.')
            card=source.crop(tuple(record['crop_box'])).convert('RGBA')
            w,h=card.size; scale=8
            mask=Image.new('L',(w*scale,h*scale))
            ImageDraw.Draw(mask).rounded_rectangle((.5*scale,.5*scale,(w-.5)*scale,(h-.5)*scale),radius=11*scale,fill=255)
            card.putalpha(mask.resize((w,h),Image.Resampling.LANCZOS)); card.save(target)
        with Image.open(target) as card:
            if card.mode!='RGBA' or card.size!=(156,299) or card.getpixel((0,0))[3]!=0:
                raise ValueError('Некорректная прозрачность карты.')
        paths[number]=target
    return paths

