"""Mindspark rev 1 schematic generator core.

Adapted from the PDB project's native_schematic.py, with the kicad-schematic-tidy rules built
in from the start:
  * everything on the 50 mil (1.27 mm) grid, orthogonal wires;
  * every connected pin gets exactly one 100 mil (2.54 mm) lead to its first anchor
    (label, power symbol, or the next part's pin);
  * each functional block is a "group" drawn inside its own circuit box, and boxes are packed
    left-to-right, top-to-bottom on A4 with 100 mil border clearance, 200 mil gaps and
    300 mil internal padding.

Connections are made with power symbols (rails), hierarchical labels (signals that leave the
sheet) and local labels (signals inside the sheet). Every placed pin is recorded in a manifest
with the net it is meant to be on, and verify_schematic.py checks KiCad's own netlist against it.
"""
import copy
import math
import uuid
from pathlib import Path

from sexpr import child, children, parse, q, walk

PROJECT_DIR = Path(__file__).resolve().parents[1]
LIBFILE = PROJECT_DIR.parent / "libraries" / "symbols" / "Mindspark.kicad_sym"
PROJECT = "mindspark_rev1"
ROOT_UUID = "af1cbb83-54b2-47b9-8bc4-08bc42da7d01"    # uuid of the existing root file
NS = uuid.UUID("5b3f0f3e-6d0e-4a59-9a77-0d6c3f1b2e11")  # fixed: reruns give identical UUIDs
DATE = "2026-11-10"

G = 1.27          # 50 mil grid
LEAD = 2.54       # 100 mil pin lead
PAD = 7.62        # 300 mil box padding
GAP = 5.08        # 200 mil between boxes
TEXT = 1.0        # label and field text size (PDB used 0.95)

# Rails drawn with power symbols. Anything else is a label.
POWER_NETS = {"GND", "+5V", "+3V3", "+1V8", "+0V9", "VBUS_MAIN", "VBUS_ESP",
              "+5V_AMP", "+5V_LED", "+3V3_MIC", "PLL_AVDD"}

PAPER = {  # inner drawing border and title-block corner of KiCad's default drawing sheet
    "A4": dict(w=297, h=210, x0=12.0, y0=12.0, x1=285.0, y1=198.0, tbx=177.0, tby=166.0),
    "A3": dict(w=420, h=297, x0=12.0, y0=12.0, x1=408.0, y1=285.0, tbx=300.0, tby=253.0),
}


def uid(name):
    return str(uuid.uuid5(NS, name))


def num(v):
    """Format a coordinate the way KiCad does (no trailing zeros)."""
    s = "%.4f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def on_grid(v):
    return abs(v / G - round(v / G)) < 1e-6


def text_width(s, size=TEXT):
    """Rough width of KiCad's stroke font; deliberately generous so boxes are never too tight."""
    return len(s) * size * 0.98 + 0.4


# ----------------------------------------------------------------------------------------
# Library access
# ----------------------------------------------------------------------------------------
class Library:
    def __init__(self, path=LIBFILE):
        tree = parse(path.read_text())
        self.syms = {str(s[1]): s for s in children(tree, "symbol")}

    def node(self, name):
        """Copy of the symbol for lib_symbols, named 'Mindspark:<name>' (sub-symbols keep the
        bare name, as KiCad writes them)."""
        sym = copy.deepcopy(self.syms[name])
        sym[1] = q("Mindspark:" + name)
        return sym

    def prop(self, name, key, default=""):
        for p in children(self.syms[name], "property"):
            if str(p[1]) == key:
                return str(p[2])
        return default

    def pins(self, name):
        out = []
        for p in walk(self.syms[name], "pin"):
            at = child(p, "at")
            hidden = "hide" in p or any(isinstance(c, list) and c[:2] == ["hide", "yes"] for c in p)
            out.append(dict(number=str(child(p, "number")[1]), name=str(child(p, "name")[1]),
                            etype=str(p[1]), x=float(at[1]), y=float(at[2]), angle=float(at[3]),
                            length=float(child(p, "length")[1]), hidden=hidden))
        return out

    def body(self, name):
        """Bounding box (lib coordinates, y up) of the drawn body: rectangles, polylines,
        circles and arcs, plus pin endpoints."""
        xs, ys = [], []
        sym = self.syms[name]
        for r in walk(sym, "rectangle"):
            for k in ("start", "end"):
                xs.append(float(child(r, k)[1])); ys.append(float(child(r, k)[2]))
        for pl in walk(sym, "polyline"):
            for xy in walk(pl, "xy"):
                xs.append(float(xy[1])); ys.append(float(xy[2]))
        for c in walk(sym, "circle"):
            cx, cy = float(child(c, "center")[1]), float(child(c, "center")[2])
            r = float(child(c, "radius")[1])
            xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
        for a in walk(sym, "arc"):
            for k in ("start", "mid", "end"):
                xs.append(float(child(a, k)[1])); ys.append(float(child(a, k)[2]))
        for p in self.pins(name):
            xs.append(p["x"]); ys.append(p["y"])
        return min(xs), min(ys), max(xs), max(ys)


