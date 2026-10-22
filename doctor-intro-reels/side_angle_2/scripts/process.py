"""Проход 2: стабилизация + кадрирование из 4K + замена стены слева на синий фон.

Для каждого кадра (30 fps CFR):
  1. Аффинное выравнивание к опорному кадру (из track.py) и вырез окна 1440×2560
     прямо из 4K — без увеличения, только исходные пиксели.
  2. Маска человека (Robust Video Matting, ResNet50) + уточнение края guided filter.
  3. Неподвижная в стабилизированных координатах маска стены и планки.
  4. Заливка стены синим: низкочастотный цвет берётся из соседнего настоящего фона
     этого же кадра, мелкая фактура и шум — зеркальная копия реального синего фона.
     Поэтому заливка «живёт» вместе с кадром: шум, экспозиция, баланс совпадают.

Выход: мастер 1440×2560 (без масштабирования) и версия 1080×1920 для Reels.
"""
import os
import subprocess
import sys

import cv2
import numpy as np
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "..", "sources", "IMG_7785.mov")
RVM = os.environ.get("RVM_MODEL", "/tmp/claude-0/-home-user-product-cardd/382abc70-8892-52f3-853b-5bc8f0827c50"
                                  "/scratchpad/models/rvm_resnet50_fp32.onnx")
FPS = 30
SW, SH = 2160, 3840                 # исходник после поворота
X0, Y0, CW, CH = 470, 760, 1440, 2560   # окно кадра в координатах опорного кадра (зум 1.5×)

# --- Геометрия стены в стабилизированных координатах кадра 1440×2560 ---
TABLE_Y = 1624          # задний край столешницы слева
EDGE_X0, EDGE_K = 347, 0.030   # правый край планки с выступами: x = 347 + 0.03·y (+ запас)
FEATHER = 10
# Источник «настоящего» синего фона рядом со стеной (левее головы, выше рукава)
NAVY_X = (392, 620)
NAVY_Y = (0, 1080)


def wall_mask():
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    edge = EDGE_X0 + EDGE_K * yy
    m_x = np.clip((edge - xx) / FEATHER + 0.5, 0, 1)            # мягко у границы с синим
    m_y = np.clip((TABLE_Y - yy) / 3.0 + 0.5, 0, 1)            # почти жёстко у столешницы
    return (m_x * m_y).astype(np.float32)


def guided_filter(I, p, r, eps):
    """Классический guided filter (He et al.) на box-фильтрах."""
    k = (2 * r + 1, 2 * r + 1)
    mean = lambda x: cv2.boxFilter(x, -1, k, borderType=cv2.BORDER_REFLECT)  # noqa: E731
    mI, mp = mean(I), mean(p)
    a = (mean(I * p) - mI * mp) / (mean(I * I) - mI * mI + eps)
    b = mp - a * mI
    return mean(a) * I + mean(b)


class Matter:
    def __init__(self):
        so = ort.SessionOptions()
        so.intra_op_num_threads = 4
        self.s = ort.InferenceSession(RVM, so)
        self.rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
        self.dr = np.array([0.25], np.float32)

    def __call__(self, rgb):
        src = (rgb.astype(np.float32) / 255).transpose(2, 0, 1)[None]
        fgr, pha, *self.rec = self.s.run(None, {"src": src, "r1i": self.rec[0], "r2i": self.rec[1],
                                                "r3i": self.rec[2], "r4i": self.rec[3],
                                                "downsample_ratio": self.dr})
        return fgr[0].transpose(1, 2, 0) * 255, pha[0, 0]


def refine_alpha(rgb, alpha):
    """Подтягивает край маски к реальной границе белого рукава на сером фоне стены."""
    luma = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    return np.clip(guided_filter(luma, alpha, 6, 2e-3), 0, 1)


