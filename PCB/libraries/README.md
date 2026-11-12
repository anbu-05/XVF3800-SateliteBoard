# Mindspark rev 1 libraries

Prepared 2026-11-07, part set updated 2026-11-12. Used by `../mindspark_rev1/` through its
project library tables (`${KIPRJMOD}/../libraries/...`). Nothing is registered in the global
KiCad tables, and every symbol and footprint the schematic uses lives here.

| Path | What it is |
|---|---|
| `symbols/Mindspark.kicad_sym` | 50 symbols: XVF3800, mic, load switch and RGB LED from easyeda2kicad, TPS2121 from TI/Ultra Librarian, stock copies with footprint + LCSC number (incl. ESP32-S3-WROOM-1U, MAX98357A TQFN, TS5A3166 SOT-23-5, SN74LVC1G125, TS24CA, MSK12C02), generic stock copies (R, C, LED, LED_RGB, test point, mounting hole, headers incl. 2x12) and power symbols (renamed rails: +0V9, VBUS_MAIN, VBUS_ESP, +5V_AMP, +5V_LED, +3V3_MIC) |
| `footprints/Mindspark.pretty` | 36 footprints: custom/fixed ones plus verbatim copies of every stock footprint used |
| `3dmodels/` | STEP models for footprints whose model the stock install lacks (paths use `${KIPRJMOD}/../libraries/3dmodels`) |
| `incoming/easyeda/`, `incoming/easyeda_models/` | Raw easyeda2kicad output, never edited |
| `incoming/easyeda_check/` | easyeda2kicad output used only to cross-check TPS2121 and W25Q32JVUUIQ |
| `incoming/espressif/` | Espressif ESP32-S3-WROOM-1U footprint + STEP from Espressif's KiCad library (plugin-manager install), never edited |
| `incoming/ti_tps2121/` | TI/Ultra Librarian TPS2121RUXR download (zip + unpacked), never edited |
| `datasheets/` | PDFs used for the checks |
| `parts-map.json` | Every rev 1 part: MPN, LCSC number, symbol, footprint, and where each came from |
| `sources.json` | Download URLs, datasheet revisions, SHA256 of every raw file |
| `tools/build_libraries.py` | Rebuilds `symbols/`, `footprints/` and `3dmodels/` from `incoming/` and the stock libraries; fails if any symbol pin has no pad |
| `tools/model_align/` | Solves 3D model offsets from bounding boxes (see below) |
| `verification/` | Symbol/footprint SVGs and 3D renders; `footprints-2026-11-10/` holds the new footprints |

## Rebuild

```bash
cd PCB/libraries
python3 -I tools/build_libraries.py
kicad-cli sym upgrade symbols/Mindspark.kicad_sym
kicad-cli fp upgrade footprints/Mindspark.pretty
```

The script clears `footprints/` and `3dmodels/` and writes them again, so dropped parts
disappear. To import another LCSC part: `easyeda2kicad --full --lcsc_id Cxxxx --output
incoming/easyeda/easyeda_raw` (installed in `~/.local/venvs/easyeda2kicad`), then add it to
`SYMBOLS` in the build script with a datasheet-checked pin map.

## Source rule (decided 2026-11-10)

KiCad 10 built-in first, then easyeda2kicad, then vendor CAD only where it matters. Stock
symbols that use `extends` are flattened into a stand-alone copy. Every part was compared pin
by pin with its datasheet.

## What was checked, and what was changed

- **XVF3800**: 65 pins is correct. The package has 5 paddles: 61–64 are VDD (0.9 V), 65 is GND.
  Pins are named `SIGNAL/PORT` (e.g. `MIC_CLK/X0D36`) from the XMOS pinout table. The
  stock KiCad QFN-60 has one paddle and **must not be used**. The EasyEDA footprint matches
  XU316 section 15. Paste on the paddles reduced by 15 % per side.
