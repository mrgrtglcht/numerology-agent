"""One approved queued-spread image correction; never creates a new publication."""
import copy,json
from agent import ROOT,GitHubStore,SafeError
from content_memory import ContentMemory
from background_history import BackgroundHistory
from oracle_posts import prepare_background,DECK,deck
from oracle_layout import render
from cloud_agent import jpeg
import postwire

OWNER='cloud-tiktok-2026-10-27/oracle'
IDENTITY='7ba07f35-1efe-4517-b221-ebfb46f7d886'
PATH='state/oracle-background-update.json'

def main():
    store=GitHubStore();memory=ContentMemory(store=store)
    row=postwire.api('/api/schedule/'+IDENTITY)['scheduled']
    assert row['status']=='queued' and len(row['payload']['media'])==5
    assert postwire.instant(row['run_at'])==postwire.instant('2026-10-30T21:27:00Z')
    saved=store.read_state(PATH)
    if saved and saved.get('stage')=='complete':print('Oracle background already verified.');return
    if not saved:
        config=copy.deepcopy(memory.data['posts'][OWNER]['content'])
        folder=ROOT/'output/oracle-background-update';folder.mkdir(parents=True,exist_ok=True)
        history=BackgroundHistory(store=store)
        sources=store.read_state('state/oracle-background-source.json')
        if sources:
            import urllib.request
            dest=folder/'backgrounds'/sources[0]['file'];dest.parent.mkdir(parents=True,exist_ok=True)
            with urllib.request.urlopen(sources[0]['public_url'],timeout=45) as response:dest.write_bytes(response.read())
        else:
            sources=prepare_background(OWNER+'-background-v3',folder,history)
            history.reserve(OWNER+'-background-v3',{1:sources[0]})
            sources[0]['public_url']=store.put('media/oracle-first-background-v2/background.jpg',(folder/'backgrounds'/sources[0]['file']).read_bytes())
            store.save_state('state/oracle-background-source.json',sources)
        config['oracle_background']=sources[0];config['visual_background_version']=2
        render(config,folder,folder/'backgrounds'/sources[0]['file'],DECK,deck(),seed=OWNER)
        payload=copy.deepcopy(row['payload']);payload.pop('_actor',None)
        for i in (0,1,3):payload['media'][i]['url']=store.put('media/oracle-first-background-v2/'+f'{i+1:02}.jpg',jpeg(folder/'slides'/f'{i+1:02}.png'))
        saved={'stage':'prepared','payload':payload,'config':config,'run_at':row['run_at']}
        store.save_state(PATH,saved)
    payload=saved['payload']
    postwire.api('/api/schedule/'+IDENTITY,{'payload':payload},method='PATCH')
    after=postwire.api('/api/schedule/'+IDENTITY)['scheduled']
    assert after['status']=='queued' and postwire.instant(after['run_at'])==postwire.instant(saved['run_at'])
    assert {k:v for k,v in after['payload'].items() if k!='_actor'}==payload
    memory.data['posts'][OWNER]['content']=saved['config'];memory.save()
    saved['stage']='complete';store.save_state(PATH,saved)
    print(json.dumps({'status':'verified','run_at':after['run_at'],'asset_count':5,'resend':False}))

if __name__=='__main__':main()

