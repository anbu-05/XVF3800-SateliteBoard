"""Groups 4-6 of the remaining-net order (2026-11-22): LED ring chain, breakout, test pads.

Winged (user 2026-11-22): no drawing. power_v2 routes these right after group 3 with the same
two-layer grid router (tools/grid_router.py) and the same rip-up-and-retry. Test pads (user
2026-11-22): 1 mm round, top or bottom, placed next to where their net already has copper
(tools/test_pad_place_2026_11_22.py), so each joins on a short stub; duplicates of header pins
were removed (tools/test_pads_2026_11_22.py).

Each entry: (net, goal (ref, pin), start), as in tools/inter_ic_2026_11_22.py, plus:
  start "*": leave from any copper the net already has (pads, tracks, vias, group 2 lane ends).

"""

EARLY = [
    # Routed before group 3 (power_v2 puts these at the front of the group 3 batch). Group 3's
    # lines are free to go anywhere, but once they hug the module these short legs are walled
    # in: south of the module the ESP32 USB pair (F.Cu) and group 3 lines (B.Cu) run one above
    # the other, and the I2C pull-ups sit right north of their pins.
    ("/ESP_I2C_SDA", ("R704", "2"), ("U601", "31")),
    ("/ESP_I2C_SCL", ("R705", "2"), ("U601", "32")),
    # ESP32 south-row pins straight down to the header
    ("/ESP_GPIO4", ("J701", "7"), ("U601", "4")),
    ("/ESP_GPIO5", ("J701", "8"), ("U601", "5")),
    ("/ESP_GPIO6", ("J701", "9"), ("U601", "6")),
    ("/ESP_GPIO7", ("J701", "10"), ("U601", "7")),
    ("/ESP_GPIO8", ("J701", "11"), ("U601", "12")),
    ("/ESP_GPIO9", ("J701", "12"), ("U601", "17")),
]

GROUP4 = [
    # LED ring data chain. The LEDs sit on the B.Cu +5V_LED ring; each DOUT feeds the next LED's
    # DIN. Where a mic line runs on B.Cu between neighbours the router hops to F.Cu.
    ("/led_ring/LED_D0", ("D801", "3"), ("R802", "2")),
    ("Net-(D801-DOUT)", ("D802", "3"), ("D801", "1")),
    ("Net-(D802-DOUT)", ("D803", "3"), ("D802", "1")),
    ("Net-(D803-DOUT)", ("D804", "3"), ("D803", "1")),
    ("Net-(D804-DOUT)", ("D805", "3"), ("D804", "1")),
    ("Net-(D805-DOUT)", ("D806", "3"), ("D805", "1")),
    ("Net-(D806-DOUT)", ("D807", "3"), ("D806", "1")),
    ("Net-(D807-DOUT)", ("D808", "3"), ("D807", "1")),
    ("Net-(D808-DOUT)", ("D809", "3"), ("D808", "1")),
    ("Net-(D809-DOUT)", ("D810", "3"), ("D809", "1")),
    ("Net-(D810-DOUT)", ("D811", "3"), ("D810", "1")),
    ("Net-(D811-DOUT)", ("D812", "3"), ("D811", "1")),
]

J701 = [
    # ESP32 north-row pins round the module to the header (first:
    # the room round the module is tight, one of four lost out whenever they came later)
    ("/ESP_UART_TX", ("J701", "21"), ("U601", "37")),
    ("/ESP_UART_RX", ("J701", "22"), ("U601", "36")),
    ("/ESP_GPIO1", ("J701", "5"), ("U601", "39")),
    ("/ESP_GPIO2", ("J701", "6"), ("U601", "38")),
    # XVF lines from their group 2 lane ends / group 3 copper
    ("/XVF_INT_N", ("J701", "17"), "*"),
    ("/XVF_I2S_DATA1", ("J701", "18"), "*"),
    ("/XVF_I2S_DATA2", ("J701", "19"), "*"),
    ("/XVF_I2C_SDA", ("J701", "14"), "*"),
    ("/XVF_I2C_SCL", ("J701", "16"), "*"),
    # ESP32 I2C: pull-ups north of the module, then round the module to the header
    ("/ESP_I2C_SDA", ("J701", "13"), "*"),
    ("/ESP_I2C_SCL", ("J701", "15"), "*"),
]

# Test pads (groups 5 and 6): each from the nearest copper of its net; the pads sit next to it
# (power_v2 places them after all other routing; spots recorded in
# tools/test_pad_spots_2026_11_22.json), so these are short stubs (or none: pad on the track).
TEST_PADS = [
    ("+0V9", ("TP204", "1"), "*"),
    ("/XVF_SPI_CS_N", ("TP401", "1"), "*"),
    ("/XVF_SPI_MOSI", ("TP402", "1"), "*"),
    ("/XVF_SPI_MISO", ("TP403", "1"), "*"),
    ("/XVF_SQ_NLIN", ("TP404", "1"), "*"),
    ("/XL_DN1", ("TP405", "1"), "*"),
    ("/XL_DN0", ("TP406", "1"), "*"),
    ("/XL_UP0", ("TP407", "1"), "*"),
    ("/XL_UP1", ("TP408", "1"), "*"),
    ("/I2S_DATA0", ("TP409", "1"), "*"),
    ("/I2S_LRCK", ("TP410", "1"), "*"),
    ("/I2S_BCLK", ("TP411", "1"), "*"),
    ("/MCLK_LOOP", ("TP412", "1"), "*"),
]

ROUTES = J701 + GROUP4          # TEST_PADS go last, once power_v2 has placed the pads
