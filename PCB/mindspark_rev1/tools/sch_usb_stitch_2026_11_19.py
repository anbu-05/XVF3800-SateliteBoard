"""Schematic changes for the XVF3800 USB pair route (agreed with the user 2026-11-19).

1. xvf3800 sheet: a new box "USB stitching caps" below the crystal, with four 100 nF 0402 caps
   (C1525, same part as the decoupling caps):
     C323 (CA) +0V9 <-> +1V8   north of the pair where it leaves the In2 +0V9 island
     C324 (CB) +0V9 <-> +1V8   south of the pair, same spot
     C325 (CC) +1V8 <-> GND    north of the layer-change vias, just outside the ESP32 module
     C326 (CD) +1V8 <-> GND    south of the layer-change vias
   Each cap stands upright, pin 1 at the top, with a power symbol on each pin (as the
   decoupling caps on this sheet do). The symbols are copies of C304 and of existing power
   symbols, with new UUIDs and references.
2. usb_power sheet: D+ and D- trade channels on U101 (TPD4E05U06 ESD array; its channels are
   identical). The hierarchical label on pin 2 becomes USB_MAIN_DP and the one on pin 4
   USB_MAIN_DM, so D- lands on the pin nearer the top of the board, the side it arrives on.

Usage (schematic and PCB editors closed):  python3 tools/sch_usb_stitch_2026_11_19.py
"""
import copy
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from sexpr import parse, dump, children, child, q  # noqa: E402

HERE = __import__("os").path.dirname(__file__) + "/.."
XVF = HERE + "/xvf3800.kicad_sch"
USB = HERE + "/usb_power.kicad_sch"
SHEET_PATH = "/af1cbb83-54b2-47b9-8bc4-08bc42da7d01/0d465b1a-46e7-5808-b4ad-30de9111d093"   # xvf3800 sheet

CAPS = [  # ref, x, top net, bottom net, use
    ("C323", 99.06, "+0V9", "+1V8", "USB stitching CA: +0V9/+1V8 north of the main USB pair"),
    ("C324", 111.76, "+0V9", "+1V8", "USB stitching CB: +0V9/+1V8 south of the main USB pair"),
    ("C325", 124.46, "+1V8", "GND", "USB stitching CC: +1V8/GND north of the USB layer change"),
    ("C326", 137.16, "+1V8", "GND", "USB stitching CD: +1V8/GND south of the USB layer change"),
]
CY = 156.21                      # cap centre; pins end 3.81 above and below
BOX = (88.9, 143.51, 175.26, 167.64)


def new_uuid():
    return q(str(uuid.uuid4()))


def find_symbol(root, pred):
    for s in children(root, "symbol"):
        if pred(s):
            return s
    raise KeyError


def prop(s, name):
    for p in children(s, "property"):
        if p[1] == name:
            return p
    return None


def move_props(s, dx, dy):
    for p in children(s, "property"):
        at = child(p, "at")
        at[1] = f"{float(at[1]) + dx:.2f}"
        at[2] = f"{float(at[2]) + dy:.2f}"


def set_instance_ref(s, ref):
    path = child(child(child(s, "instances"), "project"), "path")
    path[1] = q(SHEET_PATH)
    child(path, "reference")[1] = q(ref)


# ---------------------------------------------------------------- 1. xvf3800 sheet
root = parse(open(XVF).read())
if any(prop(s, "Reference") and prop(s, "Reference")[2] == "C323" for s in children(root, "symbol")):
    sys.exit("C323 already on the sheet: nothing to do")
c304 = find_symbol(root, lambda s: prop(s, "Reference") and prop(s, "Reference")[2] == "C304")
power = {}
for s in children(root, "symbol"):
    lid = str(child(s, "lib_id")[1])
    if lid in ("Mindspark:+0V9", "Mindspark:+1V8", "Mindspark:GND") and child(s, "at")[3] == "0":
        power.setdefault(lid.split(":")[1], s)
pwr_n = max(int(str(p[2])[4:]) for s in children(root, "symbol") for p in children(s, "property")
            if p[1] == "Reference" and str(p[2]).startswith("#PWR"))

new = []
for ref, x, top, bottom, use in CAPS:
    c = copy.deepcopy(c304)
    at = child(c, "at")
    dx, dy = x - float(at[1]), CY - float(at[2])
    at[1], at[2] = f"{x:.2f}", f"{CY:.2f}"
    move_props(c, dx, dy)
    # fixed UUID per reference, so the board footprint's link survives a rerun of this script
    child(c, "uuid")[1] = q(str(uuid.uuid5(uuid.NAMESPACE_URL, f"mindspark_rev1/xvf3800/{ref}")))
    prop(c, "Reference")[2] = q(ref)
    prop(c, "use")[2] = q(use)
    # reference, value and voltage to the right of the cap, so they stay inside the box
    for name, dy_ in (("Reference", -1.27), ("Value", 1.27), ("voltage", 3.3)):
        pr = prop(c, name)
        a = child(pr, "at")
        a[1], a[2], a[3] = f"{x + 2.54:.2f}", f"{CY + dy_:.2f}", "0"
        eff = child(pr, "effects")
        if not child(eff, "justify"):
            eff.append(["justify", "left"])
    for pn in children(c, "pin"):
        child(pn, "uuid")[1] = new_uuid()
    set_instance_ref(c, ref)
    new.append(c)
    # top pin: supply arrow pointing up; bottom pin: GND as drawn, a supply arrow turned to point down
    for net, y, rot in ((top, CY - 3.81, "0"), (bottom, CY + 3.81, "0" if bottom == "GND" else "180")):
        s = copy.deepcopy(power[net])
        at = child(s, "at")
        dx, dy = x - float(at[1]), y - float(at[2])
        at[1], at[2], at[3] = f"{x:.2f}", f"{y:.2f}", rot
        move_props(s, dx, dy)
        if rot == "180":                       # value text below the flipped arrow
            v = child(prop(s, "Value"), "at")
            v[2] = f"{y + 3.5:.2f}"
        child(s, "uuid")[1] = new_uuid()
        for pn in children(s, "pin"):
            child(pn, "uuid")[1] = new_uuid()
        pwr_n += 1
        prop(s, "Reference")[2] = q(f"#PWR{pwr_n}")
        set_instance_ref(s, f"#PWR{pwr_n}")
        new.append(s)

