"""Затемнение фона обложки «как в первом ролике» (титр «Краткая биография»): стена почти чёрная
сверху и к краям, картина приглушена, врач и стол — без изменений.

Затемняется только фон: по маске фигуры (RVM) из пикселя вычитается доля стены, поэтому
лицо, волосы и халат сохраняют яркость, а на краях фигуры не появляется ни светлый, ни тёмный
ореол. Ниже задней кромки стола затемнения нет.
Профиль (подобран по замерам образца): стена у головы ×0,56, сверху до ×0,17, к краям до ×0,3,
картина в среднем ×0,3.

python3 scripts/darken.py --base base2 --z 1.15        → base2/frame_1080_z1.15_dark.png
"""
import argparse
import os

import cv2
import numpy as np

COVERS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE, TOP, VIGNETTE = 0.56, 0.70, 0.55
FACE = (540, 760)                        # центр затемнения по краям (лицо врача)

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="base2")
ap.add_argument("--z", default="1.15")
args = ap.parse_args()
d = os.path.join(COVERS, args.base)
C = cv2.imread(os.path.join(d, f"frame_1080_z{args.z}.png")).astype(np.float32)
a = cv2.imread(os.path.join(d, f"alpha_z{args.z}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
H, W = a.shape


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# задняя кромка стола: первая светлая строка под стеной, только там, где нет фигуры
lum = cv2.cvtColor(C.astype(np.uint8), cv2.COLOR_BGR2GRAY)
xs, ys = [], []
for x in range(0, W, 8):
    col = lum[1100:1700, x]
    free = a[1100:1700, x] < 0.05
    hit = np.where((col > 150) & free)[0]
    if len(hit) and free[:hit[0]].all():
        xs.append(x)
        ys.append(1100 + hit[0])
k, b = np.polyfit(xs, ys, 1)
res = np.abs(np.polyval([k, b], xs) - ys)
k, b = np.polyfit(np.array(xs)[res < 6], np.array(ys)[res < 6], 1)            # без выбросов
print(f"кромка стола: y ≈ {b:.0f} + {k:.4f}·x  (по {int((res < 6).sum())} столбцам)")

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
wall = 1 - smoothstep(-6, 6, yy - (k * xx + b))                                # 1 — стена, 0 — стол
top = TOP * np.clip(1 - yy / 800, 0, 1) ** 1.6
r = np.hypot((xx - FACE[0]) / 540, (yy - FACE[1]) / 900)
vig = VIGNETTE * smoothstep(0.55, 1.25, r)
f = 1 - wall * (1 - BASE * (1 - top) * (1 - vig))                              # множитель фона

# цвет стены под краем фигуры — по соседним чистым пикселям фона
bg = (a < 0.05).astype(np.float32)
est = cv2.GaussianBlur(C * bg[..., None], (0, 0), 6) / np.maximum(cv2.GaussianBlur(bg, (0, 0), 6), 1e-3)[..., None]
w = smoothstep(0.02, 0.15, a)[..., None]
B = C * (1 - w) + est * w
out = C - ((1 - a) * (1 - f))[..., None] * B
out = np.clip(np.round(out), 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(d, f"frame_1080_z{args.z}_dark.png"), out)
print("готово:", os.path.join(args.base, f"frame_1080_z{args.z}_dark.png"))
