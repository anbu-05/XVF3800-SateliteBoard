"""Power copper, version 2 (2026-11-18), after the XVF3800 rotation (tools/xvf_rotate_2026_11_18.py).

Rebuilds all tracks, vias and zones from scratch:

  Zones (fill priority: higher fills first, lower keeps clearance from it)
    In1  GND          whole board
    In2  +1V8   (5)   east band x 151.4-160 (C318, C315, C316, LDO output; also under the USB
                      exit, so the USB pair crosses only one plane edge) + a leg to C317 (pin 31)
    In2  +0V9   (4)   island under the XVF3800, a 1.8 mm neck through the south cap row
                      (between C311 +3V3 and C317 +1V8, over C305), then down to L201/C203/C204
    In2  VBUS_ESP(3), VBUS_MAIN(2), +5V(1), +3V3(0): as in power_planes_2026_11_18.py
  +5V_LED ring on B.Cu (r 28.7, radial stubs) as before.
  Vias in pads (user 2026-11-18: epoxy-filled, capped): every SMD pad on a planed rail gets a via
    when the plane under it is that net, the via fits inside the pad, and it would not pierce a
    pad of another net on the other side (e.g. XVF3800 +0V9 paddles under the ESP32 GND pads).
    Since 2026-11-19: vias are centred on the pad (patterns centred on it) and their count follows
    the pad's current (PART_AMPS; 1 A per 0.6/0.3 via, 0.5 A per 0.45/0.2); a pad too small for
    its count gets the rest just outside on a stub. GND everywhere goes to In1.
  Power traces (rails without a plane, and pads whose via was skipped) are routed by
    tools/jog_router.py: 0/45/90 degree runs with jogs.

Not done here (left for the signal routing pass): XVF3800 +0V9/+3V3 pin fan-out to their caps
(those caps sit over the wrong plane for a via), FB301's +0V9 side, C313/C314 (+3V3 over the
+1V8 band), the power test pads, and the USB stitching cap.

Usage (PCB editor closed):  python3 tools/power_v2_2026_11_18.py [--out FILE]
"""
import math
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, LEFT, RIGHT, TOP, BOTTOM, Part, bbox, circle_pts  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402
from jog_router import Router, Shape, _inside  # noqa: E402

CX, CY = 146.558, 98.679
RING_R, RING_W = 28.7, 1.0
VIA_BIG, VIA_SMALL = (0.6, 0.3), (0.45, 0.2)

root = parse(open(BOARD).read())
root[:] = [n for n in root if not (isinstance(n, list) and n and n[0] in ("segment", "arc", "via", "zone"))]
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p
items, report = [], []


def uid():
    return q(str(uuid.uuid4()))


def f4(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def net_of(pd):
    n = child(pd, "net")
    return str(n[1]) if n else ""


def pads_of(ref):
    """(pin, net, polygon, centre, (w, h), type) for every pad of a part."""
    out = []
    for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
        lays = [str(x) for x in (child(pd, "layers") or [])[1:]]
        if not any(x.endswith(".Cu") for x in lays):
            continue                                   # paste-only windows (e.g. EP sub-pads): no copper
        b = bbox(poly)
        out.append((str(pd[1]), net_of(pd), poly, ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2),
                    (b[2] - b[0], b[3] - b[1]), str(pd[2])))
    return out


def pad(ref, pin):
    for x in pads_of(ref):
        if x[0] == str(pin):
            return x
    raise KeyError(f"{ref}.{pin}")


