"""Re-composite only the tail (from montage frame START) of the graded clean montage with the overlay layers."""
import cv2, numpy as np, subprocess, sys, os
src,out,START=sys.argv[1],sys.argv[2],int(sys.argv[3]); dirs=sys.argv[4:]
have={}
for d in dirs:
    for f in os.listdir(d):
        if f.endswith('.png'): have.setdefault(int(f[:5]),[]).append(os.path.join(d,f))
cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-','-ss',str(START/30),'-i',src,
     '-map','0:v','-map','1:a','-c:v','libx264','-preset','slow','-crf','10','-pix_fmt','yuv420p','-c:a','pcm_s16le','-shortest',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE); cap=cv2.VideoCapture(src); cap.set(1,START); i=START
while True:
    ok,f=cap.read()
    if not ok: break
    for pth in have.get(i,[]):
        o=cv2.imread(pth,cv2.IMREAD_UNCHANGED).astype(np.float32); a=o[...,3:]/255
        if a.max()>0: f[:960]=(f[:960]*(1-a)+o[...,:3]*a).astype(np.uint8)
    p.stdin.write(f.tobytes()); i+=1
p.stdin.close(); p.wait(); print('tail frames',i-START)
