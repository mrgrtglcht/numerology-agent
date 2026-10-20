"""Persistent content identity, preparation and verified delivery history."""
import hashlib
import json
import os
import re
from datetime import datetime,timezone
from pathlib import Path

PATH='state/content-memory.json'
ROOT=Path(__file__).resolve().parent

def normal(value): return ' '.join(re.findall(r'[\w]+',str(value).lower().replace('ё','е')))
def digest(value): return hashlib.sha256(normal(value).encode()).hexdigest()

def units(config):
    if config.get('type')=='arcana_series':
        from matrix_rules import THEMES
        key=THEMES.get(config['theme'],{}).get('semantic_key',config['theme'])
        return [f'arcana:{key}:{config.get("position")}:{n}' for n in config['part_arcana']]
    if config.get('tail_numbers'): return ['tail:'+','.join(map(str,config['tail_numbers']))]
    return ['topic:'+normal(config.get('topic') or config.get('title') or config.get('caption'))]

def body(config):
    values=[]
    for slide in config.get('slides',[]):
        if slide.get('layout') in ('bot','location','series_cover','cover'): continue
        if 'paragraphs' in slide: values.extend(slide['paragraphs'])
        for block in slide.get('blocks',[]): values.append(block.get('text',''))
        if slide.get('body'): values.append(slide['body'])
    return ' '.join(values) or config.get('caption','')

class ContentMemory:
    def __init__(self,path=None,store=None):
        self.path=Path(path) if path else ROOT/PATH;self.store=store
        if store is None and path is None and os.environ.get('GITHUB_ACTIONS')=='true':
            from agent import GitHubStore
            self.store=GitHubStore()
        data=self.store.read_state(PATH) if self.store else (json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else None)
        self.data=data if data is not None else {'version':1,'posts':{}}
        if self.data.get('version')!=1 or not isinstance(self.data.get('posts'),dict): raise ValueError('История контента повреждена; повторная генерация остановлена.')

    def save(self):
        if self.store: self.store.save_state(PATH,self.data)
        else:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.path)

    def available(self,owner,wanted):
        return not any(set(wanted)&set(p['units']) for key,p in self.data['posts'].items() if key!=owner)

    def reserve(self,owner,config):
        wanted=units(config);text=body(config);fingerprint=digest(text)
        if owner in self.data['posts']:
            old=self.data['posts'][owner]
            if old['units']!=wanted or old['fingerprint']!=fingerprint: raise ValueError('Под этим именем уже сохранён другой контент.')
            return
        if not self.available(owner,wanted): raise ValueError('Эта тема и арканы уже подготовлены или опубликованы. Нужна следующая часть или другая тема.')
        tokens=set(normal(text).split())
        for p in self.data['posts'].values():
            previous=set(normal(p['body']).split())
            if p['fingerprint']==fingerprint or (min(len(tokens),len(previous))>=15 and len(tokens&previous)/len(tokens|previous)>=.9):
                raise ValueError('Текст повторяет сохранённый пост, даже с другой обложкой.')
        self.data['posts'][owner]={'units':wanted,'fingerprint':fingerprint,'body':text,
          'title':config.get('title') or config.get('topic') or config.get('theme'),
          'theme':config.get('theme'),'position':config.get('position'),'arcana':config.get('part_arcana',[]),
          'tail':config.get('tail_numbers'),'part':config.get('part'),'sources':config.get('research_sources',[]),'status':'reserved',
          'created_at':datetime.now(timezone.utc).isoformat(),'deliveries':{},'formats':[]}
        self.save()

    def format_ready(self,owner,platform):
        record=self.data['posts'][owner]
        if platform not in record['formats']: record['formats'].append(platform)
        if record['status']=='reserved': record['status']='prepared'
        self.save()

    def delivery(self,owner,platform,status,receipt=None):
        if status not in ('draft','sending','accepted','published','needs_review'): raise ValueError('Неизвестный статус отправки.')
        record=self.data['posts'][owner]
        record['deliveries'][platform]={'status':status,'receipt':receipt or {},'updated_at':datetime.now(timezone.utc).isoformat()}
        if status=='published': record['status']='published'
        self.save()

    def context(self):
        return [{'title':r['title'],'units':r['units'],'status':r['status']} for r in list(self.data['posts'].values())[-40:]]

    def import_buffer(self,posts):
        for post in posts:
            target=post['channelService'];post_id=post['id']
            status={'sent':'published','draft':'draft','scheduled':'accepted','sending':'sending','error':'needs_review','needs_approval':'draft'}.get(post['status'])
            if status is None: raise ValueError('Неизвестный статус Buffer.')
            owner=next((key for key,r in self.data['posts'].items() if any(d.get('receipt',{}).get('id')==post_id for d in r['deliveries'].values())),None)
            if owner is None:
                owner='buffer/'+post_id
                if owner not in self.data['posts']:
                    text=post['text']
                    self.data['posts'][owner]={'units':['external:'+digest(text)],'fingerprint':digest(text),'body':text,
                      'title':text[:120],'status':'prepared','source':'buffer','created_at':post.get('sentAt'),
                      'deliveries':{},'formats':[target],'arcana':[]}
            record=self.data['posts'][owner]
            record['deliveries'][target]={'status':status,'receipt':{'id':post_id,'status':post['status'],'url':post.get('externalLink')},'updated_at':datetime.now(timezone.utc).isoformat()}
            if status=='published': record['status']='published'
        self.save()

