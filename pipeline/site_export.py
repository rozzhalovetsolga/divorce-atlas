"""Wrap built pages into full HTML documents: build/index.html → ../index.html, build/appendix.html → ../appendix.html."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
BASE = 'https://rozzhalovetsolga.github.io/divorce-atlas/'


def document(path, title, description, url):
    src = open(path).read()
    cut = src.index('</style>') + len('</style>')
    head, body = src[:cut], src[cut:]
    meta = (f'<meta name="description" content="{description}">\n'
            f'<meta property="og:type" content="website">\n'
            f'<meta property="og:title" content="{title}">\n'
            f'<meta property="og:description" content="{description}">\n'
            f'<meta property="og:url" content="{url}">\n'
            f'<meta property="og:image" content="{BASE}og.png">\n'
            f'<meta property="og:image:width" content="1200">\n'
            f'<meta property="og:image:height" content="630">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n')
    return ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + meta + head + '\n<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%}</style>\n</head>\n<body>\n'
            + body + '\n</body>\n</html>\n')


lean = document(f'{HERE}/build/index.html', 'Почему люди разводятся',
                'Где разводятся чаще, что к этому ведёт и когда браки распадаются — коротко и с источниками.', BASE)
full = document(f'{HERE}/build/appendix.html', 'Атлас разводов: все данные',
                'Карты, досье 200+ исследований, Беларусь, США и длительность брака — со ссылками на источники.', BASE + 'appendix.html')
open(f'{SITE}/index.html', 'w').write(lean)
open(f'{SITE}/appendix.html', 'w').write(full)
print('exported index', len(lean), 'appendix', len(full))
