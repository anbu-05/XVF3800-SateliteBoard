"""Write packed Sheet objects (schgen.py) out as KiCad 10 .kicad_sch files, plus the root
overview sheet with one sheet block per child."""
import json
import math

from schgen import (DATE, G, LEAD, LIB, PAPER, PROJECT, PROJECT_DIR, ROOT_UUID, TEXT, Group,
                    num, on_grid, text_width, uid)
from sexpr import dump, q


class Writer:
    """Collects nodes for one file and hands out deterministic UUIDs."""

    def __init__(self, fname, path_prefix):
        self.fname, self.path = fname, path_prefix
        self.count = 0
        self.nodes, self.libs = [], set()

    def id(self, kind):
        self.count += 1
        return q(uid("%s/%s/%d" % (self.fname, kind, self.count)))


def eff(size=TEXT, justify=None, bold=False):
    font = ["font", ["size", num(size), num(size)]] + ([["bold", "yes"]] if bold else [])
    e = ["effects", font]
    if justify:
        e.append(["justify", *justify.split()])
    return e


def prop(name, value, x, y, angle=0, size=TEXT, justify=None, hide=False):
    node = ["property", q(name), q(value), ["at", num(x), num(y), num(angle)]]
    if hide:
        node.append(["hide", "yes"])
    node += [["show_name", "no"], ["do_not_autoplace", "yes"], eff(size, justify)]
    return node


def flip(justify):
    swap = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
    return " ".join(swap.get(w, w) for w in justify.split())


def emit_symbol(w, it, dx, dy):
    lib, (x, y), rot = it["lib"], it["p"], it["rot"]
    X, Y = x + dx, y + dy
    w.libs.add(lib)
    stored = 90 if rot in (90, 270) else 0
    node = ["symbol", ["lib_id", q("Mindspark:" + lib)], ["at", num(X), num(Y), num(rot)],
            ["unit", "1"], ["body_style", "1"], ["exclude_from_sim", "no"],
            ["in_bom", "no" if (it["power"] or lib in ("TestPoint", "MountingHole")) else "yes"],
            ["on_board", "no" if it["power"] else "yes"],
            ["in_pos_files", "no" if it["power"] else "yes"], ["dnp", "yes" if it["dnp"] else "no"],
            ["uuid", w.id("symbol")]]
    if it["power"]:
        # Reference hidden on the pin; Value where the library puts it, kept horizontal.
        from schgen import tf
        vx, vy = 0.0, 3.556
        for p in LIB.syms[lib][2:]:
            if isinstance(p, list) and p[0] == "property" and str(p[1]) == "Value":
                vx, vy = float(p[3][1]), float(p[3][2])
        ox, oy = tf(vx, vy, rot)
        node.append(prop("Reference", it["ref"], X, Y, stored, hide=True))
        hide_val = lib == "PWR_FLAG"
        just = None
        if rot in (90, 270) and lib != "GND":
            # Horizontal rail symbol: write the rail name past the arrow tip, not across it.
            side = 1 if ox > 0 else -1
            ox, oy = side * 3.3, 0.0
            just = "left" if side > 0 else "right"
            if (stored + rot) % 360 == 180:
                just = flip(just)
        node.append(prop("Value", it["value"], X + ox, Y + oy, stored, size=1.0, justify=just, hide=hide_val))
        node.append(prop("Footprint", "", X, Y, stored, hide=True))
        node.append(prop("Datasheet", "", X, Y, stored, hide=True))
        node.append(prop("Description", "", X, Y, stored, hide=True))
    else:
        shown = it["shown"]
        lcsc = LIB.prop(lib, "LCSC Part")
        fields = [("Reference", it["ref"]), ("Value", it["value"]), ("Footprint", it["footprint"]),
                  ("Datasheet", LIB.prop(lib, "Datasheet")), ("Description", LIB.prop(lib, "Description")),
                  ("LCSC", it["fields"].get("LCSC", lcsc)),
                  ("MPN", it["fields"].get("MPN", LIB.prop(lib, "MPN") if lcsc else "")),
                  ("Manufacturer", it["fields"].get("Manufacturer", LIB.prop(lib, "Manufacturer")))]
        for k in ("spec", "voltage", "tolerance", "power", "use"):
            if k in it["fields"]:
                fields.append((k, it["fields"][k]))
        for k, v in fields:
            if k in shown:
                fx, fy, just, size = shown[k]
                if just == "center":
                    jtxt = None
                else:
                    jtxt = just if (stored + rot) % 360 != 180 else flip(just)
                node.append(prop(k, v, fx + dx, fy + dy, stored, size=size, justify=jtxt))
            else:
                node.append(prop(k, v, X, Y, stored, hide=True))
    for n in sorted({p["number"] for p in LIB.pins(lib)}, key=lambda s: (len(s), s)):
        node.append(["pin", q(n), ["uuid", w.id("pin")]])
    node.append(["instances", ["project", q(PROJECT), ["path", q(w.path), ["reference", q(it["ref"])],
                                                      ["unit", "1"]]]])
    w.nodes.append(node)


