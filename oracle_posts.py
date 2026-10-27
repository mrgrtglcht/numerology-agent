"""Five visual Forest of Love slides, generated questions and durable preparation."""
import copy
import hashlib
import json
import re
from pathlib import Path
from PIL import Image,ImageDraw
from agent import ROOT,SafeError
from content_memory import normal

DECK=ROOT/'assets/oracle/forest-love'
CAPTION='больше в тгк @quantafate'

def deck():
    manifest=json.loads((DECK/'manifest.json').read_text(encoding='utf-8'))
    for c in manifest['cards']+[manifest['back']]:
        if hashlib.sha256((DECK/c['file']).read_bytes()).hexdigest()!=c['sha256']:
            raise SafeError('Повреждён файл колоды оракула.')
    if len(manifest['cards'])!=50:raise SafeError('Неполная колода оракула.')
    return manifest

def ready_owner(memory):
    return next((o for o,p in memory.data['posts'].items() if p.get('content',{}).get('type')=='oracle_pick'
      and p.get('status')!='rejected' and not p.get('deliveries',{}).get('tiktok')),None)

def validate(data,catalog,count,memory=None):
    title=data.get('question','');key=data.get('question_id','');options=data.get('options',[])
    if not isinstance(title,str) or not 12<=len(title)<=100 or title!=title.lower() or any(x in title for x in ('@','http','\n')):
        raise ValueError('Нужен короткий вопрос строчными буквами.')
    if not re.fullmatch(r'[a-z][a-z0-9_]{3,70}',key):raise ValueError('Неверный смысловой ключ вопроса.')
    if count not in (3,4,5,6) or len(options)!=count or len({o.get('card_id') for o in options})!=count:
        raise ValueError('Нужно от трёх до шести разных карт.')
    known={c['id'] for c in catalog}
    for option in options:
        if option.get('card_id') not in known:raise ValueError('Выбрана неизвестная карта.')
        reason=option.get('visual_reason','')
        if not isinstance(reason,str) or not 25<=len(reason)<=450:raise ValueError('Не объяснена связь карты с вопросом.')
    if memory:
        for p in memory.data['posts'].values():
            old=p.get('content',{})
            if p.get('status')!='rejected' and old.get('type')=='oracle_pick':
                if old.get('question_id')==key or normal(old.get('title',''))==normal(title):raise ValueError('Этот вопрос уже использован.')
    return data

def schema(count,catalog):
    return {'type':'object','properties':{'question':{'type':'string'},'question_id':{'type':'string'},
      'options':{'type':'array','minItems':count,'maxItems':count,'items':{'type':'object','properties':{
      'card_id':{'type':'string','enum':[c['id'] for c in catalog]},'visual_reason':{'type':'string'}},
      'required':['card_id','visual_reason']}}},'required':['question','question_id','options']}

