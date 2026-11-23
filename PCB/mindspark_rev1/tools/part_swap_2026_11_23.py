"""Replace the out-of-stock mic and flash, fix the mic land pattern, add R407 (user 2026-11-23).

The user's choices (2026-11-23):
  * Mics MK501-504: Infineon IM69D129FV01XTMA1 (0 stock) -> Knowles SPH0641LM4H-1 (JLC C497724).
    Same pinout (1 DATA, 2 SELECT, 3 GND, 4 CLOCK, 5 VDD) and the same pads and port
    (Knowles datasheet p.8 vs Infineon p.12 Fig. 13: pads 0.522 x 0.725, rows 1.675 apart,
    pitch 0.822, GND ring 1.025/1.625). Normal mode 1.0-4.8 MHz covers the XVF's 3.072 MHz.
    It is 10 dB more sensitive (-26 vs -36 dBFS) and SNR 64.3 vs 69 dB (accepted for rev1).
  * Mic footprint fix (any mic): the pad rows were 0.838 mm apart; they belong 1.675 mm apart.
    New footprint Mindspark:Knowles_SPH0641LM4H-1_LGA-5_3.5x2.65mm replaces
    Infineon_IM69D129FV01_LGA-5_3.5x2.65mm: pads 1, 2, 4, 5 at y +-0.8375, 0.54 x 0.75 again
    (Infineon's copper size; the 2026-11-23 trim to 0.688 only existed because of the wrong rows).
    GND ring, port hole and ring paste are kept (the Knowles ring 1.025-1.625 sits inside the
    1.01-1.725 copper ring). The frozen mic routes are re-ended in power_v2
    (tools/mic_pads_2026_11_23.py).
  * Flash U401: Winbond W25Q32JVUUIQ (0 stock) -> GigaDevice GD25Q16ENIGR (JLC C5749719),
    16 Mbit = 2 MB, the XVF3800's stated minimum. Same USON-8 3x4 mm package, same pins,
    same two 0.2 x 0.8 exposed pads (not connected inside; GD25Q16E datasheet p.54), so the
    footprint stays. Pin 7 is HOLD#/IO3 (no RESET function). QE ships at 0.
  * R407 4.7k (C25900) pulls XVF_QSPI_D3 (HOLD#) up; see tools/flash_pullup_2026_11_23.py.
    Schematic: xvf3800_periph sheet, Boot flash box, below C401.

What it edits (idempotent: a second run reports nothing to do):
  library  PCB/libraries: footprint file (new name, old file removed), symbols in
           Mindspark.kicad_sym, parts-map.json, sources.json (two new datasheets)
  sheets   audio (4 mics), xvf3800_periph (U401, R407 + its +3V3 and D3 label),
           esp32_io (path B note)
  board    mic footprints (name, pads, fields), U401 fields, R407 footprint placed

Usage (schematic and PCB editors closed):  python3 tools/part_swap_2026_11_23.py
Then: python3 tools/power_v2_2026_11_18.py (rebuilds the copper) and the usual checks.
"""
import copy
import json
import math
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, dump, children, child, q          # noqa: E402
from place_tidy import Part                                 # noqa: E402
import flash_pullup_2026_11_23 as fp_pu                     # noqa: E402

PRJ = os.path.join(HERE, "..")
LIBDIR = os.path.join(PRJ, "..", "libraries")
FPDIR = os.path.join(LIBDIR, "footprints", "Mindspark.pretty")
SYMLIB = os.path.join(LIBDIR, "symbols", "Mindspark.kicad_sym")
BOARD = os.path.join(PRJ, "mindspark_rev1.kicad_pcb")
AUDIO = os.path.join(PRJ, "audio.kicad_sch")
PERIPH = os.path.join(PRJ, "xvf3800_periph.kicad_sch")
ESPIO = os.path.join(PRJ, "esp32_io.kicad_sch")

