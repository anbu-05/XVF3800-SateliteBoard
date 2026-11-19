# Escape analysis, XVF3800 (U301) and ESP32-S3 (U601), 2026-11-18

Made with `tools/escape_map.py REF OUTDIR` from the board as it was after the power planes
(placement unchanged since 2026-11-17). Everything is seen from the top, as KiCad shows it by
default; the XVF3800 is on the bottom side, so it looks mirrored compared with its datasheet.

- `U301-escape.png`, `U601-escape.png`: left, the chip with each pin coloured by the side its
  trace has to leave from (N/E/S/W), local fan-out, power, GND, NC; a red label means the
  destination is not on the pin's own side, so the trace has to wrap round the chip. Right, the
  whole board with a line from each pin to its destinations (dashed: other side of the board;
  grey: test pads, which can be moved).
- `U301-escape.md`, `U601-escape.md`: the same as tables, with every destination and distance.

## Reduced maps: length-sensitive signals to a board edge

`U301-escape-edge.png/.md` and `U601-escape-edge.png/.md` (`tools/escape_map.py REF OUTDIR --edge-sensitive`)
keep only the nets in the script's `SENSITIVE` list, and of their destinations only parts whose
courtyard comes within 8 mm of the board edge. Test pads are left out (they can be moved).

- XVF3800 (12): USB D± (pins 28/29) → J101, east; JTAG TCK/TMS/TDO/TDI (24/23/20/18) → J301,
  north; MIC_DATA0 (46) → R506, east; MIC_DATA1 (50) → R507, north; MIC_DATA2 (48) → R508,
  west; MIC_DATA3 (51) → R509, south; I2S_DATA1 (39) and I2S_DATA2 (53) → J701, south. All
  change layer; every one except MIC_DATA1 leaves a different side from the one its pin is on.
- ESP32 (2): USB D± (pins 13/14) → R605/R606 → J102, west (the pins sit on the south row).
- Not in the list (judged not length-sensitive here): I2C, buttons, LEDs, enables, reset,
  INT_N/GPO, UART, the ESP32 GPIOs on J701. QSPI, crystal and mic clock are timing-sensitive but
  stay local (flash, crystal, U501), so they have no board-edge destination.

## Rotated trial (2026-11-18)

`rotated-trial/`: the same maps for a scratch copy with U301, C301–C319, FB301 and the U501/C501/R501
group turned 90° CCW about the chip centre (seen from the top), nothing else moved. Wrap-arounds:
all signals 31 → 27, edge length-sensitive 11 → 8 of 12. USB D±, I2S to the amp, I2C and
I2S_DATA1 then leave straight towards their destinations. New wraps: QSPI pins move to the north and west edges (flash is NE),
crystal pins to the NE corner (crystal is ESE), JTAG to the east edge (J301 is north).
Clashes if nothing else moves: C314 with R301/R302, C318 with U401.

## Why this matters

The XVF3800 sits directly under the ESP32 module. In1 and In2 are planes, and on the top layer
the module's pad rows are too tight to pass a track between (0.37 mm gaps vs 0.15 mm clearance).
So inside the module's shadow the XVF3800's signals can only leave on B.Cu, through the gaps
in its decoupling-cap rows. The module footprint has no keepout, and its west (antenna) edge has
no pads, so F.Cu under the module is usable but only opens to the west.

## XVF3800 (pin roles fixed by the XMOS firmware)

- 37 far signals; all but the flash/crystal/mic-clock fan-out end on the top side (layer change).
- North-bound (19): JTAG TCK/TMS/TDO/TDI to J301 (pins on the south edge, so they wrap);
  I2S DATA0/LRCK/BCLK to the amp U503 (pins on the east edge); AMP_EN to U502 (west edge);
  MIC_DATA1; and the test-pad-only nets (XLINK 33/35/36/37, SPI CS/MOSI/MISO, SQ_nLIN, MCLK).
- East-bound (10): QSPI D0/D1/CS/CLK to the flash switches U701–U704 (plus U401 locally);
  USB D± to J101 (pins on the south edge); MUTE button; ACTION button (pin on the west edge);
  MIC_DATA0; RST_N (also goes north to J301 and west to U302/R303).
- South-bound (8): I2C SCL/SDA and I2S_DATA1 to J701 (west edge); I2S_DATA2 and INT_N to J701
  and the ESP32 (north edge); GPO_R/GPO_G to the ESP32 (pins 8/9) and the status LED (north
  edge); MIC_DATA3.
- West-bound (1): MIC_DATA2.
- Local (5): QSPI D2/D3 to the flash, crystal XIN/XOUT, MIC_CLK to its buffer U501.
- Worst crossings: GPO_R, GPO_G and INT_N leave the XVF3800's north edge but end on the ESP32's
  south pad row, right on top of it; JTAG and USB leave the south edge but go north / east.

## ESP32-S3 (GPIO matrix: most roles can be moved in the schematic)

- Top side, so its escapes are ordinary F.Cu fan-out out of its three pad rows.
- Six north-row pins go to J701 at the bottom of the board and wrap round the module:
  GPIO1, GPIO2, UART TX/RX (pins 37/36), I2C SDA/SCL (pins 31/32, pull-ups R704/R705 next to them).
- South-row pins 8/9/10 (GPIO15/16/17: XVF GPO_R/G and INT_N) go to the XVF3800's north edge on
  the bottom side, under the module.
- West-bound: EN (pin 3), BOOT (pin 27), USB D± (pins 13/14 via R605/R606 to J102).
- East-bound: LED_EN, MUX_ST, PRG_EN, mute LED, user button; local: the four flash-switch lines,
  PRG_RST, LED_DATA, USER_LED_DATA.
- Pins with fixed roles: EN, BOOT (GPIO0), USB (GPIO19/20), UART0 (GPIO43/44, only if UART0 stays
  the console; USB-Serial-JTAG can take that role). J701's GPIO1–9 were picked as ADC1 pins.

## Open (for discussion, nothing changed)

1. LDO U203 to the bottom, next to the XVF3800.
2. Joining XVF3800 +1V8 pins 26/17 (C316; C315/C318).
3. Escape plan: wider gaps in the XVF3800 cap rows for signal tracks, vias out of the module
   shadow (or F.Cu under the module, out to the west), and possibly reassigning ESP32 GPIOs so
   fewer signals wrap.
