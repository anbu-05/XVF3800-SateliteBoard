"""Group 2 of the remaining-net order (2026-11-22): XVF3800 escape, part 1.

Laid by tools/power_v2_2026_11_18.py right after the group 1 local hookups (before the vias in
pads), so the power pass and later routes go round it. All on the bottom layer, where the
XVF3800 sits. Winged (user 2026-11-22): no drawing; results shown after the build.

Power fan-out
  * +0V9 pins next to a paddle get a straight stub into it (pins 4/12 -> paddle 61, 34/42 -> 63,
    49/57 -> 64). Paddle 63 has no vias (it sits under the ESP32's GND pads), so it reaches the
    In2 +0V9 island through pin 34 -> C305's in-pad via.
  * West caps: C308 (+0V9) -> pin 57, C307 (+0V9) -> pin 49 and C312 (+3V3) -> pin 52, each
    straight across at its pin's height, between the mic lines that leave the west side.
  * South caps: pin 34 -> C305, pin 38 -> C311, pin 31 -> C317 (C305/C317 nudged east by
    tools/xvf_cap_nudge_2026_11_22.py). C306 (+0V9, pin 42) cannot be reached by a trace: pin 42
    sits between the MIC_CLK and MCLK vias. It takes a via in its pad into a small lobe of the
    +0V9 island instead (power_v2 ZONES).
  * Pin 30 (+3V3, east side) -> C313, just below the USB pair; C313/C314 sit over the In2
    +1V8 band, so C314 takes a strap south to a +3V3 via just below the module.
  * C302's GND pad: a top-layer PRG line runs over it, so its via sits just north of the pad.

South signal lanes (0.15 mm at 0.3 mm pitch, straight down through the cap row's gaps).
  Jogs leave the pins below the pad ends (0.15 mm to the next pad). Where two neighbours jog
  the same way, the second starts 0.125 mm lower: parallel 45 deg runs at 0.3 mm horizontal
  pitch would be only 0.21 mm apart.
  pins 45/44 west of C306; 40/39 between C306 and C311; 37/36/35 between C311 and C305;
  33/32 between C305 and C317. They end just south of the ESP32 module (y 108.9) for the
  group 3 / 5 routes to pick up.
"""

W_SIG, W_PWR = 0.15, 0.2
LANE_END = 108.9