def emit_item(w, it, dx, dy):
    k = it["kind"]
    if k == "symbol":
        return emit_symbol(w, it, dx, dy)
    if k == "wire":
        (ax, ay), (bx, by) = it["a"], it["b"]
        w.nodes.append(["wire", ["pts", ["xy", num(ax + dx), num(ay + dy)], ["xy", num(bx + dx), num(by + dy)]],
                        ["stroke", ["width", "0"], ["type", "default"]], ["uuid", w.id("wire")]])
    elif k == "junction":
        x, y = it["p"]
        w.nodes.append(["junction", ["at", num(x + dx), num(y + dy)], ["diameter", "0"],
                        ["color", "0", "0", "0", "0"], ["uuid", w.id("junction")]])
    elif k == "nc":
        x, y = it["p"]
        w.nodes.append(["no_connect", ["at", num(x + dx), num(y + dy)], ["uuid", w.id("nc")]])
    elif k == "label":
        x, y = it["p"]
        just = "left bottom" if it["angle"] in (0, 90) else "right bottom"
        w.nodes.append(["label", q(it["net"]), ["at", num(x + dx), num(y + dy), num(it["angle"])],
                        eff(TEXT, just), ["uuid", w.id("label")]])
    elif k == "hlabel":
        x, y = it["p"]
        just = "left" if it["angle"] in (0, 90) else "right"
        w.nodes.append(["hierarchical_label", q(it["net"]), ["shape", it["shape"]],
                        ["at", num(x + dx), num(y + dy), num(it["angle"])], eff(TEXT, just), ["uuid", w.id("hlabel")]])
    elif k == "text":
        w.nodes.append(["text", q(it["s"]), ["exclude_from_sim", "no"], ["at", num(it["x"] + dx), num(it["y"] + dy), "0"],
                        eff(it["size"], "left top", it["bold"]), ["uuid", w.id("text")]])


def box_nodes(w, title, box):
    x0, y0, x1, y1 = box
    w.nodes.append(["rectangle", ["start", num(x0), num(y0)], ["end", num(x1), num(y1)],
                    ["stroke", ["width", "0.1524"], ["type", "default"]], ["fill", ["type", "none"]],
                    ["uuid", w.id("box")]])
    w.nodes.append(["text", q(title), ["exclude_from_sim", "no"], ["at", num(x0 + 1.27), num(y0 + 1.27), "0"],
                    eff(1.524, "left top"), ["uuid", w.id("heading")]])


def header(file_uuid, paper, title, comment):
    return ["kicad_sch", ["version", "20260306"], ["generator", q("eeschema")], ["generator_version", q("10.0")],
            ["uuid", q(file_uuid)], ["paper", q(paper)],
            ["title_block", ["title", q(title)], ["date", q(DATE)], ["rev", q("1")], ["company", q("Mindspark")],
             ["comment", "1", q(comment)]]]


