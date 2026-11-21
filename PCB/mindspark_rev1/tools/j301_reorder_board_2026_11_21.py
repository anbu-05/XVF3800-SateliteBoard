"""Board side of tools/sch_j301_reorder_2026_11_21.py: set the new JTAG nets on J301 pads 2-6
and on the parallel test pads TP302-TP306 (same as KiCad's update from the schematic would).
Usage (PCB editor closed):  python3 tools/j301_reorder_board_2026_11_21.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD, Part  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

TCK, TMS, RST, TDO, TDI = ("/xvf3800/XVF_TCK", "/xvf3800/XVF_TMS", "/XVF_RST_N",
                           "/xvf3800/XVF_TDO", "/xvf3800/XVF_TDI")
NEW = {("J301", "2"): TCK, ("J301", "3"): TMS, ("J301", "4"): RST, ("J301", "5"): TDO, ("J301", "6"): TDI,
       ("TP302", "1"): TCK, ("TP303", "1"): TMS, ("TP304", "1"): RST, ("TP305", "1"): TDO, ("TP306", "1"): TDI}
root = parse(open(BOARD).read())
done = 0
for f in children(root, "footprint"):
    ref = Part(f).ref
    for pd in children(f, "pad"):
        key = (ref, str(pd[1]))
        if key in NEW:
            n = child(pd, "net")
            print(f"  {ref}.{pd[1]}: {str(n[-1]).strip(chr(34))} -> {NEW[key]}")
            n[1:] = [q(NEW[key])]
            done += 1
assert done == len(NEW), done
open(BOARD, "w").write(dump(root) + "\n")
