<!-- agents-md: v3 · current-state · ≤2000 words · history in AGENTS.archive-*.md · index in AGENTS.archive-index.md -->
# Voice satellite (MindSpeak)

Earlier history: `/home/anbu/Documents/Codex/2026-10-19/i-h/AGENTS.md` and `outputs/` (leave untouched). Full detail as of 2026-11-18 (component values, power budget, XVF/ESP pin maps, J701 pinout, programming paths, sourcing links) is word for word in `AGENTS.archive-002.md`; grep it rather than guessing.

## What this is

- **Company: MindSpeak** (mindspeakai.org). "Mindspark" survives only in identifiers (folder, `mindspark_rev1`, KiCad library `Mindspark`); use MindSpeak in anything people read.
- USB voice front-end: **XMOS XVF3800** (stock USB firmware, square mic build), 4 × IM69D129 mics, MAX98357A speaker amp, **ESP32-S3-WROOM-1U-N16R8** helper, two USB-C (main = XVF, ESP32), WS2812 ring. CM5 host is rev 2.
- **Prototype**: thin stock is fine; don't flag low stock. Designed from datasheets; XMOS XK-VOICE-SQ66 (`incoming/xk_voice_sq66/`, XMOS licence) is the reference for mic wiring and pin roles.
- **Report:** `docs/report/mindspeak_rev1_report.pdf` (weasyprint in `~/.local/venvs/weasyprint`). **Diagrams:** `docs/diagrams/` 01–08 (block, power tree, XVF connections, XVF pin map, audio, mics, ESP32, programming); sources in `docs/diagrams/src/`.
- **Git:** `git@github.com:anbu-05/XVF3800-SateliteBoard.git`, `main`. `.gitignore` leaves out KiCad backups, audio clips, `incoming/`. Last commit 2026-11-19: power copper v2 (rotation, planes, centred vias in pads, U103 flanges); not pushed.
- **Status 2026-11-19:** schematic done (9 A4 sheets, ERC 0/0, BOM 59 lines / 189 parts, LCSC on every line). XVF3800 group rotated, flash/crystal/LDO moved, power copper rebuilt and re-run with the updated router after the user's hand edits (`tools/power_v2_2026_11_18.py`, renders `verification/power-v2-2026-11-18/`): planes, vias in pads, jog-routed power traces, zones filled; U103 (TPS2121) power pins on F.Cu via flanges since 2026-11-19 (renders `verification/u103-fanout-2026-11-19/`). DRC: only the old mic-footprint errors; parity clean. Signal routing not started. Backups: `mindspark_rev1-backups/mindspark_rev1.kicad_pcb.pre-xvf-rotate-2026-11-18`, `.pre-u103-fanout-2026-11-19`.

## Files and tools (`PCB/mindspark_rev1/`, KiCad 10)

- KiCad's `pcbnew` Python segfaults here: the board is edited as S-expressions (`tools/sexpr.py`, `tools/place_tidy.py` `Part`). Each change is a dated script in `tools/` (moves, cap moves, `clear_routing_*`, `power_planes_2026_11_18.py`). Run them with the PCB editor closed; `kicad-cli pcb drc --schematic-parity --refill-zones --save-board` fills and checks.
- Schematic: generator retired; edit sheets in place (`tools/sch_tidy_2026_11_12.py` is the example; `verification/tidy-record.md`).
- Library: `PCB/libraries/` (`Mindspark`, project-only, `${KIPRJMOD}/../libraries/...`; `parts-map.json`). Sources: KiCad built-in first, then easyeda2kicad (`~/.local/venvs/easyeda2kicad`), vendor CAD where it matters. XVF3800 uses `Mindspark:XVF3800-QF60B-C` (5 paddles), never the stock QFN-60.
- Routing: `tools/jog_router.py` (grid router, 0/45/90° runs with jogs, turn-penalised, pad-centre ends, pulled tight; comparisons in `verification/jog-routing-review-2026-11-18/`; used by `power_v2_2026_11_18.py`, which rebuilds all tracks/vias/zones from scratch). Analysis: `tools/power_render.py`, `power_drop.py`, `zone_render.py`, `escape_map.py` (`--edge-sensitive`, `--board=`). Results in `verification/`: `power-review-2026-11-17/`, `power-planes-2026-11-18/`, `escape-analysis-2026-11-18/`.
- BOM and sourcing: `bom/` (sourcing notes with every LCSC link).

## Decisions in force

