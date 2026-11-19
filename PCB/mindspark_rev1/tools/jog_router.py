"""A small grid router for power traces: 0/45/90 degree "jog" routing.

Used by tools/power_v2_2026_11_18.py. KiCad's own router can't be scripted here (pcbnew's
Python segfaults), so this does the job for a handful of power connections:

  * one copper layer per call (F.Cu or B.Cu); layer changes are vias placed by the caller;
  * grid of GRID mm; moves in 8 directions, so every segment is 0, 45 or 90 degrees;
  * every change of direction costs extra, so routes come out as long straight runs joined by
    45-degree jogs (the "jog routing" the user asked for), not the shortest diagonal;
  * the route starts on copper the net already has on that layer and ends on the centre of the
    target pad (user's hand edits, 2026-11-18): pad and via centres, track centre lines; the
    grid is aligned on the goal centre and the corners are then nudged so the start lands
    exactly on its centre too, every leg keeping its 0/45/90 direction;
  * after the search the path is pulled tight (no 0.1 mm grid staircases) and runs keep
    SPACING extra room from other copper where there is room; no acute corners;
  * copper of every other net (pads, tracks, arcs, vias, holes) is kept CLEARANCE away, and
    the board edge EDGE away.

Pure Python (no numpy here). Each call only rasterises a window round the start and goal.
"""
import heapq
import math

