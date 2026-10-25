"""TikTok photo scheduling with explicit music/public visibility; no send retries.

Primary contract: https://postwire.io/docs/network-options/ and /docs/scheduling/.
Activation requires a real connected-account check, not just an API key.
"""
import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from agent import SafeError, request_json, required

ZONE = ZoneInfo('Europe/Warsaw')
PUBLIC = 'PUBLIC_TO_EVERYONE'
LAUNCH_SLOTS = {'2026-10-26':(18,30), '2026-10-28':(18,30)}


def api(path, payload=None, method=None):
    if not path.startswith('/api/') or '://' in path:
        raise ValueError('Неверный адрес PostWire.')
    return request_json('PostWire', 'https://postwire.io'+path, payload,
                        {'Authorization': 'Bearer '+required('POSTWIRE_API_KEY')},method=method)


def creator():
    brand = os.environ.get('POSTWIRE_BRAND_ID', '').strip()
    result = api('/api/tiktok/creator-info'+('?' + urlencode({'brand_id':brand}) if brand else ''))
    username = str(result.get('creator_username', '')).lstrip('@').lower()
    if result.get('ok') is not True or username != 'quanta.aura':
        raise SafeError('PostWire: нужен подключённый tiktok quanta.aura.')
    if PUBLIC not in result.get('privacy_level_options', []):
        raise SafeError('TikTok не разрешает публичную публикацию через это подключение.')
    if not result.get('brand_id'):
        raise SafeError('PostWire не подтвердил бренд аккаунта.')
    return result


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def next_slot(memory, now=None):
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(ZONE)
    receipts = [p.get('deliveries', {}).get('tiktok', {}).get('receipt', {})
                for p in memory.data['posts'].values()]
    dates = [instant(r['run_at']) for r in receipts if r.get('provider') == 'postwire' and r.get('run_at')]
    # Preserve series order: two owner-requested launch slots, then Fri/Sun.
    after = max([now+timedelta(minutes=10), *dates])
    for day in range(70):
        date = local.date()+timedelta(days=day)
        slot = LAUNCH_SLOTS.get(date.isoformat()) or {4:(22,27), 6:(9,46)}.get(date.weekday())
        if not slot:
            continue
        candidate = datetime(date.year,date.month,date.day,*slot,tzinfo=ZONE).astimezone(timezone.utc)
        month = candidate.astimezone(ZONE).strftime('%Y-%m')
        used = sum(d.astimezone(ZONE).strftime('%Y-%m') == month for d in dates)
        if candidate > after and used < 10:
            return candidate.isoformat()
    raise SafeError('Нет свободного бесплатного слота TikTok.')


def payload(config, urls, owner, memory):
    from cloud_agent import tiktok_caption
    account = creator()
    if not 2 <= len(urls) <= 10 or any(not u.startswith('https://') for u in urls):
        raise ValueError('Нужны 2–10 доступных изображений HTTPS.')
    queue = api('/api/schedule').get('scheduled')
    if not isinstance(queue, list):
        raise SafeError('PostWire не подтвердил состояние очереди.')
    if sum(p.get('status') in ('queued','held','publishing','pending_approval') for p in queue) >= 2:
        raise SafeError('Очередь PostWire заполнена; платный тариф не включается.')
    return {'platforms':['tiktok'], 'brand_id':account['brand_id'],
            'text':tiktok_caption(config), 'media':[{'url':u,'type':'image'} for u in urls],
            'run_at':next_slot(memory), 'label':'quantafate-'+hashlib.sha256(owner.encode()).hexdigest()[:24],
            'options':{'tiktok':{'privacy_level':PUBLIC, 'auto_add_music':True,
                'brand_organic_toggle':False, 'as_draft':False, 'photo_cover_index':0}}}


def enqueue(data):
    result = api('/api/schedule', data)
    row = result.get('scheduled') or {}
    if result.get('ok') is not True or result.get('held') or result.get('held_networks') or row.get('status') != 'queued':
        raise SafeError('PostWire не подтвердил очередь: проверь лимит или запрос согласования. Повтора нет.')
    identity = str(row.get('id', ''))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', identity):
        raise SafeError('PostWire не вернул идентификатор; повтор запрещён.')
    # A queued response is not a published post. Persist its ID before read-back.
    return {'provider':'postwire','id':identity,'status':'queued','run_at':data['run_at'],
            'asset_count':len(data['media']),'auto_add_music':True,'privacy_level':PUBLIC}


def verify(receipt, data):
    row = api('/api/schedule/'+receipt['id']).get('scheduled') or {}
    saved = row.get('payload',row)
    media = saved.get('media')
    options = saved.get('options', {}).get('tiktok', {})
    urls = [m.get('url') if isinstance(m,dict) else m for m in (media or [])]
    if (row.get('status') != 'queued' or saved.get('text') != data['text']
        or urls != [m['url'] for m in data['media']]
        or options.get('auto_add_music') is not True or options.get('privacy_level') != PUBLIC):
        raise SafeError('PostWire не подтвердил все слайды, музыку и публичность. Нужна сверка, повтор запрещён.')
    return receipt


def sync(memory):
    for owner, post in list(memory.data['posts'].items()):
        delivery = post.get('deliveries',{}).get('tiktok',{})
        receipt = delivery.get('receipt',{})
        if receipt.get('provider') != 'postwire' or delivery.get('status') == 'published':
            continue
        if not receipt.get('id'):
            raise SafeError('Неизвестен результат отправки PostWire; повтор запрещён.')
        row = api('/api/schedule/'+receipt['id']).get('scheduled') or {}
        # Only a positive network result proves publication. Unknown schemas stop safely.
        results = row.get('results') or []
        proof = next((r for r in results if isinstance(r,dict) and r.get('platform') == 'tiktok' and r.get('ok') is True),None) if isinstance(results,list) else None
        if proof and str(row.get('status','')).lower() in ('published','publish_complete','completed','sent'):
            memory.delivery(owner,'tiktok','published',{**receipt,'result':proof})
        elif row.get('status') == 'queued' and delivery.get('status') == 'accepted':
            continue
        else:
            raise SafeError('Публикация PostWire ещё не подтверждена; автоматический повтор запрещён.')
