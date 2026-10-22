"""Звук ролика: только голос врача + точечные звуковые акценты. Музыки нет.

1. Шумоподавление каждого дубля по профилю шума из его же пауз (мягкое, ≤12 дБ).
2. Боковой дубль подгоняется к фронтальному: громкость по речи и тембр — FIR-эквалайзер
   с линейной фазой (не сдвигает звук во времени). Тембр фронта остаётся натуральным.
3. Сборка по монтажному листу: равномощностные кроссфейды 40 мс на стыках (всегда в паузах).
4. Общая лёгкая обработка: срез ниже 70 Гц, чуть меньше «бубнения», чуть больше разборчивости,
   мягкая компрессия.
5. Звуковые акценты (синтез): 2 «воздушных» перехода, 4 тихих щелчка, 3 низких удара, финал.
6. Громкость под соцсети: −14 LUFS, пик −1,5 dBTP.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, firwin2, istft, stft, welch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edl import CLIPS, FRONT_SRC, ROOT, SIDE_SRC, TOTAL  # noqa: E402

SR = 48000
BUILD = os.path.join(ROOT, "build")
rng = np.random.default_rng(11)

# паузы для профиля шума (секунды исходника)
NOISE = {"front": [(9.0, 10.1), (44.45, 45.2), (68.15, 69.4), (105.3, 106.2)],
         "side": [(23.75, 24.25), (39.65, 40.45), (15.45, 16.05)]}
# речь для оценки громкости и тембра
SPEECH = {"front": [(10.2, 19.4), (29.0, 32.0), (41.4, 44.4), (90.3, 96.4)],
          "side": [(16.3, 23.7), (40.6, 48.3)]}


def load(src):
    pan = "pan=mono|c0=c0" if src == "front" else "pan=mono|c0=0.5*c0+0.5*c1"
    path = FRONT_SRC if src == "front" else SIDE_SRC
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-af", pan, "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def cut(x, spans):
    return np.concatenate([x[int(a * SR):int(b * SR)] for a, b in spans])


def denoise(x, noise, max_red_db=12.0):
    """Спектральное вычитание с плавным усилением (без «музыкального» шума)."""
    n = 2048
    _, _, X = stft(x, SR, nperseg=n, noverlap=n * 3 // 4)
    _, _, Nn = stft(noise, SR, nperseg=n, noverlap=n * 3 // 4)
    npow = (np.abs(Nn) ** 2).mean(1, keepdims=True)
    p = np.abs(X) ** 2
    g = np.sqrt(np.clip(1 - 1.6 * npow / (p + 1e-20), 0, 1))
    gmin = 10 ** (-max_red_db / 20)
    g = np.maximum(g, gmin)
    # сглаживание по частоте и во времени (атака быстрая, спад медленный)
    g = (np.roll(g, 1, 0) + 2 * g + np.roll(g, -1, 0)) / 4
    for k in range(1, g.shape[1]):
        g[:, k] = np.maximum(g[:, k], 0.7 * g[:, k - 1] + 0.3 * gmin)
    _, y = istft(X * g, SR, nperseg=n, noverlap=n * 3 // 4)
    return y[:len(x)]


def ltas(x):
    f, p = welch(x, SR, nperseg=8192)
    return f, 10 * np.log10(p + 1e-20)


def match_eq(src_speech, ref_speech, max_boost=6.0, max_cut=8.0):
    """FIR (линейная фаза), приводящий тембр src к ref; сглаженный по третям октавы."""
    f, a = ltas(src_speech)
    _, b = ltas(ref_speech)
    diff = b - a
    centers = 1000 * 2 ** (np.arange(-17, 15) / 3)              # ~20 Гц…20 кГц
    vals = []
    for c in centers:
        m = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        vals.append(np.median(diff[m]) if m.any() else 0.0)
    vals = np.array(vals)
    vals -= np.interp(700, centers, vals)                      # уровень — отдельно, здесь только тембр
    vals = np.clip(vals, -max_cut, max_boost)
    vals[centers < 90] = np.minimum(vals[centers < 90], 0)     # низ не поднимаем (гул)
    vals = np.convolve(np.pad(vals, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
    freqs = np.concatenate([[0], centers[centers < SR / 2], [SR / 2]])
    gains = 10 ** (np.concatenate([[vals[0]], vals[centers < SR / 2], [vals[-1]]]) / 20)
    taps = firwin2(4095, freqs / (SR / 2), gains)
    return taps, dict(zip([int(c) for c in centers], np.round(vals, 1)))


def fir(x, taps):
    y = fftconvolve(x, taps)
    d = (len(taps) - 1) // 2
    return y[d:d + len(x)]


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


# ---------- звуковые акценты ----------

def env(n, a, r):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[-nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return e


def bandpass_sweep(noise, f_path):
    """Шум через полосовой фильтр с плавающей центральной частотой (STFT-маска)."""
    n = 1024
    _, _, X = stft(noise, SR, nperseg=n)
    fr = np.linspace(0, SR / 2, X.shape[0])[:, None]
    cf = np.interp(np.linspace(0, 1, X.shape[1]), np.linspace(0, 1, len(f_path)), f_path)[None, :]
    mask = np.exp(-0.5 * (np.log2((fr + 1) / cf) / 0.9) ** 2)
    _, y = istft(X * mask, SR, nperseg=n)
    return y[:len(noise)]


def whoosh(d=0.75):
    n = int(d * SR)
    w = bandpass_sweep(rng.standard_normal(n), [380, 900, 2600, 1500, 700])
    w *= env(n, 0.5 * d, 0.38 * d)
    pan = np.linspace(-0.35, 0.35, n)
    return np.stack([w * np.sqrt(0.5 * (1 - pan)), w * np.sqrt(0.5 * (1 + pan))], 1)


def tick():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    s = 0.6 * np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.018)
    s += 0.25 * np.sin(2 * np.pi * 3700 * t) * np.exp(-t / 0.008)
    burst = rng.standard_normal(n) * np.exp(-t / 0.002) * 0.3
    s = (s + burst) * env(n, 0.001, 0.03)
    return np.stack([s, s], 1)


def thump(d=0.9):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 46 + 34 * np.exp(-t / 0.05)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    s += 0.12 * rng.standard_normal(n) * np.exp(-t / 0.006)        # мягкая атака, без щелчка
    s *= env(n, 0.004, 0.2)
    return np.stack([s, s], 1)


def swell(d=1.4):
    n = int(d * SR)
    t = np.arange(n) / SR
    tone = sum(np.sin(2 * np.pi * f0 * t + p) for f0, p in [(146.8, 0), (220.0, 1), (293.7, 2), (440.0, 3)]) / 4
    air = bandpass_sweep(rng.standard_normal(n), [300, 700, 1800])
    s = (0.6 * tone + 0.4 * air) * np.linspace(0, 1, n) ** 2.2
    s *= env(n, 0.02, 0.35)
    return np.stack([s, s], 1)


def reverb(x, rt=0.7, mix=0.25):
    m = int(rt * SR)
    t = np.arange(m) / SR
    out = np.zeros_like(x)
    for c in range(2):
        ir = rng.standard_normal(m) * np.exp(-t / (rt / 6.9))
        ir /= np.sqrt((ir ** 2).sum())
        out[:, c] = fftconvolve(x[:, c], ir)[:len(x)]
    return (1 - mix) * x + mix * out


def place(track, sig, t, gain_db, peak_at=0.0):
    i = int((t - peak_at) * SR)
    sig = sig * 10 ** (gain_db / 20) / (np.abs(sig).max() + 1e-12)
    j0, j1 = max(i, 0), min(i + len(sig), len(track))
    if j1 > j0:
        track[j0:j1] += sig[j0 - i:j1 - i]


def sfx_track(cues):
    n = int((TOTAL + 0.5) * SR)
    tr = np.zeros((n, 2))
    sc = cues["scenes"]
    shots = json.load(open(os.path.join(BUILD, "edl.json")))["shots"]
    start = {s["scene"]: s["t0"] for s in shots if s["kind"] == "scene"}
    w = reverb(whoosh(), 0.5, 0.2)
    place(tr, w, start["course"], -27, peak_at=0.5)
    place(tr, w, start["factors"], -28, peak_at=0.5)
    for k in ["f1", "f2", "f3", "f4"]:
        place(tr, reverb(tick(), 0.4, 0.3), start["factors"] + sc["factors"][k] - 0.08, -31)
    th = reverb(thump(), 0.6, 0.15)
    place(tr, th, start["timeline"] + sc["timeline"]["disease"] - 0.08, -21)
    place(tr, th, cues["overlay"]["best"] + 0.05, -20)
    place(tr, th, start["tenpercent"] + sc["tenpercent"]["ten"] - 0.02, -19)
    place(tr, reverb(swell(), 0.9, 0.3), [s for s in shots if s["kind"] == "endcard"][0]["t0"] + 0.25, -29,
          peak_at=1.2)
    return tr


def main():
    cues = json.load(open(os.path.join(BUILD, "cues.json")))
    tracks = {}
    for src in ("front", "side"):
        x = load(src)
        y = denoise(x, cut(x, NOISE[src]))
        tracks[src] = y
    # боковой дубль → громкость и тембр фронта
    f_sp, s_sp = cut(tracks["front"], SPEECH["front"]), cut(tracks["side"], SPEECH["side"])
    taps, curve = match_eq(s_sp, f_sp)
    tracks["side"] = fir(tracks["side"], taps)
    gain = rms_db(f_sp) - rms_db(cut(tracks["side"], SPEECH["side"]))
    tracks["side"] *= 10 ** (gain / 20)
    print(f"бок → фронт: усиление {gain:+.1f} дБ; тембр (Гц: дБ): "
          + ", ".join(f"{k}:{v:+.1f}" for k, v in curve.items() if 60 <= k <= 12000))
    # сборка по монтажному листу с кроссфейдами 40 мс
    n = int((TOTAL + 0.5) * SR)
    voice = np.zeros(n)
    xf = int(0.04 * SR)
    for c in CLIPS:
        src = tracks[c["src"]]
        a, b = int(round(c["a"] * SR)), int(round(c["b"] * SR))
        o = int(round(c["out"] * SR))
        seg = src[max(a - xf // 2, 0):b + xf // 2].copy()
        fade = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2
        seg[:xf] *= fade
        seg[-xf:] *= fade[::-1]
        o0 = o - xf // 2
        if o0 < 0:                                   # первый клип начинается с нуля
            seg, o0 = seg[-o0:], 0
        voice[o0:o0 + len(seg)] += seg
    wavfile.write(os.path.join(BUILD, "voice_raw.wav"), SR, voice.astype(np.float32))
    # общая обработка голоса
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(BUILD, "voice_raw.wav"), "-af",
                    "highpass=f=70:poles=2,equalizer=f=190:t=q:w=1.1:g=-1.5,"
                    "equalizer=f=3300:t=q:w=1.3:g=2.0,equalizer=f=7000:t=q:w=1.0:g=0.8,"
                    "acompressor=threshold=-24dB:ratio=2.2:attack=12:release=220:knee=4:makeup=1",
                    "-c:a", "pcm_f32le", os.path.join(BUILD, "voice.wav")], check=True)
    _, v = wavfile.read(os.path.join(BUILD, "voice.wav"))
    v = v.astype(np.float64)
    # голос к −16 LUFS-ориентиру, затем акценты
    sfx = sfx_track(cues)
    mix = np.stack([v, v], 1)[:len(sfx)]
    pre_gain = 10 ** ((-20 - rms_db(v[v != 0])) / 20)
    mix *= pre_gain
    mix[:len(sfx)] += sfx[:len(mix)] * 1.0
    wavfile.write(os.path.join(BUILD, "mix_pre.wav"), SR, mix.astype(np.float32))
    # двухпроходная нормализация громкости
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", os.path.join(BUILD, "mix_pre.wav"), "-af",
                           "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    st = json.loads(re.search(r"\{[^{}]+\}", meas[meas.rfind("[Parsed_loudnorm"):], re.S).group(0))
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={st['input_i']}:measured_TP={st['input_tp']}:"
          f"measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(BUILD, "mix_pre.wav"), "-af", ln,
                    "-ar", str(SR), "-t", f"{TOTAL:.4f}", "-c:a", "pcm_s24le", os.path.join(BUILD, "mix.wav")],
                   check=True)
    # отдельно — дорожка акцентов (для проверки уровней)
    wavfile.write(os.path.join(BUILD, "sfx_only.wav"), SR, sfx.astype(np.float32))
    print("готово: build/mix.wav")


if __name__ == "__main__":
    main()
