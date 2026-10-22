"""Фронтальная камера (новая съёмка): HDR→SDR и картина сердца на стене.

1. HLG (BT.2020, 10 бит) → SDR BT.709 тонмаппингом Hable, 1080×1920, 30 fps.
2. Картина «вешается» на стену справа вверху — там же, где на референсе
   (x 680–1005, y 102–547), в натуральную величину, без масштабирования.
   Камера на штативе, но положение всё равно отслеживается покадрово по предметам
   на столе, поэтому картина не «плывёт» даже на долю пикселя.
3. Реализм: баланс белого под сцену, перепад освещения стены, мягкая тень рамки,
   перенос реального шума камеры на картину.

Человек в зону картины за весь ролик не заходит (проверено), поэтому маска не нужна.
"""
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.dirname(ROOT)
SRC = os.path.join(PROJECT, "sources", "IMG_3483.mov")
POSTER = os.path.join(PROJECT, "assets", "photos", "heart_poster.png")
W, H, FPS = 1080, 1920, 30
PX, PY = 680, 102           # левый верхний угол рамки в кадре
REF_T = 40.0

TONEMAP = ("zscale=w=1080:h=1920:filter=lanczos:tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:"
           "t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
           "zscale=t=bt709:dither=error_diffusion,format=gbrp,format=rgb24")


def frames(t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(t)] if t is not None else []) + \
          ["-i", SRC, "-vf", f"fps={FPS},{TONEMAP}", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=W * H * 3)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()


def prepare_poster(ref_frame):
    p = cv2.cvtColor(cv2.imread(POSTER), cv2.COLOR_BGR2RGB).astype(np.float32)
    ph, pw = p.shape[:2]
    # баланс белого и яркость под нашу сцену (по халату: сцена чуть теплее референса)
    p *= np.array([1.02, 1.0, 0.97], np.float32) * 0.95
    # перепад освещения стены в этой зоне (справа светлее), смягчённый
    wall = cv2.cvtColor(ref_frame[PY:PY + ph, PX:PX + pw], cv2.COLOR_RGB2GRAY).astype(np.float32)
    light = cv2.GaussianBlur(wall, (0, 0), 60)
    p *= (1 + 0.6 * (light / light.mean() - 1))[..., None]
    # слой картины с полями под тень, альфа — прямоугольник рамки
    pad = 40
    layer = np.zeros((ph + 2 * pad, pw + 2 * pad, 3), np.float32)
    alpha = np.zeros((ph + 2 * pad, pw + 2 * pad), np.float32)
    layer[pad:pad + ph, pad:pad + pw] = p
    alpha[pad:pad + ph, pad:pad + pw] = 1
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0.6)                      # край без «лесенки»
    shadow = np.zeros_like(alpha)
    shadow[pad + 9:pad + ph + 9, pad + 5:pad + pw + 5] = 1           # свет сверху-слева
    shadow = cv2.GaussianBlur(shadow, (0, 0), 8) * 0.5
    return layer, alpha, shadow, pad


def track_setup(ref_frame):
    g = cv2.cvtColor(ref_frame, cv2.COLOR_RGB2GRAY)
    m = np.zeros_like(g)
    m[1300:1700, 0:560] = 255
    m[1380:1500, :] = 255
    pts = cv2.goodFeaturesToTrack(g, 300, 0.01, 10, mask=m)
    return g, pts


def offset(ref_g, pts, frame):
    g = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    p1, st, _ = cv2.calcOpticalFlowPyrLK(ref_g, g, pts, None, winSize=(31, 31), maxLevel=3)
    ok = st[:, 0] == 1
    A, _ = cv2.estimateAffinePartial2D(pts[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=1.0)
    return A


def composite(frame, A, layer, alpha, shadow, pad):
    lh, lw = alpha.shape
    o = np.array([PX - pad, PY - pad], np.float64)
    x0, y0, x1, y1 = PX - pad - 4, PY - pad - 4, PX - pad + lw + 4, PY - pad + lh + 4
    # слой (в координатах опорного кадра) → текущий кадр: A ∘ сдвиг на o; рисуем только в окне
    M = np.hstack([A[:, :2], (A[:, :2] @ o + A[:, 2] - [x0, y0])[:, None]])
    warp = lambda img: cv2.warpAffine(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_CUBIC,  # noqa: E731
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    f = frame[y0:y1, x0:x1].astype(np.float32)
    lay = warp(layer)
    a = warp(alpha)[..., None]
    sh = warp(shadow)[..., None]
    grain = f - cv2.GaussianBlur(f, (0, 0), 2.5)                       # шум этого кадра
    out = f * (1 - sh)
    out = out * (1 - a) + (lay + 1.2 * grain) * a
    frame[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)
    return frame


def main():
    ref = next(frames(REF_T))
    layer, alpha, shadow, pad = prepare_poster(ref)
    ref_g, pts = track_setup(ref)
    if len(sys.argv) > 1:                                               # быстрый просмотр
        for t in map(float, sys.argv[1:]):
            fr = next(frames(t))
            out = composite(fr, offset(ref_g, pts, fr), layer, alpha, shadow, pad)
            cv2.imwrite(os.path.join(ROOT, "build", f"still_{t:05.1f}.png"), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        return
    tmp = os.path.join(ROOT, "build", "video_noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-tune", "film",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            tmp], stdin=subprocess.PIPE)
    for i, fr in enumerate(frames()):
        enc.stdin.write(composite(fr, offset(ref_g, pts, fr), layer, alpha, shadow, pad).tobytes())
        if i % 300 == 0:
            print(f"кадр {i} ({i / FPS:.0f} с)", flush=True)
    enc.stdin.close()
    enc.wait()
    out = os.path.join(ROOT, "output", "front_2_poster_1080x1920.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", SRC, "-map", "0:v", "-map", "1:a:0",
                    "-c", "copy", "-shortest", "-movflags", "+faststart", out], check=True)
    print("готово:", out)


if __name__ == "__main__":
    main()
