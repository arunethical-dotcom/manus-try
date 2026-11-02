import numpy as np, sys
from PIL import Image
o=np.load('/tmp/j/can6b.npy')
Y1=int(sys.argv[1]) if len(sys.argv)>1 else 92
X0=2206
for x in range(X0,2224):
    o[40:Y1,x]=o[40:Y1,2159+(x-X0)]
Y2=int(sys.argv[2]) if len(sys.argv)>2 else 160
for x in range(2209,2224):
    o[112:Y2,x]=o[112:Y2,2166+(x-2209)]
np.save('/tmp/j/can7.npy',o)
a=o[...,3]>0; xs=np.nonzero(a.any(0))[0]; ys=np.nonzero(a.any(1))[0]
c=o[ys.min():ys.max()+1,xs.min():xs.max()+1]
full=np.concatenate([c,c[:, -2::-1]],axis=1)
f=Image.new('RGBA',(full.shape[1]+80,full.shape[0]+80),(255,255,255,255)); f.alpha_composite(Image.fromarray(full),(40,40))
f.convert('RGB').save('/tmp/j/ring_full.png')
img=Image.new('RGBA',(c.shape[1]+80,c.shape[0]+80),(255,255,255,255)); img.alpha_composite(Image.fromarray(c),(40,40)); img.convert('RGB').save('/tmp/j/joined_gate.png')
w=f.size[0]//2
f.crop((w-260,0,w+260,380)).resize((1040,760),Image.NEAREST).convert('RGB').save('/tmp/j/n_centre.png')
