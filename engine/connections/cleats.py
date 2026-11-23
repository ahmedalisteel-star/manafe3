# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5a: the purlin / girt / eave-strut / gable-girt cleats. NOT FOR ISSUE. SI: mm, kN, MPa (weld flows N/mm).

The user's decisions (2026-11-15, step 5: 2a, 3a, 4a, 5a, 11a):
    forces       the support reactions of the Phase 4 cold-formed lines (engine.design.cfs_checks: the same lines, loads,
                 laps at 2 EI and the same beam solver), EVERY LRFD combination of the line — gravity, uplift, suction.
                 Axial: the eave strut's bracing force (Phase 4: the LRFD 1.0 W value × the combination's wind factor,
                 both signs — the wind reverses); no axial force on purlins / girts (no drag in the model, stated).
    detail       from the model: PL t × W × h (PL8 × 100 × (H − 20)), standing on the frame flange beside the web; its holes
                 match the purlin's (2 rows at the gauge g = H − 2 (lip + 25), centred on the web; an interior eave-strut
                 cleat has 2 columns at ±25 mm, one per butt-jointed piece); bolts 8.8, snug-tight, threads INCLUDED
                 (the Phase 5 plan rule); M12 → 14 mm holes (the model's).
    materials    the purlin web: the member's grade and thickness, the same Fy / Fu the Phase 4 checks use
                 (engine.design.inputs.plate_strength: S350GD 350 / 420 MPa, EN 10346); an unknown grade → NOT EVALUATED.
                 The cleat: the host member's grade (bimsteelauto get_grade via PLATE_GRADE, as steps 3 / 4) unless set.

Directions at a cleat ("up" = along the cleat height, away from the frame flange; "along" = along the purlin line):
    R      the reaction normal to the roof / wall — ALONG the bolt line; + toward the flange (gravity, inward pressure)
    N      the axial force of a piece — ACROSS the bolt line, in the cleat plane, through the bolt centroid
    F_out  out of the cleat plane (along the bolt axis): the down-slope component of the roof gravity reaction (tan θ ×
           the gravity part of R — taken at the cleat as if there were no sag rods: conservative) and, on wall lines,
           the girt's own weight + the wall sheeting (1.4D / 1.2D / 0.9D with the wind; Phase 4 does not check it — a
           stated gap there). Taken as bolt TENSION (conservative).
    The bolt group is CONCENTRIC for R and N (e = 0: R acts along the bolt line, N through the group centroid at the web's
    mid-height). The lever from the flange to the bolt centroid (y_c) goes into the cleat bending and the weld instead.

