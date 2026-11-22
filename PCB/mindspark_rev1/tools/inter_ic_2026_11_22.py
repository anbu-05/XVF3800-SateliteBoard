"""Group 3 of the remaining-net order (2026-11-22): fixed inter-IC signals.

Both ends of these nets are fixed parts (no header or test pad). Winged (user 2026-11-22): no
drawing. power_v2 routes them after all power copper with tools/grid_router.py, which searches
both layers at once and drops a via wherever a layer change pays (the user's "out a little, then
a via"): long runs here cross the B.Cu +5V_LED ring, the F.Cu ESP32 USB pair and the mic legs.
Each entry: (net, goal (ref, pin), start)
  start: (ref, pin) to leave from that pad; ("@", layers, (x, y)) to leave from a point (a group 2
         lane end or escape via); None to leave from what earlier entries laid on the net.
Slow control lines, 0.15 mm, 0.15 mm clearance. The ESP32 underside keep-out for power traces
does not apply to them.
"""

W = 0.15
FB = ("F.Cu", "B.Cu")
B = ("B.Cu",)

ROUTES = [
    # Order found by power_v2's rip-up-and-retry (2026-11-22): these four nets get boxed in when
    # they come later, so they go first.
    ("/XVF_GPO_R", ("U601", "8"), ("@", FB, (142.2, 97.25))),
    ("/XVF_GPO_R", ("R405", "2"), None),
    ("/AMP_EN", ("R510", "1"), ("@", B, (145.575, 108.9))),
    ("/AMP_EN", ("U502", "3"), None),
    ("/BTN_MUTE_N", ("R402", "2"), ("@", FB, (147.758, 93.75))),
    ("/BTN_MUTE_N", ("SW401", "1"), None),
    ("/esp32/ESP_BOOT", ("R602", "1"), ("U601", "27")),
    # 0. LED ring switch and data buffer (routed first: pins 24/25 get boxed in by the lines
    #    that pass east of the module)
    ("/LED_EN", ("R801", "1"), ("U601", "24")),
    ("/LED_EN", ("U801", "3"), None),
    ("/LED_DATA", ("U802", "2"), ("U601", "25")),
    # 1. XVF reset to its pull-up / supervisor in the far west (from the RST_N copper at R703)
    ("/XVF_RST_N", ("R303", "1"), ("R703", "2")),
    ("/XVF_RST_N", ("U302", "1"), None),
    # 2. PRG_EN: ESP32 pin 22 to the flash-switch enable line west of the module
    ("/PRG_EN", ("U702", "4"), ("U601", "22")),
    # 3. PRG_RST: ESP32 pin 23 to the reset FET Q701 and its pull-down
    ("/PRG_RST", ("Q701", "1"), ("U601", "23")),
    ("/PRG_RST", ("R702", "1"), None),
    # 4. XVF status lines to the ESP32 (from the group 2 escapes), then on to the edge parts
    ("/XVF_INT_N", ("U601", "10"), ("@", B, (136.2, 97.629))),
    ("/XVF_GPO_G", ("U601", "9"), ("@", FB, (141.4, 96.85))),
    ("/XVF_GPO_G", ("R406", "2"), None),
    # 5. amp enable: XVF pin 40's south lane to the amp's load switch (north-west)
    # 6. ESP32 EN and BOOT to their RC / buttons on the west edge
    ("/esp32/ESP_EN", ("R601", "1"), ("U601", "3")),
    # 7. power mux status
    ("/MUX_ST", ("U103", "9"), ("U601", "11")),
    ("/MUX_ST", ("R114", "1"), None),
    # 9. east-edge buttons and the mute LED
    ("/BTN_ACTION_N", ("R403", "2"), ("@", B, (149.158, 108.9))),
    ("/BTN_ACTION_N", ("SW402", "1"), None),
    ("/esp32/BTN_USER_N", ("R607", "2"), ("U601", "35")),
    ("/esp32/BTN_USER_N", ("SW603", "1"), None),
    ("/ESP_MUTE_LED", ("R404", "2"), ("U601", "34")),
    # 10. user LED: ESP32 pin 33 to its buffer, buffer to the LED's resistor (west edge)
    ("/esp32/USER_LED_DATA", ("U602", "2"), ("U601", "33")),
    ("Net-(R608-Pad1)", ("R608", "1"), ("U602", "4")),
]
