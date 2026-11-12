#!/usr/bin/env python3
"""Measure circuit-box layout from KiCad's own SVG plot (kicad-schematic-tidy Step 2).

For every sheet: finds the circuit boxes (the blue #0000C2 rectangles), collects every plotted
point of every other colour that lies inside each box (half the stroke width added), and reports
the padding on each edge in mil. Also checks the 100 mil start from the inner drawing border,
200 mil gaps to neighbouring boxes and clearance from the title block, all read from the plot.

Usage: python3 -I measure_boxes.py [svg_dir]   (exports a fresh SVG set when no dir is given)
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
BOX = "#0000C2"
MIL = 0.0254


def points(d):
    """Coordinates from an SVG path (M/L/A commands as KiCad writes them)."""
    pts = []
    for cmd, args in re.findall(r'([MLA])\s*([^MLAZz]*)', d):
        nums = [float(v) for v in re.findall(r'-?[\d.]+', args)]
        if cmd == "A":                         # rx ry rot large sweep x y: only the end point
            for i in range(0, len(nums) - 6, 7):
                pts.append((nums[i + 5], nums[i + 6]))
        else:
            pts += list(zip(nums[0::2], nums[1::2]))
    return pts


def parse(svg):
    """Walk the SVG tag by tag, keeping a stack of group styles (KiCad nests text groups)."""
    t = Path(svg).read_text()
    items, stack = [], [("#000000", 0.0)]
    for m in re.finditer(r'<(/?)(g|path|circle|rect)\b([^>]*)>', t, re.S):
        close, tag, attrs = m.groups()
        if tag == "g":
            if close:
                stack.pop()
                continue
            st = re.search(r'style="([^"]*)"', attrs, re.S)
            if st:
                style = st.group(1)
                col = re.search(r'stroke:(#[0-9A-Fa-f]{6})', style) or re.search(r'fill:(#[0-9A-Fa-f]{6})', style)
                wid = re.search(r'stroke-width:([\d.]+)', style)
                stack.append((col.group(1).upper() if col else stack[-1][0], float(wid.group(1)) if wid else stack[-1][1]))
            else:
                stack.append(stack[-1])
            if attrs.rstrip().endswith("/"):
                stack.pop()
            continue
        colour, w = stack[-1]
        if tag == "path":
            d = re.search(r'\bd="([^"]*)"', attrs, re.S)
            if d:
                items.append((colour, w, points(d.group(1))))
        elif tag == "circle":
            v = {k: float(x) for k, x in re.findall(r'\b(cx|cy|r)="([-\d.]+)"', attrs)}
            if len(v) == 3:
                items.append((colour, w, [(v["cx"] - v["r"], v["cy"] - v["r"]), (v["cx"] + v["r"], v["cy"] + v["r"])]))
        elif tag == "rect":
            v = {k: float(x) for k, x in re.findall(r'\b(x|y|width|height)="([-\d.]+)"', attrs)}
            if len(v) == 4:
                x0, y0 = v["x"], v["y"]
                items.append((colour, w, [(x0, y0), (x0 + v["width"], y0), (x0 + v["width"], y0 + v["height"]),
                                          (x0, y0 + v["height"])]))
    return items


def boxes(items):
    out = []
    for colour, w, pts in items:
        if colour != BOX or len(pts) < 4:
            continue
        xs, ys = {round(p[0], 3) for p in pts}, {round(p[1], 3) for p in pts}
        if len(xs) == 2 and len(ys) == 2 and w < 0.2:
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(set(out), key=lambda b: (round(b[1], 1), b[0]))


def measure(svg):
    items = parse(svg)
    bx = boxes(items)
    rows = []
    for b in bx:
        x0, y0, x1, y1 = b
        cx0 = cy0 = 1e9
        cx1 = cy1 = -1e9
        for colour, w, pts in items:
            if colour == BOX:
                continue
            for x, y in pts:
                if x0 < x < x1 and y0 < y < y1:
                    cx0, cy0 = min(cx0, x - w / 2), min(cy0, y - w / 2)
                    cx1, cy1 = max(cx1, x + w / 2), max(cy1, y + w / 2)
        rows.append((b, ((cx0 - x0) / MIL, (cy0 - y0) / MIL, (x1 - cx1) / MIL, (y1 - cy1) / MIL)))
    return rows


def main():
    if len(sys.argv) > 1:
        d = Path(sys.argv[1])
    else:
        d = Path(tempfile.mkdtemp(prefix="mindspark-svg-"))
        subprocess.run(["kicad-cli", "sch", "export", "svg", "-o", str(d), str(PROJ / "mindspark_rev1.kicad_sch")],
                       check=True, capture_output=True)
    fails = 0
    for svg in sorted(d.glob("*.svg")):
        rows = measure(svg)
        if not rows:
            continue
        print(svg.stem)
        inner = (12.0, 12.0, 285.0, 198.0)            # read from this export's frame (see README)
        for (b, (l, t, r, bo)) in rows:
            flag = ""
            if min(l, t, r, bo) < 300 - 0.5:
                flag += " PAD<300"
                fails += 1
            if max(l, t, r, bo) >= 350:
                flag += " (an edge >= 350 mil: box could shrink)"
            if b[2] > 177 - 2.54 + 0.01 and b[3] > 166 - 2.54 + 0.01:
                flag += " TITLE-BLOCK"
                fails += 1
            print("   box %6.2f,%6.2f-%6.2f,%6.2f  pad L%5.0f T%5.0f R%5.0f B%5.0f mil%s"
                  % (*b, l, t, r, bo, flag))
        starts = [b for b, _ in rows if abs(b[0] - (inner[0] + 2.54)) < 0.01]
        print("   boxes starting 100 mil from the inner left border: %d of %d; top row at %.2f mm (border+%.0f mil)"
              % (len(starts), len(rows), min(b[1] for b, _ in rows), (min(b[1] for b, _ in rows) - inner[1]) / MIL))
        gaps = []
        for a, _ in rows:
            for c, _ in rows:
                if a is c:
                    continue
                if abs(a[2] + 5.08 - c[0]) < 0.02 and not (a[3] < c[1] or c[3] < a[1]):
                    gaps.append("h")
                if abs(a[3] + 5.08 - c[1]) < 0.02 and not (a[2] < c[0] or c[2] < a[0]):
                    gaps.append("v")
        print("   exact 200 mil gaps between neighbours: %d horizontal, %d vertical" % (gaps.count("h"), gaps.count("v")))
    print("FAIL" if fails else "PASS", "(%d findings)" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
