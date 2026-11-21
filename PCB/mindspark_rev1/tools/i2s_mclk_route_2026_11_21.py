"""I2S XVF3800 -> U503 amp, the MCLK loop (pin 14 <-> 41), and the north-row tidy (agreed 2026-11-21).

Plan and sketches: verification/i2s-plan-2026-11-21/ (north_row_closeup_B.png, mclk_closeup_F.png,
i2s_mclk_overview_B.png). The user's own MCLK trial (pin 14 -> via -> F.Cu under the chip -> via ->
pin 41) was the starting point; only its north via moved.

North row of the XVF3800 (B.Cu, pins 8-15 west to east, 0.4 mm pitch):
  * C310 (pin 8, +3V3) and C302 (pin 12, +0V9) move 0.15 mm west (--place). That lets DATA0 (pin 9)
    and BCLK (pin 13) leave dead straight, and LRCK (pin 10) with a 0.1 mm jog, all three with no via.
    The pin 8 / pin 12 stubs to those caps live in east_escape_2026_11_21.json (tracks 29 / 30);
    --place rewrites them there too. Pin 12's stub jogs 0.05 mm east to make room for the mute via.
  * BTN_MUTE_N (pin 11, not sensitive, user 2026-11-21): a short stub to a via just north of the pin,
    between LRCK and pin 12's stub. Its F.Cu run to SW401 is left for the slow-control pass.
  * MCLK: pin 14 north to a via 0.37 mm clear of XVF_XOUT (the user's trial sat at 0.15 mm), then
    F.Cu under the chip down the east side of the ESP32's ground pad, west along its south side to a
    via under pin 41, B.Cu up into pin 41. TP412 is not connected yet (test-pad pass).

I2S to U503 (0.15 mm tracks, 0.3 mm gaps, 3 vias per line; B.Cu legs over In2 +3V3, F.Cu over In1 GND):
  1. B.Cu: straight north past C310 / C302, then a 45-degree run north-west to just south of the NE
     mic pair (B.Cu, y 81.9 / 82.6), in three parallel lanes.
  2. V1 -> F.Cu straight north across the mic pair at 90 degrees -> V2 (east of U502, the amp switch).
  3. B.Cu north-west then west along U502's north side, south of the amp's GND vias by C509.
  4. V3 south-west of U503; F.Cu stubs: BCLK east into pin 16, LRCK north round to pin 14, DATA0
     up between pin 16 and R511 into pin 1.
  The amp's own copper (U502, +5V_AMP, GND vias) is routed by power_v2 after these, round them.
  Test pads TP409-TP411 are not connected yet (test-pad pass).

Usage (PCB editor closed):
  python3 tools/i2s_mclk_route_2026_11_21.py --place   move C310 / C302 and rewrite their stubs (once)
  python3 tools/i2s_mclk_route_2026_11_21.py           lengths and clearance check against the board
Imported by tools/power_v2_2026_11_18.py for TRACKS / VIAS (laid before any power copper).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
W, VIA = 0.15, (0.45, 0.2)
DATA0, LRCK, BCLK, MCLK, MUTE = "/I2S_DATA0", "/I2S_LRCK", "/I2S_BCLK", "/MCLK_LOOP", "/BTN_MUTE_N"
CAP_SHIFT = -0.15                                    # C310 and C302, in x
EAST_JSON = os.path.join(HERE, "east_escape_2026_11_21.json")

# Geometry, all 0/45/90 degrees, ends on pad / via centres. XVF3800 north row pins at y 95.179.
TRACKS = [
    # ---- DATA0: pin 9 -> U503 pin 1
    (DATA0, "B.Cu", [(146.958, 95.179), (146.958, 91.052), (140.206, 84.3), (140.206, 83.6)]),
    (DATA0, "F.Cu", [(140.206, 83.6), (140.206, 81.0)]),
    (DATA0, "B.Cu", [(140.206, 81.0), (139.116, 79.91), (133.7, 79.91)]),
    (DATA0, "F.Cu", [(133.7, 79.91), (133.7, 78.95), (134.322, 78.328), (134.322, 77.9475)]),
    # ---- LRCK: pin 10 -> U503 pin 14
    (LRCK, "B.Cu", [(147.358, 95.179), (147.358, 94.6), (147.258, 94.5), (147.258, 90.716),
                    (140.842, 84.3), (140.842, 83.6)]),
    (LRCK, "F.Cu", [(140.842, 83.6), (140.842, 81.0)]),
    (LRCK, "B.Cu", [(140.842, 81.0), (139.302, 79.46), (132.4, 79.46), (132.0, 79.06), (132.0, 77.9)]),
    (LRCK, "F.Cu", [(132.0, 77.9), (132.0, 76.71), (132.45, 76.26), (133.6345, 76.26)]),
    # ---- BCLK: pin 13 -> U503 pin 16
    (BCLK, "B.Cu", [(148.558, 95.179), (148.558, 91.38), (141.478, 84.3), (141.478, 83.6)]),
    (BCLK, "F.Cu", [(141.478, 83.6), (141.478, 81.0)]),
    (BCLK, "B.Cu", [(141.478, 81.0), (139.488, 79.01), (133.0, 79.01), (132.6, 78.61), (132.6, 77.26)]),
    (BCLK, "F.Cu", [(132.6, 77.26), (133.6345, 77.26)]),
    # ---- MCLK loop: pin 14 -> pin 41
    (MCLK, "B.Cu", [(148.958, 95.179), (148.958, 93.62), (149.03, 93.548)]),
    (MCLK, "F.Cu", [(149.03, 93.548), (148.285, 94.293), (148.285, 101.912), (147.207, 102.99), (145.358, 102.99)]),
    (MCLK, "B.Cu", [(145.358, 102.99), (145.358, 102.179)]),
    # ---- BTN_MUTE_N: pin 11 to its via (rest later)
    (MUTE, "B.Cu", [(147.758, 95.179), (147.758, 93.75)]),
]
VIAS = [((140.206, 83.6), DATA0), ((140.206, 81.0), DATA0), ((133.7, 79.91), DATA0),
        ((140.842, 83.6), LRCK), ((140.842, 81.0), LRCK), ((132.0, 77.9), LRCK),
        ((141.478, 83.6), BCLK), ((141.478, 81.0), BCLK), ((132.6, 77.26), BCLK),
        ((149.03, 93.548), MCLK), ((145.358, 102.99), MCLK),
        ((147.758, 93.75), MUTE)]
# The pin 8 / pin 12 stubs (kept in the east escape JSON, rewritten by --place)
STUB_3V3 = [[146.558, 94.88], [146.558, 92.848], [146.41, 92.7]]                     # pin 8 -> C310.1
STUB_0V9 = [[148.158, 94.88], [148.158, 94.6], [148.21, 94.548], [148.21, 92.9], [148.01, 92.7]]  # pin 12 -> C302.1


def place():
    """Move C310 / C302 0.15 mm west and rewrite their stubs and pad targets in the east JSON."""
    sys.path.insert(0, HERE)
    from place_tidy import BOARD, Part
    from sexpr import parse, dump, children
    root = parse(open(BOARD).read())
    for f in children(root, "footprint"):
        p = Part(f)
        if p.ref in ("C310", "C302"):
            x, y, rot = p.at
            if abs(x - (146.558 if p.ref == "C310" else 148.158)) > 0.01:
                sys.exit(f"{p.ref} is at x {x}, not where the plan expects it: moved already?")
            p.place(round(x + CAP_SHIFT, 4), y, rot)
            print(f"  {p.ref} -> ({x + CAP_SHIFT:.3f}, {y:.3f})")
    open(BOARD, "w").write(dump(root) + "\n")
    d = json.load(open(EAST_JSON))
    for ref in ("C310", "C302"):
        for pn in d["parts"][ref]:
            d["parts"][ref][pn][0] = round(d["parts"][ref][pn][0] + CAP_SHIFT, 4)
    n = 0
    for t in d["tracks"]:
        if t["layer"] == "B.Cu" and t["pts"][0] == [146.558, 94.88]:
            t["pts"], n = STUB_3V3, n + 1
        elif t["layer"] == "B.Cu" and t["pts"][0] == [148.158, 94.88]:
            t["pts"], n = STUB_0V9, n + 1
    if n != 2:
        sys.exit(f"found {n} of the 2 north-row stubs in {EAST_JSON}")
    json.dump(d, open(EAST_JSON, "w"), indent=1)
    print("wrote", BOARD, "and", EAST_JSON)


def check():
    """Copper gaps against every pad on the board, the other fixed routes and each other."""
    sys.path.insert(0, HERE)
    from place_tidy import BOARD, Part
    from sexpr import parse, children
    import east_escape_2026_11_21 as east
    import usb_main_route_2026_11_19 as usb
    import jtag_route_2026_11_21 as jtag
    root = parse(open(BOARD).read())
    pads = []
    for f in children(root, "footprint"):
        p = Part(f)
        for pd, poly in zip(children(f, "pad"), p.pads()):
            net = [c for c in pd if isinstance(c, list) and c and c[0] == "net"]
            net = str(net[0][-1]) if net else ""
            th = any(isinstance(c, str) and c in ("thru_hole", "np_thru_hole") for c in pd)
            pads.append((p.ref, str(pd[1]), net, {"F.Cu", "B.Cu"} if th else {p.side}, poly))
    mic = json.load(open(os.path.join(HERE, "mic_route_2026_11_20.json")))
    others = [(t["net"], t["layer"], 0.15, [tuple(p) for p in t["pts"]]) for t in mic["tracks"]]
    others += [(n, l, w, p) for n, l, w, p in east.TRACKS]
    others += [(n, l, usb.W, p) for n, l, p in usb.TRACKS]
    others += [(n, l, jtag.W, p) for n, l, p in jtag.TRACKS]
    ovias = [(tuple(x["at"]), x["net"]) for x in mic["vias"]] + list(east.VIAS) + list(usb.VIAS) + list(jtag.VIAS)

    def d_pt_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    def d_seg_seg(a, b, c, d):
        return min(d_pt_seg(a, c, d), d_pt_seg(b, c, d), d_pt_seg(c, a, b), d_pt_seg(d, a, b))

    def inside(p, poly):
        c = False
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[i - 1]
            if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
                c = not c
        return c

    def d_seg_poly(a, b, poly):
        if inside(a, poly) or inside(b, poly):
            return -1.0
        return min(d_seg_seg(a, b, poly[i - 1], poly[i]) for i in range(len(poly)))

    def near(a, b, pts, m=1.5):
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        return not (max(xs) < min(a[0], b[0]) - m or min(xs) > max(a[0], b[0]) + m
                    or max(ys) < min(a[1], b[1]) - m or min(ys) > max(a[1], b[1]) + m)

    short = lambda n: n.split("/")[-1]  # noqa: E731
    mine = [(n, l, W, p) for n, l, p in TRACKS]
    # my copper as (net, layers, segment a, b, half width): tracks and vias (a == b)
    items = [(n, {l}, a, b, w / 2, f"{short(n)} {l}") for n, l, w, p in mine for a, b in zip(p, p[1:])]
    items += [(n, {"F.Cu", "B.Cu"}, v, v, VIA[0] / 2, f"via {short(n)} {v}") for v, n in VIAS]
    theirs = [(n, {l}, a, b, w / 2, f"{short(n)} {l}") for n, l, w, p in others for a, b in zip(p, p[1:])]
    theirs += [(n, {"F.Cu", "B.Cu"}, v, v, VIA[0] / 2, f"via {short(n)}") for v, n in ovias]
    bad = []
    for k, (net, lays, a, b, hw, what) in enumerate(items):
        for ref, pn, n2, l2, poly in pads:
            if n2 != net and lays & l2 and near(a, b, poly):
                bad.append((d_seg_poly(a, b, poly) - hw, f"{what} - {ref}.{pn} {short(n2)}"))
        for n2, l2, c, d, hw2, w2 in theirs + items[k + 1:]:
            if n2 != net and lays & l2 and near(a, b, [c, d]):
                bad.append((d_seg_seg(a, b, c, d) - hw - hw2, f"{what} - {w2}"))
    bad.sort()
    return bad


if __name__ == "__main__":
    if "--place" in sys.argv:
        place()
        sys.exit()
    for net in (DATA0, LRCK, BCLK, MCLK):
        segs = [(a, b) for n, l, p in TRACKS if n == net for a, b in zip(p, p[1:])]
        nv = sum(1 for _, n in VIAS if n == net)
        print(f"{net.split('/')[-1]:10} {sum(math.dist(a, b) for a, b in segs):5.1f} mm, {nv} vias")
    bad = check()
    print("closest copper gaps (need >= 0.15):")
    for g, what in bad[:14]:
        print(f"  {g:.3f}  {what}")
