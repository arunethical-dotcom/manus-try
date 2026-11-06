import json, sys, numpy as np, cv2
sys.path.insert(0,'/home/claude/manus-try/tools')
import build_levels_polys as PP
S='/tmp/claude-0/-home-claude/e59396bc-cfb6-5546-9a15-3ded7e6db8e8/scratchpad/col2'
ROOT='/home/claude/manus-try'
L=json.load(open(ROOT+'/data/layout.json')); WW,WH=L['world']
ID=np.load(S+'/ID.npy')
m=np.zeros((WH,WW),np.uint8)
for p in json.load(open(S+'/ring_polys.json')): cv2.fillPoly(m,[np.round(np.array(p)).astype(np.int32)],1)
secids=ID.copy()
for _ in range(40): secids=np.where(secids==0,cv2.dilate(secids,np.ones((9,9),np.uint8)),secids)
ground=PP.section_polys(m.astype(bool),secids,"ground",384,22)
L['colliders']['ground']=ground
gm=np.zeros((WH,WW),np.uint8)
for p in ground: cv2.fillPoly(gm,[np.array(p['poly'],np.int32)],1)
bk=cv2.dilate(gm,np.ones((15,21),np.uint8))
for a in L['access']:
    x,y=a['ground']; d=-1 if a['gate']=='south' else 1; k=0
    while (bk[y,x] or bk[y-6,x]) and k<200: y+=d*4; k+=1
    a['ground']=[x,y+d*12]
json.dump(L,open(ROOT+'/data/layout.json','w')); print('ground sections',len(ground))
