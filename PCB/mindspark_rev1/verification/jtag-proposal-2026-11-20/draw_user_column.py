"""Check of the user's east-cap-column move (2026-11-20): pads on B.Cu, the slot each JTAG line
and power feed needs (order-preserving, so nothing crosses), and each gap's width vs the room needed."""
import sys
sys.path.insert(0, "tools")
from place_tidy import BOARD, Part
from sexpr import parse, children
from PIL import Image, ImageDraw, ImageFont

root = parse(open(BOARD).read())
P = {Part(f).ref: Part(f) for f in children(root, "footprint")}
X0, Y0, X1, Y1, S = 147.5, 91.0, 159.5, 101.5, 90
img = Image.new("RGB", (int((X1 - X0) * S), int((Y1 - Y0) * S)), "white")
d = ImageDraw.Draw(img)
T = lambda x, y: ((x - X0) * S, (y - Y0) * S)
F = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"+0V9": (200, 0, 120), "+1V8": (0, 120, 220), "GND": (120, 120, 120), "PLL_AVDD": (230, 120, 0)}
JT = {"18": "TDI", "20": "TDO", "21": "RST_N", "23": "TMS", "24": "TCK"}

def pads(ref):
    out = []
    for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
        net = [c for c in pd if isinstance(c, list) and c and c[0] == "net"]
        out.append((str(pd[1]), poly, str(net[0][-1]).strip('"') if net else ""))
    return out

def box(poly):
    xs, ys = [a for a, _ in poly], [b for _, b in poly]
    return min(xs), min(ys), max(xs), max(ys)

HINT = {"C318": "1V8 bulk", "C315": "pin 17", "C303": "pin 19", "C319": "PLL pin 22", "C316": "pin 26",
        "C323": "USB stitch", "C304": "pin 27", "FB301": "PLL ferrite", "C209": "LDO out", "C325": "USB stitch",
        "C320": "xtal cap"}
for ref in list(HINT) + ["U301"]:
    for pn, poly, net in pads(ref):
        b = box(poly)
        if ref == "U301" and not (pn.isdigit() and 16 <= int(pn) <= 28):
            continue
        if b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1:
            continue
        c = (0, 150, 0) if pn in JT and ref == "U301" else COL.get(net, (170, 170, 170))
        d.rectangle([T(b[0], b[1]), T(b[2], b[3])], fill=c)
        if ref == "U301":
            lab = JT.get(pn, net if net != "unconnected-(U301-NC-Pad25)" else "NC")
            d.text(T(b[0] - 0.1, (b[1] + b[3]) / 2), f"{pn} {lab}", font=F(13), fill="black", anchor="rm")
    if ref != "U301":
        xs = [a for _, p, _ in pads(ref) for a, _ in p]; ys = [b for _, p, _ in pads(ref) for _, b in p]
        d.text(T(max(xs) + 0.08, (min(ys) + max(ys)) / 2), f"{ref} ({HINT[ref]})", font=F(12), fill="black", anchor="lm")

# gaps between the column caps and what has to pass through each (order-preserving assignment)
col = ["C318", "C315", "C303", "C319", "C316", "C323", "C304"]
need = {("C315", "C303"): ["TDI"], ("C303", "C319"): ["TDO", "RST_N"], ("C319", "C316"): ["TMS", "TCK"],
        ("C316", "C323"): [], ("C323", "C304"): [], ("C318", "C315"): []}
for a, b in zip(col, col[1:]):
    ya = max(box(p)[3] for _, p, _ in pads(a)); yb = min(box(p)[1] for _, p, _ in pads(b))
    n = need[(a, b)]
    room = 0.15 * len(n) + 0.15 * (len(n) + 1)          # tracks + clearances at 0.15
    ok = (yb - ya) >= room
    txt = f"gap {yb - ya:.2f} mm: " + (" + ".join(n) if n else "nothing passes") + \
          (f" (needs {room:.2f})" if n else "")
    d.line([T(153.0, ya), T(153.0, yb)], fill=(0, 140, 0) if ok or not n else (220, 0, 0), width=4)
    d.text(T(152.9, (ya + yb) / 2), txt, font=F(13, True), fill=(0, 120, 0) if ok or not n else (200, 0, 0), anchor="rm")
d.text((10, 8), "B.Cu after the user's move.  Grey/green = pin or pad; red bar = gap too small for what must pass;"
       " green = fits or unused", font=F(14, True), fill="black")
d.text((10, 28), "JTAG strip north was planned at x 156.2-158.0: FB301 and C209 now sit in it", font=F(14), fill=(200, 0, 0))
img.save("verification/jtag-proposal-2026-11-20/user_column_check.png")
print("ok")
