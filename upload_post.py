"""Upload-Post API: allowlisted diagnostics and Pinterest carousel delivery."""
import json
import os
from urllib.parse import urlencode
from agent import SafeError,request_json,required

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

if __name__=='__main__':
    try:print(json.dumps(connection(),ensure_ascii=False))
    except SafeError as e:print(str(e));raise SystemExit(1)
