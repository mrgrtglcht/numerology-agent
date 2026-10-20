"""Durable, shared background reservations for carousel posts."""
import json
import os
from pathlib import Path

PATH='state/background-history.json'
ROOT=Path(__file__).resolve().parent

def identities(source):
    return {key+':'+str(source[key]) for key in ('page','url','original_sha1','sha256') if source.get(key)}

def visually_same(a,b):
    return bool(a and b) and (int(a,16)^int(b,16)).bit_count()<=6

def duplicate_visual(source,record):
    a=source.get('visual_hashes') or [source.get('visual_hash')]
    b=record.get('visual_hashes') or [record.get('visual_hash')]
    return any(visually_same(x,y) for x in a for y in b)

class BackgroundHistory:
    def __init__(self,path=None,store=None):
        self.path=Path(path) if path else ROOT/PATH
        self.store=store
        if store is None and path is None and os.environ.get('GITHUB_ACTIONS')=='true':
            from agent import GitHubStore
            self.store=GitHubStore()
        data=self.store.read_state(PATH) if self.store else (json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else None)
        self.data=data if data is not None else {'version':1,'posts':{}}
        if self.data.get('version')!=1 or not isinstance(self.data.get('posts'),dict):
            raise ValueError('Не удалось прочитать историю фонов; повторы не разрешены.')

    def available(self,source,batch):
        keys=identities(source)
        return not any(keys & set(record['identities']) and record['batch']!=batch for record in self.data['posts'].values())

    def reserve(self,batch,sources):
        # One atomic history update for all parts; retrying the same post is idempotent.
        posts=dict(self.data['posts'])
        for number,source in sources.items():
            key=f'{batch}/part-{number:02}'
            ids=identities(source)
            if not ids: raise ValueError('Источник фона не указан.')
            if key in posts:
                if not ids & set(posts[key]['identities']): raise ValueError('Фон уже закреплён за этой каруселью.')
                continue
            if any(ids & set(record['identities']) or duplicate_visual(source,record) for record in posts.values()):
                raise ValueError('Этот фон уже использован в другой карусели. Нужен новый.')
            posts[key]={'batch':batch,'part':number,'identities':sorted(ids),'page':source.get('page'),'title':source.get('title'),'visual_hash':source.get('visual_hash'),'visual_hashes':source.get('visual_hashes',[])}
        self.data={'version':1,'posts':posts}
        if self.store: self.store.save_state(PATH,self.data)
        else:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.path)

