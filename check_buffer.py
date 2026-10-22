"""Read-only Buffer connection check. Never prints credentials or API bodies."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path(__file__).with_name('.env')


def load_key():
    key = os.environ.get('BUFFER_API_KEY', '').strip()
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding='utf-8-sig').splitlines():
            name, sep, value = line.partition('=')
            if sep and name.strip() == 'BUFFER_API_KEY':
                key = value.strip().strip('\"').strip("'")
    if not key:
        raise RuntimeError('В отдельном файле quantafate-agent/.env пока нет Buffer-ключа.')
    return key


def query_buffer(key, query, variables=None):
    # This helper deliberately accepts queries only; it cannot create posts.
    if not query.lstrip().startswith('query '):
        raise RuntimeError('Проверка допускает только чтение.')
    request = urllib.request.Request(
        'https://api.buffer.com',
        data=json.dumps({'query': query, 'variables': variables or {}}).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        def read():
            with urllib.request.urlopen(request, timeout=30) as response:return json.load(response)
        from read_retry import read_retry
        payload=read_retry(read)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Buffer вернул HTTP {error.code}. Тело ответа скрыто.') from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise RuntimeError('Не удалось получить ответ Buffer. Данные запроса скрыты.') from None
    if payload.get('errors'):
        raise RuntimeError('Buffer отклонил запрос: проверьте права ключа и актуальность схемы. Ответ скрыт.')
    if not isinstance(payload.get('data'), dict):
        raise RuntimeError('Buffer вернул неожиданный ответ. Ответ скрыт.')
    return payload['data']


def main():
    key = load_key()
    account = query_buffer(key, 'query CheckAccess { account { organizations { id name } } }')['account']
    organizations = account['organizations']
    print('Ключ принят. Доступ к Buffer подтверждён.')
    for organization in organizations:
        result = query_buffer(key, '''query CheckChannels($organizationId: OrganizationId!) {
          channels(input: { organizationId: $organizationId }) {
            id name displayName service isQueuePaused
            metadata { ... on PinterestMetadata { boards { name serviceId } } }
          }
        }''', {'organizationId': organization['id']})
        print('Организация:', organization['name'])
        for channel in result['channels']:
            print('Канал:', channel['service'], '|', channel.get('displayName') or channel['name'],
                  '| ID:', channel['id'], '| очередь приостановлена:', channel['isQueuePaused'])
            for board in (channel.get('metadata') or {}).get('boards', []):
                print('  Доска:', board['name'], '| serviceId:', board['serviceId'])
    print('Проверка завершена. Публикации, черновики и расписания не изменялись.')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('Проверка остановлена. Подробности скрыты для защиты ключа.', file=sys.stderr)
        sys.exit(1)
