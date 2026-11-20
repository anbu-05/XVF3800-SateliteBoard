"""Mic routing PROPOSAL (scratch, read-only on the board).

Lays the four mic DATA + CLK pairs with tools/jog_router.py on an in-memory copy of the board and
reports what they clash with. Power *tracks* are left out of the obstacles on purpose: the
proposal is that the mics (now priority 1) are laid first, like the USB pair, and power_v2 then
routes power around them. Pads, vias, holes, zone pours, the LED ring and the USB pair stay as
obstacles. Run from PCB/mindspark_rev1."""
import json
import math
import sys

sys.path.insert(0, "tools")
from place_tidy import LEFT, RIGHT, TOP, BOTTOM, Part  # noqa: E402
from sexpr import parse, children, child  # noqa: E402
from jog_router import Router, Shape  # noqa: E402

BOARD = "mindspark_rev1.kicad_pcb"
W = 0.15                     # mic track width (Default class)
VIA = 0.45                   # small via 0.45/0.2
POWER = {"GND", "+3V3", "+5V", "+0V9", "+1V8", "VBUS_MAIN", "VBUS_ESP", "+5V_AMP"}

r = parse(open(BOARD).read())
net = lambda n: str(child(n, "net")[1]) if child(n, "net") else ""  # noqa: E731

shapes, power_tracks, pads = [], [], {}
for f in children(r, "footprint"):
    p = Part(f)
    for pd, poly in zip(children(p.node, "pad"), p.pads()):
        lays = [str(x) for x in (child(pd, "layers") or [])[1:]]
        if not any(x.endswith(".Cu") for x in lays):
            continue
        kind = str(pd[2])
        layers = {"F.Cu", "B.Cu"} if kind in ("thru_hole", "np_thru_hole") else {p.side}
        n = net(pd) if kind != "np_thru_hole" else "~hole"
        if p.ref == "C309":
            continue                            # proposal: C309 (bulk) moves out of the fan-out
        shapes.append(Shape(n or f"~{p.ref}", layers, poly=poly))
        pads.setdefault((p.ref, str(pd[1])), (poly, n))
for s in children(r, "segment"):
    lay, n = str(child(s, "layer")[1]), net(s)
    a, b = child(s, "start"), child(s, "end")
    seg = ((float(a[1]), float(a[2])), (float(b[1]), float(b[2])), float(child(s, "width")[1]))
    if n in POWER and n != "+5V_LED":
        power_tracks.append((n, lay, seg))      # movable: power_v2 re-routes round the mics
    else:
        shapes.append(Shape(n, {lay}, seg=seg))
for a in children(r, "arc"):                     # LED ring (B.Cu) stays
    pts = [(float(child(a, k)[1]), float(child(a, k)[2])) for k in ("start", "mid", "end")]
    for s, e in zip(pts, pts[1:]):
        shapes.append(Shape(net(a), {str(child(a, "layer")[1])}, seg=(s, e, float(child(a, "width")[1]))))
for v in children(r, "via"):
    x, y = float(child(v, "at")[1]), float(child(v, "at")[2])
    if abs(x - 136.783) < 0.01 and abs(y - 100.279) < 0.01:
        continue                                # C309's via, moves with it
    shapes.append(Shape(net(v), {"F.Cu", "B.Cu"}, circle=((x, y), float(child(v, "size")[1]) / 2)))
for z in children(r, "zone"):
    lay = str(child(z, "layer")[1]) if child(z, "layer") else ""
    if lay in ("F.Cu", "B.Cu"):
        for fp in children(z, "filled_polygon"):
            poly = [(float(q[1]), float(q[2])) for q in child(fp, "pts")[1:] if q[0] == "xy"]
            shapes.append(Shape(net(z), {lay}, poly=poly))

router = Router((LEFT, TOP, RIGHT, BOTTOM), shapes)


def centre(ref, pin):
    poly = pads[(ref, pin)][0]
    xs, ys = [q[0] for q in poly], [q[1] for q in poly]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def sq(pt, h=0.05):
    return [(pt[0] - h, pt[1] - h), (pt[0] + h, pt[1] - h), (pt[0] + h, pt[1] + h), (pt[0] - h, pt[1] + h)]


