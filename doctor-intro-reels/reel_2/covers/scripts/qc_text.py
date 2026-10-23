"""Проверка раскладки текста обложек по замерам scripts/measure_text.js.

Для каждого варианта: границы текста, попадание в сетку профиля (центр 3:4, y 240–1680),
зазор до картины, зазор до фигуры (текст перед ней) или доля текста, скрытая фигурой (текст за ней).
python3 scripts/qc_text.py <папка с замерами> [номера]
"""
import glob
import os
import re
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZOOM = {"a": "1.00", "b": "1.15", "c": "1.30"}
NAVY = np.array([38, 42, 72])

html = open(os.path.join(ROOT, "cover.html"), encoding="utf-8").read()
zoom_of = {int(n): ZOOM[z] for n, z in re.findall(r'\n  (\d+): \{ z: "([abc])"', html)}

maps = {}
for z in set(zoom_of.values()):
    fr = np.asarray(Image.open(os.path.join(ROOT, "base", f"frame_1080_z{z}.png")).convert("RGB")).astype(int)
    person = np.asarray(Image.open(os.path.join(ROOT, "base", f"alpha_z{z}.png"))) > 128
    poster = (np.abs(fr - NAVY).sum(2) > 90) & ~person
    poster[900:] = False
    poster[:, :540] = False
    maps[z] = (person, distance_transform_edt(~person), distance_transform_edt(~poster))

folder = sys.argv[1]
only = [int(x) for x in sys.argv[2:]]
for path in sorted(glob.glob(os.path.join(folder, "text_*_*.png"))):
    n, layer = re.match(r"text_(\d+)_(\w+)\.png", os.path.basename(path)).groups()
    n = int(n)
    if only and n not in only:
        continue
    ink = np.asarray(Image.open(path))[..., 3] > 96
    if not ink.any():
        continue
    person, d_person, d_poster = maps[zoom_of[n]]
    ys, xs = np.where(ink)
    line = f"№{n:2d} {layer:6s} x {xs.min():4d}–{xs.max():4d}  y {ys.min():4d}–{ys.max():4d}"
    line += f" | до картины {d_poster[ink].min():5.0f}"
    if layer == "front":
        line += f" | до фигуры {d_person[ink].min():4.0f}"
    else:
        line += f" | скрыто фигурой {100 * (ink & person).sum() / ink.sum():4.1f} %"
    grid_ok = ys.min() >= 262 and ys.max() <= 1500 and xs.min() >= 40 and xs.max() <= 1040
    print(line + ("" if grid_ok else "  ⚠ вне безопасной зоны"))
