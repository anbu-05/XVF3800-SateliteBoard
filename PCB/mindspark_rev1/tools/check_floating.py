#!/usr/bin/env python3
"""Two wiring checks on the generated schematic (kicad-schematic-tidy candidates C5/C6).

1. Floating passives: R, C, L and ferrites whose wired cluster never reaches a component pin
(IC, connector, switch, LED, transistor...) or a hierarchical port. Such a passive is only joined to
the circuit by net labels or power symbols. Parts with every pin on a rail (decoupling caps, rail
filters) are exempt, as are
the exceptions listed in EXCEPT with their reason.

Works on the generator's groups (local coordinates; wires never cross boxes).
2. Repeated labels: a net named by labels at two or more places inside one box. Parts in the same
box are wired together; labels are for leaving the box. Listed exceptions carry their reason.

Usage: python3 -I tools/check_floating.py   -> exit 1 if anything is found.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_schematic as b  # noqa: E402
from schgen import LIB, POWER_NETS, tf  # noqa: E402

PASSIVE = {"R", "C", "SRP4020TA-2R2M", "BLM15AG601SN1D"}

# ref -> reason. Keep this list short; each entry needs a clear reason.
EXCEPT = {}

# (sheet, net) -> reason, for nets that stay labelled twice in one box.
EXCEPT_LABELS = {
    ("usb_power", "USBM_CC1"): "connector to ESD by label: both CC lines carry an Rd to GND; wiring them across needs a crossing",
    ("usb_power", "USBM_CC2"): "as USBM_CC1",
    ("usb_power", "USBE_CC1"): "as USBM_CC1",
    ("usb_power", "USBE_CC2"): "as USBM_CC1",
    ("xvf3800", "MCLK_LOOP"): "pin 14 to pin 41 on opposite sides of the 60-pin XVF3800; a wire would run round the chip past its labelled pins",
}


def pin_points(it):
    x, y = it["p"]
    out = []
    for p in LIB.pins(it["lib"]):
        dx, dy = tf(p["x"], p["y"], it["rot"])
        out.append((round(x + dx, 4), round(y + dy, 4)))
    return out


def on_segment(p, a, c):
    if a[0] == c[0] == p[0]:
        return min(a[1], c[1]) <= p[1] <= max(a[1], c[1])
    if a[1] == c[1] == p[1]:
        return min(a[0], c[0]) <= p[0] <= max(a[0], c[0])
    return False


def check_group(g):
    wires = [(tuple(map(lambda v: round(v, 4), it["a"])), tuple(map(lambda v: round(v, 4), it["b"])))
             for it in g.items if it["kind"] == "wire"]
    # Things that sit on points: (kind, owner, point)
    things = []
    for it in g.items:
        if it["kind"] == "symbol":
            kind = "power" if it["power"] else ("passive" if it["lib"] in PASSIVE else "component")
            for pt in pin_points(it):
                things.append((kind, it, pt))
        elif it["kind"] == "hlabel":
            things.append(("port", it, tuple(round(v, 4) for v in it["p"])))
    # Union-find over wires; points join a wire if they lie on it.
    parent = list(range(len(wires)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, (a, c) in enumerate(wires):
        for j, (d, e) in enumerate(wires[:i]):
            if on_segment(a, d, e) or on_segment(c, d, e) or on_segment(d, a, c) or on_segment(e, a, c):
                parent[find(i)] = find(j)

    def nodes_at(pt):
        """Electrical node id of a point: its wire cluster, else the bare point (pin touching pin)."""
        ws = {find(i) for i, (a, c) in enumerate(wires) if on_segment(pt, a, c)}
        return ("w", min(ws)) if ws else ("p", pt)

    by_node = {}
    for kind, it, pt in things:
        by_node.setdefault(nodes_at(pt), []).append((kind, it))
    owner_nodes = {}
    for kind, it, pt in things:
        owner_nodes.setdefault(id(it), set()).add(nodes_at(pt))

    floating = []
    for it in g.items:
        if it["kind"] != "symbol" or it["power"] or it["lib"] not in PASSIVE:
            continue
        nets = set(it["pins"].values())
        if nets <= POWER_NETS:
            continue                                  # decoupling cap or rail filter: every pin on a rail
        # Walk through passives only; stop when a component pin or port is reached.
        seen, todo, ok = {id(it)}, [it], False
        while todo and not ok:
            cur = todo.pop()
            for node in owner_nodes[id(cur)]:
                for kind, other in by_node.get(node, []):
                    if other is cur:
                        continue
                    if kind in ("component", "port"):
                        ok = True
                    elif kind == "passive" and id(other) not in seen:
                        seen.add(id(other))
                        todo.append(other)
        if not ok:
            floating.append(it)
    return floating


def main():
    found = 0
    for f in (b.sheet_usb_power, b.sheet_regulators, b.sheet_xvf, b.sheet_xvf_periph, b.sheet_audio,
              b.sheet_esp32, b.sheet_link, b.sheet_ui):
        s = f()
        for g in s.groups:
            for it in check_group(g):
                if it["ref"] in EXCEPT:
                    print("  exception %-6s %s" % (it["ref"], EXCEPT[it["ref"]]))
                    continue
                found += 1
                print("FLOATING %-14s %-6s %-6s %-40s nets %s" % (s.fname, it["ref"], it["value"], g.title,
                                                                 sorted(set(it["pins"].values()))))
    labels = 0
    for f in (b.sheet_usb_power, b.sheet_regulators, b.sheet_xvf, b.sheet_xvf_periph, b.sheet_audio,
              b.sheet_esp32, b.sheet_link, b.sheet_ui):
        s = f()
        for g in s.groups:
            seen = {}
            for it in g.items:
                if it["kind"] in ("label", "hlabel"):
                    seen.setdefault(it["net"], []).append(it["p"])
            for net, pts in seen.items():
                if len(pts) < 2:
                    continue
                if (s.fname, net) in EXCEPT_LABELS:
                    print("  exception %-14s %-12s %s" % (s.fname, net, EXCEPT_LABELS[(s.fname, net)]))
                    continue
                labels += 1
                print("REPEATED %-14s %-16s %d labels in box '%s'" % (s.fname, net, len(pts), g.title))
    found += labels
    print("FAIL" if found else "PASS", "(%d floating passives / repeated labels)" % found)
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
