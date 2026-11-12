"""Push the XVF3800's decoupling caps outward to leave a via fan-out channel (2026-11-12).

User: move the caps "a bit outward" so there is room to route vias for the pins. Each cap
row (and the bulk caps / PLL ferrite behind it) moves straight out from its side of U301 by
SHIFT, so the chip-to-cap courtyard gap goes from 0.15 mm to 1.65 mm: room for two staggered
rows of 0.5 mm vias (the board's minimum via) between the QFN pads and the caps.
Neighbouring groups that would collide move out with them (NEIGHBOURS).

Usage (board closed in KiCad):  python3 tools/xvf_caps_out.py [--out trial.kicad_pcb]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from place_tidy import BOARD, Part, overlap, LEFT, RIGHT, TOP, BOTTOM  # noqa: E402
from sexpr import parse, dump, children  # noqa: E402

SHIFT = 1.5      # mm outward, per side

# Which side of U301 each part sits on (U301 is on the bottom at rot 0: pins 1-15 right,
# 16-30 bottom, 31-45 left, 46-60 top). From place_tidy2.py's cap-to-pin table.
SIDE = {
    "R": ["C301", "C310", "C302"],                          # pins 4, 8, 12
    "B": ["C315", "C303", "C319", "C316", "C304", "C313",   # pins 17, 19, 22, 26, 27, 30
          "FB301", "C318"],                                 # PLL ferrite, 1.8 V bulk behind
    "L": ["C317", "C305", "C311", "C306", "C314"],          # pins 31, 34, 38, 42 + 3.3 V bulk
    "T": ["C307", "C312", "C308", "C309"],                  # pins 49, 52, 57 + VDD bulk
}
STEP = {"R": (SHIFT, 0), "L": (-SHIFT, 0), "T": (0, -SHIFT), "B": (0, SHIFT)}
# Groups beside the cap rows that move out too: the mic clock buffer (left of the left row)
# with its cap and resistor, and the crystal group, whose Rd/Rf would otherwise sit in the
# right-hand channel by pins 13-15.
NEIGHBOURS = {"L": ["U501", "C501", "R501"], "R": ["Y301", "R301", "R302", "C320", "C321"]}

root = parse(open(BOARD).read())
P = {Part(f).ref: Part(f) for f in children(root, "footprint")}
for side, refs in SIDE.items():
    dx, dy = STEP[side]
    for r in refs + NEIGHBOURS.get(side, []):
        x, y, rot = P[r].at
        P[r].place(x + dx, y + dy, rot)
    print(f"side {side}: {len(refs)} parts (+{len(NEIGHBOURS.get(side, []))} neighbours) moved {SHIFT} mm out")

# overlap check (courtyards and pads) for every on-board part on the same side
ON = [r for r, p in P.items() if LEFT <= p.at[0] <= RIGHT and TOP <= p.at[1] <= BOTTOM]
SH = {r: ([P[r].courtyard()] if P[r].local_box("CrtYd") else []) + P[r].pads() for r in ON}
clash = [f"{a}/{b}" for i, a in enumerate(ON) for b in ON[i + 1:]
         if (P[a].side == P[b].side or any(r.startswith(("J10", "H", "SW", "MK")) for r in (a, b)))
         and any(overlap(s, t) for s in SH[a] for t in SH[b])]
print("overlaps:", clash or "none")
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else BOARD
open(out, "w").write(dump(root) + "\n")
print("wrote", out)
