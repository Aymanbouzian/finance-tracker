"""Rebuild checked-in PWA icons: python core/generate_icons.py (Pillow required)."""

from pathlib import Path

from PIL import Image, ImageDraw

TARGET = Path(__file__).resolve().parent.parent / "static" / "pwa"
SCALE = 4
GREEN = "#153f36"
MINT = "#b8e5b4"


def rect(draw, box, radius, fill):
    draw.rounded_rectangle(tuple(int(x * SCALE) for x in box), radius=radius * SCALE, fill=fill)


def line(draw, start, end, fill, width):
    draw.line([tuple(int(x * SCALE) for x in start), tuple(int(x * SCALE) for x in end)], fill=fill, width=width * SCALE)
    radius = width / 2
    for x, y in (start, end):
        draw.ellipse(tuple(int(v * SCALE) for v in (x - radius, y - radius, x + radius, y + radius)), fill=fill)


image = Image.new("RGB", (512 * SCALE, 512 * SCALE), GREEN)
draw = ImageDraw.Draw(image)
rect(draw, (144, 132, 368, 380), 40, MINT)
for y, end in ((198, 316), (248, 288), (298, 256)):
    line(draw, (196, y), (end, y), GREEN, 22)
draw.ellipse((288 * SCALE, 288 * SCALE, 396 * SCALE, 396 * SCALE), fill=GREEN)
line(draw, (342, 318), (342, 366), MINT, 14)
line(draw, (318, 342), (366, 342), MINT, 14)
for size in (192, 512):
    image.resize((size, size), Image.Resampling.LANCZOS).save(TARGET / f"icon-{size}.png")
