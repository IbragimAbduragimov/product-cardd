#!/usr/bin/env python3
"""Add the abduragimov_cvs ending to a vertical video.

The ending, measured frame by frame from the reference video:
  - the handle slides from the top-left corner to the centre and grows,
  - the picture crossfades into a Gaussian blur,
  - a big handle with an ECG line fades in and slowly scales up,
  - the ECG line is wiped on left to right (with the beep sound),
  - the picture darkens, then holds as a still.

Usage:
  python3 add_ending.py input.mp4 output.mp4
  python3 add_ending.py input.mp4 output.mp4 --cut 12.4        # end the clip at 12.4 s, then the ending
  python3 add_ending.py input.mp4 output.mp4 --watermark add   # video has no handle in the corner yet

Needs: ffmpeg/ffprobe, Python 3 with numpy, opencv-python-headless, pillow.
"""
import argparse, json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', path],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    w, h = int(v['width']), int(v['height'])
    rot = 0
    for sd in v.get('side_data_list', []):
        if 'rotation' in sd:
            rot = int(sd['rotation'])
    rot = int(v.get('tags', {}).get('rotate', rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = map(int, v['avg_frame_rate'].split('/'))
    fps = num / den if den else 30.0
    has_audio = any(s['codec_type'] == 'audio' for s in info['streams'])
    return w, h, fps, has_audio


class Ending:
    def __init__(self, w, h):
        p = json.load(open(os.path.join(ASSETS, 'params.json')))
        self.p = p
        self.w, self.h = w, h
        rw, rh = p['ref_size']
        self.kx, self.ky = w / rw, h / rh          # geometry is measured on 720x1280
        self.k = self.kx                           # text scale follows width
        m = cv2.imread(os.path.join(ASSETS, 'text_matte.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535
        self.matte = m
        self.SF, self.PAD = p['matte_scale'], p['matte_pad']
        g = p['group']
        self.text2 = self.text_at(g['text_xy'][0], g['text_xy'][1], self.SF)
        self.ecg4 = self._ecg_supersampled()
        lut = np.array(p['dark']['lut_rgb'], np.float32)
        self.lut_bgr = lut[::-1]
        self.dark_t = {int(k): v for k, v in p['dark']['t'].items()}
        r = p['rest']
        rest = self.text_at(r['x'], r['y'], r['s'])
        self.rest_alpha = rest
        wm = cv2.dilate((rest > 0.02).astype(np.uint8), np.ones((11, 11), np.uint8))
        self.wm_soft = cv2.GaussianBlur(wm.astype(np.float32), (0, 0), 2)[..., None]
        self.keep = (1 - wm).astype(np.float32)

    # -- geometry helpers (all inputs in reference 720x1280 units) --
    def text_at(self, x, y, s):
        k = s / self.SF * self.k
        small = cv2.resize(self.matte, None, fx=k, fy=k, interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
        kx = small.shape[1] / self.matte.shape[1]
        ky = small.shape[0] / self.matte.shape[0]
        M = np.float32([[1, 0, x * self.kx - self.PAD * kx], [0, 1, y * self.ky - self.PAD * ky]])
        return np.clip(cv2.warpAffine(small, M, (self.w, self.h), flags=cv2.INTER_LINEAR), 0, 1)

    def _ecg_supersampled(self):
        SS = 4
        e = self.p['ecg']
        img = Image.new('L', (self.w * SS, self.h * SS))
        d = ImageDraw.Draw(img)
        pts = [(x * self.kx * SS, y * self.ky * SS) for x, y in e['path']]
        lw = e['width'] * self.k * SS
        d.line(pts, fill=255, width=max(1, int(round(lw))), joint='curve')
        for x, y in (pts[0], pts[-1]):
            d.ellipse((x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2), fill=255)
        self.SS = SS
        return np.asarray(img).astype(np.float32) / 255

    def ecg_alpha(self, X):
        a = np.zeros((self.h, self.w), np.float32)
        X *= self.kx
        if X <= 0:
            return a
        SS = self.SS
        xs = (np.arange(self.ecg4.shape[1]) + 0.5) / SS
        sub = self.ecg4 * np.clip(X - xs + 0.5, 0, 1)[None, :]
        return cv2.resize(sub, (self.w, self.h), interpolation=cv2.INTER_AREA)

    def has_baked_watermark(self, frame):
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        th = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, k)
        ys, xs = np.where(self.rest_alpha > 0.02)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        a = self.rest_alpha[y0:y1, x0:x1].ravel()
        t = th[y0:y1, x0:x1].ravel()
        a = a - a.mean(); t = t - t.mean()
        c = float(np.dot(a, t) / (np.linalg.norm(a) * np.linalg.norm(t) + 1e-6))
        return c > 0.5, c

    def remove_watermark(self, frame):
        fr = frame.astype(np.float32)
        wgt = cv2.GaussianBlur(self.keep, (0, 0), 8)
        est = cv2.GaussianBlur(fr * self.keep[..., None], (0, 0), 8) / np.maximum(wgt, 1e-4)[..., None]
        return np.clip(fr * (1 - self.wm_soft) + est * self.wm_soft, 0, 255).astype(np.uint8)

    @staticmethod
    def white(base, a, o=1.0):
        a = (a * o)[..., None]
        return base * (1 - a) + 255 * a

    def darkness(self, f):
        d = self.p['dark']
        if f < d['start']:
            return 0.0
        if f >= d['end']:
            return 1.0
        f0 = int(np.floor(f)); t0 = self.dark_t.get(f0, 0.0); t1 = self.dark_t.get(f0 + 1, 1.0)
        return t0 + (t1 - t0) * (f - f0)

    def render(self, frame, f, watermark):
        """frame: BGR uint8 footage; f: position in reference frames (float)."""
        p = self.p
        t1 = p['text1']
        if watermark == 'baked':
            frame = self.remove_watermark(frame)
        base = frame.astype(np.float32)
        b = p['blur']
        wb = float(np.clip((f - b['start']) / b['frames'], 0, 1))
        if wb > 0:
            bl = np.asarray(Image.fromarray(frame[..., ::-1]).filter(ImageFilter.GaussianBlur(b['radius'] * self.k)))
            base = (1 - wb) * base + wb * bl[..., ::-1].astype(np.float32)
        td = self.darkness(f)
        if td > 0:
            q = np.clip(base, 0, 255)
            dark = np.stack([np.interp(q[..., c], np.arange(256), self.lut_bgr[c]) for c in range(3)], -1)
            base = (1 - td) * base + td * dark
        if watermark != 'none' and f <= t1['end']:
            ff = max(f, t1['start'])
            s, x, y = (np.polyval(t1[k], ff) for k in 'sxy')
            base = self.white(base, self.text_at(x, y, s))
        g = p['group']
        if f >= g['fade_start']:
            o = float(np.clip((f - g['fade_start']) * g['fade_rate'], 0, 1))
            r = min(np.polyval(g['scale'], f), self.SF) / self.SF
            GW = np.maximum(self.text2, self.ecg_alpha(np.polyval(p['ecg']['wipe'], f)))
            cx, cy = g['center'][0] * self.kx, g['center'][1] * self.ky
            M = np.float32([[r, 0, cx * (1 - r)], [0, r, cy * (1 - r)]])
            base = self.white(base, np.clip(cv2.warpAffine(GW, M, (self.w, self.h), flags=cv2.INTER_LINEAR), 0, 1), o)
        return np.clip(base + 0.5, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--cut', type=float, help='seconds: treat this moment as the end of the clip (default: real end)')
    ap.add_argument('--watermark', choices=['auto', 'baked', 'add', 'none'], default='auto',
                    help='auto: detect the small handle in the top-left corner; baked: it is in the video, remove it '
                         'when it starts moving; add: draw it over the whole video; none: skip the moving handle')
    ap.add_argument('--crf', type=int, default=15)
    a = ap.parse_args()

    w, h, fps, has_audio = probe(a.input)
    end = Ending(w, h)
    p = end.p
    ref_fps, anchor, last = p['ref_fps'], p['anchor_frame'], p['end_frame']

    dec = ['ffmpeg', '-v', 'error', '-i', a.input]
    if a.cut:
        dec += ['-t', f'{a.cut:.4f}']
    dec += ['-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    raw = subprocess.run(dec, capture_output=True, check=True).stdout
    fsz = w * h * 3
    n_in = len(raw) // fsz
    if n_in == 0:
        sys.exit('no frames decoded')
    frames = np.frombuffer(raw, np.uint8)[:n_in * fsz].reshape(n_in, h, w, 3)
    clip_len = n_in / fps
    n_tail = int(round((last - anchor) / ref_fps * fps))
    n_out = n_in + n_tail

    wm = a.watermark
    if wm == 'auto':
        found, score = end.has_baked_watermark(frames[-1])
        wm = 'baked' if found else 'add'
        print(f'watermark: {wm} (match {score:.2f})')

    tmp_video = a.output + '.video.mp4'
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}',
                            '-r', f'{fps}', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.crf),
                            '-pix_fmt', 'yuv420p', '-profile:v', 'high', tmp_video], stdin=subprocess.PIPE)
    start_ref = p['text1']['start']
    for i in range(n_out):
        f = anchor + (i - (n_in - 1)) / fps * ref_fps       # position on the reference timeline
        fr = frames[min(i, n_in - 1)]
        if f < start_ref:
            out = fr if wm != 'add' else end.render(fr, f, 'add')
        else:
            out = end.render(np.ascontiguousarray(fr), f, wm)
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
        if i % 30 == 0:
            print(f'\rframe {i + 1}/{n_out}', end='', flush=True)
    enc.stdin.close(); enc.wait()
    print()

    ending_wav = os.path.join(ASSETS, 'ending_audio.wav')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', tmp_video, '-i', a.input, '-i', ending_wav]
    if has_audio:
        fc = (f'[1:a]atrim=0:{clip_len:.6f},asetpts=PTS-STARTPTS,aresample=44100,'
              f'aformat=channel_layouts=stereo,afade=t=out:st={max(clip_len - 0.015, 0):.6f}:d=0.015[a1];'
              f'[2:a]aresample=44100,aformat=channel_layouts=stereo[a2];[a1][a2]concat=n=2:v=0:a=1[a]')
    else:
        fc = (f'anullsrc=r=44100:cl=stereo,atrim=0:{clip_len:.6f}[a1];'
              f'[2:a]aresample=44100,aformat=channel_layouts=stereo[a2];[a1][a2]concat=n=2:v=0:a=1[a]')
    cmd += ['-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart', a.output]
    subprocess.run(cmd, check=True)
    os.remove(tmp_video)
    print('saved', a.output)


if __name__ == '__main__':
    main()
