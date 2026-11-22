<!-- agents-md: v3 · current-state · ≤2000 words · history in AGENTS.archive-*.md · index in AGENTS.archive-index.md -->
# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched). Full detail as of 2026-11-18 (component values, power budget, XVF/ESP pin maps, J701 pinout, programming paths, sourcing links) is word for word in `AGENTS.archive-002.md`; grep it rather than guessing.

## What this is

- **Company: MindSpeak** (mindspeakai.org). "Mindspark" survives only in identifiers (folder, `mindspark_rev1`, KiCad library `Mindspark`); use MindSpeak in anything people read.
- USB voice front-end: **XMOS XVF3800** (stock USB firmware, square mic build), 4 × IM69D129 mics, MAX98357A speaker amp, **ESP32-S3-WROOM-1U-N16R8** helper, two USB-C (main = XVF, ESP32), WS2812 ring. CM5 host is rev 2.
- **Prototype**: thin stock is fine; don't flag low stock. Designed from datasheets; XMOS XK-VOICE-SQ66 (`incoming/xk_voice_sq66/`, XMOS licence) is the reference for mic wiring and pin roles.
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (weasyprint in `~/.local/venvs/weasyprint`). **Diagrams:** `docs/diagrams/` 01–08 (block, power tree, XVF connections, XVF pin map, audio, mics, ESP32, programming); sources in `docs/diagrams/src/`.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, `main`. `.gitignore` leaves out KiCad backups, audio clips, `incoming/`. Groups 1–3 committed and pushed 2026-11-22. `PCB/mindspark_rev1-backups/` stays untracked.
- **Status 2026-11-22 (evening):** schematic done (ERC 0; 11 duplicate test pads removed, TP205 last). Every link routed: **DRC 0 unconnected, parity 0, no shorts**; left only the old mic footprint items, silk, and 13 cosmetic `lib_footprint_mismatch` on the round test pads. Signals are now the user's hand routing, frozen (see Decisions); power_v2 rebuild takes ~30 s. Groups 1–3 committed; groups 4–6, user edits and LED arcs committed and pushed 2026-11-22 (7a8e60b). Backups: committed board + sheets `mindspark_rev1-backups/pre-breakout-2026-11-22/`; the user's hand-edited board `mindspark_rev1-backups/user-hand-edits-2026-11-22/`.

## Files and tools (`PCB/mindspark_rev1/`, KiCad 10)

- KiCad's `pcbnew` Python segfaults here: the board is edited as S-expressions (`tools/sexpr.py`, `tools/place_tidy.py` `Part`). Each change is a dated script in `tools/` (moves, cap moves, `clear_routing_*`, `power_planes_2026_11_18.py`). Run them with the PCB editor closed; `kicad-cli pcb drc --schematic-parity --refill-zones --save-board` fills and checks.
- Schematic: generator retired; edit sheets in place (`tools/sch_tidy_2026_11_12.py` is the example; `verification/tidy-record.md`).
- Library: `PCB/libraries/` (`Mindspark`, project-only, `${KIPRJMOD}/../libraries/...`; `parts-map.json`). Sources: KiCad built-in first, then easyeda2kicad (`~/.local/venvs/easyeda2kicad`), vendor CAD where it matters. XVF3800 uses `Mindspark:XVF3800-QF60B-C` (5 paddles), never the stock QFN-60.
- Routing: `tools/jog_router.py` (one-layer jog router, used by power_v2) and `tools/grid_router.py` (two-layer A* grid router with via and turn costs, for the long slow nets). Analysis: `route_render.py` (zoomed layer view with part hints), `power_render.py`, `power_drop.py`, `zone_render.py`, `escape_map.py`; results in `verification/`.
- BOM and sourcing: `bom/` (sourcing notes with every LCSC link).

## Decisions in force

