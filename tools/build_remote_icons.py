"""Build-time only: generate the checked-in, neutral TT remote home-screen icons."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

root = Path(__file__).resolve().parents[1]/'public/assets'
font = 'C:/Windows/Fonts/segoeuib.ttf' if os.name == 'nt' else '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
image = Image.new('RGB', (512,512), '#008e87')
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((80,115,432,357), radius=22, fill='#0b1520', outline='white', width=12)
draw.text((256,222), 'TT', font=ImageFont.truetype(font,128), fill='white', anchor='mm')
draw.rounded_rectangle((239,360,273,391),radius=4,fill='white')
draw.rounded_rectangle((181,391,331,405),radius=6,fill='white')
for size in (180,192,512):
    image.resize((size,size),Image.Resampling.LANCZOS).save(root/f'remote-{size}.png')
