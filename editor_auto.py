"""Research -> unused topic/part -> grounded previews, without publication."""
import json
from pathlib import Path
from content_memory import ContentMemory
from topic_planner import choose,register_topics
from web_research import research
from matrix_rules import THEMES

def plan(output,memory=None):
    folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    path=folder/'editor-plan.json';memory=memory or ContentMemory();register_topics()
    topic=json.loads(path.read_text(encoding='utf-8')) if path.exists() else choose(memory,folder.name)
    if topic['theme'] not in THEMES:raise ValueError('Тема отсутствует в проверенном справочнике.')
    from matrix_rules import series_plan
    expected=series_plan(topic['theme'])
    if topic['position']!=expected['position'] or not 1<=topic['part']<=expected['total_parts'] or topic['arcana']!=expected['parts'][topic['part']-1]['arcana']:
        raise ValueError('Сохранённый план не соответствует проверенной позиции.')
    topic.update(title=THEMES[topic['theme']]['title'],source=THEMES[topic['theme']]['source'])
    path.write_text(json.dumps(topic,ensure_ascii=False,indent=2),encoding='utf-8')
    from position_catalog import catalog
    (folder/'position-catalog.json').write_text(json.dumps(catalog(),ensure_ascii=False,indent=2),encoding='utf-8')
    dossier=research(topic,folder)
    profile=THEMES[topic['theme']]
    profile['single_post_research']=True
    profile['research_context']=dossier['sources']
    return topic,dossier

def run(output,plan_only=False):
    topic,dossier=plan(output)
    if not plan_only:
        from arcana_series import run as series
        series(topic['theme'],output,part=topic['part'])
    print('Выбрана новая тема: '+topic['title'].replace('\n',' ')+f'; часть {topic["part"]}. Источников: {len(dossier["sources"])}. Публикаций не было.')
    return topic

