import sys
sys.path.insert(0, sys.argv[1])
from svglib import Svg

OUT = sys.argv[2]

# ---------------------------------------------------------------- 03 XVF3800 connections
s = Svg(1160, 850, "Everything connected to the XVF3800",
        "The XVF3800 in the middle with its pin numbers. Left: USB-C, QSPI flash, crystal, reset, JTAG "
        "header, ESP32-S3 link and power. Right: four mics behind a clock buffer, MCLK loop, MAX98357A amp, "
        "buttons, GPO outputs, the 2x12 header and the solder pads.")
s.text(30, 28, "MindSpeak rev 1: everything connected to the XVF3800", "h1")
s.text(30, 52, "Numbers on the wires are XVF3800 pins. Updated 2026-11-10: ESP32-S3 link, corrected pins 54/55, "
       "mic clock buffer.", "s")

cx, cw = 480, 180
s.box(cx, 80, cw, 745, "", (), "xvf")
s.text(cx + cw / 2, 435, "XVF3800-QF60B-C", "t", "middle")
s.text(cx + cw / 2, 455, "QFN-60", "s", "middle")
s.text(cx + cw / 2, 471, "stock USB firmware", "s", "middle")


def _pins(x, y, pins):
    # pins is one string or a pair: first line above the wire, second below it
    if isinstance(pins, str):
        pins = (pins,)
    s.text(x, y - 9, pins[0], "lbl", "middle")
    if len(pins) > 1:
        s.text(x, y + 10, pins[1], "lbl", "middle")


def left(y, h, title, lines, kind, pins, wcls="sig"):
    s.box(30, y, 280, h, title, lines, kind)
    s.wire([(310, y + h / 2), (cx - 2, y + h / 2)], wcls)
    _pins((310 + cx) / 2, y + h / 2, pins)


def right(y, h, title, lines, kind, pins, wcls="sig"):
    s.box(830, y, 300, h, title, lines, kind)
    s.wire([(cx + cw, y + h / 2), (828, y + h / 2)], wcls)
    _pins((cx + cw + 830) / 2, y + h / 2, pins)


left(85, 70, "USB-C (main)", ["TPD4E05U06 ESD, 90 Ω pair", "bus-powered, no VBUS sense"], "gry",
     "28 USB_DM · 29 USB_DP")
left(175, 85, "QSPI flash W25Q32JVUUIQ", ["CS_N 4.7 kΩ pull-up to 3.3 V", "D1 straight to flash",
                                         "* also reachable by the ESP32"], "gry",
     ("3 CS* · 5 CLK* · 59 D0*", "1 D1* · 60 D2 · 2 D3"))
left(280, 70, "24 MHz crystal X322524MOB4SI", ["Rf 1 MΩ, Rd 680 Ω, 22 pF × 2", "1.8 V domain (bottom bank)"],
     "gry", "16 XIN · 15 XOUT")
left(370, 85, "Reset (RST_N, 1.8 V)", ["TPS3808G33 open drain + 10 kΩ to 1.8 V", "reset button on MR",
                                       "ESP32 GPIO21 → 2N7002 Q701 · XTAG"], "prg", "21 RST_N", "prg")
left(475, 70, "JTAG header S7B-PH-SM4-TB", ["1.8 V signals, for an XTAG4", "+ parallel solder pads"],
     "prg", ("24 TCK · 23 TMS", "18 TDI · 20 TDO"), "prg")
left(565, 115, "ESP32-S3 link", ["4 × TS5A3166 switches on 3, 5, 59, 1", "(PROG switch SW701 = on; off by default)",
                                 "taps: 56 R → GPIO15, 58 G → GPIO16", "55 INT_N → GPIO17"], "mcu",
     ("switched: 3 · 5 · 59 · 1", "taps: 55 · 56 · 58"), "mcu")
left(700, 100, "Power", ["VDD 0.9 V: 4,12,19,27,34,42,49,57,61–64", "PLL_AVDD 22: ferrite + 1 µF",
                         "VDDIOL/R/T 8,38,52 · USB_VDD33 30: 3.3 V", "VDDIOB18 17,26 · USB_VDD18 31: 1.8 V"],
     "pwr", ("power pins", "GND paddle 65"), "pwr")

right(85, 100, "4 × IM69D129F PDM mic", ["43 → SN74LVC1G125 → 100 Ω → 100 Ω per mic",
                                          "DATA 100 Ω series per mic:", "mic 0 → 46, 1 → 50, 2 → 48, 3 → 51",
                                          "SELECT → GND, 3.3 V via ferrite"], "mic",
      ("43 CLK", "46 · 50 · 48 · 51"))
