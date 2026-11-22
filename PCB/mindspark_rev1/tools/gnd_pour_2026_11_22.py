"""GND pours on F.Cu and B.Cu, and a 5 mm grid of GND stitching vias (user 2026-11-22).

Runs on the board power_v2 wrote (power_v2 rebuilds every via and zone, so run this after it).

Agreed with the user (2026-11-22):
  * GND pours on both outer layers, whole board, 0.2 mm from other nets. The U103 flange pours
    (priority 10) fill first; these sit at priority 0 and go round them.
  * Thermal spokes on small passives (R, C, L, FB in 0402 / 0603); solid everywhere else.
  * At least 0.5 mm of pour gap beside the USB pairs: a no-pour rule area round every USB track
    (0.5 mm past its copper; a custom .kicad_dru rule was tried first, but kicad-cli 10 never loads
    it), and no stitching via within 0.5 mm of them or of the mic lines.
  * Stitching vias 0.45/0.2 on one even 5 mm lattice. Its outer ring sits 2 mm inside the board
    edge, so the edge row is part of the grid (74 mm board: 2 + 14 x 5 + 2), 15 x 15 = 225 points.
    Kept at about 5 mm (not 3 mm) so the board stays under JLC's 150k holes/m² drill density.
  * A grid via may move up to 0.3 mm to find room; if it still clashes, it is dropped. Dropped when:
      - it would break clearance to any other copper or a pad (0.2 mm; holes 0.25 mm),
      - it is within 0.5 mm of a USB pair or a mic line,
      - after the fill it would not sit in filled GND on both F.Cu and B.Cu,
      - its In2 clearance hole (1.05 mm across) would take more than 30 % of the width of the
        In2 power strip it lands in (no plane cuts for signals or stitching).

Steps: (1) take out an earlier run's pours and stitching vias, (2) thermal overrides, (3) add the
two pours keeping islands and fill them with kicad-cli, (4) pick the via spots against the fill,
(5) add the vias, switch island removal on and fill again (kicad-cli DRC writes the report).

Usage (PCB editor closed):  python3 tools/gnd_pour_2026_11_22.py [--board FILE]
"""
import json
import math
import os
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from place_tidy import BOARD, LEFT, RIGHT, TOP, BOTTOM, Part  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402
from jog_router import Shape, _inside, _dist_point_seg  # noqa: E402

board = sys.argv[sys.argv.index("--board") + 1] if "--board" in sys.argv else BOARD
# the vias this script placed last time (a test copy elsewhere keeps its own record beside it)
RECORD = (os.path.join(HERE, "gnd_stitch_2026_11_22.json") if os.path.samefile(board, BOARD)
          else os.path.splitext(board)[0] + "-gnd-stitch.json")

VIA = (0.45, 0.2)              # stitching via: diameter, drill
R = VIA[0] / 2
PITCH = 5.0
MARGIN = 2.0                   # lattice outer ring (= edge row) this far inside the board edge
NUDGE = 0.3                    # how far a grid via may move to find room
CLEAR = 0.2                    # via copper to other copper / pads
HOLE_CLEAR = 0.25              # via copper to a plain hole (mic sound ports)
SENSITIVE_CLEAR = 0.5          # via copper to USB pairs and mic lines
IN2_HOLE = VIA[0] + 2 * 0.3    # the via's clearance hole in the In2 power plane (zone clearance 0.3)
IN2_MAX_CUT = 0.30             # largest share of a strip's width that hole may take
POUR_CLEAR = 0.2
POUR_NAMES = {"F.Cu": "GND F.Cu pour", "B.Cu": "GND B.Cu pour"}
USB_GAP = 0.5                  # pour kept this far from USB pair copper
USB_GAP_NAME = "USB pour gap"

USB_NETS = ["/USB_MAIN_DP", "/USB_MAIN_DM", "/USB_ESP_DP", "/USB_ESP_DM",
            "/esp32/ESP_USB_DP", "/esp32/ESP_USB_DM"]
MIC_NETS = ["/MIC_CLK", "/MIC_DATA0", "/MIC_DATA1", "/MIC_DATA2", "/MIC_DATA3",
            "Net-(R501-Pad1)", "Net-(R501-Pad2)",
            "Net-(MK501-CLK)", "Net-(MK502-CLK)", "Net-(MK503-CLK)", "Net-(MK504-CLK)"]
SENSITIVE = set(USB_NETS) | set(MIC_NETS)

