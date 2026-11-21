<!-- agents-md: v3 · current-state · ≤2000 words · history in AGENTS.archive-*.md · index in AGENTS.archive-index.md -->
# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched). Full detail as of 2026-11-18 (component values, power budget, XVF/ESP pin maps, J701 pinout, programming paths, sourcing links) is word for word in `AGENTS.archive-002.md`; grep it rather than guessing.

## What this is

- **Company: MindSpeak** (mindspeakai.org). "Mindspark" survives only in identifiers (folder, `mindspark_rev1`, KiCad library `Mindspark`); use MindSpeak in anything people read.
- USB voice front-end: **XMOS XVF3800** (stock USB firmware, square mic build), 4 × IM69D129 mics, MAX98357A speaker amp, **ESP32-S3-WROOM-1U-N16R8** helper, two USB-C (main = XVF, ESP32), WS2812 ring. CM5 host is rev 2.
- **Prototype**: thin stock is fine; don't flag low stock. Designed from datasheets; XMOS XK-VOICE-SQ66 (`incoming/xk_voice_sq66/`, XMOS licence) is the reference for mic wiring and pin roles.
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (weasyprint in `~/.local/venvs/weasyprint`). **Diagrams:** `docs/diagrams/` 01–08 (block, power tree, XVF connections, XVF pin map, audio, mics, ESP32, programming); sources in `docs/diagrams/src/`.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, `main`. `.gitignore` leaves out KiCad backups, audio clips, `incoming/`. Last commit 2026-11-22 a278827 (flash switches west, straight USB pair, plane edge, pin shift), pushed. `PCB/mindspark_rev1-backups/` stays untracked.
- **Status 2026-11-22:** schematic done (9 A4 sheets, ERC 0/0, BOM 59 lines / 203 parts, LCSC on every line). All power copper rebuilt by `tools/power_v2_2026_11_18.py`. Routed: XVF main USB pair, four mic pairs, east escape (column feeds, crystal, QSPI XVF↔flash), JTAG to J301, I2S + MCLK, and (2026-11-22) the flash switches west of the module with links R706–R709. DRC: only the old footprint errors (mic pads, switch PTH pads); parity clean; 177 unconnected. Backups in `mindspark_rev1-backups/` (latest `pre-prog-switch-2026-11-22/`: committed board, the user's hand-edit suggestion, sheets, all scripts).

## Files and tools (`PCB/mindspark_rev1/`, KiCad 10)

- KiCad's `pcbnew` Python segfaults here: the board is edited as S-expressions (`tools/sexpr.py`, `tools/place_tidy.py` `Part`). Each change is a dated script in `tools/` (moves, cap moves, `clear_routing_*`, `power_planes_2026_11_18.py`). Run them with the PCB editor closed; `kicad-cli pcb drc --schematic-parity --refill-zones --save-board` fills and checks.
- Schematic: generator retired; edit sheets in place (`tools/sch_tidy_2026_11_12.py` is the example; `verification/tidy-record.md`).
- Library: `PCB/libraries/` (`Mindspark`, project-only, `${KIPRJMOD}/../libraries/...`; `parts-map.json`). Sources: KiCad built-in first, then easyeda2kicad (`~/.local/venvs/easyeda2kicad`), vendor CAD where it matters. XVF3800 uses `Mindspark:XVF3800-QF60B-C` (5 paddles), never the stock QFN-60.
- Routing: `tools/jog_router.py` (grid router, 0/45/90° runs with jogs, turn-penalised, pad-centre ends, pulled tight; comparisons in `verification/jog-routing-review-2026-11-18/`; used by `power_v2_2026_11_18.py`, which rebuilds all tracks/vias/zones from scratch). Analysis: `tools/route_render.py` (zoomed layer view with part hints), `power_render.py`, `power_drop.py`, `zone_render.py`, `escape_map.py` (`--edge-sensitive`, `--board=`). Results in `verification/`: `power-review-2026-11-17/`, `power-planes-2026-11-18/`, `escape-analysis-2026-11-18/` and `-2026-11-19/` (sensitive nets, current board).
- BOM and sourcing: `bom/` (sourcing notes with every LCSC link).

## Decisions in force

- **Power:** either USB-C feeds a TPS2121 priority mux (main wins, XCOMP ≈4.4 V, OV 5.57 V, ILIM ≈3.2 A) → +5V. TLV62569 bucks for 0.9 V (XVF core) and 3.3 V; TLV75518 LDO 3.3 → 1.8 V. TPS3808G33 reset supervisor kept. TPS22918 switches for amp (EN = XVF pin 40) and LED ring (ESP32 GPIO47). 5 V budget ≈0.7 A typ / 2.7 A peak.
- **Audio:** MAX98357A TQFN-16 only; no codec, no jack. Mics in the XMOS square order (66 mm square, top side), one ferrite + 10 µF + 1 µF per mic.
- **ESP32 role:** USB on its own USB-C; reads XVF LED_R/G and INT_N; drives mute LED; writes the XVF flash (path B) through four TS5A3166 switches (U701–U704) turned on by SW701 (PRG_EN). Path A is XTAG4 on the 1.8 V JST JTAG header. No SPI-slave boot. PRG pins (since 2026-11-22, SPI2 via the GPIO matrix): pin 21/GPIO13 CS_N, 20/GPIO12 DO, 19/GPIO11 CLK, 18/GPIO10 DI, 22/GPIO14 EN, 23/GPIO21 RST. **0 Ω links R706–R709** (C17168) sit between each switch's COM pin and its XVF flash line: remove them to cut the switches (18–19 pF off-capacitance each) off the flash lines.
- **Breakout:** J701 2×12 2.54 mm SMD header (ESP GPIO1–9 ADC1 pins, UART0, both I²C buses with shunt links, XVF INT_N, I2S_DATA1/2, power). Other XVF spares on pads.
- **Assembly:** JLCPCB fabricates and assembles everything, both sides. Fine-pitch QFN/USON OK; **no ball-grid packages**. Prefer SOT-23-size or smaller; passives 0402 JLC Basic first (0603/0805/1206 only for 10/22/47 µF).
- **Parts kept:** Hroparts TYPE-C-31-M-12 ×2, TPD4E05U06DQAR ESD ×2, SMF5.0A TVS, SRP4020TA-2R2M inductors, YXC 24 MHz crystal, W25Q32JVUUIQ flash (centre pad floating, no vias under it), JST PH speaker and JTAG connectors (plus solder pads), TS24CA side buttons and TS-1187A top buttons. Speaker CS45-05D13-24-1X (not ordered).
- **ERC:** 0 errors (justified warnings allowed); currently 0/0.
- **Board:** 74 × 74 mm, 4 layers (In1 GND, In2 power), centre (146.558, 98.679), 0.3 mm copper-to-edge. JLC rules: min track/clearance 0.1, via 0.45/0.2; Default class 0.15/0.15; Power class 0.4 with 0.6/0.3 vias.
- **Hand edits are suggestions** (user 2026-11-22): never commit the user's KiCad hand edits; rebuild their intent in the dated scripts from the committed board.
- **Nothing is locked** (user 2026-11-22): pin orders, frozen routes, power wiring and placements can all change; propose the change and get a yes before building.
- **Placement** (user's rules, full detail in archive-002): USB-C on left/right edges, JSTs top edge, side buttons/LEDs on side edges, M2 holes 12 mm in, test pads in two bottom rows, mics at the 66 mm square corners, LED ring on the bottom at r 27.0; groups IC-anchored, 0.15 mm courtyard gaps, each cap on the pin its `use` field names. XVF3800 on the bottom under the ESP32 module, rotated 90° CCW; flash at its NW corner, LDO U203 east. **East cap column** (`tools/prog_switch_place_2026_11_22.py`): west pads on one line 1.74 mm from the pin ends; north of the USB pair C315, C303, C319, FB301, C316 (lane gaps TDI | TDO+RST | PLL | TMS+TCK kept, 0.46 mm lower than 2026-11-21), south C313, C314, C304. **Flash switches** U701 (CS_N), U704 (D1), U702 (CLK), U703 (D0) on the top side west of the module, one column at x 129.0 (pads 1–3 facing the module, 3.55 mm pitch, U704 level with the D1 line at y 93.76), caps C701–C704 upright west of them, links at x 132.2. TPS2121 block bottom right.
- **Power planes** (`tools/power_v2_2026_11_18.py`): In1 solid GND. In2: +3V3 background; +5V arms; **+0V9 island** under the XVF3800 ending at x 149.45 (behind the east pins), neck south to L201; **+1V8** from x 149.75 (under all east pins and the USB exit) to x 160, with the leg to C317 and the notch to C318; VBUS_MAIN and VBUS_ESP strips. +5V_LED: 1 mm B.Cu ring at r 28.7. **No plane cuts for signals.** The USB pair crosses no plane edge, so the +0V9/+1V8 stitching caps C323/C324 are gone (C325/C326, +1V8/GND by the layer-change vias, stay). +1V8 to R303 hops under the +5V trunk at HOP1 (134.0, 86.5) / HOP2 (122.4, 88.6).
- **Routing style: jog routing** (user 2026-11-18): horizontal/vertical runs joined by 45° jogs (LED ring arcs excepted), ends on pad/via centres, no staircases, slivers or right angles, ~0.3 mm extra room where cheap. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (GND exempt; short east +0V9 jumpers agreed). **power_v2 rebuilds every track**: fixed signal routes are laid first (`usb_main_route_2026_11_19.py`, `mic_route_2026_11_20.py` + JSON, `east_column_2026_11_22.py` = east escape JSON minus the old column feeds, `jtag_route_2026_11_21.py`, `i2s_mclk_route_2026_11_21.py`, `prog_switch_route_2026_11_22.py` + JSON) and the power router avoids them; new signal routes go in the same way.
- **Vias in pads** (epoxy-filled, capped; rules in archive-002): centred on each SMD pad over its own plane, count by current (`PART_AMPS`), the rest beside on a stub; U103 pins 1/2/7/8 on F.Cu pours to via groups. Signal vias in pads are used too (switch pins 1 and 4, R401 pad 1). Since 2026-11-22 a pad whose centre is blocked gets one small via beside it on a short stub (0.2 mm from holes) before falling back to a routed trace.
- **Priorities are scaffolding** (user 2026-11-22): the signal-priority list only orders the work; reopening a "higher" route costs nothing. Done: XVF USB D±, mics, crystal + QSPI XVF↔flash, JTAG, I2S + MCLK, flash switches. Next: XVF I2S_DATA1/2 → J701, ESP32 USB D±, slow control (PRG_EN to ESP pin 22, GPO_R/G, INT_N, AMP_EN, LED lines, XVF_RST_N, ESP_EN/BOOT, BTN_MUTE_N).
- **Built routes** (detail word for word in archives 002/003): XVF main USB pair 0.25/0.15 mm (≈92 Ω by formula, **confirm with JLC's calculator**), since 2026-11-22 straight east on B.Cu from pins 28/29, one 45° jog on F.Cu to U101, 27.57 / 27.49 mm, J101 B6/B7 by B.Cu jumpers; mic pairs (NW pair re-routed 2026-11-22 south of the switch block and up its west side on F.Cu, `mic_nw_reroute_2026_11_22.py`; 1 mm lane kept for SPI_MISO pin 47 → TP403); east escape (pins 16–30, crystal, QSPI XVF↔flash; D3's F.Cu hop now at y 93.5 with its west via at 137.8 / 93.5); east +0V9 caps fed from pin 19 (pins 19 and 27 stubbed onto the east +0V9 paddle), F.Cu jumpers C303–FB301–C304; JTAG to J301 (+ RST_N to R703); I2S to U503 + MCLK loop.
- **Flash-switch routes** (2026-11-22, `prog_switch_route_2026_11_22.py`, hand geometry): flash lines branch at the flash (CS_N via in R401 pad 1, D1 via at 143.2 / 94.0, CLK from its hop's west via, D0 via at 138.5 / 95.65) and run on the top layer west to the links, 7.8–11.2 mm. PRG_CS_N/DO/CLK/DI leave ESP32 pins 21–18 west under the module (already in the switch column's order), run up a lane inside the east pads, then straight west in a band just inside the north pads (0.31 mm pitch; C301/C302/C310's vias moved beside their pads), drop to B.Cu just west of the module (CS_N north, the rest south) and run as four parallel lines into vias in each switch's pin 1 (33–41 mm, 2 vias each). PRG_EN is chained on B.Cu (vias in pins 4), out west to F.Cu and on to R701/SW701. Plan images `verification/prog-switch-plan-2026-11-22/`, renders `verification/prog-switch-route-2026-11-22/`.

## To do (agreed, not yet done)

1. **PRG_EN from ESP32 pin 22** to the PRG_EN net (the only unrouted piece of the flash-switch work; no room in the under-module lane, so it goes with slow control).
2. **Escape and signal-routing pass**: XVF INT_N/GPO_R/GPO_G reach ESP32 pins 8–10 by B.Cu ending in a via in the ESP32 pad; reassign ESP32 GPIOs so north-row J701 signals come from the south row (needs a call on UART0 as console).
3. Power side for that pass: pin 42 (+0V9) to C306 round the MIC_CLK via, pins 40/42 past the MCLK via; XVF3800 +0V9/+3V3 fan-out on the west and south sides (pins 4/12/34/42/49/57/63/64 +0V9 and 38/52 +3V3 not joined); north caps C301/C302 have no plane under them; C313/C314 +3V3 over the +1V8 band; power test pads (TP201–TP205, TP301, TP307).

## Open questions

- Stock XVF firmware: is I²C on pins 44/45 ever a master? Are the GPO pins active high?
- TS5A3166 off-capacitance (18–19 pF per QSPI line) at the XVF boot clock; fallback 0 Ω/DNP split.
- TS24CA stem protrusion (0.31 mm) and anchor pads vs `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1.
- Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) vs JLC rules; missing/unaligned 3D models (TPS2121, RGB LED, ESP32 offset).
- OV trip at 5.57 V could trip on a charger at the 5.5 V USB limit.
- XTAG4 at 1.8 V (and the JST-to-XMOS adapter); ESP32-written `xflash` image boot, to verify on the first board.

## Next steps

1. XVF I2S_DATA1/2 → J701 (hop to F.Cu before the SE mic pair, y 122.6–123.2), then ESP32 USB, then slow control (PRG_EN pin 22, JTAG leftovers RST_N west and TP302–TP306, BTN_MUTE_N from its via to SW401); I2S/MCLK test pads TP409–TP412 with the test-pad pass.
2. Reference/label placement last (user's call). Recheck LCSC/JLC stock before ordering.

## Archive

3 archive files (2026-11-03 to 2026-11-22); index in `AGENTS.archive-index.md`.
