import json, numpy as np, cv2
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
S='/tmp/claude-0/-home-claude/e59396bc-cfb6-5546-9a15-3ded7e6db8e8/scratchpad/col2'
A=np.load(S+'/A.npy'); RGB=np.load(S+'/RGB.npy'); WH,WW=A.shape
def P(c):
    p=Polygon(c).buffer(0); return p if p.geom_type=='Polygon' else max(p.geoms,key=lambda g:g.area)
Lj=json.load(open(S+'/lines.json')); parts=[]
for sd in ('west','east'):
    inn=np.array(Lj['inner_'+sd]); out=np.array(Lj['outer_'+sd]); inn=inn[np.argsort(inn[:,0])]

    parts.append(P(list(map(tuple,inn))+list(map(tuple,out[::-1]))))
So=json.load(open(S+'/south_polys.json')); parts+= [P(So['south-west']),P(So['south-east'])]
# west / east side walls left out
U=unary_union(parts)
R=70
corners=[box(900,1350,1600,2150),box(WW-1601,1350,WW-901,2150),box(500,3150,1450,3950),box(WW-1451,3150,WW-501,3950)]
cl=U.buffer(R,join_style=1).buffer(-R,join_style=1)

U=U.buffer(-6,quad_segs=10).buffer(6,quad_segs=10)
polys=[U] if U.geom_type=='Polygon' else list(U.geoms)
polys=[p for p in polys if p.area>500]
json.dump([[list(map(lambda v:round(v,1),c)) for c in p.exterior.coords] for p in polys],open(S+'/ring_polys.json','w'))
print('pieces',len(polys),[round(p.area) for p in polys])
# seal check with Kael's box (12x6) on a 4 px grid
K=4; m=np.zeros((WH,WW),np.uint8)
for p in polys: cv2.fillPoly(m,[np.round(np.array(p.exterior.coords)).astype(np.int32)],1)
bk=cv2.dilate(m,np.ones((7,13),np.uint8))[::K,::K]
L=json.load(open('/home/claude/manus-try/data/layout.json'))
n,lab=cv2.connectedComponents((1-bk).astype(np.uint8),connectivity=4)
ins=L['inside']; sp=L['spawn']
print('gates open (inside reaches spawn):',lab[ins[1]//K,ins[0]//K]==lab[sp[1]//K,sp[0]//K])
plug=bk.copy()
for g in L['gates'].values(): gx,gy=g[0]//K,g[1]//K; plug[gy-130:gy+14,gx-30:gx+31]=1
n2,l2=cv2.connectedComponents((1-plug).astype(np.uint8),connectivity=4)
print('sealed without gates:',l2[ins[1]//K,ins[0]//K]!=l2[2,2])
X0,Y0,X1,Y1=560,560,7330,4430
im=np.zeros((Y1-Y0,X1-X0,3),np.uint8); im[:]=(90,150,60); a=A[Y0:Y1,X0:X1]; im[a]=RGB[Y0:Y1,X0:X1][a]
I=Image.fromarray(im).convert('RGBA'); ov=Image.new('RGBA',I.size,(0,0,0,0)); d=ImageDraw.Draw(ov)
for p in polys:
    q=[(x-X0,y-Y0) for x,y in p.exterior.coords]; d.polygon(q,fill=(255,0,0,85)); d.line(q,fill=(255,230,0,255),width=8)
I.alpha_composite(ov); I=I.convert('RGB'); I.resize((I.width//3,I.height//3),Image.LANCZOS).save(S+'/ring_all.png')
I.crop((700-X0,800-Y0,2300-X0,2200-Y0)).resize((800,700)).save(S+'/c_nw.png'); I.crop((500-X0,3150-Y0,1500-X0,4000-Y0)).save(S+'/c_sw.png')
