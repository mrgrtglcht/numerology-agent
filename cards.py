"""Create original test cards locally using Pillow; no API calls."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent


def font(size):
    for path in ('C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError('Нужен шрифт Arial или DejaVu Sans с поддержкой кириллицы.')


def wrap(draw, text, face, width):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line + ' ' + word).strip()
            if draw.textlength(candidate, font=face) > width:
                if not line:
                    raise ValueError('Слово не помещается на карточке.')
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return '\n'.join(lines)


def card(path, title, body, index, total, size=(1080, 1920), test=False):
    width, height = size
    image = Image.new('RGB', size, '#151329')
    draw = ImageDraw.Draw(image)
    margin = 95
    draw.rounded_rectangle((45, 45, width-45, height-45), radius=35, outline='#9580be', width=2)
    draw.text((margin, 110), 'QUANTAFATE / QUANTA AURA', font=font(30), fill='#cab6e5')
    draw.text((margin, 180), 'ТЕСТ ФОРМАТА' if test else 'ВОПРОС ДЛЯ СЕБЯ', font=font(26), fill='#efc37d')
    for font_size in range(74, 39, -2):
        face = font(font_size)
        wrapped = wrap(draw, title, face, width-2*margin)
        bounds = draw.multiline_textbbox((0, 0), wrapped, font=face, spacing=18)
        if bounds[3] <= height * .28:
            break
    else:
        raise ValueError('Слишком длинный заголовок.')
    draw.multiline_text((margin, int(height*.24)), wrapped, font=face, fill='#ffffff', spacing=18)
    body_face = font(40)
    wrapped_body = wrap(draw, body, body_face, width-2*margin)
    body_bounds = draw.multiline_textbbox((0, 0), wrapped_body, font=body_face, spacing=16)
    if body_bounds[3] > height*.27:
        raise ValueError('Слишком длинный текст карточки.')
    draw.line((margin, int(height*.54), width-margin, int(height*.54)), fill='#9580be', width=2)
    draw.multiline_text((margin, int(height*.59)), wrapped_body, font=body_face, fill='#ddd4e9', spacing=16)
    draw.text((margin, height-180), '@quanta.aura', font=font(30), fill='#cab6e5')
    draw.text((width-200, height-180), f'{index}/{total}', font=font(30), fill='#efc37d')
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=92, optimize=True)


def main():
    output = ROOT / 'output' / 'format-test'
    slides = [
        ('Знакомство с собой', 'Три вопроса для спокойной саморефлексии.'),
        ('Что даёт тебе силы?', 'Вспомни занятие, после которого чувствуешь больше энергии.'),
        ('Какой шаг сделаешь сегодня?', 'Выбери одно небольшое действие и сохрани эту мысль.'),
    ]
    for index, (title, body) in enumerate(slides, 1):
        card(output / f'tiktok-{index:02}.jpg', title, body, index, len(slides), test=True)
    card(output / 'pinterest-pin.jpg', 'Что даёт тебе силы?',
         'Один вопрос для саморефлексии. Сохрани, чтобы вернуться к нему позже.', 1, 1, (1000, 1500), test=True)
    print('Готово: 3 JPG для TikTok и 1 JPG для Pinterest. Публикаций не было.')


if __name__ == '__main__':
    main()