- **Power:** either USB-C feeds a TPS2121 priority mux (main wins, XCOMP at ≈4.4 V, OV 5.57 V, ILIM ≈3.2 A) → +5V. TLV62569 bucks for 0.9 V (XVF core) and 3.3 V; TLV75518 LDO 3.3 → 1.8 V. TPS3808G33 reset supervisor kept. TPS22918 switches for amp (EN = XVF pin 40) and LED ring (ESP32 GPIO47). 5 V budget ≈0.7 A typ / 2.7 A peak.
- **Audio:** MAX98357A TQFN-16 only; no codec, no jack. Mics in the XMOS square order (66 mm square, top side), one ferrite + 10 µF + 1 µF per mic.
- **ESP32 role:** USB on its own USB-C; reads XVF LED_R/G and INT_N; drives mute LED; can write the XVF flash (path B) through four TS5A3166 switches selected by slide switch SW701. Path A is XTAG4 on the 1.8 V JST JTAG header. No SPI-slave boot.
- **Breakout:** J701 2×12 2.54 mm SMD header (ESP GPIO1–9 ADC1 pins, UART0, both I²C buses with shunt links, XVF INT_N, I2S_DATA1/2, power). Other XVF spares on pads.
- **Assembly:** JLCPCB fabricates and assembles everything, both sides. Fine-pitch QFN/USON OK; **no ball-grid packages**. Prefer SOT-23-size or smaller; passives 0402 JLC Basic first (0603/0805/1206 only for 10/22/47 µF).
- **Parts kept:** Hroparts TYPE-C-31-M-12 ×2, TPD4E05U06DQAR ESD ×2, SMF5.0A TVS, SRP4020TA-2R2M inductors, YXC 24 MHz crystal, W25Q32JVUUIQ flash (centre pad floating, no vias under it), JST PH speaker and JTAG connectors (plus solder pads), TS24CA side buttons (mute/action/user) and TS-1187A top buttons. Speaker CS45-05D13-24-1X (not ordered).
- **ERC:** 0 errors (justified warnings allowed); currently 0/0.
- **Board:** 74 × 74 mm, 4 layers (In1 GND, In2 power), centre (146.558, 98.679), 0.3 mm copper-to-edge. JLC multilayer rules: minimum track/clearance 0.1, via 0.45/0.2; Default class 0.15/0.15; Power class 0.4 with 0.6/0.3 vias; USB pair 0.2/0.25 (not impedance-sized yet).
- **Placement** (user's rules; `tools/place_tidy2.py` second pass, archived first pass must not be rerun): USB-C on left/right edges, JSTs on the top edge, side buttons and LEDs spread on the side edges with their passives in a column inside, M2 holes 12 mm in, test pads in two bottom-side rows, mics at the 66 mm square corners, LED ring on the bottom at r 27.0. Groups are IC-anchored, 0.15 mm courtyard gaps, each cap on the pin its `use` field names. XVF3800 on the bottom directly under the ESP32 module, caps 1.65 mm out, **rotated 90° CCW 2026-11-18** with its caps and U501 group (`tools/xvf_rotate_2026_11_18.py`): USB D± leave the east edge, +1V8 pins 17/26 east, 31 SE corner. Flash U401 group at the chip's NW corner, crystal Y301 group above the north cap row, **LDO U203 + C208/C209 on the bottom at (160.35, 97.0)** (input east, output west). Gaps are still 0.15 mm; widen them in the escape pass. TPS2121 block + LED switch at the bottom right (x 159.5–171.6, y 109.3–120.5) with the VBUS caps at its inputs; TVS diodes stay at the ports. Around U103 (`tools/u103_fanout_place_2026_11_19.py`): C107 in the north row beside C105, C104 west at (165.6, 115.3), C102 standing at (172.85, 116.85), R105–R112 0.5 mm lower.
- **Power planes** (`tools/power_v2_2026_11_18.py`): In1 solid GND. In2: +3V3 background; +5V arms (top, link, bottom to y 130.2, tab with the trunk vias at x 131.2–132.4); +0V9 island under the XVF3800, a 1.8 mm neck through the south cap row (over C305) down to L201; **+1V8 band** x 151.4–160 (C318, C315, C316, LDO output, also under the USB exit) with a leg to C317; VBUS_MAIN strip J101 → TPS2121, notched for a small +5V finger (x 170.7–173.3, y 112.9–114.9) that takes U103 pin 8's vias east of the ring; VBUS_ESP strip down the left, along the bottom, up to C103/C104. +5V_LED: 1 mm B.Cu ring at r 28.7 with radial stubs; ring caps linked to their LEDs.
- **Routing style: jog routing** (user 2026-11-18): straight horizontal/vertical runs joined by 45° jogs, not direct free-angle lines; exceptions are the LED ring arcs and its radial stubs. From the user's hand edits: traces end on pad/via centres (last leg 0/45/90 into the centre), no grid staircases or slivers, ~0.3 mm extra room from other copper where it costs little (not long detours). `tools/jog_router.py` does all of this now (falls back to any point in the pad when the centre is unreachable); the hand-edited board is kept as `mindspark_rev1-backups/mindspark_rev1.kicad_pcb.hand-jogs-2026-11-18`. R303 (µA pull-up) may be thin. ≥ 2 vias 0.6/0.3 per layer change above 0.5 A. No power traces on F.Cu under the ESP32 module (kept for XVF escapes; GND exempt).
- **Vias in pads (2026-11-18, rules 2026-11-19): epoxy-filled, capped (JLC via-in-pad option).** Every SMD pad on a planed rail whose own plane is under its centre gets vias **centred on the pad** (one on the centre; several as a pattern centred on it). Count by current (`PART_AMPS` in `power_v2_2026_11_18.py`): 1 A per 0.6/0.3, 0.5 A per 0.45/0.2; VBUS/TPS2121 path 3 A, amp 1.6 A, LED switch 0.75 A, 3V3 buck 0.45 A in / 0.6 A out, 0V9 1 A, ESP32 0.4 A; GND pads take the rail's current; others one via. Too small for the count: the rest go just outside on a stub (C101, C103, C106, C509). Centre blocked (wrong plane or another net's pad opposite): no via, the pad is routed. Exception: XVF paddles keep the clear spots of their centred row (under ESP32 pad 41). **U103 pins 1/2/7/8** (no via fits under them): each has an F.Cu pour (`FLANGES` in power_v2, solid to the pad, 0.2 mm clearance) out to its own 0.6/0.3 vias: pin 1 +5V 2 W (joins C106), pin 2 VBUS_ESP 3 SW (joins C104/C103), pin 7 VBUS_MAIN 3 E (joins C102/C101), pin 8 +5V 2 NE in the finger. Backup before this: `mindspark_rev1-backups/mindspark_rev1.kicad_pcb.pre-centred-vias-2026-11-19`; renders `verification/via-in-pad-2026-11-19/`.
- **Length-sensitive nets** (escape maps): USB D± (both), mic DATA0–3, JTAG, XVF I2S_DATA1/2. The XVF3800 can only escape on B.Cu inside the module's shadow (In1/In2 are planes, the module's pad rows are too tight on F.Cu); F.Cu under the module is usable (no keepout) but opens only to the west (no pads on the antenna edge).