OLD_FP, NEW_FP = "Infineon_IM69D129FV01_LGA-5_3.5x2.65mm", "Knowles_SPH0641LM4H-1_LGA-5_3.5x2.65mm"
NEW_FP_DESCR = ("Knowles SPH0641LM4H-1 PDM MEMS microphone, 3.5x2.65 mm LGA-5, bottom port. Pads per "
                "Knowles datasheet p.8 (rows 1.675 apart, pitch 0.822; same as Infineon IM69D129FV01 "
                "p.12 Fig. 13); copper 0.54 x 0.75 and GND ring 1.01/1.725 from Infineon Fig. 14; port 0.6")
ROW = 0.8375

MIC = {"old": "IM69D129FV01XTMA1", "new": "SPH0641LM4H-1", "fields": {
    "Value": "SPH0641LM4H-1",
    "Footprint": "Mindspark:" + NEW_FP,
    "Datasheet": "https://jlcpcb.com/partdetail/C497724",   # links the PDF (saved as libraries/datasheets/SPH0641LM4H-1_C497724.pdf)
    "Description": "Knowles SiSonic PDM MEMS microphone, -26 dBFS, SNR 64.3 dB, bottom port, 1.0-4.8 MHz normal mode",
    "Manufacturer": "Knowles",
    "MPN": "SPH0641LM4H-1",
    "LCSC": "C497724",
}}
FLASH = {"old": "W25Q32JVUUIQ", "new": "GD25Q16ENIGR", "fields": {
    "Value": "GD25Q16ENIGR",
    "Datasheet": "https://download.gigadevice.com/Datasheet/DS-00473-GD25Q16E-Rev1.3.pdf",
    "Description": ("16 Mbit (2 MB) 3.3 V quad SPI flash, USON-8 3x4 mm. QE bit ships at 0 (set it before "
                    "quad use). Centre pads not connected inside; leave floating"),
    "Manufacturer": "GigaDevice",
    "MPN": "GD25Q16ENIGR",
    "LCSC": "C5749719",
    "spec": "16 Mbit QSPI flash",
}}
PIN7_OLD, PIN7_NEW = "~{HOLD}/~{RESET}/IO_{3}", "~{HOLD}/IO_{3}"

R407_USE = "QSPI_D3 (flash HOLD#) pull-up: holds HOLD# high while the XVF is in reset (ESP32 path B)"
R407_SCH = (73.66, 67.31)           # symbol centre (clear of U401's value text) on the xvf3800_periph sheet; pin 1 top, pin 2 bottom
PERIPH_SHEET_PATH = "/1506f4ea-c525-5200-b0f1-da532c70c9fb"     # sheet instance (board footprint paths)

PATH_B_OLD = ("Path B (diagram 08): slide SW701 to PROG, the ESP32 holds RST_N low through Q701, writes the "
              "W25Q32 with plain SPI (SPI2), reads it back, releases the\nflash lines, then RST_N.")
PATH_B_NEW = ("Path B (diagram 08): slide SW701 to PROG, the ESP32 holds RST_N low through Q701, first sets the "
              "flash's QE bit (GD25Q16E ships with QE = 0;\nR407 keeps HOLD# high meanwhile), writes the image with "
              "plain SPI (SPI2), reads it back, releases the flash lines, then RST_N.")

done = []


def note(s):
    done.append(s)
    print("  " + s)


def new_uuid():
    return q(str(uuid.uuid4()))


def prop(node, name):
    for p in children(node, "property"):
        if str(p[1]) == name:
            return p
    return None


def set_props(node, fields, where):
    for name, value in fields.items():
        p = prop(node, name)
        if p is None:
            continue                    # board footprints carry no Footprint field, symbols no spec
        if str(p[2]) != value:
            p[2] = q(value)
            note(f"{where}: {name} -> {value}")


# ================================================================ library footprint
def mic_pads(fp, where):
    """Pads 1, 2, 4, 5 onto the 1.675 mm rows at full size. Works on the library file and on
    board copies (board pad 'at' carries the rotation as a third value, kept as is)."""
    for p in children(fp, "pad"):
        if str(p[1]) in ("1", "2", "4", "5"):
            at, sz = child(p, "at"), child(p, "size")
            y = float(at[2])
            ny = math.copysign(ROW, y)
            if abs(y - ny) > 1e-6:
                at[2] = f"{ny:g}"
                note(f"{where}: pad {p[1]} y {y:g} -> {ny:g}")
            if abs(float(sz[2]) - 0.75) > 1e-6:
                sz[2] = "0.75"
                note(f"{where}: pad {p[1]} height -> 0.75")


