"""Power copper, version 2 (2026-11-18), after the XVF3800 rotation (tools/xvf_rotate_2026_11_18.py).

Rebuilds all tracks, vias and zones from scratch:

  Zones (fill priority: higher fills first, lower keeps clearance from it)
    In1  GND          whole board
    In2  +1V8   (5)   east band x 149.75-160 (since 2026-11-22 under all the XVF3800's east pins,
                      the east cap column and the USB exit, so the straight USB pair crosses no plane
                      edge) + a leg to C317 (pin 31) and a notch north to C318 by the LDO
    In2  +0V9   (4)   island under the XVF3800, ending at x 149.45 behind the east pins (2026-11-22),
                      a 1.8 mm neck through the south cap row
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
  Fixed signal routes are laid first, before any power copper, so a rerun keeps them and the
    power router avoids them: since 2026-11-19 the XVF3800 main USB pair
    (tools/usb_main_route_2026_11_19.py), since 2026-11-20 the mic routes (tools/mic_route_2026_11_20.py),
    since 2026-11-21 the east-side escape (crystal, QSPI flash, JTAG fan-out; its cap column feeds
    re-laid 2026-11-22 in tools/east_column_2026_11_22.py), JTAG on to J301 / R703
    (tools/jtag_route_2026_11_21.py), I2S to the amp + the MCLK loop
    (tools/i2s_mclk_route_2026_11_21.py), and since 2026-11-22 the flash switches west of the
    module (tools/prog_switch_route_2026_11_22.py) and the ESP32 USB pair
    (tools/esp_usb_route_2026_11_22.py; the +5V trunk passes under it on a short B.Cu strap,
    HOP_5V_*).
  Since 2026-11-22 the group 1 local hookups (tools/local_hookups_2026_11_22.py: buck switch
    nodes and feedback, mic last links and supply filters, U103 setting parts, USB CC, speaker
    output, button/LED locals) are laid after the U103 flanges and before the vias in pads.

Not done here (left for the signal routing pass): XVF3800 +0V9/+3V3 pin fan-out to their caps
on the west and south sides (those caps sit over the wrong plane for a via), C314 (+3V3 over the
+1V8 band), the power test pads. The east side's pin feeds are fixed routes since 2026-11-21.

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
# Test pads (2026-11-22, user): placed by this script after everything else is routed, next to
# their net's copper (tools/test_pad_place_2026_11_22.py), so they never get in the way of other
# routes. Until then they are left out of every pass.
import test_pad_place_2026_11_22 as tpp  # noqa: E402
# Since 2026-11-22 (user's hand edits, tools/user_edits_2026_11_22.py): every signal net is frozen
# as the user drew it (user_routing_2026_11_22.json) and laid before any power copper; the signal
# passes below skip those nets (FROZEN). The test pads then stay at the user's spots like any part.
import user_edits_2026_11_22 as ue  # noqa: E402
import led_arcs_2026_11_22 as led_arcs  # noqa: E402
SNAP = ue.load()
FROZEN = SNAP[2] if SNAP else set()
TP_PARTS = {} if SNAP else {r: P.pop(r) for r in tpp.TEST_PADS if r in P}
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
    # VBUS_MAIN: notched for that finger; the strip below it (y 115.25-117.2) takes the pin-7 vias.
    # Since 2026-11-23 (tools/plane_necks_2026_11_23.py) the west edge runs at x 170.8 down to
    # y 108.3 and back to x 172.8 at 45 degrees, round the row of LED-ring crossing vias.
    ("VBUS_MAIN", "In2.Cu", 2, [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 115.25),
                                (173.3, 115.25), (173.3, 112.6), (172.8, 112.6), (172.8, 110.3), (170.8, 108.3)]),
    # VBUS_ESP: since 2026-11-23 the step under J102 is a 45-degree chamfer (wider strip entrance)
    ("VBUS_ESP", "In2.Cu", 3, [(114.6, 94.8), (122.3, 94.8), (122.3, 104.5), (118.9, 107.9), (118.9, 130.5),
                               (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)]),
    ("+0V9", "In2.Cu", 4, [(142.3, 94.4), (149.45, 94.4), (149.45, 103.0), (148.8, 103.0), (148.8, 113.7),
                           (158.8, 113.7), (158.8, 121.7), (147.0, 121.7), (147.0, 103.0),
                           # lobe under C306 (2026-11-22): its pin 42 is fenced in by the MIC_CLK and
                           # MCLK vias, so the cap takes a via in its pad into the island instead;
                           # wide above y 104 so the fill flows round those two vias' clearance, narrow
                           # below so C311's +3V3 via keeps its plane
                           (146.2, 103.0), (146.2, 104.0), (145.6, 104.0), (145.6, 105.1),
                           (144.35, 105.1), (144.35, 103.0),
                           (142.3, 103.0),
                           # west lobe under C308 (2026-11-22): the cap takes a via in its pad
                           # instead of a trace to pin 57, which frees room for the GPO escapes
                           # (down to y 98.1 so the fill gets round below the GPO_R via's clearance;
                           #  the slow INT_N / SQ_NLIN lines run over it)
                           (142.3, 98.1), (140.1, 98.1), (140.1, 96.65), (142.3, 96.65)]),
    ("+1V8", "In2.Cu", 5, [(149.75, 93.9), (157.6, 93.9), (157.6, 92.5), (160.0, 92.5), (160.0, 106.3),
                           (148.9, 106.3), (148.9, 103.3), (149.75, 103.3)]),
]
for net, layer, pri, pts in ZONES:
    z = ["zone", ["net", q(net)], ["layer", q(layer)], ["uuid", uid()], ["name", q(f"{net} {layer}")],
         ["hatch", "edge", "0.5"]]
    if pri:
        z.append(["priority", str(pri)])
    # 0.2 mm to other-net copper since 2026-11-23 (was 0.3): smaller via holes, wider necks
    z += [["connect_pads", ["clearance", "0.2"]], ["min_thickness", "0.25"], ["filled_areas_thickness", "no"],
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

# ================================================================ user's signal copper (2026-11-22)
if SNAP:
    # two of the user's vias move inward out of the LED arcs' band (tools/led_arcs_2026_11_22.py NUDGES)
    SNAP = led_arcs.nudge(list(SNAP[0]), list(SNAP[1])) + (SNAP[2],)
    # mic pad rows moved out to +-0.8375 mm (2026-11-23, tools/mic_pads_2026_11_23.py): the user's
    # DATA/CLK routes are re-ended on the new pad centres before they are laid
    import mic_pads_2026_11_23 as mic_pads  # noqa: E402
    SNAP = (mic_pads.reconnect(SNAP[0], log=report), SNAP[1], SNAP[2])
    # R407 (flash HOLD# pull-up, 2026-11-23): the D3 via moves onto its pad 2
    import flash_pullup_2026_11_23 as flash_pullup  # noqa: E402
    SNAP = flash_pullup.nudge(SNAP[0], SNAP[1], log=report) + (SNAP[2],)
    for kind_, net_, lay_, w_, pts_ in SNAP[0]:
        if kind_ == "arc":
            arc(pts_[0], pts_[1], pts_[2], w_, lay_, net_)
        else:
            seg(pts_[0], pts_[1], w_, lay_, net_, connect=False)
    for net_, at_, size_ in SNAP[1]:
        via(at_, net_, size_, connect=False)
    report.append(f"user's signal copper: {len(SNAP[0])} tracks, {len(SNAP[1])} vias, {len(FROZEN)} nets")
# C802 / C807 +5V_LED joins as the user drew them (bottom layer out of the cap, a top-layer hop,
# down onto the ring), so they leave the next LED's DIN free
for ref_, hop_ in ue.CAP_HOPS.items():
    for lay_, pts_ in hop_["runs"]:
        for a_, b_ in zip(pts_, pts_[1:]):
            seg(a_, b_, 0.3, lay_, "+5V_LED")
    for pt_ in hop_["vias"]:
        via(pt_, "+5V_LED", VIA_SMALL, connect=True)
    connected.setdefault("+5V_LED", []).append(pad_shape[(ref_, "1")])


# ================================================================ fixed signal routes (laid first)
# The XVF3800 main USB pair (tools/usb_main_route_2026_11_19.py). This script rebuilds every
# track, so the pair is laid here, before any power copper, and the power router avoids it.
import usb_main_route_2026_11_19 as usb_main  # noqa: E402

for net, layer, pts in usb_main.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, usb_main.W, layer, net, connect=False)
for pt, net in usb_main.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, usb_main.VIA, connect=False)
# U101's GND pads 8 and 3 sit between D- and D+ (flow-through): a small via just west of pad 8, between
# the two lines where they are 0.75 mm apart (0.15 mm each side), linked to pads 8 and 3
via((173.2, 98.68), "GND", VIA_SMALL)
seg((173.2, 98.68), (173.825, 98.68), 0.25, "F.Cu", "GND")
seg((173.825, 98.68), (174.595, 98.68), 0.25, "F.Cu", "GND")
# The mic routes (since 2026-11-20, tools/mic_route_2026_11_20.py, geometry frozen in its JSON):
# MIC_DATA0-3 and the buffered clock to the four mics, laid before any power copper.
import mic_route_2026_11_20 as mic  # noqa: E402

if not mic.TRACKS:
    sys.exit("mic routes missing: run tools/mic_route_2026_11_20.py --generate first")
for net, layer, pts in mic.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, mic.W, layer, net, connect=False)
for pt, net in mic.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, mic.VIA, connect=False)
# The east-side escape (since 2026-11-21, tools/east_escape_2026_11_21.py, geometry frozen in its JSON):
# east cap column feeds, JTAG fan-out, crystal, QSPI flash, +0V9 jumpers. Vias that land in their
# own plane count as joined (the +0V9 island via for C324); the rest are signal or jumper vias.
import east_column_2026_11_22 as east  # noqa: E402   (east escape with the 2026-11-22 column feeds)

if not east.TRACKS:
    sys.exit("east escape missing: run tools/east_escape_2026_11_21.py --generate first")
for net, layer, w, pts in east.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, w, layer, net, connect=False)
for pt, net in east.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, east.VIA)
# JTAG from those lanes to J301, and RST_N to R703 (since 2026-11-21, tools/jtag_route_2026_11_21.py)
import jtag_route_2026_11_21 as jtag  # noqa: E402

for net, layer, pts in jtag.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, jtag.W, layer, net, connect=False)
for pt, net in jtag.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, jtag.VIA, connect=False)
# I2S XVF3800 -> U503 amp, the MCLK loop 14 <-> 41, BTN_MUTE_N's via (since 2026-11-21,
# tools/i2s_mclk_route_2026_11_21.py); the amp's power copper below is routed round them.
import i2s_mclk_route_2026_11_21 as i2s  # noqa: E402

for net, layer, pts in i2s.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, i2s.W, layer, net, connect=False)
for pt, net in i2s.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, i2s.VIA, connect=False)
# Flash switches west of the module (since 2026-11-22, tools/prog_switch_route_2026_11_22.py):
# flash branch lines, PRG_* lines (bottom-layer hops), the PRG_EN chain.
import os as _os  # noqa: E402
if _os.path.exists(_os.path.join(_os.path.dirname(__file__), "prog_switch_route_2026_11_22.json")):
    import prog_switch_route_2026_11_22 as prog  # noqa: E402
    for net, layer, w, pts in prog.TRACKS:
        if net in FROZEN:
            continue
        for a, b in zip(pts, pts[1:]):
            seg(a, b, w, layer, net, connect=False)
    for pt, net in prog.VIAS:
        if net in FROZEN:
            continue
        via(pt, net, prog.VIA, connect=False)
# ESP32 USB pair J102 -> U102 -> R606/R605 -> ESP32 pins 13/14 (since 2026-11-22,
# tools/esp_usb_route_2026_11_22.py): top layer all the way, J102 A/B jumpers on the bottom layer.
import esp_usb_route_2026_11_22 as esp_usb  # noqa: E402

for net, layer, pts in esp_usb.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, esp_usb.W, layer, net, connect=False)
for pt, net in esp_usb.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, esp_usb.VIA, connect=False)
# U102's GND pins 3 and 8 sit between D- and D+ (flow-through, as U101): a small via just east of
# pin 8, between the lines while they are still 1 mm apart, linked to pins 8 and 3
via(esp_usb.U102_GND_VIA, "GND", VIA_SMALL)
for a, b in zip(esp_usb.U102_GND, esp_usb.U102_GND[1:]):
    seg(a, b, 0.25, "F.Cu", "GND")

# ================================================================ explicit vias
VIA_5V_A, VIA_5V_B = (131.2, 116.2), (132.4, 116.2)      # +5V tab beside the old LDO spot -> trunk
# +1V8 band -> F.Cu east of the module, for J701: south of the USB pair, since F.Cu cannot cross
# the pair (2026-11-19; was one via at 157.6, 99.3). J301 and R303 find +1V8 north of the pair.
VIA_1V8_S = (158.4, 103.6)
# +1V8 to R303: B.Cu under the +5V trunk, the NW mic lanes and PRG_EN (moved 2026-11-22 for the
# flash-switch block west of the module)
HOP1, HOP2 = (134.0, 86.5), (122.4, 88.6)
# +3V3 for the SW mic's ferrite FB503 (2026-11-20): FB503 sits over In2 VBUS_ESP, between the SW mic
# pair's F.Cu legs, which cut off its old F.Cu feed from the east. Between the legs, east of the
# VBUS_ESP edge (x 118.9), In2 is +3V3: one via there, a short F.Cu feed to FB503 pad 1.
VIA_3V3_FB503 = (119.6, 126.0)
# +3V3 for J701 pin 2 (breakout header, east end; 2026-11-20): it used to join FB504's +3V3 feed,
# which the SE mic pair's F.Cu legs now cut off. In2 under J701 is +5V / VBUS_ESP; the nearest
# +3V3 plane is east of the VBUS_ESP strip (x > 170.7): one via there, F.Cu west to the pin.
VIA_3V3_J701 = (171.3, 133.0)
for pt, net in ((VIA_5V_A, "+5V"), (VIA_5V_B, "+5V"), (VIA_1V8_S, "+1V8"),
                (HOP1, "+1V8"), (HOP2, "+1V8"), (VIA_3V3_FB503, "+3V3"), (VIA_3V3_J701, "+3V3")):
    via(pt, net)
seg(VIA_5V_A, VIA_5V_B, 1.0, "F.Cu", "+5V")                 # the trunk's two vias side by side
# +5V trunk under the ESP32 USB pair (2026-11-22): the pair runs east on the top layer across the
# whole board, so the trunk drops to the bottom layer for 2.4 mm to pass under it. Two 0.6/0.3 vias
# each side (side by side, F.Cu bars), a 1.8 mm B.Cu strap. At x 127.6 the bottom layer has no mic
# lines (user: the trunk must not run where a mic line is on the bottom layer); MIC_DATA2 and the
# mic clock's bottom-layer diagonals are >= 1 mm east of the strap.
HOP_5V_N = [(127.0, 109.6), (128.2, 109.6)]                # north of the pair (D- at y 110.65)
HOP_5V_S = [(127.0, 112.0), (128.2, 112.0)]                # south of the pair (D+ at y 111.05)
# The trunk feeds the loads north of the pair (amp U502, C508, C604, U602) from the tab in the
# south, so the hop counts as joined: the first +5V route links the tab to the south vias, and the
# northern branches then start from the north vias.
for pt in HOP_5V_N + HOP_5V_S:
    via(pt, "+5V", connect=True)
seg(HOP_5V_N[0], HOP_5V_N[1], 1.0, "F.Cu", "+5V")
seg(HOP_5V_S[0], HOP_5V_S[1], 1.0, "F.Cu", "+5V")
seg((127.6, 109.6), (127.6, 112.0), 1.8, "B.Cu", "+5V")

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
    # (third via 0.07 mm further in since 2026-11-22: was (167.45, 116.5), 0.04 mm into the D802 LED arc's room)
    ("2", "VBUS_ESP", [(167.85, 115.75), (167.05, 115.75), (167.4, 116.45)],
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
# GND of the U103 divider bottoms (user 2026-11-22, tools/user_edits_2026_11_22.py GND_DIVIDER):
# one top-layer run along R106 / R110 / R112 to R108's in-pad via; those three pads get no via
if SNAP:
    for a_, b_ in zip(ue.GND_DIVIDER["run"], ue.GND_DIVIDER["run"][1:]):
        seg(a_, b_, 0.3, "F.Cu", "GND")
    FLANGED |= set(ue.GND_DIVIDER["pads"])
    # C301's GND: the via just inside the pad's north edge, clear of the TP401 stub (ue.C301_GND_VIA)
    via(ue.C301_GND_VIA, "GND", VIA_SMALL, connect=True)
    seg(ue.C301_GND_VIA, pad("C301", 2)[3], 0.45, "B.Cu", "GND")
    FLANGED.add(("C301", "2"))
    # R401's +3V3 end: one via in its pad down to In2 +3V3 (user 2026-11-22, ue.R401_VIA)
    via(ue.R401_VIA, "+3V3", VIA_SMALL, connect=True)
    connected.setdefault("+3V3", []).append(pad_shape[("R401", "2")])
    FLANGED.add(("R401", "2"))
    # R407's +3V3 end (flash HOLD# pull-up, 2026-11-23): a short bottom-layer run into U401's
    # VCC pad (pin 8). No via: the top layer above is the dense line field under the ESP32
    # module. The automatic pass skips the XVF3800 area, so it is laid here.
    for a_, b_ in zip(flash_pullup.PAD1_RUN, flash_pullup.PAD1_RUN[1:]):
        seg(a_, b_, 0.2, "B.Cu", "+3V3")
    connected.setdefault("+3V3", []).append(pad_shape[("R407", "1")])
    FLANGED.add(("R407", "1"))

# ================================================================ group 1: local hookups (2026-11-22)
# Short part-to-neighbour links (tools/local_hookups_2026_11_22.py), routed by the jog router
# after the fixed routes, explicit vias and U103 flanges, before the vias in pads and the
# power routes, so they get first pick next to their
# pads. All on the top layer.
import jog_router  # noqa: E402
import local_hookups_2026_11_22 as local  # noqa: E402


def pad_k(spec):
    """(ref, pin) or (ref, pin, k): polygon and Shape of the k-th pad with that number."""
    ref, pin = spec[0], str(spec[1])
    k = spec[2] if len(spec) > 2 else 0
    hits = [(i, x) for i, x in enumerate(pads_of(ref)) if x[0] == pin]
    i, x = hits[k]
    return x[2], pad_shape[(ref, pin, i)]


for net, layer, w_, pts in local.FIXED_TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, w_, layer, net)
for pt, net, size in local.FIXED_VIAS:
    if net in FROZEN:
        continue
    via(pt, net, size, connect=True)
# pads these hand-laid pieces join (so later routes may start from them)
for ref, pin in (("R108", 1), ("R110", 1), ("R112", 1), ("R109", 2), ("R105", 2), ("U302", 3), ("U302", 2)):
    connected.setdefault(pad(ref, pin)[1], []).append(pad_shape[(ref, str(pin))])

local_failed = []
for net, width, clr, goal, start in local.ROUTES:
    if net in FROZEN:
        continue
    jog_router.CLEARANCE = clr
    gpoly, gshape = pad_k(goal)
    starts = [pad_k(start)[1]] if start else list(connected.get(net, []))
    w, path = width, None
    while w >= 0.15 and path is None:
        path = router.route(net, "F.Cu", w, gpoly, starts)
        if path is None:
            w = round(w * 0.7, 2)
    if path is None:
        local_failed.append(f"{net} -> {goal}")
        continue
    for a, b in zip(path, path[1:]):
        seg(a, b, w, "F.Cu", net)
    connected.setdefault(net, [])
    connected[net] += starts + [gshape]
    if w < width:
        report.append(f"local {net} -> {goal}: narrowed to {w}")
report.append(f"local hookups: {len(local.ROUTES) - len(local_failed)}/{len(local.ROUTES)} routed"
              + (f"; FAILED {local_failed}" if local_failed else ""))

# ================================================================ group 2: XVF3800 escape (2026-11-22)
# Power fan-out and the south signal lanes (tools/xvf_escape_2026_11_22.py), bottom layer.
import xvf_escape_2026_11_22 as xvf_esc  # noqa: E402

for net, w_, pts in xvf_esc.TRACKS:
    if net in FROZEN:
        continue
    for a, b in zip(pts, pts[1:]):
        seg(a, b, w_, "B.Cu", net)
for pt, net, size in xvf_esc.VIAS:
    if net in FROZEN:
        continue
    via(pt, net, size, connect=True)
for ref, pin in xvf_esc.JOINED:
    connected.setdefault(pad(ref, pin)[1], []).append(pad_shape[(ref, str(pin))])
report.append(f"XVF escape: {len(xvf_esc.TRACKS)} hand-laid runs")


def escape_via(net, ref, pin, box):
    """Nearest spot in box where a 0.45/0.2 via fits (both layers clear) and the jog router
    reaches it from the pin on the bottom layer. Returns (spot, path) or None."""
    gpoly, gshape = pad_k((ref, pin))
    c = pad(ref, pin)[3]
    r = VIA_SMALL[0] / 2
    spots = [(round(box[0] + i * 0.1, 3), round(box[1] + j * 0.1, 3))
             for i in range(int((box[2] - box[0]) / 0.1) + 1) for j in range(int((box[3] - box[1]) / 0.1) + 1)]
    spots.sort(key=lambda t: math.dist(t, c))
    tried = 0
    for t in spots:
        if any(sh.net != net and sh.layers & {"F.Cu", "B.Cu"}
               and sh.dist(*t) < r + (0.2 if sh.net == "~hole" else 0.15) for sh in router.shapes):
            continue
        tried += 1
        if tried > 60:
            break
        n_items, n_shapes = len(items), len(router.shapes)
        via(t, net, VIA_SMALL, connect=False)
        vsh = via_shape[(round(t[0], 3), round(t[1], 3))]
        jog_router.CLEARANCE = 0.15
        path = router.route(net, "B.Cu", 0.15, gpoly, [vsh])
        if path is not None:
            return t, path, gshape
        del items[n_items:]
        del router.shapes[n_shapes:]
        new_vias.pop()
    return None


esc_failed = []
for net, (ref, pin), box in xvf_esc.ESCAPE:
    if net in FROZEN:
        continue
    got = escape_via(net, ref, pin, box)
    if got is None:
        esc_failed.append(f"{ref}.{pin} {net}")
        continue
    t, path, gshape = got
    for a_, b_ in zip(path, path[1:]):
        seg(a_, b_, 0.15, "B.Cu", net)
    report.append(f"escape {ref}.{pin:3s} {net:16s} via {t} ({len(path) - 1} segments)")
report.append("escape vias: " + (f"FAILED {esc_failed}" if esc_failed else "all placed"))

# ================================================================ LED chain links (2026-11-22)
# Arcs along the +5V_LED ring (tools/led_arcs_2026_11_22.py), laid after every fixed piece and
# before any generated power copper: each link's shape is searched to clear what is laid so far,
# and the power routes after it (the LED caps' joins among them) go round it.
led_bad = []
for net_, pieces_, how_ in led_arcs.links(lambda r_, p_: pad(r_, p_)[3], router.shapes):
    if how_ is None:
        led_bad.append(net_)
    for pc_ in pieces_:
        if pc_[0] == "arc":
            items.append(["arc", ["start", f4(pc_[1][0]), f4(pc_[1][1])], ["mid", f4(pc_[2][0]), f4(pc_[2][1])],
                          ["end", f4(pc_[3][0]), f4(pc_[3][1])], ["width", f4(led_arcs.W)], ["layer", q("B.Cu")],
                          ["net", q(net_)], ["uuid", uid()]])
            # clearance stand-in for the routers: short pieces along the arc at its true width
            pts_ = led_arcs.samples([pc_], step=0.3)
            for s_, e_ in zip(pts_, pts_[1:]):
                router.add(Shape(net_, {"B.Cu"}, seg=(s_, e_, led_arcs.W + 0.01)))
        else:
            seg(pc_[1], pc_[2], led_arcs.W, "B.Cu", net_, connect=False)
    report.append(f"LED link {net_}: " + (f"r {how_[0]}, dive ends {how_[1]} deg before DIN, spans {how_[2]} deg"
                                          if how_ else "NO CLEAR SHAPE (default laid)"))
FROZEN |= {f"Net-(D8{i:02d}-DOUT)" for i in range(1, 12)}
# Each LED's supply cap C8xx -> its VDD pad (bottom layer), routed here, before the vias in pads,
# so the GND vias beside the LED pads go round it (C802 / C807: the user's hops, laid above).
import jog_router  # noqa: E402
LED_CAPS = [i for i in range(1, 13) if f"C8{i:02d}" not in ue.CAP_HOPS]
led_cap_failed = []
for i in LED_CAPS:
    jog_router.CLEARANCE = 0.15
    goal_, start_ = pad(f"D8{i:02d}", 4)[2], pad_shape[(f"C8{i:02d}", "1")]
    w_, path_ = 0.3, None
    while w_ >= 0.15 and path_ is None:
        path_ = router.route("+5V_LED", "B.Cu", w_, goal_, [start_])
        if path_ is None:
            w_ = round(w_ * 0.7, 2)
    if path_ is None:
        led_cap_failed.append(f"C8{i:02d}")
        continue
    for a_, b_ in zip(path_, path_[1:]):
        seg(a_, b_, w_, "B.Cu", "+5V_LED")
    connected.setdefault("+5V_LED", []).extend([start_, pad_shape[(f"D8{i:02d}", "4")]])
report.append("LED cap joins: " + (f"FAILED {led_cap_failed}" if led_cap_failed else "all routed"))

# ================================================================ vias in pads
# User's rules (2026-11-19):
#   * vias sit on the pad centre; when a pad needs several, they form a pattern centred on the
#     pad centre (odd counts: one on the centre, the rest in mirror pairs along the long axis;
#     even counts: mirror pairs, none on the centre; a grid on big pads);
#   * the count follows the current the pad carries: 1 A per 0.6/0.3 via, 0.5 A per 0.45/0.2;
#   * if the centre is blocked (wrong plane, or another net's copper) the pad gets one small via
#     just beside it on a short stub (since 2026-11-22), and is routed only if there is no room;
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
        gap = 0.2 if sh.net == "~hole" else 0.15          # hole clearance rule is 0.2 (mic sound ports)
        if sh.net != net and sh.layers & {"F.Cu", "B.Cu"} and sh.dist(*pt) < r + gap:
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
                    and router._seg_clearance(c, pt, [sh for sh in router.shapes if sh.net not in (net, "~hole")
                                                      and layer in sh.layers], stub_w) >= 0.15
                    and router._seg_clearance(c, pt, [sh for sh in router.shapes if sh.net == "~hole"], stub_w) >= 0.2):
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
                # since 2026-11-22 (user): before routing a long trace, try one small via just
                # beside the pad on a short stub (e.g. LED-ring GND pads under the NW mic lanes,
                # the north cap row under the PRG band); GND always finds In1 there
                alt = beside_spots(c, w, h, VIA_SMALL, max(1, math.ceil(amps / VIA_AMPS[VIA_SMALL] - 1e-9)),
                                   net, p.side)
                if alt:
                    for pt, sw in alt:
                        via(pt, net, VIA_SMALL)
                        seg(c, pt, sw, p.side, net)
                    connected.setdefault(net, []).append(pad_shape[(ref, pin, pk)])
                    via_report.append((f"{ref}.{pin}", net, round(amps, 2), 0, len(alt), len(alt),
                                       f"centre blocked ({why}), via beside"))
                    continue
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
    # XVF3800 pin 31 (+1V8) to its cap; pins 17-27 are fixed routes since 2026-11-21
    # (pin 31 -> C317: hand-laid in tools/xvf_escape_2026_11_22.py since 2026-11-22)
    # R401 (QSPI CS pull-up) +3V3 end: the automatic pass skips the XVF3800 area
    # (with the user's edits: a via in its pad instead, laid just below)
] + ([] if SNAP else [("+3V3", "B.Cu", 0.2, ("R401", 2), 0.15, None)]) + [
    ("+3V3", "B.Cu", 0.2, ("C401", 1), 0.15, ("R401", 2)),     # flash decap, beside R401
    # amp supply
    ("+5V_AMP", "F.Cu", 0.8, ("C511", 1), 0.2, ("U502", 6)),
    ("+5V_AMP", "F.Cu", 0.6, ("C510", 1), 0.2, None),
    ("+5V_AMP", "F.Cu", 0.4, ("C509", 1), 0.2, None),
    ("+5V_AMP", "F.Cu", 0.25, ("U503", 7), 0.15, None),
    ("+5V_AMP", "F.Cu", 0.25, ("U503", 8), 0.15, None),
    ("+5V_AMP", "F.Cu", 0.4, ("U502", 5), 0.2, None),
    ("+5V_AMP", "F.Cu", 0.25, ("R511", 2), 0.2, None),
    # +5V trunk and branches
    # (since 2026-11-22: from the trunk tab up to the hop's south vias under the ESP32 USB pair;
    #  the branches below go on from the hop's north vias)
    ("+5V", "F.Cu", 1.0, ("@", HOP_5V_S[0]), 0.2, ("@", VIA_5V_A)),
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
    ("+1V8", "F.Cu", 0.3, ("J701", 3), 0.2, None),
    ("+1V8", "B.Cu", 0.3, ("@", HOP2), 0.2, ("@", HOP1)),
    ("+1V8", "F.Cu", 0.25, ("R303", 2), 0.2, ("@", HOP2)),
    # buck feedback tops / misc +3V3 pads that sit over another plane
    ("+3V3", "F.Cu", 0.3, ("C205", 1), 0.2, None),
    ("+3V3", "F.Cu", 0.3, ("FB503", 1), 0.2, ("@", VIA_3V3_FB503)),
    ("+3V3", "F.Cu", 0.3, ("J701", 2), 0.2, ("@", VIA_3V3_J701)),
    # TPS2121 divider tops (the input pins themselves are on their flanges, see above)
    # (VBUS_MAIN tops R109.2 / R105.2: hand-laid with the group 1 local hookups since 2026-11-22)
    ("VBUS_ESP", "F.Cu", 0.25, ("R107", 2), 0.15, None),
    # (R111.2: via in its pad since 2026-11-22; the group 1 mid links box it in)
] + [("+5V_LED", "B.Cu", 0.3, (f"C8{i:02d}", 1), 0.15, (f"D8{i:02d}", 4)) for i in range(1, 13)
     if not SNAP]                      # with the user's edits: routed after the LED arcs instead
# +1V8 to J301 pin 1 and on west to HOP1 (user's hand edit 2026-11-21, no U-turn round U802 / Q701):
# J301 now takes its +1V8 from the LDO output (U203 pin 5) past C318's pad (B.Cu north to a via
# beside U802, then F.Cu straight up
# past U802's west side); the HOP1 run starts from C209's in-pad via, straightened. Frozen here
# instead of routed, so a rerun keeps them.
V1V8_J301 = (159.1056, 91.3384)
HAND_1V8 = [
    ("B.Cu", [(158.5832, 96.0068), (158.825, 95.765), (158.825, 93.4), (158.825, 91.619), V1V8_J301]),  # from U203.5
    ("F.Cu", [V1V8_J301, (158.809, 91.0418), (158.809, 87.3237), (160.8903, 85.2424), (160.8903, 77.0007),
              (161.2912, 76.5997), (161.2912, 70.7989), (160.6913, 70.199)]),
    ("F.Cu", [(157.6832, 96.0068), (158.2082, 95.4818), (158.2082, 94.2082), (157.4, 93.4), (157.4, 88.7),
              (156.6, 87.9), (151.4, 87.9), (150.0, 86.5), HOP1]),  # ends on HOP1
]
via(V1V8_J301, "+1V8", VIA_SMALL, connect=True)
for layer, pts in HAND_1V8:
    for a, b in zip(pts, pts[1:]):
        seg(a, b, 0.3, layer, "+1V8")
connected.setdefault("+1V8", []).extend([pad_shape[("J301", "1")], via_shape[(round(HOP1[0], 3), round(HOP1[1], 3))]])
report.append("laid +1V8 to J301.1 and HOP1 by hand (user 2026-11-21)")

import jog_router  # noqa: E402

failed = []
for net, layer, width, tgt, clr, start in ROUTES:
    if net in FROZEN or (SNAP and net == "+5V_LED" and tgt[0] in ue.CAP_HOPS):
        continue
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


# ================================================================ group 3: fixed inter-IC signals (2026-11-22)
# Routed after all power copper (tools/inter_ic_2026_11_22.py) by tools/grid_router.py, which
# searches both layers at once and adds a via wherever a layer change pays (user's idea: out a
# little, then a via). The ESP32 underside keep-out for power traces does not apply to them.
import copy  # noqa: E402
import time as _time  # noqa: E402
import inter_ic_2026_11_22 as inter  # noqa: E402
import breakout_2026_11_22 as brk  # noqa: E402  (groups 4-6, same router, routed after group 3)
from grid_router import GridRouter  # noqa: E402

starts_of = {}                       # net -> [(layer, point)] laid so far by this group


def lay_runs(net, runs, first, last):
    """Lay the router's runs (vias between consecutive runs), from the exact start point to the
    exact goal point, and draw them into the grid."""
    def snap(pts, exact, at_start):
        """Move the run's end onto the exact point, sliding its neighbour so the first/last leg
        keeps its 0/45/90 direction (the grid is 0.1 mm, the points are not on it)."""
        if exact is None:
            return pts
        i, j = (0, 1) if at_start else (-1, -2)
        if len(pts) < 2:
            pts[i] = exact
            return pts
        (ax, ay), (bx, by) = pts[i], pts[j]
        dx, dy = exact[0] - ax, exact[1] - ay
        if abs(ay - by) < 1e-9:                   # horizontal leg: slide the neighbour in y
            pts[j] = (bx, by + dy)
        elif abs(ax - bx) < 1e-9:                 # vertical leg: slide it in x
            pts[j] = (bx + dx, by)
        else:                                     # diagonal leg: keep 45 degrees
            sx = 1 if bx > ax else -1
            sy = 1 if by > ay else -1
            # move the neighbour along the other axis so the leg stays at 45 degrees
            pts[j] = (bx + dx, by + dx * sx * sy) if abs(dx) >= abs(dy) else (bx + dy * sx * sy, by + dy)
        pts[i] = exact
        return pts

    pts_all = []
    for k, (L, pts) in enumerate(runs):
        pts = list(pts)
        if k == 0:
            pts = snap(pts, first, True)
        if k == len(runs) - 1:
            pts = snap(pts, last, False)
        n0 = len(router.shapes)
        for a_, b_ in zip(pts, pts[1:]):
            if math.dist(a_, b_) > 1e-6:
                seg(a_, b_, inter.W, L, net)
        if k < len(runs) - 1 and not any(v[2] == net and math.dist(v[0], pts[-1]) < 0.3 for v in new_vias):
            via(pts[-1], net, VIA_SMALL, connect=False)
        for sh in router.shapes[n0:]:
            grid.add(sh)
        pts_all += [(L, p_) for p_ in pts]
        if k < len(runs) - 1:
            pts_all += [(x, pts[-1]) for x in ("F.Cu", "B.Cu")]
    return pts_all


def route_group3(order):
    """Route the entries in this order on a fresh grid; returns (failed entries, report lines)."""
    global grid
    grid = GridRouter((LEFT, TOP, RIGHT, BOTTOM), router.shapes, width=inter.W, via_d=VIA_SMALL[0],
                      skip=lambda sh: sh.net == "~module")
    starts_of.clear()
    failed, lines = [], []
    for entry in order:
        net, goal, start = entry
        gref, gpin = goal
        gpd = pad(gref, gpin)
        g_layers = {"F.Cu", "B.Cu"} if gpd[5] == "thru_hole" else {P[gref].side}
        if start is None:
            st = list(starts_of.get(net, []))
        elif start == "*":
            # any copper the net already has: pad centres, track ends, via centres
            st = []
            gx_, gy_ = gpd[3]
            for sh in router.shapes:
                if sh.net != net:
                    continue
                if sh.poly and sh.box[0] <= gx_ <= sh.box[2] and sh.box[1] <= gy_ <= sh.box[3]:
                    continue                     # the goal pad itself is not a start
                lays = [L_ for L_ in ("F.Cu", "B.Cu") if L_ in sh.layers]
                if sh.seg:
                    pts_ = [sh.seg[0], sh.seg[1]]
                elif sh.circle:
                    pts_ = [sh.circle[0]]
                else:
                    pts_ = [((sh.box[0] + sh.box[2]) / 2, (sh.box[1] + sh.box[3]) / 2)]
                st += [(L_, p_) for L_ in lays for p_ in pts_]
        elif start[0] == "@":
            st = [(L, start[2]) for L in start[1]]
        else:
            st = [(P[start[0]].side, pad(*start)[3])]
        runs = grid.route(net, st, gpd[3], g_layers) if st else None
        if runs is None:
            failed.append(entry)
            continue
        first = min((p_ for L_, p_ in st if L_ == runs[0][0]), key=lambda p_: math.dist(p_, runs[0][1][0]),
                    default=None)
        laid = lay_runs(net, runs, first, gpd[3])
        starts_of.setdefault(net, []).extend(st + laid)
        connected.setdefault(net, []).append(pad_shape[(gref, str(gpin))])
        lines.append(f"routed {net:22s} -> {gref}.{gpin:3s} {' -> '.join(L_ for L_, _ in runs)} "
                     f"({len(runs) - 1} vias)")
    return failed, lines


# Rip-up and retry: if entries fail, undo the whole batch, put the failures first, route again.
# Group 3 goes first as its own batch (it routes in one pass in this order); groups 4-6 follow
# as a second batch whose retries never rip up group 3.
def route_batch(name, entries, passes):
    snap_items, snap_shapes, snap_vias = len(items), len(router.shapes), len(new_vias)
    snap_conn = {k: list(v) for k, v in connected.items()}
    order = list(entries)
    best = None                          # (failures, order) of the best pass so far
    for attempt in range(passes):
        _t0 = _time.time()
        failed, lines = route_group3(order)
        print(f"  {name} pass {attempt + 1}: {len(order) - len(failed)}/{len(order)} routed "
              f"in {_time.time() - _t0:.0f} s; failed {[f'{e[0]}->{e[1][0]}' for e in failed]}",
              file=sys.stderr, flush=True)
        if best is None or len(failed) < best[0]:
            best = (len(failed), list(order))
        if not failed:
            break
        if attempt == passes - 1:
            if len(failed) > best[0]:            # the last pass was not the best: lay the best again
                del items[snap_items:]
                del router.shapes[snap_shapes:]
                del new_vias[snap_vias:]
                connected.clear()
                connected.update({k: list(v) for k, v in snap_conn.items()})
                failed, lines = route_group3(best[1])
                print(f"  {name}: kept the best pass ({len(failed)} failed)", file=sys.stderr, flush=True)
            break
        del items[snap_items:]
        del router.shapes[snap_shapes:]
        del new_vias[snap_vias:]
        connected.clear()
        connected.update({k: list(v) for k, v in snap_conn.items()})
        # failures first, each with the rest of its net's entries right behind it
        fnets = []
        for e in failed:
            if e[0] not in fnets:
                fnets.append(e[0])
        order = [e for n_ in fnets for e in order if e[0] == n_] + [e for e in order if e[0] not in fnets]
    report.extend(lines)
    failed = [f"{e[0]} -> {e[1][0]}.{e[1][1]}" for e in failed]
    report.append(f"{name}: " + (f"FAILED {failed}" if failed else "all routed"))


route_batch("group 3", [e for e in inter.ROUTES[:7] + brk.EARLY + inter.ROUTES[7:] if e[0] not in FROZEN], 3)  # after the four hard nets
route_batch("groups 4-6", [e for e in brk.ROUTES if e[0] not in FROZEN], 3)


# ---------------------------------------------------------------- test pads (groups 5 and 6)
# With everything else routed, each test pad goes to the free spot closest to its net's copper
# (top or bottom), then joins it on a short stub. The chosen spots are also written to
# tools/test_pad_spots_2026_11_22.json for the record.
for r_, part in TP_PARTS.items():
    P[r_] = part
tp_net = {r_: pads_of(r_)[0][1] for r_ in TP_PARTS}
for r_ in TP_PARTS:
    del P[r_]
spots, taken, tp_lines, tp_failed = {}, [], [], []
for entry in (brk.TEST_PADS if TP_PARTS else []):     # none: pads frozen at the user's spots
    r_ = entry[1][0]
    part = TP_PARTS[r_]
    orig_node, orig_side = copy.deepcopy(part.node), part.side   # to put it back if no spot works
    cands = tpp.candidates(r_, tp_net[r_], router.shapes, P, (LEFT, TOP, RIGHT, BOTTOM), taken)
    for x_, y_, lay_, score_ in cands:
        if lay_ != str(part.side):
            if lay_ == "B.Cu":
                continue                          # (pads start on the bottom; never flipped back)
            part.flip_to_top()
            part.side = "F.Cu"
        snap_ = (len(items), len(router.shapes), len(new_vias), {k: list(v) for k, v in connected.items()})
        part.place(x_, y_)
        P[r_] = part
        for k_, (pin, net, poly, c, wh, kind) in enumerate(pads_of(r_)):
            sh = Shape(net, {lay_}, poly=poly)
            router.add(sh)
            pad_shape[(r_, pin, k_)] = sh
            pad_shape.setdefault((r_, pin), sh)
        failed_, lines_ = route_group3([entry])
        if not failed_:
            spots[r_] = [x_, y_, lay_, score_]
            taken.append((x_, y_, lay_))
            tp_lines += lines_
            print(f"  {r_:6s} -> ({x_:.3f}, {y_:.3f}) {lay_}  stub {score_:.2f} mm", file=sys.stderr, flush=True)
            break
        # the stub did not route: take the pad and anything laid back out, try the next spot
        del items[snap_[0]:]
        del router.shapes[snap_[1]:]
        del new_vias[snap_[2]:]
        connected.clear()
        connected.update(snap_[3])
        del P[r_]
    else:
        # no spot works: the pad stays where the board had it, as an obstacle, and is reported
        tp_failed.append(r_)
        part.node[:] = orig_node
        part.side = orig_side
        P[r_] = part
        for k_, (pin, net, poly, c, wh, kind) in enumerate(pads_of(r_)):
            router.add(Shape(net, {str(part.side)}, poly=poly))
if TP_PARTS:
    tpp.save(spots)
report += tp_lines
report.append("test pads: " + (f"NO SPOT {tp_failed}" if tp_failed else "all placed and joined"))


def split_t_junctions():
    """A route that starts on the middle of another track of its net (the router joins on a
    track's centre line) makes a T. KiCad flags such an end as dangling, so the run it lands on
    is cut in two at that point, and every T becomes an ordinary shared end point."""
    segs = [n for n in items if n[0] == "segment" and str(child(n, "net")[1]) not in FROZEN]
    ends = [(float(child(n, e)[1]), float(child(n, e)[2]), str(child(n, "layer")[1]), str(child(n, "net")[1]))
            for n in segs for e in ("start", "end")]
    for (px, py, lay, net) in ends:
        for n in [m for m in items if m[0] == "segment" and str(child(m, "net")[1]) not in FROZEN]:
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


def chamfer_power():
    """No right angles (user 2026-11-20): every 90 degree bend in the routed copper becomes two 45
    degree turns (jog_router.chamfer_corners), 0.2 mm from other nets. The fixed signal routes
    are left alone (the mic routes are chamfered in their own script); pad centres and vias stay."""
    fixed_nets = ({n for n, _, _ in usb_main.TRACKS} | {n for n, _, _ in mic.TRACKS}
                  | {n for n, _, _ in esp_usb.TRACKS} | FROZEN)
    keep = [n for n in items if n[0] != "segment" or str(child(n, "net")[1]) in fixed_nets]
    segs = [[str(child(n, "net")[1]), str(child(n, "layer")[1]),
             (float(child(n, "start")[1]), float(child(n, "start")[2])),
             (float(child(n, "end")[1]), float(child(n, "end")[2])), float(child(n, "width")[1])]
            for n in items if n[0] == "segment" and str(child(n, "net")[1]) not in fixed_nets]
    via_pts = {(round(v[0][0], 4), round(v[0][1], 4)) for v in new_vias}
    pad_polys = [(x[2], {"F.Cu", "B.Cu"} if x[5] in ("thru_hole", "np_thru_hole") else {P[ref].side})
                 for ref in P for x in pads_of(ref)]

    def fixed(net, layer, pt):
        return ((round(pt[0], 4), round(pt[1], 4)) in via_pts
                or any(layer in lays and _inside(pt[0], pt[1], poly) for poly, lays in pad_polys))
    n, left = jog_router.chamfer_corners(router, segs, fixed, 0.2)
    items[:] = keep + [["segment", ["start", f4(a[0]), f4(a[1])], ["end", f4(b[0]), f4(b[1])], ["width", f4(w)],
                        ["layer", q(lay)], ["net", q(net)], ["uuid", uid()]] for net, lay, a, b, w in segs]
    left = sorted(set((x[0], x[1], x[2], x[3]) for x in left))
    report.append(f"chamfered {n} right-angle bends; left as they are: {left or 'none'}")


chamfer_power()
split_t_junctions()
root.extend(items)
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else BOARD
open(out, "w").write(dump(root) + "\n")
counts = {}
for n in items:
    counts[n[0]] = counts.get(n[0], 0) + 1
print("\n".join(report))
print("added", counts, "->", out)

# GND pours on F.Cu / B.Cu and the 5 mm stitching-via grid (since 2026-11-22,
# tools/gnd_pour_2026_11_22.py). It works on the written board because it needs KiCad's fill to
# pick the via spots; this script strips every via and zone, so the pass must follow each rebuild.
import subprocess  # noqa: E402
subprocess.run([sys.executable, "-I", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                                     "gnd_pour_2026_11_22.py"), "--board", out], check=True)
