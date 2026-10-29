"""Telegram has its own publication sequence, independent of TikTok previews."""
from matrix_rules import THEMES,ARCANA,allowed

SERIES=('centre','talents','partner','profession','facts')


def select(memory):
    """Only confirmed Telegram sends advance a series; unfinished sends block it."""
    records=list(memory.data['posts'].items())
    for theme in SERIES:
        profile=THEMES[theme]
        for number in [None]+allowed(profile['position']):
            key=f'telegram-series:{theme}:'+('intro' if number is None else str(number))
            matches=[(owner,p) for owner,p in records if p.get('content',{}).get('editorial_key')==key and p['status']!='rejected']
            published=[p for _,p in matches if p.get('deliveries',{}).get('telegram',{}).get('status')=='published']
            if published:continue
            if any(p.get('deliveries',{}).get('telegram',{}).get('status') in ('sending','needs_review','accepted') for _,p in matches):
                raise ValueError('Предыдущая отправка этой серии не подтверждена. Сначала проверь Telegram.')
            cached=next(((owner,p['content']) for owner,p in matches if p.get('content')),None)
            return {'theme':theme,'position':profile['position'],'title':profile['title'],
              'source':profile['source'],'arcana':[] if number is None else [number],
              'article_kind':'intro' if number is None else 'single_arcana',
              'editorial_key':key,'number':number,'cached_owner':cached[0] if cached else None,
              'cached_content':cached[1] if cached else None}
    raise ValueError('Проверенные серии Telegram завершены. Нужны новые подтверждённые серии.')


def brief(topic):
    if topic['article_kind']=='intro':
        return ('Это вводный пост серии. Объясни позицию в целом: где найти, что она означает в данной методике, '
          'как читать её с учётом других точек. Не разбирай отдельные арканы и не составляй их список. '
          'В конце спокойно сообщи, что следующие посты будут подробно разбирать отдельные арканы этой позиции, без вопросов и рекламы.')
    return ('Это ОДИН подробный разбор '+str(topic['number'])+' аркана именно в позиции '+str(topic['position'])+'. '
      'В заголовке и тексте используй название из нашего справочника: '+str(topic['number'])+' аркан — '+ARCANA[topic['number']]+'. Не заменяй его альтернативным названием из источников. Раскрой его смысл, сильные стороны, возможные сложности, '
      'конкретные жизненные ситуации и полезную мысль, органично вплетённые в текст. Не используй одинаковую последовательность абзацев для всех арканов и не подписывай каждый абзац шаблонной связкой. Не перескакивай на другие арканы, '
      'не делай каталог из четырёх описаний. Не повторяй вводный пост целиком.')

