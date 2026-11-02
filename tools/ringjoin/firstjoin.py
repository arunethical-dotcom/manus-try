import numpy as np, cv2
from PIL import Image
W=np.load('W.npy'); G=np.load('G.npy')
can6=np.load('can6.npy')
OFF=42                                   # can -> can6 x offset (14 + 28)
sx=57.6/62.25; sy0=256.5/269.0; dy0=-87
Wd=can6.shape[1]-OFF
dxg=2182-round(G.shape[1]*sx)            # left edge of the scaled gate image (right edge = axis 2182)
KW=np.array([173,229,273,330,429],float); KG=np.array([273,332,373,433,542],float)
def pw(t):                                # wall row -> gate row, piecewise linear, uniform outside the knots
    t=np.asarray(t,float)
    v=np.interp(t,KW,KG)
    lo=t<KW[0]; hi=t>KW[-1]
    v[lo]=KG[0]+(t[lo]-KW[0])/sy0; v[hi]=KG[-1]+(t[hi]-KW[-1])/sy0
    return v
H=W.shape[0]
X=np.arange(1300,2183)
T=np.arange(0,H)
u=(X-dxg)/sx
wgt=np.clip((1620-X)/(1620-1460),0,1)
Vu=(T[:,None]-dy0)/sy0
Vp=pw(T)[:,None]
V=(wgt[None,:]*Vp+(1-wgt[None,:])*Vu).astype(np.float32)
# horizontal phase correction per band (can px): rear crenels -4, front crenels +14.6, linear across the walkway
sh=np.where(T<250,-4.0,np.where(T<338,14.6,0.0))
U=((X[None,:]-dxg-sh[:,None]*wgt[None,:])/sx).astype(np.float32)
Gsrc=cv2.resize(G,None,fx=1,fy=1)
R=cv2.remap(Gsrc,U,V,interpolation=cv2.INTER_AREA if False else cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
R[...,3]=np.where(R[...,3]>127,255,0)
# left image: W at can coords
L=np.zeros_like(R); L[:, :max(0,min(W.shape[1],2183)-1300)]=W[:, 1300:min(W.shape[1],2183)]
A=L.astype(np.float32); B=R.astype(np.float32)
ea=A[...,3]>0; eb=B[...,3]>0
cost=np.abs(A[...,:3]-B[...,:3]).sum(-1); cost[ea!=eb]=3000.0; cost[~ea&~eb]=0
xL,xR=1400-1300,1480-1300
C=cost[:,xL:xR].copy(); n,mw=C.shape
D=C.copy(); back=np.zeros((n,mw),np.int8)
for y in range(1,n):
    prev=D[y-1]; l=np.r_[np.inf,prev[:-1]]; r=np.r_[prev[1:],np.inf]
    st=np.vstack([l,prev,r]); k=st.argmin(0); D[y]+=st[k,np.arange(mw)]; back[y]=k-1
path=np.zeros(n,int); path[-1]=int(D[-1].argmin())
for y in range(n-1,0,-1): path[y-1]=np.clip(path[y]+back[y,path[y]],0,mw-1)
seam=path+xL
XX=np.arange(R.shape[1])[None,:]
wB=np.clip((XX-seam[:,None]+1.5)/3.0,0,1)
out=B*wB[...,None]+A*(1-wB[...,None])
oA=ea&~eb; oB=eb&~ea
out[oA&(wB<0.5)]=A[oA&(wB<0.5)]; out[oA&(wB>=0.5)]=0
out[oB&(wB>=0.5)]=B[oB&(wB>=0.5)]; out[oB&(wB<0.5)]=0
out=out.clip(0,255).astype(np.uint8); out[...,3]=np.where(out[...,3]>127,255,0)
new=can6.copy()
new[:H, 1300+OFF:2183+OFF]=out
np.save('can6b.npy',new)
im=Image.new('RGBA',(new.shape[1],new.shape[0]),(255,255,255,255)); im.alpha_composite(Image.fromarray(new))
im.crop((1380,0,1620,480)).resize((480,960),Image.NEAREST).convert('RGB').save('j1.png')
print('seam x range (can6)',seam.min()+1300+OFF,seam.max()+1300+OFF)
