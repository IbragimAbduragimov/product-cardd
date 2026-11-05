"""Small handle 'abduragimov_cvs' exactly where the ending template expects it (template's own letters/position),
shown only where no infographic is on screen; must be present at the end, where the template picks it up."""
import sys, os, numpy as np, cv2
sys.path.insert(0, sys.argv[1]); from add_ending import Ending
out=sys.argv[2]; os.makedirs(out,exist_ok=True)
E=Ending(1080,1920); a=E.rest_alpha[:960]
T0,FPS,N=1.40,30,3450
def ease(u): u=min(max(u,0),1); return u*u*(3-2*u)
SHOW=[(53.95,60.05),(114.52,999)]          # front-camera seconds
for i in range(N):
    t=T0+i/FPS; v=0
    for s,e in SHOW: v=max(v,ease((t-s)/0.4)*(1-ease((t-e)/0.4)))
    if v<=0: continue
    img=np.zeros((960,1080,4),np.uint8); img[...,:3]=255; img[...,3]=np.clip(a*v*255+0.5,0,255).astype(np.uint8)
    cv2.imwrite(f'{out}/{i:05d}.png',img)
print('frames',len(os.listdir(out)))
