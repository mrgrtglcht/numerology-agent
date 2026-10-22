"""Read-only Telegram check; does not read updates, change webhooks or send posts."""
import sys
from agent import SafeError, load_env, required, request_json

READ_METHODS = frozenset({'getMe', 'getChat', 'getChatMember'})


def read_telegram(method, payload=None):
    if method not in READ_METHODS:
        raise SafeError('Проверка Telegram допускает только чтение.')
    result = request_json('Telegram',
        'https://api.telegram.org/bot' + required('TELEGRAM_BOT_TOKEN') + '/' + method,
        payload or {},read_only=True)
    if not result.get('ok'):
        raise SafeError('Telegram отклонил проверку. Проверьте токен и доступ бота к каналу.')
    return result['result']


def check():
    channel = required('TELEGRAM_CHANNEL_ID')
    bot = read_telegram('getMe')
    chat = read_telegram('getChat', {'chat_id': channel})
    if chat.get('type') != 'channel':
        raise SafeError('Указан не Telegram-канал. Проверьте TELEGRAM_CHANNEL_ID.')
    if channel.startswith('@') and chat.get('username', '').lower() != channel[1:].lower():
        raise SafeError('Telegram вернул другой канал. Проверка остановлена.')
    membership = read_telegram('getChatMember', {'chat_id': chat['id'], 'user_id': bot['id']})
    if membership.get('status') != 'administrator' or membership.get('can_post_messages') is not True:
        raise SafeError('Добавьте этого бота администратором канала с правом публикации сообщений.')
    return {'bot': '@' + bot.get('username', ''), 'channel': channel, 'can_post_messages': True}


def main():
    load_env()
    result = check()
    print('Бот:', result['bot'])
    print('Канал:', result['channel'])
    print('Право публикации подтверждено. Сообщения не отправлялись.')


if __name__ == '__main__':
    try:
        main()
    except SafeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('Проверка остановлена. Подробности скрыты для защиты токена.', file=sys.stderr)
        sys.exit(1)