right(205, 70, "MCLK loop (PCB trace)", ["pin 14 MCLK out → pin 41 MCLK in", "test pad on 14"], "gry",
      "14 → 41")
right(295, 85, "MAX98357AEWL+T", ["I²S DAC + class-D amp, 5 V via TPS22918", "SD_MODE resistor, GAIN pin",
                                   "test pads on 9, 10, 13"], "aud",
      ("9 DATA0 · 10 LRCK", "13 BCLK"), "aud")
right(400, 70, "Side buttons TS24CA", ["active low, 10 kΩ pull-ups", "mute = 11, action = 32"], "ui",
      "11 · 32")
right(490, 85, "GPO outputs (stock firmware)", ["40 → amp load switch EN",
                                                 "56 R · 58 G → RGB status LED (blue unused)",
                                                 "56/58 also tapped by the ESP32"], "ui",
      ("40", "56 · 58"))
right(595, 100, "2×12 header J701", ["39 I2S_DATA1 · 53 I2S_DATA2",
                                      "44 SCL / 45 SDA (no pull-ups; shunts",
                                      "on 13–14, 15–16 join the ESP32 I²C)",
                                      "55 INT_N (also ESP32 GPIO17)"], "gry",
      ("39 · 53 · 44 · 45", "55"))
right(715, 100, "Solder pads / not connected", ["6/7/47 SPI CS/MOSI/MISO · 54 SQ_nLIN",
                                                "33/35/36/37 XLINK (debug)",
                                                "25 NC: leave unconnected"], "dnp",
      ("6 · 7 · 47 · 54", "33–37 · (25 NC)"), "dash")
s.save(f"{OUT}/03_xvf3800_connections.svg")

# ---------------------------------------------------------------- 04 pin map
s = Svg(980, 940, "XVF3800 pin map by function",
        "Top view of the 60-pin QFN with every pin coloured by function and labelled with its signal "
        "and its use on the MindSpeak rev 1 board.")
s.add("""<style>
 .k-clk { fill:#fff1c2; stroke:#a16207; } .k-fl { fill:#efe3ff; stroke:#7e22ce; }
 .k-usb { fill:#dbe7ff; stroke:#1d4ed8; } .k-gpio { fill:#e8f5c8; stroke:#4d7c0f; }
 .k-dbg { fill:#e5e7eb; stroke:#374151; } .k-esp { fill:#fde8f1; stroke:#be185d; }
 .k-hdr { fill:#d9f2f7; stroke:#0e7490; } .k-pad { fill:#ffffff; stroke:#6e7781; }
 .pn { font-size: 9.5px; font-weight: 600; } .pl { font-size: 10.5px; fill:#1f2328; }
</style>""")
s.text(30, 28, "XVF3800 pin map (top view)", "h1")
s.text(30, 52, "Signal name (official XMOS pinout), then its use on MindSpeak rev 1. Updated 2026-11-11.", "s")

