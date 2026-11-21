"""Route of the XVF3800 main USB pair, U301 pins 28/29 -> U101 -> J101 (agreed 2026-11-19).

tools/power_v2_2026_11_18.py rebuilds every track on the board, so it imports this file and lays
the pair first (before any power copper), as fixed geometry the power router then avoids.
Run on its own, this file prints the length of each line.

Geometry (all 0/45/90 degree, ends on pad / via centres):
  * Width 0.25 mm, gap 0.15 mm (pitch 0.4 = the XVF3800's pin pitch). For JLC's 4-layer stack
    (outer layer ~0.21 mm above its plane, Er ~4.4) the edge-coupled microstrip formulas give
    ~92 ohm differential; solder mask takes it a few ohm lower, so close to the 90 ohm target.
    To be confirmed with JLC's impedance calculator before ordering.
  * B.Cu from the pins (D- north, D+ south): since 2026-11-22 (user's suggestion) straight east
    from pins 28/29 through the east cap column (C316 above, C313 below) to the two 0.45/0.2
    vias just outside the ESP32 module, spread to 0.8 mm. In2 +1V8 now runs under the east
    pins (power_v2), so the pair stays over one plane: C323/C324 are gone; C325/C326 (+1V8/GND)
    still sit either side of the vias. (2026-11-21 to -22 it dipped south under the column.)
  * F.Cu (over In1 GND): since 2026-11-22 the flash switches have moved west of the module, so
    the pair runs east from the vias, takes one 45 degree jog up to the 98.78 / 99.18 rows and
    on to U101; D- jogs up to U101 pad 7, D+ runs straight into pad 9;
    each line runs straight across U101 (pad 7 -> 4, pad 9 -> 2, flow-through) and on to
    J101 A7 / A6.
  * J101's pins alternate D+ D- D+ D-, so B6 (D+) and B7 (D-) are reached by two short B.Cu
    jumpers east of the LED ring: F.Cu stubs from the pad ends to vias, then B.Cu.
"""
import math

W, VIA = 0.25, (0.45, 0.2)
DM, DP = "/USB_MAIN_DM", "/USB_MAIN_DP"

# pad / via centres used below
PIN28, PIN29 = (150.06, 100.68), (150.06, 101.08)          # U301 (bottom side)
V_DM, V_DP = (157.35, 100.48), (157.35, 101.28)             # layer change, just outside the module
U101_7, U101_4 = (173.825, 98.18), (174.595, 98.18)         # D- across U101
U101_9, U101_2 = (173.825, 99.18), (174.595, 99.18)         # D+ across U101
J_A7, J_B7 = (176.495, 98.43), (176.495, 99.43)             # J101 D- pins
J_A6, J_B6 = (176.495, 98.93), (176.495, 97.93)             # J101 D+ pins
JV_A6, JV_B6 = (177.6, 98.93), (177.6, 97.93)               # D+ jumper vias (x 177.6)
JV_A7, JV_B7 = (178.3, 98.43), (178.3, 99.43)               # D- jumper vias (x 178.3)

X1 = 158.6                                                   # where the pair starts up
TRACKS = [  # net, layer, points
    # bottom layer: pins -> layer-change vias, straight east
    (DM, "B.Cu", [PIN28, (156.6, 100.68), (156.8, 100.48), V_DM]),
    (DP, "B.Cu", [PIN29, (156.6, 101.08), (156.8, 101.28), V_DP]),
    # top layer: vias -> one 45 degree jog up -> U101
    (DM, "F.Cu", [V_DM, (X1, 100.48), (X1 + 1.7, 98.78), (172.3, 98.78), (172.9, 98.18), U101_7]),
    # D+ straight into pad 9: D-'s jog into pad 7 already evens the lengths (no bump needed now)
    (DP, "F.Cu", [V_DP, (157.75, 100.88), (X1 + 0.166, 100.88), (X1 + 0.166 + 1.7, 99.18), U101_9]),
    # across U101 (flow-through) and on to J101
    (DM, "F.Cu", [U101_7, U101_4, (175.1, 98.18), (175.35, 98.43), J_A7]),
    (DP, "F.Cu", [U101_9, U101_2, (175.1, 99.18), (175.35, 98.93), J_A6]),
    # J101 jumpers: F.Cu stubs to vias, B.Cu links
    (DP, "F.Cu", [J_A6, JV_A6]), (DP, "F.Cu", [J_B6, JV_B6]), (DP, "B.Cu", [JV_A6, JV_B6]),
    (DM, "F.Cu", [J_A7, JV_A7]), (DM, "F.Cu", [J_B7, JV_B7]), (DM, "B.Cu", [JV_A7, JV_B7]),
]
VIAS = [(V_DM, DM), (V_DP, DP), (JV_A6, DP), (JV_B6, DP), (JV_A7, DM), (JV_B7, DM)]


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def main_lengths():
    """Length from the XVF3800 pin to J101's A pin (the main path; jumpers listed apart)."""
    out = {}
    for net in (DM, DP):
        main = [t for t in TRACKS[:6] if t[0] == net]
        out[net] = sum(length(p) for _, _, p in main)
    return out


if __name__ == "__main__":
    L = main_lengths()
    for net, v in L.items():
        print(f"{net}: {v:.2f} mm pin -> J101 A pin (+2 vias)")
    print(f"mismatch {abs(L[DM] - L[DP]):.2f} mm")
    for net, layer, pts in TRACKS[6:]:
        print(f"  jumper {net} {layer} {length(pts):.2f} mm")