# Small passives get thermal spokes (less tombstoning on the small pads during reflow)
THERMAL_PREFIXES = ("R", "C", "L", "FB")
THERMAL_SIZES = ("0402", "0603")


def f4(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def uid():
    return q(str(uuid.uuid4()))


def net_of(node):
    n = child(node, "net")
    return str(n[1]) if n else ""


def xy(node, name):
    n = child(node, name)
    return (float(n[1]), float(n[2]))


def fill(path):
    """Fill every zone and save, through KiCad's own DRC run; returns the report path."""
    rpt = (os.path.join(HERE, "..", "verification", "gnd_pour_drc_2026_11_22.rpt") if path == board == BOARD
           or os.path.samefile(path, BOARD) else os.path.splitext(path)[0] + "-gnd-drc.rpt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--refill-zones", "--save-board", "-o", rpt, path],
                   check=False, stdout=subprocess.DEVNULL)
    return rpt


# ================================================================ 1. earlier run out
root = parse(open(board).read())
old, old_ties = [], []
if os.path.exists(RECORD):
    rec_ = json.load(open(RECORD))
    old = [tuple(p) for p in rec_["vias"]]
    old_ties = [(L, tuple(a), tuple(b)) for L, a, b in rec_.get("ties", [])]


def is_old_stitch(n):
    if n[0] == "segment" and net_of(n) == "GND":
        return any(str(child(n, "layer")[1]) == L and math.dist(xy(n, "start"), a) < 1e-3
                   and math.dist(xy(n, "end"), b) < 1e-3 for L, a, b in old_ties)
    if n[0] != "via" or net_of(n) != "GND":
        return False
    at = xy(n, "at")
    return any(math.dist(at, p) < 1e-3 for p in old)


before = len(root)
root[:] = [n for n in root if not (isinstance(n, list) and n and (
    (n[0] == "zone" and child(n, "name")
     and str(child(n, "name")[1]) in list(POUR_NAMES.values()) + [USB_GAP_NAME])
    or is_old_stitch(n)))]
print(f"removed {before - len(root)} items of an earlier run")

# ================================================================ 2. thermal spokes on small passives
parts = [Part(f) for f in children(root, "footprint")]
thermal = []
for p in parts:
    fpname = str(p.node[1])
    prefix = "".join(ch for ch in p.ref if ch.isalpha())
    if prefix in THERMAL_PREFIXES and any(s in fpname for s in THERMAL_SIZES):
        # Only the GND pads: a footprint-wide setting would also put spokes on pads inside the
        # U103 flange pours (C101, C104), which carry 3 A and must stay solid.
        # Pad override: 1 = thermal reliefs (the pours themselves connect solid).
        for pd in children(p.node, "pad"):
            if net_of(pd) != "GND":
                continue
            zc = child(pd, "zone_connect")
            if zc:
                zc[1] = "1"
            else:
                pd.append(["zone_connect", "1"])
            thermal.append(p.ref)
thermal = sorted(set(thermal))
print(f"thermal spokes on {len(thermal)} small passives")


# ================================================================ 3. the two pours, first fill
def pour(layer, islands):
    return ["zone", ["net", q("GND")], ["layer", q(layer)], ["uuid", uid()], ["name", q(POUR_NAMES[layer])],
            ["hatch", "edge", "0.5"],
            ["connect_pads", "yes", ["clearance", f4(POUR_CLEAR)]],
            ["min_thickness", "0.2"], ["filled_areas_thickness", "no"],
            ["fill", "yes", ["thermal_gap", "0.25"], ["thermal_bridge_width", "0.25"],
             ["island_removal_mode", islands]],
            ["polygon", ["pts"] + [["xy", f4(x), f4(y)] for x, y in
                                   ((LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM))]]]


# keep islands on the first fill (mode 1), so a via may land in one and tie it down
root.extend([pour("F.Cu", "1"), pour("B.Cu", "1")])


