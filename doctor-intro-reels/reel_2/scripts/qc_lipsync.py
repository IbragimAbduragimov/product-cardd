"""Проверка синхрона губ на боковых планах: «открытость рта» в кадре против громкости голоса.

Для каждой боковой фразы сравниваются три варианта:
  эталон      — боковое видео с его собственным звуком (естественный синхрон);
  без подгонки — боковое видео 1:1 под звук фронтального дубля;
  с подгонкой  — кадры по карте retime (как в ролике) под звук фронта.
Печатается сдвиг (мс), при котором совпадение максимально, и коэффициент корреляции.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
from assemble import SIDE_MKV_START, side_time  # noqa: E402

YUNET = "/tmp/claude-0/-home-user-product-cardd/382abc70-8892-52f3-853b-5bc8f0827c50/scratchpad/models/yunet.onnx"
SR, FPS30, OUT_FPS = 16000, 30000 / 1001, 60000 / 1001
PAIRS = {"patients": ((20.24, 26.35), (16.33, 22.95)), "realize": ((45.30, 52.46), (40.62, 48.31))}


def frames(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 1920, 1080)


def audio(path, pan):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-af", pan, "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def envelope(x, t):
    """Громкость (дБ) в окне 40 мс вокруг моментов t."""
    out = []
    for tt in t:
        a, b = int((tt - 0.02) * SR), int((tt + 0.02) * SR)
        seg = x[max(a, 0):max(b, 1)]
        out.append(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-6))
    return np.array(out)


def mouth_signal(fr):
    """Энергия движения губ по кадрам: рот находится заново в каждом кадре (голова движется)."""
    det = cv2.FaceDetectorYN.create(YUNET, "", (1080, 1920), 0.5, 0.3, 5000)
    patches, last = [], None
    for g in fr:
        _, faces = det.detect(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
        if faces is not None and len(faces):
            last = faces[0]
        f = last
        mx, my = (f[10] + f[12]) / 2, (f[11] + f[13]) / 2
        mw = max(abs(f[12] - f[10]), 40)
        x0, x1 = int(mx - 0.8 * mw), int(mx + 0.8 * mw)
        y0, y1 = int(my - 0.5 * mw), int(my + 0.7 * mw)
        p = cv2.resize(g[y0:y1, x0:x1], (64, 48), interpolation=cv2.INTER_AREA).astype(np.float32)
        patches.append((p - p.mean()) / (p.std() + 1e-6))
    P = np.array(patches)
    m = np.zeros(len(P))
    m[1:] = np.abs(np.diff(P, axis=0)).mean((1, 2))
    return m


def best_lag(sig, env, step):
    sig = (sig - sig.mean()) / (sig.std() + 1e-9)
    env = (env - env.mean()) / (env.std() + 1e-9)
    lags = range(-int(0.3 / step), int(0.3 / step) + 1)
    vals = []
    for L in lags:
        a = sig[max(0, L):len(sig) + min(0, L)]
        b = env[max(0, -L):len(env) + min(0, -L)]
        vals.append(np.corrcoef(a, b)[0, 1])
    k = int(np.nanargmax(vals))
    return list(lags)[k] * step * 1000, vals[k]


def main():
    front = audio(os.path.join(PROJECT, "sources", "IMG_3483.mov"), "pan=mono|c0=c0")
    side = audio(os.path.join(PROJECT, "sources", "IMG_7785.mov"), "pan=mono|c0=0.5*c0+0.5*c1")
    for tag, ((f0, f1), (s0, s1)) in PAIRS.items():
        fr = frames(os.path.join(ROOT, "build", f"side_{tag}.mkv"))
        m = mouth_signal(fr)
        tk = SIDE_MKV_START[tag] + np.arange(len(fr)) / FPS30
        k_of = lambda st: np.interp(st, tk, m)  # noqa: E731
        # эталон: кадры бока со своим звуком
        ts = SIDE_MKV_START[tag] + np.arange(len(fr)) / FPS30
        sel = (ts >= s0) & (ts <= s1)
        lag, r = best_lag(m[sel], np.abs(np.gradient(envelope(side, ts[sel]))), 1 / FPS30)
        print(f"{tag}: эталон (бок со своим звуком):     сдвиг {lag:+5.0f} мс, r={r:.2f}")
        # под звук фронта: время выхода с шагом 59,94 кадра/с
        tf = np.arange(f0, f1, 1 / OUT_FPS)
        env_f = np.abs(np.gradient(envelope(front, tf)))
        lin = s0 + (tf - f0)                                       # без подгонки (1:1 от начала фразы)
        lag, r = best_lag(k_of(lin), env_f, 1 / OUT_FPS)
        print(f"{tag}: без подгонки (1:1):                сдвиг {lag:+5.0f} мс, r={r:.2f}")
        rt = np.array([side_time(tag, x) for x in tf])
        lag, r = best_lag(k_of(rt), env_f, 1 / OUT_FPS)
        print(f"{tag}: с подгонкой (как в ролике):        сдвиг {lag:+5.0f} мс, r={r:.2f}")


if __name__ == "__main__":
    main()
