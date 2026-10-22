"""Проход 1: трекинг камеры по неподвижному фону (стена + декоративная планка).

Для каждого кадра (30 fps CFR) находит преобразование подобия «текущий → опорный»
кадр (t=15 с). Трекинг на половинном разрешении, точки — только на фоне слева.
"""
import subprocess
import sys

import cv2
import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
W, H = 1080, 1920          # половина от 2160×3840
REF_T = 15.0

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps=30,scale={W}:{H}:flags=area,format=gray",
                         "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
frames = []
while True:
    b = proc.stdout.read(W * H)
    if len(b) < W * H:
        break
    frames.append(np.frombuffer(b, np.uint8).reshape(H, W))
ref_i = int(REF_T * 30)
ref = frames[ref_i]

# маска фона: стена/планка левее x≈430 и выше столешницы, без зоны рукава
mask = np.zeros_like(ref)
mask[20:930, 10:440] = 255
mask[0:560, 440:1060] = 255      # верх синего фона над головой (там мало деталей, но есть край)
pts = cv2.goodFeaturesToTrack(ref, 600, 0.005, 12, mask=mask, blockSize=9)
print("точек на опорном кадре:", len(pts))

lk = dict(winSize=(41, 41), maxLevel=5, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.003))
res = []
for i, fr in enumerate(frames):
    p1, st, err = cv2.calcOpticalFlowPyrLK(ref, fr, pts, None, **lk)
    p0b, st2, _ = cv2.calcOpticalFlowPyrLK(fr, ref, p1, None, **lk)     # проверка «туда-обратно»
    good = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(p0b - pts, axis=2)[:, 0] < 0.5)
    A, inl = cv2.estimateAffinePartial2D(p1[good], pts[good], method=cv2.RANSAC,
                                         ransacReprojThreshold=1.0, maxIters=4000, refineIters=50)
    rot = np.degrees(np.arctan2(A[1, 0], A[0, 0]))
    scale = np.hypot(A[0, 0], A[1, 0])
    res.append([A[0, 0], A[0, 1], A[0, 2] * 2, A[1, 0], A[1, 1], A[1, 2] * 2])   # сдвиг в пикселях 4K
    if i % 60 == 0:
        print(f"t={i/30:5.1f}s  dx={A[0,2]*2:+7.1f} dy={A[1,2]*2:+7.1f} rot={rot:+.3f}° scale={scale:.4f} "
              f"inliers={int(inl.sum())}/{good.sum()}")
np.save(OUT, np.array(res))
print("кадров:", len(res))
