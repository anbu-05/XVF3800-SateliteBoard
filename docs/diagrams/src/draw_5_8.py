import sys
sys.path.insert(0, sys.argv[1])
from svglib import Svg

OUT = sys.argv[2]

# ---------------------------------------------------------------- 05 audio out flow
s = Svg(1000, 470, "USB audio-out flow",
        "The host sends playback audio over USB. The XVF3800 keeps a copy as the echo reference and sends "
        "the same audio out as I2S on pins 9, 10 and 13 to the MAX98357A, which drives the speaker. The "
        "speaker sound reaches the mics as echo; the XVF3800 removes it and sends clean voice back.")
s.text(30, 28, "MindSpeak rev 1: how audio gets out", "h1")
s.text(30, 52, "The XVF3800 has no DAC. It is the I²S master; the MAX98357A turns I²S into speaker drive. Updated 2026-11-10.", "s")
s.box(30, 150, 170, 80, "USB host", ["PC now, CM5 in rev 2"], "gry")
s.box(300, 120, 230, 140, "XVF3800", ["keeps playback as the", "echo reference (AEC)",
                                      "I²S master, 48 kHz", "BCLK 3.072 MHz"], "xvf")
s.wire([(200, 175), (298, 175)], "sig", label="playback (USB)", lpos=(249, 162))
s.wire([(298, 210), (200, 210)], "sig", label="clean voice (USB)", lpos=(249, 226))
s.box(630, 130, 200, 120, "MAX98357A", ["I²S DAC + class-D", "≈3.2 W into 4 Ω at 5 V",
                                         "GAIN pin, SD_MODE (L/R/mix)"], "aud")
s.wire([(530, 165), (628, 165)], "aud", label="9 I2S_DATA0", lpos=(579, 155))
s.wire([(530, 190), (628, 190)], "aud", label="10 LRCK 48 kHz", lpos=(579, 180))
s.wire([(530, 215), (628, 215)], "aud", label="13 BCLK", lpos=(579, 205))
s.box(870, 150, 110, 80, "Speaker", ["CS45, 4 Ω", "JST + pads"], "aud")
s.wire([(830, 190), (868, 190)], "aud")
s.box(300, 340, 230, 70, "4 × PDM mic", ["voice + speaker echo"], "mic")
s.wire([(415, 338), (415, 262)], "sig", label="PDM 43/46/50/48/51", lpos=(425, 300), lanchor="start")
s.wire([(925, 232), (925, 375), (532, 375)], "dash aud", label="echo through the air", lpos=(730, 362))
s.note(630, 280, 230, ["No MCLK and no I²C needed.", "Power from 5 V via TPS22918",
                       "(EN = XVF pin 40)."])
s.save(f"{OUT}/05_audio_out_flow.svg")

# ---------------------------------------------------------------- 06 mic wiring
s = Svg(1120, 905, "IM69D129F mic wiring and placement",
        "Each of the four mics has five pads. XVF3800 pin 43 drives an SN74LVC1G125 clock buffer, then a "
        "100 ohm resistor, then a separate 100 ohm into each mic's CLK. Each mic's DATA goes through its "
        "own 100 ohm to its XVF3800 data pin. The mics sit on the corners of a 66 mm square on the bottom "
        "side, numbered 0 to 3 anticlockwise seen from the top, as on the XMOS XK-VOICE-SQ66 board.")
s.text(30, 28, "MindSpeak rev 1: mic wiring and placement", "h1")
s.text(30, 52, "Infineon IM69D129FV01XTMA1, bottom-port PDM. Clock buffer, series resistors and placement copied "
       "from XMOS XK-VOICE-SQ66. Updated 2026-11-10.", "s")

