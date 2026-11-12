# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 3: knee, ridge and rafter-splice end plates — plate, bolts, welds, column side. NOT FOR ISSUE.

VERIFIED engineering used from bimsteelauto_connections (not modified) and pyaisc360:
    endplate.yield_line_Yp      AISC 358-16 Table 6.2 / DG 4 Yp for 4E, 4ES, 8ES (verified against CET)
    endplate.required_thickness_dg4, no_prying_moment_strength, endplate_moment_strength  (DG 4 thick-plate procedure)
    bolts.bolt_tension_capacity / bolt_shear_capacity / get_bolt  (AISC J3.6, Table J3.2; 8.8 / 10.9 by the J3.2 ratios)
    bolts.evaluate_bolt_row     tension with prying (AISC Manual Part 9 T-stub) — the cross-check of the plate
    welds.check_column_side     AISC J10.1, .2, .3, .5, .6
    welds.size_fillet_weld      AISC J2 fillet sizing, joint="tee" (no J2.2b edge maximum), min_leg_by="thinner"
                                (Table J2.4) — bimsteelauto 0.15.3, added for these welds (user 2026-11-12)
    pyaisc360                   J3.10 bearing / tearout, J3.7 Eq. J3-3a, G2.1 web shear (Cv1, kv Eq. G2-5)
Manafe3 code (flagged in VERIFIED, TO CONFIRM — see the HANDOVER "unverified sources" list):
    flush_Yp            DG 16 two- / four-bolt FLUSH unstiffened yield lines — WRITTEN FROM MEMORY (user 2026-11-12)
    fillet_or_cjp       only the SETTINGS around the library's weld: the leg list, one size per joint type, and the
                        switch to a CJP groove weld above weld_max_fillet (12 mm)
    column stiffeners   transverse pairs (J10.7 / J10.8) as the standard detail; panel-zone diagonal stiffener or doubler
    end-plate stiffener 4ES / 8ES (AISC 358-16 Sect. 6 as recalled)
    clearances          gauge vs plate / column-flange edges (Table J3.4M), web wrench clearance, pitch vs weld + nut

The user's decisions (2026-11-10 / 12) — the full list is in HANDOVER "Step 3 decisions":
    forces       step 1's design forces (the 50 % rule on Mu+, Mu−, Vu); axial tension CONCURRENT with the moment (same
                 combination, step 1 stores it), the worst pair: Mu_eq = max(|M|, f × φMn) + T (d − tf)/2; compression
                 not credited
    knee         extended above AND below; ONE plate and ONE bolt layout for both signs; the governing sign of the bolts
                 and of the plate are reported
    ridge/splice extended below only, FLUSH at the top: −M = the DG 16 flush case (two-bolt, then four-bolt)
    configs      4E → 4ES → 8ES; bolts 8.8 (then 10.9 if 8.8 fails up to M30 — reported), pretensioned bearing-type,
                 threads INCLUDED, no slip check; ≥ M20 on main-frame end plates (setting; M16 for secondary joints);
                 ONE bolt size and grade, ONE plate thickness and ONE weld size per joint type over the building
    shear        each sign separately: the compression-side bolts; if they fail, ALL bolts with the J3.7 interaction
                 (the method is reported); J3.10 bearing / tear-out on every ply
    welds        double fillets; flanges full strength (Fy bf tf), web: its yield over the tension-bolt zone + the shear;
                 a full-strength fillet over 12 mm (setting) → CJP, said so; minimum legs AISC 360-16 Table J2.4
    column side  J10.1 / .2 / .3 / .6 checked; J10.4 (sidesway web buckling) not applicable — the flange-level
                 stiffeners restrain the flanges; J10.5 not applicable — one-sided connection; transverse stiffeners at
                 both rafter flange levels at EVERY knee (standard detail), sized up by J10.7 / J10.8 where needed;
                 panel zone: φVpanel = min(J10.6, G2.1 shear buckling of the panel web, kv from the stiffener spacing);
                 shortfall → a diagonal stiffener As = (Vu − φVpanel) / (φ Fy cos θ) (doubler as an option); stiffener
                 welds: step 4 (engine/connections/welds.py, 2026-11-12)
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from bimsteelauto_connections import EndPlateConfig, EndPlateGeometry
from bimsteelauto_connections.anchors import NUT_ACROSS_FLATS
from bimsteelauto_connections.bolts import (GeometryError, bolt_shear_capacity, bolt_tension_capacity, evaluate_bolt_row,
                                            get_bolt, get_grade)
from bimsteelauto_connections.endplate import (VERIFIED as EP_VERIFIED, endplate_moment_strength, no_prying_moment_strength,
                                               required_thickness_dg4, yield_line_Yp)
from bimsteelauto_connections.welds import ELECTRODES, check_column_side, min_weld_size, size_fillet_weld
from pyaisc360 import chapter_g as _g
from pyaisc360 import chapter_j as _j

from .baseplates import PLATE_GRADE
from .welds import (WeldSettings, column_stiffener_welds, diagonal_welds, doubler_welds,  # step 4 (2026-11-12)
                    endplate_stiffener_welds)

BANNER = ("NOT FOR ISSUE — end plates (Phase 5 step 3); DG 16 flush yield lines written from memory; stiffener, weld and "
          "clearance rules TO CONFIRM")
PHI_BOLT, PHI_PLATE, PHI_BEARING, PHI_STIFF = 0.75, 0.90, 0.75, 0.90
E_STEEL = 200000.0
IN, KSI, KIP = 25.4, 6.894757, 4.448222
#: AISC 360-16 Table J3.3M standard holes / Table J3.4M minimum edge distances, mm — transcribed from memory, TO CONFIRM
HOLE = {12: 14.0, 16: 18.0, 20: 22.0, 22: 24.0, 24: 27.0, 27: 30.0, 30: 33.0}
EDGE_MIN = {12: 18.0, 16: 22.0, 20: 26.0, 22: 28.0, 24: 30.0, 27: 34.0, 30: 38.0}
FILLET_LEGS = (3.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0)
#: the mark every ridge / rafter-splice result carries while VERIFIED["flush_Yp_DG16"] is False (user 2026-11-12)
DG16_MARK = "NOT FOR ISSUE: DG 16 flush unverified"
#: j24_min_leg_table: the Table J2.4 values are the library's min_weld_size (3 / 5 / 6 / 8 mm up to 6 / 13 / 19 mm) — the
#: user checks them against the printed table. cjp_switch: Manafe3's rule (a setting), not a code clause.
VERIFIED = {"flush_Yp_DG16": False, "cjp_switch": False, "j24_min_leg_table": False, "column_stiffeners": False,
            "panel_zone_diagonal": False, "endplate_stiffener": False, "clearance_rules": False, "hole_edge_tables": False,
            "web_weld_tension_zone": False, "j10_4_j10_5_not_applicable": False}