pins = {
    1: ("QSPI_D1 *", "fl"), 2: ("QSPI_D3", "fl"), 3: ("QSPI_CS_N *", "fl"), 4: ("VDD", "pwr"),
    5: ("QSPI_CLK *", "fl"), 6: ("SPI_CS_N → pad", "pad"), 7: ("SPI_MOSI → pad", "pad"),
    8: ("VDDIOL 3.3 V", "pwr"), 9: ("I2S_DATA0 → amp, TP", "aud"), 10: ("I2S_LRCK → amp, TP", "aud"),
    11: ("BUTTON_0 mute", "gpio"), 12: ("VDD", "pwr"), 13: ("I2S_BCLK → amp, TP", "aud"),
    14: ("MCLK out → 41, TP", "clk"), 15: ("XOUT", "clk"),
    16: ("XIN", "clk"), 17: ("VDDIOB18 1.8 V", "pwr"), 18: ("TDI", "dbg"), 19: ("VDD", "pwr"),
    20: ("TDO", "dbg"), 21: ("RST_N", "dbg"), 22: ("PLL_AVDD", "pwr"), 23: ("TMS", "dbg"),
    24: ("TCK", "dbg"), 25: ("NC", "dnp"), 26: ("VDDIOB18 1.8 V", "pwr"), 27: ("VDD", "pwr"),
    28: ("USB_DM", "usb"), 29: ("USB_DP", "usb"), 30: ("USB_VDD33", "pwr"),
    31: ("USB_VDD18", "pwr"), 32: ("BUTTON_1 action", "gpio"), 33: ("XLINK → pad", "pad"),
    34: ("VDD", "pwr"), 35: ("XLINK → pad", "pad"), 36: ("XLINK → pad", "pad"),
    37: ("XLINK → pad", "pad"), 38: ("VDDIOR 3.3 V", "pwr"), 39: ("I2S_DATA1 → J701", "hdr"),
    40: ("GPO → amp EN", "gpio"), 41: ("MCLK in ← 14", "clk"), 42: ("VDD", "pwr"),
    43: ("MIC_CLK → buffer", "mic"), 44: ("I2C_SCL → J701", "hdr"), 45: ("I2C_SDA → J701", "hdr"),
    46: ("MIC_DATA0", "mic"), 47: ("SPI_MISO → pad", "pad"), 48: ("MIC_DATA2", "mic"),
    49: ("VDD", "pwr"), 50: ("MIC_DATA1", "mic"), 51: ("MIC_DATA3", "mic"), 52: ("VDDIOT 3.3 V", "pwr"),
    53: ("I2S_DATA2 → J701", "hdr"), 54: ("SQ_nLIN → pad", "pad"), 55: ("INT_N → ESP32, J701", "esp"),
    56: ("LED_R → RGB, ESP32", "gpio"), 57: ("VDD", "pwr"), 58: ("LED_G → RGB, ESP32", "gpio"),
    59: ("QSPI_D0 *", "fl"), 60: ("QSPI_D2", "fl"),
}
X0, Y0, SZ, P = 340, 300, 320, 20     # chip origin, chip size, pin pitch
s.box(X0, Y0, SZ, SZ, "", (), "xvf", rx=6)
s.text(X0 + SZ / 2, Y0 + SZ / 2 - 20, "XVF3800, top view", "t", "middle")
s.text(X0 + SZ / 2, Y0 + SZ / 2 + 2, "centre paddles: VDD 61–64,", "s", "middle")
s.text(X0 + SZ / 2, Y0 + SZ / 2 + 18, "GND 65", "s", "middle")
s.add(f'<circle cx="{X0 + 14}" cy="{Y0 + 14}" r="4" fill="none" stroke="#1d4ed8"/>')
off = (SZ - 15 * P) / 2 + 1  # centre the 15-pin row along each side


def pad(x, y, n):
    name, kind = pins[n]
    s.rect(x, y, 18, 18, kind, 2)
    s.text(x + 9, y + 9, str(n), "pn", "middle")
    return name


for i in range(15):
    # Left side, pins 1–15, top to bottom
    n = 1 + i; y = Y0 + off + i * P
    s.text(X0 - 26, y + 9, pad(X0 - 21, y, n), "pl", "end")
    # Bottom, pins 16–30, left to right (labels read downwards)
    n = 16 + i; x = X0 + off + i * P
    s.text(x + 9, Y0 + SZ + 26, pad(x, Y0 + SZ + 3, n), "pl", "end", rot=-90)
    # Right side, pins 31–45, bottom to top
    n = 31 + i; y = Y0 + SZ - off - P + 2 - i * P
    s.text(X0 + SZ + 26, y + 9, pad(X0 + SZ + 3, y, n), "pl", "start")
    # Top, pins 46–60, right to left (labels read upwards)
    n = 46 + i; x = X0 + SZ - off - P + 2 - i * P
    s.text(x + 9, Y0 - 26, pad(x, Y0 - 21, n), "pl", "start", rot=-90)

s.legend(40, 800, [("pwr", "Power"), ("clk", "Clock / MCLK loop"), ("fl", "Boot flash (QSPI)"),
                   ("usb", "USB data"), ("mic", "Microphones"), ("aud", "Audio out (I²S)"),
                   ("gpio", "GPI / GPO"), ("dbg", "Reset + JTAG"), ("esp", "To ESP32-S3"),
                   ("hdr", "2×12 header J701"), ("pad", "Solder pad only"), ("dnp", "NC")], col_w=185)
s.text(40, 875, "* also driven by the ESP32 (SPI2) through the four TS5A3166 switches when the PROG switch SW701 is on.", "s")
s.text(40, 893, "Pins 59, 60, 1 are boot straps (internal pull-downs → QSPI boot). No SPI-slave boot. TP = test pad.", "s")
s.text(40, 911, "Pin 43 drives an SN74LVC1G125 buffer, then 100 Ω per mic. Pins 56/58 = status LED red/green "
       "(also read by ESP32 GPIO15/16); blue unused.", "s")
s.save(f"{OUT}/04_xvf3800_pin_map.svg")
print("ok")
