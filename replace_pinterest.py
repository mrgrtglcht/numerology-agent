"""One explicitly approved replacement; never generate or resend another post."""
import json
import time
from agent import GitHubStore,SafeError,request_json,required
from pinterest_upload_cloud import PATH,sync,result_state
import upload_post

OLD='quantafate-pin-e30922480e6e37bb2786eab9'
NEW=OLD+'-v3'
OLD_ID='1141592205583291454'

def run(store):
    conn=upload_post.connection()
    ledger=store.read_state(PATH)
    old=ledger['posts'][OLD];post=ledger['posts'][NEW]
    if old.get('receipt',{}).get('post_id')!=OLD_ID or post.get('replaces')!=OLD or post.get('design_version')!=3:
        raise SafeError('Замена не соответствует согласованному пину.')
    if post['stage']=='prepared':
        post['stage']='sending';post['replacement_approved']=True;store.save_state(PATH,ledger)
        try:
            response=upload_post.publish(post,conn,NEW)
            stage,receipt=result_state(response);post.update(stage=stage,receipt=receipt)
        except Exception:
            post['stage']='needs_review';store.save_state(PATH,ledger);raise
        store.save_state(PATH,ledger)
    for attempt in range(5):
        sync(ledger,store)
        if post['stage'] in ('published','needs_review'):break
        if attempt<4:time.sleep(10)
    if post['stage']=='needs_review':raise SafeError('Сервис сообщил об ошибке новой карусели; старый пин сохранён.')
    if post['stage']!='published':
        print('Pinterest: сервис ещё обрабатывает карусель. Старый пин сохранён; повторной отправки не будет.')
        return
    if not old.get('removed'):
        if old.get('removal_started'):raise SafeError('Удаление уже начиналось; сначала нужна проверка результата.')
        old['removal_started']=True;store.save_state(PATH,ledger)
        result=request_json('Upload-Post',upload_post.BASE+'/api/uploadposts/posts/unpublish',
          {'platform':'pinterest','user':conn['profile'],'post_id':OLD_ID},
          {'Authorization':'Apikey '+required('UPLOAD_POST_API_KEY')})
        if result.get('success') is not True:raise SafeError('Сервис не подтвердил удаление старого пина.')
        old['removed']=True;old['stage']='replaced';old['replacement']=NEW;store.save_state(PATH,ledger)
    print(json.dumps({'stage':post['stage'],'new_pin':post['receipt']['url'],'old_removed':old['removed']},ensure_ascii=False))

if __name__=='__main__':
    try:run(GitHubStore())
    except SafeError as e:print(str(e));raise SystemExit(1)
