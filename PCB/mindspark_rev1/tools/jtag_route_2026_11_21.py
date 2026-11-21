"""JTAG: from the five B.Cu lanes north of the ESP32 module to J301, plus RST_N to R703 (2026-11-21).

The lanes come from tools/east_escape_2026_11_21.py: B.Cu, 0.3 mm pitch, ending at y 88.6 just
north of the module, west to east TDI, TDO, RST_N, TMS, TCK. J301 (XTAG4 JST, F.Cu, our own
pinout, no standard to follow) was reordered to match (user 2026-11-21,
tools/sch_j301_reorder_2026_11_21.py): west to east TDI (pin 6), TDO (5), RST_N (4), TMS (3),
TCK (2), at 2.0 mm pitch, so nothing crosses.

Geometry (0/45/90 degrees, ends on pad / via centres):
  * The lanes fan east on B.Cu to 0.6 mm pitch (room for vias between them): TDI stays at 154.07,
    TDO 154.69 (in line with J301 pin 4), RST_N 155.29, TMS 155.89, TCK 156.69 (in line with
    pin 3). Each 45-degree jog starts a little further north than the one east of it, so the
    parallel diagonals keep 0.15 mm.
  * One via each: TDI, TDO, TMS and TCK in a row at y 86.6; RST_N's a row further south (y 87.3)
    so its branch to R703 can leave east on F.Cu under the others' vias. On F.Cu each line fans
    straight out at 45 degrees (west for TDI / TDO / RST_N, east for TMS / TCK) and runs north
    over In1 GND to its J301 pad, crossing over the NE mic pair (B.Cu, y 81.9 / 82.6).
  * RST_N's branch: F.Cu east from its via, over the TMS / TCK lanes, down to R703 pad 2 (the
    ESP32's reset link), east of the module.
Not done here: RST_N to R303 / U302 (pull-up and supervisor, far west) and the JTAG parallel test
pads TP302-TP306 on the bottom edge: both are long runs for the signal pass.

Laid by tools/power_v2_2026_11_18.py before any power copper (like the other fixed routes).
Run on its own it checks the clearances against the board and prints lengths:
  python3 tools/jtag_route_2026_11_21.py
"""
import math

W, VIA = 0.15, (0.45, 0.2)
TDI, TDO, RST, TMS, TCK = ("/xvf3800/XVF_TDI", "/xvf3800/XVF_TDO", "/XVF_RST_N",
                           "/xvf3800/XVF_TMS", "/xvf3800/XVF_TCK")
Y_LANE = 88.6                                       # where the east_escape lanes stop
LANE = {TDI: 154.07, TDO: 154.37, RST: 154.67, TMS: 154.97, TCK: 155.27}
SPREAD = {TDI: 154.07, TDO: 154.69, RST: 155.29, TMS: 155.89, TCK: 156.69}
J301 = {TDI: (150.69, 70.2), TDO: (152.69, 70.2), RST: (154.69, 70.2), TMS: (156.69, 70.2), TCK: (158.69, 70.2)}
R703_2 = (158.23, 91.95)
VIA_Y = {RST: 87.3, TMS: 86.6, TDI: 86.6, TDO: 86.6, TCK: 86.6}

# B.Cu: fan out to SPREAD, eastern lines first: a NE diagonal keeps x + y constant, so each line's
# diagonal must sit 0.15 + 0.15 track (0.3 * sqrt 2 in x + y) west of its eastern neighbour's
TRACKS, VIAS = [], []
c_prev = None
for net in (TCK, TMS, RST, TDO, TDI):
    x0, x1 = LANE[net], SPREAD[net]
    if x1 == x0:
        pts = [(x0, Y_LANE), (x0, VIA_Y[net])]
    else:
        ys = Y_LANE if c_prev is None else min(Y_LANE, c_prev - 0.3 * math.sqrt(2) - x0)
        c_prev = x0 + ys
        pts = [(x0, Y_LANE), (x0, ys), (x1, ys - (x1 - x0)), (x1, VIA_Y[net])]
        pts = [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-6]
    TRACKS.append((net, "B.Cu", [(round(x, 4), round(y, 4)) for x, y in pts]))
    VIAS.append(((SPREAD[net], VIA_Y[net]), net))

# F.Cu: each via fans out at 45 degrees to its J301 pad column, then straight north. RST_N first
# runs north between the TDO and TMS vias, then jogs west once past them.
v = {net: (SPREAD[net], VIA_Y[net]) for net in SPREAD}


def fan(net, start):
    (x0, y0), (x1, y1) = start, J301[net]
    dx = abs(x1 - x0)
    pts = [start, (x1, y0 - dx), (x1, y1)] if dx > 1e-6 else [start, (x1, y1)]
    return (net, "F.Cu", pts)


rst_up = (v[RST][0], v[TDO][1] - 0.4)                    # past the via row
# TDO runs 0.4 north before its fan, so its diagonal clears TDI's via
_, _, tpts = fan(TDO, (v[TDO][0], v[TDO][1] - 0.4))
TRACKS += [fan(TDI, v[TDI]), (TDO, "F.Cu", [v[TDO]] + tpts), fan(TMS, v[TMS]), fan(TCK, v[TCK])]
_, _, rpts = fan(RST, rst_up)
TRACKS.append((RST, "F.Cu", [v[RST]] + rpts))
TRACKS.append((RST, "F.Cu", [v[RST], (R703_2[0] - 0.5, v[RST][1]), (R703_2[0], v[RST][1] + 0.5), R703_2]))