# --- Pads of one mic (same for all four)
s.box(40, 90, 230, 290, "", [], "mic")
s.text(155, 108, "Pads (same on each mic)", "t", "middle")
rows = [("1  DATA", "own 100 Ω series → XVF pin 46 / 50 / 48 / 51", "sig", "one XVF data pin per mic"),
        ("2  SELECT", "GND", "", "data on falling edge (to verify)"),
        ("3  GND", "GND", "", ""),
        ("4  CLK", "own 100 Ω from the clock buffer (below)", "sig", "3.072 MHz"),
        ("5  VDD", "3.3 V mic rail", "pwr", "1 µF (+100 nF) at each mic")]
for i, (pad_, to, cls, note) in enumerate(rows):
    y = 145 + i * 50
    s.text(60, y, pad_, "t")
    s.wire([(270, y), (470, y)], cls, arrow=False)
    s.text(480, y, to, "s")
    if note:
        s.text(480, y + 16, note, "xs")
s.note(800, 95, 270, ["XMOS wants one mic per data pin,", "single data rate. Which clock edge",
                      "XMOS samples decides SELECT;", "GND is assumed. Check before layout."],
       "To verify")
s.box(800, 245, 270, 75, "Mic supply", ["3.3 V buck → BLM15AG601 ferrite", "→ mic rail; keeps buck",
                                         "ripple off the mics"], "pwr")

# --- Clock and data path: one buffered clock fanned out through 100 Ω each
s.text(40, 410, "Clock and data path", "h2")
s.box(40, 465, 140, 60, "XVF3800", ["pin 43 MIC_CLK"], "xvf")
s.box(225, 465, 170, 60, "SN74LVC1G125", ["OE tied low, on +3V3"], "gry")
s.wire([(180, 495), (223, 495)], "sig")
s.box(435, 480, 60, 30, "", [], "gry")
s.text(465, 495, "100 Ω", "lbl", "middle")
s.wire([(395, 495), (433, 495)], "sig", arrow=False)
s.wire([(495, 495), (540, 495)], "sig", arrow=False)
s.add('<path class="wire sig" d="M540 440 L540 560"/>')   # fan-out node to the four mics
mic_rows = [(0, "46"), (1, "50"), (2, "48"), (3, "51")]
for i, (m, pin) in enumerate(mic_rows):
    y = 440 + i * 40
    s.wire([(540, y), (575, y)], "sig", arrow=False)
    s.box(575, y - 13, 60, 26, "", [], "gry")
    s.text(605, y, "100 Ω", "lbl", "middle")
    s.wire([(635, y), (673, y)], "sig")
    s.box(675, y - 15, 150, 30, "", [], "mic")
    s.text(750, y, f"mic {m}: CLK · DATA", "s", "middle")
    s.wire([(825, y), (860, y)], "sig", arrow=False)
    s.box(860, y - 13, 60, 26, "", [], "gry")
    s.text(890, y, "100 Ω", "lbl", "middle")
    s.wire([(920, y), (958, y)], "sig")
    s.text(965, y, f"XVF pin {pin} (DATA{m})", "s")

# --- Placement on the board, top view (mics are on the bottom side)
s.text(40, 615, "Placement: 66 × 66 mm square, all four mics on the bottom side (stock -sqr firmware)", "h2")
sx, sy, sq = 330, 660, 200            # square drawn as seen from the top
s.add(f'<rect x="{sx}" y="{sy}" width="{sq}" height="{sq}" fill="none" stroke="#2f7d1f" '
      f'stroke-width="1.4" stroke-dasharray="6 4"/>')