# ================================================================ zones
ZONES = [  # net, layer, priority, polygon
    ("GND", "In1.Cu", 0, [(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM)]),
    ("+3V3", "In2.Cu", 0, [(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM)]),
    # +5V: since 2026-11-19 a finger east of the arm (x 170.7-173.3, y 112.9-114.9) into what was
    # VBUS_MAIN, for the U103 pin-8 vias east of the LED ring
    ("+5V", "In2.Cu", 1, [(152.3, 109.8), (170.7, 109.8), (170.7, 112.9), (173.3, 112.9), (173.3, 114.9),
                          (170.7, 114.9), (170.7, 114.75), (164.3, 114.75), (164.3, 130.2),
                          (130.5, 130.2), (130.5, 115.5), (134.3, 115.5), (134.3, 119.8), (146.2, 119.8),
                          (146.2, 122.0), (158.9, 122.0), (158.9, 113.4), (152.3, 113.4)]),
    # VBUS_MAIN: notched for that finger; the strip below it (y 115.25-117.2) takes the pin-7 vias
    ("VBUS_MAIN", "In2.Cu", 2, [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 115.25),
                                (173.3, 115.25), (173.3, 112.6), (172.8, 112.6), (172.8, 103.5), (170.8, 103.5)]),
    ("VBUS_ESP", "In2.Cu", 3, [(114.6, 94.8), (122.3, 94.8), (122.3, 103.5), (118.9, 103.5), (118.9, 130.5),
                               (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)]),
    ("+0V9", "In2.Cu", 4, [(142.3, 94.4), (150.9, 94.4), (150.9, 103.0), (148.8, 103.0), (148.8, 113.7),
                           (158.8, 113.7), (158.8, 121.7), (147.0, 121.7), (147.0, 103.0), (142.3, 103.0)]),
    ("+1V8", "In2.Cu", 5, [(151.4, 93.9), (160.0, 93.9), (160.0, 106.3), (148.9, 106.3), (148.9, 103.3),
                           (151.4, 103.3)]),
]
for net, layer, pri, pts in ZONES:
    z = ["zone", ["net", q(net)], ["layer", q(layer)], ["uuid", uid()], ["name", q(f"{net} {layer}")],
         ["hatch", "edge", "0.5"]]
    if pri:
        z.append(["priority", str(pri)])
    z += [["connect_pads", ["clearance", "0.3"]], ["min_thickness", "0.25"], ["filled_areas_thickness", "no"],
          ["fill", "yes", ["thermal_gap", "0.5"], ["thermal_bridge_width", "0.5"], ["island_removal_mode", "0"]],
          ["polygon", ["pts"] + [["xy", f4(x), f4(y)] for x, y in pts]]]
    items.append(z)


def plane_owner(layer, pt):
    """Net of the highest-priority zone on `layer` containing pt."""
    best = None
    for net, lay, pri, pts in ZONES:
        if lay == layer and _inside(pt[0], pt[1], pts) and (best is None or pri > best[1]):
            best = (net, pri)
    return best[0] if best else None


def plane_ok(net, pt, r):
    """True if a via of radius r at pt lands well inside that net's own plane."""
    layer = "In1.Cu" if net == "GND" else "In2.Cu"
    ring = [pt] + [(pt[0] + (r + 0.15) * math.cos(a), pt[1] + (r + 0.15) * math.sin(a))
                   for a in [k * math.pi / 4 for k in range(8)]]
    return all(plane_owner(layer, p) == net for p in ring)


PLANED = {z[0] for z in ZONES}

# ================================================================ copper bookkeeping for the router
shapes = []
for ref, p in P.items():
    for pin, net, poly, c, wh, kind in pads_of(ref):
        layers = {"F.Cu", "B.Cu"} if kind in ("thru_hole", "np_thru_hole") else {p.side}
        shapes.append(Shape(net if kind != "np_thru_hole" else "~hole", layers, poly=poly))
router = Router((LEFT, TOP, RIGHT, BOTTOM), shapes)
new_vias = []
via_shape = {}          # (x, y) -> Shape of every via placed here
connected = {}          # net -> Shapes already joined to that net's tree (start points for routes)
pad_shape = {}          # (ref, pin) -> Shape
for ref, p in P.items():
    for k, (pin, net, poly, c, wh, kind) in enumerate(pads_of(ref)):
        layers = {"F.Cu", "B.Cu"} if kind in ("thru_hole", "np_thru_hole") else {p.side}
        pad_shape[(ref, pin, k)] = Shape(net, layers, poly=poly)
        pad_shape.setdefault((ref, pin), pad_shape[(ref, pin, k)])   # first pad of that number


def seg(a, b, w, layer, net, connect=True):
    items.append(["segment", ["start", f4(a[0]), f4(a[1])], ["end", f4(b[0]), f4(b[1])], ["width", f4(w)],
                  ["layer", q(layer)], ["net", q(net)], ["uuid", uid()]])
    sh = Shape(net, {layer}, seg=(a, b, w))
    router.add(sh)
    if connect:
        connected.setdefault(net, []).append(sh)


def arc(a, m, b, w, layer, net):
    items.append(["arc", ["start", f4(a[0]), f4(a[1])], ["mid", f4(m[0]), f4(m[1])], ["end", f4(b[0]), f4(b[1])],
                  ["width", f4(w)], ["layer", q(layer)], ["net", q(net)], ["uuid", uid()]])
    for s, e in ((a, m), (m, b)):                 # good enough for clearance: two chords + width
        router.add(Shape(net, {layer}, seg=(s, e, w + 0.3)))


def via(pt, net, size=VIA_BIG, connect=None):
    """connect=None: the via counts as joined to the net's tree only if it lands in its plane."""
    items.append(["via", ["at", f4(pt[0]), f4(pt[1])], ["size", f4(size[0])], ["drill", f4(size[1])],
                  ["layers", q("F.Cu"), q("B.Cu")], ["net", q(net)], ["uuid", uid()]])
    sh = Shape(net, {"F.Cu", "B.Cu"}, circle=(pt, size[0] / 2))
    router.add(sh)
    if connect is None:
        connect = net in PLANED and plane_ok(net, pt, size[0] / 2)
    if connect:
        connected.setdefault(net, []).append(sh)
    via_shape[(round(pt[0], 3), round(pt[1], 3))] = sh
    new_vias.append((pt, size[0] / 2, net))


