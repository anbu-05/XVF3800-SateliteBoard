"""Group 1 of the remaining-net order (2026-11-22): local hookups.

Short part-to-neighbour links, 1-5 mm, all on the top layer (every part here sits on F.Cu).
tools/power_v2_2026_11_18.py imports this list and routes it with the jog router right after the
fixed signal routes and before any power copper, so these short links get first pick of the space
next to their pads and the power router goes round them.

The user agreed (2026-11-22) that the low-priority groups are winged: no drawing or detailed plan,
results shown per group. The order below is the priority inside the group.

Each entry: (net, width, clearance, goal, start)
  goal / start: (ref, pin) or (ref, pin, k) where k picks the k-th pad with that number
                (tactile switches have two pads per pin, internally joined).
  start None:   start from anything already laid on that net (the previous entries).
A route that fails at its width retries narrower (x0.7 each time) down to 0.15 mm.
"""

ROUTES = [
    # 1. buck switch nodes: short and wide, the noisiest loops on the board
    ("Net-(U201-SW)", 0.6, 0.2, ("L201", 1), ("U201", 3)),     # 0.9 V buck -> its inductor
    ("Net-(U202-SW)", 0.6, 0.2, ("L202", 1), ("U202", 3)),     # 3.3 V buck -> its inductor

    # 2. buck feedback dividers (high impedance: thin, kept apart from the switch nodes)
    ("Net-(U201-FB)", 0.2, 0.2, ("R201", 2), ("U201", 5)),
    ("Net-(U201-FB)", 0.2, 0.2, ("C201", 2), None),
    ("Net-(U201-FB)", 0.2, 0.2, ("R202", 1), None),
    ("Net-(U202-FB)", 0.2, 0.2, ("R203", 2), ("U202", 5)),
    ("Net-(U202-FB)", 0.2, 0.2, ("C205", 2), None),
    ("Net-(U202-FB)", 0.2, 0.2, ("R204", 1), None),

    # 3. mic last link: the mic routes stop on pad 2 of the series resistors R502-R509
    ("Net-(MK501-CLK)", 0.15, 0.15, ("MK501", 4), ("R502", 1)),
    ("Net-(MK501-DATA)", 0.15, 0.15, ("MK501", 1), ("R506", 1)),
    ("Net-(MK502-CLK)", 0.15, 0.15, ("MK502", 4), ("R503", 1)),
    ("Net-(MK502-DATA)", 0.15, 0.15, ("MK502", 1), ("R507", 1)),
    ("Net-(MK503-CLK)", 0.15, 0.15, ("MK503", 4), ("R504", 1)),
    ("Net-(MK503-DATA)", 0.15, 0.15, ("MK503", 1), ("R508", 1)),
    ("Net-(MK504-CLK)", 0.15, 0.15, ("MK504", 4), ("R505", 1)),
    ("Net-(MK504-DATA)", 0.15, 0.15, ("MK504", 1), ("R509", 1)),

    # 4. mic supply filters: ferrite -> 10 uF -> 1 uF -> mic VDD (pin 5), the small cap last,
    #    next to the mic
    ("+3V3_MIC0", 0.3, 0.15, ("C506", 1), ("FB501", 2)),
    ("+3V3_MIC0", 0.3, 0.15, ("C502", 1), None),
    ("+3V3_MIC0", 0.2, 0.15, ("MK501", 5), None),
    ("+3V3_MIC1", 0.3, 0.15, ("C512", 1), ("FB502", 2)),
    ("+3V3_MIC1", 0.3, 0.15, ("C503", 1), None),
    ("+3V3_MIC1", 0.2, 0.15, ("MK502", 5), None),
    ("+3V3_MIC2", 0.3, 0.15, ("C513", 1), ("FB503", 2)),
    ("+3V3_MIC2", 0.3, 0.15, ("C504", 1), None),
    ("+3V3_MIC2", 0.2, 0.15, ("MK503", 5), None),
    ("+3V3_MIC3", 0.3, 0.15, ("C514", 1), ("FB504", 2)),
    ("+3V3_MIC3", 0.3, 0.15, ("C505", 1), None),
    ("+3V3_MIC3", 0.2, 0.15, ("MK504", 5), None),

    # 5. TPS2121 (U103, power mux) setting parts: OV / priority dividers, ILIM, soft start
    ("Net-(U103-OV1)", 0.2, 0.15, ("R109", 1), ("U103", 5)),
    ("Net-(U103-OV2)", 0.2, 0.15, ("R111", 1), ("U103", 4)),
    ("Net-(U103-PR1)", 0.2, 0.15, ("R105", 1), ("U103", 6)),
    ("Net-(U103-PR1)", 0.2, 0.15, ("R106", 1), None),
    ("Net-(U103-CP2)", 0.2, 0.15, ("R107", 1), ("U103", 3)),
    ("Net-(U103-ILIM)", 0.2, 0.15, ("R113", 1), ("U103", 10)),
    ("Net-(U103-SS)", 0.2, 0.15, ("C105", 1), ("U103", 11)),

    # 6. USB-C CC lines: connector -> ESD array -> 5.1 k pull-down
    ("/usb_power/USBM_CC1", 0.2, 0.15, ("U101", 1), ("J101", "A5")),
    ("/usb_power/USBM_CC1", 0.2, 0.15, ("R101", 1), None),
    ("/usb_power/USBM_CC2", 0.2, 0.15, ("U101", 5), ("J101", "B5")),
    ("/usb_power/USBM_CC2", 0.2, 0.15, ("R102", 1), None),
    ("/usb_power/USBE_CC1", 0.2, 0.15, ("U102", 1), ("J102", "A5")),
    ("/usb_power/USBE_CC1", 0.2, 0.15, ("R103", 1), None),
    ("/usb_power/USBE_CC2", 0.2, 0.15, ("U102", 5), ("J102", "B5")),
    ("/usb_power/USBE_CC2", 0.2, 0.15, ("R104", 1), None),

    # 7. speaker output (peaks ~1.6 A) and the amp / LED switch locals
    ("/audio/SPK_P", 0.5, 0.2, ("J501", 1), ("U503", 9)),
    ("/audio/SPK_P", 0.4, 0.2, ("TP501", 1), None),
    ("/audio/SPK_N", 0.5, 0.2, ("J501", 2), ("U503", 10)),
    ("/audio/SPK_N", 0.4, 0.2, ("TP502", 1), None),
    ("Net-(U503-~{SD_MODE})", 0.2, 0.15, ("R511", 1), ("U503", 4)),
    ("Net-(U502-CT)", 0.2, 0.15, ("C507", 1), ("U502", 4)),
    ("Net-(U801-CT)", 0.2, 0.15, ("C813", 1), ("U801", 4)),

    # 8. buttons and LEDs: switch pad pairs, pull resistors, LED resistors, buffers, FET
    ("Net-(U302-~{MR})", 0.25, 0.15, ("SW301", 1, 1), ("SW301", 1, 0)),
    ("/esp32/ESP_EN", 0.25, 0.15, ("SW601", 1, 1), ("SW601", 1, 0)),
    ("/esp32/ESP_EN", 0.25, 0.15, ("C603", 1), None),
    ("/esp32/ESP_EN", 0.25, 0.15, ("R601", 1), None),
    ("Net-(R603-Pad1)", 0.25, 0.15, ("SW601", 2, 1), ("SW601", 2, 0)),
    ("Net-(R603-Pad1)", 0.25, 0.15, ("R603", 1), None),
    ("/esp32/ESP_BOOT", 0.25, 0.15, ("SW602", 1, 1), ("SW602", 1, 0)),
    ("/esp32/ESP_BOOT", 0.25, 0.15, ("R602", 1), None),
    ("Net-(R604-Pad1)", 0.25, 0.15, ("SW602", 2, 1), ("SW602", 2, 0)),
    ("Net-(R604-Pad1)", 0.25, 0.15, ("R604", 1), None),
    ("Net-(R609-Pad1)", 0.25, 0.15, ("SW603", 2), ("R609", 1)),
    ("Net-(D201-A)", 0.25, 0.15, ("D201", 2), ("R205", 1)),
    ("Net-(D401-A)", 0.25, 0.15, ("D401", 2), ("R404", 1)),
    ("Net-(D402-RA)", 0.25, 0.15, ("D402", 4), ("R405", 1)),
    ("Net-(D402-GA)", 0.25, 0.15, ("D402", 3), ("R406", 1)),
    ("Net-(D601-DIN)", 0.25, 0.15, ("D601", 3), ("R608", 2)),
    ("Net-(R802-Pad1)", 0.25, 0.15, ("R802", 1), ("U802", 4)),
    ("Net-(Q701-D)", 0.25, 0.15, ("R703", 1), ("Q701", 3)),
]

