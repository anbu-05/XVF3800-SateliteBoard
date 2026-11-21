"""Schematic changes for the programming-switch move (agreed with the user 2026-11-22).

1. esp32_io sheet: four 0 ohm 0402 links (R706-R709, C17168, same part as R703) in series between
   each flash switch's COM pin (pin 2, XVF side) and its XVF_QSPI_* hierarchical label:
     R706  U701  XVF_QSPI_CS_N        R707  U702  XVF_QSPI_CLK
     R708  U703  XVF_QSPI_D0          R709  U704  XVF_QSPI_D1
   Removing a link cuts the switch (and its 18-19 pF off-capacitance) off the XVF3800's flash line.
   Each link stands upright just left of its switch: bottom pin on the old COM wire, top pin to the
   moved label. Top row (U701/U702): the label goes left of the link. Bottom row (U703/U704): the
   PRG_EN bus runs down the left side there, so the label points up from the link instead.
2. xvf3800 sheet: C323 and C324 (+0V9/+1V8 USB stitching caps) and their power symbols removed;
   In2 +1V8 now runs under the XVF3800's east pins, so the USB pair stays over one plane. C325 and
   C326 (+1V8/GND by the layer-change vias) move left into the freed spots; the note is updated.

Usage (schematic and PCB editors closed):  python3 tools/sch_prog_switch_2026_11_22.py
"""
import copy
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, dump, children, child, q  # noqa: E402

HERE = os.path.join(os.path.dirname(__file__), "..")
IO = os.path.join(HERE, "esp32_io.kicad_sch")
XVF = os.path.join(HERE, "xvf3800.kicad_sch")

LINKS = [  # ref, switch, label net, top row?
    ("R706", "U701", "XVF_QSPI_CS_N", True),
    ("R707", "U702", "XVF_QSPI_CLK", True),
    ("R708", "U703", "XVF_QSPI_D0", False),
    ("R709", "U704", "XVF_QSPI_D1", False),
]
USE = "Link: remove to cut {sw} off the XVF flash line (drops its off-capacitance)"


def new_uuid():
    return q(str(uuid.uuid4()))


def ref_of(sym):
    for p in children(sym, "property"):
        if str(p[1]) == "Reference":
            return str(p[2])
    return None


def set_xy(node, x, y):
    at = child(node, "at")
    at[1], at[2] = f"{x:g}", f"{y:g}"


def wire(a, b):
    return ["wire", ["pts", ["xy", f"{a[0]:g}", f"{a[1]:g}"], ["xy", f"{b[0]:g}", f"{b[1]:g}"]],
            ["stroke", ["width", "0"], ["type", "default"]], ["uuid", new_uuid()]]


