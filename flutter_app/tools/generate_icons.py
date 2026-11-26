"""Generate PocketLedger's simple wave mark without external artwork."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
for size in (192, 512):
    scale = 3
    image = Image.new('RGB', (size * scale, size * scale), '#ffc54d')
    draw = ImageDraw.Draw(image)
    for row in range(3):
        points = [(int(x*size*scale), int((.36+row*.14+.045*math.sin((x-.23)*math.pi*4))*size*scale)) for x in [i/1000 for i in range(230,771)]]
        draw.line(points, fill='#252733', width=int(size*scale*.035), joint='curve')
    image = image.resize((size,size),Image.Resampling.LANCZOS)
    for name in (f'Icon-{size}.png', f'Icon-maskable-{size}.png'):
        image.save(root/'web'/'icons'/name)
    if size==192:
        image.resize((48,48)).save(root/'web'/'favicon.png')