- **ESP32-S3-WROOM-1U-N16R8**: stock `RF_Module:ESP32-S3-WROOM-1` symbol (same 41 pins as the
  1U) on the stock `ESP32-S3-WROOM-1U` footprint. Pin numbers match Espressif's module pin table
  (datasheet in `datasheets/`). Footprint (user's choice 2026-11-12): Espressif's own
  `ESP32-S3-WROOM-1U` from github.com/espressif/kicad-libraries (raw copy and STEP in
  `incoming/espressif/`), same 41 pads as the stock one, copper unchanged, Espressif's STEP with
  its own offset. It replaces the stock copy under the same name.
- **SN74LVC1G125DBVR** (MIC_CLK buffer): stock `74LVC1G125`, SOT-23-5, TI pin table.
- **TPS2121RUXR**: TI/Ultra Librarian files. Pads equal TI's land pattern (SLVSEA3F p.39:
  8 × 0.2 × 0.6 mm, 4 × 0.4 × 1.05 mm, 2.3 / 1.35 mm spans) and EasyEDA C485916 (same pads,
  rotated 90°). Changed: the four 0.2 mm via-in-pad holes were removed (they would need the
  fab's filled-via option; put thermal vias next to the pads instead), mask polygons replaced
  by a 0.05 mm NSMD opening per pad, hidden via pins dropped from the symbol. ST is open drain
  (needs a 6–20 kΩ pull-up).
- **TS5A3166DBVR** (2026-11-12, replaces the DSBGA TS5A3166YZPR): stock
  `Analog_Switch:TS5A3166DBVR` on the stock SOT-23-5. Pin numbers match TI SCDS188D, DBV column
  (1 NO, 2 COM, 3 GND, 4 IN, 5 V+); pins 1, 2 and 4 were unnamed in the stock symbol and are
  named here. Off-state capacitance is 18–19 pF per side and IN's high threshold is 2.0 V at 3.3 V.
- **W25Q32JVUUIQ**: stock `W25Q32JVZP` symbol (same 8-pin numbering) on the stock Winbond
  USON-8-2EP 3×4 mm footprint, which matches Winbond's UU drawing (b 0.30, e 0.80, two
  0.2 × 0.8 centre pads). Winbond: the centre pad has no internal connection; leave it
  floating, no vias under it.
- **TPS3808G33**: stock symbol; RESET retyped open-collector (it is wired-OR with the
  ESP32's 2N7002 and the XTAG).
- **TLV62569DBV, TLV75518PDBV, TPD4E05U06DQA, SN74AHCT1G125**: stock pin numbers match each
  TI pin table. TPD4E05U06 pins 6, 7, 9, 10 are NC (straight-through routing).
- **SMF5.0A**: unidirectional TVS. The stock `D_TVS` is bidirectional (A1/A2), so the Zener
  graphic is used: pin 1 K = D_SMF pad 1 (cathode).
- **MAX98357AETE+T** (2026-11-12, replaces the WLP-9 MAX98357AEWL+T): stock `Audio:MAX98357A`,
  whose numbers match ADI's TQFN column (p.15): 1 DIN, 2 GAIN_SLOT, 3/11/15 GND, 4 SD_MODE,
  5/6/12/13 N.C., 7/8 VDD, 9 OUTP, 10 OUTN, 14 LRCLK, 16 BCLK. ADI: the EP has no internal
  connection and goes to a solid ground plane, so pin 17 is renamed GND and hidden in the GND
  stack. Stock `TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm` copper fits ADI's T1633-4 drawing
  (21-0136: EP 0.95–1.25 mm, leads 0.20–0.30 × 0.30–0.50 mm, 0.5 mm pitch). Its EP1.23 STEP is not
  installed, so the stock EP1.6 TQFN-16 model (same 3 × 3 × 0.75 mm body) is attached.
- **IM69D129FV01 mic**: footprint redrawn from Infineon Figure 14; EasyEDA's was ST's
  MP23ABS1 land pattern. 3D model: stock InvenSense ICS-43434 (same body).
- **TPS22918**: EasyEDA, checked against the TI pin table.
- **Speaker connector, JST S2B-PH-SM4-TB** (C295747) and **JTAG header, JST S7B-PH-SM4-TB**
  (C265453, 1.8 V xSYS2 JTAG-only signals): stock copper, verified STEP models. Parallel
  solder pads: `TestPoint_THTPad_2.0x2.0mm_Drill1.0mm` and `TestPoint_Pad_1.5x1.5mm`.
- **Bourns SRP4020TA-2R2M** (both bucks): EasyEDA footprint matches Bourns' layout exactly.
- **RGB status LED, TOGIALED TJ-S1615CY6TGLCCSRGB-A5** (C601684, common cathode): EasyEDA
  symbol pins match the datasheet (1 K, 2 blue, 3 green, 4 red anode). The footprint is drawn
  from the datasheet's recommended layout (0.85 × 0.5 mm pads, 0.9 mm column gap); EasyEDA's
  pads were 1.1 × 0.6 mm. No 3D model yet.
- **Symbol compaction (kicad-schematic-tidy Step 0, 2026-11-10, Mindspark library only):**
  `COMPACT` in the build script redraws five EasyEDA outlines. Pin numbers, names, electrical
  types and drawn lengths are unchanged; only positions and the body move.
  - IM69D129 mic: body 1100 × 400 → 500 × 300 mil; DATA/CLK left, VDD/SELECT/GND right.
  - TPS22918: body 800 × 400 → 500 × 400 mil; VIN/ON left, VOUT/QOD/CT right, GND below.
  - MAX98357A (TQFN, 2026-11-12): body 1000 × 600 mil; inputs left, VDD/OUTP/OUTN/GND right,
    pin tips where the WLP symbol had them; the hidden N.C. pins sit apart inside the body.
  - TS5A3166 (DBV, 2026-11-12, same layout as the YZP symbol): 500 × 400 mil body: COM/IN left, NO right, V+ above, GND below.
  - XVF3800: body widened 1200 → 1800 mil with every pin row and order kept, because the
    long SIGNAL/PORT names on the two sides overlapped in the middle.
  - TPS2121 (review change, 2026-11-10): body 800 × 1300 mil, IN1 + PR1/OV1 left, IN2 + CP2/OV2
    right (OV pins 800 mil below PR1/CP2), OUT/ST on top, SS/ILIM/GND below, so every divider,
    the ILIM resistor, the SS cap and the ST pull-up are wired straight to their pins.
- **PLL_AVDD power symbol** (2026-11-10): the XVF3800's filtered PLL supply is drawn as a rail,
  so its ferrite and 1 µF cap read as a rail filter.
- **Side switches (2026-11-11)**: JLC has no side-pressed tact switch in Basic (only two
  Basic tact switches exist, both top-pressed), so these are Extended. Both from easyeda2kicad,
  copper unchanged, checked against the SHOU HAN drawings in `datasheets/`; STEP models attached
  at zero offset and not yet aligned.
  - **SHOU HAN TS24CA** (C393942), mute/action/user: contacts 1/2 are 0.6 × 1.2 mm, 3.4 mm
    apart; pads 3/4 are the L-shaped hold-down tabs (5.3 mm outside, 4.0/3.2 mm inside, no net);
    two 0.7 mm locating holes 1.7 mm apart. Actuator towards −Y.
  - **SHOU HAN MSK12C02** (C431540), PROG switch: stock `SW_SPDT` symbol (pin 2 = common). Pins
    3, 2, 1 with 1.5 mm then 3 mm spacing, as drawn; four shell tabs are pad 4 (no net); two
    0.9 mm locating holes 3 mm apart. Lever towards +Y.
  - **2x12 SMD header J701** (HCTL PZ254-2-12-S, C3294470): stock
    `PinHeader_2x12_P2.54mm_Vertical_SMD` (silk, courtyard, 3D model) with the pads changed to
    HCTL's recommended layout: 1.02 × 3.12 mm, 2.26 mm between rows, 8.5 mm overall (centres
    ±2.69 mm). KiCad's generic pads were at ±2.525 mm, EasyEDA's at ±2.80 mm. No locating posts
    on the `-S` part. Named `PinHeader_2x12_P2.54mm_Vertical_SMD_HCTL_PZ254`.
  - Mounting holes H1–H4: stock `MountingHole_2.2mm_M2_Pad_Via` (M2, chosen by the user in KiCad
    2026-11-11; replaces `MountingHole_3.2mm_M3`).
