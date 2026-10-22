"""Reuse unpublished series previews, preserving part order and grounded text."""
import copy
import json
from pathlib import Path
from content_memory import body,digest,units


def delivered(record):
    return record.get('deliveries',{}).get('tiktok',{}).get('status') in ('accepted','published')


def check_order(config,memory):
    if config.get('type')!='arcana_series':return
    previous={r.get('part') for r in memory.data['posts'].values()
      if r.get('theme')==config['theme'] and delivered(r)}
    if not set(range(1,config['part']))<=previous:
        raise ValueError('Предыдущие части серии ещё не поставлены в очередь.')


def select(memory):
    ready=[]
    active={r.get('theme') for r in memory.data['posts'].values() if delivered(r)}
    unfinished=set()
    for theme in active:
        records=[r for r in memory.data['posts'].values() if r.get('theme')==theme]
        total=max((r.get('content',{}).get('total_parts',0) for r in records),default=0)
        done={r.get('part') for r in records if delivered(r)}
        if total and not set(range(1,total+1))<=done:unfinished.add(theme)
    for order,(owner,r) in enumerate(memory.data['posts'].items()):
        config=r.get('content',{})
        if r.get('status')=='rejected' or r.get('deliveries',{}).get('tiktok'):continue
        if config.get('type')!='arcana_series' or config.get('demo_content') or 'tiktok' not in r.get('formats',[]):continue
        if unfinished and config['theme'] not in unfinished:continue
        try:check_order(config,memory)
        except ValueError:continue
        ready.append((0 if config['theme'] in active else 1,order,owner))
    return min(ready)[2] if ready else None


def prepare(owner,memory,folder):
    from backgrounds import search_candidates,thumbnails,fresh_thumbnails,download_selection,NO_ATTRIBUTION
    from background_history import BackgroundHistory
    from carousel import render
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    config=copy.deepcopy(memory.data['posts'][owner]['content'])
    record=memory.data['posts'][owner]
    if digest(body(config))!=record['fingerprint'] or units(config)!=record['units']:raise ValueError('Сохранённый текст повреждён.')
    check_order(config,memory)
    plan=folder/'prepared-tiktok.json'
    if plan.exists() and json.loads(plan.read_text(encoding='utf-8'))['owner']!=owner:raise ValueError('Контрольная точка относится к другой части.')
    plan.write_text(json.dumps({'owner':owner},ensure_ascii=False),encoding='utf-8')
    history=BackgroundHistory();path=folder/'candidates.json'
    if path.exists():candidates=json.loads(path.read_text(encoding='utf-8'))
    else:
        candidates=search_candidates(limit=10,seed=folder.name,no_attribution=True,exclude=lambda s:not history.available(s,folder.name))
        path.write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding='utf-8')
    candidates=[c for c in candidates if c.get('license','').lower() in NO_ATTRIBUTION]
    candidates=fresh_thumbnails(thumbnails(candidates,folder/'candidates'),history,folder.name)
    source_path=folder/'sources.json'
    if source_path.exists():
        saved=json.loads(source_path.read_text(encoding='utf-8'));chosen=next(c for c in candidates if c['id']==saved[0]['id'])
    else:chosen=candidates[0]
    sources=download_selection([chosen],[{'id':chosen['id'],'focus':[.5,.5],'reason':'public-domain background for saved unpublished part'}],folder/'backgrounds')
    source_path.write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    for slide in config['slides']:slide.update(background=sources[0]['file'],focus=[.5,.5])
    from cloud_agent import tiktok_caption
    config['caption']=tiktok_caption(config);config.pop('attribution_required',None)
    part=folder/f'part-{config["part"]:02}';part.mkdir(exist_ok=True)
    path=part/'input.json';path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    history.reserve(folder.name,{config['part']:sources[0]})
    render(path,part,folder/'backgrounds')
    record['content']=config;memory.save()
    return part
