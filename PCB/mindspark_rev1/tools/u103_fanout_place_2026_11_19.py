"""Clear room round the TPS2121 (U103) for its power-pin via flanges (2026-11-19).

Agreed with the user: U103 stays where it is (its pins already sit where the VBUS_MAIN,
VBUS_ESP and +5V planes meet; the B.Cu LED ring under its east half is what blocks vias).
Each power pin gets a top-layer copper flange out to its own group of 0.6/0.3 vias
(tools/power_v2_2026_11_18.py builds those). This script only moves the small parts that sit
on the via spots, keeping each as close to its pin as it fits:

  C107 (+5V output bypass)    west of pin 1 -> north row, beside C105; its +5V pad gets a via
                               into the +5V plane, its GND pad a via to In1.
  C104 (VBUS_ESP bypass)      west of pin 2 -> further west, between C106 and C103, on the
                               pin-2 flange.
  C102 (VBUS_MAIN bypass)     east of pin 7 -> south-east, standing up, its VBUS_MAIN pad on
                               the pin-7 flange.
  R105-R112 (OV/PR dividers)  down 0.5 mm, so the pin-2 and pin-7 vias clear their top pads.

Tracks, vias and zones are not touched here; tools/power_v2_2026_11_18.py rebuilds them.
Usage (PCB editor closed):  python3 tools/u103_fanout_place_2026_11_19.py [--dry-run]
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part, overlap  # noqa: E402
from sexpr import parse, dump, children  # noqa: E402

# New poses (x, y, rotation). Rotation 90 puts pin 1 at +y, -90 at -y, 180 at +x.
MOVES = {
    "C107": (167.55, 112.0, 90.0),     # pin 1 (+5V) at y 112.48, pin 2 (GND) at y 111.52
    "C104": (165.6, 115.3, 180.0),     # pin 1 (VBUS_ESP) at x 166.08, pin 2 (GND) at x 165.12
    "C102": (172.85, 116.85, -90.0),   # pin 1 (VBUS_MAIN) at y 116.37, pin 2 (GND) at y 117.33
}
SHIFT_DOWN = ["R105", "R106", "R107", "R108", "R109", "R110", "R111", "R112"]
DY = 0.5

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p

for ref, pose in MOVES.items():
    P[ref].place(*pose)
for ref in SHIFT_DOWN:
    x, y, r = P[ref].at
    P[ref].place(x, round(y + DY, 4), r)


def shapes(ref):
    p = P[ref]
    return ([p.courtyard()] if p.local_box("CrtYd") else []) + p.pads()


# clash check: every moved part against everything on its side and through-hole parts
clash = []
for g in list(MOVES) + SHIFT_DOWN:
    for ref, p in P.items():
        if ref == g:
            continue
        if p.side != P[g].side and not ref.startswith(("J10", "H", "SW", "MK")):
            continue
        other = shapes(ref) if p.side == P[g].side else p.pads(only_th=True)
        if any(overlap(s, o) for s in shapes(g) for o in other):
            clash.append("/".join(sorted((g, ref))))
print("overlaps:", sorted(set(clash)) or "none")
for ref in list(MOVES) + SHIFT_DOWN:
    print(ref, tuple(round(v, 3) for v in P[ref].at))
if "--dry-run" not in sys.argv:
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)
