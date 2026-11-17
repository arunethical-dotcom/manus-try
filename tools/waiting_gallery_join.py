import numpy as np, cv2
from PIL import Image
from scipy import ndimage
P={'L':'Pixel-art gallery on magenta.png','M':'Pixel art gallery, magenta backdrop.png','R':'Stone building on magenta backdrop.png'}
def isbg(a): return (a[...,0]>170)&(a[...,2]>170)&(a[...,1]<110)
I={k:np.array(Image.open('wgm/'+v).convert('RGB')).astype(np.float32) for k,v in P.items()}
# the right piece is drawn ~5% narrower (roof tile period 75 px vs 79): stretch it horizontally to match
_r=Image.open('wgm/'+P['R']).convert('RGB'); RW=round(_r.width*79/75)
I['R']=np.array(_r.resize((RW,_r.height),Image.NEAREST)).astype(np.float32)
GAP=int(__import__('os').environ.get('GAP','0'))
# colour match: the side pieces take the middle piece's colours, band by band (stone cap, roof, stonework below),
# per channel gain, interpolated row by row
def bands(a):
    out=[]
    for y0,y1 in ((110,180),(250,780),(1080,1150)):
        r=a[y0:y1,300:1000].reshape(-1,3); out.append(((y0+y1)/2,r.mean(0)))
    return out
BM=bands(I['M'])
for k in ('L','R'):
    BK=bands(I[k]); ys=[b[0] for b in BM]
    g=np.array([bm[1]/bk[1] for bm,bk in zip(BM,BK)])          # 3 bands x 3 channels
    rows=np.arange(I[k].shape[0])
    G=np.stack([np.interp(rows,ys,g[:,c]) for c in range(3)],1)
    bgk=isbg(I[k])
    I[k]=np.where(bgk[...,None],I[k],np.clip(I[k]*G[:,None,:],0,255))
    print(k,'gains',g.round(3).tolist())
for k,a in I.items():
    ys,xs=np.where(~isbg(a)); print(k,'bbox',xs.min(),xs.max(),ys.min(),ys.max())
def edge(A,B):
    a=I[A]; b=I[B]; res=[]
    for dy in range(-20,21):
        rows=np.clip(np.arange(60,1200)+dy,0,1253)
        m=~isbg(a[60:1200,-1])&~isbg(b[rows,0])
        if m.sum()<300: continue
        res.append((round(float(np.abs(a[60:1200,-1]-b[rows,0])[m].mean()),1),dy))
    res.sort(); print(A,B,res[:3]); return res[0][1]
d1=edge('L','M'); d2=edge('M','R')
H=1254+50; OY=20
C=np.full((H,2508+GAP+RW,3),(255,0,255),np.float32)
C[OY:OY+1254,0:1254]=I['L']; C[OY+d1:OY+d1+1254,1254:2508]=I['M']; CR=np.full_like(C,0); CR[...]=(255,0,255); CR[OY+d1+d2:OY+d1+d2+1254,2508+GAP:2508+GAP+RW]=I['R']
EXT=int(__import__('os').environ.get('EXT','0'))      # extend M periodically (one roof period = 79 px back) past its edge
if EXT:
    PER=int(__import__('os').environ.get('PER','79'))
    C[:,2508:2508+EXT]=C[:,2508-PER:2508-PER+EXT]
OV=-GAP+EXT                                           # overlap band: min-error vertical cut
if OV>4:
    xa,xb=2508+GAP,2508+EXT
    E=np.abs(C[:,xa:xb]-CR[:,xa:xb]).sum(-1); E[:,:2]+=1e5; E[:,-2:]+=1e5
    acc=E.copy(); bk=np.zeros(E.shape,np.int8); n=E.shape[1]
    for y in range(1,E.shape[0]):
        p=acc[y-1]; l=np.r_[np.inf,p[:-1]]; r=np.r_[p[1:],np.inf]; st=np.stack([l,p,r]); k=st.argmin(0); acc[y]+=st[k,np.arange(n)]; bk[y]=k-1
    path=np.zeros(E.shape[0],int); path[-1]=int(acc[-1].argmin())
    for y in range(E.shape[0]-1,0,-1): path[y-1]=path[y]+bk[y,path[y]]
    X=np.arange(n)[None,:]; useR=X>=path[:,None]
    Cm=C[:,xa:xb].copy()
    C[:,xa:xb]=np.where(useR[...,None],CR[:,xa:xb],Cm)
    # roof and stone cap: tiles line up here, so cross-fade the two drawings over the whole band (no texture step)
    r0,r1=OY+100,OY+800
    t=np.clip((np.arange(xb-xa)-10)/(xb-xa-20),0,1)[None,:,None]
    okb=~isbg(Cm[r0:r1])&~isbg(CR[r0:r1,xa:xb])
    C[r0:r1,xa:xb]=np.where(okb[...,None],Cm[r0:r1]*(1-t)+CR[r0:r1,xa:xb]*t,C[r0:r1,xa:xb])
    # soft transition from the fade to the cut below the roof
    
    C[:,xb:]=CR[:,xb:]
