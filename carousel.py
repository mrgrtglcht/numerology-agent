"""Pillow carousel: proportional cover crop, focal point, dimming, measured text."""
import json
import hashlib
import math
import urllib.request
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets'
FONT=ROOT/'assets/fonts/Manrope.ttf'
WHITE='#FFFFFF'
_font_checked=False


def ensure_font():
    global _font_checked
    if _font_checked: return
    manifest=json.loads((ASSETS/'fonts/font-source.json').read_text(encoding='utf-8'))
    if not FONT.exists():
        request=urllib.request.Request(manifest['url'],headers={'User-Agent':'QuantaFate/1.0'})
        with urllib.request.urlopen(request,timeout=40) as response: data=response.read(2*1024*1024)
        if hashlib.sha256(data).hexdigest()!=manifest['sha256']: raise ValueError('Контрольная сумма шрифта не совпала.')
        FONT.parent.mkdir(parents=True,exist_ok=True); FONT.write_bytes(data)
    if hashlib.sha256(FONT.read_bytes()).hexdigest()!=manifest['sha256']: raise ValueError('Повреждён файл Manrope.')
    _font_checked=True

def face(size,bold=False):
    ensure_font()
    f=ImageFont.truetype(str(FONT),size)
    f.set_variation_by_axes([700 if bold else 500])
    return f

def lines(draw,text,font,width):
    result=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            if draw.textlength(word,font=font)>width: raise ValueError('Word exceeds text area')
            trial=(line+' '+word).strip()
            if line and draw.textlength(trial,font=font)>width:
                result.append(line); line=word
            else: line=trial
        result.append(line)
    return result

def text(draw,value,x,y,size,bold=False,width=850,gap=None):
    value=value.lower()
    f=face(size,bold); step=gap or round(size*1.28)
    for line in lines(draw,value,f,width):
        bounds=draw.textbbox((0,0),line or 'А',font=f)
        draw.text((x,y-bounds[1]),line,font=f,fill=WHITE)
        y+=step
    return y

def background(path,size,focus):
    im=ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    im=ImageOps.fit(im,size,method=Image.Resampling.LANCZOS,centering=tuple(focus))
    # Never stretch. Cover crop and focal point are explicit per-slide settings.
    layer=Image.new('RGBA',size); d=ImageDraw.Draw(layer)
    for y in range(size[1]):
        # Retain scenery between blocks; keep white text dominant throughout.
        extra=.13*math.exp(-((y/size[1]-.47)/.40)**2)
        alpha=int(255*(.54+extra))
        d.line((0,y,size[0],y),fill=(0,0,0,alpha))
    return Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')

def matrix_diagram(draw,cx,cy,radius=265,tail=(15,5,8)):
    """Original explanatory geometry, not a personal matrix calculation.

    Tail order follows the existing bot's G2, G1, G positions (.66, .83, 1).
    Other values remain blank so the illustration invents no birth data.
    """
    points=[(cx-radius,cy),(cx-radius*.695,cy-radius*.695),
            (cx,cy-radius),(cx+radius*.695,cy-radius*.695),
            (cx+radius,cy),(cx+radius*.695,cy+radius*.695),
            (cx,cy+radius),(cx-radius*.695,cy+radius*.695)]
    ink='#B3B8AC'
    for indexes in ((0,2,4,6,0),(1,3,5,7,1),(0,4),(2,6),(1,5),(3,7)):
        draw.line([points[i] for i in indexes],fill=ink,width=2)
    ir=radius*.62
    draw.ellipse((cx-ir,cy-ir,cx+ir,cy+ir),outline=ink,width=1)
    def node(x,y,r,value='',highlight=False):
        draw.ellipse((x-r,y-r,x+r,y+r),fill='#151A12',outline=WHITE if highlight else ink,width=3 if highlight else 2)
        if value: draw.text((x,y),value,font=face(22,True),fill=WHITE,anchor='mm')
    for i,(x,y) in enumerate(points):
        if i!=6: node(x,y,23 if i%2==0 else 17)
    for direction in ((-1,0),(0,-1),(1,0)):
        for frac in (.66,.83): node(cx+direction[0]*radius*frac,cy+direction[1]*radius*frac,13)
    node(cx,cy,23)
    for frac,value,r in ((.66,str(tail[0]),20),(.83,str(tail[1]),17),(1,str(tail[2]),23)):
        node(cx,cy+radius*frac,r,value,True)
    draw.rounded_rectangle((cx-40,cy+radius*.66-32,cx+40,cy+radius+35),radius=29,outline=WHITE,width=3)