# ------------------------------------------------------------------ the proposal
# Fan points just west of the module (x < 137.7), one per line, ordered so the pairs leave
# without crossing: NE pair north, NW pair west, SW pair south-west, SE pair south.
# How the pins reach them (order swap, clock star) is the escape-pass sketch.
STAR = (139.6, 103.4)        # clock star on F.Cu under the module's west end (sketch)
CLK = "Net-(R501-Pad2)"
FAN = {"D0": (137.2, 96.2), "C0": (136.7, 96.2), "D1": (136.3, 97.6), "C1": (136.3, 98.1),
       "D2": (136.3, 100.0), "C2": (136.3, 100.5), "D3": (137.0, 101.6), "C3": (137.5, 101.6)}
ROUTES = [
    ("DATA0 > NE", "/MIC_DATA0", FAN["D0"],
     [("B.Cu", (137.2, 82.6)), ("B.Cu", (162.6, 80.6)), ("F.Cu", None)], ("R506", "2")),
    ("CLK > NE", CLK, FAN["C0"],
     [("B.Cu", (136.2, 81.9)), ("B.Cu", (161.8, 79.8)), ("F.Cu", None)], ("R502", "2")),
    ("DATA1 > NW", "/MIC_DATA1", FAN["D1"],
     [("B.Cu", (128.6, 96.0)), ("B.Cu", (128.4, 83.0)), ("F.Cu", None)], ("R507", "2")),
    ("CLK > NW", CLK, FAN["C1"],
     [("B.Cu", (127.8, 96.6)), ("B.Cu", (127.6, 83.8)), ("F.Cu", None)], ("R503", "2")),
    ("DATA2 > SW", "/MIC_DATA2", FAN["D2"],
     [("B.Cu", (128.9, 113.6)), ("F.Cu", None)], ("R508", "2")),
    ("CLK > SW", CLK, FAN["C2"],
     [("B.Cu", (128.1, 114.4)), ("F.Cu", None)], ("R504", "2")),
    ("DATA3 > SE", "/MIC_DATA3", FAN["D3"],
     [("B.Cu", (137.0, 122.4)), ("B.Cu", (156.6, 122.4)), ("F.Cu", None)], ("R509", "2")),
    ("CLK > SE", CLK, FAN["C3"],
     [("B.Cu", (137.5, 121.8)), ("B.Cu", (155.8, 121.8)), ("F.Cu", None)], ("R505", "2")),
]

out = []
for name, n, start, legs, goal in ROUTES:
    cur = centre(*start) if isinstance(start, tuple) and isinstance(start[0], str) else start
    pts_all, vias, ok = [], [], True
    layer = legs[0][0]
    for i, (lay, wp) in enumerate(legs):
        if lay != layer:                       # layer change: via at the current point
            vias.append(cur)
            router.add(Shape(n, {"F.Cu", "B.Cu"}, circle=(cur, VIA / 2)))
            layer = lay
        tgt = wp if wp is not None else centre(*goal)
        if wp is None and goal is None:
            break
        gpoly = sq(tgt) if wp is not None else pads[goal][0]
        path = router.route(n, layer, W, gpoly, [], extra_starts=[cur])
        if path is None:
            print(f"FAILED {name}: {layer} {cur} -> {tgt}")
            path, ok = [cur, tgt], False
        if path[0] != cur and math.dist(path[-1], cur) < math.dist(path[0], cur):
            path = path[::-1]
        pts_all.append((layer, path, ok))
        for a, b in zip(path, path[1:]):
            router.add(Shape(n, {layer}, seg=(a, b, W)))
        cur = path[-1]
    out.append({"name": name, "net": n, "legs": pts_all, "vias": vias})

