"""Re-route the NW mic pair (MIC_DATA1 + its clock) round the new flash-switch block (user 2026-11-22).

The flash switches move to the top side west of the ESP32 module
(tools/prog_switch_place_2026_11_22.py). Their programming lines need the bottom layer under that
block, where the NW mic pair used to cross diagonally on B.Cu. The user agreed to move the pair:

  * MIC_DATA1: from the fan-out end (137.6, 99.88) down to y 101.5, west under C501 / U501's gap,
    45 degrees down to y 103.2 below the switch column, west to a via at x 124.8, then F.Cu
    straight north (east lane) and along the old 45 degree line to R507.
  * NW clock: leaves R501 pad 2 west on F.Cu, down between C501 and R501, along y 101.5 (south
    of C501), 45 degrees down to y 102.75 under the column's bottom switch, a via at x 126.3,
    B.Cu under the +5V trunk to a via at x 124.25, then F.Cu north (west lane, so it turns off
    first) and along the old 45 degree line to R503. The old branch from the clock star to the
    via at (134.3, 97.7) goes.
  The two F.Cu lanes run west of the switch caps and the +5V trunk; the pair keeps >= 0.45 mm
  pitch. Lengths go up by about 8 mm (DATA1) and 10 mm (clock); PDM at ~3 MHz does not mind.

Edits tools/mic_route_2026_11_20.json in place (backup in
mindspark_rev1-backups/pre-prog-switch-2026-11-22/tools/). Run once.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "mic_route_2026_11_20.json")
D1, CLK = "/MIC_DATA1", "Net-(R501-Pad2)"

OLD_VIAS = [(134.3, 97.7), (128.4455, 82.9623), (127.6413, 83.7665)]
D1_X, CLK_X = 124.8, 124.25                                # F.Cu lanes west of the +5V trunk
D1_DIAG_Y = round(D1_X - (117.9455 - 66.2623), 4)       # where the lane meets the old R507 line
CLK_DIAG_Y = round(CLK_X - (114.1413 - 70.2665), 4)     # where the lane meets the old R503 line
NEW = [
    (D1, "B.Cu", [[137.6, 99.879], [135.979, 101.5], [132.9, 101.5], [131.2, 103.2], [D1_X, 103.2]]),
    (D1, "F.Cu", [[D1_X, 103.2], [D1_X, D1_DIAG_Y], [117.9455, 66.2623], [117.2455, 66.2623]]),
    (CLK, "F.Cu", [[135.55, 99.84], [134.6, 99.84], [134.6, 101.5], [132.95, 101.5], [131.7, 102.75],
                   [126.3, 102.75]]),
    (CLK, "B.Cu", [[126.3, 102.75], [CLK_X, 102.75]]),
    (CLK, "F.Cu", [[CLK_X, 102.75], [CLK_X, CLK_DIAG_Y], [114.1413, 70.2665], [114.1413, 69.3665]]),
]
NEW_VIAS = [([D1_X, 103.2], D1), ([126.3, 102.75], CLK), ([CLK_X, 102.75], CLK)]


def old_nw(t):
    """True for the old NW pair tracks: DATA1 west of x 137.6, the NW clock branch and corridor."""
    pts = t["pts"]
    if t["net"] == D1:
        return max(p[0] for p in pts) <= 137.61
    if t["net"] == CLK:
        if pts[0] == [135.55, 98.95] and pts[-1] == [134.3, 97.7]:
            return True                                     # star -> old NW via
        return all(p[0] <= 134.31 and p[1] <= 98.0 for p in pts) and min(p[0] for p in pts) < 128.0 \
            or pts[0] == [134.3, 97.7]
    return False


def main():
    d = json.load(open(DATA))
    if any(t["pts"] == NEW[0][2] for t in d["tracks"]):
        raise SystemExit("already re-routed")
    keep = [t for t in d["tracks"] if not old_nw(t)]
    gone = len(d["tracks"]) - len(keep)
    keep += [{"net": n, "layer": l, "pts": p} for n, l, p in NEW]
    vias = [v for v in d["vias"] if not any(math.dist(v["at"], o) < 0.01 for o in OLD_VIAS)]
    vias += [{"at": at, "net": n} for at, n in NEW_VIAS]
    d["tracks"], d["vias"] = keep, vias
    json.dump(d, open(DATA, "w"), indent=1)
    print(f"removed {gone} old NW tracks, {len(OLD_VIAS)} vias; added {len(NEW)} tracks, {len(NEW_VIAS)} vias")


if __name__ == "__main__":
    main()
