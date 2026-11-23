"""Silkscreen pass (agreed with the user 2026-11-22).

Usage (PCB editor closed):
    python3 tools/silkscreen_2026_11_22.py                 # edit mindspark_rev1.kicad_pcb
    python3 tools/silkscreen_2026_11_22.py some/copy.kicad_pcb

What was agreed:
  * The BOTTOM side faces the sky in the product (LED ring, mic sound ports); the TOP faces
    the table (connectors, buttons, ESP32). So the "face" silk goes on B.SilkS.
  * Bottom: a ring round each mic sound port (2.0 mm inside, 3.0 mm outside), mic numbers
    1-4 (MK501..MK504 = MIC_DATA0..3), board name + rev, D801 with a chain-direction arrow,
    labels for the parts on that side (ICs, test pads).
  * Top: connector and switch labels (function word only, user 2026-11-22), test pads by
    net name, J701 pin names right at the pins, a blank serial-number box, "ESP TO XVF FLASH / CUT TO DISCONNECT" beside
    the 0 ohm links R706-R709, and the JTAG pin names under J301.
  * Top: no IC/LED/mic references; only a few crucial passives keep theirs (cut links,
    power-mux setting resistors, USB-C CC resistors). Bottom: ICs and D801 keep theirs.
  * Sizes: labels 1.0 mm, small names 0.8 mm, board name 1.5 mm; every stroke >= 0.15 mm
    (JLC minimum ~0.15 mm; KiCad's library default 0.12 mm silk lines are bumped to 0.15).

Everything this script creates carries a uuid starting with TAG, so a re-run first removes
its own earlier items and then lays them again (idempotent). Label spots are found by a small
search: the closest free spot to the part, clear of pads, courtyards, holes, the board edge,
the fixed graphics and labels already placed. A short report lists any label that had to fall
back to a looser search.
"""
import math
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, dump, children, child, q          # noqa: E402
from place_tidy import Part, to_board, rect_pts, bbox, fmt, CX, CY, SIZE  # noqa: E402

BOARD = os.path.join(HERE, "..", "mindspark_rev1.kicad_pcb")
TAG = "5111c000-2026-1122-"          # uuid prefix of everything this script makes

# ---------------------------------------------------------------- sizes (agreed)
LINE = 0.15            # minimum silk stroke
BIG = (1.0, 0.15)      # label height, stroke
SMALL = (0.8, 0.15)    # small names: test pads, crucial passives, J701 table
NAME = (1.5, 0.25)     # board name
CHAR = 0.95            # KiCad stroke-font advance per character, as a fraction of the height
GAP = 0.2              # silk-to-silk and silk-to-pad clearance kept by the label search
EDGE = 0.5             # silk-to-board-edge clearance

# ---------------------------------------------------------------- what gets a label
# Top side (faces the table), trimmed by the user 2026-11-22 ("skim it a lot more"): no IC,
# LED or mic references; switches and connectors get their function word only. The only
# references left on the top are these crucial passives.
KEEP_REFS = {
    "R706", "R707", "R708", "R709", "R703",                     # 0 ohm cut links
    "R105", "R106", "R107", "R108", "R109", "R110", "R111", "R112", "R113",  # TPS2121 setting
    "R101", "R102", "R103", "R104",                             # USB-C CC 5.1k
}
SMALL_REFS = set(KEEP_REFS)
# Bottom side (faces the sky): ICs (U*, Y*) and D801 keep their reference.
BOTTOM_REFS = {"D801"}

# Connectors and switches: just the function, next to the part.
FUNCTION = {
    "J101": "USB MAIN", "J102": "USB ESP", "J301": "JTAG 1V8", "J501": "SPK", "J701": "GPIO",
    "SW301": "XVF RESET", "SW401": "MUTE", "SW402": "ACTION",
    "SW601": "EN", "SW602": "BOOT", "SW603": "USER", "SW701": "PRG_EN",
}

