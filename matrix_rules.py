"""Exact position domains of the existing personal-matrix formulas, not LLM guesses."""
from datetime import date
from functools import lru_cache

METHOD='axvii-main-centre-22-v1'
ARCANA={1:'маг',2:'верховная жрица',3:'императрица',4:'император',5:'иерофант',
        6:'влюблённые',7:'колесница',8:'справедливость',9:'отшельник',10:'колесо фортуны',
        11:'сила',12:'повешенный',13:'смерть',14:'умеренность',15:'дьявол',16:'башня',
        17:'звезда',18:'луна',19:'солнце',20:'суд',21:'мир',22:'шут'}

def reduce22(n):
    if type(n)!=int or n<1: raise ValueError('Нужно положительное целое число.')
    while n>22: n=sum(map(int,str(n)))
    return n

def points(a,c,e):
    p={'A':a,'C':c,'E':e}; p['G']=reduce22(a+c+e)
    p['I']=reduce22(a+c+e+p['G'])
    for k,x,y in [('B','A','C'),('D','C','E'),('F','E','G'),('H','G','A')]: p[k]=reduce22(p[x]+p[y])
    p['I1']=reduce22(sum(p[k] for k in ('B','D','F','H')))
    for k in 'ABCDEFGH':
        p[k+'2']=reduce22(p[k]+p['I']); p[k+'1']=reduce22(p[k]+p[k+'2'])
    p['F3']=reduce22(p['G2']+p['E2'])
    p['FL']=reduce22(p['G2']+p['F3']); p['FR']=reduce22(p['E2']+p['F3'])
    p['A3']=reduce22(p['A2']+p['I']); p['C3']=reduce22(p['C2']+p['I'])
    p['I2']=reduce22(p['I']+p['I1'])
    return p

@lru_cache(maxsize=1)
def domains():
    # Every reduced day 1..22 is attainable in every month (literal days 1..22).
    # Every reduced year 2..22 has a real witness in 1900..2025. Years 1900..9999
    # cannot reduce to 1. Consequently these 5544 triples cover the entire domain
    # supported by the bot, not a frequency sample or a compatibility matrix.
    years={}
    for year in range(1900,2026):
        years.setdefault(reduce22(sum(map(int,str(year)))),year)
    assert set(years)==set(range(2,23))
    values={}; witnesses={}; tails=set()
    for e,year in years.items():
        for c in range(1,13):
            for a in range(1,23):
                p=points(a,c,e); birth=date(year,c,a).isoformat()
                tails.add((p['G2'],p['G1'],p['G']))
                for key,value in p.items():
                    values.setdefault(key,set()).add(value)
                    witnesses.setdefault(key,{}).setdefault(value,birth)
    return {'method':METHOD,'scope':'personal birth dates 1900..9999; not compatibility',
            'positions':{k:sorted(v) for k,v in values.items()},'witnesses':witnesses,
            'tails':sorted(tails)}

def allowed(position):
    if position is None: return list(range(1,23))
    if position not in domains()['positions']: raise ValueError('Неизвестная позиция матрицы.')
    return list(domains()['positions'][position])

def valid_tail(values): return tuple(values) in domains()['tails']

THEMES={
 'profession':{'title':'твоя профессия\nпо матрице','position':'FR',
   'label':'точка под знаком денег','instruction':'найди точку на денежном канале ближе к правому лучу — под знаком денег. для этой серии смотрим её аркан.',
   'meaning':'профессии и рабочие задачи, которые символически соотносятся с арканом денежного канала; не обещать профессию или доход',
   'source':'https://axvii.ru/blog/denezhnyy-kanal-v-matritse-sudby'},
 'partner':{'title':'какой партнёр\nтебе близок','position':'FL',
   'label':'точка под знаком сердца','instruction':'найди точку на линии отношений ближе к нижнему лучу — под знаком сердца. в этой серии читаем её аркан.',
   'meaning':'качества партнёра и характер взаимодействия, без предсказаний конкретного человека или места встречи',
   'source':'https://axvii.ru/blog/liniya-otnosheniy-v-matritse-sudby'},
 'meeting':{'title':'где ты можешь\nвстретить партнёра','position':'FL',
   'label':'точка под знаком сердца','instruction':'найди точку под знаком сердца на линии отношений. здесь рассматриваем её символическую тему, а не точный адрес будущей встречи.',
   'meaning':'возможные среды общения и совместные занятия по символике аркана; не предсказывать место, дату или гарантированную встречу',
   'source':'https://axvii.ru/blog/liniya-otnosheniy-v-matritse-sudby'},
 'talents':{'title':'твои таланты\nпо матрице','position':'C2',
   'label':'внутренняя точка верхнего луча','instruction':'найди верхний луч и его ближайшую к центру точку. здесь разбираем одну позицию талантов, а не весь верхний блок.',
   'meaning':'символические способности и способы их практиковать; не гарантировать врождённый талант',
   'source':'https://axvii.ru/blog/kak-rasschitat-matritsu-sudby-samomu'},
 'centre':{'title':'твой характер\nпо центру матрицы','position':'I',
   'label':'центр личной матрицы','instruction':'найди большой круг в центре своей личной матрицы. для этой серии нужен именно его аркан.',
   'meaning':'привычный способ действовать и личная опора по центру личной матрицы',
   'source':'https://axvii.ru/blog/kak-rasschitat-matritsu-sudby-samomu'},
 'facts':{'title':'неочевидное\nоб арканах','position':None,
   'label':'все старшие арканы','instruction':'эта серия — о самих старших арканах. искать определённую позицию в матрице не нужно.',
   'meaning':'короткие символические факты об арканах, без привязки к определённой позиции и без выдуманных исторических сведений',
   'source':'https://numerolog.ru/tarot/znacheniya-starshih-arkanov-taro.html'}
}

def series_plan(theme,per_part=4):
    if theme not in THEMES: raise ValueError('Выбери profession, partner, meeting, talents, centre или facts.')
    if type(per_part)!=int or not 1<=per_part<=6: raise ValueError('Нужно от 1 до 6 арканов на часть.')
    profile=THEMES[theme]; values=allowed(profile['position'])
    chunks=[values[i:i+per_part] for i in range(0,len(values),per_part)]
    return {'theme':theme,'method':METHOD,'position':profile['position'],'allowed':values,
            'excluded':[v for v in range(1,23) if v not in values],
            'parts':[{'part':i+1,'arcana':v} for i,v in enumerate(chunks)],
            'total_parts':len(chunks),'per_part':per_part}
