"""Clean backdrop plate = per-pixel temporal median over frames where that pixel shows backdrop.
Compression blotches differ frame to frame, the real fabric doesn't -> median keeps real texture."""
import cv2, numpy as np, sys
sys.path.insert(0,'work'); from seg import person
from cleanbg import BGCleaner
src, tfile, out = sys.argv[1], sys.argv[2], sys.argv[3]
W,H=720,1280
cap=cv2.VideoCapture(src); n=int(cap.get(7))
Ts=None
if tfile!='none':
    T=np.load(tfile).reshape(-1,6); k=15; pad=np.pad(T,((k//2,k//2),(0,0)),mode='edge')
    Ts=np.array([pad[i:i+k].mean(0) for i in range(len(T))]).reshape(-1,2,3)
key=BGCleaner().key
idx=np.linspace(20,n-20,140).astype(int)
stack=np.zeros((len(idx),H,W,3),np.uint8); have=np.zeros((len(idx),H,W),bool)
for j,i in enumerate(idx):
    cap.set(1,i); ok,f=cap.read()
    if Ts is not None:
        f=cv2.warpAffine(f,Ts[i],(W,H),flags=cv2.INTER_LANCZOS4,borderValue=0)
        valid=cv2.warpAffine(np.ones((H,W),np.float32),Ts[i],(W,H))>0.99
    else: valid=np.ones((H,W),bool)
    f=f.astype(np.float32)
    pm=cv2.dilate(person(np.clip(f,0,255).astype(np.uint8)),np.ones((15,15)))
    ok_=(key(f)>0.9)&(pm<0.2)&valid
    ok_=cv2.erode(ok_.astype(np.uint8),np.ones((5,5),np.uint8))>0
    stack[j][ok_]=np.clip(f[ok_],0,255).astype(np.uint8); have[j]=ok_
cnt=have.sum(0); good=cnt>=8
plate=np.zeros((H,W,3),np.float32)
for y in range(0,H,64):
    st=stack[:,y:y+64].astype(np.float32); st[~have[:,y:y+64]]=np.nan
    with np.errstate(all='ignore'): plate[y:y+64]=np.nan_to_num(np.nanmedian(st,axis=0))
print('coverage',good.mean())
g=good.astype(np.float32); p0=plate*g[...,None]; fill=p0.copy(); done=good.copy()
for sg in [6,15,40,100,250]:
    num=cv2.GaussianBlur(p0,(0,0),sg); den=cv2.GaussianBlur(g,(0,0),sg)
    m=(~done)&(den>0.01); fill[m]=num[m]/den[m][:,None]; done|=m
np.save(out,fill.astype(np.float32)); np.save(out.replace('.npy','_good.npy'),good)
cv2.imwrite(out.replace('.npy','.png'),np.clip(fill,0,255).astype(np.uint8))
