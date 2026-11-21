<!-- agents-md: v3 · current-state · ≤2000 words · history in AGENTS.archive-*.md · index in AGENTS.archive-index.md -->
# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched). Full detail as of 2026-11-18 (component values, power budget, XVF/ESP pin maps, J701 pinout, programming paths, sourcing links) is word for word in `AGENTS.archive-002.md`; grep it rather than guessing.

## What this is

- **Company: MindSpeak** (mindspeakai.org). "Mindspark" survives only in identifiers (folder, `mindspark_rev1`, KiCad library `Mindspark`); use MindSpeak in anything people read.
- USB voice front-end: **XMOS XVF3800** (stock USB firmware, square mic build), 4 × IM69D129 mics, MAX98357A speaker amp, **ESP32-S3-WROOM-1U-N16R8** helper, two USB-C (main = XVF, ESP32), WS2812 ring. CM5 host is rev 2.
- **Prototype**: thin stock is fine; don't flag low stock. Designed from datasheets; XMOS XK-VOICE-SQ66 (`incoming/xk_voice_sq66/`, XMOS licence) is the reference for mic wiring and pin roles.
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (weasyprint in `~/.local/venvs/weasyprint`). **Diagrams:** `docs/diagrams/` 01–08 (block, power tree, XVF connections, XVF pin map, audio, mics, ESP32, programming); sources in `docs/diagrams/src/`.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, `main`. `.gitignore` leaves out KiCad backups, audio clips, `incoming/`. Last commit 2026-11-21: JTAG to J301, I2S + MCLK loop (C310/C302 moved), with this checkpoint, pushed (east column 09d2fa3, mics 85f18cc, USB pair 39ddc97). `PCB/mindspark_rev1-backups/` stays untracked.
- **Status 2026-11-21:** schematic done (9 A4 sheets, ERC 0/0, BOM 59 lines / 201 parts, LCSC on every line). Power copper by `tools/power_v2_2026_11_18.py` (planes, vias in pads, jog-routed power traces, U103 flanges). Signal routes so far: XVF main USB pair (2026-11-19), the four mic pairs (2026-11-20), the east-side escape (2026-11-21: east cap column feeds, crystal, QSPI XVF↔flash, JTAG fan-out), JTAG on to J301 and R703 (2026-11-21), I2S to the amp + MCLK loop (2026-11-21). DRC: only the old footprint errors (mic pads, switch PTH pads) plus the dangling BTN_MUTE_N via; parity clean; 189 unconnected. Backups in `mindspark_rev1-backups/` (`pre-east-column-2026-11-21/`, `pre-jtag-2026-11-21/` with the user's MCLK trial, `pre-i2s-2026-11-21/`).

## Files and tools (`PCB/mindspark_rev1/`, KiCad 10)

- KiCad's `pcbnew` Python segfaults here: the board is edited as S-expressions (`tools/sexpr.py`, `tools/place_tidy.py` `Part`). Each change is a dated script in `tools/` (moves, cap moves, `clear_routing_*`, `power_planes_2026_11_18.py`). Run them with the PCB editor closed; `kicad-cli pcb drc --schematic-parity --refill-zones --save-board` fills and checks.
- Schematic: generator retired; edit sheets in place (`tools/sch_tidy_2026_11_12.py` is the example; `verification/tidy-record.md`).
- Library: `PCB/libraries/` (`Mindspark`, project-only, `${KIPRJMOD}/../libraries/...`; `parts-map.json`). Sources: KiCad built-in first, then easyeda2kicad (`~/.local/venvs/easyeda2kicad`), vendor CAD where it matters. XVF3800 uses `Mindspark:XVF3800-QF60B-C` (5 paddles), never the stock QFN-60.
- Routing: `tools/jog_router.py` (grid router, 0/45/90° runs with jogs, turn-penalised, pad-centre ends, pulled tight; comparisons in `verification/jog-routing-review-2026-11-18/`; used by `power_v2_2026_11_18.py`, which rebuilds all tracks/vias/zones from scratch). Analysis: `tools/route_render.py` (zoomed layer view with part hints), `power_render.py`, `power_drop.py`, `zone_render.py`, `escape_map.py` (`--edge-sensitive`, `--board=`). Results in `verification/`: `power-review-2026-11-17/`, `power-planes-2026-11-18/`, `escape-analysis-2026-11-18/` and `-2026-11-19/` (sensitive nets, current board).
- BOM and sourcing: `bom/` (sourcing notes with every LCSC link).

## Decisions in force

- **Power:** either USB-C feeds a TPS2121 priority mux (main wins, XCOMP at ≈4.4 V, OV 5.57 V, ILIM ≈3.2 A) → +5V. TLV62569 bucks for 0.9 V (XVF core) and 3.3 V; TLV75518 LDO 3.3 → 1.8 V. TPS3808G33 reset supervisor kept. TPS22918 switches for amp (EN = XVF pin 40) and LED ring (ESP32 GPIO47). 5 V budget ≈0.7 A typ / 2.7 A peak.
- **Audio:** MAX98357A TQFN-16 only; no codec, no jack. Mics in the XMOS square order (66 mm square, top side), one ferrite + 10 µF + 1 µF per mic.
- **ESP32 role:** USB on its own USB-C; reads XVF LED_R/G and INT_N; drives mute LED; can write the XVF flash (path B) through four TS5A3166 switches selected by slide switch SW701. Path A is XTAG4 on the 1.8 V JST JTAG header. No SPI-slave boot.
- **Breakout:** J701 2×12 2.54 mm SMD header (ESP GPIO1–9 ADC1 pins, UART0, both I²C buses with shunt links, XVF INT_N, I2S_DATA1/2, power). Other XVF spares on pads.
- **Assembly:** JLCPCB fabricates and assembles everything, both sides. Fine-pitch QFN/USON OK; **no ball-grid packages**. Prefer SOT-23-size or smaller; passives 0402 JLC Basic first (0603/0805/1206 only for 10/22/47 µF).
- **Parts kept:** Hroparts TYPE-C-31-M-12 ×2, TPD4E05U06DQAR ESD ×2, SMF5.0A TVS, SRP4020TA-2R2M inductors, YXC 24 MHz crystal, W25Q32JVUUIQ flash (centre pad floating, no vias under it), JST PH speaker and JTAG connectors (plus solder pads), TS24CA side buttons (mute/action/user) and TS-1187A top buttons. Speaker CS45-05D13-24-1X (not ordered).
- **ERC:** 0 errors (justified warnings allowed); currently 0/0.
- **Board:** 74 × 74 mm, 4 layers (In1 GND, In2 power), centre (146.558, 98.679), 0.3 mm copper-to-edge. JLC multilayer rules: minimum track/clearance 0.1, via 0.45/0.2; Default class 0.15/0.15 (diff-pair defaults 0.2/0.25, unused); Power class 0.4 with 0.6/0.3 vias.
- **Placement** (user's rules; `tools/place_tidy2.py` second pass, archived first pass must not be rerun; full rules in archive-002): USB-C on left/right edges, JSTs top edge, side buttons/LEDs on the side edges, M2 holes 12 mm in, test pads in two bottom rows, mics at the 66 mm square corners, LED ring on the bottom at r 27.0. Groups IC-anchored, 0.15 mm courtyard gaps, each cap on the pin its `use` field names. XVF3800 on the bottom under the ESP32 module, **rotated 90° CCW**; flash at its NW corner, LDO U203 east of it. **East side since 2026-11-21**: cap column centred on pins 17–27, pads 1.74 mm from the pin ends (C315, C303, C319 and FB301 turned with PLL pads east, C316, C304, C323, USB pair, C324, C313, C314); crystal Y301 east of the north row (C320/R302 below, R301/C321 above); C318 by the LDO; C301 between the CS_N and CLK runs; C310/C302 0.15 mm west of their pins 8/12 (2026-11-21, for straight I2S lanes). TPS2121 block bottom right (moves in `u103_fanout_place_2026_11_19.py`, `usb_main_place_2026_11_19.py`).
- **Power planes** (`tools/power_v2_2026_11_18.py`): In1 solid GND. In2: +3V3 background; +5V arms (top, link, bottom, trunk tab); +0V9 island under the XVF3800 with a neck through the south cap row to L201; **+1V8 band** x 151.4–160 (also under the USB exit) with a leg to C317, a notch north to C318 and a step west to x 150.5 under the USB pair's lanes (2026-11-21); VBUS_MAIN strip J101 → TPS2121 with a small +5V finger for U103 pin 8; VBUS_ESP strip round the left/bottom. +5V_LED: 1 mm B.Cu ring at r 28.7. **No plane cuts for signals** (user 2026-11-19): stitching caps instead.
- **Routing style: jog routing** (user 2026-11-18): horizontal/vertical runs joined by 45° jogs (LED ring arcs excepted), ends on pad/via centres, no staircases, slivers or right-angle bends (`jog_router.chamfer_corners` cuts them to 45° in the mic script and power_v2; corners inside pads and T-joins stay), ~0.3 mm extra room where cheap. `tools/jog_router.py` does this. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (GND exempt; the short east +0V9 jumpers are agreed exceptions). **power_v2 rebuilds every track**: fixed signal routes (`usb_main_route_2026_11_19.py`, `mic_route_2026_11_20.py`, `east_escape_2026_11_21.py`, `jtag_route_2026_11_21.py`, `i2s_mclk_route_2026_11_21.py`) are laid first inside it and the power router avoids them; new signal routes must be added the same way or survive a rerun some other way.
- **Vias in pads** (epoxy-filled, capped; rules 2026-11-19, detail word for word in archive-002): centred on each SMD pad over its own plane, count by current (`PART_AMPS`: 1 A per 0.6/0.3, 0.5 A per 0.45/0.2), the rest beside on a stub; centre blocked → routed instead; U103 pins 1/2/7/8 on F.Cu pours (`FLANGES`) to via groups.
- **Length-sensitive nets** (escape maps; detail word for word in archive-002): USB D± (both), mic DATA0–3, JTAG, XVF I2S_DATA1/2; the maps ignored inter-IC nets, rerun with them. The XVF3800 escapes on B.Cu only inside the module's shadow; F.Cu under the module is free but opens only to the west.
- **Signal priority** (user, agreed 2026-11-21, edge and inter-IC nets; higher gets the shortest, straightest route, fewest vias, best reference plane, first pick of escape gaps): 1. XVF USB D± (pins 28/29 → J101), 2. mics DATA0–3 + clock, 3. crystal + QSPI XVF↔flash (all done); 4. JTAG (pins 18/20/23/24 → J301); 5. I2S to the amp + MCLK loop; 6. QSPI branch to U701–U704; 7. XVF I2S_DATA1/2 → J701; 8. ESP32 USB D±; 9. PRG_*, GPO_R/G, INT_N, slow control.
- **Inter-IC signals** (2026-11-20; full list word for word in archive-002): crystal and QSPI XVF↔flash done 2026-11-21. Left: QSPI branch to U701–U704 (branch from the flash end; ESP32-side lines are lower priority, later), I2S XVF→U503 amp + MCLK_LOOP 14↔41 (+TP412), PRG_*, GPO_R/G and INT_N → ESP32, slow control (AMP_EN, LED lines, XVF_RST_N ≈64 mm, ESP_EN/BOOT), buck SW nodes and FB dividers (power_v2), speaker SPK_P/N.
- **Mic routes: built 2026-11-20** (`tools/mic_route_2026_11_20.py`, geometry frozen in its JSON; detail word for word in archive-002). A 1 mm lane between DATA2 and DATA0 is kept for SPI_MISO (pin 47 → TP403).
- **XVF main USB pair: routed 2026-11-19** (`tools/usb_main_route_2026_11_19.py`; detail word for word in archive-002): 0.25/0.15 mm (≈92 Ω by formula; **confirm with JLC's impedance calculator**), 30.46 mm, stitching caps C323–C326; no USB net class yet (needs the project closed).
- **East-side escape: built 2026-11-21** (`tools/east_escape_2026_11_21.py`, JSON-frozen; detail word for word in archive-002): pins 16–30 into the cap column, +0V9 F.Cu jumpers under the module, QSPI D3/CLK hop on F.Cu (pin 6 jogs 0.11 mm east).
- **JTAG: routed 2026-11-21** (`tools/jtag_route_2026_11_21.py`; detail word for word in archive-002): J301 reordered to the chip's lane order (pin 6 TDI … 2 TCK); one via each; RST_N branch to R703. Left: RST_N to R303/U302, TP302–TP306. User hand edits kept: MIC_DATA1 straight run (mic JSON), +1V8 to J301/HOP1 (frozen in power_v2).
- **I2S + MCLK: routed 2026-11-21** (`tools/i2s_mclk_route_2026_11_21.py`, coordinates in the script; `--place` moved C310/C302 and their pin 8/12 stubs in the east JSON; plan `verification/i2s-plan-2026-11-21/`, renders `i2s-route-2026-11-21/`). DATA0/LRCK/BCLK leave pins 9/10/13 straight, B.Cu NW, F.Cu hop across the NE mic pair, B.Cu west along U502, F.Cu into U503 pins 1/14/16: 26–31 mm, 3 vias each. MCLK: the user's path, north via 0.37 mm clear of XOUT (14.5 mm, 2 vias). BTN_MUTE_N: stub + via north of pin 11 only. TP409–TP412 not connected (test-pad pass).

## To do (agreed, not yet done)

1. **Escape and signal-routing pass** (deferred by the user): count the signals leaving each side of the rotated XVF3800, widen the cap-row gaps and the flash/crystal spacing to fit; XVF INT_N/GPO_R/GPO_G reach ESP32 pins 8–10 by B.Cu ending in a via in the ESP32 pad; later reassign ESP32 GPIOs so its north-row J701 signals come from the south row (needs a call on UART0 as console).
2. Left for that pass (power side): pin 42 (+0V9) to C306 must jog round the MIC_CLK via south of pin 43 (or stub to the paddle); pins 40 (AMP_EN) and 42 each need a 0.05 mm jog past the MCLK via south of pin 41; XVF3800 +0V9/+3V3 pin fan-out on the west and south sides (pins 4/12/34/42/49/57 +0V9 and 38/52 +3V3 not on a plane; north caps C301/C302 have no plane under them), C313/C314 (+3V3 over the +1V8 band), power test pads (TP201–TP205, TP301, TP307).

## Open questions

- Stock XVF firmware: is I²C on pins 44/45 ever a master? Are the GPO pins active high?
- TS5A3166 off-capacitance (18–19 pF per QSPI line) at the XVF boot clock; fallback 0 Ω/DNP split.
- TS24CA stem protrusion (0.31 mm) and anchor pads vs `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1.
- Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) vs JLC rules; missing/unaligned 3D models (TPS2121, RGB LED, ESP32 offset).
- OV trip at 5.57 V could trip on a charger at the 5.5 V USB limit.
- XTAG4 at 1.8 V (and the JST-to-XMOS adapter); ESP32-written `xflash` image boot, to verify on the first board.

## Next steps

1. Next: the QSPI branch to U701–U704 (from the flash end), J701 I2S (hop to F.Cu before the SE mic pair, y 122.6–123.2), ESP32 USB. JTAG leftovers (RST_N west, TP302–TP306) and BTN_MUTE_N (from its via to SW401) go with the slow-control group; I2S/MCLK test pads TP409–TP412 with the test-pad pass.
2. Escape plan and signal routing (to-do above); reference/label placement last (user's call).
3. Recheck LCSC/JLC stock before ordering.

## Archive

2 archive files (2026-11-03 to 2026-11-20); index in `AGENTS.archive-index.md`.
