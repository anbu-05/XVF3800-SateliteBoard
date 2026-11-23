# MindSpeak Voice Satellite rev1: JLCPCB order package

Made 2026-11-23 by `tools/jlc_export_2026_11_23.py` from the committed board (DRC 0 violations,
0 unconnected, parity 0; ERC 0/0; reports in `checks/`). Re-run that script after any change;
it rebuilds everything here except this README.

**Stock:** the out-of-stock mics and XVF flash were replaced 2026-11-23 (see "Part replacements");
every BOM line is in stock at LCSC or on JLC's own shelf.

## What to upload

| JLC step | File |
|---|---|
| PCB (Gerber) | `JLCPCB_rev1_gerbers.zip`: 11 Gerbers (F/B.Cu, In1/In2, paste, silk, mask, outline), job file, PTH and NPTH drill |
| Assembly: BOM | `assembly/mindspark_rev1_BOM_JLC.csv` (55 lines, one per LCSC part) |
| Assembly: CPL | `assembly/mindspark_rev1_CPL_JLC.csv` (204 parts: 144 top, 60 bottom) |

Not assembled on purpose: H1-H4 (mounting holes), all test pads (TP2xx/3xx/4xx round pads,
TP501/TP502 square pads). Rotations were checked 2026-11-23 against the user's JLC preview and
JLC's own footprints (pad by pad, with JLC's pin names); 43 rotation fixes are in `ROT_FIX` and origin offsets (USB-C 1.57 mm, ESP32 0.63 mm, mics, J301, J501) in `POS_FIX` in the
export script, so a re-export keeps them. JLC turns bottom parts the opposite way, so the ring
LEDs and caps carry per-part fixes. Re-upload the CPL and look again at the preview.

## Order options

