"""Centred east cap column with the main USB pair moved south (user's idea, 2026-11-20). Dry run:
reads the board, moves copies of the pads, sketches every B.Cu line on the east side of the
XVF3800 and measures the clearances. Writes column_centred.png beside this script.

Layout:
  * Column, north to south: C318 (1.8 V bulk), C315 (pin 17), C303 (pin 19), C319 (PLL cap),
    FB301 (PLL ferrite), C316 (pin 26), C304 (pin 27), C323 (USB stitch); then the USB pair;
    then C324 (USB stitch), C313 (pin 30), C314 (3.3 V bulk). Pad gaps: 0.45 for one line,
    0.75 for two (0.15 clearance), courtyard minimum where nothing passes.
  * C319 and FB301 are turned so their PLL pads face east and meet on a short stub; pin 22's
    feed enters through the gap between them. FB301's +0V9 pad (west) has a via and an F.Cu
    jumper to C304's +0V9 pad.
  * North of pin 27 the feeds climb in a 45-degree fan (staggered so the diagonals keep their
    spacing). South of it, pin 30 and the USB pair turn straight down in nested lanes, run east
    under the column and climb at 45 degrees back to the existing layer-change vias, so the
    vias, the F.Cu part of the pair and C325/C326 stay as they are.
  * The column x is the smallest that passes the clearance check (searched below).
Run from PCB/mindspark_rev1:  python3 verification/jtag-proposal-2026-11-20/column_centred.py
"""
import math
import sys
sys.path.insert(0, "tools")
from place_tidy import BOARD, Part
from sexpr import parse, children
from PIL import Image, ImageDraw, ImageFont

OUT = "verification/jtag-proposal-2026-11-20/column_centred.png"
W, WU = 0.15, 0.25            # signal / power track width, USB track width
CLR = 0.15                    # Default netclass clearance
PIN_X = 150.16                # tracks start 0.1 inside the pin pad's outer end (150.46)
root = parse(open(BOARD).read())
P = {Part(f).ref: Part(f) for f in children(root, "footprint")}


def net_of(pd):
    n = [c for c in pd if isinstance(c, list) and c and c[0] == "net"]
    return str(n[0][-1]).strip('"') if n else ""


pin = {}
for pd, poly in zip(children(P["U301"].node, "pad"), P["U301"].pads()):
    if str(pd[1]).isdigit():
        xs, ys = [a for a, _ in poly], [b for _, b in poly]
        pin[str(pd[1])] = ((min(xs), min(ys), max(xs), max(ys)), net_of(pd))
py = lambda n: (pin[n][0][1] + pin[n][0][3]) / 2

# pad offsets of the parts as they are now (local x of each pad's west/east edge, relative to the
# footprint centre, at the rotation they will have)
STACK = [  # name, pad height, pad gap to the next part (None = courtyard minimum), new rotation
    ("C315", .62, .45, 0), ("C303", .62, .75, 0), ("C319", .62, .45, 180), ("FB301", .64, .75, 0),
    ("C316", .62, None, 0), ("C304", .62, None, 0), ("C323", .62, "PAIR", 0),
    ("C324", .62, None, 0), ("C313", .62, None, 0), ("C314", .95, None, 0)]
CTYD_HALF = {"C314": .73}     # courtyard half heights (0402 parts: 0.46)


def build(pad_w, top):
    """Return {ref: (x, y, rot)} for the column whose pad-1 west edges sit at pad_w."""
    new, y, prev = {}, top, None
    for name, h, g, rot in STACK:
        if prev is not None:
            pn, ph, pg = prev
            if pg == "PAIR":
                y = pn_bottom + 0.2 + WU + 0.4 + 0.2      # pair (0.4 pitch) with 0.2 each side
            elif pg is None:
                y = pn_bottom + (CTYD_HALF.get(pn, .46) - ph / 2) + 0.15 + (CTYD_HALF.get(name, .46) - h / 2)
            else:
                y = pn_bottom + pg
        centre = y + h / 2
        ax, ay, ar = P[name].at
        # local west edge of the pad that will be on the west side after the turn
        edges = []
        for poly in P[name].pads():
            xs = [a for a, _ in poly]
            edges.append(min(xs) - ax)
        flip = round((rot - ar) % 360) == 180
        west_off = min(-(max(a for a, _ in poly) - ax) for poly in P[name].pads()) if flip else min(edges)
        new[name] = (pad_w - west_off, centre, rot)
        pn_bottom = y + h
        prev = (name, h, g)
    # C318 (1.8 V bulk) on top of C315, its pad 2 (east) lined up with the column's east edge so
    # the JTAG lanes run straight past it; being wider, it reaches further west into the open
    # space above the fan
    ax, ay, _ = P["C318"].at
    east_off = max(max(a for a, _ in poly) for poly in P["C318"].pads()) - ax
    col_east = max(max(a for a, _ in moved("C315", poly, new)) for poly in P["C315"].pads())
    c315 = new["C315"][1]
    new["C318"] = (col_east - east_off, c315 - .46 - .15 - .73, 0)
    return new


