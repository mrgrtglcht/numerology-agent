"""Editorial checks for repetitive Telegram prose; ordinary topic terms remain allowed."""
import re
from collections import Counter

STOCK=(
    'продолжаем разговор','продолжаем знакомство','продолжаем разбор',
    'переходим к детальному разбору','в этой статье мы рассмотрим',
    'в этом посте мы разберем','давайте разберемся',
    'спокойное практическое наблюдение показывает',
    'важно отметить что','стоит отметить что','подводя итог',
)
STOP=set('и в во на с со к ко у о об от до по из за для а но или не ни это как что то же бы ты тебе тебя твой свои себя его ее мы они он она их при без через'.split())

def words(text):
    return re.findall(r'[а-яa-z0-9]+',text.lower().replace('ё','е'))

def spans(tokens,n):
    return [tuple(tokens[i:i+n]) for i in range(max(0,len(tokens)-n+1))]

def check(text,recent=()):
    from matrix_rules import ARCANA
    terms=set('аркан аркана арканов аркане матрица матрицы матрице судьба судьбы центр центра центре энергия энергии'.split())
    for name in ARCANA.values():terms.update(words(name))
    tokens=words(text);normal=' '.join(tokens)
    for phrase in STOCK:
        if phrase in normal:
            raise ValueError('Редактура Telegram: убери шаблонный оборот «'+phrase+'» и начни с конкретной мысли.')
    if tokens and tokens[0]=='продолжаем':
        raise ValueError('Редактура Telegram: не начинай статью со слова «продолжаем».')
    sentences=[words(s) for s in re.split(r'[.!?\n]+',text)]
    counts=Counter(tuple(s) for s in sentences if len(s)>=8)
    if any(count>1 for count in counts.values()):
        raise ValueError('Редактура Telegram: одно предложение повторяется внутри статьи.')
    repeated=Counter(spans(tokens,4))
    for phrase,count in repeated.items():
        if count>=3 and sum(word not in STOP and word not in terms for word in phrase)>=2:
            raise ValueError('Редактура Telegram: оборот «'+' '.join(phrase)+'» повторяется слишком часто; перепиши фразы естественно.')
    current=set(spans(tokens,12))
    for old in recent:
        previous=words(old)
        if len(tokens)>=6 and tokens[:6]==previous[:6]:
            raise ValueError('Редактура Telegram: начало повторяет недавний пост; начни сразу с другой конкретной мысли.')
        if current.intersection(spans(previous,12)):
            raise ValueError('Редактура Telegram: длинная фраза скопирована из недавней статьи; объясни мысль заново.')
    return text

def history(memory,key=None):
    return [p['content']['caption'] for p in memory.data['posts'].values()
      if p.get('theme')=='telegram_article' and p.get('status')!='rejected'
      and p.get('content',{}).get('editorial_key')!=key
      and p.get('deliveries',{}).get('telegram',{}).get('status')=='published'][-8:]

def context(recent):
    return [{'opening':text[:260],'ending':text[-220:]} for text in recent[-6:]]
