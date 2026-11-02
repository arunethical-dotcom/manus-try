import numpy as np, sys
from PIL import Image
o=np.load('can_final_A.npy').astype(np.float32); B=np.load('TJB.npy').astype(np.float32)
H,W=o.shape[:2]
LX0,LX1=int(sys.argv[1]),int(sys.argv[2]); RX0,RX1=int(sys.argv[3]),int(sys.argv[4])
Y0,Y1=1858,2546
ea=o[...,3]>0; eb=B[...,3]>0
cost=np.abs(o[...,:3]-B[...,:3]).sum(-1); cost[ea!=eb]=3000.0; cost[~ea&~eb]=0
def seam(x0,x1):
    C=cost[Y0:Y1,x0:x1].copy(); n,mw=C.shape
    D=C.copy(); back=np.zeros((n,mw),np.int8)
    for y in range(1,n):
        prev=D[y-1]; l=np.r_[np.inf,prev[:-1]]; r=np.r_[prev[1:],np.inf]
        st=np.vstack([l,prev,r]); k=st.argmin(0); D[y]+=st[k,np.arange(mw)]; back[y]=k-1
    p=np.zeros(n,int); p[-1]=int(D[-1].argmin())
    for y in range(n-1,0,-1): p[y-1]=np.clip(p[y]+back[y,p[y]],0,mw-1)
    return p+x0, float(D[-1].min())/n
sl,cl=seam(LX0,LX1); sr,cr=seam(RX0,RX1)
print('left seam cost/row',round(cl,1),'right',round(cr,1))
out=o.copy()
X=np.arange(W)[None,:]
for i,y in enumerate(range(Y0,Y1)):
    a_,b_=sl[i],sr[i]
    seg=slice(a_,b_)
    wB=np.ones(b_-a_)
    # 3px blend at both seams
    for k in range(3):
        if k<len(wB): wB[k]=(k+0.5)/3; wB[-1-k]=(k+0.5)/3
    A_=o[y,seg]; B_=B[y,seg]
    m=(A_[:,3]>0)&(B_[:,3]>0)
    r=np.where(m[:,None],A_*(1-wB[:,None])+B_*wB[:,None],np.where((wB[:,None]>=0.5),B_,A_))
    out[y,seg]=r
out=out.clip(0,255).astype(np.uint8); out[...,3]=np.where(out[...,3]>127,255,0)
np.save('can_tj.npy',out)
im=Image.new('RGBA',(W,H),(255,255,255,255)); im.alpha_composite(Image.fromarray(out))
im.crop((480,1840,1060,2560)).convert('RGB').save('tj_res.png')