# ---------------------------------------------------------------- esp32_io: the four links
io = parse(open(IO).read())
syms = {ref_of(s): s for s in children(io, "symbol")}
template = syms["R703"]                                     # 0R 0402, C17168
for ref, sw, net, top in LINKS:
    if ref in syms:
        sys.exit(f"{ref} already on the sheet: nothing done")
    at = child(syms[sw], "at")
    sx, sy = float(at[1]), float(at[2])
    row = round(sy - 2.54, 2)                               # COM pin row (pin 2 at -8.89, +2.54)
    pin_x = round(sx - 8.89, 2)
    old_lx = round(sx - 11.43, 2)                           # where the label sits now
    rx = round(sx - 13.97, 2)                               # link column
    cy = round(row - 3.81, 2)                               # link centre; pins at cy -/+ 3.81
    top_pin = (rx, round(cy - 3.81, 2))
    # the COM wire now ends on the link's bottom pin instead of the label
    found = False
    for w in children(io, "wire"):
        pts = child(w, "pts")
        xy = [(float(p[1]), float(p[2])) for p in pts[1:]]
        if sorted(xy) == sorted([(old_lx, row), (pin_x, row)]):
            for p in pts[1:]:
                if abs(float(p[1]) - old_lx) < 0.01:
                    p[1] = f"{rx:g}"
            found = True
    if not found:
        sys.exit(f"{sw}: COM wire not found")
    # move the label
    lab = [h for h in children(io, "hierarchical_label")
           if str(h[1]) == net and abs(float(child(h, "at")[1]) - old_lx) < 0.01
           and abs(float(child(h, "at")[2]) - row) < 0.01]
    if len(lab) != 1:
        sys.exit(f"{net}: label not found at the switch")
    lab = lab[0]
    if top:
        lpos = (round(rx - 7.62, 2), top_pin[1])
        io.append(wire(top_pin, lpos))
        child(lab, "at")[1:] = [f"{lpos[0]:g}", f"{lpos[1]:g}", "180"]
    else:
        lpos = (rx, round(top_pin[1] - 2.54, 2))
        io.append(wire(top_pin, lpos))
        child(lab, "at")[1:] = [f"{lpos[0]:g}", f"{lpos[1]:g}", "90"]
        eff = child(lab, "effects")
        j = child(eff, "justify")
        if j:
            j[1:] = ["left"]
        else:
            eff.append(["justify", "left"])
    # the link itself: a copy of R703, upright
    s = copy.deepcopy(template)
    child(s, "at")[1:] = [f"{rx:g}", f"{cy:g}", "0"]
    child(s, "uuid")[1] = new_uuid()
    for p in children(s, "property"):
        name = str(p[1])
        if name == "Reference":
            p[2] = q(ref)
            child(p, "at")[1:] = [f"{rx + 2.34:g}", f"{cy - 0.75:g}", "0"]
        elif name == "Value":
            child(p, "at")[1:] = [f"{rx + 2.34:g}", f"{cy + 0.75:g}", "0"]
        elif name == "use":
            p[2] = q(USE.format(sw=sw))
            child(p, "at")[1:] = [f"{rx:g}", f"{cy:g}", "0"]
        else:
            child(p, "at")[1:] = [f"{rx:g}", f"{cy:g}", "0"]
        if name in ("Reference", "Value"):
            eff = child(p, "effects")
            j = child(eff, "justify")
            if j:
                j[1:] = ["left"]
    for pin in children(s, "pin"):
        child(pin, "uuid")[1] = new_uuid()
    inst = child(child(child(s, "instances"), "project"), "path")
    child(inst, "reference")[1] = q(ref)
    io.append(s)
    print(f"  {ref}: link for {sw} at ({rx}, {cy}), label {net} at {lpos}")
open(IO, "w").write(dump(io) + "\n")
print("wrote", IO)

# ---------------------------------------------------------------- xvf3800: C323/C324 out
xv = parse(open(XVF).read())
drop = {"C323", "C324", "#PWR3039", "#PWR3040", "#PWR3041", "#PWR3042"}
moves = {"C325": -25.4, "#PWR3043": -25.4, "#PWR3044": -25.4,
         "C326": -25.4, "#PWR3045": -25.4, "#PWR3046": -25.4}
kept = []
for n in xv:
    if isinstance(n, list) and n and n[0] == "symbol" and ref_of(n) in drop:
        continue
    if isinstance(n, list) and n and n[0] == "symbol" and ref_of(n) in moves:
        dx = moves[ref_of(n)]
        for node in [n] + children(n, "property"):
            at = child(node, "at")
            at[1] = f"{float(at[1]) + dx:g}"
    kept.append(n)
xv[:] = kept
for t in children(xv, "text"):
    if str(t[1]).startswith("The XVF3800's USB pair leaves"):
        t[1] = q("The XVF3800's USB pair leaves\non the bottom layer, over In2\n+1V8 from the pins (one plane).\n"
                 "C325/C326: +1V8 to GND either\nside of the vias where it goes\nup to the top layer (In1 GND).")
open(XVF, "w").write(dump(xv) + "\n")
print("wrote", XVF, "- removed", sorted(drop))
