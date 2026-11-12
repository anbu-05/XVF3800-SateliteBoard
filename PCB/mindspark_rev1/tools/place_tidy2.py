"""Second placement tidy of the rev 1 board (2026-11-12, evening).

Works on the board as the user left it (22:37 save, backup
mindspark_rev1-backups/mindspark_rev1.kicad_pcb.pre-tidy2-2026-11-12), not on the original
rough placement, so the user's moves are the starting point. Rules agreed in chat:

  * Mounting holes 12 mm in from both edges (round number past the user's deepest, 11.73).
  * Edge parts re-spread from the new hole line (equal courtyard gaps per half-edge); each
    edge part's own resistors/caps follow it in a column just inside it.
  * Mic corners: MK501's corner is the template (C502, FB501, C506 on the mic axis, CLK and
    DATA resistors either side); the other three are 90 deg turns of it, which also places
    FB502-504 / C512-514 and fixes the C503/C504 swap.
  * LED ring at 27.0 mm; each 100 nF beside its LED, inward unless something is in the way.
  * Every IC group: the IC is the anchor, each cap on the pin its 'use' field names,
    passives in straight rows (0/90 deg) with equal 0.15 mm courtyard gaps.
  * Twin groups are exact copies: the two USB-C groups (180 deg about the board centre),
    the two bucks (180 deg about their midpoint).
  * The user's trial tracks are removed (parts move under them); the backup keeps them.
  * Reference text is not touched (labels come last, user's call).

Usage (KiCad closed):  python3 tools/place_tidy2.py [--dry-run]
"""
import math
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import (BOARD, CX, CY, LEFT, RIGHT, TOP, BOTTOM, SIZE, to_board, bbox,  # noqa: E402
                        overlap, circle_pts, Part, norm, inward_offset, spread)
from sexpr import parse, dump, children, child  # noqa: E402

GAP = 0.15          # courtyard-to-courtyard gap inside a group
HOLE_INSET = 12.0   # user 2026-11-12: holes moved in for the mic ferrites; 12 mm chosen
HOLE_R = 2.2        # M2 pad radius
TP_INSET = 1.5
RING_R = 27.0       # user: a round number; 27 verified clear of the USB-C outlines
EDGE_COL_GAP = 0.3  # edge part courtyard -> its passives column

root = parse(open(BOARD).read())
P = {}
for f in children(root, "footprint"):
    p = Part(f)
    P[p.ref] = p
report = []


# ---------------------------------------------------------------- small helpers
def bb(r, x=None, y=None, rot=None):
    """Bounding box of part r's courtyard AND pads (optionally at a trial pose).
    Pads count because some footprints (the PROG slide switch) have pads past the courtyard."""
    pts = P[r].courtyard(x, y, rot) if P[r].local_box("CrtYd") else []
    for q in P[r].pads(x, y, rot):
        pts += q
    return bbox(pts)


def put(r, x, y, rot=None):
    P[r].place(x, y, rot)


def pads(r):
    """{pad number: (board x, board y, net)} for the part's current pose."""
    x, y, rot = P[r].at
    out = {}
    for pd in children(P[r].node, "pad"):
        a = child(pd, "at")
        net = child(pd, "net")
        bx, by = to_board(x, y, rot, float(a[1]), float(a[2]))
        out.setdefault(str(pd[1]), (bx, by, str(net[1]) if net else ""))
    return out


def nets(r):
    return {v[2] for v in pads(r).values()}


def pin_of(r, net):
    """Board position of the first pad of r on `net`."""
    for num, (x, y, n) in sorted(pads(r).items()):
        if n == net:
            return x, y
    raise KeyError(f"{r} has no pad on {net}")


# Two-pad parts: rotation that puts pad 1 on a side (same for top and bottom parts here,
# because bottom footprints are stored with local y mirrored, x unchanged).
PAD1_SIDE_ROT = {"L": 0, "R": 180, "B": 90, "T": -90}
OPPOSITE = {"L": "R", "R": "L", "T": "B", "B": "T"}


def rot_net_to(r, net, side):
    """Rotation of a 2-pad part that puts its pad on `net` toward `side`."""
    p = pads(r)
    first = p["1"][2] == net
    return PAD1_SIDE_ROT[side if first else OPPOSITE[side]]