def usb_gap_area(layer, a, b, w):
    """No-pour rule area: the track's rectangle grown by USB_GAP past its copper on every side
    (square ends, so it also covers the round track end)."""
    off = w / 2 + USB_GAP
    L = math.dist(a, b)
    ux, uy = ((b[0] - a[0]) / L, (b[1] - a[1]) / L) if L > 1e-9 else (1.0, 0.0)
    nx, ny = -uy, ux
    pts = [(a[0] - ux * off + nx * off, a[1] - uy * off + ny * off),
           (b[0] + ux * off + nx * off, b[1] + uy * off + ny * off),
           (b[0] + ux * off - nx * off, b[1] + uy * off - ny * off),
           (a[0] - ux * off - nx * off, a[1] - uy * off - ny * off)]
    return ["zone", ["net", q("")], ["layer", q(layer)], ["uuid", uid()], ["name", q(USB_GAP_NAME)],
            ["hatch", "edge", "0.5"], ["connect_pads", ["clearance", "0"]], ["min_thickness", "0.25"],
            ["filled_areas_thickness", "no"],
            ["keepout", ["tracks", "allowed"], ["vias", "allowed"], ["pads", "allowed"],
             ["copperpour", "not_allowed"], ["footprints", "allowed"]],
            ["fill", ["thermal_gap", "0.5"], ["thermal_bridge_width", "0.5"]],
            ["polygon", ["pts"] + [["xy", f4(x), f4(y)] for x, y in pts]]]


n_gap = 0
for n in children(root, "segment"):
    if net_of(n) in USB_NETS and str(child(n, "layer")[1]) in POUR_NAMES:
        root.append(usb_gap_area(str(child(n, "layer")[1]), xy(n, "start"), xy(n, "end"),
                                 float(child(n, "width")[1])))
        n_gap += 1
print(f"USB pour gap: {n_gap} no-pour areas")
open(board, "w").write(dump(root) + "\n")
fill(board)
root = parse(open(board).read())

# ================================================================ 4. obstacles and fill read back
shapes = []          # (Shape, clearance it needs from a stitching via)


def need(net):
    if net == "~hole":
        return HOLE_CLEAR
    return SENSITIVE_CLEAR if net in SENSITIVE else CLEAR


for f in children(root, "footprint"):
    p = Part(f)
    for pd, poly in zip(children(f, "pad"), p.pads()):
        kind = str(pd[2])
        lays = [str(x) for x in (child(pd, "layers") or [])[1:]]
        if kind in ("thru_hole", "np_thru_hole"):
            layers = {"F.Cu", "B.Cu"}
        else:
            layers = {x for x in lays if x in ("F.Cu", "B.Cu")} or (
                {str(p.side)} if any(x.endswith(".Cu") for x in lays) else set())
        if not layers:
            continue                                   # paste-only windows
        net = "~hole" if kind == "np_thru_hole" else net_of(pd)
        # every pad is an obstacle, GND ones too: no stitching via lands on a solder pad
        shapes.append((Shape(net if net else "~nonet", layers, poly=poly), need(net)))

stitch_old = []
for n in children(root, "segment"):
    net = net_of(n)
    shapes.append((Shape(net, {str(child(n, "layer")[1])}, seg=(xy(n, "start"), xy(n, "end"),
                                                                float(child(n, "width")[1]))), need(net)))
for n in children(root, "arc"):
    net = net_of(n)
    a, m, b = xy(n, "start"), xy(n, "mid"), xy(n, "end")
    # circle through the three points, sampled every ~0.3 mm
    ax, ay, bx, by, cx_, cy_ = a[0], a[1], m[0], m[1], b[0], b[1]
    d = 2 * (ax * (by - cy_) + bx * (cy_ - ay) + cx_ * (ay - by))
    ux = ((ax * ax + ay * ay) * (by - cy_) + (bx * bx + by * by) * (cy_ - ay) + (cx_ * cx_ + cy_ * cy_) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx_ - bx) + (bx * bx + by * by) * (ax - cx_) + (cx_ * cx_ + cy_ * cy_) * (bx - ax)) / d
    rad = math.dist((ux, uy), a)
    t0, tm, t1 = (math.atan2(p_[1] - uy, p_[0] - ux) for p_ in (a, m, b))

    def ccw(s, e):
        return (e - s) % (2 * math.pi)
    span = ccw(t0, t1) if ccw(t0, tm) < ccw(t0, t1) else -ccw(t1, t0)
    k = max(2, int(abs(span) * rad / 0.3) + 1)
    pts = [(ux + rad * math.cos(t0 + span * i / k), uy + rad * math.sin(t0 + span * i / k)) for i in range(k + 1)]
    w = float(child(n, "width")[1])
    for s_, e_ in zip(pts, pts[1:]):
        shapes.append((Shape(net, {str(child(n, "layer")[1])}, seg=(s_, e_, w)), need(net)))
for n in children(root, "via"):
    net = net_of(n)
    shapes.append((Shape(net, {"F.Cu", "B.Cu"}, circle=(xy(n, "at"), float(child(n, "size")[1]) / 2)),
                   need(net)))

