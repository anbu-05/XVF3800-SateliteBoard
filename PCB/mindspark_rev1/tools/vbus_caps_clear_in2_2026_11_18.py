"""VBUS caps to the TPS2121, and In2 cleared for the new pours (2026-11-18).

User, 2026-11-18: the VBUS decoupling caps sat at the USB-C ports by mistake; they belong at
the TPS2121 inputs. The TVS diodes D101/D102 stay at the connectors (they must clamp at the port).
Then every track on In2 is removed: In2 gets power regions next
(see verification/power-review-2026-11-17/).

  1. C102 (100 nF) beside IN1 (pin 7, right side), C101 (10 uF) beyond it, both pad 1 towards the pin.
     C104 (100 nF) beside IN2 (pin 2, left side, under C107), C103 (10 uF) below it.
     All at 0.15 mm courtyard gaps from their neighbours.
  2. Copper that served the caps at the old spot is removed (C102 stub + its via, the vias in
     the C103/C104 pads).
  (A 0.08 mm VBUS_MAIN stub left at C102's old spot was removed by hand afterwards, uuid 465a1ff9.)
  3. Every In2 track is removed. Vias stay: they mark where each rail drops to In2 and will join
     the pours (until then DRC lists them as dangling).

Usage (PCB editor closed):  python3 tools/vbus_caps_clear_in2_2026_11_18.py [--dry-run]
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part, bbox, overlap, circle_pts  # noqa: E402
from sexpr import parse, dump, children, child  # noqa: E402

# ref: (x, y, rotation). Rotation chosen so pad 1 (VBUS) faces the TPS2121 pin.
NEW = {
    "C102": (172.02, 115.13, 0.0),    # pad 1 left, next to IN1
    "C101": (174.56, 115.13, 0.0),    # pad 1 left, after C102
    "C104": (167.00, 115.28, 180.0),  # pad 1 right, next to IN2; top courtyard 0.15 below C107
    "C103": (166.54, 117.37, -90.0),  # pad 1 up, under C104; 0.15 left of R107
}

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p


def net_of(n):
    x = child(n, "net")
    return str(x[1]) if x else ""


def pts_of(n):
    if n[0] == "via":
        a = child(n, "at")
        return [(float(a[1]), float(a[2]))]
    return [(float(child(n, k)[1]), float(child(n, k)[2])) for k in ("start", "end")]


# ------------------------------------------------------------- old pad boxes, then move
old = [(r, net_of(pd), bbox(poly)) for r in NEW for pd, poly in zip(children(P[r].node, "pad"), P[r].pads())]
for r, (x, y, rot) in NEW.items():
    P[r].place(x, y, rot)
report = []
for r in NEW:
    pads = [(str(pd[1]), net_of(pd), tuple(round(v, 2) for v in bbox(poly)[:2])) for pd, poly in
            zip(children(P[r].node, "pad"), P[r].pads())]
    report.append(f"{r} -> {NEW[r]}  pads {pads}")

# ------------------------------------------------------------- copper to remove
drop, why = set(), {}
for n in [n for n in root if isinstance(n, list) and n and n[0] in ("segment", "via", "arc")]:
    lay = str(child(n, "layer")[1]) if n[0] != "via" else ""
    on_old_pad = any(net_of(n) == net and b[0] - 0.01 <= x <= b[2] + 0.01 and b[1] - 0.01 <= y <= b[3] + 0.01
                     for _, net, b in old for x, y in pts_of(n))
    if lay == "In2.Cu":
        drop.add(id(n)); why.setdefault("In2 tracks", []).append(n)
    elif on_old_pad:
        drop.add(id(n)); why.setdefault("on the caps' old pads", []).append(n)
# the via the C102 stub led to (it only went down to the old In2 run)
for n in children(root, "via"):
    if net_of(n) == "VBUS_MAIN" and pts_of(n)[0] == (168.5544, 97.536):
        drop.add(id(n)); why.setdefault("on the caps' old pads", []).append(n)
for k, lst in why.items():
    c = {}
    for n in lst:
        c[net_of(n)] = c.get(net_of(n), 0) + 1
    report.append(f"removed ({k}): {len(lst)} -> {c}")
root[:] = [n for n in root if not (isinstance(n, list) and id(n) in drop)]

# ------------------------------------------------------------- overlap check
clash = []
for g in NEW:
    gs = [P[g].courtyard()] + P[g].pads()
    for r, p in P.items():
        if r == g:
            continue
        th = r.startswith(("J10", "H", "SW", "MK"))
        if p.side != "F.Cu" and not th:
            continue
        rs = ([p.courtyard()] if p.local_box("CrtYd") else []) + p.pads(only_th=p.side != "F.Cu")
        if r.startswith("H"):
            rs.append(circle_pts(p.at[0], p.at[1], 2.2))
        if any(overlap(a, b) for a in gs for b in rs):
            clash.append(f"{g}/{r}")
report.append(f"overlaps: {sorted(set(clash)) if clash else 'none'}")
print("\n".join(report))
if "--dry-run" not in sys.argv:
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)