s.text(sx + sq / 2, sy - 12, "66 mm", "lbl", "middle")
s.text(sx + sq + 12, sy + sq / 2, "66 mm", "lbl", "start")
# USB side = edge with the main USB-C, drawn at the bottom of the picture
s.box(sx + sq / 2 - 55, sy + sq - 12, 110, 24, "", [], "gry", rx=4)
s.text(sx + sq / 2, sy + sq, "main USB-C", "lbl", "middle")
s.text(sx + sq / 2, sy + sq + 26, "USB side", "xs", "middle")
corners = [  # (x, y, label anchor side, text lines)
    (sx, sy, "end", ["mic 0 · DATA0, pin 46", "far left (XMOS MIC1)"]),
    (sx, sy + sq, "end", ["mic 1 · DATA1, pin 50", "USB side left (XMOS MIC4)"]),
    (sx + sq, sy + sq, "start", ["mic 2 · DATA2, pin 48", "USB side right (XMOS MIC5)"]),
    (sx + sq, sy, "start", ["mic 3 · DATA3, pin 51", "far right (XMOS MIC3)"]),
]
for i, (x, y, anc, lines) in enumerate(corners):
    s.add(f'<circle cx="{x}" cy="{y}" r="11" class="box k-mic"/>')
    s.text(x, y, str(i), "lbl", "middle")
    dx = -18 if anc == "end" else 18
    s.text(x + dx, y - 8, lines[0], "s", anc)
    s.text(x + dx, y + 8, lines[1], "xs", anc)
# Anticlockwise order 0 -> 1 -> 2 -> 3 (seen from the top)
s.wire([(sx + 25, sy + 30), (sx + 25, sy + sq - 30)], "dash", label=None)
s.wire([(sx + 30, sy + sq - 25), (sx + sq - 30, sy + sq - 25)], "dash")
s.wire([(sx + sq - 25, sy + sq - 30), (sx + sq - 25, sy + 30)], "dash")
s.text(sx + sq / 2, sy + sq / 2 - 8, "top view", "s", "middle")
s.text(sx + sq / 2, sy + sq / 2 + 8, "0 → 1 → 2 → 3 anticlockwise", "xs", "middle")
s.save(f"{OUT}/06_mic_wiring.svg")

# ---------------------------------------------------------------- 07 ESP32-S3 block
s = Svg(1150, 970, "ESP32-S3 helper module block",
        "The ESP32-S3-WROOM-1U-N16R8 module in the middle with its GPIO numbers on the wires. Left: its own "
        "USB-C, BOOT and EN buttons, SPI2 to the XVF3800 flash through four switches, the PROG slide switch, the "
        "XVF3800 reset transistor, the XVF3800 LED and interrupt taps and the power-mux status. Right: the "
        "WS2812 ring, user RGB LED, mute LED, user button, I2C, UART0 and the 2x12 GPIO header.")
s.text(30, 28, "MindSpeak rev 1: ESP32-S3 helper module", "h1")
s.text(30, 52, "Own firmware. The XVF3800 stays on stock firmware. Numbers on the wires are ESP32 GPIOs. "
       "Updated 2026-11-11.", "s")
s.box(430, 85, 260, 595, "ESP32-S3-WROOM-1U", ["N16R8: 16 MB flash, 8 MB PSRAM", "LCSC C3013946",
                                               "IPEX connector,", "antenna off-board",
                                               "3.3 V, Wi-Fi TX ≈0.36 A peak"], "mcu")


def lside(y, h, title, lines, kind, lbl, cls="mcu"):
    # Left peripheral box with a wire into the module, GPIO numbers on the wire
    s.box(30, y, 300, h, title, lines, kind)
    s.wire([(330, y + h / 2), (428, y + h / 2)], cls, label=lbl, lpos=(379, y + h / 2 - 9))


def rside(y, h, title, lines, kind, lbl, cls="mcu"):
    # Right peripheral box with a wire out of the module, GPIO numbers on the wire
    s.box(810, y, 310, h, title, lines, kind)
    s.wire([(692, y + h / 2), (808, y + h / 2)], cls, label=lbl, lpos=(750, y + h / 2 - 9))


lside(85, 70, "USB-C (ESP32 port)", ["27 Ω series on D+/D−, TPD4E05U06 ESD", "VBUS_ESP → TPS2121 IN2"],
      "gry", "19 D− · 20 D+", "sig")
lside(175, 70, "BOOT + EN (reset) buttons, top", ["GPIO0: 10 kΩ pull-up, button → 1 kΩ → GND",
                                              "EN: 10 kΩ pull-up + 1 µF, same button"], "ui", "0 · EN")
