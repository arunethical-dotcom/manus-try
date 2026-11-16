import numpy as np, cv2, json, sys, os
os.chdir(sys.argv[1]); OUT=sys.argv[2]
from PIL import Image
f={'tl':'Magenta castle tower detail.png','tr':'Blue-roofed Gothic castle on magenta.png','bl':'Crenellated Tower and Gothic Keep.png','br':'Gothic Castle Tower and Blue Roofs.png'}
R={k:np.array(v) for k,v in json.load(open('hf2_T.json')).items()}
A=R['tltr']@R['trbr']; B=R['tlbr']; Tbr=(A+B)/2
T={'tl':np.eye(3),'tr':R['tltr'],'bl':R['tlbl'],'br':Tbr}
W,H=2400,2600; OX,OY=40,40
off=np.array([[1,0,OX],[0,1,OY],[0,0,1]],float)
L={}
for k,v in f.items():
    a=np.array(Image.open('hf2/'+v).convert('RGB')).astype(np.float32)
    m=(~((a[...,0]>190)&(a[...,1]<90)&(a[...,2]>190))).astype(np.float32)
    M=(off@T[k])[:2]
    C=cv2.warpAffine(a,M,(W,H),flags=cv2.INTER_LANCZOS4,borderValue=(0,0,0))
    mm=cv2.warpAffine(m,M,(W,H),flags=cv2.INTER_LINEAR)>0.5
    valid=cv2.warpAffine(np.ones(a.shape[:2],np.float32),M,(W,H),flags=cv2.INTER_NEAREST)>0.5
    mm=cv2.erode(mm.astype(np.uint8),np.ones((3,3)))>0
    valid=cv2.erode(valid.astype(np.uint8),np.ones((9,9)))>0          # no black resampling border at piece edges
    mm&=valid
    L[k]=(C,mm,valid)
def mincut(E):
    acc=E.copy(); bk=np.zeros(E.shape,np.int8); n=E.shape[1]
    for y in range(1,E.shape[0]):
        p=acc[y-1]; l=np.r_[np.inf,p[:-1]]; r=np.r_[p[1:],np.inf]
        st=np.stack([l,p,r]); k=st.argmin(0); acc[y]+=st[k,np.arange(n)]; bk[y]=k-1
    path=np.zeros(E.shape[0],int); path[-1]=int(acc[-1].argmin())
    for y in range(E.shape[0]-1,0,-1): path[y-1]=path[y]+bk[y,path[y]]
    return path
FORCE=None
def join_lr(P,Q):
    (ca,ma,va),(cb,mb,vb)=P,Q
    both=va&vb; cols=np.where(both.any(0))[0]; x0,x1=cols.min()+6,cols.max()-6
    E=np.abs(ca[:,x0:x1]-cb[:,x0:x1]).sum(-1)
    E=np.where(ma[:,x0:x1]&mb[:,x0:x1],E,np.where(ma[:,x0:x1]!=mb[:,x0:x1],900.0,0.0))
    E=np.where(both[:,x0:x1],E,np.where(va[:,x0:x1],np.where(np.arange(x1-x0)[None,:]>(x1-x0)/2,1e6,0),np.where(np.arange(x1-x0)[None,:]<(x1-x0)/2,1e6,0)))
    if FORCE is not None:                       # region that must come from the second piece
        E=E+np.where(FORCE[:,x0:x1],1e7,0)
    p=mincut(E.astype(np.float64))
    X=np.arange(W)[None,:]; useB=X>=(x0+p)[:,None]
    useB=np.where(vb&~va,True,np.where(va&~vb,False,useB))
    C=np.where(useB[...,None],cb,ca); M=np.where(useB,mb,ma); V=va|vb
    return C,M,V
def tr(P): return tuple(x.transpose(1,0,2) if x.ndim==3 else x.T for x in P)
top=join_lr(L['tl'],L['tr']); bot=join_lr(L['bl'],L['br'])
# the front-right round tower's top must come whole from the bottom-right piece (the cut crossed its battlements)
bc,bm,bv=bot; tc,tm,tv=top
FORCE=np.zeros((H,W),bool)
U=L['tl'][1]|L['tr'][1]|L['bl'][1]|L['br'][1]; uy,ux=np.where(U); cy0,cx0=uy.min(),ux.min()
FT=np.zeros((H,W),bool); FT[1100+cy0:, 1250+cx0:1560+cx0]=True; FT[1060+cy0:, 1560+cx0:1745+cx0]=True
FORCE_T=FT.T
FORCE=FORCE_T
W0=W; W=H; full=tr(join_lr(tr(top),tr(bot))); W=W0
C,M,V=full
ys,xs=np.where(M); C=C[ys.min():ys.max()+1,xs.min():xs.max()+1]; M=M[ys.min():ys.max()+1,xs.min():xs.max()+1]
out=np.dstack([np.clip(C,0,255),M*255]).astype(np.uint8)
Image.fromarray(out).save(OUT); print(out.shape)
bg=Image.new('RGBA',(out.shape[1],out.shape[0]),(60,90,50,255)); bg.alpha_composite(Image.fromarray(out)); bg=bg.convert('RGB')
bg.resize((out.shape[1]//3,out.shape[0]//3)).save('hf9_s.png'); bg.save('hf9_bg.png')
# east block, lower right window: a cut crossed its right pane -> copy of its left-hand neighbour (68 px left)
a=np.array(Image.open(OUT)).astype(np.float32)
y0,y1,x0,x1,dx=1093,1185,1604,1676,-68
src=a[y0:y1,x0+dx:x1+dx].copy(); dst=a[y0:y1,x0:x1]; h,w=src.shape[:2]
fy=np.clip(np.minimum(np.arange(h),h-1-np.arange(h))/3.0,0,1)[:,None]; fx=np.clip(np.minimum(np.arange(w),w-1-np.arange(w))/3.0,0,1)[None,:]
f=(fy*fx)[...,None]; a[y0:y1,x0:x1]=src*f+dst*(1-f)
Image.fromarray(a.astype(np.uint8)).save(OUT)
bg=Image.new('RGBA',(a.shape[1],a.shape[0]),(60,90,50,255)); bg.alpha_composite(Image.fromarray(a.astype(np.uint8))); bg.convert('RGB').save('hf9_bg.png')