def library_footprint():
    old_path = os.path.join(FPDIR, OLD_FP + ".kicad_mod")
    new_path = os.path.join(FPDIR, NEW_FP + ".kicad_mod")
    src = new_path if os.path.exists(new_path) else old_path
    fp = parse(open(src).read())
    if str(fp[1]) != NEW_FP:
        fp[1] = q(NEW_FP)
        note(f"footprint renamed {OLD_FP} -> {NEW_FP}")
    child(fp, "descr")[1] = q(NEW_FP_DESCR)
    child(fp, "tags")[1] = q("MEMS microphone PDM Knowles SPH0641 bottom port")
    prop(fp, "Value")[2] = q(NEW_FP)
    mic_pads(fp, "library footprint")
    text = dump(fp) + "\n"
    if not os.path.exists(new_path) or open(new_path).read() != text:
        open(new_path, "w").write(text)
        note(f"wrote {os.path.relpath(new_path, LIBDIR)}")
    if os.path.exists(old_path):
        os.remove(old_path)
        note(f"removed {os.path.relpath(old_path, LIBDIR)}")
    return fp


# ================================================================ symbols (library and sheet caches)
def rename_symbol(sym, old, new, fields, where, cache_prefix=""):
    """Rename a symbol definition (top name and its unit sub-symbols) and set its fields."""
    if str(sym[1]) == cache_prefix + old:
        sym[1] = q(cache_prefix + new)
        note(f"{where}: symbol {old} -> {new}")
    for u in children(sym, "symbol"):
        name = str(u[1])
        if name.startswith(old + "_"):
            u[1] = q(new + name[len(old):])
    lib_fields = dict(fields)
    if "LCSC" in lib_fields and prop(sym, "LCSC") is None and prop(sym, "LCSC Part") is not None:
        lib_fields["LCSC Part"] = lib_fields.pop("LCSC")
    lib_fields.pop("spec", None)
    set_props(sym, lib_fields, where)


def pin7(sym, where):
    for u in children(sym, "symbol"):
        for pin in children(u, "pin"):
            nm = child(pin, "name")
            if str(child(pin, "number")[1]) == "7" and str(nm[1]) == PIN7_OLD:
                nm[1] = q(PIN7_NEW)
                note(f"{where}: pin 7 name -> {PIN7_NEW}")


def top_span(text, name):
    """(start, end) of the top-level '(symbol "name"' block in the library text."""
    key = f'\n\t(symbol "{name}"'
    i = text.find(key)
    if i < 0:
        return None
    i += 2                             # skip the newline and tab: span starts at '('
    depth, j = 0, i
    while True:
        c = text[j]
        if c == '"':                       # skip quoted strings (they may hold parentheses)
            j += 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1


def symbol_library():
    """Edit only the two symbols' text blocks, so the rest of the library keeps KiCad's layout."""
    text = open(SYMLIB).read()
    for part in (MIC, FLASH):
        span = top_span(text, part["old"]) or top_span(text, part["new"])
        sym = parse(text[span[0]:span[1]])
        rename_symbol(sym, part["old"], part["new"], part["fields"], "symbol library")
        if part is FLASH:
            pin7(sym, "symbol library")
        text = text[:span[0]] + dump(sym, 1) + text[span[1]:]
    open(SYMLIB, "w").write(text)


def sheet_swap(path, part, extra=None):
    sch = parse(open(path).read())
    name = os.path.basename(path)
    for s in children(child(sch, "lib_symbols"), "symbol"):
        if str(s[1]) in ("Mindspark:" + part["old"], "Mindspark:" + part["new"]):
            rename_symbol(s, part["old"], part["new"], part["fields"], f"{name} cache", "Mindspark:")
            if part is FLASH:
                pin7(s, f"{name} cache")
    for s in children(sch, "symbol"):
        lid = child(s, "lib_id")
        if str(lid[1]) == "Mindspark:" + part["old"]:
            lid[1] = q("Mindspark:" + part["new"])
            note(f"{name}: {prop(s, 'Reference')[2]} lib_id -> {part['new']}")
        if str(lid[1]) == "Mindspark:" + part["new"]:
            set_props(s, part["fields"], f"{name} {prop(s, 'Reference')[2]}")
    if extra:
        extra(sch)
    open(path, "w").write(dump(sch) + "\n")
    return sch


