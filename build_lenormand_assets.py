"""Import the public-domain BnF scans; keep exact source records and hashes."""
import concurrent.futures
import hashlib
import io
import json
import urllib.parse
import urllib.request
import time
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
from backgrounds import API,AGENT,metadata,read_bytes

ROOT=Path(__file__).resolve().parent
PREFIX='File:Grand jeu de société de Melle Lenormand - jeu de cartomancie - jeu de cartes, estampe - Melle Lenormant - btv1b10509225z '

def run():
    folder=ROOT/'assets/oracle/grand-lenormand';folder.mkdir(parents=True,exist_ok=True)
    pages=[]
    cached=ROOT/'output/lenormand-pages.json'
    if cached.exists():pages=json.loads(cached.read_text(encoding='utf-8'))
    for start in (() if pages else (3,43,83)):
        indexes=list(range(start,min(start+40,106),2))
        titles=[PREFIX+f'({i:03} of 105).jpg' for i in indexes]
        params={'action':'query','format':'json','formatversion':2,'titles':'|'.join(titles),'prop':'imageinfo','iiprop':'url|extmetadata|sha1'}
        req=urllib.request.Request(API+'?'+urllib.parse.urlencode(params),headers={'User-Agent':AGENT})
        with urllib.request.urlopen(req,timeout=40) as r:pages.extend(json.load(r)['query']['pages'])
    cached.write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
    def download(p):
        info=p['imageinfo'][0]
        if metadata(info,'LicenseShortName').lower()!='public domain':raise ValueError('Unverified license')
        number=int(p['title'].split('(')[-1][:3]);identity=f'gl-{number:03}'
        url=info['url'].split('?')[0];path=folder/(identity+'.jpg')
        raw=None
        if not path.exists():
            try:raw=read_bytes(url)
            except urllib.error.HTTPError as error:
                if error.code==429:raise
                return None
            im=Image.open(io.BytesIO(raw)).convert('RGB')
            im.thumbnail((600,900),Image.Resampling.LANCZOS)
            im.save(path,quality=94,optimize=True)
        return {'id':identity,'file':path.name,'page':info['descriptionurl'],'url':url,
          'source_sha1':info['sha1'],
          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'license':'Public domain',
          'collection':'Bibliothèque nationale de France','title':p['title'],
          'modifications':'resized only; artwork preserved'}
    cards=[]
    for page in pages:
        try:c=download(page)
        except urllib.error.HTTPError:
            print('Source rate limit; retained verified cached cards.');break
        if c:cards.append(c)
        if len(cards)>=24:break
        time.sleep(.75)
    cards.sort(key=lambda c:c['id'])
    manifest={'deck':'grand lenormand','source_collection':'BnF / Gallica, btv1b10509225z',
      'attribution':'grand lenormand · collection bnf / gallica','interpretation':'original symbolic visual reading; not a quotation from the historical guidebook','cards':cards}
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    sheet=Image.new('RGB',(1300,((len(cards)+9)//10)*220),'#151812');d=ImageDraw.Draw(sheet)
    for i,c in enumerate(cards):
        im=Image.open(folder/c['file']);im.thumbnail((120,190));x=(i%10)*130;y=(i//10)*220
        sheet.paste(im,(x,y));d.text((x,y+193),c['id'],fill='white')
    sheet.save(ROOT/'output/lenormand-contact.jpg',quality=94)
    print('Verified cards:',len(cards))

if __name__=='__main__':
    run()
    import os
    folder=ROOT/'assets/oracle/grand-lenormand'
    if os.environ.get('GITHUB_ACTIONS')=='true':
        from agent import GitHubStore
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        if len(manifest['cards'])<6:raise ValueError('Source not ready: at least six verified cards required.')
        store=GitHubStore()
        for card in manifest['cards']:store.put('assets/oracle/grand-lenormand/'+card['file'],(folder/card['file']).read_bytes())
        store.put('assets/oracle/grand-lenormand/manifest.json',(folder/'manifest.json').read_bytes())
