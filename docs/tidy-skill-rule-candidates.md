# kicad-schematic-tidy: candidate rules

Rules proposed from your Mindspark review changes (presentation only; creation rules are in
`schematic-creation-rule-candidates.md`), now in `~/.agents/skills/kicad-schematic-tidy/`. Status: **proposed**, **approved** or **dropped**.

**2026-11-10: C1–C6 approved and applied.** Skill steps are now 0 symbol compaction (C6 crossing
trigger), 1 circuit structure (C3, C5, C6), 2 connection tidying, 3 sheet organisation (C4 headings),
4 overview sheets (C1, C2, C4). Checkers shipped: `scripts/check_wiring.py` (native version of
`tools/check_floating.py`) and `scripts/measure_boxes.py`.

## From review changes

### C1. Fit overview sheet blocks to their pins (approved)
Source: change 1, 2026-11-10 (overview blocks were unnecessarily big).
- Treat a sheet block like a Step 0 symbol body: no avoidable empty space.
- Width = widest left pin name + 100 mil + widest right pin name, rounded up to 100 mil, with a
  small minimum (600 mil used) so a pin-less block still reads as a block.
- Height = pin rows at 100 mil, plus one 100 mil row above the first pin and below the last.
- Replaces SKILL.md overview rule 1 ("Keep one block width across the sheet").

### C2. Box each overview sheet block (approved)
Source: change 1, 2026-11-10.
- Every sheet block gets its own titled circuit box; the heading is the sheet's human title.
- The box holds the block, its stubs and labels, and its Sheetname/Sheetfile fields.
- These boxes follow Step 2 like any circuit box: ≥ 300 mil padding, 200 mil gaps, packed in
  reading order, 100 mil from the inner border. The loose-items box is packed with them.
- Replaces "Sheet blocks are not circuit boxes, so Step 2's box padding and 200 mil packing do
  not apply to them" and overview rule 4 (columns).

### C3. Decoupling caps as one bank per circuit box (approved)
Source: change 2, 2026-11-10 (bypass caps scattered next to each IC, each with its own rail and GND).
- Put a box's decoupling caps together in one row at 300 mil pitch, not one cap beside each IC.
- Draw each rail once: adjacent caps on the same rail share one horizontal wire with a single
  power symbol on the run's first cap; the GND side likewise shares one wire and one GND symbol.
- Junction dots on every tee of the shared wires (the first cap's corner counts: lead, wire and
  power symbol meet there).
- A cap on a different rail starts a new top run but can keep the shared GND wire.
- Name which IC each cap serves in its `use` field, so layout still places it at that pin.
- Caps with a circuit role (soft start, CT, feed-forward, timing) stay with their circuit.

### C4. Plain, short box headings (approved)
Source: change 2, 2026-11-10.
- Box headings in regular weight, not bold (same 1.524 mm size).
- On the overview, headings are short names (e.g. "USB-C power", "ESP32 I/O"); the block's own
  name and file fields already identify the sheet.

### C5. No floating passives (approved)
Source: change 3, 2026-11-10 (dividers, pull-ups and series resistors joined only by labels).
- Every passive is wired to the component pin or hierarchical port it serves. A label may carry
  the net on to other boxes, but it never replaces the wire to the part.
- Exempt: parts with every pin on a rail (decoupling caps, rail filters such as a ferrite and its
  cap). A filtered supply that feeds an IC pin gets its own power symbol so it counts as a rail.
- Techniques that kept it planar on Mindspark:
  - tee at the pin's lead end, with the part hanging down and the label continuing;
  - in line with the pin (series resistors at each mic pin);
  - adjacent shunts on pins 100–200 mil apart are staggered: the lower pin's part hangs from
    the near node, the upper pin's lead runs past the lower label to a far node;
  - a feedback divider sits beside the output node, with the FB route dropping below the IC;
  - when the IC's pins are too dense, attach to another component in the same circuit (the
    ESP32 EN RC and BOOT pull-up hang on their buttons).
- Any exception is listed with its reason. A checker reports floating passives
  (Mindspark `tools/check_floating.py`).

### C6. Wires, not repeated labels, inside a box (approved)
Source: change 4, 2026-11-10 (connector and ESD array joined only by labels a few mm apart).
Philosophy: wire connections make the schematic easier to read.
- Parts in the same box that share a net are wired together. Labels are for leaving the box
  (to another box, sheet or a dense IC's pins); a net should not be labelled twice in one box.
- A net may keep its name: a local label can sit on the wire (its text sits above the line).
  A hierarchical label goes at a line end, since its outline would sit across the wire.
- Patterns that worked: lines straight across when pins line up (pick the IC pin mapping that
  makes them line up, e.g. ESD channel order); test pads at line ends or teed off a line; one
  shared wire (riser + run) for a signal fanned out to several parts, tapped at each part;
  a row-to-row return wire in the gap between rows; moving a part into the box it talks to.
- When a symbol's pin layout makes its support parts impossible to wire without crossings
  (e.g. four dividers on 100 mil control pins), redraw the symbol (Step 0) so they fit.
- Exceptions only where a planar wired route does not exist, each listed with its reason; a
  checker flags any net labelled twice in one box.

## Gaps from the first Mindspark run

Covered by the 2026-11-10 skill update:
- Tall IC breaking strict rows on A4 → Step 3 rule 1 (reorder, then bottom-left packing, recorded).
- Native-plot padding/gap checker → `scripts/measure_boxes.py`.
- Generated schematics → Workflow bullet (rules in the generator, overwrite guard, netlist proof).
- Labels at dense IC pins and recording exceptions → Step 1 rule 5, Step 2 rule 5.
- Round generated coordinates to the grid → Workflow generated-schematic bullet (snap at write time).
