"""Schematic change for the mic routes (agreed with the user 2026-11-20).

The SE mic pair (MK504: DATA3 + clock) runs south on B.Cu over the In2 +3V3 plane and crosses
onto the In2 +5V plane near y 120 before it turns east. A stitching cap across the two planes,
right beside the crossing, gives the return current a path from one plane to the other.

audio sheet: a new box "Mic stitching cap" below the mic-supply box, with one 100 nF 0402 cap
(C515, same part as C501: C1525), +3V3 on pin 1 (top), +5V on pin 2 (bottom), a power symbol
on each pin as the other caps on this sheet have. The symbols are copies of C501 and of the
sheet's own +3V3 / +5V symbols, with new UUIDs and references.

Usage (schematic and PCB editors closed):  python3 tools/sch_mic_stitch_2026_11_20.py
"""
import copy
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from sexpr import parse, dump, children, child, q  # noqa: E402

HERE = __import__("os").path.dirname(__file__) + "/.."
AUDIO = HERE + "/audio.kicad_sch"
SHEET_PATH = "/af1cbb83-54b2-47b9-8bc4-08bc42da7d01/3f22dfb6-6fd6-54c4-9781-a982d7ddf190"   # audio sheet

REF, USE = "C515", "Mic stitching: +3V3/+5V where the SE mic pair crosses planes (In2)"
CX, CY = 215.9, 135.89            # cap centre; pins end 3.81 above and below
BOX = (202.07, 113.05, 269.5, 158.32)


def new_uuid():
    return q(str(uuid.uuid4()))


def prop(s, name):
    for p in children(s, "property"):
        if p[1] == name:
            return p
    return None


def ref_of(s):
    p = prop(s, "Reference")
    return str(p[2]).strip('"') if p else ""


def move_props(s, dx, dy):
    for p in children(s, "property"):
        at = child(p, "at")
        at[1] = f"{float(at[1]) + dx:.2f}"
        at[2] = f"{float(at[2]) + dy:.2f}"


def set_instance_ref(s, ref):
    path = child(child(child(s, "instances"), "project"), "path")
    path[1] = q(SHEET_PATH)
    child(path, "reference")[1] = q(ref)


root = parse(open(AUDIO).read())
if any(ref_of(s) == REF for s in children(root, "symbol")):
    sys.exit(f"{REF} already on the sheet: nothing to do")
c501 = next(s for s in children(root, "symbol") if ref_of(s) == "C501")
assert child(c501, "at")[3] == "0", "template cap must stand upright"
power = {}
for s in children(root, "symbol"):
    lid = str(child(s, "lib_id")[1])
    if lid in ("Mindspark:+3V3", "Mindspark:+5V") and child(s, "at")[3] == "0":
        power.setdefault(lid.split(":")[1], s)
pwr_n = max(int(str(p[2]).strip('"')[4:]) for s in children(root, "symbol") for p in children(s, "property")
            if p[1] == "Reference" and str(p[2]).strip('"').startswith("#PWR"))

new = []
c = copy.deepcopy(c501)
at = child(c, "at")
dx, dy = CX - float(at[1]), CY - float(at[2])
at[1], at[2] = f"{CX:.2f}", f"{CY:.2f}"
move_props(c, dx, dy)
# fixed UUID, so the board footprint's link survives a rerun
child(c, "uuid")[1] = q(str(uuid.uuid5(uuid.NAMESPACE_URL, f"mindspark_rev1/audio/{REF}")))
prop(c, "Reference")[2] = q(REF)
prop(c, "use")[2] = q(USE)
for name, dy_ in (("Reference", -1.27), ("Value", 1.27), ("voltage", 3.3)):
    pr = prop(c, name)
    if pr is None:
        continue
    a = child(pr, "at")
    a[1], a[2], a[3] = f"{CX + 2.54:.2f}", f"{CY + dy_:.2f}", "0"
    eff = child(pr, "effects")
    if not child(eff, "justify"):
        eff.append(["justify", "left"])
for pn in children(c, "pin"):
    child(pn, "uuid")[1] = new_uuid()
set_instance_ref(c, REF)
new.append(c)
# top pin: +3V3 arrow up; bottom pin: +5V arrow turned to point down
for net, y, rot in (("+3V3", CY - 3.81, "0"), ("+5V", CY + 3.81, "180")):
    s = copy.deepcopy(power[net])
    at = child(s, "at")
    dx, dy = CX - float(at[1]), y - float(at[2])
    at[1], at[2], at[3] = f"{CX:.2f}", f"{y:.2f}", rot
    move_props(s, dx, dy)
    if rot == "180":                       # value text below the flipped arrow
        v = child(prop(s, "Value"), "at")
        v[2] = f"{y + 3.5:.2f}"
    child(s, "uuid")[1] = new_uuid()
    for pn in children(s, "pin"):
        child(pn, "uuid")[1] = new_uuid()
    pwr_n += 1
    prop(s, "Reference")[2] = q(f"#PWR{pwr_n:02d}")
    set_instance_ref(s, f"#PWR{pwr_n:02d}")
    new.append(s)

new.append(["rectangle", ["start", f"{BOX[0]}", f"{BOX[1]}"], ["end", f"{BOX[2]}", f"{BOX[3]}"],
            ["stroke", ["width", "0.1524"], ["type", "default"]], ["fill", ["type", "none"]], ["uuid", new_uuid()]])
new.append(["text", q("Mic stitching cap"), ["exclude_from_sim", "no"],
            ["at", f"{BOX[0] + 1.27:.2f}", f"{BOX[1] + 1.27:.2f}", "0"],
            ["effects", ["font", ["size", "1.524", "1.524"]], ["justify", "left", "top"]], ["uuid", new_uuid()]])
new.append(["text", q("The SE mic pair (MK504) runs on\n"
                      "the bottom layer over In2 and\n"
                      "crosses from the +3V3 plane to\n"
                      "the +5V plane. C515 joins the\n"
                      "two planes beside the crossing."),
            ["exclude_from_sim", "no"], ["at", "233.68", "127.0", "0"],
            ["effects", ["font", ["size", "1", "1"]], ["justify", "left", "top"]], ["uuid", new_uuid()]])
idx = next((i for i, n in enumerate(root) if isinstance(n, list) and n and n[0] in ("sheet_instances", "embedded_fonts")),
           len(root))
root[idx:idx] = new
open(AUDIO, "w").write(dump(root) + "\n")
print(f"audio: added {REF} and 2 power symbols")
