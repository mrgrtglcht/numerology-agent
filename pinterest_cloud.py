"""Standalone Pinterest pins: verified copy, 2:3 rendering and durable delivery."""
import argparse
import copy
import hashlib
import io
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw
from agent import ROOT,GitHubStore,SafeError,buffer,load_env,required
from content_memory import ContentMemory,body,digest,units

PATH='state/pinterest-memory.json'
ZONE=ZoneInfo('Europe/Warsaw')


def select(memory,ledger):
    seen=ledger.get('pins',{})
    for owner,record in memory.data['posts'].items():
        config=record.get('content',{})
        if record.get('status')=='rejected' or config.get('type')!='arcana_series' or config.get('demo_content'):continue
        if record.get('deliveries',{}).get('tiktok',{}).get('status')!='published':continue
        if digest(body(config))!=record['fingerprint'] or units(config)!=record['units']:raise ValueError('Исходный текст повреждён.')
        for slide in config.get('slides',[]):
            if slide.get('layout')!='arcana':continue
            number=slide['arcana_number']
            unit=next(u for u in record['units'] if u.endswith(':'+str(number)))
            key=hashlib.sha256(unit.encode()).hexdigest()[:24]
            if key not in seen:return {'key':key,'unit':unit,'owner':owner,'number':number,'config':config,'slide':slide}
    return None


def check_channel():
    target=os.environ.get('BUFFER_PINTEREST_CHANNEL_ID') or '6ad66303778b240e2f5c7a0c'
    orgs=buffer('query PinOrgs {account{organizations{id}}}')['account']['organizations']
    for org in orgs:
        channels=buffer('query PinChannels($id:OrganizationId!){channels(input:{organizationId:$id}){id name service isDisconnected}}',{'id':org['id']})['channels']
        for channel in channels:
            if channel['id']==target and channel['service']=='pinterest':
                if channel['isDisconnected']:raise SafeError('Pinterest отключён от Buffer.')
                return target,org['id']
    raise SafeError('Подключённый Pinterest не найден.')


def sync(ledger,org,channel):
    if not ledger['pins']:return
    from sync_content_memory import QUERY
    posts=[];cursor=None
    for page in range(20):
        rows=buffer(QUERY,{'input':{'organizationId':org,'filter':{'channelIds':[channel],
          'status':['draft','error','needs_approval','scheduled','sending','sent']}},'after':cursor})['posts']
        posts.extend(e['node'] for e in rows['edges'])
        if not rows['pageInfo']['hasNextPage']:break
        cursor=rows['pageInfo']['endCursor']
    else:raise SafeError('Неполная история Pinterest.')
    indexed={p['id']:p for p in posts}
    for pin in ledger['pins'].values():
        identity=pin.get('receipt',{}).get('id')
        if pin['stage']=='published' or not identity:continue
        post=indexed.get(identity)
        if post and post['status']=='sent':pin.update(stage='published',url=post.get('externalLink'),sent_at=post.get('sentAt'))
        elif post and post['status'] in ('error','needs_approval'):pin['stage']='needs_review'


def render_pin(item,background_path,output):
    from carousel import background,text,fitted_paragraphs
    from tarot_assets import prepare
    from matrix_rules import ARCANA
    im=background(background_path,(1000,1500),[.5,.5]);draw=ImageDraw.Draw(im)
    text(draw,'quantafate',70,75,24,width=860)
    heading=item['config']['slides'][0]['title'].split('\n')[0]
    y=text(draw,heading,70,155,48,True,width=860)
    if y>330:raise ValueError('Заголовок слишком длинный для пина.')
    number=item['number']
    y=text(draw,f'{number} аркан',390,350,27,width=540)+25
    y=text(draw,ARCANA[number],390,y,44,True,width=540)+55
    art=Image.open(prepare([number])[number]).convert('RGBA')
    art.thumbnail((245,470),Image.Resampling.LANCZOS);im.paste(art,(70,430),art)
    fitted_paragraphs(draw,item['slide']['paragraphs'],390,max(y,540),540,1195,size=36,min_size=32,gap=28)
    location=next(s for s in item['config']['slides'] if s['layout']=='location')
    instruction=' '.join(b['text'] for b in location['blocks'])
    end=text(draw,instruction,70,1245,26,width=860)
    if end>1385:raise ValueError('Инструкция не помещается в пин.')
    text(draw,'больше разборов — в тгк @quantafate',70,1410,24,width=860)
    im.save(output,'JPEG',quality=94,optimize=True)


