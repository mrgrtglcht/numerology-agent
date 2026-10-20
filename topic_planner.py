"""Stable semantic angles create new topics without renaming already covered content."""
import hashlib
from matrix_rules import THEMES,series_plan
from position_catalog import catalog
from content_memory import units

# Titles vary; position + angle is the durable identity. Rewording cannot bypass memory.
ANGLES={
 'strength':('сильные стороны','какие сильные стороны можно развивать'),
 'shadow':('что может мешать','какие привычные перекосы стоит замечать без запугивания'),
 'practice':('как раскрыть потенциал','конкретные небольшие действия для развития'),
 'communication':('как тебе легче общаться','способы ясно выражать мысли и слушать'),
 'boundaries':('твои личные границы','способы договариваться и обозначать личные границы'),
 'cooperation':('как тебе легче сотрудничать','форматы совместных задач и договорённостей'),
 'learning':('как тебе легче учиться','способы освоения навыков и практики'),
 'creativity':('как проявляется твоё творчество','формы творческого самовыражения'),
 'work_rhythm':('твой рабочий ритм','подходящий стиль рабочих задач, без обещаний дохода'),
 'motivation':('что поддерживает твою мотивацию','условия вовлечённости в занятия'),
 'values':('что для тебя важно','предпочтения и ценности без категоричных предсказаний')}
GROUP_ANGLES={'character':('strength','shadow','practice','communication','boundaries','motivation','values'),
 'talent':('strength','practice','learning','creativity','motivation'),
 'work':('strength','practice','cooperation','work_rhythm','motivation'),
 'love':('communication','boundaries','cooperation','values','practice')}

def register_topics():
    positions=catalog()
    for code,p in positions.items():
        if not p['auto_topic_enabled']:continue
        for angle in GROUP_ANGLES[p['group']]:
            key=f'explore_{code}_{angle}'
            noun={'I':'твой характер','C':'твои таланты','C1':'интеллектуальный талант','C2':'самовыражение','E':'дела и ресурсы','E1':'отношение к работе','E2':'твоя реализация','FR':'работа и профессия','FL':'отношения'}[code]
            THEMES[key]={'title':ANGLES[angle][0]+'\n'+noun,'position':code,'label':p['label'],
              'instruction':p['instruction'],'meaning':p['meaning']+'; '+ANGLES[angle][1],
              'source':p['source'],'semantic_key':f'position:{code}:angle:{angle}',
              'angle':angle,'position_group':p['group'],'single_post_research':True}
    return positions

def choose(memory,batch):
    positions=register_topics();available=[]
    for key,p in THEMES.items():
        plan=series_plan(key)
        remaining=[];used=0
        for part in plan['parts']:
            wanted=units({'type':'arcana_series','theme':key,'position':p['position'],'part_arcana':part['arcana']})
            if memory.available(batch+f'/part-{part["part"]:02}',wanted):remaining.append(part['part'])
            else:used+=1
        if remaining:available.append((key,remaining[0],used,plan))
    if not available:raise ValueError('Проверенные темы исчерпаны. Нужны новые подтверждённые направления.')
    # Finish an existing series before starting another; otherwise vary broad content categories.
    unfinished=[item for item in available if item[2]>0]
    pool=unfinished or available
    recent=[r.get('theme') for r in memory.data['posts'].values() if r.get('theme')][-3:]
    fresh=[item for item in pool if item[0] not in recent]
    pool=fresh or pool
    selected=sorted(pool,key=lambda item:hashlib.sha256((batch+item[0]).encode()).hexdigest())[0]
    key,part,_,plan=selected;profile=THEMES[key]
    return {'theme':key,'part':part,'position':profile['position'],'angle':profile.get('angle'),
      'title':profile['title'],'arcana':plan['parts'][part-1]['arcana'],'total_parts':plan['total_parts'],
      'source':profile['source'],'method':plan['method'],'status':'planned'}

