# Red Keep building plan v2 - throne hall faces the main gate. Units: interior tiles (IT). 1 tactical tile = 3 IT. 1 IT = 16 px.
import json, math
from PIL import Image, ImageDraw, ImageFont
OUT='/tmp/claude-0/-home-claude/e59396bc-cfb6-5546-9a15-3ded7e6db8e8/scratchpad/keepplan/'
FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; FR='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def f(s,b=True): return ImageFont.truetype(FB if b else FR,s)
MW,MH=252,120
CURTAIN=[(15,12),(72,12),(72,6),(174,6),(174,15),(231,15),(240,24),(240,99),(228,111),(177,111),(177,117),(78,117),(78,111),(24,111),(12,99),(12,27)]
DRUMS=[(28.5,28.5),(61.5,19.5),(109.5,16.5),(154.5,16.5),(220.5,31.5),(217.5,91.5),(58.5,100.5)]
DRUM_NAME={0:'stair',1:'stair',2:"King's\ntower",3:"Queen's\ntower",4:'stair\n(maid above)',5:'stair',6:'stair'}
DR=7
HOLD_OUT=(84,9,168,42); HOLD_IN=(87,12,165,39); BRIDGE=(123,39,129,42)
ZC={'king':(250,222,150),'sister':(170,222,212),'serv':(208,208,216),'mil':(222,170,160),'gov':(176,196,232),
    'cer':(222,200,232),'court':(176,196,140),'hold':(236,214,190),'cell':(196,180,160),'fire':(255,150,90),'safe':(140,220,140)}
