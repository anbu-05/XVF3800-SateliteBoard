import sys
sys.path.insert(0, sys.argv[1])
from svglib import Svg

OUT = sys.argv[2]

# ---------------------------------------------------------------- 01 block diagram
s = Svg(1000, 740, "MindSpeak rev 1 block diagram",
        "XVF3800 voice processor in the centre with USB-C, flash, crystal and JTAG on the left, "
        "mics, MAX98357A speaker amp and UI on the right, the power block above and the ESP32-S3 "
        "helper module below it with its own USB-C, WS2812 ring, user UI and GPIO headers.")
s.text(30, 28, "MindSpeak rev 1: block diagram", "h1")
s.text(30, 52, "XVF3800 breakout on stock USB firmware, ESP32-S3 helper module, MAX98357A speaker amp. "
       "Updated 2026-11-11.", "s")

# Power block (top centre)
s.box(330, 75, 320, 95, "Power", ["USB-C ×2 → TPS2121 mux → 5 V", "0.9 V buck · 3.3 V buck · 1.8 V LDO",
                                  "TPS3808 supervisor on RST_N"], "pwr")
# XVF3800 (centre)
s.box(370, 230, 240, 160, "XVF3800-QF60B-C", ["XU316 voice processor", "USB audio + control",
                                               "AEC, beamforming, NS", "stock firmware"], "xvf")
s.wire([(490, 170), (490, 228)], "pwr", label="0.9 / 1.8 / 3.3 V", lpos=(482, 200), lanchor="end")

# Left column
s.box(40, 200, 190, 60, "USB-C (main)", ["host link, priority power"], "gry")
s.wire([(230, 230), (368, 250)], "sig", label="USB 2.0 HS (28/29)", lpos=(300, 228))
s.box(40, 290, 190, 60, "QSPI flash", ["W25Q32JVUUIQ, 4 MB, USON-8"], "gry")
s.wire([(230, 320), (368, 320)], "sig", label="QSPI (1,2,3,5,59,60)", lpos=(300, 310))
s.box(40, 375, 190, 50, "24 MHz crystal", ["X322524MOB4SI"], "gry")
s.wire([(230, 400), (300, 400), (300, 370), (368, 370)], "sig", label="XIN/XOUT 16/15", lpos=(335, 360))
s.box(40, 450, 190, 55, "JTAG header", ["S7B-PH, 1.8 V, for XTAG4"], "prg")
s.wire([(230, 470), (420, 470), (420, 392)], "prg", label="TCK/TMS/TDI/TDO/RST_N", lpos=(330, 460))

# Right column: mics (via the clock buffer), amp, speaker, XVF-side UI
s.box(760, 85, 200, 70, "4 × PDM mic", ["IM69D129F, 66 mm square", "CLK via SN74LVC1G125"], "mic")
s.wire([(758, 120), (680, 120), (680, 205), (570, 205), (570, 228)], "sig", arrow=False)
s.text(688, 165, "CLK 43", "lbl")
s.text(688, 180, "DATA 46/50/48/51", "lbl")
s.box(760, 230, 200, 60, "MAX98357A", ["I²S DAC + 3.2 W class-D"], "aud")
s.wire([(612, 260), (758, 260)], "aud", label="I²S 9/10/13", lpos=(685, 250))
s.box(800, 315, 160, 50, "Speaker", ["CS45, 4 Ω, 5 W"], "aud")
s.wire([(860, 290), (860, 313)], "aud")
s.box(760, 390, 200, 70, "XVF UI", ["mute + action side buttons (11, 32)", "RGB status LED (56 R, 58 G)",
                                     "amp enable (40)"], "ui")
s.wire([(612, 350), (700, 350), (700, 425), (758, 425)], "sig", label="GPI / GPO", lpos=(650, 340))

# ESP32-S3 helper module (bottom centre)
s.box(370, 545, 240, 110, "ESP32-S3-WROOM-1U", ["N16R8, IPEX antenna (off-board)", "own firmware: LEDs, GPIO, host link",
                                                 "can reflash the XVF3800"], "mcu")