# ================================================================ +5V_LED ring on B.Cu (unchanged design)
def on_ring(deg):
    a = math.radians(deg)
    return (CX + RING_R * math.cos(a), CY + RING_R * math.sin(a))


junctions = []
for i in range(1, 13):
    c = pad(f"D8{i:02d}", 4)[3]
    junctions.append((math.degrees(math.atan2(c[1] - CY, c[0] - CX)), "stub", c))
for a in (49.6, 51.8, -36.0):                     # two feeds from U801/C815, one up to U802
    junctions.append((a, "via", None))
junctions.sort(key=lambda j: j[0])
ring_vias = {}
for k, (ang, kind, c) in enumerate(junctions):
    pt = on_ring(ang)
    if kind == "stub":
        seg(c, pt, 0.5, "B.Cu", "+5V_LED", connect=False)
    else:
        via(pt, "+5V_LED", connect=False)
        ring_vias[ang] = pt
    a2 = junctions[(k + 1) % len(junctions)][0]
    a2 = a2 + 360 if a2 <= ang else a2
    arc(pt, on_ring((ang + a2) / 2), on_ring(a2), RING_W, "B.Cu", "+5V_LED")

# ================================================================ explicit vias
VIA_5V_A, VIA_5V_B = (131.2, 116.2), (132.4, 116.2)      # +5V tab beside the old LDO spot -> trunk
VIA_1V8 = (157.6, 99.3)                                  # +1V8 band -> F.Cu channel east of the module
HOP1, HOP2 = (133.6, 87.9), (129.0, 87.9)                # +1V8 to R303: under the +5V trunk on B.Cu
for pt, net in ((VIA_5V_A, "+5V"), (VIA_5V_B, "+5V"), (VIA_1V8, "+1V8"), (HOP1, "+1V8"), (HOP2, "+1V8")):
    via(pt, net)
seg(VIA_5V_A, VIA_5V_B, 1.0, "F.Cu", "+5V")                 # the trunk's two vias side by side

# ================================================================ TPS2121 (U103) power-pin flanges
# (user 2026-11-19) Pins 1/2/7/8 carry 1.5-3 A, but no via fits under them: pins 2/7 sit over the
# wrong In2 plane, and the B.Cu LED ring runs under the chip's east half. Each pin gets a small
# F.Cu pour (solid to the pad) out to its own group of 0.6/0.3 vias (1 A each), in its own plane:
#   pin 1 +5V       1.5 A: 2 vias west, the pour also takes in C106's +5V pad (the 3 A bulk cap)
#   pin 2 VBUS_ESP  3 A:   3 vias south-west, the pour also takes in C104 and C103's VBUS_ESP pads
#   pin 7 VBUS_MAIN 3 A:   3 vias east (In2 strip below the +5V finger), with C102 and C101's pads
#   pin 8 +5V       1.5 A: 2 vias north-east, past the ring, in the In2 +5V finger
# The spots were checked by hand against the ring, D812, the pins' signal escapes (pins 3-6 go
# south to the dividers, 9-12 north) and the In2 plane edges; DRC confirms. The pours keep 0.2 mm
# from other nets (KiCad fills them); the router treats each pour outline as that net's copper.
FLANGES = [  # pin, net, via spots, pour outline (F.Cu)
    ("1", "+5V", [(167.75, 114.1), (167.0, 113.7)],
     [(166.3, 113.3), (167.5, 113.3), (168.35, 114.15), (169.0, 114.15), (169.0, 114.68), (166.3, 114.68)]),
    ("2", "VBUS_ESP", [(167.85, 115.75), (167.05, 115.75), (167.45, 116.5)],
     [(169.0, 114.9), (165.8, 114.9), (165.8, 115.7), (166.3, 115.7), (166.3, 117.0), (167.1, 117.0),
      (167.8, 116.3), (168.35, 115.4), (169.0, 115.4)]),
    ("7", "VBUS_MAIN", [(171.6, 115.8), (172.4, 115.8), (172.0, 116.55)],
     [(170.3, 114.93), (173.6, 114.93), (173.6, 115.95), (172.6, 116.95), (171.25, 116.95), (171.25, 115.45),
      (170.3, 115.45)]),
    ("8", "+5V", [(172.25, 113.6), (171.8, 114.4)],
     [(170.3, 114.15), (171.0, 114.15), (171.0, 113.2), (172.75, 113.2), (172.75, 114.68), (170.3, 114.68)]),
]
FLANGED = set()                                   # (ref, pin) handled here, skipped by the in-pad pass
for pin, net, spots, outline in FLANGES:
    items.append(["zone", ["net", q(net)], ["layer", q("F.Cu")], ["uuid", uid()], ["name", q(f"U103.{pin} flange")],
                  ["hatch", "edge", "0.5"], ["priority", "10"], ["connect_pads", "yes", ["clearance", "0.2"]],
                  ["min_thickness", "0.2"], ["filled_areas_thickness", "no"],
                  ["fill", "yes", ["thermal_gap", "0.5"], ["thermal_bridge_width", "0.5"], ["island_removal_mode", "0"]],
                  ["polygon", ["pts"] + [["xy", f4(x), f4(y)] for x, y in outline]]])
    router.add(Shape(net, {"F.Cu"}, poly=outline))
    for s_ in spots:
        via(s_, net, VIA_BIG)
    connected.setdefault(net, []).append(pad_shape[("U103", pin)])
    FLANGED.add(("U103", pin))
    report.append(f"  U103.{pin:2s}     {net:9s} flange: {len(spots)} vias 0.6/0.3")