Checks (worst over every combination; U = demand / capacity; φ by AISC 360-16 LRFD):
    per piece (its own bolts):
        bolt shear J3.6 (bimsteelauto bolt_shear_capacity, threads included) and bolt tension with shear J3.7 (J3-3a:
            φRnt' = 1.3 φRnt − φRnt V / φRnv ≤ φRnt)
        bearing / tearout on the CLEAT (AISC J3.10, pyaisc360 bolt_hole_strength, deformation considered) and on the purlin
            WEB — AISI S100-16 J3.3.1 / J3.1 for sheet under 4.76 mm (step 5c retrofit, user 2026-11-15; transcribed from
            memory, VERIFIED False, open item 9.2: C by d/t, mf 0.75 without washers under head and nut),
            the group = the sum of its bolts, each with its own clear distance lc IN THE DIRECTION OF ITS FORCE: the cleat
            is loaded in the direction of the load, the web the opposite way. Gravity: cleat lower bolt to the flange
            (conservative: the welded edge counted as a free one), web upper bolt to the top flange (the web runs on
            into the flange: conservative); uplift: cleat upper bolt to the top edge, web lower bolt to the bottom flange;
            N: both bolts of a column are edge bolts — the cleat to its side edge (or to the other column's hole), the web
            to the piece's own end (an eave strut's butt end: 20 mm). R and N together: the resultant against the smaller
            directional capacity (conservative).
        block shear J4.3 (pyaisc360 block_shear_strength, Ubs 1, net widths + 1.6 mm, B4.3b) where the force runs toward
            a FREE edge: the cleat under uplift (one shear plane up the bolt line to the top edge, tension to the nearer
            side edge) and under N toward a side edge (two shear planes to the edge with tension between the holes, or
            one shear plane with tension up to the top edge — the smaller); the web under N toward its end (two shear
            planes, tension between the holes). Toward the flange or into a continuous web: no free edge, not applicable.
    per cleat (all pieces):
        section at the flange: axial (tension 0.9 Fy A; compression E3 with Lc = K × the top-bolt height, K = 2.1
            fixed-free, r = t / √12), in-plane bending N_net × y_c (F11 rectangular bar, Lb = the top-bolt height, Cb 1),
            out-of-plane bending F_out × y_c + |R| × (t_cleat + t_web) / 2 (the web's offset; F11 minor axis, Mp ≤ 1.6
            My), H1-1; net tension rupture at the bolt row 0.75 Fu (W − n_cols (d0 + 1.6)) t (J4.1); shear of N_net
            J4.2 (gross / net through the bolt row); a two-column cleat: the piece force through the plate between the
            columns, J4.1 on the vertical section.
        weld to the frame flange: a fillet both sides along the width W (2 lines). Per mm per line, elastic: across the
            weld |R| / 2W + 3 N_net y_c / W² (in-plane moment, two lines) + M_out / (t_cleat W) (out-of-plane moment as a
            couple over the plate thickness: conservative), F_out / 2W transverse, N_net / 2W along; weld metal: the
            resultant, NO directional increase (bimsteelauto fillet_line_strength, E70); base metal of the cleat shared
            by the two lines: the across-weld part against J4.1 (base_mode "tension"), the rest against 0.45 Fu t / 2,
            added linearly (conservative). Leg = max(J2.4 by the thinner part, shop_min_leg, demand) — ONE leg for every
            cleat of the building (one detail per joint type).
        the host member: uplift / suction (the cleat pulls the flange) J10.1 flange local bending (applies when W ≥
            0.15 bf; × 0.5 within 10 tf of the member end); inward (the cleat pushes) J10.2 web local yielding (k = tf +
            the flange-to-web fillet, lb = t_cleat; the near-end form within d) and J10.3 web crippling (near-end forms
            within d / 2) — pyaisc360. The section at the cleat (tf, tw, d, bf: the smaller flange) from the member's
            segments.
A cleat whose reaction, grade, geometry or host is missing reads NOT EVALUATED with the missing items — never a pass.
Claude's rules (VERIFIED False until the user confirms): the directional edges, the resultant against the smaller
capacity, F_out as bolt tension and its sources, K = 2.1, the couple over t, the linear base-metal sum, the cleat grade =
the host's.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from bimsteelauto_connections.bolts import bolt_shear_capacity, bolt_tension_capacity, get_grade
from bimsteelauto_connections.welds import min_weld_size
from pyaisc360 import chapter_j as J
from pyaisc360.chapter_e import flexural_buckling_stress_E3

from ..design.cfs_checks import COMBOS_MIN, COMBOS_ROOF, NST, STEEL_KN_M3, attach_struts, beam_line, building_lines, strut_setup
from ..design.cfs_section import cfs_section
from ..design.inputs import plate_strength
from ..peb.secondary import cf_dims
from .baseplates import PLATE_GRADE
from .welds import FILLET_LEGS, base_metal, base_metal_tension, section_at, weld_metal, WeldSettings

BANNER = "NOT FOR ISSUE — purlin / girt / eave-strut cleats (Phase 5 step 5a); Claude's rules VERIFIED False"
NOT_EVALUATED = "NOT EVALUATED"
DESIGNED = "DESIGNED"
FAILS = "FAILS"
#: a failure that rests only on the AISI J3 thin-web bearing typed from memory (user 2026-11-15) — until the printed page
#: is checked (open item 9.2)
FAILS_AISI = "FAILS (AISI J3.3 unverified, item 9.2)"
#: on a cleat whose GOVERNING check is the AISI J3.3 / J3.1 thin-web bearing (user 2026-11-23): a note, status unchanged
AISI_GOV_NOTE = "governing check from AISI J3.3, unverified (item 9.2)"
#: cold-formed gauges offered in the fix options (typical supplier thicknesses, mm) — options only, the model is not changed
CF_GAUGES = (1.5, 1.8, 2.0, 2.3, 2.5, 3.0, 3.2)


def aisi_only(bad: list[dict]) -> bool:
    """Every failing row is an AISI S100 J3 thin-web bearing row."""
    return bool(bad) and all(str(r.get("ref", "")).startswith("AISI") for r in bad)


def gauge_for(t: float, U: float, d: float) -> dict:
    """The thinnest gauge of CF_GAUGES that brings an AISI J3 web-bearing U to ≤ 1: the strength is linear in t while
    d / t < 10 (C = 3.0) — t_req = t × U."""
    t_req = t * U
    g = next((x for x in CF_GAUGES if x + 1e-9 >= t_req), None)
    if g is not None and d / g >= 10.0:
        g = None
    return {"t_req": round(t_req, 3), "gauge": g}
E_STEEL = 200000.0
HOLE_ALLOWANCE = 1.6                 # mm, AISC 360-16 B4.3b: net widths only
IN, KSI, KIP = 25.4, 6.894757, 4.448222
#: wall-line combinations for a cleat: the Phase 4 girt combinations (1.0 W in / out) + the girt's own weight and the wall
#: sheeting out of the cleat plane (ASCE 7-16 §2.3.1: 1.4D; 1.2D + 1.0W; 0.9D + 1.0W)
COMBOS_WALL_CLEAT = {"1.4D": {"D": 1.4}, "1.2D+1.0W inward": {"D": 1.2, "Win": 1.0}, "1.2D+1.0W outward": {"D": 1.2, "Wout": 1.0},
                     "0.9D+1.0W inward": {"D": 0.9, "Win": 1.0}, "0.9D+1.0W outward": {"D": 0.9, "Wout": 1.0}}
GRAVITY = ("D", "C", "Lr")
VERIFIED = {"directional_edges": False, "resultant_vs_smaller_capacity": False, "f_out_as_bolt_tension": False,
            "f_out_sources": False, "k_cleat_2_1": False, "couple_over_t": False, "linear_base_metal": False,
            "cleat_grade_host": False}
ASSUMPTIONS = (
    "R along the bolt line, N through the bolt centroid: a concentric group (e = 0)",
    "gravity / inward: the cleat's lower bolt is checked for tearout to the welded edge as if free; the web runs on into "
    "the flange (its lc to the flange's inside face): both conservative",
    "at a lap the two nested webs share the bolts; ONE web (the smaller edge distances) is checked for the whole force, "
    "the bolts in one shear plane: conservative",
    "the down-slope component of the roof gravity reaction is taken at the cleat as if there were no sag rods; a wall line's "
    "own weight and sheeting act out of the cleat plane; both as bolt tension and cleat minor-axis bending",
    "strut lines (open item 16.2, the same-direction pairing of open item 15 — the member check's): the eave strut's "
    "P_split (the drag, or in a braced bay the wall-panel shear), between two braced bays the item 7 panel-bracing force "
    "max(drag, 0.005 x sum Pr of the columns, same combination) (user 1c), and at the braced-bay frame lines the strut "
    "purlin's roof-X force V — C&C with the panel force only, Case B uplift with max(Case B share x the wind factor, "
    "panel), the §28.3.4 minimum with dead load only (0.9D, 1.2D); every combination both signs",
    "flange-brace force at a cleat with a strut force: the strut force PLUS the flange-brace force of THE SAME "
    "combination (frame combinations matched by their D, Lr and wind factors; Case B with the brace cases, the minimum "
    "with BRmin), worse sign — user decision 2026-11-22 ('concurrent forces, same combination'). Other purlins / girts: "
    "the flange-brace force (the largest over the frame's combinations, both signs, added to every combination: an "
    "envelope)",
    "a cleat carrying two gauges (two pieces) takes the THINNER piece's web thickness and grade (open item 16.3)",
    "one weld leg per cleat type (plate thickness and width): one detail per joint type (open item 16.2: the PL10 strut "
    "cleats have their own leg)",
    "the cleat's steel = the host member's grade unless set (the model gives the cleat no grade)",
)
FIXES = {
    "bolt": "M16 bolts (18 mm holes) or a 4-bolt cleat",
    "cleat": "a thicker cleat (PL10) or a longer edge distance",
    "web": "a thicker purlin / girt or a 4-bolt cleat",
    "strut end": "holes farther from the eave strut's butt end (a longer end distance) or a 4-bolt cleat per piece",
    "section": "a thicker / wider cleat",
    "weld": "a thicker cleat (the base metal), or a larger fillet",
    "host": "a stiffener under the cleat (flange / web) or a thicker flange",
}


@dataclass
class CleatSettings:
    """Every default the cleats use — editable per job, listed on each result."""
    bolt_grade: str = "8.8"
    threads: str = "N"                 # N = threads included in the shear plane (Phase 5 plan: 8.8 snug-tight, included)
    cleat_grade: str | None = None     # None → the host member's grade (PLATE_GRADE)
    K_cleat: float = 2.1               # the cleat as a fixed-free column (AISC Commentary Table C-A-7.1, recommended value)
    electrode: str = "E70"
    shop_min_leg: float = 5.0          # as step 4
    flange_web_leg: float = 5.0        # the host's flange-to-web fillet for k = tf + leg (J10.2); step 4's shop minimum
    #: a fixed fillet leg per cleat type (mm), still capped at J2.2b — user 2026-11-23: the PL12 strut cleat takes 10 mm
    fixed_legs: dict = None
    web_washers: bool = True           # washers under head AND nut on the cold-formed web: AISI mf 1.00 (else 0.75) —
                                       # the default for secondary bolts into cold-formed members (open item 16.5, user 2026-11-18)

    def __post_init__(self):
        if self.fixed_legs is None:
            self.fixed_legs = {"PL12x100": 10.0}

    def check(self) -> "CleatSettings":
        if self.threads not in ("N", "X"):
            raise ValueError("threads: N (included) or X (excluded)")
        for k in ("K_cleat", "shop_min_leg", "flange_web_leg"):
            v = getattr(self, k)
            if not (isinstance(v, (int, float)) and v > 0):
                raise ValueError(f"{k} must be > 0")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "CleatSettings":
        d = dict(d or {})
        bad = set(d) - set(cls.__dataclass_fields__)
        if bad:
            raise ValueError(f"unknown cleat settings: {', '.join(sorted(bad))}")
        return cls(**d).check()


# ------------------------------------------------------------------------------------------------- unit boundary

def _kN(r) -> float:
    return r.available * KIP


def hole_strength(d: float, lc: float, t: float, Fu: float) -> float:
    """φRn of one bolt hole, kN: J3.10 bearing 2.4 d t Fu / tearout 1.2 lc t Fu, the smaller, φ 0.75 (pyaisc360)."""
    if lc <= 0:
        return 0.0
    return _kN(J.bolt_hole_strength(d=d / IN, lc=lc / IN, t=t / IN, Fu=Fu / KSI))


#: AISI S100-16 J3 (bolted connections of sheet < 3/16 in = 4.76 mm) — TRANSCRIBED FROM MEMORY (user 2026-11-15, step 5c
#: decision 7b), VERIFIED False until the user confirms the printed J3.1 / J3.3.1 and Tables J3.3.1-1 / -2 (open item 9.2):
#:   J3.3.1 bearing without hole deformation: Pn = C mf d t Fu, φ 0.60; C (Table J3.3.1-1): d/t < 10 → 3.0;
#:     10 ≤ d/t ≤ 22 → 4 − 0.1 d/t; d/t > 22 → 1.8; mf (Table J3.3.1-2): single shear / outside sheets of double shear
#:     with washers under head AND nut 1.00, without (or one washer) 0.75, inside sheet of double shear 1.33
#:   J3.1 shear along the edge (end / spacing): Pn = t e Fu, e = in the line of force from the hole centre to the end of the
#:     part or the edge of the adjacent hole; φ 0.70 when Fu / Fy ≥ 1.08, else 0.60
AISI_T_MAX = 4.76
AISI_VERIFIED = False


def aisi_bearing_C(d: float, t: float) -> float:
    r = d / t
    return 3.0 if r < 10.0 else (4.0 - 0.1 * r if r <= 22.0 else 1.8)


def aisi_bolt_bearing(d: float, t: float, e: float, Fy: float, Fu: float, mf: float = 0.75) -> float:
    """φPn of one bolt in a thin sheet, kN: the smaller of AISI S100-16 J3.3.1 bearing (φ 0.60 C mf d t Fu) and J3.1 edge /
    spacing shear (φ t e Fu, φ 0.70 / 0.60 by Fu / Fy) — VERIFIED False (from memory)."""
    if e <= 0:
        return 0.0
    brg = 0.60 * aisi_bearing_C(d, t) * mf * d * t * Fu / 1000.0
    edge = (0.70 if Fu / Fy >= 1.08 else 0.60) * t * e * Fu / 1000.0
    return min(brg, edge)


def web_hole(d: float, d0: float, lc: float, t: float, Fy: float, Fu: float, mf: float) -> float:
    """One bolt in the cold-formed web: AISI S100-16 J3 when t < 4.76 mm (e = lc + d0 / 2), else AISC J3.10."""
    return aisi_bolt_bearing(d, t, lc + d0 / 2, Fy, Fu, mf) if t < AISI_T_MAX else hole_strength(d, lc, t, Fu)


def block_shear(Agv: float, Anv: float, Ant: float, Fy: float, Fu: float) -> float:
    """φRn, kN: J4.3 (Ubs 1), areas mm² (pyaisc360). A path the holes consume → 0."""
    if Anv <= 0 or Ant <= 0:
        return 0.0
    a = IN * IN
    return _kN(J.block_shear_strength(Fu=Fu / KSI, Anv=Anv / a, Ant=Ant / a, Fy=Fy / KSI, Agv=Agv / a, Ubs=1.0))


def shear_yield_rupture(Agv: float, Anv: float, Fy: float, Fu: float) -> float:
    """φRn, kN: J4.2 the smaller of 1.0 × 0.6 Fy Agv and 0.75 × 0.6 Fu Anv (pyaisc360)."""
    if Anv <= 0:
        return 0.0
    a = IN * IN
    return _kN(J.element_shear_strength(Fy=Fy / KSI, Agv=Agv / a, Fu=Fu / KSI, Anv=Anv / a))


def tension_yield_rupture(Ag: float, An: float, Fy: float, Fu: float) -> float:
    """φRn, kN: J4.1 the smaller of 0.9 Fy Ag and 0.75 Fu An (pyaisc360)."""
    if An <= 0:
        return 0.0
    a = IN * IN
    return _kN(J.element_tension_strength(Fy=Fy / KSI, Ag=Ag / a, Fu=Fu / KSI, Ae=An / a))


def bolt_tension_with_shear(T: float, V: float, phiRt: float, phiRv: float) -> float:
    """U of a bolt in tension T with shear V (kN): J3-3a in forces, φRnt' = min(φRt, 1.3 φRt − φRt V / φRv)."""
    cap = min(phiRt, 1.3 * phiRt - phiRt * V / phiRv)
    if T <= 0:
        return 0.0
    return T / cap if cap > 0 else math.inf


def plate_moments(W: float, t: float, Lb: float, Fy: float) -> dict:
    """A rectangular plate W wide, t thick, as a cantilever Lb long (AISC 360-16 F11, Cb 1, φ 0.9), kN·mm:
    in-plane (bending about the axis normal to the plate): Mp = min(Fy t W² / 4, 1.6 Fy t W² / 6), LTB by Lb W / t²
    (F11-2 / F11-3); out of plane (minor axis): Mp = min(Fy W t² / 4, 1.6 Fy W t² / 6), no LTB (F11.2(d))."""
    E = E_STEEL
    Zx, Sx = t * W * W / 4.0, t * W * W / 6.0
    Mp = min(Fy * Zx, 1.6 * Fy * Sx)
    My = Fy * Sx
    lam = Lb * W / t ** 2
    if lam <= 0.08 * E / Fy:
        Mnx, rule = Mp, "F11-1"
    elif lam <= 1.9 * E / Fy:
        Mnx, rule = min((1.52 - 0.274 * lam * Fy / E) * My, Mp), "F11-2"
    else:
        Mnx, rule = min(1.9 * E / lam * Sx, Mp), "F11-3"
    Zy, Sy = W * t * t / 4.0, W * t * t / 6.0
    Mny = min(Fy * Zy, 1.6 * Fy * Sy)
    return {"phiMx": 0.9 * Mnx / 1000.0, "phiMy": 0.9 * Mny / 1000.0, "rule_x": rule, "Lb_d_t2": lam}


def plate_compression(W: float, t: float, Lc: float, Fy: float) -> float:
    """φPn, kN: E3 flexural buckling of the plate about its minor axis, r = t / √12 (pyaisc360 E3-2 / E3-3), φ 0.9."""
    r = t / math.sqrt(12.0)
    Fcr, _ = flexural_buckling_stress_E3(Lc / r, E_STEEL / KSI, Fy / KSI)
    return 0.9 * Fcr * KSI * W * t / 1000.0


def h1_1(Pr: float, Pc: float, Mrx: float, Mcx: float, Mry: float, Mcy: float) -> float:
    """AISC 360-16 H1-1a / H1-1b."""
    p = Pr / Pc if Pc > 0 else (math.inf if Pr > 0 else 0.0)
    m = (Mrx / Mcx if Mcx > 0 else math.inf if Mrx > 0 else 0.0) + (Mry / Mcy if Mcy > 0 else math.inf if Mry > 0 else 0.0)
    return p + 8.0 / 9.0 * m if p >= 0.2 else p / 2.0 + m


# ------------------------------------------------------------------------------------------------- reactions

def line_reactions(line: dict, Ix: float) -> dict:
    """{support: {case: R kN}} of one cold-formed line — the Phase 4 model (cfs_checks.check_line: laps at 2 EI, the same
    beam solver), one load case at a time. R + = in the load's + direction (toward the frame: gravity / inward)."""
    nodes, sup = line["nodes"], line["supports"]
    laps = line.get("laps", [])
    nsec = [2 if any(l0 - 1e-6 <= (nodes[i] + nodes[i + 1]) / 2 <= l1 + 1e-6 for l0, l1 in laps) else 1 for i in range(len(nodes) - 1)]
    EI = [203395.3 * Ix * k for k in nsec]
    out = {s: {} for s in sup}
    for case, q in line["cases"].items():
        if not all(math.isfinite(v) for v in q):
            for s in sup:
                out[s][case] = math.nan
            continue
        st = beam_line(nodes, sup, list(q), EI)
        for s in sup:
            k = nodes.index(s)
            v_end = st[(k - 1) * NST + NST - 1][2] if k > 0 else 0.0
            v_start = st[k * NST][2] if k < len(nodes) - 1 else 0.0
            out[s][case] = (v_end - v_start) / 1000.0
    return out


def wall_dead_load(line: dict, li) -> list[float]:
    """kN/m on a wall line, out of the cleat plane: the member's own weight + the wall sheeting × its tributary height."""
    sw = cfs_section(line["profile"], 350.0)["props"]["A"] * 1e-6 * STEEL_KN_M3
    q = li.wall_sheeting * line["trib"] / 1000.0 + sw
    return [q] * (len(line["nodes"]) - 1)


ROOF_KINDS = ("purlin", "ridge_purlin", "eave_strut")


def cleat_cases(line: dict, R: dict, Rd: dict | None, tan_t: float, P: float, N_brace: float = 0.0, *,
                strut: dict | None = None, families: bool = False, N_brace_by=None, panel: dict | None = None) -> list[dict]:  # Rd: {"D": kN}
    """The LRFD combinations at one support of one line: [{combo, R, F_out, N}] (kN). R from the line's own load cases;
    F_out: roof — tan θ × the gravity part of R; wall — the wall dead load's reaction Rd (out of plane); N = ± P × the
    combination's wind factor (eave struts).
    families (open item 16.2, a cleat with a strut force; roof lines), the same-direction pairing of the member check
    (cfs_checks.check_line), every combination both signs:
        C&C          N = ± (the item 7 panel force of THAT combination (eave strut between braced bays) + Nb)
        Case B       the wind combinations with Case B uplift WoutB and no inward roof pressure,
                     N = ± (max(caseB × the wind factor, panel) + Nb)
        minimum + D  COMBOS_MIN, N = ± (minimum + Nb)
    strut {caseB, minimum} kN or None; panel {COMBOS_ROOF name: kN}. Nb = the flange-brace force of THE SAME combination
    (N_brace_by(family, factors) → kN; user decision 2026-11-22, "concurrent forces, same combination", worse sign);
    without it the enveloped N_brace (fallback, flagged by the caller)."""
    if not (families and line["kind"] in ROOF_KINDS):
        return _cc_family(line, R, Rd, tan_t, P, N_brace)
    nb = N_brace_by if N_brace_by is not None else (lambda fam, fac: abs(N_brace))
    panel = panel or {}
    sb = (strut or {}).get("caseB") or 0.0
    sm = (strut or {}).get("minimum") or 0.0
    Rb = {**R, "Win": 0.0, "Wout": R.get("WoutB", 0.0)}
    out = []

    def add(name, RR, fac, n):
        r = sum(f * RR.get(c, 0.0) for c, f in fac.items())
        fo = tan_t * sum(f * RR.get(c, 0.0) for c, f in fac.items() if c in GRAVITY)
        for sg, lab in ((1.0, "+"), (-1.0, "-")):
            out.append({"combo": f"{name} {lab}N", "R": r, "F_out": fo, "N": sg * n})
    for name, fac in COMBOS_ROOF["LRFD"].items():
        wf = max(fac.get("Win", 0.0), fac.get("Wout", 0.0))
        add(f"{name} (C&C)", R, fac, max(P * wf, panel.get(name, 0.0)) + nb("C&C", fac))
    for name, fac in COMBOS_ROOF["LRFD"].items():
        wf = max(fac.get("Win", 0.0), fac.get("Wout", 0.0))
        if wf > 0:
            add(f"{name} Case B + strut", Rb, fac, max(sb * wf, panel.get(name, 0.0)) + nb("caseB", fac))
    for name, fac in COMBOS_MIN["LRFD"].items():
        add(f"{name} + strut", R, fac, sm + nb("minimum", fac))
    return out


def flange_brace_match(entries: list, family: str, fac: dict) -> float | None:
    """The flange-brace force (kN) of the frame combinations that ARE this cleat combination (user decision 2026-11-22):
    the same D and Lr factors and wind factor; C&C — no brace case; Case B — a WB case with BRA / BRB (without brace
    combinations: WB alone); minimum — a BRmin case with the same D. entries [(frame factors, N)]. The largest of the
    matching frame combinations (the worse sign / direction); None when none matches."""
    D, Lr = fac.get("D", 0.0), fac.get("Lr", 0.0)
    w = max(fac.get("Win", 0.0), fac.get("Wout", 0.0))

    def pick(need_br):
        best = None
        for f, N in entries:
            if abs(f.get("D", 0.0) - D) > 1e-9:
                continue
            bm = any(k.startswith("BRmin") for k in f)
            if family == "minimum":
                ok = bm
            else:
                fw = max((v for k, v in f.items() if k.startswith("W")), default=0.0)
                br = any(k in ("BRA", "BRB") for k in f)
                if abs(f.get("Lr", 0.0) - Lr) > 1e-9 or abs(fw - w) > 1e-9 or bm:
                    continue
                ok = (any(k.startswith("WB") for k in f) and br == need_br) if family == "caseB" else not br
            if ok:
                best = max(best or 0.0, abs(N))
        return best
    v = pick(True)
    return pick(False) if v is None and family == "caseB" else v


def _cc_family(line: dict, R: dict, Rd: dict | None, tan_t: float, P: float, N_brace: float) -> list[dict]:
    out = []
    combos = COMBOS_ROOF["LRFD"] if line["kind"] in ("purlin", "ridge_purlin", "eave_strut") else COMBOS_WALL_CLEAT
    for name, fac in combos.items():
        r = sum(f * R.get(c, 0.0) for c, f in fac.items() if c in R)
        if line["kind"] in ("purlin", "ridge_purlin", "eave_strut"):
            fo = tan_t * sum(f * R.get(c, 0.0) for c, f in fac.items() if c in GRAVITY)
        else:
            fo = fac.get("D", 0.0) * (Rd or {}).get("D", 0.0)
        wf = max(fac.get("Win", 0.0), fac.get("Wout", 0.0))
        rev = line["kind"] == "eave_strut" and wf > 0      # both signs (the same list for every bay of the line)
        for s in ((1.0, -1.0) if rev else (1.0,)):
            out.append({"combo": name + (" (wind reversed)" if s < 0 else ""), "R": r, "F_out": fo, "N": s * P * wf})
        if N_brace and not rev:                             # step 5c: the flange-brace force, envelope, both signs
            out[-1] = {**out[-1], "combo": name + " + flange brace", "N": N_brace}
            out.append({**out[-1], "combo": name + " - flange brace", "N": -N_brace})
    return out


# ------------------------------------------------------------------------------------------------- one cleat

def _dir_lc_up(geom: dict, part: str, direction: float) -> list[float]:
    """Clear distances lc of the bolts of one column along the cleat height (lower, upper), for a hole loaded toward
    +up (direction > 0) or toward the flange (direction < 0)."""
    d0, lo, hi, p = geom["d0"], geom["up_low"], geom["up_high"], geom["up_high"] - geom["up_low"]
    if part == "cleat":
        return [p - d0, geom["h"] - hi - d0 / 2] if direction > 0 else [lo - d0 / 2, p - d0]
    H, tw = geom["H"], geom["t_web"]
    return [p - d0, H - tw - hi - d0 / 2] if direction > 0 else [lo - tw - d0 / 2, p - d0]


def _cleat_lc_along(geom: dict, along: float, direction: float) -> float:
    """lc of a cleat hole loaded along the line (direction ±1): to the cleat's side edge or to another column's hole."""
    d0, W = geom["d0"], geom["W"]
    lc = W / 2 - direction * along - d0 / 2
    for a in geom["columns"]:
        if a != along and (a - along) * direction > 0:
            lc = min(lc, abs(a - along) - d0)
    return lc


def check_piece(geom: dict, piece: dict, case: dict, mats: dict, bolts: dict) -> list[dict]:
    """The checks of one piece's bolt column under one combination (piece: along, e_minus / e_plus = the web's distance
    from its hole to its ends along the line, side = +1 / −1 the side of the cleat it lies on). Rows: (key, name, ref,
    demand, capacity, U)."""
    R, N, Fo = case["R"], case["N"], abs(case["F_out"])
    nb = len(geom["rows"])
    d, d0, tc, tw = geom["d"], geom["d0"], geom["t_cleat"], geom["t_web"]
    hn = d0 + HOLE_ALLOWANCE
    rows = []
    V = math.hypot(R, N)
    Vb, Tb = V / nb, Fo / nb
    rows.append(("bolt", "bolt shear", "AISC 360-16 J3.6", Vb, bolts["phiRv"], Vb / bolts["phiRv"]))
    rows.append(("bolt", "bolt tension + shear", "AISC 360-16 J3.7 (J3-3a)", Tb, None,
                 bolt_tension_with_shear(Tb, Vb, bolts["phiRt"], bolts["phiRv"])))
    # the load direction on the cleat: R + (toward the flange) = −up; N + (the piece in tension) pulls toward its side
    up_dir = -1.0 if R > 0 else 1.0
    al_dir = piece["side"] * (1.0 if N > 0 else -1.0)
    for part, t, Fy, Fu in (("cleat", tc, *mats["cleat"]), ("web", tw, *mats["web"])):
        caps = []
        if abs(R) > 1e-9:
            dr = up_dir if part == "cleat" else -up_dir
            caps.append(sum(hole_strength(d, lc, t, Fu) if part == "cleat" else web_hole(d, d0, lc, t, Fy, Fu, mats.get("mf", 0.75))
                            for lc in _dir_lc_up(geom, part, dr)))
        if abs(N) > 1e-9:
            if part == "cleat":
                lc = _cleat_lc_along(geom, piece["along"], al_dir)
            else:
                lc = (piece["e_plus"] if -al_dir > 0 else piece["e_minus"]) - d0 / 2
            caps.append(nb * (hole_strength(d, lc, t, Fu) if part == "cleat" else web_hole(d, d0, lc, t, Fy, Fu, mats.get("mf", 0.75))))
        if caps:
            c = min(caps)
            key = part if part == "cleat" else ("strut end" if piece.get("butt") and abs(N) > 1e-9 and c == caps[-1] else "web")
            ref = "AISI S100-16 J3.3.1 / J3.1 (VERIFIED False)" if part == "web" and t < AISI_T_MAX else "AISC 360-16 J3.10"
            rows.append((key, f"bearing / tearout - {part}", ref, V, c, V / c if c > 0 else math.inf))
    # block shear toward free edges
    p = geom["up_high"] - geom["up_low"]
    caps = []
    if R < -1e-9:                                         # uplift: the cleat tears out through its top edge
        Lv = geom["h"] - geom["up_low"]
        et = geom["W"] / 2 - abs(piece["along"])
        for a in geom["columns"]:
            if a != piece["along"]:
                et = min(et, abs(a - piece["along"]) / 2)
        caps.append(block_shear(Lv * tc, (Lv - (nb - 0.5) * hn) * tc, (et - 0.5 * hn) * tc, *mats["cleat"]))
    if abs(N) > 1e-9:
        es = geom["W"] / 2 - al_dir * piece["along"]
        if not any(a != piece["along"] and (a - piece["along"]) * al_dir > 0 for a in geom["columns"]):
            etop = geom["h"] - geom["up_high"]
            A = block_shear(2 * es * tc, 2 * (es - 0.5 * hn) * tc, (p - hn) * tc, *mats["cleat"])
            B = block_shear(es * tc, (es - 0.5 * hn) * tc, (p + etop - 1.5 * hn) * tc, *mats["cleat"])
            caps.append(min(A, B))
    if caps:
        c = min(caps)
        rows.append(("cleat", "block shear - cleat", "AISC 360-16 J4.3", V, c, V / c if c > 0 else math.inf))
    if abs(N) > 1e-9:
        e = piece["e_plus"] if -al_dir > 0 else piece["e_minus"]
        c = block_shear(2 * e * tw, 2 * (e - 0.5 * hn) * tw, (p - hn) * tw, *mats["web"])
        rows.append(("strut end" if piece.get("butt") else "web", "block shear - web", "AISC 360-16 J4.3", abs(N), c,
                     abs(N) / c if c > 0 else math.inf))
    return rows


def check_cleat_section(geom: dict, pieces: list[dict], cases: list[dict], mats: dict, st: CleatSettings) -> list[dict]:
    """The cleat's own section rows under one combination (cases: one per piece, same combination)."""
    tc, W, h = geom["t_cleat"], geom["W"], geom["h"]
    Fy, Fu = mats["cleat"]
    hn = geom["d0"] + HOLE_ALLOWANCE
    ncol = len(geom["columns"])
    R = sum(c["R"] for c in cases)
    Fo = sum(abs(c["F_out"]) for c in cases)
    Nnet = sum(c["N"] * p["side"] for c, p in zip(cases, pieces))
    yc = (geom["up_low"] + geom["up_high"]) / 2
    rows = []
    m = plate_moments(W, tc, geom["up_high"], Fy)
    Mx = abs(Nnet) * yc
    My = Fo * yc + abs(R) * (tc + geom["t_web"]) / 2
    if R < 0:
        Pc, kind = 0.9 * Fy * W * tc / 1000.0, "tension"
    else:
        Pc, kind = plate_compression(W, tc, st.K_cleat * geom["up_high"], Fy), "compression"
    rows.append(("section", f"cleat axial ({kind}) + bending at the flange", "AISC 360-16 H1-1, E3, F11", abs(R), Pc,
                 h1_1(abs(R), Pc, Mx, m["phiMx"], My, m["phiMy"])))
    if R < 0:
        c = 0.75 * Fu * (W - ncol * hn) * tc / 1000.0
        rows.append(("section", "cleat net tension at the bolt row", "AISC 360-16 J4.1(b)", -R, c, -R / c if c > 0 else math.inf))
    if abs(Nnet) > 1e-9:
        c = shear_yield_rupture(W * tc, (W - ncol * hn) * tc, Fy, Fu)
        rows.append(("section", "cleat shear (N)", "AISC 360-16 J4.2", abs(Nnet), c, abs(Nnet) / c if c > 0 else math.inf))
    if ncol > 1:
        Nmax = max(abs(c["N"]) for c in cases)
        if Nmax > 1e-9:
            c = tension_yield_rupture(h * tc, (h - len(geom["rows"]) * hn) * tc, Fy, Fu)
            rows.append(("section", "cleat between the columns (piece force)", "AISC 360-16 J4.1", Nmax, c, Nmax / c))
    return rows


def weld_flows(geom: dict, pieces: list[dict], cases: list[dict]) -> dict:
    """Flows per mm per line (N/mm) of the two fillet lines along W under one combination."""
    tc, W = geom["t_cleat"], geom["W"]
    R = sum(c["R"] for c in cases)
    Fo = sum(abs(c["F_out"]) for c in cases)
    Nnet = sum(c["N"] * p["side"] for c, p in zip(cases, pieces))
    yc = (geom["up_low"] + geom["up_high"]) / 2
    Mout = Fo * yc + abs(R) * (tc + geom["t_web"]) / 2           # kN·mm
    fz = (abs(R) / (2 * W) + 3 * abs(Nnet) * yc / W ** 2 + Mout / (tc * W)) * 1000.0
    fy = Fo / (2 * W) * 1000.0
    fx = abs(Nnet) / (2 * W) * 1000.0
    return {"across": fz, "transverse": fy, "along": fx, "resultant": math.sqrt(fz * fz + fy * fy + fx * fx)}


def weld_rows(f: dict, leg: float, geom: dict, cleat_grade: str, st: CleatSettings) -> list[tuple]:
    ws = WeldSettings(electrode=st.electrode)
    wm = weld_metal(leg, 0.0, ws, directional=False)
    bt = base_metal_tension(geom["t_cleat"], cleat_grade, 2)
    bs = base_metal(geom["t_cleat"], cleat_grade, 2)
    return [("weld", f"weld metal ({leg:g} mm both sides, no directional increase)", "AISC 360-16 J2.4", f["resultant"], wm,
             f["resultant"] / wm),
            ("weld", "base metal of the cleat (2 lines): across / J4.1 + along / 0.45 Fu t", "AISC 360-16 J4.1, J4.2", None, None,
             f["across"] / bt + math.hypot(f["transverse"], f["along"]) / bs)]


def host_rows(host: dict, R: float, geom: dict, st: CleatSettings) -> list[tuple]:
    """J10.1 (R < 0, the cleat pulls) / J10.2 + J10.3 (R > 0, the cleat pushes) on the host at the cleat."""
    tf, tw, d, bf, Fy = host["tf"], host["tw"], host["d"], host["bf"], host["Fy"]
    if R < 0:
        if geom["W"] < 0.15 * bf:
            return [("host", "flange local bending - not required (W < 0.15 bf)", "AISC 360-16 J10.1", -R, None, 0.0)]
        near = host["end_distance"] < 10 * tf
        c = _kN(J.flange_local_bending(Fyf=Fy / KSI, tf=tf / IN, near_member_end=near))
        return [("host", "flange local bending" + (" (within 10 tf of the end: × 0.5)" if near else ""), "AISC 360-16 J10.1",
                 -R, c, -R / c)]
    if R <= 0:
        return []
    k = tf + st.flange_web_leg
    lb = geom["t_cleat"]
    c1 = _kN(J.web_local_yielding(Fyw=Fy / KSI, tw=tw / IN, k=k / IN, lb=lb / IN, near_member_end=host["end_distance"] <= d))
    c2 = _kN(J.web_local_crippling(tw=tw / IN, tf=tf / IN, d=d / IN, lb=lb / IN, E=E_STEEL / KSI, Fyw=Fy / KSI,
                                   near_member_end=host["end_distance"] < d / 2))
    return [("host", "web local yielding", "AISC 360-16 J10.2", R, c1, R / c1),
            ("host", "web local crippling", "AISC 360-16 J10.3", R, c2, R / c2)]


def check_cleat(geom: dict, pieces: list[dict], combos: list[list[dict]], mats: dict, bolts: dict, host: dict, leg: float,
                cleat_grade: str, st: CleatSettings) -> dict:
    """Every check of one cleat over its combinations (combos: per combination, one case per piece). The worst U of each
    check with its combination; status DESIGNED / FAILS (with the fixes)."""
    worst: dict[str, dict] = {}
    weld_need = 0.0
    for cs in combos:
        name = cs[0]["combo"]
        rows = []
        for p, c in zip(pieces, cs):
            rows += check_piece(geom, p, c, mats, bolts)
        rows += check_cleat_section(geom, pieces, cs, mats, st)
        f = weld_flows(geom, pieces, cs)
        weld_need = max(weld_need, f["resultant"])
        rows += weld_rows(f, leg, geom, cleat_grade, st)
        rows += host_rows(host, sum(c["R"] for c in cs), geom, st)
        for key, nm, ref, dem, cap, U in rows:
            w = worst.get(nm)
            if w is None or U > w["U"]:
                worst[nm] = {"name": nm, "ref": ref, "key": key, "combo": name, "U": U,
                             "demand": None if dem is None else round(dem, 3), "capacity": None if cap is None else round(cap, 3)}
    checks = sorted(worst.values(), key=lambda r: -r["U"])
    for r in checks:
        r["U"] = round(r["U"], 4) if math.isfinite(r["U"]) else math.inf
    gov = checks[0]
    bad = [r for r in checks if r["U"] > 1.0]
    options = []
    for r in bad:
        if str(r.get("ref", "")).startswith("AISI"):
            g = gauge_for(geom["t_web"], r["U"], geom["d"])
            options.append(f"{r['name']} (U {r['U']:.3f}): a heavier purlin / girt gauge in that bay, t ≥ {g['t_req']:.2f} mm"
                           + (f" → {g['gauge']:g} mm" if g["gauge"] else " (beyond the gauge list)") + "; or a 4-bolt cleat")
        elif r["key"] == "weld":
            if r["name"].startswith("weld metal"):        # weld metal ∝ leg: the 8 mm fillet a PL10 cleat allows
                options.append(f"{r['name']} (U {r['U']:.3f}): a PL10 cleat (J2.2b max 8 mm) → U {r['U'] * leg / 8.0:.3f} at 8 mm")
            else:                                          # the cleat's base metal ∝ t
                options.append(f"{r['name']} (U {r['U']:.3f}): a PL10 cleat → U {r['U'] * geom['t_cleat'] / 10.0:.3f}")
        else:
            options.append(f"{r['name']} (U {r['U']:.3f}): {FIXES[r['key']]}")
    notes = [AISI_GOV_NOTE] if str(gov.get("ref", "")).startswith("AISI") else []   # user 2026-11-23 (status unchanged)
    return {"status": (FAILS_AISI if aisi_only(bad) else FAILS) if bad else DESIGNED, "fix_options": options, "notes": notes,
            "governing": {k: gov[k] for k in ("name", "U", "combo")},
            "checks": checks, "weld_flow_max": round(weld_need, 2),
            "fixes": sorted({f"{r['name']}: {FIXES[r['key']]}" for r in bad})}


def weld_leg(flow: float, t_thinner: float, st: CleatSettings) -> float | None:
    """The smallest leg of FILLET_LEGS ≥ max(J2.4 by the thinner part, shop_min_leg) whose weld metal (no directional
    increase) carries `flow` N/mm; None when even the largest fillet does not."""
    ws = WeldSettings(electrode=st.electrode)
    lo = max(min_weld_size(t_thinner), st.shop_min_leg)
    for leg in FILLET_LEGS:
        if leg >= lo - 1e-9 and weld_metal(leg, 0.0, ws, directional=False) + 1e-9 >= flow:
            return leg
    return None


# ------------------------------------------------------------------------------------------------- the building

def _host_at(m: dict, p: list[float]) -> dict | None:
    """The host's section at the point nearest p: tf, tw, d, bf (the smaller flange), Fy, distance to the nearer end."""
    sec = m.get("section") or {}
    segs = sec.get("segments")
    if not segs:
        return None
    a, b = m["start"], m["end"]
    L = math.dist(a, b)
    s = max(0.0, min(L, sum((p[i] - a[i]) * (b[i] - a[i]) for i in range(3)) / L))
    run = 0.0
    seg, f = segs[-1], 1.0
    for g in segs:
        if s <= run + g["length"] + 1e-6:
            seg, f = g, (s - run) / g["length"]
            break
        run += g["length"]
    x = section_at(seg, max(0.0, min(1.0, f)))
    tf = min(x["tf_top"], x["tf_bot"])
    bf = min(x["bf_top"], x["bf_bot"])
    grade = PLATE_GRADE.get(seg.get("grade") or m.get("material"))
    if grade is None:
        return None
    Fy, _ = get_grade(grade, tf)
    return {"member": m["id"], "tf": tf, "tw": x["tw"], "d": x["d"], "bf": bf, "Fy": Fy, "grade": grade,
            "end_distance": round(min(s, L - s), 1), "s": s, "L": L, "sec": x}


def _line_key(m: dict) -> str:
    """The cleat's line name of a cold-formed member: its line, or a gable girt's G<end><z>."""
    if m["role"] == "gable_girt":
        return f"{m['id'][:2]}{m.get('z', m['start'][2]):g}"
    return m.get("line", "")


def building_cleats(joints_result: dict, out: dict, li, settings: CleatSettings | None = None,
                    flange_brace_N: dict | None = None, flange_brace_N_by_combo: dict | None = None, b=None) -> dict:
    """Every cleat joint of a building_joints() result (CL k ↔ out["cleats"][k − 1]) → checked cleats.
    flange_brace_N {(line, x): kN} the enveloped flange-brace force; flange_brace_N_by_combo {(line, x): {frame combo:
    (factors, kN)}} the same per frame combination (a strut cleat takes the force of the same combination). b: the
    BuildingInput — needed for the item 7 panel-bracing force of an eave strut between two braced bays (ΣPr of the
    columns, cfs_checks._column_Pr); without it such a cleat reads NOT EVALUATED."""
    from ..design.cfs_checks import _column_Pr
    st = (settings or CleatSettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    lines = building_lines(out, li)
    tan_t = float(out["input"]["roof_slope"])
    ss = strut_setup(out, li)          # open item 16.2: the member checks' strut forces (one source)
    no_panel = set()
    for ln in lines:
        e = ((ss["bl"] or {}).get("struts", {}).get("eave", {}) if ln["kind"] == "eave_strut" else {}).get(
            int(ln["id"].rsplit("-", 1)[1]) if ln["kind"] == "eave_strut" else None)
        if e and e.get("between") and b is None:
            no_panel.add(ln["id"])
        attach_struts(ln, ss, panel=(lambda e_, side: _column_Pr(b, li, out, e_["panel_lines"], side)) if b is not None else None)
    # cfs line id → (line, reactions, wall dead-load reactions); the members of each line by the cleat's line name
    key_of = {}
    for m in out["members"]:
        if m["role"] in ("purlin", "ridge_purlin", "eave_strut", "girt", "gable_girt"):
            cid = m["id"] if m["role"] == "eave_strut" else m["id"].split("-")[0] if m["role"] == "gable_girt" else m["line"]
            key_of[cid] = _line_key(m)
    by_key: dict[str, list] = {}
    ixs = {}
    for ln in lines:
        if ln["profile"] not in ixs:
            ixs[ln["profile"]] = cfs_section(ln["profile"], 350.0)["props"]["Ix"]     # geometry only (Fy-independent)
        R = line_reactions(ln, ixs[ln["profile"]])
        Rd = None
        if ln["kind"] in ("girt", "gable_girt"):
            Rd = line_reactions({**ln, "cases": {"D": wall_dead_load(ln, li)}}, ixs[ln["profile"]])
        by_key.setdefault(key_of.get(ln["id"], ln["id"]), []).append((ln, R, Rd))
    d_bolt = float(str(out.get("bolt", "M12"))[1:])
    bolts = {"phiRv": bolt_shear_capacity(st.bolt_grade, d_bolt, threads=st.threads),
             "phiRt": bolt_tension_capacity(st.bolt_grade, d_bolt)}
    pending = []
    res = []
    for j in joints_result["joints"]:
        if j["type"] != "cleat":
            continue
        c = out["cleats"][int(j["id"][2:]) - 1]
        rec = {"joint": j["id"], "line": c["line"], "point": j["point"], "cleat": c["profile"], "status": NOT_EVALUATED}
        missing = []
        hosts = [x for x in j["members"] if "distance" in x]
        host = _host_at(mem[hosts[0]["id"]], c["base"]) if hosts else None
        if host is None:
            missing.append("host member (or its section / grade)")
        pcs = [mem[x["id"]] for x in j["members"] if "distance" not in x]
        if not pcs:
            missing.append("the cold-formed piece on the cleat")
        try:
            t_c, W = (float(v) for v in c["profile"][2:].split("x"))
        except ValueError:
            t_c = W = None
            missing.append(f"cleat size from {c['profile']!r}")
        mats = {"mf": 1.0 if st.web_washers else 0.75}
        thin = None
        if pcs:
            thin = min(pcs, key=lambda m: cf_dims(m["profile"])["t"])      # two gauges on one cleat: the thinner (item 16.3)
            dims = cf_dims(thin["profile"])
            try:
                ws_ = plate_strength(thin.get("material", ""), dims["t"])
                mats["web"] = (ws_["Fy"], ws_["Fu"])
            except ValueError:
                missing.append(f"web grade {thin.get('material')!r} (not a known grade)")
        cg = st.cleat_grade or (host or {}).get("grade")
        if cg and t_c:
            mats["cleat"] = get_grade(cg, t_c)
        elif not missing:
            missing.append("cleat grade")
        found = by_key.get(c["line"], [])
        sup_x = c["x"]
        contrib = [(ln, R[s], None if Rd is None else Rd[s]) for ln, R, Rd in found
                   for s in ln["supports"] if abs(s - sup_x) < 1.0]
        if not contrib:
            missing.append(f"support reaction of line {c['line']} at {sup_x:g}")
        elif any(not math.isfinite(v) for _, R, _ in contrib for v in R.values()):
            missing.append(f"line {c['line']}: a load case not evaluated (C&C wind)")
        if missing:
            res.append({**rec, "missing": missing})
            continue
        ups = sorted(h["up"] for h in c["holes"])
        cols = sorted({h["along"] for h in c["holes"]})
        geom = {"d": d_bolt, "d0": c["holes"][0]["d"], "t_cleat": t_c, "W": W, "h": c["height"], "up_low": ups[0],
                "up_high": ups[-1], "rows": sorted(set(ups)), "columns": cols, "H": dims["H"], "t_web": dims["t"]}
        axis = 0 if abs(c["width_dir"][0]) > 0.5 else 1
        sgn = c["width_dir"][axis]
        pieces, combos = [], None

        def strut_at(ln):
            """{caseB, minimum} of a line at this support (open item 16.2), or None."""
            if ln["kind"] == "eave_strut":
                return ln.get("P_split")
            z = [p for a, b_, p in ln.get("P_zones") or [] if abs(sup_x - a) < 1.0 or abs(sup_x - b_) < 1.0]
            return z[0] if z else None
        fam = any(strut_at(ln) or ln.get("P_panel_by_combo") for ln, _, _ in contrib)
        np_ = sorted(ln["id"] for ln, _, _ in contrib if ln["id"] in no_panel)
        if np_:
            res.append({**rec, "missing": [f"the item 7 panel-bracing force of {', '.join(np_)} (between two braced bays): "
                                           "the building input b is not given"]})
            continue
        for ln, R, Rd in contrib:
            # the pieces this line puts on the cleat: an eave-strut bay = one piece; a continuous line = every piece there
            # (a bay line of the eave strut is numbered by x; its piece is the one spanning the bay's middle)
            mid_x = (ln["supports"][0] + ln["supports"][-1]) / 2
            ps = [m for m in pcs if ln["kind"] != "eave_strut"
                  or min(m["start"][axis], m["end"][axis]) < mid_x < max(m["start"][axis], m["end"][axis])]
            if not ps:
                continue
            if ln["kind"] == "eave_strut":
                m = ps[0]
                mid = (m["start"][axis] + m["end"][axis]) / 2
                side = 1.0 if (mid - c["base"][axis]) * sgn > 0 else -1.0
                along = (max(cols) if side > 0 else min(cols)) if len(cols) > 1 else cols[0]
                hx = c["base"][axis] + along * sgn
                lo, hi = min(m["start"][axis], m["end"][axis]), max(m["start"][axis], m["end"][axis])
                e_neg, e_pos = (hx - lo, hi - hx) if sgn > 0 else (hi - hx, hx - lo)
                bay = int(ln["id"].rsplit("-", 1)[1])
                pc = {"piece": m["id"], "along": along, "side": side, "e_minus": e_neg, "e_plus": e_pos,
                      "butt": len(cols) > 1}
                Nb = 0.0
            else:
                hx = c["base"][axis] + cols[0] * sgn
                ds = []
                for m in ps:
                    lo, hi = min(m["start"][axis], m["end"][axis]), max(m["start"][axis], m["end"][axis])
                    ds.append((hx - lo, hi - hx) if sgn > 0 else (hi - hx, hx - lo))
                pc = {"piece": "+".join(m["id"] for m in ps), "along": cols[0], "side": 1.0,
                      "e_minus": min(x[0] for x in ds), "e_plus": min(x[1] for x in ds), "butt": False}
                Nb = (flange_brace_N or {}).get((c["line"], round(sup_x)), 0.0)
                if Nb:
                    pc["flange_brace_N"] = round(Nb, 3)
            sp = strut_at(ln)
            if sp:
                pc["strut_kN"] = {"caseB": round(sp["caseB"], 3), "minimum": round(sp["minimum"], 3), "split": sp.get("split")}
            pnl = ln.get("P_panel_by_combo")
            if pnl:
                pc["panel_kN"] = {k_: round(v, 3) for k_, v in pnl.items()}
                pc["panel_rule"] = ln.get("P_rule")
            nby = None
            byc = (flange_brace_N_by_combo or {}).get((c["line"], round(sup_x)))
            if fam and Nb and ln["kind"] != "eave_strut":
                if byc:
                    ent = list(byc.values())

                    def nby(fam_, fac, ent=ent, Nb=Nb):
                        v = flange_brace_match(ent, fam_, fac)
                        if v is None:                       # no frame combination matches: the envelope (flagged)
                            pc.setdefault("flange_brace_unmatched", []).append(fam_)
                            return Nb
                        return v
                    pc["flange_brace_rule"] = "the same combination (user 2026-11-22), worse sign"
                else:
                    pc["flange_brace_rule"] = "envelope (no per-combination forces given)"
            pieces.append(pc)
            cs = cleat_cases(ln, R, Rd, tan_t, 0.0, 0.0 if ln["kind"] == "eave_strut" else Nb, strut=sp, families=fam,
                             N_brace_by=nby, panel=pnl)
            combos = [[x] for x in cs] if combos is None else [a + [x] for a, x in zip(combos, cs)]
        if combos is None:
            res.append({**rec, "missing": [f"the piece of line {c['line']} on the cleat"]})
            continue
        rec.update(geometry={k: geom[k] for k in ("t_cleat", "W", "h", "up_low", "up_high", "columns", "d0")},
                   pieces=pieces, host=host, materials={"cleat": {"grade": cg, "Fy": mats["cleat"][0], "Fu": mats["cleat"][1]},
                                                        "web": {"grade": thin.get("material"), "t": dims["t"],
                                                                "Fy": mats["web"][0], "Fu": mats["web"][1]}},
                   cases=[{"combo": cs_[0]["combo"], "R": round(sum(x["R"] for x in cs_), 3),
                           "F_out": round(sum(abs(x["F_out"]) for x in cs_), 3),
                           "N": [round(x["N"], 3) for x in cs_]} for cs_ in combos])
        pending.append((rec, geom, pieces, combos, mats, host, cg))
        res.append(rec)
    # one weld leg per cleat type (one detail per joint type; open item 16.2: the PL10 strut cleats are their own type)
    groups: dict[tuple, list] = {}
    for item in pending:
        groups.setdefault((item[1]["t_cleat"], item[1]["W"]), []).append(item)
    group_rec = []
    for (tc_g, W_g), items in sorted(groups.items()):
        need_g = max(weld_flows(geom, pieces, cs)["resultant"] for _, geom, pieces, combos, *_ in items for cs in combos)
        t_thin = min([tc_g] + [h["tf"] for *_, h, _ in items])
        sized = weld_leg(need_g, t_thin, st)
        # the leg is CAPPED at the AISC J2.2b maximum for the cleat (t − 2 mm for t ≥ 6, else t — user 2026-11-16); a
        # cleat needing more shows its weld rows FAIL with the fix option "PL10 cleat (max 8 mm)"
        cap = tc_g if tc_g < 6.0 else tc_g - 2.0
        fixed = (st.fixed_legs or {}).get(f"PL{tc_g:g}x{W_g:g}")
        if fixed and fixed + 1e-9 < max(min_weld_size(t_thin), st.shop_min_leg):
            raise ValueError(f"fixed weld leg {fixed:g} mm on PL{tc_g:g}x{W_g:g} is below the AISC J2.4 minimum for the thinner "
                             f"part ({t_thin:g} mm) / the shop minimum")
        leg = min(fixed, cap) if fixed else min(x for x in (sized, cap) if x is not None)
        for rec, geom, pieces, combos, mats, host, cg in items:
            if fixed and host["tf"] + 1e-9 < leg:
                # user 2026-11-23: the flange-side base metal of the fillet is not a separate row — it cannot govern while
                # the host flange tf ≥ the leg (hand check in docs/reports/item16.md); a thinner flange is not evaluated
                rec.update(status=NOT_EVALUATED, missing=[f"host flange tf {host['tf']:g} mm < the fixed fillet leg {leg:g} mm: "
                                                          "the flange-side base metal is not checked"], weld_leg=leg)
                continue
            rec.update(check_cleat(geom, pieces, combos, mats, bolts, host, leg, cg, st))
            rec["weld_leg"] = leg
        # AISC 360-16 J2.2b maximum fillet ALONG AN EDGE: t for t < 6 mm, t − 2 mm for t ≥ 6 mm (user 2026-11-15)
        cap_mx = weld_metal(cap, 0.0, WeldSettings(electrode=st.electrode), directional=False)
        over = sorted(rec["joint"] for rec, geom, pieces, combos, *_ in items
                      if max(weld_flows(geom, pieces, cs)["resultant"] for cs in combos) > cap_mx + 1e-9)
        group_rec.append({"cleat": f"PL{tc_g:g}x{W_g:g}", "count": len(items), "t_cleat": tc_g, "max_leg": cap, "leg": leg,
                          "fixed_leg": fixed,
                          "sized_leg": sized, "capped": sized is None or sized > cap, "weld_flow_max": round(need_g, 2),
                          "cleats_needing_more_than_max": over})
    need = max((g["weld_flow_max"] for g in group_rec), default=0.0)
    leg = group_rec[0]["leg"] if group_rec else None       # the thinnest cleat type's leg (the common PL8 detail)
    j22b = None
    if group_rec and leg:
        g0 = group_rec[0]
        j22b = {**{k: g0[k] for k in ("t_cleat", "max_leg", "leg", "sized_leg", "capped", "cleats_needing_more_than_max")},
                "by_cleat": group_rec,
                "note": ("the leg is capped at the J2.2b maximum (user 2026-11-16); J2.2b is written for fillets along the "
                         "EDGE of a part (lap joints) — the cleat weld is a T-joint on the cleat's faces; one leg per cleat "
                         "type (by_cleat)")}
    counts: dict[str, int] = {}
    for r in res:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "verified": dict(VERIFIED),
            "assumptions": list(ASSUMPTIONS), "weld_j2_2b": j22b,
            "detail": {"cleat": sorted({r["cleat"] for r in res}), "bolts": f"2 x M{d_bolt:g} {st.bolt_grade} per piece, snug-tight, "
                       f"threads {'included' if st.threads == 'N' else 'excluded'}", "weld_leg": leg,
                       "weld_legs": {g["cleat"]: g["leg"] for g in group_rec},
                       "weld_flow_max": round(need, 2), "bolt_phiRv": round(bolts["phiRv"], 3), "bolt_phiRt": round(bolts["phiRt"], 3)},
            "cleats": res, "counts": counts}
