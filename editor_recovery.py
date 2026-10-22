"""Formatting normalization and one bounded correction of a received model answer."""
import json
import os
from pathlib import Path


def normalize(data):
    if not isinstance(data,dict):return data
    data=json.loads(json.dumps(data,ensure_ascii=False))
    for key in ('title','text','caption'):
        if isinstance(data.get(key),str):data[key]=data[key].replace('\\n','\n').strip().lower()
    for entry in data.get('entries',[]) if isinstance(data.get('entries'),list) else []:
        if isinstance(entry,dict) and isinstance(entry.get('paragraphs'),list):
            entry['paragraphs']=[p.strip().lower() if isinstance(p,str) else p for p in entry['paragraphs']]
    return data


def validated(raw,validate,folder,repair,allow_repair=True):
    """Never repeat an unknown request; save intent before the one allowed correction."""
    folder=Path(folder);answer=folder/'repair-response.json';state=folder/'repair-state.json'
    if answer.exists():return validate(normalize(json.loads(answer.read_text(encoding='utf-8'))))
    try:return validate(normalize(raw))
    except ValueError as error:
        if not allow_repair or os.environ.get('AUTO_EDITOR_REPAIR')!='true':raise
        if state.exists():raise ValueError('Попытка редакторского исправления уже записана; новый запрос не отправлен.') from error
        state.write_text(json.dumps({'requests':1,'stage':'request_started','reason':str(error)},ensure_ascii=False),encoding='utf-8')
        result=repair(str(error),normalize(raw))
        answer.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        state.write_text(json.dumps({'requests':1,'stage':'response_received'}),encoding='utf-8')
        return validate(normalize(result))


def series_schema(plan,candidates):
    return {'type':'object','required':['selected','caption','entries'],'properties':{
      'selected':{'type':'array','maxItems':plan.get('background_count',plan['total_parts']),
        'items':{'type':'object','required':['id','focus','reason'],'properties':{
          'id':{'type':'string','enum':[c['id'] for c in candidates]},
          'focus':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'number','minimum':0,'maximum':1}},
          'reason':{'type':'string','maxLength':400}}}},
      'caption':{'type':'string','maxLength':300},
      'entries':{'type':'array','minItems':len(plan['allowed']),'maxItems':len(plan['allowed']),
        'items':{'type':'object','required':['number','paragraphs','source_ids'],'properties':{
          'number':{'type':'integer','enum':plan['allowed']},
          'paragraphs':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'string','maxLength':140}},
          'source_ids':{'type':'array','items':{'type':'string'}}}}}}}


def article_schema(topic,sources,candidates):
    number={'type':'null'} if topic['number'] is None else {'type':'integer','enum':[topic['number']]}
    image={'anyOf':[{'type':'null'},{'type':'string','enum':[c['id'] for c in candidates]}]} if candidates else {'type':'null'}
    return {'type':'object','required':['title','text','arcana_number','source_ids','image_id'],'properties':{
      'title':{'type':'string','maxLength':120},
      'text':{'type':'string','minLength':1400 if topic['number'] is None else 1600,'maxLength':3200},
      'arcana_number':number,'image_id':image,
      'source_ids':{'type':'array','items':{'type':'string','enum':[s['id'] for s in sources]}}}}
