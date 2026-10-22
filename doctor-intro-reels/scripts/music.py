"""Синтез сдержанного фонового трека и деликатных звуковых акцентов.

Dm – B♭ – F – C, 70 BPM: тёплый пэд, редкое «фортепианное» арпеджио, мягкий бас,
лёгкая реверберация. Ничего яркого — музыка должна сидеть глубоко под голосом.
"""
import sys
import wave

import numpy as np
from scipy.signal import fftconvolve

sys.path.insert(0, __import__("os").path.dirname(__file__))
from timeline import ROOT, TOTAL, MAIN_END  # noqa: E402

SR = 48000
BPM = 70
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


N = int((TOTAL + 0.5) * SR)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(sig)] += sig * np.sqrt(0.5 * (1 + pan))


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def pad_note(m, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for cents in (-5, 0, 6):
        f = hz(m) * 2 ** (cents / 1200)
        ph = rng.uniform(0, 2 * np.pi)
        s += np.sin(2 * np.pi * f * t + ph) + 0.22 * np.sin(4 * np.pi * f * t + ph) \
            + 0.06 * np.sin(6 * np.pi * f * t + ph)
    s *= 1 + 0.08 * np.sin(2 * np.pi * 0.17 * t + rng.uniform(0, 6))
    return s * env_adsr(len(t), 1.8, 2.2) / 3


def piano_note(m, dur=3.2):
    t = np.arange(int(dur * SR)) / SR
    f = hz(m)
    s = np.zeros_like(t)
    for k in range(1, 7):
        s += np.sin(2 * np.pi * f * k * 1.0007 ** (k - 1) * t) / k ** 1.6 * np.exp(-t * (0.9 + 0.7 * k))
    att = np.minimum(1, t / 0.006)
    return s * att


def bass_note(m, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * hz(m) * t) + 0.15 * np.sin(4 * np.pi * hz(m) * t)
    return s * env_adsr(len(t), 0.6, 1.2)


def low_hit(dur=2.5):
    """Мягкий низкий удар (как отдалённый удар сердца), без щелчка."""
    t = np.arange(int(dur * SR)) / SR
    f = 52 + 30 * np.exp(-t * 14)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    return s * np.minimum(1, t / 0.004)


def swell(dur=1.6):
    """Тихий нарастающий «воздух» перед акцентом."""
    n = int(dur * SR)
    noise = rng.standard_normal(n + 4000)
    k = np.hanning(220)
    noise = fftconvolve(noise, k / k.sum(), mode="same")[:n]
    e = np.linspace(0, 1, n) ** 2.6
    e[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))
    return noise * e


# Аккорды: (бас, голоса пэда, тоны арпеджио)
CHORDS = [
    (38, [50, 53, 57, 62], [62, 65, 69, 72, 74]),      # Dm
    (34, [50, 53, 58, 62], [62, 65, 70, 74, 77]),      # B♭
    (41, [48, 53, 57, 60], [60, 65, 69, 72, 77]),      # F
    (36, [48, 52, 55, 60], [60, 64, 67, 72, 76]),      # C
]
CHORD_LEN = 2 * BAR

t, k = 0.0, 0
end_music = MAIN_END + 0.2
while t < end_music:
    bass, pad, arp = CHORDS[k % 4]
    dur = min(CHORD_LEN, end_music - t) + 2.2
    for m in pad:
        add(pad_note(m, dur), t, pan=rng.uniform(-0.5, 0.5), gain=0.16)
    if t >= 9.0:                                   # бас вступает после представления
        add(bass_note(bass, dur), t, gain=0.20)
    if t >= 14.0:                                  # редкое арпеджио
        pattern = [0, 2, 3, 1, 4, 2, 3, 1] if t < 100 else [0, 3, 1, 4]
        step = CHORD_LEN / len(pattern)
        for j, idx in enumerate(pattern):
            add(piano_note(arp[idx]), t + j * step, pan=-0.35 + 0.7 * (idx / 4),
                gain=0.10 if 60 < t < 100 else 0.075)
    t += CHORD_LEN
    k += 1

# Финальный аккорд D-moll(add9) → мягкое затухание на плашке
for m in (50, 57, 62, 64, 69):
    add(pad_note(m, 4.2), MAIN_END - 0.4, pan=rng.uniform(-0.4, 0.4), gain=0.15)
add(piano_note(74, 4.0), MAIN_END - 0.1, gain=0.10)

# Деликатные акценты
add(low_hit(), 0.0, gain=0.55)
add(swell(1.3), 46.45 - 1.3, gain=0.05)
add(low_hit(), 46.45, gain=0.35)
add(swell(1.0), MAIN_END - 1.0, gain=0.04)
add(low_hit(), MAIN_END, gain=0.40)

# Реверберация (синтетический хвост 3 с, разный для каналов)
ir_t = np.arange(int(3.0 * SR)) / SR
irs = [rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.75) for _ in range(2)]
for ir in irs:
    ir[: int(0.012 * SR)] = 0
wetL = fftconvolve(L, irs[0])[:N]
wetR = fftconvolve(R, irs[1])[:N]
wetL *= np.abs(L).max() / (np.abs(wetL).max() + 1e-9)
wetR *= np.abs(R).max() / (np.abs(wetR).max() + 1e-9)
outL, outR = 0.7 * L + 0.45 * wetL, 0.7 * R + 0.45 * wetR

# Общая огибающая: вход, финал
t = np.arange(N) / SR
master = np.clip(t / 1.2, 0, 1) * np.clip((TOTAL + 0.3 - t) / 2.0, 0, 1)
out = np.stack([outL, outR], 1) * master[:, None]
out /= np.abs(out).max() / 0.89

with wave.open(f"{ROOT}/build/music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print("music.wav", N / SR, "s")
