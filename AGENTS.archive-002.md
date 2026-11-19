<!-- agents-md archive 002 · word-for-word history · ≤10000 words -->
# AGENTS.md archive 002 (MindSpeak voice satellite)

## 2026-11-18: full AGENTS.md (v2) as it was before the v3 conversion


# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched).

## What this is

- **Name: the company is MindSpeak** (mindspeakai.org). "Mindspark" is a misnaming that remains in identifiers: the folder, `mindspark_rev1`, and the KiCad library nickname `Mindspark`. Those are left as they are; use MindSpeak in everything people read (diagrams, reports).
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (6 pages: decisions, schematic status, JLC cost; source HTML alongside, built with `~/.local/venvs/weasyprint/bin/weasyprint`).
- A USB voice front-end board built around the XMOS XVF3800, with an ESP32-S3 helper MCU. A Raspberry Pi CM5 host comes in rev 2.
- **Prototype, not yet a product.** Thin distributor stock is fine; bulk ordering is deferred to production. Do not flag low stock as a blocker.
- **Designed from datasheets, not copied from Seeed** (2026-11-09). XMOS's own XK-VOICE-SQ66 reference board is now the reference for mic wiring and pin roles (2026-11-10).
- Status 2026-11-12: **rev 1 schematic regenerated with no ball-grid parts** (TQFN-16 amp, 4 × SOT-23-5 switches), including the user's 02:28 KiCad edits (Espressif ESP32 footprint, 1.0 mm JTAG pads). Nine A4 sheets, ERC 0/0, netlist, tidy and floating checks pass; BOM 59 lines / 189 parts, LCSC on every line. No purchase and no vendor contact.
- Status 2026-11-18: **power planes drawn** after clearing all routing (`tools/clear_routing_2026_11_18.py`; old routing in b6417da). Next: plane vias and routing from scratch. ERC 0/0, parity clean.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, branch `main`. `.gitignore` leaves out KiCad backups, the audio clips and `incoming/` (XMOS licence).

## Diagrams (`docs/diagrams/`, updated 2026-11-10)

01 block diagram · 02 power tree + start-up order · 03 everything connected to the XVF3800 · 04 XVF3800 pin map · 05 audio-out flow · 06 mic wiring · 07 ESP32-S3 block · 08 XVF3800 programming paths. They show the ESP32-S3 swap, the corrected XVF pin roles and the XMOS-style mic clock. Sources in `docs/diagrams/src/`; regenerate with `python3 src/draw_1_2.py src .` (likewise `draw_3_4.py`, `draw_5_8.py`) from `docs/diagrams/`. Component values are in the schematic, not the diagrams.

## PCB folder (KiCad 10)

- `PCB/mindspark_rev1/`: the project. The schematic is **generated** by `tools/build_schematic.py`; see `tools/README.md`.
  - **The generator is retired** (the user saved hand edits at 20:45 on 2026-11-12). Edit the sheets in place: `tools/sch_tidy_2026_11_12.py` is the worked example (group moves on the 50 mil grid, box refits), and the record is in `verification/tidy-record.md`. Sheet backups are in `mindspark_rev1-backups/pre-sch-tidy-2026-11-12/`.
  - Libraries are registered **in the project only**, as `${KIPRJMOD}/../libraries/...`.
  - `verification/`: design manifest, netlist, ERC, tidy record and tidy exceptions; placement renders `placement-2026-11-12-top.png` / `-bot.png` (bottom mirrored).
  - `tools/place_tidy2.py` applies the placement below (`--out` writes a trial copy). KiCad's `pcbnew` Python segfaults here, so the board is edited as S-expressions via `tools/sexpr.py`. Board backups: `mindspark_rev1-backups/*.pre-tidy2-2026-11-12` (user's 22:37 save, with their trial tracks) and older `pre-*` files.
  - `bom/`: BOM CSV, JLC stock JSON, `sourcing-2026-11-10-esp32.md` (every line linked) `sourcing-2026-11-11.md` (side buttons, PROG switch, 2×12 SMD header) and `sourcing-2026-11-12.md` (TQFN amp, SOT-23-5 switches).
- `PCB/libraries/`: the `Mindspark` library, built by `tools/build_libraries.py`; details in `PCB/libraries/README.md`. Part → symbol → footprint → LCSC map: `parts-map.json`.
  - The project uses only this library (symbols, footprints and power symbols).
