"""Tidy the rough rev 1 placement (user's rules, 2026-11-12).

Usage (KiCad must be closed):
    python3 tools/place_tidy.py              # rewrite mindspark_rev1.kicad_pcb and print a report
    python3 tools/place_tidy.py --dry-run    # report only

Why this exists: KiCad's Python API (pcbnew.LoadBoard) segfaults on this machine, so the
board file is edited as S-expressions with tools/sexpr.py. Only the parts that sit inside
the board outline are moved; the parts parked off the board are left untouched.

KiCad conventions this script relies on (checked against a kicad-cli IPC-2581 export):
  * A footprint at (X, Y, rot) maps a local point (x, y) to
        (X + x*cos(rot) + y*sin(rot),  Y - x*sin(rot) + y*cos(rot))
    for top AND bottom footprints (bottom-side local coordinates are stored already mirrored).
  * Pad and text angles in the file are absolute, so a rotation change must be added to
    every pad and text angle of that footprint as well.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, dump, children, child, Quoted  # noqa: E402

BOARD = os.path.join(HERE, "..", "mindspark_rev1.kicad_pcb")
CONTROLLER = os.path.expanduser(
    "~/Z/projects/internship/stealth_startup/diff-drive-robot/hardware/electrical/kicad/"
    "controller-board_rev1_4/controller-board_rev1_4.kicad_pcb")

# ---------------------------------------------------------------- board geometry
CX, CY = 146.558, 98.679          # board centre, kept from the user's 70 mm outline
SIZE = 74.0                       # grown from 70 mm so the 66 mm mic square sits 4 mm in
LEFT, RIGHT = CX - SIZE / 2, CX + SIZE / 2
TOP, BOTTOM = CY - SIZE / 2, CY + SIZE / 2

EDGE_COPPER = 0.3                 # JLC minimum copper-to-board-edge
CLEAR = 0.25                      # courtyard-to-courtyard clearance used for the ring search
HOLE_INSET = 10.0                 # mounting holes: same inset from both edges
TP_INSET = 1.5                    # test-pad rows: pad centre this far in from the edge
USB_INSET = 3.015                 # USB-C origin inside the edge (controller board rev 1.4)
JST_INSET = 5.67                  # JST PH side-entry origin inside the edge (controller board)
MIC_SQUARE = 66.0                 # XMOS XK-VOICE-SQ66 mic square, measured on the sound ports
MIC_PORT = 0.71                   # sound-port NPTH offset in the IM69D129 footprint (local +x)


# ---------------------------------------------------------------- small geometry helpers
def to_board(fx, fy, rot, x, y):
    """Local footprint point -> board point (KiCad convention, see module docstring)."""
    a = math.radians(rot)
    return (fx + x * math.cos(a) + y * math.sin(a),
            fy - x * math.sin(a) + y * math.cos(a))


def rect_pts(cx, cy, w, h, ang=0.0):
    """Corners of a w x h rectangle centred on (cx, cy), turned by ang (KiCad sense)."""
    return [to_board(cx, cy, ang, sx * w / 2, sy * h / 2)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def circle_pts(cx, cy, r, n=16):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def overlap(p, q):
    """Separating-axis test for two convex polygons (lists of points)."""
    for poly in (p, q):
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            nx, ny = y1 - y2, x2 - x1
            a = [nx * x + ny * y for x, y in p]
            b = [nx * x + ny * y for x, y in q]
            if max(a) < min(b) or max(b) < min(a):
                return False
    return True


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- footprint access
class Part:
    """Thin wrapper round one footprint node of the board."""

    def __init__(self, node):
        self.node = node
        self.props = {p[1]: p[2] for p in children(node, "property")}
        self.ref = str(self.props["Reference"])
        self.side = child(node, "layer")[1]

    # position ---------------------------------------------------------------
    @property
    def at(self):
        a = child(self.node, "at")
        return float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else 0.0

    def place(self, x, y, rot=None):
        """Move the footprint; on a rotation change, turn every pad and text with it."""
        old = self.at[2]
        rot = old if rot is None else rot
        delta = rot - old
        a = child(self.node, "at")
        a[1:] = [fmt(x), fmt(y)] + ([fmt(norm(rot))] if norm(rot) != 0 else [])
        if abs(delta) > 1e-9:
            for item in children(self.node, "pad") + children(self.node, "property") + \
                    children(self.node, "fp_text"):
                ia = child(item, "at")
                if ia is None:
                    continue
                # (at x y [angle] [unlocked]): keep any trailing keyword such as 'unlocked'
                has_ang = len(ia) > 3 and ia[3] != "unlocked"
                ang = float(ia[3]) if has_ang else 0.0
                extra = ia[4:] if has_ang else ia[3:]
                ia[1:] = ia[1:3] + [fmt(norm(ang + delta))] + extra

    def flip_to_top(self):
        """Move a bottom-side footprint to the top side, as KiCad's top/bottom flip does.

        A bottom footprint is stored as the library footprint with every local y negated
        and its layers swapped to B.*. So flipping back means: negate local y again
        (pads, graphics, texts and custom-pad primitives), swap B.* -> F.*, and drop the
        'mirror' text justification. The footprint's own (at ...) is not touched here.
        """
        if self.side == "F.Cu":
            return

        def swap(tok):
            if isinstance(tok, str) and tok.startswith("B."):
                return Quoted("F." + tok[2:])
            return tok

        def walk(node, is_root):
            for i, item in enumerate(node):
                if not isinstance(item, list) or not item:
                    continue
                head = item[0]
                if head in ("layer", "layers"):
                    item[1:] = [swap(t) for t in item[1:]]
                elif head in ("at", "start", "end", "center", "mid", "xy") and not is_root:
                    item[2] = fmt(-float(item[2]))          # mirror local y
                elif head == "justify" and "mirror" in item:
                    item.remove("mirror")
                if head not in ("at",):
                    walk(item, False)
            # an empty (justify) left behind would be harmless, but remove it for tidiness
            node[:] = [n for n in node if not (isinstance(n, list) and n == ["justify"])]

        walk(self.node, True)
        self.side = "F.Cu"

    # geometry in local coordinates -----------------------------------------
    def local_box(self, layer_suffix):
        """Bounding box of the graphics on e.g. 'CrtYd' or 'Fab' layers (local coords)."""
        xs, ys = [], []
        for g in self.node[1:]:
            if not (isinstance(g, list) and g[0].startswith("fp_") and child(g, "layer")):
                continue
            if not child(g, "layer")[1].endswith(layer_suffix):
                continue
            if g[0] == "fp_circle":
                cxy, exy = child(g, "center"), child(g, "end")
                cx, cy = float(cxy[1]), float(cxy[2])
                rad = math.hypot(float(exy[1]) - cx, float(exy[2]) - cy)
                xs += [cx - rad, cx + rad]
                ys += [cy - rad, cy + rad]
                continue
            pts = [child(g, k) for k in ("start", "end", "center") if child(g, k)]
            if child(g, "pts"):
                pts += [p for p in child(g, "pts")[1:] if isinstance(p, list)]
            for p in pts:
                xs.append(float(p[1]))
                ys.append(float(p[2]))
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    def courtyard(self, x=None, y=None, rot=None):
        """Courtyard as a board polygon (optionally for a trial position)."""
        fx, fy, fr = self.at
        x, y, rot = (fx if x is None else x), (fy if y is None else y), (fr if rot is None else rot)
        b = self.local_box("CrtYd")
        return [to_board(x, y, rot, px, py) for px, py in
                ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))]

    def pads(self, x=None, y=None, rot=None, only_th=False):
        """Copper shapes of the pads as board polygons. Through holes count on both sides."""
        fx, fy, fr = self.at
        x, y, rot = (fx if x is None else x), (fy if y is None else y), (fr if rot is None else rot)
        out = []
        for p in children(self.node, "pad"):
            kind, shape = p[2], p[3]
            if only_th and kind not in ("thru_hole", "np_thru_hole"):
                continue
            pa = child(p, "at")
            px, py = float(pa[1]), float(pa[2])
            rel = (float(pa[3]) if len(pa) > 3 else 0.0) - fr   # pad angle relative to footprint
            w, h = float(child(p, "size")[1]), float(child(p, "size")[2])
            cx, cy = to_board(x, y, rot, px, py)
            if shape == "custom" and child(p, "primitives"):
                # use the bounding box of the primitives (custom pads here are small polygons)
                pts = []
                for prim in child(p, "primitives")[1:]:
                    if child(prim, "pts"):
                        pts += [(float(q[1]), float(q[2])) for q in child(prim, "pts")[1:]]
                    for k in ("start", "end", "center", "mid"):
                        if child(prim, k):
                            pts.append((float(child(prim, k)[1]), float(child(prim, k)[2])))
                bx = bbox(pts)
                w, h = bx[2] - bx[0] + 0.4, bx[3] - bx[1] + 0.4   # + line width margin
            if shape == "circle":
                out.append(circle_pts(cx, cy, w / 2))
            else:
                out.append(rect_pts(cx, cy, w, h, rot + rel))
        return out


def fmt(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def norm(a):
    a = a % 360.0
    if a > 180.0 + 1e-9:
        a -= 360.0
    return round(a, 4)


# ---------------------------------------------------------------- placement helpers
def inward_offset(part, rot, edge, body_front=None):
    """Distance from the edge to the origin so the part sits right on that edge.

    Normal parts: courtyard flush with the edge, but copper at least EDGE_COPPER inside.
    Side-actuated switches pass body_front (local y of the body's front face from the
    footprint silk): the body goes flush with the edge and the actuator pokes out, again
    pulled back if copper would come closer than EDGE_COPPER.
    """
    pads = [pt for poly in part.pads(0, 0, rot) for pt in poly]
    cy = part.courtyard(0, 0, rot)
    key = {"L": lambda p: -p[0], "R": lambda p: p[0], "T": lambda p: -p[1], "B": lambda p: p[1]}[edge]
    copper = max(key(p) for p in pads) + EDGE_COPPER
    if body_front is None:
        body = max(key(p) for p in cy)
    else:
        bx, by = to_board(0, 0, rot, 0, body_front)
        body = key((bx, by))
    return max(copper, body)


def spread(parts, axis, start, end, rot_of):
    """Place parts along one axis between start and end with equal courtyard gaps.

    Returns the list of origin coordinates along that axis and the gap used.
    """
    spans = []
    for p in parts:
        b = bbox(p.courtyard(0, 0, rot_of[p.ref]))
        spans.append((b[1], b[3]) if axis == "y" else (b[0], b[2]))
    total = sum(hi - lo for lo, hi in spans)
    gap = (end - start - total) / (len(parts) + 1)
    pos, cursor = [], start
    for lo, hi in spans:
        cursor += gap
        pos.append(cursor - lo)
        cursor += hi - lo
    return pos, gap


# ---------------------------------------------------------------- main work
def main(dry_run):
    text = open(BOARD).read()
    root = parse(text)
    parts = {Part(f).ref: Part(f) for f in children(root, "footprint")}
    old_box = [g for g in children(root, "gr_rect") if child(g, "layer")[1] == "Edge.Cuts"][0]
    ox1, oy1 = float(child(old_box, "start")[1]), float(child(old_box, "start")[2])
    ox2, oy2 = float(child(old_box, "end")[1]), float(child(old_box, "end")[2])
    on_board = sorted(r for r, p in parts.items()
                      if ox1 <= p.at[0] <= ox2 and oy1 <= p.at[1] <= oy2)
    report = []

    # 0. outline and 4 layers --------------------------------------------------
    child(old_box, "start")[1:] = [fmt(LEFT), fmt(TOP)]
    child(old_box, "end")[1:] = [fmt(RIGHT), fmt(BOTTOM)]
    make_four_layer(root)
    report.append(f"board {SIZE:.0f} x {SIZE:.0f} mm, x {LEFT:.3f}-{RIGHT:.3f}, y {TOP:.3f}-{BOTTOM:.3f}, 4 layers")

    P = parts

    # 1a. USB-C, centred on each side edge -------------------------------------
    P["J102"].place(LEFT + USB_INSET, CY, -90)
    P["J101"].place(RIGHT - USB_INSET, CY, 90)

    # 1b. mounting holes, same inset from both edges ---------------------------
    holes = {"H2": (LEFT + HOLE_INSET, TOP + HOLE_INSET), "H1": (RIGHT - HOLE_INSET, TOP + HOLE_INSET),
             "H3": (LEFT + HOLE_INSET, BOTTOM - HOLE_INSET), "H4": (RIGHT - HOLE_INSET, BOTTOM - HOLE_INSET)}
    for r, (x, y) in holes.items():
        P[r].place(x, y)
    hole_r = 2.2   # M2 pad radius (4.4 mm pad)

    # 1c. JSTs on the top edge, equal gaps between the two top hole pads --------
    #     The speaker group (amp U503, TP501/TP502) moves with J501 as one block.
    jx0, jy0, _ = P["J501"].at
    group = {r: (P[r].at[0] - jx0, P[r].at[1] - jy0) for r in ("U503", "TP501", "TP502")}
    xs, gap = spread([P["J501"], P["J301"]], "x", LEFT + HOLE_INSET + hole_r,
                     RIGHT - HOLE_INSET - hole_r, {"J501": 180, "J301": 180})
    jy = TOP + JST_INSET
    # User's choice (2026-11-12): the speaker group sat on the 11 o'clock ring LED and held
    # the ring to 22.2 mm. Shifting J501 1.6 mm right (equal gaps would give x 133.425)
    # lets the ring grow to 33 mm, so the JST gaps are no longer exactly equal.
    xs[0] = 135.0
    P["J501"].place(xs[0], jy, 180)
    P["J301"].place(xs[1], jy, 180)
    tp_dx = (group["TP502"][0] - group["TP501"][0]) / 2          # make the test points symmetric
    tp_dy = (group["TP501"][1] + group["TP502"][1]) / 2
    P["U503"].place(xs[0] + group["U503"][0], jy + group["U503"][1])
    P["TP501"].place(xs[0] - tp_dx, jy + tp_dy)
    P["TP502"].place(xs[0] + tp_dx, jy + tp_dy)
    report.append(f"JST equal gap would be {gap:.3f} mm; J501 x {xs[0]:.3f} (shifted), "
                  f"J301 x {xs[1]:.3f}, y {jy:.3f}")

    # 1d. buttons, switches and LEDs on the left/right edges -------------------
    #     Each USB-C splits its edge; each half runs from the hole centre line to the
    #     USB courtyard and its parts get equal courtyard gaps.
    usb_half = 5.32                                          # USB courtyard half-length along the edge
    halves = [(TOP + HOLE_INSET, CY - usb_half), (CY + usb_half, BOTTOM - HOLE_INSET)]
    side_parts = {
        "L": [["SW701", "SW301"], ["SW602", "SW601", "D601"]],
        "R": [["SW401", "D401", "SW402"], ["SW603", "D402", "D201"]],
    }
    body_front = {"SW_SHOUHAN_TS24CA_SideActuated": -1.23,       # silk line where the stem starts
                  "SW_SHOUHAN_MSK12C02_SideActuated": 1.95}
    for edge, groups in side_parts.items():
        for (a, b), refs in zip(halves, groups):
            ps = [P[r] for r in refs]
            rots = {r: P[r].at[2] for r in refs}             # keep each part's rotation
            ys, gap = spread(ps, "y", a, b, rots)
            for p, y in zip(ps, ys):
                bf = body_front.get(p.node[1].split(":")[-1])
                off = inward_offset(p, rots[p.ref], edge, bf)
                p.place(LEFT + off if edge == "L" else RIGHT - off, y)
            report.append(f"edge {edge} {refs}: gap {gap:.3f} mm")

    # 1e. J701 centred on the bottom edge, same distance to the edge as before --
    jx, jy7, jr = P["J701"].at
    P["J701"].place(CX, jy7 + (BOTTOM - oy2), jr)

    # 1f. test pads: two rows on the bottom side, equal gaps between the hole pads
    top_row = sorted(["TP4%02d" % i for i in range(1, 13)], key=lambda r: P[r].at[0])
    bot_row = sorted(["TP2%02d" % i for i in range(1, 6)] + ["TP3%02d" % i for i in range(1, 8)],
                     key=lambda r: P[r].at[0])
    for row, y in ((top_row, TOP + TP_INSET), (bot_row, BOTTOM - TP_INSET)):
        ps = [P[r] for r in row]
        xs, gap = spread(ps, "x", LEFT + HOLE_INSET + hole_r, RIGHT - HOLE_INSET - hole_r,
                         {r: P[r].at[2] for r in row})
        for p, x in zip(ps, xs):
            p.place(x, y)
        report.append(f"test-pad row y {y:.3f}: {len(row)} pads, gap {gap:.3f} mm")

    # 1g. mics: ports on a 66 mm square, each turned 45 deg with the port facing its corner.
    #     User (2026-11-12, later): mics on the TOP side so their bottom ports open through
    #     the board on the bottom, the same side as the LED ring. The port sits on the
    #     footprint's local y = 0 axis, so the flip keeps it at local (0.71, 0).
    h = MIC_SQUARE / 2
    mic = {"MK501": (CX + h, CY - h, 45), "MK502": (CX - h, CY - h, 135),
           "MK503": (CX - h, CY + h, -135), "MK504": (CX + h, CY + h, -45)}
    for r, (px, py, rot) in mic.items():
        P[r].flip_to_top()
        dx, dy = to_board(0, 0, rot, MIC_PORT, 0)            # port offset in board axes
        P[r].place(px - dx, py - dy, rot)

    # 2. XVF3800 centred (bottom); clock buffer U501 stays where the user put it
    P["U301"].place(CX, CY, P["U301"].at[2])

    # 3a. ESP32 module body centred (top). Body centre is local (0, 0.15) (Eco2 outline).
    er = P["U601"].at[2]
    ex, ey = to_board(0, 0, er, 0, 0.15)
    P["U601"].place(CX - ex, CY - ey, er)

    # 3b. bucks + LDO: one column, equal 0.5 mm gaps, centred on y = CY.
    #     User (2026-11-12, later): the column sat 0.5 mm off the module's pins 15-26, so it
    #     moves to the other end of the module, the antenna/IPEX end that faces the ESP32's
    #     own USB-C (J102, left edge). That end has no module pins. The layout is the old one
    #     mirrored: buck next to the module, inductor further out toward J102, and each
    #     SOT-23-5 turned 180 deg so the same pins still face its inductor.
    rows = [("U203", None), ("U202", "L202"), ("U201", "L201")]
    esp_left = bbox(P["U601"].courtyard())[0]
    ux = esp_left - 0.5 - 2.05                               # SOT-23-5 courtyard half-width 2.05
    lx_off = -6.45                                           # inductor beside its buck, mirrored
    heights = [4.1 if l else 3.4 for _, l in rows]
    y = CY - (sum(heights) + 0.5 * (len(rows) - 1)) / 2
    for (u, l), hgt in zip(rows, heights):
        P[u].place(ux, y + hgt / 2, 0)
        if l:
            P[l].place(ux + lx_off, y + hgt / 2, 0)
        y += hgt + 0.5

    # 3c. LED ring (bottom): clock positions kept, turned to follow the circle,
    #     radius = the largest that clears every bottom-side courtyard and every through-hole pad
    clock = {"D801": 3, "D802": 2, "D803": 1, "D804": 12, "D805": 11, "D806": 10,
             "D807": 9, "D808": 8, "D809": 7, "D810": 6, "D811": 5, "D812": 4}
    ring = list(clock)
    obstacles = []
    for r in on_board:
        if r in ring:
            continue
        p = P[r]
        if p.side == "B.Cu" and p.local_box("CrtYd"):
            obstacles.append((r, p.courtyard()))
        for poly in p.pads(only_th=True):
            obstacles.append((r, poly))
        if r.startswith("H"):
            obstacles.append((r, circle_pts(p.at[0], p.at[1], hole_r)))
        # User (2026-11-12): no ring LED directly beneath a USB-C, so the whole top-side
        # connector outline (courtyard) counts, not just its through-hole shell legs.
        if r in ("J101", "J102"):
            obstacles.append((r, p.courtyard()))

    def ring_pose(r, R):
        hr = clock[r] % 12
        a = math.radians(30 * hr)
        return CX + R * math.sin(a), CY - R * math.cos(a), norm(180 - 30 * hr)

    def ring_ok(R):
        for r in ring:
            x, y, rot = ring_pose(r, R)
            b = P[r].local_box("CrtYd")
            led = [to_board(x, y, rot, px, py) for px, py in
                   ((b[0] - CLEAR, b[1] - CLEAR), (b[2] + CLEAR, b[1] - CLEAR),
                    (b[2] + CLEAR, b[3] + CLEAR), (b[0] - CLEAR, b[3] + CLEAR))]
            bx = bbox(led)
            if bx[0] < LEFT or bx[1] < TOP or bx[2] > RIGHT or bx[3] > BOTTOM:
                return False, r, "edge"
            for name, poly in obstacles:
                if overlap(led, poly):
                    return False, r, name
        return True, None, None

    R = 36.0
    while R > 10 and not ring_ok(R)[0]:
        R = round(R - 0.01, 2)
    limit = ring_ok(round(R + 0.01, 2))
    for r in ring:
        P[r].place(*ring_pose(r, R))
    report.append(f"LED ring radius {R:.2f} mm (next 0.01 mm blocked: {limit[1]} vs {limit[2]})")

    # ---------------------------------------------------------------- checks
    off = [r for r in on_board if not (LEFT <= P[r].at[0] <= RIGHT and TOP <= P[r].at[1] <= BOTTOM)]
    report.append(f"moved {len(on_board)} on-board parts; outside the new outline: {off or 'none'}")
    for side in ("F.Cu", "B.Cu"):
        refs = [r for r in on_board if P[r].side == side and P[r].local_box("CrtYd")]
        for i, a in enumerate(refs):
            for b in refs[i + 1:]:
                if overlap(P[a].courtyard(), P[b].courtyard()):
                    report.append(f"  courtyard overlap {side}: {a} / {b}")

    print("\n".join(report))
    if not dry_run:
        open(BOARD, "w").write(dump(root) + "\n")
        print("written", os.path.relpath(BOARD))


def make_four_layer(root):
    """Add In1.Cu/In2.Cu and the 4-layer JLC stackup copied from the controller board."""
    layers = child(root, "layers")
    if any(isinstance(l, list) and l[1] == "In1.Cu" for l in layers[1:]):
        return
    i = [n for n, l in enumerate(layers) if isinstance(l, list) and l[1] == "F.Cu"][0]
    layers.insert(i + 1, ["4", Quoted("In1.Cu"), "power", Quoted("In1.Cu-GND")])
    layers.insert(i + 2, ["6", Quoted("In2.Cu"), "power", Quoted("In2.Cu-PWR")])
    ctrl = parse(open(CONTROLLER).read())
    stackup = child(child(ctrl, "setup"), "stackup")
    setup = child(root, "setup")
    setup.insert(1, stackup)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