def position_diagram(draw,cx,cy,position,example,radius=265):
    """The same geometry as the bot, with a different highlighted real position."""
    vectors={'A':(-1,0),'B':(-.695,-.695),'C':(0,-1),'D':(.695,-.695),
             'E':(1,0),'F':(.695,.695),'G':(0,1),'H':(-.695,.695)}
    pos={k:(cx+x*radius,cy+y*radius) for k,(x,y) in vectors.items()}
    for k,(x,y) in vectors.items():
        for suffix,f in [('2',.66),('1',.82)]: pos[k+suffix]=(cx+x*radius*f,cy+y*radius*f)
    pos.update({'I':(cx,cy),'A3':(cx-radius*.36,cy),'C3':(cx,cy-radius*.36),
                'I2':(cx+radius*112/590,cy),'I1':(cx+radius*205/590,cy)})
    for k,t in [('FL',.25),('F3',.5),('FR',.75)]:
        a,b=pos['G2'],pos['E2']; pos[k]=(a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t)
    ink='#B3B8AC'
    for keys in [('A','C','E','G','A'),('B','D','F','H','B'),('A','E'),('C','G'),('B','F'),('D','H')]:
        draw.line([pos[k] for k in keys],fill=ink,width=2)
    draw.ellipse((cx-radius*.62,cy-radius*.62,cx+radius*.62,cy+radius*.62),outline=ink,width=1)
    draw.line([pos[k] for k in ['G2','FL','F3','FR','E2']],fill=ink,width=2)
    # Draw the chosen point last so its halo stays clear.
    for key in [k for k in pos if k!=position]+([position] if position else []):
        x,y=pos[key]; chosen=key==position
        r=25 if chosen or key=='I' else 21 if key in 'ACEG' else 15 if key in vectors else 12
        draw.ellipse((x-r,y-r,x+r,y+r),fill='#151A12',outline=WHITE if chosen else ink,width=3 if chosen else 1)
        draw.text((x,y),str(example[key]),font=face(22 if chosen else 16,chosen),fill=WHITE if chosen else ink,anchor='mm')
        if chosen: draw.ellipse((x-r-8,y-r-8,x+r+8,y+r+8),outline=WHITE,width=3)
    if position in ('FR','FL'):
        x,y=pos[position]
        if position=='FR': text(draw,'$',x-9,y-72,28,width=60)
        else:
            # Original heart geometry; no emoji-font dependency.
            outline=[]
            for i in range(80):
                t=i*2*math.pi/80
                outline.append((x+12*math.sin(t)**3,y-61-(13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t))*.8))
            draw.polygon(outline,fill=WHITE)


