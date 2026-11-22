"""Place each test pad next to where its net already has copper (2026-11-22, user).

User 2026-11-22: "put the test points where it makes sense", 1 mm round, top or bottom,
wherever comfortable; labels later. So instead of rows along the edges, each pad goes to the
free spot closest to its own net's copper, and joins it on a short stub (or sits right on the
track when there is room).

power_v2 does it, after every other route is laid, so the pads never get in anyone's way: for
each pad, candidates() lists free spots (shortest stub first); power_v2 tries them in turn and
keeps the first whose stub actually routes. The chosen spots are written to
test_pad_spots_2026_11_22.json for the record. This file is a helper module, not run on its own.

A spot is free when:
  * the 1 mm pad keeps 0.15 mm from other nets' copper on its layer (its own net may be under it);
  * its 1 mm-radius courtyard stays off every other part's courtyard on that side (and off the
    other test pads already placed);
  * on the top, it is not under the ESP32 module.
Score = distance from the pad edge to the nearest copper of its own net on the same layer
(a stub), or to any of its copper plus 1.0 mm when the stub needs a via. Lowest first; ties go
to the bottom side.
"""
import json
import math
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

SPOTS = os.path.join(os.path.dirname(__file__), "test_pad_spots_2026_11_22.json")
TEST_PADS = ["TP204"] + [f"TP{n}" for n in range(401, 413)]
PAD_R = 0.5          # 1 mm round pad
CRT_R = 1.0          # its courtyard
SEARCH = 8.0         # look this far (mm) from the net's copper
VIA_EXTRA = 1.0      # score penalty when the stub has to change layer


def candidates(ref, net, shapes, parts, box, taken, keep=25):
    """Free spots for one test pad, best (shortest stub) first.
    shapes: jog_router Shapes on the board now (other test pads already placed included);
    parts: ref -> Part (test pads left out); taken: [(x, y, layer)] of test pads placed so far.
    Returns up to `keep` spots [x, y, layer, score], at least 0.5 mm apart."""
    from grid_router import GridRouter, shape_dist
    from jog_router import Shape
    own = [s for s in shapes if s.net == net]
    x0 = max(box[0], min(s.box[0] for s in own) - SEARCH)
    y0 = max(box[1], min(s.box[1] for s in own) - SEARCH)
    x1 = min(box[2], max(s.box[2] for s in own) + SEARCH)
    y1 = min(box[3], max(s.box[3] for s in own) + SEARCH)
    near = [s for s in shapes if s.box[2] > x0 - 2 and s.box[0] < x1 + 2 and s.box[3] > y0 - 2 and s.box[1] < y1 + 2]
    grid = GridRouter(box, near, width=2 * PAD_R, via_d=2 * PAD_R)
    nid = grid.nid(net)
    crt = {L: [Shape("", {L}, poly=p.courtyard()) for r, p in parts.items() if str(p.side) == L]
           for L in ("F.Cu", "B.Cu")}
    module = Shape("", {"F.Cu"}, poly=parts["U601"].courtyard())
    found = []
    i0, j0 = grid.cell(x0, y0)
    i1, j1 = grid.cell(x1, y1)
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            x, y = grid.xy(i, j)
            k = j * grid.nx + i
            for L in ("B.Cu", "F.Cu"):
                if grid.trk[L][k] not in (0, nid):
                    continue
                d_same = min((shape_dist(s, x, y) for s in own if L in s.layers), default=1e9)
                d_any = min(shape_dist(s, x, y) for s in own)
                score = min(max(0.0, d_same - PAD_R), max(0.0, d_any - PAD_R) + VIA_EXTRA)
                if score <= SEARCH:
                    found.append((score, L != "B.Cu", x, y, L))
    found.sort()
    out = []
    for score, _, x, y, L in found:
        if len(out) >= keep:
            break
        if any(L == o[2] and math.hypot(x - o[0], y - o[1]) < 0.5 for o in out):
            continue
        if any(L == pl and math.hypot(x - px, y - py) < 2 * CRT_R + 0.2 for px, py, pl in taken):
            continue
        if any(shape_dist(c, x, y) < CRT_R for c in crt[L]):
            continue
        if L == "F.Cu" and shape_dist(module, x, y) < CRT_R:
            continue
        out.append([round(x, 3), round(y, 3), L, round(score, 3)])
    return out


def save(spots):
    json.dump(spots, open(SPOTS, "w"), indent=1)