# XVF -> ESP32: LED/INT taps and reset; XVF -> 2x12 header: spare I2S/I2C/INT_N
s.wire([(540, 392), (540, 543)], "mcu", label="taps 55 INT_N, 56 R, 58 G", lpos=(548, 520), lanchor="start")
s.wire([(430, 543), (430, 393)], "prg", label="RST_N (Q701)", lpos=(422, 520), lanchor="end")
s.wire([(595, 392), (595, 495), (758, 495)], "sig", label="39/44/45/53/55", lpos=(680, 485))
s.box(170, 555, 150, 55, "Flash switches", ["4 × TS5A3166 + SW701"], "prg")
s.wire([(368, 585), (322, 585)], "mcu", label="SPI2", lpos=(345, 575))
s.wire([(245, 553), (245, 365), (200, 365), (200, 352)], "prg", label="flash lines", lpos=(252, 420), lanchor="start")
s.box(40, 650, 150, 50, "USB-C (ESP32)", ["USB FS + power"], "gry")
s.wire([(190, 675), (368, 640)], "mcu")

# Right column below: headers, LED ring, ESP32-side UI
s.box(760, 475, 200, 60, "Header J701 (2×12)", ["GPIO, UART0, I²C, XVF taps", "+5V, +3V3, +1V8 (low current)"], "gry")
s.wire([(612, 560), (690, 560), (690, 520), (758, 520)], "mcu")
s.box(760, 560, 200, 55, "WS2812B ring", ["12 × 2020, 5 V via buffer"], "ui")
s.wire([(612, 590), (758, 588)], "mcu")
s.box(760, 640, 200, 75, "ESP32 UI", ["user RGB LED (own buffer)", "mute LED · user button (side)",
                                       "BOOT + EN buttons"], "ui")
s.wire([(612, 630), (700, 630), (700, 677), (758, 677)], "mcu")
s.save(f"{OUT}/01_block_diagram.svg")

# ---------------------------------------------------------------- 02 power tree
s = Svg(1040, 800, "MindSpeak rev 1 power tree and start-up order",
        "Two USB-C inputs (main and ESP32 port) feed a TPS2121 priority mux that makes the 5 V rail. 5 V "
        "feeds a 0.9 V buck, a 3.3 V buck, two load switches and the user RGB LED. The 3.3 V buck feeds "
        "the ESP32-S3 module and the 1.8 V LDO. A TPS3808 supervisor watching 3.3 V holds RST_N low until "
        "3.3 V is valid.")
s.text(30, 28, "MindSpeak rev 1: power tree", "h1")
s.text(30, 52, "Updated 2026-11-10: ESP32-S3 helper replaces the RP2350A, so the 1.1 V rail is gone and the "
       "3.3 V load grows.", "s")

s.box(30, 90, 190, 70, "USB-C main", ["TYPE-C-31-M-12", "SMF5.0A TVS, Rd 5.1 kΩ"], "gry")
s.box(30, 190, 190, 70, "USB-C ESP32", ["TYPE-C-31-M-12", "SMF5.0A TVS, Rd 5.1 kΩ"], "gry")
s.box(260, 120, 170, 110, "Power mux", ["TI TPS2121", "IN1 = main (priority)", "IN2 = ESP32 port",
                                        "ST → ESP32 GPIO18"], "pwr")
s.wire([(220, 125), (240, 125), (240, 150), (258, 150)], "pwr", label="VBUS_MAIN", lpos=(240, 112))
s.wire([(220, 225), (240, 225), (240, 200), (258, 200)], "pwr", label="VBUS_ESP", lpos=(240, 238))
# 5 V bus
s.wire([(430, 175), (460, 175)], "pwr", arrow=False)
s.add('<path class="wire pwr" d="M460 110 L460 745"/>')
s.text(460, 760, "5 V rail", "t", "middle")
s.text(460, 777, "≈0.6 A typ, 2.4 A peak", "xs", "middle")

