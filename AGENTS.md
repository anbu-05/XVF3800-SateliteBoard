<!-- agents-md: v3 · current-state · ≤2000 words · history in AGENTS.archive-*.md · index in AGENTS.archive-index.md -->
# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched). Full detail as of 2026-11-18 (component values, power budget, XVF/ESP pin maps, J701 pinout, programming paths, sourcing links) is word for word in `AGENTS.archive-002.md`; grep it rather than guessing.

## What this is

- **Company: MindSpeak** (mindspeakai.org). "Mindspark" survives only in identifiers (folder, `mindspark_rev1`, KiCad library `Mindspark`); use MindSpeak in anything people read.
- USB voice front-end: **XMOS XVF3800** (stock USB firmware, square mic build), 4 × IM69D129 mics, MAX98357A speaker amp, **ESP32-S3-WROOM-1U-N16R8** helper, two USB-C (main = XVF, ESP32), WS2812 ring. CM5 host is rev 2.
- **Prototype**: thin stock is fine; don't flag low stock. Designed from datasheets; XMOS XK-VOICE-SQ66 (`incoming/xk_voice_sq66/`, XMOS licence) is the reference for mic wiring and pin roles.
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (weasyprint in `~/.local/venvs/weasyprint`). **Diagrams:** `docs/diagrams/` 01–08 (block, power tree, XVF connections, XVF pin map, audio, mics, ESP32, programming); sources in `docs/diagrams/src/`.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, `main`. `.gitignore` leaves out KiCad backups, audio clips, `incoming/`. Groups 1–3 committed and pushed 2026-11-22. `PCB/mindspark_rev1-backups/` stays untracked.
- **Status 2026-11-22:** schematic done (ERC 0/0, BOM 59 lines / 203 parts). All copper rebuilt by `power_v2` (now ~4 min: group 3's grid routing). Groups 1–3 done and committed. DRC: only the old footprint errors plus 9 dangling lane ends and 3 one-sided escape vias (continued by group 5); parity clean; 53 unconnected (groups 4–6). Latest backup `mindspark_rev1-backups/pre-xvf-escape-2026-11-22/` (also holds the user's pin 6 hand edit).

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
- **Hand edits are suggestions** (user 2026-11-22): never commit the user's KiCad hand edits; rebuild their intent in the dated scripts from the committed board.
- **Nothing is locked** (user 2026-11-22): pin orders, frozen routes, power wiring and placements can all change; propose the change and get a yes before building.
- **Placement:** user's rules and current spots word for word in archives 002/003; XVF3800 on the bottom under the ESP32, rotated 90° CCW.
- **Power planes** (`power_v2`): In1 solid GND; In2 +3V3 background with +5V arms, +0V9 island under the XVF3800, +1V8 east band, VBUS strips; +5V_LED B.Cu ring r 28.7. **No plane cuts for signals.** Detail in archive-003.
- **Routing style: jog routing** (user 2026-11-18): 0/45/90° runs with 45° jogs, ends on pad/via centres, no staircases, slivers or right angles. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (GND exempt). **power_v2 rebuilds every track**; fixed signal routes come from dated scripts laid first, and new signal routes go in the same way. Detail in archive-003.
- **Vias in pads** (epoxy-filled, capped): centred on the pad, count by current; a blocked pad gets one small via beside it on a stub. Detail in archives 002/003.
- **Priorities are scaffolding** (user 2026-11-22): the order only sequences the work; reopening a route costs nothing. Done: XVF USB, mics, crystal + QSPI, JTAG, I2S + MCLK, flash switches, ESP32 USB, groups 1–3.
- **Remaining-net order** (scan 2026-11-22: 169 gaps, 82 nets): 1. local hookups (buck SW/FB, mic resistor→mic and mic supply filters, U103 setting parts, USB CC, speaker out, button/LED locals); 2. XVF3800 escape (power fan-out, then a stub + via out for every signal pin, west side hardest); 3. fixed inter-IC (RST_N + PRG_EN east→west, INT_N/GPO_R/G, AMP_EN, ESP_EN/BOOT, MUX_ST, LED_EN/DATA, east buttons, USER_LED_DATA); 4. LED ring chain D801→D812 (F.Cu hop at each mic diagonal); 5. breakout + test pads; 6. power test pads.
- **Low-priority routing is winged** (user 2026-11-22): no drawings or pre-agreed plans for groups 1–6; show results per group. XVF decaps may move ≤ ~0.5 mm (stay ≤ ~2 mm from their pin) so fan-out stays on B.Cu, going up to F.Cu only clear of the ESP32. Slow signals run as parallel bundles at 0.3 mm pitch (north to test pads, south to J701, east to edge parts), fanning out near their ends; bundles take F.Cu where they cross In2 island edges; no vias under USB pairs or mic lines.
- **Group 1 local hookups** (2026-11-22, `tools/local_hookups_2026_11_22.py`, laid by power_v2 after the U103 flanges, before the vias in pads; renders `verification/local-hookups-2026-11-22/`): 68 jog-routed links on F.Cu plus hand-laid pieces: U103 divider mid links down the 0.45 mm column gaps (CP2/OV2/OV1; PR1 round the east), VBUS_MAIN tops R109.2/R105.2 by in-pad vias + B.Cu strap to the pin 7 flange via, U302 MR north round the chip with U302.2's GND via between its pad rows (LED ring under pin 2). `tools/resistor_swaps_2026_11_22.py` swapped R602/R604, R101/R102, R103/R104, R405/R406 to uncross their links.
- **Group 2 XVF escape** (2026-11-22, `tools/xvf_escape_2026_11_22.py`, laid by power_v2 after group 1; renders `verification/xvf-escape-2026-11-22/`): all XVF power joined. +0V9 pins stub into their paddles; west caps C307/C312 and south caps C305/C311/C317 by straight traces; C306 and C308 by in-pad vias into +0V9 island lobes (power_v2 ZONES: south lobe stepped round the MIC_CLK/MCLK vias, west lobe to y 98.1); pin 30/C313/C314 strap south to a +3V3 via at (151, 109); C302 GND via north of its pad; R401/C401 +3V3 routed. `tools/xvf_cap_nudge_2026_11_22.py` moved C305 +0.15, C317 +0.5 mm east. Signals: 9 south lanes (pins 32–45) at 0.3 mm pitch on B.Cu, ending at y 108.9; INT_N/SQ_NLIN/I2S_DATA2 west on B.Cu between C308/C312, ending at x 136.2; GPO_G, GPO_R, MISO, MOSI end in vias (F.Cu onward). Parallel 45° jogs at 0.3 mm pitch need a 0.125 mm stagger.
- **Pin 6/7 escape** (user's hand edit 2026-11-22, rebuilt in `xvf_escape` + `east_column`): pin 4's feed to C301 0.1 mm west; SPI_CS_N via (145.308, 93.675), SPI_MOSI via (145.81, 93.28).
- **Group 3 inter-IC** (2026-11-22, `tools/inter_ic_2026_11_22.py`, routed by power_v2 after all power copper with `grid_router.py`; renders `verification/inter-ic-2026-11-22/`): all 28 legs routed, 0.15 mm, 65 vias, machine-routed (not bundled). Via cost 10 mm of track; the four nets that get boxed in (GPO_R, AMP_EN, BTN_MUTE_N, ESP_BOOT) go first; power_v2 rips up and retries with failures first if anything fails. The ESP32 underside keep-out does not apply to these signals.
- **Group 5 calls** (winged): swap the JTAG (TP302–306) and XL (TP405–408) test-pad rows; put TP411/TP412/TCK pads on their routes (no long clock stubs); UART0 stays the J701 console; IO3 may take GPIO1 (ADC1 kept). Never put the J701 I²C pull-ups on IO45 (VDD_SPI strap) or IO46.
- **Built routes** (detail word for word in archives 002/003): XVF main USB pair 0.25/0.15 mm (≈92 Ω by formula, **confirm with JLC's calculator**), mic pairs, east escape, JTAG to J301, I2S + MCLK, flash switches (`prog_switch_route_2026_11_22.py`).
- **ESP32 USB pair** (2026-11-22, `tools/esp_usb_route_2026_11_22.py`, laid by power_v2; renders `verification/esp-usb-route-2026-11-22/`): top layer all the way, 0.25/0.15 mm, D− 50.7 / D+ 52.6 mm (full speed). Starts at J102 B7/B6 (A pins in the wrong order; A↔B by B.Cu jumpers, J101's turned 180°); straight through U102 (NC pins 9/7 tied to D−/D+ by `sch_esp_usb_2026_11_22.py` + `esp_usb_nets_2026_11_22.py`), GND via between the lines east of pin 8; between D102's pads, south at x 122.2/122.6, east below the module, into R606/R605 from below. **+5V trunk hop** (`HOP_5V_*`): 1.8 mm B.Cu strap at x 127.6, 2 + 2 vias, where no mic line runs on B.Cu (user). The user's hand edits for this (PRG_EN, U102 GND) were not needed.

## To do (agreed, not yet done)

Work the remaining-net order above. Notes per group:

1. Group 4: LED ring chain D801→D812. Group 5: continue the group 2 lane ends / escape vias (incl. SPI_CS_N's via) to J701 and the test pads; INT_N's J701 and RST_N's TP304 branches. North-row ESP pins (GPIO1/2, UART, I²C) must get round the module; free pins are only IO3/IO45/IO46 (IO35–37 lost to octal PSRAM).

## Open questions

- Stock XVF firmware: is I²C on pins 44/45 ever a master? Are the GPO pins active high?
- TS5A3166 off-capacitance (18–19 pF per QSPI line) at the XVF boot clock; fallback 0 Ω/DNP split.
- TS24CA stem protrusion (0.31 mm) and anchor pads vs `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1.
- Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) vs JLC rules.
- **3D model check** (2026-11-22, read-only render of a copy): missing: U401 (stock `Winbond_USON-8-2EP_3x4mm` STEP not in KiCad 10), D402 (TOGIALED 1615, no model). Wrong: J301 JST 7-pin turned 180° (leads at edge, opening inward); J501 JST 2-pin likely tipped 90° (opening up); SW701 MSK12C02 slider faces into the board (180°). Pin 1 checked OK on U301, U503, U601, Y301, D101, Q701, SOT-23s; U103 too small to confirm. Fix after the layout session (touches the board file).
- OV trip at 5.57 V could trip on a charger at the 5.5 V USB limit.
- XTAG4 at 1.8 V (and the JST-to-XMOS adapter); ESP32-written `xflash` image boot, to verify on the first board.

## Next steps

1. Group 4 (LED ring chain), then groups 5–6. Group 3 could be tidied into bundles later if the user wants.
2. Reference/label placement last (user's call). Recheck LCSC/JLC stock before ordering.

## Archive

3 archive files (2026-11-03 to 2026-11-22); index in `AGENTS.archive-index.md`.
