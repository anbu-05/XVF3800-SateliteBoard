"""Escape map of a chip: which way each pin's trace has to leave, and where it goes.

    python3 tools/escape_map.py REF OUTDIR [zoom_mm] [--edge-sensitive] [--board=PATH]   (run from the project folder)

--edge-sensitive keeps only the length-sensitive nets listed in SENSITIVE below, and of their
destinations only those near a board edge (test pads left out: they can be moved). It writes
REF-escape-edge.png / .md next to the full map.

For every pin of REF it finds the other pads on the pin's net (following through a series
resistor next to the chip, e.g. the ESP32's USB 27R), then sorts the pin into a group:

  N / E / S / W   signal: the side of the chip that faces its (nearest far) destination
  local           signal whose only destinations are close by on the chip's own side
                  (crystal, flash, mic-clock buffer ...)
  power           power pin: decoupling caps next to it, or a plane via (+1V8: the LDO)
  GND / NC        ground (plane) and unconnected pins

Writes OUTDIR/REF-escape.png (left: the chip with each pin coloured by group and labelled
with its destinations; right: the whole board with a line from each pin to its destinations)
and OUTDIR/REF-escape.md (the same as a table). Coordinates are the board's (seen from the
top, as KiCad shows it by default), so a bottom-side chip appears mirrored compared with
its datasheet drawing.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD, LEFT, RIGHT, TOP, BOTTOM, Part, bbox  # noqa: E402
from sexpr import parse, children, child  # noqa: E402
from PIL import Image, ImageDraw, ImageFont

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
REF, OUT = ARGS[0], ARGS[1]
ZOOM = float(ARGS[2]) if len(ARGS) > 2 else 30.0
EDGE_ONLY = "--edge-sensitive" in sys.argv
EDGE_MM = 8.0           # a destination part whose courtyard comes this close to the board edge is "at the edge"
# Length-sensitive nets (2026-11-18): differential pairs and signals clocked against another line.
SENSITIVE = {
    "/USB_MAIN_DP": "USB 2.0 high-speed pair (90 ohm, match D+/D-)",
    "/USB_MAIN_DM": "USB 2.0 high-speed pair (90 ohm, match D+/D-)",
    "/esp32/ESP_USB_DP": "USB full-speed pair (match D+/D-)",
    "/esp32/ESP_USB_DM": "USB full-speed pair (match D+/D-)",
    "/MIC_DATA0": "PDM data, sampled on MIC_CLK edges",
    "/MIC_DATA1": "PDM data, sampled on MIC_CLK edges",
    "/MIC_DATA2": "PDM data, sampled on MIC_CLK edges",
    "/MIC_DATA3": "PDM data, sampled on MIC_CLK edges",
    "/xvf3800/XVF_TCK": "JTAG clock",
    "/xvf3800/XVF_TMS": "JTAG, sampled on TCK",
    "/xvf3800/XVF_TDI": "JTAG, sampled on TCK",
    "/xvf3800/XVF_TDO": "JTAG, sampled on TCK",
    "/XVF_I2S_DATA1": "I2S data, timed against BCLK",
    "/XVF_I2S_DATA2": "I2S data, timed against BCLK",
}
LOCAL_MM = 9.0          # a destination this close, on the chip's side, counts as local fan-out
POWER = {"+3V3", "+0V9", "+1V8", "+5V", "PLL_AVDD", "VBUS_MAIN", "VBUS_ESP"}
COL = {"N": (30, 110, 230), "E": (240, 130, 0), "S": (0, 160, 70), "W": (160, 40, 200),
       "local": (0, 160, 170), "power": (210, 40, 40), "GND": (120, 120, 120), "NC": (255, 255, 255)}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# --board=PATH analyses another copy of the board (e.g. a trial placement in a scratch folder)
BOARD = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--board=")), BOARD)
root = parse(open(BOARD).read())
parts, by_net = {}, {}
for f in children(root, "footprint"):
    p = Part(f)
    parts[p.ref] = p
    for pd, poly in zip(children(f, "pad"), p.pads()):
        net = str(child(pd, "net")[1]) if child(pd, "net") else ""
        b = bbox(poly)
        by_net.setdefault(net, []).append(dict(ref=p.ref, pin=str(pd[1]), net=net, poly=poly,
                                                c=((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), side=p.side[0]))
chip = parts[REF]
box = bbox(chip.courtyard())
CX, CY = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def short(net):
    for pre in ("/xvf3800/", "/esp32/", "/usb_power/", "/audio/", "/led_ring/", "/"):
        if net.startswith(pre):
            return net[len(pre):]
    return net


def side_of(pt):
    """Which side of the chip box faces point pt (by angle from the chip centre)."""
    a = math.degrees(math.atan2(pt[1] - CY, pt[0] - CX))       # y grows downwards
    if -45 <= a < 45:
        return "E"
    if 45 <= a < 135:
        return "S"
    if -135 <= a < -45:
        return "N"
    return "W"


def pin_side(c):
    """Which edge of the chip the pad itself sits on."""
    d = {"W": c[0] - box[0], "E": box[2] - c[0], "N": c[1] - box[1], "S": box[3] - c[1]}
    return min(d, key=d.get)


def destinations(pad):
    """Other pads on this pad's net; a 2-pad resistor next to the chip is followed through."""
    out = []
    for o in by_net.get(pad["net"], []):
        if o["ref"] == REF:
            continue
        r = parts[o["ref"]]
        if (o["ref"].startswith("R") and math.dist(o["c"], pad["c"]) < 4.0
                and len(children(r.node, "pad")) == 2):
            other = [x for n, lst in by_net.items() for x in lst if x["ref"] == o["ref"] and x["pin"] != o["pin"]]
            if other and other[0]["net"] not in POWER | {"GND", ""}:
                out += [dict(x, via_r=o["ref"]) for x in by_net[other[0]["net"]] if x["ref"] != o["ref"]]
                continue
        out.append(o)
    return out


