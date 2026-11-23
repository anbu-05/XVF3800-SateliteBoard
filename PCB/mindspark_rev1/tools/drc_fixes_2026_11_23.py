"""DRC fixes before ordering (user 2026-11-23: "fix all the DRC issues").

Usage (PCB editor closed):
    python3 tools/drc_fixes_2026_11_23.py              # edit the board and the library
    python3 tools/drc_fixes_2026_11_23.py --check      # only report what would change

Every fix is made the same way in the library footprint (PCB/libraries/footprints/
Mindspark.pretty) and in each copy of it on the board, so KiCad's "footprint differs from
library" check stays clean. The script is idempotent: a second run finds nothing to change.

What it fixes (DRC on 2026-11-23: 61 items):
  1. Switch locating pegs (TS24CA SW401/402/603, MSK12C02 SW701): the plastic pegs had
     plated holes with no copper ring (padstack + annular_width errors). They are now
     non-plated holes (np_thru_hole), same size.
  2. Mic land pattern (IM69D129, MK501-504). Infineon's recommended pattern (datasheet p.13,
     Figure 14) puts the 0.75 mm tall pads on a 0.838 mm pitch: a 0.088 mm gap, under JLC's
     0.1 mm and our 0.15 mm clearance. Pads 1, 2, 4, 5 are trimmed to 0.688 mm tall about
     their own centres (gap 0.15 mm; still larger than the 0.63 mm stencil opening the
     datasheet asks for). The GND ring round the sound port: its inner diameter goes from
     0.985 to 1.01 mm (outer 1.725 mm kept), so the 0.6 mm port hole has 0.205 mm to copper
     (rule 0.2). The pad's small anchor circle now sits exactly inside the ring.
     SUPERSEDED 2026-11-23 (tools/part_swap_2026_11_23.py): the 0.838 mm "pitch" was a misread
     (it is centre line to pad row; rows are 1.675 mm apart), so the footprint was replaced by
     Knowles_SPH0641LM4H-1_LGA-5_3.5x2.65mm with full 0.75 mm pads on the right rows. fix_mic is
     no longer in FIXES (it would trim the new pads again).
  3. Silk crossing the board edge on the edge parts. Every remaining silk stroke ends at
     least 0.1 mm inside the edge:
       - TS24CA, MSK12C02, USB-C (HRO): the outline of the part's overhang past the edge is
         cut back to stubs that stop inside the board; the cross line off the board goes.
       - LED_0603 (D401, D201): the edge-side outline line moves in 0.735 -> 0.6 mm.
       - WS2812B-2020 (D601 and the ring): outline sides move in 1.6 -> 1.35 mm (both sides,
         keeps it symmetric; still clear of the pads); the pin-1 bevel becomes a 0.15 mm
         chamfer so it stays off pad 1.
       - TOGIALED RGB (D402): the pin-1 dot moves 0.27 mm away from the edge.
  4. Test pads (TestPoint_Pad_D1.0mm): board copies said "exclude from BOM" only, the library
     said "exclude from BOM and placement file". For JLC both are right (no part to place), so
     the board copies now match the library; library silk ring 0.12 -> 0.15 mm like the board,
     and the library circles start at the same point as the board copies.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, dump, children, child, q          # noqa: E402

BOARD = os.path.join(HERE, "..", "mindspark_rev1.kicad_pcb")
LIB = os.path.join(HERE, "..", "..", "libraries", "footprints", "Mindspark.pretty")

changes = []


def note(where, what):
    changes.append(f"{where}: {what}")


# ---------------------------------------------------------------- small helpers
def silk_lines(fp):
    """fp_line items on a silkscreen layer."""
    for g in fp:
        if isinstance(g, list) and g and g[0] == "fp_line" and str(child(g, "layer")[1]).endswith("SilkS"):
            yield g


def xy(node, key):
    c = child(node, key)
    return float(c[1]), float(c[2])


def set_xy(node, key, x, y):
    c = child(node, key)
    c[1], c[2] = fmt(x), fmt(y)


def fmt(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def same(a, b):
    return abs(a - b) < 1e-6


def drop_line(fp, a, b, where):
    """Remove the silk line between points a and b (either direction)."""
    for g in list(silk_lines(fp)):
        s, e = xy(g, "start"), xy(g, "end")
        if (all(map(same, s, a)) and all(map(same, e, b))) or (all(map(same, s, b)) and all(map(same, e, a))):
            fp.remove(g)
            note(where, f"silk line {a}-{b} removed")


def move_y(fp, old, new, where, xs=None):
    """Move every silk line end at y == old to y == new (optionally only at these x)."""
    for g in silk_lines(fp):
        for k in ("start", "end"):
            x, y = xy(g, k)
            if same(y, old) and (xs is None or any(same(x, v) for v in xs)):
                set_xy(g, k, x, new)
                note(where, f"silk end ({x}, {old}) -> ({x}, {new})")


def move_x(fp, old, new, where):
    for g in silk_lines(fp):
        for k in ("start", "end"):
            x, y = xy(g, k)
            if same(x, old):
                set_xy(g, k, new, y)
                note(where, f"silk end ({old}, {y}) -> ({new}, {y})")


def move_pt(fp, old, new, where):
    for g in silk_lines(fp):
        for k in ("start", "end"):
            if all(map(same, xy(g, k), old)):
                set_xy(g, k, *new)
                note(where, f"silk end {old} -> {new}")


def pegs_to_npth(fp, where):
    """Plated unnumbered peg holes -> non-plated."""
    for p in children(fp, "pad"):
        if p[1] in ('""', "") and p[2] == "thru_hole":
            p[2] = "np_thru_hole"
            p[:] = [n for n in p if not (isinstance(n, list) and n[0] == "remove_unused_layers")]
            note(where, f"peg hole at {child(p, 'at')[1:3]} -> np_thru_hole")


# ---------------------------------------------------------------- the fixes, per footprint
def fix_ts24ca(fp, where):
    pegs_to_npth(fp, where)
    # actuator outline sticks 0.31 mm past the edge: keep stubs to y = -1.945 (0.1 mm inside
    # after the 0.25 mm stroke), drop the cross line off the board
    drop_line(fp, (-1, -2.43), (1, -2.43), where)
    move_y(fp, -2.43, -1.945, where, xs=(-1, 1))


def fix_msk12c02(fp, where):
    pegs_to_npth(fp, where)
    # actuator outline 1.18 mm past the edge: stubs to y = 2.125, cross line goes
    drop_line(fp, (0.15, 3.53), (1.43, 3.53), where)
    move_y(fp, 3.53, 2.125, where, xs=(0.15, 1.43))


def fix_usb_hro(fp, where):
    # shell front 0.885 mm past the edge: side lines stop at y = 2.84, front line goes
    drop_line(fp, (-4.7, 3.9), (4.7, 3.9), where)
    move_y(fp, 3.9, 2.84, where, xs=(-4.7, 4.7))


def fix_led0603(fp, where):
    # the +y outline line lies along the east edge for D401/D201 (only users of this footprint)
    move_y(fp, 0.735, 0.6, where)


def fix_ws2812(fp, where):
    # bevel corner first, then the two sides. Bottom-side copies (the LED ring) are stored
    # mirrored in y by KiCad, so their bevel corner sits at y = +1.15.
    # The pin-1 bevel shrinks to a 0.15 mm chamfer: a longer one would clip pad 1's corner
    # now that the side has moved in (silk 0.056 mm clear of the pad).
    for sy in (-1, 1):
        move_pt(fp, (-1.3, 1.15 * sy), (-1.2, 1.15 * sy), where)
        move_pt(fp, (-1.6, 0.85 * sy), (-1.35, 1.0 * sy), where)
        move_pt(fp, (-1.6, 0.850001 * sy), (-1.35, 1.0 * sy), where)
    move_x(fp, -1.6, -1.35, where)
    move_x(fp, 1.6, 1.35, where)


def fix_togialed(fp, where):
    for g in fp:
        if isinstance(g, list) and g and g[0] == "fp_circle" and str(child(g, "layer")[1]).endswith("SilkS"):
            if same(xy(g, "center")[1], -1.05):
                set_xy(g, "center", 1.7, -0.78)
                set_xy(g, "end", 1.6, -0.78)
                note(where, "pin-1 dot (1.7, -1.05) -> (1.7, -0.78)")


def fix_mic(fp, where):
    for p in children(fp, "pad"):
        if p[1] in ('"1"', '"2"', '"4"', '"5"', "1", "2", "4", "5"):
            sz = child(p, "size")
            if same(float(sz[2]), 0.75):
                sz[2] = "0.688"
                note(where, f"pad {p[1]} height 0.75 -> 0.688")
        if p[1] in ('"3"', "3"):
            at, sz = child(p, "at"), child(p, "size")
            if same(float(at[1]), 1.3875):
                at[1] = "1.39375"
                sz[1] = sz[2] = "0.3575"
                circ = child(child(p, "primitives"), "gr_circle")
                child(circ, "center")[1] = "-0.68375"
                child(circ, "width")[1] = "0.3575"
                note(where, "pad 3 ring inner dia 0.985 -> 1.01 mm (outer 1.725 kept)")


TP_ATTR = ["attr", "exclude_from_pos_files", "exclude_from_bom"]


def fix_tp_board(fp, where, lib_fp):
    a = child(fp, "attr")
    if a != TP_ATTR:
        a[:] = list(TP_ATTR)
        note(where, "attr -> exclude_from_pos_files exclude_from_bom")
    for key in ("descr", "tags"):
        if child(fp, key) != child(lib_fp, key):
            child(fp, key)[1] = child(lib_fp, key)[1]
            note(where, f"{key} -> library text")


def fix_tp_lib(fp, where):
    for g in fp:
        if isinstance(g, list) and g and g[0] == "fp_circle" and child(g, "layer")[1] == q("F.SilkS"):
            w = child(child(g, "stroke"), "width")
            if float(w[1]) < 0.15:
                w[1] = "0.15"
                note(where, "silk ring 0.12 -> 0.15")
    # KiCad compares circles by their stored end point: start them where the board copies do
    for g in fp:
        if isinstance(g, list) and g and g[0] == "fp_circle":
            e = child(g, "end")
            r = max(abs(float(e[1])), abs(float(e[2])))
            if [float(e[1]), float(e[2])] != [0.0, -r]:
                e[1], e[2] = "0", fmt(-r)
                note(where, f"circle r {r} end point -> (0, {-r})")


FIXES = {
    "SW_SHOUHAN_TS24CA_SideActuated": fix_ts24ca,
    "SW_SHOUHAN_MSK12C02_SideActuated": fix_msk12c02,
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12": fix_usb_hro,
    "LED_0603_1608Metric": fix_led0603,
    "LED_WS2812B-2020_PLCC4_2.0x2.0mm": fix_ws2812,
    "LED_RGB_TOGIALED_1615_1.6x1.5mm": fix_togialed,
    # fix_mic (the pad trim) is retired: that footprint was replaced 2026-11-23 (see item 2 above)
}


def main(check):
    # library files
    libs = {}
    for name in list(FIXES) + ["TestPoint_Pad_D1.0mm"]:
        path = os.path.join(LIB, name + ".kicad_mod")
        root = parse(open(path).read())
        if name in FIXES:
            FIXES[name](root, "lib " + name)
        else:
            fix_tp_lib(root, "lib " + name)
        libs[name] = (path, root)

    # board copies
    board = parse(open(BOARD).read())
    for fp in children(board, "footprint"):
        lib_name = str(fp[1]).strip('"').split(":", 1)[-1]
        ref = next(p[2] for p in children(fp, "property") if p[1] == q("Reference"))
        if lib_name in FIXES:
            FIXES[lib_name](fp, ref)
        elif lib_name == "TestPoint_Pad_D1.0mm":
            fix_tp_board(fp, ref, libs[lib_name][1])

    for line in changes:
        print("  " + line)
    print(f"{len(changes)} changes")
    if check or not changes:
        return
    for path, root in libs.values():
        open(path, "w").write(dump(root) + "\n")
    open(BOARD, "w").write(dump(board) + "\n")
    print("written: board + %d library footprints" % len(libs))


if __name__ == "__main__":
    main("--check" in sys.argv)
