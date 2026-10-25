"""Cloud Pinterest carousels through Upload-Post, with durable no-repeat delivery."""
import argparse
import copy
import hashlib
import json
import os
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from agent import ROOT,GitHubStore,SafeError,load_env
from content_memory import ContentMemory,body,digest,units
import upload_post

PATH='state/pinterest-carousel-memory.json'
ZONE=ZoneInfo('Europe/Warsaw')

def select(memory,ledger):
    from topic_planner import register_topics
    register_topics()
    for owner,record in memory.data['posts'].items():
        config=record.get('content',{})
        if record.get('status')=='rejected' or config.get('type')!='arcana_series' or config.get('demo_content'):continue
        if record.get('deliveries',{}).get('tiktok',{}).get('status')!='published':continue
        if digest(body(config))!=record['fingerprint'] or units(config)!=record['units']:raise SafeError('Исходный текст не прошёл проверку истории.')
        key='quantafate-pin-'+hashlib.sha256('|'.join(record['units']).encode()).hexdigest()[:24]
        if key not in ledger['posts']:return key,owner,copy.deepcopy(config)
    return None

def prepare(key,owner,config,store):
    from backgrounds import search_candidates,thumbnails,fresh_thumbnails,download_selection
    from background_history import BackgroundHistory
    from pinterest_carousel import render
    folder=ROOT/'output'/key;folder.mkdir(parents=True,exist_ok=True)
    history=BackgroundHistory(store=store)
    saved=store.read_state('media/'+key+'/background.json')
    if saved:
        from agent import request_json
        import urllib.request
        path=folder/'backgrounds'/saved['file'];path.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(saved['download_url'],timeout=45) as r:path.write_bytes(r.read())
        source=saved
    else:
        candidates=search_candidates(limit=8,seed=key,no_attribution=True,exclude=lambda s:not history.available(s,key))
        candidates=fresh_thumbnails(thumbnails(candidates,folder/'candidates'),history,key)
        if not candidates:raise SafeError('Новый фон для Pinterest не найден.')
        chosen=candidates[0]
        source=download_selection([chosen],[{'id':chosen['id'],'focus':[.5,.5],'reason':'fresh public-domain carousel background'}],folder/'backgrounds')[0]
        source['download_url']=store.put('media/'+key+'/background.jpg',(folder/'backgrounds'/source['file']).read_bytes())
        store.save_state('media/'+key+'/background.json',source)
    history.reserve(key,{1:source})
    for slide in config['slides']:slide.update(background=source['file'],focus=[.5,.5])
    files=render(config,folder,folder/'backgrounds')
    urls=[store.put('media/'+key+'/'+f'{i:02}.png',path.read_bytes()) for i,path in enumerate(files,1)]
    preview=store.put('media/'+key+'/preview.jpg',(folder/'preview.jpg').read_bytes())
    title=config['slides'][0]['title'].split('\n')[0]+f' · часть {config["part"]}/{config["total_parts"]}'
    caption='арканы '+', '.join(map(str,config['part_arcana']))+' в матрице судьбы.\n\nбольше разборов — в тгк @quantafate'
    if len(title)>100 or len(caption)>500:raise SafeError('Слишком длинное описание Pinterest.')
    return {'stage':'prepared','owner':owner,'title':title,'caption':caption,'image_urls':urls,'preview_url':preview,
      'units':units(config),'prepared_at':datetime.now(timezone.utc).isoformat()}

def result_state(result):
    rows=result.get('results',{})
    pin=next((p for p in rows if p.get('platform')=='pinterest'),{}) if isinstance(rows,list) else rows.get('pinterest',{})
    url=pin.get('url') or pin.get('post_url')
    if pin.get('success') is True and not pin.get('skipped') and url and url.startswith('https://') and 'pinterest.' in url:
        return 'published',{'url':url,'post_id':pin.get('post_id')}
    if pin.get('success') is False or result.get('success') is False or result.get('status')=='failed':return 'needs_review',{}
    return 'accepted',{}

def sync(ledger,store):
    for key,post in ledger['posts'].items():
        if post['stage'] not in ('sending','accepted','needs_review'):continue
        try:result=upload_post.status(key)
        except SafeError:continue
        stage,receipt=result_state(result)
        if stage=='published':post.update(stage=stage,receipt=receipt)
        elif stage=='needs_review':post['stage']=stage
    store.save_state(PATH,ledger)

def run(mode,store,now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(ZONE);day=now.date().isoformat()
    ledger=store.read_state(PATH) or {'version':1,'posts':{},'days':{}}
    if ledger.get('version')!=1:raise SafeError('Неизвестная версия журнала Pinterest.')
    conn=upload_post.connection();sync(ledger,store)
    if mode=='status':print(json.dumps(ledger,ensure_ascii=False));return
    if mode=='scheduled' and (now.weekday() not in (1,5) or (now.hour,now.minute)<(18,30)):return
    if mode in ('publish','scheduled') and day in ledger['days']:print('Pinterest: отправка за день уже начиналась.');return
    if any(p['stage'] in ('sending','accepted','needs_review') for p in ledger['posts'].values()):raise SafeError('Предыдущая карусель ещё не подтверждена; повтор запрещён.')
    if sum(d.startswith(day[:7]) for d in ledger['days'])>=10:print('Pinterest: достигнут предел 10 отправок за месяц.');return
    ready=next(((k,p) for k,p in ledger['posts'].items() if p['stage']=='prepared'),None)
    if ready:key,post=ready
    else:
        item=select(ContentMemory(store=store),ledger)
        if not item:print('Pinterest: нет новых опубликованных материалов.');return
        key,owner,config=item;post=prepare(key,owner,config,store);ledger['posts'][key]=post;store.save_state(PATH,ledger)
    if mode=='preview':print(json.dumps(post,ensure_ascii=False));return
    post['stage']='sending';ledger['days'][day]=key;store.save_state(PATH,ledger)
    try:
        result=upload_post.publish(post,conn,key)
        stage,receipt=result_state(result);post.update(stage=stage,receipt=receipt)
    except Exception:
        post['stage']='needs_review';store.save_state(PATH,ledger);raise
    store.save_state(PATH,ledger)
    print(json.dumps({'stage':post['stage'],'receipt':post['receipt'],'title':post['title']},ensure_ascii=False))

if __name__=='__main__':
    load_env();os.environ['PUBLICATION_ASSETS']='true'
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['preview','publish','scheduled','status']);args=parser.parse_args()
    try:run(args.mode,GitHubStore())
    except (SafeError,ValueError) as e:print(str(e));raise SystemExit(1)
