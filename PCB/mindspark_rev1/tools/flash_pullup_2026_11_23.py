"""R407: 4.7k pull-up on XVF_QSPI_D3 (flash HOLD#) for the GD25Q16E flash (user 2026-11-23).

Why: the replacement flash GD25Q16ENIGR ships with its Quad Enable bit at 0, so pin 7 works as
HOLD# until something sets QE. During ESP32 programming (path B) the XVF3800 is held in reset,
and in reset every XVF GPIO has a weak pull-down on (XU316 datasheet section 8), which would pull
HOLD# low and pause the flash. R407 holds it high; XMOS asks for 4.7k to beat the internal pull
(XU316 datasheet DC characteristics, note D). Once QE is 1, pin 7 is IO3 and the XVF drives it.
D2 (WP#) gets no pull-up on purpose: it is XVF boot pin X0D06 (XU316 datasheet section 9,
Figure 14), and a high level there selects another boot mode. WP# low does nothing while the
flash's SRP1/SRP0 bits are 0 (factory default, GD25Q16E datasheet table "SRP1, SRP0 bits").

Placement (bottom side, PCB editor closed; done by tools/part_swap_2026_11_23.py): upright 0402
in the strip between the MIC_DATA0 line (x 137.3) and U401's west pads, pad 2 (D3) on the D3
via, pad 1 (+3V3) above it, joined to U401's VCC pad on the bottom layer (PAD1_RUN).
Clearances: pad to MIC_DATA0 0.155 mm (rule 0.15), courtyard clear of U401 (0.05) and C401.

power_v2 calls nudge() on the user's frozen snapshot: the D3 via moves 0.05 mm east onto
R407's pad 2 centre (vias sit centred in pads), and its two tracks are re-ended so every run
stays at 0 or 45 degrees.
"""
import math

REF = "R407"
POS = (137.85, 92.99)          # footprint centre, bottom side
ROT = 90.0                     # upright; part_swap checks pad 2 ends up at the lower (south) spot
VALUE = "4.7k"

OLD_VIA, NEW_VIA = (137.8, 93.5), (137.85, 93.5)
# pad 1 (+3V3) joins U401 pin 8 (VCC, centre (139.15, 92.96)) on the bottom layer, 0.2 mm wide:
# east along the pad's row, then 45 degrees down onto the VCC pad centre (laid by power_v2).
# A via is not possible: the top layer above is the line field under the ESP32 module.
PAD1_RUN = [(137.85, 92.48), (138.67, 92.48), (139.15, 92.96)]
EDITS = [  # net, layer, old (a, b), new (a, b)
    ("/XVF_QSPI_D3", "F.Cu", ((143.87, 93.5), (137.8, 93.5)), ((143.87, 93.5), (137.85, 93.5))),
    ("/XVF_QSPI_D3", "B.Cu", ((138.06, 93.76), (137.8, 93.5)), ((138.11, 93.76), (137.85, 93.5))),
    ("/XVF_QSPI_D3", "B.Cu", ((139.15, 93.76), (138.06, 93.76)), ((139.15, 93.76), (138.11, 93.76))),
]


def _same(p, q):
    return math.dist(p, q) < 2e-3


def nudge(tracks, vias, log=None):
    """Apply EDITS and the via move to the snapshot lists; stop if anything is not found."""
    tracks = [list(t) for t in tracks]
    vias = [list(v) for v in vias]
    for net, layer, (a, b), new in EDITS:
        hit = [t for t in tracks if t[0] == "segment" and t[1] == net and t[2] == layer
               and ((_same(t[4][0], a) and _same(t[4][1], b)) or (_same(t[4][0], b) and _same(t[4][1], a)))]
        if len(hit) != 1:
            raise SystemExit(f"flash_pullup: {net} {layer} {a}-{b} not found once in the snapshot")
        hit[0][4] = [list(new[0]), list(new[1])]
    v = [x for x in vias if x[0] == "/XVF_QSPI_D3" and _same(x[1], OLD_VIA)]
    if len(v) != 1:
        raise SystemExit("flash_pullup: D3 via not found in the snapshot")
    v[0][1] = list(NEW_VIA)
    msg = f"flash pull-up: D3 via {OLD_VIA} -> {NEW_VIA} (R407 pad 2), 3 tracks re-ended"
    if log is not None:
        log.append(msg)
    return tracks, vias