def moved(ref, pts, new):
    if ref not in new:
        return pts
    ax, ay, ar = P[ref].at
    nx, ny, nr = new[ref]
    flip = round((nr - ar) % 360) == 180
    return [(nx - (a - ax), ny - (b - ay)) if flip else (nx + a - ax, ny + b - ay) for a, b in pts]


def pads(ref, new):
    out = []
    for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
        poly = moved(ref, poly, new)
        xs, ys = [a for a, _ in poly], [b for _, b in poly]
        out.append((str(pd[1]), (min(xs), min(ys), max(xs), max(ys)), net_of(pd)))
    return out


def box_of(ref, new):
    b = moved(ref, P[ref].courtyard(), new)
    xs, ys = [a for a, _ in b], [c for _, c in b]
    return min(xs), min(ys), max(xs), max(ys)


def pad_centre(ref, net, new):
    b = [bb for _, bb, n in pads(ref, new) if n == net][0]
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def layout(pad_w, top):
    new = build(pad_w, top)
    pb = {r: pads(r, new) for r in new}
    bot = lambda r: max(b[3] for _, b, _ in pb[r])
    tp = lambda r: min(b[1] for _, b, _ in pb[r])
    east = max(b[2] for _, b, _ in pb["C315"])               # column pad-2 east edge
    gap = lambda a, b: (bot(a) + tp(b)) / 2
    T = {"17": pad_centre("C315", "+1V8", new)[1], "18": gap("C315", "C303"),
         "19": pad_centre("C303", "+0V9", new)[1],
         "20": gap("C303", "C319") - .15, "21": gap("C303", "C319") + .15, "22": gap("C319", "FB301"),
         "23": gap("FB301", "C316") - .15, "24": gap("FB301", "C316") + .15}
    NAME = {"18": "/xvf3800/XVF_TDI", "20": "/xvf3800/XVF_TDO", "21": "/XVF_RST_N",
            "23": "/xvf3800/XVF_TMS", "24": "/xvf3800/XVF_TCK"}
    lane = {k: east + 0.35 + 0.3 * i for i, k in enumerate(["18", "20", "21", "23", "24"])}
    tracks = []               # (net, width, points)
    # XIN (pin 16): out, straight up the west edge of the fan to C320's XIN pad
    xX = 150.62
    c320 = pad_centre("C320", "/xvf3800/XVF_XIN", {})
    tracks.append(("/xvf3800/XVF_XIN", W, [(PIN_X, py("16")), (xX - .2, py("16")), (xX, py("16") - .2),
                                          (xX, c320[1] + (c320[0] - xX)), c320]))
    # climbers 17-22: 45-degree fan, diagonals staggered (x + y grows >= 0.43 per line)
    c = xX + py("16") + 0.43
    for k in ["17", "18", "19", "20", "21", "22"]:
        p, t = py(k), T[k]
        c = max(c, 150.66 + p)
        xs = c - p
        xe = xs + (p - t)
        pts = [(PIN_X, p), (xs, p), (xe, t)]
        net = pin[k][1]
        if k in NAME:
            pts += [(lane[k] - .2, t), (lane[k], t - .2), (lane[k], 88.6)]
        elif k == "22":
            pts += [(east - 0.3, t)]
        else:
            ref = {"17": "C315", "19": "C303"}[k]
            pts += [pad_centre(ref, net, new)]
        tracks.append((net, W, pts))
        c += 0.43
    # PLL stub joining the east pads of C319 and FB301
    a, b = pad_centre("C319", "PLL_AVDD", new), pad_centre("FB301", "PLL_AVDD", new)
    tracks.append(("PLL_AVDD", W, [a, b]))
    # TMS / TCK: small jog to their gap, then east to their lanes and north
    for k, xj in (("23", 150.75), ("24", 150.75)):
        p, t = py(k), T[k]
        d = t - p
        pts = [(PIN_X, p), (xj, p), (xj + abs(d), t), (lane[k] - .2, t), (lane[k], t - .2), (lane[k], 88.6)]
        tracks.append((pin[k][1], W, pts))
    # 26: east, a 45-degree jog into C316's +1V8 pad centre
    c316 = pad_centre("C316", "+1V8", new)
    d = py("26") - c316[1]
    tracks.append(("+1V8", W, [(PIN_X, py("26")), (c316[0] - abs(d), py("26")), c316]))
    # 27: east above C304, then 45 degrees down into its +0V9 pad centre
    c304 = pad_centre("C304", "+0V9", new)
    d = c304[1] - py("27")
    tracks.append(("+0V9", W, [(PIN_X, py("27")), (c304[0] - d, py("27")), c304]))
    # south: pin 30 and the pair in nested lanes, straight down, then east
    dm_y = bot("C323") + 0.2 + WU / 2
    dp_y = dm_y + 0.4
    c313 = pad_centre("C313", "+3V3", new)
    x30, xdp, xdm = 150.62, 150.62 + .35, 150.62 + .75
    tracks.append(("+3V3", W, [(PIN_X, py("30")), (x30 - .1, py("30")), (x30, py("30") + .1),
                               (x30, c313[1] - .3), (x30 + .3, c313[1]), c313]))
    # pair: east under the column to X1, 45 degrees up to the old rows, on to the existing vias
    V_DM, V_DP = (157.35, 100.48), (157.35, 101.28)
    rise = dm_y - 100.68
    X1 = 156.6 - 0.2 - rise - 0.4                          # D- back on its old row 0.4 before 156.6
    dm = [(PIN_X, py("28")), (xdm - .3, py("28")), (xdm, py("28") + .3), (xdm, dm_y - .3), (xdm + .3, dm_y),
          (X1, dm_y), (X1 + rise, 100.68), (156.6, 100.68), (156.8, 100.48), V_DM]
    # D+ is the outer line on both bends; the 0.166 offsets keep the pitch at 0.4 on the 45s
    dp = [(PIN_X, py("29")), (xdp - .3 + .166 * 0, py("29")), (xdp, py("29") + .3), (xdp, dp_y - .3),
          (xdp + .3, dp_y), (X1 + .166, dp_y), (X1 + .166 + rise, 101.08), (156.6, 101.08), (156.8, 101.28), V_DP]
    tracks.append(("/USB_MAIN_DM", WU, dm))
    tracks.append(("/USB_MAIN_DP", WU, dp))
    # FB301 +0V9 jumper (F.Cu): via in FB301's west pad -> west of C316's via -> via in C304's pad
    fb = pad_centre("FB301", "+0V9", new)
    jx = pad_w - 0.35
    jump = [fb, (jx, fb[1] + (fb[0] - jx)), (jx, c304[1] - (c304[0] - jx)), c304]
    return new, tracks, jump, lane, east, (dm_y, dp_y, X1)