SIDE_NAME = {"-M": "-M (top flange in tension)", "+M": "+M (bottom flange in tension)"}


@dataclass
class EndPlateSettings:
    """Every default the end plates use — editable per job, listed on each result."""
    bolt_grade: str = "8.8"
    escalate_to_10_9: bool = True        # 8.8 fails up to the largest size → try 10.9, reported
    bolt_sizes: tuple = (16.0, 20.0, 24.0, 27.0, 30.0)
    bolt_min_main: float = 20.0          # main-frame end plates (knee / ridge / splice)
    bolt_min_secondary: float = 16.0     # secondary joints (step 5)
    threads: str = "N"                   # threads included in the shear plane
    configs: tuple = ("4E", "4ES", "8ES")
    plate_stock: tuple = (12.0, 15.0, 16.0, 18.0, 20.0, 22.0, 25.0, 30.0, 35.0, 40.0, 50.0)
    electrode: str = "E70"               # E70XX, 482 MPa
    weld_max_fillet: float = 12.0        # a full-strength fillet above this → CJP
    bp_extra: float = 50.0
    gauge_small: float = 100.0
    gauge_large: float = 140.0
    gauge_switch: float = 24.0
    pf_min: float = 40.0
    pf_add: float = 12.0
    de_factor: float = 1.5
    pb_factor: float = 3.0
    wrench_allowance: float = 5.0        # mm beyond the nut's corner radius (socket wall)
    tension_zone_extra: float = 2.0      # × d beyond the innermost tension row: web weld developing the web yield
    panel_zone: str = "diagonal"         # or "doubler"
    k_weld_assumed: float = 6.0          # column flange-to-web weld leg in k = tf + w, until step 4
    one_per_type: bool = True

    def check(self) -> "EndPlateSettings":
        get_bolt(self.bolt_grade)
        if self.threads not in ("N", "X"):
            raise ValueError("threads must be 'N' or 'X'")
        if not self.configs or any(c not in ("4E", "4ES", "8ES") for c in self.configs):
            raise ValueError(f"configs from 4E / 4ES / 8ES, got {self.configs}")
        if any(int(d) not in HOLE for d in self.bolt_sizes):
            raise ValueError("a bolt size with no standard hole / edge distance listed")
        if self.electrode not in ELECTRODES:
            raise ValueError("electrode E60 / E70 / E80")
        if self.panel_zone not in ("diagonal", "doubler"):
            raise ValueError("panel_zone: diagonal / doubler")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "EndPlateSettings":
        d = dict(d or {})
        bad = set(d) - set(cls.__dataclass_fields__)
        if bad:
            raise ValueError(f"unknown end-plate settings: {', '.join(sorted(bad))}")
        for k in ("bolt_sizes", "configs", "plate_stock"):
            if k in d:
                d[k] = tuple(d[k])
        return cls(**d).check()

    def gauge(self, db: float) -> float:
        return self.gauge_small if db <= self.gauge_switch + 1e-9 else self.gauge_large

    def pf(self, db: float) -> float:
        return max(self.pf_min, db + self.pf_add)

    def grades(self) -> list[str]:
        return [self.bolt_grade] + (["10.9"] if self.escalate_to_10_9 and self.bolt_grade == "8.8" else [])


# ------------------------------------------------------------------------------------------------------------ geometry

def _up10(v: float) -> float:
    return math.ceil(v / 10.0 - 1e-9) * 10.0


def corner_radius(db: float) -> float:
    """Half the nut's width across corners (ISO 4032 across flats / cos 30°), mm."""
    return NUT_ACROSS_FLATS[float(db)] / math.cos(math.radians(30.0)) / 2.0


def extended_rows(sec: dict, db: float, config: str, st: EndPlateSettings) -> dict:
    """Rows of an EXTENDED side; lever arms from the compression-flange centreline (sec: d, tf_t tension, tf_c)."""
    d, tft, tfc = sec["d"], sec["tf_t"], sec["tf_c"]
    pf, pb, de = st.pf(db), st.pb_factor * db, st.de_factor * db
    out0, in0 = d + pf - tfc / 2, d - tft - pf - tfc / 2
    h = (out0 + pb, out0, in0, in0 - pb) if config == "8ES" else (out0, in0)
    return {"h_rows": h, "pfo": pf, "pfi": pf, "de": de, "pb": pb if config == "8ES" else None,
            "extension": pf + de + (pb if config == "8ES" else 0.0), "n_bolts": 2 * len(h)}


def flush_rows(sec: dict, db: float, kind: str, st: EndPlateSettings) -> dict:
    d, tft, tfc = sec["d"], sec["tf_t"], sec["tf_c"]
    pf, pb = st.pf(db), st.pb_factor * db
    h1 = d - tft - pf - tfc / 2
    h = (h1,) if kind == "two-bolt" else (h1, h1 - pb)
    return {"h_rows": h, "pf": pf, "pb": pb if kind == "four-bolt" else None, "n_bolts": 2 * len(h)}


