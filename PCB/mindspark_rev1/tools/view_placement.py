# view_placement.py BOARD OUT.png x0 y0 x1 y1 [F|B|FB] [px per mm]: plan view with courtyards, pads coloured by net, refs
import sys
sys.path.insert(0, "/home/anbu/Z/projects/internship/mindspark/PCB/mindspark_rev1/tools")
import place_tidy as T
from sexpr import parse, children, child
from PIL import Image, ImageDraw, ImageFont
board, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
sides = sys.argv[7] if len(sys.argv) > 7 else "FB"
sc = float(sys.argv[8]) if len(sys.argv) > 8 else 40
root = parse(open(board).read())
img = Image.new("RGB", (int((x1 - x0) * sc), int((y1 - y0) * sc)), "white")
d = ImageDraw.Draw(img, "RGBA")
F = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(s))
P = lambda x, y: ((x - x0) * sc, (y - y0) * sc)
d.rectangle([P(T.LEFT, T.TOP), P(T.RIGHT, T.BOTTOM)], outline="black", width=2)
for g in children(root, "segment"):
    lay = child(g, "layer")[1]
    if lay[0] in sides:
        s, e = child(g, "start"), child(g, "end")
        d.line([P(float(s[1]), float(s[2])), P(float(e[1]), float(e[2]))], fill=(200, 50, 50, 90) if lay == "F.Cu" else (50, 50, 200, 90), width=max(1, int(float(child(g, "width")[1]) * sc)))
labels = []
for f in children(root, "footprint"):
    p = T.Part(f)
    if p.side[0] not in sides: continue
    col = (210, 30, 30) if p.side == "F.Cu" else (30, 30, 210)
    for pd, pts in zip(children(f, "pad"), p.pads()):
        net = child(pd, "net"); n = str(net[1]) if net else ""
        fill = (170, 170, 170, 200) if n == "GND" else (255, 200, 90, 200) if n.startswith(("+", "VBUS")) else ((255, 140, 190, 200) if p.side == "F.Cu" else (130, 180, 240, 200))
        d.polygon([P(*q) for q in pts], fill=fill)
        bx = T.bbox(pts); s = n.replace("Net-(", "").replace(")", "").replace("unconnected-", "nc")[:9]
        if sc >= 30 and s:
            labels.append(((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, s, max(8, sc * 0.18), (0, 90, 0)))
    if p.local_box("CrtYd"):
        c = p.courtyard(); d.polygon([P(*q) for q in c], outline=col)
        b = T.bbox(c)
    else:
        x, y, _ = p.at; b = (x, y, x, y)
    labels.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, p.ref, max(10, sc * 0.4), (0, 0, 0)))
for x, y, s, size, colr in labels:
    fnt = F(size); w = d.textlength(s, font=fnt)
    px, py = P(x, y); d.text((px - w / 2, py - size / 2), s, font=fnt, fill=colr)
img.save(out)
