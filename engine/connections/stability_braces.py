# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5c: flange braces, sag rods and ridge ties as standard-detail joints. NOT FOR ISSUE. SI: mm, kN, MPa.

The user's decisions (2026-11-15, step 5c: 1a–6a, 7b, 8a (as corrected), 9a, 10a):
    FLANGE BRACES (L50 × 5 from the frame's inner flange to a purlin / girt, 45°; a PAIR at interior frames, one at the
    end frames):
        force       AISC 360-16 Appendix 6.3.2a point bracing, at each brace point in EVERY LRFD combination of the frame
                    line: Prb = 0.02 Mr Cd / ho (A-6-7), Mr = the moment with the INNER flange in compression (M < 0 by the
                    sign rule M + = outer / top flange in compression; a wind column: |M|, both wind directions), ho = d −
                    (tf_top + tf_bot) / 2 at the point, Cd = 2 for the brace point nearest an inflection point of that
                    combination, else 1.
        stiffness   βbr = 10 Mr Cd / (φ Lbr ho), φ 0.75 (A-6-8), Lbr = the longer of the two adjacent inner-flange segments
                    (the brace points of the member and its ends). Provided (Claude's simple check, VERIFIED False — user
                    7a(3) / 4a): the braces axially, n × E A cos²α / L (α from the lateral direction), IN SERIES with the
                    purlin / girt cleat bending in its own plane, 3 E I / y_c³ (I = t W³ / 12, y_c = the bolt centroid
                    height); the purlin axially rigid; bolt slip NEGLECTED (snug-tight bolts slip — stated).
        brace       per brace P = Prb / (n cos α) (a pair shares, 2a); compression AISC E5(a) (pyaisc360 single-angle
                    effective slenderness, connected through one leg, L = the model length) with E3; local buckling of
                    the leg checked nonslender (Table B4.1a, b / t ≤ 0.45 √(E / Fy)); tension 0.9 Fy Ag and 0.75 Fu Ae with
                    Ae = the connected leg's net area (b − d0) t (one bolt: Table D3.1 does not cover it — conservative,
                    stated). Section without root fillets (A = t (2b − t)).
                    E5 only with bolts_per_end ≥ 2 (its condition "at least two bolts or welded"); with ONE bolt per end
                    (the default — the model gives no count) E5 does not apply (user review 2026-11-15): the angle under
                    eccentric axial load by H2, the force on the bolt gauge line (gauge 28 mm setting) eccentric about
                    both principal axes, Lc = the full length (angle_eccentric).
        springs     (user review 2026-11-15) the springs in series: the braces; the web local bending (none: the brace lies in the
                    web plane — the model's geometry is checked, else NOT EVALUATED); the cleat; the purlin / girt axially
                    to the nearest braced-bay frame line (gable girts: to the wall end), E A / L.
        slip        (user 2026-11-15) the hole clearance is a ONE-TIME slip, not a spring: an added initial imperfection,
                    the required brace force × (1 + slip / Δo), Δo = the SHORTER adjacent unbraced segment at the brace
                    point / 500 (user 2026-11-15; βbr keeps the longer, Lbr), slip 2 mm (setting) — applied to every
                    brace force check (H2, bolts, bearing) and to the force into the cleat; the stiffness is unchanged.
        bolts       M12 8.8 per end (bolts_per_end), threads included: shear J3.6; bearing on the 5 mm leg AISC J3.10 (lc =
                    end_distance − d0 / 2); on the 2 mm purlin / girt web AISI S100-16 J3.3.1 / J3.1 (VERIFIED False), e
                    = the hole's distance to the purlin's flange along the brace / sin 45° (conservative). The FRAME-SIDE
                    end (clip / flange hole) is not detailed in the model → NOT EVALUATED, the point reads PARTIAL.
        cleats      the point's lateral force Prb (the largest over the combinations) goes along the purlin into its cleat
                    at that frame: the 5a cleats are re-run with it (both signs, every combination: an envelope).
    SAG RODS (RD12, through the purlin webs, one piece per purlin gap) and RIDGE TIES (RD12 across the apex):
        force       the down-slope component of each roof line's gravity load (tan θ × D, C, Lr of the Phase 4 line — the
                    normal components), the line as a continuous beam about its weak axis on the frames AND the sag-rod
                    rows (the same beam solver, laps at 2 EI); its reactions at a row accumulate UP the slope from the eave
                    strut to the ridge (no credit for the eave strut: conservative). A rod piece above line k carries the
                    sum of lines 1..k; the ridge tie (horizontal) the whole slope × cos θ, the larger slope. Combinations:
                    the gravity parts of the Phase 4 roof combinations (1.4D, 1.2D + 1.6Lr, 1.2D + 0.5Lr, 0.9D).
        checks      threads AISC J3.6 / Table J3.2 φ 0.75 × 0.75 Fu Ab, body D2-1 0.9 Fy Ab, the washer pulled through
                    the web: φ 0.75 × 0.6 Fu × (4 × side) × t (a square plate washer 40 × 40 × 4 — user default, VERIFIED
                    False; Claude's punching rule as step 5b).
    Status: DESIGNED / FAILS (fixes) / NOT EVALUATED; any row not evaluated → PARTIAL (never DESIGNED).
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

from bimsteelauto_connections.bolts import bolt_shear_capacity
from pyaisc360.chapter_e import AngleConfig, flexural_buckling_stress_E3, single_angle_effective_slenderness
from pyaisc360.chapter_f import Mcr_F10_principal
from pyaisc360.chapter_h import combined_stress_ratio

from ..design.cfs_checks import COMBOS_ROOF, building_lines, tied_rows
from ..design.cfs_section import cfs_section
from ..design.inputs import plate_strength
from ..peb.bracing import INTO_SECONDARY
from ..peb.secondary import cf_dims
from .cleats import (FAILS_AISI, IN, KSI, _host_at, _line_key, aisi_bolt_bearing, aisi_only, building_cleats, gauge_for,
                     hole_strength, line_reactions)

BANNER = "NOT FOR ISSUE — flange braces, sag rods, ridge ties (Phase 5 step 5c); Claude's rules and AISI J3 VERIFIED False"
DESIGNED, FAILS, NOT_EVALUATED, PARTIAL = "DESIGNED", "FAILS", "NOT EVALUATED", "PARTIAL"
E_STEEL = 200000.0
PHI_STIFF = 0.75
VERIFIED = {"brace_support_springs": False, "e5_one_bolt": False, "one_bolt_Ae": False, "aisi_j3": False,
            "sag_accumulation": False, "plate_washer": False, "punching_rule": False, "frame_side_end": False}
FRAME_END_NOTE = ("the flange brace's FRAME-SIDE end (a clip on the web / a hole in the inner flange) is not detailed in the "
                  "model: NOT EVALUATED")
FIXES = {"brace": "a larger angle (L60×6) or 2 bolts per end (E5)", "stiffness": "the smallest spring governs (see "
         "the stiffness record): bolt slip -> pretensioned / slip-critical bolts, fitted holes or welded brace ends; "
         "purlin axial -> a brace node / strut nearer; else a stiffer brace", "bolt": "2 bolts per end or M16", "web": "a thicker purlin / girt web or a washer under head and nut",
         "rod": "a larger rod (RD16)", "washer": "a larger / thicker plate washer"}


@dataclass
class StabilitySettings:
    """Every default of step 5c — editable per job, listed on each result."""
    brace_fraction: float = 0.02         # Prb = 0.02 Mr Cd / ho (App. 6 A-6-7)
    bolt_grade: str = "8.8"
    threads: str = "N"
    bolts_per_end: int = 1               # the model gives no count; E5 wants ≥ 2 (flagged)
    end_distance: float = 25.0           # bolt to the angle's end, mm (setting, VERIFIED False)
    gauge: float = 28.0                  # bolt gauge line from the heel in the connected leg, mm (setting, VERIFIED False)
    merge_tol: float = 150.0             # brace points closer than this to a member end / another point merge (user 2026-11-16)
    gauge_L60: float = 35.0              # bolt gauge for the L60x6 fix option, mm (setting, VERIFIED False)
    slip: float = 2.0                    # one-time bolt slip = the hole clearance (M12 in a 14 mm hole), mm — an added
                                         # initial imperfection: Prb × (1 + slip / Δo), Δo = Lbr / 500 (user 2026-11-15)
    web_washers: bool = False            # AISI mf: 1.00 with washers under head and nut, else 0.75
    plate_washer: float = 40.0           # sag rod / ridge tie square plate washer side, mm (user default)
    plate_washer_t: float = 4.0

    def check(self) -> "StabilitySettings":
        if self.threads not in ("N", "X"):
            raise ValueError("threads: N or X")
        if not (isinstance(self.bolts_per_end, int) and self.bolts_per_end >= 1):
            raise ValueError("bolts_per_end must be a whole number ≥ 1")
        for k in ("brace_fraction", "end_distance", "plate_washer", "plate_washer_t"):
            v = getattr(self, k)
            if not (isinstance(v, (int, float)) and v > 0):
                raise ValueError(f"{k} must be > 0")
        return self


# ------------------------------------------------------------------------------------------------- the angle

def angle_props(b: float, t: float) -> dict:
    """An equal-leg angle without root fillets: A, the centroid from the heel, ra (geometric axis parallel to a leg) and
    rz (minor principal axis), mm."""
    A = t * (2 * b - t)
    xb = (b * b + b * t - t * t) / (2 * (2 * b - t))
    Ix = t * b ** 3 / 3 + (b - t) * t ** 3 / 3 - A * xb ** 2
    Ixy = b * t * (b / 2 - xb) * (t / 2 - xb) + (b - t) * t * (t / 2 - xb) * (t + (b - t) / 2 - xb)
    Iz = Ix - abs(Ixy)
    return {"A": A, "xbar": xb, "Ix": Ix, "Ixy": Ixy, "ra": math.sqrt(Ix / A), "rz": math.sqrt(Iz / A)}


def angle_compression(b: float, t: float, L: float, Fy: float) -> dict:
    """φPn, kN: E5(a) effective slenderness (connected through one leg), E3 on it; the leg's b / t against 0.45 √(E/Fy)."""
    ap = angle_props(b, t)
    cfg = AngleConfig(L=L / IN, ra=ap["ra"] / IN, rz=ap["rz"] / IN, b_long=b / IN, b_short=b / IN)
    lam = single_angle_effective_slenderness(cfg)
    Fcr, Fe = flexural_buckling_stress_E3(lam, E_STEEL / KSI, Fy / KSI)
    slender = b / t > 0.45 * math.sqrt(E_STEEL / Fy)
    return {"phiPn": 0.9 * Fcr * KSI * ap["A"] / 1000.0, "Lc_r": lam, "L_ra": L / ap["ra"], "Fcr": Fcr * KSI,
            "slender_leg": slender, "A": ap["A"]}


def angle_tension(b: float, t: float, d0: float, Fy: float, Fu: float) -> float:
    """φPn, kN: min(0.9 Fy Ag, 0.75 Fu (b − d0) t) — the connected leg's net area only (one bolt: conservative)."""
    A = t * (2 * b - t)
    return min(0.9 * Fy * A, 0.75 * Fu * (b - d0) * t) / 1000.0


def angle_eccentric(b: float, t: float, L: float, Fy: float, P: float, gauge: float) -> dict:
    """A single angle bolted through ONE leg by ONE bolt (E5 does not apply): AISC 360-16 H2 at the force P (kN, +
    compression, − tension) applied on the bolt gauge line, eccentric to the centroid about BOTH principal axes.
    The force acts at the gauge g from the heel on the connected leg's contact face: (dx, dy) = (g − x̄, −x̄) from the
    centroid; principal axes of the equal-leg angle at 45°: w = (dx − dy)/√2 (the arm for bending about the minor axis
    z), z = (dx + dy)/√2 (the arm about the major axis w). Compression: Fca = 0.9 Fcr (E3, Lc = L about rz, K 1);
    moments amplified by B1 = 1 / (1 − P / Pe) about each axis (Cm 1). Bending: minor axis F10-1 (1.5 My, the leg compact);
    major axis min(1.5 My, F10-2 / F10-3 LTB with Mcr F10-4, βw 0, Cb 1, Lb = L). Section moduli to the farthest corner.
    Tension: Fta = 0.9 Fy, no amplification. pyaisc360: H2-1 (combined_stress_ratio), F10-4 (Mcr_F10_principal), E3."""
    ap = angle_props(b, t)
    A, xb, Ix, Ixy = ap["A"], ap["xbar"], ap["Ix"], ap["Ixy"]
    Iz, Iw = Ix - abs(Ixy), Ix + abs(Ixy)
    r2 = math.sqrt(2.0)
    corners = [(0, 0), (b, 0), (b, t), (t, t), (t, b), (0, b)]
    cw = max(abs(((x - xb) - (y - xb)) / r2) for x, y in corners)
    cz = max(abs(((x - xb) + (y - xb)) / r2) for x, y in corners)
    dx, dy = gauge - xb, -xb
    ew, ez = abs(dx - dy) / r2, abs(dx + dy) / r2
    Sz, Sw = Iz / cw, Iw / cz
    rz = math.sqrt(Iz / A)
    Mnz = 1.5 * Fy * Sz
    Myw = Fy * Sw
    Mcr = Mcr_F10_principal(1.0, E_STEEL / KSI, A / IN ** 2, rz / IN, t / IN, L / IN, 0.0) * KSI * IN ** 3
    Mnw = min((1.92 - 1.17 * math.sqrt(Myw / Mcr)) * Myw, 1.5 * Myw) if Myw / Mcr <= 1.0 else (0.92 - 0.17 * Mcr / Myw) * Mcr
    Pn = abs(P) * 1000.0
    if P >= 0:
        Fcr, _ = flexural_buckling_stress_E3(L / rz, E_STEEL / KSI, Fy / KSI)
        Fa = 0.9 * Fcr * KSI
        B1z = 1.0 / (1.0 - Pn / (math.pi ** 2 * E_STEEL * Iz / L ** 2)) if Pn < math.pi ** 2 * E_STEEL * Iz / L ** 2 else math.inf
        B1w = 1.0 / (1.0 - Pn / (math.pi ** 2 * E_STEEL * Iw / L ** 2))
    else:
        Fa, B1z, B1w = 0.9 * Fy, 1.0, 1.0
    if not math.isfinite(B1z):
        return {"U": math.inf, "B1z": B1z, "note": "P above the minor-axis Euler load"}
    r = combined_stress_ratio(Pn / A / KSI, Fa / KSI, frbw=B1w * Pn * ez / Sw / KSI, Fcbw=0.9 * Mnw / Sw / KSI,
                              frbz=B1z * Pn * ew / Sz / KSI, Fcbz=0.9 * Mnz / Sz / KSI)
    return {"U": r.ratio, "terms": dict(r.terms), "e_w": ew, "e_z": ez, "Sz": Sz, "Sw": Sw, "Mnz": Mnz, "Mnw": Mnw,
            "Fa": Fa, "B1z": B1z, "B1w": B1w, "Lc_rz": L / rz}


def slip_factor(slip: float, Lbr: float) -> float:
    """The one-time bolt slip as an added initial imperfection (engineering judgement from the AISC 360-16 App. 6
    commentary, VERIFIED False — user 2026-11-15): the brace force scales with the total displacement, × (1 + slip / Δo),
    Δo = Lbr / 500 (the App. 6 initial out-of-straightness)."""
    return 1.0 + slip / (Lbr / 500.0)


def stiffness_provided(n: int, A: float, L: float, cos_a: float, t_cleat: float, W: float, y_c: float,
                       k_secondary: float = math.inf) -> dict:
    """kN/mm, the springs in series (step 5c review): the braces n × E A cos²α / L; the purlin / girt web local bending —
    none, the brace force lies in the web plane (checked on the model by the caller); the cleat's in-plane bending
    3 E (t W³ / 12) / y_c³; the purlin / girt axially out to where the bracing holds it, E A_p / L_p (k_secondary). The
    bolt slip is NOT a spring (a one-time slip): it amplifies the brace force instead (slip_factor)."""
    kb = n * E_STEEL * A * cos_a ** 2 / L / 1000.0
    kc = 3 * E_STEEL * (t_cleat * W ** 3 / 12.0) / y_c ** 3 / 1000.0
    springs = {"braces": kb, "web local bending": math.inf, "cleat": kc, "purlin axial": k_secondary}
    inv = sum(0.0 if not math.isfinite(v) else (math.inf if v <= 0 else 1.0 / v) for v in springs.values())
    return {**springs, "system": (1.0 / inv) if inv > 0 else math.inf}


def point_demand(Mr: float, Cd: float, ho: float, Lbr: float, fraction: float = 0.02) -> dict:
    """App. 6: Prb (kN) = fraction × Mr Cd / ho; βbr (kN/mm) = 10 Mr Cd / (0.75 Lbr ho), Mr kN·m, ho / Lbr mm."""
    return {"Prb": fraction * Mr * 1000.0 * Cd / ho, "beta": 10.0 * Mr * 1e6 * Cd / (PHI_STIFF * Lbr * ho) / 1000.0}


def inflections(rows: list[tuple], tol: float = 1e-6) -> list[float]:
    """x where M CHANGES SIGN (double curvature) between consecutive non-zero (x, M) rows (linear). A zero moment at a
    pinned end, with one sign on the member, is not an inflection point."""
    nz = [(float(x), float(m)) for x, m in rows if abs(m) > tol]
    return [x0 + (x1 - x0) * m0 / (m0 - m1) for (x0, m0), (x1, m1) in zip(nz, nz[1:]) if m0 * m1 < 0]


def cd_factors(points: list[float], rows: list[tuple]) -> dict:
    """{brace point s: Cd}: 2 for the point nearest each inflection point, else 1."""
    cd = {s: 1.0 for s in points}
    for xi in inflections(rows):
        if points:
            cd[min(points, key=lambda s: abs(s - xi))] = 2.0
    return cd


def _segments(points: list[float], ends: tuple[float, float], tol: float = 0.0) -> dict:
    """{s: [the adjacent segments]} over the brace points and the member's ends; a neighbour closer than tol MERGES with s
    (user 2026-11-16: 150 mm) — the segment beyond it is used instead; with no neighbour beyond tol on a side, that side
    has no segment."""
    ps = sorted(set([ends[0], ends[1]] + list(points)))
    out = {}
    for s in points:
        lefts = [p for p in ps if p < s - max(tol, 1e-9)]
        rights = [p for p in ps if p > s + max(tol, 1e-9)]
        segs = ([s - max(lefts)] if lefts else []) + ([min(rights) - s] if rights else [])
        out[s] = segs or [max(s - ends[0], ends[1] - s)]
    return out


def merged_points(points: list[float], ends: tuple[float, float], tol: float) -> list[dict]:
    """The geometry warnings (for the step 7 clash check): brace points within tol of a member end or another point."""
    ps = sorted(set([ends[0], ends[1]] + list(points)))
    return [{"s": round(s, 1), "near": round(p, 1), "distance": round(abs(p - s), 1),
             "with": "member end" if p in ends else "brace point"}
            for s in points for p in ps if p != s and abs(p - s) < tol and (p in ends or p > s)]


def lbr_short_of(points: list[float], ends: tuple[float, float], tol: float = 0.0) -> dict:
    """{s: the SHORTER adjacent segment} — the slip imperfection's Δo = this / 500 (user 2026-11-15 / -16)."""
    return {s: min(v) for s, v in _segments(points, ends, tol).items()}


def lbr_of(points: list[float], ends: tuple[float, float], tol: float = 0.0) -> dict:
    """{s: the longer adjacent segment} over the brace points and the member's ends."""
    return {s: max(v) for s, v in _segments(points, ends, tol).items()}


def _interp(rows: list[tuple], s: float) -> float:
    if s <= rows[0][0]:
        return rows[0][1]
    for (x0, m0), (x1, m1) in zip(rows, rows[1:]):
        if x0 <= s <= x1:
            return m0 + (m1 - m0) * ((s - x0) / (x1 - x0) if x1 > x0 else 0.0)
    return rows[-1][1]


# ------------------------------------------------------------------------------------------------- rods

def rod_rows(T: float, d: float, Fy: float, Fu: float, t_web: float, Fu_web: float, side: float) -> list[tuple]:
    Ab = math.pi * d * d / 4.0
    th = 0.75 * 0.75 * Fu * Ab / 1000.0
    body = 0.9 * Fy * Ab / 1000.0
    punch = 0.75 * 0.6 * Fu_web * 4 * side * t_web / 1000.0
    return [("rod", "rod threads", "AISC 360-16 J3.6, Table J3.2", T, th, T / th),
            ("rod", "rod body yield", "AISC 360-16 D2-1", T, body, T / body),
            ("washer", "plate washer pulled through the web", "Claude's rule: φ 0.75 × 0.6 Fu × 4 side × t", T, punch, T / punch)]


def sag_forces(out: dict, li) -> dict:
    """Per side and sag-rod row: the down-slope reactions of every roof line (eave strut → ridge) per gravity combination,
    the accumulated rod-piece forces and the ridge-tie force (kN)."""
    slope = float(out["input"]["roof_slope"])
    c = 1.0 / math.sqrt(1 + slope * slope)
    ok, bad = tied_rows(out)
    rows = sorted(ok + bad)
    lines = [ln for ln in building_lines(out, li) if ln["kind"] in ("purlin", "ridge_purlin", "eave_strut")]
    ys = {}
    for m in out["members"]:
        if m["role"] in ("purlin", "ridge_purlin", "eave_strut"):
            ys.setdefault(m["line"], (m["side"], abs(m["start"][1] - (0.0 if m["side"] == "A" else float(out["input"]["span"])))))
    grav = {n: {k: f for k, f in fac.items() if k in ("D", "C", "Lr")} for n, fac in COMBOS_ROOF["LRFD"].items()}
    react = {}                                      # (line base, row) → {combo: R}
    ixs = {}
    for ln in lines:
        x0, x1 = ln["nodes"][0], ln["nodes"][-1]
        inner = [r for r in rows if x0 < r < x1 and ln["supports"][0] - 1e-6 <= r <= ln["supports"][-1] + 1e-6]
        if not inner:
            continue
        if ln["profile"] not in ixs:
            ixs[ln["profile"]] = cfs_section(ln["profile"], 350.0)["props"]["Ix"]
        cases = {k: [v * slope for v in ln["cases"][k]] for k in ("D", "C", "Lr")}
        nodes = sorted(set(ln["nodes"] + inner))
        # the element loads on the refined nodes: the value of the original element that contains it
        def q_on(qs):
            return [qs[max(i for i in range(len(ln["nodes"]) - 1) if ln["nodes"][i] <= (a + b) / 2)] for a, b in zip(nodes, nodes[1:])]
        wl = {**ln, "nodes": nodes, "supports": sorted(set(ln["supports"] + inner)), "cases": {k: q_on(v) for k, v in cases.items()}}
        R = line_reactions(wl, ixs[ln["profile"]])
        base = ln["id"].split("-")[0]
        for r in inner:
            d = react.setdefault((base, r), {})
            for name, fac in grav.items():
                d[name] = d.get(name, 0.0) + sum(f * R[r][k] for k, f in fac.items())
    res = {"rows": rows, "tied": ok, "untied": bad, "sides": {}}
    for side in "AB":
        order = sorted((b for b in ys if ys[b][0] == side), key=lambda b: ys[b][1])
        for r in rows:
            chain = [(b, react.get((b, r))) for b in order if (b, r) in react]
            if not chain:
                continue
            per = {}
            for name in grav:
                acc, pieces = 0.0, []
                for k, (b, d) in enumerate(chain):
                    acc += d[name]
                    if k < len(chain) - 1:
                        pieces.append({"below": b, "above": chain[k + 1][0], "T": acc})
                per[name] = {"pieces": pieces, "slope_total": acc, "tie": acc * c}
            res["sides"].setdefault(side, {})[r] = {"lines": [b for b, _ in chain], "combos": per}
    return res


# ------------------------------------------------------------------------------------------------- the building

def _host_of(fb: dict, mem: dict, out: dict) -> dict | None:
    h = fb.get("host", "")
    if h.startswith("wind column "):
        return mem.get(h[len("wind column "):])
    role, side = h.split(" ")[0], h.split(" ")[-1]
    best = None
    for m in out["members"]:
        if m.get("role") == role and m.get("side") == side and abs(m["start"][0] - fb["start"][0]) < 1.0:
            best = m
    return best


def _moment_rows(host: dict, analysis: dict, wc_inputs: dict) -> dict | None:
    """{combo: [(s, M kN·m)]} along the host (LRFD)."""
    from .welds import _frame_result
    if host["role"] == "wind_column":
        inp = wc_inputs.get(host["id"])
        if inp is None:
            return None
        return {c: sorted((f.station, f.Mz) for f in sts) for c, sts in inp.forces.items()}
    fres, pref = _frame_result(analysis, host["start"][0])
    if fres is None:
        return None
    mid = pref + host["id"].split("-", 1)[1]
    marks = [m for m in fres["members"] if m["id"] == mid]
    if not marks:
        return None
    out = {}
    for name, r in fres["results"].items():
        if r.get("set") != "LRFD":
            continue
        rows, off = [], 0.0
        for m in marks:
            rows += [(off + x, M) for x, _P, _V, M in r["members"][m["mark"]]]
            off += m["length"]
        out[name] = sorted(rows)
    return out


def _row(r):
    key, name, ref, dem, cap, U = r[:6]
    dem, cap, U = float(dem), float(cap), float(U)
    return {"name": name, "ref": ref, "key": key, "demand": round(dem, 3), "capacity": round(cap, 3),
            "U": round(U, 4) if math.isfinite(U) else math.inf, **({"combo": r[6]} if len(r) > 6 else {})}


def _status(checks, notes):
    bad = [c for c in checks if c["U"] > 1.0]
    st = (FAILS_AISI if aisi_only(bad) else FAILS) if bad else (PARTIAL if notes else DESIGNED)
    return st, sorted({f"{c['name']}: {FIXES[c['key']]}" for c in bad})


def building_stability_braces(joints_result: dict, out: dict, analysis: dict, li, settings: StabilitySettings | None = None,
                              cleat_settings=None) -> dict:
    """Step 5c over a building: flange-brace points, sag-rod pieces, ridge ties, and the 5a cleats re-run with the
    flange-brace force (with the before / after)."""
    st = (settings or StabilitySettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    d_bolt = float(str(out.get("bolt", "M12"))[1:])
    d0 = d_bolt + 2.0
    phiRv = bolt_shear_capacity(st.bolt_grade, d_bolt, threads=st.threads)
    mf = 1.0 if st.web_washers else 0.75
    wc_inputs = {}
    if any(m["role"] == "flange_brace" and m.get("host", "").startswith("wind column") for m in out["members"]):
        from ..design.secondary_checks import wind_column_inputs
        efs = {e["end"]: e for e in analysis.get("end_frames", [])}
        try:
            wc_inputs = {row["id"]: inp for row, inp in wind_column_inputs(out, li, efs)}
        except Exception:                                   # stated per point below, never a silent pass
            wc_inputs = {}
    cleat_of = {(c["line"], round(c["x"])): c for c in out["cleats"]}
    # group the flange braces by brace point (host, the frame-side end)
    groups: dict = {}
    for m in out["members"]:
        if m["role"] == "flange_brace":
            groups.setdefault((m["host"], tuple(round(v, 1) for v in m["start"])), []).append(m)
    by_host: dict = {}
    for (h, p), ms in groups.items():
        host = _host_of(ms[0], mem, out)
        by_host.setdefault(host["id"] if host else h, []).append((p, ms, host))
    points, N_map, geometry_warnings = [], {}, []
    for hid, pts in by_host.items():
        host = pts[0][2]
        if host is None:
            for p, ms, _ in pts:
                points.append({"point": list(p), "braces": [x["id"] for x in ms], "status": NOT_EVALUATED, "missing": ["host member"]})
            continue
        L = math.dist(host["start"], host["end"])
        a = [(host["end"][i] - host["start"][i]) / L for i in range(3)]
        sv = {p: sum((p[i] - host["start"][i]) * a[i] for i in range(3)) for p, _, _ in pts}
        mrows = _moment_rows(host, analysis, wc_inputs)
        brace_s = sorted(sv.values())
        lbr = lbr_of(brace_s, (0.0, L), st.merge_tol)    # βbr: the longer adjacent segment (App. 6 Lbr)
        lsh = lbr_short_of(brace_s, (0.0, L), st.merge_tol)   # the slip imperfection: the shorter one (user 2026-11-15)
        for w in merged_points(brace_s, (0.0, L), st.merge_tol):
            geometry_warnings.append({"host": hid, **w, "note": f"brace point within {st.merge_tol:g} mm — merged; check "
                                      "the detail for clashes in step 7"})
        for p, ms, _ in pts:
            s = sv[p]
            rec = {"point": list(p), "host": hid, "host_role": host["role"], "s": round(s, 1), "braces": [x["id"] for x in ms],
                   "n": len(ms), "status": NOT_EVALUATED}
            hs = _host_at(host, list(p))
            if mrows is None or hs is None:
                points.append({**rec, "missing": ["the host's moments (analysis) or section"]})
                continue
            sec = hs["sec"]
            ho = sec["d"] - (sec["tf_top"] + sec["tf_bot"]) / 2
            b0 = ms[0]
            mm = re.fullmatch(r"L(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", b0["profile"])
            Lb_ = b0["length"]
            cos_a = abs(b0["end"][0] - b0["start"][0]) / Lb_ if host["role"] != "wind_column" else abs(b0["end"][1] - b0["start"][1]) / Lb_
            sec_line = mem.get(b0.get("line")) or next((x for x in out["members"] if x.get("line") == b0.get("line")
                                                        and x["role"] in ("purlin", "ridge_purlin", "eave_strut", "girt")), None)
            ck = None if sec_line is None else cleat_of.get((_line_key(sec_line), round(p[1] if host["role"] == "wind_column" else p[0])))
            missing = []
            if not mm:
                missing.append(f"flange brace profile {b0['profile']!r} (equal angles L<b>x<t>)")
            if ck is None:
                missing.append("the purlin / girt cleat at this point (the brace's support)")
            try:
                gb = plate_strength(b0.get("material", ""), float(mm[2]) if mm else 1.0)
            except ValueError:
                gb = None
                missing.append(f"brace grade {b0.get('material')!r}")
            if missing:
                points.append({**rec, "missing": missing})
                continue
            bb, tb = float(mm[1]), float(mm[2])
            tc, W = (float(v) for v in ck["profile"][2:].split("x"))
            ups = sorted(h["up"] for h in ck["holes"])
            y_c = (ups[0] + ups[-1]) / 2
            ang = angle_props(bb, tb)
            worst = None
            for combo, rows in mrows.items():
                cd = cd_factors(brace_s, rows)
                M = float(_interp(rows, s))
                Mr = abs(M) if host["role"] == "wind_column" else max(0.0, -M)
                dm = point_demand(Mr, cd[s], ho, lbr[s], st.brace_fraction)
                if worst is None or dm["Prb"] > worst["Prb"]:
                    worst = {**dm, "combo": combo, "Mr": Mr, "Cd": cd[s]}
            amp = slip_factor(st.slip, lsh[s])
            Prb_amp = worst["Prb"] * amp
            # the split between the braces at the point by their relative axial stiffness A cos²α / L (user 2026-11-16):
            # a pair of equal braces = half each (one in tension, one in compression — both checks run on each brace);
            # one brace (an end frame) = the full force
            kk = [ang["A"] * cos_a ** 2 / m_["length"] for m_ in ms]
            shares = [k_ / sum(kk) for k_ in kk]
            P = Prb_amp * max(shares) / cos_a            # every brace check takes the amplified force
            # the springs (step 5c review): the brace's line must lie in the secondary's web plane (no web bending)
            ub = [(b0["end"][i] - b0["start"][i]) / Lb_ for i in range(3)]
            if sec_line["role"] in ("girt", "gable_girt"):
                n_web = [0.0, 0.0, 1.0]
            else:
                sl = float(out["input"]["roof_slope"]) * (-1.0 if sec_line["side"] == "A" else 1.0)
                nr = [0.0, sl / math.hypot(sl, 1.0), 1.0 / math.hypot(sl, 1.0)]
                n_web = [0.0, -nr[2], nr[1]]
            web_normal_cos = abs(sum(a_ * b_ for a_, b_ in zip(ub, n_web)))
            if host["role"] == "wind_column":
                ys_ = [0.0, float(out["input"]["span"])]
                Lp = min(abs(p[1] - y) for y in ys_)
            else:
                xs_ = sorted(g["at"] for g in out["grids"]["x"])
                bnd = [xs_[j - 1] for j in out.get("braced_bays", [])] + [xs_[j] for j in out.get("braced_bays", [])]
                Lp = min((abs(p[0] - x) for x in bnd), default=math.inf)
            Ap = cfs_section(sec_line["profile"], 350.0)["props"]["A"]
            k_sec = math.inf if Lp < 1.0 else E_STEEL * Ap / Lp / 1000.0
            k = stiffness_provided(len(ms), ang["A"], Lb_, cos_a, tc, W, y_c, k_sec)
            comp = angle_compression(bb, tb, Lb_, gb["Fy"])
            ten = angle_tension(bb, tb, d0, gb["Fy"], gb["Fu"])
            dims = cf_dims(sec_line["profile"])
            web_g = plate_strength(sec_line.get("material", ""), dims["t"])
            e_web = (INTO_SECONDARY - dims["t"]) / math.sin(math.radians(45.0))
            nb = st.bolts_per_end
            if nb >= 2:
                brace_rows = [("brace", "flange brace compression (E5(a), E3)", "AISC 360-16 E5, E3", P, comp["phiPn"], P / comp["phiPn"], worst["combo"])]
                ecc = None
            else:                                   # 1 bolt per end: E5 does not apply (user 2026-11-15) → H2 eccentric
                ecc = {"compression": angle_eccentric(bb, tb, Lb_, gb["Fy"], P, st.gauge),
                       "tension": angle_eccentric(bb, tb, Lb_, gb["Fy"], -P, st.gauge)}
                brace_rows = [("brace", f"flange brace {kk} on the gauge line (1 bolt: H2, eccentric both axes)",
                               "AISC 360-16 H2-1, E3, F10", P, P / v["U"] if v["U"] > 0 else math.inf, v["U"], worst["combo"])
                              for kk, v in ecc.items()]
            rows_ = brace_rows + [
                     ("brace", "flange brace tension (connected leg net)", "AISC 360-16 D2", P, ten, P / ten, worst["combo"]),
                     ("stiffness", "brace stiffness βbr (App. 6.3.2a) vs every spring in series", "AISC 360-16 A-6-8; Claude's springs",
                      worst["beta"], k["system"], worst["beta"] / k["system"], worst["combo"]),
                     ("bolt", "bolt shear (per end)", "AISC 360-16 J3.6", P, nb * phiRv, P / (nb * phiRv)),
                     ("bolt", "bearing on the angle leg", "AISC 360-16 J3.10", P,
                      nb * hole_strength(d_bolt, st.end_distance - d0 / 2, tb, gb["Fu"]), None),
                     ("web", "bearing on the purlin / girt web", "AISI S100-16 J3.3.1 / J3.1 (VERIFIED False)", P,
                      nb * aisi_bolt_bearing(d_bolt, dims["t"], e_web, web_g["Fy"], web_g["Fu"], mf), None)]
            rows_ = [r if r[5] is not None else (*r[:5], r[3] / r[4] if r[4] > 0 else math.inf) for r in rows_]
            notes = [FRAME_END_NOTE]
            if nb < 2:
                notes.append(f"{nb} bolt per end (setting bolts_per_end): E5 does not apply — H2 eccentric axial, gauge {st.gauge:g} mm")
            if web_normal_cos > 0.01:
                rows_.append(("stiffness", "web local bending spring — NOT EVALUATED (the brace is not in the web plane)",
                              "Claude's springs", web_normal_cos, 0.0, math.inf))
            if comp["slender_leg"]:
                rows_.append(("brace", "slender leg (E7) — NOT EVALUATED", "AISC 360-16 E7", 1.0, 0.0, math.inf))
            checks = sorted((_row(r) for r in rows_), key=lambda r: -r["U"])
            status, fixes = _status(checks, notes)
            fix_options = []                          # options only (user 2026-11-15) — the model is not changed
            for c in checks:
                if c["U"] > 1.0 and c["key"] == "brace" and "H2" in c["name"]:
                    e5 = angle_compression(bb, tb, Lb_, gb["Fy"])
                    big = angle_eccentric(60.0, 6.0, Lb_, plate_strength(b0.get("material", ""), 6.0)["Fy"], P, st.gauge_L60)
                    fix_options.append(f"2 bolts per end: E5 compression U {P / e5['phiPn']:.3f}")
                    fix_options.append(f"L60x6 (gauge {st.gauge_L60:g} mm, 1 bolt): H2 compression U {big['U']:.3f}")
                if c["U"] > 1.0 and c["key"] == "web":
                    g = gauge_for(dims["t"], c["U"], d_bolt)
                    fix_options.append(f"2 bolts per end: web bearing U {c['U'] / 2:.3f} (E5 then applies instead of H2)")
                    fix_options.append(f"a heavier {sec_line['role'].replace('_', ' ')} gauge in that bay: t ≥ {g['t_req']:.2f} mm"
                                       + (f" → {g['gauge']:g} mm" if g["gauge"] else " (beyond the gauge list)"))
            rec["fix_options"] = list(dict.fromkeys(fix_options))
            rec["split"] = {"n": len(ms), "shares": [round(x, 4) for x in shares],
                            "rule": "by relative axial stiffness A cos²α / L; a pair: one tension, one compression"}
            rec.update(status=status, fixes=fixes, notes=notes, checks=checks, governing={k_: checks[0][k_] for k_ in ("name", "U")},
                       demand={"combo": worst["combo"], "Mr": round(worst["Mr"], 3), "Cd": worst["Cd"], "ho": round(ho, 1),
                               "Lbr": round(lbr[s], 1), "Prb": round(worst["Prb"], 3), "beta_req": round(worst["beta"], 4),
                               "slip_mm": st.slip, "L_short": round(lsh[s], 1), "delta_o": round(lsh[s] / 500.0, 3),
                               "slip_factor": round(amp, 4),
                               "Prb_amplified": round(Prb_amp, 3), "P_brace": round(P, 3), "cos_alpha": round(cos_a, 4)},
                       stiffness={**{kk: (round(v, 3) if math.isfinite(v) else "rigid") for kk, v in k.items()},
                                  "purlin_axial_length": round(Lp, 1) if math.isfinite(Lp) else None,
                                  "web_normal_cos": round(web_normal_cos, 5)},
                       angle=({"method": "E5(a)", "Lc_r": round(comp["Lc_r"], 2), "phiPn": round(comp["phiPn"], 3)} if ecc is None else
                              {"method": "H2 eccentric (1 bolt)", **{kk: {x: (round(y, 4) if isinstance(y, float) else y) for x, y in v.items()
                                                                       if x != "terms"} for kk, v in ecc.items()}}),
                       cleat=f"{ck['line']} at {ck['x']:g}")
            key = (ck["line"], round(ck["x"]))
            N_map[key] = max(N_map.get(key, 0.0), Prb_amp)
            points.append(rec)
    # sag rods and ridge ties
    sf = sag_forces(out, li)
    rods = [m for m in out["members"] if m["role"] in ("sag_rod", "ridge_tie")]
    rod_prof = {m["role"]: m for m in rods}
    lines_t = {m["line"]: cf_dims(m["profile"])["t"] for m in out["members"] if m["role"] in ("purlin", "ridge_purlin", "eave_strut")}
    lines_g = {m["line"]: m.get("material", "") for m in out["members"] if m["role"] in ("purlin", "ridge_purlin", "eave_strut")}
    sag, ties = [], []
    for role, target in (("sag_rod", sag), ("ridge_tie", ties)):
        m = rod_prof.get(role)
        if m is None:
            continue
        mm = re.fullmatch(r"RD(\d+(?:\.\d+)?)", m["profile"])
        if not mm:
            target.append({"role": role, "status": NOT_EVALUATED, "missing": [f"profile {m['profile']!r} (rods RD<d>)"]})
            continue
        d = float(mm[1])
        g = plate_strength(m.get("material", ""), d)
        for side, rws in sf["sides"].items():
            for r, rec in rws.items():
                if role == "sag_rod":
                    best = None
                    for combo, v in rec["combos"].items():
                        for pc in v["pieces"]:
                            if best is None or pc["T"] > best[1]["T"]:
                                best = (combo, pc)
                    if best is None:
                        continue
                    combo, pc = best
                    tw = min(lines_t[pc["below"]], lines_t[pc["above"]])
                    gl = pc["below"] if lines_t[pc["below"]] <= lines_t[pc["above"]] else pc["above"]
                    T, where = pc["T"], f"{pc['below']} - {pc['above']}"
                else:
                    if side != "A":
                        continue
                    combo, T, where, gl = None, -1.0, "ridge", None
                    for sd in sf["sides"].values():
                        rr = sd.get(r)
                        if not rr:
                            continue
                        for cn, v in rr["combos"].items():
                            if v["tie"] > T:
                                combo, T, gl = cn, v["tie"], rr["lines"][-1]
                    tw = lines_t[gl]
                gw = plate_strength(lines_g[gl], tw)
                checks = sorted((_row((*x, combo)) for x in rod_rows(T, d, g["Fy"], g["Fu"], tw, gw["Fu"], st.plate_washer)),
                                key=lambda x: -x["U"])
                status, fixes = _status(checks, [])
                target.append({"role": role, "side": side if role == "sag_rod" else "both", "row": round(r, 1), "piece": where,
                               "T": round(T, 3), "combo": combo, "status": status, "fixes": fixes, "checks": checks,
                               "governing": {k_: checks[0][k_] for k_ in ("name", "U")}, "web_t": tw})
    # the 5a cleats, before and after the flange-brace force
    before = building_cleats(joints_result, out, li, cleat_settings)
    after = building_cleats(joints_result, out, li, cleat_settings, flange_brace_N=N_map)
    bmap = {x["joint"]: x for x in before["cleats"]}
    changed = []
    for x in after["cleats"]:
        b = bmap[x["joint"]]
        if "governing" in x and "governing" in b and abs(x["governing"]["U"] - b["governing"]["U"]) > 1e-4:
            changed.append({"joint": x["joint"], "line": x["line"], "U_before": b["governing"]["U"], "U_after": x["governing"]["U"],
                            "governing_after": x["governing"]["name"], "status": x["status"],
                            "N": [p.get("flange_brace_N") for p in x.get("pieces", []) if p.get("flange_brace_N")]})
    counts = {}
    for grp, rs in (("flange_braces", points), ("sag_rods", sag), ("ridge_ties", ties)):
        c = {}
        for r in rs:
            c[r["status"]] = c.get(r["status"], 0) + 1
        counts[grp] = c
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "verified": dict(VERIFIED),
            "geometry_warnings": geometry_warnings, "flange_braces": points, "sag_rods": sag, "ridge_ties": ties, "sag_forces": sf, "counts": counts,
            "cleats": after, "cleats_changed": changed, "flange_brace_N": {f"{k[0]}@{k[1]}": round(v, 3) for k, v in N_map.items()}}