L0=[
 # Tower of the Hand
 (24,21,42,36,'Records Room\n(LOCKED)','gov'),(42,21,51,36,'Hand\nguard','mil'),(51,21,60,36,'Stair','gov'),
 (24,36,42,51,"Hand's Hall",'gov'),(42,36,60,51,'Garden Court\n(ivy wall)','court'),
 # Kitchens + service
 (24,54,36,69,'Bake-\nhouse','fire'),(36,54,60,69,'KITCHEN','fire'),(24,69,48,84,'Service Court\nwell, woodpile,\nhay, kennel','court'),
 (48,69,60,76,'Larder','serv'),(48,76,60,84,"Servants'\nhall",'fire'),
 # Great Hall
 (60,45,66,54,'But-\ntery','serv'),(60,54,66,72,'Ser-\nvery','serv'),(66,45,99,72,'GREAT HALL\n(feasts)','cer'),
 # Throne Hall
 (99,45,153,72,'THRONE HALL\nthrone on the north dais\npublic doors face the gate','cer'),
 # Small Council
 (153,45,165,58,'Ante-\nroom','gov'),(165,45,192,58,'Small Council\nChamber (LOCKED)','gov'),(153,58,175,72,'Clerks\nscriptorium','gov'),(175,58,192,72,'Archive\nvault (IRON)','gov'),
 # Royal Apartments ground
 (192,24,210,39,'Wardrobe\n& linen','sister'),(210,24,228,39,'Household\nservants','sister'),(192,39,210,51,'Apartments\nentrance hall','sister'),(210,39,228,51,'Guard room','mil'),
 # Maester
 (192,54,210,69,"Maester's hall\n(infirmary)",'gov'),(210,54,228,69,'Herb &\npoison store','gov'),(192,69,228,84,"Maester's library",'gov'),
 # Holdfast ground
 (87,12,102,24,'Kingsguard\narmory','mil'),(102,12,117,24,'','hold'),(117,12,147,24,'Holdfast Hall\n(private dining)','hold'),(147,12,165,24,'','hold'),
 (87,24,165,30,'Holdfast corridor','hold'),(87,24,93,30,'Grand\nstair','hold'),(159,24,165,30,'East\nstair','hold'),
 (87,30,111,39,'Stores + well','hold'),(111,30,117,39,'Gu-\nard','mil'),(117,30,123,39,'WIN-\nCH','mil'),(123,30,129,39,'gate','hold'),(129,30,135,39,'Brdg\nguard','mil'),(135,30,165,39,'Royal Sept (chapel)','hold'),
 # Outer ward, barracks, gate, White Sword
 (84,72,168,102,'OUTER WARD (open courtyard)\ncrowds gather here by day - alarm bell','court'),
 (24,87,54,108,'Gold Cloak\nBarracks\n(12 bunks)','mil'),(54,87,66,108,'','mil'),(66,87,84,97,'Armory','mil'),(66,97,84,108,'Mess hall','mil'),
 (111,102,120,117,'W gate\nguards','mil'),(120,102,132,117,'MAIN\nGATE','mil'),(132,102,141,117,'E gate\nguards','mil'),
 (168,87,186,102,'White Sword\nRound Room\n(White Book)','mil'),(186,87,210,102,'Kingsguard\ndormitory','mil'),(210,87,228,102,'Armory','mil'),
]
L1=[
 (24,21,42,36,"Hand's Solar\n(letters)",'gov'),(42,21,60,36,"Hand's library",'gov'),(24,36,42,51,"Hand's\nbedchamber\n(window)",'gov'),
 (24,54,60,69,"Servants' dormitory",'fire'),(48,69,60,84,"Steward\n(postern\nKEY)",'serv'),
 (60,45,66,72,'','serv'),(66,45,99,49,'minstrel gallery','cer'),
 (99,45,103,72,'','fire'),(149,45,153,72,'','fire'),(99,68,153,72,'public gallery (timber)','fire'),
 (153,45,172,58,"Whisperers'\noffice (trap)",'gov'),(172,45,192,58,'Coin\ncounting','gov'),(153,58,192,72,'Records loft','gov'),
 # Sister's family
 (192,24,200,36,'Brdg\nhall','mil'),(200,24,207,36,'Niece','sister'),(207,24,214,36,'Neph-\new','sister'),(214,24,228,36,"Lady's\nmaid",'sister'),
 (192,36,210,51,'SISTER &\nHUSBAND\nBEDCHAMBER','sister'),(210,36,219,51,"Sister's\nsolar",'sister'),(219,36,228,51,"Hus-\nband's\nstudy",'sister'),
 (192,54,210,69,"Maester's\nchambers\n(letters)",'gov'),(210,54,228,69,'ROOKERY\n(ravens)','gov'),(192,69,228,84,'Apprentices','gov'),
 # King's family - Holdfast
 (87,12,102,24,"KING'S\nSOLAR",'king'),(102,12,117,24,'','king'),(117,12,147,24,'KING & QUEEN\nBEDCHAMBER','king'),(147,12,165,24,'','king'),
 (87,24,165,30,'royal corridor','king'),(87,24,93,30,'Grand\nstair','hold'),(159,24,165,30,'East\nstair','hold'),
 (87,30,99,39,"Queen's\nsolar",'king'),(99,30,111,39,'Crown\nPrince','king'),(111,30,117,39,'Bath','king'),(117,30,135,39,'Kingsguard\n+ murder holes','mil'),
 (135,30,147,39,'Princess','king'),(147,30,156,39,'Nur-\nsery','king'),(156,30,165,39,'Nurse-\nmaid','king'),
 (24,87,54,108,'Bunk loft','mil'),(66,87,84,97,"Captain's\nquarters",'mil'),(66,97,84,108,'Store','mil'),
 (111,102,141,117,'PORTCULLIS WINCH\n+ murder holes','mil'),
 (168,87,186,102,'Lord Cmdr\n(KEY RING)','mil'),(186,87,228,102,'Kingsguard cells','mil'),
]
LM1=[
 (24,21,42,36,"Hand's\ncellar",'cell'),(24,54,36,69,'OIL &\nPITCH\nSTORE','fire'),(36,54,60,69,'Root cellar\n(stair up)','cell'),(66,54,99,72,'Wine cellar','cell'),
 (99,50,153,72,'CRYPT OF KINGS','cell'),(87,12,102,24,'Royal\nTreasury','cell'),
 (117,14,147,26,'SAFE ROOM\nsealed, water, food, beds','safe'),(117,30,123,39,'Ctr-\nwt\npit','mil'),(129,30,165,39,'Holdfast cellar','cell'),
 (24,87,54,108,'Black cells\n(dungeon)','cell'),(66,87,84,108,'Gaoler','cell'),
]
# doors (x,y,orient,len,type): d=door L=locked at night H=hidden G=gate/portcullis
D0=[(120,114,'h',12,'G'),(120,102,'h',12,'G'),(120,108,'v',3,'d'),(132,108,'v',3,'d'),
    (84,90,'v',3,'d'),(84,100,'v',3,'d'),(66,100,'v',3,'d'),(66,90,'v',3,'L'),
    (120,72,'h',12,'L'),(123,45,'h',6,'L'),(99,57,'v',4,'d'),(153,50,'v',3,'L'),
    (80,72,'h',4,'d'),(66,60,'v',4,'d'),(60,60,'v',4,'d'),(62,54,'h',3,'d'),
    (84,42,'v',3,'G'),(168,42,'v',3,'G'),(123,39,'h',6,'G'),
    (123,33,'v',3,'L'),(129,33,'v',3,'d'),(123,30,'h',6,'d'),(130,24,'h',4,'d'),(93,24,'h',3,'L'),(100,30,'h',3,'d'),(113,30,'h',3,'d'),(148,30,'h',4,'d'),
    (33,51,'h',3,'d'),(33,36,'h',3,'L'),(42,42,'v',3,'d'),(45,36,'h',3,'d'),(54,36,'h',3,'d'),
    (42,69,'h',3,'d'),(36,60,'v',3,'d'),(48,72,'v',3,'d'),(48,80,'v',3,'d'),(24,76,'v',3,'L'),(12,75,'v',3,'L'),(50,54,'h',3,'d'),
    (158,72,'h',3,'d'),(165,50,'v',3,'L'),(160,58,'h',3,'d'),(175,64,'v',3,'L'),
    (199,51,'h',3,'d'),(210,44,'v',3,'d'),(199,39,'h',3,'d'),(215,39,'h',3,'d'),
    (199,54,'h',3,'d'),(210,60,'v',3,'L'),(200,69,'h',3,'d'),
    (168,92,'v',3,'d'),(186,94,'v',3,'d'),(210,94,'v',3,'d')]
