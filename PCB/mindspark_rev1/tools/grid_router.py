"""Two-layer grid router for the slow signals (2026-11-22, group 3 onward).

The jog router (tools/jog_router.py) routes one layer at a time. Long slow-control nets on this
board cross several walls on both layers (the +5V_LED ring on the bottom layer, the ESP32 USB
pair and the mic legs on the top layer), so they need several layer changes. This router
searches both layers at once:

  * The board is a 0.1 mm grid per copper layer (F.Cu, B.Cu). Every piece of copper already on
    the board is drawn into it, grown by clearance + half the track width, labelled with its
    net. A cell is free for net N if nothing covers it, or only net N's own copper does.
  * A second pair of grids is grown by clearance + via radius: a via may go where both layers
    are free in that grid.
  * A* over (layer, x, y) with 8 directions (0/45/90 degree runs), a cost for each turn (so runs
    stay straight), a cost for each via (so layer changes are rare), and a small cost near
    other copper (so routes keep a little room where there is some).
  * The cell path is reduced to its corner points; each layer change becomes a via.

Plain Python (no numpy here): grids are flat bytearrays/arrays, one cell per 0.1 mm.
"""
import heapq
import math
from array import array

LAYERS = ("F.Cu", "B.Cu")
G = 0.1               # grid pitch, mm
CLR = 0.15            # clearance to other nets' copper, mm
HOLE_CLR = 0.2        # clearance to non-plated holes (mic sound ports), mm
EDGE = 0.35           # copper to board edge, mm
TURN = 3.0            # cost of a 45 degree change of direction (in grid steps)
VIA_COST = 100.0      # cost of a layer change (in grid steps, i.e. 10 mm of track)
SAFETY = 0.04         # extra keep-away: a diagonal step between free cell centres can pass a
                      # little closer to a corner than the cells themselves are