rows = []
for pd, poly in zip(children(chip.node, "pad"), chip.pads()):
    net = str(child(pd, "net")[1]) if child(pd, "net") else ""
    b = bbox(poly)
    pad = dict(pin=str(pd[1]), net=net, poly=poly, c=((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    own = pin_side(pad["c"])
    if net == "GND":
        group, dests, far = "GND", [], []
    elif not net or net.startswith("unconnected"):
        group, dests, far = "NC", [], []
    elif net in POWER:
        dests = destinations(pad)
        group, far = "power", []
    else:
        dests = destinations(pad)
        far = [d for d in dests if not (d["side"] == chip.side[0] and math.dist(d["c"], pad["c"]) < LOCAL_MM)]
        # Test pads can be moved, so they only decide the group when nothing else is there.
        real = [d for d in far if not d["ref"].startswith("TP")] or far
        if real:
            near = min(real, key=lambda d: math.dist(d["c"], pad["c"]))
            group = side_of(near["c"])
        else:
            group = "local"
        multi = sorted({side_of(d["c"]) for d in real}) if real else []
    if group in ("GND", "NC", "power"):
        multi = []
    rows.append(dict(pad, own=own, group=group, dests=dests, far=far, multi=multi if len(multi) > 1 else []))



def at_edge(dst):
    """True if the destination part's courtyard reaches within EDGE_MM of the board edge."""
    p = parts[dst["ref"]]
    c = bbox(p.courtyard()) if p.local_box("CrtYd") else (dst["c"][0], dst["c"][1]) * 2
    return min(c[0] - LEFT, RIGHT - c[2], c[1] - TOP, BOTTOM - c[3]) < EDGE_MM


# In --edge-sensitive mode every other pin is drawn faint and left out of the table.
for r_ in rows:
    r_["hidden"] = False
    if EDGE_ONLY:
        keep = [x for x in r_["far"] if at_edge(x) and not x["ref"].startswith("TP")]
        if r_["net"] in SENSITIVE and keep:
            r_["far"] = keep
            r_["group"] = side_of(min(keep, key=lambda x: math.dist(x["c"], r_["c"]))["c"])
            r_["multi"] = []
        else:
            r_["hidden"] = True
SUF = "-edge" if EDGE_ONLY else ""
shown = [r for r in rows if not r["hidden"]]

# ------------------------------------------------------------------ table
layer_word = {"F": "top", "B": "bottom"}
with open(os.path.join(OUT, f"{REF}-escape{SUF}.md"), "w") as fh:
    fh.write(f"# {REF} escape map ({chip.props.get('Value', '')}, {layer_word[chip.side[0]]} side)"
             f"{': length-sensitive signals to a board edge' if EDGE_ONLY else ''}\n\n")
    fh.write("Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), "
             "`local` = only close destinations on the same side, `power` = decoupling / plane, "
             "`wraps` = destination is not on the pin's own side. "
             "Layer change = destination on the other side of the board (needs a via). "
             "Test pads (TP) are movable, so they set the group only when nothing else is on the net; "
             "`also X` = real destinations in more than one direction.\n\n")
    fh.write("| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) |"
             + (" Why length-sensitive |\n|---|---|---|---|---|---|---|\n" if EDGE_ONLY else "\n|---|---|---|---|---|---|\n"))
    order = ["N", "E", "S", "W", "local", "power", "GND", "NC"]
    for r_ in sorted(shown, key=lambda r: (order.index(r["group"]), r["c"])):
        dl = r_["far"] if EDGE_ONLY else r_["dests"]
        ds = ", ".join(f"{d['ref']}.{d['pin']} ({d['side']}{', via ' + d['via_r'] if d.get('via_r') else ''}, "
                       f"{math.dist(d['c'], r_['c']):.0f})"
                       for d in sorted(dl, key=lambda d: math.dist(d["c"], r_["c"]))[:6])
        wraps = "yes" if r_["group"] in "NESW" and r_["group"] != r_["own"] else ""
        flip = any(d["side"] != chip.side[0] for d in r_["far"])
        multi = f" (also {'/'.join(x for x in r_['multi'] if x != r_['group'])})" if r_["multi"] else ""
        fh.write(f"| {r_['pin']} | {r_['own']} | {short(r_['net'])} | {r_['group']}{multi}"
                 f"{' + layer change' if flip else ''} | {wraps} | {ds} |"
                 + (f" {SENSITIVE[r_['net']]} |\n" if EDGE_ONLY else "\n"))

# ------------------------------------------------------------------ picture
SZ = 40                                         # px per mm in the zoom panel
SB = 13                                         # px per mm in the board panel
zx0, zy0 = CX - ZOOM / 2, CY - ZOOM / 2
ZW = int(ZOOM * SZ)
BW = int((RIGHT - LEFT + 4) * SB)
H = max(ZW, BW) + 150
img = Image.new("RGB", (ZW + BW + 30, H), "white")
d = ImageDraw.Draw(img, "RGBA")
f_small, f_lab, f_big = (ImageFont.truetype(FONT, 11), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 18))
Z = lambda x, y: ((x - zx0) * SZ, (y - zy0) * SZ + 40)
bx0, by0 = LEFT - 2, TOP - 2
B = lambda x, y: (ZW + 30 + (x - bx0) * SB, (y - by0) * SB + 40)

# zoom panel: neighbouring parts faint, chip pads coloured
for p in parts.values():
    for poly in p.pads():
        if all(zx0 <= x <= zx0 + ZOOM and zy0 <= y <= zy0 + ZOOM for x, y in poly) and p.ref != REF:
            d.polygon([Z(*q) for q in poly], outline=(200, 200, 200), fill=(240, 240, 240) if p.side == chip.side else None)
d.rectangle([Z(box[0], box[1]), Z(box[2], box[3])], outline=(0, 0, 0), width=2)


def text_rot(xy, s, font, fill, angle):
    w, h = int(d.textlength(s, font=font)) + 4, font.size + 6
    t = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((2, 1), s, font=font, fill=fill)
    t = t.rotate(angle, expand=True)
    img.paste(t, (int(xy[0]), int(xy[1])), t)
    return t.size


pc = bbox([r["c"] for r in rows])                 # outline of the pad centres: edge pins sit on it
for r_ in rows:
    col = COL[r_["group"]]
    if r_["hidden"]:
        d.polygon([Z(*q) for q in r_["poly"]], fill=(225, 225, 225), outline=(170, 170, 170))
        continue
    d.polygon([Z(*q) for q in r_["poly"]], fill=col + (230,), outline=(0, 0, 0))
    inner = (pc[0] + 0.5 < r_["c"][0] < pc[2] - 0.5) and (pc[1] + 0.5 < r_["c"][1] < pc[3] - 0.5)
    if r_["group"] == "GND" or inner:
        continue                                   # centre / paddle pads: no label
    if r_["group"] in ("power", "NC"):
        lab = f"{r_['pin']} {short(r_['net'])[:16]}"
    else:
        real = [x for x in r_["far"] if not x["ref"].startswith("TP")] or r_["far"] or r_["dests"]
        dest = ", ".join(sorted({x["ref"] for x in real}))[:26]
        tp = " +TP" if any(x["ref"].startswith("TP") for x in r_["far"]) and real is not r_["far"] else ""
        lab = f"{r_['pin']} {short(r_['net'])[:16]} > {dest}{tp}" + (" *" if r_["multi"] else "")
    wraps = r_["group"] in "NESW" and r_["group"] != r_["own"]
    fill = (0, 0, 0) if not wraps else (200, 0, 0)
    x, y = Z(*r_["c"])
    edge = {"E": Z(box[2], 0)[0], "W": Z(box[0], 0)[0], "N": Z(0, box[1])[1], "S": Z(0, box[3])[1]}[r_["own"]]
    gap = 0.8 * SZ
    if r_["own"] == "E":
        d.line([(x, y), (edge + gap, y)], fill=col, width=1)
        d.text((edge + gap + 3, y - 7), lab, font=f_small, fill=fill)
    elif r_["own"] == "W":
        w = d.textlength(lab, font=f_small)
        d.line([(x, y), (edge - gap, y)], fill=col, width=1)
        d.text((edge - gap - 3 - w, y - 7), lab, font=f_small, fill=fill)
    elif r_["own"] == "N":
        w = d.textlength(lab, font=f_small)
        d.line([(x, y), (x, edge - gap)], fill=col, width=1)
        text_rot((x - 8, edge - gap - 3 - w - 4), lab, f_small, fill, 90)
    else:
        d.line([(x, y), (x, edge + gap)], fill=col, width=1)
        text_rot((x - 8, edge + gap + 3), lab, f_small, fill, 90)
d.text((8, 8), f"{REF} {chip.props.get('Value', '')}: "
               f"{'length-sensitive signals to a board edge, ' if EDGE_ONLY else ''}pins by escape side "
               f"({layer_word[chip.side[0]]} side, seen from the top)", font=f_big, fill="black")

# board panel
d.rectangle([B(LEFT, TOP), B(RIGHT, BOTTOM)], outline=(0, 0, 0), width=2)
for p in parts.values():
    if p.local_box("CrtYd") and (p.ref[0] in "UJ" or p.ref.startswith(("SW", "MK", "H"))):
        c = bbox(p.courtyard())
        d.rectangle([B(c[0], c[1]), B(c[2], c[3])], outline=(190, 190, 190))
        d.text(B(c[0] + 0.2, c[1] + 0.1), p.ref, font=f_small, fill=(150, 150, 150))
d.rectangle([B(box[0], box[1]), B(box[2], box[3])], outline=(0, 0, 0), width=3)
labelled = set()
for r_ in shown:
    if r_["group"] not in "NESW":
        continue
    for t in r_["far"]:
        if t["ref"].startswith("TP") and any(not x["ref"].startswith("TP") for x in r_["far"]):
            a, b_ = B(*r_["c"]), B(*t["c"])
            d.line([a, b_], fill=(170, 170, 170, 120), width=1)       # test pad: movable, drawn faint
            continue
        dash = t["side"] != chip.side[0]
        a, b_ = B(*r_["c"]), B(*t["c"])
        if dash:                                  # destination on the other side of the board
            n = max(2, int(math.dist(a, b_) / 8))
            for k in range(0, n, 2):
                p1 = (a[0] + (b_[0] - a[0]) * k / n, a[1] + (b_[1] - a[1]) * k / n)
                p2 = (a[0] + (b_[0] - a[0]) * (k + 1) / n, a[1] + (b_[1] - a[1]) * (k + 1) / n)
                d.line([p1, p2], fill=COL[r_["group"]] + (200,), width=2)
        else:
            d.line([a, b_], fill=COL[r_["group"]] + (200,), width=2)
        d.ellipse([b_[0] - 3, b_[1] - 3, b_[0] + 3, b_[1] + 3], fill=COL[r_["group"]])
        key = t["ref"]
        if key not in labelled:
            labelled.add(key)
            d.text((b_[0] + 4, b_[1] - 6), key, font=f_small, fill=(0, 0, 0))
d.text((ZW + 38, 8), "Where each signal goes (solid: same side, dashed: other side of the board)",
       font=f_big, fill="black")

# legend
yy, xx = H - 100, 10
legend = (("N", "north"), ("E", "east"), ("S", "south"), ("W", "west"))
if not EDGE_ONLY:
    legend += (("local", "local fan-out"), ("power", "power / decoupling"), ("GND", "GND"), ("NC", "not connected"))
for k, lab in legend:
    d.rectangle([xx, yy, xx + 18, yy + 18], fill=COL[k], outline=(0, 0, 0))
    d.text((xx + 24, yy), lab, font=f_lab, fill="black")
    xx += 34 + d.textlength(lab, font=f_lab)
d.text((10, yy + 30), "Red label: the pin's destination is not on the side the pin sits on (the trace has to wrap round the chip). "
                      "Labels: pin, net > destination parts (+TP: also a test pad; * real destinations in more than one direction). "
                      "Grey lines: test pads (movable).", font=f_lab, fill=(150, 0, 0))
if EDGE_ONLY:
    d.text((10, yy + 74), "Grey pads: not length-sensitive, or no destination at a board edge. Test pads left out "
                          "(movable). Edge = destination courtyard within %.0f mm of the board edge." % EDGE_MM,
           font=f_lab, fill="black")
counts = {}
for r_ in shown:
    counts[r_["group"]] = counts.get(r_["group"], 0) + 1
d.text((10, yy + 52), "Counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()), font=f_lab, fill="black")
img.save(os.path.join(OUT, f"{REF}-escape{SUF}.png"))
print(REF, counts)