def wire(a, b):
    return ["wire", ["pts", ["xy", f"{a[0]:g}", f"{a[1]:g}"], ["xy", f"{b[0]:g}", f"{b[1]:g}"]],
            ["stroke", ["width", "0"], ["type", "default"]], ["uuid", new_uuid()]]


def add_r407(sch):
    """R407 below U401's value text: +3V3 on pin 1 (top), XVF_QSPI_D3 hierarchical label on pin 2."""
    syms = {str(prop(s, "Reference")[2]): s for s in children(sch, "symbol")}
    x, y = R407_SCH
    keep_uuid = None
    if "R407" in syms:
        at = child(syms["R407"], "at")
        ox = float(at[1])
        if abs(ox - x) < 1e-6 and abs(float(at[2]) - y) < 1e-6:
            return
        # moved since the first run: take its drawing out and lay it again, keeping the symbol's
        # uuid (the board footprint R407 points at it)
        keep_uuid = child(syms["R407"], "uuid")[1]

        def ours(n):
            if not (isinstance(n, list) and n):
                return False
            if n[0] == "symbol" and str(prop(n, "Reference")[2]) in ("R407", "#PWR4012"):
                return True
            if n[0] == "wire":
                return all(abs(float(pt[1]) - ox) < 1e-6 and float(pt[2]) > 55 for pt in child(n, "pts")[1:])
            if n[0] == "hierarchical_label" and str(n[1]) == "XVF_QSPI_D3":
                return abs(float(child(n, "at")[1]) - ox) < 1e-6
            return False
        sch[:] = [n for n in sch if not ours(n)]
    top, bot = (x, round(y - 3.81, 2)), (x, round(y + 3.81, 2))
    # the resistor: a copy of R401 (4.7k 0402, C25900), upright (rotation 0: pin 1 on top)
    r = copy.deepcopy(syms["R401"])
    child(r, "at")[1:] = [f"{x:g}", f"{y:g}", "0"]
    child(r, "uuid")[1] = keep_uuid or new_uuid()
    for p in children(r, "property"):
        name = str(p[1])
        if name == "Reference":
            p[2] = q("R407")
            child(p, "at")[1:] = [f"{x + 2.3:g}", f"{y - 1.0:g}", "0"]
        elif name == "Value":
            child(p, "at")[1:] = [f"{x + 2.3:g}", f"{y + 0.5:g}", "0"]
        elif name == "use":
            p[2] = q(R407_USE)
            child(p, "at")[1:] = [f"{x:g}", f"{y:g}", "0"]
        else:
            child(p, "at")[1:] = [f"{x:g}", f"{y:g}", "0"]
        if name in ("Reference", "Value"):
            eff = child(p, "effects")
            if child(eff, "justify") is None:
                eff.append(["justify", "left"])
    for pin in children(r, "pin"):
        child(pin, "uuid")[1] = new_uuid()
    child(child(child(child(r, "instances"), "project"), "path"), "reference")[1] = q("R407")
    sch.append(r)
    # +3V3 power symbol above it (a copy of R401's, #PWR4012)
    pwr = [s for s in children(sch, "symbol") if str(child(s, "lib_id")[1]) == "Mindspark:+3V3"
           and abs(float(child(s, "at")[1]) - 38.1) < 0.01][0]
    pw = copy.deepcopy(pwr)
    pp = (x, round(top[1] - 2.54, 2))
    child(pw, "at")[1:] = [f"{pp[0]:g}", f"{pp[1]:g}", "0"]
    child(pw, "uuid")[1] = new_uuid()
    for p in children(pw, "property"):
        if str(p[1]) == "Reference":
            p[2] = q("#PWR4012")
        dy = -3.556 if str(p[1]) == "Value" else 0.0
        child(p, "at")[1:3] = [f"{pp[0]:g}", f"{pp[1] + dy:g}"]
    for pin in children(pw, "pin"):
        child(pin, "uuid")[1] = new_uuid()
    child(child(child(child(pw, "instances"), "project"), "path"), "reference")[1] = q("#PWR4012")
    sch.append(pw)
    sch.append(wire(pp, top))
    # D3 hierarchical label below (same name as the sheet's own D3 label = same net)
    lab = copy.deepcopy([h for h in children(sch, "hierarchical_label") if str(h[1]) == "XVF_QSPI_D3"][0])
    child(lab, "at")[1:] = [f"{bot[0]:g}", f"{bot[1]:g}", "180"]      # right on pin 2
    child(lab, "uuid")[1] = new_uuid()
    sch.append(lab)
    note(f"xvf3800_periph: R407 4.7k at {R407_SCH}, +3V3 above, XVF_QSPI_D3 label on pin 2")