def write_child(sheet):
    sheet.pack()
    w = Writer(sheet.fname, "/%s/%s" % (ROOT_UUID, sheet.block_uuid))
    for g in sheet.groups:
        box_nodes(w, g.title, g.box)
        for it in g.items:
            emit_item(w, it, g.dx, g.dy)
    # Notes go below the boxes (outside them), left-aligned with the first box.
    if sheet.notes:
        import textwrap
        P = PAPER[sheet.paper]
        y = max(g.box[3] for g in sheet.groups) + 2.54
        lines = [l for n in sheet.notes for l in textwrap.wrap(n, 150)]
        w.nodes.append(["text", q("\n".join(lines)), ["exclude_from_sim", "no"],
                        ["at", num(P["x0"] + 2.54), num(y), "0"], eff(1.0, "left top"), ["uuid", w.id("note")]])
    tree = header(sheet.file_uuid, sheet.paper, "Mindspark rev 1: " + sheet.title, sheet.description)
    tree.append(["lib_symbols", *[LIB.node(n) for n in sorted(w.libs)]])
    tree += w.nodes
    tree.append(["embedded_fonts", "no"])
    (PROJECT_DIR / (sheet.fname + ".kicad_sch")).write_text(dump(tree) + "\n")
    return w


# ----------------------------------------------------------------------------------------
# Root overview
# ----------------------------------------------------------------------------------------
STUB = 2.54           # 100 mil labelled stub on every sheet pin
NAME_GAP = 2.54       # 100 mil clear between the left and right pin names inside a block
MIN_W = 15.24         # 600 mil: narrowest block, so a pin-less block still reads as a block


# Short box headings on the overview (the block's own name field already gives the file).
SHORT = {"usb_power": "USB-C power", "regulators": "Regulators", "xvf3800": "XVF3800",
         "xvf3800_periph": "XVF3800 peripherals", "audio": "Audio", "esp32": "ESP32-S3",
         "esp32_io": "ESP32 I/O", "led_ring": "LED ring"}


def block_size(left, right):
    """Fit a sheet block to its pins, the way Step 0 fits a symbol body: width = widest left
    pin name + gap + widest right pin name (100 mil steps), height = pin rows at 100 mil with
    one 100 mil row of margin above and below."""
    names = max([text_width(p) for p in left] + [0]) + NAME_GAP + max([text_width(p) for p in right] + [0])
    w = max(MIN_W, math.ceil(names / 2.54 - 1e-9) * 2.54)
    h = (max(len(left), len(right), 1) + 1) * 2.54
    return w, h


