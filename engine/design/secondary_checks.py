# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 5: wind columns, end rafters and the bracing — AISC 360-16 LRFD. NOT FOR ISSUE.

    wind columns   pinned-pinned simple beams under ASCE 7-16 Ch. 30 C&C wall pressure (endwall_analysis.wind_columns,
                   LRFD 1.0 W), inward and outward; stations M(x) = w x (L − x) / 2, V(x) = w (L/2 − x); axial = 1.2 × own
                   weight above the station, + on an end-rafter wall the frame's largest LRFD column load (an envelope:
                   conservative). Sections: the generated built-up WIND_COLUMN. check_member (prismatic: constant section).
                   Flanges: the OUTER flange (girt side) is "top", braced at every gable girt; the INNER flange at the
                   column's ends and at its flange braces from the gable girts (user 2026-11-09: default every second girt
                   from the top, per wall, 0 = none). Inward pressure puts the outer flange in compression (M +), suction
                   the inner one (M −).
    end rafters    each half (EFRA / EFRB) one design member over the wind-column tops, forces at every element end of the
                   end-rafter frame's LRFD solve (DAM: 0.8 stiffness, notional loads, P-δ); top flange braced at the purlins,
                   eave strut and ridge purlin; bottom flange at the supports (wind-column tops) only. check_member, prismatic.
    bracing        tension-only members, the largest LRFD tension:
                     roof / side-wall X (bracing_system: roof_diagonal / wall_diagonal), end-wall X (end-rafter frame)
                     rod RD<d>   threaded rod, AISC 360-16 J3.6 / Table J3.2: φRn = 0.75 × 0.75 Fu × Ab (Ab: the nominal
                                 unthreaded body), and the body's yield φ 0.90 Fy Ab (D2-1); no slenderness limit (D1 note)
                     angle L<b>x<t>  D2-1 yield φ 0.90 Fy Ag; D2-2 rupture φ 0.75 Fu Ae, Ae = U An, An = Ag − (d_hole) t
                                 (one standard hole, Table J3.3: d + 2 mm for M12–M24), U = 0.6 (Table D3.1 case 8, three bolts
                                 in line — the placeholder until Phase 5 details the joint); L / r_min ≤ 300 reported (D1 note)
    eave struts    with the purlins and girts in step 6 (engine/design/cfs_checks.py, AISI S100-16 DSM): the result's
                   "cold_formed" entry; "eave_struts" repeats that step's eave-strut lines
