"""PNG-рендеры обложек → JPG для Instagram (качество 95, без субдискретизации цвета) и два обзора:
полный кадр 9:16 и то, как обложка видна в сетке профиля (центр 3:4, y 240–1680).
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
FONT = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 30)
COLS, TILE_W, GAP, LABEL = 5, 300, 16, 56
GRID_CROP = (0, 240, 1080, 1680)


def sheet(images, crop, name):
    tiles = [im.crop(crop) if crop else im for im in images]
    th = round(TILE_W * tiles[0].height / tiles[0].width)
    rows = (len(tiles) + COLS - 1) // COLS
    W = GAP + COLS * (TILE_W + GAP)
    H = GAP + rows * (th + LABEL + GAP)
    out = Image.new("RGB", (W, H), (244, 244, 244))
    d = ImageDraw.Draw(out)
    for i, (n, t) in enumerate(zip(numbers, tiles)):
        x = GAP + (i % COLS) * (TILE_W + GAP)
        y = GAP + (i // COLS) * (th + LABEL + GAP)
        out.paste(t.resize((TILE_W, th), Image.LANCZOS), (x, y))
        d.text((x, y + th + 12), f"№{n}", font=FONT, fill=(28, 28, 32))
    out.save(os.path.join(OUT, name), quality=92, subsampling=0)


paths = sorted(glob.glob(os.path.join(OUT, "cover_*.png")))
numbers = [int(os.path.basename(p)[6:8]) for p in paths]
images = [Image.open(p).convert("RGB") for p in paths]
for p, im in zip(paths, images):
    im.save(p[:-4] + ".jpg", quality=95, subsampling=0)
sheet(images, None, "_обзор_9x16.jpg")
sheet(images, GRID_CROP, "_обзор_сетка_профиля_3x4.jpg")
print(f"{len(images)} обложек → JPG, обзоры готовы")