# J701 pin names, printed right at the pins (user 2026-11-22, replaces the separate table).
# North (odd) row: turned 90 degrees in the free band above the header (>= 3.07 mm there,
# tightest over pins 7-10 because of C204, so those names stay 3 characters).
# South (even) row: only ~1.3 mm between the pads and the board edge, so the names run
# horizontally at 0.8 mm, at most 3 characters per 2.54 mm (a narrower font breaks the
# project's 0.8 mm minimum text size): X_SDA -> XDA, X_SCL -> XCL, X_I2S_DATA1 -> XD1.
# E = ESP32, X = XVF3800; pins 13/14 and 15/16 take the I2C shunt jumpers.
J701_NORTH = {1: "5V", 3: "1V8", 5: "IO1", 7: "IO4", 9: "IO6", 11: "IO8", 13: "ESDA",
              15: "ESCL", 17: "XINT", 19: "XD2", 21: "TX", 23: "5V"}
J701_SOUTH = {2: "3V3", 4: "GND", 6: "IO2", 8: "IO5", 10: "IO7", 12: "IO9", 14: "XDA",
              16: "XCL", 18: "XD1", 20: "GND", 22: "RX", 24: "3V3"}
SERIAL_BOX = (118.5, 78.5, 128.5, 82.5)       # top, north-west free area, 10 x 4 mm

# J301 JTAG header (JST PH 7-pin): a name under each pin, read off the board nets 2026-11-22.
J301_NAMES = {1: "1V8", 2: "TCK", 3: "TMS", 4: "RST", 5: "TDO", 6: "TDI", 7: "GND"}

# Board name on the sky face. Renamed by the user 2026-11-23 (was "MindSpeak Voice Satellite").
BOARD_NAME = "MindSpeakAI Voice Satellite v1"

# Sky-face labels for the parts on the table side that a user looks for (user 2026-11-23:
# "add the LED, USB and button labels to the back silkscreen"). The parts can't be seen from
# the sky, so each label gets an arrow (user 2026-11-23: "arrows everywhere"): arrow and label
# sit on the part's own centreline, perpendicular to the nearest (east or west) edge, the arrow
# pointing out towards that edge with its tip at the edge. All arrows on one edge are lined up
# (user 2026-11-23): same tip, same shaft length, so the labels start on one line. The label sits
# inward of the shaft's tail on the part's line; if a line is blocked the label stacks on two
# lines or every arrow on that edge grows together. It never leaves its line.
# (The second field records what the part is: "edge" = touched at the edge, "part" = top button
# or LED; both now get the same lined-up arrow.)
SKY_LABELS = {
    "J101": ("USB MAIN", "edge"), "J102": ("USB ESP", "edge"),
    "SW401": ("MUTE", "edge"), "SW402": ("ACTION", "edge"), "SW603": ("USER", "edge"),
    "SW701": ("PRG_EN", "edge"),          # side-actuated slide switch (user 2026-11-23)
    "SW301": ("XVF RESET", "part"), "SW601": ("EN", "part"), "SW602": ("BOOT", "part"),
    "D401": ("MUTE LED", "part"), "D402": ("XVF LED", "part"), "D201": ("PWR LED", "part"),
    "D601": ("USER LED", "part"),
}
ARROW_HEAD = (0.7, 0.45)     # head length, half-width (mm)
ARROW_SHAFT = 1.5            # shortest shaft (mm)
ARROW_TO_TEXT = 0.3          # gap between the shaft's tail and the label (mm)

MICS = {"MK501": "1", "MK502": "2", "MK503": "3", "MK504": "4"}   # MIC_DATA0..3
RING_R, RING_W = 1.25, 0.5                     # ring 2.0 mm inside, 3.0 mm outside


# ---------------------------------------------------------------- helpers
_count = [0]


def new_uuid():
    """Tagged uuid so the next run can find and remove what this run made."""
    _count[0] += 1
    return q(TAG + "%04x-%012x" % (_count[0] >> 48, _count[0] & 0xFFFFFFFFFFFF))