- **Power:** USB-C main or ESP → TPS2121 priority mux (main wins) → +5V; TLV62569 bucks for 0.9 V and 3.3 V, TLV75518 LDO 1.8 V; TPS22918 switches for amp and LED ring. Values in archive-003.
- **Audio:** MAX98357A TQFN-16 only; no codec, no jack. Mics in the XMOS square order (66 mm square, top side), one ferrite + 10 µF + 1 µF per mic.
- **ESP32 role:** USB on J102; reads XVF LED_R/G and INT_N; drives the mute LED; writes the XVF flash (path B) through switches U701–U704 (SW701 = PRG_EN; 0 Ω links R706–R709 cut them off). Path A: XTAG4 on the 1.8 V JTAG header. Pin list in archive-003.
- **Breakout:** J701 2×12 2.54 mm SMD header (ESP GPIO1–9 ADC1 pins, UART0, both I²C buses with shunt links, XVF INT_N, I2S_DATA1/2, power). Other XVF spares on pads.
- **Assembly:** JLCPCB fabricates and assembles everything, both sides. Fine-pitch QFN/USON OK; **no ball-grid packages**. Prefer SOT-23-size or smaller; passives 0402 JLC Basic first (0603/0805/1206 only for 10/22/47 µF).
- **Parts kept:** list (USB-C, ESD, TVS, inductors, crystal, flash, JST, buttons, speaker) in archive-003.
- **ERC:** 0 errors (justified warnings allowed); currently 0/0.
- **Board:** 74 × 74 mm, 4 layers (In1 GND, In2 power), centre (146.558, 98.679), 0.3 mm copper-to-edge. JLC rules: min track/clearance 0.1, via 0.45/0.2; Default class 0.15/0.15; Power class 0.4 with 0.6/0.3 vias.
- **Hand edits are suggestions** (user 2026-11-22): never commit the user's KiCad hand edits; rebuild their intent in the dated scripts from the committed board. Small nudges of neighbouring lines/vias to make room need no asking (user 2026-11-22).
- **Signal copper frozen from the user's hand routing** (2026-11-22, `tools/user_edits_2026_11_22.py`): `--snapshot` stores every track/via of every non-power net from the board as saved into `tools/user_routing_2026_11_22.json` (LED DOUT links and one-sided vias left out); power_v2 lays it first and every signal pass skips those nets (`FROZEN`), so groups 1–6 and the fixed signal scripts now only supply power pieces. Power rails (`POWER` set) stay generated. User power pieces kept as drawn: C802/C807 cap hops (`CAP_HOPS`), R106–R112 GND run (`GND_DIVIDER`), R401 and C301 vias; the +3V3 jog past XVF_INT_N is in `xvf_escape`. Placement (C602, all test pads at the user's spots, `PLACE`) is applied by running the script without arguments. Re-snapshot only after a new hand-routing session (it overwrites the JSON).
- **LED chain as ring arcs** (user 2026-11-22, `tools/led_arcs_2026_11_22.py`, curved tracks allowed here only): DOUT → r 27.95 arc just inside the +5V_LED ring (0.175 mm from it) → dive to r 26.47 → short arc into the next DIN, all B.Cu 0.15, no vias; shape searched per link (D803→D804 steps in almost radially past GPIO8's via). Laid after all fixed copper, before the in-pad vias; the LED cap joins follow right after, so GND vias go round them. Nudges to the user's routing there (`EDITS`/`VIA_MOVES`): UART_TX/RX vias 0.35 mm in + R608 line 0.27 mm down, GPIO1 via 0.1 mm, GPIO2 via + loop pulled in, GPIO8 via 0.15 mm; U103 flange via (167.45, 116.5) → (167.4, 116.45) in power_v2.
- **Nothing is locked** (user 2026-11-22): pin orders, frozen routes, power wiring and placements can all change; propose the change and get a yes before building.
- **Placement:** user's rules and current spots word for word in archives 002/003; XVF3800 on the bottom under the ESP32, rotated 90° CCW.
- **Power planes** (`power_v2`): In1 solid GND; In2 +3V3 background with +5V arms, +0V9 island under the XVF3800, +1V8 east band, VBUS strips; +5V_LED B.Cu ring r 28.7. **No plane cuts for signals.** Detail in archive-003.
- **Routing style: jog routing** (user 2026-11-18): 0/45/90° runs with 45° jogs, ends on pad/via centres, no staircases, slivers or right angles. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (GND exempt). **power_v2 rebuilds every track**; fixed signal routes come from dated scripts laid first, and new signal routes go in the same way. Detail in archive-003.
- **Vias in pads** (epoxy-filled, capped): centred on the pad, count by current; a blocked pad gets one small via beside it on a stub. Detail in archives 002/003.
- **Routing done so far** (detail word for word in archive-004): built routes (XVF main USB pair 0.25/0.15 mm, ≈92 Ω by formula, **confirm with JLC's calculator**; mics; east escape; JTAG; I2S + MCLK; flash switches; ESP32 USB pair on F.Cu, which walls the module's south side), groups 1 (`local_hookups`), 2 (`xvf_escape`, pin 6/7 user edit rebuilt), 3 (`inter_ic`, grid router). Each is a dated script in `tools/`, laid by power_v2.
- **Low-priority routing is winged** (user 2026-11-22): no drawings or pre-agreed plans; show results per group; slow signals as parallel bundles where possible; no vias under USB pairs or mic lines; the order only sequences the work, reopening a route costs nothing.
- **3D models** (2026-11-22, `tools/models_3d_2026_11_22.py`, board and library footprints): J301 and SW701 models turned 180°; side switches SW401/402/603 (TS24CA) and SW701 (MSK12C02) were never aligned, now solved with `libraries/tools/model_align/align.py` (TS24CA 1.05 mm out and lifted 0.87 mm; MSK12C02 0.5 mm out); U401 and D402 got EasyEDA models (C2999380, C601684; D402 turned 180° to match datasheet p.2). J501 checked correct. Renders in `verification/models-3d-2026-11-22/`. Pin 1 checked on U301, U503, U601, Y301, D101, Q701, SOT-23s.
- **Test pads** (user 2026-11-22): uniform 1 mm round (`Mindspark:TestPoint_Pad_D1.0mm`), top or bottom, placed where comfortable; labels later; duplicates removed (`tools/test_pads_2026_11_22.py`: TP301–307 = J301 pins, TP201–203 = J701 rails, TP205 GND). Kept: TP204 (+0V9), TP401–412, at the user's spots (`user_edits` `PLACE`); power_v2's spot search (`tools/test_pad_place_2026_11_22.py`) only runs when there is no snapshot. UART0 stays the J701 console; IO3 may take GPIO1 (ADC1 kept); never put the J701 I²C pull-ups on IO45 or IO46.
- **Groups 4–6** (2026-11-22, `tools/breakout_2026_11_22.py`): the grid-router batches stay in power_v2 for a board without a snapshot; with the snapshot they are empty (the user routed J701 by hand). **LED ring reversed** (`tools/led_ring_reverse_2026_11_22.py`): D802↔D812 … D806↔D808 with their caps C8xx, so each DOUT faces the next LED's DIN.

## To do (agreed, not yet done)

- Nothing open on routing.

## Open questions

- Stock XVF firmware: is I²C on pins 44/45 ever a master? Are the GPO pins active high?
- TS5A3166 off-capacitance (18–19 pF per QSPI line) at the XVF boot clock; fallback 0 Ω/DNP split.
- TS24CA stem protrusion (0.31 mm) and anchor pads vs `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1.
- Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) vs JLC rules.
- **Library builder drifted:** `PCB/libraries/tools/build_libraries.py` no longer reproduces the committed `Mindspark.pretty` (27 footprints differ, and it would drop `TestPoint_Pad_D1.0mm`). Never rerun it as is; edit library files from dated scripts. Bringing it back in line is open.
- OV trip at 5.57 V could trip on a charger at the 5.5 V USB limit.
- XTAG4 at 1.8 V (and the JST-to-XMOS adapter); ESP32-written `xflash` image boot, to verify on the first board.

## Next steps

1. Reference/label placement last (user's call). Recheck LCSC/JLC stock before ordering.

## Archive

4 archive files (2026-11-03 to 2026-11-22); index in `AGENTS.archive-index.md`.