# Laid by hand before the routed entries (the router's 0.1 mm grid misses these tight spots).
FIXED_TRACKS = [  # net, layer, width, points
    # U103 dividers: each top resistor's VBUS pad sits between its mid node and the bottom
    # resistor. Columns west to east: R107/R108 (CP2), R111/R112 (OV2), R109/R110 (OV1),
    # R105/R106 (PR1). The mid links of CP2, OV2 and OV1 run down the 0.45 mm gaps east of
    # their column (0.15 mm line, 0.15 mm to each pad); PR1 is routed round the east side; the
    # west side stays free for R107.2's VBUS_ESP feed (the B.Cu LED ring runs under R107, so no
    # via fits in that pad). R111.2 takes a via in its pad (In2 VBUS_ESP).
    ("Net-(U103-CP2)", "F.Cu", 0.15, [(167.891, 117.542), (168.436, 118.087), (168.436, 119.007), (167.891, 119.552)]),
    ("Net-(U103-OV2)", "F.Cu", 0.15, [(168.981, 117.542), (169.527, 118.088), (169.527, 119.006), (168.981, 119.552)]),
    ("Net-(U103-OV1)", "F.Cu", 0.15, [(170.073, 117.55), (170.618, 118.095), (170.618, 119.015), (170.073, 119.56)]),
    # VBUS_MAIN tops R109.2 + R105.2: a via in each pad, joined on the bottom layer and taken on
    # to the pin 7 flange via (In2 under R109 is VBUS_ESP, so the vias cannot use the plane)
    ("VBUS_MAIN", "B.Cu", 0.3, [(170.073, 118.57), (171.163, 118.57), (171.163, 117.387), (172.0, 116.55)]),
    # U302 (reset supervisor) MR from SW301: north round the chip (clear of C322) and in to pin 3
    # from the east, so the gap between U302's pad rows stays free for its GND via (the B.Cu LED
    # ring runs under pin 2, so no via fits in that pad or east of it)
    ("Net-(U302-~{MR})", "F.Cu", 0.2, [(116.358, 89.941), (117.0, 89.941), (117.3, 89.641), (117.3, 84.9),
                                       (117.6, 84.6), (120.5, 84.6), (120.8, 84.9), (120.8, 88.903),
                                       (120.5, 89.203), (120.058, 89.203)]),
    ("GND", "F.Cu", 0.25, [(119.108, 89.203), (119.108, 88.578), (118.6, 88.07)]),
]
FIXED_VIAS = [  # point, net, (size, drill)
    ((170.073, 118.57), "VBUS_MAIN", (0.45, 0.2)),
    ((171.163, 118.57), "VBUS_MAIN", (0.45, 0.2)),
    ((118.6, 88.07), "GND", (0.45, 0.2)),
]
