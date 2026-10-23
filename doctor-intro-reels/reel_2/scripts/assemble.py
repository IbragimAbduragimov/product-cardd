"""Сборка ролика: кадр за кадром по монтажному листу, вывод 1080×1920, 59,94 fps.

Фронт берётся прямо из 4K HDR-исходника (одно декодирование, без промежуточных файлов):
тонмаппинг Hable → картина на стене → кадрирование по лицу (приближение ≤1,7× — всегда
уменьшение 4K, без увеличения) → восстановление светлых тонов (кривая из color_luts.json).
Остальное: боковые планы, графика и финальная плашка — из файлов без потерь; фото — с
медленным наездом. Поверх — субтитры и титры (PIL).
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.dirname(ROOT)
BUILD = os.path.join(ROOT, "build")
sys.path.insert(0, HERE)
from edl import FRONT_SRC  # noqa: E402

FPS = 60000 / 1001
W, H = 1080, 1920
SW, SH = 2160, 3840
EDL = json.load(open(os.path.join(BUILD, "edl.json")))
CUES = json.load(open(os.path.join(BUILD, "cues.json")))
TOTAL = EDL["total"]
LUTS = json.load(open(os.path.join(BUILD, "color_luts.json")))
FRONT_LUT = np.clip(np.round(np.array(LUTS["front"]).T), 0, 255).astype(np.uint8).reshape(256, 1, 3)
FACE_X4, EYES_Y4 = 538 * 2, 819 * 2          # медианное положение лица (YuNet), координаты 4K
EYES_FRAC = 0.39                               # глаза на 39 % высоты кадра при приближении
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:dither=error_diffusion,"
           "format=gbrp,format=rgb24")
rng = np.random.default_rng(5)


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- источники кадров

class Pipe:
    def __init__(self, cmd, w, h):
        self.n = w * h * 3
        self.shape = (h, w, 3)
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.n)
        self.j, self.frame = -1, None

    def get(self, j):
        j = max(j, 0)                       # начало плана между кадрами исходника → первый кадр
        while self.j < j:
            b = self.p.stdout.read(self.n)
            if len(b) < self.n:             # поток кончился раньше — держим последний кадр
                break
            self.frame = np.frombuffer(b, np.uint8).reshape(self.shape)
            self.j += 1
        if self.frame is None:
            raise RuntimeError("источник не отдал ни одного кадра")
        return self.frame

    def close(self):
        self.p.kill()
        self.p.wait()


def front_pipe(sa, dur):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{sa:.5f}", "-i", FRONT_SRC, "-t", f"{dur:.4f}",
           "-vf", TONEMAP, "-f", "rawvideo", "-"]
    pipe = Pipe(cmd, SW, SH)
    pipe.k0 = math.ceil(sa * FPS - 1e-6)       # первый кадр с pts ≥ sa
    return pipe


def file_pipe(path):
    return Pipe(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], W, H)


class Poster:
    """Картина сердца на стене, в координатах 4K (EDSR ×2 — без увеличения при приближении)."""
    PX, PY = 1360, 204

    def __init__(self, ref):
        p = cv2.cvtColor(cv2.imread(os.path.join(ROOT, "assets", "upscaled", "heart_poster_x2.png")),
                         cv2.COLOR_BGR2RGB).astype(np.float32)
        ph, pw = p.shape[:2]
        p *= np.array([1.02, 1.0, 0.97], np.float32) * 0.95            # баланс белого сцены
        wall = cv2.cvtColor(ref[self.PY:self.PY + ph, self.PX:self.PX + pw], cv2.COLOR_RGB2GRAY).astype(np.float32)
        light = cv2.GaussianBlur(wall, (0, 0), 120)
        p *= (1 + 0.6 * (light / light.mean() - 1))[..., None]          # освещение стены
        self.pad = pad = 80
        self.layer = np.zeros((ph + 2 * pad, pw + 2 * pad, 3), np.float32)
        self.alpha = np.zeros((ph + 2 * pad, pw + 2 * pad), np.float32)
        self.layer[pad:pad + ph, pad:pad + pw] = p
        self.alpha[pad:pad + ph, pad:pad + pw] = 1
        self.alpha = cv2.GaussianBlur(self.alpha, (5, 5), 1.2)
        sh = np.zeros_like(self.alpha)
        sh[pad + 18:pad + ph + 18, pad + 10:pad + pw + 10] = 1
        self.shadow = cv2.GaussianBlur(sh, (0, 0), 16) * 0.5
        # трекинг по предметам на столе (масштаб 540×960)
        g = cv2.cvtColor(cv2.resize(ref, (540, 960), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        m = np.zeros_like(g)
        m[650:850, 0:280] = 255
        m[690:750, :] = 255
        self.ref_g = g
        self.pts = cv2.goodFeaturesToTrack(g, 300, 0.01, 6, mask=m)

    def track(self, frame):
        g = cv2.cvtColor(cv2.resize(frame, (540, 960), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(self.ref_g, g, self.pts, None, winSize=(21, 21), maxLevel=3)
        ok = st[:, 0] == 1
        A, _ = cv2.estimateAffinePartial2D(self.pts[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=0.6)
        if A is None:
            A = np.array([[1, 0, 0], [0, 1, 0]], np.float64)
        A = A.copy()
        A[:, 2] *= 4                                                     # сдвиг в пикселях 4K
        return A

    def composite(self, frame, dof=0.0):
        A = self.track(frame)
        lh, lw = self.alpha.shape
        o = np.array([self.PX - self.pad, self.PY - self.pad], np.float64)
        x0, y0 = int(o[0]) - 8, int(o[1]) - 8
        x1, y1 = min(x0 + lw + 16, SW), y0 + lh + 16
        M = np.hstack([A[:, :2], (A[:, :2] @ o + A[:, 2] - [x0, y0])[:, None]])
        warp = lambda img: cv2.warpAffine(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_CUBIC,  # noqa: E731
                                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        f = frame[y0:y1, x0:x1].astype(np.float32)
        lay, a, sh = warp(self.layer), warp(self.alpha), warp(self.shadow)[..., None]
        if dof > 0.3:                    # на приближении фон чуть мягче — как у длинного фокуса
            lay, a = cv2.GaussianBlur(lay, (0, 0), dof), cv2.GaussianBlur(a, (0, 0), dof)
        a = a[..., None]
        grain = f - cv2.GaussianBlur(f, (0, 0), 2.0)                      # шум этого кадра
        out = f * (1 - sh)
        out = out * (1 - a) + (lay + 1.15 * grain) * a
        frame = frame.copy()
        frame[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)
        return frame


def zoom_crop(frame, z, smooth):
    """Кадрирование по лицу и уменьшение до 1080×1920 (всегда уменьшение из 4K)."""
    if z <= 1.0001:
        out = cv2.resize(frame, (W, H), interpolation=cv2.INTER_AREA)
    else:
        cw, ch = SW / z, SH / z
        x0 = min(max(FACE_X4 - cw / 2, 0), SW - cw)
        y0 = min(max(EYES_Y4 - EYES_FRAC * ch, 0), SH - ch)
        s = W / cw
        if not smooth:                                    # статичный план: точное уменьшение
            xi, yi = int(round(x0)), int(round(y0))
            out = cv2.resize(frame[yi:yi + int(round(ch)), xi:xi + int(round(cw))], (W, H),
                             interpolation=cv2.INTER_AREA)
        else:                                             # плавный наезд: субпиксельно, с антиалиасингом
            xi, yi = int(x0) - 4, int(y0) - 4
            x2, y2 = min(int(x0 + cw) + 6, SW), min(int(y0 + ch) + 6, SH)
            xi, yi = max(xi, 0), max(yi, 0)
            reg = cv2.GaussianBlur(frame[yi:y2, xi:x2], (0, 0), 0.42 / s)
            M = np.array([[s, 0, -(x0 - xi) * s], [0, s, -(y0 - yi) * s]])
            out = cv2.warpAffine(reg, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return cv2.LUT(out, FRONT_LUT)


class Photo:
    def __init__(self, name, kb, focus):
        img = cv2.cvtColor(cv2.imread(os.path.join(ROOT, "assets", "upscaled", f"{name}_x2.png")), cv2.COLOR_BGR2RGB)
        self.img = cv2.GaussianBlur(img, (0, 0), 0.45)            # антиалиасинг при уменьшении
        self.kb, self.focus = kb, focus

    def frame(self, p):
        ph, pw = self.img.shape[:2]
        cw0 = min(pw, ph * 9 / 16)
        k = self.kb[0] + (self.kb[1] - self.kb[0]) * p
        cw, ch = cw0 / k, cw0 * 16 / 9 / k
        x0 = min(max(self.focus[0] * pw - cw / 2, 0), pw - cw)
        y0 = min(max(self.focus[1] * ph - ch / 2, 0), ph - ch)
        s = W / cw
        M = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]])
        return cv2.warpAffine(self.img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


# ---------------------------------------------------------------- оверлей (титры, субтитры)

FONT_DIR = "/usr/share/fonts/opentype/inter"
ACCENT = (216, 188, 142)
SOFT = (255, 255, 255, 214)
NAVY = (12, 18, 34)


def font(name, size):
    return ImageFont.truetype(f"{FONT_DIR}/{name}.otf", size)


F_LABEL = font("Inter-SemiBold", 25)
F_SUB = font("Inter-SemiBold", 47)


def shadowed(img, radius=9, opacity=0.5):
    a = np.array(img)
    sh = np.zeros_like(a)
    sh[..., 3] = (a[..., 3] * opacity).astype(np.uint8)
    base = Image.new("RGBA", img.size, (0, 0, 0, 0))
    base.alpha_composite(Image.fromarray(sh).filter(ImageFilter.GaussianBlur(radius)), (0, 4))
    base.alpha_composite(img)
    return base


def text_img(text, fnt, fill, tracking=0, h=None):
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = int(sum(d.textlength(c, font=fnt) + tracking for c in text)) + 8
    h = h or int(fnt.size * 1.35)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    x = 2
    for c in text:
        dd.text((x, 0), c, font=fnt, fill=fill)
        x += dd.textlength(c, font=fnt) + tracking
    return shadowed(img)


def label_img(text):
    img = text_img(text.upper(), F_LABEL, ACCENT, tracking=5)
    out = Image.new("RGBA", (img.width + 62, img.height), (0, 0, 0, 0))
    ImageDraw.Draw(out).rectangle((2, 13, 46, 15), fill=ACCENT + (235,))
    out.alpha_composite(img, (62, 0))
    return out


class Heading:
    """Титр в верхней безопасной зоне: строки появляются по своим моментам."""

    def __init__(self, t_out, items, x=92, y=262, scrim=0.0, panel=False):
        self.t_out, self.x, self.y, self.scrim, self.panel = t_out, x, y, scrim, panel
        self.items = []                                          # (картинка, dy, момент)
        dy = 0
        for kind, text, t, *rest in items:
            if kind == "label":
                img = label_img(text)
                gap = 46
            else:
                size, weight, color = rest
                img = text_img(text, font(weight, size), color)
                gap = int(size * 1.12)
            self.items.append((img, dy, t))
            dy += gap
        self.t_in = min(t for _, _, t in self.items)
        if panel:                         # полупрозрачная подложка в стиле субтитров
            pw = max(img.width for img, _, _ in self.items) + 56
            ph = dy + 30
            self.panel_img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            ImageDraw.Draw(self.panel_img).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=24, fill=NAVY + (178,))

    def draw(self, canvas, t):
        if t < self.t_in - 0.01 or t > self.t_out:
            return
        out = ease_out((self.t_out - t) / 0.35)
        if self.panel:
            pa = ease_out((t - self.t_in) / 0.5) * out
            arr = np.array(self.panel_img)
            arr[..., 3] = (arr[..., 3] * pa).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(arr), (self.x - 28, self.y - 22))
        for img, dy, t0 in self.items:
            p = ease_out((t - t0) / 0.6)
            if p <= 0:
                continue
            a = np.array(img)
            a[..., 3] = (a[..., 3] * p * out).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(a), (self.x, self.y + dy + int((1 - p) * 22)))


def top_scrim(strength):
    g = np.zeros((780, W, 4), np.uint8)
    g[..., 3] = (np.clip(1 - np.arange(780) / 780, 0, 1) ** 1.5 * 170 * strength)[:, None].astype(np.uint8)
    return Image.fromarray(g)


SCRIM = top_scrim(1.0)


def watermark():
    """Водяной знак «abduragimov_cvs» как на референсе: антиква с широкой разрядкой, без подложки."""
    f = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 36)
    text, tracking = "abduragimov_cvs", 7.3
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = int(sum(d.textlength(c, font=f) for c in text) + tracking * (len(text) - 1)) + 4
    top = f.getbbox(text)[1]
    img = Image.new("RGBA", (w, 48), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    x = 0
    for c in text:
        dd.text((x, -top), c, font=f, fill=(255, 255, 255, 236))
        x += dd.textlength(c, font=f) + tracking
    return img


WATERMARK = watermark()
WATERMARK_XY = (92, 172)      # левый верхний угол, выше заголовков (они начинаются с y=262)


def parse_marked(text):
    out, hl = [], False
    for tok in text.split(" "):
        if tok.startswith("*"):
            hl, tok = True, tok[1:]
        end = "*" in tok
        out.append((tok.replace("*", ""), hl))
        if end:
            hl = False
    return out


def subtitle_img(text):
    words = parse_marked(text)
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    width = lambda ws: d.textlength(" ".join(w for w, _ in ws), font=F_SUB)  # noqa: E731
    lines = [words]
    if width(words) > 800:
        best = None
        for i in range(1, len(words)):
            a, b = words[:i], words[i:]
            if max(width(a), width(b)) <= 800:
                sc = abs(width(a) - width(b)) + (0 if width(a) >= 0.75 * width(b) else 60)
                if best is None or sc < best[0]:
                    best = (sc, [a, b])
        lines = best[1] if best else [words]
    lh, px, py = 62, 34, 20
    ws = [width(l) for l in lines]
    bw, bh = int(max(ws) + 2 * px), int(len(lines) * lh + 2 * py - 6)
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    dd.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=22, fill=NAVY + (188,))
    sp = dd.textlength(" ", font=F_SUB)
    for i, (ln, w) in enumerate(zip(lines, ws)):
        x = (bw - w) / 2
        for word, hl in ln:
            dd.text((x, py + i * lh - 4), word, font=F_SUB, fill=ACCENT if hl else (255, 255, 255))
            x += dd.textlength(word, font=F_SUB) + sp
    return img


def build_overlay():
    oc = CUES["overlay"]
    shots = EDL["shots"]
    end_t0 = next(s["t0"] for s in shots if s["kind"] == "endcard")

    def shot_end(kind, after):
        return next(s["t1"] for s in shots if s["kind"] == kind and s["t0"] <= after < s["t1"])

    W_ = (255, 255, 255)
    heads = [
        Heading(shot_end("front", oc["name"]), [
            ("label", "Врач-ординатор", oc["name"]),
            ("text", "Абдурагимов", oc["name"] + 0.08, 86, "InterDisplay-SemiBold", W_),
            ("text", "Абдурагим Магомедрасулович", oc["name"] + 0.16, 40, "InterDisplay-Light", SOFT),
            ("text", "Сердечно-сосудистый хирург", oc["surgeon"], 34, "Inter-Medium", ACCENT)]),
        Heading(shot_end("side", oc["handle"]), [
            ("label", "Мой блог", oc["handle"]),
            ("text", "@abduragimov_cvs", oc["handle"] + 0.1, 56, "Inter-SemiBold", W_)]),
        Heading(shot_end("front", oc["best"]), [
            ("label", "Главное", oc["best"]),
            ("text", "Лучшее лечение —", oc["best"] + 0.08, 70, "InterDisplay-SemiBold", W_),
            ("text", "это профилактика", oc["best_word"], 70, "InterDisplay-SemiBold", ACCENT)]),
        Heading(shot_end("front", oc["cond_label"]), [
            ("label", "Два условия", oc["cond_label"]),
            ("text", "Знания", oc["cond_know"], 70, "InterDisplay-SemiBold", W_),
            ("text", "+ готовность им следовать", oc["cond_ready"], 56, "InterDisplay-SemiBold", ACCENT)]),
        Heading(shot_end("front", oc["share"]), [
            ("label", "Цель блога", oc["share"]),
            ("text", "Профессиональные знания", oc["share"] + 0.1, 46, "InterDisplay-SemiBold", W_),
            ("text", "о профилактике болезней", oc["share"] + 0.4, 46, "InterDisplay-SemiBold", ACCENT)]),
    ]
    subs = [(e["s"], min(e["e"], end_t0), subtitle_img(e["text"])) for e in CUES["subs"]]
    return heads, subs


def draw_overlay(canvas, t, heads, subs):
    canvas.alpha_composite(WATERMARK, WATERMARK_XY)
    for h in heads:
        if h.scrim and h.t_in - 0.3 <= t <= h.t_out:
            a = min(ease_out((t - h.t_in + 0.3) / 0.5), ease_out((h.t_out - t) / 0.35))
            s = np.array(SCRIM)
            s[..., 3] = (s[..., 3] * a).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(s), (0, 0))
        h.draw(canvas, t)
    for s0, s1, img in subs:
        if s0 <= t < s1:
            a = min(1.0, (t - s0) / 0.12, (s1 - t) / 0.10)
            dy = int((1 - ease_out((t - s0) / 0.18)) * 8)
            arr = np.array(img)
            arr[..., 3] = (arr[..., 3] * a).astype(np.uint8)
            canvas.alpha_composite(Image.fromarray(arr), ((W - img.width) // 2, 1392 - img.height // 2 + dy))


# ---------------------------------------------------------------- сборка

class Renderer:
    def __init__(self):
        self.shots = EDL["shots"]
        self.clips = EDL["clips"]
        ref = front_pipe(40.0, 0.05).get(0)
        self.poster = Poster(ref)
        self.heads, self.subs = build_overlay()
        self.readers = {}
        self.photos = {}

    def front_src_time(self, shot, t):
        # клип фронта, внутри которого лежит этот план (или последний перед ним)
        cs = [c for c in self.clips if c["src"] == "front" and c["out"] <= shot["t0"] + 1e-6]
        c = max(cs, key=lambda c: c["out"])
        return c["a"] + (t - c["out"])

    def reader(self, shot):
        key = id(shot)
        if key not in self.readers:
            k = shot["kind"]
            if k == "front":
                sa = self.front_src_time(shot, shot["t0"])
                self.readers[key] = front_pipe(sa, shot["t1"] - shot["t0"] + 0.3)
            elif k == "side":
                tag = next(c["tag"] for c in self.clips if c["src"] == "side" and abs(c["out"] - shot["t0"]) < 0.02)
                self.readers[key] = file_pipe(os.path.join(BUILD, f"side_{tag}.mkv"))
            elif k in ("scene", "endcard"):
                name = shot.get("scene", "endcard")
                self.readers[key] = file_pipe(os.path.join(BUILD, f"scene_{name}.mkv"))
        return self.readers.get(key)

    def release(self, t):
        for s in self.shots:
            if s["t1"] < t - 0.05 and id(s) in self.readers:
                self.readers.pop(id(s)).close()

    def shot_frame(self, s, t):
        k = s["kind"]
        p = (t - s["t0"]) / max(s["t1"] - s["t0"], 1e-6)
        if k == "front":
            r = self.reader(s)
            src_t = self.front_src_time(s, t)
            fr = r.get(round(src_t * FPS) - r.k0)
            z0, z1 = s["zoom"]
            z = z0 + (z1 - z0) * ease_io(p)
            fr = self.poster.composite(fr, dof=max(0.0, z - 1.0) * 5.0)
            return zoom_crop(fr, z, smooth=abs(z1 - z0) > 1e-3)
        if k == "side":
            return self.reader(s).get(int((t - s["t0"]) * 30000 / 1001 + 1e-6))
        if k in ("scene", "endcard"):
            fr = self.reader(s).get(int(round((t - s["t0"]) * FPS))).astype(np.int16)
            noise = rng.normal(0, 1.5, (H // 2, W // 2)).astype(np.float32)
            noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
            return np.clip(fr + noise, 0, 255).astype(np.uint8)
        if k == "photo":
            if s["src"] not in self.photos:
                self.photos[s["src"]] = Photo(s["src"], s["kb"], s["focus"])
            return self.photos[s["src"]].frame(p)
        raise ValueError(k)

    def frame(self, t):
        active = [s for s in self.shots if s["t0"] - 1e-6 <= t < s["t1"]]
        if len(active) == 1:
            base = self.shot_frame(active[0], t)
        else:                                            # перекрытие = растворение (финал)
            a, b = sorted(active, key=lambda s: s["t0"])
            k = ease_io((t - b["t0"]) / (a["t1"] - b["t0"]))
            base = cv2.addWeighted(self.shot_frame(a, t), 1 - k, self.shot_frame(b, t), k, 0)
        canvas = Image.fromarray(base).convert("RGBA")
        draw_overlay(canvas, t, self.heads, self.subs)
        return np.asarray(canvas.convert("RGB"))


def main():
    args = sys.argv[1:]
    r = Renderer()
    if args and args[0] == "--stills":
        for t in map(float, args[1:]):
            img = r.frame(t)
            cv2.imwrite(os.path.join(BUILD, f"still_{t:07.2f}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            for k in list(r.readers):
                r.readers.pop(k).close()
        return
    t_from, t_to = (float(args[1]), float(args[2])) if args and args[0] == "--range" else (0.0, TOTAL)
    out = os.path.join(ROOT, "output", "reel_blog_purpose_1080x1920.mp4") if not args else \
        os.path.join(BUILD, f"range_{t_from:.0f}_{t_to:.0f}.mp4")
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", "60000/1001", "-i", "-", "-ss", f"{n0 / FPS:.5f}", "-t", f"{(n1 - n0) / FPS:.5f}",
                            "-i", os.path.join(BUILD, "mix.wav"),
                            "-map", "0:v", "-map", "1:a",
                            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.2",
                            "-g", "120", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", "-shortest", out],
                           stdin=subprocess.PIPE)
    for i in range(n0, n1):
        t = i / FPS
        enc.stdin.write(r.frame(t).tobytes())
        r.release(t)
        if i % 600 == 0:
            print(f"кадр {i}/{n1} ({t:.1f} с)", flush=True)
    enc.stdin.close()
    enc.wait()
    print("готово:", out)


if __name__ == "__main__":
    main()