def flush_Yp(kind: str, bp: float, g: float, pf: float, h_rows: tuple, pb: float | None = None) -> dict:
    """DG 16 yield-line parameter of an UNSTIFFENED FLUSH end plate, mm. WRITTEN FROM MEMORY (user decision 2026-11-12):
    AISC Design Guide 16 (Murray & Shoemaker, 2002), the flush end-plate yield-line table — section / table number TO
    CONFIRM against the printed guide; VERIFIED False until compared line by line.
        s = ½ √(bp g); pf capped at s
        two-bolt:  Yp = (bp/2)[h1 (1/pf + 1/s) − 1/2] + (2/g)[h1 (pf + s)]
        four-bolt: Yp = (bp/2)[h1 (1/pf + 1/s) + h2 (1/s) − 1/2] + (2/g)[h1 (pf + 3pb/4) + h2 (s + pb/4)] + g/2"""
    s = 0.5 * math.sqrt(bp * g)
    p = min(pf, s)
    if kind == "two-bolt":
        (h1,) = h_rows
        a = (bp / 2) * (h1 * (1 / p + 1 / s) - 0.5)
        b = (2 / g) * (h1 * (p + s))
        c = 0.0
    elif kind == "four-bolt":
        h1, h2 = h_rows
        a = (bp / 2) * (h1 * (1 / p + 1 / s) + h2 / s - 0.5)
        b = (2 / g) * (h1 * (p + 0.75 * pb) + h2 * (s + 0.25 * pb))
        c = g / 2
    else:
        raise ValueError("flush kind: two-bolt / four-bolt")
    return {"Yp": a + b + c, "s": s, "pf_used": p, "terms": {"bp/2": a, "2/g": b, "g/2": c}, "verified": False,
            "clause": "AISC Design Guide 16, flush unstiffened (from memory — TO CONFIRM)"}


def _plate_section(w: dict, cos: float, tension_top: bool) -> dict:
    """What a vertical plate sees of a sloping member: d / cos, tf / cos (bimsteelauto cut_cosine)."""
    d, tt, tb = w["d"] / cos, w["tf_top"] / cos, w["tf_bot"] / cos
    return {"d": d, "tf_t": tt if tension_top else tb, "tf_c": tb if tension_top else tt,
            "bf": min(w["bf_top"], w["bf_bot"]), "tw": w["tw"]}


# ------------------------------------------------------------------------------------------------------------- forces

def sign_demands(j: dict, lever: float) -> dict:
    """Per sign, the worst CONCURRENT (M, T) pair (user decision 2026-11-12): candidates = the largest moment of that sign
    with its own axial force, and the largest tension with its own moment when that moment has the sign; each with the 50 %
    rule on the moment: Mu_eq = max(|M|, f × φMn) + T × lever / 2 (T = tension in that combination; compression not
    credited). kN·m."""
    F, D = j["forces"], j["design"]
    out = {}
    for sg, mkey, dkey in (("-M", "M_neg", "Mu_neg"), ("+M", "M_pos", "Mu_pos")):
        capb = D[dkey]["capacity_based"] or 0.0
        cands = []
        me = F[mkey]
        if me.get("combo"):
            cands.append(("largest moment of the sign", abs(me["M"]), max(0.0, -me["P"]), me["combo"]))
        pt = F["P_tens"]
        if pt.get("combo") and ((pt["M"] < 0) if sg == "-M" else (pt["M"] > 0)):
            cands.append(("largest tension with its moment", abs(pt["M"]), pt["value"], pt["combo"]))
        if not cands:
            cands.append(("the 50 % rule alone (no moment of this sign in any combination)", 0.0, 0.0, None))
        rows = []
        for why, M, T, combo in cands:
            Mu = max(M, capb)
            rows.append({"pair": why, "combo": combo, "M": round(M, 3), "T": round(T, 3), "Mu_design": round(Mu, 3),
                         "Mu_eq": round(Mu + T * lever / 2 / 1000.0, 3),
                         "criterion": "% of member capacity" if capb > M else "analysis force"})
        w = max(rows, key=lambda r: r["Mu_eq"])
        out[sg] = {**w, "candidates": rows}
    return out


# ------------------------------------------------------------------------------------------------------------- welds

def fillet_or_cjp(demand: float, length: float, theta: float, t_part: float, t_plate: float, grade: str,
                  st: EndPlateSettings, leg_min: float = 0.0) -> dict:
    """Double fillet of a T-joint — a flange or the web welded on the FACE of the end plate. The weld is sized by the
    library: bimsteelauto_connections.welds.size_fillet_weld(joint="tee", min_leg_by="thinner") — AISC 360-16 J2.4 weld
    metal (with the directional increase) and J2-2 base metal, the Table J2.4 minimum by the thinner part, and NO J2.2b
    t − 2 maximum (these welds lie on the plate face, not along a plate edge). Manafe3 adds only its settings: the leg
    list, leg ≥ leg_min (one size per joint type), and the switch to a CJP groove weld when the fillet would exceed
    weld_max_fillet (12 mm) or the thinner part — said so. kN, mm; capacity = both weld lines."""
    if demand <= 0 or length <= 0:
        raise ValueError(f"weld demand and length must be > 0, got {demand} kN on {length} mm")
    t_thin = min(t_part, t_plate)
    top = min(st.weld_max_fillet, t_thin)
    legs = tuple(w for w in FILLET_LEGS if leg_min - 1e-9 <= w <= top + 1e-9)
    out = {"demand": round(demand, 2), "min_leg_J2_4": min_weld_size(t_thin), "theta": theta, "length": round(length, 1)}
    try:
        if not legs:
            raise GeometryError("no leg in the list")
        w = size_fillet_weld(demand=demand, length=length, t_part1=t_part, t_part2=t_plate, base_grade=grade, theta=theta,
                             electrode=st.electrode, n_welds=2, palette=legs, joint="tee", min_leg_by="thinner")
    except GeometryError:
        return {"type": "CJP groove weld (matching E70XX filler; full strength, AISC 360-16 Table J2.5)", "leg": 0.0, **out,
                "capacity": round(demand, 2), "U": 1.0,
                "why": f"a full-strength fillet would exceed {top:g} mm (setting / thinner part)"}
    return {"type": "double fillet", "leg": float(w.leg), **out, "capacity": round(2 * float(w.capacity), 2),
            "U": round(float(w.utilization), 4), "governs": w.governing,
            "sized_by": "bimsteelauto_connections.size_fillet_weld (tee joint, Table J2.4 by the thinner part)"}


def flange_weld(bf: float, tf: float, tp: float, grade: str, st: EndPlateSettings, leg_min: float = 0.0) -> dict:
    Fy, _ = get_grade(grade, tf)
    return {**fillet_or_cjp(Fy * bf * tf / 1000.0, bf, 90.0, tf, tp, grade, st, leg_min), "basis": "full strength Fy bf tf"}


