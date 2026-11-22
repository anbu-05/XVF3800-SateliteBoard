"""Nudge two XVF3800 south-row decaps east (2026-11-22, group 2 escape).

The user allows XVF decaps to move up to ~0.5 mm so the fan-out fits on the bottom layer.
  C305 (+0V9, pin 34)  +0.15 mm: the gap west of it (to C311) takes three south lanes.
  C317 (+1V8, pin 31)  +0.50 mm: the gap west of it (to C305) takes two lanes (pins 32/33);
                       pin 31 reaches it by a 45 deg jog.
Run once, PCB editor closed:  python3 tools/xvf_cap_nudge_2026_11_22.py
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children, child  # noqa: E402

MOVES = {"C305": (148.158, 148.308), "C317": (149.358, 149.858)}   # ref: (original x, new x)
root = parse(open(BOARD).read())
for f in children(root, "footprint"):
    ref = [p[2] for p in children(f, "property") if p[1] == "Reference"][0]
    if ref in MOVES:
        at = child(f, "at")
        old, new = MOVES[ref]
        if abs(float(at[1]) - old) > 1e-3:
            print(f"{ref}: not at its original x ({at[1]}), skipped")
            continue
        at[1] = f"{new}"
        print(f"{ref}: x {old} -> {new}")
open(BOARD, "w").write(dump(root) + "\n")
