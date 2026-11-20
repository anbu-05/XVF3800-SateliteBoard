"""Proposed east-cap-column positions (uneven gaps) for the JTAG escape, 2026-11-20. Dry run only.
Second version: FB301 (PLL ferrite) sits in the column under C319, as the user placed it. Both are
turned so their PLL_AVDD pads face east and meet on a short stub; pin 22's feed enters through the
gap between them. FB301's +0V9 pad (west) gets a via and an F.Cu jumper under the module to C323's
+0V9 pad (the F.Cu east of x 155 is blocked by the ESP32 module's east pad row).
The script
reads the board, moves copies of the pads, sketches the JTAG lines and power feeds on B.Cu as 45-degree
jog routes and measures the copper clearances. Writes column_proposal.png beside this script."""
import math
import sys
sys.path.insert(0, "tools")
from place_tidy import BOARD, Part
from sexpr import parse, children
from PIL import Image, ImageDraw, ImageFont

OUT = "verification/jtag-proposal-2026-11-20/column_proposal.png"
W = 0.15                      # track width
COLX = 154.6868               # column x as the user left it
# proposed centre per part: (x, y). Column: C304 fixed at pin 27; 1.07 pitch where nothing passes,
# 1.52 for two lines (0.9 pad gap = 3 x 0.2 clearance + 2 x 0.15), 1.17 for one line (0.55 gap).

# (x, y, rotation), stacked up from C304 (fixed level with pin 27, just north of the USB pair).
# Pad gaps: 0.45 where one line passes, 0.75 for two (0.15 clearance, the Default rule), courtyard
# minimum (0.15) where nothing passes. The column moves DX east so the steepest fan line (pin 17,
# rising ~3.5 mm) fits at 45 degrees; FB301's via-in-pad then still clears the module's F.Cu pad row.
DX = 0.30
CX = COLX + DX
PADH = {"C": 0.62, "FB": 0.64}             # pad heights (0402 cap, 0402 ferrite)
STACK = [("C304", None), ("C323", 0.45), ("C316", 0.45), ("FB301", 0.75), ("C319", 0.45),
         ("C303", 0.75), ("C315", 0.45)]    # (part, pad gap to the part below it)
NEW, y, h_prev = {}, 99.9904, PADH["C"]
for ref, g in STACK:
    h = PADH["FB" if ref.startswith("FB") else "C"]
    if g is not None:
        y -= h_prev / 2 + g + h / 2
    NEW[ref] = (CX, round(y, 4), {"C319": 180}.get(ref, 0))
    h_prev = h
NEW["C318"] = (max(CX - 0.39, 154.30), round(NEW["C315"][1] - 0.46 - 0.15 - 0.73, 4), 0)
SHIFT = 0.40 + DX                           # LDO group east, out of the JTAG strip
NEW.update({"U203": (160.35 + SHIFT, 97.0, 180), "C208": (163.01 + SHIFT, 97.0, 90),
            "C209": (157.6832 + SHIFT, 95.5268, 90)})
root = parse(open(BOARD).read())
P = {Part(f).ref: Part(f) for f in children(root, "footprint")}


def moved(ref, pts):
    """Points of a part moved to its NEW pose (a 180-degree turn mirrors them through the centre)."""
    if ref not in NEW:
        return pts
    ax, ay, ar = P[ref].at
    nx, ny, nr = NEW[ref]
    flip = round((nr - ar) % 360) == 180
    return [(nx - (a - ax), ny - (b - ay)) if flip else (nx + a - ax, ny + b - ay) for a, b in pts]


def pads(ref):
    out = []
    for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
        net = [c for c in pd if isinstance(c, list) and c and c[0] == "net"]
        poly = moved(ref, poly)
        xs, ys = [a for a, _ in poly], [b for _, b in poly]
        out.append((str(pd[1]), (min(xs), min(ys), max(xs), max(ys)), str(net[0][-1]).strip('"') if net else ""))
    return out


def ctyd(ref):
    b = moved(ref, P[ref].courtyard())
    xs, ys = [a for a, _ in b], [c for _, c in b]
    return min(xs), min(ys), max(xs), max(ys)


pin = {pn: b for pn, b, _ in pads("U301") if pn.isdigit()}
py = lambda n: (pin[n][1] + pin[n][3]) / 2
cy = lambda r: NEW[r][1]
X_PIN = 150.46                # pin outer end
PAD1_W = 153.93 + DX          # column pad 1 west edge
EAST = 155.45 + DX            # column pad 2 east edge


def gap(a, b):                # y range between two column caps' pads
    return max(bb[3] for _, bb, _ in pads(a)), min(bb[1] for _, bb, _ in pads(b))


g_tdi, g_2a, g_2b = gap("C315", "C303"), gap("C303", "C319"), gap("FB301", "C316")
mid = lambda g: (g[0] + g[1]) / 2
# exit rows through the gaps (track centres), lanes going north east of the column (0.4 pitch)
ROW = {"18": mid(g_tdi), "20": mid(g_2a) - 0.15, "21": mid(g_2a) + 0.15,
       "23": mid(g_2b) - 0.15, "24": mid(g_2b) + 0.15}
