# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 4 step 6: cold-formed lipped C and Z sections FROM THEIR GEOMETRY — gross properties and elastic buckling
(finite strip). No supplier catalogue yet (user decision 2026-11-08); a supplier table overrides any value (cfs_checks).

Geometry (the profile name Z200x65x20x2.0 = depth H, flange B, lip D, thickness t, all out-to-out, mm):
    centreline h = H − t, b = B − t, d = D − t/2; lips at 90° to the flanges; Z: the flanges point opposite ways,
    C: the same way; corners rounded on the centreline radius r + t/2 with the inside radius r = R_INSIDE × t
    (the names carry no radius: R_INSIDE = 1.0 is Claude's assumption, listed on every result; a supplier value
    replaces it).
Properties (thin-walled line integrals along the centreline, the corners as chords — exact for the polyline):
    A, centroid, Ix (about the horizontal geometric axis through the centroid), Iz (about the vertical one), Ixz,
    principal I1 / I2, Sx = Ix / (H / 2) (the gross modulus at the extreme fibre, DSM's Sf; bending about the
    GEOMETRIC axis — "restrained bending", the purlin / girt case where the sheeting holds the section), J = Σ b t³ / 3,
    the shear centre (the pole for which the sectorial products vanish) and Cw = ∫ ω² dA (ω normalised).
    Independent check: sectionproperties (a finite-element solid section with the true corners) in the tests.
Finite strip (simply supported ends, one half-wave of length a; Cheung's method, written here from the theory):
    membrane  u = U(x) sin(πy/a), v = V(x) cos(πy/a), U, V linear across the strip; plane stress
    bending   w = W(x) sin(πy/a), W cubic (Hermite: w, θ = dw/dx at each edge); Kirchhoff plate
    geometric the longitudinal stress σ(x) (compression +, linear across the strip) on the three slopes ∂u/∂y, ∂v/∂y,
              ∂w/∂y
    strain energies integrated by 5-point Gauss across the strip, exactly in y (∫sin² = ∫cos² = a/2)
    (Ke − λ Kg) d = 0, the smallest positive λ: the load factor on the reference stress at that half-wavelength.
    Reference stresses: bending σ = Fy (z − zc) / (H / 2) (top in compression; λ My = Mcr), compression σ = Fy (λ Py = Pcr).
    Signature curve over a = 15 … 30 000 mm: the FIRST minimum = local (Mcrl / Pcrl), the SECOND = distortional
    (Mcrd / Pcrd); global (Mcre / Pcre) = the curve AT the member's unbraced length (K = 1, Cb = 1; at that length the
    curve is the lowest mode there, so a distortional mode lower than the global one is taken — conservative). Below
    the curve's peak after the distortional minimum (a_global_from) the lowest mode is local / distortional, and the
    global mode — falling with length — lies above the peak value: there the curve AT THE PEAK is used, a lower bound.
    If a second minimum is not found the distortional value is NOT invented: the result says so and the check that
    needs it reports ratio = inf.
    Independent checks (tests): a flat plate with both edges supported → k = 4.00, one edge free → k → 0.425 (closed
    forms); a long C column → the closed-form flexural / flexural-torsional buckling load from the properties.
Units: mm, N, MPa. E = 29 500 ksi (AISI S100-16 A3.1, NOT AISC's 29 000), ν = 0.3.
VERIFIED False for everything here until the tests' independent checks are reviewed (they pass; the review is open).
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize_scalar

KSI = 6.894757293168361               # MPa per ksi (exact)
E_CFS = 29500.0 * KSI                 # 203 395 MPa
NU = 0.30
R_INSIDE = 1.0                        # inside bend radius / t — Claude's assumption (the names carry no radius)
LENGTHS = tuple(float(v) for v in np.logspace(math.log10(15.0), math.log10(30000.0), 90))
VERIFIED = {"properties": False, "finite_strip": False, "mode_split": False}
ASSUMPTIONS = (
    f"inside bend radius = {R_INSIDE:g} t (the profile name carries no radius; a supplier table replaces it)",
    "lips at 90 degrees to the flanges; both flanges the same width",
    "bending about the geometric (horizontal) axis — restrained bending, the sheeting holds the section",
    "finite strip: simply supported ends, one half-wave; local = first minimum, distortional = second minimum of the "
    "signature curve; global = the curve at the unbraced length (K = 1, Cb = 1)",
)

_NAME = re.compile(r"^([CZ])\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)$")


def parse_name(name: str) -> dict:
    m = _NAME.match(name.strip())
    if not m:
        raise ValueError(f"{name!r} is not a lipped C or Z name (e.g. Z200x65x20x2.0)")
    return {"kind": m[1].upper(), "H": float(m[2]), "B": float(m[3]), "D": float(m[4]), "t": float(m[5])}


# ----------------------------------------------------------------------------------------------- geometry

def _unit(p, q):
    dx, dz = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dz)
    return dx / L, dz / L