new.append(["rectangle", ["start", str(BOX[0]), str(BOX[1])], ["end", str(BOX[2]), str(BOX[3])],
            ["stroke", ["width", "0.1524"], ["type", "default"]], ["fill", ["type", "none"]], ["uuid", new_uuid()]])
new.append(["text", q("USB stitching caps (main USB pair)"), ["exclude_from_sim", "no"],
            ["at", f"{BOX[0] + 1.27:.2f}", f"{BOX[1] + 1.27:.2f}", "0"],
            ["effects", ["font", ["size", "1.524", "1.524"]], ["justify", "left", "top"]], ["uuid", new_uuid()]])
new.append(["text", q("The XVF3800's USB pair leaves\n"
                      "on the bottom layer, over In2.\n"
                      "C323/C324: +0V9 to +1V8 either\n"
                      "side of the pair where it\n"
                      "leaves the +0V9 island.\n"
                      "C325/C326: +1V8 to GND either\n"
                      "side of the vias where it goes\n"
                      "up to the top layer (In1 GND)."),
            ["exclude_from_sim", "no"], ["at", "146.05", "148.59", "0"],
            ["effects", ["font", ["size", "1", "1"]], ["justify", "left", "top"]], ["uuid", new_uuid()]])
# insert before sheet_instances / embedded_fonts if present, else at the end
idx = next((i for i, n in enumerate(root) if isinstance(n, list) and n and n[0] in ("sheet_instances", "embedded_fonts")),
           len(root))
root[idx:idx] = new
open(XVF, "w").write(dump(root) + "\n")
print("xvf3800: added", ", ".join(c[0] for c in CAPS), f"and {2 * len(CAPS)} power symbols")

# ---------------------------------------------------------------- 2. usb_power sheet: swap U101 channels
root = parse(open(USB).read())
swapped = 0
for n in children(root, "hierarchical_label"):
    at = (float(child(n, "at")[1]), float(child(n, "at")[2]))
    if at == (91.44, 35.56) and n[1] == "USB_MAIN_DM":          # U101 pin 2
        n[1] = q("USB_MAIN_DP")
        swapped += 1
    elif at == (124.46, 30.48) and n[1] == "USB_MAIN_DP":       # U101 pin 4
        n[1] = q("USB_MAIN_DM")
        swapped += 1
if swapped != 2:
    sys.exit(f"expected 2 U101 labels, found {swapped}; usb_power not written")

# ---------------------------------------------------------------- 3. usb_power sheet: U101 flow-through pins
# The pair runs straight across U101: each data line enters over one of the spare pins (7, 9)
# and continues over the protected pin opposite it (4, 2), as in TI's flow-through layout. So
# pin 9 joins pin 2 and pin 7 joins pin 4 (they were no-connects); pins 6 and 10 stay NC.
JOIN = [((95.25, 40.64), (95.25, 35.56)),      # pin 9 -> pin 2 (left side, U101 at 107.95, 33.02)
        ((120.65, 25.4), (120.65, 30.48))]     # pin 7 -> pin 4 (right side)
removed = 0
for n in list(children(root, "no_connect")):
    at = (float(child(n, "at")[1]), float(child(n, "at")[2]))
    if at in [a for a, _ in JOIN]:
        root.remove(n)
        removed += 1
if removed != 2:
    sys.exit(f"expected 2 no-connect flags on U101 pins 7/9, found {removed}; usb_power not written")
idx = next((i for i, n in enumerate(root) if isinstance(n, list) and n and n[0] in ("sheet_instances", "embedded_fonts")),
           len(root))
for a, b in JOIN:
    root.insert(idx, ["wire", ["pts", ["xy", str(a[0]), str(a[1])], ["xy", str(b[0]), str(b[1])]],
                      ["stroke", ["width", "0"], ["type", "default"]], ["uuid", new_uuid()]])
    root.insert(idx, ["junction", ["at", str(b[0]), str(b[1])], ["diameter", "0"], ["color", "0", "0", "0", "0"],
                      ["uuid", new_uuid()]])
open(USB, "w").write(dump(root) + "\n")
print("usb_power: U101 pin 2 -> USB_MAIN_DP, pin 4 -> USB_MAIN_DM; pin 9 joined to pin 2, pin 7 to pin 4")
