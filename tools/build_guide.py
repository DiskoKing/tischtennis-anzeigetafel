"""Render the shared German guide to HTML and PDF (build-time ReportLab only)."""
from pathlib import Path
import html
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'docs/ANLEITUNG.md').read_text(encoding='utf-8')

def inline(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'<font face="Code">\1</font>', text)
    return text

def blocks(section):
    paragraph = []
    lines = section.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            if paragraph:
                yield 'p', ' '.join(paragraph); paragraph = []
            code = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            yield 'code', '\n'.join(code)
        elif line.startswith('#'):
            if paragraph:
                yield 'p', ' '.join(paragraph); paragraph = []
            level = len(line)-len(line.lstrip('#'))
            yield 'h'+str(level), line[level:].strip()
        elif not line.strip():
            if paragraph:
                yield 'p', ' '.join(paragraph); paragraph = []
        elif re.match(r'^(- |\d+\. )', line):
            if paragraph:
                yield 'p', ' '.join(paragraph); paragraph = []
            yield 'li', line
        else:
            paragraph.append(line)
        i += 1
    if paragraph:
        yield 'p', ' '.join(paragraph)

sections = source.split('\n---\n')
html_parts=[]
for section in sections:
    content=[]
    for kind,text in blocks(section):
        if kind=='code': content.append('<pre><code>'+html.escape(text)+'</code></pre>')
        else:
            tag='p' if kind=='li' else kind
            formatted=inline(text).replace('<font face="Code">','<code>').replace('</font>','</code>')
            formatted=re.sub(r'(https?://[^\s<]+)',r'<a href="\1">\1</a>',formatted)
            content.append('<'+tag+'>'+formatted+'</'+tag+'>')
    html_parts.append('<section>'+'\n'.join(content)+'</section>')
stylesheet='''body{font:16px/1.6 system-ui,Arial,sans-serif;background:#eeeae4;color:#202d33;margin:0}main{max-width:900px;margin:auto}section{background:#fff;padding:36px 44px;margin:24px 0;border-top:5px solid #008e87;border-radius:8px}h1{line-height:1.2;font-size:30px}h2,h3{color:#006f69}pre{background:#f0f3f4;padding:14px;overflow:auto;font:13px/1.5 Consolas,monospace}a{color:#006f69;overflow-wrap:anywhere}code{font-family:Consolas,monospace}nav{padding:20px;text-align:center}button{padding:10px 18px;cursor:pointer}@media(max-width:600px){section{padding:22px 18px;margin:12px 0}}@media print{body{background:white;font-size:10pt}section{break-after:page;margin:0;padding:0;border:0}nav{display:none}pre{white-space:pre-wrap;font-size:8pt}}'''
(ROOT/'docs/ANLEITUNG.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TT-Anzeigetafel - Anleitung</title><style>'+stylesheet+'</style><nav><button onclick="window.print()">Drucken / als PDF speichern</button></nav><main>'+''.join(html_parts)+'</main></html>',encoding='utf-8')

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

if sys.platform=='win32':
    fonts=Path('C:/Windows/Fonts')
    regular,bold,code=fonts/'segoeui.ttf',fonts/'segoeuib.ttf',fonts/'consola.ttf'
else:
    fonts=Path('/usr/share/fonts/truetype/dejavu')
    regular,bold,code=fonts/'DejaVuSans.ttf',fonts/'DejaVuSans-Bold.ttf',fonts/'DejaVuSansMono.ttf'
for name,file in [('Body',regular),('BodyBold',bold),('Code',code)]:
    pdfmetrics.registerFont(TTFont(name,str(file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
styles={
 'h1':ParagraphStyle('h1',fontName='BodyBold',fontSize=23,leading=28,textColor=HexColor('#202d33'),spaceAfter=14),
 'h2':ParagraphStyle('h2',fontName='BodyBold',fontSize=17,leading=21,textColor=HexColor('#008e87'),spaceAfter=12),
 'h3':ParagraphStyle('h3',fontName='BodyBold',fontSize=12,leading=16,textColor=HexColor('#006f69'),spaceBefore=10,spaceAfter=6),
 'p':ParagraphStyle('body',fontName='Body',fontSize=9.7,leading=13.6,textColor=HexColor('#283840'),spaceAfter=8),
 'li':ParagraphStyle('list',fontName='Body',fontSize=9.7,leading=13.6,textColor=HexColor('#283840'),leftIndent=10,firstLineIndent=-10,spaceAfter=6),
 'code':ParagraphStyle('code',fontName='Code',fontSize=7.3,leading=10,backColor=HexColor('#f0f3f4'),borderPadding=7,spaceBefore=6,spaceAfter=10),
}
def footer(c,doc):
    w,h=A4
    c.setFillColor(HexColor('#008e87'));c.rect(0,h-5,w,5,fill=1,stroke=0)
    c.setStrokeColor(HexColor('#d5dfdf'));c.line(40,35,w-40,35)
    c.setFont('Body',8);c.setFillColor(HexColor('#53626b'))
    c.drawString(40,22,'TT-Anzeigetafel | Anleitung 2.2.14')
    c.drawRightString(w-40,22,str(doc.page))
story=[]
for n,section in enumerate(sections):
    if n:story.append(PageBreak())
    for kind,text in blocks(section):
        if kind=='code':
            max_width=A4[0]-80-14
            for line in text.splitlines():
                if pdfmetrics.stringWidth(line,'Code',7.3)>max_width:
                    raise ValueError('Codezeile zu breit: '+line)
            story.append(Preformatted(text,styles['code']))
        else:
            story.append(Paragraph(inline(text),styles[kind]))
output=ROOT/'docs/TT-Anzeigetafel-Anleitung.pdf'
SimpleDocTemplate(str(output),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=39,bottomMargin=47,title='TT-Anzeigetafel - Einrichtung und Bedienung',author='Frank Fehrmann').build(story,onFirstPage=footer,onLaterPages=footer)
print(output)
