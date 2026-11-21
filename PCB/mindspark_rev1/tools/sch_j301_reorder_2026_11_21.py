"""J301 (XTAG4 JTAG header, our own JST PH pinout) reordered to match the order the JTAG lines
leave the XVF3800 (user 2026-11-21), so they run straight to it without crossing.

  pin 2: TMS -> TCK     pin 3: TCK -> TMS     pin 4: TDO -> RST_N
  pin 5: TDI -> TDO     pin 6: RST_N -> TDI   (pin 1 +1V8 and pin 7 GND stay)

The test pads TP302-TP306 sit on the same wires as J301 pins 2-6 (parallel solder pads), so they
follow. Done by moving the net labels along their wires on the xvf3800 sheet: each label keeps its
x and angle, only its row changes.
Usage (schematic editor closed):  python3 tools/sch_j301_reorder_2026_11_21.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, dump, children, child  # noqa: E402

SHEET = os.path.join(os.path.dirname(__file__), "..", "xvf3800.kicad_sch")
X = 53.34
MOVE = {"XVF_TCK": (144.78, 142.24), "XVF_TMS": (142.24, 144.78), "XVF_RST_N": (152.4, 147.32),
        "XVF_TDO": (147.32, 149.86), "XVF_TDI": (149.86, 152.4)}
root = parse(open(SHEET).read())
done = []
for kind in ("label", "hierarchical_label"):
    for lab in children(root, kind):
        name = str(lab[1]).strip('"')
        at = child(lab, "at")
        if name in MOVE and abs(float(at[1]) - X) < 1e-3 and abs(float(at[2]) - MOVE[name][0]) < 1e-3:
            at[2] = f"{MOVE[name][1]:g}"
            for p in children(lab, "property"):          # keep any field text with its label
                pa = child(p, "at")
                if pa is not None:
                    pa[2] = f"{float(pa[2]) + MOVE[name][1] - MOVE[name][0]:.2f}"
            done.append(name)
if sorted(done) != sorted(MOVE):
    sys.exit(f"labels not found as expected: moved {done}")
open(SHEET, "w").write(dump(root) + "\n")
print("moved", done)
