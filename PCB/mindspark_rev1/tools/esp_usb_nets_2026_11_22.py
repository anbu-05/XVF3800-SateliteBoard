"""Board side of tools/sch_esp_usb_2026_11_22.py (2026-11-22): U102's NC pads 9 and 7 take the
ESP32 USB nets, so the pair can run straight through the ESD array (pin 2 -> 9 D-, 4 -> 7 D+).
Same change as U101's in tools/usb_main_place_2026_11_19.py. Run before power_v2.

Usage (PCB editor closed):  python3 tools/esp_usb_nets_2026_11_22.py
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from place_tidy import BOARD, Part  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

U102_NETS = {"9": "/USB_ESP_DM", "7": "/USB_ESP_DP"}

root = parse(open(BOARD).read())
u102 = next(p for p in (Part(f) for f in children(root, "footprint")) if p.ref == "U102")
done = 0
for pd in children(u102.node, "pad"):
    if str(pd[1]) in U102_NETS:
        child(pd, "net")[1] = q(U102_NETS[str(pd[1])])
        # the pin is wired now: drop the no-connect pin type, as on U101
        child(pd, "pintype")[1] = q("passive")
        done += 1
if done != 2:
    sys.exit(f"expected 2 pads, changed {done}")
open(BOARD, "w").write(dump(root) + "\n")
print("U102 pads 9/7 ->", U102_NETS)
