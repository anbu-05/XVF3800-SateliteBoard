"""Placement for the programming-switch move and the straight XVF USB pair (user, 2026-11-22).

Plan: verification/prog-switch-plan-2026-11-22/ (plan.png, east-column.png, west-wall.png).

  * C323 / C324 (+0V9/+1V8 USB stitching caps) leave the board: In2 +1V8 now runs under the
    XVF3800's east pins (tools/power_v2_2026_11_18.py), so the pair stays over one plane.
  * East cap column (bottom side), the main USB pair now running straight east from pins 28/29:
      north of the pair the stack keeps its lane gaps (TDI | TDO+RST | PLL | TMS+TCK) and moves
      0.46 mm south so C316 ends 0.15 mm above the pair: C315, C303, C319, FB301, C316;
      south of the pair, west pads on one line: C313 (pin 30) 0.15 mm below the pair, C314
      (3.3 V bulk) and C304 (pin 27, whose feed now comes from the east paddle).
  * Flash switches U701-U704 (TS5A3166) and their caps C701-C704 move to the top side west of
    the ESP32 module, in one column, pads 1-3 facing the module (180 degrees), 3.55 mm pitch,
    top to bottom in the order their flash lines leave the module: U701 (CS_N), U704 (D1),
    U702 (CLK), U703 (D0). Each cap stands upright west of its switch, pad 1 (+3V3) level
    with the switch's pin 5.
  * New 0 ohm links R706-R709 (schematic: tools/sch_prog_switch_2026_11_22.py) sit on the flash
    lines between the switch column and the module, pad 1 (XVF side) east; R708 sits 2 mm
    above U703's pin 2 to stay clear of C501. The column sits 2 mm in from the module edge so the
    PRG lines can drop to the bottom layer between the links and the module, and U704 sits level
    with the D1 line where it leaves the module (y 93.76).

Re-running moves the parts again (the links are only created the first time).

Usage (PCB editor closed):  python3 tools/prog_switch_place_2026_11_22.py
"""
import copy
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD, Part  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

COLUMN = {  # bottom side, footprint centres (rotation kept)
    "C315": (152.96, 95.19), "C303": (152.96, 96.26), "C319": (152.96, 97.63), "FB301": (152.98, 98.71),
    "C316": (152.96, 100.09), "C313": (152.96, 101.67), "C314": (153.255, 103.01), "C304": (152.96, 104.35),
}
SW_X = 129.0
SWITCHES = [("U701", 90.21), ("U704", 93.76), ("U702", 97.31), ("U703", 100.86)]   # top to bottom
CAPS = {"U701": "C701", "U704": "C704", "U702": "C702", "U703": "C703"}
CAP_X = 126.34
LINKS = [  # ref, switch, XVF net, y, schematic symbol uuid
    ("R706", "U701", "/XVF_QSPI_CS_N", 90.21, "3731bee0-86cb-4a75-897d-bd89fe40c9dc"),
    ("R709", "U704", "/XVF_QSPI_D1", 93.76, "9fc027d3-bd9b-4a73-8db7-e653bcf6bab6"),
    ("R707", "U702", "/XVF_QSPI_CLK", 97.31, "4111c103-29b3-4b50-835b-b40d95722280"),
    ("R708", "U703", "/XVF_QSPI_D0", 98.8, "d5b6bf53-827b-45d8-b8ad-c72228148812"),
]
LINK_X = 132.2
SHEET = "/cf525f19-95da-5350-b107-43084f64972d"          # esp32_io sheet instance


def main():
    root = parse(open(BOARD).read())
    first = not any(Part(f).ref == "R706" for f in children(root, "footprint"))
    # drop the two stitching caps
    root[:] = [n for n in root if not (isinstance(n, list) and n and n[0] == "footprint"
                                       and Part(n).ref in ("C323", "C324"))]
    P = {Part(f).ref: Part(f) for f in children(root, "footprint")}
    for ref, (x, y) in COLUMN.items():
        P[ref].place(x, y)
    for sw, y in SWITCHES:
        P[sw].place(SW_X, y, 180.0)
        P[CAPS[sw]].place(CAP_X, round(y + 0.47, 3), 90.0)
        for pd in children(P[sw].node, "pad"):          # pin 2 now goes through the link
            if str(pd[1]) == "2":
                child(pd, "net")[1] = q(f"Net-({sw}-COM)")
    template = P["R703"].node
    for ref, sw, net, y, sym in LINKS:
        if not first:
            P[ref].place(LINK_X, y, 180.0)
            continue
        fp = copy.deepcopy(template)
        child(fp, "uuid")[1] = q(str(uuid.uuid4()))
        for p in children(fp, "property"):
            if str(p[1]) == "Reference":
                p[2] = q(ref)
            elif str(p[1]) == "use":
                p[2] = q(f"Link: remove to cut {sw} off the XVF flash line (drops its off-capacitance)")
        child(fp, "path")[1] = q(f"{SHEET}/{sym}")
        for pd in children(fp, "pad"):
            child(pd, "net")[1] = q(net if str(pd[1]) == "1" else f"Net-({sw}-COM)")
            if child(pd, "uuid"):
                child(pd, "uuid")[1] = q(str(uuid.uuid4()))
        root.append(fp)
        Part(fp).place(LINK_X, y, 180.0)
    open(BOARD, "w").write(dump(root) + "\n")
    print("placed: column", list(COLUMN), "| switches", [s for s, _ in SWITCHES], "| links", [r[0] for r in LINKS])


if __name__ == "__main__":
    main()
