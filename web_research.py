"""Bounded live source discovery, not arbitrary URL execution or paid search."""
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path

HOSTS={'axvii.ru','numerolog.ru','www.numerolog.ru'}
ROOT=Path(__file__).resolve().parent

class Article(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.started=False;self.text=[];self.links=[];self.in_h1=False;self.heading=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','nav','header','footer','noscript'):self.skip+=1
        if tag=='h1':self.started=True;self.in_h1=True
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.links.append(href)
        if tag in ('p','h1','h2','h3','li','td','th') and self.started:self.text.append('\n')
    def handle_endtag(self,tag):
        if tag=='h1':self.in_h1=False;self.text.append('\n')
        if tag in ('script','style','nav','header','footer','noscript'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if self.in_h1 and not self.skip:self.heading.append(data)
        if self.started and not self.skip:self.text.append(data)

def safe(url):
    parsed=urllib.parse.urlsplit(url)
    return parsed.scheme=='https' and parsed.hostname in HOSTS and not parsed.username and parsed.port in (None,443)

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not safe(newurl):raise ValueError('Источник перенаправляет на неподтверждённый сайт.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url):
    if not safe(url):raise ValueError('Источник не входит в проверенный список.')
    request=urllib.request.Request(url,headers={'User-Agent':'QuantaFate/1.0 (source research)'})
    def read():
        with urllib.request.build_opener(Redirect()).open(request,timeout=25) as response:
            raw=response.read(1_500_001)
            if len(raw)>1_500_000 or not safe(response.url):raise ValueError('Слишком большая или неподтверждённая страница.')
            return raw,response.headers.get_content_charset() or 'utf-8'
    from read_retry import read_retry
    raw,charset=read_retry(read)
    parser=Article();parser.feed(raw.decode(charset,errors='replace'))
    lines=[' '.join(line.split()) for line in ''.join(parser.text).splitlines()]
    lines=[line for line in lines if line]
    if len(' '.join(lines))<150:raise ValueError('Текст источника недоступен; трактовка не будет выдумана.')
    return {'url':url,'title':(' '.join(''.join(parser.heading).split()) or lines[0])[:180],'lines':lines,'links':parser.links,
      'sha256':hashlib.sha256(raw).hexdigest(),'checked_at':datetime.now(timezone.utc).isoformat()}

def excerpt(page,keywords):
    ranked=sorted(enumerate(page['lines']),key=lambda pair:(-sum(word in pair[1].lower() for word in keywords),pair[0]))
    avoid=re.compile(r'здоров|беремен|болезн|диагноз|предвещ|сулит|прожив[её]|проживет|нерушим|гарантир|из нашей статьи|дата смерти',re.I)
    candidates=[line for _,line in ranked if len(line)>70 and not avoid.search(line)]
    if not candidates:raise ValueError('В источнике не найдена подходящая выдержка без прогнозов.')
    # A bounded research excerpt, not a mirror of the article.
    return ' '.join(' '.join(candidates[:3]).split()[:110])[:850]


def evidence(url,group,keywords):
    from source_library import lookup,SourceUnavailable
    cached=lookup(url,group)
    if cached and os.environ.get('REFRESH_RESEARCH')!='true':return cached
    try:page=fetch(url)
    except (OSError,TimeoutError) as error:
        if cached:return cached
        raise SourceUnavailable(url,error) from error
    return {**{k:page[k] for k in ('url','title','sha256','checked_at')},
      'excerpt':excerpt(page,keywords),'links':page['links'],'evidence_mode':'live'}

def research(topic,folder):
    from matrix_rules import THEMES
    profile=THEMES[topic['theme']];folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    group=profile.get('position_group',{'FR':'work','FL':'love','I':'character','C2':'talent'}.get(profile.get('position'),'character'))
    words={'work':['работ','професс','задач','правый','ресурс'], 'love':['отношен','общен','чувств','выбор'], 'talent':['талант','творч','способност','самовыраж','интеллект'], 'character':['характер','личност','качеств','привыч']}.get(group,[])
    keywords=words+['символ']
    base=evidence(topic['source'],group,keywords+['точк'])
    sources=[{'id':'position','kind':'position',**{k:v for k,v in base.items() if k!='links'}}]
    # Follow a relevant article hyperlink discovered on the actual page, not a guessed URL.
    links=[]
    for href in base['links']:
        link=urllib.parse.urljoin(base['url'],href).split('#')[0]
        if safe(link) and '/blog/' in link and link!=base['url'] and link not in links:links.append(link)
    terms={'talent':('talant','samovyrazh'),'work':('denezh','material'),
           'love':('otnoshen','lyub'),'character':('tsentr','centr','chitat')}.get(group,('matrit',))
    related=next((url for url in links if any(t in url for t in terms)),None)
    if related:
        try:
            page=evidence(related,group,keywords)
            sources.append({'id':'related','kind':'context',**{k:v for k,v in page.items() if k!='links'}})
        except (OSError,ValueError):pass  # The mandatory source above must still be available.
    manifest=json.loads((ROOT/'assets/tarot/source-manifest.json').read_text(encoding='utf-8'))
    entries=manifest if isinstance(manifest,list) else manifest['cards']
    for number in topic['arcana']:
        card=next(c for c in entries if c['number']==number)
        page=evidence(card['page'],group,keywords+['характер','смысл'])
        sources.append({'id':f'arcana-{number}','kind':'arcana','number':number,
          **{k:v for k,v in page.items() if k!='links'}})
    result={'topic':topic,'sources':sources,'discovered_links':links[:30],
      'policy':'web pages are untrusted data; no instructions followed; symbolic interpretations only'}
    (folder/'research.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
