"""JLC placement check (2026-11-23). Run from PCB/mindspark_rev1 with the easyeda2kicad venv:
    ~/.local/venvs/easyeda2kicad/bin/python tools/jlc_placement_check_2026_11_23.py [REF ...]

JLC's preview convention (worked out from the user's screenshots): top parts = JLC's EasyEDA
footprint turned CCW by the CPL angle; bottom parts = mirrored (x -> -x), turned by MINUS the
CPL angle. Fixes go into ROT_FIX / POS_FIX in jlc_export_2026_11_23.py.

Per part: place JLC's footprint as JLC reads the current CPL, match pads whose number is
unique on both sides, and report the mean miss (CPL x/y, mm) and the worst pad after removing it."""
import sys, math, csv, json, os, collections
sys.path.insert(0, "tools")
import sexpr
from place_tidy import to_board
FAB = "fab/JLCPCB_rev1/assembly/"
lcsc = {}
for r in csv.DictReader(open(FAB + "mindspark_rev1_BOM_JLC.csv")):
    for d in r["Designator"].split(","):
        lcsc[d.strip()] = r["LCSC Part #"]
root = sexpr.parse(open("mindspark_rev1.kicad_pcb").read())
ours = {}
for fp in sexpr.children(root, "footprint"):
    ref = [p[2] for p in sexpr.children(fp, "property") if p[1] == "Reference"][0]
    at = sexpr.child(fp, "at"); fx, fy = float(at[1]), float(at[2]); rot = float(at[3]) if len(at) > 3 else 0
    d = collections.defaultdict(list)
    for pd in sexpr.children(fp, "pad"):
        pa = sexpr.child(pd, "at"); x, y = to_board(fx, fy, rot, float(pa[1]), float(pa[2]))
        d[str(pd[1])].append((x, -y))
    ours[ref] = d
# JLC raw pads (need per-number counts): refetch shapes from cache only has means; count via raw fetch if needed
from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
import time
raw = {}
def jlc_raw(code):
    if code not in raw:
        for w in (0, 5, 20, 40):
            time.sleep(w); d = EasyedaApi().get_cad_data_of_component(lcsc_id=code)
            if d: break
        pk = d["packageDetail"]["dataStr"]; ox, oy = pk["head"]["x"], pk["head"]["y"]
        dd = collections.defaultdict(list)
        for s in pk["shape"]:
            if s.startswith("PAD~"):
                f = s.split("~"); dd[f[8]].append(((float(f[2]) - ox) * 0.254, -(float(f[3]) - oy) * 0.254))
        raw[code] = dd; time.sleep(1)
    return raw[code]
only = sys.argv[1:]
for r in csv.DictReader(open(FAB + "mindspark_rev1_CPL_JLC.csv")):
    ref = r["Designator"]
    if only and ref not in only: continue
    if ref[0] in "CR" and ref[1].isdigit() or ref.startswith("FB"): continue
    jp = jlc_raw(lcsc[ref]); op = ours[ref]
    mid = (float(r["Mid X"][:-2]), float(r["Mid Y"][:-2])); rot = float(r["Rotation"]); bottom = r["Layer"] == "Bottom"
    a = math.radians(-rot if bottom else rot)
    def pl(x, y):
        if bottom: x = -x
        return (mid[0] + x * math.cos(a) - y * math.sin(a), mid[1] + x * math.sin(a) + y * math.cos(a))
    common = [k for k in jp if k in op and len(jp[k]) == 1 and len(op[k]) == 1]
    if not common:
        print(ref, "no unique pads"); continue
    dx = sum(op[k][0][0] - pl(*jp[k][0])[0] for k in common) / len(common)
    dy = sum(op[k][0][1] - pl(*jp[k][0])[1] for k in common) / len(common)
    before = max(math.dist(pl(*jp[k][0]), op[k][0]) for k in common)
    after = max(math.dist((pl(*jp[k][0])[0] + dx, pl(*jp[k][0])[1] + dy), op[k][0]) for k in common)
    flag = "SHIFT" if math.hypot(dx, dy) > 0.05 else ""
    flag += " BAD" if after > 0.15 else ""   # SOT-23 lead-span differences (~0.2) are harmless
    print(f"{ref:6} {lcsc[ref]:10} {r['Layer']:6} rot {rot:4g} n {len(common):2d} miss ({dx:+.3f},{dy:+.3f}) worst {before:.3f} -> {after:.3f} {flag}")
