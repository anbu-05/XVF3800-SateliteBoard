# power_render.py LAYERS [px_per_mm] [x0 y0 x1 y1]: draw power-net copper per layer (run from the project folder; PNGs go to $OUT, default .)
import sys, os
sys.path.insert(0,"tools")
import place_tidy as T
from sexpr import parse, children, child
from PIL import Image, ImageDraw, ImageFont
root=parse(open("mindspark_rev1.kicad_pcb").read())
x0,y0,x1,y1=108.5,60.7,184.6,136.7; sc=float(sys.argv[2]) if len(sys.argv)>2 else 22
reg=sys.argv[3:7]
if reg: x0,y0,x1,y1=map(float,reg)
COL={"+5V":(230,30,30),"VBUS_MAIN":(150,0,150),"VBUS_ESP":(255,0,255),"+5V_LED":(255,140,0),"+5V_AMP":(160,90,0),
"+3V3":(0,150,0),"+1V8":(0,120,220),"+0V9":(200,0,90),"PLL_AVDD":(120,0,200),"GND":(60,60,60),
"Net-(U201-SW)":(0,200,200),"Net-(U202-SW)":(0,200,200)}
for i in range(4): COL[f"+3V3_MIC{i}"]=(100,200,0)
F=lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",int(s))
fps=[(T.Part(f),f) for f in children(root,"footprint")]
def nn(n):
    x=child(n,"net"); return str(x[1]) if x else ""
for lay in sys.argv[1].split(","):
    img=Image.new("RGB",(int((x1-x0)*sc),int((y1-y0)*sc)+40),"white"); d=ImageDraw.Draw(img,"RGBA")
    P=lambda x,y:((x-x0)*sc,(y-y0)*sc)
    d.rectangle([P(T.LEFT,T.TOP),P(T.RIGHT,T.BOTTOM)],outline="black",width=2)
    side="F.Cu" if lay=="F.Cu" else "B.Cu" if lay=="B.Cu" else None
    for p,f in fps:
        for pd,pts in zip(children(f,"pad"),p.pads()):
            n=nn(pd); ls=[str(a) for a in (child(pd,"layers") or [])[1:]]
            on = (p.side==side) or ("*.Cu" in ls)
            if not on: continue
            c=COL.get(n,(200,200,200)); d.polygon([P(*q) for q in pts],fill=c+(150,) if n in COL else (215,215,215,255))
    for g in children(root,"segment"):
        if str(child(g,"layer")[1])!=lay: continue
        n=nn(g); s,e=child(g,"start"),child(g,"end")
        d.line([P(float(s[1]),float(s[2])),P(float(e[1]),float(e[2]))],fill=COL.get(n,(150,150,255))+(230,) ,width=max(1,round(float(child(g,"width")[1])*sc)))
    for v in children(root,"via"):
        n=nn(v); a=child(v,"at"); r=float(child(v,"size")[1])/2*sc; cx,cy=P(float(a[1]),float(a[2]))
        d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=COL.get(n,(150,150,255)),outline="black")
    if side:
        for p,f in fps:
            if p.side!=side: continue
            x,y,_=p.at; w=d.textlength(p.ref,font=F(sc*0.32)); px,py=P(x,y); d.text((px-w/2,py-sc*0.16),p.ref,font=F(sc*0.32),fill=(0,0,0))
    xx=5
    for k,c in COL.items():
        if "MIC" in k and k!="+3V3_MIC0": continue
        d.rectangle([xx,img.height-30,xx+14,img.height-16],fill=c); d.text((xx+18,img.height-32),k.replace("Net-(","").replace(")",""),font=F(13),fill="black"); xx+=d.textlength(k,font=F(13))+40
    d.text((5,5),lay,font=F(20),fill="black")
    img.save(os.environ.get("OUT",".")+f"/pw_{lay.replace('.','')}{'_z' if reg else ''}.png")
