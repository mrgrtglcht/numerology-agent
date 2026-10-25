"""Apply the owner's explicit disclosure preference to the existing queued part."""
import copy
import json
from agent import GitHubStore, SafeError
from content_memory import ContentMemory
import postwire


def main():
    postwire.creator()
    store=GitHubStore()
    path='state/postwire/music-replacement-part-02.json'
    state=store.read_state(path)
    receipt=state['schedule_receipt']
    endpoint='/api/schedule/'+receipt['id']
    before=postwire.api(endpoint)['scheduled']
    if before['status']!='queued':raise SafeError('Пост уже не в очереди, изменение остановлено.')
    payload=copy.deepcopy(before['payload']);payload.pop('_actor',None)
    payload.setdefault('options',{}).setdefault('tiktok',{})['brand_organic_toggle']=False
    postwire.api(endpoint,{'payload':payload},method='PATCH')
    after=postwire.api(endpoint)['scheduled'];saved=after['payload']
    if (after['status']!='queued' or after['run_at']!=before['run_at']
        or saved.get('text')!=payload.get('text') or saved.get('media')!=payload.get('media')
        or saved.get('options',{}).get('tiktok')!=payload['options']['tiktok']):
        raise SafeError('Не подтверждено сохранение настроек; повторной публикации не было.')
    for key in ('payload','scheduled_payload'):
        if key in state:state[key].setdefault('options',{}).setdefault('tiktok',{})['brand_organic_toggle']=False
    state['schedule_receipt']['brand_organic_toggle']=False
    store.save_state(path,state)
    memory=ContentMemory(store=store)
    delivery=memory.data['posts'][state['owner']]['deliveries']['tiktok']
    delivery['receipt']['brand_organic_toggle']=False;memory.save()
    proof={'schedule_id':receipt['id'],'brand_organic_toggle':False,
      'auto_add_music':saved['options']['tiktok']['auto_add_music'],
      'privacy_level':saved['options']['tiktok']['privacy_level'],
      'asset_count':len(saved['media']),'run_at':after['run_at'],'status':'queued','new_post_created':False}
    store.save_state('state/postwire/label-preference.json',proof)
    print(json.dumps(proof))


if __name__=='__main__':main()
