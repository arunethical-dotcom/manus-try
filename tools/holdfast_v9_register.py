import numpy as np, cv2, json
from PIL import Image
f={'tl':'Magenta castle tower detail.png','tr':'Blue-roofed Gothic castle on magenta.png','bl':'Crenellated Tower and Gothic Keep.png','br':'Gothic Castle Tower and Blue Roofs.png'}
I={k:np.array(Image.open('hf2/'+v).convert('RGB')) for k,v in f.items()}
def mask(a): return ~((a[...,0]>190)&(a[...,1]<90)&(a[...,2]>190))
sift=cv2.SIFT_create(20000)
KD={k:sift.detectAndCompute(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY),cv2.erode(mask(a).astype(np.uint8)*255,np.ones((7,7)))) for k,a in I.items()}
def est(a,b):
    ka,da=KD[a]; kb,db=KD[b]
    m=cv2.BFMatcher().knnMatch(db,da,k=2); good=[x for x,y in m if x.distance<0.7*y.distance]
    src=np.float32([kb[g.queryIdx].pt for g in good]); dst=np.float32([ka[g.trainIdx].pt for g in good])
    T,inl=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=1.5,maxIters=50000,confidence=0.999)
    s=np.hypot(T[0,0],T[1,0]); print(a,b,'good',len(good),'inl',int(inl.sum()),'s',round(s,4),'rot',round(np.degrees(np.arctan2(T[1,0],T[0,0])),2),'t',T[:,2].round(1))
    return np.vstack([T,[0,0,1]])
R={}
for a,b in (('tl','tr'),('tl','bl'),('tr','br'),('bl','br'),('tl','br')): R[a+b]=est(a,b).tolist()
json.dump(R,open('hf2_T.json','w'))
