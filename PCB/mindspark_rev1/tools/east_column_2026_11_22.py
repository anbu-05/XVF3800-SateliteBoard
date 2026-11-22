"""East cap column feeds after the straight XVF USB pair (user, 2026-11-22).

tools/east_escape_2026_11_21.py (and its JSON) still holds the crystal, QSPI flash and the rest of
the 2026-11-21 east escape. This file takes those tracks and vias, drops the ones that fed the old
cap column (pins 17-30 fan-out, the +0V9 jumpers, the island via for C324) and adds the new set
for tools/prog_switch_place_2026_11_22.py's column:

  * C323 / C324 are gone and In2 +1V8 runs under the east pins (power_v2), so the pair needs no
    +0V9/+1V8 stitching.
  * North of the pair the lanes keep their 2026-11-21 shape, 0.46 mm further south with the caps:
    pin 17 -> C315, TDI between C315 and C303, pin 19 -> C303, TDO + RST between C303 and C319,
    pin 22 (PLL_AVDD) between C319 and FB301, TMS + TCK between FB301 and C316, pin 26 -> C316.
    The JTAG lanes still turn north at x 154.07 ... 155.27 and stop at y 88.6 (jtag_route goes on).
  * Pins 19 and 27 (+0V9) get a short stub west onto the east +0V9 paddle (pad 62, same net),
    because pin 27 now sits between pin 26's feed and the pair with no room for a via, and the
    +0V9 island stops behind the pins.
  * The +0V9 caps sit over In2 +1V8, so they join on F.Cu (vias in their +0V9 pads): C303 ->
    FB301 -> C304 (down over the pair). Their +0V9 comes from pin 19's feed (pin 19 -> paddle).
  * Pin 30 -> C313 just below the pair; C313 -> C314 (+3V3) along their west pads.
  * QSPI D3's F.Cu hop over the flash now runs at y 93.5 to a west via at (137.8, 93.5), clear of
    the PRG band north of it and the D1 flash-switch line south of it, whose via sits just below
    D1's own track at (143.2, 94.0) (tools/prog_switch_route_2026_11_22.py).

Imported by tools/power_v2_2026_11_18.py for TRACKS / VIAS (instead of east_escape's).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import east_escape_2026_11_21 as ee  # noqa: E402

W, VIA = ee.W, ee.VIA

DROP_TRACKS = set(range(0, 12)) | {34, 35, 36, 37} | {23, 32} | {27}   # indices in the 2026-11-21 JSON
# 27: pin 4 -> C301, re-laid 0.1 mm further west below (user's hand edit 2026-11-22: room for the
#     XVF SPI_CS_N escape via between it and the QSPI_CLK via)
DROP_VIAS = [(152.495, 98.25), (152.48, 100.7), (152.48, 103.44), (149.95, 102.75), (152.48, 95.8),
             (138.05, 93.76)]

NEW_TRACKS = [  # net, layer, width, points
    ("+1V8", "B.Cu", W, [(150.16, 96.279), (150.66, 96.279), (151.749, 95.19), (152.48, 95.19)]),          # pin 17
    ("/xvf3800/XVF_TDI", "B.Cu", W, [(150.16, 96.679), (150.69, 96.679), (151.644, 95.725), (153.87, 95.725),
                                     (154.07, 95.525), (154.07, 88.6)]),
    ("+0V9", "B.Cu", W, [(150.16, 97.079), (150.72, 97.079), (151.539, 96.26), (152.48, 96.26)]),          # pin 19
    ("/xvf3800/XVF_TDO", "B.Cu", W, [(150.16, 97.479), (150.75, 97.479), (151.434, 96.795), (154.17, 96.795),
                                     (154.37, 96.595), (154.37, 88.6)]),
    ("/XVF_RST_N", "B.Cu", W, [(150.16, 97.879), (150.78, 97.879), (151.564, 97.095), (154.47, 97.095),
                               (154.67, 96.895), (154.67, 88.6)]),
    ("PLL_AVDD", "B.Cu", W, [(150.16, 98.279), (150.81, 98.279), (150.924, 98.165), (153.455, 98.165)]),  # pin 22
    ("PLL_AVDD", "B.Cu", W, [(153.44, 97.63), (153.47, 98.71)]),                                          # C319 - FB301
    ("/xvf3800/XVF_TMS", "B.Cu", W, [(150.16, 98.679), (150.75, 98.679), (151.326, 99.255), (154.77, 99.255),
                                     (154.97, 99.055), (154.97, 88.6)]),
    ("/xvf3800/XVF_TCK", "B.Cu", W, [(150.16, 99.079), (150.70, 99.079), (151.176, 99.555), (155.07, 99.555),
                                     (155.27, 99.355), (155.27, 88.6)]),
    ("+1V8", "B.Cu", W, [(150.16, 99.879), (152.269, 99.879), (152.48, 100.09)]),                         # pin 26
    ("+0V9", "B.Cu", W, [(150.06, 97.079), (149.06, 97.079)]),                                            # pin 19 -> paddle
    ("+0V9", "B.Cu", W, [(150.06, 100.279), (149.06, 100.279)]),                                          # pin 27 -> paddle
    ("+3V3", "B.Cu", W, [(150.16, 101.479), (152.289, 101.479), (152.48, 101.67)]),                       # pin 30
    ("+3V3", "B.Cu", 0.25, [(152.48, 101.67), (152.48, 103.01)]),                                         # C313 - C314
    # +0V9 caps over In2 +1V8: F.Cu jumpers between vias in their +0V9 pads
    ("+0V9", "F.Cu", W, [(152.48, 96.26), (151.85, 96.89), (151.85, 98.07), (152.49, 98.71)]),            # C303 - FB301
    ("+0V9", "F.Cu", W, [(152.49, 98.71), (151.85, 99.35), (151.85, 103.71), (152.48, 104.35)]),          # FB301 - C304
    # pin 4 -> C301, 0.1 mm west of the pin's axis (user 2026-11-22)
    ("+0V9", "B.Cu", W, [(144.958, 94.88), (144.958, 94.654), (144.858, 94.554), (144.858, 91.75), (144.35, 91.75)]),
    # QSPI D3 hop, 0.45 mm further north than on 2026-11-21
    ("/XVF_QSPI_D3", "F.Cu", W, [(144.06, 93.31), (143.87, 93.5), (137.8, 93.5)]),
    ("/XVF_QSPI_D3", "B.Cu", W, [(139.15, 93.76), (138.06, 93.76), (137.8, 93.5)]),
]
NEW_VIAS = [((152.48, 96.26), "+0V9"), ((152.49, 98.71), "+0V9"), ((152.48, 104.35), "+0V9"),
            ((137.8, 93.5), "/XVF_QSPI_D3")]


def _build():
    tr = [(n, l, w, p) for i, (n, l, w, p) in enumerate(ee.TRACKS) if i not in DROP_TRACKS]
    vi = [(at, n) for at, n in ee.VIAS if not any(math.dist(at, d) < 0.01 for d in DROP_VIAS)]
    return tr + NEW_TRACKS, vi + NEW_VIAS


TRACKS, VIAS = _build()

if __name__ == "__main__":
    print(f"{len(TRACKS)} tracks, {len(VIAS)} vias (east escape minus the old column feeds, plus the new ones)")
