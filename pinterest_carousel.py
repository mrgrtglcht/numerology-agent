"""Native 1000x1500 composition: maximum five images, no stretched TikTok slides."""
import json
import zipfile
from pathlib import Path
from PIL import Image,ImageDraw
from carousel import background,text,position_diagram,matrix_diagram,fitted_paragraphs

SIZE=(1000,1500)
from brand import BOT_CTA as BOT

def plan(config):
    slides=config['slides'];arcana=[s for s in slides if s['layout']=='arcana']
    if arcana:
        if len(arcana)>4: raise ValueError('Для pinterest нужны части максимум по четыре аркана.')
        result=[{'layout':'pin_overview','background':slides[0]['background'],'focus':slides[0]['focus']}]+[dict(s) for s in arcana]
        result[-1]['bot_footer']=True
        return result
    bodies=[s for s in slides if s['layout'] not in ('cover','location','bot')]
    result=[{'layout':'pin_overview','background':slides[0]['background'],'focus':slides[0]['focus']}]
    # Keep all copy, merging the last two short body slides when needed.
    for s in bodies[:3]: result.append(dict(s))
    if len(bodies)>3:
        rest=bodies[3:];merged=dict(rest[0]);merged['blocks']=[]
        for s in rest:
            merged['blocks'].append({'heading':s['title'],'text':'\n'.join(b['text'] for b in s['blocks'])})
        merged['title']='что важно помнить';result.append(merged)
    if not 2<=len(result)<=5: raise ValueError('Для pinterest нужны 2–5 карточек.')
    return result

def render(config,output,backgrounds,cards=None):
    folder=Path(output);out=folder/'slides';out.mkdir(parents=True,exist_ok=True)
    sources=Path(backgrounds).resolve();pages=plan(config)
    cards=cards or {}
    if not cards and any(s['layout']=='arcana' for s in pages):
        from tarot_assets import prepare
        cards=prepare([s['arcana_number'] for s in pages if s['layout']=='arcana'])
    rendered=[]
    for index,s in enumerate(pages,1):
        path=(sources/s['background']).resolve()
        if not path.is_relative_to(sources): raise ValueError('Неверный путь фона pinterest.')
        im=background(path,SIZE,s['focus']);d=ImageDraw.Draw(im)
        text(d,'quantafate',70,85,24,width=860)
        if s['layout']=='pin_overview':
            cover=config['slides'][0]
            title=cover['title'].replace('\n',' ')
            if cover.get('number'): title+=' '+cover['number']
            y=text(d,title,70,190,60,True,width=860)+35
            if cover.get('subtitle'): y=text(d,cover['subtitle'],70,y,29,width=860)+30
            location=next((v for v in config['slides'] if v['layout']=='location'),None)
            if location:
                instruction=' '.join(b['text'] for b in location['blocks'])
                y=text(d,instruction,70,y,32,width=860)
                cy=max(910,y+250)
                if cy+260>1330: raise ValueError('Схема не помещается в pinterest.')
                if config.get('example_points'): position_diagram(d,500,cy,config['position'],config['example_points'],radius=225)
                else: matrix_diagram(d,500,cy,radius=225,tail=config.get('tail_numbers',[15,5,8]))
            else:
                intro=next((v for v in config['slides'] if v['layout']=='body'),None)
                if intro:
                    for b in intro['blocks']: y=text(d,b['text'],70,y+30,36,width=860)
        elif s['layout']=='arcana':
            from matrix_rules import ARCANA
            n=s['arcana_number'];text(d,f'{n} аркан',390,225,27,width=540)
            y=text(d,ARCANA[n],390,285,46,True,width=540)+65
            art=Image.open(cards[n]).convert('RGBA').resize((260,498),Image.Resampling.LANCZOS)
            im.paste(art,(70,355),art);d=ImageDraw.Draw(im)
            y=max(y,465)
            limit=1145 if s.get('bot_footer') else 1340
            y=fitted_paragraphs(d,s['paragraphs'],390,y,540,limit,size=36,min_size=32,gap=32)
            if y>limit: raise ValueError('Текст аркана не помещается в pinterest.')
            if s.get('bot_footer'):
                d.line((70,1190,930,1190),fill='#B3B8AC',width=1)
                text(d,BOT,70,1230,32,True,width=860)
        else:
            y=text(d,s['title'],70,200,53,True,width=860)+48
            for b in s.get('blocks',[]):
                if b.get('heading'): y=text(d,b['heading'],70,y,35,True,width=860)+20
                y=text(d,b['text'],70,y,35,width=860)+34
            if y>1340: raise ValueError('Текст не помещается в pinterest.')
        text(d,'quantafate',70,1410,23,width=650)
        text(d,f'{index:02} / {len(pages):02}',800,1410,23,width=150)
        im.save(out/f'{index:02}.png');rendered.append(im)
    sheet=Image.new('RGB',(300*len(pages),450),'#151812')
    for i,im in enumerate(rendered):sheet.paste(im.resize((300,450),Image.Resampling.LANCZOS),(300*i,0))
    sheet.save(folder/'preview.jpg',quality=94)
    manifest={'platform':'pinterest','size':list(SIZE),'slides':pages,'caption':config.get('caption',''),
      'content_identity':{'theme':config.get('theme'),'part':config.get('part'),'arcana':config.get('part_arcana')},
      'delivery':'image assets only; carousel publishing requires a supported Pinterest business creation flow'}
    (folder/'content.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(folder/'carousel.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.glob('*.png')):z.write(path,'slides/'+path.name)
        for name in ('content.json','preview.jpg'):z.write(folder/name,name)
    return [out/f'{i:02}.png' for i in range(1,len(pages)+1)]

