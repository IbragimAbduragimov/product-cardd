import cv2, numpy as np
class BGCleaner:
    """Removes compression blotches from the dark-navy backdrop: replaces backdrop pixels
    with a smooth, temporally stable version of themselves (person/objects untouched)."""
    def __init__(self, sigma=30, ema=0.85):
        self.sigma=sigma; self.ema=ema; self.prev=None
    def key(self, f):
        b,g,r=f[...,0],f[...,1],f[...,2]
        k=np.clip((b-r-2)/8,0,1)*np.clip((135-b)/30,0,1)*np.clip((b-g+2)/6,0,1)
        return k
    def __call__(self, f, person):
        h,w=f.shape[:2]
        k=self.key(f)
        core=cv2.erode((person>0.5).astype(np.uint8),np.ones((9,9),np.uint8)).astype(np.float32)
        core=cv2.GaussianBlur(core,(0,0),2)
        k=cv2.GaussianBlur(k*(1-core),(0,0),1.2)
        s=4; small=cv2.resize(f*k[...,None],(w//s,h//s),interpolation=cv2.INTER_AREA)
        ks=cv2.resize(k,(w//s,h//s),interpolation=cv2.INTER_AREA)
        sg=self.sigma/s
        num=cv2.GaussianBlur(small,(0,0),sg); den=cv2.GaussianBlur(ks,(0,0),sg)[...,None]
        plate=num/np.maximum(den,1e-3)
        plate=cv2.resize(plate,(w,h),interpolation=cv2.INTER_CUBIC)
        if self.prev is not None: plate=self.ema*self.prev+(1-self.ema)*plate
        self.prev=plate
        return f*(1-k[...,None])+plate*k[...,None]
def grain(img_u8, rng, std=1.6):
    n=rng.normal(0,std,img_u8.shape[:2]).astype(np.float32)
    n=cv2.GaussianBlur(n,(0,0),0.6)*1.3
    return np.clip(img_u8.astype(np.float32)+n[...,None],0,255).astype(np.uint8)
def sharpen(img_u8, amt=0.45, sigma=1.4):
    bl=cv2.GaussianBlur(img_u8,(0,0),sigma)
    return cv2.addWeighted(img_u8,1+amt,bl,-amt,0)
ENC=['-c:v','libx264','-preset','slow','-crf','16','-tune','film','-x264-params','aq-mode=3:aq-strength=1.0',
     '-maxrate','6M','-bufsize','12M','-pix_fmt','yuv420p','-profile:v','high','-c:a','aac','-b:a','192k','-movflags','+faststart']
