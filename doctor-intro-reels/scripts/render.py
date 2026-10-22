"""Сборка: звук (голос + музыка) → видеоряд (фронт + вставки + цвет + графика) → MP4.

Оригинальная фронтальная дорожка идёт целиком и по порядку; всё прочее —
поверх неё. Звук речи — только оригинальный, с бережной обработкой.
"""
import json
import re
import subprocess
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from timeline import (FPS, FRONT_1, FRONT_2, FRONT_2_IN, H, INSERTS, MAIN_END, ROOT,  # noqa: E402
                      SEAM, TOTAL, W, plain, subtitle_events)

BUILD = f"{ROOT}/build"
OUT = f"{ROOT}/output/doctor_intro_reels_1080x1920.mp4"

# Сдержанная цветокоррекция: чуть плотнее контраст, естественная кожа,
# лёгкий «холодный» сдвиг в тенях под тёмно-синий фон студии.
GRADE = ("eq=contrast=1.045:saturation=0.97:gamma=0.985,"
         "colorbalance=rs=-0.015:bs=0.025:rm=0.008:bh=-0.012,"
         "curves=all='0/0.012 0.25/0.235 0.75/0.77 1/0.985'")
GRADE_SIDE = GRADE + ",eq=brightness=-0.012"
VIGNETTE = "vignette=angle=0.42:mode=forward"


def run(cmd):
    print(" ".join(cmd[:6]), "…", flush=True)
    subprocess.run(cmd, check=True)


def measure(path, extra=""):
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        extra + "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return json.loads(re.search(r"\{[^{}]+\}", m[m.rfind("[Parsed_loudnorm"):], re.S).group(0))


def build_audio():
    # 1. Голос: оригинальная речь целиком, бережная очистка и выравнивание
    voice = (f"[0:a]atrim=0:{SEAM},asetpts=PTS-STARTPTS[a1];"
             f"[1:a]atrim={FRONT_2_IN:.4f},asetpts=PTS-STARTPTS[a2];"
             "[a1][a2]concat=n=2:v=0:a=1,"
             # afftdn задерживает сигнал на 1200 сэмплов — компенсируем ради точного синхрона
             "highpass=f=70,afftdn=nr=6:nf=-62,atrim=start_sample=1200,asetpts=PTS-STARTPTS,"
             "equalizer=f=220:t=q:w=1.0:g=-1.5,equalizer=f=3600:t=q:w=1.2:g=1.8,"
             "acompressor=threshold=-40dB:ratio=2.2:attack=10:release=180:makeup=1,"
             f"apad=whole_dur={TOTAL:.3f}")
    run(["ffmpeg", "-v", "error", "-y", "-i", FRONT_1, "-i", FRONT_2, "-filter_complex", voice,
         "-ar", "48000", "-ac", "2", "-t", f"{TOTAL:.3f}", f"{BUILD}/voice.wav"])
    v = measure(f"{BUILD}/voice.wav")
    voice_gain = -16.0 - float(v["input_i"])          # голос → −16 LUFS
    m = measure(f"{BUILD}/music.wav")
    music_gain = -33.0 - float(m["input_i"])          # музыка ≈17 дБ ниже голоса (+ мягкий дакинг)
    print(f"voice {v['input_i']} LUFS → gain {voice_gain:+.1f} dB; music gain {music_gain:+.1f} dB")
    mix = (f"[0:a]volume={voice_gain:.2f}dB,asplit=2[v1][vsc];"
           f"[1:a]volume={music_gain:.2f}dB[m];"
           "[m][vsc]sidechaincompress=threshold=0.1:ratio=2:attack=80:release=1000:makeup=1[mduck];"
           "[v1][mduck]amix=inputs=2:normalize=0:duration=first,"
           # компенсация lookahead лимитера (239 сэмплов)
           "alimiter=limit=0.84:attack=5:release=60:level=disabled,"
           "atrim=start_sample=239,asetpts=PTS-STARTPTS,apad[mix]")
    pre = f"{BUILD}/mix_pre.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{BUILD}/voice.wav", "-i", f"{BUILD}/music.wav",
         "-filter_complex", mix, "-map", "[mix]", "-ar", "48000", "-t", f"{TOTAL:.3f}", pre])
    # 2. Итоговая громкость под соцсети: −14 LUFS, пик −1.5 dBTP (двухпроходно, линейно)
    st = measure(pre)
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={st['input_i']}:"
          f"measured_TP={st['input_tp']}:measured_LRA={st['input_lra']}:"
          f"measured_thresh={st['input_thresh']}:offset={st['target_offset']}")
    run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", ln, "-ar", "48000", f"{BUILD}/mix.wav"])


