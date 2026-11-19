"""Remove every track, arc and via from the board (2026-11-18).

User, 2026-11-18: routing is redone from scratch after the power planes (In1 GND, In2 regions)
are drawn. Footprints, zones (none yet), outline and texts are untouched.
The last routing is in git (commit b6417da).

Usage (PCB editor closed):  python3 tools/clear_routing_2026_11_18.py
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump  # noqa: E402

root = parse(open(BOARD).read())
kinds = ("segment", "arc", "via")
counts = {k: sum(1 for n in root if isinstance(n, list) and n and n[0] == k) for k in kinds}
root[:] = [n for n in root if not (isinstance(n, list) and n and n[0] in kinds)]
open(BOARD, "w").write(dump(root) + "\n")
print("removed", counts)