# ------------------------------------------------------------------ clashes with power tracks
def seg_dist(a, b, c, d):
    def pd(p, s, e):
        dx, dy = e[0] - s[0], e[1] - s[1]
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / L))
        return math.hypot(p[0] - s[0] - t * dx, p[1] - s[1] - t * dy)
    best = min(pd(a, c, d), pd(b, c, d), pd(c, a, b), pd(d, a, b))
    # proper crossing
    def ccw(p, q, s):
        return (s[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (s[0] - p[0])
    if (ccw(a, b, c) > 0) != (ccw(a, b, d) > 0) and (ccw(c, d, a) > 0) != (ccw(c, d, b) > 0):
        best = 0
    return best

clashes = []
for rt in out:
    for layer, path, _ in rt["legs"]:
        for a, b in zip(path, path[1:]):
            for pn, pl, (c, d, w) in power_tracks:
                if pl == layer and seg_dist(a, b, c, d) < W / 2 + w / 2 + 0.15:
                    clashes.append((rt["name"], pn, pl, c, d))
    for v in rt["vias"]:
        for pn, pl, (c, d, w) in power_tracks:
            if seg_dist(v, v, c, d) < VIA / 2 + w / 2 + 0.15:
                clashes.append((rt["name"] + " via", pn, pl, c, d))
seen = set()
for c in clashes:
    k = (c[0], c[1], c[3], c[4])
    if k not in seen:
        seen.add(k)
        print("CLASH", c[0], "with", c[1], c[2], "segment", tuple(round(x, 1) for x in c[3] + c[4]))
ZONES = [("+5V", 1, [(152.3, 109.8), (170.7, 109.8), (170.7, 112.9), (173.3, 112.9), (173.3, 114.9),
                     (170.7, 114.9), (170.7, 114.75), (164.3, 114.75), (164.3, 130.2), (130.5, 130.2),
                     (130.5, 115.5), (134.3, 115.5), (134.3, 119.8), (146.2, 119.8), (146.2, 122.0),
                     (158.9, 122.0), (158.9, 113.4), (152.3, 113.4)]),
         ("VBUS_MAIN", 2, [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 115.25),
                           (173.3, 115.25), (173.3, 112.6), (172.8, 112.6), (172.8, 103.5), (170.8, 103.5)]),
         ("VBUS_ESP", 3, [(114.6, 94.8), (122.3, 94.8), (122.3, 103.5), (118.9, 103.5), (118.9, 130.5),
                          (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)]),
         ("+0V9", 4, [(142.3, 94.4), (150.9, 94.4), (150.9, 103.0), (148.8, 103.0), (148.8, 113.7),
                      (158.8, 113.7), (158.8, 121.7), (147.0, 121.7), (147.0, 103.0), (142.3, 103.0)]),
         ("+1V8", 5, [(151.4, 93.9), (160.0, 93.9), (160.0, 106.3), (148.9, 106.3), (148.9, 103.3), (151.4, 103.3)])]
from jog_router import _inside  # noqa: E402


def plane(pt):
    best = ("+3V3", 0)
    for n, pri, poly in ZONES:
        if _inside(pt[0], pt[1], poly) and pri > best[1]:
            best = (n, pri)
    return best[0]


for rt in out:
    seq = []
    for layer, path, _ in rt["legs"]:
        if layer != "B.Cu":
            continue
        for a, b in zip(path, path[1:]):
            n = max(1, int(math.dist(a, b) / 0.2))
            for k in range(n + 1):
                pn = plane((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
                if not seq or seq[-1] != pn:
                    seq.append(pn)
    print(f"{rt['name']:12s} B.Cu reference planes (In2): {' > '.join(seq)}")
for rt in out:
    L = sum(math.dist(a, b) for _, p, _ in rt["legs"] for a, b in zip(p, p[1:]))
    LB = sum(math.dist(a, b) for lay, p, _ in rt["legs"] if lay == "B.Cu" for a, b in zip(p, p[1:]))
    print(f"{rt['name']:12s} length {L:5.1f} mm (B.Cu {LB:4.1f}), vias {len(rt['vias'])}")
json.dump({"routes": out, "clashes": sorted(seen), "star": STAR, "fan": FAN}, open(sys.argv[1], "w"), default=list)