LIB = Library()


def tf(x, y, rot):
    """Library point (y up) -> schematic offset (y down) for a symbol rotated `rot` degrees."""
    r = math.radians(rot)
    return (round(x * math.cos(r) - y * math.sin(r), 4), round(-(x * math.sin(r) + y * math.cos(r)), 4))


def outward(pin_angle, rot):
    """Unit vector (schematic coords) pointing away from the body at a pin's connection end."""
    a = math.radians(pin_angle + rot)
    return (round(-math.cos(a)), round(math.sin(a)))


DIR_ANGLE = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}


# ----------------------------------------------------------------------------------------
# Groups (one circuit box each)
# ----------------------------------------------------------------------------------------
class Group:
    """A functional block drawn in local coordinates; the sheet packs it later."""

    def __init__(self, sheet, title):
        self.sheet, self.title = sheet, title
        self.items = []
        self.bb = [math.inf, math.inf, -math.inf, -math.inf]
        self.dx = self.dy = 0.0
        self.box = None

    # -- bookkeeping --------------------------------------------------------------------
    def grow(self, x0, y0, x1=None, y1=None):
        x1 = x0 if x1 is None else x1
        y1 = y0 if y1 is None else y1
        self.bb = [min(self.bb[0], x0, x1), min(self.bb[1], y0, y1),
                   max(self.bb[2], x0, x1), max(self.bb[3], y0, y1)]

    def grow_text(self, s, x, y, size, justify="center", angle=0):
        w, h = text_width(s, size), size * 1.4
        if angle in (90, 270):
            w, h = h, w
            self.grow(x - w / 2, y - h if "left" in justify else y, x + w / 2, y + h if "right" in justify else y)
            return
        if "left" in justify:
            x0, x1 = x, x + w
        elif "right" in justify:
            x0, x1 = x - w, x
        else:
            x0, x1 = x - w / 2, x + w / 2
        if "bottom" in justify:
            y0, y1 = y - h, y
        elif "top" in justify:
            y0, y1 = y, y + h
        else:
            y0, y1 = y - h / 2, y + h / 2
        self.grow(x0, y0, x1, y1)

    # -- primitives ---------------------------------------------------------------------
    def wire(self, a, b):
        assert a[0] == b[0] or a[1] == b[1], ("wire not orthogonal", a, b)
        assert all(on_grid(v) for v in (*a, *b)), ("wire off grid", a, b)
        if a != b:
            self.items.append(dict(kind="wire", a=a, b=b))
            self.grow(*a, *b)

    def path(self, *pts):
        """Orthogonal wire through the given points."""
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    def junction(self, p):
        self.items.append(dict(kind="junction", p=p))

    def nc(self, p):
        self.items.append(dict(kind="nc", p=p))
        self.grow(p[0] - 0.7, p[1] - 0.7, p[0] + 0.7, p[1] + 0.7)

    def text(self, s, x, y, size=TEXT, bold=False):
        self.items.append(dict(kind="text", s=s, x=x, y=y, size=size, bold=bold))
        lines = s.split("\n")
        w = max(text_width(line, size) for line in lines)
        self.grow(x, y, x + w, y + len(lines) * size * 1.6)

    def anchor(self, p, d, net, horiz=False, angle=None):
        """Put the thing that names a net at point p, facing direction d (away from the pin).
        horiz=True writes a label horizontally even on a vertical lead (two-pin parts, where
        the neighbours are a branch pitch away rather than 100 mil)."""
        sheet = self.sheet
        if net in POWER_NETS:
            self.power(p, d, net)
            return
        ang = DIR_ANGLE[d]
        if horiz and d[0] == 0:
            ang = 0
        if angle is not None:
            ang = angle
        kind = "hlabel" if net in sheet.ports else "label"
        self.items.append(dict(kind=kind, net=net, p=p, angle=ang, shape=sheet.ports.get(net)))
        extra = 2.6 if kind == "hlabel" else 0.3
        L = text_width(net) + extra
        if ang == 0:
            self.grow(p[0], p[1] - 1.8, p[0] + L, p[1] + (0.9 if kind == "hlabel" else 0.2))
        elif ang == 180:
            self.grow(p[0] - L, p[1] - 1.8, p[0], p[1] + (0.9 if kind == "hlabel" else 0.2))
        elif ang == 90:
            self.grow(p[0] - 1.8, p[1] - L, p[0] + (0.9 if kind == "hlabel" else 0.2), p[1])
        else:
            self.grow(p[0] - 1.8, p[1], p[0] + (0.9 if kind == "hlabel" else 0.2), p[1] + L)

    def power(self, p, d, net):
        """Power or ground symbol whose body points along d."""
        if net == "GND":
            rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
        else:
            rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
        ref = self.sheet.next_ref("#PWR")
        self.items.append(dict(kind="symbol", lib=net, p=p, rot=rot, ref=ref, value=net,
                               fields={}, footprint="", pins={"1": net}, dnp=False, power=True))
        ln = 3.2 + (0 if net == "GND" else text_width(net, 1.0) * (1 if d[0] else 0))
        self.grow(p[0] - 1.3 if d[0] == 0 else p[0], p[1] - 1.3 if d[1] == 0 else p[1],
                  p[0] + d[0] * ln + (1.3 if d[0] == 0 else 0), p[1] + d[1] * 4.2 + (1.3 if d[1] == 0 else 0))
        if d[1] == -1 and net != "GND":                 # rail name written above the arrow
            self.grow_text(net, p[0], p[1] - 4.4, TEXT)
        if d[1] == 1 and net != "GND":
            self.grow_text(net, p[0], p[1] + 4.4, TEXT)

    def flag(self, p, net):
        """PWR_FLAG on a rail that has no power-output pin: rail symbol at p, flag beside it."""
        self.power(p, (0, 1) if net == "GND" else (0, -1), net)
        f = (p[0] + LEAD, p[1])
        self.wire(p, f)
        ref = self.sheet.next_ref("#FLG")
        rot = 180 if net == "GND" else 0
        self.items.append(dict(kind="symbol", lib="PWR_FLAG", p=f, rot=rot, ref=ref, value="PWR_FLAG",
                               fields={}, footprint="", pins={"1": net}, dnp=False, power=True))
        self.grow(f[0] - 1.3, f[1] - (5 if rot == 0 else 0), f[0] + 1.3, f[1] + (5 if rot else 0))

    def flag_at(self, p, d=(1, 0)):
        """PWR_FLAG whose pin sits on an existing rail anchor point p, body pointing along d."""
        rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
        ref = self.sheet.next_ref("#FLG")
        self.items.append(dict(kind="symbol", lib="PWR_FLAG", p=p, rot=rot, ref=ref, value="PWR_FLAG",
                               fields={}, footprint="", pins={}, dnp=False, power=True))
        self.grow(p[0], p[1], p[0] + d[0] * 5.0 + (1.3 if d[0] == 0 else 0), p[1] + d[1] * 5.0 + (1.3 if d[1] == 0 else 0))
        self.grow(p[0] - (1.3 if d[0] == 0 else 0), p[1] - (1.3 if d[1] == 0 else 0))

    # -- parts --------------------------------------------------------------------------
    def part(self, lib, x, y, nets, rot=0, value=None, prefix=None, fields=None,
             footprint=None, dnp=False, attach=(), lead=None, fieldpos=None, join=(), label_angle=None,
             hlabels=None, rowfields=False):
        """Place a symbol with its origin at (x, y). `nets` maps pin number -> net name
        (None = no-connect). Pins listed in `attach` get no lead/anchor (the caller wires
        them). Returns {pin: (point, outward direction)}."""
        assert on_grid(x) and on_grid(y), (lib, x, y)
        pins = LIB.pins(lib)
        prefix = prefix or LIB.prop(lib, "Reference", "U")
        ref = self.sheet.next_ref(prefix)
        value = value if value is not None else LIB.prop(lib, "Value", lib)
        lead = LEAD if lead is None else lead
        # Stacked pins share one connection point and must share one net.
        at = {}
        for p in pins:
            dx, dy = tf(p["x"], p["y"], rot)
            pt = (round(x + dx, 4), round(y + dy, 4))
            at.setdefault(pt, []).append(p)
        result, pinnets = {}, {}
        horiz = (len(at) == 2) if hlabels is None else hlabels
        # Part-local extent, so IC fields can sit clear of this part's own leads and anchors.
        outer_bb, self.bb = self.bb, [math.inf, math.inf, -math.inf, -math.inf]
        connected = set()
        for pt, plist in at.items():
            if any(nets.get(p["number"]) for p in plist):
                connected.add(pt)
        # join: groups of same-net pins on one side whose leads are tied by a short wire so the
        # net gets a single anchor (on the group's first pin), e.g. a USB-C connector's two D+.
        joined = {n for grp in join for n in grp[1:]}
        end_of = {}
        for pt, plist in at.items():
            given = [p["number"] for p in plist if p["number"] in nets]
            assert given, (self.sheet.fname, ref, lib, "no net for pins", [p["number"] for p in plist])
            net = nets[given[0]]
            for n in given:
                assert nets[n] == net, (ref, "stacked pins on different nets", given)
            d = outward(plist[0]["angle"], rot)
            for p in plist:
                pinnets[p["number"]] = net
                result[p["number"]] = (pt, d)
            if any(p["number"] in attach for p in plist):
                continue
            if net is None:
                if not all(p["hidden"] for p in plist):   # hidden NC pins need no marker
                    self.nc(pt)
            else:
                end = (round(pt[0] + d[0] * lead, 4), round(pt[1] + d[1] * lead, 4))
                self.wire(pt, end)
                for p in plist:
                    end_of[p["number"]] = end
                if not any(p["number"] in joined for p in plist):
                    la = (label_angle or {}).get(plist[0]["number"])
                    dd = d
                    if d[1] == 0 and net in POWER_NETS:
                        # Hang grounds down and point rails up from side leads, unless the
                        # neighbouring pin's lead is in the way (then the symbol stays sideways).
                        below = (pt[0], round(pt[1] + 2.54, 4)) in connected
                        above = any((pt[0], round(pt[1] - k, 4)) in connected for k in (2.54, 5.08))
                        if net == "GND" and not below:
                            dd = (0, 1)
                        elif net != "GND" and not above:
                            dd = (0, -1)
                        else:
                            self.sheet.exceptions.append("%s pin %s: %s symbol sideways (adjacent pin lead)"
                                                         % (ref, plist[0]["number"], net))
                    self.anchor(end, dd, net, horiz, la)
        for grp in join:
            nets_in = {pinnets[n] for n in grp}
            assert len(nets_in) == 1, (ref, "joined pins on different nets", grp)
            pts = sorted({end_of[n] for n in grp})
            assert len({q[0] for q in pts}) == 1 or len({q[1] for q in pts}) == 1, (ref, "join not in line", grp)
            for a, b in zip(pts, pts[1:]):
                self.wire(a, b)
            for q in pts[1:-1]:
                self.junction(q)
            if end_of[grp[0]] in pts[1:-1]:
                pass                                   # anchor on an interior point: junction drawn
        extra = set(nets) - set(pinnets)
        assert not extra, (ref, lib, "nets for unknown pins", extra)
        if lib != "PWR_FLAG":
            for n, net in pinnets.items():
                self.sheet.manifest_pin(ref, n, net)
        # Body extent
        bx0, by0, bx1, by1 = LIB.body(lib)
        corners = [tf(cx, cy, rot) for cx in (bx0, bx1) for cy in (by0, by1)]
        X0 = x + min(c[0] for c in corners); X1 = x + max(c[0] for c in corners)
        Y0 = y + min(c[1] for c in corners); Y1 = y + max(c[1] for c in corners)
        self.grow(X0, Y0, X1, Y1)
        local_bb, self.bb = self.bb, outer_bb
        self.grow(*local_bb)
        # Fields: two-pin parts get them beside the body, ICs above/below everything they own.
        fields = dict(fields or {})
        power = lib == "PWR_FLAG"
        two_pin = len(at) == 2
        if fieldpos:
            fp = fieldpos
        elif power or rowfields:
            fp = []
        elif two_pin and (Y1 - Y0) >= (X1 - X0):            # vertical: text to the right
            tx = X1 + 1.27
            fp = [("Reference", ref, tx, y - 1.0, "left", 1.0), ("Value", value, tx, y + 1.0, "left", 1.0)]
            vis = [k for k in ("voltage", "tolerance") if k in fields]
            for i, k in enumerate(vis):
                fp.append((k, fields[k], tx, y + 3.0 + i * 1.5, "left", 0.8))
        elif two_pin:                                       # horizontal: above and below
            fp = [("Reference", ref, x, Y0 - 1.6, "center", 1.0), ("Value", value, x, Y1 + 1.6, "center", 1.0)]
            vis = [k for k in ("voltage", "tolerance") if k in fields]
            for i, k in enumerate(vis):
                fp.append((k, fields[k], x, Y1 + 3.2 + i * 1.5, "center", 0.8))
        else:
            top, bot = min(Y0, local_bb[1]), max(Y1, local_bb[3])
            fp = [("Reference", ref, X0, top - 1.8, "left"), ("Value", value, X0, bot + 1.0, "left")]
            if "spec" in fields:
                fp.append(("spec", fields["spec"], X0, bot + 2.5, "left", 0.9))
        shown = {}
        for f in fp:
            k, s, fx, fy, just = f[:5]
            size = f[5] if len(f) > 5 else TEXT
            shown[k] = (fx, fy, just, size)
            self.grow_text(s, fx, fy, size, just)
        self.items.append(dict(kind="symbol", lib=lib, p=(x, y), rot=rot, ref=ref, value=value,
                               fields=fields, shown=shown, pins=pinnets,
                               footprint=footprint if footprint is not None else LIB.prop(lib, "Footprint"),
                               dnp=dnp, power=power))
        if power:
            return result
        self.sheet.parts.append(dict(ref=ref, lib=lib, value=value, footprint=footprint if footprint is not None
                                     else LIB.prop(lib, "Footprint"), fields=fields, dnp=dnp))
        return result

    # -- two-pin helpers ------------------------------------------------------------------
    def two(self, lib, x, y, n1, n2, value, orient="v", rot=None, **kw):
        """Two-pin part. orient 'v' = pin 1 on top, 'h' = pin 1 on the left (rot overrides)."""
        if rot is None:
            rot = 0 if orient == "v" else 90
            if lib in ("LED", "SMF5.0A", "TS-1187A-B-A-B", "TS24CA", "AOTA-B201610S3R3-101-T"):
                rot = 0 if orient == "h" else 270      # these are drawn horizontally in the library
        return self.part(lib, x, y, {"1": n1, "2": n2}, rot=rot, value=value, **kw)

    def R(self, x, y, n1, n2, value, orient="v", tol="1%", power="62.5mW", use="", **kw):
        f = dict(tolerance=tol, power=power, use=use)
        f.update(kw.pop("fields", {}))
        return self.two("R", x, y, n1, n2, value, orient, prefix="R", fields=f,
                        footprint=kw.pop("footprint", "Mindspark:R_0402_1005Metric"), **kw)

    def C(self, x, y, n1, n2, value, voltage, orient="v", spec="X5R", use="", size=None, **kw):
        f = dict(voltage=voltage, spec=spec, use=use)
        size = size or cap_size(value, voltage)
        return self.two("C", x, y, n1, n2, value, orient, prefix="C", fields=f,
                        footprint="Mindspark:C_%s" % size, **kw)

    def decaps(self, x, y, rail, caps, pitch=10.16, gnd="GND"):
        """A row of vertical decoupling caps from `rail` to GND, pitch 400 mil (fields fit between)."""
        for i, (value, voltage, use) in enumerate(caps):
            self.C(x + i * pitch, y, rail, gnd, value, voltage, use=use)

    def inline(self, start, d, lib, n_far, value, n_near=None, near_pin="1", far_dir=None, **kw):
        """Place a two-pin part in line with a pin: pin -> 100 mil -> part -> 100 mil -> anchor.
        Works for any two-pin library symbol; `near_pin` is the pin that faces the start point.
        far_dir overrides which way the far anchor faces (e.g. a sideways rail where an
        upward symbol would hit a neighbouring label)."""
        far_pin = "2" if near_pin == "1" else "1"
        lp = {p["number"]: (p["x"], p["y"]) for p in LIB.pins(lib)}
        rot = None
        for r in (0, 90, 180, 270):
            a, b = tf(*lp[near_pin], r), tf(*lp[far_pin], r)
            v = (b[0] - a[0], b[1] - a[1])
            if (v[0] == 0 or v[1] == 0) and v[0] * d[0] + v[1] * d[1] > 0:
                rot = r
                break
        assert rot is not None, (lib, d)
        p1 = (start[0] + d[0] * LEAD, start[1] + d[1] * LEAD)
        off = tf(*lp[near_pin], rot)
        cx, cy = round(p1[0] - off[0], 4), round(p1[1] - off[1], 4)
        self.wire(start, p1)
        f = kw.pop("fields", {})
        if lib == "R":
            f = dict(tolerance=kw.pop("tol", "1%"), power="62.5mW", use=kw.pop("use", ""), **f)
            kw.setdefault("prefix", "R")
            kw.setdefault("footprint", "Mindspark:R_0402_1005Metric")
        elif lib == "C":
            f = dict(voltage=kw.pop("voltage"), spec=kw.pop("spec", "C0G"), use=kw.pop("use", ""), **f)
            kw.setdefault("prefix", "C")
            kw.setdefault("footprint", "Mindspark:C_0402_1005Metric")
        else:
            if "use" in kw:
                f = dict(use=kw.pop("use"), **f)
        nets = {near_pin: n_near, far_pin: n_far}
        if far_dir is None:
            return self.part(lib, cx, cy, nets, rot=rot, value=value, fields=f, attach=(near_pin,), **kw)
        res = self.part(lib, cx, cy, nets, rot=rot, value=value, fields=f, attach=(near_pin, far_pin), **kw)
        (fx, fy), fd = res[far_pin]
        end = (fx + fd[0] * LEAD, fy + fd[1] * LEAD)
        self.wire((fx, fy), end)
        self.anchor(end, far_dir, n_far)
        self.sheet.exceptions.append("%s: %s symbol faces %s to clear a neighbouring label"
                                     % (n_far, "rail" if n_far in POWER_NETS else "label", far_dir))
        return res


