# Schematic generator

The rev 1 schematic is generated. Edit `build_schematic.py` (the circuit, sheet by sheet), not the
`.kicad_sch` files, then rebuild. A hash guard refuses to overwrite sheets that were saved in KiCad
since the last build. Once you start editing in KiCad, stop using the generator for those sheets.

| File | What it does |
|---|---|
| `build_schematic.py` | The circuit: values, LCSC picks (`R_PICKS`, `C_PICKS`, `OTHER_PICKS`), layout. Two passes: build, then measure each box on KiCad's SVG and re-pack |
| `schgen.py` | Generator core: groups, leads, anchors, rows, packing (tidy rules built in) |
| `emit.py` | Writes KiCad 10 files and the root overview |
| `verify_schematic.py` | KiCad netlist and ERC against the intended pin-to-net partition |
| `measure_boxes.py` | Box padding, border and gap checks from the native SVG plot |
| `check_floating.py` | Lists passives not wired to a component pin or port (rail-only parts exempt) |
| `sexpr.py` | S-expression reader/writer (from the PDB project) |
| `place_tidy.py` | PCB: tidies the parts inside the board outline to the 2026-11-12 placement rules (74 mm board, 4 layers, edges, mic square, LED ring). Edits the `.kicad_pcb` directly because `pcbnew` Python segfaults here; `--dry-run` prints the report only |

Close KiCad on this project before rebuilding, then run:

```bash
cd PCB/mindspark_rev1
python3 -I tools/build_schematic.py
python3 -I tools/verify_schematic.py
python3 -I tools/measure_boxes.py
python3 -I tools/check_floating.py
```

Outputs: `verification/` holds the design manifest, netlist, ERC, hashes, tidy exceptions and the
tidy record. `bom/` holds the BOM CSV and the LCSC/JLC stock check.
