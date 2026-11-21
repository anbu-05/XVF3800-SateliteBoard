"""Shift the ESP32's flash-programming pins (user, 2026-11-22).

The four PRG lines leave ESP32 pins 18-21 (GPIO10-13) on the east side of the module and run to
the flash switches west of it (tools/prog_switch_route_2026_11_22.py). With the old order the line
for the top switch (PRG_CS_N) came out at the bottom and had to loop round the others. New order,
so the lines leave in the order of the switch column (top to bottom CS_N, DO, CLK, DI):

    pin 21  GPIO13  PRG_CS_N   (was PRG_DO)
    pin 20  GPIO12  PRG_DO     (was PRG_CLK)
    pin 19  GPIO11  PRG_CLK    (was PRG_DI)
    pin 18  GPIO10  PRG_DI     (was PRG_CS_N)

SPI2 now goes through the GPIO matrix instead of its IOMUX pins; fine at flash-programming speed.
Edits esp32.kicad_sch (the four hierarchical labels and the GPIO note) and the board's pad nets for
U601 pads 18-21.

Usage (schematic and PCB editors closed):  python3 tools/sch_prog_pins_2026_11_22.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD, Part  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

HERE = os.path.join(os.path.dirname(__file__), "..")
SHEET = os.path.join(HERE, "esp32.kicad_sch")
BY_Y = {68.58: "PRG_DI", 71.12: "PRG_CLK", 73.66: "PRG_DO", 76.2: "PRG_CS_N"}   # GPIO10..13 rows
OLD = {68.58: "PRG_CS_N", 71.12: "PRG_DI", 73.66: "PRG_CLK", 76.2: "PRG_DO"}
PADS = {"18": "/PRG_DI", "19": "/PRG_CLK", "20": "/PRG_DO", "21": "/PRG_CS_N"}
NOTE_OLD = "10-13 SPI2 to the XVF flash (CS, MOSI=DI, CLK, MISO=DO)"
NOTE_NEW = "10-13 SPI2 (GPIO matrix) to the XVF flash (10 MOSI=DI, 11 CLK, 12 MISO=DO, 13 CS)"

s = parse(open(SHEET).read())
done = 0
for h in children(s, "hierarchical_label"):
    at = child(h, "at")
    y = round(float(at[2]), 2)
    if abs(float(at[1]) - 31.75) < 0.01 and y in BY_Y:
        if str(h[1]) != OLD[y]:
            sys.exit(f"label at y {y} is {h[1]}, expected {OLD[y]}: nothing done")
        h[1] = q(BY_Y[y])
        done += 1
if done != 4:
    sys.exit(f"found {done} of 4 labels: nothing written")
for t in children(s, "text"):
    if NOTE_OLD in str(t[1]):
        t[1] = q(str(t[1]).replace(NOTE_OLD, NOTE_NEW))
open(SHEET, "w").write(dump(s) + "\n")
print("relabelled GPIO10-13:", ", ".join(BY_Y.values()))

b = parse(open(BOARD).read())
for f in children(b, "footprint"):
    if Part(f).ref == "U601":
        for pd in children(f, "pad"):
            if str(pd[1]) in PADS:
                child(pd, "net")[1] = q(PADS[str(pd[1])])
open(BOARD, "w").write(dump(b) + "\n")
print("U601 pads 18-21 renamed on the board")
