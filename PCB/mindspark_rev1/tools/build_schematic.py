#!/usr/bin/env python3
"""Mindspark rev 1 schematic: the circuit, sheet by sheet.

Run from anywhere:   python3 -I PCB/mindspark_rev1/tools/build_schematic.py
It (re)writes the root and the eight child .kicad_sch files plus design-manifest.json, and
refuses to overwrite files that were edited by hand since the last run (hash guard).

Values come from the datasheets; the reasoning for each is in the comments and in
design_notes (written onto each sheet below its boxes).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from emit import write_child, write_root          # noqa: E402
from schgen import LEAD, LIB, POWER_NETS, PROJECT, PROJECT_DIR, Sheet, cap_size, text_width  # noqa: E402

HASHES = PROJECT_DIR / "verification" / "generated-hashes.json"


# ----------------------------------------------------------------------------------------
# Small layout helper: lay two-pin parts left to right with enough room for their text.
# ----------------------------------------------------------------------------------------
def pitch_for(*texts):
    """Row pitch: 300 mil (tidy rule 3), widened in 50 mil steps only when a field is wider."""
    w = max(text_width(t, 1.0) for t in texts) + 1.6
    return max(7.62, -(-w // 1.27) * 1.27)


def anchor_len(g, net):
    """How far an anchor reaches past a 100 mil lead (power symbol with its text, or a label)."""
    from schgen import POWER_NETS
    if net in POWER_NETS:
        return 4.8
    return text_width(net) + (2.6 if net in g.sheet.ports else 0.4)


class Row:
    """Vertical two-pin parts at 300 mil pitch. Leads carry power symbols or labels written along
    the lead; references sit above the row and values (with rating) below it, outside the gaps."""

    def __init__(self, g, x, y):
        self.g, self.x, self.y = g, x, y
        self.cols = []
        self.runs = {}            # lead direction -> the rail run the previous column ended
        g.rows = getattr(g, "rows", []) + [self]

    def _add(self, res, x, texts):
        item = [it for it in self.g.items if it["kind"] == "symbol" and not it["power"]][-1]
        top = min(pt[1] - 2.54 - anchor_len(self.g, item["pins"][n]) for n, (pt, d) in res.items() if d[1] == -1)
        bot = max(pt[1] + 2.54 + anchor_len(self.g, item["pins"][n]) for n, (pt, d) in res.items() if d[1] == 1)
        self.cols.append((item, x, top, bot))
        self.x = round(self.x + pitch_for(*texts), 4)

    def R(self, n1, n2, value, **kw):
        ref = "R%d" % (self.g.sheet.index * 100 + self.g.sheet.counters.get("R", 0) + 1)
        res = self.g.R(self.x, self.y, n1, n2, value, hlabels=False, rowfields=True, **kw)
        self._add(res, self.x, (ref, value))
        return res

    def C(self, n1, n2, value, voltage, **kw):
        """Capacitor column. Rail pins (power nets) are bussed: adjacent caps in the row on the
        same rail share one horizontal wire and one power symbol (drawn on the run's first cap),
        so a decoupling bank shows each rail and GND once."""
        ref = "C%d" % (self.g.sheet.index * 100 + self.g.sheet.counters.get("C", 0) + 1)
        rails = tuple(p for p, n in (("1", n1), ("2", n2)) if n in POWER_NETS)
        res = self.g.C(self.x, self.y, n1, n2, value, voltage, hlabels=False, rowfields=True,
                       attach=rails, **kw)
        col = len(self.cols)
        for p in rails:
            net = n1 if p == "1" else n2
            pt, d = res[p]
            end = (pt[0], round(pt[1] + d[1] * LEAD, 4))
            self.g.wire(pt, end)
            run = self.runs.get(d)
            if run and run["net"] == net and run["col"] == col - 1:
                self.g.wire(run["end"], end)           # extend the rail along the row
                self.g.junction(run["end"])            # the previous point now has 3 connections
            else:
                self.g.anchor(end, d, net)             # first cap of a run carries the symbol
            self.runs[d] = dict(net=net, col=col, end=end)
        self._add(res, self.x, (ref, value, "25V X5R"))
        return res

    def part(self, lib, n1, n2, value, **kw):
        x = self.x
        res = self.g.two(lib, x, self.y, n1, n2, value, "v", hlabels=False, rowfields=True, **kw)
        self._add(res, x, ("SW000", value))
        return x, res

    def skip(self, w=7.62):
        self.x += w

    def finish(self):
        """Align references above and values below the whole row (called by the sheet packer)."""
        if not self.cols:
            return
        top = min(c[2] for c in self.cols)
        bot = max(c[3] for c in self.cols)
        for item, x, _, _ in self.cols:
            f = item["fields"]
            shown = {"Reference": (x, top - 1.0, "center", 1.0), "Value": (x, bot + 1.0, "center", 1.0)}
            extra = [k for k in ("voltage",) if k in f] or [k for k in ("tolerance",) if k in f]
            for i, k in enumerate(extra):
                shown[k] = (x, bot + 2.4 + i * 1.3, "center", 0.8)
            item["shown"] = shown
            self.g.grow_text(item["ref"], x, top - 1.0, 1.0)
            self.g.grow_text(item["value"], x, bot + 1.0, 1.0)
            for k in extra:
                self.g.grow_text(f[k], x, shown[k][1], 0.8)


def tee(g, pin, net, branch, label_net=None, step=2.54):
    """Pin -> 100 mil lead -> junction N -> branch part (vertical, perpendicular to the lead);
    the lead continues another 100 mil past N to the net's label. `branch` = (callable placing the
    part with its near pin at a given point, direction). Returns N."""
    (px, py), d = pin
    n = (px + d[0] * 2.54, py + d[1] * 2.54)
    g.wire((px, py), n)
    far = (n[0] + d[0] * step, n[1] + d[1] * step)
    g.wire(n, far)
    g.anchor(far, d, label_net or net)
    place, bd = branch
    near = (n[0] + bd[0] * 2.54, n[1] + bd[1] * 2.54)
    g.wire(n, near)
    place(near)
    g.junction(n)
    return n


def vbranch(g, lib, near, bd, n_near, n_far, value, **kw):
    """Vertical two-pin part whose near pin sits at `near`, extending in direction bd (down/up)."""
    span = 7.62
    cx, cy = near[0], near[1] + bd[1] * span / 2
    rot = 0 if bd[1] == 1 else 180
    nets = {"1": n_near, "2": n_far}
    if lib == "R":
        f = dict(tolerance="1%", power="62.5mW", use=kw.pop("use", ""))
        return g.part("R", cx, cy, nets, rot=rot, value=value, prefix="R", fields=f, attach=("1",),
                      footprint="Mindspark:R_0402_1005Metric", hlabels=False, **kw)
    f = dict(voltage=kw.pop("voltage"), spec=kw.pop("spec", "X7R"), use=kw.pop("use", ""))
    # Package follows the value (cap_size), so a 10 uF gets the 0603 its LCSC part is.
    return g.part("C", cx, cy, nets, rot=rot, value=value, prefix="C", fields=f, attach=("1",),
                  footprint="Mindspark:C_%s" % cap_size(value, f["voltage"]), hlabels=False, **kw)


def pads_on_lines(g, conn, nets, x_tp, values, footprint, uses):
    """Connector pins on the left of `conn` -> 100 mil lead -> net name -> wire on to a test pad
    at x_tp (pad body pointing left). The net's label (or rail symbol) sits at the lead end, on
    the wire, so each pad is visibly wired to its connector pin. Returns nothing."""
    for (pin, net), value, use in zip(nets, values, uses):
        (px, py), d = conn[pin]
        e = (px + d[0] * 2.54, py)
        g.wire((px, py), e)
        g.wire(e, (x_tp, py))
        if net in POWER_NETS:
            g.anchor(e, (0, -1) if net != "GND" else (0, 1), net)
            g.junction(e)                              # lead, rail symbol and the line to the pad
        else:
            g.anchor(e, (-1, 0), net)                  # label on the line
        ref = nref(g, "TP")
        g.part("TestPoint", x_tp, py, {"1": net}, rot=90, prefix="TP", value=value, attach=("1",),
               footprint=footprint, fields=dict(use=use),
               fieldpos=[("Reference", ref, x_tp - 4.6, py, "right", 1.0),
                         ("Value", value, x_tp - 10.4, py, "right", 1.0)])


def series_r(g, start, d, n_near, n_far, value, use, fieldpos):
    """Horizontal resistor in line with a pin: start -> 100 mil -> R -> 100 mil -> end. Nothing is
    drawn at the far end (the caller wires it on). Returns the far end point."""
    from schgen import tf
    lp = {p["number"]: (p["x"], p["y"]) for p in LIB.pins("R")}
    rot = next(r for r in (90, 270) if tf(*lp["1"], r)[0] * d[0] < 0)   # pin 1 faces the start
    p1 = (start[0] + d[0] * 2.54, start[1])
    cx = round(p1[0] - tf(*lp["1"], rot)[0], 4)
    g.wire(start, p1)
    res = g.part("R", cx, start[1], {"1": n_near, "2": n_far}, rot=rot, value=value, prefix="R",
                 attach=("1", "2"), hlabels=False, footprint="Mindspark:R_0402_1005Metric",
                 fields=dict(tolerance="1%", power="62.5mW", use=use), fieldpos=fieldpos)
    (fx, fy), _ = res["2"]
    end = (round(fx + d[0] * 2.54, 4), fy)
    g.wire((fx, fy), end)
    return end


def nref(g, prefix):
    """The reference the next part with this prefix will get (for custom field placement)."""
    return "%s%d" % (prefix, g.sheet.index * 100 + g.sheet.counters.get(prefix, 0) + 1)


def crystal(g, lib, value, xin, xout, xtal_d, cap, rf, rd, fields):
    """Pierce crystal wired as one cell. Y.1 = XIN node A, Y.3 = drive node D; the load caps hang
    from A and D; Rd runs from D to the XOUT node; optional Rf runs above from A to XOUT.
    Labels only for XIN and XOUT, which reach the IC in its own box."""
    y = g.part(lib, 0, 0, {"1": xin, "3": xtal_d, "2": "GND", "4": "GND"}, prefix="Y", value=value,
               attach=("1", "3"), fields=fields,
               fieldpos=[("Reference", nref(g, "Y"), 0, -6.0, "center", 1.0), ("Value", value, 0, -4.5, "center", 1.0)])
    A, D = (-6.35, 0), (6.35, 0)
    g.wire(y["1"][0], A)
    g.wire(y["3"][0], D)
    for node, net, side in ((A, xin, "right"), (D, xtal_d, "left")):
        x = node[0]
        fx = x + (2.8 if side == "left" else -2.8)
        # caps hang below the nodes; their text goes on the outer side, clear of the crystal's GND
        just = "left" if x > 0 else "right"
        fx = x + 2.8 if x > 0 else x - 2.8
        g.wire(node, (x, 2.54))
        vbranch(g, "C", (x, 2.54), (0, 1), net, "GND", cap, voltage="50V", spec="C0G", use="Crystal load",
                fieldpos=[("Reference", nref(g, "C"), fx, 5.6, just, 1.0), ("Value", cap, fx, 7.1, just, 1.0)])
    g.junction(D)                                      # Y.3 lead, load cap and Rd meet here
    g.inline(D, (1, 0), "R", xout, rd, n_near=xtal_d, use="Rd: drive limit" if rf else "XOUT series",
             fieldpos=[("Reference", nref(g, "R"), 12.7, -2.2, "center", 1.0), ("Value", rd, 12.7, 2.2, "center", 1.0)])
    if rf:
        g.junction(A)                                  # Y.1 lead, load cap and the Rf route meet here
        g.path(A, (-6.35, -8.89))
        ref = nref(g, "R")
        r = g.part("R", 0, -8.89, {"1": xin, "2": xout}, rot=90, value=rf, prefix="R", attach=("1", "2"),
                   fields=dict(tolerance="1%", power="62.5mW", use="Rf: oscillator bias"),
                   footprint="Mindspark:R_0402_1005Metric",
                   fieldpos=[("Reference", ref, 0, -11.9, "center", 1.0), ("Value", rf, 0, -10.4, "center", 1.0)])
        g.wire((-6.35, -8.89), r["1"][0])
        g.path(r["2"][0], (19.05, -8.89), (19.05, 0))
        g.anchor((-6.35, -8.89), (-1, 0), xin)
        g.sheet.exceptions.append("%s pin 2: 600 mil lead to the XOUT node (spans Rd)" % ref)
    else:
        g.anchor(A, (-1, 0), xin)


# ========================================================================================
# Sheet 1: USB-C inputs and power mux
# ========================================================================================
def sheet_usb_power():
    s = Sheet(1, "usb_power", "USB-C inputs and power mux", {
        "USB_MAIN_DP": "bidirectional", "USB_MAIN_DM": "bidirectional",
        "USB_ESP_DP": "bidirectional", "USB_ESP_DM": "bidirectional",
        "MUX_ST": "output"},
        "Either USB-C powers the board; TPS2121 gives the main (XVF3800) port priority")

    for name, j, vbus, dp, dm, cc in (("USB-C main (J101, XVF3800)", "J101", "VBUS_MAIN", "USB_MAIN_DP",
                                       "USB_MAIN_DM", "USBM_CC"),
                                      ("USB-C ESP32 (J102)", "J102", "VBUS_ESP", "USB_ESP_DP",
                                       "USB_ESP_DM", "USBE_CC")):
        g = s.group(name)
        # Receptacle: VBUS, CC, D+/D- on the right (the two D+ and two D- pins tied); GND, shield below.
        g.part("TYPE-C-31-M-12", 0, 0, {
            "A4": vbus, "A9": vbus, "B4": vbus, "B9": vbus, "A5": cc + "1", "B5": cc + "2",
            "A6": dp, "B6": dp, "A7": dm, "B7": dm, "A8": None, "B8": None,
            "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND"},
            prefix="J", join=(("B7", "A7"), ("B6", "A6")),     # ports on B7/B6; A7/A6 wired to the ESD
            fieldpos=[("Reference", j, -10.16, -19.4, "left"), ("Value", "TYPE-C-31-M-12", 2.54, 31.0, "left"),
                      ("spec", "USB 2.0, 16-pin", 2.54, 32.6, "left", 0.9)],
            fields=dict(spec="USB 2.0, 16-pin", use="USB-C receptacle"))
        # ESD array: ch1 = D+/D-, ch2 = CC1/CC2; pins 6, 7, 9, 10 are NC (flow-through routing).
        # ESD channel 1 takes the data pair: pin 1 = D- and pin 2 = D+ line up with the connector's
        # D- / D+ rows, so both are wired straight across (any IO pin protects any line).
        esd = g.part("TPD4E05U06DQAR", 63.5, 0, {
            "1": dm, "2": dp, "4": cc + "1", "5": cc + "2", "3": "GND", "8": "GND",
            "6": None, "7": None, "9": None, "10": None},
            prefix="U", attach=("1", "2", "4", "5"), fields=dict(spec="USB ESD, 0.5 pF", use="ESD on D+/D-/CC1/CC2"))
        for pin, y in (("1", -2.54), ("2", 2.54)):
            g.wire((17.78, y), esd[pin][0])
            g.junction((17.78, y))                     # connector lead, join wire, line to the ESD
        # Rd on CC1/CC2 wired at the ESD array's CC pins (200 mil apart). Staggered: CC2's Rd hangs
        # from the near node, CC1's from a node past CC2's label, so neither crosses the other wire.
        (p5x, p5y), _ = esd["5"]
        (p4x, p4y), _ = esd["4"]
        n2 = (p5x + 2.54, p5y)
        g.wire((p5x, p5y), n2)
        g.wire(n2, (n2[0] + 2.54, p5y))
        g.anchor((n2[0] + 2.54, p5y), (1, 0), cc + "2")
        n1x = round(n2[0] + 2.54 + -(-(text_width(cc + "2") + 1.27) // 2.54) * 2.54, 4)
        n1 = (n1x, p4y)
        g.wire((p4x, p4y), n1)
        g.wire(n1, (n1x + 2.54, p4y))
        g.anchor((n1x + 2.54, p4y), (1, 0), cc + "1")
        for node, net, use in ((n1, cc + "1", "Rd: UFP pull-down on CC1 (5 V only, no PD)"), (n2, cc + "2", "Rd on CC2")):
            g.wire(node, (node[0], node[1] + 2.54))
            vbranch(g, "R", (node[0], node[1] + 2.54), (0, 1), net, "GND", "5.1k", use=use,
                    fieldpos=[("Reference", nref(g, "R"), node[0] + 1.8, node[1] + 5.6, "left", 1.0),
                              ("Value", "5.1k", node[0] + 1.8, node[1] + 7.1, "left", 1.0)])
            g.junction(node)
        g.sheet.exceptions.append("%s CC1: lead runs past the CC2 label to its Rd node (staggered Rd pair)" % j)
        g.sheet.exceptions.append("%s CC1/CC2: connector to ESD by label (two adjacent lines each with an Rd to GND "
                                  "cannot be wired across without a crossing)" % j)
        ry = 20.32                                       # under the connector's right side
        r = Row(g, 27.94, ry)
        x, _ = r.part("SMF5.0A", vbus, "GND", "SMF5.0A", prefix="D",
                      fields=dict(spec="TVS 5 V", use="VBUS clamp"))
        g.flag_at((x, ry - 6.35))                         # VBUS has no power-output pin
        if j == "J101":
            g.flag_at((x, ry + 6.35))                     # the board's one GND flag
        r.C(vbus, "GND", "10uF", "10V", use="VBUS bulk (USB limit 10 uF)")
        r.C(vbus, "GND", "100nF", "16V", spec="X7R", use="VBUS bypass")

    g = s.group("Power mux (U103), main port first")
    # XCOMP mode (TPS2121 datasheet 10.3): PR1 and CP2 are dividers from IN1 and IN2. With both
    # inputs at 5 V, PR1 = 1.76 V > CP2 = 1.56 V, so IN1 (main) is used. IN1 is dropped when
    # VIN1 < 1.56 V / 0.353 = 4.4 V. CP2 >= VREF also enables fast switchover.
    # All values are JLC Basic parts. The symbol is redrawn so every divider hangs off its pin:
    # PR1/CP2 dividers sit on far nodes (clear of the IN rail symbols), OV1/OV2 on near nodes.
    u = g.part("TPS2121RUXR", 0, 0, {
        "7": "VBUS_MAIN", "2": "VBUS_ESP", "1": "+5V", "8": "+5V", "9": "MUX_ST",
        "10": "MUX_ILIM", "11": "MUX_SS", "12": "GND", "6": "MUX_PR1", "5": "MUX_OV1",
        "4": "MUX_OV2", "3": "MUX_CP2"},
        prefix="U", attach=("3", "4", "5", "6", "9", "10", "11"),
        fields=dict(spec="Power mux 4.5 A", use="USB-C source selection"),
        fieldpos=[("Reference", nref(g, "U"), -10.16, -22.0, "left"), ("Value", "TPS2121RUXR", 10.16, 40.0, "left"),
                  ("spec", "Power mux 4.5 A", 10.16, 41.5, "left", 0.9)])

    def divider_at(pin, node_x, top, rt, rb, ut, ub):
        (px, py), d = u[pin]
        n = (node_x, py)
        g.wire((px, py), n)
        side = "right" if d[0] < 0 else "left"            # field text on the outer side
        fx = node_x - 1.8 if d[0] < 0 else node_x + 1.8
        vbranch(g, "R", (node_x, py - 2.54), (0, -1), u_net(pin), top, rt, use=ut,
                fieldpos=[("Reference", nref(g, "R"), fx, py - 7.1, side, 1.0), ("Value", rt, fx, py - 5.6, side, 1.0)])
        g.wire(n, (node_x, py - 2.54))
        vbranch(g, "R", (node_x, py + 2.54), (0, 1), u_net(pin), "GND", rb, use=ub,
                fieldpos=[("Reference", nref(g, "R"), fx, py + 5.6, side, 1.0), ("Value", rb, fx, py + 7.1, side, 1.0)])
        g.wire(n, (node_x, py + 2.54))
        g.junction(n)

    nets = {"6": "MUX_PR1", "3": "MUX_CP2", "5": "MUX_OV1", "4": "MUX_OV2"}
    u_net = nets.get
    # Creation order keeps the old references: R105/106 PR1, R107/108 CP2, R109/110 OV1, R111/112 OV2.
    divider_at("6", -27.94, "VBUS_MAIN", "22k", "12k", "PR1 divider top", "PR1 divider bottom: 1.76 V at 5 V")
    divider_at("3", 27.94, "VBUS_ESP", "22k", "10k", "CP2 divider top", "CP2 divider bottom: 1.56 V at 5 V")
    divider_at("5", -17.78, "VBUS_MAIN", "51k", "12k", "OV1 divider top: 1.06 x (1 + 51/12) = 5.57 V trip", "OV1 divider bottom")
    divider_at("4", 17.78, "VBUS_ESP", "51k", "12k", "OV2 divider top: 5.57 V trip", "OV2 divider bottom")
    # ILIM and SS hang straight down from their bottom pins.
    for pin, lib, val, kw in (("10", "R", "33k", dict(use="ILIM: 65.2/33^0.861 = 3.2 A typ, above the 2.4 A peak")),
                              ("11", "C", "100nF", dict(voltage="16V", spec="X7R", use="Soft start, 780 V/s"))):
        (px, py), _ = u[pin]
        g.wire((px, py), (px, py + 2.54))
        vbranch(g, lib, (px, py + 2.54), (0, 1), {"10": "MUX_ILIM", "11": "MUX_SS"}[pin], "GND", val,
                # SS cap text on its left, ILIM resistor text on its right (they sit 300 mil apart)
                fieldpos=[("Reference", nref(g, lib), px - 2.8, py + 5.6, "right", 1.0), ("Value", val, px - 2.8, py + 7.1, "right", 1.0),
                          ("voltage", "16V", px - 2.8, py + 8.5, "right", 0.8)] if lib == "C" else
                         [("Reference", nref(g, lib), px + 1.8, py + 5.6, "left", 1.0), ("Value", val, px + 1.8, py + 7.1, "left", 1.0)],
                **kw)
    # ST: open drain, pull-up straight above the pin; the port leaves sideways.
    (sx, sy), _ = u["9"]
    nst = (sx, sy - 2.54)
    g.wire((sx, sy), nst)
    vbranch(g, "R", (sx, sy - 5.08), (0, -1), "MUX_ST", "+3V3", "10k", use="ST open-drain pull-up (high = main port)",
            fieldpos=[("Reference", nref(g, "R"), sx + 1.8, sy - 10.7, "left", 1.0), ("Value", "10k", sx + 1.8, sy - 9.2, "left", 1.0)])
    g.wire(nst, (sx, sy - 5.08))
    g.wire(nst, (sx + 2.54, sy - 2.54))
    g.anchor((sx + 2.54, sy - 2.54), (1, 0), "MUX_ST")
    g.junction(nst)
    r = Row(g, 45.72, 7.62)
    r.C("+5V", "GND", "22uF", "10V", use="OUT bulk")
    r.C("+5V", "GND", "100nF", "16V", spec="X7R", use="OUT bypass")
    s.note("USB: no PD, Rd 5.1k on CC1/CC2, so a source offers 5 V only. SBU unused. Shield tied to GND.")
    s.note("TPS2121 (SLVSEA3F): XCOMP priority, switches to the ESP32 port when main VBUS < 4.4 V. ILIM 3.2 A typ for a 2.4 A peak load. OV1/OV2 trip at 5.57 V to protect the 5.5 V-max bucks, amp and LEDs.")
    s.note("ST = high when the main port (IN1) powers the board, low on the ESP32 port; read by ESP32 GPIO18.")
    return s


# ========================================================================================
# Sheet 2: regulators
# ========================================================================================
def buck(s, title, ref_vout, rtop, rbot, couts, sw, fb, note, cff):
    g = s.group(title)
    pins = g.part("TLV62569DBVR", 0, 0, {"4": "+5V", "1": "+5V", "2": "GND", "3": sw, "5": fb},
                  prefix="U", attach=("3", "5"), join=(("4", "1"),),
                  fields=dict(spec="2 A buck, 1.5 MHz", use=note))
    # SW -> inductor -> output rail, wired in line.
    g.inline(pins["3"][0], (1, 0), "SRP4020TA-2R2M", ref_vout, "2.2uH", n_near=sw, prefix="L",
             fields=dict(spec="2.2 uH 6 A Isat", use="Buck inductor (TI table 4 standard value)"),
             fieldpos=[("Reference", nref(g, "L"), 13.97, -4.6, "center", 1.0), ("Value", "2.2uH", 13.97, -0.6, "center", 1.0)])
    # FB divider wired in: VOUT node (inductor end) -> R1 down -> N -> R2 down -> GND, Cff across
    # R1 one column to the right. FB leaves its pin, drops below the IC's right side and enters N
    # from the left, so it never crosses the SW -> inductor path above it.
    vout = (20.32, -2.54)                              # inductor far lead end (rail symbol sits here)
    xd, xc = 25.4, 33.02
    g.wire(vout, (xd, -2.54))
    g.junction(vout)                                   # inductor lead, rail symbol and the wire
    g.part("R", xd, 1.27, {"1": ref_vout, "2": fb}, value=rtop, prefix="R", attach=("1", "2"), hlabels=False,
           fields=dict(tolerance="1%", power="62.5mW", use="FB divider top"), footprint="Mindspark:R_0402_1005Metric",
           fieldpos=[("Reference", nref(g, "R"), xd - 1.8, 0.52, "right", 1.0), ("Value", rtop, xd - 1.8, 2.02, "right", 1.0)])
    n = (xd, 7.62)
    g.wire((xd, 5.08), n)
    g.part("R", xd, 11.43, {"1": fb, "2": "GND"}, value=rbot, prefix="R", attach=("1",), hlabels=False,
           fields=dict(tolerance="1%", power="62.5mW", use="FB divider bottom (TI: R2 <= 200k)"),
           footprint="Mindspark:R_0402_1005Metric",
           fieldpos=[("Reference", nref(g, "R"), xd - 1.8, 10.68, "right", 1.0), ("Value", rbot, xd - 1.8, 12.18, "right", 1.0)])
    g.part("C", xc, 1.27, {"1": ref_vout, "2": fb}, value=cff, prefix="C", attach=("1", "2"), hlabels=False,
           fields=dict(voltage="50V", spec="C0G", use="Feed-forward: zero at about 117 kHz, as TI's 200k / 6.8 pF example"),
           footprint="Mindspark:C_0402_1005Metric",
           fieldpos=[("Reference", nref(g, "C"), xc + 2.8, 0.52, "left", 1.0), ("Value", cff, xc + 2.8, 2.02, "left", 1.0),
                     ("voltage", "50V", xc + 2.8, 3.4, "left", 0.8)])
    g.path((xd, -2.54), (xc, -2.54))
    g.junction((xd, -2.54))                            # wire in, R1 top, wire on to Cff
    g.path((xc, 5.08), (xd, 5.08))
    g.junction((xd, 5.08))                             # R1 bottom, Cff wire, wire down to N
    (fx, fy), _ = pins["5"]
    g.path((fx, fy), (fx + 2.54, fy), (fx + 2.54, 7.62), n)
    g.junction(n)                                      # R1 side, R2 top and the FB route
    r = Row(g, -7.62, 33.02)
    r.C("+5V", "GND", "10uF", "10V", use="Input cap (TI: >= 4.7 uF)")
    for v in couts:
        r.C(ref_vout, "GND", v, "10V" if ref_vout == "+3V3" else "6.3V", use="Output cap")
    rx = r.x
    g.flag((rx + 2.54, 33.02 - 6.35), ref_vout)
    return g


def sheet_regulators():
    s = Sheet(2, "regulators", "Regulators", {}, "0.9 V and 3.3 V bucks from +5 V; 1.8 V LDO from 3.3 V")
    # TLV62569: VOUT = 0.6 V x (1 + R1/R2).  0.6 x (1 + 51/100) = 0.906 V (XU316 VDD 0.855-0.945 V).
    buck(s, "0.9 V buck (U201)", "+0V9", "51k", "100k", ["22uF", "22uF"],
         "SW_0V9", "FB_0V9", "0.9 V XVF3800 core, 300 mA typ / 1 A max", "22pF")
    # 0.6 x (1 + 100/22) = 3.327 V (JLC Basic values; R2 = 22k is well under TI's 200k limit).
    buck(s, "3.3 V buck (U202)", "+3V3", "100k", "22k", ["22uF"],
         "SW_3V3", "FB_3V3", "3.3 V rail: XVF I/O + ESP32 (Wi-Fi peaks about 0.36 A)", "15pF")

    g = s.group("1.8 V LDO (U203)")
    g.part("TLV75518PDBVR", 0, 0, {"1": "+3V3", "3": "+3V3", "2": "GND", "4": None, "5": "+1V8"},
           prefix="U", join=(("1", "3"),), fields=dict(spec="500 mA LDO", use="1.8 V from 3.3 V, about 60 mA"))
    r = Row(g, -7.62, 33.02)
    r.C("+3V3", "GND", "1uF", "10V", use="LDO input (TI: >= 1 uF)")
    r.C("+1V8", "GND", "1uF", "6.3V", use="LDO output (TI: >= 1 uF)")

    g = s.group("Power LED and test points")
    led = g.part("LED", 0, 7.62, {"1": "GND", "2": "PWR_LED_A"}, rot=90, prefix="D", value="GREEN", attach=("2",),
                 fields=dict(spec="0603 green", use="Power indicator"), footprint="Mindspark:LED_0603_1608Metric")
    g.inline(led["2"][0], (0, -1), "R", "+5V", "2.2k", n_near="PWR_LED_A", use="Power LED, about 1 mA")
    x = 15.24
    for net in ("+5V", "+3V3", "+1V8", "+0V9", "GND"):
        g.part("TestPoint", x, 5.08, {"1": net}, prefix="TP", value=net,
               footprint="Mindspark:TestPoint_Pad_1.0x1.0mm", fields=dict(use="Rail test point"))
        x += 10.16
    s.note("TLV62569 (SLVSDG1C): L = 2.2 uH, COUT 2 x 22 uF for 0.6-1.2 V and 22 uF above 1.8 V (Table 4). EN tied to VIN: both bucks start together, within the XU316's 50 ms window. 3.3 V load: about 0.25 A typ, about 0.6 A peak with ESP32 Wi-Fi transmit (2 A buck).")
    return s


# ========================================================================================
# Sheet 3: XVF3800 core
# ========================================================================================
XVF_PORTS = {
    "USB_MAIN_DP": "bidirectional", "USB_MAIN_DM": "bidirectional",
    "XVF_QSPI_CS_N": "bidirectional", "XVF_QSPI_CLK": "bidirectional", "XVF_QSPI_D0": "bidirectional",
    "XVF_QSPI_D1": "bidirectional", "XVF_QSPI_D2": "bidirectional", "XVF_QSPI_D3": "bidirectional",
    "I2S_DATA0": "output", "I2S_LRCK": "output", "I2S_BCLK": "output", "MIC_CLK": "output",
    "MIC_DATA0": "input", "MIC_DATA1": "input", "MIC_DATA2": "input", "MIC_DATA3": "input",
    "BTN_MUTE_N": "input", "BTN_ACTION_N": "input",
    "XVF_GPO_R": "output", "XVF_GPO_G": "output", "XVF_INT_N": "output",
    "XVF_I2C_SCL": "bidirectional", "XVF_I2C_SDA": "bidirectional",
    "XVF_I2S_DATA1": "bidirectional", "XVF_I2S_DATA2": "bidirectional",
    "AMP_EN": "output", "XVF_RST_N": "bidirectional",
    "XVF_SPI_CS_N": "bidirectional", "XVF_SPI_MOSI": "bidirectional", "XVF_SPI_MISO": "bidirectional",
    "XVF_SQ_NLIN": "bidirectional", "XL_DN1": "bidirectional", "XL_DN0": "bidirectional",
    "XL_UP0": "bidirectional", "XL_UP1": "bidirectional", "MCLK_LOOP": "bidirectional",
}


def sheet_xvf():
    s = Sheet(3, "xvf3800", "XVF3800 core", XVF_PORTS,
              "XVF3800 on stock XMOS USB firmware: supplies, crystal, reset, JTAG")
    g = s.group("XVF3800 (U301)")
    V9, V33, V18 = "+0V9", "+3V3", "+1V8"
    pins = g.part("XVF3800-QF60B-C", 0, 0, {
        "1": "XVF_QSPI_D1", "2": "XVF_QSPI_D3", "3": "XVF_QSPI_CS_N", "4": V9, "5": "XVF_QSPI_CLK",
        "6": "XVF_SPI_CS_N", "7": "XVF_SPI_MOSI", "8": V33, "9": "I2S_DATA0", "10": "I2S_LRCK",
        "11": "BTN_MUTE_N", "12": V9, "13": "I2S_BCLK", "14": "MCLK_LOOP", "15": "XVF_XOUT", "16": "XVF_XIN",
        "17": V18, "18": "XVF_TDI", "19": V9, "20": "XVF_TDO", "21": "XVF_RST_N", "22": "PLL_AVDD",
        "23": "XVF_TMS", "24": "XVF_TCK", "25": None, "26": V18, "27": V9, "28": "USB_MAIN_DM",
        "29": "USB_MAIN_DP", "30": V33, "31": V18, "32": "BTN_ACTION_N", "33": "XL_DN1", "34": V9,
        "35": "XL_DN0", "36": "XL_UP0", "37": "XL_UP1", "38": V33, "39": "XVF_I2S_DATA1", "40": "AMP_EN", "41": "MCLK_LOOP",
        "42": V9, "43": "MIC_CLK", "44": "XVF_I2C_SCL", "45": "XVF_I2C_SDA", "46": "MIC_DATA0", "47": "XVF_SPI_MISO",
        "48": "MIC_DATA2", "49": V9, "50": "MIC_DATA1", "51": "MIC_DATA3", "52": V33, "53": "XVF_I2S_DATA2",
        "54": "XVF_SQ_NLIN", "55": "XVF_INT_N", "56": "XVF_GPO_R", "57": V9, "58": "XVF_GPO_G",
        "59": "XVF_QSPI_D0", "60": "XVF_QSPI_D2", "61": V9, "62": V9, "63": V9, "64": V9, "65": "GND"},
        prefix="U", join=(("61", "62", "63", "64"),),
        fields=dict(spec="Voice processor", use="XMOS XVF3800, stock USB firmware"))
    # MIC_CLK (pin 43) leaves unterminated: as on XMOS's XK-VOICE-SQ66, the buffer and the
    # series resistors sit with the mics (sheet audio).

    g = s.group("Decoupling and PLL filter")
    r = Row(g, 0, 0)
    for i in range(8):
        r.C(V9, "GND", "100nF", "6.3V", use="VDD pin bypass")
    r.C(V9, "GND", "10uF", "6.3V", use="VDD bulk")
    r = Row(g, 0, 30.48)
    for use in ("VDDIOL pin 8", "VDDIOR pin 38", "VDDIOT pin 52", "USB_VDD33A pin 30"):
        r.C(V33, "GND", "100nF", "10V", use=use)
    r.C(V33, "GND", "10uF", "10V", use="3.3 V bulk at XVF3800")
    for use in ("VDDIOB18 pin 17", "VDDIOB18 pin 26", "USB_VDD18A pin 31"):
        r.C(V18, "GND", "100nF", "6.3V", use=use)
    r.C(V18, "GND", "10uF", "6.3V", use="1.8 V bulk")
    # PLL_AVDD filter: ferrite from +0V9, cap and flag on the filtered node (wired).
    fx = r.x + 5.08
    fb = g.part("BLM15AG601SN1D", fx, 22.86, {"1": V9, "2": "PLL_AVDD"}, prefix="FB", attach=("2",),
                value="600R@100MHz", fields=dict(use="PLL_AVDD filter (XU316: 600 R at 100 MHz + 1 uF)"),
                fieldpos=[("Reference", nref(g, "FB"), fx + 2.4, 22.1, "left", 1.0),
                          ("Value", "600R@100MHz", fx + 2.4, 23.6, "left", 1.0)])
    n = (fx, 27.94)
    g.wire(fb["2"][0], n)
    vbranch(g, "C", (fx, 30.48), (0, 1), "PLL_AVDD", "GND", "1uF", voltage="6.3V", spec="X5R", use="PLL_AVDD cap",
            fieldpos=[("Reference", nref(g, "C"), fx - 2.6, 33.5, "right", 1.0), ("Value", "1uF", fx - 2.6, 35.0, "right", 1.0)])
    g.wire(n, (fx, 30.48))
    g.wire(n, (fx + 2.54, 27.94))
    g.junction(n)
    g.anchor((fx + 2.54, 27.94), (1, 0), "PLL_AVDD")
    g.flag_at((fx + 2.54, 27.94), (0, 1))

    g = s.group("24 MHz crystal")
    crystal(g, "X322524MOB4SI", "24MHz", "XVF_XIN", "XVF_XOUT", "XVF_XTAL_D", "22pF", "1M", "680R",
            dict(spec="12 pF, 50 R ESR", use="XVF3800 system clock"))

    g = s.group("Reset supervisor (U302)")
    # TPS3808G33 senses 3.3 V (trip 3.07 V). CT open = fixed 20 ms delay. RESET is open drain,
    # pulled to the 1.8 V bank; wired-OR with the ESP32's 2N7002 and the XTAG.
    u = g.part("TPS3808G33DBVR", 0, 0, {"6": V33, "5": V33, "4": None, "3": "RST_BTN_N", "1": "XVF_RST_N",
                                       "2": "GND"}, prefix="U", attach=("3", "1"),
               fields=dict(spec="Supervisor 3.07 V", use="Holds XVF3800 in reset until 3.3 V is good"))
    g.inline(u["3"][0], (-1, 0), "TS-1187A-B-A-B", "GND", "RESET", n_near="RST_BTN_N", prefix="SW",
             use="XVF3800 reset button (TPS3808 MR)",
             fieldpos=[("Reference", nref(g, "SW"), -17.78, -4.3, "center", 1.0), ("Value", "RESET", -17.78, -2.8, "center", 1.0)])
    tee(g, u["1"], "XVF_RST_N", (lambda near: vbranch(g, "R", near, (0, -1), "XVF_RST_N", V18, "10k",
                                                      use="RST_N pull-up to the 1.8 V bank",
                                                      fieldpos=[("Reference", nref(g, "R"), 14.5, -6.35, "left", 1.0),
                                                                ("Value", "10k", 14.5, -4.85, "left", 1.0)]), (0, -1)))
    r = Row(g, 27.94, -2.54)
    r.C(V33, "GND", "100nF", "10V", use="TPS3808 VDD bypass")

    g = s.group("JTAG (J301, 1.8 V) + pads")
    jt = {"1": V18, "2": "XVF_TMS", "3": "XVF_TCK", "4": "XVF_TDO", "5": "XVF_TDI", "6": "XVF_RST_N", "7": "GND",
          "MP": None}
    j = g.part("S7B-PH-SM4-TB", 0, 0, jt, prefix="J", attach=tuple("1234567"),
               fields=dict(spec="JST PH 7-pin", use="XTAG4 JTAG (1.8 V)"))
    # Parallel pads wired to the header lines (one pad per pin, in pin order).
    pads_on_lines(g, j, [(p, jt[p]) for p in "1234567"], -22.86, ["JTAG%s" % p for p in "1234567"],
                  "Mindspark:TestPoint_Pad_1.0x1.0mm", ["JTAG parallel pad %s" % p for p in "1234567"])  # 1.0 mm: user's KiCad edit 2026-11-12
    s.exceptions.append("MCLK_LOOP: labelled between pins 14 and 41 (opposite sides of U301)")
    s.note("Pins 39, 44, 45, 53, 55 go to the 2x12 header (sheet esp32_io); 55 (INT_N) also to ESP32 GPIO17, 56/58 (LED_R/G) to the status LED and ESP32 GPIO15/16. Pin 54 (SQ_nLIN, geometry select on XMOS's board) and the SPI-control and XLINK pins end on pads (sheet xvf3800_periph). Pin 25 is NC. MCLK loop: pin 14 to pin 41 as a short PCB trace.")
    s.note("Decoupling per XU316: >= 8 x 100 nF on VDD, 100 nF per VDDIO pin, >= 10 uF per rail; PLL_AVDD via 600 R ferrite + 1 uF. Crystal on the 1.8 V bank.")
    s.note("USB D+/D- go straight to the main USB-C (ESD on sheet usb_power); bus-powered, no VBUS sense.")
    return s


# ========================================================================================
# Sheet 4: XVF3800 peripherals
# ========================================================================================
def sheet_xvf_periph():
    s = Sheet(4, "xvf3800_periph", "XVF3800 flash, buttons, LEDs and pads", {
        "XVF_QSPI_CS_N": "bidirectional", "XVF_QSPI_CLK": "bidirectional", "XVF_QSPI_D0": "bidirectional",
        "XVF_QSPI_D1": "bidirectional", "XVF_QSPI_D2": "bidirectional", "XVF_QSPI_D3": "bidirectional",
        "BTN_MUTE_N": "output", "BTN_ACTION_N": "output",
        "ESP_MUTE_LED": "input", "XVF_GPO_R": "input", "XVF_GPO_G": "input",
        "I2S_DATA0": "input", "I2S_LRCK": "input", "I2S_BCLK": "input",
        "XVF_SPI_CS_N": "bidirectional", "XVF_SPI_MOSI": "bidirectional", "XVF_SPI_MISO": "bidirectional",
        "XVF_SQ_NLIN": "bidirectional", "XL_DN1": "bidirectional", "XL_DN0": "bidirectional",
        "XL_UP0": "bidirectional", "XL_UP1": "bidirectional", "MCLK_LOOP": "bidirectional"},
        "Boot flash, user buttons, mute LED, status LED, spare-pin pads")
    g = s.group("Boot flash (U401)")
    u = g.part("W25Q32JVUUIQ", 0, 0, {"1": "XVF_QSPI_CS_N", "2": "XVF_QSPI_D1", "3": "XVF_QSPI_D2", "4": "GND",
                                      "5": "XVF_QSPI_D0", "6": "XVF_QSPI_CLK", "7": "XVF_QSPI_D3", "8": "+3V3",
                                      "9": None},
               prefix="U", attach=("1",), fields=dict(spec="32 Mbit QSPI flash", use="XVF3800 boot image"),
               fieldpos=[("Reference", nref(g, "U"), 11.5, -5.0, "left", 1.27), ("Value", "W25Q32JVUUIQ", 11.5, 6.4, "left", 1.27),
                         ("spec", "32 Mbit QSPI flash", 11.5, 8.0, "left", 0.9)])
    tee(g, u["1"], "XVF_QSPI_CS_N", (lambda near: vbranch(g, "R", near, (0, -1), "XVF_QSPI_CS_N", "+3V3", "4.7k",
                                                          use="QSPI_CS_N pull-up (XVF3800)",
                                                          fieldpos=[("Reference", nref(g, "R"), -15.24, -18.9, "center", 1.0),
                                                                    ("Value", "4.7k", -15.24, -17.4, "center", 1.0)]), (0, -1)))
    r = Row(g, 27.94, -2.54)
    r.C("+3V3", "GND", "100nF", "10V", use="Flash bypass")

    g = s.group("Buttons")
    for i, (net, name) in enumerate((("BTN_MUTE_N", "MUTE"), ("BTN_ACTION_N", "ACTION"))):
        x = i * 22.86
        rr = g.R(x, 0, "+3V3", net, "10k", use="%s button pull-up" % name.lower(), attach=("2",),
                 fieldpos=[("Reference", nref(g, "R"), x + 2.3, -1.0, "left", 1.0), ("Value", "10k", x + 2.3, 0.5, "left", 1.0)])
        n = (x, 6.35)
        g.wire(rr["2"][0], n)
        g.wire(n, (x + 2.54, 6.35))
        g.anchor((x + 2.54, 6.35), (1, 0), net)
        g.wire(n, (x, 8.89))
        g.junction(n)
        sw = g.part("TS24CA", x, 13.97, {"1": net, "2": "GND"}, rot=270, prefix="SW", value=name, attach=("1",),
                    fields=dict(spec="side-pressed", use="%s button (XVF3800), board edge" % name.lower()),
                    fieldpos=[("Reference", nref(g, "SW"), x - 3.6, 13.2, "right", 1.0), ("Value", name, x - 3.6, 14.7, "right", 1.0)])

    g = s.group("Mute and status LEDs")
    led = g.part("LED", 0, 10.16, {"1": "GND", "2": "LED_MUTE_A"}, rot=90, prefix="D", value="RED", attach=("2",),
                 fields=dict(spec="0603 red", use="Mute indicator"), footprint="Mindspark:LED_0603_1608Metric")
    g.inline(led["2"][0], (0, -1), "R", "ESP_MUTE_LED", "1k", n_near="LED_MUTE_A", use="Mute LED from ESP32 GPIO41, about 1.3 mA")
    rgb = g.part("TJ-S1615CY6TGLCCSRGB-A5", 25.4, 7.62, {"4": "LED_RGB_R", "3": "LED_RGB_G", "2": None, "1": "GND"},
                 prefix="D", value="RGB", attach=("3", "4"),
                 fields=dict(spec="RGB, common cathode", use="XVF3800 status, red pin 56, green pin 58; blue unused"))
    for pin, net, an, val in (("4", "XVF_GPO_R", "LED_RGB_R", "1k"), ("3", "XVF_GPO_G", "LED_RGB_G", "330R")):
        (px, py), d = rgb[pin]
        g.inline((px, py), d, "R", net, val, n_near=an, use="RGB status LED series resistor",
                 fieldpos=[("Reference", nref(g, "R"), px + 2.54 + 3.81, py - 1.6, "center", 0.9),
                           ("Value", val, px + 2.54 + 3.81 + 6.0, py - 1.6, "center", 0.9)])
    g = s.group("Spare-pin pads and I2S taps")
    x = 0
    for net, val in (("XVF_SPI_CS_N", "SPI_CS_N"), ("XVF_SPI_MOSI", "SPI_MOSI"), ("XVF_SPI_MISO", "SPI_MISO"),
                     ("XVF_SQ_NLIN", "SQ_nLIN"), ("XL_DN1", "XL_DN1"), ("XL_DN0", "XL_DN0")):
        g.part("TestPoint", x, 0, {"1": net}, prefix="TP", value=val,
               footprint="Mindspark:TestPoint_Pad_1.0x1.0mm", fields=dict(use="Spare XVF3800 pin pad"))
        x += 12.7
    x = 0
    for net, val in (("XL_UP0", "XL_UP0"), ("XL_UP1", "XL_UP1"), ("I2S_DATA0", "I2S_DAT0"), ("I2S_LRCK", "I2S_LRCK"),
                     ("I2S_BCLK", "I2S_BCLK"), ("MCLK_LOOP", "MCLK")):
        g.part("TestPoint", x, 27.94, {"1": net}, prefix="TP", value=val,
               footprint="Mindspark:TestPoint_Pad_1.0x1.0mm", fields=dict(use="XVF3800 pad / I2S tap"))
        x += 12.7
    s.note("Buttons are active low. The XVF3800 GPO pins are assumed active high (LED on when high). Status LED: red/green from XVF pins 56/58 as on XMOS's two-colour LED; blue anode left open. The mute LED is driven by the ESP32.")
    s.note("XVF3800 flash: QSPI_CS_N pull-up 4.7k. Must be ready within 300 us of reset release. The four flash lines are also reachable by the ESP32 through the switches on sheet esp32_io. No SPI-slave boot.")
    return s


# ========================================================================================
# Sheet 5: audio (mics + amp)
# ========================================================================================
AUDIO_ORDER = (0, 1, 2, 3)       # packing order of the audio boxes (refs keep creation order)


def sheet_audio():
    s = Sheet(5, "audio", "Microphones and speaker amplifier", {
        "I2S_DATA0": "input", "I2S_LRCK": "input", "I2S_BCLK": "input", "MIC_CLK": "input",
        "MIC_DATA0": "output", "MIC_DATA1": "output", "MIC_DATA2": "output", "MIC_DATA3": "output",
        "AMP_EN": "input"},
        "Four PDM mics (one per XVF3800 data pin) and the MAX98357A class-D amp")
    # Square positions copied from XMOS XK-VOICE-SQ66 (JGB0084 1V1 placement file, square mode):
    # MIC_DATA0 = XMOS MIC1, 1 = MIC4, 2 = MIC5, 3 = MIC3; 66 x 66 mm, all on the bottom side.
    corner = ("far-left (XMOS MIC1)", "USB-side left (XMOS MIC4)", "USB-side right (XMOS MIC5)",
              "far-right (XMOS MIC3)")
    g = s.group("PDM mics (MK501-MK504) and clock buffer, 66 mm square")
    # One XVF3800 clock drives four mics up to 93 mm apart: buffered and series-terminated as on
    # XMOS's XK-VOICE-SQ66 (74LVC1G125 + 100R, then 100R into each mic CLK, 100R in each DATA).
    # The buffered clock is drawn as one wire: down the left column, along the bottom, up the
    # right column, with each mic's CLK resistor tapping it.
    XL, XR, YB = -36.83, 21.59, 43.18                    # left / right clock risers, bottom run
    bx, by = XL - 25.4, 15.24                            # buffer: its output resistor ends on XL
    u = g.part("SN74LVC1G125DBVR", bx, by, {"1": "GND", "2": "MIC_CLK", "3": "GND", "4": "MIC_CLK_Y",
                                            "5": "+3V3"}, prefix="U", attach=("4",),
               fields=dict(spec="Buffer, 3-state", use="MIC_CLK fan-out buffer, OE tied low (always on)"))
    tap = series_r(g, u["4"][0], (1, 0), "MIC_CLK_Y", "MIC_CLK_BUF", "100R", "Buffer output series (XMOS R12)",
                   [("Reference", nref(g, "R"), bx + 19.05, by - 2.2, "center", 1.0), ("Value", "100R", bx + 19.05, by + 2.2, "center", 1.0)])
    # Each mic's CLK and DATA series resistors sit in line at its pins (XMOS places them at each
    # mic). CLK resistors are created first so they keep R502-R505; DATA ones are R506-R509.
    pins = []
    for i in range(4):
        x, y = (i % 2) * 58.42, (i // 2) * 30.48
        pins.append(g.part("IM69D129FV01XTMA1", x, y, {"1": "MIC%d_DAT" % i, "2": "GND", "3": "GND",
                                                       "4": "MIC%d_CLK" % i, "5": "+3V3_MIC"},
                           prefix="MK", attach=("1", "4"),
                           fields=dict(spec="PDM mic", use="MIC_DATA%d, %s corner" % (i, corner[i]))))
    ends = []
    for i, p in enumerate(pins):
        (px, py), _ = p["4"]                           # CLK (lower left pin): fields below
        ends.append(series_r(g, (px, py), (-1, 0), "MIC%d_CLK" % i, "MIC_CLK_BUF", "100R",
                             "CLK series at mic %d (XMOS R11/R13/R15/R17)" % i,
                             [("Reference", nref(g, "R"), px - 6.35, py + 2.2, "center", 1.0),
                              ("Value", "100R", px - 6.35, py + 3.7, "center", 1.0)]))
    for i, p in enumerate(pins):
        (px, py), _ = p["1"]                           # DATA (upper left pin): fields above
        g.inline((px, py), (-1, 0), "R", "MIC_DATA%d" % i, "100R", n_near="MIC%d_DAT" % i,
                 use="DATA series at mic %d (XMOS R10/R14/R16/R18)" % i,
                 fieldpos=[("Reference", nref(g, "R"), px - 6.35, py - 3.7, "center", 1.0),
                           ("Value", "100R", px - 6.35, py - 2.2, "center", 1.0)])
    # Clock wire: each CLK resistor end runs out to its column's riser.
    for e in ends:
        g.wire(e, (XL if e[0] < 0 else XR, e[1]))
    top_l, bot_l = (XL, ends[0][1]), (XL, ends[2][1])
    top_r, bot_r = (XR, ends[1][1]), (XR, ends[3][1])
    g.path(top_l, tap, bot_l, (XL, YB), (XR, YB), bot_r, top_r)
    for pt in (tap, bot_l, bot_r):
        g.junction(pt)                                 # tees on the clock wire
    # One decoupling bank: the buffer's +3V3 cap, then the four mic caps (place each at its part).
    r = Row(g, -88.9, 53.34)                          # under the buffer, left of the clock run
    r.C("+3V3", "GND", "100nF", "16V", spec="X7R", use="Buffer bypass, U501")
    for i in range(4):
        r.C("+3V3_MIC", "GND", "1uF", "10V", use="Mic %d bypass, MK%d" % (i, 501 + i))

    g = s.group("Mic supply")
    fb = g.part("BLM15AG601SN1D", 0, 0, {"1": "+3V3", "2": "+3V3_MIC"}, prefix="FB", attach=("2",),
                value="600R@100MHz", fields=dict(use="Mic supply filter"),
                fieldpos=[("Reference", nref(g, "FB"), -2.4, -0.75, "right", 1.0), ("Value", "600R@100MHz", -2.4, 0.75, "right", 1.0)])
    n = (0, 5.08)
    g.wire(fb["2"][0], n)
    vbranch(g, "C", (0, 7.62), (0, 1), "+3V3_MIC", "GND", "10uF", voltage="10V", spec="X5R", use="Mic supply bulk",
            fieldpos=[("Reference", nref(g, "C"), -2.6, 10.6, "right", 1.0), ("Value", "10uF", -2.6, 12.1, "right", 1.0)])
    g.wire(n, (0, 7.62))
    g.wire(n, (7.62, 5.08))
    g.junction(n)
    g.anchor((7.62, 5.08), (0, -1), "+3V3_MIC")
    g.flag_at((7.62, 5.08), (1, 0))
    g.items[-1]["ref"]                                  # (flag drawn on the rail point)

    g = s.group("Amp load switch (U502)")
    u = g.part("TPS22918DBVR", 0, 0, {"1": "+5V", "2": "GND", "3": "AMP_EN", "4": "AMP_CT", "5": "+5V_AMP",
                                     "6": "+5V_AMP"}, prefix="U", attach=("3", "4"), join=(("6", "5"),),
               fields=dict(spec="2 A load switch", use="Amp supply switch, QOD to VOUT"))
    tee(g, u["3"], "AMP_EN", (lambda near: vbranch(g, "R", near, (0, 1), "AMP_EN", "GND", "100k",
                                                   use="Keeps the amp off while the XVF3800 is in reset",
                                                   fieldpos=[("Reference", nref(g, "R"), -15.8, 8.9, "right", 1.0),
                                                             ("Value", "100k", -15.8, 10.4, "right", 1.0)]), (0, 1)))
    (cx, cy), d = u["4"]
    g.path((cx, cy), (cx + 2.54, cy), (cx + 2.54, cy + 2.54))
    vbranch(g, "C", (cx + 2.54, cy + 2.54), (0, 1), "AMP_CT", "GND", "1nF", voltage="16V", spec="X7R",
            use="CT: about 2.5 ms rise at 5 V",
            fieldpos=[("Reference", nref(g, "C"), cx + 5.2, cy + 5.6, "left", 1.0), ("Value", "1nF", cx + 5.2, cy + 7.1, "left", 1.0)])
    r = Row(g, -22.86, 33.02)
    r.C("+5V", "GND", "1uF", "10V", use="Load switch input")

    g = s.group("Speaker amp (U503) and speaker (J501)")
    # MAX98357AETE+T, TQFN-16 (2026-11-12, replaces the WLP-9 part). Stacked pins: VDD 7/8,
    # GND 3/11/15 + EP 17. Pins 5, 6, 12, 13 are N.C. (hidden, no marker).
    u = g.part("MAX98357AETE+T", 0, 0, {"4": "AMP_SD", "7": "+5V_AMP", "9": "SPK_P", "1": "I2S_DATA0",
                                        "2": None, "10": "SPK_N", "16": "I2S_BCLK", "3": "GND", "14": "I2S_LRCK",
                                        "5": None, "6": None, "12": None, "13": None},
               prefix="U", attach=("4",), fields=dict(spec="I2S class-D 3.2 W", use="Speaker amp, GAIN_SLOT open = 9 dB"))
    g.inline(u["4"][0], (-1, 0), "R", "+5V_AMP", "1M", n_near="AMP_SD", far_dir=(-1, 0),
             use="SD_MODE: R_LARGE = 222.2 x 5 - 100 = 1011k -> (L+R)/2",
             fieldpos=[("Reference", nref(g, "R"), -23.5, 4.3, "center", 1.0), ("Value", "1M", -23.5, 5.8, "center", 1.0)])
    r = Row(g, 0, 25.4)                                  # decoupling bank under the amp
    r.C("+5V_AMP", "GND", "100nF", "16V", spec="X7R", use="Amp VDD bypass")
    r.C("+5V_AMP", "GND", "10uF", "10V", use="Amp VDD (ADI: 10 uF + 0.1 uF)")
    r.C("+5V_AMP", "GND", "47uF", "10V", use="Amp bulk for 1.4 A peaks")
    # OUTP/OUTN wired straight to the speaker connector; the solder pads tee off the two lines
    # (SPK+ above the upper line, SPK- below the lower one).
    jx = 40.64
    j = g.part("S2B-PH-SM4-TB", jx, -1.27, {"1": "SPK_P", "2": "SPK_N", "MP": None}, prefix="J", attach=("1", "2"),
               fields=dict(spec="JST PH 2-pin, 2 A", use="4 R 5 W speaker"),
               fieldpos=[("Reference", nref(g, "J"), jx - 5.08, -6.0, "left"),
                         ("Value", "S2B-PH-SM4-TB", jx - 5.08, 9.5, "left"), ("spec", "JST PH 2-pin, 2 A", jx - 5.08, 11.0, "left", 0.9)])
    xt = 27.94
    for pin, net, rot, value, use, fy in (("9", "SPK_P", 0, "SPK+", "Speaker solder pad +", -4.3),
                                          ("10", "SPK_N", 180, "SPK-", "Speaker solder pad -", 4.3)):
        (ax, ay), _ = u[pin]
        g.wire((ax + 2.54, ay), j["1" if net == "SPK_P" else "2"][0])
        ref = nref(g, "TP")
        g.part("TestPoint", xt, ay, {"1": net}, rot=rot, prefix="TP", value=value, attach=("1",),
               footprint="Mindspark:TestPoint_THTPad_2.0x2.0mm_Drill1.0mm", fields=dict(use=use),
               fieldpos=[("Reference", ref, xt + 1.6, fy - 0.75, "left", 1.0), ("Value", value, xt + 1.6, fy + 0.75, "left", 1.0)])
        g.junction((xt, ay))                           # line in, line on, pad
    s.note("Mics: corners of a 66 x 66 mm square on the underside, in XMOS's square order (stock -sqr firmware): DATA0 far-left, DATA1 USB-side left, DATA2 USB-side right, DATA3 far-right. XVF pins: DATA0 46, 1 50, 2 48, 3 51.")
    s.note("Mic SELECT tied to GND, as on XMOS's board. Amp: MAX98357A, 9 dB (GAIN_SLOT open), (L+R)/2; its load switch EN is XVF3800 pin 40.")
    s.note("MAX98357A: SD_MODE 1M to VDD with the internal 100k pull-down gives 0.45 V = (L+R)/2 mode. The load switch removes amp power when the XVF3800 drops pin 40.")
    # Packing order (refs stay as created): mic boxes first, then the amp chain. With the mic
    # decoupling bank this is the order that fits A4 (found by trying the mic-first orders).
    s.groups = [s.groups[i] for i in AUDIO_ORDER]
    return s


# ========================================================================================
# Sheet 6: ESP32-S3 helper MCU
# ========================================================================================
ESP_PORTS = {
    "USB_ESP_DP": "bidirectional", "USB_ESP_DM": "bidirectional", "MUX_ST": "input",
    "XVF_GPO_R": "input", "XVF_GPO_G": "input", "XVF_INT_N": "input",
    "LED_DATA": "output", "LED_EN": "output", "ESP_MUTE_LED": "output",
    "ESP_UART_TX": "output", "ESP_UART_RX": "input", "ESP_I2C_SDA": "bidirectional", "ESP_I2C_SCL": "bidirectional",
    "PRG_CS_N": "output", "PRG_CLK": "output", "PRG_DI": "output", "PRG_DO": "input",
    "PRG_RST": "output", "PRG_EN": "input",
    "ESP_GPIO1": "bidirectional", "ESP_GPIO2": "bidirectional", "ESP_GPIO4": "bidirectional",
    "ESP_GPIO5": "bidirectional", "ESP_GPIO6": "bidirectional", "ESP_GPIO7": "bidirectional",
    "ESP_GPIO8": "bidirectional", "ESP_GPIO9": "bidirectional",
}
# Module pad -> net (GPIO in the comment). Strapping pins 3, 45, 46 and the PSRAM pins 35-37 are
# left unconnected; GPIO0 keeps only the BOOT pull-up and button. SPI2 (FSPI) uses its IO_MUX
# pins 10-13 for path B. GPIO19/20 are the USB pins.
ESP_PINS = {
    "1": "GND", "40": "GND", "41": "GND", "2": "+3V3", "3": "ESP_EN", "27": "ESP_BOOT",       # GPIO0
    "39": "ESP_GPIO1", "38": "ESP_GPIO2", "4": "ESP_GPIO4", "5": "ESP_GPIO5",                 # 1, 2, 4, 5
    "6": "ESP_GPIO6", "7": "ESP_GPIO7", "12": "ESP_GPIO8", "17": "ESP_GPIO9",                 # 6, 7, 8, 9
    "18": "PRG_CS_N", "19": "PRG_DI", "20": "PRG_CLK", "21": "PRG_DO",                        # 10 CS, 11 MOSI, 12 CLK, 13 MISO
    "22": "PRG_EN", "23": "PRG_RST",                                                          # 14, 21
    "8": "XVF_GPO_R", "9": "XVF_GPO_G", "10": "XVF_INT_N", "11": "MUX_ST",                    # 15, 16, 17, 18
    "13": "ESP_USB_DM", "14": "ESP_USB_DP",                                                   # 19, 20
    "31": "ESP_I2C_SDA", "32": "ESP_I2C_SCL",                                                 # 38, 39
    "33": "USER_LED_DATA", "34": "ESP_MUTE_LED", "35": "BTN_USER_N",                          # 40, 41, 42
    "37": "ESP_UART_TX", "36": "ESP_UART_RX",                                                 # 43, 44
    "24": "LED_EN", "25": "LED_DATA",                                                         # 47, 48
    "15": None, "16": None, "26": None, "28": None, "29": None, "30": None,                   # 3, 46, 45, 35-37
}


def sheet_esp32():
    s = Sheet(6, "esp32", "ESP32-S3 helper MCU", ESP_PORTS,
              "ESP32-S3-WROOM-1U (IPEX): supply, EN/BOOT, USB, user button and user LED")
    g = s.group("ESP32-S3-WROOM-1U-N16R8 (U601)")
    # Footprint: Espressif's own ESP32-S3-WROOM-1U (chosen by the user in KiCad 2026-11-12, copied
    # into the Mindspark library the same day): same 41 pads as the stock one, plus Espressif's STEP.
    g.part("ESP32-S3-WROOM-1U-N16R8", 0, 0, dict(ESP_PINS), prefix="U",
           footprint="Mindspark:ESP32-S3-WROOM-1U",
           fields=dict(spec="Wi-Fi/BLE module, IPEX", use="Helper MCU (own firmware)"))

    g = s.group("Supply, EN and BOOT")
    r = Row(g, 0, 0)
    r.C("+3V3", "GND", "22uF", "10V", use="Module bulk (controller board / Espressif)")
    r.C("+3V3", "GND", "100nF", "16V", spec="X7R", use="Module bypass")
    # EN RC and the GPIO0 pull-up are wired to their buttons' top pins; the nets reach the module
    # by label. Switch pin 1 is on top (rot 270): (x, -10.16); 100 mil lead up to N1.
    ex, bx = 27.94, 48.26
    n1, n2 = (ex, -12.7), (ex, -15.24)
    g.path(n1, n2)
    vbranch(g, "R", (ex, -17.78), (0, -1), "ESP_EN", "+3V3", "10k", use="EN pull-up (Espressif RC delay)",
            fieldpos=[("Reference", nref(g, "R"), ex + 1.8, -22.36, "left", 1.0), ("Value", "10k", ex + 1.8, -20.86, "left", 1.0)])
    g.wire(n2, (ex, -17.78))
    g.path(n1, (ex - 7.62, -12.7), (ex - 7.62, -10.16))
    vbranch(g, "C", (ex - 7.62, -10.16), (0, 1), "ESP_EN", "GND", "1uF", voltage="10V", spec="X5R",
            use="EN delay, 10k x 1 uF",
            fieldpos=[("Reference", nref(g, "C"), ex - 10.4, -7.1, "right", 1.0), ("Value", "1uF", ex - 10.4, -5.6, "right", 1.0),
                      ("voltage", "10V", ex - 10.4, -4.2, "right", 0.8)])
    g.wire(n2, (ex + 2.54, -15.24))
    g.anchor((ex + 2.54, -15.24), (1, 0), "ESP_EN")
    g.junction(n1)
    g.junction(n2)
    nb = (bx, -12.7)
    vbranch(g, "R", (bx, -15.24), (0, -1), "ESP_BOOT", "+3V3", "10k", use="GPIO0 pull-up (Espressif)",
            fieldpos=[("Reference", nref(g, "R"), bx + 1.8, -19.82, "left", 1.0), ("Value", "10k", bx + 1.8, -18.32, "left", 1.0)])
    g.wire(nb, (bx, -15.24))
    g.wire(nb, (bx + 2.54, -12.7))
    g.anchor((bx + 2.54, -12.7), (1, 0), "ESP_BOOT")
    g.junction(nb)
    for i, (net, name, use) in enumerate((("ESP_EN", "EN", "ESP32 reset (EN) button"),
                                          ("ESP_BOOT", "BOOT", "ESP32 BOOT (GPIO0) button"))):
        x = (ex, bx)[i]
        sw = g.part("TS-1187A-B-A-B", x, -5.08, {"1": net, "2": net + "_R"}, rot=270, prefix="SW", value=name,
                    attach=("1", "2"), fields=dict(use=use),
                    fieldpos=[("Reference", nref(g, "SW"), x + 3.6, -5.84, "left", 1.0), ("Value", name, x + 3.6, -4.34, "left", 1.0)])
        g.wire(sw["1"][0], (x, -12.7))
        g.inline(sw["2"][0], (0, 1), "R", "GND", "1k", n_near=net + "_R", use="%s button series resistor" % name,
                 fieldpos=[("Reference", nref(g, "R"), x + 2.3, 6.86, "left", 1.0), ("Value", "1k", x + 2.3, 8.36, "left", 1.0)])
    s.exceptions.append("ESP_EN / ESP_BOOT: labelled between the button circuits and the module's dense pins")

    g = s.group("USB series resistors")
    g.R(0, 0, "ESP_USB_DP", "USB_ESP_DP", "27R", orient="h", use="USB D+ series (Espressif: 22-33 R)")
    g.R(0, 7.62, "ESP_USB_DM", "USB_ESP_DM", "27R", orient="h", use="USB D- series (Espressif: 22-33 R)")

    g = s.group("User button")
    rr = g.R(0, 0, "+3V3", "BTN_USER_N", "10k", use="user button pull-up", attach=("2",),
             fieldpos=[("Reference", nref(g, "R"), 2.3, -1.0, "left", 1.0), ("Value", "10k", 2.3, 0.5, "left", 1.0)])
    n = (0, 6.35)
    g.wire(rr["2"][0], n)
    g.wire(n, (2.54, 6.35))
    g.anchor((2.54, 6.35), (1, 0), "BTN_USER_N")
    g.wire(n, (0, 8.89))
    g.junction(n)
    g.part("TS24CA", 0, 13.97, {"1": "BTN_USER_N", "2": "GND"}, rot=270, prefix="SW", value="USER", attach=("1",),
           fields=dict(spec="side-pressed", use="User button (ESP32 GPIO42, active low), board edge"),
           fieldpos=[("Reference", nref(g, "SW"), -3.6, 13.2, "right", 1.0), ("Value", "USER", -3.6, 14.7, "right", 1.0)])

    g = s.group("User RGB LED (D601), own 5 V buffer")
    # Separate from the ring: always-on +5V, its own AHCT buffer (WS2812 needs ~3.5 V high at 5 V).
    u = g.part("SN74AHCT1G125DBVR", 0, 0, {"1": "GND", "2": "USER_LED_DATA", "3": "GND", "4": "USER_LED_5V",
                                           "5": "+5V"}, prefix="U", attach=("4",),
               fields=dict(spec="Buffer, TTL inputs", use="User LED data level shift"))
    end = series_r(g, u["4"][0], (1, 0), "USER_LED_5V", "USER_LED_DIN", "33R", "Data line series resistor",
                   [("Reference", nref(g, "R"), 19.05, -2.2, "center", 1.0), ("Value", "33R", 19.05, 2.2, "center", 1.0)])
    d = g.part("WS2812B-2020", 45.72, 0, {"3": "USER_LED_DIN", "1": None, "4": "+5V", "2": "GND"}, prefix="D",
               value="WS2812B-2020", attach=("3",), fields=dict(spec="WS2812B-2020", use="User RGB LED (ESP32 GPIO40)"))
    g.wire(end, d["3"][0])                              # resistor straight into DIN
    r = Row(g, 63.5, 0)
    r.C("+5V", "GND", "100nF", "16V", spec="X7R", use="Buffer bypass")
    r.C("+5V", "GND", "100nF", "16V", spec="X7R", use="User LED bypass")
    s.note("GPIO: 0 BOOT, 1/2/4-9 2x12 header, 10-13 SPI2 to the XVF flash (CS, MOSI=DI, CLK, MISO=DO), 14 PROG switch sense, 15/16 XVF LED_R/G taps, 17 XVF INT_N, 18 mux ST, 19/20 USB, 21 XVF reset (Q701), 38/39 I2C SDA/SCL, 40 user LED, 41 mute LED, 42 user button, 43/44 UART0 TX/RX (J701 21/22), 47 ring enable, 48 ring data.")
    s.note("Not connected: strapping pins 3, 45, 46 and PSRAM pins 35-37 (N16R8 = octal PSRAM). Antenna: IPEX connector on the module, antenna off board.")
    return s


# ========================================================================================
# Sheet 7: ESP32 I/O: XVF programming link + headers
# ========================================================================================
def sheet_link():
    s = Sheet(7, "esp32_io", "ESP32 I/O and XVF programming link", {
        "XVF_QSPI_CS_N": "bidirectional", "XVF_QSPI_CLK": "bidirectional", "XVF_QSPI_D0": "bidirectional",
        "XVF_QSPI_D1": "bidirectional",
        "PRG_CS_N": "input", "PRG_CLK": "input", "PRG_DI": "input", "PRG_DO": "output",
        "PRG_RST": "input", "XVF_RST_N": "bidirectional", "PRG_EN": "output",
        "ESP_UART_TX": "input", "ESP_UART_RX": "output",
        "ESP_I2C_SDA": "bidirectional", "ESP_I2C_SCL": "bidirectional",
        "ESP_GPIO1": "bidirectional", "ESP_GPIO2": "bidirectional", "ESP_GPIO4": "bidirectional",
        "ESP_GPIO5": "bidirectional", "ESP_GPIO6": "bidirectional", "ESP_GPIO7": "bidirectional",
        "ESP_GPIO8": "bidirectional", "ESP_GPIO9": "bidirectional",
        "XVF_I2C_SCL": "bidirectional", "XVF_I2C_SDA": "bidirectional", "XVF_INT_N": "input",
        "XVF_I2S_DATA1": "bidirectional", "XVF_I2S_DATA2": "bidirectional"},
        "Switch-enabled flash switches (path B), XVF3800 reset, I2C pull-ups and 2x12 GPIO header")
    g = s.group("XVF flash switches (U701-U704)")
    pairs = (("XVF_QSPI_CS_N", "PRG_CS_N"), ("XVF_QSPI_CLK", "PRG_CLK"),
             ("XVF_QSPI_D0", "PRG_DI"), ("XVF_QSPI_D1", "PRG_DO"))
    # The four IN pins share one PRG_EN wire: each IN line runs left under its COM label to a
    # riser per column; the risers meet along the bottom. One port label on the left riser.
    XL, XR, YB = -29.21, 26.67, 58.42
    ins = []
    for i, (com, no) in enumerate(pairs):
        x, y = (i % 2) * 55.88, (i // 2) * 38.1
        # TS5A3166DBVR, SOT-23-5 (2026-11-12, replaces the DSBGA YZPR): 1 NO, 2 COM, 3 GND, 4 IN, 5 V+.
        sw = g.part("TS5A3166DBVR", x, y, {"2": com, "1": no, "4": "PRG_EN", "5": "+3V3", "3": "GND"},
                    prefix="U", attach=("4",), fields=dict(spec="SPST 0.9 R", use="XVF flash line %s <-> ESP32" % com[9:]))
        (px, py), _ = sw["4"]
        rx = XL if i % 2 == 0 else XR
        g.wire((px, py), (rx, py))
        ins.append((rx, py))
    g.path((XL, -5.08), (XL, YB), (XR, YB), (XR, ins[1][1]))
    for pt in (ins[0], ins[2], ins[3]):
        g.junction(pt)                                  # IN lines teeing into the risers
    g.anchor((XL, -5.08), (-1, 0), "PRG_EN")
    # One decoupling bank for the four switches: one +3V3 and one GND (place each cap at its switch).
    r = Row(g, 0, 76.2)
    for i in range(4):
        r.C("+3V3", "GND", "100nF", "10V", use="Switch bypass, U%d" % (701 + i))

    g = s.group("PROG switch, XVF reset")
    # Side slide switch (replaces the JP701 jumper, 2026-11-11). The common pin drives PRG_EN:
    # slid to pin 1 = +3V3 (programming), to pin 3 = GND (normal run). The 4.7k pull-down keeps
    # PRG_EN low while the slider is between positions.
    sw = g.part("MSK12C02", 0, 0, {"1": "+3V3", "2": "PRG_EN", "3": "GND"}, prefix="SW", value="PROG", attach=("2",),
                fields=dict(spec="SPDT side slide", use="1-2 = PROG (ESP32 may write the XVF flash), 2-3 = RUN"),
                fieldpos=[("Reference", nref(g, "SW"), 0, -5.1, "center", 1.0), ("Value", "PROG", 0, 5.3, "center", 1.0)])
    tee(g, sw["2"], "PRG_EN", (lambda near: vbranch(g, "R", near, (0, 1), "PRG_EN", "GND", "4.7k",
                                                    use="Switches off by default",
                                                    fieldpos=[("Reference", nref(g, "R"), -5.3, 8.9, "left", 1.0),
                                                              ("Value", "4.7k", -5.3, 10.4, "left", 1.0)]), (0, 1)))
    q = g.part("2N7002", 7.62, 33.02, {"1": "PRG_RST", "2": "GND", "3": "XVF_RST_Q"}, prefix="Q", attach=("1", "3"),
               fields=dict(spec="N-MOSFET 60 V", use="ESP32 pulls XVF3800 RST_N low"),
               fieldpos=[("Reference", nref(g, "Q"), 13.5, 33.0, "left", 1.0), ("Value", "2N7002", 13.5, 34.5, "left", 1.0)])
    tee(g, q["1"], "PRG_RST", (lambda near: vbranch(g, "R", near, (0, 1), "PRG_RST", "GND", "4.7k",
                                                   use="Gate pull-down (off while the ESP32 boots)",
                                                   fieldpos=[("Reference", nref(g, "R"), 2.6, 41.9, "left", 1.0),
                                                             ("Value", "4.7k", 2.6, 43.4, "left", 1.0)]), (0, 1)))
    g.inline(q["3"][0], (0, -1), "R", "XVF_RST_N", "0R", n_near="XVF_RST_Q",
             use="Link: remove to isolate the ESP32 from RST_N",
             fieldpos=[("Reference", nref(g, "R"), 12.5, 21.6, "left", 1.0), ("Value", "0R", 12.5, 23.1, "left", 1.0)])

    g = s.group("ESP32 I2C pull-ups")
    # Were on the host header (old 1x6 J701, removed 2026-11-11). They also serve the XVF3800 bus when
    # the GPIO header (now J701) shunts join the two buses.
    g.R(0, 0, "+3V3", "ESP_I2C_SDA", "4.7k", use="ESP32 I2C SDA pull-up")
    g.R(20.32, 0, "+3V3", "ESP_I2C_SCL", "4.7k", use="ESP32 I2C SCL pull-up")

    g = s.group("GPIO header (J701, 2x12)")
    # Pin 13-14 and 15-16 put the two I2C buses side by side: two jumper shunts join them.
    g.part("Conn_02x12_Odd_Even", 0, 0, {
        "1": "+5V", "2": "+3V3", "3": "+1V8", "4": "GND", "5": "ESP_GPIO1", "6": "ESP_GPIO2",
        "7": "ESP_GPIO4", "8": "ESP_GPIO5", "9": "ESP_GPIO6", "10": "ESP_GPIO7", "11": "ESP_GPIO8",
        "12": "ESP_GPIO9", "13": "ESP_I2C_SDA", "14": "XVF_I2C_SDA", "15": "ESP_I2C_SCL", "16": "XVF_I2C_SCL",
        "17": "XVF_INT_N", "18": "XVF_I2S_DATA1", "19": "XVF_I2S_DATA2", "20": "GND",
        "21": "ESP_UART_TX", "22": "ESP_UART_RX", "23": "+5V", "24": "+3V3"},
        prefix="J", value="GPIO", footprint="Mindspark:PinHeader_2x12_P2.54mm_Vertical_SMD_HCTL_PZ254",
        fields=dict(spec="2.54 mm 2x12 SMD", use="ESP32 GPIO + UART0 + XVF3800 I/O breakout"))
    s.note("Path B (diagram 08): slide SW701 to PROG, the ESP32 holds RST_N low through Q701, writes the W25Q32 with plain SPI (SPI2), reads it back, releases the flash lines, then RST_N.")
    s.note("Each TS5A3166 adds 18-19 pF (off) to its XVF QSPI line (TI SCDS188D). IN threshold 2.0 V at 3.3 V.")
    s.note("J701: shunts on 13-14 and 15-16 join the ESP32 and XVF I2C buses (the 4.7k pull-ups here then serve both). XVF I2C has no pull-ups of its own. 1V8 pin: low current only (shared with the XVF3800). 21/22 = ESP32 UART0 TX/RX (boot log at power-up).")
    return s


# ========================================================================================
# Sheet 8: LED ring
# ========================================================================================
def sheet_ui():
    s = Sheet(8, "led_ring", "LED ring", {"LED_EN": "input", "LED_DATA": "input"},
              "12 x WS2812B-2020 on a switched 5 V rail, data buffered to 5 V")
    g = s.group("LED ring (D801-D812)")
    # DOUT of each LED wires straight to DIN of the next (100 mil apart); rows of six.
    for row in range(2):
        prev = None
        for k in range(6):
            i = row * 6 + k
            x, y = k * 17.78, row * 40.64
            nets = {"3": "LED_D%d" % i, "1": "LED_D%d" % (i + 1) if i < 11 else None, "4": "+5V_LED", "2": "GND"}
            att = []
            if k > 0 or row == 1:
                att.append("3")
            if (k < 5 and i < 11) or i == 5:
                att.append("1")
            res = g.part("WS2812B-2020", x, y, nets, prefix="D", value="WS2812B-2020", attach=tuple(att),
                         fields=dict(spec="WS2812B-2020", use="Ring LED %d" % (i + 1)))
            if prev is not None:
                g.wire(prev, res["3"][0])
            prev = res["1"][0] if "1" in att else None
            if i == 5:
                wrap = res["1"][0]
            if i == 6:
                # Row 1's last DOUT drops into the gap between the rows and runs back to row 2's DIN.
                (dx, dy) = res["3"][0]
                g.path(wrap, (wrap[0] + 2.54, wrap[1]), (wrap[0] + 2.54, 19.05), (dx - 2.54, 19.05),
                       (dx - 2.54, dy), (dx, dy))
                prev = res["1"][0]
            if k == 5 and i < 11:
                pass                                   # row end: DOUT has its own lead + label
    r = Row(g, 0, 76.2)
    for i in range(12):
        r.C("+5V_LED", "GND", "100nF", "16V", spec="X7R", use="LED %d bypass" % (i + 1))
    g = s.group("LED power switch (U801)")
    u = g.part("TPS22918DBVR", 0, 0, {"1": "+5V", "2": "GND", "3": "LED_EN", "4": "LED_CT", "5": "+5V_LED",
                                     "6": "+5V_LED"}, prefix="U", attach=("3", "4"), join=(("6", "5"),),
               fields=dict(spec="2 A load switch", use="LED ring supply, EN from ESP32 GPIO47"))
    tee(g, u["3"], "LED_EN", (lambda near: vbranch(g, "R", near, (0, 1), "LED_EN", "GND", "4.7k",
                                                   use="Off by default",
                                                   fieldpos=[("Reference", nref(g, "R"), -15.8, 8.9, "right", 1.0),
                                                             ("Value", "4.7k", -15.8, 10.4, "right", 1.0)]), (0, 1)))
    (cx, cy), d = u["4"]
    g.path((cx, cy), (cx + 2.54, cy), (cx + 2.54, cy + 2.54))
    vbranch(g, "C", (cx + 2.54, cy + 2.54), (0, 1), "LED_CT", "GND", "1nF", voltage="16V", spec="X7R",
            use="CT: about 2.5 ms rise",
            fieldpos=[("Reference", nref(g, "C"), cx + 5.2, cy + 5.6, "left", 1.0), ("Value", "1nF", cx + 5.2, cy + 7.1, "left", 1.0)])
    r = Row(g, -22.86, 33.02)
    r.C("+5V", "GND", "1uF", "10V", use="Switch input")
    r.C("+5V_LED", "GND", "22uF", "10V", use="Ring bulk")

    g = s.group("Data buffer (U802)")
    u = g.part("SN74AHCT1G125DBVR", 0, 0, {"1": "GND", "2": "LED_DATA", "3": "GND", "4": "LED_DATA_5V",
                                           "5": "+5V_LED"}, prefix="U", attach=("4",),
               fields=dict(spec="Buffer, TTL inputs", use="WS2812 data level shift"))
    g.inline(u["4"][0], (1, 0), "R", "LED_D0", "33R", n_near="LED_DATA_5V", use="Data line series resistor",
             fieldpos=[("Reference", nref(g, "R"), 19.05, -2.2, "center", 1.0), ("Value", "33R", 19.05, 2.2, "center", 1.0)])
    r = Row(g, 33.02, -5.08)
    r.C("+5V_LED", "GND", "100nF", "16V", spec="X7R", use="Buffer bypass")

    s.note("The buffer runs from the switched rail, so the ESP32 must hold LED_DATA low while LED_EN is off. Data from ESP32 GPIO48 (RMT).")
    return s


# ========================================================================================
# LCSC picks (checked 2026-11-10 through the JLCPCB/LCSC part APIs; JLC Basic unless noted).
# Capacitor voltage is the picked part's rating, one step up from the requirement where the
# price is the same (e.g. all 100 nF are the 16 V X7R Basic part).
# ========================================================================================
UR = "UNI-ROYAL"
R_PICKS = {"0R": ("C17168", "0402WGF0000TCE"), "27R": ("C25100", "0402WGF270JTCE"), "33R": ("C25105", "0402WGF330JTCE"),
           "330R": ("C25104", "0402WGF3300TCE"), "680R": ("C25130", "0402WGF6800TCE"), "1k": ("C11702", "0402WGF1001TCE"),
           "2.2k": ("C25879", "0402WGF2201TCE"), "4.7k": ("C25900", "0402WGF4701TCE"), "5.1k": ("C25905", "0402WGF5101TCE"),
           "10k": ("C25744", "0402WGF1002TCE"), "12k": ("C25752", "0402WGF1202TCE"), "22k": ("C25768", "0402WGF2202TCE"),
           "33k": ("C25779", "0402WGF3302TCE"), "51k": ("C25794", "0402WGF5102TCE"), "100k": ("C25741", "0402WGF1003TCE"),
           "1M": ("C26083", "0402WGF1004TCE"), "100R": ("C25076", "0402WGF1000TCE")}
C_PICKS = {"100nF": ("C1525", "CL05B104KO5NNNC", "Samsung", "16V", "X7R"),
           "10uF": ("C19702", "CL10A106KP8NNNC", "Samsung", "10V", "X5R"),
           "1uF": ("C52923", "CL05A105KA5NQNC", "Samsung", "25V", "X5R"),
           "22uF": ("C45783", "CL21A226MAQNNNE", "Samsung", "25V", "X5R"),
           "4.7uF": ("C23733", "CL05A475MP5NRNC", "Samsung", "10V", "X5R"),
           "47uF": ("C96123", "CL31A476MPHNNNE", "Samsung", "10V", "X5R"),
           "1nF": ("C1523", "0402B102K500NT", "FH", "50V", "X7R"),
           "15pF": ("C1548", "0402CG150J500NT", "FH", "50V", "C0G"),
           "22pF": ("C1555", "0402CG220J500NT", "FH", "50V", "C0G")}
OTHER_PICKS = {("LED", "RED"): ("C2286", "KT-0603R", "Hubei KENTO"),
               ("LED", "GREEN"): ("C12624", "KT-0603G", "Hubei KENTO"),
               ("2N7002", "2N7002"): ("C8545", "2N7002", "CJ (Changjiang)"),
               ("Conn_02x12_Odd_Even", "GPIO"): ("C3294470", "PZ254-2-12-S", "HCTL")}


def apply_picks(sheets):
    for s in sheets:
        by_ref = {p["ref"]: p for p in s.parts}
        for g in s.groups:
            for it in g.items:
                if it["kind"] != "symbol" or it["power"]:
                    continue
                f, lib, val = it["fields"], it["lib"], it["value"]
                if lib == "R":
                    code, mpn = R_PICKS[val]
                    f.update(LCSC=code, MPN=mpn, Manufacturer=UR, tolerance="1%", power="62.5mW")
                elif lib == "C":
                    code, mpn, mfr, volt, diel = C_PICKS[val]
                    f.update(LCSC=code, MPN=mpn, Manufacturer=mfr, voltage=volt, spec=diel)
                elif (lib, val) in OTHER_PICKS:
                    code, mpn, mfr = OTHER_PICKS[(lib, val)]
                    f.update(LCSC=code, MPN=mpn, Manufacturer=mfr)
                if it["ref"] in by_ref:
                    by_ref[it["ref"]]["fields"] = f
                # visible rating text follows the picked part
                if "voltage" in it.get("shown", {}) and lib == "C":
                    pass


def rows_done(s):
    """Fields of rows are placed by Row.finish(); make sure they are placed exactly once."""
    for g in s.groups:
        for r in getattr(g, "_all_rows", []):
            pass


def measure_groups(sheets):
    """Export SVG once and return each group's plotted content extent in its local coordinates."""
    import subprocess
    import tempfile
    import measure_boxes as mb
    d = Path(tempfile.mkdtemp(prefix="mindspark-measure-"))
    root = PROJECT_DIR / (PROJECT + ".kicad_sch")
    if not root.exists():
        return {}
    write_root(sheets, mech)
    subprocess.run(["kicad-cli", "sch", "export", "svg", "-o", str(d), str(root)], check=True, capture_output=True)
    out = {}
    for s in sheets:
        svg = d / ("%s-%s.svg" % (PROJECT, s.fname))
        items = mb.parse(svg)
        for gi, g in enumerate(s.groups):
            x0, y0, x1, y1 = g.box
            c = [1e9, 1e9, -1e9, -1e9]
            for colour, w, pts in items:
                if colour == mb.BOX:
                    continue
                for x, y in pts:
                    if x0 < x < x1 and y0 < y < y1:
                        c = [min(c[0], x - w / 2), min(c[1], y - w / 2), max(c[2], x + w / 2), max(c[3], y + w / 2)]
            # heading (box colour) must fit too: keep the box at least as wide as the heading
            from schgen import text_width
            hw = text_width(g.title, 1.524) * 1.08 + 2.54 - 2 * 7.62
            if c[2] - c[0] < hw:
                c[2] = c[0] + hw
            out[(s.fname, gi)] = (c[0] - g.dx, c[1] - g.dy, c[2] - g.dx, c[3] - g.dy)
    items = mb.parse(d / ("%s.svg" % PROJECT))
    out["root"] = {}
    for gi, g in enumerate(write_root.groups):
        x0, y0, x1, y1 = g.box
        c = [1e9, 1e9, -1e9, -1e9]
        for colour, w, pts in items:
            if colour == mb.BOX:
                continue
            for x, y in pts:
                if x0 < x < x1 and y0 < y < y1:
                    c = [min(c[0], x - w / 2), min(c[1], y - w / 2), max(c[2], x + w / 2), max(c[3], y + w / 2)]
        hw = text_width(g.title, 1.524) * 1.08 + 2.54 - 2 * 7.62
        if c[2] - c[0] < hw:
            c[2] = c[0] + hw
        out["root"][gi] = (c[0] - g.dx, c[1] - g.dy, c[2] - g.dx, c[3] - g.dy)
    return out


