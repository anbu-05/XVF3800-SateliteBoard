"""JLCPCB fabrication + assembly package (user 2026-11-23, pre-order step 1).

Usage (PCB editor closed, board DRC-clean):
    python3 tools/jlc_export_2026_11_23.py

Writes fab/JLCPCB_rev1/:
    gerbers/        11 Gerbers + job file + PTH/NPTH Excellon drill files (what JLC needs)
    assembly/       BOM and CPL in JLC's column format, plus KiCad's raw .pos for reference
    checks/         drill report and maps, DRC/ERC reports, the KiCad BOM it started from
    JLCPCB_rev1_gerbers.zip   upload this as the PCB
    README.md       ordering notes, written by hand, kept across reruns
Then upload assembly/mindspark_rev1_BOM_JLC.csv and assembly/mindspark_rev1_CPL_JLC.csv on the
assembly step. The user checks part rotations in JLC's preview (user 2026-11-23); any fixes go
into ROT_FIX below so a re-export keeps them.

Settings follow JLC's KiCad export guide: Protel extensions, no X2, no netlist attributes,
soldermask subtracted from silkscreen; Excellon in mm, decimal, PTH and NPTH in separate
files, absolute origin. The CPL holds exactly the parts on the BOM (no mounting holes, no test
pads), with JLC's column names and mm units.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(HERE, "..")
BOARD = os.path.join(PRJ, "mindspark_rev1.kicad_pcb")
SCH = os.path.join(PRJ, "mindspark_rev1.kicad_sch")
OUT = os.path.join(PRJ, "fab", "JLCPCB_rev1")

LAYERS = ("F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
          "F.Mask,B.Mask,Edge.Cuts")

# Rotation corrections for JLC's preview, by reference: degrees added to KiCad's angle.
# Found 2026-11-23 from the user's JLC preview screenshots plus a pad-by-pad comparison of
# JLC's own (EasyEDA) footprints against our pads, matching JLC's pin names (K/A, DI/DO, ...).
# How JLC reads the CPL (worked out from the preview): top parts are its footprint turned CCW
# by the CPL angle; bottom parts are mirrored and turned by MINUS the CPL angle, so a bottom
# part at 0/180 comes out flipped and one at 30/60/... comes out crooked (the ring).
ROT_FIX = {
    # top: JLC footprint drawn with pin 1 elsewhere ("BR"/"BL" packages) -> turn 180 or 270
    "J301": 180, "J701": 270, "Q701": 180, "D402": 180,
    "MK501": 90, "MK502": 90, "MK503": 90, "MK504": 90,
    "U101": 270, "U102": 270, "U103": 270, "U501": 270, "U503": 270,
    "U701": 270, "U702": 270, "U703": 270, "U704": 270,
    "U201": 180, "U202": 180, "U302": 180, "U502": 180, "U602": 180, "U801": 180, "U802": 180,
    # bottom ring LEDs: JLC needs 180 - KiCad angle
    "D802": 60, "D803": 120, "D804": 180, "D805": 240, "D806": 300,
    "D808": 60, "D809": 120, "D810": 180, "D811": 240, "D812": 300,
    # bottom ring caps (non-polar, so 180 apart is the same): only the crooked ones
    "C802": 60, "C803": 120, "C805": 60, "C806": 120,
    "C808": 60, "C809": 120, "C811": 60, "C812": 120,
    # bottom flash: JLC's USON-8 footprint lines up pad for pad only a further 90 deg round
    # (the user's preview showed it crossways, pin-1 dot in the wrong corner)
    "U401": 90,
}

# Position corrections (mm, added to the CPL Mid X / Mid Y) where JLC's footprint origin is
# not at our footprint origin. Measured 2026-11-23 from JLC's footprint pads matched to ours
# (unique pad numbers, after ROT_FIX); the user's preview showed both USB-C sockets off the pads.
POS_FIX = {
    "J101": (-1.571, 0.0), "J102": (1.571, 0.0),     # USB-C: JLC origin is 1.57 mm into the body
    "U601": (0.627, 0.0),                             # ESP32 module
    "MK501": (-0.074, -0.074), "MK502": (0.074, -0.074),
    "MK503": (0.074, 0.074), "MK504": (-0.074, 0.074),
    "J301": (0.0, 0.05), "J501": (0.0, 0.075),
}


def run(*args):
    r = subprocess.run(["kicad-cli", *args], capture_output=True, text=True)
    if r.returncode not in (0, 5):          # 5 = DRC/ERC found violations (checked below)
        sys.exit(f"kicad-cli {args[0]} {args[1]} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def expand(refs):
    """'C301-C304,C310' -> ['C301', 'C302', 'C303', 'C304', 'C310']"""
    out = []
    for part in refs.replace(" ", "").split(","):
        m = re.fullmatch(r"([A-Z]+)(\d+)-\1?(\d+)", part)
        if m:
            out += [f"{m[1]}{n}" for n in range(int(m[2]), int(m[3]) + 1)]
        elif part:
            out.append(part)
    return out


def ref_key(r):
    m = re.fullmatch(r"([A-Z]+)(\d+)", r)
    return (m[1], int(m[2])) if m else (r, 0)


def main():
    # rebuild everything except README.md (the hand-written ordering notes)
    g, a, c = (os.path.join(OUT, d) for d in ("gerbers", "assembly", "checks"))
    for d in (g, a, c):
        if os.path.exists(d):
            shutil.rmtree(d)
    if os.path.exists(os.path.join(OUT, "JLCPCB_rev1_gerbers.zip")):
        os.remove(os.path.join(OUT, "JLCPCB_rev1_gerbers.zip"))
    for d in (g, a, c):
        os.makedirs(d, exist_ok=True)

    # 0. checks first: the package is only worth making from a clean board
    run("pcb", "drc", "--schematic-parity", "--refill-zones", "-o", os.path.join(c, "drc.rpt"), BOARD)
    run("sch", "erc", "-o", os.path.join(c, "erc.rpt"), SCH)
    drc = open(os.path.join(c, "drc.rpt")).read()
    erc = open(os.path.join(c, "erc.rpt")).read()
    clean = ("Found 0 DRC violations" in drc and "Found 0 unconnected pads" in drc
             and "Errors 0" in erc)
    print("DRC/ERC clean" if clean else "WARNING: DRC/ERC not clean, see checks/")

    # 1. Gerbers + drill
    run("pcb", "export", "gerbers", "-l", LAYERS, "--no-x2", "--no-netlist",
        "--subtract-soldermask", "-o", g + "/", BOARD)
    run("pcb", "export", "drill", "--format", "excellon", "-u", "mm",
        "--excellon-zeros-format", "decimal", "--excellon-oval-format", "alternate",
        "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2",
        "--generate-report", "--report-path", os.path.join(c, "drill-report.txt"),
        "-o", g + "/", BOARD)
    for f in os.listdir(g):                 # drill maps are for people, not for the fab
        if "drl_map" in f:
            shutil.move(os.path.join(g, f), os.path.join(c, f))
    zpath = os.path.join(OUT, "JLCPCB_rev1_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(g)):
            z.write(os.path.join(g, f), f)

    # 2. BOM: one line per LCSC part
    raw = os.path.join(c, "kicad-bom.csv")
    run("sch", "export", "bom", "--fields",
        "Reference,Value,Footprint,LCSC,${DNP},${EXCLUDE_FROM_BOM}",
        "--labels", "Reference,Value,Footprint,LCSC,DNP,EXCL",
        "--group-by", "", "--exclude-dnp", "-o", raw, SCH)
    lines = {}
    for r in csv.DictReader(open(raw)):
        if r["DNP"].strip() or r["EXCL"].strip():
            continue
        # one BOM line per LCSC part: the three side buttons (MUTE/ACTION/USER) and the three
        # top buttons (RESET/EN/BOOT) share a part but carry different values
        fp = r["Footprint"].split(":", 1)[-1]
        key = (r["LCSC"].strip(), fp)
        entry = lines.setdefault(key, {"values": [], "refs": []})
        if r["Value"] not in entry["values"]:
            entry["values"].append(r["Value"])
        entry["refs"].extend(expand(r["Reference"]))
    missing = [e["refs"] for (lcsc, _), e in lines.items() if not lcsc]
    if missing:
        sys.exit(f"parts without an LCSC number: {missing}")
    bom_refs = set()
    with open(os.path.join(a, "mindspark_rev1_BOM_JLC.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (lcsc, fp), e in sorted(lines.items(), key=lambda kv: ref_key(sorted(kv[1]["refs"], key=ref_key)[0])):
            refs = sorted(e["refs"], key=ref_key)
            bom_refs.update(refs)
            w.writerow([" / ".join(e["values"]), ",".join(refs), fp, lcsc])

    # 3. CPL: KiCad positions of exactly the BOM parts
    pos = os.path.join(a, "mindspark_rev1-all-pos.csv")
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
        "--exclude-dnp", "-o", pos, BOARD)
    placed = {}
    for r in csv.DictReader(open(pos)):
        placed[r["Ref"]] = r
    with open(os.path.join(a, "mindspark_rev1_CPL_JLC.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref in sorted(bom_refs, key=ref_key):
            r = placed[ref]
            rot = (float(r["Rot"]) + ROT_FIX.get(ref, 0)) % 360
            dx, dy = POS_FIX.get(ref, (0.0, 0.0))
            w.writerow([ref, f"{float(r['PosX']) + dx:.4f}mm", f"{float(r['PosY']) + dy:.4f}mm",
                        "Top" if r["Side"] == "top" else "Bottom", f"{rot:g}"])

    not_on_board = sorted(bom_refs - set(placed), key=ref_key)
    left_out = sorted(set(placed) - bom_refs, key=ref_key)
    top = sum(1 for x in bom_refs if placed[x]["Side"] == "top")
    print(f"BOM: {len(lines)} lines, {len(bom_refs)} parts ({top} top, {len(bom_refs) - top} bottom)")
    print(f"CPL: {len(bom_refs)} rows; on the board but not assembled: {', '.join(left_out)}")
    if not_on_board:
        sys.exit(f"BOM parts missing from the board: {not_on_board}")
    print(f"gerber zip: {os.path.relpath(zpath, PRJ)} ({len(os.listdir(g))} files)")


if __name__ == "__main__":
    main()