def is_ours(node):
    u = child(node, "uuid")
    return u is not None and str(u[1]).startswith(TAG)


def effects(size, thick, mirror, width=None):
    w = size if width is None else width
    e = ["effects", ["font", ["size", fmt(w), fmt(size)], ["thickness", fmt(thick)]]]
    if mirror:
        e.append(["justify", "mirror"])
    return e


def text_box(cx, cy, text, size, thick, ang):
    """Axis-aligned box of a centred text at 0 or 90 degrees (may hold several lines)."""
    lines = text.split("\n")
    w = max(len(s) for s in lines) * CHAR * size + thick
    h = size + thick + (len(lines) - 1) * size * 1.7      # KiCad line pitch ~1.6-1.7 x height
    if int(round(ang)) % 180:
        w, h = h, w
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def hit(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def box_gap(a, b):
    """Distance between two boxes (0 when they touch or overlap)."""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def to_local(part, x, y):
    """Board point -> footprint-local point (inverse of place_tidy.to_board)."""
    fx, fy, fr = part.at
    a = math.radians(fr)
    dx, dy = x - fx, y - fy
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def silk_of(side):
    return "F.SilkS" if side == "F.Cu" else "B.SilkS"


def prop(part, name):
    for p in children(part.node, "property"):
        if p[1] == name:
            return p
    return None


def set_hidden(node, hidden):
    """Show or hide a footprint property; (hide yes) goes right after its (layer ...)."""
    node[:] = [n for n in node if not (isinstance(n, list) and n and n[0] == "hide")]
    if hidden:
        at = next(i for i, n in enumerate(node) if isinstance(n, list) and n[0] == "layer")
        node.insert(at + 1, ["hide", "yes"])


# ---------------------------------------------------------------- main
def main(path):
    root = parse(open(path).read())

    # 1. remove what an earlier run made -------------------------------------------------
    root[:] = [n for n in root if not (isinstance(n, list) and is_ours(n))]
    for fp in children(root, "footprint"):
        fp[:] = [n for n in fp if not (isinstance(n, list) and n[0] == "fp_text" and is_ours(n))]

    parts = {Part(fp).ref: Part(fp) for fp in children(root, "footprint")}

    # 2. silk strokes up to the JLC minimum ----------------------------------------------
    bumped = 0
    for node in list(children(root, "footprint")) + [root]:
        for g in node:
            if not (isinstance(g, list) and g and g[0] in (
                    "fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly",
                    "gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly")):
                continue
            lay = child(g, "layer")
            st = child(g, "stroke")
            if lay is None or st is None or not str(lay[1]).endswith("SilkS"):
                continue
            w = child(st, "width")
            if w is not None and float(w[1]) < LINE:
                w[1] = fmt(LINE)
                bumped += 1

    # 3. obstacles for the label search -----------------------------------------------
    edge = (CX - SIZE / 2 + EDGE, CY - SIZE / 2 + EDGE, CX + SIZE / 2 - EDGE, CY + SIZE / 2 - EDGE)
    pads = {"F.Cu": [], "B.Cu": []}
    crt = {"F.Cu": [], "B.Cu": []}
    for ref, p in parts.items():
        side = str(p.side)
        if p.local_box("CrtYd"):
            crt[side].append((ref, bbox(p.courtyard())))
        for pad, poly in zip(children(p.node, "pad"), p.pads()):
            if pad[2] in ("thru_hole", "np_thru_hole"):
                pads["F.Cu"].append(bbox(poly))
                pads["B.Cu"].append(bbox(poly))
            elif side in pads:
                pads[side].append(bbox(poly))
    placed = {"F.Cu": [], "B.Cu": []}       # silk boxes laid so far
    # footprint silk graphics (outlines, pin-1 marks) count as laid silk too
    for p in parts.values():
        fx, fy, fr = p.at
        for g in p.node:
            if not (isinstance(g, list) and g and g[0] in ("fp_line", "fp_arc", "fp_circle",
                                                           "fp_rect", "fp_poly")):
                continue
            lay = child(g, "layer")
            if lay is None or not str(lay[1]).endswith("SilkS"):
                continue
            pts = [child(g, k) for k in ("start", "end", "mid", "center") if child(g, k)]
            if child(g, "pts"):
                pts += [c for c in child(g, "pts")[1:] if isinstance(c, list)]
            xy = [to_board(fx, fy, fr, float(c[1]), float(c[2])) for c in pts]
            if g[0] == "fp_circle":
                c, e = xy[-1], xy[0]          # center listed last above, end first
                r = math.hypot(e[0] - c[0], e[1] - c[1])
                xy = [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]
            b = bbox(xy)
            side = "F.Cu" if str(lay[1]).startswith("F.") else "B.Cu"
            placed[side].append((b[0] - LINE / 2, b[1] - LINE / 2, b[2] + LINE / 2, b[3] + LINE / 2))

    def add_text(layer_side, text, x, y, size, thick, ang=0.0):
        """Board-level text."""
        root.append(["gr_text", q(text), ["at", fmt(x), fmt(y), fmt(ang)],
                     ["layer", q(silk_of(layer_side))], ["uuid", new_uuid()],
                     effects(size, thick, layer_side == "B.Cu")])
        placed[layer_side].append(text_box(x, y, text, size, thick, ang))

    def add_shape(layer_side, node, box):
        node.append(["layer", q(silk_of(layer_side))])
        node.append(["uuid", new_uuid()])
        root.append(node)
        placed[layer_side].append(box)

    # 4. fixed graphics ----------------------------------------------------------------
    # 4a. mic rings and numbers on the bottom (the sky face)
    for ref, num in MICS.items():
        p = parts[ref]
        hole = [pd for pd in children(p.node, "pad") if pd[2] == "np_thru_hole"][0]
        a = child(hole, "at")
        hx, hy = to_board(*p.at, float(a[1]), float(a[2]))
        add_shape("B.Cu", ["gr_circle", ["center", fmt(hx), fmt(hy)],
                           ["end", fmt(hx + RING_R), fmt(hy)],
                           ["stroke", ["width", fmt(RING_W)], ["type", "solid"]], ["fill", "no"]],
                  (hx - 1.5, hy - 1.5, hx + 1.5, hy + 1.5))
        # number 2.6 mm from the hole, towards the board centre
        d = math.hypot(CX - hx, CY - hy)
        nx, ny = hx + (CX - hx) / d * 2.6, hy + (CY - hy) / d * 2.6
        add_text("B.Cu", num, nx, ny, *BIG)

    # 4b. board name along the south edge of the bottom, between the mic rings
    add_text("B.Cu", BOARD_NAME, CX, CY + 31.7, *NAME)
    add_text("B.Cu", "rev1  2026-11", CX, CY + 34.0, *BIG)

    # 4c. LED chain arrow: D801 -> D802, just inside the ring
    a1 = math.atan2(parts["D801"].at[1] - CY, parts["D801"].at[0] - CX)
    a2 = math.atan2(parts["D802"].at[1] - CY, parts["D802"].at[0] - CX)
    da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    am = a1 + da / 2
    r = 23.0
    mx, my = CX + r * math.cos(am), CY + r * math.sin(am)
    sgn = 1 if da > 0 else -1
    tx, ty = -math.sin(am) * sgn, math.cos(am) * sgn          # tangent towards D802
    nx, ny = math.cos(am), math.sin(am)                       # outward normal
    tail = (mx - tx * 1.2, my - ty * 1.2)
    tip = (mx + tx * 1.2, my + ty * 1.2)
    add_shape("B.Cu", ["gr_line", ["start", fmt(tail[0]), fmt(tail[1])],
                       ["end", fmt(mx), fmt(my)],
                       ["stroke", ["width", fmt(LINE)], ["type", "solid"]]],
              (min(tail[0], mx) - .1, min(tail[1], my) - .1, max(tail[0], mx) + .1, max(tail[1], my) + .1))
    head = [tip, (mx + nx * 0.5, my + ny * 0.5), (mx - nx * 0.5, my - ny * 0.5)]
    add_shape("B.Cu", ["gr_poly", ["pts"] + [["xy", fmt(x), fmt(y)] for x, y in head],
                       ["stroke", ["width", fmt(LINE)], ["type", "solid"]], ["fill", "yes"]],
              bbox(head))

    # 4d. J701 pin names at the pins: odd row above the header, even row below it
    j7 = parts["J701"]
    for pad in children(j7.node, "pad"):
        pin = int(pad[1])
        px, py = to_board(*j7.at, float(child(pad, "at")[1]), float(child(pad, "at")[2]))
        half = float(child(pad, "size")[1]) / 2          # pads run north-south, 3.12 mm long
        h, t = SMALL
        if pin in J701_NORTH:
            name = J701_NORTH[pin]
            ln = len(name) * CHAR * h + t
            cy = py - half - GAP - ln / 2
            root.append(["gr_text", q(name), ["at", fmt(px), fmt(cy), "90"],
                         ["layer", q("F.SilkS")], ["uuid", new_uuid()], effects(h, t, False)])
            placed["F.Cu"].append((px - h / 2 - t, cy - ln / 2, px + h / 2 + t, cy + ln / 2))
        else:
            name = J701_SOUTH[pin]
            ln = len(name) * CHAR * h + t
            cy = py + half + GAP + (h + t) / 2
            root.append(["gr_text", q(name), ["at", fmt(px), fmt(cy), "0"],
                         ["layer", q("F.SilkS")], ["uuid", new_uuid()],
                         effects(h, t, False)])
            placed["F.Cu"].append((px - ln / 2, cy - (h + t) / 2, px + ln / 2, cy + (h + t) / 2))

    # 4d2. J301 JTAG pin names: one per pin, turned 90 degrees, just south of the courtyard
    j3 = parts["J301"]
    j3_low = bbox(j3.courtyard())[3]               # south edge of the connector courtyard
    for pad in children(j3.node, "pad"):
        if pad[1] not in [str(k) for k in J301_NAMES]:
            continue                               # skip the mounting pads
        a = child(pad, "at")
        px, _ = to_board(*j3.at, float(a[1]), float(a[2]))
        name = J301_NAMES[int(pad[1])]
        cy = j3_low + 0.25 + len(name) * CHAR * SMALL[0] / 2 + SMALL[1] / 2
        add_text("F.Cu", name, px, cy, *SMALL, 90.0)

    # 4e. blank serial-number box (filled, so a marker writes on it)
    sx0, sy0, sx1, sy1 = SERIAL_BOX
    add_shape("F.Cu", ["gr_rect", ["start", fmt(sx0), fmt(sy0)], ["end", fmt(sx1), fmt(sy1)],
                       ["stroke", ["width", fmt(LINE)], ["type", "solid"]], ["fill", "yes"]],
              SERIAL_BOX)

    # 5. decide every footprint label ---------------------------------------------------
    jobs = []   # (part or None, text, size, thick, anchor box, side, kind)
    for ref, p in sorted(parts.items()):
        side = str(p.side)
        refp = prop(p, "Reference")
        keep = ref in KEEP_REFS or (side == "B.Cu" and (ref[:1] in "UQY" or ref in BOTTOM_REFS))
        if ref in FUNCTION:
            set_hidden(refp, True)
            jobs.append((p, FUNCTION[ref], *BIG, side, "fp_text"))
        elif ref.startswith("TP"):
            set_hidden(refp, True)
            jobs.append((p, str(p.props["Value"]), *SMALL, side, "fp_text"))
        elif keep:
            set_hidden(refp, False)
            size = SMALL if ref in SMALL_REFS else BIG
            jobs.append((p, ref, *size, side, "ref"))
        else:
            set_hidden(refp, True)

    # extra board labels anchored to groups of parts
    def group_box(refs):
        boxes = [bbox(parts[r].courtyard()) for r in refs]
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    extras = [("ESP TO XVF FLASH\nCUT TO DISCONNECT", SMALL, group_box(["R706", "R707", "R708", "R709"]), "F.Cu"),
              ("S/N", SMALL, SERIAL_BOX, "F.Cu")]

    # 6. label search --------------------------------------------------------------------
    def free(box, side, loose):
        if box[0] < edge[0] or box[1] < edge[1] or box[2] > edge[2] or box[3] > edge[3]:
            return False
        # the outline has 5 mm corner radii: every box corner must stay inside them too
        rc = 5.0
        for px in (box[0], box[2]):
            for py in (box[1], box[3]):
                ccx = min(max(px, CX - SIZE / 2 + rc), CX + SIZE / 2 - rc)
                ccy = min(max(py, CY - SIZE / 2 + rc), CY + SIZE / 2 - rc)
                if math.hypot(px - ccx, py - ccy) > rc - EDGE:
                    return False
        if any(hit(box, b, GAP) for b in pads[side]):
            return False
        if any(hit(box, b, GAP) for b in placed[side]):
            return False
        for ref, b in crt[side]:
            if loose and ref[:1] in "RCLF":      # loose pass: may sit over small passives
                continue
            if hit(box, b, 0.05):
                return False
        return True

    def search(text, size, thick, anchor, side):
        """Closest free spot: list every candidate by score, then test them in order."""
        step = 0.2
        acx, acy = (anchor[0] + anchor[2]) / 2, (anchor[1] + anchor[3]) / 2
        half = max(anchor[2] - anchor[0], anchor[3] - anchor[1]) / 2
        for loose, reach in ((False, 3.0), (False, 6.0), (True, 6.0)):
            n = int((reach + half + len(text) * size) / step)
            cands = []
            for ang in (0.0, 90.0):
                for i in range(-n, n + 1):
                    for j in range(-n, n + 1):
                        x, y = acx + i * step, acy + j * step
                        box = text_box(x, y, text, size, thick, ang)
                        if hit(box, anchor, 0.05):
                            continue
                        g = box_gap(box, anchor)
                        if g <= reach:
                            cands.append((g + (1.5 if ang else 0.0), x, y, ang, box))   # prefer horizontal text
            cands.sort(key=lambda c: c[0])
            for c in cands:
                if free(c[4], side, loose):
                    return c, loose, reach
        return None, None, None

    report = []

    def lay(text, size, thick, anchor, side, part=None, kind="gr"):
        best, loose, reach = search(text, size, thick, anchor, side)
        if best is None:
            report.append(f"NO SPOT: {text}")
            return
        _, x, y, ang, box = best
        placed[side].append(box)
        if loose or reach > 3.0:
            report.append(f"looser search ({'over passives' if loose else 'up to 6 mm'}): {text}")
        if part is None:
            add_text(side, text, x, y, size, thick, ang)
            placed[side].pop()          # add_text re-adds the same box
            return
        lx, ly = to_local(part, x, y)
        mirror = side == "B.Cu"
        if kind == "ref":
            # rebuild the Reference property in KiCad's own order: at, layer, uuid, effects
            refp = prop(part, "Reference")
            keep_uuid = child(refp, "uuid")
            refp[3:] = [["at", fmt(lx), fmt(ly), fmt(ang)], ["layer", q(silk_of(side))],
                        keep_uuid, effects(size, thick, mirror)]
        else:
            part.node.append(["fp_text", "user", q(text), ["at", fmt(lx), fmt(ly), fmt(ang)],
                              ["layer", q(silk_of(side))], ["uuid", new_uuid()],
                              effects(size, thick, mirror)])

    # sky-face arrows + labels, laid before the other labels so those keep clear of them.
    # Lined up (user 2026-11-23): on each edge every arrow has its tip at the edge and the same
    # shaft length, so the arrows form one column and the labels start on one line. The shaft
    # length is the shortest that lets every label on that edge fit on its part's centreline.
    def sky_try(ref, text, s, k):
        """Arrow + label for one part with shaft step k; None if anything is blocked."""
        py = parts[ref].at[1]
        tip = CX + s * (SIZE / 2 - EDGE)
        base = tip - s * ARROW_HEAD[0]                   # where the head meets the shaft
        tail = base - s * (ARROW_SHAFT + 0.2 * k)
        h, t = BIG
        head_box = (min(tip, base), py - ARROW_HEAD[1], max(tip, base), py + ARROW_HEAD[1])
        shaft_box = (min(tail, base), py - LINE, max(tail, base), py + LINE)
        for box in (head_box, shaft_box):
            if any(hit(box, b, 0.1) for b in pads["B.Cu"]) or any(hit(box, b) for b in placed["B.Cu"]):
                return None
        # one line first; stacked on two lines (centred on the same line) if that is blocked
        for label in (text, text.replace(" ", "\n", 1)):
            w = max(len(x) for x in label.split("\n")) * CHAR * h + t
            lx = tail - s * (ARROW_TO_TEXT + w / 2)
            box = text_box(lx, py, label, h, t, 0.0)
            if free(box, "B.Cu", True):
                return dict(text=label, py=py, tip=tip, base=base, tail=tail, lx=lx,
                            head_box=head_box, shaft_box=shaft_box, box=box)
        return None

    for s in (1, -1):                                    # east edge, then west edge
        refs = [r for r in SKY_LABELS if (parts[r].at[0] > CX) == (s > 0)]
        for k in range(60):                              # shaft grows in 0.2 mm steps, <= 12 mm
            got = [sky_try(r, SKY_LABELS[r][0], s, k) for r in refs]
            # labels on one edge must not overlap each other either
            boxes = [g["box"] for g in got if g]
            if all(got) and not any(hit(a, b, GAP) for i, a in enumerate(boxes) for b in boxes[i + 1:]):
                break
        else:
            report.append(f"NO COMMON SHAFT LENGTH ON THE {'EAST' if s > 0 else 'WEST'} EDGE")
            continue
        if k:
            report.append(f"{'east' if s > 0 else 'west'} arrows lengthened {0.2 * k:.1f} mm to fit every label")
        for g in got:
            if "\n" in g["text"]:
                report.append(f"stacked on two lines to fit: {g['text']!r}")
            py = g["py"]
            add_shape("B.Cu", ["gr_line", ["start", fmt(g["tail"]), fmt(py)], ["end", fmt(g["base"]), fmt(py)],
                               ["stroke", ["width", fmt(LINE)], ["type", "solid"]]], g["shaft_box"])
            head = [(g["tip"], py), (g["base"], py - ARROW_HEAD[1]), (g["base"], py + ARROW_HEAD[1])]
            add_shape("B.Cu", ["gr_poly", ["pts"] + [["xy", fmt(x), fmt(y)] for x, y in head],
                               ["stroke", ["width", fmt(LINE)], ["type", "solid"]], ["fill", "yes"]],
                      g["head_box"])
            add_text("B.Cu", g["text"], g["lx"], py, *BIG)

    # big parts first, then function labels, then the small names
    order = sorted(jobs, key=lambda j: (j[5] != "fp_text" and not j[0].ref.startswith("U"),
                                        j[1].startswith(("R", "TP")), j[0].ref))
    for part, text, size, thick, side, kind in order:
        lay(text, size, thick, bbox(part.courtyard()), side, part, kind)
    for text, (size, thick), anchor, side in extras:
        lay(text, size, thick, anchor, side)

    open(path, "w").write(dump(root) + "\n")
    print(f"silk strokes bumped to {LINE} mm: {bumped}")
    print(f"labels laid: {len(jobs) + len(extras) + len(SKY_LABELS)}")
    for line in report:
        print("  " + line)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else BOARD)