def prepare(item,store,folder):
    from backgrounds import search_candidates,thumbnails,fresh_thumbnails,download_selection
    from background_history import BackgroundHistory
    folder.mkdir(parents=True,exist_ok=True)
    history=BackgroundHistory(store=store);batch='pinterest-'+item['key']
    candidates=search_candidates(limit=8,seed=batch,no_attribution=True,exclude=lambda s:not history.available(s,batch))
    candidates=fresh_thumbnails(thumbnails(candidates,folder/'candidates'),history,batch)
    if not candidates:raise SafeError('Нет нового подходящего фона Pinterest.')
    chosen=candidates[0]
    source=download_selection([chosen],[{'id':chosen['id'],'focus':[.5,.5],'reason':'new public-domain Pinterest background'}],folder/'backgrounds')[0]
    history.reserve(batch,{1:source})
    out=folder/'pin.jpg';render_pin(item,folder/'backgrounds'/source['file'],out)
    url=store.put('media/'+batch+'/pin.jpg',out.read_bytes())
    source['modifications']='cropped to 2:3, darkened, overlaid with text and public-domain card'
    store.save_state('media/'+batch+'/sources.json',{'background':source,'tarot_manifest':'assets/tarot/public-domain-manifest.json'})
    from matrix_rules import ARCANA
    title=item['config']['slides'][0]['title'].split('\n')[0]+' · '+str(item['number'])+' аркан'
    caption=title+'\n\n'+'\n\n'.join(item['slide']['paragraphs'])+'\n\nбольше разборов — @quantafate'
    if len(title)>100 or len(caption)>500:raise ValueError('Описание Pinterest слишком длинное.')
    board=json.loads((ROOT/'pinterest-board.json').read_text(encoding='utf-8'))
    return {'stage':'prepared','owner':item['owner'],'unit':item['unit'],'number':item['number'],
      'image_url':url,'title':title,'caption':caption,'board':board['service_id'],'prepared_at':datetime.now(timezone.utc).isoformat()}


def send(pin,channel):
    data={'channelId':channel,'text':pin['caption'],'assets':[{'image':{'url':pin['image_url']}}],
      'schedulingType':'automatic','mode':'shareNow','saveToDraft':False,'needsApproval':False,
      'metadata':{'pinterest':{'boardServiceId':pin['board'],'title':pin['title'],'url':'https://t.me/quantafate'}}}
    action=buffer('''mutation PublishPin($input:CreatePostInput!){createPost(input:$input){
      __typename ... on PostActionSuccess {post{id status assets{id}}}
    }}''',{'input':data})['createPost']
    if action.get('__typename')!='PostActionSuccess':raise SafeError('Buffer не подтвердил Pinterest. Повтор остановлен: '+str(action.get('__typename')))
    result=action['post']
    if len(result.get('assets',[]))!=1:raise SafeError('Buffer не подтвердил изображение Pinterest.')
    return {'id':result['id'],'status':result['status'],'asset_count':1}


def run(mode,store,now=None):
    now=now or datetime.now(timezone.utc).astimezone(ZONE);day=now.astimezone(ZONE).date().isoformat()
    ledger=store.read_state(PATH) or {'version':1,'pins':{},'days':{}}
    if ledger.get('version')!=1:raise SafeError('Повреждён журнал Pinterest.')
    channel,org=check_channel();sync(ledger,org,channel);store.save_state(PATH,ledger)
    if mode=='status':print(json.dumps(ledger,ensure_ascii=False));return
    if mode=='scheduled' and (now.astimezone(ZONE).weekday() not in (1,5) or (now.astimezone(ZONE).hour,now.astimezone(ZONE).minute)<(18,30)):return
    if mode in ('publish','scheduled') and day in ledger['days']:print('Pinterest: отправка за день уже начиналась.');return
    if any(p['stage'] in ('sending','needs_review','accepted') for p in ledger['pins'].values()):
        raise SafeError('Pinterest: предыдущая отправка ещё не подтверждена; повтор запрещён.')
    ready=next(((k,p) for k,p in ledger['pins'].items() if p['stage']=='prepared'),None)
    if not ready:
        item=select(ContentMemory(store=store),ledger)
        if not item:print('Pinterest: нет нового опубликованного материала для адаптации.');return
        pin=prepare(item,store,ROOT/'output'/('pinterest-'+item['key']))
        key=item['key'];ledger['pins'][key]=pin;store.save_state(PATH,ledger)
    else:key,pin=ready
    if mode=='preview':print(json.dumps({'stage':'prepared','image_url':pin['image_url'],'title':pin['title']},ensure_ascii=False));return
    ledger['days'][day]=key;pin['stage']='sending';store.save_state(PATH,ledger)
    try:receipt=send(pin,channel)
    except Exception:
        pin['stage']='needs_review';store.save_state(PATH,ledger);raise
    pin.update(stage='published' if receipt['status']=='sent' else 'accepted',receipt=receipt)
    store.save_state(PATH,ledger)
    print(json.dumps({'stage':pin['stage'],'receipt':receipt,'title':pin['title']},ensure_ascii=False))


if __name__=='__main__':
    load_env();os.environ['PUBLICATION_ASSETS']='true'
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['preview','publish','scheduled','status']);args=parser.parse_args()
    try:run(args.mode,GitHubStore())
    except (SafeError,ValueError) as error:print(str(error));raise SystemExit(1)