lside(265, 85, "XVF flash, path B (SPI2)", ["via 4 × TS5A3166 to the W25Q32", "10 CS_N · 11 MOSI → DI",
                                             "12 CLK · 13 MISO ← DO"], "prg", "10–13", "prg")
lside(370, 60, "PROG slide switch SW701", ["side-actuated; PRG_EN high = switches on"], "prg", "14", "prg")
lside(450, 60, "XVF reset", ["PRG_RST → 2N7002 Q701 → XVF RST_N"], "prg", "21", "prg")
lside(530, 70, "XVF3800 taps (inputs)", ["15 ← LED_R (pin 56) · 16 ← LED_G (pin 58)",
                                          "17 ← INT_N (pin 55)"], "xvf", "15 · 16 · 17", "sig")
lside(620, 60, "Power-mux status", ["TPS2121 ST"], "pwr", "18", "pwr")

rside(85, 85, "WS2812B ring", ["12 × WS2812B-2020 on switched 5 V", "47 → TPS22918 EN",
                               "48 → SN74AHCT1G125 → data (RMT)"], "ui", "47 · 48")
rside(190, 70, "User RGB LED", ["WS2812B-2020 + own SN74AHCT1G125", "always-on +5V, not chained to the ring"],
      "ui", "40")
rside(280, 55, "Mute LED", ["red, via 1 kΩ (was XVF pin 54)"], "ui", "41")
rside(355, 55, "User button (side, TS24CA)", ["10 kΩ pull-up, active low"], "ui", "42")
rside(430, 70, "I²C", ["4.7 kΩ pull-ups", "→ J701 pins 13 / 15"], "gry", "38 SDA · 39 SCL", "sig")
rside(520, 70, "UART0", ["boot log + console", "on header pins 21 / 22"], "gry",
      "43 TX · 44 RX", "sig")
rside(610, 70, "2×12 header J701", ["GPIO 1, 2, 4, 5, 6, 7, 8, 9", "on header pins 5–12"], "gry",
      "8 GPIO", "sig")

# 2x12 header J701 pinout, drawn as the real two-row header (odd pins left, even pins right)
j702 = ["+5V", "+3V3", "+1V8", "GND", "GPIO1", "GPIO2", "GPIO4", "GPIO5", "GPIO6", "GPIO7",
        "GPIO8", "GPIO9", "ESP I²C SDA", "XVF I²C SDA", "ESP I²C SCL", "XVF I²C SCL",
        "XVF INT_N", "XVF I2S_DATA1", "XVF I2S_DATA2", "GND",
        "ESP UART TX (43)", "ESP UART RX (44)", "+5V", "+3V3"]
jx, jy = 30, 705
s.add(f'<rect class="note" x="{jx}" y="{jy}" width="560" height="237" rx="6"/>')
s.text(jx + 10, jy + 16, "J701 pinout (2×12, 2.54 mm, SMD)", "t")
for i, name in enumerate(j702):
    row, col = i // 2, i % 2
    x = jx + 20 + col * 240
    y = jy + 42 + row * 16
    s.text(x, y, f"{i + 1:>2}", "lbl")
    s.text(x + 24, y, name, "s")
# Shunt note beside rows 13-16
for k, ln in enumerate(["shunts on 13–14 and", "15–16 join the ESP32", "and XVF I²C buses"]):
    s.text(jx + 410, jy + 42 + (6 + k) * 16, ln, "xs")
s.note(810, 705, 310, ["Strapping pins GPIO3, 45, 46",
                       "PSRAM pins GPIO35–37"], "Not connected")
s.note(810, 795, 310, ["+5V, +3V3 and +1V8 on J701 are",
                       "for low-current use only."], "Header power")
s.save(f"{OUT}/07_esp32_block.svg")

# ---------------------------------------------------------------- 08 programming paths
s = Svg(1100, 720, "XVF3800 programming paths: XTAG or ESP32-S3",
        "Path A: an XTAG4 on the 1.8 V JTAG header loads firmware through the XVF3800 into its flash. "
        "Path B: with the PROG slide switch SW701 on, the ESP32-S3 holds the XVF3800 in reset through Q701, connects "
        "to the flash through four TS5A3166 switches and writes the image directly over SPI2, then lets go "
        "and releases reset.")