D1=[(94,24,'h',3,'d'),(130,24,'h',4,'L'),(117,15,'v',3,'H'),(102,15,'v',3,'H'),(94,30,'h',3,'d'),(104,30,'h',3,'d'),(113,30,'h',3,'d'),(125,30,'h',3,'L'),
    (140,30,'h',3,'d'),(150,30,'h',3,'d'),(156,34,'v',3,'d'),(165,27,'v',3,'L'),(192,27,'v',3,'L'),
    (195,36,'h',3,'d'),(200,29,'v',3,'d'),(207,29,'v',3,'d'),(214,29,'v',3,'d'),(210,42,'v',3,'d'),(219,42,'v',3,'d'),
    (33,36,'h',3,'d'),(42,28,'v',3,'d'),(172,51,'v',3,'L'),(160,58,'h',3,'d'),(210,60,'v',3,'d'),(200,69,'h',3,'d'),(186,94,'v',3,'L'),(52,69,'h',3,'d')]
DM1=[(36,60,'v',3,'L'),(39,54,'h',2,'L'),(117,15.5,'v',2,'H'),(117,22,'v',2,'H'),(147,18,'v',2,'H'),(147,23,'v',2,'H'),(125,26,'h',2,'H')]
SECRET_STAIRS={'K':(109.5,16.5),'S':(193.5,37.5),'T':(126,48.5)}
TUN={'K':[(109.5,16.5),(117,16.5)],
     'S':[(193.5,37.5),(193.5,19),(147,19)],
     'T':[(126,48.5),(126,26)],
     'RIVER':[(147,24),(166.5,24),(166.5,52.5),(240,52.5)],
     'FOREST':[(117,23),(80,23),(80,48.5),(12,48.5)]}
DRAIN=[(0,52.5),(40,52.5),(40,54.5)]
G0=[(123,110,1,''),(129,110,1,''),(115,109,1,''),(137,109,1,''),(38,97,0,'12 asleep'),(126,43.5,1,'bridge foot'),(132,35,1,''),(95,18,1,''),(114,35,1,''),
    (124,74,1,''),(128,74,1,''),(33,53,1,''),(201,45,1,''),(219,45,1,''),(15,79,1,'postern'),(177,95,1,''),(40,80,0,'2 hounds'),(158,74,1,'')]
P0=[[(88,76),(164,76),(164,99),(88,99),(88,76)],[(74,10),(74,43.5),(82,43.5)],[(178,18),(178,43.5),(170,43.5)],
    [(233,30),(233,100),(226,106),(145,106)],[(18,30),(18,96)]]
