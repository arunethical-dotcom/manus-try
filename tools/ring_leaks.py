import json, numpy as np, cv2
L=json.load(open('data/layout.json'))
W,H=L['world']; G=4
bl=np.zeros((H//G,W//G),np.uint8)
for r in L['wall_rects']:
    bl[r[1]//G:(r[1]+r[3])//G+1, r[0]//G:(r[0]+r[2])//G+1]=1
gx,gy=L['gate']
bl[(gy-70)//G:(gy+20)//G+1,(gx-60)//G:(gx+60)//G+1]=1
seed=L['inside_seed']
for k in range(0,40,2):
    b2=cv2.dilate(bl,np.ones((2*k+1,2*k+1),np.uint8)) if k else bl
    n2,l2=cv2.connectedComponents((b2==0).astype(np.uint8),connectivity=4)
    if l2[seed[1]//G,seed[0]//G]!=l2[5,5]:
        print('sealed when walls grown by',k*G,'px')
        if k==0: break
        ins=(l2==l2[seed[1]//G,seed[0]//G]).astype(np.uint8); out=(l2==l2[5,5]).astype(np.uint8)
        d=2*k+4
        gap=cv2.dilate(ins,np.ones((d,d),np.uint8))&cv2.dilate(out,np.ones((d,d),np.uint8))&(bl==0)
        cl=cv2.connectedComponentsWithStats(cv2.dilate(gap,np.ones((9,9),np.uint8)))
        for st in cl[2][1:]: print(' leak near world px',(st[0]+st[2]//2)*G,(st[1]+st[3]//2)*G,'size',st[2]*G,st[3]*G)
        break