def web_weld(sec: dict, zone: float, Vu: float, tp: float, grade: str, st: EndPlateSettings, leg_min: float = 0.0) -> dict:
    """Web to end plate: the web's yield Fy tw over each tension-bolt zone (θ 90°), the shear Vu on the rest (θ 0°). The
    zone (innermost tension row + tension_zone_extra × d from the flange) is Claude's rule — TO CONFIRM."""
    tw = sec["tw"]
    Fy, _ = get_grade(grade, tw)
    hw = sec["d"] - sec["tf_t"] - sec["tf_c"]
    Lt = min(zone, hw / 2)
    rest = max(hw - 2 * Lt, 50.0)                    # a tension zone at each flange (both signs)
    wt = fillet_or_cjp(Fy * tw * Lt / 1000.0, Lt, 90.0, tw, tp, grade, st, leg_min)
    wv = fillet_or_cjp(max(Vu, 1e-6), rest, 0.0, tw, tp, grade, st, leg_min)
    return {"tension_zone": wt, "shear": wv, "leg": max(wt["leg"], wv["leg"]), "zone_length": round(Lt, 1),
            "basis": "web yield Fy tw over each tension-bolt zone; the shear on the rest"}


# --------------------------------------------------------------------------------------------------------- the sides

def _plate_for(Mnp: float, Yp: float, grade: str, stock) -> float | None:
    for t in sorted(stock):
        Fy, _ = get_grade(grade, t)
        if t + 1e-9 >= required_thickness_dg4(Mnp, Fy, Yp):
            return t
    return None


def _side(kind: str, sec: dict, db: float, grade_b: str, pg: str, Mu: float, st: EndPlateSettings) -> dict:
    """One tension side: kind 4E / 4ES / 8ES (extended) or two-bolt / four-bolt (flush). Bolts by the no-prying moment
    φMnp = 0.75 × 2 Pt Σh; the plate by the thick-plate rule (DG 4 Eq. 3.10 / DG 16): tp ≥ √(1.11 φMnp / (φ Fy Yp))."""
    bp, g = _up10(sec["bf"] + st.bp_extra), st.gauge(db)
    if kind in ("4E", "4ES", "8ES"):
        rows = extended_rows(sec, db, kind, st)
        geom = EndPlateGeometry(bp=bp, g=g, pfo=rows["pfo"], pfi=rows["pfi"], h_rows=tuple(rows["h_rows"]), de=rows["de"], pb=rows["pb"])
        yl = yield_line_Yp(EndPlateConfig(kind), geom)
        Yp, clause, ver, label = yl.Yp, yl.clause, bool(EP_VERIFIED[kind]), kind
    else:
        rows = flush_rows(sec, db, kind, st)
        label = f"flush {kind}"
        if min(rows["h_rows"]) <= sec["tf_c"]:
            return {"kind": label, "rows": rows, "ok": False, "why": "the flush rows do not fit inside the depth"}
        fy = flush_Yp(kind, bp, g, rows["pf"], rows["h_rows"], rows["pb"])
        Yp, clause, ver = fy["Yp"], fy["clause"], False
    Pt = bolt_tension_capacity(grade_b, db) / PHI_BOLT
    Mnp = no_prying_moment_strength(Pt, rows["h_rows"], n_per_row=2)
    out = {"kind": label, "rows": rows, "bp": bp, "g": g, "Yp": round(Yp, 2), "Yp_clause": clause, "Yp_verified": ver,
           "Mu": round(Mu, 3), "phiMnp_bolts": round(PHI_BOLT * Mnp, 3), "U_bolts": round(Mu / (PHI_BOLT * Mnp), 4),
           "Mnp": round(Mnp, 3)}
    out["t_need"] = _plate_for(Mnp, Yp, pg, st.plate_stock)
    out["ok"] = Mu <= PHI_BOLT * Mnp + 1e-9 and out["t_need"] is not None
    if not out["ok"]:
        out["why"] = "bolts (no-prying moment) too weak" if Mu > PHI_BOLT * Mnp else "no stock plate thick enough"
    return out


def _at_thickness(side: dict, t: float, pg: str) -> None:
    Fy, _ = get_grade(pg, t)
    Yp = side["Yp"]
    side["t"], side["Fy"] = t, Fy
    side["t_req"] = round(required_thickness_dg4(side["Mnp"], Fy, Yp), 2)
    phiMpl = endplate_moment_strength(t, Fy, Yp)
    side["phiMpl"] = round(phiMpl, 3)
    side["U_plate"] = round(side["Mu"] / phiMpl, 4)
    side["plate_ok"] = t + 1e-9 >= side["t_req"]


def _prying(side: dict, db: float, grade_b: str, pg: str, st: EndPlateSettings) -> dict:
    """Cross-check: every tension bolt at Tu = Mu / (2 Σh) (AISC 358 6.2), AISC Manual Part 9 T-stub prying (library)."""
    h = side["rows"]["h_rows"]
    Tu = side["Mu"] * 1000.0 / (2 * sum(h))
    pf = side["rows"].get("pfo") or side["rows"].get("pf")
    de = side["rows"].get("de") or pf
    r = evaluate_bolt_row(Tu=Tu, Vu=0.0, bolt_grade=grade_b, d_bolt=db, plate_grade=pg, t_plate=side["t"], b=pf,
                          a=min(de, 1.25 * pf), p=side["bp"] / 2, d_hole=HOLE[int(db)], threads=st.threads)
    return {"Tu_per_bolt": round(Tu, 3), "T_available": round(float(r.T_available), 3), "U": round(float(r.utilization), 4)}


def _bearing_per_bolt(db: float, t: float, Fu: float, lc: float) -> float:
    """φ min(J3-6a 2.4 d t Fu, J3-6c 1.2 lc t Fu), kN (pyaisc360; deformation considered)."""
    b, _ = _j.bearing_strength(db / IN, t / IN, Fu / KSI)
    r, _ = _j.tearout_strength(max(lc, 0.0) / IN, t / IN, Fu / KSI)
    return PHI_BEARING * min(b, r) * KIP