# other pads the pours take in (they need no route of their own)
for ref, pin in (("C104", "1"), ("C102", "1")):
    connected.setdefault(pad(ref, pin)[1], []).append(pad_shape[(ref, pin)])

# ================================================================ vias in pads
# User's rules (2026-11-19):
#   * vias sit on the pad centre; when a pad needs several, they form a pattern centred on the
#     pad centre (odd counts: one on the centre, the rest in mirror pairs along the long axis;
#     even counts: mirror pairs, none on the centre; a grid on big pads);
#   * the count follows the current the pad carries: 1 A per 0.6/0.3 via, 0.5 A per 0.45/0.2;
#   * if the centre is blocked (wrong plane, or another net's pad on the other side) the pad
#     gets no via and is routed instead, as before;
#   * if the pad is too small for the count it needs, the rest go just outside it on a short
#     stub of pad width.
VIA_AMPS = {VIA_BIG: 1.0, VIA_SMALL: 0.5}
# Peak current (A) each part carries on a net, from the 5 V budget (AGENTS.md / archive-002):
# VBUS and the TPS2121 path 3 A (ILIM 3.2 A), amp 1.6 A (5 W into 4 ohm), LED ring 0.75 A,
# 3.3 V buck ~0.45 A in / 0.6 A out, 0.9 V buck ~0.2 A in / 1 A out, ESP32 0.4 A on Wi-Fi.
# It is shared equally between the part's pads on that net. GND pads carry the current of the
# rail the part serves. Parts not listed carry little (one via).
PART_AMPS = {
    ("J101", "VBUS_MAIN"): 3.0, ("C101", "VBUS_MAIN"): 3.0, ("U103", "VBUS_MAIN"): 3.0,
    ("J102", "VBUS_ESP"): 3.0, ("C103", "VBUS_ESP"): 3.0, ("U103", "VBUS_ESP"): 3.0,
    ("U103", "+5V"): 3.0, ("C106", "+5V"): 3.0, ("U502", "+5V"): 1.6, ("U801", "+5V"): 0.75,
    ("U201", "+5V"): 0.45, ("C202", "+5V"): 0.45, ("C206", "+5V"): 0.45, ("U202", "+5V"): 0.2,
    ("J701", "+5V"): 0.5,
    ("L202", "+3V3"): 0.6, ("C207", "+3V3"): 0.6, ("U601", "+3V3"): 0.4, ("C601", "+3V3"): 0.4,
    ("L201", "+0V9"): 1.0, ("C203", "+0V9"): 1.0, ("C204", "+0V9"): 1.0,
    ("J101", "GND"): 3.0, ("J102", "GND"): 3.0, ("C101", "GND"): 3.0, ("C103", "GND"): 3.0,
    ("C106", "GND"): 3.0, ("U201", "GND"): 0.45, ("C202", "GND"): 0.45, ("C206", "GND"): 0.45,
    ("U202", "GND"): 0.2, ("C207", "GND"): 0.6, ("C203", "GND"): 1.0, ("C204", "GND"): 1.0,
    ("U503", "GND"): 1.6, ("C509", "GND"): 1.6, ("U601", "GND"): 0.4,
}
other_side = {"F.Cu": "B.Cu", "B.Cu": "F.Cu"}
skipped = {"wrong plane": 0, "too small": 0, "other side": 0}
via_report = []                                   # (ref.pin, net, amps, vias in pad, vias beside)


