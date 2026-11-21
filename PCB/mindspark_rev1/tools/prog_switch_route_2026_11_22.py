"""Routes for the flash switches west of the ESP32 module (user, 2026-11-22).

Plan: verification/prog-switch-plan-2026-11-22/. Parts: tools/prog_switch_place_2026_11_22.py.
Laid by tools/power_v2_2026_11_18.py before any power copper (geometry frozen in
prog_switch_route_2026_11_22.json next to this file).

  Flash lines (XVF side, top layer, branch from the flash end, through the 0 ohm links R706-R709
  into each switch's pin 2):
    CS_N  via in R401's pad 1 (the flash's CS pull-up, beside the flash), north edge of the band
    D1    via just below D1's own track at (143.2, 94.0), between the D3 and CLK hops over the flash
    CLK   from the CLK hop's west via beside the flash
    D0    short B.Cu stub west from the flash's D0 pad to a via
  PRG lines (ESP32 side): from ESP32 pins 21, 20, 19, 18 (CS_N, DO, CLK, DI since the pin shift
    of 2026-11-22, tools/sch_prog_pins_2026_11_22.py, so they leave in the switch column's order)
    on the top layer under the module: west off the pads into a lane inside the module's east pads
    (southern pin = western lane, so nothing crosses), north, then straight west in a band just
    inside the module's north pads (the north cap row's in-pad vias move beside their pads,
    power_v2), between the CS_N flash line (north) and the D1 flash line (south). Just outside the
    module CS_N drops north, the other three south, and each runs on B.Cu into a via in its
    switch's pin 1 as four parallel lines. Every switch needs one PRG and one flash line on neighbouring pins, so
    on one layer they would have to cross; the bottom layer under the block is free since the NW
    mic pair moved (tools/mic_nw_reroute_2026_11_22.py).
  PRG_EN: a via in each switch's pin 4, a B.Cu chain beside the column, out west under the +5V
    trunk and the NW mic lanes to a via, then top layer north and west to R701 and SW701 (PROG
    slide). ESP32 pin 22's link to PRG_EN is left for the slow-control pass.

  python3 tools/prog_switch_route_2026_11_22.py --generate   write the JSON from the hand geometry
  python3 tools/prog_switch_route_2026_11_22.py              print lengths and vias
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "prog_switch_route_2026_11_22.json")
W, VIA = 0.15, (0.45, 0.2)

CS, DI, CLK, DO, EN = "/PRG_CS_N", "/PRG_DI", "/PRG_CLK", "/PRG_DO", "/PRG_EN"
XCS, XD1, XCLK, XD0 = "/XVF_QSPI_CS_N", "/XVF_QSPI_D1", "/XVF_QSPI_CLK", "/XVF_QSPI_D0"

# switch column (x 129.0, pads 1-3 east at 130.1375, 4-5 west at 127.8625) and the links (x 132.2)
SW = {"U701": 90.21, "U704": 93.76, "U702": 97.31, "U703": 100.86}
P1 = lambda sw: (130.1375, round(SW[sw] + 0.95, 3))      # noqa: E731  PRG side, via in pad
P2 = lambda sw: (130.1375, SW[sw])                        # noqa: E731  flash side
P4 = lambda sw: (127.8625, round(SW[sw] - 0.95, 3))      # noqa: E731  PRG_EN, via in pad
LINK = {"R706": 90.21, "R709": 93.76, "R707": 97.31, "R708": 98.8}
L1 = lambda r: (132.71, LINK[r])                          # noqa: E731  flash side (east)
L2 = lambda r: (131.69, LINK[r])                          # noqa: E731  switch side

BAND_X = 141.6                                             # band entry, west of the routed part
BAND_Y = {CS: 92.05, DO: 92.36, CLK: 92.67, DI: 92.98}     # north -> south, 0.31 pitch
LANE_X = {DI: 153.96, CLK: 154.27, DO: 154.58, CS: 154.89}   # southern pin = western lane, 0.31 pitch
ESP_PAD = {DI: (155.91, 101.85), CLK: (155.91, 100.58), DO: (155.91, 99.31), CS: (155.91, 98.04)}
LANE_TOP = {CS: 91.9, DO: 93.2, CLK: 93.51, DI: 93.82}       # each lane turns west at its own row
DROP = {CS: (134.5, 91.55), DO: (133.65, 93.45), CLK: (134.4, 93.45), DI: (135.15, 93.45)}

HAND = [  # net, layer, width, points
    # flash branches (top layer)
    (XCS, "F.Cu", W, [(142.36, 91.29), (141.91, 91.74), (135.0, 91.74), (135.0, 90.51), (134.7, 90.21), L1("R706")]),
    (XD1, "B.Cu", W, [(143.2, 93.76), (143.2, 94.0)]),
    (XD1, "F.Cu", W, [(143.2, 94.0), (133.2, 94.0), (132.96, 93.76), L1("R709")]),
    (XCLK, "F.Cu", W, [(138.05, 94.56), (134.1, 94.56), (134.1, 96.81), (133.6, 97.31), L1("R707")]),
    (XD0, "B.Cu", W, [(139.15, 95.65), (138.5, 95.65)]),
    (XD0, "F.Cu", W, [(138.5, 95.65), (138.35, 95.5), (134.7, 95.5), (134.7, 98.8), L1("R708")]),
    # links -> switch pin 2
    ("Net-(U701-COM)", "F.Cu", W, [L2("R706"), P2("U701")]),
    ("Net-(U704-COM)", "F.Cu", W, [L2("R709"), P2("U704")]),
    ("Net-(U702-COM)", "F.Cu", W, [L2("R707"), P2("U702")]),
    ("Net-(U703-COM)", "F.Cu", W, [L2("R708"), (131.25, 99.24), (131.25, 100.86), P2("U703")]),
    # PRG lines: the band under the module, from the lane tops to BAND_X (top layer): CS_N straight
    # west at 91.9; DO / CLK / DI pass under the crystal's GND via (151.96, 92.62), rise at 45 degrees
    # north of the MCLK via (149.03, 93.548), run straight (0.31 mm pitch) past the D3 via
    # (144.06, 93.31) and step down 0.15 mm to the band rows west of the CS_N flash line's via.
    (CS, "F.Cu", W, [(LANE_X[CS], LANE_TOP[CS]), (142.9, 91.9), (142.75, 92.05), (BAND_X, 92.05)]),
    (DO, "F.Cu", W, [(LANE_X[DO], LANE_TOP[DO]), (150.9, 93.2), (149.91, 92.21), (143.1, 92.21), (142.95, 92.36),
                     (BAND_X, 92.36)]),
    (CLK, "F.Cu", W, [(LANE_X[CLK], LANE_TOP[CLK]), (150.6, 93.51), (149.61, 92.52), (143.3, 92.52), (143.15, 92.67),
                      (BAND_X, 92.67)]),
    (DI, "F.Cu", W, [(LANE_X[DI], LANE_TOP[DI]), (150.3, 93.82), (149.31, 92.83), (143.5, 92.83), (143.35, 92.98),
                     (BAND_X, 92.98)]),
    # PRG lines: band west of BAND_X to the drops (top layer): CS_N turns north, the others south
    (CS, "F.Cu", W, [(BAND_X, BAND_Y[CS]), (DROP[CS][0], BAND_Y[CS]), DROP[CS]]),
    (DO, "F.Cu", W, [(BAND_X, BAND_Y[DO]), (DROP[DO][0], BAND_Y[DO]), DROP[DO]]),
    (CLK, "F.Cu", W, [(BAND_X, BAND_Y[CLK]), (DROP[CLK][0], BAND_Y[CLK]), DROP[CLK]]),
    (DI, "F.Cu", W, [(BAND_X, BAND_Y[DI]), (DROP[DI][0], BAND_Y[DI]), DROP[DI]]),
    # PRG lines: drops -> switch pin 1 (bottom layer), parallel
    (CS, "B.Cu", W, [DROP[CS], (134.11, 91.16), P1("U701")]),
    (DO, "B.Cu", W, [DROP[DO], (132.39, 94.71), P1("U704")]),
    (CLK, "B.Cu", W, [DROP[CLK], (132.85, 95.0), (132.85, 97.76), (132.35, 98.26), P1("U702")]),
    (DI, "B.Cu", W, [DROP[DI], (133.45, 95.15), (133.45, 98.8), (132.0, 100.25), (132.0, 101.31), (131.5, 101.81),
                     P1("U703")]),
    # PRG lines: ESP32 pad -> lane inside the east pads (top layer, under the module)
    (CS, "F.Cu", W, [ESP_PAD[CS], (LANE_X[CS], ESP_PAD[CS][1]), (LANE_X[CS], LANE_TOP[CS])]),
    (DI, "F.Cu", W, [ESP_PAD[DI], (LANE_X[DI], ESP_PAD[DI][1]), (LANE_X[DI], LANE_TOP[DI])]),
    (CLK, "F.Cu", W, [ESP_PAD[CLK], (LANE_X[CLK], ESP_PAD[CLK][1]), (LANE_X[CLK], LANE_TOP[CLK])]),
    (DO, "F.Cu", W, [ESP_PAD[DO], (LANE_X[DO], ESP_PAD[DO][1]), (LANE_X[DO], LANE_TOP[DO])]),
    # PRG_EN: pin-4 vias, chain at x 129.0, out west to a via, then north and west to R701 / SW701
    (EN, "B.Cu", W, [P4("U701"), (129.0, P4("U701")[1]), (129.0, P4("U703")[1])]),
    (EN, "B.Cu", W, [P4("U704"), (129.0, P4("U704")[1])]),
    (EN, "B.Cu", W, [P4("U702"), (129.0, P4("U702")[1])]),
    (EN, "B.Cu", W, [(129.0, P4("U703")[1]), P4("U703"), (123.3, P4("U703")[1])]),
    (EN, "F.Cu", W, [(123.3, P4("U703")[1]), (123.3, 83.0), (117.57, 83.0), (115.09, 80.52), (115.09, 79.47)]),
    (EN, "F.Cu", W, [(115.09, 80.22), (113.608, 80.22)]),
]
HAND_VIAS = ([((142.36, 91.29), XCS), ((143.2, 94.0), XD1), ((138.5, 95.65), XD0)]
             + [(DROP[n], n) for n in (CS, DO, CLK, DI)]
             + [(P1("U701"), CS), (P1("U704"), DO), (P1("U702"), CLK), (P1("U703"), DI)]
             + [(P4(s), EN) for s in SW] + [((123.3, P4("U703")[1]), EN)])


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _load():
    if not os.path.exists(DATA):
        return [], []
    d = json.load(open(DATA))
    return ([(t["net"], t["layer"], t["w"], [tuple(p) for p in t["pts"]]) for t in d["tracks"]],
            [(tuple(v["at"]), v["net"]) for v in d["vias"]])


TRACKS, VIAS = _load()


def generate():
    """Freeze HAND / HAND_VIAS into the JSON (all of it is hand geometry, checked by DRC)."""
    tracks = [{"net": n, "layer": l, "w": w, "pts": [[round(x, 4), round(y, 4)] for x, y in pts]}
              for n, l, w, pts in HAND]
    vias = [{"at": [round(pt[0], 4), round(pt[1], 4)], "net": n} for pt, n in HAND_VIAS]
    json.dump({"tracks": tracks, "vias": vias}, open(DATA, "w"), indent=1)
    print(f"wrote {DATA}: {len(tracks)} tracks, {len(vias)} vias")


if __name__ == "__main__":
    if "--generate" in sys.argv:
        generate()
    else:
        per = {}
        for n, l, w, p in TRACKS:
            per[n] = per.get(n, 0) + length(p)
        for n, v in sorted(per.items()):
            print(f"{n:22s} {v:6.2f} mm, {sum(1 for _, vn in VIAS if vn == n)} vias")
