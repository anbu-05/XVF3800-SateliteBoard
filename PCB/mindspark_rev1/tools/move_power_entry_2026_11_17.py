"""Move the TPS2121 block and the LED-ring switch to the bottom right (2026-11-17).

Why: the power review (verification/power-review-2026-11-17/) found +5V had to cross the
XVF3800/ESP32 middle to reach the bucks. With the TPS2121 next to the bucks, power flows one
way (in at the bottom, up through the middle) and In2 can be split into simple regions.

What it does (KiCad PCB editor closed):
  1. Moves both groups together, unchanged in arrangement, by one translation so the block's
     top-left courtyard corner lands at TARGET (free top-side area between L201 and J101).
  2. Removes the copper the move breaks:
       - every track/via on the groups' own nets (dividers, CT, SS, ILIM);
       - every track whose end sits on a moved pad (at the old position);
       - vias and F.Cu tracks under the new block (they would short to its pads);
       - then, repeatedly, tracks and vias left dangling (an end touching nothing).
     Copper on In2 that merely passes under the new block is kept.
  3. Checks overlaps against all top-side parts and through-hole parts, then writes the board.

Usage:  python3 tools/move_power_entry_2026_11_17.py [--dry-run]
"""
import math
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part, bbox, overlap, circle_pts  # noqa: E402
from sexpr import parse, dump, children, child  # noqa: E402

# The two groups, as tidied on 2026-11-12 (TPS2121 with its dividers and caps; U801 with its own).
MUX = ["U103", "C105", "C106", "C107", "R105", "R106", "R107", "R108", "R109", "R110",
       "R111", "R112", "R113", "R114"]
LEDSW = ["U801", "C813", "R801", "C814", "C815"]
GROUP = MUX + LEDSW
OWN_NETS = {"Net-(U103-CP2)", "Net-(U103-OV1)", "Net-(U103-OV2)", "Net-(U103-PR1)",
            "Net-(U103-ILIM)", "Net-(U103-SS)", "Net-(U801-CT)"}
TARGET = (159.5, 109.3)   # new top-left courtyard corner: 0.9 mm right of L201, 0.7 mm above H4
CLEAR = 0.3               # margin round the new block for removing vias / F.Cu tracks under it

root = parse(open(BOARD).read())
P = {Part(f).ref: Part(f) for f in children(root, "footprint")}
for f in children(root, "footprint"):          # keep the Part objects bound to the real nodes
    P[Part(f).ref].node = f


def net_of(n):
    x = child(n, "net")
    return str(x[1]) if x else ""


def group_box():
    return bbox([q for r in GROUP for q in P[r].courtyard()])


# ------------------------------------------------------------- 1. pads at the old position
old_pads = []   # (polygon, net) of every moved pad, before the move
for r in GROUP:
    for pd, poly in zip(children(P[r].node, "pad"), P[r].pads()):
        old_pads.append((poly, net_of(pd)))


def inside(pt, poly):
    b = bbox(poly)
    return b[0] - 1e-3 <= pt[0] <= b[2] + 1e-3 and b[1] - 1e-3 <= pt[1] <= b[3] + 1e-3


# ------------------------------------------------------------- 2. move
b0 = group_box()
dx, dy = TARGET[0] - b0[0], TARGET[1] - b0[1]
for r in GROUP:
    x, y, rot = P[r].at
    P[r].place(x + dx, y + dy, rot)
b1 = group_box()
report = [f"moved {len(GROUP)} parts by ({dx:+.3f}, {dy:+.3f}) mm; block now "
          f"x {b1[0]:.2f}-{b1[2]:.2f}, y {b1[1]:.2f}-{b1[3]:.2f}; U103 at {P['U103'].at[:2]}"]

# ------------------------------------------------------------- 3. copper the move breaks
items = [n for n in root if isinstance(n, list) and n and n[0] in ("segment", "via", "arc")]


def ends(n):
    if n[0] == "via":
        a = child(n, "at")
        return [(float(a[1]), float(a[2]))]
    return [(float(child(n, k)[1]), float(child(n, k)[2])) for k in ("start", "end")]


def layer(n):
    return str(child(n, "layer")[1]) if n[0] != "via" else "via"


new_pads = [poly for r in GROUP for poly in P[r].pads()]
area = (b1[0] - CLEAR, b1[1] - CLEAR, b1[2] + CLEAR, b1[3] + CLEAR)


def seg_hits_area(n):
    """A track or via whose copper reaches into the new block's area (sampled along the track)."""
    pts = ends(n)
    if len(pts) == 2:
        pts = [(pts[0][0] + (pts[1][0] - pts[0][0]) * t / 20, pts[0][1] + (pts[1][1] - pts[0][1]) * t / 20)
               for t in range(21)]
    return any(area[0] <= x <= area[2] and area[1] <= y <= area[3] for x, y in pts)