- **Removed 2026-11-12**: no ball-grid parts: MAX98357AEWL+T (WLP-9 footprint and STEP) and
  TS5A3166YZPR (DSBGA-5 footprint and STEP).
- **Removed 2026-11-11**: 1x6 host header, PROG jumper (`Jumper_2_Open`) and the 1x02/1x06/2x10
  header footprints; the through-hole 2x12 header (HanElectricity C5383110) was replaced the
  same day by the SMD one.
- **Removed 2026-11-10 (ESP32 swap)**: RP2350A, AOTA-B201610 inductor, ABM8-272-T3 crystal, 1x3 and 1x10 headers, +1V1 rail; VBUS_RP renamed VBUS_ESP.
- **Removed 2026-11-10**: TLV320AIC3104, LM48511, IHLP2525CZER6R8M01, DFLS230LH-7, PJ-327A jack
  (and footprint/model), W25Q32JVSNIQ (SOIC-8). Their datasheets stay in `datasheets/`.

## How 3D models were placed

EasyEDA's `.wrl` files are placed correctly on EasyEDA's own footprints, but its `.step`
files often are not. `tools/model_align/` matches pads between the EasyEDA footprint and the
target footprint to find the rotation and shift, exports the STEP with `kicad-cli pcb export
glb`, and solves the offset so the STEP's bounding box equals the WRL's. The new 2026-11-10
models (TS5A3166, TPS2121) are attached at zero offset and still need that check
before layout.

## Still open

- Generic parts (R, C, LEDs, headers, jumper, 2N7002) get their LCSC number per placed
  instance in the schematic.
- Before ordering: check the 0.4 mm-pitch QFN-60, the VQFN-HR, the USON-10 and the TQFN-16
  against the fab's rules.
