"""Centred east cap column (column_centred.py) plus the crystal and the QSPI boot flash, 2026-11-20.
Dry run: nothing is written to the board. Writes column_full.png beside this script.

Crystal (24 MHz, Y301) moves east and turns so its XIN pad sits at the top of the XIN lane:
  * XIN (pin 16) runs up its lane straight into Y301 pad 1; C320 (XIN load) and R302 (1 M bias,
    XIN-XOUT) sit between the crystal and the chip, on that lane.
  * XOUT (pin 15) runs up the crystal's west side, through R302's other pad, round the top to
    R301 (680 R drive limit) and on to Y301 pad 3 with C321 (load).
  * The old crystal spot above pins 6-14 is left free for the other north-row signals (escape pass).
  * C318 (1.8 V bulk) leaves the top of the column for a spot by the LDO, east of the JTAG strip.
QSPI (XVF3800 <-> U401, W25Q32 USON-8), flash and its parts where they are:
  * The flash's pad order needs one crossing: D3 hops on F.Cu under the module (two vias).
  * CLK hops too (user's sketch, 2026-11-21): a via just north of pin 5, F.Cu straight west under
    the flash (south of D3's F.Cu run), a via west of pad 6, B.Cu east into pad 6. The via sits
    0.05 east of pin 5 (0.15 to pin 4's +0V9 feed); pin 6's line (SPI_CS_N, escape pass) takes a
    0.1 mm 45-degree jog east right out of its pad to keep 0.15 from it (stub drawn).
  * CS_N, D1, D2 come in from the east; D0 runs under the flash into pad 5 from below.
  * C301 (pin 4 +0V9) moves into the pocket between the CS_N and CLK runs; C310 (pin 8) and
    C302 (pin 12) move east one step each so CLK can run straight north from pin 5.
Not drawn: the flash lines' branches to the path-B switches U701-U704 (east side, F.Cu), and
the other north-row signals (pins 6, 7, 9-11, 13, 14).
Run from PCB/mindspark_rev1:  python3 verification/jtag-proposal-2026-11-20/column_full.py
"""
import json
import math
import sys

src = open("verification/jtag-proposal-2026-11-20/column_centred.py").read().split("# search: smallest column x")[0]
G = {"__name__": "column_centred"}
exec(compile(src, "column_centred.py", "exec"), G)
P, pin, pads, layout, check_c, seg_d, seg_box = (G[k] for k in ("P", "pin", "pads", "layout", "check", "seg_d", "seg_box"))
net_of = G["net_of"]
from sexpr import children  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = "verification/jtag-proposal-2026-11-20/column_full.png"
W = 0.15
PAD_W, TOP = 152.20, 94.42                 # column found by column_centred.py
new, tracks, jump, lane, east, pair = layout(PAD_W, TOP)
tracks = [t for t in tracks if t[0] != "/xvf3800/XVF_XIN"]       # XIN redrawn below


# ---------------------------------------------------------------- extra parts, any quarter turn
def turn_pts(ref, pts, x, y, q):
    ax, ay, _ = P[ref].at
    out = []
    for a, b in pts:
        dx, dy = a - ax, b - ay
        for _ in range(q):
            dx, dy = dy, -dx
        out.append((x + dx, y + dy))
    return out


EXTRA = {}                                 # ref: (x, y, quarter turns)


def xpads(ref):
    if ref in EXTRA:
        x, y, q = EXTRA[ref]
        out = []
        for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
            poly = turn_pts(ref, poly, x, y, q)
            xs, ys = [a for a, _ in poly], [b for _, b in poly]
            out.append((str(pd[1]), (min(xs), min(ys), max(xs), max(ys)), net_of(pd)))
        return out
    return pads(ref, new)


def xbox(ref):
    if ref in EXTRA:
        x, y, q = EXTRA[ref]
        b = turn_pts(ref, P[ref].courtyard(), x, y, q)
    else:
        b = G["moved"](ref, P[ref].courtyard(), new)
    xs, ys = [a for a, _ in b], [c for _, c in b]
    return min(xs), min(ys), max(xs), max(ys)