def spot_clear(pt, net, r):
    """A via of radius r at pt: right plane under it, and clear of other nets' copper."""
    if not plane_ok(net, pt, r):
        return "wrong plane"
    for sh in router.shapes:
        if sh.net != net and sh.layers & {"F.Cu", "B.Cu"} and sh.dist(*pt) < r + 0.15:
            return "other side"
    return None


def gap_same(r1, r2):
    """Centre spacing for two vias of the same net: drill edges 0.25 mm apart (copper may touch)."""
    drill = {VIA_BIG[0] / 2: VIA_BIG[1], VIA_SMALL[0] / 2: VIA_SMALL[1]}
    return drill.get(round(r1, 4), 0.3) / 2 + drill.get(round(r2, 4), 0.3) / 2 + 0.25


def centred_pattern(c, w, h, size, n):
    """Up to n via spots centred on c that fit inside a w x h pad."""
    r = size[0] / 2
    pitch = size[0] + 0.15
    def fit(span):                                # how many fit in a row across this span
        k = 0
        while (k * pitch) + 2 * r <= span + 1e-9:          # a via may reach the pad edge
            k += 1
        return k
    along_x = w >= h
    cols, rows = (fit(w), fit(h)) if along_x else (fit(h), fit(w))   # cols on the long axis
    if cols == 0 or rows == 0:
        return []
    if n <= cols:
        cols, rows = n, 1
    else:
        rows = min(rows, math.ceil(n / cols))
        if n <= cols * rows:                      # trim columns while the grid still holds n
            while (cols - 1) * rows >= n:
                cols -= 1
    pts = []
    for i in range(cols):
        for j in range(rows):
            u = (i - (cols - 1) / 2) * pitch
            v = (j - (rows - 1) / 2) * pitch
            pts.append((c[0] + u, c[1] + v) if along_x else (c[0] + v, c[1] + u))
    return pts


