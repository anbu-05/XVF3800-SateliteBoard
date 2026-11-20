"""Checks on the built mic routes (run from PCB/mindspark_rev1):  check_routes.py BOARD
  * closest centre spacing between different mic lines on the same layer (approved: >= 0.45 mm;
    the fan-out at the XVF3800's 0.4 mm pin pitch is the one place below it)
  * track edge to courtyard of L201, L202, U503, J501 (approved: >= 2.5 mm)"""
import math
import sys
sys.path.insert(0, "tools")
from place_tidy import Part  # noqa: E402
from sexpr import parse, children  # noqa: E402
import mic_route_2026_11_20 as m  # noqa: E402


def pd(p, s, e):
    dx, dy = e[0] - s[0], e[1] - s[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / L))
    return math.hypot(p[0] - s[0] - t * dx, p[1] - s[1] - t * dy)


def sd(a, b, c, d):
    return min(pd(a, c, d), pd(b, c, d), pd(c, a, b), pd(d, a, b))


segs = [(n, l, a, b) for n, l, p in m.TRACKS for a, b in zip(p, p[1:])]
worst = {}
for i, (n1, l1, a, b) in enumerate(segs):
    for (n2, l2, c, d) in segs[i + 1:]:
        if n1 == n2 or l1 != l2 or {n1, n2} & {"/MIC_CLK", "Net-(R501-Pad1)"}:
            continue
        x = sd(a, b, c, d)
        k = tuple(sorted((n1, n2)))
        if x < worst.get(k, (9,))[0]:
            worst[k] = (x, l1, a, b)
print("closest spacing between mic lines (centre to centre):")
for k, v in sorted(worst.items(), key=lambda kv: kv[1][0]):
    if v[0] < 1.0:
        print(f"  {v[0]:.3f} mm  {k[0]} / {k[1]}  ({v[1]} near {tuple(round(t, 2) for t in v[2])})")
r = parse(open(sys.argv[1]).read())
P = {Part(f).ref: Part(f) for f in children(r, "footprint")}
print("track edge to courtyard:")
for ref in m.KEEP_AWAY:
    poly = P[ref].courtyard()
    best = (1e9, None)
    for net, layer, pts in m.TRACKS:
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(math.dist(a, b) / 0.1))
            for k in range(n + 1):
                p = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                for s, e in zip(poly, poly[1:] + poly[:1]):
                    dd = pd(p, s, e) - m.W / 2
                    if dd < best[0]:
                        best = (dd, net)
    print(f"  {ref}: {best[0]:.2f} mm ({best[1]})")
