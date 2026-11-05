import cv2, numpy as np, subprocess, sys
sys.path.insert(0,'work'); from seg import person
from cleanbg import BGCleaner, grain, sharpen, ENC
cleaner=BGCleaner()
SRC='videos/VID_20261105_144306_140.mp4.mov'
start=int(sys.argv[1]); count=int(sys.argv[2]); out=sys.argv[3]
W,H=720,1280
T=np.load('work/T.npy').reshape(-1,6)
# smooth transforms (moving average, 15 frames)
k=15; pad=np.pad(T,((k//2,k//2),(0,0)),mode='edge')
Ts=np.array([pad[i:i+k].mean(0) for i in range(len(T))]).reshape(-1,2,3)
cols=np.load('work/cols.npy')
# vertical profile for blue fill
prof=cols.copy(); prof[:40]=prof[40]; prof[680:]=prof[680]
prof=cv2.GaussianBlur(prof.reshape(-1,1,3),(1,0),sigmaX=0.1,sigmaY=20).reshape(-1,3)
xs=np.arange(W,dtype=np.float32)
hfac=np.where(xs<170,1-0.10*(170-xs)/170,1.0)
plate=prof[:,None,:]*hfac[None,:,None]
# real fabric texture from median of backdrop
cap=cv2.VideoCapture(SRC); fr=[]
for i in range(100,3351,250):
    cap.set(1,i); ok,f=cap.read(); fr.append(cv2.warpAffine(f,Ts[i],(W,H)).astype(np.float32))
med=np.median(np.array(fr),0)
patch=med[20:520,180:350]; det=patch-cv2.GaussianBlur(patch,(0,0),12)
tile=np.concatenate([det,det[::-1]],0); tile=np.concatenate([tile,tile[:,::-1]],1)
reps=(H//tile.shape[0]+1,W//tile.shape[1]+1,1)
tex=np.tile(tile,reps)[:H,:W]
plate=plate+tex*0.9
# replace region: left of backdrop edge, above table back edge
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
tableline=720+0.18*xx
R=((xx<174)&(yy<tableline-1)).astype(np.float32)
R=cv2.GaussianBlur(R,(0,0),2.5)
above=(yy<tableline-1).astype(np.float32)
CX,CY,CW,CH=60,15,585,1040
cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s','1080x1920','-r','30','-i','-',
     '-ss',str(start/30),'-t',str(count/30),'-i',SRC,'-map','0:v','-map','1:a',
     *ENC,'-shortest',out]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
cap.set(1,start); pm=None; rng=np.random.default_rng(0)
ones=np.ones((H,W),np.float32)
for i in range(start,start+count):
    ok,f=cap.read()
    if not ok: break
    M=Ts[min(i,len(Ts)-1)]
    w=cv2.warpAffine(f,M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    valid=cv2.warpAffine(ones,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=0)
    valid=cv2.erode(valid,np.ones((5,5)))
    pmask=person(np.clip(w,0,255).astype(np.uint8))
    pmask=cv2.dilate(pmask,np.ones((5,5)))
    pmask=cv2.GaussianBlur(pmask,(0,0),1.5)
    pm=pmask if pm is None else 0.5*pm+0.5*pmask
    pm[:320]=0
    b,g,r=w[...,0],w[...,1],w[...,2]
    near=cv2.dilate((pm>0.3).astype(np.uint8),np.ones((41,41),np.uint8))>0
    keep=(((r-b>22)&(r>90)) | ((b+g+r)/3>215)) & near
    keep=cv2.GaussianBlur(cv2.dilate(keep.astype(np.float32),np.ones((5,5))),(0,0),1.5)
    prot=np.clip(np.maximum(pm*1.2,keep),0,1)
    a=np.maximum(R,(1-valid)*above)*(1-prot)
    fill=plate+rng.normal(0,1.3,(H,W,1)).astype(np.float32)
    o=w*(1-a[...,None])+fill*a[...,None]
    o=cleaner(o,pm)
    c=o[CY:CY+CH,CX:CX+CW]
    c=cv2.resize(np.clip(c,0,255).astype(np.uint8),(1080,1920),interpolation=cv2.INTER_LANCZOS4)
    c=grain(sharpen(c),rng)
    p.stdin.write(c.tobytes())
p.stdin.close(); p.wait()
