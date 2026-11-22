"""Test pads: drop the duplicates, make the rest round (2026-11-22, user).

User 2026-11-22: test pads are uniform 1 mm round pads, top or bottom, placed wherever comfortable
near their signal; duplicates are removed. Labels come later.

Duplicates removed (schematic symbol, its wire stub and the board footprint):
  TP301-TP307  wired in parallel with J301 (XTAG4 JTAG header) pins 1-7: +1V8, TCK, TMS, RST_N,
               TDO, TDI, GND. The header pins are the probe points.
  TP201-TP203  +5V, +3V3, +1V8: the same rails are on J701 pins 1/23, 2/24 and 3.
  TP205        GND (added 2026-11-22: the user deleted it on the board; GND is on every header).
Kept: TP204 (+0V9, on no header) and TP401-TP412 (XVF QSPI, SQ_NLIN, XL lines, I2S, MCLK).

The kept pads switch to Mindspark:TestPoint_Pad_D1.0mm (copied from KiCad's TestPoint library):
schematic footprint field, and on the board the pad shape (rect -> circle) and the outline
graphics (silk circle r 0.7, courtyard circle r 1.0) on the footprint's own side.

Run once, PCB and schematic editors closed:  python3 tools/test_pads_2026_11_22.py
Running it again changes nothing (removed parts are gone, kept ones are already round).
"""
import os
import sys
import uuid
sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

HERE = os.path.dirname(BOARD)
REMOVE = {"TP201", "TP202", "TP203", "TP205", "TP301", "TP302", "TP303", "TP304", "TP305", "TP306", "TP307"}
KEEP = {"TP204"} | {f"TP{n}" for n in range(401, 413)}
NEW_FP = "Mindspark:TestPoint_Pad_D1.0mm"
OLD_FP = "Mindspark:TestPoint_Pad_1.0x1.0mm"


def ref_of(node):
    r = [p[2] for p in children(node, "property") if p[1] == "Reference"]
    return r[0] if r else None


def pts_of(wire):
    return [(float(p[1]), float(p[2])) for p in children(child(wire, "pts"), "xy")]


def close(a, b):
    return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01


# ------------------------------------------------------------------ schematic
def fix_regulators():
    """TP201-TP203, TP205: each pin has a short wire down to its own power symbol; all three go."""
    path = os.path.join(HERE, "regulators.kicad_sch")
    root = parse(open(path).read())
    gone = 0
    for s in list(children(root, "symbol")):
        if ref_of(s) not in REMOVE:
            continue
        at = child(s, "at")
        pin = (float(at[1]), float(at[2]))
        for w in list(children(root, "wire")):
            p = pts_of(w)
            if any(close(q, pin) for q in p):
                other = p[1] if close(p[0], pin) else p[0]
                root.remove(w)
                # the power symbol at the wire's other end only fed this test pad
                for ps in list(children(root, "symbol")):
                    a = child(ps, "at")
                    if (ref_of(ps) or "").startswith("#PWR") and close((float(a[1]), float(a[2])), other):
                        root.remove(ps)
        root.remove(s)
        gone += 1
    for s in children(root, "symbol"):
        if ref_of(s) in KEEP:
            for p in children(s, "property"):
                if p[1] == "Footprint":
                    p[2] = q(NEW_FP)
    open(path, "w").write(dump(root) + "\n")
    print(f"regulators: removed {gone} test pads")


def fix_xvf3800():
    """TP301-TP307 sit in a column at x 38.1, each wired east to J301's pin column (x 55.88),
    through a net label or power symbol at x 53.34. Cut each wire back to start at x 53.34 so the
    labels keep their connection, drop the test pads and the two junctions they needed."""
    path = os.path.join(HERE, "xvf3800.kicad_sch")
    root = parse(open(path).read())
    gone = 0
    for s in list(children(root, "symbol")):
        if ref_of(s) not in REMOVE:
            continue
        at = child(s, "at")
        pin = (float(at[1]), float(at[2]))
        for w in list(children(root, "wire")):
            p = pts_of(w)
            k = [i for i, q in enumerate(p) if close(q, pin)]
            if not k:
                continue
            other = p[1 - k[0]]
            if other[0] > 53.34 + 0.01:                 # runs on to J301: start it at the label
                xy = children(child(w, "pts"), "xy")[k[0]]
                xy[1] = "53.34"  # numbers are plain tokens
            else:                                       # ends at the label: no longer needed
                root.remove(w)
        root.remove(s)
        gone += 1
    for j in list(children(root, "junction")):
        a = child(j, "at")
        if abs(float(a[1]) - 53.34) < 0.01 and float(a[2]) in (139.7, 154.94):
            root.remove(j)
    open(path, "w").write(dump(root) + "\n")
    print(f"xvf3800: removed {gone} test pads")


def fix_periph():
    path = os.path.join(HERE, "xvf3800_periph.kicad_sch")
    root = parse(open(path).read())
    for s in children(root, "symbol"):
        if ref_of(s) in KEEP:
            for p in children(s, "property"):
                if p[1] == "Footprint":
                    p[2] = q(NEW_FP)
    open(path, "w").write(dump(root) + "\n")


# ------------------------------------------------------------------ board
def fix_board():
    root = parse(open(BOARD).read())
    removed = changed = 0
    for f in list(children(root, "footprint")):
        ref = ref_of(f)
        if ref in REMOVE:
            root.remove(f)
            removed += 1
            continue
        if ref not in KEEP or f[1] == NEW_FP:
            continue
        side = "B" if str(child(f, "layer")[1]).startswith("B") else "F"
        f[1] = q(NEW_FP)
        for p in children(f, "property"):
            if p[1] == "Value" and p[2] == OLD_FP.split(":")[1]:
                p[2] = q(NEW_FP.split(":")[1])
        for g in list(children(f, "fp_line")) + list(children(f, "fp_rect")):
            f.remove(g)
        pad = child(f, "pad")
        pad[3] = "circle"
        # outline: silk ring just outside the pad, round courtyard (as KiCad's TestPoint_Pad_D1.0mm)
        at_pad = children(f, "pad")[0]
        i = f.index(at_pad)
        for r, w, lay in ((0.7, 0.12, f"{side}.SilkS"), (1.0, 0.05, f"{side}.CrtYd")):
            f.insert(i, ["fp_circle", ["center", "0", "0"], ["end", "0", f"{r}"],
                         ["stroke", ["width", f"{w}"], ["type", "solid"]], ["fill", "no"],
                         ["layer", q(lay)], ["uuid", q(uuid.uuid4())]])
        changed += 1
    open(BOARD, "w").write(dump(root) + "\n")
    print(f"board: removed {removed} footprints, made {changed} round")


fix_regulators()
fix_xvf3800()
fix_periph()
fix_board()