def centre(ref, padnum):
    b = [bb for pn, bb, _ in xpads(ref) if pn == padnum][0]
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def place(ref, x, y, want):
    """Put ref at (x, y) with the first quarter turn for which want(pad centres) holds."""
    for q in range(4):
        EXTRA[ref] = (x, y, q)
        if want({pn: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for pn, b, _ in xpads(ref)}):
            return
    sys.exit(f"no turn fits {ref}")


XL = 150.62                                # XIN lane (from column_centred)
# crystal: pad 1 (XIN) south-west, centred on the XIN lane; GND pads get vias in pad
place("Y301", XL + 0.85, 89.90, lambda c: c["1"][0] < c["3"][0] and c["1"][1] > c["3"][1] and abs(c["1"][0] - XL) < .01)
place("C320", 151.48, 92.62, lambda c: c["1"][0] < c["2"][0] and abs(c["1"][1] - c["2"][1]) < .01)     # XIN west
place("R302", 150.21, 93.72, lambda c: c["2"][0] < c["1"][0] and abs(c["1"][1] - c["2"][1]) < .01)     # XOUT west
y3 = centre("Y301", "3")
place("R301", y3[0] - 1.55, 86.95, lambda c: c["2"][0] < c["1"][0] and abs(c["1"][1] - c["2"][1]) < .01)  # XOUT west
place("C321", y3[0] + 0.45, 86.95, lambda c: c["1"][0] < c["2"][0] and abs(c["1"][1] - c["2"][1]) < .01)  # node west
place("C318", 159.60, 93.40, lambda c: c["1"][0] < c["2"][0])                                         # +1V8 west
# north cap row: C301 into the CS_N / CLK pocket (horizontal, +0V9 east), C310 / C302 one step east
place("C301", 143.87, 91.75, lambda c: c["1"][0] > c["2"][0] and abs(c["1"][1] - c["2"][1]) < .01)
place("C310", 146.56, 92.22, lambda c: c["1"][1] > c["2"][1] and abs(c["1"][0] - c["2"][0]) < .01)
place("C302", 148.16, 92.22, lambda c: c["1"][1] > c["2"][1] and abs(c["1"][0] - c["2"][0]) < .01)
new.pop("C318", None)

py = lambda n: (pin[n][0][1] + pin[n][0][3]) / 2
px = lambda n: (pin[n][0][0] + pin[n][0][2]) / 2
TOPY = 94.88                               # north-row tracks start 0.1 inside the pad's outer end
FT, VIAS = [], []
dn = lambda c: c                          # vias in pad centres                          # F.Cu tracks, vias (net, centre)

# ---------------------------------------------------------------- crystal
p1, p3 = centre("Y301", "1"), centre("Y301", "3")
c320, r302x, r302i = centre("C320", "1"), centre("R302", "2"), centre("R302", "1")
r301o, r301n, c321n = centre("R301", "2"), centre("R301", "1"), centre("C321", "1")
XO = 149.70                                # XOUT lane up the crystal's west side
tracks += [
    ("/xvf3800/XVF_XIN", W, [(G["PIN_X"], py("16")), (XL - .2, py("16")), (XL, py("16") - .2), (XL, p1[1])]),
    ("/xvf3800/XVF_XIN", W, [(XL, c320[1]), c320]),
    ("/xvf3800/XVF_XIN", W, [(XL, r302i[1]), r302i]),
    ("/xvf3800/XVF_XOUT", W, [(px("15"), TOPY), (px("15"), 94.6), (XO, 94.6 - (XO - px("15"))), (XO, r301o[1] + .3),
                              (XO + .3, r301o[1]), r301o]),
    ("Net-(C321-Pad1)", W, [r301n, c321n]),
    ("Net-(C321-Pad1)", W, [c321n, (p3[0], c321n[1] + abs(p3[0] - c321n[0])), p3]),
]
# GND vias in the crystal's GND pads; the south-east one sits 0.25 below the pad centre so it
# clears the module's north-edge pad 29 (F.Cu) above
for pn in ("2", "4"):
    cx, cy = centre("Y301", pn)
    VIAS.append(("GND", (cx, cy + (0.25 if cy > 90 else 0.0))))
