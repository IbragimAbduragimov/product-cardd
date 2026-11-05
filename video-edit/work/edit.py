"""Montage v1: front camera as base + audio, two cuts to the side camera, punch-ins and slow zooms.
Times are FRONT-camera seconds; all cuts sit in pauses between phrases."""
import cv2, numpy as np, subprocess, sys
sys.path.insert(0,'work'); from cleanbg import ENC
FRONT='out/front_final.mp4'; SIDE='out/side_final.mp4'; AUDIO=sys.argv[2] if len(sys.argv)>2 else 'audio/edit_audio.wav'
OUT=sys.argv[1]
LAG=-4.2066            # side_t = front_t + LAG
FPS=30; T0=1.40; T1=116.40
OW,OH=1080,1920
FACE={'F':(565,780),'S':(645,990)}     # face centres (zoom targets)
BODY={'F':(545,1000),'S':(600,1100)}   # upper-body centres for gentle pushes
def ease(u): u=min(max(u,0),1); return u*u*(3-2*u)
# (start, end, cam, z_start, z_end, centre)
TL=[(T0,  15.30,'F',1.00,1.10,'body'),
    (15.30,20.60,'F',1.22,1.25,'face'),   # punch-in
    (20.60,35.20,'F',1.00,1.08,'body'),
    (35.20,47.90,'S',1.00,1.12,'face'),   # side camera 1
    (47.90,60.00,'F',1.18,1.00,'face'),   # slow pull-out
    (60.00,69.00,'F',1.00,1.04,'body'),
    (69.00,77.60,'F',1.22,1.25,'face'),   # punch-in
    (77.60,88.30,'F',1.00,1.10,'body'),
    (88.30,99.90,'S',1.14,1.00,'face'),   # side camera 2, pull-out
    (99.90,T1,   'F',1.00,1.16,'face')]   # slow push to the end
def params(t):
    for a,b,cam,z0,z1,c in TL:
        if a<=t<b:
            z=z0+(z1-z0)*ease((t-a)/(b-a))
            f=FACE[cam] if c=='face' else BODY[cam]
            # blend centre from frame centre (z=1) towards the target as we zoom in
            k=min(1,(z-1)/0.15) if z>1 else 0
            cx=OW/2+(f[0]-OW/2)*k; cy=OH/2+(f[1]-OH/2)*k
            return cam,z,cx,cy
    return 'F',1,OW/2,OH/2
def zoom(img,z,cx,cy):
    if z<=1.0001: return img
    w,h=OW/z,OH/z
    x0=min(max(cx-w/2,0),OW-w); y0=min(max(cy-h/2,0),OH-h)
    M=np.float32([[z,0,-x0*z],[0,z,-y0*z]])
    return cv2.warpAffine(img,M,(OW,OH),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_REFLECT)
cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{OW}x{OH}','-r',str(FPS),'-i','-',
     '-i',AUDIO,'-map','0:v','-map','1:a',*ENC,'-shortest',OUT]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
capF=cv2.VideoCapture(FRONT); capS=cv2.VideoCapture(SIDE)
fi=0; si=-1; sframe=None
capF.set(1,int(round(T0*FPS))); fi=int(round(T0*FPS))
n=int(round((T1-T0)*FPS))
for j in range(n):
    t=T0+j/FPS
    ok,ff=capF.read(); fi+=1
    cam,z,cx,cy=params(t)
    if cam=='S':
        want=int(round((t+LAG)*FPS))
        if sframe is None or want<si or want>si+5: capS.set(1,want); si=want-1
        while si<want: ok,sframe=capS.read(); si+=1
        img=sframe
    else: img=ff
    p.stdin.write(zoom(img,z,cx,cy).tobytes())
p.stdin.close(); p.wait()
