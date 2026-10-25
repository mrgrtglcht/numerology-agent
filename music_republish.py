"""Explicitly authorized one-time music replacements; never erase original history."""
import argparse
import io
import json
import os
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode
from PIL import Image
from agent import GitHubStore, SafeError, required
from cloud_agent import tiktok_caption
from content_memory import ContentMemory
import postwire

ASSET_REF='2f211f3b33bf09e7ff88bed654f3bde9e61d1464'
OWNERS={1:'quantafate-editor-focused/part-01',2:'cloud-tiktok-2026-10-20-preview/part-02'}


def state_path(part):
    if part not in OWNERS: raise ValueError('Разрешены только первые две части.')
    return f'state/postwire/music-replacement-part-{part:02}.json'


def prepare(part, store):
    path=state_path(part)
    old=store.read_state(path)
    if old: return old
    account=postwire.creator()
    memory=store.read_state('state/content-memory.json')
    record=memory['posts'][OWNERS[part]]
    config=record['content']
    if config.get('part')!=part or config.get('theme')!='explore_E1_motivation':
        raise SafeError('Исходная часть не совпадает с согласованной серией.')
    urls=[f'https://raw.githubusercontent.com/mrgrtglcht/quantafate-agent/{ASSET_REF}/media/caption-repair-20261022/part-{part:02}/{i:02}.jpg' for i in range(1,8)]
    for url in urls:
        with urllib.request.urlopen(url,timeout=30) as response: data=response.read(6_000_001)
        if len(data)>6_000_000:raise SafeError('Слайд превышает размер.')
        with Image.open(io.BytesIO(data)) as image:
            if image.format!='JPEG' or image.size!=(1080,1920): raise SafeError('Неверный размер или формат слайда.')
            image.verify()
    payload={'platforms':['tiktok'],'brand_id':account['brand_id'],
      'text':tiktok_caption(config),'media':[{'url':u,'type':'image'} for u in urls],
      'idempotency_key':f'quantafate-music-replacement-part-{part:02}-20261025',
      'options':{'tiktok':{'privacy_level':postwire.PUBLIC,'auto_add_music':True,
        'brand_organic_toggle':False,'as_draft':False,'photo_cover_index':0}}}
    state={'stage':'prepared','part':part,'owner':OWNERS[part],'payload':payload,
      'old_delivery':record['deliveries']['tiktok'],'asset_count':7,'prepared_at':datetime.now(timezone.utc).isoformat()}
    store.save_state(path,state)
    return state


def summarize(result):
    allowed=('platform','ok','id','post_id','publish_id','schedule_id','url','status','code','privacy_level','auto_add_music','delivered_to','as_draft','notice')
    return {'posted':result.get('posted'),'id':result.get('id'),'status':result.get('status'),
      'held':result.get('held'),'results':[{k:v for k,v in r.items() if k in allowed}
      for r in result.get('results',[]) if isinstance(r,dict)]}


def publish(part,store):
    if os.environ.get('ALLOW_MUSIC_REPLACEMENT')!='true' or os.environ.get('OLD_POSTS_REMOVED')!='true':
        raise SafeError('Нужно подтверждение отправки и удаления старых постов.')
    path=state_path(part);state=store.read_state(path)
    if not state or state.get('stage')!='prepared':
        raise SafeError('Эта замена уже отправлялась или ещё не подготовлена. Повтор запрещён.')
    if part==2:
        previous=store.read_state(state_path(1)) or {}
        if previous.get('stage')!='published':raise SafeError('Сначала должна выйти первая часть.')
    account=postwire.creator()
    if account['brand_id']!=state['payload']['brand_id']:raise SafeError('Подключение изменилось.')
    state.update(stage='sending',attempted_at=datetime.now(timezone.utc).isoformat())
    store.save_state(path,state)
    try:result=postwire.api('/api/post',state['payload'])
    except Exception:
        state['stage']='needs_review';store.save_state(path,state);raise
    state['receipt']=summarize(result)
    proof=next((r for r in state['receipt']['results'] if r.get('platform')=='tiktok' and r.get('ok') is True),None)
    state['stage']='accepted' if proof and result.get('posted')==1 and not result.get('held') else 'needs_review'
    store.save_state(path,state)
    print(json.dumps({'stage':state['stage'],'part':part,'receipt':state['receipt']},ensure_ascii=False))
    if state['stage']=='needs_review':raise SafeError('PostWire не подтвердил отправку; повтор запрещён.')
    return state


