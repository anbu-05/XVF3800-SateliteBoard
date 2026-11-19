"""route_render.py BOARD OUT.png LAYER x0 y0 x1 y1 [px_per_mm] [--labels REF:hint,...]
Zoomed render of one copper layer as built (zone fills included): In2 plane fills faint behind,
that layer's pads, tracks, arcs and vias coloured by net (the main USB pair bright orange /
yellow), the other outer layer's copper as faint outlines, part references with optional hints.
Run from the project folder."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import Part, bbox  # noqa: E402
from sexpr import parse, children, child  # noqa: E402
from PIL import Image, ImageDraw, ImageFont

board, out, layer = sys.argv[1], sys.argv[2], sys.argv[3]
x0, y0, x1, y1 = map(float, sys.argv[4:8])
sc = float(sys.argv[8]) if len(sys.argv) > 8 and not sys.argv[8].startswith("--") else 40
hints = {}
if "--labels" in sys.argv:
    for kv in sys.argv[sys.argv.index("--labels") + 1].split(","):
        k, v = kv.split(":", 1)
        hints[k] = v
other = "B.Cu" if layer == "F.Cu" else "F.Cu"
r = parse(open(board).read())
COL = {"/USB_MAIN_DM": (255, 110, 0), "/USB_MAIN_DP": (235, 185, 0), "GND": (110, 110, 110), "+0V9": (200, 0, 120),
       "+1V8": (0, 120, 220), "+3V3": (0, 160, 0), "+5V": (230, 40, 40), "VBUS_MAIN": (140, 0, 170),
       "VBUS_ESP": (255, 0, 255), "+5V_LED": (120, 170, 255)}
W, H = int((x1 - x0) * sc), int((y1 - y0) * sc)
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img, "RGBA")
P = lambda x, y: ((x - x0) * sc, (y - y0) * sc)  # noqa: E731
F = lambda s, b=False: ImageFont.truetype(  # noqa: E731
    "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
nn = lambda n: str(child(n, "net")[1]) if child(n, "net") else ""  # noqa: E731


def fills(lay, alpha):
    for z in children(r, "zone"):
        if str(child(z, "layer")[1]) != lay:
            continue
        c = COL.get(nn(z), (190, 190, 190))
        for fp in children(z, "filled_polygon"):
            d.polygon([P(float(q[1]), float(q[2])) for q in child(fp, "pts")[1:] if q[0] == "xy"], fill=c + (alpha,))


def tracks(lay, alpha, outline_only=False):
    for s in children(r, "segment") + children(r, "arc"):
        if str(child(s, "layer")[1]) != lay:
            continue
        pts = [child(s, k) for k in ("start", "mid", "end") if child(s, k)]
        c = COL.get(nn(s), (150, 150, 150))
        w = max(1, int(float(child(s, "width")[1]) * sc))
        d.line([P(float(q[1]), float(q[2])) for q in pts], fill=c + (alpha,), width=w, joint="curve")
        if not outline_only:
            for q in (pts[0], pts[-1]):
                X, Y = P(float(q[1]), float(q[2]))
                d.ellipse([X - w / 2, Y - w / 2, X + w / 2, Y + w / 2], fill=c + (alpha,))


fills("In2.Cu", 35)
fills(layer, 120)
parts = [Part(f) for f in children(r, "footprint")]
for p in parts:                                   # other layer: faint outlines
    if p.side == other:
        for poly in p.pads():
            d.polygon([P(*q) for q in poly], outline=(120, 120, 220, 110))
tracks(other, 45, True)
for p in parts:
    for pd, poly in zip(children(p.node, "pad"), p.pads()):
        lays = [str(a) for a in (child(pd, "layers") or [])[1:]]
        if p.side == layer or "*.Cu" in lays:
            c = COL.get(nn(pd), (200, 200, 200))
            d.polygon([P(*q) for q in poly], fill=c + (210,), outline=(0, 0, 0, 160))
tracks(layer, 235)
for v in children(r, "via"):
    x, y = float(child(v, "at")[1]), float(child(v, "at")[2])
    rr, dr = float(child(v, "size")[1]) / 2, float(child(v, "drill")[1]) / 2
    c = COL.get(nn(v), (150, 150, 150))
    d.ellipse([P(x - rr, y - rr), P(x + rr, y + rr)], fill=c + (255,), outline="black")
    d.ellipse([P(x - dr, y - dr), P(x + dr, y + dr)], fill="white")
for p in parts:
    if p.ref not in hints:
        continue
    b = bbox(p.courtyard()) if p.local_box("CrtYd") else bbox(p.pads()[0])
    t = f"{p.ref} ({hints[p.ref]})" if hints[p.ref] else p.ref
    X, Y = P(b[0], b[1])
    bb = d.textbbox((X, Y - 17), t, font=F(14, True))
    d.rectangle([bb[0] - 2, bb[1] - 1, bb[2] + 2, bb[3] + 1], fill=(255, 255, 255, 220))
    d.text((X, Y - 17), t, fill=(30, 30, 30), font=F(14, True))
img.save(out)
