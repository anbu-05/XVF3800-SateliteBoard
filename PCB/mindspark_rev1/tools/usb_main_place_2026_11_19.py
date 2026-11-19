"""Placement for the XVF3800 main USB pair route (agreed with the user 2026-11-19).

The pair leaves XVF3800 pins 28/29 on B.Cu, runs east through a gap in the chip's east cap
column, goes up to F.Cu just outside the ESP32 module, passes under U702 through a gap below
it, crosses the open area and runs straight through U101 (ESD array) into J101.

  1. New footprints C323-C326 (stitching caps, from tools/sch_usb_stitch_2026_11_19.py), copies
     of C304 (100 nF 0402, bottom side) with their own schematic links and nets.
  2. U101 pad nets follow the schematic: D- on pads 4/7 (nearer the top of the board, the side
     it arrives on), D+ on pads 2/9.
  3. East cap column re-stacked (same x, same order, 0.15 mm courtyard gaps) round a copper-free
     band for the pair (pair centre y 100.88, 0.28/0.17 mm, 0.25 mm clear each side):
        north, from the band: C304, C323 (CA), C316, C319, C303, C315, C318 (C318 also 0.3 mm
        east, clear of crystal resistor R302);  south: C313, C324 (CB), C314.
  4. C325 (CC) / C326 (CD) either side of the layer-change vias just outside the module.
  5. U703 and U701 (flash switches) with C701 move down 0.35 mm, C703 1.0 mm, opening the F.Cu
     gap under U702.
  6. D101 (VBUS TVS) moves north of U101/R101 and turns so its VBUS pad stays over the In2
     VBUS_MAIN plane.

Tracks, vias and zones are left to tools/power_v2_2026_11_18.py and the route script.
Usage (PCB editor closed):  python3 tools/usb_main_place_2026_11_19.py [--dry-run]
"""
import copy
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part, overlap  # noqa: E402
from sexpr import parse, dump, children, child, walk, q  # noqa: E402

SHEET = "/0d465b1a-46e7-5808-b4ad-30de9111d093"          # xvf3800 sheet (as in C304's path)
NEW_CAPS = {  # ref: (symbol uuid in xvf3800.kicad_sch, pad 1 net, pad 2 net, use, pose)
    "C323": ("6dd173ef-e02b-5385-bf76-22aff565b1f4", "+0V9", "+1V8",
             "USB stitching CA: +0V9/+1V8 north of the main USB pair", (153.018, 98.88, 0.0)),
    "C324": ("1022b833-aa05-50c5-b836-48cd44a46590", "+0V9", "+1V8",
             "USB stitching CB: +0V9/+1V8 south of the main USB pair", (153.018, 102.88, 0.0)),
    "C325": ("ea7bb6ba-4dfa-5d36-b980-b24d4a85f2d6", "+1V8", "GND",
             "USB stitching CC: +1V8/GND north of the USB layer change", (157.65, 99.60, 0.0)),
    "C326": ("44584fe1-9df2-54d4-85c0-3d6fafc4b4a4", "+1V8", "GND",
             "USB stitching CD: +1V8/GND south of the USB layer change", (157.65, 102.60, 0.0)),
}
MOVES = {  # ref: (x, y, rotation)
    # east cap column, north of the pair
    "C304": (153.018, 99.95, 0.0), "C316": (153.018, 97.81, 0.0), "C319": (153.018, 96.74, 0.0),
    "C303": (153.018, 95.67, 0.0), "C315": (153.018, 94.60, 0.0), "C318": (153.335, 93.26, 0.0),
    # south of the pair
    "C313": (153.018, 101.81, 0.0), "C314": (153.035, 104.22, 0.0),
    # flash switches and their caps
    "U703": (160.909, 103.589, 0.0), "U701": (160.909, 107.139, 0.0),
    "C701": (163.569, 106.189, -90.0), "C703": (163.569, 103.289, -90.0),
    # VBUS TVS: north of U101, VBUS pad (1) at the bottom
    "D101": (171.983, 95.0, 90.0),
}
U101_NETS = {"2": "/USB_MAIN_DP", "9": "/USB_MAIN_DP", "4": "/USB_MAIN_DM", "7": "/USB_MAIN_DM"}

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p
if "C323" in P:
    sys.exit("C323 already on the board: nothing to do")


def prop(node, name):
    for p in children(node, "property"):
        if p[1] == name:
            return p
    return None


# 1. stitching cap footprints
for ref, (sym, n1, n2, use, pose) in NEW_CAPS.items():
    f = copy.deepcopy(P["C304"].node)
    for u in walk(f, "uuid"):
        u[1] = q(str(uuid.uuid4()))
    child(f, "path")[1] = q(f"{SHEET}/{sym}")
    prop(f, "Reference")[2] = q(ref)
    prop(f, "use")[2] = q(use)
    for pd in children(f, "pad"):
        child(pd, "net")[1] = q(n1 if str(pd[1]) == "1" else n2)
    root.insert(root.index(P["C304"].node) + 1, f)
    P[ref] = Part(f)
    P[ref].place(*pose)

# 2. U101 pad nets
for pd in children(P["U101"].node, "pad"):
    if str(pd[1]) in U101_NETS:
        child(pd, "net")[1] = q(U101_NETS[str(pd[1])])
        pf = child(pd, "pintype")
        if pf and str(pf[1]) == "free":
            pf[1] = q("passive")

# 3-6. moves
for ref, pose in MOVES.items():
    P[ref].place(*pose)


def shapes(ref):
    p = P[ref]
    return ([p.courtyard()] if p.local_box("CrtYd") else []) + p.pads()


clash = []
for g in list(NEW_CAPS) + list(MOVES):
    for ref, p in P.items():
        if ref == g:
            continue
        if p.side != P[g].side and not ref.startswith(("J10", "H", "SW", "MK")):
            continue
        other = shapes(ref) if p.side == P[g].side else p.pads(only_th=True)
        if any(overlap(s, o) for s in shapes(g) for o in other):
            clash.append("/".join(sorted((g, ref))))
print("overlaps:", sorted(set(clash)) or "none")
if "--dry-run" not in sys.argv:
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)