def mech(g):
    for i in range(4):
        g.part("MountingHole", i * 12.7, 0, {}, prefix="H", value="M2",
               footprint="Mindspark:MountingHole_2.2mm_M2_Pad_Via", fields=dict(use="Mounting hole"))


def main():
    sheets = [sheet_usb_power(), sheet_regulators(), sheet_xvf(), sheet_xvf_periph(), sheet_audio(),
              sheet_esp32(), sheet_link(), sheet_ui()]
    targets = [PROJECT_DIR / (PROJECT + ".kicad_sch")] + [PROJECT_DIR / (s.fname + ".kicad_sch") for s in sheets]
    # Hash guard: refuse to overwrite a file someone saved since the last generation.
    if HASHES.exists() and "--force" not in sys.argv:
        old = json.loads(HASHES.read_text())
        for t in targets:
            if t.exists() and t.name in old and hashlib.sha256(t.read_bytes()).hexdigest() != old[t.name]:
                raise SystemExit("%s was edited since it was generated; not overwriting (use --force)" % t.name)
    apply_picks(sheets)
    for s in sheets:
        write_child(s)
    # Second pass: replace each box's estimated content extent with the extent measured on
    # KiCad's own SVG plot, then re-pack, so padding and gaps are exact (tidy Step 2).
    measured = measure_groups(sheets)
    sheets = [sheet_usb_power(), sheet_regulators(), sheet_xvf(), sheet_xvf_periph(), sheet_audio(),
              sheet_esp32(), sheet_link(), sheet_ui()]
    apply_picks(sheets)
    for s in sheets:
        for gi, g in enumerate(s.groups):
            m = measured.get((s.fname, gi))
            if m:
                g.bb, g.measured = list(m), True
        rows_done(s)
        write_child(s)
        print("%-16s %s  %3d parts  %d boxes" % (s.fname, s.paper, len(s.parts), len(s.groups)))
    root = write_root(sheets, mech, measured.get("root"))
    manifest = {"sheets": {s.fname: {"index": s.index, "paper": s.paper, "pins": s.manifest, "parts": s.parts,
                                     "ports": s.ports} for s in sheets},
                "root": {"pins": root.manifest}}
    (PROJECT_DIR / "verification").mkdir(exist_ok=True)
    (PROJECT_DIR / "verification" / "design-manifest.json").write_text(json.dumps(manifest, indent=1))
    HASHES.write_text(json.dumps({t.name: hashlib.sha256(t.read_bytes()).hexdigest() for t in targets}, indent=1))
    (PROJECT_DIR / "verification" / "tidy-exceptions.json").write_text(
        json.dumps({s.fname: sorted(set(s.exceptions)) for s in sheets}, indent=1))
    print("wrote", len(targets), "schematic files")


if __name__ == "__main__":
    main()
