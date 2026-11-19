# zone_render.py BOARD OUT.png LAYER [px_per_mm]: draw filled zones on LAYER (coloured by net),
# plus that layer's tracks, arcs (as polylines through start/mid/end) and vias, with a legend.
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import LEFT, RIGHT, TOP, BOTTOM, Part  # noqa: E402
from sexpr import parse, children, child  # noqa: E402
from PIL import Image, ImageDraw, ImageFont

board, out, layer = sys.argv[1], sys.argv[2], sys.argv[3]
sc = float(sys.argv[4]) if len(sys.argv) > 4 else 14
root = parse(open(board).read())
COL = {"GND": (90, 90, 90), "+3V3": (0, 160, 0), "+5V": (230, 40, 40), "+0V9": (200, 0, 120),
       "VBUS_MAIN": (140, 0, 160), "VBUS_ESP": (255, 0, 255), "+5V_LED": (255, 140, 0),
       "+5V_AMP": (160, 90, 0), "+1V8": (0, 110, 220)}
x0, y0 = LEFT - 1, TOP - 1
W, H = int((RIGHT - LEFT + 2) * sc), int((BOTTOM - TOP + 2) * sc) + 40
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img, "RGBA")
P = lambda x, y: ((x - x0) * sc, (y - y0) * sc)
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
net = lambda n: str(child(n, "net")[1]) if child(n, "net") else ""
for z in children(root, "zone"):
    for fp in children(z, "filled_polygon"):
        if str(child(fp, "layer")[1]) != layer:
            continue
        pts = [P(float(p[1]), float(p[2])) for p in child(fp, "pts")[1:] if isinstance(p, list)]
        d.polygon(pts, fill=COL.get(net(z), (150, 150, 150)) + (110,))
# pads on this side for orientation
side = layer if layer in ("F.Cu", "B.Cu") else None
for f in children(root, "footprint"):
    p = Part(f)
    for pd, poly in zip(children(f, "pad"), p.pads()):
        if p.side == side or pd[2] == "thru_hole":
            d.polygon([P(*q) for q in poly], outline=(60, 60, 60, 200))
for s in children(root, "segment") + children(root, "arc"):
    if str(child(s, "layer")[1]) != layer:
        continue
    pts = [child(s, k) for k in ("start", "mid", "end") if child(s, k)]
    w = max(1, round(float(child(s, "width")[1]) * sc))
    xy = [P(float(p[1]), float(p[2])) for p in pts]
    d.line(xy, fill=COL.get(net(s), (120, 120, 255)) + (255,), width=w)
for v in children(root, "via"):
    a = child(v, "at"); r = float(child(v, "size")[1]) / 2 * sc; cx, cy = P(float(a[1]), float(a[2]))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COL.get(net(v), (120, 120, 255)), outline="black")
d.rectangle([P(LEFT, TOP), P(RIGHT, BOTTOM)], outline="black", width=2)
xx = 5
for k, c in COL.items():
    d.rectangle([xx, H - 30, xx + 14, H - 16], fill=c); d.text((xx + 18, H - 32), k, font=F, fill="black")
    xx += d.textlength(k, font=F) + 36
d.text((6, 4), layer, font=F, fill="black")
img.save(out)
