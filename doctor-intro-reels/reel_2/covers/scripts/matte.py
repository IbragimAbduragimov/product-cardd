"""Маска фигуры врача на кадре обложки (RVM ResNet50) — для текста «за спиной».

Нейросеть прогоняется по полсекунды кадров до выбранного (рекуррентная модель уточняет
края по движению), маска берётся с кадра из <папка>/frame.json (его выбирает base_frame.py).
Для трёх крупностей кадра. Результат — person_z*.png: фон обложки с маской в альфа-канале
(слой поверх текста).

python3 scripts/matte.py [--out base2]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REEL = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REEL, "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(REEL), "side_angle_2", "scripts"))
from assemble import FPS, Poster, front_pipe, zoom_crop  # noqa: E402
import process as P  # noqa: E402  (Matter: RVM + guided filter)

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="base")
OUT = os.path.join(os.path.dirname(HERE), ap.parse_args().out)
T_PICK = json.load(open(os.path.join(OUT, "frame.json")))["t"]
T_START = T_PICK - 0.5

ref = front_pipe(40.0, 0.05).get(0)
poster = Poster(ref)
for z in (1.0, 1.15, 1.3):
    matter = P.Matter()
    pipe = front_pipe(T_START, T_PICK - T_START + 0.05)
    j, alpha = 0, None
    while True:
        fr = pipe.get(j)
        if pipe.j < j:
            break
        t = (pipe.k0 + j) / FPS
        img = zoom_crop(poster.composite(fr, dof=(z - 1) * 5.0), z, False)
        _, a = matter(img)
        if t >= T_PICK - 1e-3:
            alpha = P.refine_alpha(img, a)
            break
        j += 1
    pipe.close()
    a8 = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(OUT, f"alpha_z{z:.2f}.png"), a8)
    bg = cv2.imread(os.path.join(OUT, f"frame_1080_z{z:.2f}.png"))            # из base_frame.py
    cv2.imwrite(os.path.join(OUT, f"person_z{z:.2f}.png"), np.dstack([bg, a8]))
    print(f"z={z}: маска готова (кадр {t:.3f} с)")
