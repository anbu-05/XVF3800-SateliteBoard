#!/usr/bin/env python3
"""Check the generated schematic against what the generator meant to draw.

1. Exports KiCad's XML netlist and full ERC with kicad-cli.
2. Builds the intended net partition from verification/design-manifest.json (every pin of every
   part and the net it should be on) and compares it with KiCad's partition, ignoring net names:
   no missing pins, no merged nets, no split nets, no-connect pins alone.
3. Prints an ERC summary.

Usage: python3 -I PCB/mindspark_rev1/tools/verify_schematic.py [netlist.xml erc.json]
Exit status 1 if connectivity differs or ERC has errors.
"""
import collections
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
SCH = PROJ / "mindspark_rev1.kicad_sch"
VER = PROJ / "verification"


def export(netlist, erc):
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", str(netlist), str(SCH)],
                   check=True, capture_output=True)
    subprocess.run(["kicad-cli", "sch", "erc", "--severity-all", "--format", "json", "-o", str(erc), str(SCH)],
                   check=True, capture_output=True)


def intended():
    m = json.loads((VER / "design-manifest.json").read_text())
    nets, nc = collections.defaultdict(set), set()
    for sheet in list(m["sheets"].values()) + [m["root"]]:
        for ref, pins in sheet["pins"].items():
            for pin, key in pins.items():
                if key is None:
                    nc.add((ref, pin))
                else:
                    nets[key].add((ref, pin))
    return nets, nc


def actual(netlist):
    r = ET.parse(netlist).getroot()
    nets = {}
    for n in r.iter("net"):
        nets[n.get("name")] = {(x.get("ref"), x.get("pin")) for x in n.iter("node")}
    return nets


def main():
    netlist = Path(sys.argv[1]) if len(sys.argv) > 1 else VER / "netlist.xml"
    erc = Path(sys.argv[2]) if len(sys.argv) > 2 else VER / "erc.json"
    if len(sys.argv) == 1:
        export(netlist, erc)
    want, nc = intended()
    have = actual(netlist)
    where = {node: name for name, nodes in have.items() for node in nodes}
    problems = []
    for key, nodes in sorted(want.items()):
        names = {where.get(n) for n in nodes}
        if None in names:
            problems.append("%s: pins missing from netlist: %s" % (key, sorted(n for n in nodes if n not in where)))
        names.discard(None)
        if len(names) > 1:
            problems.append("%s: split across %s" % (key, sorted(names)))
        for name in names:
            extra = have[name] - nodes
            if extra:
                problems.append("%s (KiCad %s): also contains %s" % (key, name, sorted(extra)))
    for n in sorted(nc):
        name = where.get(n)
        if name and len(have[name]) > 1:
            problems.append("no-connect pin %s is on net %s with %s" % (n, name, sorted(have[name] - {n})))
    pins_total = sum(len(v) for v in want.values()) + len(nc)
    print("intended: %d nets, %d connected pins, %d no-connect pins" % (len(want), pins_total - len(nc), len(nc)))
    print("KiCad:    %d nets, %d pin nodes" % (len(have), sum(len(v) for v in have.values())))
    print("connectivity:", "MATCH" if not problems else "%d problems" % len(problems))
    for p in problems[:40]:
        print("  ", p)
    d = json.loads(erc.read_text())
    count = collections.Counter()
    for s in d["sheets"]:
        for v in s["violations"]:
            count[(v["severity"], v["type"])] += 1
            print("  ERC %-7s %-28s %s %s" % (v["severity"], v["type"], s["path"],
                                              "; ".join(i["description"] for i in v["items"])[:150]))
    print("ERC:", dict(count) or "no violations")
    errors = sum(n for (sev, _), n in count.items() if sev == "error")
    sys.exit(1 if problems or errors else 0)


if __name__ == "__main__":
    main()
