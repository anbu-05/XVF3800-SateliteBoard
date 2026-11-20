"""Final drawings of the mic routing proposal.
draw_final.py ROUTES.json BASE_FULL.png OUT_overview.png OUT_fanout.png"""
import json
import math
import sys
from PIL import Image, ImageDraw, ImageFont

R = json.load(open(sys.argv[1]))
X0, Y0, SC = 109.5, 61.6, 16.0
F = lambda s, b=False: ImageFont.truetype(  # noqa: E731
    "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"NE": (225, 115, 0), "NW": (0, 105, 225), "SW": (0, 145, 65), "SE": (165, 35, 185)}
lighter = lambda c: tuple(int(v * 0.5 + 255 * 0.5) for v in c)  # noqa: E731


def dashed(d, a, b, col, w, dash):
    L = math.dist(a, b)
    n = max(1, int(L / dash))
    for k in range(0, n, 2):
        s = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
        e = (a[0] + (b[0] - a[0]) * min(k + 1, n) / n, a[1] + (b[1] - a[1]) * min(k + 1, n) / n)
        d.line([s, e], fill=col, width=w)


def inter(a, b, c, e):
    """Intersection of segments a-b and c-e, or None."""
    d1 = (b[0] - a[0], b[1] - a[1])
    d2 = (e[0] - c[0], e[1] - c[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * d2[1] - (c[1] - a[1]) * d2[0]) / den
    u = ((c[0] - a[0]) * d1[1] - (c[1] - a[1]) * d1[0]) / den
    return (a[0] + t * d1[0], a[1] + t * d1[1]) if 0 <= t <= 1 and 0 <= u <= 1 else None


# ============================================================ overview
base = Image.open(sys.argv[2]).convert("RGB")
base = Image.blend(base, Image.new("RGB", base.size, "white"), 0.5)
BW, BH = base.size
img = Image.new("RGB", (BW + 470, max(BH, 1190)), "white")
img.paste(base, (0, 0))
d = ImageDraw.Draw(img, "RGBA")
P = lambda p: ((p[0] - X0) * SC, (p[1] - Y0) * SC)  # noqa: E731

# where the fan-out happens (sketch in the second picture)
fx0, fy0, fx1, fy1 = P((135.6, 95.4)) + P((143.6, 103.0))
d.rectangle([fx0, fy0, fx1, fy1], outline=(60, 60, 60, 255), width=2)
d.text((fx0, fy1 + 4), "fan-out\n(2nd picture)", fill=(40, 40, 40), font=F(13, True))
# clock buffer now / proposed
ux, uy = P((146.4, 111.2))
d.ellipse([ux - 26, uy - 26, ux + 26, uy + 26], outline=(200, 0, 0, 255), width=3)
d.text((ux + 30, uy - 8), "U501/R501 clock buffer:\nmove from here (between\nthe two bucks) to the fan-out", fill=(200, 0, 0),
       font=F(12, True))

for rt in R["routes"]:
    corner = rt["name"].split(">")[-1].strip()
    clk = rt["name"].startswith("CLK")
    c = (lighter(COL[corner]) if clk else COL[corner]) + (255,)
    for layer, path, ok in rt["legs"]:
        pts = [P(q) for q in path]
        for a, b in zip(pts, pts[1:]):
            if layer == "B.Cu":
                dashed(d, a, b, c, 3, 7)
            else:
                d.line([a, b], fill=c, width=3)
    for v in rt["vias"]:
        X, Y = P(v)
        d.ellipse([X - 6, Y - 6, X + 6, Y + 6], fill=(255, 255, 255, 255), outline=c, width=3)

# clash markers: where a proposed F.Cu route crosses a power track that power_v2 must move
groups = {}
for name, pn, c0, c1 in R["clashes"]:
    pl = "F.Cu"
    rt = next(x for x in R["routes"] if x["name"] == name.replace(" via", ""))
    for layer, path, _ in rt["legs"]:
        if layer != pl:
            continue
        for a, b in zip(path, path[1:]):
            q = inter(a, b, c0, c1)
            if q:
                groups.setdefault(pn + " " + name.split(">")[-1].strip(), []).append(q)
LABEL = {"+5V SW": "+5V branch to the west edge", "+3V3 SW": "+3V3 feed to the SW mic (FB503)",
         "+1V8 SE": "+1V8 feed to J701", "+3V3 SE": "+3V3 feed to the SE mic (FB504)"}
marks = []
for k, (key, qs) in enumerate(sorted(groups.items(), key=lambda kv: kv[0][-2:])):
    cx = sum(q[0] for q in qs) / len(qs)
    cy = sum(q[1] for q in qs) / len(qs)
    X, Y = P((cx, cy))
    d.ellipse([X - 15, Y - 15, X + 15, Y + 15], outline=(220, 0, 0, 255), width=3)
    d.text((X + 17, Y - 22), str(k + 1), fill=(220, 0, 0), font=F(18, True))
    marks.append((k + 1, key))

# corner labels
for corner, pos, txt in [("NW", (111.2, 76.5), "MK502 (NW)\nDATA1 + CLK"), ("NE", (169.2, 76.5), "MK501 (NE)\nDATA0 + CLK"),
                         ("SW", (111.2, 112.0), "MK503 (SW)\nDATA2 + CLK"), ("SE", (174.0, 121.0), "MK504 (SE)\nDATA3 + CLK")]:
    d.text(P(pos), txt, fill=COL[corner], font=F(14, True))

# ---- side panel
x = BW + 18
y = 14
d.text((x, y), "Mic routing proposal", fill="black", font=F(22, True))
y += 40
lines = [
    ("Each mic gets its DATA and CLK as a pair:", True),
    ("same corridor, ≥0.45 mm apart, 0.15 mm wide.", False),
    ("", False),
]
for t, b in lines:
    d.text((x, y), t, fill="black", font=F(14, b))
    y += 20
# legend
for corner in ("NE", "NW", "SW", "SE"):
    d.line([x, y + 9, x + 40, y + 9], fill=COL[corner], width=4)
    d.line([x + 50, y + 9, x + 90, y + 9], fill=lighter(COL[corner]), width=4)
    d.text((x + 100, y), f"{corner}: DATA (dark), CLK (light)", fill="black", font=F(14))
    y += 24
y += 6
d.line([x, y + 9, x + 40, y + 9], fill=(70, 70, 70), width=3)
d.text((x + 50, y), "F.Cu (over solid In1 GND)", fill="black", font=F(14))
y += 24
dashed(d, (x, y + 9), (x + 40, y + 9), (70, 70, 70), 3, 7)
d.text((x + 50, y), "B.Cu (over In2 +3V3)", fill="black", font=F(14))
y += 24
d.ellipse([x + 14, y + 3, x + 26, y + 15], fill="white", outline=(70, 70, 70), width=3)
d.text((x + 50, y), "via 0.45/0.2, inside the LED ring", fill="black", font=F(14))
y += 24
d.ellipse([x + 5, y, x + 35, y + 30], outline=(220, 0, 0), width=3)
d.text((x + 50, y + 5), "power track in the way (below)", fill="black", font=F(14))
y += 44

notes = [
    ("Why this shape", True),
    ("• B.Cu can't cross the LED ring (+5V_LED on B.Cu),", False),
    ("  so every pair goes up to F.Cu just inside it.", False),
    ("• Inside the ring, F.Cu is fenced in by power", False),
    ("  tracks (+5V, +1V8, +3V3), so the inner part runs", False),
    ("  on B.Cu, which is almost empty there.", False),
    ("• 1 via per line on the long run; F.Cu outside", False),
    ("  the ring sits over solid GND.", False),
    ("• Corridors keep ≥2.5 mm from the bucks", False),
    ("  (L201/L202), the amp U503 and speaker J501.", False),
    ("• At ~3 MHz PDM, length matching isn't needed:", False),
    ("  60 mm ≈ 0.4 ns vs a 160 ns half-period.", False),
    ("", False),
    ("Lengths (router), mm", True),
]
for t, b in notes:
    d.text((x, y), t, fill="black", font=F(14, b))
    y += 20
for corner, dn, cn in [("NW", "DATA1 > NW", "CLK > NW"), ("NE", "DATA0 > NE", "CLK > NE"),
                       ("SW", "DATA2 > SW", "CLK > SW"), ("SE", "DATA3 > SE", "CLK > SE")]:
    def L(n, lay=None):
        rt = next(r for r in R["routes"] if r["name"] == n)
        return sum(math.dist(a, b) for l, p, _ in rt["legs"] if lay in (None, l) for a, b in zip(p, p[1:]))
    d.text((x, y), f"{corner}: DATA {L(dn):.0f} (B.Cu {L(dn, 'B.Cu'):.0f}), CLK {L(cn):.0f}", fill=COL[corner],
           font=F(14, True))
    y += 20
y += 14
d.text((x, y), "Power tracks to move (power_v2 reruns", fill=(200, 0, 0), font=F(14, True))
y += 20
d.text((x, y), "after the mics are laid, like the USB pair)", fill=(200, 0, 0), font=F(14, True))
y += 24
for k, key in marks:
    d.text((x, y), f"{k}. {LABEL.get(key, key)}", fill="black", font=F(14))
    y += 20
y += 10
for t in ["NW and NE: nothing in the way.",
          "SE: B.Cu passes from In2 +3V3 to +5V",
          "near y 120: one stitching cap there."]:
    d.text((x, y), t, fill="black", font=F(14))
    y += 20
img.save(sys.argv[3])

# ============================================================ fan-out sketch (not to scale)
W2, H2 = 1150, 620
s = Image.new("RGB", (W2, H2), "white")
d = ImageDraw.Draw(s, "RGBA")
d.text((20, 12), "Fan-out at the XVF3800 west edge — topology sketch (not to scale; details in the escape pass)",
       fill="black", font=F(17, True))
# XVF block and pins
d.rectangle([900, 70, 1010, 560], outline="black", width=2, fill=(250, 235, 245))
d.text((955, 315), "U301\nXVF3800\n(B.Cu)", fill="black", font=F(14, True), anchor="mm", align="center")
pins = [("51", "DATA3 → SE", "SE", 140), ("50", "DATA1 → NW", "NW", 200), ("48", "DATA2 → SW", "SW", 270),
        ("46", "DATA0 → NE", "NE", 340), ("43", "MIC_CLK (S edge)", None, 470)]
for pn, lab, corner, py in pins:
    col = COL[corner] if corner else (60, 60, 60)
    d.rectangle([886, py - 5, 900, py + 5], fill=col)
    d.text((1016, py - 8), f"pin {pn}", fill="black", font=F(13))
    d.text((760, py - 24), lab, fill=col, font=F(13, True))
# cap column
for cy, nm in [(110, "C308"), (170, "C312"), (235, "C307")]:
    d.rectangle([700, cy - 12, 740, cy + 12], fill=(210, 210, 210), outline="black")
    d.text((720, cy), nm, fill="black", font=F(11), anchor="mm")
d.text((600, 40), "cap column: widen the C312/C307 gap\n(~0.4 mm) so DATA3 + DATA1 pass side by side", fill=(150, 0, 0), font=F(12, True))
d.rectangle([600, 480, 660, 510], outline=(150, 0, 0), width=2)
d.text((630, 495), "C309", fill=(150, 0, 0), font=F(12, True), anchor="mm")
d.text((668, 482), "bulk cap: moves off\nthe fan-out", fill=(150, 0, 0), font=F(12, True))
# module edge
d.line([560, 60, 560, 580], fill=(120, 120, 120), width=2)
d.text((420, 40), "ESP32 module\nwest edge", fill=(90, 90, 90), font=F(12))
d.text((566, 535), "under the module →\nF.Cu free, over GND", fill=(90, 90, 90), font=F(12))
# fan points (left)
fan = [("DATA0", "NE", 120, False), ("CLK", "NE", 150, True), ("DATA1", "NW", 210, False), ("CLK", "NW", 240, True),
       ("CLK", "SW", 330, True), ("DATA2", "SW", 360, False), ("DATA3", "SE", 430, False), ("CLK", "SE", 460, True)]
for nm, corner, fy, clk in fan:
    col = lighter(COL[corner]) if clk else COL[corner]
    d.ellipse([400 - 5, fy - 5, 400 + 5, fy + 5], fill=col)
    d.line([300, fy, 395, fy], fill=col, width=3)
    d.text((140, fy - 9), f"{nm} → {corner} corridor", fill=col, font=F(13, True))


def hop(d, pts, col):
    """B.Cu dashed, F.Cu solid, via at every layer change: pts = [(x, y, layer), ...]"""
    for (x1, y1, l1), (x2, y2, l2) in zip(pts, pts[1:]):
        if l2 == "B":
            dashed(d, (x1, y1), (x2, y2), col, 3, 7)
        else:
            d.line([(x1, y1), (x2, y2)], fill=col, width=3)
    for (x1, y1, l1), (x2, y2, l2) in zip(pts, pts[1:]):
        if l1 != l2:
            d.ellipse([x1 - 7, y1 - 7, x1 + 7, y1 + 7], fill="white", outline=col, width=3)


# DATA1, DATA2: straight on B.Cu
hop(d, [(886, 200, "B"), (770, 200, "B"), (760, 212, "B"), (600, 212, "B"), (405, 210, "B")], COL["NW"])
hop(d, [(886, 270, "B"), (670, 270, "B"), (590, 360, "B"), (405, 360, "B")], COL["SW"])
# DATA3 (top pin, goes south): through the cap gap, then a short F.Cu hop under the module
hop(d, [(886, 140, "B"), (770, 140, "B"), (745, 192, "B"), (655, 192, "B"), (655, 410, "F"), (560, 430, "B"),
        (405, 430, "B")], COL["SE"])
# DATA0 (bottom pin, goes north): below the caps, F.Cu hop north under the module
hop(d, [(886, 340, "B"), (690, 340, "B"), (690, 120, "F"), (560, 120, "B"), (405, 120, "B")],
    COL["NE"])
# MIC_CLK pin 43 to the moved buffer, clock star; NE and SE branches hop on F.Cu
d.rectangle([215, 268, 300, 302], outline=(200, 0, 0), width=2, fill=(255, 240, 240))
d.text((257, 285), "U501+R501", fill=(200, 0, 0), font=F(12, True), anchor="mm")
d.text((150, 304), "clock buffer, moved here", fill=(200, 0, 0), font=F(12))
hop(d, [(886, 470, "B"), (800, 470, "B"), (800, 520, "F"), (257, 520, "F"), (257, 304, "F"), (257, 302, "B")], (60, 60, 60))
star = (330, 285)
d.line([(300, 285), star], fill=(60, 60, 60), width=3)
for fy, corner, layer_hop in [(240, "NW", False), (330, "SW", False), (150, "NE", True), (460, "SE", True)]:
    col = lighter(COL[corner])
    if not layer_hop:
        hop(d, [(star[0], star[1], "B"), (360, fy, "B"), (395, fy, "B")], col)
    else:
        mid = 350 if corner == "NE" else 345
        hop(d, [(star[0], star[1], "B"), (mid, star[1] + (-15 if corner == "NE" else 15), "B"),
                (mid, fy + (10 if corner == "NE" else -10), "F"), (380, fy, "B"), (395, fy, "B")], col)
d.ellipse([star[0] - 4, star[1] - 4, star[0] + 4, star[1] + 4], fill=(60, 60, 60))
# legend
d.line([20, 560, 60, 560], fill=(60, 60, 60), width=3)
d.text((68, 552), "F.Cu", fill="black", font=F(13))
dashed(d, (120, 560), (160, 560), (60, 60, 60), 3, 7)
d.text((168, 552), "B.Cu", fill="black", font=F(13))
d.ellipse([224, 553, 238, 567], fill="white", outline=(60, 60, 60), width=3)
d.text((246, 552), "via", fill="black", font=F(13))
d.text((20, 585), "Pin order N→S is SE, NW, SW, NE: DATA3 and DATA0 swap ends with one short F.Cu hop each (2 extra vias).",
       fill="black", font=F(13))
s.save(sys.argv[4])
print("ok")