Grades: the member's material in the model (rods and angles: the generator gives the frame grade), EN 10025-2 bands by
thickness (a rod: its diameter). Every result carries the NOT FOR ISSUE banner.
"""

from __future__ import annotations

import math
import re

from bimsteelauto.design import BracingSpec, MemberDesignInput, check_member
from bimsteelauto.sections import TaperedMember, WeldedI
from bimsteelauto.spec import DesignMethod, MemberForces, MemberType

from ..analysis.endwall_analysis import WIND_COLUMN, end_rafter_frame, longitudinal_feed, wind_columns, _geom
from ..analysis.bracing_system import longitudinal_bracing
from ..analysis.secondary_weight import secondary_kpa
from ..peb.building import BuildingInput, peb_building, resolve
from .cfs_checks import cfs_checks
from .frame_checks import _materials, _check_row
from .inputs import plate_strength, section_strength

BANNER = "NOT FOR ISSUE — wind columns, end rafters, bracing, purlins, girts and eave struts checked with open verification flags"
STEEL_KN_M3 = 77.0
PHI_T_YIELD, PHI_T_RUPT, PHI_ROD = 0.90, 0.75, 0.75
U_ANGLE = 0.6
HOLE = {"M12": 14.0, "M16": 18.0, "M20": 22.0, "M24": 26.0}
NSTATIONS = 21


def _ratio_row(name, ref, demand, capacity, unit="kN", note=""):
    r = demand / capacity if capacity > 0 else math.inf
    return {"name": name, "reference": ref, "demand": round(demand, 3), "capacity": round(capacity, 3), "ratio": round(r, 4), "unit": unit, "note": note}


# --------------------------------------------------------------------------------------------- wind columns

def wind_column_inputs(out: dict, li, end_frames: dict) -> list[tuple[dict, MemberDesignInput]]:
    """(row, MemberDesignInput) per wind column."""
    wc = wind_columns(out, li)
    seg = dict(tw=WIND_COLUMN["tw"], tf_top=WIND_COLUMN["tf"], tf_bot=WIND_COLUMN["tf"], grade=WIND_COLUMN["grade"])
    st = section_strength(seg)
    wi = WeldedI(d=WIND_COLUMN["hw"] + 2 * WIND_COLUMN["tf"], tw=WIND_COLUMN["tw"], bf_top=WIND_COLUMN["bf"], tf_top=WIND_COLUMN["tf"],
                 bf_bot=WIND_COLUMN["bf"], tf_bot=WIND_COLUMN["tf"])
    sw = wi.A * 1e-6 * STEEL_KN_M3                                   # kN/m
    girts = {}
    for m in out["members"]:
        if m["role"] == "gable_girt":
            girts.setdefault(m["id"][:2], set()).add(round(m["z"] if "z" in m else m["start"][2], 1))
    res = []
    for c in wc["columns"]:
        L = c["L_m"] * 1000
        tag = "G" + c["id"][1]                                       # WF… → GF, WL… → GL
        top = tuple(sorted(z for z in girts.get(tag, ()) if 1.0 < z < L - 1.0))
        bottom = tuple(sorted({round(m["start"][2], 1) for m in out["members"] if m["role"] == "flange_brace" and m.get("host") == "wind column " + c["id"]
                               and 1.0 < m["start"][2] < L - 1.0}))
        P_frame = 0.0
        ef = end_frames.get(c["end"])
        if ef:
            P_frame = max(max(0.0, r["column_P"].get(c["id"], 0.0)) for r in ef["results"].values() if r["set"] == "LRFD")
        forces = {}
        for side, sg in (("inward", 1.0), ("outward", -1.0)):
            w = abs(c["sets"]["LRFD"][side]["w"])
            sts = []
            for k in range(NSTATIONS):
                x = L * k / (NSTATIONS - 1)
                xm = x / 1000
                M = sg * w * xm * (c["L_m"] - xm) / 2                 # kN·m, + = outer flange in compression
                V = w * (c["L_m"] / 2 - xm)
                P = P_frame + 1.2 * sw * (c["L_m"] - xm)              # compression +
                sts.append(MemberForces(P=P, Vy=V, Mz=M, station=min(max(x, 0.01), L - 0.01)))
            forces[f"LRFD C&C {side} (+ frame P)"] = sts
        inp = MemberDesignInput(mark=c["id"], member_type=MemberType.COLUMN, taper=TaperedMember(wi, wi, L), forces=forces,
                                bracing=BracingSpec(top_flange=top, bottom_flange=bottom), materials=_materials(st["Fy"], st["Fu"]),
                                method=DesignMethod.LRFD, K_in_plane=1.0, stability="prismatic")
        res.append(({**c, "Fy": st["Fy"], "P_frame": round(P_frame, 3), "girts": top, "flange_braces": bottom, "self_weight_kN_m": round(sw, 4)}, inp))
    return res


# --------------------------------------------------------------------------------------------- end rafters

def end_rafter_inputs(out: dict, ef: dict) -> list[tuple[dict, MemberDesignInput]]:
    inp_ = out["input"]
    span, slope = float(inp_["span"]), float(inp_["roof_slope"])
    c = math.sqrt(1 + slope * slope)
    tag = "F" if ef["end"] == "first" else "L"
    ew = next(e for e in out["end_walls"] if e["end"] == ef["end"])
    supports = sorted(ew["supports"])
    lines = sorted({round(m["start"][1], 3) for m in out["members"] if m["role"] in ("purlin", "ridge_purlin", "eave_strut")}
                   | {round(m["end"][1], 3) for m in out["members"] if m["role"] in ("purlin", "ridge_purlin", "eave_strut")})
    res = []
    for half, side in (("A", lambda y: y <= span / 2 + 1e-6), ("B", lambda y: y >= span / 2 - 1e-6)):
        m = next(x for x in out["members"] if x["role"] == "end_rafter" and x["id"] == f"E{tag}R{half}")
        seg = m["section"]["segments"][0]
        wi = WeldedI(d=seg["hw_start"] + seg["tf_top"] + seg["tf_bot"], tw=seg["tw"], bf_top=seg["bf_top"], tf_top=seg["tf_top"],
                     bf_bot=seg["bf_bot"], tf_bot=seg["tf_bot"])
        y0, y1 = m["start"][1], m["end"][1]
        L = math.hypot(y1 - y0, m["end"][2] - m["start"][2])
        s_of = lambda y: min(max(abs(y - y0) * c, 0.01), L - 0.01)
        top = tuple(sorted({round(s_of(y), 1) for y in lines if side(y) and 1.0 < abs(y - y0) * c < L - 1.0}))
        bot = tuple(sorted({round(s_of(y), 1) for y in supports if side(y) and 1.0 < abs(y - y0) * c < L - 1.0}))
        forces = {}
        for combo, r in ef["results"].items():
            if r["set"] != "LRFD":
                continue
            forces[combo] = [MemberForces(P=P, Vy=V, Mz=M, station=s_of(y)) for y, P, V, M in r["rafter_stations"] if side(y)]
        st = section_strength(seg)
        inp = MemberDesignInput(mark=m["id"], member_type=MemberType.RAFTER, taper=TaperedMember(wi, wi, L), forces=forces,
                                bracing=BracingSpec(top_flange=top, bottom_flange=bot), materials=_materials(st["Fy"], st["Fu"]),
                                method=DesignMethod.LRFD, K_in_plane=1.0, stability="prismatic")
        res.append(({"id": m["id"], "end": ef["end"], "length": round(L, 1), "Fy": st["Fy"], "Lb_top": top, "Lb_bottom": bot}, inp))
    return res


# --------------------------------------------------------------------------------------------- tension bracing

def angle_props(b: float, t: float) -> dict:
    """An equal-leg angle from its two rectangles (root and toe radii ignored — conservative): A, the minor principal r."""
    A1, A2 = b * t, (b - t) * t
    A = A1 + A2
    xc = (A1 * b / 2 + A2 * t / 2) / A                               # leg 1 along x (b × t), leg 2 up (t × (b − t))
    yc = (A1 * t / 2 + A2 * (t + (b - t) / 2)) / A
    Ix = b * t ** 3 / 12 + A1 * (t / 2 - yc) ** 2 + t * (b - t) ** 3 / 12 + A2 * (t + (b - t) / 2 - yc) ** 2
    Ixy = A1 * (b / 2 - xc) * (t / 2 - yc) + A2 * (t / 2 - xc) * (t + (b - t) / 2 - yc)
    Imin = Ix - abs(Ixy)                                             # equal legs: Ix = Iy, principal at 45°
    return {"A": A, "r_min": math.sqrt(Imin / A), "x_bar": xc}


def tension_check(profile: str, grade: str, T: float, L: float, bolt: str = "M16") -> dict:
    """One tension-only brace, LRFD. T kN, L mm."""
    rows = []
    rd = re.fullmatch(r"RD(\d+(?:\.\d+)?)", profile)
    an = re.fullmatch(r"L(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", profile)
    if rd:
        d = float(rd.group(1))
        s = plate_strength(grade, d)
        Ab = math.pi * d * d / 4
        rows.append(_ratio_row("Threaded rod (tensile rupture of the threads)", "AISC 360-16 J3.6, Table J3.2 (Fnt = 0.75 Fu)", T, PHI_ROD * 0.75 * s["Fu"] * Ab / 1000,
                               note=f"0.75 × 0.75 × {s['Fu']:g} × {Ab:.1f} mm² (Ab, nominal body)"))
        rows.append(_ratio_row("Tension yielding (rod body)", "AISC 360-16 Eq. D2-1", T, PHI_T_YIELD * s["Fy"] * Ab / 1000, note=f"0.90 × {s['Fy']:g} × {Ab:.1f}"))
    elif an:
        b, t = float(an.group(1)), float(an.group(2))
        s = plate_strength(grade, t)
        p = angle_props(b, t)
        dh = HOLE.get(bolt, 18.0)
        An = p["A"] - dh * t
        Ae = U_ANGLE * An
        rows.append(_ratio_row("Tension yielding (gross)", "AISC 360-16 Eq. D2-1", T, PHI_T_YIELD * s["Fy"] * p["A"] / 1000, note=f"0.90 × {s['Fy']:g} × {p['A']:.1f} mm²"))
        rows.append(_ratio_row("Tension rupture (net, shear lag)", "AISC 360-16 Eq. D2-2, D3-1, Table D3.1 case 8", T, PHI_T_RUPT * s["Fu"] * Ae / 1000,
                               note=f"0.75 × {s['Fu']:g} × U {U_ANGLE} × An {An:.1f} (one {dh:g} mm hole) — U a placeholder until Phase 5 details the joint"))
        sl = L / p["r_min"]
        rows.append({"name": "Slenderness L / r (tension member, preferred ≤ 300)", "reference": "AISC 360-16 D1 user note", "demand": round(sl, 1),
                     "capacity": 300.0, "ratio": round(sl / 300, 4), "unit": "", "note": f"r_min {p['r_min']:.2f} mm (rectangles, radii ignored)", "advisory": True})
    else:
        raise ValueError(f"no tension check for brace profile {profile!r} (rods RD<d>, equal angles L<b>x<t>)")
    gov = max((r for r in rows if not r.get("advisory")), key=lambda r: r["ratio"])
    return {"profile": profile, "grade": grade, "T": round(T, 3), "checks": rows, "ratio": gov["ratio"], "governing": gov["name"],
            "passed": all(r["ratio"] <= 1.0 for r in rows if not r.get("advisory"))}


# --------------------------------------------------------------------------------------------- the step

def _design_row(meta: dict, inp: MemberDesignInput) -> dict:
    d = check_member(inp)
    f = lambda v, n=3: round(float(v), n)                            # plain floats (JSON)
    return {**{k: (list(v) if isinstance(v, tuple) else v) for k, v in meta.items() if k not in ("sets", "cc")}, "ratio": f(d.utilisation, 4), "passed": bool(d.passed),
            "combo": d.governing_combination, "x": f(d.forces.station, 1), "governing": d.governing_check.name if d.governing_check else None,
            "forces": {"P": f(d.forces.P), "V": f(d.forces.Vy), "M": f(d.forces.Mz)},
            "checks": [{**r, **{k: float(r[k]) for k in ("demand", "capacity", "ratio")}} for r in (_check_row(c) for c in d.checks)]}


def secondary_checks(b: BuildingInput, li, *, supplier: dict | None = None, limits=None, uplift_method: str = "strict") -> dict:
    """Steps 5 and 6 for a building: every wind column, end rafter and brace type, and (step 6) every purlin, girt and
    eave-strut line. Runs the analyses it needs."""
    b, _ = resolve(b)
    out = peb_building(b)
    sec = secondary_kpa(out)
    ends = {e["end"]: e for e in out["end_walls"]}
    efs = {end: end_rafter_frame(out, end, li, roof_secondary_kpa=sec["roof_kpa"], wall_secondary_kpa=sec["wall_kpa"])
           for end, e in ends.items() if e["kind"] == "rafter"}
    wcs = [_design_row(meta, inp) for meta, inp in wind_column_inputs(out, li, efs)]
    ers = [_design_row(meta, inp) for ef in efs.values() for meta, inp in end_rafter_inputs(out, ef)]
    braces = [m for m in out["members"] if m["role"] in ("roof_brace", "wall_brace")]
    bs = longitudinal_bracing(_geom(out["input"]), braces, [j - 1 for j in out["braced_bays"]], longitudinal_feed(out, li))["sets"]["LRFD"]
    rows = []
    for role, T in (("roof_brace", bs["roof_diagonal"]), ("wall_brace", bs["wall_diagonal"])):
        ms = [m for m in braces if m["role"] == role]
        if ms:
            m = max(ms, key=lambda x: x["length"])
            rows.append({"what": role.replace("_", " "), "members": len(ms), **tension_check(m["profile"], m.get("material", "S355"), T, m["length"], b.bolt)})
    for end, ef in efs.items():
        T, bid = max(((v, k) for r in ef["results"].values() if r["set"] == "LRFD" for k, v in r["braces"].items()), default=(0.0, None))
        m = next((x for x in out["members"] if x["id"] == bid), None)
        if m:
            L = math.dist(m["start"], m["end"])
            rows.append({"what": f"end-wall brace ({end} end)", "members": sum(1 for x in out["members"] if x["role"] == "endwall_brace" and x.get("wall") == end),
                         **tension_check(m["profile"], m.get("material", "S355"), T, L, b.bolt)})
    cf = cfs_checks(b, li, supplier=supplier, limits=limits, out=out, uplift_method=uplift_method)
    allr = [r["ratio"] for r in wcs + ers + rows] + ([cf["max_ratio"]] if cf["max_ratio"] is not None else [])
    return {"banner": BANNER, "code": "AISC 360-16 LRFD; cold-formed AISI S100-16 (DSM)", "wind_columns": wcs, "end_rafters": ers,
            "bracing": rows, "eave_struts": cf["eave_struts"], "cold_formed": cf, "max_ratio": max(allr) if allr else None,
            "designed": False}