G1=[(126,35,2,''),(126,27,1,"King's door"),(196,30,1,''),(177,95,0,'Lord Cmdr'),(116,110,1,''),(136,110,1,''),(54,78,0,'Steward')]+[(x,y,1,'') for x,y in DRUMS]
P1=[CURTAIN+[CURTAIN[0]]]
FIRE=[('F0',(27,66),'L-1'),('F1',(56,66),'L-1'),('F2',(56,66),'L0'),('F3',(27,66),'L0'),('F3',(27,81),'L0'),('F3',(57,81.5),'L0'),('F4',(56,66),'L1'),('F5',(70,68.5),'L0')]
ENTRY={'A':(5,52.5,'L-1','River drain culvert -> grate (crowbar) -> root cellar'),'B':(9,72,'L0','Supply postern -> service court (key from the Steward)'),
       'C':(58,44,'L0','Climb the ivy in the Garden Court -> Hand bedchamber window (L1)'),'D':(85.5,37,'L1','Privy chute from the dry moat -> Queen\'s solar privy')}

S=8; PX,PY=20,120
def draw(level,rooms,doors,legend):
    W=PX*2+MW*S; H=PY+MH*S+40+len(legend)*26+30
    im=Image.new('RGB',(W,H),(250,247,240)); d=ImageDraw.Draw(im)
    T=lambda x,y:(PX+x*S,PY+y*S)
    poly=[T(*p) for p in CURTAIN]
    if level=='L-1':
        d.rectangle([PX,PY,PX+MW*S,PY+MH*S],fill=(90,80,72)); d.polygon(poly,fill=(120,108,96),outline=(40,32,28))
    else:
        d.polygon(poly,fill=(214,204,186) if level=='L0' else (190,200,215))
        d.line(poly+[poly[0]],fill=(57,41,33),width=3*S)
        if level=='L1': d.line([T(*p) for p in P1[0]],fill=(255,200,0),width=5)
    if level in('L0','L1'):
        x0,y0,x1,y1=HOLD_OUT; d.rectangle([*T(x0,y0),*T(x1,y1)],fill=(60,50,45))
        for i in range(x0,x1,2):
            yy=y1-1.5; d.polygon([T(i+.5,yy+.8),T(i+1,yy-.8),T(i+1.5,yy+.8)],fill=(150,150,160))
        for j in range(y0+1,y1,2):
            for xx in (x0+1.5,x1-1.5): d.polygon([T(xx-.8,j+1.5),T(xx,j+.5),T(xx+.8,j+1.5)],fill=(150,150,160))
        d.rectangle([*T(*HOLD_IN[:2]),*T(*HOLD_IN[2:])],fill=ZC['hold'])
    for x0,y0,x1,y1,lab,z in rooms: d.rectangle([*T(x0,y0),*T(x1,y1)],fill=ZC[z],outline=(57,41,33),width=2)
    if level!='L-1':
        for i,(x,y) in enumerate(DRUMS):
            d.ellipse([*T(x-DR,y-DR),*T(x+DR,y+DR)],fill=(196,150,130),outline=(57,41,33),width=3)
            nm=DRUM_NAME[i] if level=='L0' or i in(2,3) else 'sentry'
            for k,l in enumerate(nm.split('\n')):
                tw=d.textlength(l,font=f(10)); d.text((PX+x*S-tw/2,PY+(y+2.2)*S+k*12),l,font=f(10),fill=(40,20,10))
    if level=='L0':
        d.rectangle([*T(*BRIDGE[:2]),*T(*BRIDGE[2:])],fill=(140,90,50),outline=(30,20,10),width=2)
        d.text(T(129.5,39.4),'DRAWBRIDGE',font=f(11),fill=(255,230,120))
        d.text(T(85,39.6),'DRY MOAT - iron spikes',font=f(10),fill=(255,255,255))
        d.text(T(88,42.3),'bridge lane (iron gates both ends)',font=f(10),fill=(60,40,30))
    col={'d':(150,95,50),'L':(200,30,30),'H':(255,0,255),'G':(30,30,30)}
    for x,y,o,l,t in doors:
        a=T(x,y); b=T(x+l,y) if o=='h' else T(x,y+l)
        d.line([a,b],fill=col[t],width=6 if t!='G' else 9)
    for x0,y0,x1,y1,lab,z in rooms:
        if not lab: continue
        ls=lab.split('\n'); fs=11 if (x1-x0)<12 else 13
        cy=PY+(y0+y1)/2*S-len(ls)*(fs+2)/2
        for k,l in enumerate(ls):
            tw=d.textlength(l,font=f(fs)); d.text((PX+(x0+x1)/2*S-tw/2,cy+k*(fs+2)),l,font=f(fs),fill=(25,18,12))
    return im,d,T
