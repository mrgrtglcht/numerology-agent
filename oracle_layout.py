"""Square photo panels and matching physical card layouts on a black portrait canvas."""
from pathlib import Path
import random,hashlib
from PIL import Image,ImageOps,ImageDraw,ImageFont,ImageFilter,ImageEnhance
ROOT=Path(__file__).resolve().parent
W,H=1080,1920

def face(size):
    f=ImageFont.truetype(str(ROOT/'assets/fonts/Manrope.ttf'),size)
    f.set_variation_by_axes([650]);return f

def wrapped(value,font,width):
    d=ImageDraw.Draw(Image.new('RGB',(1,1)));lines=[]
    for paragraph in value.split('\n'):
        line=''
        for word in paragraph.split():
            trial=(line+' '+word).strip()
            if line and d.textlength(trial,font=font)>width:lines.append(line);line=word
            else:line=trial
        lines.append(line)
    return lines

def text_slide(value,bg,handle=True,size=52):
    photo=ImageOps.fit(Image.open(bg).convert('RGB'),(1080,1080),method=Image.Resampling.LANCZOS)
    photo=Image.blend(photo,Image.new('RGB',photo.size,'black'),.23)
    canvas=Image.new('RGB',(W,H),'black');canvas.paste(photo,(0,420))
    d=ImageDraw.Draw(canvas);f=face(size);lines=wrapped(value,f,850)
    step=round(size*1.26);total=len(lines)*step+(70 if handle else 0)
    y=960-total//2
    for line in lines:
        d.text((540,y),line,font=f,fill='white',anchor='mt',stroke_width=3,stroke_fill='#171a16')
        y+=step
    if handle:d.text((540,y+28),'тгк: @quantafate',font=face(30),fill='white',anchor='mt',stroke_width=2,stroke_fill='#171a16')
    return canvas

def positions(count):
    if count==3:return [(235,300,-2.0),(800,305,1.7),(535,795,-.8)]
    if count==4:return [(295,290,-2),(785,295,1.4),(290,795,1.1),(790,790,-1.8)]
    all_six=[(205,280,-1.5),(540,275,.8),(875,285,-1.2),(200,795,1.3),(540,790,-.8),(880,800,1.7)]
    return all_six[:count]

def crop_alpha(path):
    with Image.open(path) as source:
        card=source.convert('RGBA')
        return card.crop(card.getchannel('A').point(lambda a:255 if a>8 else 0).getbbox())

def table_slide(numbers,deck,manifest,table_path,reveal=False,seed=''):
    table=ImageOps.fit(Image.open(table_path).convert('RGBA'),(1080,1080),method=Image.Resampling.LANCZOS)
    rng=random.Random(seed)
    table=table.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if rng.random()<.5 else table
    table=ImageEnhance.Color(table).enhance(rng.uniform(.65,1.15))
    table=ImageEnhance.Brightness(table).enhance(rng.uniform(.82,1.08))
    width=260 if len(numbers)>=5 else 270
    for n,(cx,cy,angle) in zip(numbers,positions(len(numbers))):
        file=next(c['file'] for c in manifest['cards'] if c['id']==n) if reveal else manifest['back']['file']
        card=crop_alpha(deck/file)
        # Shared physical dimensions keep front/back footprints aligned.
        card=card.resize((width,round(width*118/70)),Image.Resampling.LANCZOS)
        card=card.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
        x=round(cx-card.width/2);y=round(cy-card.height/2)
        shadow=Image.new('RGBA',table.size,(0,0,0,0))
        mask=card.getchannel('A').point(lambda a:round(a*.36))
        shadow.paste((48,32,22,255),(x+5,y+7,x+5+card.width,y+7+card.height),mask)
        table=Image.alpha_composite(table,shadow.filter(ImageFilter.GaussianBlur(5)))
        table.alpha_composite(card,(x,y))
    result=Image.new('RGB',(W,H),'black');result.paste(table.convert('RGB'),(0,420))
    return result


def render(config,folder,bg,deck,manifest,seed=''):
    folder=Path(folder);out=folder/'slides';out.mkdir(parents=True,exist_ok=True)
    ids=[o['card_id'] for o in config['options']]
    table=deck/'table.jpg'
    slides=[text_slide(config['title'],bg),
      text_slide('подумай о человеке и\nинтуитивно выбери карту',bg,False),
      table_slide(ids,deck,manifest,table,seed=seed),
      text_slide('это оракул — здесь важны\nтвои ассоциации. первая мысль\nпри взгляде на выбранную карту\nможет стать твоей подсказкой',bg,False,size=47),
      table_slide(ids,deck,manifest,table,True,seed)]
    for i,im in enumerate(slides,1):im.save(out/f'{i:02}.png')
    sheet=Image.new('RGB',(1800,640),'black')
    for i,im in enumerate(slides):sheet.paste(im.resize((360,640),Image.Resampling.LANCZOS),(i*360,0))
    sheet.save(folder/'preview.jpg',quality=94)