def cap_size(value, voltage):
    """Default package by value: 0402 up to 1 uF, 0603 for 2.2-10 uF, 0805 for 22 uF, 1206 above."""
    v = value.replace("uF", "e-6").replace("nF", "e-9").replace("pF", "e-12")
    c = float(v)
    if c <= 1.01e-6:
        return "0402_1005Metric"
    if c <= 10.1e-6:
        return "0603_1608Metric"
    if c <= 22.1e-6:
        return "0805_2012Metric"
    return "1206_3216Metric"


# ----------------------------------------------------------------------------------------
# Sheets
# ----------------------------------------------------------------------------------------
class Sheet:
    def __init__(self, index, fname, title, ports, description=""):
        self.index, self.fname, self.title = index, fname, title
        self.description = description
        self.ports = dict(ports)               # name -> shape (input/output/bidirectional/passive)
        self.port_order = list(ports)
        self.groups, self.parts, self.manifest = [], [], {}
        self.counters, self.netuse = {}, {}
        self.notes = []
        self.exceptions = []          # recorded tidy-rule exceptions (sideways rails, long leads, labels)
        self.file_uuid = uid("file/" + fname)
        self.block_uuid = uid("block/" + fname)
        self.paper = "A4"

    def group(self, title):
        g = Group(self, title)
        self.groups.append(g)
        return g

    def note(self, s):
        self.notes.append(s)

    def next_ref(self, prefix):
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        n = self.counters[prefix]
        if prefix.startswith("#"):
            return "%s%d%03d" % (prefix, self.index, n)
        assert n < 100, (self.fname, prefix, "more than 99 parts of one kind on a sheet")
        return "%s%d" % (prefix, self.index * 100 + n)

    def netkey(self, net):
        if net is None:
            return None
        if net in POWER_NETS or net in self.ports:
            return net
        return "%s:%s" % (self.fname, net)

    def manifest_pin(self, ref, pin, net):
        self.manifest.setdefault(ref, {})[pin] = self.netkey(net)

    # -- layout ---------------------------------------------------------------------------
    def pack(self):
        """Bottom-left packing: each group (in order) goes to the highest, then leftmost, free
        spot. Candidates are the sheet start and the spots 200 mil right of / below placed boxes,
        so boxes in a row share their tops where they fit. Box edges are computed exactly:
        content snapped to the 50 mil grid with >= 300 mil padding (the heading sits inside the
        top padding). A4 first, then A3."""
        for g in self.groups:
            keep = list(g.bb)
            for r in getattr(g, "rows", []):
                r.finish()                             # places the row fields
            if getattr(g, "measured", False):
                g.bb = keep                            # the measured extent already includes them
            else:
                hw = text_width(g.title, 1.524) * 1.08 + 2.54 - ((g.bb[2] - g.bb[0]) + 2 * PAD)
                if hw > 0:
                    g.grow(g.bb[2] + hw, g.bb[1])

        def rect(g, cx, cy):
            dx = math.ceil((cx + PAD - g.bb[0]) / G - 1e-9) * G
            dy = math.ceil((cy + PAD - g.bb[1]) / G - 1e-9) * G
            return dx, dy, (cx, cy, round(g.bb[2] + dx + PAD, 4), round(g.bb[3] + dy + PAD, 4))

        for paper in ("A4", "A3"):
            P = PAPER[paper]
            X0, Y0 = P["x0"] + 2.54, P["y0"] + 2.54
            X1, Y1 = P["x1"] - 2.54, P["y1"] - 2.54 - 8.0              # leave room for notes
            tb = (P["tbx"] - 2.54, P["tby"] - 2.54)
            placed, ok = [], True
            for g in self.groups:
                cands = [(X0, Y0)] + [(r[2] + GAP, r[1]) for r in placed] + [(r[0], r[3] + GAP) for r in placed] \
                    + [(X0, r[3] + GAP) for r in placed]
                best = None
                for cx, cy in sorted(set((round(a, 4), round(b, 4)) for a, b in cands), key=lambda c: (c[1], c[0])):
                    dx, dy, r = rect(g, cx, cy)
                    if r[2] > X1 or r[3] > Y1:
                        continue
                    if r[2] > tb[0] and r[3] > tb[1]:
                        continue
                    if any(not (r[2] + GAP - 0.001 <= o[0] or o[2] + GAP - 0.001 <= r[0] or
                                r[3] + GAP - 0.001 <= o[1] or o[3] + GAP - 0.001 <= r[1]) for o in placed):
                        continue
                    best = (dx, dy, r)
                    break
                if best is None:
                    ok = False
                    break
                g.dx, g.dy, g.box = best
                placed.append(g.box)
            if ok:
                self.paper = paper
                return paper
        raise SystemExit("%s: groups do not fit on A3 either" % self.fname)
