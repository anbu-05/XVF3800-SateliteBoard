"""Power planes and power traces, 2026-11-18 (plan: verification/power-review-2026-11-17/).

User, 2026-11-18: draw the In2 regions; the LED ring supply is a circle on the bottom layer;
the rails without a plane are thick traces on the top layer. In1 is a solid GND plane.
Pads on rails that have a plane are joined to it later, in the routing pass.

  Zones (fill priority: higher fills first, lower keeps clearance from it)
    In1  GND        whole board
    In2  +0V9  (4)  island under the XVF3800, neck down between the bucks, pocket round L201/C203/C204
    In2  VBUS_ESP(3) J102 strip down the left edge, along the bottom edge, up a column to C103/C104
    In2  VBUS_MAIN(2) J101 strip down to C101/C102 at the TPS2121 IN1
    In2  +5V   (1)  top arm (C202, U801, TPS2121 OUT), link column, bottom arm (C206, J701 5 V pins),
                    tab beside the LDO for the top-side trunk vias
    In2  +3V3  (0)  whole board, background
  +5V_LED  1 mm ring on B.Cu at r 28.7 (outside the WS2812 DOUT pads, which share the VDD radius),
           a 0.5 mm stub to each VDD pad, two vias from U801/C815, one via up to U802/C816.
  Top-layer traces
    +5V      trunk at x 131.2 from two vias in the +5V bottom arm up to U502/C508; branches to
             U602/C604 (y 85.5), D601/C605 (y 119.0); R205 from a via in the top arm; J701 1/23 vias.
    +5V_AMP  U502 VOUT/QOD -> C511 -> C510 -> C509 -> U503 pins 7/8; R511.
    +1V8     LDO -> J701 pin 3; LDO -> x 133.5 -> y 86.36 (between U602 and R704/R705) -> J301 pin 1;
             LDO -> via -> B.Cu -> C317 -> pin 31; B.Cu branch -> via -> R303.
             Pins 26/17 get their cap links (C316; C315, C318) only: joining them to the rest goes
             through the XVF fan-out under the ESP32 module, so it waits for the routing pass.

Usage (PCB editor closed):  python3 tools/power_planes_2026_11_18.py [--out FILE]
"""
import math
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, LEFT, RIGHT, TOP, BOTTOM, Part, bbox  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

CX, CY = 146.558, 98.679          # board centre = LED ring centre
RING_R = 28.7                     # ring track radius (VDD/DOUT pads end at r 27.92)
RING_W = 1.0
VIA = (0.6, 0.3)                  # Power class via

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p
items = []


def uid():
    return q(str(uuid.uuid4()))


def f6(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def seg(a, b, w, layer, net):
    items.append(["segment", ["start", f6(a[0]), f6(a[1])], ["end", f6(b[0]), f6(b[1])], ["width", f6(w)],
                  ["layer", q(layer)], ["net", q(net)], ["uuid", uid()]])


def path(pts, w, net, layer="F.Cu"):
    for a, b in zip(pts, pts[1:]):
        seg(a, b, w, layer, net)


def arc(a, m, b, w, layer, net):
    items.append(["arc", ["start", f6(a[0]), f6(a[1])], ["mid", f6(m[0]), f6(m[1])], ["end", f6(b[0]), f6(b[1])],
                  ["width", f6(w)], ["layer", q(layer)], ["net", q(net)], ["uuid", uid()]])


def via(pt, net):
    items.append(["via", ["at", f6(pt[0]), f6(pt[1])], ["size", f6(VIA[0])], ["drill", f6(VIA[1])],
                  ["layers", q("F.Cu"), q("B.Cu")], ["net", q(net)], ["uuid", uid()]])


def zone(net, layer, pts, priority):
    z = ["zone", ["net", q(net)], ["layer", q(layer)], ["uuid", uid()], ["name", q(f"{net} {layer}")],
         ["hatch", "edge", "0.5"]]
    if priority:
        z.append(["priority", str(priority)])
    z += [["connect_pads", ["clearance", "0.3"]], ["min_thickness", "0.25"], ["filled_areas_thickness", "no"],
          ["fill", "yes", ["thermal_gap", "0.5"], ["thermal_bridge_width", "0.5"], ["island_removal_mode", "0"]],
          ["polygon", ["pts"] + [["xy", f6(x), f6(y)] for x, y in pts]]]
    items.append(z)


def pad_c(ref, pin):
    for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
        if str(pd[1]) == str(pin):
            b = bbox(poly)
            return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    raise KeyError(f"{ref}.{pin}")


def on_ring(deg, r=RING_R):
    a = math.radians(deg)
    return (CX + r * math.cos(a), CY + r * math.sin(a))


# ================================================================ zones
board = [(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM)]
zone("GND", "In1.Cu", board, 0)
zone("+3V3", "In2.Cu", board, 0)
zone("+5V", "In2.Cu", [(152.3, 109.8), (170.7, 109.8), (170.7, 114.75), (164.3, 114.75), (164.3, 130.2),
                       (130.5, 130.2), (130.5, 115.5), (134.3, 115.5), (134.3, 119.8), (146.2, 119.8),
                       (146.2, 122.0), (158.9, 122.0), (158.9, 113.4), (152.3, 113.4)], 1)
zone("VBUS_MAIN", "In2.Cu", [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 112.6),
                             (172.8, 112.6), (172.8, 103.5), (170.8, 103.5)], 2)