| Option | Choice | Why |
|---|---|---|
| Layers / size | 4 layers, 74 x 74 mm | |
| Quantity | 5 boards, assemble 2 (user 2026-11-23) | |
| Thickness / stackup | 1.6 mm, **JLC04161H-7628** | the board's stackup and the USB impedance below assume it |
| Copper | 1 oz outer, 0.5 oz inner | |
| Via covering | **epoxy-filled and capped (via-in-pad)** | vias sit in pads (power pads, switch pins, XVF paddles); plain tented vias would wick solder |
| Min via | 0.45 / 0.2 mm (544 holes of 0.2 mm) | |
| Surface finish | ENIG | 0.4 mm QFN-60 and USON/VQFN parts; JLC pairs via-in-pad with ENIG |
| Order number | **specify a location** | "JLCJLCJLCJLC" sits on the table side next to the S/N box |
| Assembly | both sides | 144 parts top, 60 bottom (XVF3800, ring LEDs, mics' neighbours) |
| Remove order number | no | |

## Checks done

- **USB pair impedance** (XVF main USB, 0.25 mm lines, 0.15 mm gap, outer layer over GND, JLC04161H-7628):
  **92.6 ohm differential** from a 2D field solve (`tools/usb_impedance_2026_11_23.py`; the GND
  pour 0.5 mm away changes it by 0.2 ohm). USB 2.0 asks 90 ohm +-15 % (76.5-103.5), so the routing
  stays. JLC's online calculator could not be driven from here; the solver's 50 ohm single line
  comes out at 0.35 mm, in line with JLC's published width for this stackup.
- **Drill:** 690 plated holes (vias 0.2/0.3/0.4 mm, USB shell slots, M2 holes) and 16
  non-plated (mic ports 0.6, USB pegs 0.65, switch pegs 0.7/0.9); `checks/drill-report.txt`.
- **Stock** (LCSC API and JLC's parts search, 2 boards): `../../bom/stock-2026-11-23.md`, nothing
  flagged. Parts about $107 for 2 boards ($94 at LCSC prices plus the mics at JLC's price), before
  JLC's assembly and extended-part fees.

## Part replacements (done 2026-11-23)

Both out-of-stock parts were replaced by in-stock parts that fit the same footprint
(`tools/part_swap_2026_11_23.py`; reasons in its header).

| Refs | Was | Now | JLC stock (need for 2 boards) | Datasheet |
|---|---|---|---|---|
| MK501-504 | Infineon IM69D129FV01XTMA1 | Knowles **SPH0641LM4H-1** [C497724](https://jlcpcb.com/partdetail/C497724) | 5819 (8) | `PCB/libraries/datasheets/SPH0641LM4H-1_C497724.pdf` p.8 |
| U401 | Winbond W25Q32JVUUIQ (32 Mbit) | GigaDevice **GD25Q16ENIGR** (16 Mbit = 2 MB) [C5749719](https://jlcpcb.com/partdetail/C5749719) | 2168 (2) | `PCB/libraries/datasheets/GD25Q16E.pdf` p.54 |
| R407 (new) | - | 4.7k 0402 [C25900](https://www.lcsc.com/product-detail/C25900.html), same part as R401 | Basic part | - |

- **Mic:** same pinout, pads and sound port as the IM69D129 (Knowles p.8 matches Infineon p.12
  Fig. 13 number for number). Normal mode runs 1.0-4.8 MHz, so the XVF's 3.072 MHz mic clock is
  fine. It is 10 dB more sensitive (-26 vs -36 dBFS) and SNR is 64.3 vs 69 dB (accepted for rev1);
  the XVF mic gain may want turning down. Not on LCSC; JLC sells it from its own shelf (about
  $1.68 each at 1-9).
- **Mic footprint bug fixed (affected any mic):** the old footprint had the two pad rows 0.838 mm
  apart; both datasheets give 1.675 mm (the "0.838" in Infineon Fig. 14 is centre line to a row).
  New footprint `Knowles_SPH0641LM4H-1_LGA-5_3.5x2.65mm`, full 0.54 x 0.75 pads; the frozen DATA
  and CLK routes are re-ended on the new pad centres (`tools/mic_pads_2026_11_23.py`).
- **Flash:** same USON-8 3 x 4 mm package, pins and two 0.2 x 0.8 centre pads. 2 MB is the
  XVF3800's stated minimum flash (its example part is also 16 Mbit). Its Quad Enable bit ships
  at 0: the XTAG4 path (xflash) sets it; the ESP32 path must set it before writing the image.
- **R407** pulls D3 (flash HOLD#) up so the flash runs while the XVF is held in reset (the XVF
  pulls all its pins low in reset). D2 (WP#) gets no pull-up on purpose: it is an XVF boot-mode
  pin. Bottom side, between the MIC_DATA0 line and U401 (`tools/flash_pullup_2026_11_23.py`).

## Final review (2026-11-23)

| Item | Finding | Action |
|---|---|---|
| DRC / ERC / parity | 0 / 0 / 0 | none |
| USB impedance | 92.6 ohm, in spec | none |
| OV trip 5.57 V (TPS2121 OV1/OV2 51k/12k, threshold about 1.06 V) | above USB 2.0's 5.25 V max and USB-C's 5.5 V vSafe5V max typ; with a low-side threshold tolerance it could trip near 5.46 V on a charger sitting at 5.5 V | optional: 51k -> 56k gives about 6.0 V; real chargers sit at 5.0-5.2 V, so leaving it is a small risk |
| Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) | DRC runs JLC's limits (0.1 mm track/space, 0.45/0.2 vias) and passes; all within JLC assembly capability | confirm in JLC's DFM after upload |
| Top-side LEDs D401, D402, D201 face the table | visible only from the table side in the product; sky labels mark where they are | user decision: leave, or move to the bottom (re-route) |
| TS5A3166 off-capacitance on QSPI (18-19 pF per line) | can't settle without a board; R706-R709 0 ohm links can cut the switches off | verify on the first board |
| TS24CA stem protrusion 0.31 mm | mechanical, depends on the enclosure | check with the enclosure |
| Stock XVF firmware I2C master / GPO polarity, XTAG4 at 1.8 V, ESP-written flash boot | firmware / bring-up questions | verify on the first board |
| Mics, flash | replaced 2026-11-23 (above); re-exported, stock rechecked | rotations fixed in `ROT_FIX` (mics +90); after re-upload check the preview again, U401 now +90 |
| Mic sensitivity -26 dBFS (was -36) | 10 dB hotter into the XVF's stock tuning | check levels on the first board; lower the XVF mic gain if it clips |
| Flash QE bit ships at 0 | XVF boot needs quad mode | XTAG4 path: xflash sets it. ESP32 path: the ESP32 must set QE (status register bit 9) before writing |
