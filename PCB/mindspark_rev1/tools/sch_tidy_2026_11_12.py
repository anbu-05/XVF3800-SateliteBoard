"""One-off schematic tidy of the user's hand edits (2026-11-12).

The generator (build_schematic.py) is retired: the sheets were saved in KiCad at 20:45 with
edits the generator does not have (per-mic supply filters, R609, the USB ESD pin remap).
Only three sheets differ from the last verified generator output (03:07), so only these
are touched. Everything is a whole-group translation on the 50 mil grid, a box refit, or
one restored wire, so pin-to-net partitions stay the same except the J102 VBUS fix.

    usb_power  - restore J102's VBUS lead wire (pin A4 -> VBUS_ESP symbol), deleted by
                 accident: J102's VBUS pins had become their own net (2 ERC errors).
               - lift each USB box's VBUS row (TVS + 10 uF + 100 nF) 150 mil back up,
                 so the boxes get their 300 mil bottom padding again.
    audio      - Mic supply box: shift the four filters right to 300 mil left padding,
                 then shrink the box to its content.
               - Amp load switch box: move it to the packing position (200 mil right of
                 the amp box, tops aligned) and fit it to its content.
    esp32      - User button box: extend the bottom for R609 (to the supply box's bottom).

Run from the project folder with KiCad closed on the schematic:  python3 -I tools/sch_tidy_2026_11_12.py
Box edges are finished by measuring KiCad's own SVG plot (tools/measure_boxes.py) after the moves.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sexpr import parse, dump, children, child, Quoted

HERE = Path(__file__).resolve().parent.parent
G = 1.27                       # 50 mil grid
PAD = 7.62                     # 300 mil box padding


def r4(v):
    """Round to 4 decimals, as KiCad writes coordinates."""
    return f"{round(v, 4):.4f}".rstrip("0").rstrip(".")


def inside(x, y, box):
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1


def anchor_points(item):
    """Every coordinate an item sits on (symbol origin, wire ends, label anchor ...)."""
    kind = item[0]
    if kind == "wire":
        return [(float(p[1]), float(p[2])) for p in children(child(item, "pts"), "xy")]
    at = child(item, "at")
    return [(float(at[1]), float(at[2]))] if at else []


def shift_at(node, dx, dy):
    at = child(node, "at")
    at[1], at[2] = r4(float(at[1]) + dx), r4(float(at[2]) + dy)


def translate(root, region, dx, dy, skip_text=()):
    """Move every top-level item whose anchors all lie in `region` by (dx, dy).

    Symbols take their fields with them; wires move both ends. Box headings are text
    items and are listed in `skip_text`, since they follow the box, not the circuit.
    Returns the number of items moved.
    """
    kinds = ("symbol", "wire", "junction", "label", "hierarchical_label", "global_label", "no_connect", "text")
    n = 0
    for item in root:
        if not (isinstance(item, list) and item and item[0] in kinds):
            continue
        if item[0] == "text" and item[1] in skip_text:
            continue
        pts = anchor_points(item)
        if not pts or not all(inside(x, y, region) for x, y in pts):
            continue
        if item[0] == "wire":
            for p in children(child(item, "pts"), "xy"):
                p[1], p[2] = r4(float(p[1]) + dx), r4(float(p[2]) + dy)
        else:
            shift_at(item, dx, dy)
            for prop in children(item, "property"):
                shift_at(prop, dx, dy)
        n += 1
    return n


def set_box(root, old_start, new_start, new_end, heading):
    """Move/resize the rectangle that starts at `old_start`, and its heading text."""
    for rect in children(root, "rectangle"):
        s = child(rect, "start")
        if abs(float(s[1]) - old_start[0]) < 0.01 and abs(float(s[2]) - old_start[1]) < 0.01:
            s[1], s[2] = r4(new_start[0]), r4(new_start[1])
            e = child(rect, "end")
            e[1], e[2] = r4(new_end[0]), r4(new_end[1])
            break
    else:
        raise SystemExit(f"box at {old_start} not found")
    for t in children(root, "text"):
        if t[1] == heading:
            at = child(t, "at")
            at[1], at[2] = r4(new_start[0] + G), r4(new_start[1] + G)   # heading 50 mil inside, as generated
            return
    raise SystemExit(f"heading {heading!r} not found")


def add_wire(root, a, b, uuid):
    wire = ["wire", ["pts", ["xy", r4(a[0]), r4(a[1])], ["xy", r4(b[0]), r4(b[1])]],
            ["stroke", ["width", "0"], ["type", "default"]], ["uuid", Quoted(uuid)]]
    # insert next to the other wires so the file keeps KiCad's grouping
    idx = max(i for i, it in enumerate(root) if isinstance(it, list) and it and it[0] == "wire")
    root.insert(idx + 1, wire)


def edit(name, fn):
    path = HERE / name
    root = parse(path.read_text())
    fn(root)
    path.write_text(dump(root) + "\n")
    print("wrote", name)


# ---------------------------------------------------------------- usb_power
def usb_power(root):
    # J102 VBUS: pin A4 end (181.61, 27.94) to the VBUS_ESP symbol at (184.15, 27.94),
    # the same 100 mil lead J101 has (48.26 -> 50.8). Fixed UUID so a rerun is identical.
    add_wire(root, (181.61, 27.94), (184.15, 27.94), "5b1c0e64-3a70-4f0e-9c1d-102a4a000001")
    # VBUS rows: D101/C101/C102 (x 66-92) and D102/C103/C104 (133.35 mm further right),
    # with their power symbols, flags, wires and junctions; nothing else lies in y 55-80 there.
    for x0 in (60.0, 60.0 + 133.35):
        moved = translate(root, (x0, 55.0, x0 + 33.0, 80.0), 0, -3 * G)
        print(f"  usb_power VBUS row at x {x0:.2f}: {moved} items up 150 mil")
    # "USB_MAIN_DP" is longer than "USB_ESP_DP", so the main box needs 0.81 mm more on the
    # right (268 -> 300 mil); the ESP32 box shifts right to keep the 200 mil gap, and its
    # spare right padding (335 mil) is trimmed to 300. No circuit moves.
    for (old, new_s, new_e, head) in BOXES["usb_power"]:
        set_box(root, old, new_s, new_e, head)


# ---------------------------------------------------------------- audio
SUPPLY_DX = 4 * G              # content left 205.07 -> 210.15 (needs >= 202.07 + 7.62)
SWITCH_DX, SWITCH_DY = 1 * G, -1 * G


def audio(root):
    n = translate(root, (202.5, 16.5, 279.0, 106.0), SUPPLY_DX, 0, skip_text=("Mic supply",))
    print(f"  audio Mic supply: {n} items right {SUPPLY_DX:.2f} mm")
    n = translate(root, (130.0, 116.0, 190.6, 162.5), SWITCH_DX, SWITCH_DY, skip_text=("Amp load switch (U502)",))
    print(f"  audio load switch: {n} items by ({SWITCH_DX:.2f}, {SWITCH_DY:.2f}) mm")
    # The sheet note predates the mic flip (mics moved to the top side on 2026-11-12).
    for t in children(root, "text"):
        if t[1].startswith("Mics: corners of a 66 x 66 mm square on the underside"):
            t[1] = Quoted(t[1].replace("square on the underside", "square on the top side"))
    # Box edges, set from the native plot measurement (BOXES below).
    for (old, new_s, new_e, head) in BOXES["audio"]:
        set_box(root, old, new_s, new_e, head)


def esp32(root):
    for (old, new_s, new_e, head) in BOXES["esp32"]:
        set_box(root, old, new_s, new_e, head)


# Box edges (start, new start, new end, heading), from the native plot measurement.
BOXES = {
    "usb_power": [
        ((14.54, 14.54), (14.54, 14.54), (143.2761, 85.1082), "USB-C main (J101, XVF3800)"),
        ((147.5431, 14.54), (148.3561, 14.54), (274.686, 85.1082), "USB-C ESP32 (J102)"),
    ],
    "audio": [
        ((202.0695, 14.54), (202.0695, 14.54), (269.5, 100.86), "Mic supply"),
        ((129.6795, 113.5608), (128.9552, 113.0482), (197.04, 158.32), "Amp load switch (U502)"),
    ],
    "esp32": [
        ((227.7821, 14.54), (227.7821, 14.54), (264.494, 79.27), "User button"),
    ],
}

if __name__ == "__main__":
    edit("usb_power.kicad_sch", usb_power)
    edit("audio.kicad_sch", audio)
    edit("esp32.kicad_sch", esp32)