filled = {"F.Cu": [], "B.Cu": []}      # GND pour fill polygons per layer
in2 = []                               # (net, priority, outline) of the In2 power planes
for z in children(root, "zone"):
    name = str(child(z, "name")[1]) if child(z, "name") else ""
    layer = str(child(z, "layer")[1]) if child(z, "layer") else ""
    outline = [(float(c[1]), float(c[2])) for c in child(child(z, "polygon"), "pts")[1:]]
    if name in POUR_NAMES.values():
        for fp in children(z, "filled_polygon"):
            poly = [(float(c[1]), float(c[2])) for c in child(fp, "pts")[1:] if c[0] == "xy"]
            xs, ys = [p_[0] for p_ in poly], [p_[1] for p_ in poly]
            filled[str(child(fp, "layer")[1])].append((poly, (min(xs), min(ys), max(xs), max(ys))))
    elif layer in ("F.Cu", "B.Cu"):
        # other pours on the outer layers (the U103 flanges) are copper of their net
        shapes.append((Shape(net_of(z), {layer}, poly=outline), need(net_of(z))))
    elif layer == "In2.Cu":
        pr = child(z, "priority")
        in2.append((net_of(z), int(pr[1]) if pr else 0, outline))


def in2_owner(pt):
    best = None
    for net, pri, poly in in2:
        if _inside(pt[0], pt[1], poly) and (best is None or pri > best[1]):
            best = (net, pri)
    return best[0] if best else None


def in2_width(pt):
    """Narrowest width of the In2 plane strip at pt, measured along 0/45/90/135 degrees."""
    own = in2_owner(pt)
    widths = []
    for ang in (0, 45, 90, 135):
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        span = 0.0
        for sgn in (1, -1):
            d = 0.0
            while d < 15.0:
                d += 0.05
                x_, y_ = pt[0] + sgn * ux * d, pt[1] + sgn * uy * d
                if not (LEFT + 0.3 <= x_ <= RIGHT - 0.3 and TOP + 0.3 <= y_ <= BOTTOM - 0.3) \
                        or in2_owner((x_, y_)) != own:
                    break
            span += d
        widths.append(span)
    return min(widths)


def in_fill(pt, layer):
    """The whole via (plus 0.05 mm) sits inside the GND fill on that layer."""
    for poly, box in filled[layer]:
        if not (box[0] <= pt[0] <= box[2] and box[1] <= pt[1] <= box[3]):
            continue
        if not _inside(pt[0], pt[1], poly):
            continue
        # distance to the fill's outline (_dist_point_poly gives 0 inside, so measure the edges).
        # KiCad stores holes as part of the outline through zero-width slits; a via on a slit is
        # turned away too, and the nudge moves it off.
        n_ = len(poly)
        edge = min(_dist_point_seg(pt[0], pt[1], *poly[i], *poly[(i + 1) % n_]) for i in range(n_))
        if edge >= R + 0.05:
            return True
    return False


def clash(pt, fill_check=None):
    """Name of the first rule a via at pt breaks, or None. fill_check(pt) replaces the
    'in GND fill on both outer layers' test (the island pass checks its own island instead)."""
    if not (LEFT + 0.3 + R <= pt[0] <= RIGHT - 0.3 - R and TOP + 0.3 + R <= pt[1] <= BOTTOM - 0.3 - R):
        return "edge"
    for sh, gap in near:
        if sh.net == "GND" and not sh.poly and gap == CLEAR:
            # GND tracks may touch; other GND vias keep the drill spacing (centres 0.65 apart)
            if sh.circle and math.dist(sh.circle[0], pt) < R + sh.circle[1] + CLEAR:
                return "GND via"
            continue
        if sh.dist(*pt) < R + gap:
            return "USB/mic line" if gap == SENSITIVE_CLEAR else ("hole" if gap == HOLE_CLEAR else "copper")
    if fill_check is not None:
        if not fill_check(pt):
            return "no fill"
    elif not in_fill(pt, "F.Cu") or not in_fill(pt, "B.Cu"):
        return "no fill"
    if IN2_HOLE / in2_width(pt) > IN2_MAX_CUT:
        return "In2 strip"
    return None


# candidate offsets, nearest first: 0.05 mm steps inside the nudge radius
offsets = sorted({(round(i * 0.05, 3), round(j * 0.05, 3)) for i in range(-6, 7) for j in range(-6, 7)
                  if math.hypot(i * 0.05, j * 0.05) <= NUDGE + 1e-9}, key=lambda o: math.hypot(*o))
