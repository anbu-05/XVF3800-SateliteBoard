"""Overlay the built mic routes (tools/mic_route_2026_11_20.json) on route_render.py images.
draw_routes.py BASE.png OUT.png x0 y0 px_per_mm [title]   (run from PCB/mindspark_rev1)
DATA lines dark, clock tree light, per corridor; B.Cu dashed, F.Cu solid; vias as rings."""
import json
import math
import sys
from PIL import Image, ImageDraw, ImageFont

base, out = sys.argv[1], sys.argv[2]
X0, Y0, SC = map(float, sys.argv[3:6])
title = sys.argv[6] if len(sys.argv) > 6 else ""
R = json.load(open("tools/mic_route_2026_11_20.json"))
img = Image.open(base).convert("RGB")
img = Image.blend(img, Image.new("RGB", img.size, "white"), 0.35)
d = ImageDraw.Draw(img, "RGBA")
P = lambda p: ((p[0] - X0) * SC, (p[1] - Y0) * SC)  # noqa: E731
F = lambda s, b=False: ImageFont.truetype(  # noqa: E731
    "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"/MIC_DATA0": (225, 115, 0), "/MIC_DATA1": (0, 105, 225), "/MIC_DATA2": (0, 145, 65),
       "/MIC_DATA3": (165, 35, 185), "Net-(R501-Pad2)": (120, 120, 120), "/MIC_CLK": (60, 60, 60),
       "Net-(R501-Pad1)": (60, 60, 60)}
w = max(2, int(0.15 * SC))


def dashed(a, b, col, dash):
    L = math.dist(a, b)
    n = max(1, int(L / dash))
    for k in range(0, n, 2):
        s = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
        e = (a[0] + (b[0] - a[0]) * min(k + 1, n) / n, a[1] + (b[1] - a[1]) * min(k + 1, n) / n)
        d.line([s, e], fill=col, width=w)


for t in R["tracks"]:
    c = COL.get(t["net"], (0, 0, 0)) + (255,)
    pts = [P(p) for p in t["pts"]]
    for a, b in zip(pts, pts[1:]):
        if t["layer"] == "B.Cu":
            dashed(a, b, c, max(5, SC * 0.45))
        else:
            d.line([a, b], fill=c, width=w)
for v in R["vias"]:
    X, Y = P(v["at"])
    rr = max(5, 0.225 * SC)
    d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=(255, 255, 255, 255),
              outline=COL.get(v["net"], (0, 0, 0)) + (255,), width=max(2, w // 2 + 1))
if title:
    y = 6
    d.text((8, y), title, fill="black", font=F(16, True))
    y += 24
    for name, net in (("DATA0 > NE (MK501)", "/MIC_DATA0"), ("DATA1 > NW (MK502)", "/MIC_DATA1"),
                      ("DATA2 > SW (MK503)", "/MIC_DATA2"), ("DATA3 > SE (MK504)", "/MIC_DATA3"),
                      ("clock tree (R501 out)", "Net-(R501-Pad2)"), ("MIC_CLK (pin 43 > U501)", "/MIC_CLK")):
        d.line([8, y + 8, 40, y + 8], fill=COL[net], width=4)
        d.text((48, y), name, fill="black", font=F(13))
        y += 19
    d.text((8, y + 2), "dashed = B.Cu, solid = F.Cu, ring = via", fill="black", font=F(13))
img.save(out)
print(out)
