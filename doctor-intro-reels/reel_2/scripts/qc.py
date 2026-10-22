"""Проверка готового ролика: параметры, ошибки декодирования, громкость, синхрон фраз с исходником."""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.signal import fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from edl import CLIPS, FRONT_SRC, SIDE_SRC  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "output", "reel_blog_purpose_1080x1920.mp4")
SR = 8000


def audio(path, pan="pan=mono|c0=0.5*c0+0.5*c1"):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-af", pan, "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def envelope(x, hop=40):                     # 5 мс
    x = x[:len(x) // hop * hop].reshape(-1, hop)
    return np.abs(x).mean(1)


def main():
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                      "format=duration,size,bit_rate:stream=codec_name,profile,width,height,"
                                      "r_frame_rate,pix_fmt,sample_rate,channels,nb_frames",
                                      "-of", "json", OUT], capture_output=True, text=True).stdout)
    for s in info["streams"]:
        print("поток:", {k: v for k, v in s.items() if k in ("codec_name", "profile", "width", "height",
                                                             "r_frame_rate", "pix_fmt", "sample_rate", "channels",
                                                             "nb_frames")})
    f = info["format"]
    print(f"длительность {float(f['duration']):.2f} с, размер {int(f['size']) / 1e6:.1f} МБ, "
          f"битрейт {int(f['bit_rate']) / 1e6:.1f} Мбит/с")
    err = subprocess.run(["ffmpeg", "-v", "error", "-i", OUT, "-f", "null", "-"], capture_output=True, text=True).stderr
    print("ошибок декодирования:", len(err.strip().splitlines()) if err.strip() else 0)
    loud = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", OUT, "-af", "ebur128=framelog=quiet:peak=true",
                           "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
    for line in loud.splitlines():
        if line.strip().startswith(("I:", "LRA:", "Peak:")):
            print("  ", line.strip())
    # синхрон: огибающая каждой фразы в ролике против исходника
    out = envelope(audio(OUT))
    src = {"front": envelope(audio(FRONT_SRC, "pan=mono|c0=c0")), "side": envelope(audio(SIDE_SRC))}
    worst = 0
    for c in CLIPS:
        s, e = c["speech"]
        ref = src[c["src"]][int(s * 200):int(e * 200)]
        ref = (ref - ref.mean()) / (ref.std() + 1e-9)
        exp = c["out"] + (s - c["a"])
        lo = int((exp - 0.3) * 200)
        seg = out[lo:lo + len(ref) + 120]
        seg = (seg - seg.mean()) / (seg.std() + 1e-9)
        cc = fftconvolve(seg, ref[::-1], mode="valid")
        k = int(np.argmax(cc))
        shift = (lo + k) / 200 - exp
        r = np.corrcoef(seg[k:k + len(ref)], ref)[0, 1]
        worst = max(worst, abs(shift))
        print(f"  {c['tag']:9s} {c['src']:5s} сдвиг {shift * 1000:+5.0f} мс  r={r:.2f}")
    print(f"максимальный сдвиг звука фраз: {worst * 1000:.0f} мс")


if __name__ == "__main__":
    main()