n_side = int(round((RIGHT - LEFT - 2 * MARGIN) / PITCH)) + 1
lattice = [(LEFT + MARGIN + i * PITCH, TOP + MARGIN + j * PITCH) for j in range(n_side) for i in range(n_side)]
placed, nudged, dropped = [], 0, {}
for g in lattice:
    near = [(sh, gap) for sh, gap in shapes
            if sh.box[0] - 1.5 <= g[0] <= sh.box[2] + 1.5 and sh.box[1] - 1.5 <= g[1] <= sh.box[3] + 1.5]
    first_why = None
    for o in offsets:
        pt = (round(g[0] + o[0], 3), round(g[1] + o[1], 3))
        why = clash(pt)
        if why is None:
            placed.append(pt)
            nudged += o != (0.0, 0.0)
            break
        first_why = first_why or why
    else:
        dropped[first_why] = dropped.get(first_why, 0) + 1
print(f"lattice {n_side} x {n_side} = {len(lattice)} points: {len(placed)} vias ({nudged} nudged), "
      f"dropped {sum(dropped.values())} {dropped}")

# ================================================================ 4b. a via for every pour island
# (user 2026-11-22) Patches of pour boxed in by tracks with no grid via used to be removed as
# islands, leaving big voids. Each patch of at least ISLAND_MIN mm² that touches no GND copper now
# gets one via of its own, off the grid, wherever it fits nearest the patch's middle; it only has
# to sit in that patch (it reaches In1 GND anyway). Patches with no room are still removed.
ISLAND_MIN = 2.0


def area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly)))) / 2


def edge_dist(pt, poly):
    n_ = len(poly)
    return min(_dist_point_seg(pt[0], pt[1], *poly[i], *poly[(i + 1) % n_]) for i in range(n_))


gnd_shapes = [sh for sh, gap in shapes if sh.net == "GND"]
gnd_shapes += [Shape("GND", {"F.Cu", "B.Cu"}, circle=(pt, R)) for pt in placed]
island_vias, no_room = [], []
for layer in ("F.Cu", "B.Cu"):
    for poly, box in filled[layer]:
        if area(poly) < ISLAND_MIN:
            continue
        # touches GND copper (pad, track or via of GND on this layer) = not an island
        hits = [sh for sh in gnd_shapes if layer in sh.layers
                and sh.box[0] <= box[2] and sh.box[2] >= box[0] and sh.box[1] <= box[3] and sh.box[3] >= box[1]]
        mid = lambda sh: (((sh.box[0] + sh.box[2]) / 2), ((sh.box[1] + sh.box[3]) / 2))
        if any(_inside(*mid(sh), poly) or any(sh.dist(*v) < 0.02 for v in poly) for sh in hits):
            continue
        cx_, cy_ = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        cands = [(round(box[0] + i * 0.1, 3), round(box[1] + j * 0.1, 3))
                 for i in range(int((box[2] - box[0]) / 0.1) + 1) for j in range(int((box[3] - box[1]) / 0.1) + 1)]
        cands = [c for c in cands if _inside(c[0], c[1], poly)]
        cands.sort(key=lambda c: math.dist(c, (cx_, cy_)))
        got = None
        for c in cands:
            near = [(sh, gap) for sh, gap in shapes
                    if sh.box[0] - 1.5 <= c[0] <= sh.box[2] + 1.5 and sh.box[1] - 1.5 <= c[1] <= sh.box[3] + 1.5]
            near += [(Shape("GND", {"F.Cu", "B.Cu"}, circle=(v, R)), CLEAR) for v in placed + island_vias]
            if clash(c, fill_check=lambda p_: edge_dist(p_, poly) >= R + 0.05) is None:
                got = c
                break
        if got:
            island_vias.append(got)
        else:
            no_room.append((layer, poly, box))
placed += island_vias

# (user 2026-11-22) no floating islands: a patch with no room for a via is tied to the nearest GND
# pad / via / track on its layer by one short straight trace (0/45/90 degrees, as the jog style),
# laid from the GND item outward until it is well inside the patch. Unreachable patches are removed.
TIE_W, TIE_MAX = 0.2, 3.0
ties, tie_fail = [], 0