class NavyFill:
    """Синяя заливка, повторяющая настоящий фон этого же кадра."""

    def __init__(self):
        self.base = None    # сглаженный во времени профиль цвета по строкам

    def __call__(self, rgb, alpha):
        x1, x2 = NAVY_X
        y1, y2 = NAVY_Y
        src = rgb[y1:y2, x1:x2].astype(np.float32)
        clean = (alpha[y1:y2, x1:x2] < 0.02).astype(np.float32)[..., None]
        # низкие частоты: средний цвет по строкам в полосе у самой границы
        strip = src[:, :90]
        w = clean[:, :90]
        prof = (strip * w).sum(1) / np.maximum(w.sum(1), 1)
        prof = cv2.GaussianBlur(prof[None], (0, 0), sigmaX=40, sigmaY=0.1)[0]
        rows = np.arange(y1, y2)
        # продолжение вниз, до столешницы: линейный тренд по нижней части профиля
        fit_rows = rows[-380:]
        coef = [np.polyfit(fit_rows, prof[-380:, c], 1) for c in range(3)]
        all_rows = np.arange(0, TABLE_Y + 8)
        base = np.empty((len(all_rows), 3), np.float32)
        base[: y2] = prof
        for c in range(3):
            ext = np.polyval(coef[c], all_rows[y2:])
            base[y2:, c] = ext
        if self.base is None:
            self.base = base
        else:
            self.base = 0.75 * self.base + 0.25 * base          # без мерцания
        # высокие частоты: фактура/шум настоящего фона, зеркально размноженные
        hp = src - cv2.GaussianBlur(src, (0, 0), 6)
        hp *= clean
        tile_x = np.concatenate([hp[:, ::-1], hp], 1)              # 456 px в ширину
        tile = np.concatenate([tile_x, tile_x[::-1]], 0)           # 2160 px в высоту
        need_h, need_w = TABLE_Y + 8, EDGE_X0 + int(EDGE_K * CH) + 2 * FEATHER
        tile = tile[:need_h, -need_w:] if tile.shape[1] >= need_w else np.pad(
            tile, ((0, 0), (need_w - tile.shape[1], 0), (0, 0)), mode="reflect")[:need_h]
        fill = self.base[:, None, :] + tile[:need_h, :need_w]
        return fill, need_h, need_w


def decode(src):
    cmd = ["ffmpeg", "-v", "error", "-i", src, "-vf",
           f"fps={FPS},scale=in_color_matrix=bt709:out_color_matrix=bt709,format=rgb24",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=SW * SH * 3)
    n = SW * SH * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(SH, SW, 3)


def process_frame(fr, A, matter, filler, wmask):
    M = np.array([[A[0], A[1], A[2] - X0], [A[3], A[4], A[5] - Y0]], np.float64)
    out = cv2.warpAffine(fr, M, (CW, CH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    fgr, alpha = matter(out)
    rh, rw = TABLE_Y + 8, 700                      # уточняем край только в зоне стены
    alpha[:rh, :rw] = refine_alpha(out[:rh, :rw], alpha[:rh, :rw])
    fill, fh, fw = filler(out, alpha)
    orig = out[:fh, :fw].astype(np.float32)
    a = alpha[:fh, :fw, None]
    # цвет переднего плана без примеси стены: внутри — оригинал, на краю — оценка RVM
    s = np.clip((a - 0.90) / 0.08, 0, 1)
    fg = orig * s + fgr[:fh, :fw] * (1 - s)
    composite = a * fg + (1 - a) * fill            # человек поверх нового синего фона
    w = wmask[:fh, :fw, None]
    out[:fh, :fw] = np.clip(orig * (1 - w) + composite * w, 0, 255).astype(np.uint8)
    return out, alpha


def main():
    T = np.load(os.path.join(ROOT, "build", "transforms.npy"))
    wmask = wall_mask()
    matter, filler = Matter(), NavyFill()
    stills = [float(x) for x in sys.argv[1:]]
    if stills:                                   # быстрый просмотр отдельных кадров
        want = {int(t * FPS) for t in stills}
        warm = {i - k for i in want for k in range(1, 6)}   # прогрев рекуррентной маски
        for i, fr in enumerate(decode(SRC)):
            if i in warm or i in want:
                out, alpha = process_frame(fr, T[i], matter, filler, wmask)
                if i in want:
                    cv2.imwrite(os.path.join(ROOT, "build", f"still_{i / FPS:05.1f}.png"),
                                cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
            if i > max(want):
                break
        return
    master = os.path.join(ROOT, "build", "video_master_noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{CW}x{CH}", "-r", str(FPS), "-i", "-",
                            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "13", "-tune", "film",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            master], stdin=subprocess.PIPE)
    for i, fr in enumerate(decode(SRC)):
        A = T[min(i, len(T) - 1)]
        out, _ = process_frame(fr, A, matter, filler, wmask)
        enc.stdin.write(out.tobytes())
        if i % 150 == 0:
            print(f"кадр {i} ({i / FPS:.1f} с)", flush=True)
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