def star(d,T,x,y,c,txt):
    pts=[T(x+(1.6 if i%2==0 else .7)*math.cos(-math.pi/2+i*math.pi/5),y+(1.6 if i%2==0 else .7)*math.sin(-math.pi/2+i*math.pi/5)) for i in range(10)]
    d.polygon(pts,fill=c,outline=(0,0,0)); d.text(T(x+1.5,y-1.6),txt,font=f(14),fill=c,stroke_width=3,stroke_fill='white')
def guard(d,T,x,y,n,lab):
    d.ellipse([*T(x-.9,y-.9),*T(x+.9,y+.9)],fill=(30,60,200),outline='white',width=2)
    if n>1 or lab: d.text(T(x+1,y-1),(f'x{n} ' if n>1 else '')+lab,font=f(10),fill=(20,40,160),stroke_width=2,stroke_fill='white')
def sstair(d,T,k,x,y):
    d.rectangle([*T(x-1.4,y-1.4),*T(x+1.4,y+1.4)],fill=(255,0,255),outline=(0,0,0),width=2); d.text(T(x-.7,y-1.2),k,font=f(12),fill='white')
def fire(d,T,k,x,y):
    d.ellipse([*T(x-1.6,y-1.6),*T(x+1.6,y+1.6)],fill=(255,90,0),outline=(120,0,0),width=2); d.text(T(x-1.2,y-.9),k,font=f(11),fill='white')
def header(im,title,sub):
    d=ImageDraw.Draw(im); d.rectangle([0,0,im.width,PY-12],fill=(0,0,0))
    d.text((18,10),title,font=f(40),fill='white'); d.text((18,62),sub,font=f(20,False),fill=(220,220,220))
def legend(d,y,lines):
    for l in lines: d.text((PX,y),l,font=f(17,False),fill=(0,0,0)); y+=26
def marks(d,T,level):
    for k,(x,y) in SECRET_STAIRS.items(): sstair(d,T,k,x,y)
    for k,(x,y),lv in FIRE:
        if lv==level: fire(d,T,k,x,y)
    for k,(x,y,lv,t) in ENTRY.items():
        if lv==level: star(d,T,x,y,(220,160,0),k)

leg0=['KEY: blue dot = guard   red door = LOCKED at night   magenta = hidden door / secret stair (K, S, T)   black bar = gate / portcullis   orange = fire stage   gold star = way in',
      'Yellow lines = lantern patrols (back and forth).  PUBLIC ROUTE: main gate -> outer ward -> throne hall doors.  KING\'S ROUTE: Holdfast -> drawbridge -> King\'s door behind the throne.',
      'Night: portcullis down, throne hall doors locked, bridge-lane gates locked, drawbridge UP.  Fire: F0-F1 below ground, F2 kitchen, F3 bakehouse + court + servants hall, F5 Great Hall.']
im,d,T=draw('L0',L0,D0,leg0)
for p in P0: d.line([T(*q) for q in p],fill=(230,170,0),width=4)
for g in G0: guard(d,T,*g)
marks(d,T,'L0'); d.text(T(118,117.4),'MAIN GATE (south)',font=f(12),fill=(0,0,0))
d.text(T(128.5,46.6),'THRONE (T under the dais)',font=f(11),fill=(120,0,0))
header(im,'LEVEL 0 - GROUND FLOOR (252 x 120 tiles)','v2: throne hall faces the gate.  1 tactical tile = 3 interior tiles = 48 px.  Kael = 1 x 1.75 tiles.  North is up.')
legend(d,PY+MH*S+20,leg0); im.save(OUT+'v2_L0_ground.png')

