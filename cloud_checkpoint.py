"""Small, durable preparation checkpoints. Sending remains a separate transaction."""
import json
import re
from pathlib import Path

FILES={'oracle-plan.json','oracle-response.json','oracle-generation.json','oracle-model.json','tiktok-format.json','prepared-tiktok.json','editor-plan.json','research.json','series-plan.json','candidates.json','pipeline.json',
 'background-review.json','model-response.json','model-diagnostic.json','raw-model-output.txt','sources.json',
 'telegram-plan.json','telegram-response.json','telegram-generation.json','telegram.json',
 'model-request.json','repair-state.json','repair-response.json','repair-diagnostic.json'}


def pointer(target):
    if target not in ('tiktok','telegram'):raise ValueError('Неизвестная площадка.')
    return 'state/cloud/pending-'+target+'.json'


def snapshot(folder):
    root=Path(folder);files={}
    for path in root.rglob('*'):
        relative=path.relative_to(root).as_posix()
        if path.is_file() and (('/' not in relative and path.name in FILES) or re.fullmatch(r'part-\d{2}/(input|content)\.json',relative)):
            if path.stat().st_size>1_000_000:raise ValueError('Файл контрольной точки слишком большой.')
            files[relative]=path.read_text(encoding='utf-8')
    if sum(len(v) for v in files.values())>2_000_000:raise ValueError('Контрольная точка слишком большая.')
    return files


def restore(state,output):
    name=state.get('folder','')
    if not re.fullmatch(r'cloud-(tiktok|telegram)-\d{4}-\d{2}-\d{2}',name):raise ValueError('Повреждено имя контрольной точки.')
    root=Path(output)/name;root.mkdir(parents=True,exist_ok=True)
    for relative,content in state.get('files',{}).items():
        if relative not in FILES and not re.fullmatch(r'part-\d{2}/(input|content)\.json',relative):raise ValueError('Неизвестный файл контрольной точки.')
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
    return root


def attempts(memory,folder,target):
    return [(key,p['deliveries'][target]) for key,p in memory.data['posts'].items()
      if key.startswith(folder+'/') and target in p.get('deliveries',{})]


def preparation_failed(store,target,folder,day,previous=None,error=None):
    from preparation_errors import diagnostic,temporary
    count=(previous or {}).get('attempts',0)+1
    state={'stage':'preparation_failed' if count<3 or temporary(error) else 'needs_review',
      'folder':Path(folder).name,'day':day,'attempts':count,'files':snapshot(folder)}
    if error:state['diagnostic']=diagnostic(error)
    store.save_state(pointer(target),state)
    return state
