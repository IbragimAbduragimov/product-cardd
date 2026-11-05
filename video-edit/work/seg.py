import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
opt=vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path='models/selfie.tflite'),running_mode=vision.RunningMode.IMAGE,output_confidence_masks=True)
seg=vision.ImageSegmenter.create_from_options(opt)
def person(bgr):
    rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    r=seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb)))
    m=r.confidence_masks[-1].numpy_view()
    return cv2.resize(m,(bgr.shape[1],bgr.shape[0]))
if __name__=='__main__':
    im=cv2.imread('frames/ref.png'); m=person(im)
    print(m.shape,m.min(),m.max(),len(seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(im[:,:,::-1]))).confidence_masks))
    vis=im.copy(); vis[m<0.5]//=3
    cv2.imwrite('frames/seg.png',vis)
