"""Mic routes: XVF3800 MIC_DATA0-3 and the buffered mic clock to the four mics (approved 2026-11-20).

tools/power_v2_2026_11_18.py rebuilds every track on the board, so it imports this file and lays
the mic routes first (with the main USB pair, before any power copper) as fixed geometry the power
router then avoids. The geometry itself is frozen in mic_route_2026_11_20.json next to this file.

  python3 tools/mic_route_2026_11_20.py              print lengths / vias / reference planes
  python3 tools/mic_route_2026_11_20.py --generate   rebuild the JSON from the current board
                                                     (after tools/mic_place_2026_11_20.py; power
                                                     tracks are ignored, power_v2 re-routes them)

Plan (verification/mic-routing-proposal-2026-11-20/):
  * Each mic gets DATA + clock as a pair, 0.15 mm wide, >= 0.45 mm apart, in the same corridor:
    NE (MK501) north past the flash then east above the module; NW (MK502) west then north;
    SW (MK503) south-west; SE (MK504) south then east. Long runs on B.Cu over In2, one
    0.45/0.2 via up to F.Cu just inside the LED ring (+5V_LED, B.Cu), F.Cu over In1 GND to the
    mic's series resistor.
  * Fan-out (hand-drawn here): pins N->S are DATA3 (SE), DATA1 (NW), DATA2 (SW), DATA0 (NE).
    DATA1 and DATA3 leave west at the pin pitch through the C312/C307 gap; DATA2, (SPI_MISO)
    and DATA0 bend 0.4/0.4/0.6 mm south to pass under C307. DATA3 and DATA0 swap ends with one
    short F.Cu hop each under the module's west end (2 vias each): DATA3 at x 138.2 down,
    DATA0 at x 138.9 up. Between DATA2 and DATA0 there is a 1.0 mm lane for SPI_MISO (pin 47,
    test pad TP403), with room for its via at about (141.4, 101.58); not routed here.
  * Clock: MIC_CLK leaves pin 43 south to a via, then F.Cu under the module to U501's input
    (top side, west of the module). R501 pad 2 is the clock star, on F.Cu over In1 GND, with
    one via down to B.Cu at the start of each corridor.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "mic_route_2026_11_20.json")
W, VIA = 0.15, (0.45, 0.2)

D0, D1, D2, D3 = "/MIC_DATA0", "/MIC_DATA1", "/MIC_DATA2", "/MIC_DATA3"
MCLK, CLKA, CLK = "/MIC_CLK", "Net-(R501-Pad1)", "Net-(R501-Pad2)"

# ------------------------------------------------------------------ hand-drawn fan-out
# U301 (XVF3800, bottom side) west pins, pin 43 on the south edge
P51, P50, P48, P46 = (143.058, 99.479), (143.058, 99.879), (143.058, 100.679), (143.058, 101.479)
P43 = (144.558, 102.179)
V3A, V3B = (138.2, 99.25), (138.2, 102.35)          # DATA3 hop (F.Cu, x 138.2, down)
V0A, V0B = (138.9, 102.079), (138.9, 96.4)          # DATA0 hop (F.Cu, x 138.9, up)
VM = (144.558, 103.45)                              # MIC_CLK down to F.Cu, just south of pin 43
U501_2, U501_4, R501_1, R501_2 = (134.6, 104.737), (135.55, 102.462), (135.55, 100.86), (135.55, 99.84)
# clock vias from the F.Cu star down to B.Cu, one per corridor
CV = {"NE": (136.0, 96.0), "NW": (134.3, 97.7), "SW": (136.4, 102.6), "SE": (137.6, 104.3)}

FAN_TRACKS = [  # net, layer, points
    (D3, "B.Cu", [P51, (139.25, 99.479), (139.021, 99.25), V3A]),
    (D3, "F.Cu", [V3A, V3B]),
    (D3, "B.Cu", [V3B, (137.0, 103.55)]),
    # South of the fan-out four lines turn south-west together as parallel 45 degree runs, 0.45 mm
    # pitch (x + y = 242.5 / 243.14 / 243.78 / 244.42 for SW DATA2 / SW clock / SE DATA3 / SE
    # clock): the SE pair has to get west of L202's 2.5 mm keep-away and past C601's vias
    # (GND via at 135.838, 109.609), and the SW clock turns only after the SE pair is clear of it.
    # SW pair, whole B.Cu run, straight down its 45 degree lines to the ring vias (clock via a
    # little further in, so the two vias sit 0.7 mm apart)
    (D2, "B.Cu", [(137.0, 101.079), (134.3, 103.779), (134.3, 108.2), (128.9, 113.6)]),
    (CLK, "B.Cu", [(136.4, 102.6), (136.4, 106.74), (129.6, 113.54)]),
    # SE pair, whole B.Cu run (off the router's 0.1 mm grid, which cannot hold 0.45 mm pitch and
    # 0.3 mm clearance to C601's via at once): south at x 134.7 / 135.15 past C601's GND via, a
    # 0.35 mm jog east (clock first, so the pitch holds through it) to pass between ring parts
    # C809/D809 and the stitching cap C515, then east along y 123.2 / 122.6 (2.5 mm clear of
    # L201/U201/U202) to the ring vias
    (D3, "B.Cu", [(137.0, 103.55), (137.0, 106.78), (134.7, 109.08), (134.7, 114.99), (135.05, 115.34),
                  (135.05, 121.37), (136.88, 123.2), (156.6, 123.2)]),
    (CLK, "B.Cu", [(137.6, 104.3), (137.6, 106.82), (135.15, 109.27), (135.15, 114.8), (135.5, 115.15),
                   (135.5, 121.18), (136.92, 122.6), (155.8, 122.6)]),
    (D1, "B.Cu", [P50, (137.6, 99.879), (134.6, 96.879)]),
    (D2, "B.Cu", [P48, (142.11, 100.679), (141.71, 101.079), (137.0, 101.079)]),
    (D0, "B.Cu", [P46, (142.45, 101.479), (141.85, 102.079), V0A]),
    (D0, "F.Cu", [V0A, V0B]),
    (D0, "B.Cu", [V0B, (137.3, 96.4)]),
    (MCLK, "B.Cu", [P43, VM]),
    (MCLK, "F.Cu", [VM, (142.258, 105.75), (134.6, 105.75), U501_2]),
    (CLKA, "F.Cu", [U501_4, R501_1]),
    # clock star on F.Cu (over In1 GND): R501 pad 2 to the four clock vias
    (CLK, "F.Cu", [R501_2, (135.55, 98.95)]),
    (CLK, "F.Cu", [(135.55, 98.95), (135.55, 96.45), CV["NE"]]),
    (CLK, "F.Cu", [(135.55, 98.95), CV["NW"]]),
    (CLK, "F.Cu", [R501_2, (136.0, 99.84)]),
    (CLK, "F.Cu", [(136.0, 99.84), (136.4, 100.24), CV["SW"]]),
    (CLK, "F.Cu", [(136.0, 99.84), (136.9, 99.84), (137.6, 100.54), CV["SE"]]),
]
FAN_VIAS = [(V3A, D3), (V3B, D3), (V0A, D0), (V0B, D0), (VM, MCLK)] + [(p, CLK) for p in CV.values()]

# corridors (router): name, net, start, B.Cu waypoints (last = ring via), resistor pad,
# optional F.Cu waypoints after the ring via
CORRIDORS = [
    # NE: DATA0 north at x 137.3, between C507's GND via (136.69, 83.86) and the module's GND via
    # (138.15, 89.93); the clock north at x 136.0, west of C507's via (as in the approved drawing)
    ("DATA0 > NE", D0, (137.3, 96.4), [(137.3, 82.6), (162.6, 80.6)], ("R506", "2")),
    ("CLK > NE", CLK, CV["NE"], [(136.0, 81.9), (161.8, 79.8)], ("R502", "2")),
    ("DATA1 > NW", D1, (134.6, 96.879), [(128.4, 83.0)], ("R507", "2")),
    ("CLK > NW", CLK, CV["NW"], [(127.6, 83.8)], ("R503", "2")),
    ("DATA2 > SW", D2, (128.9, 113.6), [], ("R508", "2")),
    ("CLK > SW", CLK, (129.6, 113.54), [], ("R504", "2")),
    # SE: the clock (inner, north) goes first, so its F.Cu leg keeps the northern lane to R505
    ("CLK > SE", CLK, (155.8, 122.6), [], ("R505", "2"), [(157.0, 121.4)]),
    ("DATA3 > SE", D3, (156.6, 123.2), [], ("R509", "2")),
]
# noise sources the mic copper keeps >= 2.5 mm from (courtyard to track edge): the buck
# inductors, the speaker amp and the speaker connector
KEEP_AWAY, KEEP_DIST = ("L201", "L202", "U503", "J501"), 2.5
# router clearance for the mic copper: 0.3 mm keeps every pair at >= 0.45 mm pitch (0.15 mm lines)
CLR = 0.3


def _load():
    if not os.path.exists(DATA):
        return [], []
    d = json.load(open(DATA))
    return ([(t["net"], t["layer"], [tuple(p) for p in t["pts"]]) for t in d["tracks"]],
            [(tuple(v["at"]), v["net"]) for v in d["vias"]])


TRACKS, VIAS = _load()


# ------------------------------------------------------------------ generator
def generate():
    sys.path.insert(0, HERE)
    from place_tidy import BOARD, LEFT, RIGHT, TOP, BOTTOM, Part  # noqa: E402
    from sexpr import parse, children, child  # noqa: E402
    from jog_router import Router, Shape  # noqa: E402
    import jog_router  # noqa: E402

    POWER = {"GND", "+3V3", "+5V", "+0V9", "+1V8", "VBUS_MAIN", "VBUS_ESP", "+5V_AMP"}
    MOVED = ("C312", "C307", "C309", "U501", "R501", "C501")
    PLANED = POWER - {"+5V_AMP"}
    r = parse(open(BOARD).read())
    old = parse(open(os.path.join(HERE, "..", "..", "mindspark_rev1-backups", "pre-mic-route-2026-11-20",
                                  "mindspark_rev1.kicad_pcb")).read())
    netof = lambda n: str(child(n, "net")[1]) if child(n, "net") else ""  # noqa: E731

    def centre(poly):
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

    # vias that stood in the old pads of the moved parts go away with power_v2's rerun
    stale = []
    for f in children(old, "footprint"):
        p = Part(f)
        if p.ref in MOVED:
            stale += [centre(poly) for poly in p.pads()]
    shapes, pads = [], {}
    for f in children(r, "footprint"):
        p = Part(f)
        for pd, poly in zip(children(p.node, "pad"), p.pads()):
            lays = [str(x) for x in (child(pd, "layers") or [])[1:]]
            if not any(x.endswith(".Cu") for x in lays):
                continue
            kind = str(pd[2])
            layers = {"F.Cu", "B.Cu"} if kind in ("thru_hole", "np_thru_hole") else {p.side}
            n = netof(pd) if kind != "np_thru_hole" else "~hole"
            shapes.append(Shape(n or f"~{p.ref}", layers, poly=poly))
            pads[(p.ref, str(pd[1]))] = poly
            # moved / new parts: the via power_v2 will drop in each planed pad
            if p.ref in MOVED + ("C515",) and n in PLANED:
                shapes.append(Shape(n, {"F.Cu", "B.Cu"}, circle=(centre(poly), 0.3)))
    for s in children(r, "segment"):
        n = netof(s)
        if n in POWER:
            continue                                     # power_v2 re-routes round the mics
        a, b = child(s, "start"), child(s, "end")
        shapes.append(Shape(n, {str(child(s, "layer")[1])},
                            seg=((float(a[1]), float(a[2])), (float(b[1]), float(b[2])), float(child(s, "width")[1]))))
    for a in children(r, "arc"):                         # LED ring (B.Cu)
        pts = [(float(child(a, k)[1]), float(child(a, k)[2])) for k in ("start", "mid", "end")]
        for s_, e_ in zip(pts, pts[1:]):
            shapes.append(Shape(netof(a), {str(child(a, "layer")[1])}, seg=(s_, e_, float(child(a, "width")[1]) + 0.3)))
    for v in children(r, "via"):
        x, y = float(child(v, "at")[1]), float(child(v, "at")[2])
        if any(math.dist((x, y), s_) < 0.6 for s_ in stale):
            continue
        shapes.append(Shape(netof(v), {"F.Cu", "B.Cu"}, circle=((x, y), float(child(v, "size")[1]) / 2)))
    for z in children(r, "zone"):
        lay = str(child(z, "layer")[1]) if child(z, "layer") else ""
        if lay in ("F.Cu", "B.Cu"):
            for fp in children(z, "filled_polygon"):
                poly = [(float(q[1]), float(q[2])) for q in child(fp, "pts")[1:] if q[0] == "xy"]
                shapes.append(Shape(netof(z), {lay}, poly=poly))
    # keep-away boxes: the router keeps CLEARANCE + half the width from an obstacle, so the box
    # grows by the rest of KEEP_DIST
    grow = KEEP_DIST - CLR
    for f in children(r, "footprint"):
        p = Part(f)
        if p.ref in KEEP_AWAY:
            xs, ys = [q[0] for q in p.courtyard()], [q[1] for q in p.courtyard()]
            x0, y0, x1, y1 = min(xs) - grow, min(ys) - grow, max(xs) + grow, max(ys) + grow
            shapes.append(Shape(f"~keep {p.ref}", {"F.Cu", "B.Cu"}, poly=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
    router = Router((LEFT, TOP, RIGHT, BOTTOM), shapes)
    jog_router.CLEARANCE = CLR
    jog_router.SPACING = 0.0       # CLR already doubles the 0.15 rule; no drifting off-line for room

    tracks, vias = [], []

    def lay(net, layer, pts):
        tracks.append({"net": net, "layer": layer, "pts": [[round(x, 4), round(y, 4)] for x, y in pts]})
        for a, b in zip(pts, pts[1:]):
            router.add(Shape(net, {layer}, seg=(a, b, W)))

    def drop(pt, net):
        vias.append({"at": [round(pt[0], 4), round(pt[1], 4)], "net": net})
        router.add(Shape(net, {"F.Cu", "B.Cu"}, circle=(pt, VIA[0] / 2)))

    for net, layer, pts in FAN_TRACKS:
        others = [sh for sh in router.shapes if sh.net != net and layer in sh.layers]
        for a_, b_ in zip(pts, pts[1:]):
            c_ = router._seg_clearance(a_, b_, others, W)
            if c_ < 0.15 - 1e-6:
                sys.exit(f"hand track {net} {layer} {a_}-{b_}: only {c_:.3f} mm clear")
            if c_ < CLR - 1e-6:
                print(f"  note: hand track {net} {layer} {a_}-{b_}: {c_:.3f} mm clear (< {CLR})")
        lay(net, layer, pts)
    for pt, net in FAN_VIAS:
        drop(pt, net)

    def sq(pt, h=0.05):
        return [(pt[0] - h, pt[1] - h), (pt[0] + h, pt[1] - h), (pt[0] + h, pt[1] + h), (pt[0] - h, pt[1] + h)]

    def leg(net, layer, cur, goal_poly, label):
        path = router.route(net, layer, W, goal_poly, [], extra_starts=[cur])
        if path is None:
            sys.exit(f"FAILED {label}: {layer} from {cur}")
        if math.dist(path[-1], cur) < math.dist(path[0], cur):
            path = path[::-1]
        if math.dist(path[0], cur) > 1e-6:
            path = [cur] + path
        lay(net, layer, path)
        return path[-1]

    # corridors. A ring via at the end of a routed B.Cu leg sits on the 0.1 mm grid of the F.Cu
    # leg's goal pad (the router aligns its grid on the goal), so the F.Cu leg starts cleanly.
    for name, net, start, wps, goal, *fwps in CORRIDORS:
        cur = start
        for k, wp in enumerate(wps):
            if k == len(wps) - 1 and not fwps:
                xs, ys = [q[0] for q in pads[goal]], [q[1] for q in pads[goal]]
                gx, gy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                wp = (gx - round((gx - wp[0]) / 0.1) * 0.1, gy - round((gy - wp[1]) / 0.1) * 0.1)
            cur = leg(net, "B.Cu", cur, sq(wp), name)
        drop(cur, net)
        for wp in (fwps[0] if fwps else []):
            cur = leg(net, "F.Cu", cur, sq(wp), name)
        leg(net, "F.Cu", cur, pads[goal], name)
        print(f"routed {name}")
    # no right angles (user 2026-11-20): every 90 degree bend becomes two 45 degree turns, with
    # the mic clearance CLR kept (so pairs keep their 0.45 mm pitch); pad centres and vias stay
    from jog_router import chamfer_corners, _inside  # noqa: E402
    segs = [[t["net"], t["layer"], tuple(a), tuple(b), W] for t in tracks for a, b in zip(t["pts"], t["pts"][1:])]
    via_pts = {(round(v["at"][0], 4), round(v["at"][1], 4)) for v in vias}

    def fixed(net, layer, pt):
        return (round(pt[0], 4), round(pt[1], 4)) in via_pts or any(_inside(pt[0], pt[1], poly) for poly in pads.values())
    n, left = chamfer_corners(router, segs, fixed, CLR)
    print(f"chamfered {n} right-angle bends; left: {sorted(set(map(str, left))) or 'none'}")
    tracks = [{"net": s_[0], "layer": s_[1], "pts": [list(s_[2]), list(s_[3])]} for s_ in segs]
    json.dump({"tracks": tracks, "vias": vias}, open(DATA, "w"), indent=0)
    print("wrote", DATA)


# ------------------------------------------------------------------ report
ZONES = [  # In2 planes (copy of power_v2's), net, priority, polygon
    ("+5V", 1, [(152.3, 109.8), (170.7, 109.8), (170.7, 112.9), (173.3, 112.9), (173.3, 114.9), (170.7, 114.9),
                (170.7, 114.75), (164.3, 114.75), (164.3, 130.2), (130.5, 130.2), (130.5, 115.5), (134.3, 115.5),
                (134.3, 119.8), (146.2, 119.8), (146.2, 122.0), (158.9, 122.0), (158.9, 113.4), (152.3, 113.4)]),
    ("VBUS_MAIN", 2, [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 115.25),
                      (173.3, 115.25), (173.3, 112.6), (172.8, 112.6), (172.8, 103.5), (170.8, 103.5)]),
    ("VBUS_ESP", 3, [(114.6, 94.8), (122.3, 94.8), (122.3, 103.5), (118.9, 103.5), (118.9, 130.5),
                     (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)]),
    ("+0V9", 4, [(142.3, 94.4), (150.9, 94.4), (150.9, 103.0), (148.8, 103.0), (148.8, 113.7),
                 (158.8, 113.7), (158.8, 121.7), (147.0, 121.7), (147.0, 103.0), (142.3, 103.0)]),
    ("+1V8", 5, [(151.4, 93.9), (160.0, 93.9), (160.0, 106.3), (148.9, 106.3), (148.9, 103.3), (151.4, 103.3)]),
]


def _inside(x, y, poly):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def plane(pt):
    best = ("+3V3", 0)
    for n, pri, poly in ZONES:
        if _inside(pt[0], pt[1], poly) and pri > best[1]:
            best = (n, pri)
    return best[0]


def report():
    by_net = {}
    for net, layer, pts in TRACKS:
        L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        d = by_net.setdefault(net, {"F.Cu": 0.0, "B.Cu": 0.0, "planes": []})
        d[layer] += L
        if layer == "B.Cu":
            for a, b in zip(pts, pts[1:]):
                n = max(1, int(math.dist(a, b) / 0.2))
                for k in range(n + 1):
                    pn = plane((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
                    if pn not in d["planes"]:
                        d["planes"].append(pn)
    nv = {}
    for _, net in VIAS:
        nv[net] = nv.get(net, 0) + 1
    for net, d in by_net.items():
        print(f"{net:18s} B.Cu {d['B.Cu']:6.1f}  F.Cu {d['F.Cu']:5.1f}  total {d['B.Cu'] + d['F.Cu']:6.1f} mm, "
              f"{nv.get(net, 0)} vias; B.Cu over In2 {' / '.join(d['planes'])}")


if __name__ == "__main__":
    if "--generate" in sys.argv:
        generate()
        TRACKS, VIAS = _load()
    report()