def generate(memory,folder,catalog,count):
    from carousel_auto import generate_visual
    from editor_recovery import validated
    from carousel import face
    response_path=folder/'oracle-response.json'
    if response_path.exists():return validate(json.loads(response_path.read_text(encoding='utf-8')),catalog,count,memory)
    sheet=Image.new('RGB',(1400,7*240),'#151812');d=ImageDraw.Draw(sheet)
    for i,c in enumerate(catalog):
        art=Image.open(DECK/c['file']).convert('RGBA');art.thumbnail((145,195))
        x=(i%8)*175;y=(i//8)*240;sheet.paste(art,(x,y),art)
        d.text((x,y+198),c['id'],font=face(17),fill='white')
    sheet_path=folder/'oracle-catalog.jpg';sheet.save(sheet_path,quality=90)
    history=[{'question':p.get('content',{}).get('title'),'key':p.get('content',{}).get('question_id')}
      for p in memory.data['posts'].values() if p.get('content',{}).get('type')=='oracle_pick' and p.get('status')!='rejected']
    prompt=('Ты редактор quantafate. Придумай новый короткий вопрос для визуального оракула про отношения с парнем. '
      'Примеры направлений: что он чувствует к тебе; ты его глазами; что будет дальше между вами; его скрытые намерения. '
      'Не ограничивайся примерами. Чередуй направления, не повторяй смысл прошлых вопросов даже с другими словами. '
      'question_id — стабильный английский смысловой ключ, не случайное число. question — живой русский текст строчными. '
      'Выбери ровно '+str(count)+' разных карт из приложенной колоды лес любви, подходящих именно под новый вопрос. '
      'Выборы должны давать разные возможные символические версии ответа: интерес, близость, пауза, сомнение, действие и т.п. '
      'Смотри изображения и русские названия, не выбирай произвольно. visual_reason — внутреннее объяснение конкретной сцены '
      'и её связи с вопросом, не утверждение о достоверном знании чужих мыслей. Никаких абзацев трактовки на слайды. '
      'Каталог: '+json.dumps([{k:c[k] for k in ('id','name')} for c in catalog],ensure_ascii=False)+
      '. Использованные вопросы: '+json.dumps(history,ensure_ascii=False)+'. Верни JSON по схеме.')
    pictures=[{'id':'forest-love-catalog','local_thumbnail':str(sheet_path)}]
    intent=folder/'oracle-generation.json'
    if intent.exists():raise SafeError('Запрос оракула уже начинался; нужна сверка сохранённого ответа.')
    intent.write_text('{"stage":"started"}',encoding='utf-8')
    response=generate_visual(prompt,pictures,max_tokens=3500,diagnostic_path=folder/'oracle-model.json',response_schema=schema(count,catalog))
    def repair(reason,previous):
        return generate_visual(prompt+' Исправь: '+reason+'. Предыдущий ответ: '+json.dumps(previous,ensure_ascii=False),
          pictures,max_tokens=3500,diagnostic_path=folder/'repair-diagnostic.json',response_schema=schema(count,catalog))
    response=validated(response,lambda d:validate(d,catalog,count,memory),folder,repair)
    response_path.write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
    return response

def prepare_background(owner,folder,history):
    from backgrounds import search_candidates,thumbnails,fresh_thumbnails,download_selection
    saved=folder/'sources.json';path=folder/'candidates.json'
    if path.exists():candidates=json.loads(path.read_text(encoding='utf-8'))
    else:
        candidates=search_candidates(limit=10,seed=owner,no_attribution=True,exclude=lambda s:not history.available(s,owner))
        path.write_text(json.dumps(candidates,ensure_ascii=False),encoding='utf-8')
    candidates=fresh_thumbnails(thumbnails(candidates,folder/'candidates'),history,owner)
    candidates=[c for c in candidates if re.search(r'abbey|abtei|ruin|forest|landscape|landschaft|cathedral|dom |kloster|garden|castle|church',c['title'],re.I)]
    if not candidates:raise SafeError('Не найден новый фон оракула.')
    review=folder/'oracle-background-review.json'
    if saved.exists():selected=json.loads(saved.read_text(encoding='utf-8'))[0]['id']
    elif review.exists():selected=json.loads(review.read_text(encoding='utf-8'))['id']
    else:
        from carousel_auto import generate_visual
        result=generate_visual('Выбери один эстетичный атмосферный фон для оракула об отношениях: лес, сад, пейзаж или готическая архитектура. '
          'Нужна цельная красивая сцена, подходящая для квадратного кадрирования и белого текста. Не выбирай предметные музейные фото, '
          'посуду, портреты, скульптуры и страницы текста. Если подходящих нет, верни id=none. Верни JSON с id и reason.',candidates,
          max_tokens=500,diagnostic_path=folder/'oracle-background-model.json',response_schema={'type':'object','properties':{
          'id':{'type':'string','enum':['none']+[c['id'] for c in candidates]},'reason':{'type':'string'}},'required':['id','reason']})
        selected=result['id'];review.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    chosen=next((c for c in candidates if c['id']==selected),None)
    if not chosen:raise SafeError('Модель не нашла подходящий атмосферный фон.')
    return download_selection([chosen],[{'id':chosen['id'],'focus':[.5,.5],'reason':'fresh atmospheric background for relationship oracle'}],folder/'backgrounds')

def prepare(owner,memory,folder):
    from tiktok_formats import choice_count
    from background_history import BackgroundHistory
    from oracle_layout import render
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    manifest=deck();catalog=manifest['cards']
    config=copy.deepcopy(memory.data['posts'].get(owner,{}).get('content'))
    if not config:
        plan_path=folder/'oracle-plan.json'
        if plan_path.exists():plan=json.loads(plan_path.read_text(encoding='utf-8'))
        else:
            plan={'count':choice_count(memory)};plan_path.write_text(json.dumps(plan),encoding='utf-8')
        response=generate(memory,folder,catalog,plan['count'])
        config={'type':'oracle_pick','theme':'oracle_pick','deck':'лес любви','question_id':response['question_id'],
          'title':response['question'],'topic':response['question'],'count':plan['count'],'options':response['options'],
          'caption':CAPTION,'size':[1080,1920],'include_tarot_cards':False,'include_cta':False,
          'slides':[{'layout':v} for v in ('oracle_cover','oracle_instruction','oracle_backs','oracle_note','oracle_faces')]}
    history=BackgroundHistory(store=memory.store)
    source=config.get('oracle_background')
    if source:
        import urllib.request
        path=folder/'backgrounds'/source['file'];path.parent.mkdir(parents=True,exist_ok=True)
        url=source['public_url']
        if not url.startswith('https://raw.githubusercontent.com/mrgrtglcht/quantafate-agent/'):raise SafeError('Неверный адрес фона.')
        with urllib.request.urlopen(url,timeout=45) as r:path.write_bytes(r.read())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:raise SafeError('Повреждён фон.')
        sources=[source]
    else:
        sources=prepare_background(owner,folder,history)
        if memory.store:
            safe=hashlib.sha256(owner.encode()).hexdigest()[:24]
            sources[0]['public_url']=memory.store.put('media/oracle-'+safe+'/background.jpg',(folder/'backgrounds'/sources[0]['file']).read_bytes())
        config['oracle_background']=sources[0]
    (folder/'sources.json').write_text(json.dumps(sources,ensure_ascii=False),encoding='utf-8')
    history.reserve(owner,{1:sources[0]})
    part=folder/'part-01';part.mkdir(exist_ok=True)
    render(config,part,folder/'backgrounds'/sources[0]['file'],DECK,manifest,seed=owner)
    (part/'content.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    memory.reserve(owner,config);memory.format_ready(owner,'tiktok')
    return part