## To do (agreed, not yet done)

1. **Escape and signal-routing pass** (deferred by the user): count the signals leaving each side of the rotated XVF3800, widen the cap-row gaps and the flash/crystal spacing to fit; XVF INT_N/GPO_R/GPO_G reach ESP32 pins 8–10 by B.Cu ending in a via in the ESP32 pad; later reassign ESP32 GPIOs so its north-row J701 signals come from the south row (needs a call on UART0 as console).
2. USB stitching cap: 100 nF 0402 (C1525) between +0V9 and +1V8 beside the main USB pair where it leaves the +0V9 island on B.Cu (pair goes to F.Cu once clear of the module); alternative discussed: a +1V8 notch under pins 27–30. Not decided.
3. Left for that pass (power side): XVF3800 +0V9/+3V3 pin fan-out to their caps (19 +0V9, 8 +3V3 unconnected), FB301's +0V9 side, C313/C314 (+3V3 over the +1V8 band), flash/crystal grounds (U401.4, Y301 incl. pad 2 which lost its off-centre via, C320/C321), power test pads (TP201–TP205, TP301, TP307).

## Open questions

- Stock XVF firmware: is I²C on pins 44/45 ever a master? Are the GPO pins active high?
- TS5A3166 off-capacitance (18–19 pF per QSPI line) at the XVF boot clock; fallback 0 Ω/DNP split.
- TS24CA stem protrusion (0.31 mm) and anchor pads vs `PCB/libraries/datasheets/TS24CA_C393942.pdf` p.1.
- Fine-pitch footprints (QFN-60 0.4 mm, VQFN-HR, USON-10, TQFN-16) vs JLC rules; missing/unaligned 3D models (TPS2121, RGB LED, ESP32 offset).
- OV trip at 5.57 V could trip on a charger at the 5.5 V USB limit.
- XTAG4 at 1.8 V (and the JST-to-XMOS adapter); ESP32-written `xflash` image boot, to verify on the first board.

## Next steps

1. User checks the rerouted power copper in KiCad and decides the USB stitching cap vs +1V8 notch.
2. Escape plan and signal routing (to-do above); reference/label placement last (user's call).
3. Recheck LCSC/JLC stock before ordering.

## Archive

2 archive files (2026-11-03 to 2026-11-18); index in `AGENTS.archive-index.md`.
