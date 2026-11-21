"""Route of the ESP32 USB pair, J102 -> U102 -> R606/R605 -> ESP32 pins 13/14 (agreed 2026-11-22).

Plan image: verification/esp-usb-plan-2026-11-22/. Laid by tools/power_v2_2026_11_18.py before
any power copper, like the other fixed routes, so a rerun keeps it and the power router avoids it.
Run on its own, this file prints each line's length.

Why it looks like this:
  * ESP32-S3 USB is full speed (12 Mbit/s), so impedance and skew hardly matter. We still use the
    main pair's geometry (0.25 mm lines, 0.15 mm gap, ~90 ohm) because it costs nothing.
  * Top layer all the way (user 2026-11-22): over In1 GND the whole length, no layer changes.
  * J102's A pins are in the wrong order for U102 (A6 D+ is north, but U102 pin 2 D- is north),
    so the lines start from the B pins (B7 D- north, B6 D+ south) and the A pins join them by two
    short bottom-layer jumpers west of the LED ring. That is J101's jumper layout turned 180 deg
    about the board centre (J102 is the J101 group turned 180 deg).
  * U102 (TPD4E05U06) is crossed straight through: in on pins 2/4, out on the NC pins 9/7
    opposite them (TI datasheet p.4: NC pins are for straight-through routing; the schematic ties
    them to the nets since tools/sch_esp_usb_2026_11_22.py). U102's GND pins 3/8 sit between the
    lines; they get one small GND via just east of pin 8, between the lines while they are still
    1 mm apart (power_v2 lays it, as for U101).
  * The pair closes to 0.4 mm pitch to pass between D102's pads (VBUS TVS), turns south just east
    of it (west of PRG_EN's line at x 123.3), runs south to below the ESP32 module, then east:
    south of C601 (3V3 bulk cap), one 45 deg jog up past C602, north of C207/L202 and C309's
    vias, into R606 (D-) / R605 (D+) from below. D- runs straight into R606; D+ dips under R606
    and comes up into R605.
  * ESP32 pins 13 (D-) / 14 (D+) drop straight down to the other ends of R606 / R605.
  * The +5V trunk crosses the pair on the bottom layer (power_v2, HOP_5V_*), at x 127.6 where
    the bottom layer has no mic lines.
"""
import math

W, VIA = 0.25, (0.45, 0.2)
DM, DP = "/USB_ESP_DM", "/USB_ESP_DP"
EDM, EDP = "/esp32/ESP_USB_DM", "/esp32/ESP_USB_DP"     # ESP32 side of the 27 ohm resistors

# pad centres
J_B7, J_A7 = (116.618, 97.929), (116.618, 98.929)        # J102 D- pins
J_A6, J_B6 = (116.618, 98.429), (116.618, 99.429)        # J102 D+ pins
U2, U9 = (118.518, 98.18), (119.288, 98.18)              # D- across U102 (pin 2 -> NC pin 9)
U4, U7 = (118.518, 99.18), (119.288, 99.18)              # D+ across U102 (pin 4 -> NC pin 7)
R606_1, R606_2 = (153.39, 109.05), (153.39, 110.07)      # D- 27 ohm (pad 1 ESP side)
R605_1, R605_2 = (154.66, 109.05), (154.66, 110.07)      # D+ 27 ohm
PIN13, PIN14 = (153.39, 107.43), (154.66, 107.43)        # ESP32 USB pins

# J102 jumper vias: J101's (177.6 / 178.3) turned 180 deg about the board centre (146.558, 98.679)
JV_A6, JV_B6 = (115.516, 98.429), (115.516, 99.429)      # D+ column
JV_A7, JV_B7 = (114.816, 98.929), (114.816, 97.929)      # D- column

# U102's GND via, between the lines just east of pin 8 (0.15 mm to each line and to pins 9/7)
U102_GND_VIA = (119.75, 98.68)
U102_GND = [(118.518, 98.68), (119.288, 98.68), U102_GND_VIA]   # pin 3 -> pin 8 -> via

# Lanes (line centres). West run: D- east of D+ (x 122.6 / 122.2). South run: D- north (110.65),
# D+ south (111.05) until past C601, then 110.07 / 110.47 (D- level with R606's pad).
TRACKS = [  # net, layer, points
    # J102 B pins -> U102 pins 2/4 (one 45 deg jog each, clear of the A pins' ends)
    (DM, "F.Cu", [J_B7, (117.4, 97.929), (117.651, 98.18), U2]),
    (DP, "F.Cu", [J_B6, (117.4, 99.429), (117.651, 99.18), U4]),
    # across U102 (flow-through) and out east
    (DM, "F.Cu", [U2, U9, (120.0, 98.18), (120.3, 98.48),                 # close to 0.4 pitch
                  (122.2, 98.48), (122.6, 98.88),                         # turn south (outer)
                  (122.6, 110.484), (122.766, 110.65),                    # turn east (inner)
                  (139.0, 110.65), (139.58, 110.07),                      # jog up past C601
                  R606_2]),
    (DP, "F.Cu", [U4, U7, (120.0, 99.18), (120.3, 98.88),
                  (122.034, 98.88), (122.2, 99.046),                      # turn south (inner)
                  (122.2, 110.65), (122.6, 111.05),                       # turn east (outer)
                  (139.166, 111.05), (139.746, 110.47),                   # jog up, parallel to D-
                  (152.6, 110.47), (152.88, 110.75),                      # dip under R606's pad
                  (154.34, 110.75), (154.66, 110.43), R605_2]),
    # ESP32 pins -> resistors
    (EDM, "F.Cu", [PIN13, R606_1]),
    (EDP, "F.Cu", [PIN14, R605_1]),
    # J102 jumpers: F.Cu stubs from the pad centres west to the vias, B.Cu links
    (DP, "F.Cu", [J_A6, JV_A6]), (DP, "F.Cu", [J_B6, JV_B6]), (DP, "B.Cu", [JV_A6, JV_B6]),
    (DM, "F.Cu", [J_A7, JV_A7]), (DM, "F.Cu", [J_B7, JV_B7]), (DM, "B.Cu", [JV_A7, JV_B7]),
]
VIAS = [(JV_A6, DP), (JV_B6, DP), (JV_A7, DM), (JV_B7, DM)]


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def main_lengths():
    """J102 B pin -> ESP32 pin, through U102 and the resistor (resistor body not counted)."""
    out = {}
    for net, enet in ((DM, EDM), (DP, EDP)):
        out[net] = sum(length(p) for n, _, p in TRACKS[:6] if n in (net, enet))
    return out


if __name__ == "__main__":
    L = main_lengths()
    for net, v in L.items():
        print(f"{net}: {v:.2f} mm J102 -> ESP32 pin")
    print(f"mismatch {abs(L[DM] - L[DP]):.2f} mm")
