import cv2, numpy as np, subprocess, sys
sys.path.insert(0,'work'); from seg import person
from cleanbg import BGCleaner, grain, sharpen, ENC
SRC='videos/VID_20261105_144308_670.mp4.mov'
start=int(sys.argv[1]); count=int(sys.argv[2]); out=sys.argv[3]
POSTER=cv2.imread('work/poster.png',cv2.IMREAD_UNCHANGED).astype(np.float32); PX,PY=659,83
ph,pw=POSTER.shape[:2]; pa=POSTER[...,3:]/255; prgb=POSTER[...,:3]
cleaner=BGCleaner(); rng=np.random.default_rng(1)
cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-',
     '-ss',str(start/30),'-t',str(count/30),'-i',SRC,'-map','0:v','-map','1:a',*ENC,'-shortest',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
cap=cv2.VideoCapture(SRC); cap.set(1,start); pm=None
for i in range(start,start+count):
    ok,f=cap.read()
    if not ok: break
    m=person(f); m=cv2.dilate(m,np.ones((5,5)))
    pm=m if pm is None else 0.5*pm+0.5*m
    o=cleaner(f.astype(np.float32),pm)
    c=cv2.resize(np.clip(o,0,255).astype(np.uint8),(1080,1920),interpolation=cv2.INTER_LANCZOS4)
    c=sharpen(c).astype(np.float32)
    roi=c[PY:PY+ph,PX:PX+pw]; c[PY:PY+ph,PX:PX+pw]=roi*(1-pa)+prgb*pa
    c=grain(np.clip(c,0,255).astype(np.uint8),rng)
    p.stdin.write(c.tobytes())
p.stdin.close(); p.wait()
