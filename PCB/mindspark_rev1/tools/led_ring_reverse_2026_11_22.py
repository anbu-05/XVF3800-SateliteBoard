"""Reverse the LED ring's direction (2026-11-22, group 4).

Every WS2812B-2020 on the ring has its VDD and DOUT pads in the outer column (VDD sits on the
+5V_LED ring) and DIN and GND in the inner column. DOUT can only leave on the side away from
VDD, and with the chain running D801 -> D802 -> ... counter-clockwise (as seen from the top) that
side faced away from the next LED, so every link had to loop round its own LED. Three loops
could not get past the parts around them (J101 at D801, the regulators at D811).

Running the chain the other way round puts each DOUT on the side facing the next LED, next to
that LED's DIN (inner column, on the facing side): every link becomes a short hop along the ring.
So the LEDs swap places in pairs, mirrored about the D801-D807 line; each takes the other's
position and rotation (same footprint, same rotation rule), and D801 / D807 stay. Each LED's
supply cap (C802-C812) swaps with it, since power_v2 joins each cap to its own LED.

Run once, PCB editor closed:  python3 tools/led_ring_reverse_2026_11_22.py
A pair already swapped (D802 no longer at its original spot) is skipped.
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children  # noqa: E402

PAIRS = [("D802", "D812"), ("D803", "D811"), ("D804", "D810"), ("D805", "D809"), ("D806", "D808")]
# each LED's supply cap C8xx goes with it (power_v2 joins C8xx to D8xx's VDD pad)
PAIRS += [("C" + a[1:], "C" + b[1:]) for a, b in PAIRS]
D802_ORIGINAL = (169.9407, 85.179)

root = parse(open(BOARD).read())
fp = {}
for f in children(root, "footprint"):
    fp[[p[2] for p in children(f, "property") if p[1] == "Reference"][0]] = f


def at_of(ref):
    return [c for c in fp[ref] if isinstance(c, list) and c and c[0] == "at"][0]


a = at_of("D802")
if abs(float(a[1]) - D802_ORIGINAL[0]) > 1e-3 or abs(float(a[2]) - D802_ORIGINAL[1]) > 1e-3:
    print("LED ring already reversed, skipped")
    sys.exit(0)


def set_rot(f, new):
    """Turn the footprint and every pad / text in it by the change of angle (KiCad stores pad
    and text angles as board angles)."""
    at = [c for c in f if isinstance(c, list) and c and c[0] == "at"][0]
    old = float(at[3]) if len(at) > 3 else 0.0
    delta = new - old
    for item in [c for c in f if isinstance(c, list) and c and c[0] in ("pad", "property", "fp_text")]:
        ia = [c for c in item if isinstance(c, list) and c and c[0] == "at"]
        if not ia:
            continue
        ia = ia[0]
        has_ang = len(ia) > 3 and ia[3] != "unlocked"
        ang = float(ia[3]) if has_ang else 0.0
        extra = ia[4:] if has_ang else ia[3:]
        ang = (ang + delta + 180) % 360 - 180
        ia[1:] = ia[1:3] + [f"{ang:g}"] + extra


for r1, r2 in PAIRS:
    a1, a2 = at_of(r1), at_of(r2)
    p1, p2 = list(a1[1:]), list(a2[1:])
    rot1 = float(p1[2]) if len(p1) > 2 else 0.0
    rot2 = float(p2[2]) if len(p2) > 2 else 0.0
    set_rot(fp[r1], rot2)
    set_rot(fp[r2], rot1)
    a1[1:], a2[1:] = p2, p1
    print(f"{r1} <-> {r2}")
open(BOARD, "w").write(dump(root) + "\n")