def esp_note():
    sch = parse(open(ESPIO).read())
    for t in children(sch, "text"):
        if str(t[1]).startswith(PATH_B_OLD):
            t[1] = q(PATH_B_NEW + str(t[1])[len(PATH_B_OLD):])
            note("esp32_io: path B note now says to set QE first")
    open(ESPIO, "w").write(dump(sch) + "\n")


# ================================================================ board
def pad_xy(p, pad):
    x, y, r = p.at
    at = child(pad, "at")
    a = math.radians(-r)
    lx, ly = float(at[1]), float(at[2])
    return x + lx * math.cos(a) - ly * math.sin(a), y + lx * math.sin(a) + ly * math.cos(a)


def board(lib_fp, r407_uuid):
    root = parse(open(BOARD).read())
    P = {Part(f).ref: Part(f) for f in children(root, "footprint")}
    for ref in ("MK501", "MK502", "MK503", "MK504"):
        f = P[ref].node
        if str(f[1]) != "Mindspark:" + NEW_FP:
            f[1] = q("Mindspark:" + NEW_FP)
            note(f"board {ref}: footprint -> {NEW_FP}")
        child(f, "descr")[1] = q(NEW_FP_DESCR)
        set_props(f, MIC["fields"], f"board {ref}")
        mic_pads(f, f"board {ref}")
    set_props(P["U401"].node, FLASH["fields"], "board U401")
    if "R407" not in P:
        fp = copy.deepcopy(P["R401"].node)                 # 4.7k 0402 on the bottom, C25900
        child(fp, "uuid")[1] = q(str(uuid.uuid4()))
        prop(fp, "Reference")[2] = q("R407")
        prop(fp, "use")[2] = q(R407_USE)
        child(fp, "path")[1] = q(f"{PERIPH_SHEET_PATH}/{r407_uuid}")
        for pd in children(fp, "pad"):
            child(pd, "net")[1] = q("+3V3" if str(pd[1]) == "1" else "/XVF_QSPI_D3")
            if child(pd, "uuid"):
                child(pd, "uuid")[1] = q(str(uuid.uuid4()))
        root.append(fp)
        P["R407"] = Part(fp)
        note("board R407: added (copy of R401)")
    r = P["R407"]
    if r.side != "B.Cu":
        sys.exit("R407 copy is not on the bottom side")
    # pick the upright rotation that puts pad 2 (D3) on the south spot, on the D3 via
    for rot in (fp_pu.ROT, (fp_pu.ROT + 180) % 360):
        r.place(*fp_pu.POS, rot)
        pads = {str(pd[1]): pad_xy(r, pd) for pd in children(r.node, "pad")}
        if pads["2"][1] > pads["1"][1]:
            break
    if math.dist(pads["2"], fp_pu.NEW_VIA) > 0.01:
        sys.exit(f"R407 pad 2 at {pads['2']}, expected on {fp_pu.NEW_VIA}")
    print(f"  board R407 at {fp_pu.POS} rot {r.at[2]:g}: pad 2 (D3) {tuple(round(v, 3) for v in pads['2'])}, "
         f"pad 1 (+3V3) {tuple(round(v, 3) for v in pads['1'])}")
    # library-mismatch check: board mic pads must equal the library pads (only rotation differs)
    lib_pads = {str(p[1]): (child(p, "at")[1:3], child(p, "size")[1:3]) for p in children(lib_fp, "pad") if str(p[1])}
    for ref in ("MK501", "MK502", "MK503", "MK504"):
        for p in children(P[ref].node, "pad"):
            if str(p[1]) in lib_pads and str(p[1]) != "3":
                la, ls = lib_pads[str(p[1])]
                if [float(v) for v in child(p, "at")[1:3]] != [float(v) for v in la] or \
                        [float(v) for v in child(p, "size")[1:3]] != [float(v) for v in ls]:
                    sys.exit(f"{ref} pad {p[1]} differs from the library")
    open(BOARD, "w").write(dump(root) + "\n")


