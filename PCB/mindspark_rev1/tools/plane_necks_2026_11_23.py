"""Widen the In2 power-plane necks on the USB input paths (user 2026-11-23, after the routing review).

Usage (PCB editor closed):
    python3 tools/plane_necks_2026_11_23.py              # edit the board
    python3 tools/plane_necks_2026_11_23.py --check      # only report what would change
    python3 tools/plane_necks_2026_11_23.py --board FILE # work on a copy

Then refill and check:
    kicad-cli pcb drc --schematic-parity --refill-zones --save-board mindspark_rev1.kicad_pcb

The script is idempotent: a second run finds nothing to change. power_v2 and gnd_pour carry the
same changes (zone clearance, the two outlines, NO_STITCH boxes), so a rebuild keeps them; this
script is for the board as it stands.

Agreed with the user (2026-11-23):
  1. Every In2 power zone keeps 0.2 mm (was 0.3 mm) from other-net copper. Each via through
     In2 then leaves a 0.85 mm hole instead of 1.05 mm, and the gaps between neighbouring
     power areas shrink the same way, so every neck widens a little. JLC's minimum is 0.15 mm.
  2. Extra work only where the neck sits on a high-current path: the two USB input strips
     (VBUS_MAIN from J101 down to U103, VBUS_ESP out of J102 and round to U103). Necks in the
     low-current areas (+1V8, +0V9, the +5V islands, +3V3) only get the clearance change.
     No signal via could move far enough to help (tracks run tight above and below them), so
     the strips grow where the neighbouring +3V3 ground is free, and GND stitching vias come
     out of the tightest cuts.

Result, narrowest copper across each path (sum of the parallel paths through the via holes):
  VBUS_MAIN  2.7 -> 4.5 mm      VBUS_ESP exit at J102  1.9 -> 4.2 mm (rest of that strip 3.3)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children, child  # noqa: E402

IN2_CLEARANCE_OLD = "0.3"
IN2_CLEARANCE_NEW = "0.2"

# In2 outlines: net -> (old points, new points, what changed). power_v2's ZONES hold the new ones.
OUTLINES = {
    # South of J101 the signals that cross the LED ring (XVF_GPO_R, MUX_ST, the C802 +5V_LED
    # hop) put four vias in a near-solid row across the strip. The west edge (x 172.8 from
    # y 103.5) now runs at x 170.8 down to y 108.3, then back to x 172.8 at 45 degrees
    # (y 110.3), round the row's west end. That ground was +3V3 with no +3V3 via in it. The
    # 45-degree corner leaves the +3V3 via at (171.1, 110.9) (R607's pull-up feed) a corridor
    # north-west to the rest of +3V3 above the +5V area; a square corner cut it off.
    "VBUS_MAIN": (
        [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 115.25),
         (173.3, 115.25), (173.3, 112.6), (172.8, 112.6), (172.8, 103.5), (170.8, 103.5)],
        [(170.8, 94.8), (178.6, 94.8), (178.6, 117.2), (171.0, 117.2), (171.0, 115.25),
         (173.3, 115.25), (173.3, 112.6), (172.8, 112.6), (172.8, 110.3), (170.8, 108.3)],
        "west edge x 170.8 down to y 108.3, 45 deg back to x 172.8"),
    # Where the strip leaves J102, the connector's shell leg (a plated hole at the strip's west
    # side) and the square step from x 122.3 in to x 118.9 at y 103.5 left about 2.3 mm. The
    # step is now a 45-degree chamfer from (122.3, 104.5) to (118.9, 107.9); no +3V3 via sits
    # in that corner.
    "VBUS_ESP": (
        [(114.6, 94.8), (122.3, 94.8), (122.3, 103.5), (118.9, 103.5), (118.9, 130.5),
         (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)],
        [(114.6, 94.8), (122.3, 94.8), (122.3, 104.5), (118.9, 107.9), (118.9, 130.5),
         (164.6, 130.5), (164.6, 115.05), (170.7, 115.05), (170.7, 134.9), (114.6, 134.9)],
        "step under J102 becomes a 45 deg chamfer (122.3, 104.5) -> (118.9, 107.9)"),
}

# GND stitching vias taken out of the two VBUS strips' tightest cuts. They only tie the F.Cu
# and B.Cu pours together, and the next grid row inward still does that. gnd_pour keeps
# stitching out of the same boxes (NO_STITCH there).
DROPS = [
    ("GND", (176.558, 108.679)),    # VBUS_MAIN, grid via beside the ring-crossing row
    ("GND", (176.283, 106.367)),    # VBUS_MAIN, grid via north of the row (nudged off the lattice)
    ("GND", (116.558, 103.929)),    # VBUS_ESP, grid via where the strip leaves J102
    ("GND", (116.558, 108.679)),    # VBUS_ESP, grid via in the west strip beside ESP_BOOT's via
]

TOL = 0.002   # mm: how close two points must be to count as the same spot


def same(a, b):
    return abs(a[0] - b[0]) < TOL and abs(a[1] - b[1]) < TOL


def same_poly(a, b):
    return len(a) == len(b) and all(same(p, r) for p, r in zip(a, b))


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def main():
    check = "--check" in sys.argv
    path = sys.argv[sys.argv.index("--board") + 1] if "--board" in sys.argv else BOARD
    root = parse(open(path).read())
    changes = []

    for z in children(root, "zone"):
        layer = child(z, "layer")
        if not layer or layer[1] != "In2.Cu":
            continue
        net = child(z, "net")[1]

        # 1. clearance to other-net copper
        clr = child(child(z, "connect_pads"), "clearance")
        if clr[1] == IN2_CLEARANCE_OLD:
            clr[1] = IN2_CLEARANCE_NEW
            changes.append(f"zone {net} In2 clearance {IN2_CLEARANCE_OLD} -> {IN2_CLEARANCE_NEW}")

        # 2. outline
        if net in OUTLINES:
            old, new, what = OUTLINES[net]
            pts = child(child(z, "polygon"), "pts")
            now = [(float(p[1]), float(p[2])) for p in children(pts, "xy")]
            if same_poly(now, old):
                pts[1:] = [["xy", fmt(x), fmt(y)] for x, y in new]
                for fp in children(z, "filled_polygon"):     # stale fill; kicad-cli refills
                    z.remove(fp)
                changes.append(f"zone {net} In2 outline: {what}")
            elif not same_poly(now, new):
                sys.exit(f"{net} outline is neither the old nor the new one: {now}")

    # 3. stitching vias out of the tightest cuts
    for net, at in DROPS:
        for v in children(root, "via"):
            a = child(v, "at")
            if child(v, "net")[1] == net and same((float(a[1]), float(a[2])), at):
                root.remove(v)
                changes.append(f"via {net} at {at} removed")

    for c in changes:
        print(c)
    if not changes:
        print("nothing to change")
    elif not check:
        open(path, "w").write(dump(root) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