s.text(30, 28, "MindSpeak rev 1: two ways to load XVF3800 firmware", "h1")
s.text(30, 52, "SW701 at RUN (default): ESP32 is cut off from the flash, XTAG works as normal. SW701 at PROG: the ESP32 "
       "can write the flash.", "s")

s.box(420, 250, 220, 120, "XVF3800", ["boots from QSPI flash", "boot straps 59, 60, 1"], "xvf")
s.box(420, 520, 220, 80, "W25Q32JVUUIQ", ["XVF3800 boot flash"], "gry")
s.wire([(470, 372), (470, 518)], "sig")
s.text(462, 435, "3 CS · 5 CLK", "lbl", "end")
s.text(462, 451, "59 D0 · 1 D1", "lbl", "end")
s.text(462, 467, "(+ 60, 2)", "lbl", "end")
# Path A
s.text(40, 100, "Path A: XTAG4 (XMOS tools)", "h2")
s.box(40, 120, 180, 70, "PC + XTC tools", ["xflash"], "gry")
s.box(240, 120, 160, 70, "XTAG4", ["XMOS debug adapter"], "prg")
s.box(40, 280, 300, 80, "JTAG header (1.8 V)", ["24 TCK · 23 TMS · 18 TDI · 20 TDO", "21 RST_N"], "prg")
s.wire([(220, 155), (238, 155)], "prg")
s.wire([(320, 190), (320, 230), (190, 230), (190, 278)], "prg")
s.wire([(340, 320), (418, 320)], "prg", label="JTAG", lpos=(379, 308))
s.note(40, 390, 300, ["XTAG loads a helper into the XVF3800,",
                      "which writes its own flash. Also gives",
                      "live debugging. Check XTAG4 at 1.8 V."])
# Path B
s.text(760, 100, "Path B: ESP32-S3 (no XMOS hardware)", "h2")
s.box(760, 120, 140, 70, "PC", ["sends image"], "gry")
s.box(930, 120, 150, 70, "ESP32-S3", ["SPI flash writer"], "mcu")
s.wire([(900, 155), (928, 155)], "mcu")
s.text(830, 205, "image over USB-C (ESP32)", "lbl", "middle")
s.box(760, 290, 150, 60, "2N7002 Q701", ["+ 0 Ω link"], "prg")
s.wire([(960, 190), (960, 320), (912, 320)], "mcu", label="GPIO21", lpos=(968, 300), lanchor="start")
s.wire([(758, 320), (642, 320)], "prg", label="RST_N low", lpos=(700, 308))
s.box(760, 400, 320, 90, "4 × TS5A3166 switches", ["IN ← SW701 PROG switch (RUN = off)",
                                                     "switch state → ESP32 GPIO14",
                                                     "SPI2: 10 CS · 11 MOSI · 12 CLK · 13 MISO"], "prg")
s.wire([(1050, 190), (1050, 398)], "mcu", label="GPIO10–13", lpos=(1044, 240), lanchor="end")
s.wire([(758, 470), (700, 470), (700, 560), (642, 560)], "prg", label="flash lines", lpos=(706, 515),
       lanchor="start")

s.note(40, 560, 380, ["1. Slide SW701 to PROG; ESP32 pulls RST_N low (Q701).",
                      "2. XVF3800 lets go of the flash pins in reset.",
                      "3. ESP32 erases + writes the image (standard",
                      "    W25Q commands), reads it back to check.",
                      "4. ESP32 releases the lines (59, 60, 1 are boot",
                      "    straps), then RST_N. XVF3800 boots."], "Path B step by step")
s.note(760, 560, 320, ["Image = .xe converted to raw flash bytes",
                       "by XMOS xflash (free tool) on the PC.",
                       "Verify boot from it on the first board."])
s.save(f"{OUT}/08_programming_paths.svg")
print("ok")
