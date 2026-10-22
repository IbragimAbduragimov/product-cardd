"""Точные границы речи (Silero VAD) — резать только в тишине."""
import json
import sys
import wave

import numpy as np
import sherpa_onnx as so

model, out = sys.argv[1], sys.argv[2]
res = {}
for name, path in zip(sys.argv[3::2], sys.argv[4::2]):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    cfg = so.VadModelConfig()
    cfg.silero_vad.model = model
    cfg.silero_vad.min_silence_duration = 0.18
    cfg.silero_vad.min_speech_duration = 0.08
    cfg.silero_vad.threshold = 0.45
    cfg.sample_rate = 16000
    vad = so.VoiceActivityDetector(cfg, buffer_size_in_seconds=300)
    for i in range(0, len(a), 512):
        vad.accept_waveform(a[i:i + 512])
    vad.flush()
    segs = []
    while not vad.empty():
        segs.append((round(vad.front.start / 16000, 3), round((vad.front.start + len(vad.front.samples)) / 16000, 3)))
        vad.pop()
    res[name] = segs
    print(name, len(segs), "островков речи")
    print("  ", "  ".join(f"{s:.2f}-{e:.2f}" for s, e in segs))
json.dump(res, open(out, "w"), indent=0)