reg_x, reg_w = 490, 220
load_x, load_w = 750, 270
rows = [
    (85, "0.9 V buck", ["TI TLV62569 + SRP4020TA-2R2M"], "pwr",
     "VDD 0.9 V", ["XVF core: 4,12,19,27,34,42,49,57,61–64", "PLL_AVDD 22 via ferrite + 1 µF"], "xvf"),
    (180, "3.3 V buck", ["TI TLV62569 + SRP4020TA-2R2M", "≈0.25 A typ, ≈0.6 A peak"], "pwr",
     "3.3 V", ["XVF VDDIOL/R/T 8,38,52 · USB_VDD33 30", "ESP32-S3 module (Wi-Fi TX ≈0.36 A peak)",
               "W25Q32 · 4 flash switches · mic clock buffer", "mics via ferrite · J701 pins 2, 24"], "xvf"),
    (310, "1.8 V LDO", ["TI TLV75518P, fed from 3.3 V"], "pwr",
     "1.8 V", ["XVF VDDIOB18 17,26 · USB_VDD18 31", "RST_N pull-up 10 kΩ · J701 pin 3"], "xvf"),
    (420, "Reset supervisor", ["TI TPS3808G33, senses 3.3 V", "open drain, trip 3.07 V, 20 ms"], "prg",
     "RST_N (pin 21)", ["wired-OR: TPS3808 · reset button (MR)", "ESP32 2N7002 Q701 (0 Ω link) · XTAG"], "prg"),
    (530, "Amp load switch", ["TI TPS22918, soft start", "EN ← XVF pin 40"], "aud",
     "MAX98357A", ["own bulk capacitor", "4 Ω speaker, ≈1.4 A peak"], "aud"),
    (625, "LED load switch", ["TI TPS22918", "EN ← ESP32 GPIO47"], "ui",
     "WS2812B ring ×12", ["data via SN74AHCT1G125 on 5 V", "≈0.6 A full white"], "ui"),
]
for y, rt, rl, rk, lt, ll, lk in rows:
    h = 70 if len(ll) < 3 else 15 * len(ll) + 40
    s.box(reg_x, y, reg_w, h, rt, rl, rk)
    s.box(load_x, y, load_w, h, lt, ll, lk)
    s.wire([(reg_x + reg_w, y + h / 2), (load_x - 2, y + h / 2)], "pwr")
    if rt not in ("1.8 V LDO", "Reset supervisor"):
        s.wire([(460, y + h / 2), (reg_x - 2, y + h / 2)], "pwr")
# Always-on 5 V loads straight off the rail (no switch)
s.box(load_x, 715, load_w, 55, "Always-on 5 V", ["user RGB LED + its SN74AHCT1G125", "J701 pins 1, 23 (low current)"], "ui")
s.wire([(460, 742), (load_x - 2, 742)], "pwr")
# 3.3 V buck feeds 1.8 V LDO; supervisor watches 3.3 V
s.wire([(600, 280), (600, 308)], "pwr", label="3.3 V", lpos=(625, 294))
s.wire([(560, 280), (560, 295), (475, 295), (475, 455), (488, 455)], "dash")

s.note(30, 300, 415, [
    "1. A cable is plugged in; the TPS2121 passes 5 V (main port wins).",
    "2. The 0.9 V and 3.3 V bucks soft-start from 5 V together.",
    "3. The 1.8 V LDO follows 3.3 V, so it can never come up first.",
    "4. TPS3808 holds RST_N low until 3.3 V > 3.07 V, then 20 ms more.",
    "5. XVF3800 boots from its QSPI flash (boot pins all low).",
    "6. After boot: host enables the amp (pin 40);",
    "    ESP32 switches on the LED ring (GPIO47).",
], "Start-up order")
s.note(30, 470, 415, [
    "Main USB-C should be a 5 V / 3 A supply for full volume + LEDs.",
    "On the ESP32 port alone (PC port, 0.5–0.9 A) the ESP32 reads",
    "TPS2121 ST and keeps the LED ring dim; the amp may brown out.",
    "Bucks: TLV62569 is 2 A; 0.9 V core worst case is 1 A,",
    "3.3 V peak ≈0.6 A with ESP32 Wi-Fi transmitting.",
    "J701 exposes +5V, +3V3, +1V8 for low-current use only.",
], "Budget notes")
s.save(f"{OUT}/02_power_tree.svg")
print("ok")