def seg_d(a, b, c, d):
    """Distance between segments ab and cd (sampled; fine at these sizes)."""
    best = 9.0
    n = max(2, int(math.dist(a, b) / 0.02))
    for i in range(n + 1):
        t = i / n
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx, dy = d[0] - c[0], d[1] - c[1]
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((x - c[0]) * dx + (y - c[1]) * dy) / L2))
        best = min(best, math.hypot(x - c[0] - u * dx, y - c[1] - u * dy))
    return best


def seg_box(a, b, bx):
    best = 9.0
    n = max(2, int(math.dist(a, b) / 0.02))
    for i in range(n + 1):
        t = i / n
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        best = min(best, math.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3])))
    return best


NEAR = ["C318", "C315", "C303", "C319", "FB301", "C316", "C304", "C323", "C324", "C313", "C314",
        "C320", "Y301", "C325", "C326", "C209", "U203", "C317", "C305", "R301", "R302"]


def check(new, tracks):
    bad = []
    allp = [(r, pn, bx, n) for r in NEAR for pn, bx, n in pads(r, new)] + \
           [("U301", k, v[0], v[1]) for k, v in pin.items()]
    for net, w, pts in tracks:
        for a, b in zip(pts, pts[1:]):
            for r, pn, bx, n in allp:
                if n == net or bx[2] < min(a[0], b[0]) - 1 or bx[0] > max(a[0], b[0]) + 1 \
                        or bx[3] < min(a[1], b[1]) - 1 or bx[1] > max(a[1], b[1]) + 1:
                    continue
                bad.append((seg_box(a, b, bx) - w / 2, f"{net.split('/')[-1]} - {r}.{pn}"))
    for i, (n1, w1, p1) in enumerate(tracks):
        for n2, w2, p2 in tracks[i + 1:]:
            if n1 == n2:
                continue
            for a, b in zip(p1, p1[1:]):
                for c, d in zip(p2, p2[1:]):
                    if max(a[0], b[0]) < min(c[0], d[0]) - 1 or min(a[0], b[0]) > max(c[0], d[0]) + 1:
                        continue
                    bad.append((seg_d(a, b, c, d) - (w1 + w2) / 2, f"{n1.split('/')[-1]} - {n2.split('/')[-1]}"))
    bad.sort()
    return bad