LANE = {k: v + DX for k, v in {"18": 155.80, "20": 156.20, "21": 156.60, "23": 157.00, "24": 157.40}.items()}
NAME = {"18": "TDI", "20": "TDO", "21": "RST_N", "23": "TMS", "24": "TCK"}
POWER = {"17": "C315", "19": "C303", "22": "C319", "26": "C316", "27": "C304"}
STUB_X = 155.22 + DX  # PLL_AVDD stub joining the east pads of C319 and FB301


def fan(y0, y1, xs):
    """East from the pin at y0, 45-degree jog north starting at x xs, then east at y1."""
    return [(X_PIN - 0.3, y0), (xs, y0), (xs + (y0 - y1), y1)]


# jog starts staggered so the parallel diagonals keep their spacing; the pin with the most rise jogs first
order = ["17", "18", "19", "20", "21", "22", "23", "24", "26", "27"]
target = {**{p: cy(c) for p, c in POWER.items()}, **ROW, "22": mid(gap("C319", "FB301"))}
tracks = []
xs = 150.62
for p in order:
    y0, y1 = py(p), target[p]
    pts = fan(y0, y1, xs)
    if p == "22":
        pts.append((STUB_X, y1))
    elif p in POWER:
        pts.append((PAD1_W + 0.28, y1))
    else:
        pts += [(LANE[p], y1), (LANE[p], 88.6)]
    tracks.append((p, pts))
    xs += 0.06                # each next pin starts its jog a little further east
# XIN: pin 16 north-west of the whole fan, up to the crystal pad 1
xin = [(X_PIN - 0.3, py("16")), (150.52, py("16")), (152.05, py("16") - 1.53), (152.05, 91.2)]
tracks.insert(0, ("16", xin))
pll = [b for r in ("C319", "FB301") for pn, b, n in pads(r) if n == "PLL_AVDD"]
tracks.append(("22s", [(STUB_X, (pll[0][1] + pll[0][3]) / 2), (STUB_X, (pll[1][1] + pll[1][3]) / 2)]))
# FB301 +0V9 jumper on F.Cu: via in FB301's west pad, dodge C316's +1V8 via-in-pad to the west,
# via in C323's +0V9 pad
fbv = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for pn, b, n in pads("FB301") if n == "+0V9"][0]
c23 = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for pn, b, n in pads("C323") if n == "+0V9"][0]
JX = 153.6 + DX
JUMP = [fbv, (JX, fbv[1] + (fbv[0] - JX)), (JX, c23[1] - (c23[0] - JX)), c23]


def seg_box(a, b, bx):        # distance from segment ab to an axis-aligned box
    best = 9.0
    for t in [i / 60 for i in range(61)]:
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx = max(bx[0] - x, 0, x - bx[2]); dy = max(bx[1] - y, 0, y - bx[3])
        best = min(best, math.hypot(dx, dy))
    return best


def seg_seg(a, b, c, d):
    best = 9.0
    for t in [i / 60 for i in range(61)]:
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        for u in [i / 60 for i in range(61)]:
            X, Y = c[0] + (d[0] - c[0]) * u, c[1] + (d[1] - c[1]) * u
            best = min(best, math.hypot(x - X, y - Y))
    return best


REFS = ["C318", "C315", "C303", "C319", "C316", "C323", "C304", "C209", "FB301", "U203", "C320", "Y301",
        "R301", "R302", "C325"]
netof = {"16": "/xvf3800/XVF_XIN", "17": "+1V8", "19": "+0V9", "22": "PLL_AVDD", "22s": "PLL_AVDD", "26": "+1V8", "27": "+0V9"}
worst = []
for p, pts in tracks:
    for a, b in zip(pts, pts[1:]):
        for r in REFS:
            for pn, bx, net in pads(r):
                if net == netof.get(p, "?"):
                    continue
                if p == "16" and r in ("Y301", "C320") and net == netof["16"]:
                    continue
                worst.append((seg_box(a, b, bx) - W / 2, f"{NAME.get(p, 'pin ' + p)} - {r}.{pn}"))
        for q, qts in tracks:
            if q <= p or {p, q} == {"22", "22s"}:
                continue
            for c, d in zip(qts, qts[1:]):
                worst.append((seg_seg(a, b, c, d) - W, f"{NAME.get(p, 'pin ' + p)} - {NAME.get(q, 'pin ' + q)}"))
worst.sort()
print("closest copper gaps (mm):")
for v, what in worst[:8]:
    print(f"  {v:.3f}  {what}")
# courtyard gaps between moved parts and their neighbours
print("courtyard gaps:")
for a, b in [("C318", "C315"), ("C318", "C320"), ("C318", "Y301"), ("C315", "C303"), ("C303", "C319"),
             ("C319", "FB301"), ("FB301", "C316"), ("C316", "C323"), ("C323", "C304"),
             ("U203", "C208"), ("U203", "C209"), ("U203", "C325")]:
    A, B = ctyd(a), ctyd(b)
    gx = max(B[0] - A[2], A[0] - B[2]); gy = max(B[1] - A[3], A[1] - B[3])
    print(f"  {a}/{b}: {max(gx, gy):.2f}")
