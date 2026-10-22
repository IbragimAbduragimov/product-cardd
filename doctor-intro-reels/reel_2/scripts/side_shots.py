"""Боковые планы: две фразы бокового дубля из 4K-исходника.

Та же обработка, что в side_angle_2 (стабилизация «как со штатива», кадр 1,5× из 4K,
замена стены синим фоном с маской RVM), плюс:
  • ровный шаг 29,97 кадра/с (исходник писал неравномерно 30–60 fps) — в монтаже 59,94
    каждый кадр показывается дважды, без рывков;
  • цветовая подгонка под фронтальную камеру (только цвет стены, см. color_luts.json).
Результат — build/side_<фраза>.mkv (FFV1, без потерь), 1080×1920.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "side_angle_2", "scripts"))
import process as P  # noqa: E402  (стабилизация, маска, заливка стены)

sys.path.insert(0, HERE)
from edl import clip  # noqa: E402

FPS = 30000 / 1001
WARM = 0.6
T = np.load(os.path.join(os.path.dirname(ROOT), "side_angle_2", "build", "transforms.npy"))
LUT = np.array(json.load(open(os.path.join(ROOT, "build", "color_luts.json")))["side"], np.float32)
LUT8 = np.clip(np.round(LUT), 0, 255).astype(np.uint8)


def transform_at(t):
    x = t * 30.0
    i = int(np.floor(x))
    f = x - i
    i = min(max(i, 0), len(T) - 2)
    return T[i] * (1 - f) + T[i + 1] * f


def frames(ss, dur):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss:.4f}", "-i", P.SRC, "-t", f"{dur:.4f}", "-vf",
           f"fps=30000/1001,scale=in_color_matrix=bt709:out_color_matrix=bt709,format=rgb24",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=P.SW * P.SH * 3)
    n = P.SW * P.SH * 3
    k = 0
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield ss + k / FPS, np.frombuffer(b, np.uint8).reshape(P.SH, P.SW, 3)
        k += 1


def render(tag):
    c = clip(tag)
    a, b = c["a"], c["b"]
    out = os.path.join(ROOT, "build", f"side_{tag}.mkv")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                            "-r", "30000/1001", "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", out],
                           stdin=subprocess.PIPE)
    matter, filler, wmask = P.Matter(), P.NavyFill(), P.wall_mask()
    n = 0
    for t, fr in frames(a - WARM, (b - a) + WARM + 0.2):
        img, _ = P.process_frame(fr, transform_at(t), matter, filler, wmask)
        if t < a - 0.5 / FPS:          # прогрев рекуррентной маски
            continue
        img = cv2.resize(img, (1080, 1920), interpolation=cv2.INTER_AREA)
        for ch in range(3):
            img[..., ch] = LUT8[ch][img[..., ch]]
        enc.stdin.write(img.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    print(f"{tag}: {n} кадров ({a:.2f}–{b:.2f} с бокового дубля) → {out}", flush=True)


if __name__ == "__main__":
    for tag in sys.argv[1:] or ["patients", "realize"]:
        render(tag)