def _line(p, q, n):
    return [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n) for k in range(1, n + 1)]


def centreline(kind: str, H: float, B: float, D: float, t: float, r: float | None = None,
               n_web: int = 10, n_flange: int = 4, n_lip: int = 2, n_corner: int = 4) -> list[tuple[float, float]]:
    """Centreline nodes (x, z) from the bottom lip's tip to the top lip's tip; z up, the web on x = 0."""
    r = R_INSIDE * t if r is None else r
    h, b, d = H - t, B - t, D - t / 2
    s = 1.0 if kind == "C" else -1.0
    pts = [(s * b, d), (s * b, 0.0), (0.0, 0.0), (0.0, h), (b, h), (b, h - d)]
    rc = r + t / 2 if r > 0 else 0.0
    if d - rc <= 0 or b - 2 * rc <= 0 or h - 2 * rc <= 0:
        raise ValueError(f"{kind}{H:g}x{B:g}x{D:g}x{t:g}: the corners (radius {r:g}) do not fit the flats")
    ndiv = [n_lip, n_flange, n_web, n_flange, n_lip]
    nodes = [pts[0]]
    for i in range(1, 5):
        P = pts[i]
        u1, u2 = _unit(pts[i - 1], P), _unit(P, pts[i + 1])
        if rc == 0:
            nodes += _line(nodes[-1], P, ndiv[i - 1])
            continue
        T1 = (P[0] - rc * u1[0], P[1] - rc * u1[1])
        T2 = (P[0] + rc * u2[0], P[1] + rc * u2[1])
        C = (T1[0] + rc * u2[0], T1[1] + rc * u2[1])
        nodes += _line(nodes[-1], T1, ndiv[i - 1])
        a1 = math.atan2(T1[1] - C[1], T1[0] - C[0])
        a2 = math.atan2(T2[1] - C[1], T2[0] - C[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        nodes += [(C[0] + rc * math.cos(a1 + da * k / n_corner), C[1] + rc * math.sin(a1 + da * k / n_corner)) for k in range(1, n_corner + 1)]
    nodes += _line(nodes[-1], pts[5], ndiv[4])
    return nodes


# ----------------------------------------------------------------------------------------------- properties

def properties(nodes, t: float, H: float) -> dict:
    """Gross thin-walled properties of an open single-branch centreline (mm)."""
    P = np.asarray(nodes, dtype=float)
    p1, p2 = P[:-1], P[1:]
    L = np.hypot(*(p2 - p1).T)
    A = float(L.sum() * t)
    xc = float((L * (p1[:, 0] + p2[:, 0]) / 2).sum() * t / A)
    zc = float((L * (p1[:, 1] + p2[:, 1]) / 2).sum() * t / A)
    X, Z = P[:, 0] - xc, P[:, 1] - zc
    x1, x2, z1, z2 = X[:-1], X[1:], Z[:-1], Z[1:]
    Ix = float(t * (L * (z1 * z1 + z1 * z2 + z2 * z2) / 3).sum())
    Iz = float(t * (L * (x1 * x1 + x1 * x2 + x2 * x2) / 3).sum())
    Ixz = float(t * (L * (2 * x1 * z1 + x1 * z2 + x2 * z1 + 2 * x2 * z2) / 6).sum())
    J = float((L * t ** 3 / 3).sum())
    # sectorial coordinate about the centroid: dω = x dz − z dx
    w = np.concatenate([[0.0], np.cumsum(x1 * z2 - x2 * z1)])
    w1, w2 = w[:-1], w[1:]
    Iwz = float(t * (L * (2 * w1 * z1 + w1 * z2 + w2 * z1 + 2 * w2 * z2) / 6).sum())
    Iwx = float(t * (L * (2 * w1 * x1 + w1 * x2 + w2 * x1 + 2 * w2 * x2) / 6).sum())
    # the pole S (dx, dz from the centroid) with ∫ω_S z = ∫ω_S x = 0, ω_S = ω − dx z + dz x + c
    dx, dz = np.linalg.solve(np.array([[Ix, -Ixz], [Ixz, -Iz]]), np.array([Iwz, Iwx]))
    ws = w - dx * Z + dz * X
    ws = ws - float(t * (L * (ws[:-1] + ws[1:]) / 2).sum()) / A
    Cw = float(t * (L * (ws[:-1] ** 2 + ws[:-1] * ws[1:] + ws[1:] ** 2) / 3).sum())
    avg, dif = (Ix + Iz) / 2, (Ix - Iz) / 2
    R = math.hypot(dif, Ixz)
    c = max(float(Z.max()), float(-Z.min())) + t / 2
    return {"A": A, "xc": xc, "zc": zc, "Ix": Ix, "Iz": Iz, "Ixz": Ixz, "I1": avg + R, "I2": avg - R,
            "principal_angle_deg": math.degrees(0.5 * math.atan2(-2 * Ixz, Ix - Iz)),
            "Sx": Ix / c, "c": c, "J": J, "Cw": Cw, "xs": float(dx), "zs": float(dz),
            "x0": float(-dx), "ro": math.sqrt(Ix / A + Iz / A + dx * dx + dz * dz)}


# ----------------------------------------------------------------------------------------------- finite strip

_GP, _GW = np.polynomial.legendre.leggauss(5)
_GP, _GW = (_GP + 1) / 2, _GW / 2                      # on 0..1


def _strip(b, t, a, T1, T2, E, nu):
    """Local Ke, Kg (8 × 8) of one strip; DOF [u1 v1 w1 θ1 u2 v2 w2 θ2]."""
    k = math.pi / a
    Dm = E / (1 - nu * nu) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    Db = Dm * t ** 3 / 12
    Ke = np.zeros((8, 8))
    Kg = np.zeros((8, 8))
    for xi, gw in zip(_GP, _GW):
        N = np.array([1 - xi, xi])
        dN = np.array([-1.0, 1.0]) / b
        H = np.array([1 - 3 * xi ** 2 + 2 * xi ** 3, b * (xi - 2 * xi ** 2 + xi ** 3), 3 * xi ** 2 - 2 * xi ** 3, b * (-xi ** 2 + xi ** 3)])
        dH = np.array([-6 * xi + 6 * xi ** 2, b * (1 - 4 * xi + 3 * xi ** 2), 6 * xi - 6 * xi ** 2, b * (-2 * xi + 3 * xi ** 2)]) / b
        d2H = np.array([-6 + 12 * xi, b * (-4 + 6 * xi), 6 - 12 * xi, b * (-2 + 6 * xi)]) / b ** 2
        Nu, Nv, Nw = np.zeros(8), np.zeros(8), np.zeros(8)
        dNu, dNv, dNw, d2Nw = np.zeros(8), np.zeros(8), np.zeros(8), np.zeros(8)
        Nu[[0, 4]], dNu[[0, 4]] = N, dN
        Nv[[1, 5]], dNv[[1, 5]] = N, dN
        Nw[[2, 3, 6, 7]], dNw[[2, 3, 6, 7]], d2Nw[[2, 3, 6, 7]] = H, dH, d2H
        Bm = np.vstack([dNu, -k * Nv, k * Nu + dNv])
        Bb = np.vstack([-d2Nw, k * k * Nw, 2 * k * dNw])
        s = T1 * (1 - xi) + T2 * xi
        f = gw * b * a / 2
        Ke += f * (t * Bm.T @ Dm @ Bm + Bb.T @ Db @ Bb)
        Kg += f * s * t * k * k * (np.outer(Nu, Nu) + np.outer(Nv, Nv) + np.outer(Nw, Nw))
    return Ke, Kg


def _assemble(nodes, t, a, stress, E=E_CFS, nu=NU):
    n = len(nodes)
    K = np.zeros((4 * n, 4 * n))
    G = np.zeros((4 * n, 4 * n))
    for i in range(n - 1):
        (xi_, zi), (xj, zj) = nodes[i], nodes[i + 1]
        b = math.hypot(xj - xi_, zj - zi)
        cx, cz = (xj - xi_) / b, (zj - zi) / b
        ke, kg = _strip(b, t, a, stress[i], stress[i + 1], E, nu)
        R1 = np.array([[cx, 0, cz, 0], [0, 1, 0, 0], [-cz, 0, cx, 0], [0, 0, 0, 1]])   # local = R1 · global [X Y Z Θ]
        R = np.zeros((8, 8))
        R[:4, :4], R[4:, 4:] = R1, R1
        idx = list(range(4 * i, 4 * i + 8))
        K[np.ix_(idx, idx)] += R.T @ ke @ R
        G[np.ix_(idx, idx)] += R.T @ kg @ R
    return K, G


def load_factor(nodes, t, a, stress, fixed_w=()) -> float:
    """Smallest positive λ at half-wavelength a (inf if none). fixed_w: global DOF indices held at zero (4 i + 0..3 = X Y Z Θ of node i)."""
    K, G = _assemble(nodes, t, a, stress)
    keep = [i for i in range(K.shape[0]) if i not in set(fixed_w)]
    K, G = K[np.ix_(keep, keep)], G[np.ix_(keep, keep)]
    mu = eigh(G, K, eigvals_only=True, subset_by_index=[K.shape[0] - 1, K.shape[0] - 1])[0]
    return 1.0 / mu if mu > 0 else math.inf


def signature(nodes, t, stress, lengths=LENGTHS, fixed=()) -> list[tuple[float, float]]:
    return [(a, load_factor(nodes, t, a, stress, fixed)) for a in lengths]


def minima(nodes, t, stress, curve, fixed=()) -> list[tuple[float, float]]:
    """Refined local minima (a, λ) of a signature curve, in order of a."""
    out = []
    for i in range(1, len(curve) - 1):
        if curve[i][1] < curve[i - 1][1] and curve[i][1] <= curve[i + 1][1]:
            lo, hi = math.log(curve[i - 1][0]), math.log(curve[i + 1][0])
            r = minimize_scalar(lambda la: load_factor(nodes, t, math.exp(la), stress, fixed), bounds=(lo, hi), method="bounded",
                                options={"xatol": 1e-4})
            out.append((math.exp(r.x), float(r.fun)))
    return out


# ----------------------------------------------------------------------------------------------- the section

@lru_cache(maxsize=64)
def cfs_section(name: str, Fy: float, r: float | None = None) -> dict:
    """Properties and elastic buckling of one profile at one Fy (cached). Moments N·mm, forces N."""
    g = parse_name(name)
    nodes = centreline(g["kind"], g["H"], g["B"], g["D"], g["t"], r)
    t = g["t"]
    p = properties(nodes, t, g["H"])
    My, Py = p["Sx"] * Fy, p["A"] * Fy
    sb = [Fy * (z - p["zc"]) / (g["H"] / 2) for _, z in nodes]
    sc = [Fy] * len(nodes)
    out = {"name": name, **g, "r_inside": R_INSIDE * t if r is None else r, "Fy": Fy, "E": E_CFS, "props": p, "My": My, "Py": Py,
           "nodes": len(nodes), "assumptions": list(ASSUMPTIONS), "VERIFIED": dict(VERIFIED)}
    for key, st, ref in (("bending", sb, My), ("compression", sc, Py)):
        curve = signature(nodes, t, st)
        mins = minima(nodes, t, st, curve)
        loc = mins[0] if mins else None
        dist = mins[1] if len(mins) > 1 else None
        last = (dist or loc or (curve[0][0], 0.0))[0]
        tail = [c for c in curve if c[0] > last]
        a_peak = max(tail, key=lambda c: c[1])[0] if tail else last
        out[key] = {"curve": [(round(a, 2), round(l, 5)) for a, l in curve], "a_global_from": round(a_peak, 1),
                    "local": {"a": round(loc[0], 1), "factor": loc[1], "value": loc[1] * ref} if loc else None,
                    "distortional": {"a": round(dist[0], 1), "factor": dist[1], "value": dist[1] * ref} if dist else None,
                    "note": None if dist else "the signature curve shows no second minimum: distortional buckling NOT identified"}
    out["_nodes"] = tuple(nodes)
    out["_sb"], out["_sc"] = tuple(sb), tuple(sc)
    return out


@lru_cache(maxsize=512)
def _global(name: str, Fy: float, r: float | None, key: str, L: float) -> float:
    s = cfs_section(name, Fy, r)
    st = s["_sb"] if key == "bending" else s["_sc"]
    a = max(L, s[key]["a_global_from"])        # below the peak the curve is a local / distortional mode: the global
    return load_factor(list(s["_nodes"]), s["t"], a, list(st)) * (s["My"] if key == "bending" else s["Py"])   # one is above it


def Mcre(name: str, Fy: float, Lb: float, r: float | None = None) -> float:
    """Global (lateral-torsional) elastic buckling moment at unbraced length Lb, N·mm (K = 1, Cb = 1)."""
    return _global(name, Fy, r, "bending", round(float(Lb), 1))


def Pcre(name: str, Fy: float, L: float, r: float | None = None) -> float:
    """Global (flexural / flexural-torsional) elastic buckling load at length L, N (K = 1 about every axis)."""
    return _global(name, Fy, r, "compression", round(float(L), 1))
