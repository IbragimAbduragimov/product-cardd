"""Синхронизация бокового видео со звуком фронтального дубля (единый голос во всём ролике).

Боковое видео — отдельный дубль: те же фразы произнесены в чуть другом темпе. Чтобы звук
при смене ракурса не менялся, на боковых планах звучит фронтальный дубль, а кадры бокового
видео выбираются по карте времени «фронт → бок», найденной DTW-выравниванием речи
(MFCC с нормализацией под каждый микрофон). Карта сглаживается и проверяется по пословной
разметке распознавания обоих дублей.
Результат: build/retime_<фраза>.json — пары (время фронта, время бока) с шагом 10 мс.
"""
import difflib
import json
import os
import subprocess

import numpy as np
from scipy.fft import dct
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.dirname(ROOT)
SR = 16000
HOP = 160                       # 10 мс

# фраза: (речь во фронтальном дубле, речь в боковом дубле)
PAIRS = {"patients": ((20.24, 28.40), (16.33, 23.70)),
         "realize": ((45.30, 52.46), (40.62, 48.31))}
PAD = 0.15


def load(path, pan):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-af", pan, "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def mel_bank(n_fft=512, n_mels=40, fmin=60, fmax=7600):
    mel = lambda f: 2595 * np.log10(1 + f / 700)  # noqa: E731
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)  # noqa: E731
    pts = imel(np.linspace(mel(fmin), mel(fmax), n_mels + 2))
    bins = np.floor((n_fft + 1) * pts / SR).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        a, b, c = bins[m - 1], bins[m], bins[m + 1]
        fb[m - 1, a:b] = (np.arange(a, b) - a) / max(b - a, 1)
        fb[m - 1, b:c] = (c - np.arange(b, c)) / max(c - b, 1)
    return fb


FB = mel_bank()


def mfcc(x):
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])
    n = 1 + (len(x) - 400) // HOP
    idx = np.arange(400)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[idx] * np.hamming(400)
    spec = np.abs(np.fft.rfft(frames, 512)) ** 2
    logmel = np.log(spec @ FB.T + 1e-10)
    c = dct(logmel, type=2, axis=1, norm="ortho")[:, :13]
    d = np.gradient(c, axis=0)
    f = np.hstack([c, d])
    return (f - f.mean(0)) / (f.std(0) + 1e-9)          # нормализация под микрофон (CMVN)


def dtw(A, B, band=0.18):
    n, m = len(A), len(B)
    C = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(-1))
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    w = int(band * max(n, m)) + abs(n - m)
    for i in range(1, n + 1):
        jc = int(i * m / n)
        lo, hi = max(1, jc - w), min(m, jc + w)
        prev, cur = D[i - 1], D[i]
        for j in range(lo, hi + 1):
            cur[j] = C[i - 1, j - 1] + min(prev[j - 1], prev[j], cur[j - 1])
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]])
        i, j = (i - 1, j - 1) if k == 0 else (i - 1, j) if k == 1 else (i, j - 1)
    return np.array(path[::-1])


def words(name):
    return json.load(open(os.path.join(ROOT, "build", f"words_{name}.json")))


def main():
    front = load(os.path.join(PROJECT, "sources", "IMG_3483.mov"), "pan=mono|c0=c0")
    side = load(os.path.join(PROJECT, "sources", "IMG_7785.mov"), "pan=mono|c0=0.5*c0+0.5*c1")
    for tag, ((f0, f1), (s0, s1)) in PAIRS.items():
        fa, sa = f0 - PAD, s0 - PAD
        A = mfcc(front[int(fa * SR):int((f1 + PAD) * SR)])
        B = mfcc(side[int(sa * SR):int((s1 + PAD) * SR)])
        path = dtw(A, B)
        # карта «кадр фронта → время бока»: среднее по пути, сглаживание, монотонность
        n = len(A)
        sm = np.zeros(n)
        cnt = np.zeros(n)
        np.add.at(sm, path[:, 0], path[:, 1])
        np.add.at(cnt, path[:, 0], 1)
        sj = sm / np.maximum(cnt, 1)
        sj = gaussian_filter1d(sj, 4)
        sj = np.maximum.accumulate(sj)
        ft = fa + np.arange(n) * HOP / SR
        st = sa + sj * HOP / SR
        # проверка по пословной разметке обоих дублей
        fw = [w for w in words("IMG_3483") if f0 - 0.1 <= w["s"] <= f1]
        sw = [w for w in words("IMG_7785") if s0 - 0.1 <= w["s"] <= s1]
        sm_ = difflib.SequenceMatcher(a=[w["w"][:5] for w in fw], b=[w["w"][:5] for w in sw], autojunk=False)
        res = []
        for blk in sm_.get_matching_blocks():
            for k in range(blk.size):
                a, b = fw[blk.a + k], sw[blk.b + k]
                res.append(np.interp(a["s"], ft, st) - b["s"])
        res = np.array(res) * 1000
        slope = np.diff(st) / np.diff(ft)
        print(f"{tag}: {len(fw)} слов фронт / {len(sw)} бок; расхождение с разметкой слов: "
              f"медиана {np.median(np.abs(res)):.0f} мс, макс {np.abs(res).max():.0f} мс; "
              f"скорость бока относительно фронта: {np.percentile(slope, 5):.2f}–{np.percentile(slope, 95):.2f}")
        json.dump(dict(front=ft.round(4).tolist(), side=st.round(4).tolist()),
                  open(os.path.join(ROOT, "build", f"retime_{tag}.json"), "w"))


if __name__ == "__main__":
    main()
