"""Чистый кадр для обложки прямо из 4K-исходника (как в ролике: тонмаппинг, картина, цвет).

Без --ref берётся самый резкий кадр отрезка (так сделана основа base/: 99,58–99,86 с).
С --ref кадр выбирается по скриншоту заказчика: из отрезка берётся кадр, у которого лицо и рука
совпадают со скриншотом (сравниваются контуры, поэтому цвет экрана телефона и ник на кадре не мешают).
Сохраняются: 4K-кадр, фоны обложек 1080×1920 трёх крупностей (1,00 / 1,15 / 1,30) и frame.json.

python3 scripts/base_frame.py                                       # → base/
python3 scripts/base_frame.py --ref screenshot.jpg --out base2 --from 99.55 --to 99.90
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(COVERS), "scripts"))
from assemble import FPS, FRONT_LUT, Poster, front_pipe, zoom_crop  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--ref", help="скриншот с нужным кадром (поиск по совпадению вместо резкости)")
ap.add_argument("--out", default="base")
ap.add_argument("--from", dest="t0", type=float, default=99.58)
ap.add_argument("--to", dest="t1", type=float, default=99.86)
args = ap.parse_args()
OUT = os.path.join(COVERS, args.out)
os.makedirs(OUT, exist_ok=True)

FACE_HAND = (640, 1320, 140, 920)          # y0, y1, x0, x1 в кадре 1080×1920: лицо и поднятая рука


def contours(gray):
    y0, y1, x0, x1 = FACE_HAND
    g = gray.astype(np.float32)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))[y0:y1, x0:x1]
    return (m - m.mean()) / (m.std() + 1e-6)


if args.ref:
    shot = cv2.cvtColor(cv2.imread(args.ref), cv2.COLOR_BGR2GRAY)
    rows = np.where(shot.mean(1) > 8)[0]                       # убрать чёрные поля скриншота
    shot = cv2.resize(shot[rows.min():rows.max() + 1], (1080, 1920), interpolation=cv2.INTER_AREA)
    target = contours(shot)


def score(fr):
    if args.ref:                                                # меньше — лучше
        small = cv2.LUT(cv2.resize(fr, (1080, 1920), interpolation=cv2.INTER_AREA), FRONT_LUT)
        return float(((contours(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)) - target) ** 2).mean())
    face = cv2.cvtColor(fr[1500:2900, 500:1700], cv2.COLOR_RGB2GRAY)      # лицо и поднятая рука
    return -cv2.Laplacian(face, cv2.CV_64F).var()


ref = front_pipe(40.0, 0.05).get(0)
poster = Poster(ref)
pipe = front_pipe(args.t0, args.t1 - args.t0)
best = None
j = 0
while True:
    fr = pipe.get(j)
    if pipe.j < j:
        break
    t = (pipe.k0 + j) / FPS
    s = score(fr)
    print(f"t={t:.3f} {'расхождение со скриншотом' if args.ref else 'резкость'} {abs(s):.4f}")
    if best is None or s < best[0]:
        best = (s, t, fr.copy())
    j += 1
pipe.close()
s, t, fr = best
print(f"выбран кадр t={t:.3f} с")
json.dump({"t": round(t, 4), "how": f"совпадение со скриншотом {os.path.basename(args.ref)}" if args.ref
           else f"самый резкий кадр {args.t0}–{args.t1} с"}, open(os.path.join(OUT, "frame.json"), "w"),
          ensure_ascii=False)
full = poster.composite(fr, dof=0.0)
cv2.imwrite(os.path.join(OUT, "frame_4k.png"), cv2.cvtColor(cv2.LUT(full, FRONT_LUT), cv2.COLOR_RGB2BGR))
cv2.imwrite(os.path.join(OUT, "frame_1080_z1.00.png"), cv2.cvtColor(zoom_crop(full, 1.0, False), cv2.COLOR_RGB2BGR))
for z in (1.15, 1.3):
    img = zoom_crop(poster.composite(fr, dof=(z - 1) * 5.0), z, False)
    cv2.imwrite(os.path.join(OUT, f"frame_1080_z{z:.2f}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
