"""Alpha-composite the infographic PNG frames (named by montage frame index) onto a montage."""
import cv2, numpy as np, subprocess, sys, os
sys.path.insert(0,'work'); from cleanbg import ENC
src, out = sys.argv[1], sys.argv[-1]; dirs=sys.argv[2:-1]   # overlay.py SRC DIR1 [DIR2 ...] OUT (later dirs on top)
have={}
for d in dirs:
    for f in os.listdir(d):
        if f.endswith('.png'): have.setdefault(int(f[:5]),[]).append(os.path.join(d,f))
cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-i',src,
     '-map','0:v','-map','1:a','-c:a','copy',*[x for x in ENC if x not in ('-c:a','aac','-b:a','192k')],'-shortest',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE); cap=cv2.VideoCapture(src); i=0
while True:
    ok,f=cap.read()
    if not ok: break
    for pth in have.get(i,[]):
        o=cv2.imread(pth,cv2.IMREAD_UNCHANGED).astype(np.float32); a=o[...,3:]/255
        if a.max()>0: f[:960]=(f[:960]*(1-a)+o[...,:3]*a).astype(np.uint8)
    p.stdin.write(f.tobytes()); i+=1
p.stdin.close(); p.wait(); print('frames',i)