def shear_for_sign(Vu: float, n_comp: int, n_tens: int, Tu_bolt: float, db: float, grade_b: str, plies: list, de: float,
                   st: EndPlateSettings) -> dict:
    """One moment sign (user decision): the compression-side bolts first; if they fail, ALL bolts share Vu and the tension
    bolts take the J3.7 reduction (Eq. J3-3a, pyaisc360). Bearing / tear-out (J3.10) on every ply; tear-out clear distance
    de − hole/2 for every bolt (conservative). Threads included unless the setting says otherwise."""
    bolt = get_bolt(grade_b)
    Ab = math.pi * db * db / 4
    vb = bolt_shear_capacity(grade_b, db, threads=st.threads)
    br = min(_bearing_per_bolt(db, t, Fu, de - HOLE[int(db)] / 2) for t, Fu in plies)
    per = min(vb, br)
    capA = n_comp * per
    out = {"Vu": round(Vu, 3), "bolt_shear": round(vb, 3), "bearing_tearout": round(br, 3)}
    if Vu <= capA + 1e-9:
        return {**out, "method": f"compression-side bolts only ({n_comp})", "phiVn": round(capA, 3), "U": round(Vu / capA, 4)}
    n_all = n_comp + n_tens
    vbolt = Vu / n_all
    Fnv = bolt.Fnv_N if st.threads == "N" else bolt.Fnv_X
    frv = vbolt * 1000.0 / Ab
    Fnt_mod, eq = _j.combined_tension_shear(bolt.Fnt / KSI, Fnv / KSI, frv / KSI)
    phiT = PHI_BOLT * Fnt_mod * KSI * Ab / 1000.0
    U = max(vbolt / per, Tu_bolt / phiT if phiT > 0 else math.inf)
    return {**out, "method": f"ALL bolts ({n_all}) with the J3.7 interaction ({eq}) — the compression-side bolts alone "
                             f"({n_comp}, phiVn {capA:.1f} kN) do not carry Vu",
            "shear_per_bolt": round(vbolt, 3), "Fnt_modified": round(Fnt_mod * KSI, 1), "phiT_reduced": round(phiT, 3),
            "Tu_per_bolt": round(Tu_bolt, 3), "phiVn": round(n_all * per, 3), "U": round(U, 4)}


def clearances(sec: dict, db: float, bp: float, g: float, pf: float, w_flange: float, w_web: float, st: EndPlateSettings,
               col_bf: float | None = None) -> list[dict]:
    """Detailing (user 2026-11-12; Claude's rules, TO CONFIRM): plate edge (bp − g)/2 and, at the knee, the column flange
    edge (bf_col − g)/2 ≥ Table J3.4M; web wrench clearance g/2 − tw/2 − w_web ≥ nut corner + allowance; pitch pf − w_flange
    ≥ nut corner + allowance."""
    e_min, cr = EDGE_MIN[int(db)], corner_radius(db) + st.wrench_allowance
    rows = [("plate edge (bp - g)/2 >= Table J3.4M", (bp - g) / 2, e_min),
            ("web wrench clearance g/2 - tw/2 - w_web >= nut corner + allowance", g / 2 - sec["tw"] / 2 - w_web, cr),
            ("pitch clears the flange weld: pf - w_flange >= nut corner + allowance", pf - w_flange, cr)]
    if col_bf is not None:
        rows.append(("column flange edge (bf_col - g)/2 >= Table J3.4M", (col_bf - g) / 2, e_min))
    return [{"check": n, "value": round(v, 1), "required": round(r, 1), "ok": bool(v + 1e-9 >= r)} for n, v, r in rows]


def endplate_stiffener(config: str, side: dict, tw_beam: float, pg: str, stock, tp: float | None = None,
                       tf_beam: float | None = None, ws: WeldSettings | None = None) -> dict | None:
    """4ES / 8ES end-plate stiffener (AISC 358-16 Sect. 6, as recalled — TO CONFIRM): height hst = the extension beyond
    the flange; Lst = hst / tan 30°; ts ≥ tw (Fyb / Fys) and hst / ts ≤ 0.56 √(E / Fys). Welds (step 4): welds.endplate_stiffener_welds — double fillets developing the
    stiffener, CJP above 12 mm (needs the end-plate thickness tp and the beam flange tf_beam)."""
    if config not in ("4ES", "8ES"):
        return None
    hst = side["rows"]["extension"]
    for t in sorted(stock):
        Fys, _ = get_grade(pg, t)
        if t + 1e-9 >= tw_beam and hst / t <= 0.56 * math.sqrt(E_STEEL / Fys) + 1e-9:
            Lst = hst / math.tan(math.radians(30.0))
            weld = ("NOT EVALUATED (no end-plate thickness given)" if tp is None or tf_beam is None
                    else endplate_stiffener_welds(hst, Lst, t, tp, tf_beam, pg, (ws or WeldSettings()).check()))
            return {"height": round(hst, 1), "length": round(Lst, 1), "t": t, "weld": weld}
    return {"height": round(hst, 1), "t": None, "weld": "NOT EVALUATED (no stiffener plate)",
            "why": "no stock plate meets hst/ts"}


# ------------------------------------------------------------------------------------------------------- column side