# ================================================================ parts map, sources
def parts_map():
    path = os.path.join(LIBDIR, "parts-map.json")
    pm = json.load(open(path))
    for e in pm:
        if e.get("mpn") == MIC["old"]:
            e.update({"mpn": MIC["new"], "lcsc": "C497724", "symbol": "Mindspark:" + MIC["new"],
                      "footprint": "Mindspark:" + NEW_FP,
                      "symbol_source": "former IM69D129 symbol renamed (same pin numbers and names), 2026-11-23",
                      "footprint_source": ("former Infineon footprint, pad rows fixed to 1.675 mm apart (Knowles p.8 / "
                                           "Infineon p.12 Fig. 13), 2026-11-23; 3D = stock InvenSense ICS-43434 "
                                           "model (same 3.5x2.65x0.98 body), rot -90")})
            note("parts-map: mic entry")
        if e.get("mpn") == FLASH["old"]:
            e.update({"mpn": FLASH["new"], "lcsc": "C5749719", "symbol": "Mindspark:" + FLASH["new"],
                      "symbol_source": "former W25Q32JVUUIQ symbol renamed, pin 7 HOLD#/IO3, 2026-11-23",
                      "footprint_source": ("stock copy, checked vs Winbond UU drawing and GD25Q16E USON8 3x4 p.54 "
                                           "(b 0.3, e 0.8, centre pads 0.2x0.8 at 0.8)")})
            note("parts-map: flash entry")
    json.dump(pm, open(path, "w"), indent=2, ensure_ascii=False)
    open(path, "a").write("\n")
    path = os.path.join(LIBDIR, "sources.json")
    src = json.load(open(path))
    add = {
        "datasheets/SPH0641LM4H-1_C497724.pdf": {
            "url": "https://jlcpcb.com/partdetail/C497724 (Datasheet link)", "rev": "Rev D",
            "downloaded": "2026-11-23",
            "sha256": "7e2b058bc3c5b96cafd386c41d30fe2f4154d7f78d1deff08d404c6dc131beef"},
        "datasheets/GD25Q16E.pdf": {
            "url": "https://download.gigadevice.com/Datasheet/DS-00473-GD25Q16E-Rev1.3.pdf", "rev": "Rev 1.3",
            "downloaded": "2026-11-23",
            "sha256": "91343ed2fdd16b671de2555657a0bc5d21d045ab3ac224f725c3986d568f8fe5"},
    }
    for k, v in add.items():
        if k not in src["datasheets"]:
            src["datasheets"][k] = v
            note(f"sources: {k}")
    json.dump(src, open(path, "w"), indent=1, ensure_ascii=False)     # file style: indent 1, no newline


def main():
    lib_fp = library_footprint()
    symbol_library()
    sheet_swap(AUDIO, MIC)
    periph = sheet_swap(PERIPH, FLASH, extra=add_r407)
    r407 = [s for s in children(periph, "symbol") if str(prop(s, "Reference")[2]) == "R407"][0]
    esp_note()
    board(lib_fp, str(child(r407, "uuid")[1]))
    parts_map()
    print(f"{len(done)} changes" if done else "nothing to do")


if __name__ == "__main__":
    main()