VIAS += [("GND", centre("C320", "2")), ("GND", centre("C321", "2"))]

# ---------------------------------------------------------------- QSPI
U = {pn: c for pn, c in ((pn, ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)) for pn, b, _ in xpads("U401"))}
CSY, CLKY, D2X, CLKX = 92.86, 90.35, 142.62, 137.60
VIA_D3A, VIA_D3B = (144.06, 93.31), (138.05, U["7"][1])
VIA_CKA, VIA_CKB = (145.41, 94.33), (138.05, U["6"][1])   # A: just north of pin 5, 0.05 east
CKF_Y, CKF_X = 90.95, 137.55        # CLK F.Cu: west below the module's north pads, down west of D3's via
tracks += [
    # CS_N: north, west into pad 1; branch up to R401's pad 1 (pull-up)
    ("/XVF_QSPI_CS_N", W, [(px("3"), TOPY), (px("3"), CSY), (142.6, CSY), (142.5, U["1"][1]), U["1"]]),
    ("/XVF_QSPI_CS_N", W, [(centre("R401", "1")[0], CSY), centre("R401", "1")]),
    # D1: north, west into pad 2
    ("/XVF_QSPI_D1", W, [(px("1"), TOPY), (px("1"), U["2"][1]), U["2"]]),
    # D2: from pin 60 west, up the channel east of the flash, west into pad 3
    ("/XVF_QSPI_D2", W, [(143.06, py("60")), (D2X + .2, py("60")), (D2X, py("60") - .2), (D2X, U["3"][1] + .2),
                         (D2X - .2, U["3"][1]), U["3"]]),
    # D3: north to a via, F.Cu west under the module, via, B.Cu into pad 7 from the west
    ("/XVF_QSPI_D3", W, [(px("2"), TOPY), (px("2"), 94.0), (VIA_D3A[0], 93.9), VIA_D3A]),
    ("/XVF_QSPI_D3", W, [VIA_D3B, U["7"]]),
    # CLK: north from pin 5 to a via; F.Cu below (FT); via west of the flash, east into pad 6
    ("/XVF_QSPI_CLK", W, [(px("5"), TOPY), (px("5"), 94.71), (VIA_CKA[0], 94.66), VIA_CKA]),
    # pin 6 (SPI_CS_N, routed in the escape pass): 0.1 jog east out of its pad, clear of the CLK via
    ("/XVF_SPI_CS_N", W, [(px("6"), TOPY), (px("6"), 94.70), (px("6") + .11, 94.59), (px("6") + .11, 93.5)]),
    ("/XVF_QSPI_CLK", W, [VIA_CKB, U["6"]]),
    # D0: pin 59 west under the flash, up into pad 5 from below
    ("/XVF_QSPI_D0", W, [(143.06, py("59")), (142.76, py("59")), (142.69, 96.35), (U["5"][0] + .7, 96.35),
                         (U["5"][0], 95.65), U["5"]]),
    # power: pin 4 into C301 (pocket), flash VCC up to C401, flash GND down to a via
    ("+0V9", W, [(px("4"), TOPY), (px("4"), centre("C301", "1")[1]), centre("C301", "1")]),
    ("+3V3", W, [U["8"], (U["8"][0], 92.3), (centre("C401", "1")[0], 91.75), centre("C401", "1")]),
    ("+3V3", W, [(px("8"), TOPY), centre("C310", "1")]),
    ("+0V9", W, [(px("12"), TOPY), centre("C302", "1")]),
    ("GND", W, [U["4"], (U["4"][0], 95.85)]),
]
FT.append(("/XVF_QSPI_D3", W, [VIA_D3A, (VIA_D3A[0] - .45, U["7"][1]), VIA_D3B]))
FT.append(("/XVF_QSPI_CLK", W, [VIA_CKA, (VIA_CKA[0] - (VIA_CKB[1] - VIA_CKA[1]), VIA_CKB[1]), VIA_CKB]))
VIAS += [("/XVF_QSPI_D3", VIA_D3A), ("/XVF_QSPI_D3", VIA_D3B), ("GND", (U["4"][0], 95.85)),
         ("/XVF_QSPI_CLK", VIA_CKA), ("/XVF_QSPI_CLK", VIA_CKB),
         ("+3V3", dn(centre("C401", "1"))), ("+3V3", dn(centre("R401", "2"))), ("GND", dn(centre("C401", "2"))),
         ("GND", centre("C301", "2")), ("+3V3", centre("C310", "1")), ("GND", centre("C310", "2")),
         ("GND", centre("C302", "2"))]