def column_side(Mu: float, rafter_d: float, rafter_tf: float, lever: float, lb: float, col: dict, pg: str,
                st: EndPlateSettings, ws: WeldSettings | None = None) -> dict:
    """Knee column side. Library J10.1 / .2 / .3 / .6 (J10.5 run by the library, listed NOT APPLICABLE: one-sided);
    J10.4 not applicable (the flange-level stiffeners restrain the flanges). Transverse stiffeners at both rafter flange
    levels at EVERY knee (standard detail; Claude's reading of J10.8: bs + tw/2 ≥ bf/3, ts ≥ tb/2, ts ≥ bs/16, half depth),
    sized up for Rst = Puf − min φRn(J10.1–3) when one fails (J10.7: Ast = Rst / (φ Fy)). Panel zone: φVpanel =
    min(J10.6, φ 0.6 Fy dc tw Cv1 — G2.1 with kv from a = the stiffener spacing (the lever), h = dc − 2 tf); Vu = Puf;
    a shortfall → diagonal stiffener As = (Vu − φVpanel) / (φ Fy cos θ), cos θ = dc / √(dc² + a²) (or a doubler
    td = (Vu − φVpanel) / (φ 0.6 Fy dc)). Welds (step 4, welds.py): the transverse stiffeners to the flanges and the web
    for Rst + the horizontal part of the diagonal force; the diagonal for As_req Fy; the doubler for its required shear."""
    ws = (ws or WeldSettings()).check()
    cs = check_column_side(Mu=Mu, d_beam=rafter_d, tf_beam=rafter_tf, col_grade=pg, d_col=col["d"], tw_col=col["tw"],
                           tf_col=col["tf"], k_col=col["tf"] + st.k_weld_assumed, h_col=col["d"] - 2 * col["tf"], lb=lb,
                           Pr_col=col.get("Pr", 0.0), Py_col=col.get("Py", 0.0), bcf=col["bf"], near_member_end=True)
    Puf = float(cs.Puf)
    rows, local, j106 = [], [], None
    for n, c, u in cs.checks:
        c, u = float(c), float(u)
        if n.startswith("J10.5"):
            rows.append({"check": n, "phiRn": round(c, 2), "U": round(u, 4), "applicable": False,
                         "note": "one-sided connection: J10.5 needs compressive forces on both flanges"})
            continue
        rows.append({"check": n, "phiRn": round(c, 2), "U": round(u, 4)})
        if n.startswith("J10.6"):
            j106 = c
        else:
            local.append((n, c, u))
    rows.append({"check": "J10.4 web sidesway buckling", "applicable": False,
                 "note": "the flange-level transverse stiffeners restrain the flanges"})
    tw, bf, d, tf = col["tw"], col["bf"], col["d"], col["tf"]
    Fy, _ = get_grade(pg, tw)
    Fy_st = get_grade(pg, 12.0)[0]
    bs = math.floor(min(max(bf / 3 - tw / 2, 50.0), (bf - tw) / 2) / 5) * 5
    need, Rst, As = max(rafter_tf / 2, bs / 16), 0.0, 0.0
    if any(u > 1.0 for _, _, u in local):
        Rst = Puf - min(c for _, c, _ in local)
        As = Rst * 1000.0 / (PHI_STIFF * Fy_st)
        need = max(need, As / (2 * bs))
    ts = next((t for t in sorted(st.plate_stock) if t + 1e-9 >= need), None)
    trans = {"detail": "standard: a pair at both rafter flange levels", "bs": bs, "t": ts, "t_req": round(need, 2),
             "length": round(d / 2, 1), "Rst": round(Rst, 2), "As_req": round(As, 1),
             "sized_by": "J10.7 force (a J10.1-J10.3 check fails)" if Rst > 0 else "J10.8 dimensions only (minimum)"}
    a, h = lever, d - 2 * tf
    kv = _g.kv_coefficient(a / h)
    Vn, cv1, phi, _ = _g.g2_1_strength(Fy / KSI, (d * tw) / IN ** 2, h / tw, E_STEEL / KSI, kv=kv, rolled=False)
    phiG2 = phi * Vn * KIP
    phiV = min(j106, phiG2) if j106 is not None else phiG2
    panel = {"Vu": round(Puf, 2), "phi_J10_6": None if j106 is None else round(j106, 2), "phi_G2_1": round(phiG2, 2),
             "G2_1": {"a": round(a, 1), "h": round(h, 1), "a_over_h": round(a / h, 3), "kv": round(kv, 3), "Cv1": round(cv1, 4),
                      "phi": phi},
             "phiVpanel": round(phiV, 2), "U": round(Puf / phiV, 4)}
    F_diag_h = 0.0
    if Puf > phiV:
        dV = Puf - phiV
        if st.panel_zone == "diagonal":
            cos_t = d / math.hypot(d, a)
            Areq = dV * 1000.0 / (PHI_STIFF * Fy_st * cos_t)
            tsd = next((t for t in sorted(st.plate_stock) if t + 1e-9 >= max(Areq / (2 * bs), bs / 16)), None)
            panel["diagonal_stiffener"] = {"formula": "As = (Vu - phiVpanel) / (phi Fy cos theta)", "Vu": round(Puf, 2),
                                           "phiVpanel": round(phiV, 2), "phi": PHI_STIFF, "Fy": Fy_st,
                                           "cos_theta": round(cos_t, 4), "theta_deg": round(math.degrees(math.acos(cos_t)), 2),
                                           "As_req": round(Areq, 1), "pair_bs": bs, "t": tsd}
            if tsd is not None:
                panel["diagonal_stiffener"]["weld"] = diagonal_welds(Areq, Fy_st, bs, tsd, tf, pg, ws)
                F_diag_h = Areq * Fy_st * cos_t / 1000.0
        else:
            td_req = dV * 1000.0 / (PHI_STIFF * 0.6 * Fy * d)
            tdd = next((t for t in sorted(st.plate_stock) if t + 1e-9 >= td_req), None)
            panel["doubler"] = {"formula": "td = (Vu - phiVpanel) / (phi 0.6 Fy dc)", "td_req": round(td_req, 2), "t": tdd}
            if tdd is not None:
                panel["doubler"]["weld"] = doubler_welds(dV, d, tdd, tf, pg, ws)
    # Manafe3 step 4 (2026-11-12): each stiffener must carry (Rst + the diagonal's horizontal part) / 2 in tension across
    # its flange contact bs − clip (J4.1, φ 0.9) — the force its welds are sized for (user answer 10); thicker from stock
    Fc = Rst + F_diag_h
    if ts is not None and Fc > 0 and bs > ws.stiffener_clip:
        def contact_need(t):
            return Fc / 2 * 1000.0 / (PHI_STIFF * get_grade(pg, t)[0] * (bs - ws.stiffener_clip))
        if ts + 1e-9 < contact_need(ts):
            ts2 = next((t for t in sorted(st.plate_stock) if t + 1e-9 >= max(need, contact_need(t))), None)
            trans.update(t=ts2, t_req=round(max(need, contact_need(ts2 or max(st.plate_stock))), 2),
                         t_contact=round(contact_need(ts2 or max(st.plate_stock)), 2),
                         sized_by=trans["sized_by"] + "; the flange contact bs - clip carries (Rst + diagonal horizontal) / 2")
            ts = ts2
    if ts is not None:
        trans["weld"] = column_stiffener_welds(Rst, F_diag_h, bs, ts, d / 2 - tf, tf, tw, pg, ws)
    welds = [trans.get("weld")] + [v.get("weld") for k, v in panel.items() if k in ("diagonal_stiffener", "doubler")]
    welds_ok = all(w["status"] == "DESIGNED" for w in welds if w)
    ok = ts is not None and welds_ok and all(v.get("t") is not None for k, v in panel.items()
                                             if k in ("diagonal_stiffener", "doubler"))
    return {"Puf": round(Puf, 2), "checks": rows, "transverse_stiffeners": trans, "panel_zone": panel, "ok": ok,
            "near_member_end": True, "k_note": f"k = tf + {st.k_weld_assumed:g} mm (assumed flange-to-web weld, step 4)"}


