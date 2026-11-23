"""Differential impedance of the XVF main USB pair (pre-order step 4, 2026-11-23).

Usage (needs numpy + scipy, e.g. a scratch venv):
    python tools/usb_impedance_2026_11_23.py

JLC's online calculator could not be driven from here (browser pane hidden), so this solves
the 2D Laplace equation across the pair's cross-section instead (finite differences, 5 um
grid) and reports Zdiff = 2 * Zodd, with Zodd = 1 / (c * sqrt(C * C_air)) per trace in odd mode.

Stackup from the board file (JLC04161H-7628): the pair runs on an outer layer, 1 oz copper
(35 um), over 0.2104 mm of 7628 prepreg (er 4.4) to the reference plane (In1 GND on F.Cu, In2
on B.Cu, same distance). Solder mask 15 um, er 3.8, over the copper and the gaps.
Two cases: plain edge-coupled microstrip, and with the GND pour 0.5 mm beside each line (the
real board: the pour keeps 0.5 mm from every USB track).

Check: the solver also gives a single 50 ohm reference line so the result can be compared
with JLC's published widths for this stackup.
"""
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

E0 = 8.8541878128e-12
C0 = 299792458.0

D = 0.005            # grid step, mm
H = 0.2104           # prepreg 7628 to the reference plane, mm
ER = 4.4
T = 0.035            # 1 oz copper
MASK_T = 0.015
MASK_ER = 3.8
TOP = 1.6            # air above, mm (domain height)
HALF_W = 3.0         # domain half width, mm


def solve(eps, fixed, volt):
    """Laplace with Dirichlet nodes `fixed` (bool) at `volt`; returns energy-based C (per V^2)."""
    ny, nx = eps.shape
    idx = -np.ones((ny, nx), dtype=np.int64)
    free = ~fixed
    idx[free] = np.arange(free.sum())
    rows, cols, vals = [], [], []
    rhs = np.zeros(free.sum())
    diag = np.zeros(free.sum())
    # faces between neighbours: permittivity = mean of the two cells
    for dy, dx in ((0, 1), (1, 0)):
        a = (slice(0, ny - dy), slice(0, nx - dx))
        b = (slice(dy, ny), slice(dx, nx))
        ef = 0.5 * (eps[a] + eps[b])
        ia, ib = idx[a], idx[b]
        va, vb = volt[a], volt[b]
        fa, fb = free[a], free[b]
        # a free, b anything
        m = fa
        np.add.at(diag, ia[m], ef[m])
        mm = m & fb
        rows.append(ia[mm]); cols.append(ib[mm]); vals.append(-ef[mm])
        mf = m & ~fb
        np.add.at(rhs, ia[mf], ef[mf] * vb[mf])
        # b free, a anything
        m = fb
        np.add.at(diag, ib[m], ef[m])
        mm = m & fa
        rows.append(ib[mm]); cols.append(ia[mm]); vals.append(-ef[mm])
        mf = m & ~fa
        np.add.at(rhs, ib[mf], ef[mf] * va[mf])
    n = free.sum()
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    v = volt.copy()
    v[free] = spsolve(A, rhs)
    # energy: 1/2 sum over faces eps_f * dV^2 (dx = dy, so the grid size drops out)
    w = 0.0
    for dy, dx in ((0, 1), (1, 0)):
        a = (slice(0, ny - dy), slice(0, nx - dx))
        b = (slice(dy, ny), slice(dx, nx))
        w += 0.5 * np.sum(0.5 * (eps[a] + eps[b]) * (v[a] - v[b]) ** 2)
    return w * E0          # J/m per (1 V)^2 scale


def geometry(widths_and_volts, gnd_gap=None):
    """Build eps (with and without dielectric), fixed mask and voltages."""
    nx = int(round(2 * HALF_W / D)) + 1
    ny = int(round(TOP / D)) + 1
    x = -HALF_W + D * np.arange(nx)
    y = D * np.arange(ny)
    X, Y = np.meshgrid(x, y)
    eps = np.ones((ny, nx))
    eps[Y < H] = ER
    copper = np.zeros_like(eps, dtype=bool)
    volt = np.zeros_like(eps)
    in_cu = (Y >= H - 1e-9) & (Y <= H + T + 1e-9)
    traces = []
    for x0, x1, vv in widths_and_volts:
        m = in_cu & (X >= x0 - 1e-9) & (X <= x1 + 1e-9)
        copper |= m
        volt[m] = vv
        traces.append((x0, x1))
    if gnd_gap is not None:
        lo = min(t[0] for t in traces) - gnd_gap
        hi = max(t[1] for t in traces) + gnd_gap
        m = in_cu & ((X <= lo) | (X >= hi))
        copper |= m
        traces += [(-HALF_W, lo), (hi, HALF_W)]
    # solder mask: a 15 um layer on the board surface and over every copper item
    mask = (Y >= H) & (Y < H + MASK_T)
    for x0, x1 in traces:
        mask |= (Y >= H) & (Y < H + T + MASK_T) & (X >= x0 - MASK_T) & (X <= x1 + MASK_T)
    eps[mask & ~copper] = MASK_ER
    fixed = copper.copy()
    fixed[0, :] = True                   # reference plane at y = 0
    volt[0, :] = 0.0
    # side walls far away at 0 V, top open enough
    fixed[:, 0] = fixed[:, -1] = True
    fixed[-1, :] = True
    return eps, fixed, volt


def z_odd_pair(w, s, gnd_gap=None):
    tr = [(-s / 2 - w, -s / 2, 1.0), (s / 2, s / 2 + w, -1.0)]
    eps, fixed, volt = geometry(tr, gnd_gap)
    c = solve(eps, fixed, volt)                 # total energy with +-1 V = C_odd per trace
    c_air = solve(np.ones_like(eps), fixed, volt)
    z_odd = 1 / (C0 * math.sqrt(c * c_air))
    return 2 * z_odd


def z_single(w):
    eps, fixed, volt = geometry([(-w / 2, w / 2, 1.0)])
    c = 2 * solve(eps, fixed, volt)             # W = C V^2 / 2
    c_air = 2 * solve(np.ones_like(eps), fixed, volt)
    return 1 / (C0 * math.sqrt(c * c_air))


if __name__ == "__main__":
    print(f"reference single line 0.35 mm: {z_single(0.35):.1f} ohm")
    for w, s in ((0.25, 0.15), (0.20, 0.15), (0.18, 0.15), (0.20, 0.20)):
        print(f"pair w {w:.2f} / s {s:.2f}: microstrip {z_odd_pair(w, s):.1f} ohm, "
              f"with GND pour 0.5 mm away {z_odd_pair(w, s, 0.5):.1f} ohm")