def ctyd_clash(new):
    out = []
    refs = list(new) + ["C320", "Y301", "C325", "C326", "C317", "C305", "R301", "R302", "C209", "U203"]
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            A, B = box_of(a, new), box_of(b, new)
            g = max(B[0] - A[2], A[0] - B[2], B[1] - A[3], A[1] - B[3])
            if g < 0.149:
                out.append((round(g, 2), a, b))
    return out


# search: smallest column x (pad-1 west edge), and the column height position, that pass
best = None
for i in range(0, 40):
    pad_w = 151.60 + 0.05 * i
    for j in range(0, 31):
        top = 94.0 + 0.03 * j
        new, tracks, jump, lane, east, pair = layout(pad_w, top)
        worst = check(new, tracks)[0][0]
        if worst >= CLR - 1e-6 and not ctyd_clash(new):
            best = (pad_w, top)
            break
    if best:
        break
if not best:
    sys.exit("no layout passed")
pad_w, top = best
new, tracks, jump, lane, east, (dm_y, dp_y, X1) = layout(pad_w, top)
bad = check(new, tracks)
print(f"column pad-1 west edge {pad_w:.2f}: {pad_w - 150.46:.2f} mm from the pin ends (XMOS board: 1.39)")
print("closest copper gaps:")
for v, what in bad[:6]:
    print(f"  {v:.3f}  {what}")
print("courtyard clashes:", ctyd_clash(new) or "none")
print("pair rows: D- %.2f, D+ %.2f (was 100.68 / 101.08); JTAG lanes x %.2f-%.2f" % (dm_y, dp_y, min(lane.values()), max(lane.values())))
for ref, (x, y, r) in sorted(new.items(), key=lambda kv: kv[1][1]):
    ax, ay, ar = P[ref].at
    print(f"  {ref:6} ({x:.3f}, {y:.3f}) rot {r:>3}   moves {x - ax:+.2f} east, {y - ay:+.2f} south")
L = lambda pts: sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
dm = [t for t in tracks if t[0] == "/USB_MAIN_DM"][0][2]
dp = [t for t in tracks if t[0] == "/USB_MAIN_DP"][0][2]
print(f"pair B.Cu part: D- {L(dm):.2f} mm, D+ {L(dp):.2f} mm (was 7.33 each with the 0.2 spread); "
      f"skew {L(dp) - L(dm):+.2f}")
print("jumper:", [tuple(round(c, 2) for c in q) for q in jump])

# ---------------------------------------------------------------- drawing
X0, Y0, X1d, Y1d, S = 145.4, 87.8, 163.4, 107.6, 62
img = Image.new("RGB", (int((X1d - X0) * S), int((Y1d - Y0) * S) + 64), "white")
d = ImageDraw.Draw(img)
Tt = lambda x, y: ((x - X0) * S, (y - Y0) * S + 64)
F = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"+0V9": (200, 0, 120), "+1V8": (0, 120, 220), "GND": (130, 130, 130), "PLL_AVDD": (230, 120, 0),
       "+3V3": (0, 150, 0), "/USB_MAIN_DM": (255, 110, 0), "/USB_MAIN_DP": (235, 185, 0),
       "/xvf3800/XVF_XIN": (120, 0, 200)}