def beside_spots(c, w, h, size, k, net, layer):
    """k vias just outside the pad, each on a straight 0/45/90 stub from the pad centre."""
    r = size[0] / 2
    stub_w = max(0.3, min(min(w, h), size[0]))
    out = []
    long_dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)] if w >= h else [(0, 1), (0, -1), (1, 0), (-1, 0)]
    dirs = long_dirs + [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    for dx, dy in dirs:
        if len(out) >= k:
            break
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        # distance from the centre to the pad edge in this direction
        edge = min((w / 2) / abs(ux) if ux else 1e9, (h / 2) / abs(uy) if uy else 1e9)
        d = edge + r + 0.1
        while d <= edge + 1.6 and len(out) < k:
            pt = (round(c[0] + ux * d, 4), round(c[1] + uy * d, 4))
            if (spot_clear(pt, net, r) is None
                    and all(math.dist(pt, v[0]) >= (gap_same(r, v[1]) if v[2] == net else r + v[1] + 0.15)
                            for v in new_vias)
                    and router._seg_clearance(c, pt, [sh for sh in router.shapes if sh.net != net and layer in sh.layers],
                                              stub_w) >= 0.15):
                out.append((pt, stub_w))
                break
            d += 0.1
    return out


for ref, p in P.items():
    pads_here = pads_of(ref)
    for pk, (pin, net, poly, c, (w, h), kind) in enumerate(pads_here):
        if kind != "smd" or net not in PLANED or (ref, pin) in FLANGED:
            continue
        small, long_ = min(w, h), max(w, h)
        n_same = sum(1 for x in pads_here if x[1] == net and x[5] == "smd")
        amps = PART_AMPS.get((ref, net), 0.0) / max(1, n_same)
        paddle = ref == "U301" and long_ > 3.0
        if paddle:                                            # XVF3800 paddles: a row (or grid), centred
            size = VIA_BIG if small >= 0.8 else VIA_SMALL
            if small > 3.0:
                spots = [(c[0] + dx, c[1] + dy) for dx in (-1.1, 0, 1.1) for dy in (-1.1, 0, 1.1)]
            elif w > h:
                spots = [(c[0] + dx, c[1]) for dx in (-1.1, 0, 1.1)]
            else:
                spots = [(c[0], c[1] + dy) for dy in (-1.1, 0, 1.1)]
            need = len(spots)
        else:
            if small < 0.5 and amps == 0.0:
                skipped["too small"] += 1
                continue
            # via size: the big one if the pad takes it; for a current, whichever size holds
            # the needed count inside the pad (else the one that holds more of it)
            options = []
            for sz in (VIA_BIG, VIA_SMALL):
                if sz == VIA_BIG and small < 0.8:
                    continue
                n = max(1, math.ceil(amps / VIA_AMPS[sz] - 1e-9))
                inside = centred_pattern(c, w, h, sz, n)
                options.append((min(len(inside), n) >= n, len(inside) * VIA_AMPS[sz], sz, n, inside))
            options.sort(key=lambda o: (not o[0], -o[1]))
            _, _, size, need, spots = options[0]
        r = size[0] / 2
        # the centre (or the centre spot of the pattern) must be clear, else route this pad
        # (paddles: their centred row keeps whichever spots are clear, as agreed on 2026-11-18,
        #  because the +0V9 paddles under the ESP32 GND pads cannot be routed instead)
        if spots and not paddle:
            why = spot_clear(c if any(math.dist(s_, c) < 1e-6 for s_ in spots) else spots[0], net, r)
            if why and not any(math.dist(c, v[0]) < r + v[1] + 0.1 for v in new_vias):
                skipped[why] += 1
                if amps > 0:
                    via_report.append((f"{ref}.{pin}", net, round(amps, 2), 0, 0, 0, f"centre blocked ({why}), routed"))
                continue
        placed = 0
        kept = []
        for s_ in spots:
            if any(math.dist(s_, v[0]) < r + v[1] + 0.1 for v in new_vias):
                placed += 1                                  # stacked pads (USB-C A/B pins): shared via
                continue
            if spot_clear(s_, net, r):
                continue
            kept.append(s_)
        # keep the pattern symmetric about the centre: drop spots whose mirror image is lost
        if not paddle:
            kept = [s_ for s_ in kept if any(math.dist((2 * c[0] - s_[0], 2 * c[1] - s_[1]), t) < 1e-6 for t in kept)]
        for s_ in kept:
            via(s_, net, size)
        placed += len(kept)
        if placed:
            connected.setdefault(net, []).append(pad_shape[(ref, pin, pk)])
        beside = []
        if amps > 0 and placed < need and not paddle:
            # the rest go outside the pad, where there is room for the big via (1 A each)
            rest = max(0.0, amps - placed * VIA_AMPS[size])
            need = placed + math.ceil(rest / VIA_AMPS[VIA_BIG] - 1e-9)
            beside = beside_spots(c, w, h, VIA_BIG, need - placed, net, p.side)
            for pt, sw in beside:
                via(pt, net, VIA_BIG)
                seg(c, pt, sw, p.side, net)
            if beside and not placed:
                connected.setdefault(net, []).append(pad_shape[(ref, pin, pk)])
        if amps > 0:
            via_report.append((f"{ref}.{pin}", net, round(amps, 2), placed, len(beside), need, ""))
report.append(f"vias in pads: {sum(1 for v in new_vias)} vias total so far; skipped {skipped}")
for name, net, amps, inside, out_, need, note in via_report:
    flag = note or ("" if inside + out_ >= need else f"  SHORT by {need - inside - out_}")
    report.append(f"  {name:9s} {net:9s} {amps:4.2f} A: {inside} in pad + {out_} beside (need {need}){flag}")

# ================================================================ routed power traces
# Keep power traces out from under the ESP32 module on the top layer: that area only opens to
# the west and may be needed for XVF3800 escapes. GND may still join the module's centre pads.
keep = Shape("~module", {"F.Cu"}, poly=P["U601"].courtyard())
keep.exempt = {"GND"}
router.add(keep)
ROUTES = [  # net, layer, width, target (ref, pin) or ("@", (x, y)), clearance
    # XVF3800 +1V8 pins to their caps (bottom)
    ("+1V8", "B.Cu", 0.15, ("C315", 1), 0.15, ("U301", 17)),
    ("+1V8", "B.Cu", 0.15, ("C316", 1), 0.15, ("U301", 26)),
    ("+1V8", "B.Cu", 0.15, ("C317", 1), 0.15, ("U301", 31)),
    # amp supply
    ("+5V_AMP", "F.Cu", 0.8, ("C511", 1), 0.2, ("U502", 6)),
    ("+5V_AMP", "F.Cu", 0.6, ("C510", 1), 0.2, None),
    ("+5V_AMP", "F.Cu", 0.4, ("C509", 1), 0.2, None),
    ("+5V_AMP", "F.Cu", 0.25, ("U503", 7), 0.15, None),
    ("+5V_AMP", "F.Cu", 0.25, ("U503", 8), 0.15, None),
    ("+5V_AMP", "F.Cu", 0.4, ("U502", 5), 0.2, None),
    ("+5V_AMP", "F.Cu", 0.25, ("R511", 2), 0.2, None),
    # +5V trunk and branches
    ("+5V", "F.Cu", 1.0, ("@", VIA_5V_A), 0.2, None),
    ("+5V", "F.Cu", 0.5, ("U502", 1), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("C508", 1), 0.2, None),
    ("+5V", "F.Cu", 0.5, ("C604", 1), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("U602", 5), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("C605", 1), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("D601", 4), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("R205", 2), 0.2, None),
    ("+5V", "F.Cu", 0.5, ("U201", 4), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("U201", 1), 0.2, None),
    ("+5V", "F.Cu", 0.5, ("U202", 4), 0.2, None),
    ("+5V", "F.Cu", 0.4, ("U202", 1), 0.2, None),
    ("+5V", "F.Cu", 0.5, ("U801", 1), 0.2, None),
    # LED switch output to the ring and to U802
    ("+5V_LED", "F.Cu", 0.5, ("U801", 5), 0.2, ("U801", 6)),
    ("+5V_LED", "F.Cu", 0.8, ("C815", 1), 0.2, ("U801", 6)),
    ("+5V_LED", "F.Cu", 1.0, ("@", ring_vias[49.6]), 0.2, None),
    ("+5V_LED", "F.Cu", 1.0, ("@", ring_vias[51.8]), 0.2, None),
    ("+5V_LED", "F.Cu", 0.5, ("C816", 1), 0.2, ("@", ring_vias[-36.0])),
    ("+5V_LED", "F.Cu", 0.4, ("U802", 5), 0.2, None),
    # LDO
    ("+1V8", "B.Cu", 0.4, ("C209", 1), 0.2, ("U203", 5)),
    ("+3V3", "B.Cu", 0.4, ("C208", 1), 0.2, ("U203", 1)),
    ("+3V3", "B.Cu", 0.3, ("U203", 3), 0.2, None),
    # +1V8 loads on the top side, from the band via
    ("+1V8", "F.Cu", 0.3, ("J301", 1), 0.2, None),
    ("+1V8", "F.Cu", 0.3, ("J701", 3), 0.2, None),
    ("+1V8", "F.Cu", 0.3, ("@", HOP1), 0.2, None),
    ("+1V8", "B.Cu", 0.3, ("@", HOP2), 0.2, ("@", HOP1)),
    ("+1V8", "F.Cu", 0.25, ("R303", 2), 0.2, ("@", HOP2)),
    # buck feedback tops / misc +3V3 pads that sit over another plane
    ("+3V3", "F.Cu", 0.3, ("C205", 1), 0.2, None),
    # TPS2121 divider tops (the input pins themselves are on their flanges, see above)
    ("VBUS_MAIN", "F.Cu", 0.25, ("R109", 2), 0.15, None),
    ("VBUS_MAIN", "F.Cu", 0.25, ("R105", 2), 0.15, None),
    ("VBUS_ESP", "F.Cu", 0.25, ("R107", 2), 0.15, None),
    ("VBUS_ESP", "F.Cu", 0.25, ("R111", 2), 0.15, None),
] + [("+5V_LED", "B.Cu", 0.3, (f"C8{i:02d}", 1), 0.15, (f"D8{i:02d}", 4)) for i in range(1, 13)]
import jog_router  # noqa: E402

failed = []
for net, layer, width, tgt, clr, start in ROUTES:
    jog_router.CLEARANCE = clr
    if tgt[0] == "@":
        goal = circle_pts(tgt[1][0], tgt[1][1], 0.15)
        label = f"via {tgt[1]}"
    else:
        goal = pad(*tgt)[2]
        label = f"{tgt[0]}.{tgt[1]}"
    # a named start is the only start; otherwise anything already joined to the net
    if start is None:
        starts = list(connected.get(net, []))
    elif start[0] == "@":
        starts = [via_shape[(round(start[1][0], 3), round(start[1][1], 3))]]
    else:
        starts = [pad_shape[(start[0], str(start[1]))]]
    extra = []
    w = width
    path = None
    while w >= 0.15 and path is None:
        path = router.route(net, layer, w, goal, starts, extra_starts=extra)
        if path is None:
            w = round(w * 0.7, 2)
    if path is None:
        failed.append(f"{net} {layer} -> {label}")
        continue
    for a, b in zip(path, path[1:]):
        seg(a, b, w, layer, net)
    connected.setdefault(net, [])
    connected[net] += starts
    if tgt[0] != "@":
        connected[net].append(pad_shape[(tgt[0], str(tgt[1]))])
    else:
        connected[net].append(via_shape[(round(tgt[1][0], 3), round(tgt[1][1], 3))])
    report.append(f"routed {net:8s} {layer} w{w:<4} -> {label} ({len(path) - 1} segments)")
report.append(f"FAILED: {failed}" if failed else "all explicit routes found")

# ---------------------------------------------------------------- automatic pass
# Every SMD pad on a planed rail that has neither a via nor a route yet: route it on its own
# layer to the nearest copper already joined to its net (within a few mm); failing that, drop a
# fan-out via beside it in its plane. The XVF3800 area (chip, its caps, flash, crystal) is left
# for the signal-routing pass, where its fan-out is planned together with the escape gaps.
XVF_AREA = (136.0, 86.0, 158.2, 108.6)                  # bottom side only
jog_router.MARGIN = 4.0
jog_router.CLEARANCE = 0.15
joined = {id(x) for lst in connected.values() for x in lst}
auto_ok, auto_via, auto_fail = 0, 0, []


def via_fits(pt, net, r):
    if not (LEFT + 0.6 < pt[0] < RIGHT - 0.6 and TOP + 0.6 < pt[1] < BOTTOM - 0.6):
        return False
    if not plane_ok(net, pt, r):
        return False
    return not any(sh.net != net and not sh.net.startswith("~module") and sh.layers & {"F.Cu", "B.Cu"}
                   and sh.dist(*pt) < r + 0.15 for sh in router.shapes)


for ref, p in sorted(P.items()):
    if ref.startswith("TP"):
        continue
    for pk, (pin, net, poly, c, (w, h), kind) in enumerate(pads_of(ref)):
        if kind != "smd" or net not in PLANED:
            continue
        sh = pad_shape[(ref, pin, pk)]
        if id(sh) in joined or any(math.dist(c, v[0]) < max(w, h) / 2 and v[2] == net for v in new_vias):
            continue
        if p.side == "B.Cu" and XVF_AREA[0] < c[0] < XVF_AREA[2] and XVF_AREA[1] < c[1] < XVF_AREA[3]:
            continue
        layer = p.side
        width = max(0.15, min(0.3, min(w, h) - 0.05))
        path = router.route(net, layer, width, poly, list(connected.get(net, [])))
        if path is None:
            # fan-out via: nearest spot within 1.6 mm where a small via fits in the right plane
            spot = None
            for rad in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6):
                for k in range(16):
                    a = k * math.pi / 8
                    t = (round((c[0] + rad * math.cos(a)) / 0.1) * 0.1, round((c[1] + rad * math.sin(a)) / 0.1) * 0.1)
                    if via_fits(t, net, VIA_SMALL[0] / 2):
                        spot = t
                        break
                if spot:
                    break
            if spot:
                n_items, n_shapes = len(items), len(router.shapes)
                via(spot, net, VIA_SMALL, connect=False)
                vsh = via_shape[(round(spot[0], 3), round(spot[1], 3))]
                path = router.route(net, layer, width, poly, [vsh])
                if path is None:                                 # no use: take the via back out
                    del items[n_items:]
                    del router.shapes[n_shapes:]
                    new_vias.pop()
                else:
                    connected.setdefault(net, []).append(vsh)
                    auto_via += 1
        if path is None:
            auto_fail.append(f"{ref}.{pin} {net}")
            continue
        for a, b in zip(path, path[1:]):
            seg(a, b, width, layer, net)
        connected.setdefault(net, []).append(sh)
        joined.add(id(sh))
        auto_ok += 1