NEAR = 0.3            # extra room the route likes to keep, mm
NEAR_COST = 0.4       # cost per step taken inside that room

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _inside(px, py, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            c = not c
    return c


def shape_dist(sh, px, py):
    """Distance from a point to a jog_router Shape's copper edge (0 inside)."""
    if sh.poly:
        if _inside(px, py, sh.poly):
            return 0.0
        p = sh.poly
        return min(_seg_dist(px, py, *p[i], *p[(i + 1) % len(p)]) for i in range(len(p)))
    if sh.seg:
        (ax, ay), (bx, by), w = sh.seg
        return max(0.0, _seg_dist(px, py, ax, ay, bx, by) - w / 2)
    (cx, cy), r = sh.circle
    return max(0.0, math.hypot(px - cx, py - cy) - r)


class GridRouter:
    def __init__(self, box, shapes, width=0.15, via_d=0.45, skip=None):
        """box: board outline (x0, y0, x1, y1); shapes: jog_router Shapes already on the board;
        skip(shape) -> True for shapes to leave out (e.g. keep-outs that do not apply)."""
        self.x0, self.y0 = box[0], box[1]
        self.nx = int(round((box[2] - box[0]) / G)) + 1
        self.ny = int(round((box[3] - box[1]) / G)) + 1
        self.w, self.vr = width, via_d / 2
        self.ids = {}                                       # net name -> small integer (1...)
        n = self.nx * self.ny
        # per layer: track grid, via grid (net id, 0 free, 65535 = several nets) and a "near" flag
        self.trk = {L: array("H", bytes(2 * n)) for L in LAYERS}
        self.via = {L: array("H", bytes(2 * n)) for L in LAYERS}
        self.near = {L: bytearray(n) for L in LAYERS}
        self._edges(box)
        for sh in shapes:
            if skip and skip(sh):
                continue
            self.add(sh)

    # ------------------------------------------------------------ grid bookkeeping
    def nid(self, net):
        if net not in self.ids:
            self.ids[net] = len(self.ids) + 1
        return self.ids[net]

    def cell(self, x, y):
        return int(round((x - self.x0) / G)), int(round((y - self.y0) / G))

    def xy(self, i, j):
        return self.x0 + i * G, self.y0 + j * G

    def _mark(self, grid, idx, v):
        old = grid[idx]
        if old == 0:
            grid[idx] = v
        elif old != v:
            grid[idx] = 65535

    def _edges(self, box):
        """Cells too close to the board edge are blocked for everyone."""
        m_t = EDGE + self.w / 2
        m_v = EDGE + self.vr
        for j in range(self.ny):
            for i in range(self.nx):
                x, y = self.xy(i, j)
                d = min(x - box[0], box[2] - x, y - box[1], box[3] - y)
                k = j * self.nx + i
                for L in LAYERS:
                    if d < m_t:
                        self.trk[L][k] = 65535
                    if d < m_v:
                        self.via[L][k] = 65535

    def add(self, sh):
        """Draw a piece of copper into the grids (grown by clearance)."""
        layers = [L for L in LAYERS if L in sh.layers]
        if not layers:
            return
        hole = sh.net == "~hole"
        v = 65535 if hole or sh.net.startswith("~") else self.nid(sh.net)
        clr = HOLE_CLR if hole else CLR
        g_t = clr + self.w / 2 + SAFETY         # a track centre must stay this far away
        g_v = clr + self.vr + SAFETY            # a via centre must stay this far away
        g_n = g_t + NEAR
        i0, j0 = self.cell(sh.box[0] - g_n, sh.box[1] - g_n)
        i1, j1 = self.cell(sh.box[2] + g_n, sh.box[3] + g_n)
        i0, j0 = max(0, i0), max(0, j0)
        i1, j1 = min(self.nx - 1, i1), min(self.ny - 1, j1)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                x, y = self.xy(i, j)
                d = shape_dist(sh, x, y)
                if d >= g_n:
                    continue
                k = j * self.nx + i
                for L in layers:
                    if d < g_t - 1e-9:
                        self._mark(self.trk[L], k, v)
                    if d < g_v - 1e-9:
                        self._mark(self.via[L], k, v)
                    self.near[L][k] = 1

    # ------------------------------------------------------------ search
    def route(self, net, starts, goal, goal_layers, max_nodes=8_000_000):
        """starts: [(layer, (x, y))], goal: (x, y) reached on any of goal_layers.
        Returns [(layer, [(x, y), ...]), ...] runs with a via between consecutive runs, or None."""
        nid = self.nid(net)
        nx = self.nx
        trk, via, near = self.trk, self.via, self.near
        gi, gj = self.cell(*goal)

        def free_t(L, k):
            v = trk[L][k]
            return v == 0 or v == nid

        def free_v(k):
            return all(via[L][k] in (0, nid) for L in LAYERS)

        def h(i, j):
            dx, dy = abs(i - gi), abs(j - gj)
            return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)

        best = {}
        heap = []
        for L, p in starts:
            i, j = self.cell(*p)
            for d in range(8):
                key = (L, i, j, d)
                best[key] = 0.0
                heapq.heappush(heap, (h(i, j), 0.0, L, i, j, d, None))
        parent = {}
        n = 0
        while heap:
            f, g, L, i, j, d, par = heapq.heappop(heap)
            key = (L, i, j, d)
            if key in parent:
                continue
            parent[key] = par
            n += 1
            if n > max_nodes:
                return None
            if i == gi and j == gj and L in goal_layers:
                return self._unwind(parent, key)
            k = j * nx + i
            # moves on this layer
            for nd, (dx, dy) in enumerate(DIRS):
                ii, jj = i + dx, j + dy
                if not (0 <= ii < nx and 0 <= jj < self.ny):
                    continue
                kk = jj * nx + ii
                if not free_t(L, kk) and not (ii == gi and jj == gj):
                    continue
                if dx and dy:                       # diagonal: both side cells must be free too
                    if not (free_t(L, j * nx + ii) or free_t(L, jj * nx + i)):
                        continue
                turn = min((nd - d) % 8, (d - nd) % 8)
                if turn > 2:                        # no sharper than 90 degrees
                    continue
                step = math.sqrt(2) if dx and dy else 1.0
                cost = g + step + TURN * turn + (NEAR_COST if near[L][kk] else 0.0)
                nk = (L, ii, jj, nd)
                if cost < best.get(nk, 1e18):
                    best[nk] = cost
                    heapq.heappush(heap, (cost + h(ii, jj), cost, L, ii, jj, nd, key))
            # layer change (a via here)
            if free_v(k):
                L2 = "B.Cu" if L == "F.Cu" else "F.Cu"
                nk = (L2, i, j, d)
                cost = g + VIA_COST
                if cost < best.get(nk, 1e18):
                    best[nk] = cost
                    heapq.heappush(heap, (cost + h(i, j), cost, L2, i, j, d, key))
        return None

    def _unwind(self, parent, key):
        cells = []
        while key is not None:
            L, i, j, d = key
            cells.append((L, i, j))
            key = parent[key]
        cells.reverse()
        runs = []
        for L, i, j in cells:
            if not runs or runs[-1][0] != L:
                runs.append((L, []))
            pts = runs[-1][1]
            if not pts or pts[-1] != (i, j):
                pts.append((i, j))
        out = []
        for L, pts in runs:
            corners = [pts[0]]
            for a, b, c in zip(pts, pts[1:], pts[2:]):
                if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                    corners.append(b)
            if len(pts) > 1:
                corners.append(pts[-1])
            out.append((L, [self.xy(i, j) for i, j in corners]))
        return out
