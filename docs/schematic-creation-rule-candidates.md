# Schematic creation: candidate rules

These rules cover creating a schematic: from an agreed architecture to an ERC-clean, sourced,
tidied KiCad schematic. They are drawn from your first schematic prompt and its answers
(2026-11-10). They are kept apart from the tidy-skill candidates
(`tidy-skill-rule-candidates.md`), which only cover presentation.

Status per rule: **proposed**, **approved** or **dropped**.

Source tags:
- [P]: your prompt.
- [A]: your answers to the setup questions.
- [I]: a choice made while implementing, which you did not ask for directly.

## Order of work

### S1. Draw first, pick parts later (proposed) [P]
1. Draw the circuit with values only. Leave exact passive and small-part picks open.
2. Reach the ERC target.
3. Collect every resistor, capacitor and other open part from the finished schematic, and pick
   each one on LCSC. The agent's picks are fine without asking.
4. Tidy the schematic with the kicad-schematic-tidy skill.

### S2. Update everything that describes the design in the same run (proposed) [A]
Diagrams, parts map, library README and AGENTS.md are updated in the same run as the schematic,
not later.

## Structure

### S3. Hierarchical sheets, one function each (proposed) [P] [A]
- The root sheet is an overview of the sheet blocks plus a mechanical box.
- Each child sheet holds one function, for example USB-C power, regulators, main IC,
  peripherals, audio, MCU, MCU I/O and UI.
- Every sheet is A4. Report before any sheet goes to A3.
- A single-unit symbol that is too big to share a sheet gets its own sheet, with its
  peripherals on the next sheet. [I]

### S4. Circuit-separation boxes (proposed) [P]
- Each functional circuit on a sheet gets a titled box.
- Notes go outside the boxes, below them.

### S5. References and fields (proposed) [A]
- **References** are numbered per sheet in hundreds: sheet 1 is R101, C101…; sheet 7 is R701….
- **Fields** follow the controller board: LCSC, MPN, Manufacturer, spec, voltage, tolerance,
  power, use.
  - Rating text on capacitors is small and visible. Everything else stays hidden.
  - `use` says what the part does and, for bypass caps, which part it serves.
- **Value format:** `10k`, `100nF`, `4.7uF`.

### S6. Nets (proposed) [I]
- **Names:** UPPER_SNAKE_CASE. Active-low signals end in `_N`.
- **Rails** are global power symbols. A renamed rail (e.g. `+5V_AMP`) is its own power symbol in
  the project library.
- **Between sheets:** hierarchical labels on the child sheets, matched by sheet pins on the root.
- **PWR_FLAG** only where a rail has no driver that ERC can see.
- **Nets that belong to one feature share a prefix**, e.g. `PRG_*` for the programming path.

## Library and parts

### S7. Library sources (proposed) [A]
- **Source order:** KiCad built-in first, then easyeda2kicad, then vendor CAD where it matters.
- **Built-in parts** are copied into the project library with the LCSC number added.
- **The project uses only its own library**, for symbols, footprints and power symbols.
- **Vendor CAD files** go into `libraries/incoming/`, are cross-checked against the EasyEDA
  version, and are recorded in `sources.json`.
- **Every part is checked pin by pin** against its datasheet before use: numbers, names and
  electrical types. Stock symbols whose pin numbers belong to a different package are rejected.

### S8. Passive defaults (proposed) [A]
- Passives are 0402 and JLC Basic first.
- A larger package is used only where the value or voltage needs it (10 µF, 22 µF, 47 µF here).

### S9. Values from datasheets and reference designs (proposed) [I]
- Every value comes from the part's datasheet or the vendor's reference design.
- Each derived value is recorded with its result: divider ratio, trip voltage, current limit,
  rise time.
- A value the datasheet specifies is kept even when it is a JLC Extended part.
- A value that is not specified may move to the nearest JLC Basic value if the result still
  meets the spec. Record the change.

### S10. Picking and sourcing (proposed) [P] [I]
- Check every pick on LCSC first, then DigiKey, then Mouser.
- Apply the one-step-up rule: take the higher-spec part when it costs the same or less.
- Every BOM line gets an LCSC number.
- The sourcing table links every line to the exact page that was checked, with the date, stock
  and price.

## Verification

### S11. ERC target (proposed) [A]
- 0 errors. Warnings are allowed only with a written justification.
- Run with `kicad-cli sch erc --severity-all`.

### S12. Prove connectivity, not just ERC (proposed) [I]
- Keep a manifest of the intended connection for every pin, then compare it with KiCad's
  exported netlist. Nets must not be missing, shorted or split, and NC pins must stay isolated.
- Run the check after every sheet and again after every tidy or review change.

### S13. Generated schematics (proposed) [P] [I]
These follow from your PDB reference, the fully agent-built pipeline.
- **Deterministic:** fixed UUIDs, so a rebuild with the same input gives the same output.
- **Hash guard:** the generator refuses to overwrite a sheet that has been saved in KiCad since
  the last build. Once you edit a sheet by hand, the generator stops owning it.
- **One place for tidy rules:** they are built into the generator, not applied afterwards.

### S14. Style references (proposed) [P]
- The controller board is the reference for how a person draws: fields, boxes and labels.
- The PDB is the reference for the agent pipeline: generator, verification and tidy record.
