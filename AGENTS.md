<!-- agents-md: v3 · current-state · ≤2000 words · history in AGENTS.archive-*.md · index in AGENTS.archive-index.md -->
# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched). Full detail as of 2026-11-18 (component values, power budget, XVF/ESP pin maps, J701 pinout, programming paths, sourcing links) is word for word in `AGENTS.archive-002.md`; grep it rather than guessing.

## What this is

- **Company: MindSpeak** (mindspeakai.org). "Mindspark" survives only in identifiers (folder, `mindspark_rev1`, KiCad library `Mindspark`); use MindSpeak in anything people read.
- USB voice front-end: **XMOS XVF3800** (stock USB firmware, square mic build), 4 × IM69D129 mics, MAX98357A speaker amp, **ESP32-S3-WROOM-1U-N16R8** helper, two USB-C (main = XVF, ESP32), WS2812 ring. CM5 host is rev 2.
- **Prototype**: thin stock is fine; don't flag low stock. Designed from datasheets; XMOS XK-VOICE-SQ66 (`incoming/xk_voice_sq66/`, XMOS licence) is the reference for mic wiring and pin roles.
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (weasyprint in `~/.local/venvs/weasyprint`). **Diagrams:** `docs/diagrams/` 01–08 (block, power tree, XVF connections, XVF pin map, audio, mics, ESP32, programming); sources in `docs/diagrams/src/`.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, `main`. `.gitignore` leaves out KiCad backups, audio clips, `incoming/`. Everything through the 2026-11-23 DRC fixes and lined-up sky arrow labels is committed (not pushed). `PCB/mindspark_rev1-backups/` stays untracked.
- **Status 2026-11-23:** schematic done (ERC 0/0). Board complete: **DRC 0 violations, 0 unconnected, parity 0** after `tools/drc_fixes_2026_11_23.py` and a silkscreen rerun (zones refilled by kicad-cli); committed. Signals are the user's frozen hand routing; power_v2 rebuild takes ~2 min. Backups: before the DRC fixes `mindspark_rev1-backups/pre-drc-fixes-2026-11-23/` (board + `Mindspark.pretty`); older ones `pre-breakout-2026-11-22/`, `user-hand-edits-2026-11-22/`.

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
- **Signal copper frozen** (2026-11-22, `tools/user_edits_2026_11_22.py`): every non-power net comes from the user's hand-routing snapshot `tools/user_routing_2026_11_22.json`, laid first by power_v2 (`FROZEN`); power rails (`POWER`) stay generated; placement in `PLACE`. Re-snapshot (`--snapshot`, overwrites the JSON) only after a new hand-routing session. Detail in archive-004.
- **LED chain as ring arcs** (`tools/led_arcs_2026_11_22.py`, curved tracks allowed here only): B.Cu 0.15 mm arcs DOUT → DIN just inside the +5V_LED ring, no vias. Detail in archive-004.
- **Nothing is locked** (user 2026-11-22): pin orders, frozen routes, power wiring and placements can all change; propose the change and get a yes before building.
- **Placement:** user's rules and current spots word for word in archives 002/003; XVF3800 on the bottom under the ESP32, rotated 90° CCW.
- **Power planes** (`power_v2`): In1 solid GND; In2 +3V3 background with +5V arms, +0V9 island under the XVF3800, +1V8 east band, VBUS strips; +5V_LED B.Cu ring r 28.7. **No plane cuts for signals.** Detail in archive-003.
- **Routing style: jog routing** (user 2026-11-18): 0/45/90° runs with 45° jogs, ends on pad/via centres, no staircases, slivers or right angles. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (GND exempt). **power_v2 rebuilds every track**; fixed signal routes come from dated scripts laid first, and new signal routes go in the same way. Detail in archive-003.
- **Vias in pads** (epoxy-filled, capped): centred on the pad, count by current; a blocked pad gets one small via beside it on a stub. Detail in archives 002/003.
- **Routing history** (built routes, groups 1–6, LED ring reversal `tools/led_ring_reverse_2026_11_22.py`, winged low-priority routing): all done, each a dated script laid by power_v2; detail word for word in archive-004. The main USB pair (0.25/0.15 mm, ≈92 Ω by formula) still needs JLC's impedance calculator.
- **3D models** fixed and pin-1 checked 2026-11-22 (`tools/models_3d_2026_11_22.py`, side switches aligned with `libraries/tools/model_align/align.py`); detail in archive-004.
- **GND pours and stitching** (`tools/gnd_pour_2026_11_22.py`, run at the end of power_v2): F/B.Cu GND pours; 0.45/0.2 stitching vias on a 5 mm lattice (JLC hole density); 0.5 mm pour gap round USB tracks through rule areas (**kicad-cli 10 ignores `.kicad_dru`**, no custom rules); pour islands get a via or a short trace, else are removed, never left floating. Detail in archive-004.
- **Silkscreen** (user 2026-11-22, `tools/silkscreen_2026_11_22.py`, idempotent, own items tagged by uuid prefix `5111c000-2026-1122-`; rerun after anything moves parts): **bottom faces the sky, top faces the table.** Bottom: mic port rings (2.0/3.0 mm) numbered 1–4 (MK501–504 = MIC_DATA0–3), "MindSpeakAI Voice Satellite v1 / rev1 2026-11" on the south edge (renamed by the user 2026-11-23, `BOARD_NAME`), sky labels with arrows for the table-side parts (`SKY_LABELS`, user 2026-11-23 "arrows everywhere": USB MAIN/ESP, XVF RESET, MUTE, ACTION, EN, BOOT, USER, PRG_EN, MUTE LED, XVF LED, PWR LED, USER LED): arrow and label on the part's own centreline, arrow pointing out to the nearest edge; **lined up** (user 2026-11-23): on each edge every tip is at the edge with one shared shaft length, so arrows form a column and labels start on one line; a blocked line stacks its label on two lines or lengthens every arrow on that edge, never leaves the line (USB MAIN/ESP and USER LED are stacked), D801 + chain arrow, IC refs, test pads by net name. Top, kept sparse: function words only on switches/connectors (BOOT, EN, XVF RESET, PRG_EN, MUTE, ACTION, USER, USB MAIN/ESP, SPK, JTAG 1V8, GPIO), no IC/LED/mic refs; refs kept only on R703, R706–R709, R101–R113; J701 names at each pin (north row vertical, south row ≤ 3 chars: XDA/XCL/XD1); J301 pin names under the pins; filled S/N box (kept); "ESP TO XVF FLASH / CUT TO DISCONNECT" by R706–R709. Sizes 1.0 mm (small names 0.8), board name 1.5; every silk stroke ≥ 0.15 mm. SW701 has no ON arrow (direction unknown). Renders `verification/silkscreen_2026_11_23/`.
- **DRC fixes** (2026-11-23, `tools/drc_fixes_2026_11_23.py`, idempotent; edits each library footprint and its board copies alike so the library-mismatch check stays clean): switch pegs (TS24CA, MSK12C02) are non-plated holes; mic pads 1/2/4/5 trimmed 0.75 → 0.688 mm about their centres (Infineon's pattern, datasheet p.13 Fig. 14, leaves 0.088 mm) and the GND ring inner dia 0.985 → 1.01 mm (port hole to copper 0.205); edge-part silk kept ≥ 0.1 mm inside the edge (overhang outlines cut to stubs; LED_0603 edge line 0.735 → 0.6; WS2812 sides 1.6 → 1.35 with a 0.15 mm pin-1 chamfer; D402 pin-1 dot moved in); test pads match the library.
- **Test pads**: 1 mm round `Mindspark:TestPoint_Pad_D1.0mm` at the user's spots (TP204, TP401–412; J301/J701 duplicates removed); excluded from the BOM and the placement file. UART0 stays the J701 console; never put the J701 I²C pull-ups on IO45 or IO46. Detail in archive-004.

## To do (agreed, not yet done)

- Nothing open on routing.

## Open questions

- Stock XVF firmware: is I²C on pins 44/45 ever a master? Are the GPO pins active high?
- TS5A3166 off-capacitance (18–19 pF per QSPI line) at the XVF boot clock; fallback 0 Ω/DNP split.
- TS24CA stem protrusion (0.31 mm) and anchor pads vs `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1.
- Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) vs JLC rules.
- **Library builder drifted:** `PCB/libraries/tools/build_libraries.py` no longer reproduces the committed `Mindspark.pretty` (27+ footprints differ, 8 more edited by the DRC fixes, and it would drop `TestPoint_Pad_D1.0mm`). Never rerun it as is; edit library files from dated scripts. Bringing it back in line is open.
- OV trip at 5.57 V could trip on a charger at the 5.5 V USB limit.
- XTAG4 at 1.8 V (and the JST-to-XMOS adapter); ESP32-written `xflash` image boot, to verify on the first board.

## Next steps

Pre-order steps (from the controller-board comparison 2026-11-23, `stealth_startup/archive/controller-board`):

1. Fab and assembly files: Gerbers, drill, JLC BOM and CPL (test pads excluded); refresh `bom/`; re-export the schematic PDF (from 2026-11-12).
2. JLC placement preview and per-part rotation fixes (both sides; the controller board needed 46), plus a footprint check against JLC's library pads.
3. Order options: JLC04161H-7628 stackup (the board already uses it), epoxy-filled capped via-in-pad, the JLC order-number spot.
4. Confirm the main USB pair impedance with JLC's calculator.
5. Final design review, including the open questions and the top-side LEDs D401/D402/D201 facing the table.
6. Recheck LCSC/JLC stock right before ordering.

## Archive

4 archive files (2026-11-03 to 2026-11-23); index in `AGENTS.archive-index.md`.
