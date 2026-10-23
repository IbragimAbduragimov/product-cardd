"""Основа обложки прямо из скриншота заказчика (без поиска кадра в видео).

1. Из скриншота телефона вырезается кадр ролика (чёрные поля сверху и снизу), 1080×1920.
2. Ник «abduragimov_cvs» убирается со стены: буквы закрашиваются по окружающей стене,
   поверх кладётся зерно, взятое с чистого участка той же стены, — заплатка не видна.
3. Крупность 1,15× — то же окно кадрирования, что у планов ролика (zoom_crop): участок
   увеличивается нейросетью EDSR ×2 и уменьшается до 1080×1920, без мыла от растяжения.
4. Маска фигуры (RVM) — для проверки раскладки текста и вариантов «текст за спиной».

python3 scripts/base_from_screenshot.py reference/screenshot_cover_frame3.jpg --out base3
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.dirname(HERE)
REEL = os.path.dirname(COVERS)
sys.path.insert(0, os.path.join(REEL, "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(REEL), "side_angle_2", "scripts"))
from assemble import EYES_FRAC, EYES_Y4, FACE_X4, SH, SW  # noqa: E402
import process as P  # noqa: E402  (Matter: RVM + guided filter)

EDSR = os.environ.get("EDSR_MODEL", "/tmp/claude-0/-home-user-product-cardd/382abc70-8892-52f3-853b-5bc8f0827c50"
                                    "/scratchpad/models/EDSR_x2.pb")
NICK_BOX = (120, 330, 40, 640)            # y0, y1, x0, x1 — где на кадре стоит ник
WALL_PATCH = (330, 470, 60, 600)          # чистая стена под ником: образец зерна

ap = argparse.ArgumentParser()
ap.add_argument("screenshot")
ap.add_argument("--out", default="base3")
ap.add_argument("--clean-only", action="store_true", help="только убрать ник (без 1,15× и маски)")
args = ap.parse_args()
OUT = os.path.join(COVERS, args.out)
os.makedirs(OUT, exist_ok=True)

# 1. кадр без чёрных полей
shot = cv2.imread(args.screenshot)
rows = np.where(shot.mean((1, 2)) > 8)[0]
cols = np.where(shot.mean((0, 2)) > 8)[0]
frame = shot[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
if frame.shape[:2] != (1920, 1080):
    frame = cv2.resize(frame, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
print("кадр со скриншота:", frame.shape[1], "×", frame.shape[0])

# 2. ник: светлые буквы на тёмной стене → маска → заливка по стене + зерно стены
y0, y1, x0, x1 = NICK_BOX
reg = frame[y0:y1, x0:x1]
lum = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY).astype(np.float32)
wall = np.median(lum)
mask = np.zeros(frame.shape[:2], np.uint8)
mask[y0:y1, x0:x1] = (lum > wall + 22).astype(np.uint8) * 255
# с запасом: у светлых букв после сжатия видео тёмный ореол — он тоже уходит под заливку
mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (23, 23)))
ys, xs = np.where(mask > 0)
print(f"ник: x {xs.min()}–{xs.max()}, y {ys.min()}–{ys.max()}, {int((mask > 0).sum())} пикс. под заливку")
# стена под буквами — гладкий фон по окрестности (нормированная свёртка без пикселей маски)
keep = (mask == 0).astype(np.float32)
fill = cv2.GaussianBlur(frame.astype(np.float32) * keep[..., None], (0, 0), 28)
fill /= np.maximum(cv2.GaussianBlur(keep, (0, 0), 28), 1e-3)[..., None]
smooth = fill
py0, py1, px0, px1 = WALL_PATCH
patch = frame[py0:py1, px0:px1].astype(np.float32)
grain = patch - cv2.GaussianBlur(patch, (0, 0), 3)               # зерно чистой стены
gh, gw = grain.shape[:2]
reps = (int(np.ceil(1920 / gh)), int(np.ceil(1080 / gw)), 1)
grain_full = np.tile(grain, reps)[:1920, :1080]
soft = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), 3)[..., None]
clean = frame.astype(np.float32) * (1 - soft) + (smooth + grain_full) * soft
clean = np.clip(np.round(clean), 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(OUT, "frame_1080_z1.00.png"), clean)
if args.clean_only:
    sys.exit(0)

# 3. крупность 1,15× — окно как у zoom_crop, увеличение EDSR ×2 и точное уменьшение
z = 1.15
cw, ch = SW / z, SH / z
cx0 = min(max(FACE_X4 - cw / 2, 0), SW - cw) / 2                   # в координатах 1080×1920
cy0 = min(max(EYES_Y4 - EYES_FRAC * ch, 0), SH - ch) / 2
cw, ch = cw / 2, ch / 2
bx0, by0 = int(cx0) - 8, int(cy0) - 8
bx1, by1 = min(int(cx0 + cw) + 9, 1080), min(int(cy0 + ch) + 9, 1920)
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(EDSR)
sr.setModel("edsr", 2)
big = sr.upsample(clean[by0:by1, bx0:bx1])
gx, gy = round((cx0 - bx0) * 2), round((cy0 - by0) * 2)
zoomed = cv2.resize(big[gy:gy + round(ch * 2), gx:gx + round(cw * 2)], (1080, 1920), interpolation=cv2.INTER_AREA)
cv2.imwrite(os.path.join(OUT, "frame_1080_z1.15.png"), zoomed)
print(f"1,15×: окно x {cx0:.1f}, y {cy0:.1f}, {cw:.1f}×{ch:.1f} → EDSR ×2 → 1080×1920")

# 4. маска фигуры: RVM несколько раз по одному кадру (рекуррентное состояние успевает сойтись)
for name, img in (("1.00", clean), ("1.15", zoomed)):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    matter = P.Matter()
    for _ in range(6):
        _, a = matter(rgb)
    a8 = np.clip(P.refine_alpha(rgb, a) * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(OUT, f"alpha_z{name}.png"), a8)
    cv2.imwrite(os.path.join(OUT, f"person_z{name}.png"), np.dstack([img, a8]))
json.dump({"source": os.path.basename(args.screenshot), "how": "кадр взят из скриншота, ник убран, 1,15× через EDSR ×2"},
          open(os.path.join(OUT, "frame.json"), "w"), ensure_ascii=False)
print("готово:", OUT)
