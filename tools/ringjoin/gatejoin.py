import sys, numpy as np, cv2
from PIL import Image
src=sys.argv[1]
a=np.array(Image.open(src).convert('RGB')); c=a.astype(int)
mag=(c[...,0]-c[...,1]>60)&(c[...,2]-c[...,1]>60)
al=(~mag).astype(np.uint8)*255; al=cv2.morphologyEx(al,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
G=np.dstack([a,al])[:, :1369]   # true symmetry axis of the gate (merlon centre / arch apex) at x=1368
can=np.load('canQ2.npy')
def starts(im,x0,x1,ylo,yhi):
    m=im[...,3]>0
    t=np.array([(np.nonzero(m[ylo:yhi,x])[0].min()+ylo) if m[ylo:yhi,x].any() else 99999 for x in range(x0,x1)])
    v=t[t<99999]; lo,hi=np.percentile(v,5),np.percentile(v,95); up=t<(lo+hi)/2
    return [x0+i for i in range(1,len(up)) if up[i] and not up[i-1]], lo
s2,top2=starts(G,0,480,400,1000); P=float(np.median(np.diff(s2))); print('piece crenels',s2,'period',P,'top',top2)
gx=np.nonzero((G[...,3]>0).any(0))[0]; print('piece opaque x',gx.min(),gx.max(),'width',G.shape[1])
k0=s2[1]
s=(2444-2092)/(976-top2)            # wall height of the gate piece = wall height of the south wall
KFLAT=float(sys.argv[2]) if len(sys.argv)>2 else 1.0     # horizontal squeeze of the flat wall stretch only
FL=400                                # native: flat wall [0,FL) ; the step, towers and arch are never resized
TS,TP=15,292                           # exact seamless tile of the flat wall: columns [15,307), period 292 (measured), includes the buttresses
for nper in range(1,20):
    flat=np.concatenate([G[:,TS:TS+TP]]*nper+[G[:,TS:FL]],axis=1)
    fw=max(1,int(round(flat.shape[1]*KFLAT)))
    flat=cv2.resize(flat,(fw,flat.shape[0]),interpolation=cv2.INTER_AREA)
    flat[...,3]=np.where(flat[...,3]>127,255,0)
    ext=np.concatenate([flat,G[:,FL:]],axis=1)
    if 2223-ext.shape[1]*s<=790: break
Gs=cv2.resize(ext,None,fx=s,fy=s,interpolation=cv2.INTER_AREA); Gs[...,3]=np.where(Gs[...,3]>127,255,0)
gxs=np.nonzero((Gs[...,3]>0).any(0))[0]
AX=2223; ox=AX-gxs.max(); oy=int(round(2092-top2*s))
print('scale',s,'ox',ox,'oy',oy,'nper',nper,'tile bounds',[round(ox+i*TP*s*KFLAT,1) for i in range(nper+1)])
H=max(can.shape[0],oy+Gs.shape[0])+20; W=can.shape[1]
A=np.zeros((H,W,4),np.float32); B=np.zeros((H,W,4),np.float32)
A[:can.shape[0]]=can
x0=max(0,ox); B[oy:oy+Gs.shape[0],x0:ox+Gs.shape[1]]=Gs[:,x0-ox:]
ea=A[...,3]>0; eb=B[...,3]>0
yT=1850; xL,xR=812,880
cost=np.abs(A[...,:3]-B[...,:3]).sum(-1); cost[ea!=eb]=2000.0; cost[~ea&~eb]=0
C=cost[yT:,xL:xR].copy(); n,mw=C.shape
D=C.copy(); back=np.zeros((n,mw),np.int8)
for y in range(1,n):
    prev=D[y-1]; l=np.r_[np.inf,prev[:-1]]; r=np.r_[prev[1:],np.inf]
    st=np.vstack([l,prev,r]); k=st.argmin(0); D[y]+=st[k,np.arange(mw)]; back[y]=k-1
path=np.zeros(n,int); path[-1]=int(D[-1].argmin())
for y in range(n-1,0,-1): path[y-1]=np.clip(path[y]+back[y,path[y]],0,mw-1)
seamx=np.full(H,xL); seamx[yT:]=path+xL      # above yT: the gate piece owns everything right of xL
X=np.arange(W)[None,:]
wB=np.clip((X-seamx[:,None]+1.5)/3.0,0,1)
out=B*wB[...,None]+A*(1-wB[...,None])
onlyA=ea&~eb; onlyB=eb&~ea
keepA_top=onlyA&(np.arange(H)[:,None]<yT)   # old content far above (side walls) stays
out[onlyA&(wB<0.5)]=A[onlyA&(wB<0.5)]; out[onlyA&(wB>=0.5)]=0
out[keepA_top]=A[keepA_top]
out[onlyB&(wB>=0.5)]=B[onlyB&(wB>=0.5)]; out[onlyB&(wB<0.5)]=0
Y=np.arange(H)[:,None]
band=(Y>=yT)&(X>=780)&(X<822)
right=(Y>=yT)&(X>=780)&(X<900)
out[right&eb]=B[right&eb]
out[right&~eb]=0
# the south tower (old image) drawn whole on top. It is round and symmetric about x=744.5; its left outline is clean
# (sky behind), so the right outline = mirrored left outline, row by row.
Ai_=A.astype(int); dark=(Ai_[...,:3].sum(-1)<160)&ea
tow=np.zeros((H,W),bool)
cxT=744.5; prevL=None
Ls={}; 
for y in range(1990,H):
    xs=np.nonzero(dark[y,648:705])[0]
    if len(xs): L=648+xs.min()
    elif prevL is not None: L=prevL
    else: continue
    if prevL is not None and abs(L-prevL)>6 and y>2135: L=prevL
    prevL=L
    if ea[y,int(cxT)]: Ls[y]=L
ys_=np.array(sorted(Ls)); Lv=np.array([Ls[y] for y in ys_],float)
from scipy.ndimage import median_filter
Lm=Lv.copy(); sel=ys_>=2200; Lm[sel]=median_filter(Lv[sel],size=11,mode='nearest')
Rmap={}
Rraw=[]
for y,L in zip(ys_,Lm):
    L=int(round(L)); R=int(round(2*cxT-L))
    if y<2150: R=min(R,838)
    elif y<2168: R=838-(y-2150)
    elif y<2430: R=821                                     # straight cylinder body
    else: R=int(round(2*cxT-(665+(y-2430)*34/28)))          # rounded bottom (mirror of left outline 665->699)
    Rraw.append(R)
Rraw=np.array(Rraw,float); sel2=ys_>=2200
for y,L,R in zip(ys_,Lm,Rraw):
    L=int(round(L)); R=int(round(R)); Rmap[int(y)]=R
    tow[y,L:R+1]=ea[y,L:R+1]
tow&=(np.arange(H)[:,None]>=yT)
gry=(abs(Ai_[...,0]-Ai_[...,1])<16)&(abs(Ai_[...,1]-Ai_[...,2])<20)&(Ai_[...,:3].sum(-1)>200)
tow_=tow
out[tow]=A[tow]
# continuous outline along the tower's right edge (below the roof), in the tower's own outline colour
dk=A[...,:3][dark&tow]
oc=np.median(dk,axis=0) if len(dk) else np.array([30,22,24],np.float32)
for y,R in Rmap.items():
    if y<2150 or y<yT: continue
    out[y,R-1:R+1,:3]=oc; out[y,R-1:R+1,3]=255
out=out.clip(0,255).astype(np.uint8); out[...,3]=np.where(out[...,3]>127,255,0)
# fill pin-holes at the junction: transparent pixels enclosed by opaque ones
reg=out[yT:, 760:920]
al=(reg[...,3]>0).astype(np.uint8)
closed=cv2.morphologyEx(al,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
holes=(closed>0)&(al==0)
if holes.any():
    src=reg.copy()
    for _ in range(4):
        dil=cv2.dilate(src,np.ones((3,3),np.uint8))
        m=holes&(src[...,3]==0)
        src[m]=dil[m]
    reg[holes]=src[holes]; reg[holes,3]=255
print('holes filled',int(holes.sum()))
np.save('can6.npy',out); np.save('B6.npy',B[...,3]); np.save('B6c.npy',B[...,:3].astype(np.uint8)); np.save('A6.npy',A[...,3])
m=out[...,3]>0; xs=np.nonzero(m.any(0))[0]; ys=np.nonzero(m.any(1))[0]; print('content x',xs.min(),xs.max())
c=out[ys.min():ys.max()+1,xs.min():xs.max()+1]
img=Image.new('RGBA',(c.shape[1]+80,c.shape[0]+80),(255,255,255,255)); img.alpha_composite(Image.fromarray(c),(40,40))
img.convert('RGB').save('joined_gate.png')
full=np.concatenate([c,c[:, -2::-1]],axis=1)
f=Image.new('RGBA',(full.shape[1]+80,full.shape[0]+80),(255,255,255,255)); f.alpha_composite(Image.fromarray(full),(40,40))
f.convert('RGB').save('ring_full.png')
w,h=f.size; f.crop((w//2-800,h-900,w//2+800,h)).convert('RGB').save('south_gate_zoom.png')
img.crop((500,img.size[1]-800,1300,img.size[1])).convert('RGB').save('seam6_zoom.png')
