"""Upload-Post API: allowlisted diagnostics and Pinterest carousel delivery."""
import json
import os
import urllib.request
import urllib.error
import uuid
from urllib.parse import urlencode
from agent import SafeError,request_json,required
from media_urls import trusted_media_url

BASE='https://api.upload-post.com'

def get(path):
    return request_json('Upload-Post',BASE+path,headers={'Authorization':'Apikey '+required('UPLOAD_POST_API_KEY')})

def connection():
    me=get('/api/uploadposts/me')
    result=get('/api/uploadposts/users')
    profiles=[p for p in result.get('profiles',[]) if isinstance(p.get('social_accounts',{}).get('pinterest'),dict)
              and not p['social_accounts']['pinterest'].get('reauth_required')]
    selected=os.environ.get('UPLOAD_POST_PROFILE')
    if selected:profiles=[p for p in profiles if p['username']==selected]
    if len(profiles)!=1:raise SafeError('Нужен один подключённый Pinterest либо UPLOAD_POST_PROFILE.')
    profile=profiles[0]['username']
    boards=get('/api/uploadposts/pinterest/boards?'+urlencode({'profile':profile}))
    wanted=os.environ.get('PINTEREST_BOARD_ID','1141592274236006099')
    matches=[b for b in boards.get('boards',[]) if str(b['id'])==wanted]
    if len(matches)!=1:raise SafeError('Доска quantaura не найдена в подключённом Pinterest.')
    return {'plan':me.get('plan'),'profile':profile,'board':wanted,'board_name':matches[0]['name'],
            'account':boards.get('pinterest_account_used')}

def publish(post,conn,key):
    urls=post['image_urls']
    if not 2<=len(urls)<=5:raise SafeError('Карусель Pinterest требует 2–5 изображений.')
    link='https://t.me/quantafate'
    fields=[('user',conn['profile']),('platform[]','pinterest'),('title',' '),
      ('pinterest_title',post['title']),('pinterest_description',post['caption'] or ' '),
      ('pinterest_board_id',conn['board']),('pinterest_link',link),('async_upload','true'),
      ('request_id',key),('external_id',key)]
    for url in urls:
        if not trusted_media_url(url):raise SafeError('Непроверенный адрес изображения.')
        fields.extend([('photos[]',url),('pinterest_carousel_titles[]',post['title']),
          ('pinterest_carousel_descriptions[]',post['caption'] or ' '),('pinterest_carousel_links[]',link)])
    boundary='quantafate'+uuid.uuid4().hex
    data=b''.join((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode() for name,value in fields)
    data+=f'--{boundary}--\r\n'.encode()
    req=urllib.request.Request(BASE+'/api/upload_photos',data=data,method='POST',headers={
      'Authorization':'Apikey '+required('UPLOAD_POST_API_KEY'),'Content-Type':'multipart/form-data; boundary='+boundary,
      'Idempotency-Key':key,'User-Agent':'QuantaFate/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=90) as response:return json.load(response)
    except urllib.error.HTTPError as e:
        raise SafeError('Upload-Post: HTTP '+str(e.code)+'. Повтор остановлен; требуется проверка статуса.') from None
    except (OSError,ValueError):raise SafeError('Upload-Post: результат отправки неизвестен; повтор остановлен.') from None

def status(key):
    return get('/api/uploadposts/status?'+urlencode({'request_id':key}))

def safe_summary(value):
    """Expose response shape and delivery facts, never credentials or free-form errors."""
    allowed={'status','success','platform','url','post_url','post_id','platform_post_id','pin_id','error_code','skipped','completed','total'}
    if isinstance(value,list):return [safe_summary(v) for v in value]
    if isinstance(value,dict):
        return {k:(safe_summary(v) if isinstance(v,(dict,list)) else v if k in allowed else '<hidden>') for k,v in value.items()}
    return '<hidden>'

if __name__=='__main__':
    try:print(json.dumps(connection(),ensure_ascii=False))
    except SafeError as e:print(str(e));raise SystemExit(1)