else:
    C[OY+d1+d2:OY+d1+d2+1254,2508+GAP:2508+GAP+RW]=I['R']
# seam 1 (left | middle): below the roof the pieces already meet edge to edge; the roof is where a texture step showed.
# The left roof is continued past the seam by its own tile period (79 px) and cross-faded into the middle roof
# over 3 tiles, so the tiles run on and the drawing changes gradually.
r0, r1 = OY + 100, OY + 800
n = 237; xa = 1254
src_cols = 1254 - 79 + (np.arange(n) % 79)
LE = C[r0:r1, src_cols].copy(); MM = C[r0:r1, xa:xa + n].copy()
t = np.clip(np.arange(n) / (n - 1), 0, 1)[None, :, None]; t = t * t * (3 - 2 * t)
okb = ~isbg(LE) & ~isbg(MM)
C[r0:r1, xa:xa + n] = np.where(okb[..., None], LE * (1 - t) + MM * t, MM)
bg=isbg(C)
for X in ((1254,) if OV>4 else (1254,2508+GAP)):
    ok=~bg[:,X-6:X].any(1)&~bg[:,X:X+6].any(1)
    a=C[:,X-6:X].mean(1); b=C[:,X:X+6].mean(1); d=np.where(ok[:,None],a-b,0)
    d=ndimage.gaussian_filter1d(d,8,axis=0)
    for k in range(40):
        f=0.5*(1-k/40); mb=~bg[:,X+k]; ma=~bg[:,X-1-k]
        C[mb,X+k]+=d[mb]*f; C[ma,X-1-k]-=d[ma]*f
C=np.clip(C,0,255)
c=C.astype(int); bg=isbg(C)
lab,n=ndimage.label(~bg); sz=ndimage.sum(~bg,lab,range(1,n+1)); fg=lab==(1+np.argmax(sz))
# despill magenta fringe
edge_=fg&~ndimage.binary_erosion(fg,iterations=2)
spill=edge_&(c[...,0]-c[...,1]>50)&(c[...,2]-c[...,1]>50)
fg&=~(spill&~ndimage.binary_erosion(fg,iterations=1))
inner=fg&~spill; _,(iy,ix)=ndimage.distance_transform_edt(~inner,return_indices=True)
m=spill&fg; C[m]=C[iy[m],ix[m]]
ys,xs=np.where(fg)
out=np.dstack([C,fg*255]).astype(np.uint8)[ys.min():ys.max()+1,xs.min():xs.max()+1]
Image.fromarray(out).save('waiting_gallery_joined.png'); print(out.shape,'offsets',d1,d2,'x0',xs.min())
bg_=Image.new('RGBA',(out.shape[1],out.shape[0]),(96,150,60,255)); bg_.alpha_composite(Image.fromarray(out)); bg_=bg_.convert('RGB')
bg_.resize((out.shape[1]//3,out.shape[0]//3)).save('wg_s.png')
x1=1254-xs.min(); x2=2508+GAP-xs.min()
s=Image.new('RGB',(840,out.shape[0]),(255,255,255))
s.paste(bg_.crop((x1-100,0,x1+100,out.shape[0])).resize((400,out.shape[0])),(0,0)); s.paste(bg_.crop((x2-100,0,x2+100,out.shape[0])).resize((400,out.shape[0])),(440,0)); s.save('wg_seams.png')