# FB301 jumper from column_centred (F.Cu) and its vias
FT.append(("+0V9", W, jump))
VIAS += [("+0V9", jump[0]), ("+0V9", jump[-1])]

# ---------------------------------------------------------------- checks
mic = json.load(open("tools/mic_route_2026_11_20.json"))
MIC_B = [(t["net"], 0.15, [tuple(p) for p in t["pts"]]) for t in mic["tracks"] if t["layer"] == "B.Cu"]
MIC_F = [(t["net"], 0.15, [tuple(p) for p in t["pts"]]) for t in mic["tracks"] if t["layer"] == "F.Cu"]
MIC_V = [(v["net"], tuple(v["at"])) for v in mic["vias"]]
REFS = G["NEAR"] + ["U401", "R401", "C401", "C308", "C301", "C310", "C302", "C318"]
REFS = [r for r in dict.fromkeys(REFS)]
BPADS = [(r, pn, bx, n) for r in REFS for pn, bx, n in xpads(r)] + [("U301", k, v[0], v[1]) for k, v in pin.items()]
FPADS = [("U601", str(pd[1]), (min(a for a, _ in pl), min(b for _, b in pl), max(a for a, _ in pl), max(b for _, b in pl)),
          net_of(pd)) for pd, pl in zip(children(P["U601"].node, "pad"), P["U601"].pads())]
VR = 0.225
bad = []


def near(a, b, bx, m=1.2):
    return not (bx[2] < min(a[0], b[0]) - m or bx[0] > max(a[0], b[0]) + m or bx[3] < min(a[1], b[1]) - m or bx[1] > max(a[1], b[1]) + m)


def track_checks(trs, pads_, others):
    for net, w, pts in trs:
        for a, b in zip(pts, pts[1:]):
            for r, pn, bx, n in pads_:
                if n != net and near(a, b, bx):
                    bad.append((seg_box(a, b, bx) - w / 2, f"{net.split('/')[-1]} - {r}.{pn}"))
            for n2, w2, p2 in others:
                if n2 == net:
                    continue
                for c, d in zip(p2, p2[1:]):
                    if near(a, b, (min(c[0], d[0]), min(c[1], d[1]), max(c[0], d[0]), max(c[1], d[1]))):
                        bad.append((seg_d(a, b, c, d) - (w + w2) / 2, f"{net.split('/')[-1]} - {n2.split('/')[-1]}"))
            for n2, v in VIAS + MIC_V:
                if n2 != net and near(a, b, (v[0], v[1], v[0], v[1])):
                    bad.append((seg_d(a, b, v, v) - w / 2 - VR, f"{net.split('/')[-1]} - via {n2.split('/')[-1]}"))


track_checks(tracks, BPADS, tracks + MIC_B)
track_checks(FT, FPADS, FT + MIC_F)
for i, (n1, v1) in enumerate(VIAS):
    for r, pn, bx, n in BPADS + FPADS:
        if n != n1 and near(v1, v1, bx):
            bad.append((seg_box(v1, v1, bx) - VR, f"via {n1.split('/')[-1]} at ({v1[0]:.2f}, {v1[1]:.2f}) - {r}.{pn}"))
    for n2, v2 in VIAS[i + 1:] + MIC_V:
        if n2 != n1:
            bad.append((math.dist(v1, v2) - 2 * VR, f"via {n1.split('/')[-1]} - via {n2.split('/')[-1]}"))
