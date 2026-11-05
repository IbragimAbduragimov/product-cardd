"""Montage v8 (smooth ~4 s moves, start punch-in, strong push on 'именно вы'): front camera as base + audio, two cuts to the side camera, punch-ins and slow zooms.
Times are FRONT-camera seconds; all cuts sit in pauses between phrases."""
import cv2, numpy as np, subprocess, sys
sys.path.insert(0,'work'); from cleanbg import ENC
FRONT='out/front_final.mp4'; SIDE='out/side_tight.mp4'; AUDIO=sys.argv[2] if len(sys.argv)>2 else 'audio/edit_audio.wav'
OUT=sys.argv[1]
LAG=-4.2066            # side_t = front_t + LAG
FPS=30; T0=1.40; T1=116.40
OW,OH=1080,1920
FACE={'F':(565,780),'S':(694,870)}     # face centres (zoom targets)
BODY={'F':(545,1000),'S':(600,1100)}   # upper-body centres for gentle pushes
def ease(u): u=min(max(u,0),1); return u*u*(3-2*u)
# Camera shots: (start, end, cam, [(t, zoom), ...]) - zoom is continuous inside a shot and eased
# (zero speed at every keyframe), so moves are slow and gentle; jumps happen only at camera cuts.
SHOTS=[(T0,   35.20,'F',[(T0,1.00),(1.75,1.12),            # sharp punch-in at the very start (0.35 s)
                          (6.5,1.12),(8.0,1.03),(14.3,1.03),(15.6,1.16),(22.5,1.16),(24.0,1.05),(30.5,1.05),(32.0,1.14)]),
       (35.20,47.90,'S',[(35.20,1.00),(36.6,1.09),(43.0,1.09),(44.4,1.02)]),
       (47.90,88.30,'F',[(47.90,1.14),(49.3,1.02),(54.0,1.02),(55.4,1.13),(60.3,1.13),(61.7,1.03),(69.7,1.03),
                          (71.1,1.15),(75.5,1.15),(76.9,1.04),(81.0,1.04),(82.4,1.14)]),
       (88.30,99.90,'S',[(88.30,1.09),(89.7,1.00),(94.5,1.00),(95.9,1.08)]),
       (99.90,T1,   'F',[(99.90,1.00),(101.3,1.10),(108.8,1.10),(110.2,1.04),(113.0,1.04),(114.4,1.14),(114.55,1.14),
                          (115.25,1.40),(T1,1.42)])]           # moves ~1.4 s (eased), strong push on "именно вы"
def params(t):
    for a,b,cam,kf in SHOTS:
        if a<=t<b or (b==T1 and t>=a):
            z=kf[-1][1]
            for (ta,za),(tb,zb) in zip(kf,kf[1:]):
                if ta<=t<=tb: z=za+(zb-za)*ease((t-ta)/(tb-ta)); break
            f=FACE[cam]; k=min(1,(z-1)/0.2)
            return cam,z,OW/2+(f[0]-OW/2)*k,OH/2+(f[1]-OH/2)*k
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