leg1=["KING'S FAMILY = gold (Maegor's Holdfast, behind the moat).  SISTER'S FAMILY = teal (Royal Apartments), joined to the Holdfast by a covered bridge, locked both sides at night.",
      'Yellow line = wall-walk patrol (2 pairs, opposite directions); every drum tower has a sentry with a brazier.  F4 = fire reaches the servants dormitory above the kitchen.',
      'Information targets: Hand Solar, Whisperers office, Coin room, King Solar, Maester chambers + Rookery.  Steward holds the supply-postern key (way in B).']
im,d,T=draw('L1',L1,D1,leg1)
d.rectangle([*T(165,27),*T(192,30)],fill=(160,120,90),outline=(0,0,0),width=2); d.text(T(169,27.4),'covered bridge',font=f(11),fill='white')
for g in G1: guard(d,T,*g)
marks(d,T,'L1')
d.rectangle([*T(87,36),*T(90,39)],fill=(120,90,60))
d.text(T(72,58),'(Great Hall\nopen below)',font=f(12,False),fill=(60,60,90)); d.text(T(115,56),'(Throne Hall open below)',font=f(12,False),fill=(60,60,90))
d.text(T(110,85),'(outer ward - open)',font=f(12,False),fill=(60,60,90)); d.text(T(35,75),'(court\nopen)',font=f(12,False),fill=(60,60,90))
header(im,'LEVEL 1 - UPPER FLOOR','Royal family floors, offices of the Hand and Council, Maester, wall-walk.  Same grid as Level 0.')
legend(d,PY+MH*S+20,leg1); im.save(OUT+'v2_L1_upper.png')

legm=['SECRET ESCAPE (magenta): K = King\'s tower beside the royal bedchamber, S = Sister & Husband bedchamber, T = behind the throne.  All three reach the SAFE ROOM under the Holdfast.',
      'From the SAFE ROOM: RIVER TUNNEL (east) -> hidden river dock + boat;  FOREST TUNNEL (west) -> ruined watchtower outside the walls.',
      'A = way in: river drain culvert, locked grate (crowbar) -> root cellar.  F0 = player lights the oil & pitch store, F1 = root cellar catches, smoke climbs into the kitchen.']
im,d,T=draw('L-1',LM1,DM1,legm)
for k,p in TUN.items():
    d.line([T(*q) for q in p],fill=(255,0,255) if k in 'KST' else (200,0,200),width=2*S); d.line([T(*q) for q in p],fill=(255,170,255),width=4)
d.line([T(*q) for q in DRAIN],fill=(70,120,200),width=2*S)
marks(d,T,'L-1')
d.text(T(14,54.6),'DRAIN CULVERT',font=f(12),fill=(220,235,255))
d.text(T(196,49.3),'RIVER TUNNEL -> hidden dock',font=f(12),fill='white')
d.text(T(14,44.8),'<- FOREST TUNNEL -> ruined watchtower',font=f(12),fill='white')
header(im,'LEVEL -1 - UNDERGROUND','Cellars, dungeon, treasury, crypt, drawbridge counterweight, secret tunnels, safe room.  Same grid as Level 0.')
legend(d,PY+MH*S+20,legm); im.save(OUT+'v2_Lm1_underground.png')

json.dump({'version':2,'units':'interior tiles (16 px); tactical tile = 3','size':[MW,MH],'curtain':CURTAIN,'drum_towers':DRUMS,'drum_radius':DR,
  'holdfast_moat_outer':HOLD_OUT,'holdfast_inner':HOLD_IN,'drawbridge':BRIDGE,
  'levels':{'L0':{'rooms':L0,'doors':D0,'guards':G0,'patrols':P0},'L1':{'rooms':L1,'doors':D1,'guards':G1,'patrols':P1},'L-1':{'rooms':LM1,'doors':DM1}},
  'secret_stairs':SECRET_STAIRS,'tunnels':TUN,'drain':DRAIN,'fire':FIRE,'entries':ENTRY},open(OUT+'keep_plan_v2.json','w'),indent=1)
# overlap check (rooms of same level must not overlap, except sub-rooms inside the corridor/drum fillers)
for nm,R in (('L0',L0),('L1',L1),('L-1',LM1)):
    for i,a in enumerate(R):
        for b in R[i+1:]:
            ox=min(a[2],b[2])-max(a[0],b[0]); oy=min(a[3],b[3])-max(a[1],b[1])
            if ox>0 and oy>0: print('OVERLAP',nm,a[4].replace('\n',' '),'|',b[4].replace('\n',' '))
print('ok')
