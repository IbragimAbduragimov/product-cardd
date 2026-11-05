"""Side video: stabilize + replace left wall/tape strip with blue + crop floor, rendered in ONE
resampling step (stabilize, crop and upscale combined into a single Lanczos warp)."""
import cv2, numpy as np, subprocess, sys
sys.path.insert(0,'work'); from seg import person
from cleanbg import BGCleaner, grain, sharpen, ENC
SRC='videos/VID_20261105_144306_140.mp4.mov'
start=int(sys.argv[1]); count=int(sys.argv[2]); out=sys.argv[3]
OW,OH=1080,1920
# crop window in stabilized reference coords (720x1280): x 20..690, bottom at y=1060 (floor hidden);
# rows above y=0 do not exist in the source and are filled with backdrop blue.
X0,CWID,YBOT=35,600,1060
S=OW/CWID; Y0=YBOT-OH/S
A=np.array([[S,0,-S*X0],[0,S,-S*Y0],[0,0,1]])
T=np.load('work/T.npy').reshape(-1,6)
k=15; pad=np.pad(T,((k//2,k//2),(0,0)),mode='edge')
Ts=np.array([pad[i:i+k].mean(0) for i in range(len(T))]).reshape(-1,2,3)
def Mout(i):
    M=np.vstack([Ts[min(i,len(Ts)-1)],[0,0,1]]); return (A@M)[:2]
yo,xo=np.mgrid[0:OH,0:OW].astype(np.float32)
xr=xo/S+X0; yr=yo/S+Y0                       # reference coords of each output pixel
table=720+0.18*xr
above=(yr<table-1).astype(np.float32)
R=((xr<174)&(yr<table-1)).astype(np.float32); R=cv2.GaussianBlur(R,(0,0),2.5*S)
band=((xr>112)&(xr<178)).astype(np.float32)   # tape-strip column
# blue fill: vertical colour profile of the backdrop next to the wall (ref coords), slight falloff to the left
cols=np.load('work/cols.npy'); prof=cols.copy(); prof[:40]=prof[40]; prof[680:]=prof[680]
prof=cv2.GaussianBlur(prof.reshape(-1,1,3),(1,0),sigmaX=0.1,sigmaY=20).reshape(-1,3)
yi=np.clip(yr,0,1279).astype(int)[:,0]
plate=prof[yi][:,None,:]*np.where(xr<174,1-0.10*(174-xr)/174,1.0)[...,None]
plate=plate.astype(np.float32)
cleaner=BGCleaner(sigma=30*S)
cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{OW}x{OH}','-r','30','-i','-',
     '-ss',str(start/30),'-t',str(count/30),'-i',SRC,'-map','0:v','-map','1:a',*ENC,'-shortest',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
cap=cv2.VideoCapture(SRC); cap.set(1,start); pm=None; rng=np.random.default_rng(0)
ones=np.ones((1280,720),np.float32)
for i in range(start,start+count):
    ok,f=cap.read()
    if not ok: break
    M=Mout(i)
    w=cv2.warpAffine(f,M,(OW,OH),flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    valid=cv2.warpAffine(ones,M,(OW,OH),flags=cv2.INTER_LINEAR,borderValue=0)
    valid=cv2.erode(valid,np.ones((7,7)))
    m=person(np.clip(w,0,255).astype(np.uint8)); m[yr<320]=0
    pm=m if pm is None else 0.5*pm+0.5*m
    b,g,r=w[...,0],w[...,1],w[...,2]; v=(b+g+r)/3
    mu=cv2.blur(v,(9,9)); lstd=np.sqrt(np.maximum(cv2.blur(v*v,(9,9))-mu*mu,0))
    near=cv2.dilate((pm>0.3).astype(np.uint8),np.ones((61,61),np.uint8))>0
    skin=(r-b>22)&(r>90)
    white=(v>205)|((v>183)&(lstd<9))         # sleeve: bright and smooth; tape strip is grey and speckled
    keep=(skin|white)&near
    keep=cv2.morphologyEx(keep.astype(np.uint8),cv2.MORPH_OPEN,np.ones((7,7),np.uint8))>0
    core=cv2.erode((pm>0.5).astype(np.uint8),np.ones((9,9),np.uint8))>0
    # outside the strip column trust the person mask; inside it only colour decides (removes the strip)
    stripish=(r-b>5)&(v<192)&~skin              # warm grey = tape strip / wall; sleeve shadows are cool
    prot=np.where(band>0, keep|(core&~stripish), keep|core).astype(np.float32)
    prot=cv2.GaussianBlur(prot,(0,0),2.0)
    a=np.maximum(R,(1-valid)*above)*(1-prot)
    o=w*(1-a[...,None])+plate*a[...,None]
    o=cleaner(o,pm)
    c=grain(sharpen(np.clip(o,0,255).astype(np.uint8),amt=0.35),rng)
    p.stdin.write(c.tobytes())
p.stdin.close(); p.wait()
