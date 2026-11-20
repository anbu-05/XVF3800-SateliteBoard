"""East cap column, crystal and QSPI flash escape (agreed with the user 2026-11-21).

The plan was worked out in verification/jtag-proposal-2026-11-20/ (column_centred.py, then
column_full.py, render column_full.png). This script freezes that geometry into
east_escape_2026_11_21.json and applies it:

  Placement
    * East cap column centred on pins 17-27 (1.74 mm from the pin ends): C315, C303, C319 (turned,
      PLL pad east), FB301 (turned, PLL pad east), C316, C304, C323; the main USB pair below it,
      then C324, C313, C314.
    * Crystal Y301 turned and moved east so its XIN pad sits on the XIN lane; C320 and R302
      between it and the chip; R301 and C321 north of it. C318 (1.8 V bulk) to the LDO.
    * North cap row: C301 (pin 4) into the CS_N / CLK pocket; C310 (pin 8), C302 (pin 12) east.
  Fixed routes (laid by tools/power_v2_2026_11_18.py before any power copper, like the mic routes)
    * Fan-out of pins 16-30 into the column: XIN lane, power feeds to C315 / C303 / C316 / C304 /
      C313, pin 22 into the C319 / FB301 gap and the PLL stub, JTAG through the gaps and north in
      lanes east of the column (they stop just north of the module edge: the rest of JTAG is next).
    * Crystal: XIN, XOUT round the crystal's west side to R301, R301 / C321 to Y301 pad 3.
    * QSPI XVF3800 <-> U401: CS_N (+ R401 branch), D1, D2 from the east, D0 under the flash,
      D3 and CLK hop on F.Cu under the module (two vias each).
    * Pins 4 / 8 / 12 to C301 / C310 / C302, the flash's VCC to C401 and its GND pad to a via.
    * +0V9 jumpers on F.Cu: FB301's +0V9 pad to C304; C324's +0V9 pad to a via in the In2 +0V9
      island west of the pair's lanes (the lanes cut it off on B.Cu); and C304's via straight down
      to C324's, and a via in C303's +0V9 pad down to FB301's via (west of C319's GND via), both
      added after the first rebuild, so pins 19 / 27, C303, C304, C323 and FB301 reach the island
      too instead of floating.
    * The crystal's GND pads: vias 0.25 off their centres, away from the module's north-edge pads
      29 / 30 above them on F.Cu (power_v2's in-pad pass skips the centres there). The north-west
      one was added to the JSON by hand after the first rebuild (2026-11-21); generate() makes it too.
  The main USB pair's new B.Cu leg is in tools/usb_main_route_2026_11_19.py (edited 2026-11-21).
  Vias centred in pads over their own plane are left to power_v2's in-pad pass.

Usage (PCB editor closed):
  python3 tools/east_escape_2026_11_21.py --generate   freeze the plan into the JSON (from the
                                                        board as it was before the moves)
  python3 tools/east_escape_2026_11_21.py --place       move the parts (checked against the JSON)
Imported by power_v2 for TRACKS / VIAS.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "east_escape_2026_11_21.json")
W, VIA = 0.15, (0.45, 0.2)
ISLAND_VIA_0V9 = (149.95, 102.75)          # +0V9 island, west of the pair's lanes, for C324


def generate():
    """Run the agreed sketch (column_full.py, before its checks and drawing) on the current board."""
    proj = os.path.join(HERE, "..")
    os.chdir(proj)
    src = open("verification/jtag-proposal-2026-11-20/column_full.py").read()
    src = src.split("# ---------------------------------------------------------------- checks")[0]
    g = {"__name__": "column_full"}
    exec(compile(src, "column_full.py", "exec"), g)
    parts = {}
    for ref in list(g["new"]) + list(g["EXTRA"]):
        parts[ref] = {pn: [round((b[0] + b[2]) / 2, 4), round((b[1] + b[3]) / 2, 4)] for pn, b, _ in g["xpads"](ref)}
    tracks = []
    for net, w, pts in g["tracks"]:
        if net.startswith("/USB_MAIN") or net == "/XVF_SPI_CS_N":   # USB: own script; pin 6: escape pass
            continue
        tracks.append({"net": net, "layer": "B.Cu", "w": w, "pts": [[round(x, 4), round(y, 4)] for x, y in pts]})
    for net, w, pts in g["FT"]:
        tracks.append({"net": net, "layer": "F.Cu", "w": w, "pts": [[round(x, 4), round(y, 4)] for x, y in pts]})
    # C324's +0V9: via in its pad, F.Cu west to a via in the +0V9 island
    c324 = [c for pn, c in parts["C324"].items() if pn == "1"][0]
    tracks.append({"net": "+0V9", "layer": "F.Cu", "w": W,
                   "pts": [c324, [round(c324[0] - (c324[1] - ISLAND_VIA_0V9[1]), 4), ISLAND_VIA_0V9[1]],
                           list(ISLAND_VIA_0V9)]})
    c303, fbv = parts["C303"]["1"], parts["FB301"]["1"]           # C303's +0V9 pad down to FB301's via
    jx = round(c303[0] - 0.63, 4)
    tracks.append({"net": "+0V9", "layer": "F.Cu", "w": W,
                   "pts": [c303, [jx, round(c303[1] + 0.63, 4)], [jx, round(fbv[1] - (fbv[0] - jx), 4)], fbv]})
    c304 = parts["C304"]["1"]                                     # C304's via down to C324's on F.Cu
    tracks.append({"net": "+0V9", "layer": "F.Cu", "w": W, "pts": [c304, c324]})
    # vias: keep the ones power_v2's in-pad pass will not make (not centred in a pad over its plane)
    pad_centres = [(tuple(c), ref) for ref, pads in parts.items() for c in pads.values()]
    for ref in ("U401", "R401", "C401"):                        # not moved, but in-pad vias all the same
        pad_centres += [(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), ref) for _, b, _ in g["xpads"](ref)]
    keep_in_pad = {"FB301", "C304", "C324", "C303"}              # +0V9 pads over the +1V8 band
    vias = []
    y2 = parts["Y301"]["2"]                                      # crystal NW GND pad: via 0.25 north
    extra = [("GND", (y2[0], round(y2[1] - 0.25, 4)))]
    for net, (x, y) in g["VIAS"] + extra + [("+0V9", tuple(c324)), ("+0V9", ISLAND_VIA_0V9),
                                            ("+0V9", tuple(parts["C303"]["1"]))]:
        on = [ref for c, ref in pad_centres if math.dist(c, (x, y)) < 0.01]
        if on and not (set(on) & keep_in_pad):
            continue
        vias.append({"net": net, "at": [round(x, 4), round(y, 4)]})
    json.dump({"parts": parts, "tracks": tracks, "vias": vias}, open(DATA, "w"), indent=1)
    print(f"wrote {DATA}: {len(parts)} parts, {len(tracks)} tracks, {len(vias)} vias")


def place():
    sys.path.insert(0, HERE)
    from place_tidy import BOARD, Part
    from sexpr import parse, dump, children
    d = json.load(open(DATA))
    root = parse(open(BOARD).read())
    P = {Part(f).ref: Part(f) for f in children(root, "footprint")}

    def centres(ref):
        out = {}
        for pd, poly in zip(children(P[ref].node, "pad"), P[ref].pads()):
            xs, ys = [a for a, _ in poly], [b for _, b in poly]
            out[str(pd[1])] = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        return out

    for ref, want in d["parts"].items():
        cx = sum(c[0] for c in want.values()) / len(want)
        cy = sum(c[1] for c in want.values()) / len(want)
        best = None
        for rot in (0.0, 90.0, 180.0, -90.0):
            P[ref].place(0.0, 0.0, rot)
            have = centres(ref)
            hx = sum(c[0] for c in have.values()) / len(have)
            hy = sum(c[1] for c in have.values()) / len(have)
            P[ref].place(cx - hx, cy - hy, rot)              # footprint centre so the pads land on target
            have = centres(ref)
            err = max(math.dist(have[pn], want[pn]) for pn in want)
            if best is None or err < best[0]:
                best = (err, cx - hx, cy - hy, rot)
        err, x, y, rot = best
        if err > 0.01:
            sys.exit(f"{ref}: no rotation puts its pads on the plan (best {err:.3f} mm)")
        P[ref].place(round(x, 4), round(y, 4), rot)
        print(f"  {ref:6} at ({x:.3f}, {y:.3f}) rot {rot:>5}")
    open(BOARD, "w").write(dump(root) + "\n")
    print("wrote", BOARD)


def _load():
    if not os.path.exists(DATA):
        return [], []
    d = json.load(open(DATA))
    tr = [(t["net"], t["layer"], t["w"], [tuple(p) for p in t["pts"]]) for t in d["tracks"]]
    vi = [(tuple(v["at"]), v["net"]) for v in d["vias"]]
    return tr, vi


TRACKS, VIAS = _load()

if __name__ == "__main__":
    if "--generate" in sys.argv:
        generate()
    elif "--place" in sys.argv:
        place()
    else:
        print(f"{len(TRACKS)} tracks, {len(VIAS)} vias in {DATA}")
