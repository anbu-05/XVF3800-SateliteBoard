"""Rotate the XVF3800 group 90 deg CCW and re-place the parts that this displaces (2026-11-18).

Agreed with the user (AGENTS.md, To do 1 and Under discussion 1):
  * U301 (XVF3800) turns 90 deg counter-clockwise, seen from the top, about its own centre,
    together with its decoupling caps C301-C319, the PLL ferrite FB301 and the mic-clock
    buffer group U501/C501/R501. USB D+/- then leave the east edge towards J101.
  * The rotated east cap column lands on the flash and the crystal resistors, so:
      flash group U401/C401/R401 -> the chip's north-west corner (next to the QSPI pins),
      crystal group Y301/R301/R302/C320/C321 -> above the north cap row (pins 15/16).
    These poses came from a search on a scratch copy (all four 90 deg turns, every 0.25 mm,
    clash-free, shortest links to the XVF3800 pins).
  * The LDO group U203/C208/C209 flips to the bottom, east of the XVF3800 just outside the
    ESP32 module (x > 156.96), next to the +1V8 pins (17 and 26 on the east edge after the
    rotation). Its pose is searched here: closest clash-free spot in that box, with the input
    (pin 1, +3V3) east of the output (pin 5, +1V8) so the In2 +1V8 area can stop between them.

Tracks, vias and zones are not touched here; tools/power_v2_2026_11_18.py rebuilds them.
Usage (PCB editor closed):  python3 tools/xvf_rotate_2026_11_18.py [--dry-run]
"""
import math
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part, bbox, overlap, norm  # noqa: E402
from sexpr import parse, dump, children, child, Quoted  # noqa: E402

CX, CY = 146.558, 98.679                      # XVF3800 centre = board centre
ROT_GROUP = ["U301", "FB301", "U501", "C501", "R501"] + [f"C3{i:02d}" for i in range(1, 20)]
FLASH = {"U401": (140.5, 94.16, 180.0), "C401": (139.15, 91.3, 180.0), "R401": (141.85, 91.29, 180.0)}
XTAL = {"Y301": (150.75, 90.12, 180.0), "R301": (150.2, 92.95, -90.0), "R302": (151.3, 92.95, -90.0),
        "C320": (153.46, 90.12, 90.0), "C321": (148.04, 90.12, 90.0)}
LDO = ["U203", "C208", "C209"]
LDO_BOX = (157.1, 86.0, 162.0, 100.0)         # where the LDO group may go (bottom side)

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p


def flip_to_bottom(part):
    """Move a top-side footprint to the bottom, as KiCad's flip does: every local y is negated,
    F.* layers become B.*, and texts get a 'mirror' justification. The (at ...) is kept."""
    def swap(tok):
        return Quoted("B." + tok[2:]) if isinstance(tok, str) and tok.startswith("F.") else tok

    def walk(node, is_root):
        for item in node:
            if not isinstance(item, list) or not item:
                continue
            head = item[0]
            if head in ("layer", "layers"):
                item[1:] = [swap(t) for t in item[1:]]
            elif head in ("at", "start", "end", "center", "mid", "xy") and not is_root:
                item[2] = f"{-float(item[2]):.6g}"
            elif head == "effects" and not child(item, "justify"):
                item.append(["justify", "mirror"])
            elif head == "justify" and "mirror" not in item:
                item.append("mirror")
            if head != "at":
                walk(item, False)

    walk(part.node, True)
    part.side = "B.Cu"


def pad_xy(ref, pin, pose=None):
    p = P[ref]
    x, y, r = pose if pose else p.at
    for pd, poly in zip(children(p.node, "pad"), p.pads(x, y, r)):
        if str(pd[1]) == str(pin):
            b = bbox(poly)
            return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def shapes(ref, pose=None):
    p = P[ref]
    x, y, r = pose if pose else p.at
    return ([p.courtyard(x, y, r)] if p.local_box("CrtYd") else []) + p.pads(x, y, r)


# 1. rotate the XVF3800 group (KiCad sense: +90 = counter-clockwise on screen)
for g in ROT_GROUP:
    x, y, r = P[g].at
    P[g].place(CX + (y - CY), CY - (x - CX), norm(r + 90))
# 2. flash and crystal
for ref, pose in {**FLASH, **XTAL}.items():
    P[ref].place(*pose)
# 3. LDO group to the bottom, then search its pose
for g in LDO:
    flip_to_bottom(P[g])
gx = sum(P[g].at[0] for g in LDO) / 3
gy = sum(P[g].at[1] for g in LDO) / 3
rel = {g: (P[g].at[0] - gx, P[g].at[1] - gy, P[g].at[2]) for g in LDO}
obs = []
for ref, p in P.items():
    if ref in LDO:
        continue
    if p.side == "B.Cu" or ref.startswith(("J10", "H", "SW", "MK")):
        obs += shapes(ref) if p.side == "B.Cu" else p.pads(only_th=True)
target = pad_xy("C315", 1)                      # +1V8 cap of pin 17
best = None
for ang in (0, 90, 180, 270):
    a = math.radians(ang)
    x = LDO_BOX[0]
    while x <= LDO_BOX[2]:
        y = LDO_BOX[1]
        while y <= LDO_BOX[3]:
            poses = {g: (x + dx * math.cos(a) + dy * math.sin(a), y - dx * math.sin(a) + dy * math.cos(a),
                         norm(r + ang)) for g, (dx, dy, r) in rel.items()}
            sh = [s for g in LDO for s in shapes(g, poses[g])]
            inside = all(LDO_BOX[0] <= px <= LDO_BOX[2] + 2 and LDO_BOX[1] - 2 <= py <= LDO_BOX[3] + 2
                         for s in sh for px, py in s)
            if inside:
                vin, vout = pad_xy("U203", 1, poses["U203"]), pad_xy("U203", 5, poses["U203"])
                if vin[0] > vout[0] + 1.0 and not any(overlap(s, o) for s in sh for o in obs):
                    cost = math.dist(vout, target) + 0.5 * math.dist(pad_xy("C209", 1, poses["C209"]), vout)
                    if best is None or cost < best[0]:
                        best = (cost, ang, poses)
            y += 0.25
        x += 0.25
        x = round(x, 3)
if best is None:
    sys.exit("no clash-free LDO pose found")
for g, pose in best[2].items():
    P[g].place(*pose)
print("LDO", {g: tuple(round(v, 3) for v in P[g].at) for g in LDO},
      "IN", tuple(round(v, 2) for v in pad_xy("U203", 1)), "OUT", tuple(round(v, 2) for v in pad_xy("U203", 5)))

# 4. clash check: every moved part against everything on its side and through-hole parts
moved = ROT_GROUP + list(FLASH) + list(XTAL) + LDO
clash = []
for g in moved:
    for ref, p in P.items():
        if ref == g:
            continue
        if p.side != P[g].side and not ref.startswith(("J10", "H", "SW", "MK")):
            continue
        other = shapes(ref) if p.side == P[g].side else p.pads(only_th=True)
        if any(overlap(s, o) for s in shapes(g) for o in other):
            clash.append("/".join(sorted((g, ref))))
print("overlaps:", sorted(set(clash)) or "none")
if "--dry-run" not in sys.argv:
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)
