"""JTAG routing proposal sketch over a route_render image (B.Cu, x 140-168, y 64-103, 30 px/mm).
draw_jtag.py BASE.png OUT.png   (run from PCB/mindspark_rev1). Proposal only: nothing on the board."""
import math
import sys
from PIL import Image, ImageDraw, ImageFont

X0, Y0, SC = 140.0, 64.0, 30.0
img = Image.open(sys.argv[1]).convert("RGB")
img = Image.blend(img, Image.new("RGB", img.size, "white"), 0.4)
W0, H0 = img.size
out = Image.new("RGB", (W0 + 430, H0), "white")
out.paste(img, (0, 0))
d = ImageDraw.Draw(out, "RGBA")
P = lambda p: ((p[0] - X0) * SC, (p[1] - Y0) * SC)  # noqa: E731
F = lambda s, b=False: ImageFont.truetype(  # noqa: E731
    "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)


def dashed(a, b, col, w=3, dash=8):
    L = math.dist(a, b)
    n = max(1, int(L / dash))
    for k in range(0, n, 2):
        s = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
        e = (a[0] + (b[0] - a[0]) * min(k + 1, n) / n, a[1] + (b[1] - a[1]) * min(k + 1, n) / n)
        d.line([s, e], fill=col, width=w)


# five lines on a 0.45 mm strip east of the cap column (W->E: TDI, TDO, RST_N, TMS, TCK, the order
# they leave the chip in after turning north). J301 wants RST_N, TDI, TDO, TCK, TMS (W->E), so
# RST_N and TCK change layer first (south row of vias) and cross their neighbours on F.Cu while
# those are still on B.Cu; no extra vias. F.Cu order after that: RST_N, TDI, TDO, TCK, TMS.
LINES = [  # name, colour, pin y, strip x, via, F.Cu path (after the via), pad x
    ("TDI", (0, 110, 230), 96.68, 156.2, (156.2, 85.6), [], 152.69),
    ("TDO", (0, 150, 70), 97.48, 156.65, (156.65, 86.4), [], 154.69),
    ("RST_N", (120, 120, 120), 97.88, 157.1, (157.1, 88.0), [(156.7, 87.6), (155.6, 87.6)], 150.69),
    ("TMS", (210, 110, 0), 98.68, 157.55, (157.55, 85.6), [], 158.69),
    ("TCK", (180, 30, 170), 99.08, 158.0, (158.0, 88.6), [(157.5, 88.1), (157.1, 88.1)], 156.69),
]
for name, col, py, sx, via, fmid, px in LINES:
    c = col + (255,)
    pts_b = [(150.06, py), (sx - 0.6, py), (sx, py - 0.6), via]
    for a, b in zip(pts_b, pts_b[1:]):
        dashed(P(a), P(b), c)
    cur = fmid[-1] if fmid else via
    dx = px - cur[0]
    pts_f = [via] + fmid + [(cur[0], 72.6 + abs(dx)), (px, 72.6), (px, 70.2)]
    for a, b in zip(pts_f, pts_f[1:]):
        d.line([P(a), P(b)], fill=c, width=3)
    X, Y = P(via)
    d.ellipse([X - 7, Y - 7, X + 7, Y + 7], fill=(255, 255, 255, 255), outline=c, width=3)
    d.text((P((px, 69.6))[0] - 14, P((px, 69.6))[1] - 16), name, fill=col, font=F(12, True))
# RST_N branch to R703 (ESP32's reset path)
d.line([P((157.1, 88.0)), P((158.23, 89.13)), P((158.23, 91.95))], fill=(120, 120, 120, 255), width=3)

# moves / problem spots
def box(x0, y0, x1, y1, col, txt, tx=None):
    d.rectangle([P((x0, y0)), P((x1, y1))], outline=col + (255,), width=3)
    if txt:
        d.text(tx or (P((x1, y0))[0] + 4, P((x1, y0))[1]), txt, fill=col, font=F(12, True))


box(150.5, 95.6, 152.25, 99.6, (220, 0, 0), "")
d.text(P((140.3, 100.4)), "zone between pins and caps (1.8 mm):\n5 JTAG lines + 5 power feeds + PLL_AVDD", fill=(200, 0, 0), font=F(12, True))
box(152.0, 95.0, 154.0, 100.5, (220, 0, 0), "", None)
box(153.9, 97.6, 156.1, 99.0, (230, 120, 0), "FB301: move", (P((150.2, 101.7))[0], P((150.2, 101.7))[1]))
box(157.0, 95.9, 158.4, 98.1, (230, 120, 0), "C209: move", (P((158.6, 95.0))[0], P((158.6, 95.0))[1]))
d.text(P((140.3, 88.3)), "module's north edge:\nvias must sit north of it", fill=(60, 60, 60), font=F(12))

# side panel
x, y = W0 + 14, 12
d.text((x, y), "JTAG proposal (sketch)", fill="black", font=F(20, True))
y += 34
lines = [
    ("Corridor (east route)", True),
    ("B.Cu from pins 18/20/21/23/24 east", False),
    ("through the east cap column, north", False),
    ("in a strip east of it (over In2 +1V8,", False),
    ("the JTAG I/O rail), one via each just", False),
    ("north of the ESP32 module, F.Cu over", False),
    ("In1 GND to J301 (crosses the NE mic", False),
    ("pair, which is on B.Cu). ~25 mm, 1 via.", False),
    ("", False),
    ("Order fixes, no extra vias", True),
    ("RST_N and TCK go up to F.Cu first", False),
    ("(south row of vias) and cross over", False),
    ("their neighbours on F.Cu.", False),
    ("", False),
    ("Hard part: the escape", True),
    ("The 1.8 mm zone between the pins", False),
    ("and the cap column also carries the", False),
    ("power feeds (pins 17/19/26/27) and", False),
    ("PLL_AVDD (pin 22, between RST_N and", False),
    ("TMS). Needs a cap-column re-stack:", False),
    ("C315/C303 lower, C316/C319/C323 out,", False),
    ("and FB301 + C209 moved off the strip.", False),
    ("", False),
    ("dashed = B.Cu, solid = F.Cu, ring = via", False),
    ("red = tight, orange = part to move", False),
]
for t, b in lines:
    d.text((x, y), t, fill="black", font=F(13, b))
    y += 19
out.save(sys.argv[2])
print(sys.argv[2])
