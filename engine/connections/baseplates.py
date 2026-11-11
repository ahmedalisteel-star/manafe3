# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 2: column base plates and anchor rods (main-frame and wind-column bases). NOT FOR ISSUE.

The engineering is bimsteelauto_connections (v0.7.0, all flags closed, NOT modified):
    design_base_plate   AISC Design Guide 1, 2nd ed. Sect. 3.1–3.4 with AISC 360-16 J8: bearing, the eccentricity cases,
                        net uplift, plate thickness (bearing interface Eq. 3.3.14 / 3.3.15; tension interface Eq. 3.4.5 –
                        3.4.7 for rods OUTSIDE the flanges)
    check_anchors       ACI 318-19 Ch. 17 cast-in anchors: steel, breakout, pullout, side-face blowout (tension); steel,
                        breakout, pryout (shear); interaction 17.8.3
Manafe3 adds (this module):
    the joints and their forces (step 1: bases are designed for the analysis force alone — the capacity rule is for
    knee / ridge / splice only, user decision 2026-11-11); the cases per base: largest compression with its H, largest
    uplift with its H, largest |H| with its V (wind columns: the largest P / uplift with the largest V — conservative pairing)
    the rod layout, plate size and the sizing loop (Claude's detailing rules below — TO CONFIRM, editable)
    the plate in bending under uplift for rods INSIDE the flanges (user decision 2026-11-11): see inside_rod_plate()

User decisions (2026-11-10 / 11):
    anchor grade default F1554 Gr 36 (editable); concrete default C30/37 → f'c = fck = 30 MPa (cylinder, EN 206 Table 12)
    pedestal size = the user's input per building; BLANK → the anchor check (concrete modes) reads NOT EVALUATED; the
        rods are then sized on their steel strength alone and say so. Never an invented pedestal.
    rod layout per building: "inside" (default — 2 rods each side of the web, between the flanges) or "outside" (2 rods
        beyond each flange, the field-fix-10 layout)
    shear: the anchors in shear (ACI 17.7), NO friction credit; plate washers WELDED to the base plate (stated on every
        result and carried to the detail); breakout / pryout failing → the result names it and suggests the fixes
        (larger edge distance / pedestal, anchor reinforcement — hairpins or ties —, or a shear lug); no shear-lug check yet
    anchors DESIGNED: the smallest rod (ROD_SIZES) and then the shortest embedment that pass

Claude's detailing rules (TO CONFIRM with the user; constants below, editable):
    rods       4 per base, ISO metric thread areas (the library's THREAD_AREA) with the chosen grade's strengths —
               F1554 is supplied in inch sizes: TO CONFIRM which the user buys
    holes      AISC DG 1 Table 2.3 (the next inch rod size up), plate washers its minimum size / thickness
    clearance  rod centre to a steel face (web face, inner flange face) c = washer / 2 + WELD (8) + 5 mm, rounded up to 5
    spacing    ≥ 4 d (ACI 318-19 17.9.1, untorqued cast-in) and ≥ washer + 10 mm
    inside     across the web s_x = max(tw + 2c, 4d, washer + 10); along the web s_y = max(4d, washer + 10) — kept small,
               the base is analysed as a pin; it must fit between the flanges: s_y/2 + c ≤ d/2 − tf
               plate N = d + 2 × 25, B = bf + 2 × 25 (a weld margin), rounded up to 5 mm
    outside    along the depth s_d = d + 2c, across s_b = max(bf, 4d); plate N = s_d + 2e, B = s_b + 2e with e = c
    embedment  hef from HEF_MIN in HEF_STEP steps up to the pedestal depth − HEF_COVER
    pedestal   rods centred on it; A2/A1 = (the largest similar rectangle in the pedestal / the plate)², ≤ 4
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from bimsteelauto_connections import (AnchorGroup, BasePlateGeometry, check_anchors, design_base_plate)
from bimsteelauto_connections.anchors import ANCHOR_GRADES, THREAD_AREA
from bimsteelauto_connections.anchors import VERIFIED as ANCHORS_VERIFIED
from bimsteelauto_connections.baseplate import DEFAULT_PLATE_PALETTE
from bimsteelauto_connections.baseplate import VERIFIED as BASEPLATE_VERIFIED

BANNER = "NOT FOR ISSUE — base plates and anchors (Phase 5 step 2); detailing rules and the inside-rod plate model TO CONFIRM"
ROD_SIZES = (16.0, 20.0, 24.0, 27.0, 30.0, 36.0)
WELD = 8.0                   # mm, assumed column-to-plate fillet leg for the rod clearance (the weld itself: not checked yet)
PLATE_MARGIN = 25.0          # mm each side, inside layout
HEF_MIN, HEF_STEP, HEF_COVER = 150.0, 25.0, 100.0
PHI_B = 0.90
WASHER_NOTE = ("Plate washers WELDED to the base plate (user decision 2026-11-11): the anchor rods take the base shear "
               "(ACI 318-19 17.7) with no friction credit; carry this note to the base plate detail.")
#: AISC DG 1 2nd ed. Table 2.3 [rod, hole, min. washer dimension, min. washer thickness], inches — as tabulated in the
#: upstream app (app/connections.js DG1_TABLE_2_3), NOT re-read from the printed guide (VERIFIED False). Its last row
#: repeats the 2 in. hole for 2-1/2 in. rods (a likely slip there); rods up to M36 never reach it.
DG1_TABLE_2_3 = ((0.75, 1 + 5 / 16, 2, 0.25), (0.875, 1 + 9 / 16, 2.5, 5 / 16), (1, 1 + 13 / 16, 3, 0.375), (1.25, 2 + 1 / 16, 3, 0.5),
                 (1.5, 2 + 5 / 16, 3.5, 0.5), (1.75, 2.75, 4, 0.625), (2, 3.25, 5, 0.75))
#: frame grade → the library's plate grade name; grades the library does not list read NOT EVALUATED (no invented mapping)
PLATE_GRADE = {"S275": "S275JR", "S355": "S355JR", "A572 Gr 50": "A572-50"}
CONCRETE_FC = {"C25/30": 25.0, "C30/37": 30.0, "C35/45": 35.0}     # f'c = fck (cylinder), EN 206 Table 12
VERIFIED = {"inside_rod_plate": False, "dg1_table_2_3": False, "detailing_rules": False}
LAYOUTS = ("inside", "outside")


@dataclass
class BaseSettings:
    """Per building. pedestal = {"along_d": mm, "across": mm, "depth": mm} or None (anchor check NOT EVALUATED)."""
    anchor_grade: str = "F1554-36"
    concrete: str = "C30/37"
    layout: str = "inside"
    pedestal: dict | None = None
    cracked: bool = True

    def check(self) -> "BaseSettings":
        if self.anchor_grade not in ANCHOR_GRADES:
            raise ValueError(f"anchor grade {self.anchor_grade!r}: known {', '.join(ANCHOR_GRADES)}")
        if self.concrete not in CONCRETE_FC:
            raise ValueError(f"concrete {self.concrete!r}: known {', '.join(CONCRETE_FC)}")
        if self.layout not in LAYOUTS:
            raise ValueError(f"layout must be one of {LAYOUTS}")
        if self.pedestal is not None:
            p = self.pedestal
            if set(p) != {"along_d", "across", "depth"} or not all(isinstance(p[k], (int, float)) and p[k] > 0 for k in p):
                raise ValueError("pedestal = {along_d, across, depth} in mm, all > 0 (or leave it blank)")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "BaseSettings":
        d = dict(d or {})
        bad = set(d) - {"anchor_grade", "concrete", "layout", "pedestal", "cracked"}
        if bad:
            raise ValueError(f"unknown base-plate settings: {', '.join(sorted(bad))}")
        return cls(**d).check()

    @property
    def fc(self) -> float:
        return CONCRETE_FC[self.concrete]


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
    Source: AISC Design Guide 1, 2nd ed. — the section / example that gives the 45° effective width for rods inside
    the flanges is TO CONFIRM against the printed guide (believed the tensile-axial-load section, Sect. 3.2). VERIFIED False.
    T_rod kN, lengths mm, Fy MPa → t_req mm."""
    if lever <= 0:
        raise ValueError("rod lever to the web face must be > 0")
    b_side = min(2 * lever + s_along, clear_between_flanges)
    b_eff = b_side / 2
    t = math.sqrt(4 * T_rod * 1000 * lever / (PHI_B * Fy * b_eff)) if T_rod > 0 else 0.0
    return {"T_rod": T_rod, "lever": lever, "b_eff": b_eff, "b_side": b_side, "t_req": t,
            "rule": "cantilever from the web face, 45 deg spread, phi Fy b_eff t^2/4 >= T x lever (DG 1 form; section TO CONFIRM)"}


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


FIXES = {"breakout": "a larger edge distance / pedestal, anchor reinforcement (hairpins or ties), or a shear lug",
         "pryout": "a deeper embedment, a larger edge distance / pedestal, anchor reinforcement, or a shear lug"}


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


def _try(sec: dict, cases: list[dict], d_rod: float, st: BaseSettings, plate_grade: str) -> dict:
    geo = layout_geometry(sec, d_rod, st.layout)
    if not geo["fits"]:
        return {"ok": False, "geometry": geo, "why": geo["why"]}
    ped = st.pedestal
    gm = BasePlateGeometry(N=geo["N"], B=geo["B"], d=sec["d"], bf=sec["bf"], f=geo["f"], A2_over_A1=_A2_A1(geo["N"], geo["B"], ped),
                           tf=sec["tf"])
    t, plates, inside = 0.0, [], []
    for cs in cases:
        bp = design_base_plate(Pu=cs["Pu"], Mu=cs["Mu"], Vu=cs["Vu"], geom=gm, plate_grade=plate_grade, fc_prime=st.fc)
        T_group = bp.T_anchor
        n_tension = 4 if cs["Mu"] == 0 else 2
        cs_out = {**cs, "case": bp.case.value, "t_bearing_or_DG1": float(bp.t_selected), "T_anchor": round(float(T_group), 3),
                  "bearing_U": round(float(bp.bearing_utilization), 4), "phiPp": round(float(bp.phiPp), 2), "warnings": list(bp.warnings)}
        t = max(t, bp.t_selected)
        if st.layout == "inside" and T_group > 0:
            ip = inside_rod_plate(T_group / n_tension, geo["lever_to_web"], geo["s_along_d"], geo["clear_between_flanges"],
                                  _plate_fy(plate_grade, max(t, 12.0)))
            cs_out["inside_plate"] = ip
            inside.append(ip["t_req"])
        cs_out["T_rod"] = round(T_group / n_tension, 3)
        plates.append(cs_out)
    t_inside = max(inside, default=0.0)
    t_sel = _palette_at_least(max(t, t_inside), plate_grade)
    if t_sel is None:
        return {"ok": False, "geometry": geo, "why": "no plate in the palette is thick enough"}
    # anchors: every case, the smallest passing embedment
    hefs = [None] if not ped else list(_hefs(ped["depth"]))
    if ped and not hefs:
        return {"ok": False, "geometry": geo, "why": f"pedestal depth {ped['depth']} mm leaves no embedment ≥ {HEF_MIN:g} mm"}
    best = None
    for hef in hefs:
        checks = []
        for cs in plates:
            g = _group(geo, d_rod, hef or 300.0, ped, st.cracked)
            chk = check_anchors(Nua=max(cs["T_anchor"], 0.0), Vua=cs["Vu"], group=g, grade=st.anchor_grade, fc_prime=st.fc)
            checks.append((cs, chk))
        if ped:
            ok = all(chk.passed for _, chk in checks)
        else:                                                      # steel modes only (no pedestal: concrete NOT EVALUATED)
            ok = all(_steel_ok(chk) for _, chk in checks)
        best = (hef, checks, ok)
        if ok:
            break
    hef, checks, ok = best
    return {"ok": ok, "geometry": geo, "t": t_sel, "t_inside": round(t_inside, 2), "hef": hef, "cases": plates,
            "anchors": [_anchor_row(cs, chk, bool(ped)) for cs, chk in checks], "A2_A1": round(gm.A2_over_A1, 4)}


def _steel_ok_row(a: dict) -> bool:
    return all(m["U"] <= 1.0 for m in a["modes"] if "steel" in m["mode"].lower())


def _steel_ok(chk) -> bool:
    us = [u for n, c, u in chk.tension + chk.shear if "steel" in n.lower()]
    return all(u <= 1.0 for u in us)


def _anchor_row(cs: dict, chk, with_pedestal: bool) -> dict:
    rows = [{"mode": n, "phiRn": round(float(c), 2), "U": round(float(u), 4), "kind": "tension"} for n, c, u in chk.tension] + \
           [{"mode": n, "phiRn": round(float(c), 2), "U": round(float(u), 4), "kind": "shear"} for n, c, u in chk.shear]
    if not with_pedestal:
        rows = [r for r in rows if "steel" in r["mode"].lower()]
    return {"case": cs["name"], "Nua": round(float(chk.Nua), 3), "Vua": round(float(chk.Vua), 3), "modes": rows,
            "interaction": round(float(chk.interaction), 4) if with_pedestal else None,
            "status": ("EVALUATED" if with_pedestal else "NOT EVALUATED (no pedestal: concrete modes not checked; rod steel only)"),
            "passed": bool(chk.passed if with_pedestal else _steel_ok(chk)),
            "fixes": _concrete_fixes(chk) if with_pedestal else [], "warnings": list(chk.warnings)}


def _hefs(depth: float):
    h = HEF_MIN
    while h <= depth - HEF_COVER + 1e-9:
        yield h
        h += HEF_STEP


def _plate_fy(grade: str, t: float) -> float:
    from bimsteelauto_connections.bolts import get_grade
    return get_grade(grade, t)[0]


def _palette_at_least(t_req: float, grade: str) -> float | None:
    for t in sorted(DEFAULT_PLATE_PALETTE):
        if t + 1e-9 >= t_req:
            return t
    return None


def design_base(j: dict, sec: dict, frame_grade: str, st: BaseSettings) -> dict:
    """One base joint (from step 1, with forces) → the designed plate and rods, or NOT EVALUATED with the reason."""
    out = {"joint": j["id"], "type": j["type"], "member": j["members"][0]["id"], "section": sec, "settings": asdict(st),
           "notes": [WASHER_NOTE]}
    if j.get("status") != "EVALUATED" or not j.get("forces"):
        return {**out, "status": "NOT EVALUATED", "missing": j.get("missing", ["no forces at this base"])}
    pg = PLATE_GRADE.get(frame_grade)
    if pg is None:
        return {**out, "status": "NOT EVALUATED",
                "missing": [f"plate grade {frame_grade!r} is not in bimsteelauto_connections (S275 / S355 / A572 Gr 50 only)"]}
    cases = _cases(j)
    tries = []
    for d_rod in ROD_SIZES:
        r = _try(sec, cases, d_rod, st, pg)
        tries.append((d_rod, r))
        if r["ok"]:
            break
    d_rod, r = tries[-1]
    if not r["ok"]:
        # nothing passes: report the SMALLEST rod whose steel passes (at the deepest embedment that fits) — the concrete
        # modes (shear breakout above all) barely depend on the rod size, so M36 would only hide the real fix
        steel = [(d, t) for d, t in tries if "anchors" in t and all(_steel_ok_row(a) for a in t["anchors"])]
        if steel:
            d_rod, r = steel[0]
    ped = st.pedestal is not None
    res = {**out, "plate_grade": pg, "rod": {"d": d_rod, "n": 4, "grade": st.anchor_grade, "thread_area": THREAD_AREA.get(d_rod)},
           **{k: v for k, v in r.items() if k != "ok"}}
    if not r["ok"]:
        res.update(status="FAILS" if "cases" in r else "NOT EVALUATED",
                   missing=[r.get("why") or "no rod up to M36 with an embedment that fits the pedestal passes every case"])
        if "anchors" in r:
            res["fixes"] = sorted({f for a in r["anchors"] for f in a["fixes"]})
        return res
    res["status"] = "DESIGNED" if ped else "PLATE DESIGNED - ANCHORS NOT EVALUATED"
    if not ped:
        res["missing"] = ["pedestal size (the user's input per building): the anchors' concrete modes are NOT EVALUATED"]
    g = r["geometry"]
    res["app_params"] = {"length": g["N"], "width": g["B"], "tp": r["t"], "rodD": d_rod, "hole": g["hole"],
                         "sx": g["s_along_d"], "sy": g["s_across"], "embed": r["hef"], "grade": st.anchor_grade,
                         "plateGrade": pg, "washers": 1, "washerSize": g["washer"], "washerT": g["washer_t"], "layout": st.layout}
    return res


def column_section(m: dict) -> dict:
    """The base section of a generated built-up column {d, bf, tf, tw} (bottom segment, its start)."""
    s = m["section"]["segments"][0]
    return {"d": s["hw_start"] + s["tf_top"] + s["tf_bot"], "bf": min(s["bf_top"], s["bf_bot"]),
            "tf": max(s["tf_top"], s["tf_bot"]), "tw": s["tw"]}


def building_bases(joints_result: dict, out: dict, settings: BaseSettings | None = None) -> dict:
    """Every base joint of a building_joints() result → designed base plates."""
    st = (settings or BaseSettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    rows = []
    for j in joints_result["joints"]:
        if j["type"] not in ("base", "wind_column_base"):
            continue
        m = mem[j["members"][0]["id"]]
        rows.append(design_base(j, column_section(m), m.get("material", "S355"), st))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "bases": rows, "counts": counts,
            "warnings": list(joints_result.get("warnings", [])), "notes": [WASHER_NOTE],
            "open_flags": sorted([f"engine.connections.baseplates.{k}" for k, v in VERIFIED.items() if not v]),
            "library_flags": {"baseplate": dict(BASEPLATE_VERIFIED), "anchors": dict(ANCHORS_VERIFIED)}}
