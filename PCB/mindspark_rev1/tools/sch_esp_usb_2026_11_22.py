"""Schematic change for the ESP32 USB pair route (agreed with the user 2026-11-22).

usb_power sheet, U102 (TPD4E05U06 ESD array on the ESP32 USB-C): the pair runs straight through
the chip, in on the connector-side pins and out over the NC pins opposite them (TI datasheet p.4:
NC pins are "used for optional straight-through routing"). So the NC pins must carry the nets:
  pin 9 (opposite pin 2, D-) joins USB_ESP_DM
  pin 7 (opposite pin 4, D+) joins USB_ESP_DP
Done exactly as U101 already is: a short vertical wire from the NC pin to the signal pin, a
junction on the signal pin, and the no-connect flag on the NC pin removed.

Usage (schematic and PCB editors closed):  python3 tools/sch_esp_usb_2026_11_22.py
"""
import copy
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__file__))
from sexpr import parse, dump, children, child, q  # noqa: E402

USB = __import__("os").path.dirname(__file__) + "/../usb_power.kicad_sch"

# U102 sits at (241.3, 33.02); pin ends on the sheet (from the symbol's pin table):
#   pin 2 D1- (228.6, 35.56)  pin 9 NC (228.6, 40.64)
#   pin 4 D2+ (254.0, 30.48)  pin 7 NC (254.0, 25.4)
LINKS = [  # (NC pin end, signal pin end)
    ((228.6, 40.64), (228.6, 35.56)),   # pin 9 -> pin 2, USB_ESP_DM
    ((254.0, 25.4), (254.0, 30.48)),    # pin 7 -> pin 4, USB_ESP_DP
]


def fmt(v):
    # KiCad writes coordinates without trailing zeros (254 not 254.0)
    return f"{v:g}"


root = parse(open(USB).read())

# Templates: any existing wire and junction on the sheet (same stroke/diameter style)
wire_t = children(root, "wire")[0]
junc_t = children(root, "junction")[0]


def at_of(node):
    a = child(node, "at")
    return float(a[1]), float(a[2])


ncs = {at_of(n): n for n in children(root, "no_connect")}
for nc_end, sig_end in LINKS:
    if nc_end not in ncs:
        sys.exit(f"no no-connect flag at {nc_end}: already done?")

for nc_end, sig_end in LINKS:
    # 1. drop the no-connect flag on the NC pin
    root.remove(ncs[nc_end])
    # 2. wire NC pin -> signal pin
    w = copy.deepcopy(wire_t)
    pts = child(w, "pts")
    pts[1:] = [["xy", fmt(nc_end[0]), fmt(nc_end[1])], ["xy", fmt(sig_end[0]), fmt(sig_end[1])]]
    child(w, "uuid")[1] = q(str(uuid.uuid4()))
    # 3. junction on the signal pin (the label wire and the new wire meet there)
    j = copy.deepcopy(junc_t)
    a = child(j, "at")
    a[1], a[2] = fmt(sig_end[0]), fmt(sig_end[1])
    child(j, "uuid")[1] = q(str(uuid.uuid4()))
    # insert next to the templates so the file keeps KiCad's grouping
    root.insert(root.index(wire_t), w)
    root.insert(root.index(junc_t), j)

open(USB, "w").write(dump(root) + "\n")
print("U102 pins 9/7 joined to USB_ESP_DM/DP")