def render(config_path=None, output=None, background_dir=None):
    config_path=Path(config_path) if config_path else ROOT/'examples/15-5-8.json'
    folder=Path(output) if output else ROOT/'output/approved-style-15-5-8'
    backgrounds=Path(background_dir) if background_dir else ASSETS/'backgrounds'
    c=json.loads(config_path.read_text(encoding='utf-8'))
    is_series=c.get('type')=='arcana_series'
    if c.get('include_tarot_cards') and not is_series:
        raise ValueError('В кармический хвост карты таро не добавляются.')
    cards={}
    if is_series:
        from matrix_rules import THEMES,allowed
        from tarot_assets import prepare
        profile=THEMES[c['theme']]
        if c.get('position')!=profile['position']: raise ValueError('Позиция не соответствует теме.')
        numbers=[s['arcana_number'] for s in c['slides'] if s['layout']=='arcana']
        if len(numbers)!=len(set(numbers)) or any(n not in allowed(c['position']) for n in numbers):
            raise ValueError('Недопустимый или повторный аркан в позиции.')
        cards=prepare(numbers)
    if c.get('size')!=[1080,1920]:
        raise ValueError('Для этого макета нужен профиль 1080×1920.')
    out=folder/'slides'; out.mkdir(parents=True,exist_ok=True)
    slides=list(c['slides'])
    if c['include_cta']:
        slides.append({'layout':'closing','title':'разбор матрицы судьбы в Telegram-боте QuantaFate','background':'gothic-window.png','focus':[.5,.5],'blocks':[]})
    rendered=[]
    for i,s in enumerate(slides,1):
        asset=(backgrounds/s['background']).resolve()
        if not asset.is_relative_to(backgrounds.resolve()):
            raise ValueError('Фон должен находиться в каталоге фонов.')
        im=background(asset,tuple(c['size']),s['focus']); d=ImageDraw.Draw(im)
        x=90
        text(d,'quantafate',x,215,25,width=840)
        if s['layout']=='series_cover':
            y=text(d,s['title'],x,500,82,True)
            text(d,s['subtitle'],x,max(y+95,860),38,width=850)
        elif s['layout']=='arcana':
            from matrix_rules import ARCANA
            number=s['arcana_number']
            text(d,f'{number} аркан',460,390,28,width=505)
            y=text(d,ARCANA[number],460,460,50,True,width=505)+80
            art=Image.open(cards[number]).convert('RGBA')
            art=art.resize((312,598),Image.Resampling.LANCZOS)
            im.paste(art,(90,480),art); d=ImageDraw.Draw(im)
            y=max(650,y)
            for paragraph in s['paragraphs']: y=text(d,paragraph,460,y,40,width=500)+44
            if y>1510: raise ValueError(f'Аркан {number}: текст не помещается справа от карты.')
        elif s['layout']=='bot':
            text(d,'разобрать свою матрицу судьбы можешь в боте @quantafate',90,420,64,True,width=850)
            # Original matrix illustration, using the same real example as the series.
            if c.get('example_points'):
                position_diagram(d,540,1120,None,c['example_points'],radius=285)
            else:
                from matrix_rules import points
                position_diagram(d,540,1120,None,points(22,4,6),radius=285)
        elif s['layout']=='cover':
            text(d,s['title'],x,510,91,True)
            text(d,s['number'],x,805,109)
            text(d,s['subtitle'],x,1060,45,width=820)
        else:
            y=text(d,s['title'],x,345,64,True)+65
            for block in s.get('blocks',[]):
                if block.get('heading'): y=text(d,block['heading'],x,y,43,True)+22
                y=text(d,block['text'],x,y,43)+48
            if s['layout']=='location':
                cy=max(y+290,1060)
                if is_series:
                    position_diagram(d,525,cy,c['position'],c['example_points'])
                else: matrix_diagram(d,525,cy,tail=c.get('tail_numbers',[15,5,8]))
                y=cy+335
                text(d,s['note'],x,y,26)
                y+=50
            if y>1560: raise ValueError(f'Slide {i} overflows: {y}')
        text(d,'quantafate',90,1625,27)
        text(d,f'{i:02} / {len(slides):02}',825,1625,24,width=180)
        im.save(out/f'{i:02}.png'); rendered.append(im)
    sheet=Image.new('RGB',(360*4,640*math.ceil(len(rendered)/4)),'#151812')
    for i,im in enumerate(rendered): sheet.paste(im.resize((360,640),Image.Resampling.LANCZOS),((i%4)*360,(i//4)*640))
    sheet.save(folder/'preview.jpg',quality=95)
    compare=Image.new('RGB',(1080,960))
    first=backgrounds/slides[0]['background']
    original=ImageOps.fit(Image.open(first).convert('RGB'),(540,960))
    dark=background(first,(1080,1920),slides[0]['focus']).resize((540,960),Image.Resampling.LANCZOS)
    compare.paste(original,(0,0)); compare.paste(dark,(540,0)); compare.save(folder/'background-before-after.jpg',quality=95)
    (folder/'content.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'caption.txt').write_text(c.get('caption','').lower(),encoding='utf-8')
    with zipfile.ZipFile(folder/'carousel.zip','w',zipfile.ZIP_DEFLATED) as z:
        for i in range(1,len(slides)+1): z.write(out/f'{i:02}.png',f'slides/{i:02}.png')
        for name in ['content.json','caption.txt','preview.jpg']: z.write(folder/name,name)
    from pinterest_carousel import render as render_pinterest
    render_pinterest(c,folder/'pinterest',backgrounds,cards)
    print(f'Exported {len(rendered)} slides at {c["size"]}; tarot_cards={bool(cards)}; CTA={c["include_cta"] or is_series}')
    return [out/f'{i:02}.png' for i in range(1,len(slides)+1)]

if __name__=='__main__': render()