TRACKS = [  # net, width, points (all B.Cu)
    # ---- +0V9 pins into the paddles
    ("+0V9", W_PWR, [(144.958, 95.179), (144.958, 96.179)]),        # pin 4 -> paddle 61
    ("+0V9", W_PWR, [(148.158, 95.179), (148.158, 96.179)]),        # pin 12 -> paddle 61
    ("+0V9", W_PWR, [(148.158, 102.179), (148.158, 101.179)]),      # pin 34 -> paddle 63
    ("+0V9", W_PWR, [(144.958, 102.179), (144.958, 101.179)]),      # pin 42 -> paddle 63
    ("+0V9", W_PWR, [(143.058, 100.279), (144.058, 100.279)]),      # pin 49 -> paddle 64
    ("+0V9", W_PWR, [(143.058, 97.079), (144.058, 97.079)]),        # pin 57 -> paddle 64
    # ---- west caps
    # (C308 -> pin 57: no trace; C308 takes a via in its pad into the west lobe of the +0V9
    #  island, which frees the space north of the west signal box for the GPO vias)
    ("+0V9", W_PWR, [(140.578, 100.479), (140.778, 100.279), (143.058, 100.279)]),   # C307 -> pin 49
    ("+3V3", W_PWR, [(143.058, 99.079), (140.778, 99.079), (140.578, 98.879)]),      # pin 52 -> C312
    # ---- south caps
    ("+0V9", W_PWR, [(148.158, 102.179), (148.158, 103.9), (148.308, 104.05), (148.308, 104.659)]),  # pin 34 -> C305
    ("+3V3", W_PWR, [(146.558, 102.179), (146.558, 104.659)]),                                      # pin 38 -> C311
    ("+1V8", W_PWR, [(149.358, 102.179), (149.358, 102.58), (149.858, 103.08), (149.858, 104.659)]),  # pin 31 -> C317
    # (pin 30 -> C313 -> C314 is laid by tools/east_column_2026_11_22.py)
    # ---- pin 30 / C313 / C314 (+3V3) sit over the +1V8 band: a strap from C314 south, under
    #      the ESP32's south pins, to a +3V3 via just below the module
    # (user 2026-11-22: jogs east past XVF_INT_N's lane, was straight down x 151.0)
    ("+3V3", 0.3, [(152.48, 103.01), (151.976, 103.01), (151.638, 103.348), (151.638, 105.5565),
                   (151.183, 106.0115), (151.183, 108.817), (151.0, 109.0)]),
    # ---- C302 GND: a PRG line on the top layer runs over the pad, so its via sits just north,
    #      between the I2S LRCK and BCLK lines
    ("GND", 0.25, [(148.01, 91.72), (148.01, 91.49), (147.92, 91.4)]),
    # ---- west signals: GPO_G and GPO_R step up to vias (top layer onward); INT_N, SQ_NLIN and
    #      I2S_DATA2 close to 0.3 mm pitch and leave west between C308 and C312, out past the
    #      module's west end, on the bottom layer
    ("/XVF_GPO_G", W_SIG, [(143.058, 96.679), (141.571, 96.679), (141.4, 96.85)]),        # pin 58
    ("/XVF_GPO_R", W_SIG, [(143.058, 97.479), (142.429, 97.479), (142.2, 97.25)]),        # pin 56
    ("/XVF_INT_N", W_SIG, [(143.058, 97.879), (141.8, 97.879), (141.55, 97.629), (136.2, 97.629)]),       # 55
    ("/XVF_SQ_NLIN", W_SIG, [(143.058, 98.279), (141.6, 98.279), (141.25, 97.929), (136.2, 97.929)]),     # 54
    ("/XVF_I2S_DATA2", W_SIG, [(143.058, 98.679), (141.4, 98.679), (140.95, 98.229), (136.2, 98.229)]),   # 53
    # ---- north: SPI_CS_N (pin 6) and SPI_MOSI (pin 7) to vias north of the pins, between the
    #      QSPI_CLK via, pin 4's feed (moved 0.1 mm west) and C310's via (user's hand edit 2026-11-22)
    ("/XVF_SPI_CS_N", W_SIG, [(145.758, 95.179), (145.758, 94.618), (145.86, 94.516), (145.86, 94.115),
                              (145.42, 93.675), (145.308, 93.675)]),
    ("/XVF_SPI_MOSI", W_SIG, [(146.158, 94.779), (146.158, 94.654), (146.258, 94.554), (146.258, 94.047),
                              (145.81, 93.599), (145.81, 93.28)]),
    # ---- south signal lanes
    ("/XVF_I2C_SDA", W_SIG, [(143.758, 102.179), (143.758, LANE_END)]),                               # pin 45
    ("/XVF_I2C_SCL", W_SIG, [(144.158, 102.179), (144.158, 102.68), (144.058, 102.78), (144.058, LANE_END)]),  # 44
    ("/AMP_EN", W_SIG, [(145.758, 102.179), (145.758, 102.68), (145.858, 102.78), (145.858, 103.5),
                        (145.575, 103.783), (145.575, LANE_END)]),                                   # pin 40
    ("/XVF_I2S_DATA1", W_SIG, [(146.158, 102.179), (146.158, 103.625), (145.875, 103.908), (145.875, LANE_END)]),  # 39
    ("/XL_UP1", W_SIG, [(146.958, 102.179), (146.958, 103.0), (147.158, 103.2), (147.158, LANE_END)]),  # pin 37
    ("/XL_UP0", W_SIG, [(147.358, 102.179), (147.358, 102.7), (147.458, 102.8), (147.458, LANE_END)]),  # pin 36
    ("/XL_DN0", W_SIG, [(147.758, 102.179), (147.758, LANE_END)]),                                    # pin 35
    ("/XL_DN1", W_SIG, [(148.558, 102.179), (148.558, 102.9), (148.858, 103.2), (148.858, LANE_END)]),  # pin 33
    ("/BTN_ACTION_N", W_SIG, [(148.958, 102.179), (148.958, 102.7), (149.158, 102.9), (149.158, LANE_END)]),  # 32
]
VIAS = [          # (point, net, (size, drill))
    ((151.0, 109.0), "+3V3", (0.45, 0.2)),
    ((147.92, 91.4), "GND", (0.45, 0.2)),
    ((141.4, 96.85), "/XVF_GPO_G", (0.45, 0.2)),
    ((142.2, 97.25), "/XVF_GPO_R", (0.45, 0.2)),
    ((145.308, 93.675), "/XVF_SPI_CS_N", (0.45, 0.2)),
    ((145.81, 93.28), "/XVF_SPI_MOSI", (0.45, 0.2)),
]
# pads the pieces above join, so later routes may start from them
JOINED = [("U301", p) for p in ("4", "12", "34", "42", "49", "57", "52", "38", "31", "30")] + \
         [("C307", "1"), ("C312", "1"), ("C305", "1"), ("C311", "1"), ("C317", "1"), ("C313", "1"),
          ("C314", "1"), ("C302", "2")]

ESCAPE = [  # net, (ref, pin), search box (x0, y0, x1, y1) for the via; routed in this order
    ("/XVF_SPI_MISO", ("U301", "47"), (138.0, 100.5, 143.0, 104.5)),
]