report.append(f"automatic pass: {auto_ok} pads joined ({auto_via} with a fan-out via); "
              f"not joined: {auto_fail if auto_fail else 'none'}")


def split_t_junctions():
    """A route that starts on the middle of another track of its net (the router joins on a
    track's centre line) makes a T. KiCad flags such an end as dangling, so the run it lands on
    is cut in two at that point, and every T becomes an ordinary shared end point."""
    segs = [n for n in items if n[0] == "segment"]
    ends = [(float(child(n, e)[1]), float(child(n, e)[2]), str(child(n, "layer")[1]), str(child(n, "net")[1]))
            for n in segs for e in ("start", "end")]
    for (px, py, lay, net) in ends:
        for n in [m for m in items if m[0] == "segment"]:
            if str(child(n, "layer")[1]) != lay or str(child(n, "net")[1]) != net:
                continue
            a = (float(child(n, "start")[1]), float(child(n, "start")[2]))
            b = (float(child(n, "end")[1]), float(child(n, "end")[2]))
            if min(math.dist(a, (px, py)), math.dist(b, (px, py))) < 0.1:
                continue                     # at (or a hair from) its end: no sliver
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = ((px - a[0]) * dx + (py - a[1]) * dy) / L2
            if 0 < t < 1 and math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy)) < 1e-3:
                w = float(child(n, "width")[1])
                items.remove(n)
                for s_, e_ in ((a, (px, py)), ((px, py), b)):
                    items.append(["segment", ["start", f4(s_[0]), f4(s_[1])], ["end", f4(e_[0]), f4(e_[1])],
                                  ["width", f4(w)], ["layer", q(lay)], ["net", q(net)], ["uuid", uid()]])
                break


split_t_junctions()
root.extend(items)
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else BOARD
open(out, "w").write(dump(root) + "\n")
counts = {}
for n in items:
    counts[n[0]] = counts.get(n[0], 0) + 1
print("\n".join(report))
print("added", counts, "->", out)
