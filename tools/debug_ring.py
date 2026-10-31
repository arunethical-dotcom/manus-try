import json, sys, numpy as np
from PIL import Image, ImageDraw
L=json.load(open('data/layout.json'))
x0,y0,x1,y1=[int(v) for v in sys.argv[1:5]]; sc=float(sys.argv[5]); out=sys.argv[6]
cv=Image.new('RGBA',(int((x1-x0)*sc),int((y1-y0)*sc)),(236,236,236,255))
for s in L['sprites']:
    im=Image.open('art/game/%s.png'%s['img']).convert('RGBA')
    im=im.resize((max(1,int(im.width*sc)),max(1,int(im.height*sc))),Image.BOX)
    cv.alpha_composite(im,(int((s['x']-x0)*sc),int((s['y']-y0)*sc)))
d=ImageDraw.Draw(cv)
if len(sys.argv)>7:
    for r in L['wall_rects']:
        d.rectangle([(r[0]-x0)*sc,(r[1]-y0)*sc,(r[0]+r[2]-x0)*sc,(r[1]+r[3]-y0)*sc],outline=(255,0,0))
cv.convert('RGB').save(out)