zone("VBUS_ESP", "In2.Cu", [(114.6, 94.8), (122.3, 94.8), (122.3, 103.5), (118.9, 103.5), (118.9, 130.5),
                            (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)], 3)
zone("+0V9", "In2.Cu", [(142.3, 94.4), (150.9, 94.4), (150.9, 108.6), (151.8, 108.6), (151.8, 113.7),
                        (158.8, 113.7), (158.8, 121.7), (146.4, 121.7), (146.4, 103.0), (142.3, 103.0)], 4)

# ================================================================ +5V_LED ring on B.Cu
NET = "+5V_LED"
junctions = []                                    # (angle, kind)
for i in range(1, 13):
    ref = f"D8{i:02d}"
    px, py = pad_c(ref, 4)                         # VDD pad
    ang = math.degrees(math.atan2(py - CY, px - CX))
    junctions.append((ang, ("stub", (px, py))))
FEED = [49.6, 51.8]                                # two vias fed from U801 / C815 (top side)
U802_FEED = -36.0                                  # one via up to U802 / C816
for a in FEED:
    junctions.append((a, ("via", None)))
junctions.append((U802_FEED, ("via", None)))
junctions.sort(key=lambda j: j[0])
for k, (ang, (kind, pad)) in enumerate(junctions):
    pt = on_ring(ang)
    if kind == "stub":
        seg(pad, pt, 0.5, "B.Cu", NET)
    else:
        via(pt, NET)
    a2 = junctions[(k + 1) % len(junctions)][0]
    if a2 <= ang:
        a2 += 360
    arc(pt, on_ring((ang + a2) / 2), on_ring(a2), RING_W, "B.Cu", NET)
# top side: C815 / U801 VOUT -> the two feed vias
v1, v2 = on_ring(FEED[1]), on_ring(FEED[0])
c815 = pad_c("C815", 1)
path([pad_c("U801", 6), (c815[0], pad_c("U801", 6)[1])], 0.6, NET)          # VOUT pin 6 -> above C815
path([(c815[0], pad_c("U801", 6)[1]), c815, (c815[0], 118.3), (c815[0] + 2.53, 120.83), v1], RING_W, NET)
seg(v1, v2, RING_W, "F.Cu", NET)
seg(pad_c("U801", 5), pad_c("U801", 6), 0.3, "F.Cu", NET)                    # QOD pin 5 to VOUT pin 6
# top side: ring via -> C816 -> U802 pin 5
vu = on_ring(U802_FEED)
c816 = pad_c("C816", 1)
path([vu, (c816[0] + 0.9, c816[1]), c816], 0.5, NET)
seg(c816, (pad_c("U802", 5)[0] + 0.25, pad_c("U802", 5)[1]), 0.3, "F.Cu", NET)

# ================================================================ +5V on top
NET = "+5V"
TX = 131.2                                         # trunk x
# vias into the +5V tab beside the LDO: inside the LED ring (r < 23.5), clear of the B.Cu ring
va, vb = (TX, 116.2), (TX + 1.2, 116.2)
via(va, NET)
via(vb, NET)
seg(vb, va, 1.0, "F.Cu", NET)
u502 = pad_c("U502", 1)
path([(TX, 119.0), (TX, u502[1])], 1.0, NET)
seg((TX, u502[1]), u502, 0.6, "F.Cu", NET)                                  # also over C508 pad 1
# U602 / C604 branch
c604 = pad_c("C604", 1)
path([(TX, 85.5), (143.6, 85.5), (143.6, c604[1]), c604, (pad_c("U602", 5)[0], 83.3)], 0.5, NET)
# D601 / C605 branch
c605 = pad_c("C605", 1)
path([(TX, 119.0), (c605[0], 119.0), c605, pad_c("D601", 4)], 0.4, NET)
# R205 (power LED) from a via in the +5V top arm
vr = (167.4, 110.3)                                # clear of C812 (ring cap) on B.Cu
via(vr, NET)
r205 = pad_c("R205", 2)
path([vr, (176.8, 110.3), (176.8, r205[1]), r205], 0.4, NET)
# J701 +5V pins 1 and 23: a via between the header's two pad rows (outside the LED ring)
for pin in (1, 23):
    c = pad_c("J701", pin)
    v = (c[0], 129.61)
    via(v, NET)
    seg(v, (c[0], 128.0), 0.8, "F.Cu", NET)