def check():
    """Copper gaps against every pad on the board, the other fixed routes and each other."""
    import json
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from place_tidy import BOARD, Part
    from sexpr import parse, children
    import east_escape_2026_11_21 as east
    import usb_main_route_2026_11_19 as usb
    root = parse(open(BOARD).read())
    pads = []
    for f in children(root, "footprint"):
        p = Part(f)
        for pd, poly in zip(children(f, "pad"), p.pads()):
            net = [c for c in pd if isinstance(c, list) and c and c[0] == "net"]
            net = str(net[0][-1]).strip('"') if net else ""
            th = any(isinstance(c, str) and c in ("thru_hole", "np_thru_hole") for c in pd)
            xs, ys = [a for a, _ in poly], [b for _, b in poly]
            pads.append((p.ref, str(pd[1]), net, {"F.Cu", "B.Cu"} if th else {p.side},
                         (min(xs), min(ys), max(xs), max(ys))))
    mic = json.load(open(os.path.join(here, "mic_route_2026_11_20.json")))
    others = [(t["net"], t["layer"], 0.15, [tuple(p) for p in t["pts"]]) for t in mic["tracks"]]
    others += [(n, l, w, p) for n, l, w, p in east.TRACKS if n not in SPREAD]
    others += [(n, l, usb.W, p) for n, l, p in usb.TRACKS]
    ovias = [(tuple(x["at"]), x["net"]) for x in mic["vias"]] + list(east.VIAS) + list(usb.VIAS)

    def d_seg_pt(a, b, p):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    def d_seg_seg(a, b, c, d):
        n = max(2, int(math.dist(a, b) / 0.02))
        return min(d_seg_pt(c, d, (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)) for i in range(n + 1))

    def d_seg_box(a, b, bx):
        n = max(2, int(math.dist(a, b) / 0.02))
        best = 9.0
        for i in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
            best = min(best, math.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3])))
        return best

    near = lambda a, b, bx: not (bx[2] < min(a[0], b[0]) - 1 or bx[0] > max(a[0], b[0]) + 1
                                 or bx[3] < min(a[1], b[1]) - 1 or bx[1] > max(a[1], b[1]) + 1)
    bad = []
    mine = [(n, l, W, p) for n, l, p in TRACKS]
    for net, lay, w, pts in mine:
        for a, b in zip(pts, pts[1:]):
            for ref, pn, n2, lays, bx in pads:
                if n2 != net and lay in lays and near(a, b, bx):
                    bad.append((d_seg_box(a, b, bx) - w / 2, f"{net.split('/')[-1]} {lay} - {ref}.{pn}"))
            for n2, l2, w2, p2 in mine + others:
                if n2 == net or l2 != lay:
                    continue
                for c, d in zip(p2, p2[1:]):
                    if near(a, b, (min(c[0], d[0]), min(c[1], d[1]), max(c[0], d[0]), max(c[1], d[1]))):
                        bad.append((d_seg_seg(a, b, c, d) - (w + w2) / 2, f"{net.split('/')[-1]} {lay} - {n2.split('/')[-1]}"))
            for vp, n2 in VIAS + ovias:
                if n2 != net and near(a, b, (vp[0], vp[1], vp[0], vp[1])):
                    bad.append((d_seg_pt(a, b, vp) - w / 2 - VIA[0] / 2, f"{net.split('/')[-1]} {lay} - via {n2.split('/')[-1]}"))
    for vp, net in VIAS:
        for ref, pn, n2, lays, bx in pads:
            if n2 != net and near(vp, vp, bx):
                bad.append((d_seg_box(vp, vp, bx) - VIA[0] / 2, f"via {net.split('/')[-1]} - {ref}.{pn}"))
        for n2, l2, w2, p2 in others:
            if n2 != net:
                for c, d in zip(p2, p2[1:]):
                    if near(vp, vp, (min(c[0], d[0]), min(c[1], d[1]), max(c[0], d[0]), max(c[1], d[1]))):
                        bad.append((d_seg_pt(c, d, vp) - w2 / 2 - VIA[0] / 2, f"via {net.split('/')[-1]} - {n2.split('/')[-1]} {l2}"))
        for vq, n2 in VIAS + ovias:
            if n2 != net and vq != vp:
                bad.append((math.dist(vp, vq) - VIA[0], f"via {net.split('/')[-1]} - via {n2.split('/')[-1]}"))
    bad.sort()
    return bad


if __name__ == "__main__":
    for v_, net in VIAS:
        print(f"via {net.split('/')[-1]:6} at {v_}")
    for net in SPREAD:
        L = sum(math.dist(a, b) for n, l, p in TRACKS if n == net for a, b in zip(p, p[1:]))
        print(f"{net.split('/')[-1]:6} {L:5.1f} mm from the lane end (y 88.6) to J301" +
              (" incl. the R703 branch" if net == RST else ""))
    bad = check()
    print("closest copper gaps:")
    for g, what in bad[:8]:
        print(f"  {g:.3f}  {what}")
