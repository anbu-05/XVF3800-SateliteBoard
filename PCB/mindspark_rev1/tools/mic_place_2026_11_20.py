"""Placement for the mic routes (approved by the user 2026-11-20).

  1. C312 0.2 mm north and C307 0.2 mm south: the gap between them grows from 0.6 to 1.0 mm so
     MIC_DATA3 and MIC_DATA1 (pins 51/50) pass straight between them at the pin pitch.
  2. C309 (10 uF, XVF3800 +0V9 bulk) leaves the fan-out west of the chip. It goes to the spot
     the clock buffer frees between the bucks, on the In2 +0V9 neck: its +0V9 pad sits over the
     neck (via in pad), its GND pad just west of it.
  3. Clock buffer group U501 / R501 / C501 moves to the top side, just west of the ESP32 module.
     The clock star (R501 pad 2) then runs on F.Cu over solid In1 GND, where no data line runs.
     U501 input (pin 2) faces south, where MIC_CLK arrives from XVF3800 pin 43; output (pin 4)
     faces north-east with R501 above it; C501 above pin 5 (+3V3).
  4. New footprint C515 (stitching cap +3V3 / +5V, from tools/sch_mic_stitch_2026_11_20.py), a
     copy of C501 on the bottom side, just east of the SE mic pair where it crosses from the
     In2 +3V3 plane to +5V (y 119.8; the pair runs at x 134.7 / 135.15 there, 2.5 mm clear of L202):
     +3V3 pad north of the edge, +5V pad south of it.

Tracks, vias and zones are left to tools/power_v2_2026_11_18.py and tools/mic_route_2026_11_20.py.
Usage (PCB editor closed):  python3 tools/mic_place_2026_11_20.py [--dry-run]
"""
import copy
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part, overlap  # noqa: E402
from sexpr import parse, dump, children, child, walk, q  # noqa: E402

SHEET = "/3f22dfb6-6fd6-54c4-9781-a982d7ddf190"          # audio sheet (as in C501's path)
C515_SYM = str(uuid.uuid5(uuid.NAMESPACE_URL, "mindspark_rev1/audio/C515"))
C515_POSE = (136.2, 119.8, 90.0)                           # checked below: pad 1 (+3V3) north

MOVES = {  # ref: (x, y, rotation)
    "C312": (140.098, 98.879, 180.0),
    "C307": (140.098, 100.479, 180.0),
    "C309": (147.2, 111.2, 180.0),
}
TO_TOP = {  # ref: (x, y, rotation) after flipping to the top side
    "U501": (134.6, 103.6, None),
    "R501": (135.55, 100.35, None),
    "C501": (133.65, 100.35, None),
}

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p
if "C515" in P:
    sys.exit("C515 already on the board: nothing to do")


def prop(node, name):
    for p in children(node, "property"):
        if p[1] == name:
            return p
    return None


def pad_centres(ref):
    out = {}
    for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
        xs, ys = [a for a, _ in poly], [b for _, b in poly]
        out[str(pd[1])] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    return out


# 4 (made first). stitching cap: a copy of C501 while C501 is still on the bottom side
f = copy.deepcopy(P["C501"].node)
for u in walk(f, "uuid"):
    u[1] = q(str(uuid.uuid4()))
child(f, "path")[1] = q(f"{SHEET}/{C515_SYM}")
prop(f, "Reference")[2] = q("C515")
prop(f, "use")[2] = q("Mic stitching: +3V3/+5V where the SE mic pair crosses planes (In2)")
for pd in children(f, "pad"):
    child(pd, "net")[1] = q("+3V3" if str(pd[1]) == "1" else "+5V")
root.insert(root.index(P["C501"].node) + 1, f)
P["C515"] = Part(f)

# 1-2. bottom-side moves
for ref, pose in MOVES.items():
    P[ref].place(*pose)

# 3. clock buffer group to the top side. Rotation is picked so the pins land where wanted:
#    U501 pin 2 south of the body, pin 4 north-east; R501 pad 1 south (to pin 4); C501 pad 1
#    south (+3V3, beside pin 5).
WANT = {"U501": lambda c: c["2"][1] > TO_TOP["U501"][1] and c["4"][1] < TO_TOP["U501"][1]
        and c["4"][0] > TO_TOP["U501"][0],
        "R501": lambda c: c["1"][1] > c["2"][1],
        "C501": lambda c: c["1"][1] > c["2"][1]}
for ref, (x, y, _) in TO_TOP.items():
    P[ref].flip_to_top()
    for rot in (0.0, 90.0, 180.0, -90.0):
        P[ref].place(x, y, rot)
        if WANT[ref](pad_centres(ref)):
            break
    else:
        sys.exit(f"no rotation puts {ref}'s pins where wanted")

# 4. stitching cap: placed above, from C501 while it was still on the bottom side
for rot in (90.0, -90.0):
    P["C515"].place(C515_POSE[0], C515_POSE[1], rot)
    c = pad_centres("C515")
    if c["1"][1] < c["2"][1]:
        break


def shapes(ref):
    p = P[ref]
    return ([p.courtyard()] if p.local_box("CrtYd") else []) + p.pads()


clash = []
for g in list(MOVES) + list(TO_TOP) + ["C515"]:
    for ref, p in P.items():
        if ref == g:
            continue
        if p.side != P[g].side and not ref.startswith(("J10", "H", "SW", "MK")):
            continue
        other = shapes(ref) if p.side == P[g].side else p.pads(only_th=True)
        if any(overlap(s, o) for s in shapes(g) for o in other):
            clash.append("/".join(sorted((g, ref))))
print("overlaps:", sorted(set(clash)) or "none")
for ref in list(MOVES) + list(TO_TOP) + ["C515"]:
    print(f"  {ref} {P[ref].side} " + " ".join(f"{k}:({v[0]:.3f},{v[1]:.3f})" for k, v in sorted(pad_centres(ref).items())))
if "--dry-run" not in sys.argv:
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)
