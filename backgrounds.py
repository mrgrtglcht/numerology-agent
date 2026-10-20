"""Bounded Commons search with attributable, reusable image candidates."""
import hashlib
import html
import io
import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

API='https://commons.wikimedia.org/w/api.php'
QUERIES=('gothic church ruin painting', 'gothic window ivy', 'abbey ruins ivy',
         'gothic cathedral painting', 'medieval castle garden', 'gothic ruins')
LICENSES={'public domain','pdm-owner','cc0','cc0 1.0','cc by 4.0','cc by-sa 4.0',
          'cc by 3.0','cc by-sa 3.0','cc by 2.0','cc by-sa 2.0','cc by 2.5','cc by-sa 2.5'}
AGENT='QuantaFate/1.0 (licensed gothic-art carousel previews)'


def clean(value):
    return html.unescape(re.sub('<[^>]*>',' ',str(value))).strip()


def metadata(info,key):
    return clean(info.get('extmetadata',{}).get(key,{}).get('value',''))


def allowed_url(url):
    p=urllib.parse.urlparse(url)
    return p.scheme=='https' and p.hostname in ('upload.wikimedia.org','thumb.wikimedia.org') and not p.username


def read_bytes(url,limit=18*1024*1024):
    if not allowed_url(url): raise ValueError('Изображение должно быть с Wikimedia Commons.')
    req=urllib.request.Request(url,headers={'User-Agent':AGENT})
    with urllib.request.urlopen(req,timeout=40) as response:
        if not allowed_url(response.url): raise ValueError('Неожиданный источник изображения.')
        data=response.read(limit+1)
    if len(data)>limit: raise ValueError('Изображение слишком большое.')
    return data


def search_candidates(limit=8,exclude=None):
    results=[]; seen=set()
    for query in QUERIES:
        query_count=0
        params={'action':'query','format':'json','formatversion':2,'generator':'search',
                'gsrsearch':query,'gsrnamespace':6,'gsrlimit':50,'prop':'imageinfo',
                'iiprop':'url|size|mime|extmetadata|sha1','iiurlwidth':400}
        req=urllib.request.Request(API+'?'+urllib.parse.urlencode(params),headers={'User-Agent':AGENT})
        with urllib.request.urlopen(req,timeout=40) as response: data=json.load(response)
        for page in sorted(data.get('query',{}).get('pages',[]),key=lambda p:p.get('index',999)):
            if page['title'] in seen: continue
            info=(page.get('imageinfo') or [{}])[0]
            w,h=info.get('width',0),info.get('height',0)
            license_name=metadata(info,'LicenseShortName')
            if info.get('mime') not in ('image/jpeg','image/png'): continue
            if w<700 or h<1050 or not .40<=w/h<=1.55: continue
            if w*h>40_000_000 or info.get('size',0)>18*1024*1024: continue
            if license_name.lower() not in LICENSES: continue
            if not allowed_url(info.get('url','')) or not allowed_url(info.get('thumburl','')): continue
            identity={'page':info['descriptionurl'],'url':info['url'],'original_sha1':info.get('sha1')}
            if exclude and exclude(identity): continue
            seen.add(page['title'])
            results.append({'id':f'b{len(results)+1}','title':page['title'],
                            'url':info['url'],'thumbnail':info['thumburl'],
                            'page':info['descriptionurl'],'original_sha1':info.get('sha1'),'width':w,'height':h,
                            'creator':metadata(info,'Artist')[:1000],
                            'credit':metadata(info,'Credit')[:1000],
                            'license':license_name,'license_url':metadata(info,'LicenseUrl'),
                            'query':query})
            if len(results)>=limit: return results
            query_count+=1
            if query_count>=max(2,math.ceil(limit/len(QUERIES))): break
    if not results: raise ValueError('Подходящие фоны с подтверждённой лицензией не найдены.')
    return results


def thumbnails(candidates,folder):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    for item in candidates:
        path=folder/(item['id']+'.jpg')
        if not path.exists():
            raw=read_bytes(item['thumbnail'],limit=3*1024*1024)
            with Image.open(io.BytesIO(raw)) as original:
                image=ImageOps.exif_transpose(original).convert('RGB')
                image.thumbnail((400,650),Image.Resampling.LANCZOS)
                image.save(path,quality=85)
        item['local_thumbnail']=str(path)
    return candidates


def download_selection(candidates,selections,folder):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    known={i['id']:i for i in candidates}; sources=[]
    for selection in selections:
        item=dict(known[selection['id']])
        path=folder/(item['id']+'.jpg')
        if not path.exists():
            raw=read_bytes(item['url'])
            with Image.open(io.BytesIO(raw)) as original:
                if original.width*original.height>40_000_000: raise ValueError('Слишком большое изображение.')
                image=ImageOps.exif_transpose(original).convert('RGB')
                image.thumbnail((2400,3600),Image.Resampling.LANCZOS)
                image.save(path,quality=95)
        with Image.open(path) as image:
            if image.width<600 or image.height<1000: raise ValueError('Недостаточное разрешение фона.')
        with Image.open(path) as thumb:
            pixels=list(ImageOps.grayscale(thumb).resize((9,8),Image.Resampling.LANCZOS).getdata())
            bits=[pixels[y*9+x]>pixels[y*9+x+1] for y in range(8) for x in range(8)]
            visual_hash=f'{sum(int(bit)<<i for i,bit in enumerate(bits)):016x}'
        item.update({'visual_hash':visual_hash,'file':path.name,'focus':selection['focus'],
                     'selection_reason':selection['reason'],
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'modifications':'cropped to 9:16, darkened, overlaid with text'})
        item.pop('local_thumbnail',None)
        sources.append(item)
    return sources


def write_credits(sources,path):
    parts=['background sources and changes / источники фонов и изменения\n']
    for s in sources:
        parts.append(f"{s['id']}: {s['title']}\n{s['creator']}\n{s['page']}\n"
                     f"{s['license']} — {s['license_url']}\n"
                     f"changes: {s['modifications']}\n")
    Path(path).write_text('\n'.join(parts),encoding='utf-8')