- `incoming/xk_voice_sq66/`: XMOS XK-VOICE-SQ66 design files (schematic PDF, Altium, gerbers, BOM, placement). XMOS design-file licence: use for PCBs that carry XMOS parts.
- easyeda2kicad 1.0.1 lives in `~/.local/venvs/easyeda2kicad` (linked in `~/.local/bin`).
- **Library sources (decided 2026-11-10): KiCad 10 built-in first, then easyeda2kicad, then vendor CAD only where it matters.** Built-in parts are copied into Mindspark with the LCSC number added, and every part was checked pin by pin.
  - easyeda2kicad: TPS22918 and the RGB LED.
  - Stock KiCad (2026-11-12): MAX98357AETE+T (`Audio:MAX98357A` on the stock TQFN-16 3×3 EP1.23, EP 17 tied to GND) and TS5A3166DBVR (`Analog_Switch:TS5A3166DBVR` on SOT-23-5).
  - Vendor CAD: TPS2121RUXR from TI/Ultra Librarian (zip in `incoming/ti_tps2121/`, recorded in `sources.json`). Its 0.2 mm in-pad vias were removed and each pad given an NSMD mask.
  - ESP32-S3-WROOM-1U: stock WROOM-1 symbol (same 41 pins, checked against Espressif's pin table) on Espressif's own `ESP32-S3-WROOM-1U` footprint and STEP (user's choice 2026-11-12, copied from Espressif's KiCad library into Mindspark; same 41 pads as the stock one).
- **Footprint notes.**
  - Use `Mindspark:XVF3800-QF60B-C` with its 5-paddle footprint, never the stock single-paddle QFN-60.
  - The mic footprint is redrawn from the Infineon datasheet; the RGB LED footprint from TOGIALED's recommended layout.
- Kept parts: speaker connector JST S2B-PH-SM4-TB ([C295747](https://www.lcsc.com/product-detail/C295747.html)); buck inductor Bourns SRP4020TA-2R2M ([C719179](https://www.lcsc.com/product-detail/C719179.html)); JTAG header JST S7B-PH-SM4-TB ([C265453](https://www.lcsc.com/product-detail/C265453.html), JTAG at **1.8 V**). Speaker and JTAG also get parallel solder pads.

## Schematic (rev 1, generated 2026-11-10)

- **Sheets** (all A4, refs numbered per sheet: R101, C301…):
  - root overview (blocks + 4 × M2 mounting holes, `MountingHole_2.2mm_M2_Pad_Via`, chosen by the user in KiCad 2026-11-11);
  - 1 `usb_power`: 2 × USB-C (main, ESP32), ESD, TVS, TPS2121;
  - 2 `regulators`;
  - 3 `xvf3800`: chip, decoupling, PLL filter, crystal, TPS3808, JTAG;
  - 4 `xvf3800_periph`: flash, buttons, mute + status LEDs, spare-pin pads and I²S taps;
  - 5 `audio`: mics, mic clock buffer + series resistors, amp load switch, MAX98357A, speaker;
  - 6 `esp32`: module, decoupling, EN/BOOT, USB series R, user button, user WS2812;
  - 7 `esp32_io`: flash switches, PROG slide switch SW701, Q701 reset, I²C pull-ups, 2×12 header J701;
  - 8 `led_ring`.
- **Conventions.**
  - Rails are global power symbols: +5V, +3V3, +1V8, +0V9, VBUS_MAIN, VBUS_ESP, +5V_AMP, +5V_LED, +3V3_MIC0–3 (one 600R ferrite + 10 µF + 1 µF per mic, user 2026-11-12).
  - Inter-sheet signals use hierarchical labels.
  - Programming-path nets are named `PRG_*` (CS_N, CLK, DI, DO, RST, EN).
  - Fields follow the controller board: LCSC, MPN, Manufacturer, spec, voltage, tolerance, power, use.
- **Tidy** (kicad-schematic-tidy): rules, exceptions and the A4 packing deviation are in `verification/tidy-record.md` and `tidy-exceptions.json`.
- **Values** (JLC Basic parts preferred; datasheet-specified values kept even when Extended):
  - **TPS2121 in XCOMP priority mode:**
    - PR1 = 22k/12k from VBUS_MAIN and CP2 = 22k/10k from VBUS_ESP, so it moves to the ESP32 port when main VBUS drops below ≈4.4 V.
    - OV1/OV2 = 51k/12k, tripping at 5.57 V.
    - ILIM = 33k, ≈3.2 A typ.
    - SS = 100 nF.
    - ST has a 10k pull-up to 3.3 V and goes to ESP32 GPIO18.
  - **Bucks** (L = 2.2 µH):
    - 0.9 V: FB 51k/100k (0.906 V), Cff 22 pF, output 2 × 22 µF.
    - 3.3 V: FB 100k/22k (3.327 V), Cff 15 pF, output 22 µF.
    - Cff is scaled to TI's 200k/6.8 pF example.
  - **LDO:** 1 µF in and out.
  - **XVF3800 crystal:** 22 pF ×2, Rf 1M, Rd 680R.
  - **ESP32-S3** (controller board + Espressif checklist): 22 µF + 100 nF at the module; EN 10k + 1 µF; GPIO0 10k pull-up; EN and BOOT buttons through 1k to GND; 27R USB series (Espressif: 22–33 Ω).
  - **Mic clock** (as XMOS XK-VOICE-SQ66): XVF pin 43 → SN74LVC1G125 (OE tied low, +3V3) → 100R → 100R into each mic CLK; 100R in each mic DATA line.
  - **MAX98357A:** SD_MODE 1M to VDD gives (L+R)/2; GAIN_SLOT open = 9 dB.
  - **TPS22918s:** CT 1 nF (≈2.5 ms rise); ON pull-downs 100k (amp) and 4.7k (LED switch).
  - **ESP32-driven enables:** PRG_EN and PRG_RST have 4.7k pull-downs (off while the ESP32 boots).
  - **LEDs:** mute LED 1k; status LED 1k (R) / 330R (G), blue anode open; power LED 2.2k from +5V. User WS2812 and ring data: 33R after the AHCT buffer.

## PCB placement (user's rules; second pass 2026-11-12 by `tools/place_tidy2.py`)

The first pass (`place_tidy.py`, 74 mm board, 4 layers, edge rules) is archived; the second pass works on the user's own rough placement (22:37 save) and is the one to rerun or adapt. Don't rerun `place_tidy.py`: it predates the user's moves.

- **Board:** 74 × 74 mm, centre (146.558, 98.679), 4 layers (In1 GND, In2 power), 0.3 mm copper-to-edge (JLC allows 0.2; kept as margin).
- **Design rules (2026-11-13, [JLC](https://jlcpcb.com/capabilities/pcb-capabilities) multilayer):** minimums track/clearance 0.1, via 0.45/0.2 (smallest free), holes 0.2. Default class 0.15/0.15; Power class (5 V rails, VBUS, SPK) 0.4 with 0.6/0.3 vias. USB pair 0.2/0.25 not impedance-sized yet.
- **Edges:**
  - USB-C origin 3.015 mm inside the left and right edges.
  - JST origin 5.67 mm inside the top edge. J501 is at x 135.0 (user's choice); TP501 (SPK+, right) and TP502 are symmetric about it, 4.13 mm off its axis, just under its courtyard.
  - Side parts have equal gaps per half-edge, from the hole line to the USB-C. Left: PROG, RESET / BOOT, EN, user LED. Right: MUTE, mute LED, ACTION / USER, status LED, power LED (D201 on the edge).
  - Each side part's resistors and caps sit in a column just inside it. The TPS3808 block sits beside RESET.
- **Mounting holes:** 12 mm in from both edges (user moved them in for the mic ferrites; 12 chosen).
- **Test pads:** two bottom-side rows, 1.5 mm in, spread between the hole pads.
- **Mics:**
  - Top side, ports on the 66 mm square, turned 45°.
  - MK501's corner is the template, in the mic's own frame: 1 µF, ferrite and 10 µF in a line inward on the mic axis, CLK and DATA 100R either side. The other three corners are 90° turns of it, which fixed the C503/C504 swap.
- **LED ring:** bottom side, radius **27.0 mm**, ≥ 0.47 mm from the USB-C outlines. Each 100 nF sits beside its LED on the inner side, GND pad by the LED's GND (all fitted inward).
- **Groups** (IC as anchor, 0.15 mm courtyard gaps, 0/90° within a group, each cap on the pin its `use` field names):
  - XVF3800 (bottom): one cap row per side, each cap on its own pin, 1.65 mm out for via fan-out (`tools/xvf_caps_out.py`). Bulk 10 µF behind a same-rail cap. PLL ferrite behind C319. Crystal with Rd/Rf between it and the chip. Flash with C401/R401 on their pads. Clock buffer with C501/R501.
  - USB-C: the J101 group is tidied, and the J102 group is the same group turned 180° about the board centre.
  - TPS2121 + LED switch (moved 2026-11-17 by `tools/move_power_entry_2026_11_17.py`, arrangement unchanged): bottom right between L201 and J101 (x 159.5–171.6, y 109.3–120.5), LED switch on the left. VBUS caps at the TPS2121 pins (2026-11-18, `tools/vbus_caps_clear_in2_2026_11_18.py`): C102 + C101 right of IN1, C104 left of IN2 with C103 below; TVS D101/D102 stay at the ports.
  - Regulators below the ESP32. U202's group is U201's turned 180° (FB networks face each other), the LDO is to the left, and the block is centred on x.
  - ESP32: C601/C602 under the 3V3 pin, R605/R606 under the USB pins. Flash switches in a column in the user's order, each with its own cap. Q701, U802, U801, U602, amp U503 and switch U502 are each squared up with their parts.
- **Checks 2026-11-18:** no overlaps; parity clean; DRC errors only inside footprints; isolated-copper warnings until the plane vias exist.

## Decisions in force

- **Routing style (2026-11-18):** 0°/45°/90° segments only; exceptions are the LED ring arcs and the radial stubs to the ring LEDs. R303 (reset pull-up, µA) may use a thin trace.
- **Power planes (drawn 2026-11-18, `tools/power_planes_2026_11_18.py`; renders `verification/power-planes-2026-11-18/`):** In1 solid GND. In2 regions: +3V3 background; +5V top arm, link and bottom arm (to y 130.2, J701 5 V vias between its pad rows) plus a tab beside the LDO; +0V9 island under the XVF3800 with a neck to L201; VBUS_MAIN strip J101 → TPS2121; VBUS_ESP strip down the left edge, along the bottom edge, up to C103/C104. +5V_LED: 1 mm B.Cu ring at r 28.7 (outside the DOUT pads) with stubs. Top traces: +5V trunk at x 131.2 to U502, U602, D601, R205; +5V_AMP; +1V8 to J701, J301, C317/pin 31 and R303 (via B.Cu). Open: pins 26/17 (C316, C315/C318) not yet joined; J701 3V3 pins sit over VBUS_ESP. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A; no vias in pads. Review: `verification/power-review-2026-11-17/`.
- **Rev 1 = XVF3800 breakout + ESP32-S3 helper.** XVF3800, 4 mics, MAX98357A speaker amp, power, two USB-C, UI, WS2812 ring. CM5 is rev 2.
- **XVF3800 stays on stock XMOS USB firmware; no modification** (2026-11-09). The square build (`application_xvf3800_ua-io48-sqr.xe`) sets the mic geometry. Anything extra goes on the ESP32.
- **Audio out: MAX98357A only** (2026-11-09, reconfirmed 2026-11-10 after the XK-VOICE-SQ66 comparison). Package **MAX98357AETE+T, TQFN-16** ([C910544](https://www.lcsc.com/product-detail/C910544.html), 2026-11-12; replaces the WLP-9 AEWL+T). No codec, no TLV320DAC3101, no 3.5 mm jack.
- **Helper MCU: ESP32-S3-WROOM-1U-N16R8** (2026-11-10, replaces the RP2350A; [C3013946](https://www.lcsc.com/product-detail/C3013946.html)). IPEX antenna connector; the antenna is off board and not our concern yet. N16R8 instead of N8R8 because it was cheaper (one step up). Support circuits from the controller board, except the reset/boot buttons and USB wiring, which keep this board's style (approved list, 2026-11-10).
- **Host link: USB on the ESP32's own USB-C**, plus the ESP32 reading XVF LED_R/LED_G/INT_N. The 1×6 host header was dropped (2026-11-11); UART0 and I²C are on the 2×12 header.
- **XVF3800 pin roles follow XMOS's pinout** (2026-11-10): 54 is SQ_nLIN (geometry select, pad only), 55 is INT_N (to the ESP32 and the header). The status LED is red 56 / green 58, blue unused. The mute LED is driven by the ESP32.
- **Mic placement: XMOS square order** (2026-11-10, from the XK-VOICE-SQ66 placement file): corners of a 66 × 66 mm square, top side. DATA0 (pin 46) far-left, DATA1 (50) USB-side left, DATA2 (48) USB-side right, DATA3 (51) far-right (anticlockwise seen from the top). The chip sits off-centre towards the USB side on XMOS's board.
- **Breakouts** (2026-11-11): 2×12 2.54 mm **SMD** header J701 (SMD so JLC places it by machine; pads hold it, so avoid heavy side loads) (pinout under ESP32-S3 block; pins 1–20 as the old 2×10, plus UART0 TX/RX and a second +5V and +3V3); other XVF spares on solder pads. XVF I²C has no pull-ups; shunts on J701 13–14 / 15–16 join it to the ESP32 bus.
- **No SPI-slave boot** (2026-11-10): the 33R links and the pin-1 pull-up are gone.
- **Two programming paths for the XVF3800**: XTAG4 on the JTAG header, or the ESP32 writing the flash directly (path B kept on the ESP32, 2026-11-10). Selected by a side slide switch (SW701, SHOU HAN MSK12C02, replaced the jumper 2026-11-11) that turns on four single-channel switches.
- **Dropped from the XMOS comparison** (2026-11-10): the 20-pin XMOS debug connector (JST 7-pin JTAG stays) and XMOS's simpler RC reset (TPS3808 stays).
- **Either USB-C powers the board** through a TPS2121 priority mux (main port wins) (2026-11-09).
- **Power: 0.9 V and 3.3 V both on TLV62569 bucks; 1.8 V LDO from 3.3 V** (2026-11-09). LDO chain rejected (≈1.2 W heat typical).
- **External reset supervisor kept: TPS3808G33** (2026-11-09). The internal POR only watches VDD and VDDIOB18; VDDIOL/R/T (3.3 V) must be valid before reset releases (XU316 datasheet p.26). Also catches 3.3 V brownouts.
- **Assembly: JLCPCB fabricates and assembles everything; no hand assembly** (2026-11-10). Fine-pitch QFN/USON parts are acceptable, but **no ball-grid (WLP/WCSP/DSBGA/BGA) packages** (user, 2026-11-12).
- **Package rule (2026-11-10):** prefer SOT-23-size or smaller packages. Connectors, buttons, the SRP4020 inductors, the SMF5.0A and the ESP32 module stay as they are.
- **Passives: 0402, JLC Basic first** (2026-11-10); 0603/0805/1206 only for 10 µF, 22 µF and 47 µF.
- **ERC target: 0 errors; justified warnings allowed** (2026-11-10). Currently there are also 0 warnings.
- **Buttons (2026-11-11):** mute, action and user are side-pressed SHOU HAN TS24CA ([C393942](https://www.lcsc.com/product-detail/C393942.html), Extended: JLC Basic has no side-pressed switch) on the board edge; XVF reset, EN and BOOT stay top-pressed TS-1187A.
- **USB-C receptacle: Hroparts TYPE-C-31-M-12 ×2** ([C165948](https://www.lcsc.com/product-detail/C165948.html)). Same part as the PDB_rev1 board.
- **USB ESD: TI TPD4E05U06DQAR ×2** ([C138714](https://www.lcsc.com/product-detail/C138714.html), USON-10; user's map 2026-11-12: pin 1 CC1, 2 D−, 4 D+, 5 CC2; D± reach it by label).
- **Speaker power: 3–5 W, 5 V USB-C, no PD.** 5 V / 3 A supply for full volume + LEDs.
- **Mics: Infineon IM69D129FV01XTMA1 ×4**, [C43314439](https://www.lcsc.com/product-detail/C43314439.html). SELECT tied to GND, as on XMOS's board.
- **Flash: Winbond W25Q32JVUUIQ, 4 MB, USON-8 3×4 mm** ([C2999380](https://www.lcsc.com/product-detail/C2999380.html)), for the XVF3800. Centre pad left floating (Winbond: no internal connection, no vias under it).
- **Speaker: Challenge Electronics CS45-05D13-24-1X** (45 mm, 4 Ω, 5 W), [DigiKey India](https://www.digikey.in/en/products/detail/challenge-electronics/CS45-05D13-24-1X/25602924). Not ordered.

## Power (rev 1, redone 2026-11-10 for the ESP32)

XU316 limits ([datasheet via LCSC C6036851](https://www.lcsc.com/datasheet/C6036851.pdf)): VDD 0.855–0.945 V, 300 mA typ / 1 A max. VDDIO 2.97–3.63 V. USB_VDD18 ≤ 36 mA. Rails rise monotonically within 50 ms of each other. PLL_AVDD: 1 µF + 600 Ω@100 MHz ferrite. ≥ 8 × 100 nF on VDD, 100 nF per VDDIO pin, ≥ 10 µF bulk per rail. Bus-powered USB needs no VBUS sense.

- USB-C main and USB-C ESP32: Rd 5.1 kΩ on CC, SMF5.0A TVS, 10 µF + 100 nF on VBUS → TPS2121 (IN1 main, IN2 ESP32) → +5V (22 µF + 100 nF).
- 0.9 V buck (XVF core; PLL_AVDD via ferrite). 1.8 V LDO from 3.3 V (≈60 mA for the XVF; J701 pin 3 adds only light loads). Both bucks have EN tied to VIN, so they start together.
- **3.3 V buck (TLV62569, 2 A):** XVF I/O, flash, mics, switches and the 1.8 V LDO ≈0.18 A; ESP32-S3 ≈0.1 A receiving, **≈0.36 A peaks on Wi-Fi transmit** (Espressif/LCSC figure). Total ≈0.25–0.3 A typical, ≈0.6 A peak: well inside 2 A. 22 µF + 100 nF at the module for the transmit bursts.
- RST_N: TPS3808 open drain, 10 kΩ to 1.8 V, reset button on MR, CT open (20 ms). Wired-OR with the ESP32's 2N7002 (via 0 Ω) and the XTAG.
- Amp: TPS22918 from 5 V, EN = XVF pin 40, 47 µF bulk. LED ring: second TPS22918, EN from ESP32 GPIO47, 22 µF bulk. User WS2812 and its buffer on always-on +5V (≤ 40 mA).
- **5 V budget:** ≈0.7 A typical, ≈2.7 A peak (the 3.3 V peak adds ≈0.3 A at 5 V over the RP2350 design). This is still under the TPS2121's ≈3.2 A typical ILIM, but the margin is smaller. On the ESP32 port alone (often a 0.5–0.9 A PC port), firmware keeps the ring dim or off and limits Wi-Fi bursts.
- **24 MHz crystal: YXC X322524MOB4SI** ([C70590](https://www.lcsc.com/product-detail/C70590.html)). 12 pF load and 50 Ω ESR per LCSC meet the XU316 spec (12 pF, ≤ 60 Ω). Fallback: TXC 7M-24.000MAAE-T ([C2450246](https://www.lcsc.com/product-detail/C2450246.html), 0 stock 2026-11-10).

## XVF3800 pin use (diagram 04)

Roles per the [XMOS pinout](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/04_device_pinout.html) and the XK-VOICE-SQ66 schematic.

- QSPI flash 1, 2, 3, 5, 59, 60 (CS_N 4.7 kΩ pull-up). Crystal 16/15 (1.8 V bank). USB 28/29 (90 Ω). JTAG 18/20/23/24, RST_N 21.
- Mics: CLK 43 → buffer (sheet audio); DATA 46 (DATA0), 50 (1), 48 (2), 51 (3). MCLK loop: PCB trace 14 → 41.
- I²S to MAX98357A: 9 DATA0, 10 LRCK, 13 BCLK (I²S master, BCLK = 64 × fs).
- Buttons 11 (mute), 32 (action), active low, 10 kΩ pull-ups.
- GPO: 40 CODEC_RST_N = amp EN; 56 LED_R, 58 LED_G → status LED and ESP32 GPIO15/16; 55 INT_N → ESP32 GPIO17 + J701.
- To J701: 39 I2S_DATA1 (external AEC reference input), 53 I2S_DATA2, 44/45 I²C SCL/SDA (I²C slave control in the I²S builds), 55 INT_N.
- Solder pads: 6/7/47 (SPI control CS/MOSI/MISO), 54 SQ_nLIN, XLINK 33/35/36/37. Test pads: 9, 10, 13, 14. Pin 25 NC.
- ESP32 path B: 3, 5, 59, 1 through the four flash switches.

## ESP32-S3 block (diagram 07)

- **GPIO map:**
  - 0 BOOT (button + 10k pull-up); EN reset button.
  - 1, 2, 4, 5, 6, 7, 8, 9 → J701 (all ADC1/touch).
  - 10–13 SPI2 to the XVF flash: 10 CS_N, 11 MOSI → DI, 12 CLK, 13 MISO ← DO. 14 PROG switch sense (PRG_EN). 21 PRG_RST → Q701.
  - 15/16 XVF LED_R/LED_G taps; 17 XVF INT_N; 18 TPS2121 ST.
  - 19/20 USB D−/D+ (27R series).
  - 38/39 I²C SDA/SCL (J701, 4.7k pull-ups on sheet esp32_io).
  - 40 user WS2812 (own SN74AHCT1G125 on always-on +5V); 41 mute LED; 42 user button (10k pull-up, active low).
  - 43/44 UART0 TX/RX → J701 pins 21/22.
  - 47 LED ring enable; 48 LED ring data (RMT).
  - Unconnected, no pads: strapping pins 3, 45, 46; PSRAM pins 35–37.
- **J701 (2×12, 2.54 mm SMD, HCTL PZ254-2-12-S [C3294470](https://www.lcsc.com/product-detail/C3294470.html); HCTL land pattern; pick-up cap unconfirmed):** 1 +5V, 2 +3V3, 3 +1V8, 4 GND, 5 GPIO1, 6 GPIO2, 7 GPIO4, 8 GPIO5, 9 GPIO6, 10 GPIO7, 11 GPIO8, 12 GPIO9, 13 ESP SDA, 14 XVF SDA, 15 ESP SCL, 16 XVF SCL, 17 XVF INT_N, 18 XVF I2S_DATA1, 19 XVF I2S_DATA2, 20 GND, 21 ESP UART TX, 22 ESP UART RX, 23 +5V, 24 +3V3.
- Switch choice: four single TS5A3166DBVR switches, SOT-23-5 ([C353035](https://www.lcsc.com/product-detail/C353035.html), 2026-11-12; replaced the DSBGA YZPR) instead of one quad (the '3125 has no in-stock QFN; TMUX1574RSVR had 12 in stock). Fallback with active-low OE: SN74CBTLV1G125DCKR ([C131992](https://www.lcsc.com/product-detail/C131992.html)).
- **TS5A3166 datasheet check:** off-state capacitance is 18–19 pF on each switched XVF QSPI line; IN logic-high threshold is 2.0 V at 3.3 V supply.
- WS2812B ring: data through SN74AHCT1G125 on the switched 5 V rail. The ESP32 must hold LED_DATA low while the ring is off.
- Datasheet: `PCB/libraries/datasheets/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf`; [Espressif schematic checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html).

## XVF3800 programming (diagram 08)

- **Path A, XTAG4:** JTAG header at 1.8 V; XMOS tools load a helper that writes the flash. Also the only route for live debugging. Check that the XTAG4 works at 1.8 V (and with a JST-to-XMOS 20-pin adapter cable).
- **Path B, ESP32:**
  - Four TS5A3166 switches sit on flash CS_N, CLK, D0 and D1 (XVF pins 3, 5, 59, 1). D2/D3 are not needed: the JV-IQ has QE fixed on, so plain SPI writes work.
  - PRG_EN has a 4.7k pull-down. SW701 (common = PRG_EN) slides to 3.3 V for PROG or GND for RUN; GPIO14 reads it.
  - Sequence: the ESP32 holds RST_N low through Q701, writes the W25Q32 over SPI2, reads it back, releases the lines (59/60/1 are boot straps), then releases reset.
- The image is the `.xe` converted to raw flash bytes by XMOS `xflash` (free tool); the exact option is unverified. Verify boot from an ESP32-written image on the first board.

## Reference documents

- **XVF3800:** [XMOS docs v3.2.1](https://www.xmos.com/documentation/XM-014888-PC/html/); [pinout](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/04_device_pinout.html); [device interfaces](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/05_device_interfaces.html); XU316-1024-QF60B datasheet in `PCB/libraries/datasheets/`.
- **ESP32-S3:** module datasheet in `PCB/libraries/datasheets/`; Espressif schematic checklist (link above).
- **Schematic references:** human style and ESP32 support circuits from `~/Z/projects/internship/stealth_startup/diff-drive-robot/hardware/electrical/kicad/controller-board_rev1_4/`; agent pipeline from `~/Z/projects/PDB/PDB_rev1/tools/`; tidy skill in `~/.agents/skills/kicad-schematic-tidy/`.

## Open questions

- Whether the stock USB firmware ever uses pins 44/45 as an I²C master (XMOS docs describe only an I²C slave); XVF I²C has no pull-ups unless J701 shunts join it to the ESP32 bus.
- Whether the XVF GPO pins are active high (the LEDs assume they are).
- Whether 18–19 pF from each TS5A3166 on the XVF QSPI lines is acceptable at the XVF3800's boot clock. The fallback is a 0 Ω/DNP split.
- TS24CA side buttons: the stem pokes out only 0.31 mm. Check the footprint's front anchor pads against the land pattern in `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1, and whether the stem is 1.2 mm (footprint silk) or longer (the drawing's 2.15 mm).
- QFN-60 (0.4 mm), VQFN-HR, USON-10 and TQFN-16 vs JLC's rules.
- 3D models still to align or source: TPS2121 is attached at zero offset; the RGB LED has none. The TQFN-16 uses the stock EP1.6 model (same body). The ESP32 has Espressif's STEP (Espressif's offset; not checked in the 3D viewer).
- OV trip at 5.57 V (± about 2 %) could trip on a charger that sits at the 5.5 V USB limit.

## Next steps

1. User checks the tidied schematic (`PCB/mindspark_rev1/mindspark_rev1_schematic.pdf`) and placement in KiCad.
2. Under discussion (`verification/escape-analysis-2026-11-18/`): LDO to the bottom by the XVF3800, +1V8 pins 26/17, XVF3800 escape plan. Then plane vias and routing (power traces redrawn at 45°); reference/label placement last (user's call). Also: JLC rule check of the fine-pitch footprints, align or source the missing 3D models.
3. Recheck LCSC/JLC stock just before ordering.

## Archive

1 archive file (2026-11-03 to 2026-11-18; incl. the first placement rules, the small-parts table and the 2026-11-12 placement checks); index in `AGENTS.archive-index.md`.

## 2026-11-19: decision lines replaced when the main USB pair was built (word for word)

- **Placement** (user's rules; `tools/place_tidy2.py` second pass, archived first pass must not be rerun): USB-C on left/right edges, JSTs on the top edge, side buttons and LEDs spread on the side edges with their passives in a column inside, M2 holes 12 mm in, test pads in two bottom-side rows, mics at the 66 mm square corners, LED ring on the bottom at r 27.0. Groups are IC-anchored, 0.15 mm courtyard gaps, each cap on the pin its `use` field names. XVF3800 on the bottom directly under the ESP32 module, caps 1.65 mm out, **rotated 90° CCW 2026-11-18** with its caps and U501 group (`tools/xvf_rotate_2026_11_18.py`): USB D± leave the east edge, +1V8 pins 17/26 east, 31 SE corner. Flash U401 group at the chip's NW corner, crystal Y301 group above the north cap row, **LDO U203 + C208/C209 on the bottom at (160.35, 97.0)** (input east, output west). Gaps are still 0.15 mm; widen them in the escape pass. TPS2121 block + LED switch at the bottom right (x 159.5–171.6, y 109.3–120.5) with the VBUS caps at its inputs; TVS diodes stay at the ports. Around U103 (`tools/u103_fanout_place_2026_11_19.py`): C107 in the north row beside C105, C104 west at (165.6, 115.3), C102 standing at (172.85, 116.85), R105–R112 0.5 mm lower.
- **Power planes** (`tools/power_v2_2026_11_18.py`): In1 solid GND. In2: +3V3 background; +5V arms (top, link, bottom to y 130.2, tab with the trunk vias at x 131.2–132.4); +0V9 island under the XVF3800, a 1.8 mm neck through the south cap row (over C305) down to L201; **+1V8 band** x 151.4–160 (C318, C315, C316, LDO output, also under the USB exit) with a leg to C317; VBUS_MAIN strip J101 → TPS2121, notched for a small +5V finger (x 170.7–173.3, y 112.9–114.9) that takes U103 pin 8's vias east of the ring; VBUS_ESP strip down the left, along the bottom, up to C103/C104. +5V_LED: 1 mm B.Cu ring at r 28.7 with radial stubs; ring caps linked to their LEDs.
- **Routing style: jog routing** (user 2026-11-18): straight horizontal/vertical runs joined by 45° jogs, not direct free-angle lines; exceptions are the LED ring arcs and its radial stubs. From the user's hand edits: traces end on pad/via centres (last leg 0/45/90 into the centre), no grid staircases or slivers, ~0.3 mm extra room from other copper where it costs little (not long detours). `tools/jog_router.py` does all of this now (falls back to any point in the pad when the centre is unreachable); the hand-edited board is kept as `mindspark_rev1-backups/mindspark_rev1.kicad_pcb.hand-jogs-2026-11-18`. R303 (µA pull-up) may be thin. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (kept for XVF escapes; GND exempt).
- **Vias in pads (2026-11-18, rules 2026-11-19): epoxy-filled, capped (JLC via-in-pad option).** Every SMD pad on a planed rail whose own plane is under its centre gets vias **centred on the pad** (one on the centre; several as a pattern centred on it). Count by current (`PART_AMPS` in `power_v2_2026_11_18.py`): 1 A per 0.6/0.3, 0.5 A per 0.45/0.2; VBUS/TPS2121 path 3 A, amp 1.6 A, LED switch 0.75 A, 3V3 buck 0.45 A in / 0.6 A out, 0V9 1 A, ESP32 0.4 A; GND pads take the rail's current; others one via. Too small for the count: the rest go just outside on a stub (C101, C103, C106, C509). Centre blocked (wrong plane or another net's pad opposite): no via, the pad is routed. Exception: XVF paddles keep the clear spots of their centred row (under ESP32 pad 41). **U103 pins 1/2/7/8** (no via fits under them): each has an F.Cu pour (`FLANGES` in power_v2, solid to the pad, 0.2 mm clearance) out to its own 0.6/0.3 vias: pin 1 +5V 2 W (joins C106), pin 2 VBUS_ESP 3 SW (joins C104/C103), pin 7 VBUS_MAIN 3 E (joins C102/C101), pin 8 +5V 2 NE in the finger. Backup before this: `mindspark_rev1-backups/mindspark_rev1.kicad_pcb.pre-centred-vias-2026-11-19`; renders `verification/via-in-pad-2026-11-19/`.
- **XVF USB pair route** (agreed 2026-11-19, not built): B.Cu from pins 28/29 east through a gap in the XVF east cap column (C304 in the way; C313/C316 re-space) to just outside the ESP32 module's east edge (x ≈ 157.4, vias ≈ y 100.65/101.35), then F.Cu over In1 GND to U101/J101. No plane cuts. Four stitching caps, 100 nF 0402 C1525 on B.Cu: CA/CB +0V9↔+1V8 either side of the pair where it leaves the +0V9 island (CA's +0V9 pad to pin 27, CB's to a small +0V9 via south of pin 30); CC/CD +1V8↔GND either side of the layer-change vias (their GND vias double as return vias). Make room: the F.Cu +1V8 feed at x 158.3 moves east; U703 + U701 + C703/C701 shift south (≈0.6–0.85 mm, room above C813/R801) to open a top-layer gap below U702. D101 still partly in the way before U101 (next to look at). Plan image `verification/usb-stitching-plan-2026-11-19/plan.png`. Caps need adding to the schematic.