bad.sort()
print("closest copper gaps (all B.Cu and F.Cu lines, vias through both):")
for v, what in bad[:10]:
    print(f"  {v:.3f}  {what}")
clash = []
refs = list(new) + list(EXTRA) + ["U401", "R401", "C401", "C308", "C325", "C326", "C209", "U203", "C317", "C305"]
refs = [r for r in dict.fromkeys(refs)]
for i, a in enumerate(refs):
    for b in refs[i + 1:]:
        A, B = xbox(a), xbox(b)
        g = max(B[0] - A[2], A[0] - B[2], B[1] - A[3], A[1] - B[3])
        if g < 0.149:
            clash.append((round(g, 2), a, b))
print("courtyard clashes:", clash or "none")
for ref, (x, y, q) in EXTRA.items():
    ax, ay, ar = P[ref].at
    print(f"  {ref:5} to ({x:.2f}, {y:.2f}), turned {90 * q:>3} deg   (moves {x - ax:+.2f} east, {y - ay:+.2f} south)")
L = lambda pts: sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
for net in ("/XVF_QSPI_CLK", "/XVF_QSPI_CS_N", "/XVF_QSPI_D0", "/XVF_QSPI_D1", "/XVF_QSPI_D2", "/XVF_QSPI_D3"):
    n = sum(L(p) for nn, _, p in tracks + FT if nn == net and not (net.endswith("CS_N") and p[-1] == centre("R401", "1")))
    print(f"  {net.split('/')[-1]:12} {n:5.1f} mm")
print(f"  XIN {L([(150.16, py('16')), (XL, py('16')), (XL, p1[1])]):.1f} mm to Y301 pad 1;  "
      f"XOUT {L(tracks[[t[0] for t in tracks].index('/xvf3800/XVF_XOUT')][2]):.1f} mm to R301")

# ---------------------------------------------------------------- drawing
X0, Y0, X1, Y1, S = 133.6, 85.4, 162.4, 107.0, 46
img = Image.new("RGB", (int((X1 - X0) * S), int((Y1 - Y0) * S) + 70), "white")
d = ImageDraw.Draw(img)
T = lambda x, y: ((x - X0) * S, (y - Y0) * S + 70)
F = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"+0V9": (200, 0, 120), "+1V8": (0, 120, 220), "GND": (130, 130, 130), "PLL_AVDD": (230, 120, 0),
       "+3V3": (0, 150, 0), "/USB_MAIN_DM": (255, 110, 0), "/USB_MAIN_DP": (235, 185, 0),
       "/xvf3800/XVF_XIN": (120, 0, 200)}
COL.update({"/XVF_QSPI_CLK": (220, 0, 0), "/XVF_QSPI_CS_N": (150, 60, 0), "/XVF_QSPI_D0": (0, 170, 170),
            "/XVF_QSPI_D1": (0, 90, 160), "/XVF_QSPI_D2": (90, 0, 160), "/XVF_QSPI_D3": (200, 0, 200),
            "/xvf3800/XVF_XOUT": (160, 90, 220), "Net-(C321-Pad1)": (190, 140, 240)})
JT = {"/xvf3800/XVF_TDI": "TDI", "/xvf3800/XVF_TDO": "TDO", "/XVF_RST_N": "RST_N",
      "/xvf3800/XVF_TMS": "TMS", "/xvf3800/XVF_TCK": "TCK"}
HINT = {"C315": "pin 17", "C303": "pin 19", "C319": "PLL cap", "FB301": "PLL ferrite",
        "C316": "pin 26", "C304": "pin 27", "C323": "USB stitch", "C324": "USB stitch", "C313": "pin 30",
        "C314": "3V3 bulk", "C320": "xtal cap", "Y301": "crystal", "C325": "USB stitch", "C326": "USB stitch",
        "C209": "LDO out", "U203": "1V8 LDO", "C317": "pin 31", "C305": ""}
