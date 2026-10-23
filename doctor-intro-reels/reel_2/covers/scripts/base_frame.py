"""Чистый кадр для обложки прямо из 4K-исходника (как в ролике: тонмаппинг, картина, цвет).

Ищется самый резкий кадр позы с поднятым пальцем (≈99,6–99,8 с исходника), без ника на фоне.
Сохраняются: 4K-кадр и фоны обложек 1080×1920 трёх крупностей (1,00 / 1,15 / 1,30), PNG без сжатия.
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REEL = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REEL, "scripts"))
from assemble import FPS, FRONT_LUT, Poster, front_pipe, zoom_crop  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "base")
T0, T1 = 99.58, 99.86

ref = front_pipe(40.0, 0.05).get(0)
poster = Poster(ref)
pipe = front_pipe(T0, T1 - T0)
best = None
j = 0
while True:
    fr = pipe.get(j)
    if pipe.j < j:
        break
    face = cv2.cvtColor(fr[1500:2900, 500:1700], cv2.COLOR_RGB2GRAY)      # лицо и поднятая рука
    sharp = cv2.Laplacian(face, cv2.CV_64F).var()
    t = (pipe.k0 + j) / FPS
    print(f"t={t:.3f} резкость {sharp:.1f}")
    if best is None or sharp > best[0]:
        best = (sharp, t, fr.copy())
    j += 1
pipe.close()
sharp, t, fr = best
print(f"выбран кадр t={t:.3f} с")
full = poster.composite(fr, dof=0.0)
cv2.imwrite(os.path.join(OUT, "frame_4k.png"), cv2.cvtColor(cv2.LUT(full, FRONT_LUT), cv2.COLOR_RGB2BGR))
cv2.imwrite(os.path.join(OUT, "frame_1080_z1.00.png"), cv2.cvtColor(zoom_crop(full, 1.0, False), cv2.COLOR_RGB2BGR))
for z in (1.15, 1.3):
    img = zoom_crop(poster.composite(fr, dof=(z - 1) * 5.0), z, False)
    cv2.imwrite(os.path.join(OUT, f"frame_1080_z{z:.2f}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
