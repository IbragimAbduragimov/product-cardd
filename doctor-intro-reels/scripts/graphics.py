"""Графический слой (RGBA 1080×1920, 30 fps): титры, субтитры, финальная плашка.

Палитра: тёмно-синий фона студии, белый, приглушённое «шампанское» как единственный
акцент. Типографика — Inter / Inter Display. Анимации короткие и мягкие.
"""
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __import__("os").path.dirname(__file__))
from timeline import CARDS, FPS, H, MAIN_END, ROOT, TOTAL, W, subtitle_events  # noqa: E402

FONT_DIR = "/usr/share/fonts/opentype/inter"
WHITE = (255, 255, 255)
SOFT = (255, 255, 255, 214)
ACCENT = (214, 186, 140)
NAVY = (10, 19, 37)

MARGIN_X = 92
TOP_Y = 252          # ниже интерфейса Reels сверху
SUB_CENTER_Y = 1392  # выше подписи и кнопок Reels снизу
SUB_MAX_W = 800


def font(name, size):
    return ImageFont.truetype(f"{FONT_DIR}/{name}.otf", size)


F_LABEL = font("Inter-SemiBold", 25)
F_TITLE = font("InterDisplay-SemiBold", 76)
F_NAME = font("InterDisplay-SemiBold", 86)
F_SUBT = font("InterDisplay-Light", 40)
F_LINE = font("Inter-Regular", 30)
F_NUM = font("InterDisplay-SemiBold", 150)
F_UNIT = font("InterDisplay-Light", 46)
F_STAT_SUB = font("Inter-Light", 31)
F_SUB = font("Inter-SemiBold", 47)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def text_tracked(draw, xy, text, fnt, fill, tracking=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def tracked_width(draw, text, fnt, tracking):
    return sum(draw.textlength(c, font=fnt) for c in text) + tracking * (len(text) - 1)


def shadowed(img, radius=10, opacity=0.55):
    """Мягкая тень под текстом — читаемость без «обводки»."""
    from PIL import ImageFilter
    a = np.array(img)
    sh = np.zeros_like(a)
    sh[..., 3] = (a[..., 3] * opacity).astype(np.uint8)
    sh_img = Image.fromarray(sh).filter(ImageFilter.GaussianBlur(radius))
    base = Image.new("RGBA", img.size, (0, 0, 0, 0))
    base.alpha_composite(sh_img, (0, 4))
    base.alpha_composite(img)
    return base


# ---------- Титры ----------

def card_layers(card):
    """Возвращает список (слой, y_слоя, время_появления) для одной карточки."""
    layers = []
    cw = W - MARGIN_X - 40

    def layer(h):
        img = Image.new("RGBA", (cw, h), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    y = TOP_Y
    img, d = layer(40)
    text_tracked(d, (0, 2), card["label"], F_LABEL, ACCENT, tracking=5)
    layers.append((shadowed(img, 6, 0.4), y, 0.0))
    y += 44

    if card["kind"] in ("name", "info"):
        big = F_NAME if card["kind"] == "name" else F_TITLE
        img, d = layer(110)
        d.text((0, 0), card["title"], font=big, fill=WHITE)
        layers.append((shadowed(img), y, 0.08))
        y += 98 if card["kind"] == "name" else 88
        img, d = layer(60)
        d.text((2, 0), card["subtitle"], font=F_SUBT, fill=SOFT)
        layers.append((shadowed(img), y, 0.16))
        y += 66
        for t_rel, text in card.get("lines", []):
            img, d = layer(46)
            d.ellipse((4, 15, 12, 23), fill=ACCENT)
            d.text((26, 2), text, font=F_LINE, fill=SOFT)
            layers.append((shadowed(img, 6), y, t_rel - card["t0"]))
            y += 44
    else:  # stat
        layers.append(("NUMBER", y - 14, 0.08))
        y += 162
        img, d = layer(100)
        for i, line in enumerate(card["subtitle"].split("\n")):
            d.text((2, i * 42), line, font=F_STAT_SUB, fill=SOFT)
        layers.append((shadowed(img), y, 0.18))
        y += 92
    return layers, y


def number_layer(card, value_text):
    img = Image.new("RGBA", (W - MARGIN_X, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((-4, 0), value_text, font=F_NUM, fill=WHITE)
    x = d.textlength(value_text, font=F_NUM) + 16
    d.text((x, 84), card["unit"], font=F_UNIT, fill=ACCENT)
    return shadowed(img, 12)


CARD_CACHE = {}


def draw_card(canvas, card, t):
    if not (card["t0"] <= t < card["t1"]):
        return 0.0
    key = id(card)
    if key not in CARD_CACHE:
        CARD_CACHE[key] = card_layers(card)
    layers, bottom = CARD_CACHE[key]
    rel = t - card["t0"]
    out = ease_out((card["t1"] - t) / 0.45) if card["t1"] - t < 0.45 else 1.0
    for lay, y, delay in layers:
        p = ease_out((rel - delay) / 0.65)
        if p <= 0:
            continue
        if lay == "NUMBER":
            num = card["number"]
            if card.get("count_up"):
                q = ease_out((rel - delay) / 1.2)
                num = str(int(round(100 + (int(num) - 100) * q)))
            lay = number_layer(card, num)
        a = p * out
        dy = int((1 - p) * 22)
        paste(canvas, lay, MARGIN_X, y + dy, a)
    # вертикальная акцентная линия, «прорисовывается» сверху вниз
    p = ease_out(rel / 0.8)
    line_h = int((bottom - TOP_Y - 18) * p)
    if line_h > 2:
        a = int(235 * out)
        canvas_draw = ImageDraw.Draw(canvas)
        canvas_draw.rectangle((MARGIN_X - 30, TOP_Y + 6, MARGIN_X - 28, TOP_Y + 6 + line_h),
                              fill=ACCENT + (a,))
    return out * ease_out(rel / 0.5)


def paste(canvas, img, x, y, alpha):
    if alpha <= 0.003:
        return
    if alpha < 0.999:
        arr = np.array(img)
        arr[..., 3] = (arr[..., 3] * alpha).astype(np.uint8)
        img = Image.fromarray(arr)
    canvas.alpha_composite(img, (int(x), int(y)))


# Верхний мягкий градиент под титрами (полезен на фото со светлым верхом)
_g = np.zeros((760, W, 4), np.uint8)
_g[..., 3] = (np.clip(1 - np.arange(760) / 760, 0, 1) ** 1.6 * 150)[:, None].astype(np.uint8)
TOP_SCRIM = Image.fromarray(_g)


# ---------- Субтитры ----------

def wrap(draw, words, fnt, max_w):
    def width(ws):
        return draw.textlength(" ".join(w for w, _ in ws), font=fnt)
    if width(words) <= max_w:
        return [words]
    best = None
    for i in range(1, len(words)):
        a, b = words[:i], words[i:]
        wa, wb = width(a), width(b)
        if max(wa, wb) <= max_w:
            score = abs(wa - wb) + (0 if wa >= wb * 0.75 else 60)
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else [words]


def parse_marked(text):
    out, hl = [], False
    for tok in text.split(" "):
        start = tok.startswith("*")
        if start:
            hl = True
            tok = tok[1:]
        end = tok.endswith("*") or (tok.endswith("*,") or tok.endswith("*."))
        clean = tok.replace("*", "")
        out.append((clean, hl))
        if end:
            hl = False
    return out


def subtitle_image(text):
    words = parse_marked(text)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = wrap(tmp, words, F_SUB, SUB_MAX_W)
    lh = 62
    widths = [tmp.textlength(" ".join(w for w, _ in ln), font=F_SUB) for ln in lines]
    pad_x, pad_y = 34, 20
    bw = int(max(widths) + 2 * pad_x)
    bh = int(len(lines) * lh + 2 * pad_y - 6)
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=22, fill=NAVY + (190,))
    space = d.textlength(" ", font=F_SUB)
    for i, (ln, wdt) in enumerate(zip(lines, widths)):
        x = (bw - wdt) / 2
        y = pad_y + i * lh - 4
        for w, hl in ln:
            d.text((x, y), w, font=F_SUB, fill=ACCENT if hl else WHITE)
            x += d.textlength(w, font=F_SUB) + space
    return img


# ---------- Финальная плашка ----------

def end_card():
    img = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    label = "ВРАЧ-ОРДИНАТОР"
    lw = tracked_width(d, label, F_LABEL, 6)
    text_tracked(d, ((W - lw) / 2, 40), label, F_LABEL, ACCENT, tracking=6)
    for i, (txt, fnt, fill) in enumerate([("Абдурагимов", F_NAME, WHITE),
                                          ("Абдурагим Магомедрасулович", F_SUBT, SOFT)]):
        tw = d.textlength(txt, font=fnt)
        d.text(((W - tw) / 2, 92 + i * 108), txt, font=fnt, fill=fill)
    d.rectangle((W / 2 - 36, 278, W / 2 + 36, 280), fill=ACCENT)
    txt = "Сердечно-сосудистая хирургия"
    tw = d.textlength(txt, font=F_LINE)
    d.text(((W - tw) / 2, 308), txt, font=F_LINE, fill=SOFT)
    return img


def main():
    events = subtitle_events()
    sub_imgs = [subtitle_image(e["text"]) for e in events]
    end_img = end_card()
    n_frames = int(math.ceil(TOTAL * FPS))
    out = f"{ROOT}/build/overlay.mov"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "qtrle", "-pix_fmt", "argb", out], stdin=subprocess.PIPE)
    blank = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    preview_at = {int(float(a) * FPS) for a in sys.argv[1:]}
    for fi in range(n_frames):
        t = fi / FPS
        canvas = blank.copy()
        for c in CARDS:
            if c["t0"] <= t < c["t1"]:
                a = min(ease_out((t - c["t0"]) / 0.5), ease_out((c["t1"] - t) / 0.45)) * 0.9
                strength = c.get("scrim", 1.0)       # >1 — плотнее, для светлого верха кадра
                paste(canvas, TOP_SCRIM, 0, 0, a)
                if strength > 1:
                    paste(canvas, TOP_SCRIM, 0, 0, a * (strength - 1))
        for c in CARDS:
            draw_card(canvas, c, t)
        for e, img in zip(events, sub_imgs):
            if e["s"] <= t < e["e"]:
                a = min(1.0, (t - e["s"]) / 0.12, (e["e"] - t) / 0.10)
                dy = int((1 - ease_out((t - e["s"]) / 0.18)) * 8)
                paste(canvas, img, (W - img.width) / 2, SUB_CENTER_Y - img.height / 2 + dy, a)
        if t >= MAIN_END - 0.25:
            p = ease_out((t - (MAIN_END - 0.25)) / 0.9)
            paste(canvas, end_img, 0, 760 + int((1 - p) * 20), p * min(1.0, (TOTAL - t) / 0.4 + 0.0001))
        if fi in preview_at:
            canvas.save(f"{ROOT}/build/overlay_{t:.2f}.png")
        ff.stdin.write(canvas.tobytes())
    ff.stdin.close()
    ff.wait()
    print("overlay frames:", n_frames)


if __name__ == "__main__":
    main()