def build_video(preview=None):
    inputs = ["-i", FRONT_1, "-i", FRONT_2]
    fc = [
        f"[0:v]trim=0:{SEAM},setpts=PTS-STARTPTS,fps={FPS},"
        f"scale={W}:{H}:flags=lanczos,setsar=1,{GRADE}[f1]",
        f"[1:v]trim={FRONT_2_IN:.4f},setpts=PTS-STARTPTS,fps={FPS},"
        f"scale={W}:{H}:flags=lanczos,setsar=1,{GRADE}[f2]",
        f"[f1][f2]concat=n=2:v=1:a=0,tpad=stop_mode=clone:stop_duration={TOTAL - MAIN_END + 0.2:.2f},"
        f"trim=0:{TOTAL:.3f}[base0]",
    ]
    cur = "base0"
    for k, ins in enumerate(INSERTS):
        idx = len(inputs) // 2
        t0, t1 = ins["t0"], ins["t1"]
        dur = t1 - t0
        lbl = f"ins{k}"
        fades = ""
        if ins.get("fade_in", ins.get("fade", 0)) > 0:
            fades += f",fade=t=in:st={t0}:d={ins.get('fade_in', ins.get('fade'))}:alpha=1"
        if ins.get("fade_out", ins.get("fade", 0)) > 0:
            fo = ins.get("fade_out", ins.get("fade"))
            fades += f",fade=t=out:st={t1 - fo:.3f}:d={fo}:alpha=1"
        if ins["kind"] == "side":
            inputs += ["-i", ins["src"]]
            s0 = t0 + ins["offset"]
            chain = (f"[{idx}:v]trim={s0:.4f}:{s0 + dur:.4f},setpts=PTS-STARTPTS+{t0}/TB,fps={FPS},"
                     f"scale={W}:{H}:flags=lanczos,setsar=1,{GRADE_SIDE},format=yuva420p")
            fc.append(chain + fades + f"[{lbl}]")
        elif ins["kind"] == "photo":
            inputs += ["-i", ins["src"]]
            n = int((dur + 0.5) * FPS)
            fy = ins.get("focus_y", 0.4)
            cx = ins.get("crop_x", 0.5)
            # кадрирование 9:16 + медленный наезд (≈4 %) на увеличенном исходнике без дрожания
            fc.append(
                f"[{idx}:v]crop='min(iw,ih*9/16)':'ih':'(iw-ow)*{cx}':0,scale=3240:5760:flags=lanczos,"
                f"zoompan=z='1+0.04*on/{n}':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*{fy}':d={n}:"
                f"s={W}x{H}:fps={FPS},setsar=1,{GRADE},eq=gamma=1.03,format=yuva420p,"
                f"setpts=PTS-STARTPTS+{t0}/TB,trim={t0}:{t1}{fades}[{lbl}]")
        elif ins["kind"] == "clip":
            inputs += ["-i", ins["src"]]
            sp = ins["speed"]
            fc.append(
                f"[{idx}:v]setpts=(PTS-STARTPTS)/{sp},fps={FPS},split[ca][cb];"
                f"[ca]scale=-2:{H},crop={W}:{H},gblur=sigma=42,eq=brightness=-0.30:contrast=0.85:saturation=0,colorbalance=bs=0.06:bm=0.04[cbg];"
                f"[cb]scale=1000:-2:flags=lanczos,eq=contrast=1.04[cfg];"
                f"[cbg][cfg]overlay=(W-w)/2:560,setsar=1,format=yuva420p,"
                f"setpts=PTS-STARTPTS+{t0}/TB,trim={t0}:{t1}{fades}[{lbl}]")
        fc.append(f"[{cur}][{lbl}]overlay=0:0:eof_action=pass:enable='between(t,{t0},{t1})'[c{k}]")
        cur = f"c{k}"
    oi = len(inputs) // 2
    inputs += ["-i", f"{BUILD}/overlay.mov", "-i", f"{BUILD}/mix.wav"]
    fc.append(f"[{cur}]{VIGNETTE},fade=t=out:st={MAIN_END - 0.55:.3f}:d=0.85:color=0x0A1325[graded]")
    fc.append(f"[{oi}:v]format=rgba[ov];[graded][ov]overlay=0:0:format=auto,format=yuv420p[vout]")
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", f"{oi + 1}:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2),
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
           "-movflags", "+faststart", "-t", f"{TOTAL:.3f}"]
    if preview:
        cmd += ["-ss", str(preview[0]), "-t", str(preview[1])]
    run(cmd + [OUT])


def export_srt():
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(f"{ROOT}/output/subtitles_ru.srt", "w", encoding="utf-8") as f:
        for i, e in enumerate(subtitle_events(), 1):
            f.write(f"{i}\n{ts(e['s'])} --> {ts(e['e'])}\n{plain(e['text'])}\n\n")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("audio", "all"):
        build_audio()
    if step in ("video", "all"):
        build_video()
    if step in ("srt", "all"):
        export_srt()