# --------------------------------------------------------------------------------------------------------- one joint

def design_joint(j: dict, rs: dict, cos: float, grade: str, st: EndPlateSettings, col: dict | None = None,
                 fixed: dict | None = None, ws: WeldSettings | None = None) -> dict:
    """One knee / ridge / splice joint (step 1, with design forces). fixed = {grade, db, t, w_flange, w_web} imposes the
    per-type values (one size per joint type)."""
    fixed = fixed or {}
    out = {"joint": j["id"], "type": j["type"], "rafter_section": rs, "cos_cut": round(cos, 6)}
    if j.get("status") != "EVALUATED" or not j.get("design"):
        return {**out, "status": "NOT EVALUATED", "missing": j.get("missing", ["no design forces at this joint"])}
    pg = PLATE_GRADE.get(grade)
    if pg is None:
        return {**out, "status": "NOT EVALUATED", "missing": [f"plate grade {grade!r} not in bimsteelauto_connections"]}
    if j["type"] != "knee" and not VERIFIED["flush_Yp_DG16"]:
        # the top side of a ridge / splice is the DG 16 flush case, written from memory: marked until the user confirms it
        out["not_for_issue"] = DG16_MARK
    secs = {"-M": _plate_section(rs, cos, True), "+M": _plate_section(rs, cos, False)}
    lever = secs["-M"]["d"] - (secs["-M"]["tf_t"] + secs["-M"]["tf_c"]) / 2
    dem = sign_demands(j, lever)
    Vu = j["design"]["Vu"]["value"]
    grades = [fixed["grade"]] if "grade" in fixed else st.grades()
    sizes = [fixed["db"]] if "db" in fixed else [d for d in st.bolt_sizes if d >= st.bolt_min_main - 1e-9]
    last = None
    for gb in grades:
        for cfg in st.configs:
            for db in sizes:
                for fk in ([None] if j["type"] == "knee" else ["two-bolt", "four-bolt"]):
                    sides = {"-M": _side(cfg if fk is None else fk, secs["-M"], db, gb, pg, dem["-M"]["Mu_eq"], st),
                             "+M": _side(cfg, secs["+M"], db, gb, pg, dem["+M"]["Mu_eq"], st)}
                    r = _evaluate(j, sides, cfg, db, gb, pg, rs, cos, col, Vu, dem, lever, st, fixed, ws)
                    last = r
                    if r["ok"]:
                        if gb != st.bolt_grade:
                            r["grade_note"] = f"{st.bolt_grade} failed up to M{max(sizes):g} in every configuration: {gb} used"
                        return {**out, **r, "status": "DESIGNED"}
    return {**out, **last, "status": "FAILS",
            "fixes": ["a deeper plate (more rows / 8ES), a thicker plate, or bigger bolts / grade 10.9"]
            + (["the flush (top) side: four-bolt flush, a deeper rafter at the joint, or bigger bolts"] if j["type"] != "knee" else [])}


def _evaluate(j, sides, cfg, db, gb, pg, rs, cos, col, Vu, dem, lever, st, fixed, ws=None) -> dict:
    res = {"bolt": {"d": db, "label": f"M{db:g}", "grade": gb, "hole": HOLE[int(db)], "pretensioned": True,
                    "type": "pretensioned bearing-type (no slip check)", "threads": "included" if st.threads == "N" else "excluded"},
           "config": cfg, "demands": dem}
    named = {("-M (top flange in tension, flush)" if (j["type"] != "knee" and k == "-M") else SIDE_NAME[k]): v
             for k, v in sides.items()}
    res["sides"] = named
    bad = [f"{k}: {v.get('why')}" for k, v in named.items() if not v.get("ok")]
    if bad:
        return {**res, "ok": False, "why": "; ".join(bad)}
    t = max(fixed.get("t", 0.0), max(s["t_need"] for s in sides.values()))
    for s in sides.values():
        _at_thickness(s, t, pg)
        s["prying_check"] = _prying(s, db, gb, pg, st)
    res["t"] = t
    res["governs"] = {"bolts": max(named, key=lambda k: named[k]["U_bolts"]), "plate": max(named, key=lambda k: named[k]["U_plate"])}
    tf_max = max(rs["tf_top"], rs["tf_bot"])
    psec = _plate_section(rs, cos, True)
    fw = flange_weld(rs["bf_top"], tf_max, t, pg, st, fixed.get("w_flange", 0.0))
    ext = next(s for s in sides.values() if "pfo" in s["rows"])
    zone = ext["rows"]["pfi"] + (ext["rows"]["pb"] or 0.0) + st.tension_zone_extra * db
    ww = web_weld(psec, zone, Vu, t, pg, st, fixed.get("w_web", 0.0))
    res["welds"] = {"flanges": fw, "web": ww, "electrode": "E70XX (482 MPa)"}
    res["clearances"] = clearances(psec, db, ext["bp"], ext["g"], st.pf(db), fw["leg"], ww["leg"], st, col["bf"] if col else None)
    plies = [(t, get_grade(pg, t)[1])] + ([(col["tf"], get_grade(pg, col["tf"])[1])] if col else [(t, get_grade(pg, t)[1])])
    res["shear"] = {}
    for sg, comp in (("-M", "+M"), ("+M", "-M")):                  # under −M the bottom (the +M side's bolts) is in compression
        sd = sides[sg]
        Tu_b = sd["Mu"] * 1000.0 / (2 * sum(sd["rows"]["h_rows"]))
        res["shear"][SIDE_NAME[sg]] = shear_for_sign(Vu, sides[comp]["rows"]["n_bolts"], sd["rows"]["n_bolts"], Tu_b, db, gb,
                                                     plies, st.de_factor * db, st)
    res["endplate_stiffener"] = endplate_stiffener(cfg, ext, rs["tw"], pg, st.plate_stock, t, tf_max, ws)
    bad = [f"plate thickness, {k}" for k, s in named.items() if not s["plate_ok"]]
    bad += [f"prying cross-check, {k} (U {s['prying_check']['U']:.2f})" for k, s in named.items() if s["prying_check"]["U"] > 1.0]
    bad += [f"clearance: {c['check']} ({c['value']:g} < {c['required']:g} mm)" for c in res["clearances"] if not c["ok"]]
    bad += [f"bolt shear, {k} (U {v['U']:.2f})" for k, v in res["shear"].items() if v["U"] > 1.0]
    bad += [f"weld: {n}" for n, w in (("flanges", fw), ("web tension zone", ww["tension_zone"]), ("web shear", ww["shear"]))
            if w["U"] > 1.0]
    if res["endplate_stiffener"] is not None and res["endplate_stiffener"]["t"] is None:
        bad.append("end-plate stiffener: no stock plate")
    elif res["endplate_stiffener"] is not None and res["endplate_stiffener"]["weld"].get("status") != "DESIGNED":
        bad.append("end-plate stiffener welds")
    if col is not None:
        Mu = max(s["Mu"] for s in sides.values())
        lb = rs["tf_top"] / cos + 2 * fw["leg"] + 2 * t
        res["column_side"] = column_side(Mu, psec["d"], tf_max / cos, lever, lb, col, pg, st, ws)
        if not res["column_side"]["ok"]:
            bad.append("column side: no stock plate for a stiffener / doubler, or a stiffener weld fails")
    res["ok"] = not bad
    if bad:
        res["failed_checks"] = bad
        res["why"] = "; ".join(bad)
    return res