def seg_clear(a, b, layer):
    """The trace a-b keeps its clearance from every other net's copper on that layer."""
    k = max(1, int(math.dist(a, b) / 0.05))
    pts_ = [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k + 1)]
    bx0, by0 = min(a[0], b[0]) - 1, min(a[1], b[1]) - 1
    bx1, by1 = max(a[0], b[0]) + 1, max(a[1], b[1]) + 1
    for sh, gap in shapes:
        if sh.net == "GND" or layer not in sh.layers or sh.box[2] < bx0 or sh.box[0] > bx1 \
                or sh.box[3] < by0 or sh.box[1] > by1:
            continue
        if any(sh.dist(*p_) < TIE_W / 2 + gap for p_ in pts_):
            return False
    return LEFT + 0.5 < min(a[0], b[0]) and max(a[0], b[0]) < RIGHT - 0.5 \
        and TOP + 0.5 < min(a[1], b[1]) and max(a[1], b[1]) < BOTTOM - 0.5


for layer, poly, box in no_room:
    best = None
    for sh in gnd_shapes:
        if layer not in sh.layers or sh.box[2] < box[0] - TIE_MAX or sh.box[0] > box[2] + TIE_MAX \
                or sh.box[3] < box[1] - TIE_MAX or sh.box[1] > box[3] + TIE_MAX:
            continue
        # start on the item: a pad's or via's centre, or points along a track
        if sh.seg:
            (ax, ay), (bx, by), _ = sh.seg
            n_ = max(1, int(math.dist((ax, ay), (bx, by)) / 0.25))
            starts = [(ax + (bx - ax) * i / n_, ay + (by - ay) * i / n_) for i in range(n_ + 1)]
        else:
            starts = [(((sh.box[0] + sh.box[2]) / 2), ((sh.box[1] + sh.box[3]) / 2))]
        for st in starts:
            for ang in range(0, 360, 45):
                ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                d = 0.1
                while d <= TIE_MAX:
                    e = (round(st[0] + ux * d, 3), round(st[1] + uy * d, 3))
                    if _inside(e[0], e[1], poly) and edge_dist(e, poly) >= TIE_W / 2 + 0.15:
                        if (best is None or d < best[0]) and seg_clear(st, e, layer):
                            best = (d, st, e)
                        break
                    d += 0.05
    if best:
        ties.append((layer, best[1], best[2]))
    else:
        tie_fail += 1
print(f"pour islands: {len(island_vias)} got a via of their own, {len(ties)} a short GND trace, "
      f"{tie_fail} unreachable (removed)")

# ================================================================ 5. vias in, islands off, final fill
for pt in placed:
    root.append(["via", ["at", f4(pt[0]), f4(pt[1])], ["size", f4(VIA[0])], ["drill", f4(VIA[1])],
                 ["layers", q("F.Cu"), q("B.Cu")], ["net", q("GND")], ["uuid", uid()]])
for layer, a, b in ties:
    root.append(["segment", ["start", f4(a[0]), f4(a[1])], ["end", f4(b[0]), f4(b[1])], ["width", f4(TIE_W)],
                 ["layer", q(layer)], ["net", q("GND")], ["uuid", uid()]])
for z in children(root, "zone"):
    if child(z, "name") and str(child(z, "name")[1]) in POUR_NAMES.values():
        child(child(z, "fill"), "island_removal_mode")[1] = "0"
open(board, "w").write(dump(root) + "\n")
rpt = fill(board)

# A small passive's GND pad that ends up with fewer than two spokes (e.g. C313 beside a USB
# no-pour area) goes back to a solid connection; then fill once more.
import re  # noqa: E402
starved = set()
lines = open(rpt).read().splitlines()
for i, line in enumerate(lines):
    if line.startswith("[starved_thermal]"):
        for nxt in lines[i + 1:i + 4]:
            m = re.search(r"Pad (\S+) \[GND\] of (\S+)", nxt)
            if m and m.group(2) in thermal:
                starved.add((m.group(2), m.group(1)))
if starved:
    root = parse(open(board).read())
    for f in children(root, "footprint"):
        ref = Part(f).ref
        for pd in children(f, "pad"):
            if (ref, str(pd[1])) in starved and child(pd, "zone_connect"):
                child(pd, "zone_connect")[1] = "2"
    open(board, "w").write(dump(root) + "\n")
    rpt = fill(board)
    print(f"solid again (too few spokes): {sorted(starved)}")
json.dump({"vias": placed, "ties": ties, "dropped": dropped}, open(RECORD, "w"), indent=1)

holes = sum(1 for _ in children(parse(open(board).read()), "via"))
print(f"vias on the board now: {holes}; DRC report: {rpt}")