print("gaps:", {k: round(v[1] - v[0], 2) for k, v in (("TDI", g_tdi), ("TDO+RST", g_2a), ("TMS+TCK", g_2b),
                                                       ("pin 22", gap("C319", "FB301")))})
print("positions:", NEW)
print("jumper:", [tuple(round(c, 2) for c in q) for q in JUMP])
for vx, vy in (fbv, c23):        # through vias must clear the module's F.Cu east pad row (x >= 155.16)
    print(f"  via at ({vx:.2f}, {vy:.2f}): {155.16 - (vx + 0.225):.2f} mm from the module pad row")

# ---------------------------------------------------------------- drawing
X0, Y0, X1, Y1, S = 146.0, 88.4, 164.2, 101.2, 64
img = Image.new("RGB", (int((X1 - X0) * S), int((Y1 - Y0) * S) + 60), "white")
d = ImageDraw.Draw(img)
T = lambda x, y: ((x - X0) * S, (y - Y0) * S + 60)
F = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"+0V9": (200, 0, 120), "+1V8": (0, 120, 220), "GND": (130, 130, 130), "PLL_AVDD": (230, 120, 0),
       "+3V3": (0, 150, 0)}
HINT = {"C318": "1V8 bulk", "C315": "pin 17", "C303": "pin 19", "C319": "PLL pin 22", "C316": "pin 26",
        "C323": "USB stitch", "C304": "pin 27", "FB301": "PLL ferrite", "C209": "LDO out", "U203": "1V8 LDO",
        "C208": "LDO in", "C325": "USB stitch", "C320": "xtal cap", "Y301": "crystal", "R301": "", "R302": ""}
for r in HINT:
    mv = r in NEW
    if mv:   # old outline, dashed grey
        b = P[r].courtyard(); xs_, ys_ = [a for a, _ in b], [c for _, c in b]
        d.rectangle([T(min(xs_), min(ys_)), T(max(xs_), max(ys_))], outline=(200, 200, 200))
    for pn, bx, net in pads(r):
        d.rectangle([T(bx[0], bx[1]), T(bx[2], bx[3])], fill=COL.get(net, (180, 180, 180)))
    c = ctyd(r)
    d.rectangle([T(*c[:2]), T(*c[2:])], outline=(0, 0, 0) if mv else (170, 170, 170))
    if HINT[r]:
        d.text(T(c[2] + 0.05, (c[1] + c[3]) / 2), f"{r} ({HINT[r]})", font=F(12, mv), fill="black", anchor="lm")
for pn, bx in pin.items():
    if 16 <= int(pn) <= 27:
        net = netof.get(pn)
        d.rectangle([T(bx[0], bx[1]), T(bx[2], bx[3])], fill=COL.get(net, (0, 150, 60) if pn in NAME else (180, 180, 180)))
        d.text(T(bx[0] - 0.08, (bx[1] + bx[3]) / 2), f"{pn} {NAME.get(pn, netof.get(pn, 'NC' if pn == '25' else 'XIN'))}",
               font=F(11), fill="black", anchor="rm")
for i in range(len(JUMP) - 1):      # F.Cu jumper, dashed
    (ax_, ay_), (bx_, by_) = JUMP[i], JUMP[i + 1]
    n = 12
    for k in range(0, n, 2):
        d.line([T(ax_ + (bx_ - ax_) * k / n, ay_ + (by_ - ay_) * k / n),
                T(ax_ + (bx_ - ax_) * (k + 1) / n, ay_ + (by_ - ay_) * (k + 1) / n)], fill=(200, 0, 120), width=4)
for vx, vy in (fbv, c23):
    d.ellipse([T(vx - 0.225, vy - 0.225), T(vx + 0.225, vy + 0.225)], outline="black", width=2)
for p, pts in tracks:
    c = (0, 160, 60) if p in NAME else COL.get(netof.get(p), (120, 0, 200))
    d.line([T(*q) for q in pts], fill=c, width=max(2, int(W * S)), joint="curve")
    if p in NAME:
        d.text(T(pts[-1][0], pts[-1][1] - 0.1), NAME[p], font=F(11, True), fill=(0, 120, 40), anchor="lb")
for lab, g in (("0.55", g_tdi), ("0.90", g_2a), ("0.90", g_2b)):
    d.text(T(PAD1_W - 0.05, mid(g)), "", font=F(10), fill="black")
d.text((10, 6), "Proposed east cap column (bold outline = moved, grey = where it is now). B.Cu sketch: JTAG green,",
       font=F(14, True), fill="black")
d.text((10, 26), "power feeds in net colours, XIN purple. Gaps: TDI 0.45, TDO+RST 0.75, pin 22 0.45, TMS+TCK 0.75 mm;"
       " unused gaps at the courtyard minimum.", font=F(14), fill="black")
d.text((10, 44), "C319 and FB301 turned: PLL pads east, joined by a stub. Dashed magenta = F.Cu jumper, +0V9 to FB301"
       " (circles = vias).", font=F(13), fill=(150, 0, 90))
img.save(OUT)
print("wrote", OUT)