# ------------------------------------------------------------------------------------------------------- the building

def _args(j: dict, mem: dict, cos_slope: float):
    raf = next((m for m in j["members"] if m["role"] == "rafter"), j["members"][0])
    sec = raf["section"]
    rs = {k: sec[k] for k in ("d", "tw", "bf_top", "tf_top", "bf_bot", "tf_bot")}
    cos = 1.0 if j["type"] == "rafter_splice" else cos_slope
    col = None
    if j["type"] == "knee":
        c = next(m for m in j["members"] if m["role"] == "column")
        cs = c["section"]
        pgc = PLATE_GRADE.get(mem[c["id"]].get("material", "S355"), "S355JR")
        A = cs["bf_top"] * cs["tf_top"] + cs["bf_bot"] * cs["tf_bot"] + (cs["d"] - cs["tf_top"] - cs["tf_bot"]) * cs["tw"]
        col = {"d": cs["d"], "tw": cs["tw"], "tf": max(cs["tf_top"], cs["tf_bot"]), "bf": min(cs["bf_top"], cs["bf_bot"]),
               "Pr": (j.get("design") or {}).get("Pu", {}).get("value", 0.0), "Py": get_grade(pgc, cs["tw"])[0] * A / 1000.0}
    return rs, cos, mem[raf["id"]].get("material", "S355"), col


def building_endplates(joints_result: dict, out: dict, settings: EndPlateSettings | None = None,
                       weld_settings: WeldSettings | None = None) -> dict:
    """Every knee / ridge / rafter-splice joint of a building_joints() result. One bolt size and grade, one plate
    thickness and one weld size per joint type (user decisions): each joint designed, then the per-type maxima imposed
    on every joint of the type and re-checked until they stop changing."""
    st = (settings or EndPlateSettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    slope = float(out["input"]["roof_slope"])
    cos_slope = 1.0 / math.sqrt(1.0 + slope * slope)
    js = [j for j in joints_result["joints"] if j["type"] in ("knee", "ridge", "rafter_splice")]
    def run(j, fixed=None):
        rs, cos, grade, col = _args(j, mem, cos_slope)
        return design_joint(j, rs, cos, grade, st, col, fixed, weld_settings)
    rows = {j["id"]: run(j) for j in js}
    per_type, notes = {}, []
    if st.one_per_type:
        for _ in range(4):
            new = {}
            for r in rows.values():
                if r["status"] != "DESIGNED":
                    continue
                p = new.setdefault(r["type"], {"grade": st.bolt_grade, "db": 0.0, "t": 0.0, "w_flange": 0.0, "w_web": 0.0})
                if r["bolt"]["grade"] != st.bolt_grade:
                    p["grade"] = r["bolt"]["grade"]
                p["db"] = max(p["db"], r["bolt"]["d"])
                p["t"] = max(p["t"], r["t"])
                p["w_flange"] = max(p["w_flange"], r["welds"]["flanges"]["leg"])
                p["w_web"] = max(p["w_web"], r["welds"]["web"]["leg"])
            if new == per_type:
                break
            per_type = new
            for j in js:
                if j["type"] in per_type and rows[j["id"]]["status"] == "DESIGNED":
                    rows[j["id"]] = run(j, per_type[j["type"]])
        for ty, p in per_type.items():
            if p["grade"] != st.bolt_grade:
                notes.append(f"{ty}: bolt grade {p['grade']} for every {ty} — {st.bolt_grade} failed up to M30 at one of them")
    lst = list(rows.values())
    counts = {}
    for r in lst:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    marked = [r["joint"] for r in lst if r.get("not_for_issue")]
    if marked:
        notes.append(f"{DG16_MARK} — {len(marked)} ridge / rafter-splice joints: their top (flush) side uses the DG 16 yield "
                     "lines written from memory, until the user confirms them against the printed guide")
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "joints": lst, "counts": counts, "per_type": per_type,
            "not_for_issue": {DG16_MARK: marked} if marked else {},
            "notes": notes, "warnings": list(joints_result.get("warnings", [])),
            "open_flags": sorted([f"engine.connections.endplates.{k}" for k, v in VERIFIED.items() if not v]),
            "library_flags": {"endplate": dict(EP_VERIFIED)}}