HINT.update({"U401": "QSPI flash", "R401": "CS pull-up", "C401": "flash bypass", "C308": "pin 57",
             "C301": "pin 4", "C310": "pin 8", "C302": "pin 12", "R301": "680R", "R302": "1M",
             "C321": "xtal cap", "C318": "1V8 bulk"})
# mic routes (context), faint
for net, w, pts in MIC_B:
    d.line([T(*q) for q in pts], fill=(200, 220, 200), width=max(2, int(w * S)))
for net, w, pts in MIC_F:
    d.line([T(*q) for q in pts], fill=(220, 200, 200), width=2)
for r in HINT:
    mv = r in new or r in EXTRA
    if mv:
        b = P[r].courtyard(); xs_, ys_ = [a for a, _ in b], [c for _, c in b]
        d.rectangle([T(min(xs_), min(ys_)), T(max(xs_), max(ys_))], outline=(210, 210, 210))
    for pn, bx, net in xpads(r):
        d.rectangle([T(bx[0], bx[1]), T(bx[2], bx[3])], fill=COL.get(net, (185, 185, 185)))
    cb = xbox(r)
    d.rectangle([T(*cb[:2]), T(*cb[2:])], outline=(0, 0, 0) if mv else (170, 170, 170))
    if HINT[r]:
        d.text(T(cb[2] + 0.05, (cb[1] + cb[3]) / 2), f"{r} ({HINT[r]})", font=F(10, mv), fill="black", anchor="lm")
for k, (bx, net) in pin.items():
    d.rectangle([T(bx[0], bx[1]), T(bx[2], bx[3])], fill=COL.get(net, (0, 150, 60) if net in JT else (185, 185, 185)))
d.text(T(146.6, 98.6), "XVF3800", font=F(14, True), fill=(120, 120, 120), anchor="mm")
for net, w, pts in FT:
    for a, b in zip(pts, pts[1:]):
        for k in range(0, 12, 2):
            d.line([T(a[0] + (b[0] - a[0]) * k / 12, a[1] + (b[1] - a[1]) * k / 12),
                    T(a[0] + (b[0] - a[0]) * (k + 1) / 12, a[1] + (b[1] - a[1]) * (k + 1) / 12)],
                   fill=COL.get(net, (100, 100, 100)), width=3)
for net, w, pts in tracks:
    c = (0, 160, 60) if net in JT else COL.get(net, (100, 100, 100))
    d.line([T(*q) for q in pts], fill=c, width=max(2, int(w * S)), joint="curve")
for net, v in VIAS + [("x", (157.35, 100.48)), ("x", (157.35, 101.28))]:
    d.ellipse([T(v[0] - VR, v[1] - VR), T(v[0] + VR, v[1] + VR)], outline="black", width=2)
LEG = [("CLK (dashed = F.Cu)", "/XVF_QSPI_CLK"), ("CS_N", "/XVF_QSPI_CS_N"), ("D0", "/XVF_QSPI_D0"), ("D1", "/XVF_QSPI_D1"),
       ("D2", "/XVF_QSPI_D2"), ("D3", "/XVF_QSPI_D3"), ("XIN", "/xvf3800/XVF_XIN"),
       ("XOUT", "/xvf3800/XVF_XOUT")]
x = 10
for lab, net in LEG:
    d.rectangle([x, 50, x + 18, 62], fill=COL[net])
    d.text((x + 22, 56), lab, font=F(12), fill="black", anchor="lm")
    x += 40 + 8 * len(lab)
d.text((10, 6), "East column + crystal + QSPI flash (sketch). Bold outline = moved, grey = now; faint green/red = mic routes "
       "(fixed).", font=F(14, True), fill="black")
d.text((10, 26), "JTAG green, USB orange/yellow, power in net colours. Dashed = F.Cu. Circles = vias. Not drawn: flash "
       "branches to U701-U704, other north-row signals.", font=F(13), fill="black")
img.save(OUT)
print("wrote", OUT)