def status(part,store):
    path=state_path(part);state=store.read_state(path)
    if not state or state.get('stage') not in ('accepted','published'):raise SafeError('Нет подтверждённого идентификатора отправки.')
    receipt=state['receipt'];result=next(r for r in receipt['results'] if r.get('platform')=='tiktok' and r.get('ok') is True)
    identity=result.get('id') or result.get('publish_id') or result.get('post_id')
    if not identity:raise SafeError('В ответе нет идентификатора TikTok; нужна сверка.')
    outcome=postwire.api('/api/post/status?'+urlencode({'platform':'tiktok','id':identity}))
    state['status_check']={k:v for k,v in outcome.items() if k in ('platform','id','status','url','privacy_level','auto_add_music','publish_id','post_id')}
    if str(outcome.get('status','')).lower() in ('published','publish_complete','sent','completed'):
        state['stage']='published'
    store.save_state(path,state)
    print(json.dumps({'stage':state['stage'],'part':part,'status_check':state['status_check']},ensure_ascii=False))
    return state


def record_delivery(state,store,receipt,status):
    memory=ContentMemory(store=store);record=memory.data['posts'][state['owner']]
    old=record.get('deliveries',{}).get('tiktok')
    if old and old.get('receipt',{}).get('provider','buffer')=='buffer':
        record.setdefault('delivery_history',[]).append({'platform':'tiktok','reason':'owner_deleted_silent_post',
          'delivery':old})
    memory.delivery(state['owner'],'tiktok',status,receipt)


def schedule_second(store):
    if os.environ.get('ALLOW_MUSIC_REPLACEMENT')!='true' or os.environ.get('OLD_POSTS_REMOVED')!='true':
        raise SafeError('Нужно подтверждение замены.')
    first=status(1,store)
    if first['stage']!='published':raise SafeError('Первая часть ещё обрабатывается.')
    proof=first['receipt']['results'][0]
    record_delivery(first,store,{'provider':'postwire','mode':'immediate','id':proof['id'],
      'run_at':first['attempted_at'],'asset_count':7,'auto_add_music':True,
      'privacy_level':postwire.PUBLIC,'url':first['status_check'].get('url')},'published')
    state=prepare(2,store);path=state_path(2)
    if state['stage']!='prepared':raise SafeError('Вторая часть уже отправлялась. Повтора нет.')
    memory=ContentMemory(store=store)
    urls=[m['url'] for m in state['payload']['media']]
    config=memory.data['posts'][state['owner']]['content']
    payload=postwire.payload(config,urls,state['owner'],memory)
    state.update(stage='sending',scheduled_payload=payload)
    store.save_state(path,state)
    receipt={'provider':'postwire','run_at':payload['run_at']}
    try:
        receipt=postwire.enqueue(payload)
        state['schedule_receipt']=receipt;store.save_state(path,state)
        # Store the actual public schedule row for a schema-safe readback audit.
        observed=postwire.api('/api/schedule/'+receipt['id']).get('scheduled') or {}
        saved=observed.get('payload',observed)
        state['schedule_readback']={'id':observed.get('id'),'status':observed.get('status'),
          'run_at':observed.get('run_at'),'payload':{k:v for k,v in saved.items() if k in ('text','media','options','platforms','brand_id')}}
        store.save_state(path,state)
        postwire.verify(receipt,payload)
    except Exception:
        state['stage']='needs_review';store.save_state(path,state)
        record_delivery(state,store,receipt,'needs_review');raise
    state['stage']='scheduled';store.save_state(path,state)
    record_delivery(state,store,receipt,'accepted')
    print(json.dumps({'stage':'scheduled','part':2,'receipt':receipt},ensure_ascii=False))


def reconcile_second(store):
    state=store.read_state(state_path(2)) or {}
    receipt=state.get('schedule_receipt')
    if not receipt or state.get('stage') not in ('needs_review','scheduled'):
        raise SafeError('Нет сохранённого идентификатора второй части.')
    postwire.verify(receipt,state['scheduled_payload'])
    state['stage']='scheduled'
    state.pop('schedule_readback',None)
    store.save_state(state_path(2),state)
    record_delivery(state,store,receipt,'accepted')
    print(json.dumps({'stage':'scheduled','part':2,'receipt':receipt,'resend':False},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','publish','status','schedule-second','reconcile-second']);parser.add_argument('--part',type=int,choices=[1,2],default=1)
    args=parser.parse_args();store=GitHubStore()
    if args.mode=='prepare':
        state=prepare(args.part,store)
        print(json.dumps({'stage':state['stage'],'part':args.part,'asset_count':state['asset_count'],'caption':state['payload']['text'],'music':True,'public':True},ensure_ascii=False))
    elif args.mode=='publish':publish(args.part,store)
    elif args.mode=='schedule-second':schedule_second(store)
    elif args.mode=='reconcile-second':reconcile_second(store)
    else:status(args.part,store)


if __name__=='__main__':
    try:main()
    except (SafeError,ValueError) as error:print(str(error));raise SystemExit(1)