drop = set()
why = {}
for n in items:
    net = net_of(n)
    if net in OWN_NETS:
        drop.add(id(n)); why.setdefault("groups' own nets", []).append(n)
    elif n[0] != "via" and any(inside(e, poly) and net == pn for e in ends(n) for poly, pn in old_pads):
        drop.add(id(n)); why.setdefault("ended on a moved pad", []).append(n)
    elif (n[0] == "via" or layer(n) == "F.Cu") and seg_hits_area(n):
        drop.add(id(n)); why.setdefault("under the new block", []).append(n)

# pads that stay put, with their nets and copper layers (for the dangling test)
fixed_pads = []
for r, p in P.items():
    for pd, poly in zip(children(p.node, "pad"), p.pads()):
        lays = [str(a) for a in (child(pd, "layers") or [])[1:]]
        cu = {"F.Cu", "B.Cu", "In1.Cu", "In2.Cu"} if "*.Cu" in lays else {p.side}
        fixed_pads.append((poly, net_of(pd), cu))


def touches(pt, lay, net, others):
    """True if point pt on layer lay meets a pad, a via, or another track end/body of the same net."""
    for poly, pn, cu in fixed_pads:
        if pn == net and (lay == "via" or lay in cu) and inside(pt, poly):
            return True
    for m in others:
        if net_of(m) != net:
            continue
        if m[0] == "via":
            a = ends(m)[0]
            if math.dist(a, pt) <= float(child(m, "size")[1]) / 2 + 1e-3:
                return True
            continue
        if lay != "via" and layer(m) != lay:
            continue
        (x1, y1), (x2, y2) = ends(m)
        w = float(child(m, "width")[1]) / 2
        L2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
        t = 0 if L2 == 0 else max(0, min(1, ((pt[0] - x1) * (x2 - x1) + (pt[1] - y1) * (y2 - y1)) / L2))
        if math.dist(pt, (x1 + t * (x2 - x1), y1 + t * (y2 - y1))) <= w + 1e-3:
            return True
    return False


# ------------------------------------------------------------- 4. dangling clean-up, repeated
# Only nets the move touched are cleaned; anything else stays exactly as it was.
affected = {net_of(n) for n in items if id(n) in drop}


def via_layers(v, others):
    """Copper layers on which via v meets a track of its net."""
    out = set()
    for m in others:
        if m[0] == "via" or net_of(m) != net_of(v):
            continue
        if touches(ends(v)[0], layer(m), net_of(v), [m]):
            out.add(layer(m))
    return out


changed = True
while changed:
    changed = False
    alive = [n for n in items if id(n) not in drop]
    for n in alive:
        if net_of(n) not in affected:
            continue
        others = [m for m in alive if m is not n]
        if n[0] == "via":
            # a via must sit in a pad, or join tracks on at least two layers; otherwise it's a dead end
            in_pad = any(pn == net_of(n) and inside(ends(n)[0], poly) for poly, pn, _ in fixed_pads)
            ok = in_pad or len(via_layers(n, others)) >= 2
        else:
            ok = all(touches(e, layer(n), net_of(n), others) for e in ends(n))
        if not ok:
            drop.add(id(n)); why.setdefault("left dangling", []).append(n); changed = True
            break

if "-v" in sys.argv:
    for n in [m for m in items if id(m) in drop]:
        print("   ", net_of(n), n[0], layer(n), [tuple(round(c, 2) for c in e) for e in ends(n)])
for k, lst in why.items():
    nets = {}
    for n in lst:
        nets[net_of(n)] = nets.get(net_of(n), 0) + 1
    report.append(f"removed ({k}): {len(lst)} -> {nets}")
root[:] = [n for n in root if not (isinstance(n, list) and id(n) in drop)]

# ------------------------------------------------------------- 5. overlap check
clash = []
board_parts = [r for r in P if r not in GROUP]
for g in GROUP:
    gs = [P[g].courtyard()] + P[g].pads()
    for r in board_parts:
        p = P[r]
        th = r.startswith(("J10", "H", "SW", "MK"))
        if p.side != "F.Cu" and not th:
            continue
        rs = ([p.courtyard()] if p.local_box("CrtYd") else []) + p.pads(only_th=p.side != "F.Cu")
        if r.startswith("H"):
            rs.append(circle_pts(p.at[0], p.at[1], 2.2))
        if any(overlap(a, b) for a in gs for b in rs):
            clash.append(f"{g}/{r}")
report.append(f"overlaps with other parts: {clash if clash else 'none'}")
print("\n".join(report))
if "--dry-run" not in sys.argv:
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)