def abut(r, rot, box, side, along, gap=GAP):
    """Place r (at rotation rot) against `box` on `side`, its courtyard centred on `along`
    (a y for L/R, an x for T/B). Returns the new courtyard box."""
    o = bb(r, 0, 0, rot)
    if side in "LR":
        x = box[0] - gap - o[2] if side == "L" else box[2] + gap - o[0]
        y = along - (o[1] + o[3]) / 2
    else:
        y = box[1] - gap - o[3] if side == "T" else box[3] + gap - o[1]
        x = along - (o[0] + o[2]) / 2
    put(r, x, y, rot)
    return bb(r)


def union(*boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def row(items, axis, edge, side, gap=GAP):
    """Lay parts in one straight row against a line.

    items: list of (ref, rot, target) where target is where the part's courtyard centre
    would ideally sit along the row (e.g. the pin it serves). axis 'x' = horizontal row.
    edge: the line the row sits against; side: 'T'/'B'/'L'/'R' of that line the row is on.
    Centres are solved by isotonic regression (pool-adjacent-violators): every part as
    close to its target as the minimum gap allows, order kept.
    """
    items = sorted(items, key=lambda t: t[2])
    w = []
    for r, rot, _ in items:
        o = bb(r, 0, 0, rot)
        w.append((o[0], o[2]) if axis == "x" else (o[1], o[3]))
    sizes = [hi - lo for lo, hi in w]
    off = [0.0]
    for i in range(1, len(items)):
        off.append(off[-1] + sizes[i - 1] / 2 + gap + sizes[i] / 2)
    blocks = []                                          # (mean, count)
    for (r, rot, t), o in zip(items, off):
        blocks.append([t - o, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            m2, n2 = blocks.pop()
            m1, n1 = blocks.pop()
            blocks.append([(m1 * n1 + m2 * n2) / (n1 + n2), n1 + n2])
    s = [m for m, n in blocks for _ in range(n)]
    for (r, rot, _), o, si, (lo, hi) in zip(items, off, s, w):
        centre = si + o
        ob = bb(r, 0, 0, rot)
        if axis == "x":
            x = centre - (lo + hi) / 2
            y = edge + GAP - ob[1] if side == "B" else edge - GAP - ob[3]
        else:
            y = centre - (lo + hi) / 2
            x = edge + GAP - ob[0] if side == "R" else edge - GAP - ob[2]
        put(r, x, y, rot)


def column(refs, anchor_box, side, along, gap=GAP, face=None, rot=None):
    """Stack 2-pad parts beside anchor_box (horizontal parts in a vertical column for L/R,
    vertical parts in a horizontal row for T/B), centred on `along`.
    face: net-sharing anchor ref whose nets should face the anchor."""
    if not refs:
        return None
    rots = []
    for r in refs:
        if rot is not None:
            rots.append(rot)
            continue
        shared = nets(r) & nets(face) if face else set()
        shared.discard("GND")
        net = sorted(shared)[0] if shared else pads(r)["1"][2]
        toward = OPPOSITE[side]                              # pad faces back to the anchor
        rots.append(rot_net_to(r, net, toward))
    sizes = []
    for r, ro in zip(refs, rots):
        o = bb(r, 0, 0, ro)
        sizes.append(o[3] - o[1] if side in "LR" else o[2] - o[0])
    total = sum(sizes) + gap * (len(refs) - 1)
    cursor = along - total / 2
    boxes = []
    for r, ro, s in zip(refs, rots, sizes):
        boxes.append(abut(r, ro, anchor_box, side, cursor + s / 2, EDGE_COL_GAP if face else gap))
        cursor += s + gap
    return union(*boxes)


def rigid(refs, about, angle, target):
    """Copy-rotate: move each ref so the group turns by `angle` about point `about` and
    that point lands on `target`. Each part's own rotation turns by the same angle."""
    a = math.radians(angle)
    out = {}
    for r in refs:
        x, y, rot = P[r].at
        dx, dy = x - about[0], y - about[1]
        # KiCad sense (positive = counter-clockwise on screen, y down)
        nx = target[0] + dx * math.cos(a) + dy * math.sin(a)
        ny = target[1] - dx * math.sin(a) + dy * math.cos(a)
        out[r] = (nx, ny, norm(rot + angle))
    return out


# ================================================================ 0. tracks
segs = children(root, "segment") + children(root, "via") + children(root, "arc")
root[:] = [n for n in root if not (isinstance(n, list) and n and n[0] in ("segment", "via", "arc"))]
report.append(f"removed the user's {len(segs)} trial track segments / vias (suggestions only; backup keeps them)")

# ================================================================ 0b. J102 VBUS net
# The schematic tidy restored J102's deleted VBUS wire, so its VBUS pads are on VBUS_ESP
# again; the board still had them on the orphan net. Same as KiCad's Update PCB from Schematic.
n = 0
for pd in children(P["J102"].node, "pad"):
    net = child(pd, "net")
    if net and net[1] == "Net-(J102-VBUS-PadA4)":
        net[1] = type(net[1])("VBUS_ESP")
        n += 1
report.append(f"J102 VBUS: {n} pads moved to VBUS_ESP (schematic fix)")

# ================================================================ 1. mounting holes
HOLES = {"H2": (LEFT + HOLE_INSET, TOP + HOLE_INSET), "H1": (RIGHT - HOLE_INSET, TOP + HOLE_INSET),
         "H3": (LEFT + HOLE_INSET, BOTTOM - HOLE_INSET), "H4": (RIGHT - HOLE_INSET, BOTTOM - HOLE_INSET)}
for r, (x, y) in HOLES.items():
    put(r, x, y)
report.append(f"holes {HOLE_INSET} mm in from both edges")

# ================================================================ 2. test-pad rows (bottom)
top_row = sorted(["TP4%02d" % i for i in range(1, 13)], key=lambda r: P[r].at[0])
bot_row = sorted(["TP2%02d" % i for i in range(1, 6)] + ["TP3%02d" % i for i in range(1, 8)],
                 key=lambda r: P[r].at[0])
for rowrefs, y in ((top_row, TOP + TP_INSET), (bot_row, BOTTOM - TP_INSET)):
    ps = [P[r] for r in rowrefs]
    xs, gap = spread(ps, "x", LEFT + HOLE_INSET + HOLE_R, RIGHT - HOLE_INSET - HOLE_R,
                     {r: P[r].at[2] for r in rowrefs})
    for p, x in zip(ps, xs):
        p.place(x, y)
    report.append(f"test-pad row y {y:.3f}: gap {gap:.3f} mm")

# ================================================================ 3. edge parts + their passives
usb_half = 5.32
halves = [(TOP + HOLE_INSET, CY - usb_half), (CY + usb_half, BOTTOM - HOLE_INSET)]
side_parts = {"L": [["SW701", "SW301"], ["SW602", "SW601", "D601"]],
              "R": [["SW401", "D401", "SW402"], ["SW603", "D402", "D201"]]}
body_front = {"SW_SHOUHAN_TS24CA_SideActuated": -1.23, "SW_SHOUHAN_MSK12C02_SideActuated": 1.95}
for edge, groups in side_parts.items():
    for (a, b), refs in zip(halves, groups):
        ps = [P[r] for r in refs]
        rots = {r: P[r].at[2] for r in refs}
        ys, gap = spread(ps, "y", a, b, rots)
        for p, y in zip(ps, ys):
            bf = body_front.get(p.node[1].split(":")[-1])
            off = inward_offset(p, rots[p.ref], edge, bf)
            p.place(LEFT + off if edge == "L" else RIGHT - off, y)
        report.append(f"edge {edge} {refs}: gap {gap:.3f} mm")

# passives that belong to each edge part (schematic sheets), in column order
EDGE_KIT = {
    "SW701": ["R701"],                       # PROG switch: PRG_EN pull-down
    "SW602": ["R602", "R604"],               # BOOT: GPIO0 pull-up, button series R
    "SW601": ["R601", "C603", "R603"],       # EN: pull-up, RC delay cap, button series R
    "D601": ["R608", "C605"],                # user WS2812: data series R, its bypass cap
    "SW401": ["R402"],                       # MUTE pull-up
    "D401": ["R404"],                        # mute LED series R
    "SW402": ["R403"],                       # ACTION pull-up
    "SW603": ["R607", "R609"],               # USER: pull-up, series R
    "D402": ["R405", "R406"],                # status LED series Rs
    "D201": ["R205"],                        # power LED series R
}
for e, kit in EDGE_KIT.items():
    side = "R" if P[e].at[0] < CX else "L"                   # the column sits inward
    eb = bb(e)
    column(kit, eb, side, (eb[1] + eb[3]) / 2, face=e)

# RESET (SW301): TPS3808 U302 just inside the button, its bypass C322 above, RST pull-up R303 below
sb = bb("SW301")
ub = abut("U302", P["U302"].at[2], sb, "R", (sb[1] + sb[3]) / 2, EDGE_COL_GAP)
abut("C322", rot_net_to("C322", "+3V3", "R"), ub, "T", (ub[0] + ub[2]) / 2)
abut("R303", rot_net_to("R303", "/XVF_RST_N", "L"), ub, "B", (ub[0] + ub[2]) / 2)

# ================================================================ 4. speaker test points
jb = bb("J501")
jx = P["J501"].at[0]
tp_dx = 4.13                                   # user's average offset (4.32 / 3.94), now symmetric
for r, sx in (("TP501", 1), ("TP502", -1)):          # SPK+ right, SPK- left, as the user had them
    o = bb(r, 0, 0, P[r].at[2])
    put(r, jx + sx * tp_dx, jb[3] + GAP - o[1])
report.append(f"TP501/TP502 symmetric about J501 (x {jx:.3f} -/+ {tp_dx}), just below its courtyard")

# ================================================================ 5. mic corners
# Template in MK501's own frame (mic-local x, y; rotation relative to the mic). Mic courtyard
# is x -2.0..2.0, y -1.575..1.575; its VDD/CLK/DATA/GND pads sit at x -1.36..-0.54 (inner side).
#   centre column on the mic axis, inward: 1 uF at VDD, then the ferrite, then the 10 uF
#   CLK resistor on the CLK side (y < 0), DATA resistor on the DATA side, mirror images
c_1u = -2.0 - GAP - 0.46
c_fb = c_1u - 0.46 - GAP - 0.47
c_10u = c_fb - 0.47 - GAP - 0.73
r_y = 1.575 + GAP + 0.47
TEMPLATE = {                                  # role: (local x, local y, rotation rel. to mic)
    "c1u": (c_1u, 0.0, -90), "fb": (c_fb, 0.0, 90), "c10u": (c_10u, 0.0, -90),
    "rclk": (-1.8, -r_y, 180), "rdata": (-1.8, r_y, 180),
}
MICS = {  # from the schematic (audio sheet) and the parts' 'use' fields
    "MK501": {"c1u": "C502", "fb": "FB501", "c10u": "C506", "rclk": "R502", "rdata": "R506"},
    "MK502": {"c1u": "C503", "fb": "FB502", "c10u": "C512", "rclk": "R503", "rdata": "R507"},
    "MK503": {"c1u": "C504", "fb": "FB503", "c10u": "C513", "rclk": "R504", "rdata": "R508"},
    "MK504": {"c1u": "C505", "fb": "FB504", "c10u": "C514", "rclk": "R505", "rdata": "R509"},
}
for mk, roles in MICS.items():
    mx, my, mr = P[mk].at
    for role, ref in roles.items():
        lx, ly, rel = TEMPLATE[role]
        bx, by = to_board(mx, my, mr, lx, ly)
        put(ref, bx, by, norm(mr + rel))
    # check the net roles: pad 1 of the 1 uF / 10 uF and ferrite pad 2 on this mic's VDD net
    vdd = pads(mk)["5"][2]
    assert pads(roles["c1u"])["1"][2] == vdd and pads(roles["c10u"])["1"][2] == vdd \
        and pads(roles["fb"])["2"][2] == vdd, f"{mk}: supply parts not on {vdd}"
    assert pads(roles["rclk"])["1"][2] == pads(mk)["4"][2] and pads(roles["rdata"])["1"][2] == pads(mk)["1"][2]
report.append("mic corners: MK501 template copied to MK502-504 (90 deg turns); C503/C504 back at their own mics")

# ================================================================ 6. LED ring + its caps
CLOCK = {"D801": 3, "D802": 2, "D803": 1, "D804": 12, "D805": 11, "D806": 10,
         "D807": 9, "D808": 8, "D809": 7, "D810": 6, "D811": 5, "D812": 4}
for d, h in CLOCK.items():
    a = math.radians(30 * (h % 12))
    put(d, CX + RING_R * math.sin(a), CY - RING_R * math.cos(a), norm(180 - 30 * (h % 12)))
report.append(f"LED ring radius {RING_R} mm")
# (caps placed after all other parts, see step 12, so the collision test sees the final board)

# ================================================================ 7. USB-C groups
# J101 group is the template; the J102 group is the same group turned 180 deg about the
# board centre (J102 is J101 turned 180 deg), so both route identically.
#   ESD U101 just inside J101, centred on the connector axis; Rd R101 (CC1) above it and
#   R102 (CC2) below it; TVS D101, 10 uF C101 and 100 nF C102 in a column further in.
j1 = bb("J101")
u = abut("U101", P["U101"].at[2], j1, "L", CY)
r_up = abut("R101", rot_net_to("R101", "GND", "L"), u, "T", (u[0] + u[2]) / 2)
r_dn = abut("R102", rot_net_to("R102", "GND", "L"), u, "B", (u[0] + u[2]) / 2)
esd = union(u, r_up, r_dn)
dtv = abut("D101", P["D101"].at[2], esd, "L", CY)
# 10 uF and 100 nF beside the TVS, VBUS pads on top like the TVS's
c10 = abut("C101", rot_net_to("C101", "VBUS_MAIN", "T"), dtv, "L", CY)
abut("C102", rot_net_to("C102", "VBUS_MAIN", "T"), c10, "L", CY)
USB_MAP = {"U101": "U102", "R101": "R103", "R102": "R104", "D101": "D102", "C101": "C103", "C102": "C104"}
for src, (x, y, rot) in rigid(list(USB_MAP), (CX, CY), 180, (CX, CY)).items():
    put(USB_MAP[src], x, y, rot)
for a_, b_ in USB_MAP.items():   # same pad on the same role net (MAIN <-> ESP)
    for num in pads(a_):
        na, nb = pads(a_)[num][2], pads(b_)[num][2]
        assert (na == "GND") == (nb == "GND"), f"{a_}/{b_} pad {num}: {na} vs {nb}"
report.append("USB-C groups: J101 group tidied, J102 group = 180 deg copy")

# ================================================================ 8. TPS2121 power mux (U103)
# 4 x 2 divider array above U103 (as the user drew it), ILIM/ST/SS row below, OUT caps right.
ub = bb("U103")
ucx = (ub[0] + ub[2]) / 2
pair_cols = [("R106", "R105"), ("R110", "R109"), ("R112", "R111"), ("R108", "R107")]   # (top, lower)
rw = bb("R105", 0, 0, 90)
colw = rw[2] - rw[0]
x0 = ucx - (4 * colw + 3 * GAP) / 2 - rw[0]
for i, (top, low) in enumerate(pair_cols):
    x = x0 + i * (colw + GAP)
    # lower resistor: divider-top (VBUS) pad down toward U103? keep the user's orientation:
    # node (U103 control net) pads face each other in the middle of the pair
    rl = 90 if pads(low)["2"][2].startswith("VBUS") else -90
    rt = -90 if pads(top)["2"][2] == "GND" else 90
    ylow = ub[1] - GAP - bb(low, 0, 0, rl)[3]
    put(low, x, ylow, rl)
    put(top, x, bb(low)[1] - GAP - bb(top, 0, 0, rt)[3], rt)
row([(r, rot_net_to(r, n, "T"), pin_of("U103", m)[0])
     for r, n, m in (("R114", "/MUX_ST", "/MUX_ST"), ("R113", pads("R113")["1"][2], pads("R113")["1"][2]),
                     ("C105", pads("C105")["1"][2], pads("C105")["1"][2]))],
    "x", ub[3], "B")
cb = abut("C107", rot_net_to("C107", "+5V", "T"), ub, "R", (ub[1] + ub[3]) / 2)
abut("C106", rot_net_to("C106", "+5V", "T"), cb, "R", (ub[1] + ub[3]) / 2)
report.append("TPS2121: divider array, control row and OUT caps squared up on U103")

# ================================================================ 9. regulators
# U201 (0.9 V) is the template; U202 (3.3 V) is the same layout turned 180 deg (the user's
# arrangement), the two FB networks facing each other; LDO U203 further left.
ux, uy, _ = P["U201"].at
put("U201", ux, uy, 90)
u = bb("U201")
cin = abut("C202", rot_net_to("C202", "+5V", "R"), u, "T", (u[0] + u[2]) / 2)
co1 = abut("C203", rot_net_to("C203", "+0V9", "R"), u, "B", (u[0] + u[2]) / 2)
co2 = abut("C204", rot_net_to("C204", "+0V9", "R"), co1, "B", (u[0] + u[2]) / 2)
lb = bb("L201", 0, 0, -90)
put("L201", u[2] + GAP - lb[0], u[1] - lb[1], -90)           # inductor beside the buck, tops level
fb_r = abut("R201", rot_net_to("R201", "+0V9", "B"), u, "L", (u[1] + u[3]) / 2)
fb_c = abut("C201", rot_net_to("C201", "+0V9", "B"), fb_r, "L", (u[1] + u[3]) / 2)
pair = union(fb_r, fb_c)
abut("R202", rot_net_to("R202", "GND", "R"), pair, "T", (pair[0] + pair[2]) / 2)
BUCK = ["U201", "C202", "C203", "L201", "R201", "C201", "R202"]
BUCK_MAP = {"U201": "U202", "C202": "C206", "C203": "C207", "L201": "L202",
            "R201": "R203", "C201": "C205", "R202": "R204"}
g = union(*[bb(r) for r in BUCK + ["C204"]])
gl = union(*[bb(r) for r in BUCK])
# turn 180 deg about M: the copy's right edge lands 0.5 mm left of the template's left edge
mx = g[0] - 0.25
for src, (x, y, rot) in rigid(BUCK, (mx, uy), 180, (mx, uy)).items():
    put(BUCK_MAP[src], x, y, rot)
for a_, b_ in BUCK_MAP.items():
    for num in pads(a_):
        na, nb = pads(a_)[num][2], pads(b_)[num][2]
        assert (na in ("GND",)) == (nb in ("GND",)), f"{a_}/{b_} pad {num}: {na} vs {nb}"
g2 = union(*[bb(BUCK_MAP[r]) for r in BUCK])
lu = abut("U203", P["U203"].at[2], g2, "L", uy, 0.5)
abut("C208", rot_net_to("C208", "+3V3", "R"), lu, "T", (lu[0] + lu[2]) / 2)
abut("C209", rot_net_to("C209", "+1V8", "R"), lu, "B", (lu[0] + lu[2]) / 2)
# centre the whole block on the board's x centre, keeping its y
block = ["U203", "C208", "C209"] + BUCK + ["C204"] + list(BUCK_MAP.values())
bx = union(*[bb(r) for r in block])
dx = CX - (bx[0] + bx[2]) / 2
for r in block:
    x, y, rot = P[r].at
    put(r, x + dx, y, rot)
report.append("regulators: U202 group = U201 group turned 180 deg, LDO left, block centred on x")

# ================================================================ 10. ESP32 and its I/O
ub = bb("U601")
# module 3V3 pin bypass: 100 nF nearest the pin, 22 uF beside it, in a row under the module
p3 = pin_of("U601", "+3V3")
row([("C602", rot_net_to("C602", "+3V3", "L"), p3[0]),        # +3V3 pads of the two caps
     ("C601", rot_net_to("C601", "+3V3", "R"), p3[0] - 2.5)],   # face each other
    "x", ub[3], "B")
# USB series resistors under pins 13/14, each centred on its pin
row([(r, rot_net_to(r, pads(r)["1"][2], "T"), pin_of("U601", pads(r)["1"][2])[0])
     for r in ("R606", "R605")], "x", ub[3], "B")
# flash switches: column right of the module in the user's order, each with its own bypass cap
SW_ORDER = ["U704", "U702", "U703", "U701"]
SW_CAP = {"U701": "C701", "U702": "C702", "U703": "C703", "U704": "C704"}
first = bb("U704")
x_sw = P["U704"].at[0]
y = first[1]
for s in SW_ORDER:
    o = bb(s, 0, 0, P[s].at[2])
    put(s, x_sw, y - o[1])
    sb_ = bb(s)
    vy = pin_of(s, "+3V3")[1]
    abut(SW_CAP[s], rot_net_to(SW_CAP[s], "+3V3", "T"), sb_, "R", vy - 0.0)
    y = sb_[3] + GAP
# Q701 (XVF reset pull-down) above the column: R703 (0R link) left, gate pull-down R702 right
qb = bb("Q701")
abut("R703", rot_net_to("R703", "/XVF_RST_N", "T"), qb, "L", (qb[1] + qb[3]) / 2)
abut("R702", rot_net_to("R702", "GND", "T"), qb, "R", (qb[1] + qb[3]) / 2)
# ring data buffer U802: bypass C816 on its VCC pad, series R802 on its output pad
b8 = bb("U802")
abut("C816", rot_net_to("C816", "+5V_LED", "R"), b8, "T", pin_of("U802", "+5V_LED")[0])
abut("R802", rot_net_to("R802", pads("R802")["1"][2] if pads("R802")["1"][2] in nets("U802") else pads("R802")["2"][2], "B"),
     b8, "R", pin_of("U802", [n for n in nets("R802") if n in nets("U802")][0])[1])
# user-LED buffer U602 with its bypass C604 beside the VCC pad
b6 = bb("U602")
abut("C604", rot_net_to("C604", "+5V", "T"), b6, "L", (b6[1] + b6[3]) / 2)
# I2C pull-ups: a matched pair, side by side
pb = bb("R705")
abut("R704", P["R705"].at[2], pb, "R", (pb[1] + pb[3]) / 2)

# ================================================================ 11. LED power switch, amp
b1 = bb("U801")
abut("C815", rot_net_to("C815", "+5V_LED", "T"), b1, "L", (b1[1] + b1[3]) / 2)
col = column(["C813", "R801"], b1, "R", (b1[1] + b1[3]) / 2, face="U801")
abut("C814", rot_net_to("C814", "+5V", "L"), b1, "B", (b1[0] + b1[2]) / 2)   # VIN cap under U801 (C106 is left of pin 1)
# amp U503: VDD bypass 100 nF, 10 uF and 47 uF to its right; SD_MODE resistor below
b3 = bb("U503")
c9 = abut("C509", rot_net_to("C509", "+5V_AMP", "T"), b3, "R", (b3[1] + b3[3]) / 2)
c10b = abut("C510", rot_net_to("C510", "+5V_AMP", "L"), c9, "R", (c9[1] + c9[3]) / 2)
w11 = bb("C511", 0, 0, rot_net_to("C511", "+5V_AMP", "L"))
abut("C511", rot_net_to("C511", "+5V_AMP", "L"), c10b, "B", c10b[0] + (w11[2] - w11[0]) / 2)   # left-aligned under C510, clear of the amp
r11 = abut("R511", rot_net_to("R511", "+5V_AMP", "R"), b3, "B", (b3[0] + b3[2]) / 2)
# amp load switch U502 under the amp: input cap left, ON pull-down and CT cap below
u2 = bb("U502")
o2 = bb("U502", 0, 0, P["U502"].at[2])
put("U502", (b3[0] + b3[2]) / 2 - (o2[0] + o2[2]) / 2, r11[3] + GAP - o2[1])
u2 = bb("U502")
abut("C508", rot_net_to("C508", "+5V", "T"), u2, "L", (u2[1] + u2[3]) / 2)
row([("R510", rot_net_to("R510", "/AMP_EN", "L"), pin_of("U502", "/AMP_EN")[0]),
     ("C507", rot_net_to("C507", "GND", "R"), pin_of("U502", [n for n in nets("C507") if n != "GND"][0])[0])],
    "x", u2[3], "B")

# ================================================================ 12. XVF3800 (bottom) decoupling, crystal, flash, clock buffer
xb = bb("U301")
# QFN-60 sides by pin number as placed (bottom side, rot 0): 1-15 right, 16-30 bottom,
# 31-45 left, 46-60 top. Corner pins are ambiguous by position, so go by number.
SIDE_OF = {str(n): "R" if n <= 15 else "B" if n <= 30 else "L" if n <= 45 else "T" for n in range(1, 61)}
# cap -> pin (from the 'use' fields, plus the eight VDD caps one per VDD pin)
CAP_PIN = {"C310": "8", "C311": "38", "C312": "52", "C313": "30", "C315": "17", "C316": "26",
           "C317": "31", "C319": "22"}
vdd_caps = ["C301", "C302", "C303", "C304", "C305", "C306", "C307", "C308"]
for c, pnum in zip(vdd_caps, ["4", "12", "19", "27", "34", "42", "49", "57"]):
    CAP_PIN[c] = pnum
rows = {"L": [], "R": [], "T": [], "B": []}
for c, pnum in CAP_PIN.items():
    sd = SIDE_OF[pnum]
    x, y, n = pads("U301")[pnum]
    assert n in nets(c), f"{c} not on pin {pnum}'s net {n}"
    rot = rot_net_to(c, n, OPPOSITE[sd])             # power pad toward the chip, GND outward
    rows[sd].append((c, rot, x if sd in "TB" else y))
for sd, items in rows.items():
    edge = {"L": xb[0], "R": xb[2], "T": xb[1], "B": xb[3]}[sd]
    row(items, "x" if sd in "TB" else "y", edge, sd)
# PLL filter: ferrite behind its 1 uF, on the PLL pin
cb = bb("C319")
abut("FB301", rot_net_to("FB301", "PLL_AVDD", "T"), cb, "B", (cb[0] + cb[2]) / 2)
# bulk caps behind the rows: 10 uF VDD (top), 3.3 V (left), 1.8 V (bottom)
for c, sd, near in (("C309", "T", "C307"), ("C314", "L", "C311"), ("C318", "B", "C315")):   # behind a cap on the same rail
    nb = bb(near)
    n = [m for m in nets(c) if m != "GND"][0]
    along = (nb[0] + nb[2]) / 2 if sd in "TB" else (nb[1] + nb[3]) / 2
    abut(c, rot_net_to(c, n, OPPOSITE[sd]), nb, sd, along)
report.append("XVF3800: every cap on the pin its use field names, rows at 0.15 mm gaps")

# crystal: Y301 stays; Rd R301 and Rf R302 in a column between it and the chip,
# load caps on the crystal's two pins (C321 on the XOUT-side pin above, C320 on XIN below)
yb = bb("Y301")
column(["R301", "R302"], yb, "L", (yb[1] + yb[3]) / 2, rot=None, face=None)
abut("C321", rot_net_to("C321", "GND", "R"), yb, "T", (yb[0] + yb[2]) / 2)
abut("C320", rot_net_to("C320", "GND", "R"), yb, "B", (yb[0] + yb[2]) / 2)
# flash: bypass on the VCC pad, CS pull-up on the CS pad, one row above the chip
fb = bb("U401")
row([("C401", rot_net_to("C401", "GND", "L"), pin_of("U401", "+3V3")[0]),
     ("R401", rot_net_to("R401", "+3V3", "L"), pin_of("U401", "/XVF_QSPI_CS_N")[0])], "x", fb[1], "T")
# mic clock buffer: bypass above on VCC, output resistor below on the output pad
b5 = bb("U501")
abut("C501", rot_net_to("C501", "+3V3", "L"), b5, "T", pin_of("U501", "+3V3")[0])
abut("R501", rot_net_to("R501", pads("R501")["1"][2], "L"), b5, "B", pin_of("U501", pads("R501")["1"][2])[0])

# ================================================================ 13. ring caps (last: they test against the final board)
RING_CAP = {d: "C8%02d" % (int(d[1:]) - 800) for d in CLOCK}     # D801 -> C801 ...
ON = [r for r, p in P.items() if LEFT <= p.at[0] <= RIGHT and TOP <= p.at[1] <= BOTTOM]
def blockers(skip):
    out = []
    for r in ON:
        if r in skip:
            continue
        p = P[r]
        if p.side == "B.Cu" and p.local_box("CrtYd"):
            out.append((r, p.courtyard()))
        out += [(r, q) for q in p.pads(only_th=True)]
        if r in ("J101", "J102"):
            out.append((r, p.courtyard()))
        if r.startswith("H"):
            out.append((r, circle_pts(p.at[0], p.at[1], HOLE_R)))
    return out
for d, c in RING_CAP.items():
    lx, ly, lr = P[d].at
    obs = blockers({c})
    placed = None
    for where, sy in (("inward", -1), ("outward", 1)):
        cx_, cy_ = to_board(lx, ly, lr, 0, sy * (1.25 + GAP + 0.46))
        rot = norm(lr + 180)                            # GND pad next to the LED's GND side
        poly = [to_board(cx_, cy_, rot, px, py) for px, py in
                ((-0.91 - GAP, -0.46 - GAP), (0.91 + GAP, -0.46 - GAP), (0.91 + GAP, 0.46 + GAP), (-0.91 - GAP, 0.46 + GAP))]
        hit = [n for n, q in obs if n != d and overlap(poly, q)]
        if not hit:
            put(c, cx_, cy_, rot)
            placed = where
            break
    report.append(f"{c} at {d}: {placed or 'NOT PLACED (both sides blocked)'}")
    ON.append(c) if c not in ON else None

# ================================================================ 14. checks + write
ON = [r for r, p in P.items() if LEFT <= p.at[0] <= RIGHT and TOP <= p.at[1] <= BOTTOM]
off = sorted(r for r in P if r not in ON)
report.append(f"parts off the board: {off if off else 'none'}")
def shapes(r):
    out = [P[r].courtyard()] if P[r].local_box("CrtYd") else []
    return out + P[r].pads()
SH = {r: shapes(r) for r in ON}
clash = []
for i, a_ in enumerate(ON):
    for b_ in ON[i + 1:]:
        same = P[a_].side == P[b_].side
        th = any(r.startswith(("J10", "H", "SW", "MK")) for r in (a_, b_))   # parts with holes
        if not (same or th):
            continue
        if any(overlap(x, y) for x in SH[a_] for y in SH[b_]):
            clash.append(f"{a_}/{b_}" + ("" if same else " (other side)"))
report.append(f"courtyard overlaps: {clash if clash else 'none'}")
print("\n".join(report))
if "--dry-run" not in sys.argv:
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else BOARD   # --out: trial copy
    open(out, "w").write(dump(root) + "\n")
    print("wrote", out)
