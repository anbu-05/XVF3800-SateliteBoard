"""Swap resistor pairs whose short links crossed (2026-11-22, group 1 local hookups).

Each pair has the same footprint and rotation, so swapping their positions uncrosses the links
without touching anything else. Pad 2 of each (GND / +3V3 / the group 3 signal) is joined later:
power_v2 rebuilds every track, and the group 3 signals are not routed yet.

  R602 / R604  SW602 (BOOT button): ESP_BOOT is on its south pads, R604's net on its north pads,
               but R602 (BOOT pull-up) sat north of R604.
  R101 / R102  J101 CC pull-downs: CC1 leaves U101 (ESD) on its south pin, CC2 on its north pin,
               but R101 (CC1) sat north and R102 (CC2) south, across the USB pair.
  R103 / R104  J102 CC pull-downs: the same, mirrored (CC1 north, CC2 south on U102).
  R405 / R406  D402 (RGB LED) resistors: red anode is D402's south pin, green its north pin, but
               R405 (red) sat north of R406 (green).

Run once, PCB editor closed:  python3 tools/resistor_swaps_2026_11_22.py
A pair already swapped (its first resistor no longer at its original spot) is skipped.
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children, child  # noqa: E402

PAIRS = [  # first, second, first resistor's original (x, y) before 2026-11-22
    ("R602", "R604", (118.338, 107.749)),
    ("R101", "R102", (174.213, 96.559)),
    ("R103", "R104", (118.903, 100.799)),
    ("R405", "R406", (180.178, 114.089)),
]

root = parse(open(BOARD).read())
fp = {}
for f in children(root, "footprint"):
    fp[[p[2] for p in children(f, "property") if p[1] == "Reference"][0]] = f
for a_ref, b_ref, orig in PAIRS:
    a, b = child(fp[a_ref], "at"), child(fp[b_ref], "at")
    if abs(float(a[1]) - orig[0]) > 1e-3 or abs(float(a[2]) - orig[1]) > 1e-3:
        print(f"{a_ref}/{b_ref}: already swapped, skipped")
        continue
    a[1:], b[1:] = list(b[1:]), list(a[1:])
    print(f"{a_ref} -> {a[1:]}   {b_ref} -> {b[1:]}")
open(BOARD, "w").write(dump(root) + "\n")
