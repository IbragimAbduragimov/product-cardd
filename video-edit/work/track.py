import cv2, numpy as np, sys
cap=cv2.VideoCapture(sys.argv[1]); n=int(cap.get(7))
orb=cv2.ORB_create(3000)
bf=cv2.BFMatcher(cv2.NORM_HAMMING)
# static-ish regions mask: exclude person center region roughly
def feats(g):
    m=np.full(g.shape,255,np.uint8)
    m[300:900,180:620]=0  # person area
    return orb.detectAndCompute(g,m)
cap.set(1,1500); ok,ref=cap.read(); rg=cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY)
kr,dr=feats(rg)
cap.set(1,0)
T=[]
for i in range(n):
    ok,f=cap.read()
    if not ok: break
    g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
    k,d=feats(g)
    ms=bf.knnMatch(d,dr,k=2)
    good=[a for a,b in ms if a.distance<0.75*b.distance]
    src=np.float32([k[m.queryIdx].pt for m in good]); dst=np.float32([kr[m.trainIdx].pt for m in good])
    M,inl=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=2.0)
    T.append(M.flatten()); 
    if i%300==0: print(i,len(good),int(inl.sum()),np.round(M,3).tolist(),flush=True)
np.save(sys.argv[2],np.array(T))
