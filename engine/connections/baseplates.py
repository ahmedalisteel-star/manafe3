# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 2 / 2b: column base plates and anchor rods (main-frame and wind-column bases). NOT FOR ISSUE.

The engineering is bimsteelauto_connections (0.15.2 adds anchor grade ISO 4.6 and plate grades St 37 / 44 / 52 at the
user's request, 2026-11-11 — the relations themselves unchanged):
    design_base_plate   AISC Design Guide 1, 2nd ed. Sect. 3.1–3.4 with AISC 360-16 J8: bearing, the eccentricity cases,
                        net uplift, plate thickness (bearing interface Eq. 3.3.14 / 3.3.15; tension interface Eq. 3.4.5 –
                        3.4.7 for rods OUTSIDE the flanges)
    check_anchors       ACI 318-19 Ch. 17 cast-in HEADED anchors: steel, breakout, pullout (head / nut bearing area),
                        side-face blowout (tension); steel, breakout, pryout (shear); interaction 17.8
Manafe3 adds (this module):
    the joints and their forces (step 1: bases are designed for the analysis force alone — the capacity rule is for
    knee / ridge / splice only, user decision 2026-11-11); the cases per base: largest compression with its H, largest
    uplift with its H, largest |H| with its V (wind columns: the largest P / uplift with the largest V — conservative pairing)
    the rod layout, plate size and the sizing loop
    the plate in bending under uplift for rods INSIDE the flanges (user decision 2026-11-11): inside_rod_plate()
    ANCHOR REINFORCEMENT as the first fix when the concrete breakout in shear fails (step 2b, user decision 2026-11-11):
    anchor_reinforcement()

User decisions (2026-11-10 / 11):
    anchor grade default ISO 4.6 (metric rods M16 … M36); F1554 grades only with INCH rods (5/8 … 1-1/2 in.); concrete
        default C30/37 → f'c = fck = 30 MPa (cylinder, EN 206 Table 12)
    anchor type HEADED (hex head or heavy hex nut at the embedded end — the library's pullout uses that bearing area);
        hooked anchors are not covered and are refused
    minimum rod and embedment: main-frame columns M20 and 300 mm, wind columns M16 and 150 mm; embedment in 50 mm steps
        (all editable settings)
    pedestal size = the user's input per building; BLANK → the anchors' concrete modes read NOT EVALUATED; the rods are
        then sized on their steel strength alone and say so. Never an invented pedestal.
    rod layout per building: "inside" (default — 2 rods each side of the web, between the flanges) or "outside"
    shear: the anchors in shear (ACI 17.7), NO friction credit; plate washers WELDED to the base plate (stated on every
        result and carried to the detail); shear breakout failing → anchor reinforcement first; pryout or anything else
        failing → the result names it and suggests the fixes; shear lug: step 4 (with the column-to-plate weld)
    St 37 / 44 / 52 plates: the library's ECP values (from the ecp205-lrfd library)

Claude's detailing rules — ACCEPTED by the user 2026-11-11 (except the embedment, now as above); constants, editable:
    rods 4 per base; holes / plate washers AISC DG 1 Table 2.3 (the next inch rod size up); clearance rod centre to a
    steel face c = washer / 2 + WELD (8) + 5, rounded up to 5; spacing ≥ 4 d (ACI 318-19 17.9.1) and ≥ washer + 10;
    inside: s_x = max(tw + 2c, 4d, washer + 10) across the web, s_y = max(4d, washer + 10) along it, fitting between the
    flanges (s_y/2 + c ≤ d/2 − tf), plate = footprint + 25 each side; outside: s_d = d + 2c, s_b = max(bf, 4d), plate
    edge c; embedment up to the pedestal depth − HEF_COVER (100); A2/A1 from the largest similar rectangle in the
    pedestal (≤ 4). Plate palette = the library's (12 … 70 mm).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from bimsteelauto_connections import (AnchorGroup, BasePlateGeometry, check_anchors, design_base_plate)
from bimsteelauto_connections.anchors import ANCHOR_GRADES, GRADE_SOURCES, THREAD_AREA
from bimsteelauto_connections.anchors import VERIFIED as ANCHORS_VERIFIED
from bimsteelauto_connections.baseplate import DEFAULT_PLATE_PALETTE
from bimsteelauto_connections.baseplate import VERIFIED as BASEPLATE_VERIFIED
from bimsteelauto_connections.bolts import get_grade

BANNER = "NOT FOR ISSUE — base plates and anchors (Phase 5 step 2); the inside-rod plate model and anchor reinforcement TO CONFIRM"
METRIC_RODS = (16.0, 20.0, 24.0, 27.0, 30.0, 36.0)
#: inch rods (mm) → label; the library's THREAD_AREA has their UNC tensile stress areas
INCH_RODS = {15.875: '5/8"', 19.05: '3/4"', 22.225: '7/8"', 25.4: '1"', 28.575: '1-1/8"', 31.75: '1-1/4"', 38.1: '1-1/2"'}
WELD = 8.0                   # mm, assumed column-to-plate fillet leg for the rod clearance (the weld: step 4)
PLATE_MARGIN = 25.0          # mm each side, inside layout
PHI_B = 0.90
PHI_ANCHOR_REINF = 0.75      # ACI 318-19 17.5.2.1 (anchor reinforcement) — clause TO CONFIRM against the printed code
HAIRPIN_BARS = (10.0, 12.0, 16.0, 20.0)
HAIRPIN_MAX = 4              # hairpins per base (2 legs each)
ANCHOR_TYPE = ("headed: hex head or heavy hex nut at the embedded end; pullout from its bearing area (ACI 318-19 "
               "17.6.3.2.2(a)); hooked anchors are not covered")
WASHER_NOTE = ("Plate washers WELDED to the base plate (user decision 2026-11-11): the anchor rods take the base shear "
               "(ACI 318-19 17.7) with no friction credit; carry this note to the base plate detail.")
#: AISC DG 1 2nd ed. Table 2.3 [rod, hole, min. washer dimension, min. washer thickness], inches — as tabulated in the
#: upstream app (app/connections.js DG1_TABLE_2_3), NOT re-read from the printed guide (VERIFIED False). Its last row
#: repeats the 2 in. hole for 2-1/2 in. rods (a likely slip there); rods up to 1-1/2 in. / M36 never reach it.
DG1_TABLE_2_3 = ((0.75, 1 + 5 / 16, 2, 0.25), (0.875, 1 + 9 / 16, 2.5, 5 / 16), (1, 1 + 13 / 16, 3, 0.375), (1.25, 2 + 1 / 16, 3, 0.5),
                 (1.5, 2 + 5 / 16, 3.5, 0.5), (1.75, 2.75, 4, 0.625), (2, 3.25, 5, 0.75))
#: frame grade → the library's plate grade name; grades it does not list read NOT EVALUATED (no invented mapping)
PLATE_GRADE = {"S275": "S275JR", "S355": "S355JR", "A572 Gr 50": "A572-50", "St 37": "St 37", "St 44": "St 44", "St 52": "St 52"}
CONCRETE_FC = {"C25/30": 25.0, "C30/37": 30.0, "C35/45": 35.0}     # f'c = fck (cylinder), EN 206 Table 12
VERIFIED = {"inside_rod_plate": False, "dg1_table_2_3": False, "anchor_reinforcement": False, "interaction_with_reinforcement": False}
LAYOUTS = ("inside", "outside")


@dataclass
class BaseSettings:
    """Per building. pedestal = {"along_d": mm, "across": mm, "depth": mm} or None (anchor concrete modes NOT EVALUATED)."""
    anchor_grade: str = "4.6"
    anchor_type: str = "headed"
    concrete: str = "C30/37"
    layout: str = "inside"
    pedestal: dict | None = None
    cracked: bool = True
    rod_min_frame: float = 20.0
    rod_min_wind: float = 16.0
    hef_min_frame: float = 300.0
    hef_min_wind: float = 150.0
    hef_step: float = 50.0
    hef_cover: float = 100.0
    anchor_reinforcement: bool = True
    rebar_fy: float = 500.0          # B500 (BS 4449), the Job units bars

    def check(self) -> "BaseSettings":
        if self.anchor_grade not in ANCHOR_GRADES:
            raise ValueError(f"anchor grade {self.anchor_grade!r}: known {', '.join(ANCHOR_GRADES)}")
        if self.anchor_type != "headed":
            raise ValueError("anchor type: only 'headed' is covered (the library has no hooked-anchor pullout)")
        if self.concrete not in CONCRETE_FC:
            raise ValueError(f"concrete {self.concrete!r}: known {', '.join(CONCRETE_FC)}")
        if self.layout not in LAYOUTS:
            raise ValueError(f"layout must be one of {LAYOUTS}")
        for k in ("rod_min_frame", "rod_min_wind", "hef_min_frame", "hef_min_wind", "hef_step", "hef_cover", "rebar_fy"):
            if not (isinstance(getattr(self, k), (int, float)) and getattr(self, k) > 0):
                raise ValueError(f"{k} must be > 0")
        if self.pedestal is not None:
            p = self.pedestal
            if set(p) != {"along_d", "across", "depth"} or not all(isinstance(p[k], (int, float)) and p[k] > 0 for k in p):
                raise ValueError("pedestal = {along_d, across, depth} in mm, all > 0 (or leave it blank)")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "BaseSettings":
        d = dict(d or {})
        bad = set(d) - set(cls.__dataclass_fields__)
        if bad:
            raise ValueError(f"unknown base-plate settings: {', '.join(sorted(bad))}")
        return cls(**d).check()

    @property
    def fc(self) -> float:
        return CONCRETE_FC[self.concrete]

    @property
    def inch(self) -> bool:
        return self.anchor_grade.upper().startswith("F1554")

    def rods(self, role: str) -> list[float]:
        lst = list(INCH_RODS) if self.inch else list(METRIC_RODS)
        dmin = self.rod_min_frame if role == "frame" else self.rod_min_wind
        return [d for d in lst if d >= dmin - 1e-9]

    def hefs(self, role: str):
        if not self.pedestal:
            return [None]
        h = self.hef_min_frame if role == "frame" else self.hef_min_wind
        out = []
        while h <= self.pedestal["depth"] - self.hef_cover + 1e-9:
            out.append(h)
            h += self.hef_step
        return out


def rod_label(d: float) -> str:
    return INCH_RODS.get(d, f"M{d:g}")


def dg1_row(d_rod: float) -> dict:
    for r in DG1_TABLE_2_3:
        if r[0] * 25.4 >= d_rod - 0.5:
            return {"rod_in": r[0], "hole": round(r[1] * 25.4, 1), "washer": round(r[2] * 25.4, 1), "washer_t": round(r[3] * 25.4, 1)}
    raise ValueError(f"rod {d_rod} mm is beyond DG 1 Table 2.3")


def _up5(v: float) -> float:
    return math.ceil(v / 5.0 - 1e-9) * 5.0


def clearance(d_rod: float) -> float:
    return _up5(dg1_row(d_rod)["washer"] / 2 + WELD + 5.0)


def layout_geometry(sec: dict, d_rod: float, layout: str) -> dict:
    """Rod spacings and plate size for a column section {d, bf, tf, tw}; fits False when the rods do not fit."""
    d, bf, tf, tw = sec["d"], sec["bf"], sec["tf"], sec["tw"]
    row = dg1_row(d_rod)
    c = clearance(d_rod)
    smin = max(4 * d_rod, row["washer"] + 10.0)
    if layout == "inside":
        s_x = _up5(max(tw + 2 * c, smin))                        # across the web
        s_y = _up5(smin)                                          # along the web (column depth)
        fits = s_y / 2 + c <= d / 2 - tf + 1e-9
        N, B = _up5(d + 2 * PLATE_MARGIN), _up5(bf + 2 * PLATE_MARGIN)
        return {"layout": layout, "fits": fits, "c": c, "s_along_d": s_y, "s_across": s_x, "N": N, "B": B,
                "f": s_y / 2, "lever_to_web": s_x / 2 - tw / 2, "clear_between_flanges": d - 2 * tf, **row,
                **({} if fits else {"why": f"s/2 + c = {s_y / 2 + c:.0f} > d/2 - tf = {d / 2 - tf:.0f}: the rods do not fit between the flanges"})}
    s_d = _up5(d + 2 * c)
    s_b = _up5(max(bf, smin))
    return {"layout": layout, "fits": True, "c": c, "s_along_d": s_d, "s_across": s_b, "N": _up5(s_d + 2 * c), "B": _up5(s_b + 2 * c),
            "f": s_d / 2, **row}


def inside_rod_plate(T_rod: float, lever: float, s_along: float, clear_between_flanges: float, Fy: float) -> dict:
    """Base plate in bending under the tension of rods INSIDE the flanges (user decision 2026-11-11).

    The plate cantilevers from the web face; lever = rod centre to the web face; each rod's tension spreads at 45° to the
    web, so one rod engages 2 × lever of plate at the web; the two rods on one side of the web share the union of their
    patches, limited by the clear depth between the flanges: b_side = min(2 lever + s_along, d − 2 tf), b_eff = b_side / 2
    per rod. The flanges' support of the plate is ignored (conservative). Plastic moment of the plate strip, as DG 1
    Eq. 3.4.5 / 3.4.7 for the outside case: φ Fy b_eff t² / 4 ≥ T_rod × lever → t_req = √(4 T lever / (φ Fy b_eff)).
    Source: AISC Design Guide 1, 2nd ed., Sect. 3.2 / Example 4.6 — the user confirms from the printed guide; until then
    VERIFIED False. T_rod kN, lengths mm, Fy MPa → t_req mm."""
    if lever <= 0:
        raise ValueError("rod lever to the web face must be > 0")
    b_side = min(2 * lever + s_along, clear_between_flanges)
    b_eff = b_side / 2
    t = math.sqrt(4 * T_rod * 1000 * lever / (PHI_B * Fy * b_eff)) if T_rod > 0 else 0.0
    return {"T_rod": T_rod, "lever": lever, "b_eff": b_eff, "b_side": b_side, "t_req": t,
            "rule": "cantilever from the web face, 45 deg spread, phi Fy b_eff t^2/4 >= T x lever (DG 1 Sect. 3.2 / Ex. 4.6, TO CONFIRM)"}


def development_length(db: float, fy: float, fc: float) -> float:
    """ACI 318-19 25.4.2.3 (simplified, Table 25.4.2.3): straight bar in tension, normal-weight concrete (λ 1), uncoated
    (ψe 1), not top bar (ψt 1); ψg 1.15 for fy above 420 MPa (B500 → the Grade 550 row, conservative); db ≤ 20 mm:
    ld = fy ψt ψe ψg db / (2.1 λ √f'c), larger bars / 1.7; ≥ 300 mm. The Table's spacing / cover conditions are ASSUMED
    met — TO CHECK in the pedestal detail."""
    psi_g = 1.0 if fy <= 420.0 else (1.15 if fy <= 550.0 else 1.3)
    k = 2.1 if db <= 20.0 else 1.7
    return max(fy * psi_g * db / (k * math.sqrt(fc)), 300.0)


def anchor_reinforcement(Vua: float, fy: float, fc: float) -> dict | None:
    """Hairpins / ties that take the base shear instead of the concrete breakout (ACI 318-19 17.5.2.1(b) — anchor
    reinforcement for shear; φ 0.75; clause numbering TO CONFIRM against the printed code). The fewest hairpins (2 legs
    each, ≤ HAIRPIN_MAX), then the smallest bar, with φ As fy ≥ Vua. Required by the clause and NOT checked here (stated on
    the result): the legs within 0.5 ca1 of the anchors, developed on both sides of the breakout surface (ld below)."""
    as_req = Vua * 1000.0 / (PHI_ANCHOR_REINF * fy)
    for n in range(1, HAIRPIN_MAX + 1):
        for db in HAIRPIN_BARS:
            As = n * 2 * math.pi * db * db / 4
            if As + 1e-9 >= as_req:
                return {"hairpins": n, "legs": 2 * n, "bar": db, "As": round(As, 1), "As_req": round(as_req, 1),
                        "phiVn": round(PHI_ANCHOR_REINF * As * fy / 1000.0, 3), "fy": fy, "phi": PHI_ANCHOR_REINF,
                        "ld": round(development_length(db, fy, fc), 0),
                        "clause": "ACI 318-19 17.5.2.1(b) anchor reinforcement for shear (TO CONFIRM)",
                        "to_check": ["legs within 0.5 ca1 of the anchor rods (R17.5.2.1)",
                                     "each leg developed (ld) on both sides of the breakout surface (ACI 318-19 Ch. 25)",
                                     "the Table 25.4.2.3 spacing / cover conditions assumed for ld"]}
    return None


def interaction_17_8(ut: float, uv: float) -> tuple[float, str]:
    """ACI 318-19 17.8 (the linear rule 17.8.3, as the library uses it): ut = Nua/φNn, uv = Vua/φVn."""
    if uv <= 0.2:
        return ut, "17.8.1: Vua <= 0.2 phiVn, full tension"
    if ut <= 0.2:
        return uv, "17.8.2: Nua <= 0.2 phiNn, full shear"
    return (ut + uv) / 1.2, "17.8.3 linear: (Nua/phiNn + Vua/phiVn) <= 1.2"


def _A2_A1(N: float, B: float, ped: dict | None) -> float:
    if not ped:
        return 1.0
    k = min(ped["along_d"] / N, ped["across"] / B)
    return max(1.0, min(k * k, 4.0))


def _group(geo: dict, d_rod: float, hef: float, ped: dict | None, cracked: bool) -> AnchorGroup:
    if ped:
        ca_d = (ped["along_d"] - geo["s_along_d"]) / 2
        ca_b = (ped["across"] - geo["s_across"]) / 2
        ha = ped["depth"]
    else:
        ca_d = ca_b = 10_000.0
        ha = None
    # x = across the web (the building's length), y = along the column depth (the frame's span — the shear direction)
    return AnchorGroup(d=d_rod, hef=hef, n_x=2, n_y=2, s_x=geo["s_across"], s_y=geo["s_along_d"], ca_x1=ca_b, ca_x2=ca_b,
                       ca_y1=ca_d, ca_y2=ca_d, cracked=cracked, grout_pad=True, ha=ha)


FIXES = {"breakout": "anchor reinforcement (hairpins or ties) first, then a larger edge distance / pedestal, or a shear lug (step 4)",
         "pryout": "a deeper embedment, a larger edge distance / pedestal, anchor reinforcement, or a shear lug (step 4)"}


def _concrete_fixes(chk) -> list[str]:
    out = []
    for name, cap, u in chk.shear:
        low = name.lower()
        if u > 1.0 and ("breakout" in low or "pryout" in low):
            kind = "breakout" if "breakout" in low else "pryout"
            out.append(f"shear {kind} fails ({name}, U = {u:.2f}): {FIXES[kind]}")
    for name, cap, u in chk.tension:
        if u > 1.0 and "steel" not in name.lower():
            out.append(f"tension {name} fails (U = {u:.2f}): a deeper embedment, a larger pedestal or anchor reinforcement")
    return out


def _cases(j: dict) -> list[dict]:
    F = j["forces"]
    if j["type"] == "base":
        out = [{"name": "max compression", "Pu": F["compression"]["value"], "Vu": abs(F["compression"].get("H", 0.0)),
                "Mu": abs(F["compression"].get("M", 0.0)), "combo": F["compression"]["combo"]}]
        if F["uplift"]["combo"]:
            out.append({"name": "max uplift", "Pu": -F["uplift"]["value"], "Vu": abs(F["uplift"]["H"]), "Mu": abs(F["uplift"]["M"]),
                        "combo": F["uplift"]["combo"]})
        s = F["shear"]
        if s["combo"]:
            out.append({"name": "max shear", "Pu": s["V"], "Vu": s["value"], "Mu": abs(s["M"]), "combo": s["combo"]})
        return out
    out = [{"name": "max compression + max shear (paired conservatively)", "Pu": F["P_comp"], "Vu": F["V_out_of_plane"], "Mu": 0.0,
            "combo": "envelope"}]
    if F.get("uplift", 0.0) > 0:
        out.append({"name": "max uplift + max shear (paired conservatively)", "Pu": -F["uplift"], "Vu": F["V_out_of_plane"],
                    "Mu": 0.0, "combo": "envelope"})
    return out


def _steel_ok(chk) -> bool:
    return all(u <= 1.0 for n, c, u in chk.tension + chk.shear if "steel" in n.lower())


def _with_reinforcement(checks: list, st: BaseSettings) -> dict | None:
    """When ONLY the shear breakout fails: hairpins replace it; the rest must pass, and 17.8 is re-run with
    φVn = min(rod steel, anchor reinforcement, pryout). None when that does not make every case pass."""
    for _, chk in checks:
        for n, c, u in chk.tension + chk.shear:
            if u > 1.0 and "17.7.2" not in n:
                return None
    vmax = max(chk.Vua for _, chk in checks)
    ar = anchor_reinforcement(vmax, st.rebar_fy, st.fc)
    if ar is None:
        return None
    rows = []
    for cs, chk in checks:
        phiVn = min([c for n, c, u in chk.shear if "17.7.2" not in n] + [ar["phiVn"]])
        ut = chk.Nua / chk.phiNn if chk.phiNn > 0 else math.inf
        uv = chk.Vua / phiVn if phiVn > 0 else math.inf
        inter, rule = interaction_17_8(ut, uv)
        if uv > 1.0 or inter > 1.0:
            return None
        rows.append({"case": cs["name"], "phiVn_with_reinforcement": round(float(phiVn), 3), "interaction": round(float(inter), 4),
                     "rule": rule})
    return {**ar, "cases": rows}


def _anchor_row(cs: dict, chk, with_pedestal: bool, reinf: dict | None = None) -> dict:
    rows = [{"mode": n, "phiRn": round(float(c), 2), "U": round(float(u), 4), "kind": "tension"} for n, c, u in chk.tension] + \
           [{"mode": n, "phiRn": round(float(c), 2), "U": round(float(u), 4), "kind": "shear"} for n, c, u in chk.shear]
    if not with_pedestal:
        rows = [r for r in rows if "steel" in r["mode"].lower()]
    out = {"case": cs["name"], "Nua": round(float(chk.Nua), 3), "Vua": round(float(chk.Vua), 3), "modes": rows,
           "interaction": round(float(chk.interaction), 4) if with_pedestal else None,
           "status": ("EVALUATED" if with_pedestal else "NOT EVALUATED (no pedestal: concrete modes not checked; rod steel only)"),
           "passed": bool(chk.passed if with_pedestal else _steel_ok(chk)),
           "fixes": _concrete_fixes(chk) if with_pedestal else [], "warnings": list(chk.warnings)}
    if reinf:
        r = next(x for x in reinf["cases"] if x["case"] == cs["name"])
        out.update(passed=True, interaction=r["interaction"], interaction_rule=r["rule"], fixes=[],
                   shear_breakout="replaced by the anchor reinforcement (ACI 318-19 17.5.2.1(b), TO CONFIRM)")
    return out


def _try(sec: dict, cases: list[dict], d_rod: float, st: BaseSettings, plate_grade: str, role: str) -> dict:
    geo = layout_geometry(sec, d_rod, st.layout)
    if not geo["fits"]:
        return {"ok": False, "geometry": geo, "why": geo["why"]}
    ped = st.pedestal
    gm = BasePlateGeometry(N=geo["N"], B=geo["B"], d=sec["d"], bf=sec["bf"], f=geo["f"], A2_over_A1=_A2_A1(geo["N"], geo["B"], ped),
                           tf=sec["tf"])
    t, plates, inside = 0.0, [], []
    for cs in cases:
        bp = design_base_plate(Pu=cs["Pu"], Mu=cs["Mu"], Vu=cs["Vu"], geom=gm, plate_grade=plate_grade, fc_prime=st.fc)
        T_group = float(bp.T_anchor)
        n_tension = 4 if cs["Mu"] == 0 else 2
        cs_out = {**cs, "case": bp.case.value, "t_bearing_or_DG1": float(bp.t_selected), "T_anchor": round(T_group, 3),
                  "bearing_U": round(float(bp.bearing_utilization), 4), "phiPp": round(float(bp.phiPp), 2), "warnings": list(bp.warnings)}
        t = max(t, float(bp.t_selected))
        if st.layout == "inside" and T_group > 0:
            ip = inside_rod_plate(T_group / n_tension, geo["lever_to_web"], geo["s_along_d"], geo["clear_between_flanges"],
                                  get_grade(plate_grade, max(t, 12.0))[0])
            cs_out["inside_plate"] = ip
            inside.append(ip["t_req"])
        cs_out["T_rod"] = round(T_group / n_tension, 3)
        plates.append(cs_out)
    t_inside = max(inside, default=0.0)
    t_sel = next((x for x in sorted(DEFAULT_PLATE_PALETTE) if x + 1e-9 >= max(t, t_inside)), None)
    if t_sel is None:
        return {"ok": False, "geometry": geo, "why": "no plate in the palette is thick enough"}
    hefs = st.hefs(role)
    if ped and not hefs:
        hmin = st.hef_min_frame if role == "frame" else st.hef_min_wind
        return {"ok": False, "geometry": geo, "why": f"pedestal depth {ped['depth']} mm − cover {st.hef_cover:g} leaves no embedment ≥ {hmin:g} mm"}
    best = None
    for hef in hefs:
        checks = []
        for cs in plates:
            g = _group(geo, d_rod, hef or 300.0, ped, st.cracked)
            checks.append((cs, check_anchors(Nua=max(cs["T_anchor"], 0.0), Vua=cs["Vu"], group=g, grade=st.anchor_grade, fc_prime=st.fc)))
        reinf = None
        if ped:
            ok = all(chk.passed for _, chk in checks)
            if not ok and st.anchor_reinforcement:
                reinf = _with_reinforcement(checks, st)
                ok = reinf is not None
        else:                                                      # steel modes only (no pedestal: concrete NOT EVALUATED)
            ok = all(_steel_ok(chk) for _, chk in checks)
        best = (hef, checks, ok, reinf)
        if ok:
            break
    hef, checks, ok, reinf = best
    return {"ok": ok, "geometry": geo, "t": t_sel, "t_inside": round(t_inside, 2), "hef": hef, "cases": plates,
            "anchors": [_anchor_row(cs, chk, bool(ped), reinf) for cs, chk in checks], "A2_A1": round(gm.A2_over_A1, 4),
            "anchor_reinforcement": reinf}


def _steel_ok_row(a: dict) -> bool:
    return all(m["U"] <= 1.0 for m in a["modes"] if "steel" in m["mode"].lower())


def design_base(j: dict, sec: dict, frame_grade: str, st: BaseSettings, extra_cases: list[dict] | None = None) -> dict:
    """One base joint (from step 1, with forces) → the designed plate and rods, or NOT EVALUATED / FAILS with the reason.
    extra_cases (open item 6): the braced-bay pairs {name, combo, Pu, Vu} — Vu the vector sum of the strong- and weak-axis
    shears (the anchors take both)."""
    role = "frame" if j["type"] == "base" else "wind"
    out = {"joint": j["id"], "type": j["type"], "member": j["members"][0]["id"], "section": sec, "settings": asdict(st),
           "anchor_type": ANCHOR_TYPE, "notes": [WASHER_NOTE]}
    if st.anchor_grade in GRADE_SOURCES:
        out["anchor_grade_source"] = dict(GRADE_SOURCES[st.anchor_grade])
    if j.get("status") != "EVALUATED" or not j.get("forces"):
        return {**out, "status": "NOT EVALUATED", "missing": j.get("missing", ["no forces at this base"])}
    pg = PLATE_GRADE.get(frame_grade)
    if pg is None:
        return {**out, "status": "NOT EVALUATED",
                "missing": [f"plate grade {frame_grade!r} is not in bimsteelauto_connections ({', '.join(PLATE_GRADE)})"]}
    cases = _cases(j) + list(extra_cases or [])
    tries = []
    for d_rod in st.rods(role):
        r = _try(sec, cases, d_rod, st, pg, role)
        tries.append((d_rod, r))
        if r["ok"]:
            break
    d_rod, r = tries[-1]
    if not r["ok"]:
        # nothing passes: report the SMALLEST rod whose steel passes (at the deepest embedment that fits) — the concrete
        # modes barely depend on the rod size, so the largest rod would only hide the real fix
        steel = [(d, t) for d, t in tries if "anchors" in t and all(_steel_ok_row(a) for a in t["anchors"])]
        if steel:
            d_rod, r = steel[0]
    ped = st.pedestal is not None
    res = {**out, "plate_grade": pg, "rod": {"d": d_rod, "label": rod_label(d_rod), "n": 4, "grade": st.anchor_grade,
                                             "thread_area": THREAD_AREA.get(d_rod)},
           **{k: v for k, v in r.items() if k != "ok"}}
    if not r["ok"]:
        res.update(status="FAILS" if "cases" in r else "NOT EVALUATED",
                   missing=[r.get("why") or f"no rod {rod_label(st.rods(role)[0])} … {rod_label(st.rods(role)[-1])} with an embedment that fits the pedestal passes every case"])
        if "anchors" in r:
            res["fixes"] = sorted({f for a in r["anchors"] for f in a["fixes"]})
        return res
    if not ped:
        res["status"] = "PLATE DESIGNED - ANCHORS NOT EVALUATED"
        res["missing"] = ["pedestal size (the user's input per building): the anchors' concrete modes are NOT EVALUATED"]
    elif r.get("anchor_reinforcement"):
        res["status"] = "DESIGNED WITH ANCHOR REINFORCEMENT - DEVELOPMENT NOT EVALUATED"
        res["missing"] = r["anchor_reinforcement"]["to_check"]
    else:
        res["status"] = "DESIGNED"
    g = r["geometry"]
    res["app_params"] = {"length": g["N"], "width": g["B"], "tp": r["t"], "rodD": d_rod, "hole": g["hole"],
                         "sx": g["s_along_d"], "sy": g["s_across"], "embed": r["hef"], "grade": st.anchor_grade,
                         "plateGrade": pg, "washers": 1, "washerSize": g["washer"], "washerT": g["washer_t"], "layout": st.layout,
                         "anchorType": "headed"}
    return res


def column_section(m: dict) -> dict:
    """The base section of a generated built-up column {d, bf, tf, tw} (bottom segment, its start)."""
    s = m["section"]["segments"][0]
    return {"d": s["hw_start"] + s["tf_top"] + s["tf_bot"], "bf": min(s["bf_top"], s["bf_bot"]),
            "tf": max(s["tf_top"], s["tf_bot"]), "tw": s["tw"]}


def building_bases(joints_result: dict, out: dict, settings: BaseSettings | None = None, analysis: dict | None = None,
                   flexible_diaphragm: bool | None = None) -> dict:
    """Every base joint of a building_joints() result → designed base plates. analysis (open item 6): the braced-bay
    bases also take the longitudinal pairs (frame reaction + the wall brace of the same combination)."""
    from .longitudinal import braced_base, building_record
    st = (settings or BaseSettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    rows = []
    for j in joints_result["joints"]:
        if j["type"] not in ("base", "wind_column_base"):
            continue
        m = mem[j["members"][0]["id"]]
        lon = braced_base(j, m, out, analysis, flexible_diaphragm) if analysis is not None else None
        extra = [{"name": c["name"], "combo": c["combo"], "Pu": c["Pu"], "Vu": round(math.hypot(c["V_strong"], c["V_weak"]), 3),
                  "Mu": 0.0} for c in (lon or {}).get("cases", [])]
        r = design_base(j, column_section(m), m.get("material", "S355"), st, extra)
        if lon is not None:
            r["longitudinal"] = lon
            if lon["status"] != "EVALUATED" and r["status"] not in ("NOT EVALUATED", "FAILS"):
                r["status"] = "PARTIAL - brace case NOT EVALUATED"
                r.setdefault("missing", []).append(lon["why"])
        rows.append(r)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "bases": rows, "counts": counts,
            **({"longitudinal": building_record(out, analysis, flexible_diaphragm)} if analysis is not None else {}),
            "anchor_type": ANCHOR_TYPE, "warnings": list(joints_result.get("warnings", [])), "notes": [WASHER_NOTE],
            "open_flags": sorted([f"engine.connections.baseplates.{k}" for k, v in VERIFIED.items() if not v]
                                 + [f"bimsteelauto_connections.anchors.GRADE_SOURCES[{k!r}]" for k, v in GRADE_SOURCES.items()
                                    if not v.get("checked_against_source")]),
            "library_flags": {"baseplate": dict(BASEPLATE_VERIFIED), "anchors": dict(ANCHORS_VERIFIED)}}