# ================================================================ +5V_AMP on top
NET = "+5V_AMP"
p6, p5 = pad_c("U502", 6), pad_c("U502", 5)
seg(p6, p5, 0.6, "F.Cu", NET)                                                 # VOUT and QOD
c511 = pad_c("C511", 1)
path([p6, (138.2, p6[1]), (c511[0] - 0.05, 79.35)], 0.8, NET)              # -> C511 pad 1
c510 = pad_c("C510", 1)
seg((c511[0] - 0.1, c511[1]), (c510[0], c510[1]), 0.6, "F.Cu", NET)         # C511 -> C510
path([(c510[0], 76.0), (136.5, 76.0)], 0.6, NET)                            # C510 -> U503 pins 7/8
c509 = pad_c("C509", 1)
seg(c509, (c509[0], 76.0), 0.4, "F.Cu", NET)
seg(pad_c("R511", 2), (135.95, 80.45), 0.3, "F.Cu", NET)                    # R511 (SD_MODE pull-up)

# ================================================================ +1V8
NET = "+1V8"
ldo = pad_c("U203", 5)
c209 = pad_c("C209", 1)
seg(ldo, (ldo[0] - 0.47, c209[1] - 0.2), 0.4, "F.Cu", NET)                # pin 5 -> C209
# LDO -> J701 pin 3
j3 = pad_c("J701", 3)
path([c209, (c209[0], 122.8), (j3[0], 122.8), (j3[0], 125.9)], 0.3, NET)
# LDO -> up the left of the module -> J301 pin 1; and the drop to the XVF3800
vx = (140.3, 110.9)
path([ldo, (138.2, ldo[1]), (138.2, 111.2)], 0.4, NET)
seg((138.2, 111.2), vx, 0.4, "F.Cu", NET)
via(vx, NET)
j301 = pad_c("J301", 1)
path([(138.2, 111.2), (133.5, 111.2), (133.5, 86.36), (158.5, 86.36), (158.5, 73.5), (j301[0], 73.5),
      (j301[0], 71.6)], 0.3, NET)
# B.Cu: via -> C317 -> pin 31
c317 = pad_c("C317", 1)
path([vx, (c317[0], 108.0), c317], 0.3, NET, "B.Cu")
seg(c317, (pad_c("U301", 31)[0] - 0.1, c317[1]), 0.2, "B.Cu", NET)
# B.Cu branch west -> via -> R303 (TPS3808 RST pull-up)
vr3 = (122.0, 92.5)
path([(c317[0], 103.0), (128.0, 103.0), vr3], 0.25, NET, "B.Cu")
via(vr3, NET)
r303 = pad_c("R303", 2)
path([vr3, (120.3, r303[1]), r303], 0.25, NET)
# local cap links for pins 26 and 17 (joined to the rest in the routing pass)
p26, p17 = pad_c("U301", 26), pad_c("U301", 17)
path([(p26[0], p26[1]), (p26[0], 103.6), (pad_c("C316", 1)[0], 104.45)], 0.15, NET, "B.Cu")
path([(p17[0], p17[1]), (p17[0], 103.6), (pad_c("C315", 1)[0], 104.45)], 0.15, NET, "B.Cu")
seg(pad_c("C315", 1), pad_c("C318", 1), 0.3, "B.Cu", NET)

# ================================================================ write
existing = sum(1 for n in root if isinstance(n, list) and n and n[0] in ("segment", "arc", "via", "zone"))
if existing:
    sys.exit(f"board already has {existing} tracks/vias/zones; run on a cleared board")
root.extend(items)
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else BOARD
open(out, "w").write(dump(root) + "\n")
counts = {}
for n in items:
    counts[n[0]] = counts.get(n[0], 0) + 1
print("added", counts, "->", out)