JT = {"/xvf3800/XVF_TDI": "TDI", "/xvf3800/XVF_TDO": "TDO", "/XVF_RST_N": "RST_N",
      "/xvf3800/XVF_TMS": "TMS", "/xvf3800/XVF_TCK": "TCK"}
HINT = {"C318": "1V8 bulk", "C315": "pin 17", "C303": "pin 19", "C319": "PLL cap", "FB301": "PLL ferrite",
        "C316": "pin 26", "C304": "pin 27", "C323": "USB stitch", "C324": "USB stitch", "C313": "pin 30",
        "C314": "3V3 bulk", "C320": "xtal cap", "Y301": "crystal", "C325": "USB stitch", "C326": "USB stitch",
        "C209": "LDO out", "U203": "1V8 LDO", "C317": "pin 31", "C305": "", "R301": "", "R302": ""}
for r in HINT:
    mv = r in new
    if mv:
        b = P[r].courtyard(); xs_, ys_ = [a for a, _ in b], [c for _, c in b]
        d.rectangle([Tt(min(xs_), min(ys_)), Tt(max(xs_), max(ys_))], outline=(205, 205, 205))
    for pn, bx, net in pads(r, new):
        d.rectangle([Tt(bx[0], bx[1]), Tt(bx[2], bx[3])], fill=COL.get(net, (180, 180, 180)))
    cb = box_of(r, new)
    d.rectangle([Tt(*cb[:2]), Tt(*cb[2:])], outline=(0, 0, 0) if mv else (170, 170, 170))
    if HINT[r]:
        d.text(Tt(cb[2] + 0.05, (cb[1] + cb[3]) / 2), f"{r} ({HINT[r]})", font=F(12, mv), fill="black", anchor="lm")
for k, (bx, net) in pin.items():
    if 14 <= int(k) <= 31 and bx[0] > 149.5:
        d.rectangle([Tt(bx[0], bx[1]), Tt(bx[2], bx[3])], fill=COL.get(net, (0, 150, 60) if net in JT else (180, 180, 180)))
        lab = JT.get(net, {"/xvf3800/XVF_XIN": "XIN", "PLL_AVDD": "PLL", "/USB_MAIN_DM": "D-",
                           "/USB_MAIN_DP": "D+"}.get(net, net if not net.startswith("unconn") else "NC"))
        d.text(Tt(bx[0] - 0.08, (bx[1] + bx[3]) / 2), f"{k} {lab}", font=F(11), fill="black", anchor="rm")
for i in range(len(jump) - 1):
    (ax_, ay_), (bx_, by_) = jump[i], jump[i + 1]
    for k in range(0, 12, 2):
        d.line([Tt(ax_ + (bx_ - ax_) * k / 12, ay_ + (by_ - ay_) * k / 12),
                Tt(ax_ + (bx_ - ax_) * (k + 1) / 12, ay_ + (by_ - ay_) * (k + 1) / 12)], fill=(200, 0, 120), width=4)
for v in (jump[0], jump[-1], (157.35, 100.48), (157.35, 101.28)):
    d.ellipse([Tt(v[0] - .225, v[1] - .225), Tt(v[0] + .225, v[1] + .225)], outline="black", width=2)
for net, w, pts in tracks:
    c = (0, 160, 60) if net in JT else COL.get(net, (100, 100, 100))
    d.line([Tt(*q) for q in pts], fill=c, width=max(2, int(w * S)), joint="curve")
    if net in JT:
        d.text(Tt(pts[-1][0], pts[-1][1]), JT[net], font=F(11, True), fill=(0, 120, 40), anchor="mb")
d.text((10, 6), f"Centred column, USB pair moved south (B.Cu sketch). Caps {pad_w - 150.46:.2f} mm from the pin ends "
       "(XMOS: 1.4). Bold outline = moved, grey = now.", font=F(14, True), fill="black")
d.text((10, 26), "JTAG green, USB orange/yellow, power in net colours, XIN purple. Gaps: TDI 0.45, TDO+RST 0.75, "
       "pin 22 0.45, TMS+TCK 0.75 mm.", font=F(14), fill="black")
d.text((10, 44), "Dashed magenta = F.Cu jumper, +0V9 to FB301. Circles = vias (the two on the right are the existing "
       "USB layer-change vias, unchanged).", font=F(13), fill=(150, 0, 90))
img.save(OUT)
print("wrote", OUT)