def write_root(sheets, mech, measured=None):
    """One titled circuit box per sheet block, plus the Mechanical box, packed by the same
    bottom-left packer as the child sheets. mech(group) draws the mounting holes. measured
    maps group index -> content extent read from the previous plot (exact padding)."""
    from schgen import Sheet

    class RootSheet:                       # minimal stand-in so Group and Sheet.pack work on root
        fname, index, ports, netuse, exceptions = "root", 0, {}, {}, []
        counters, manifest, parts = {}, {}, []
        paper = "A4"
        pack = Sheet.pack

        def next_ref(self, prefix):
            self.counters[prefix] = self.counters.get(prefix, 0) + 1
            n = self.counters[prefix]
            return "%s%d" % (prefix, n) if not prefix.startswith("#") else "%s0%03d" % (prefix, n)

        def netkey(self, net):
            from schgen import POWER_NETS
            return net if (net in POWER_NETS or net in ALL_PORTS) else "root:" + net

        def manifest_pin(self, ref, pin, net):
            self.manifest.setdefault(ref, {})[pin] = self.netkey(net)

    ALL_PORTS = {p for s in sheets for p in s.ports}
    root = RootSheet()
    root.groups = []
    w = Writer("root", "/%s" % ROOT_UUID)

    # Each block is drawn at the local origin of its own group; packing moves the group.
    blocks = []
    for s in sheets:
        left = [p for p in s.port_order if s.ports[p] == "input"]
        right = [p for p in s.port_order if s.ports[p] != "input"]
        bw, bh = block_size(left, right)
        g = Group(root, SHORT[s.fname])
        g.grow(0, 0, bw, bh)
        g.grow_text(s.fname, 0, -0.7, TEXT, "left bottom")                  # Sheetname above
        g.grow_text(s.fname + ".kicad_sch", 0, bh + 0.7, 1.0, "left top")    # Sheetfile below
        for side, names in (("L", left), ("R", right)):
            for i, name in enumerate(names):
                py = 2.54 * (i + 1)
                px = 0 if side == "L" else bw
                d = (-1, 0) if side == "L" else (1, 0)
                end = (px + d[0] * STUB, py)
                g.wire((px, py), end)
                g.anchor(end, d, name)
        root.groups.append(g)
        blocks.append((s, g, left, right, bw, bh))
    m = Group(root, "Mechanical")
    mech(m)
    root.groups.append(m)
    for gi, g in enumerate(root.groups):
        if measured and gi in measured:
            g.bb, g.measured = list(measured[gi]), True
    paper = root.pack()
    write_root.groups = root.groups

    for s, g, left, right, bw, bh in blocks:
        x, y = g.dx, g.dy
        assert on_grid(x) and on_grid(y), (s.fname, x, y)
        node = ["sheet", ["at", num(x), num(y)], ["size", num(bw), num(bh)], ["exclude_from_sim", "no"],
                ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "no"],
                ["stroke", ["width", "0.1524"], ["type", "solid"]], ["fill", ["color", "0", "0", "0", "0.0000"]],
                ["uuid", q(s.block_uuid)],
                prop("Sheetname", s.fname, x, y - 0.7, 0, justify="left bottom"),
                prop("Sheetfile", s.fname + ".kicad_sch", x, y + bh + 0.7, 0, size=1.0, justify="left top")]
        for side, names in (("L", left), ("R", right)):
            for i, name in enumerate(names):
                py = y + 2.54 * (i + 1)
                px = x if side == "L" else x + bw
                node.append(["pin", q(name), s.ports[name], ["at", num(px), num(py), "180" if side == "L" else "0"],
                             ["uuid", q(uid("pin/%s/%s" % (s.fname, name)))],
                             eff(TEXT, "left" if side == "L" else "right")])
        node.append(["instances", ["project", q(PROJECT), ["path", q("/" + ROOT_UUID), ["page", q(str(s.index + 1))]]]])
        w.nodes.append(node)
    for g in root.groups:
        box_nodes(w, g.title, g.box)
        for it in g.items:
            emit_item(w, it, g.dx, g.dy)
    tree = header(ROOT_UUID, paper, "Mindspark rev 1: overview",
                  "XVF3800 USB voice front end + ESP32-S3 helper. Rails are global power symbols.")
    tree.append(["lib_symbols", *[LIB.node(n) for n in sorted(w.libs)]])
    tree += w.nodes
    tree.append(["sheet_instances", ["path", q("/"), ["page", q("1")]]])
    tree.append(["embedded_fonts", "no"])
    (PROJECT_DIR / (PROJECT + ".kicad_sch")).write_text(dump(tree) + "\n")
    # Keep the project file's sheet list in step (KiCad would otherwise rebuild it on open).
    pro = PROJECT_DIR / (PROJECT + ".kicad_pro")
    d = json.loads(pro.read_text())
    d["sheets"] = [[ROOT_UUID, "Root"]] + [[s.block_uuid, s.fname] for s in sheets]
    pro.write_text(json.dumps(d, indent=2) + "\n")
    return root
