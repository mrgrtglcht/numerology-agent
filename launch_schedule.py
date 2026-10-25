"""Move part two and schedule existing part three for the owner's launch dates."""
import json
import urllib.request
import io
from PIL import Image
from agent import GitHubStore,SafeError
from content_memory import ContentMemory
from cloud_agent import tiktok_caption
from music_republish import ASSET_REF
import postwire


def main():
    postwire.creator();store=GitHubStore()
    part2path='state/postwire/music-replacement-part-02.json';state=store.read_state(part2path)
    receipt=state['schedule_receipt'];endpoint='/api/schedule/'+receipt['id']
    before=postwire.api(endpoint)['scheduled']
    if before['status']!='queued':raise SafeError('Вторая часть уже не в очереди.')
    when='2026-10-26T17:30:00+00:00'
    if postwire.instant(before['run_at'])!=postwire.instant(when):postwire.api(endpoint,{'run_at':when},method='PATCH')
    after=postwire.api(endpoint)['scheduled']
    if postwire.instant(after['run_at'])!=postwire.instant(when) or before['payload']!=after['payload']:
        raise SafeError('Перенос второй части не подтверждён.')
    receipt['run_at']=when;state['scheduled_payload']['run_at']=when
    store.save_state(part2path,state)
    memory=ContentMemory(store=store)
    memory.delivery(state['owner'],'tiktok','accepted',receipt)
    print(json.dumps({'part':2,'run_at':when,'status':'queued','resend':False}))
    owner='cloud-tiktok-2026-10-22/part-03';path='state/postwire/launch-part-03.json'
    saved=store.read_state(path)
    if saved:
        if saved['stage']=='scheduled':print('part 3 already scheduled');return
        raise SafeError('Третья часть уже отправлялась; нужна сверка без повтора.')
    config=memory.data['posts'][owner]['content']
    if config.get('part')!=3 or memory.data['posts'][owner].get('deliveries',{}).get('tiktok'):
        raise SafeError('Третья часть не доступна для новой отправки.')
    urls=[f'https://raw.githubusercontent.com/mrgrtglcht/quantafate-agent/{ASSET_REF}/media/caption-repair-20261022/part-03/{i:02}.jpg' for i in range(1,8)]
    for url in urls:
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read(6_000_001)
        if len(data)>6_000_000:raise SafeError('Слишком большой слайд.')
        with Image.open(io.BytesIO(data)) as image:
            if image.format!='JPEG' or image.size!=(1080,1920):raise SafeError('Неверный слайд.')
            image.verify()
    payload=postwire.payload(config,urls,owner,memory)
    if postwire.instant(payload['run_at'])!=postwire.instant('2026-10-28T17:30:00+00:00'):
        raise SafeError('Не подтверждён слот среды.')
    saved={'stage':'sending','owner':owner,'payload':payload}
    store.save_state(path,saved)
    expected={'provider':'postwire','run_at':payload['run_at'],'expected_asset_count':7}
    memory.delivery(owner,'tiktok','sending',expected)
    receipt=expected
    try:
        receipt=postwire.enqueue(payload)
        saved['receipt']=receipt;store.save_state(path,saved)
        postwire.verify(receipt,payload)
    except Exception:
        saved['stage']='needs_review';store.save_state(path,saved)
        memory.delivery(owner,'tiktok','needs_review',receipt);raise
    memory.delivery(owner,'tiktok','accepted',receipt)
    saved['stage']='scheduled';store.save_state(path,saved)
    print(json.dumps({'part':3,'receipt':receipt}))


if __name__=='__main__':main()