GRID = 0.1           # mm
CLEARANCE = 0.2      # mm, a little over the 0.15 netclass clearance
EDGE = 0.35          # mm, copper to board edge (rule 0.3)
TURN_COST = 3.0      # extra cost (in grid steps) for each change of direction
MARGIN = 8.0         # mm round the start/goal box that the search may use
SPACING = 0.3        # mm beyond CLEARANCE that the route tries to keep where there is room
MIN_LEG = 0.1        # mm, shortest leg kept after the end fit (no slivers)
NEAR_COST = 0.3      # extra cost per step when right at CLEARANCE (falls to 0 at +SPACING)

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _dist_point_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _inside(px, py, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _dist_point_poly(px, py, poly):
    if _inside(px, py, poly):
        return 0.0
    n = len(poly)
    return min(_dist_point_seg(px, py, *poly[i], *poly[(i + 1) % n]) for i in range(n))


class Shape:
    """A piece of copper: polygon (pad), capsule (track) or circle (via / hole)."""

    def __init__(self, net, layers, poly=None, seg=None, circle=None):
        self.net, self.layers = net, set(layers)
        self.poly, self.seg, self.circle = poly, seg, circle
        if poly:
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            self.box = (min(xs), min(ys), max(xs), max(ys))
        elif seg:
            (ax, ay), (bx, by), w = seg
            self.box = (min(ax, bx) - w / 2, min(ay, by) - w / 2, max(ax, bx) + w / 2, max(ay, by) + w / 2)
        else:
            (cx, cy), r = circle
            self.box = (cx - r, cy - r, cx + r, cy + r)

    def dist(self, px, py):
        """Distance from a point to this copper (0 inside)."""
        if self.poly:
            return _dist_point_poly(px, py, self.poly)
        if self.seg:
            (ax, ay), (bx, by), w = self.seg
            return max(0.0, _dist_point_seg(px, py, ax, ay, bx, by) - w / 2)
        (cx, cy), r = self.circle
        return max(0.0, math.hypot(px - cx, py - cy) - r)


class Router:
    def __init__(self, board_box, shapes):
        self.box = board_box            # (x0, y0, x1, y1) of the board outline
        self.shapes = list(shapes)      # every piece of copper already on the board

    def add(self, shape):
        self.shapes.append(shape)

    # ------------------------------------------------------------------ helpers
    def _others(self, net, layer):
        """Copper of other nets on this layer (the obstacles)."""
        return [s for s in self.shapes
                if s.net != net and layer in s.layers and net not in getattr(s, "exempt", ())]

    def _seg_clearance(self, a, b, obstacles, width):
        """Smallest gap (edge to edge) between a track a-b of this width and the obstacles,
        and the board edge. Sampled every 0.05 mm, which is close enough at these sizes."""
        n = max(1, int(math.dist(a, b) / 0.05))
        bx0, by0 = min(a[0], b[0]) - 1.5, min(a[1], b[1]) - 1.5
        bx1, by1 = max(a[0], b[0]) + 1.5, max(a[1], b[1]) + 1.5
        near = [s for s in obstacles
                if not (s.box[2] < bx0 or s.box[0] > bx1 or s.box[3] < by0 or s.box[1] > by1)]
        best = 9.0
        for k in range(n + 1):
            t = k / n
            x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
            edge = min(x - self.box[0], self.box[2] - x, y - self.box[1], self.box[3] - y) - EDGE + CLEARANCE
            best = min(best, edge - width / 2)
            for s in near:
                best = min(best, s.dist(x, y) - width / 2)
                if best <= 0:
                    return best
        return best

    def _path_clearance(self, pts, obstacles, width):
        return min(self._seg_clearance(a, b, obstacles, width) for a, b in zip(pts, pts[1:]))

    @staticmethod
    def _anchor(shape, near_pt):
        """Where a track should join this copper: pad centre, via centre, or the point on a
        track's centre line closest to near_pt (user's rule: traces end on pad centres)."""
        if shape.poly:
            b = shape.box
            return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        if shape.circle:
            return shape.circle[0]
        (ax, ay), (bx, by), _ = shape.seg
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((near_pt[0] - ax) * dx + (near_pt[1] - ay) * dy) / L2))
        return (ax + t * dx, ay + t * dy)

    @staticmethod
    def _jog(p, q):
        """The ways to join p to q with 0/45/90 legs and at most one 45-degree corner."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        adx, ady = abs(dx), abs(dy)
        if adx < 1e-6 or ady < 1e-6 or abs(adx - ady) < 1e-6:
            return [[p, q]]
        m = min(adx, ady)
        diag = (math.copysign(m, dx), math.copysign(m, dy))
        c1 = (p[0] + diag[0], p[1] + diag[1])                     # 45 first, then straight
        c2 = (q[0] - diag[0], q[1] - diag[1])                     # straight first, then 45
        return [[p, c1, q], [p, c2, q]]

    @staticmethod
    def _turn_ok(u, v):
        """No acute corners: the turn between two legs may be at most 90 degrees."""
        lu, lv = math.hypot(*u), math.hypot(*v)
        if lu < 1e-9 or lv < 1e-9:
            return True
        return (u[0] * v[0] + u[1] * v[1]) / (lu * lv) > -1e-6

    def _straighten(self, pts, obstacles, width):
        """Pull the grid path tight: replace runs of waypoints by one straight leg or one
        straight leg + one 45-degree leg wherever that keeps at least the spacing the grid path
        had (capped at CLEARANCE + SPACING). This removes the small grid staircases."""
        want = CLEARANCE + SPACING
        legs = [self._seg_clearance(a, b, obstacles, width) for a, b in zip(pts, pts[1:])]
        out, i = [pts[0]], 0
        while i < len(pts) - 1:
            for j in range(len(pts) - 1, i, -1):
                need = max(CLEARANCE + 0.01, min(want, min(legs[i:j]) - 1e-6))
                done = False
                for cand in self._jog(pts[i], pts[j]):
                    prev = (out[-1][0] - out[-2][0], out[-1][1] - out[-2][1]) if len(out) > 1 else None
                    first = (cand[1][0] - cand[0][0], cand[1][1] - cand[0][1])
                    last = (cand[-1][0] - cand[-2][0], cand[-1][1] - cand[-2][1])
                    nxt = (pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1]) if j + 1 < len(pts) else None
                    if prev and not self._turn_ok(prev, first):
                        continue
                    if nxt and not self._turn_ok(last, nxt):
                        continue
                    if j == i + 1 and len(cand) == 2:
                        ok = True                                  # the original leg itself
                    else:
                        ok = self._path_clearance(cand, obstacles, width) >= need
                    if ok:
                        out += cand[1:]
                        i, done = j, True
                        break
                if done:
                    break
            else:
                out.append(pts[i + 1])
                i += 1
        return _merge(out)

    def _fit_ends(self, pts, S, E, obstacles, width):
        """Move the corners a little so the path starts exactly on S and ends exactly on E
        (pad / via centres, track centre lines) while every leg keeps its 0/45/90 direction.
        The grid ends are within ~0.07 mm of S and E; the correction is the smallest change of
        leg lengths that closes the gap. Returns None if that is not possible."""
        n = len(pts) - 1
        if n < 1:
            return None
        u = []
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            u.append(((b[0] - a[0]) / L, (b[1] - a[1]) / L, L))
        rx = (E[0] - S[0]) - (pts[-1][0] - pts[0][0])
        ry = (E[1] - S[1]) - (pts[-1][1] - pts[0][1])
        # least-norm delta: d = U^T (U U^T)^-1 r, U = 2 x n matrix of leg directions
        a11 = sum(x * x for x, _, _ in u)
        a12 = sum(x * y for x, y, _ in u)
        a22 = sum(y * y for _, y, _ in u)
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-9:
            # all legs parallel: only a correction along that direction is possible
            ux, uy, _ = u[0]
            if abs(rx * uy - ry * ux) > 1e-4:
                return None
            d = [(rx * ux + ry * uy) / n] * n
        else:
            l1 = (a22 * rx - a12 * ry) / det
            l2 = (-a12 * rx + a11 * ry) / det
            d = [x * l1 + y * l2 for x, y, _ in u]
        lens = [L + dl for (_, _, L), dl in zip(u, d)]
        short = min(range(n), key=lambda k: lens[k])
        if lens[short] < MIN_LEG:
            # a leg would shrink to a sliver: drop it (the later corners shift by its vector,
            # every direction is kept) and fit again, as long as no acute corner appears
            if n == 1:
                return None
            v = (pts[short + 1][0] - pts[short][0], pts[short + 1][1] - pts[short][1])
            rest = pts[:short + 1] + [(p[0] - v[0], p[1] - v[1]) for p in pts[short + 2:]]
            rest = _merge(rest)
            for a, b, c in zip(rest, rest[1:], rest[2:]):
                if not self._turn_ok((b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])):
                    return None
            if len(rest) < 2 or len(rest) - 1 >= n:
                return None
            return self._fit_ends(rest, S, E, obstacles, width)
        out = [S]
        for (x, y, L), ln in zip(u, lens):
            p = out[-1]
            out.append((p[0] + x * ln, p[1] + y * ln))
        out[-1] = E
        if self._path_clearance(out, obstacles, width) < CLEARANCE + 0.01:
            return None
        return out

    # ------------------------------------------------------------------ the router
    def route(self, net, layer, width, goal_poly, start_shapes, extra_starts=()):
        """Route `net` on `layer` from start_shapes (copper already joined to the net's tree;
        the caller keeps that list) plus extra_starts points, into goal_poly.

        User's rules (2026-11-18, from their hand edits):
          * the trace ends on the centre of the goal pad and starts on the centre of a start
            pad or via, or on a track's centre line; the last/first leg is 0/45/90 into it;
          * no grid staircases: the path is pulled tight after the search;
          * stay a little away from other copper where there is room (SPACING).
        Falls back to the old behaviour (any point inside the pads) if the centre is not
        reachable at this width. Returns the list of waypoints, or None."""
        path = self._route(net, layer, width, goal_poly, start_shapes, extra_starts, centres=True)
        if path is None:
            path = self._route(net, layer, width, goal_poly, start_shapes, extra_starts, centres=False)
        return path

    def _route(self, net, layer, width, goal_poly, start_shapes, extra_starts, centres):
        g = GRID
        own = [s for s in start_shapes if layer in s.layers]
        gb = [min(p[0] for p in goal_poly), min(p[1] for p in goal_poly),
              max(p[0] for p in goal_poly), max(p[1] for p in goal_poly)]
        gx, gy = (gb[0] + gb[2]) / 2, (gb[1] + gb[3]) / 2          # goal pad centre
        near = min((s for s in own), key=lambda s: s.dist(gx, gy), default=None)
        if near is None and not extra_starts:
            return None
        pts = [(gx, gy)] + list(extra_starts)
        if near is not None:
            b = near.box
            pts += [(b[0], b[1]), (b[2], b[3])]
        x0 = max(self.box[0], min(p[0] for p in pts) - MARGIN)
        y0 = max(self.box[1], min(p[1] for p in pts) - MARGIN)
        x1 = min(self.box[2], max(p[0] for p in pts) + MARGIN)
        y1 = min(self.box[3], max(p[1] for p in pts) + MARGIN)
        # the grid is aligned on the goal centre, so the route can end exactly on it
        ox = gx - math.ceil((gx - x0) / g) * g
        oy = gy - math.ceil((gy - y0) / g) * g
        W, H = int((x1 - ox) / g) + 2, int((y1 - oy) / g) + 2
        X = lambda i: ox + i * g
        Y = lambda j: oy + j * g
        I = lambda x: int(round((x - ox) / g))
        J = lambda y: int(round((y - oy) / g))
        blocked = bytearray(W * H)
        nearc = [0.0] * (W * H)                                  # 0..1, how close to other copper
        infl = CLEARANCE + width / 2
        soft = infl + SPACING
        for j in range(H):
            for i in range(W):
                x, y = X(i), Y(j)
                if (x < self.box[0] + EDGE + width / 2 or x > self.box[2] - EDGE - width / 2 or
                        y < self.box[1] + EDGE + width / 2 or y > self.box[3] - EDGE - width / 2):
                    blocked[j * W + i] = 1
        others = self._others(net, layer)
        for s in others:
            b = s.box
            if b[2] + soft < x0 or b[0] - soft > x1 or b[3] + soft < y0 or b[1] - soft > y1:
                continue
            ia, ib = max(0, math.floor((b[0] - soft - ox) / g)), min(W - 1, math.ceil((b[2] + soft - ox) / g))
            ja, jb = max(0, math.floor((b[1] - soft - oy) / g)), min(H - 1, math.ceil((b[3] + soft - oy) / g))
            for j in range(ja, jb + 1):
                for i in range(ia, ib + 1):
                    k = j * W + i
                    if blocked[k]:
                        continue
                    d = s.dist(X(i), Y(j))
                    if d < infl:
                        blocked[k] = 1
                    elif d < soft:
                        nearc[k] = max(nearc[k], (soft - d) / SPACING)
        # start cells (and the exact point each one stands for)
        starts = {}
        for s in own:
            b = s.box
            if s.poly is not None and _inside(gx, gy, goal_poly) and s.dist(gx, gy) == 0:
                continue                                  # the goal pad itself is not a start
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            if centres and not s.seg:
                ax, ay = self._anchor(s, (gx, gy))
                c = (I(ax), J(ay))
                if 0 <= c[0] < W and 0 <= c[1] < H and s.dist(X(c[0]), Y(c[1])) == 0:
                    starts.setdefault(c, (ax, ay))
                continue
            ia, ib = max(0, math.floor((b[0] - ox) / g)), min(W - 1, math.ceil((b[2] - ox) / g))
            ja, jb = max(0, math.floor((b[1] - oy) / g)), min(H - 1, math.ceil((b[3] - oy) / g))
            for j in range(ja, jb + 1):
                for i in range(ia, ib + 1):
                    x, y = X(i), Y(j)
                    if s.dist(x, y) != 0:
                        continue
                    if centres and s.seg:
                        (sax, say), (sbx, sby), _ = s.seg
                        if _dist_point_seg(x, y, sax, say, sbx, sby) > 0.75 * g:
                            continue                      # only cells on the track's centre line
                        starts.setdefault((i, j), self._anchor(s, (x, y)))
                    else:
                        starts.setdefault((i, j), (x, y))
        for (px, py) in extra_starts:
            starts.setdefault((I(px), J(py)), (px, py))
        # goal cells
        if centres:
            goal = {(I(gx), J(gy))}
        else:
            goal = {(i, j) for j in range(H) for i in range(W) if _inside(X(i), Y(j), goal_poly)}
            if not goal:
                goal = {(I(gx), J(gy))}
        goal = {c for c in goal if 0 <= c[0] < W and 0 <= c[1] < H and not blocked[c[1] * W + c[0]]}
        starts = {c: p for c, p in starts.items() if 0 <= c[0] < W and 0 <= c[1] < H and not blocked[c[1] * W + c[0]]}
        if not goal or not starts:
            return None
        # A* with a turn penalty and a cost for running close to other copper
        INF = float("inf")
        cost = [INF] * (W * H)
        parent = [-1] * (W * H)
        pdir = [-1] * (W * H)
        tgi, tgj = I(gx), J(gy)
        h = lambda i, j: (max(abs(i - tgi), abs(j - tgj)) + (math.sqrt(2) - 1) * min(abs(i - tgi), abs(j - tgj)))
        heap = []
        for (i, j) in starts:
            cost[j * W + i] = 0.0
            heapq.heappush(heap, (h(i, j), 0.0, i, j))
        done = bytearray(W * H)
        end = None
        while heap:
            f, c, i, j = heapq.heappop(heap)
            k = j * W + i
            if done[k]:
                continue
            done[k] = 1
            if (i, j) in goal:
                end = k
                break
            for d, (di, dj) in enumerate(DIRS):
                ni, nj = i + di, j + dj
                if not (0 <= ni < W and 0 <= nj < H):
                    continue
                nk = nj * W + ni
                if blocked[nk] or done[nk]:
                    continue
                if di and dj and (blocked[j * W + ni] or blocked[nj * W + i]):
                    continue                       # no corner-cutting past an obstacle
                if pdir[k] != -1 and not self._turn_ok(DIRS[pdir[k]], (di, dj)):
                    continue                       # no acute corners
                step = math.sqrt(2) if di and dj else 1.0
                turn = 0.0 if pdir[k] in (-1, d) else TURN_COST
                nc = c + step * (1.0 + NEAR_COST * nearc[nk]) + turn
                if nc < cost[nk]:
                    cost[nk] = nc
                    parent[nk] = k
                    pdir[nk] = d
                    heapq.heappush(heap, (nc + h(ni, nj), nc, ni, nj))
        if end is None:
            return None
        cells = []
        k = end
        while k != -1:
            cells.append((k % W, k // W))
            k = parent[k]
        cells.reverse()
        way = [cells[0]]
        for a, b, c_ in zip(cells, cells[1:], cells[2:]):
            if (b[0] - a[0], b[1] - a[1]) != (c_[0] - b[0], c_[1] - b[1]):
                way.append(b)
        if len(cells) > 1:
            way.append(cells[-1])
        pts = [(X(i), Y(j)) for i, j in way]
        S = starts[cells[0]]
        E = (gx, gy) if centres else pts[-1]
        if len(pts) == 1:
            pts = [S, E] if math.dist(S, E) > 1e-6 else pts
        else:
            pts = self._straighten(pts, others, width)
            fitted = self._fit_ends(pts, S, E, others, width)
            if fitted is None and centres:
                return None                         # caller retries without the centre rule
            pts = fitted or pts
        return [(round(x, 4), round(y, 4)) for x, y in _merge(pts)]


def _merge(pts):
    """Drop repeated points and join consecutive legs that run in the same direction."""
    out = []
    for p in pts:
        if out and math.dist(out[-1], p) < 1e-4:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            u = (b[0] - a[0], b[1] - a[1])
            v = (p[0] - b[0], p[1] - b[1])
            if abs(u[0] * v[1] - u[1] * v[0]) < 1e-6 * max(1e-9, math.hypot(*u) * math.hypot(*v)) \
                    and u[0] * v[0] + u[1] * v[1] > 0:
                out[-1] = p
                continue
        out.append(p)
    return out
