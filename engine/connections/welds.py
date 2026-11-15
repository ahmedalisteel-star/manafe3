# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 4: the welds — flange-to-web welds of the built-up members, the column-to-base-plate weld, the shear lug,
and the stiffener welds (column transverse stiffeners, the panel-zone diagonal / doubler, the 4ES / 8ES end-plate
stiffeners). NOT FOR ISSUE. SI: mm, kN, MPa (stresses in N/mm²; weld flows in N/mm).

From bimsteelauto (not rewritten here):
    bimsteelauto_connections.welds.fillet_line_strength (0.15.4)   one fillet line per mm: AISC 360-16 J2.4 weld metal
                                               (φ 0.75, Fnw = 0.60 FEXX (1 + 0.5 sin^1.5 θ when allowed), throat 0.707 w)
                                               and the base metal of the straddled plate shared by its lines — J2-2 shear
                                               rupture 0.45 Fu t / n, or J4.1 tension min(0.9 Fy t, 0.75 Fu t) / n
    bimsteelauto_connections.welds.min_weld_size   Table J2.4 minimum leg (by the THINNER part joined)
    bimsteelauto_connections.bolts.get_grade       Fy / Fu by thickness
Manafe3 here (the user's decisions 2026-11-12, HANDOVER "Step 4 decisions"; Claude's rules flagged in VERIFIED):
    base metal of a DOUBLE fillet that straddles one plate (both faces of a web, a flange, a stiffener, a lug): the two
        lines share that plate — 0.45 Fu t / 2 per line (user 2026-11-12; the library credits the full t to each line —
        open item for bimsteelauto 0.15.4); a one-sided fillet: 0.45 Fu t. A plate pulled ACROSS the weld (θ 90°: a
        stiffener into a flange or an end plate): J4.1 min(0.9 Fy t, 0.75 Fu t), shared the same way (Claude, 2026-11-12)
    flange_web_weld      q = V Q / I at every station of every LRFD combination + the local loads at purlin / girt points
                         (w × spacing, w = |dV/dx| of the SAME combination) and at flange-brace points (2 % of the flange
                         force |M| / (d − tf) of the same combination), each spread over lb = t_cleat + 5 k, vector sum;
                         ONE-SIDED continuous fillet (SAW) up to one_side_max_leg (8 mm), both sides above it; the web base
                         metal 0.45 Fu tw caps both (two sides cannot beat it) → FAILS "thicker web"; leg = max(J2.4 by the
                         thinner part, shop_min_leg, demand); one leg per member segment; END ZONES (one depth from a knee /
                         ridge / splice end plate): both sides, developing the web shear 0.9 × 0.6 Fy tw. Shop butt splices
                         of flange and web plates are CJP — stated, not designed.
    base_weld            uplift and shear on the weld, compression by BEARING (AISC 360-16 J1.4 / M2.6: unmilled base
                         plates up to 50 mm — unverified); a plate over 50 mm → NOT EVALUATED. Strong-axis shear on the web
                         welds, weak-axis shear (bracing reactions) on the flange welds, uplift shared by the whole weld
                         length; elastic, vector sum, NO directional increase.
    braced-bay bases     engine/connections/longitudinal.py (open item 6): the frame reaction and the wall brace (T cos α
                         across, T sin α up) of the SAME combination — Load Case B with its own brace force, and the
                         §28.3.4 minimum family with dead load only; DESIGNED only when all are evaluated, else PARTIAL
    shear_lug            only when the anchors fail in shear / breakout and shear_fix = "lug" (default "hairpins"): a flat
                         plate; ACI 318-19 17.11.2 bearing φ 0.65 × 1.7 f'c Aef Ψ (VERIFIED False); the 17.11.3 breakout NOT
                         EVALUATED until the user sends the printed text (never a pass); DG 1 plate bending t ≥ √(4 Mu /
                         (φ Fy B)), Mu = Vu (G + h/2), and the lug weld (shear + the moment as a couple over t), VERIFIED
                         False; the anchors then take tension only.
    column_stiffener_welds   the pair carries F = max(Rst, ΔV) across its flange contact (welds θ 90°); its web welds
                         carry only the share the web panel takes, φVpanel − (Puf − F); the column web base metal for the
                         welds on both faces: min(1.0 × 0.6 Fy tw, 0.75 × 0.6 Fu tw) per mm (user review 2026-11-12) →
                         FAILS "doubler or thicker web"; never below J2.4 / shop_min_leg; CJP only above 12 mm
    diagonal_welds       the corner: max(As_req Fy, the stiffener's corner force / cos θ), end welds across bs (double
                         fillet, θ 90°); along the web: the minimum leg
    doubler_welds        the doubler's REQUIRED shear (Vu − φVpanel): flow (Vu − φVpanel) / dc along each flange edge
    endplate_stiffener_welds  double fillets developing the stiffener's design strength: 0.9 Fy ts to the end plate
                         (J4.1, θ 90°), 0.6 Fy ts to the beam flange (J4.2, θ 0°); CJP above 12 mm. AISC 358 is reference only (non-seismic frames, user 2026-11-12).
    Every weld: E70XX (482 MPa), the leg list FILLET_LEGS, a fillet over weld_max_fillet (12 mm) → CJP, said so.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from bimsteelauto_connections.anchors import ANCHOR_GRADES, THREAD_AREA
from bimsteelauto_connections.bolts import get_grade
from bimsteelauto_connections.welds import ELECTRODES, fillet_line_strength, min_weld_size

BANNER = ("NOT FOR ISSUE — welds (Phase 5 step 4); the local-load spread, the one-sided limit, AISC M2.6 / J1.4, ACI 17.11 "
          "and DG 1 TO CONFIRM; the shear-lug breakout NOT EVALUATED")
FILLET_LEGS = (3.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0)
PHI_V_WEB = 0.9                    # the end-zone web shear developed: 0.9 × 0.6 Fy tw (G2.1, built-up)
PHI_LUG_BEARING = 0.65             # ACI 318-19 17.11.2 / 21.2.1 — TO CONFIRM
PHI_PLATE = 0.9
CJP = "CJP groove weld (matching E70XX filler; full strength, AISC 360-16 Table J2.5)"
BUTT_SPLICE_NOTE = "shop butt splices of flange and web plates: CJP groove welds (full strength) — stated, not designed"
BEARING_NOTE = ("compression by bearing on the base plate; base plate <= 50 mm, unmilled (AISC 360-16 M2.6 / J1.4 — "
                "TO CONFIRM)")
VERIFIED = {"shared_base_metal": False, "local_load_spread": False, "one_side_max_leg": False, "end_zone_web_shear": False,
            "base_bearing_M2_6_J1_4": False, "aci_17_11_lug_bearing": False, "dg1_lug": False, "stiffener_clip": False,
            "weak_axis_from_brace": False, "j4_1_transverse_welds": False, "stiffener_corner_load_path": False}
PARTIAL = "PARTIAL - brace case NOT EVALUATED"
NOT_EVALUATED = "NOT EVALUATED"


@dataclass
class WeldSettings:
    """Every default the step 4 welds use — editable per job, listed on each result."""
    electrode: str = "E70"
    shop_min_leg: float = 5.0          # shop minimum fillet leg (user 2026-11-12)
    one_side_max_leg: float = 8.0      # single-pass SAW one-sided fillet; both sides above it (user 2026-11-12)
    weld_max_fillet: float = 12.0      # a fillet needing more → CJP
    stiffener_clip: float = 20.0       # corner clip of a stiffener at the flange-to-web weld (Claude's default, TO CONFIRM)
    cleat_thickness: float | None = None   # None → the model's purlin / girt cleat (PL8): the local-load bearing length
    end_zone_depths: float = 1.0       # end zone length = this × the member depth at the end plate
    flange_brace_fraction: float = 0.02    # flange-brace force = 2 % of the flange force (Phase 5 plan)
    base_plate_max: float = 50.0       # AISC M2.6: unmilled base plates up to 50 mm bear without milling (TO CONFIRM)
    shear_fix: str = "hairpins"        # when the anchors fail in shear / breakout: "hairpins" (step 2b) or "lug"
    grout: float = 50.0                # grout thickness under the base plate, mm (lug lever)
    lug_width: float | None = None     # None → the column flange width
    lug_heights: tuple = (100.0, 150.0, 200.0, 250.0, 300.0)   # embedment into the concrete below the grout
    plate_stock: tuple = (12.0, 15.0, 16.0, 18.0, 20.0, 22.0, 25.0, 30.0, 35.0, 40.0, 50.0)

    def check(self) -> "WeldSettings":
        if self.electrode not in ELECTRODES:
            raise ValueError("electrode E60 / E70 / E80")
        if self.shear_fix not in ("hairpins", "lug"):
            raise ValueError("shear_fix: hairpins / lug")
        for k in ("shop_min_leg", "one_side_max_leg", "weld_max_fillet", "stiffener_clip", "end_zone_depths",
                  "flange_brace_fraction", "base_plate_max", "grout"):
            v = getattr(self, k)
            if not (isinstance(v, (int, float)) and v > 0):
                raise ValueError(f"{k} must be > 0")
        if self.one_side_max_leg > self.weld_max_fillet:
            raise ValueError("one_side_max_leg must not exceed weld_max_fillet")
        if self.cleat_thickness is not None and not self.cleat_thickness > 0:
            raise ValueError("cleat_thickness must be > 0 (or blank: the model's cleat)")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "WeldSettings":
        d = dict(d or {})
        bad = set(d) - set(cls.__dataclass_fields__)
        if bad:
            raise ValueError(f"unknown weld settings: {', '.join(sorted(bad))}")
        for k in ("lug_heights", "plate_stock"):
            if k in d:
                d[k] = tuple(d[k])
        return cls(**d).check()

    @property
    def fexx(self) -> float:
        return ELECTRODES[self.electrode]


# ------------------------------------------------------------------------------------------------------- strengths

def weld_metal(leg: float, theta: float = 0.0, st: WeldSettings | None = None, directional: bool = True) -> float:
    """φRn of ONE fillet line per mm of length, N/mm — bimsteelauto 0.15.4 fillet_line_strength (pyaisc360 J2.4).
    directional=False: no 1 + 0.5 sin^1.5 θ."""
    st = st or WeldSettings()
    return fillet_line_strength(leg, t_base=10.0, base_grade="S355JR", theta=theta, electrode=st.electrode,
                                directional_increase=directional).weld


def base_metal(t: float, grade: str, lines_sharing: int = 1) -> float:
    """φRn of the base metal per mm per weld line, N/mm: 0.75 × 0.60 Fu t (J2-2), shared by the lines that straddle the
    plate (a double fillet on both faces of one plate: 2 → 0.45 Fu t / 2 per line) — bimsteelauto 0.15.4."""
    return fillet_line_strength(1.0, t_base=t, base_grade=grade, lines_sharing=lines_sharing).base


def base_metal_tension(t: float, grade: str, lines_sharing: int = 1) -> float:
    """A plate pulled ACROSS the weld (θ 90°: a stiffener into a flange): AISC 360-16 J4.1 per mm, min(0.9 Fy t,
    0.75 Fu t) (Ae = Ag), shared by the lines that straddle it, N/mm per line — bimsteelauto 0.15.4."""
    return fillet_line_strength(1.0, t_base=t, base_grade=grade, lines_sharing=lines_sharing, base_mode="tension").base


DEV_PLATE = "develops plate (by definition)"


def size_line(flow: float, theta: float, t_shared: float, t_thinner: float, grade: str, st: WeldSettings,
              lines_sharing: int = 2, directional: bool = True, leg_cap: float | None = None, mode: str = "shear",
              develops_plate: bool = False) -> dict:
    """The smallest leg of the list carrying `flow` (N/mm, per line): leg ≥ max(J2.4 by the thinner part, shop_min_leg),
    per line φRn = min(weld metal, base metal of the straddled plate shared by `lines_sharing`). Base metal: mode "shear"
    = 0.45 Fu t / lines (the user's rule, J2-2 / J4.2); mode "tension" (the plate pulled across the weld) = J4.1. The base
    metal does not grow with the leg: above it → FAILS (a thicker plate); a fillet over weld_max_fillet → CJP.
    develops_plate: the flow IS the straddled plate's design strength — the base metal row reads "develops plate (by
    definition)" and U is the weld metal's (user 2026-11-15)."""
    lo = max(min_weld_size(t_thinner), st.shop_min_leg)
    top = st.weld_max_fillet if leg_cap is None else min(leg_cap, st.weld_max_fillet)
    bm = base_metal(t_shared, grade, lines_sharing) if mode == "shear" else base_metal_tension(t_shared, grade, lines_sharing)
    out = {"flow": round(flow, 2), "theta": theta, "min_leg": lo, "base_metal": round(bm, 2), "base_metal_mode": mode,
           "base_metal_plate": t_shared, "lines_sharing": lines_sharing}
    if develops_plate:
        out["base_metal"] = f"{DEV_PLATE} ({round(bm, 2)} N/mm per line)"
        bm = math.inf
    if flow > bm + 1e-9:
        return {**out, "type": "FAILS", "leg": None, "U": round(flow / bm, 4), "ok": False,
                "why": f"base metal of the {t_shared:g} mm plate: {flow:.1f} > {bm:.1f} N/mm per line — a thicker plate"}
    for leg in FILLET_LEGS:
        if leg < lo - 1e-9 or leg > top + 1e-9:
            continue
        cap = min(weld_metal(leg, theta, st, directional), bm)
        if cap + 1e-9 >= flow:
            return {**out, "type": "fillet", "leg": leg, "capacity": round(cap, 2), "U": round(flow / cap, 4), "ok": True,
                    "governs": "weld metal" if weld_metal(leg, theta, st, directional) <= bm else "base metal",
                    "sized_by": "minimum" if leg == lo and flow <= min(weld_metal(lo, theta, st, directional), bm) else "demand"}
    if develops_plate:                                   # a CJP develops the plate by definition
        return {**out, "type": CJP, "leg": 0.0, "U": 1.0, "ok": True, "capacity": round(flow, 2),
                "why": f"a fillet over {top:g} mm would be needed"}
    return {**out, "type": CJP, "leg": 0.0, "U": round(flow / bm, 4), "ok": True, "capacity": round(bm, 2),
            "why": f"a fillet over {top:g} mm would be needed"}


# ------------------------------------------------------------------------------------------ flange-to-web welds

def section_at(seg: dict, f: float) -> dict:
    """The built-up section at fraction f of one segment (linear web height)."""
    hw = seg["hw_start"] + (seg["hw_end"] - seg["hw_start"]) * f
    return {"hw": hw, "tw": seg["tw"], "bf_top": seg["bf_top"], "tf_top": seg["tf_top"], "bf_bot": seg["bf_bot"],
            "tf_bot": seg["tf_bot"], "d": hw + seg["tf_top"] + seg["tf_bot"]}


def flange_web_q(sec: dict, V: float) -> dict:
    """Horizontal shear flow at each flange-to-web junction, N/mm: q = V Q / I (V in kN). Unequal flanges allowed."""
    bt, tt, bb, tb, hw, tw = sec["bf_top"], sec["tf_top"], sec["bf_bot"], sec["tf_bot"], sec["hw"], sec["tw"]
    d = hw + tt + tb
    parts = [(bt * tt, d - tt / 2), (hw * tw, tb + hw / 2), (bb * tb, tb / 2)]
    A = sum(a for a, _ in parts)
    yc = sum(a * y for a, y in parts) / A
    I = bt * tt ** 3 / 12 + tw * hw ** 3 / 12 + bb * tb ** 3 / 12 + sum(a * (y - yc) ** 2 for a, y in parts)
    Qt, Qb = bt * tt * (d - tt / 2 - yc), bb * tb * (yc - tb / 2)
    return {"I": I, "Q_top": Qt, "Q_bot": Qb, "q_top": abs(V) * 1000.0 * Qt / I, "q_bot": abs(V) * 1000.0 * Qb / I,
            "q": abs(V) * 1000.0 * max(Qt, Qb) / I}


def local_flow(P: float, lb: float) -> float:
    """A concentrated load P (kN) into the web through the flange-to-web weld, spread over lb (mm) → N/mm."""
    return P * 1000.0 / lb


def spread_length(t_cleat: float, tf: float, st: WeldSettings) -> float:
    """lb = t_cleat + 5 k, k = tf + shop_min_leg (Claude's rule, J10.2-like spread — TO CONFIRM)."""
    return t_cleat + 5.0 * (tf + st.shop_min_leg)


def body_weld(flow: float, sec: dict, grade: str, st: WeldSettings) -> dict:
    """Continuous flange-to-web weld for a demand flow (N/mm, the resultant): one-sided up to one_side_max_leg, both sides
    above; the web base metal 0.45 Fu tw caps both."""
    tw, tf = sec["tw"], min(sec["tf_top"], sec["tf_bot"])
    t_thin = min(tw, tf)
    cap_web = base_metal(tw, grade, 1)
    if flow > cap_web + 1e-9:
        return {"sides": None, "type": "FAILS", "leg": None, "flow": round(flow, 2), "web_base_metal": round(cap_web, 2),
                "U": round(flow / cap_web, 4), "ok": False,
                "why": f"web base metal 0.45 Fu tw = {cap_web:.1f} N/mm < {flow:.1f} N/mm — welding both sides cannot "
                       "beat it", "fixes": ["thicker web"]}
    one = size_line(flow, 0.0, tw, t_thin, grade, st, lines_sharing=1, leg_cap=st.one_side_max_leg)
    if one["type"] == "fillet":
        return {**one, "sides": "one side (continuous, SAW)", "web_base_metal": round(cap_web, 2)}
    two = size_line(flow / 2.0, 0.0, tw, t_thin, grade, st, lines_sharing=2)
    two["flow_total"] = round(flow, 2)
    return {**two, "sides": "both sides (continuous)", "web_base_metal": round(cap_web, 2),
            "why_two": f"one side would need more than {st.one_side_max_leg:g} mm"}


def end_zone_weld(sec: dict, grade: str, st: WeldSettings) -> dict:
    """Within one depth of an end plate: both sides, developing the web shear 0.9 × 0.6 Fy tw (N/mm)."""
    tw = sec["tw"]
    Fy, _ = get_grade(grade, tw)
    flow = PHI_V_WEB * 0.6 * Fy * tw
    w = size_line(flow / 2.0, 0.0, tw, min(tw, sec["tf_top"], sec["tf_bot"]), grade, st, lines_sharing=2)
    return {**w, "sides": "both sides", "flow_total": round(flow, 2), "basis": "develops the web shear 0.9 x 0.6 Fy tw"}


def _member_stations(fres: dict, mid: str) -> list[tuple[str, list]]:
    """[(combo, [(x_along_member, V, M), ...])] for one Manafe3 member in one frame result (LRFD only); the frame
    model's sub-members (RA1, RA2) are joined end to end."""
    marks = [m for m in fres["members"] if m["id"] == mid]
    out = []
    for name, r in fres["results"].items():
        if r.get("set") != "LRFD":
            continue
        rows, off = [], 0.0
        for m in marks:
            for x, _P, V, M in r["members"][m["mark"]]:
                rows.append((off + x, V, M))
            off += m["length"]
        out.append((name, rows))
    return out


def _spacing(positions: list[float]) -> float | None:
    p = sorted(set(round(v, 1) for v in positions))
    gaps = [b - a for a, b in zip(p, p[1:]) if b - a > 1.0]
    return max(gaps) if gaps else None


def _member_length(m: dict) -> float:
    return sum(s["length"] for s in m["section"]["segments"])


def _along(m: dict, point) -> float:
    """Distance from the member start to the projection of a point on the member line, mm."""
    s, e = m["start"], m["end"]
    v = [e[i] - s[i] for i in range(3)]
    L = math.sqrt(sum(c * c for c in v))
    return sum((point[i] - s[i]) * v[i] for i in range(3)) / L


def flange_web_member(m: dict, stations: list, grade: str, st: WeldSettings, local: dict, zones: list) -> dict:
    """One built-up member: per segment the governing station / combination and the body weld; the end zones."""
    segs = m["section"]["segments"]
    Lm = _member_length(m)
    Lf = max((rows[-1][0] for _, rows in stations if rows), default=Lm)
    bounds, acc = [], 0.0
    for s in segs:
        bounds.append((acc, acc + s["length"]))
        acc += s["length"]

    def seg_at(sm):
        for i, (a, b) in enumerate(bounds):
            if sm <= b + 1e-6:
                return i, (sm - a) / (b - a) if b > a else 0.0
        return len(segs) - 1, 1.0

    worst = [None] * len(segs)
    for combo, rows in stations:
        for k, (x, V, M) in enumerate(rows):
            sm = x * Lm / Lf
            i, f = seg_at(sm)
            sec = section_at(segs[i], f)
            qq = flange_web_q(sec, V)
            w = 0.0                                           # |dV/dx| of this combination, kN/mm
            for a, b in ((k - 1, k), (k, k + 1)):
                if 0 <= a and b < len(rows) and rows[b][0] - rows[a][0] > 1.0:
                    w = max(w, abs(rows[b][1] - rows[a][1]) / (rows[b][0] - rows[a][0]))
            tf = min(sec["tf_top"], sec["tf_bot"])
            lb = spread_length(local["t_cleat"], tf, st)
            P = w * local["spacing"] if local.get("spacing") else 0.0
            Ffb = st.flange_brace_fraction * abs(M) * 1000.0 / (sec["d"] - tf) if local.get("flange_braces") else 0.0
            p, fb = local_flow(P, lb), local_flow(Ffb, lb)
            flow = math.sqrt(qq["q"] ** 2 + p ** 2 + fb ** 2)
            if worst[i] is None or flow > worst[i]["flow"]:
                worst[i] = {"flow": flow, "combo": combo, "x": round(sm, 1), "V": V, "M": M, "q": round(qq["q"], 2),
                            "P_local": round(P, 3), "p_local": round(p, 2), "F_flange_brace": round(Ffb, 3),
                            "p_flange_brace": round(fb, 2), "lb": round(lb, 1), "d": round(sec["d"], 1), "sec": sec}
    seg_out = []
    for i, s in enumerate(segs):
        wv = worst[i]
        if wv is None:
            seg_out.append({"segment": i + 1, "status": NOT_EVALUATED, "missing": ["no analysis station on this segment"]})
            continue
        sec = wv.pop("sec")
        wd = body_weld(wv["flow"], sec, grade, st)
        seg_out.append({"segment": i + 1, "status": "DESIGNED" if wd["ok"] else "FAILS", "governing": {**wv,
                        "flow": round(wv["flow"], 2)}, "weld": wd})
    zone_out = []
    for z in zones:
        sm = min(max(z["at"], 0.0), Lm)
        i, f = seg_at(sm)
        sec = section_at(segs[i], f)
        L = st.end_zone_depths * sec["d"]
        zone_out.append({"joint": z["joint"], "from": round(max(0.0, sm - L), 1), "to": round(min(Lm, sm + L), 1),
                         "weld": end_zone_weld(sec, grade, st)})
    ok = all(s.get("status") == "DESIGNED" for s in seg_out) and all(z["weld"]["ok"] for z in zone_out)
    return {"member": m["id"], "role": m["role"], "segments": seg_out, "end_zones": zone_out,
            "status": "DESIGNED" if ok else ("NOT EVALUATED" if any(s.get("status") == NOT_EVALUATED for s in seg_out)
                                             else "FAILS"),
            "local_loads": {k: v for k, v in local.items()}, "notes": [BUTT_SPLICE_NOTE]}


# ----------------------------------------------------------------------------------------------- base plate weld

def base_weld(sec: dict, tp: float | None, cases: list[dict], grade: str, st: WeldSettings) -> dict:
    """Column-to-base-plate weld, double fillets all round (both faces of both flanges, both faces of the web). cases:
    {name, combo, Pu (kN, + compression), V_strong, V_weak}. Elastic, vector sum, NO directional increase."""
    d, bf, tf, tw = sec["d"], sec["bf"], sec["tf"], sec["tw"]
    out = {"pattern": "double fillets: both faces of both flanges and of the web", "notes": [BEARING_NOTE]}
    if tp is None:
        return {**out, "status": NOT_EVALUATED, "missing": ["no base plate thickness (step 2 not designed)"]}
    if tp > st.base_plate_max + 1e-9:
        return {**out, "status": NOT_EVALUATED, "tp": tp,
                "missing": [f"base plate {tp:g} mm > {st.base_plate_max:g} mm: bearing without milling not covered "
                            "(AISC 360-16 M2.6)"]}
    Lf, Lw = 2 * (2 * bf - tw), 2 * (d - 2 * tf)
    L = Lf + Lw
    rows = []
    for c in cases:
        T = max(0.0, -c["Pu"])
        u = T * 1000.0 / L
        vw = abs(c.get("V_strong", 0.0)) * 1000.0 / Lw
        vf = abs(c.get("V_weak", 0.0)) * 1000.0 / Lf
        rows.append({**{k: c.get(k) for k in ("name", "combo", "Pu", "V_strong", "V_weak")}, "uplift_flow": round(u, 2),
                     "web_shear_flow": round(vw, 2), "flange_shear_flow": round(vf, 2),
                     "web": round(math.hypot(u, vw), 2), "flange": round(math.hypot(u, vf), 2)})
    fw = max((r["web"] for r in rows), default=0.0)
    ff = max((r["flange"] for r in rows), default=0.0)
    web = size_line(fw, 0.0, tw, min(tw, tp), grade, st, lines_sharing=2, directional=False)
    fl = size_line(ff, 0.0, tf, min(tf, tp), grade, st, lines_sharing=2, directional=False)
    legs = [w["leg"] for w in (web, fl) if w["type"] == "fillet"]
    ok = web["ok"] and fl["ok"]
    res = {**out, "tp": tp, "lengths": {"flanges": Lf, "web": Lw, "total": L}, "cases": rows, "web": web, "flanges": fl,
           "status": "DESIGNED" if ok else "FAILS"}
    if ok:
        if any(w["type"] == CJP for w in (web, fl)):
            res["weld"] = CJP
        else:
            res["leg"] = max(legs)
    else:
        res["why"] = "; ".join(w["why"] for w in (web, fl) if not w["ok"])
    return res


# --------------------------------------------------------------------------------------------------- shear lug

def lug_bearing_factor(Pu: float, n_anchors: int, Nsa: float, Abp: float, fc: float) -> float:
    """ACI 318-19 17.11.2.1 Ψbrg,sl (as recalled — VERIFIED False): tension (Pu < 0): 1 + Pu / (n Nsa) ≤ 1;
    compression: 1 + 4 Pu / (Abp f'c) ≤ 2; none: 1."""
    if Pu < 0:
        return max(0.0, 1.0 + Pu / (n_anchors * Nsa))
    if Pu > 0:
        return min(2.0, 1.0 + 4.0 * Pu * 1000.0 / (Abp * fc))
    return 1.0


def shear_lug(Vu: float, Pu: float, B: float, tp: float, fc: float, grade: str, st: WeldSettings, n_anchors: int = 4,
              Nsa: float | None = None, Abp: float | None = None) -> dict:
    """A flat-plate shear lug under the base plate taking ALL the base shear (the anchors: tension only). kN, mm."""
    out = {"Vu": Vu, "Pu": Pu, "width": B, "grout": st.grout, "fc": fc, "verified": False,
           "breakout": {"status": NOT_EVALUATED, "U": math.inf,
                        "note": "ACI 318-19 17.11.3 shear-lug breakout: NOT EVALUATED until the user sends the printed text"},
           "anchors": "tension only (the lug takes all the shear)"}
    if Pu < 0 and Nsa is None:
        return {**out, "status": NOT_EVALUATED, "missing": ["anchor steel strength Nsa for the tension factor"]}
    psi = lug_bearing_factor(Pu, n_anchors, Nsa or 1.0, Abp or 1.0, fc)
    pick = None
    for h in st.lug_heights:
        cap = PHI_LUG_BEARING * 1.7 * fc * B * h * psi / 1000.0
        if cap + 1e-9 >= Vu:
            pick = (h, cap)
            break
    if pick is None:
        return {**out, "status": "FAILS", "psi_brg": round(psi, 4),
                "why": f"bearing: no lug height up to {max(st.lug_heights):g} mm carries {Vu:.1f} kN"}
    h, cap = pick
    Mu = Vu * (st.grout + h / 2.0) / 1000.0                     # kN·m
    t_req = None
    t = None
    for tt in sorted(st.plate_stock):
        Fy, _ = get_grade(grade, tt)
        req = math.sqrt(4.0 * Mu * 1e6 / (PHI_PLATE * Fy * B))
        if tt + 1e-9 >= req:
            t, t_req = tt, req
            break
    res = {**out, "psi_brg": round(psi, 4), "height": h, "bearing": {"phiVbrg": round(cap, 2), "U": round(Vu / cap, 4),
           "Aef": B * h, "phi": PHI_LUG_BEARING}, "Mu": round(Mu, 4)}
    if t is None:
        return {**res, "status": "FAILS", "why": "no stock plate thick enough for the lug bending"}
    shear, mom = Vu * 1000.0 / (2 * B), Mu * 1e6 / (t * B)
    flow = math.hypot(shear, mom)
    w = size_line(flow, 0.0, t, min(t, tp), grade, st, lines_sharing=2, directional=False)
    res.update(t=t, t_req=round(t_req, 2), weld={**w, "shear_flow": round(shear, 2), "moment_flow": round(mom, 2)})
    if not w["ok"]:
        return {**res, "status": "FAILS", "why": w["why"]}
    return {**res, "status": "DESIGNED - BREAKOUT NOT EVALUATED"}


def lug_needed(base: dict) -> bool:
    """The anchors fail in shear / breakout / pryout (step 2's fixes name it)."""
    if base.get("status") != "FAILS":
        return False
    txt = " ".join(base.get("fixes", []) + base.get("missing", [])).lower()
    return any(k in txt for k in ("breakout", "pryout", "shear"))


def anchor_Nsa(base: dict) -> float | None:
    """Nominal steel strength of one anchor rod, kN: Ase futa (ACI 318-19 17.6.1.2; library grade data)."""
    rod = base.get("rod") or {}
    g = ANCHOR_GRADES.get(rod.get("grade"))
    Ase = rod.get("thread_area") or THREAD_AREA.get(rod.get("d"))
    return None if g is None or not Ase else g.futa * Ase / 1000.0


# ---------------------------------------------------------------------------------------------- stiffener welds

def web_base_metal(flow_total: float, t_web: float, grade: str) -> dict:
    """The column web under the stiffener web welds on BOTH faces, per unit length, total for both faces (user review
    2026-11-12): φRn = min(1.0 × 0.6 Fy tw (J4.2 shear yielding), 0.75 × 0.6 Fu tw (J4.2 shear rupture)), N/mm."""
    Fy, Fu = get_grade(grade, t_web)
    y, r = 1.0 * 0.6 * Fy * t_web, 0.75 * 0.6 * Fu * t_web
    cap = min(y, r)
    return {"flow_total": round(flow_total, 2), "yield": round(y, 2), "rupture": round(r, 2), "capacity": round(cap, 2),
            "t": t_web, "U": round(flow_total / cap, 4), "ok": bool(flow_total <= cap + 1e-9)}


def column_stiffener_welds(F_pair: float, F_web: float, bs: float, ts: float, length: float, tf_col: float,
                           t_web: float, grade: str, st: WeldSettings, web_note: str = "column web",
                           clips: int = 2) -> dict:
    """Column transverse stiffener pair at one rafter-flange level (both faces of the column web). F_pair (kN) crosses the
    flange contact: each stiffener F_pair / 2 with a double fillet (both faces of the stiffener) across bs − clip (θ 90°,
    J4.1 on the stiffener); F_web (kN, the share the web panel takes) goes through the web welds along length − clip
    (θ 0°; length = the stiffener plate, d − 2 tf at full depth with a clip at both ends — clips 2 — or d/2 − tf at half
    depth — clips 1), and the column web takes it from both faces: web_base_metal. Never below J2.4 / shop_min_leg; CJP above 12 mm."""
    Lfl, Lwb = bs - st.stiffener_clip, length - clips * st.stiffener_clip      # full depth: a clip at both flanges
    if Lfl <= 0 or Lwb <= 0:
        return {"status": "FAILS", "why": f"the clip {st.stiffener_clip:g} mm leaves no weld length"}
    fl = size_line(F_pair / 2.0 * 1000.0 / 2.0 / Lfl, 90.0, ts, min(ts, tf_col), grade, st, lines_sharing=2, mode="tension")
    wb = size_line(F_web / 2.0 * 1000.0 / 2.0 / Lwb, 0.0, ts, min(ts, t_web), grade, st, lines_sharing=2)
    wbm = {**web_base_metal(F_web * 1000.0 / Lwb, t_web, grade), "plate": web_note}
    ok = fl["ok"] and wb["ok"] and wbm["ok"]
    out = {"force_pair": round(F_pair, 2), "force_web": round(F_web, 2), "force_each": round(F_pair / 2.0, 2),
           "length_flange": Lfl, "length_web": round(Lwb, 1), "to_flange": fl, "to_web": wb, "web_base_metal": wbm,
           "status": "DESIGNED" if ok else "FAILS",
           "basis": "the pair carries F = max(Rst, the diagonal's dV) across the flange; its web welds only the panel's share"}
    if not wbm["ok"]:
        out["why"] = (f"{web_note} base metal: {wbm['flow_total']:.1f} > {wbm['capacity']:.1f} N/mm (both faces)")
        out["fixes"] = ["doubler or thicker web"]
    return out


def diagonal_welds(As_req: float, Fy: float, bs: float, t_d: float, t_other: float, grade: str, st: WeldSettings,
                   corner_axial: float = 0.0) -> dict:
    """Diagonal stiffener pair: its end welds (the corner at the stiffener and the column flange) across bs, a double
    fillet each plate (θ 90°), for max(As_req Fy, the corner force from the transverse stiffener along the diagonal,
    corner_axial = F_corner / cos θ) (kN, the pair); along the web the minimum leg (continuity)."""
    F_as = As_req * Fy / 1000.0
    F = max(F_as, corner_axial)
    each = F / 2.0
    end = size_line(each * 1000.0 / 2.0 / bs, 90.0, t_d, min(t_d, t_other), grade, st, lines_sharing=2, mode="tension")
    return {"force_pair": round(F, 2), "force_As_Fy": round(F_as, 2), "corner_axial": round(corner_axial, 2),
            "force_each": round(each, 2), "ends": end,
            "web": {"leg": max(min_weld_size(t_d), st.shop_min_leg), "sized_by": "minimum (continuity)"},
            "status": "DESIGNED" if end["ok"] else "FAILS"}


def doubler_welds(dV: float, dc: float, td: float, tf_col: float, grade: str, st: WeldSettings) -> dict:
    """Doubler plate: its required shear dV = Vu − φVpanel (kN) as a flow dV / dc (N/mm) along each flange edge, a single
    fillet each edge (θ 0°); the top / bottom edges the minimum leg."""
    flow = dV * 1000.0 / dc
    edge = size_line(flow, 0.0, min(td, tf_col), min(td, tf_col), grade, st, lines_sharing=1)
    return {"dV": round(dV, 2), "flow": round(flow, 2), "flange_edges": edge,
            "top_bottom": {"leg": max(min_weld_size(td), st.shop_min_leg), "sized_by": "minimum"},
            "status": "DESIGNED" if edge["ok"] else "FAILS"}


def endplate_stiffener_welds(hst: float, Lst: float, ts: float, tp: float, tf_beam: float, grade: str,
                             st: WeldSettings) -> dict:
    """4ES / 8ES end-plate stiffener: double fillets developing the stiffener's DESIGN strength — 0.9 Fy ts per mm into
    the end plate (J4.1, θ 90°), 0.6 Fy ts per mm along the beam flange (J4.2 shear yielding, φ 1.0, θ 0°); CJP above
    12 mm. AISC 358 is reference only (non-seismic)."""
    Fy, _ = get_grade(grade, ts)
    to_plate = size_line(PHI_PLATE * Fy * ts / 2.0, 90.0, ts, min(ts, tp), grade, st, lines_sharing=2, mode="tension",
                         develops_plate=True)
    to_flange = size_line(0.6 * Fy * ts / 2.0, 0.0, ts, min(ts, tf_beam), grade, st, lines_sharing=2)
    ok = to_plate["ok"] and to_flange["ok"]
    return {"to_end_plate": {**to_plate, "length": hst}, "to_beam_flange": {**to_flange, "length": Lst},
            "status": "DESIGNED" if ok else "FAILS", "basis": "develops the stiffener's design strength: 0.9 Fy ts into the plate (J4.1), 0.6 Fy ts along the flange (J4.2, phi 1.0)",
            "reference": "AISC 358-16 Sect. 6 — reference only (non-seismic frames), unverified"}


# ------------------------------------------------------------------------------------------------- the building

def _frame_result(an: dict, x: float) -> tuple[dict | None, str | None]:
    """The frame-line result for a Manafe3 frame line at x (same_as resolved) and its id prefix."""
    by_line = {f["line"]: f for f in an.get("frames", [])}
    for f in an.get("frames", []):
        if abs(f["x"] - x) < 1.0:
            src = by_line.get(f.get("same_as") or f["line"], f)
            return src.get("result"), f"F{src['line']}-"
    return None, None


def building_welds(joints_result: dict, out: dict, analysis: dict, bases_result: dict | None = None,
                   settings: WeldSettings | None = None, base_settings=None, li=None,
                   flexible_diaphragm: bool | None = None) -> dict:
    """The step 4 welds over a building: flange-to-web of every frame column and rafter, the column-to-base-plate weld of
    every base (with the braced-bay brace case), the shear lug where selected and needed."""
    from .baseplates import BaseSettings, column_section, design_base     # local: avoid an import cycle
    from .longitudinal import braced_base, building_record
    st = (settings or WeldSettings()).check()
    bst = base_settings or BaseSettings()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    notes = [BUTT_SPLICE_NOTE]
    slope = float(out["input"]["roof_slope"])
    k_slope = math.sqrt(1.0 + slope * slope)
    t_cleat = st.cleat_thickness
    if t_cleat is None:
        prof = next((c.get("profile", "") for c in out.get("cleats", []) if c.get("profile", "").startswith("PL")), "")
        try:
            t_cleat = float(prof[2:].split("x")[0])
        except ValueError:
            t_cleat = None
    if t_cleat is None:
        notes.append("no purlin / girt cleat in the model: the local loads are NOT EVALUATED (no bearing length)")
    others = out["members"]
    ends = [j for j in joints_result["joints"] if j["type"] in ("knee", "ridge", "rafter_splice")]
    fw_rows = []
    for m in out["members"]:
        if m.get("role") not in ("column", "rafter") or not m.get("section"):
            continue
        fres, pref = _frame_result(analysis, m["start"][0])
        mid_src = None if pref is None else pref + m["id"].split("-", 1)[1]
        if fres is None or not any(x["id"] == mid_src for x in fres["members"]):
            fw_rows.append({"member": m["id"], "role": m["role"], "status": NOT_EVALUATED,
                            "missing": ["no frame-line analysis for this member"]})
            continue
        side = m.get("side")
        host = f"{m['role']} {side}"
        if m["role"] == "rafter":
            ys = [o["start"][1] for o in others if o.get("role") in ("purlin", "eave_strut") and o.get("side") == side]
            sp = _spacing(ys)
            sp = None if sp is None else sp * k_slope
            what = "purlins"
        else:
            zs = [o["start"][2] for o in others if o.get("role") == "girt" and o.get("side") == side]
            sp = _spacing(zs)
            what = "girts"
        fbs = any(o.get("role") == "flange_brace" and o.get("host") == host and abs(o["start"][0] - m["start"][0]) < 1.0
                  for o in others)
        local = {"t_cleat": t_cleat or 0.0, "spacing": sp if t_cleat else None, "carried_by": what,
                 "flange_braces": bool(fbs and t_cleat),
                 "rule": "local loads w x spacing (w = |dV/dx|, same combination) and 2 % of the flange force, spread "
                         "over lb = t_cleat + 5 k (TO CONFIRM); applied at every station (conservative)"}
        zones = []
        for j in ends:
            for jm in j["members"]:
                if jm["id"] == m["id"]:
                    zones.append({"joint": j["id"], "at": _along(m, j["point"])})
        zones = [dict(t) for t in {(z["joint"], round(z["at"], 1)): z for z in zones}.values()]
        stations = _member_stations(fres, mid_src)
        fw_rows.append(flange_web_member(m, stations, _plate_grade(m), st, local, zones))
    # wind columns (the forces of their member check: C&C 1.0 W simple beam, both directions) and end-wall rafters
    efs = {e["end"]: e for e in analysis.get("end_frames", [])}
    wcs = [m for m in out["members"] if m.get("role") == "wind_column" and m.get("section")]
    if wcs:
        inputs = {}
        why = None
        if li is None:
            why = "the loads input (li) is needed for the wind-column forces"
        else:
            from ..design.secondary_checks import wind_column_inputs
            try:
                inputs = {row["id"]: (row, inp) for row, inp in wind_column_inputs(out, li, efs)}
            except Exception as exc:                                     # stated, never a silent pass
                why = f"wind-column forces: {exc}"
        for m in wcs:
            if m["id"] not in inputs:
                fw_rows.append({"member": m["id"], "role": m["role"], "status": NOT_EVALUATED,
                                "missing": [why or "no wind-column forces for this member"]})
                continue
            row, inp = inputs[m["id"]]
            stations = [(combo, [(f.station, f.Vy, f.Mz) for f in sts]) for combo, sts in inp.forces.items()]
            local = {"t_cleat": t_cleat or 0.0, "spacing": _spacing([0.0, *row["girts"]]) if t_cleat else None,
                     "carried_by": "gable girts", "flange_braces": bool(row["flange_braces"] and t_cleat),
                     "rule": "as the frame members; forces: the wind column's member check (C&C 1.0 W, simple beam)"}
            fw_rows.append(flange_web_member(m, stations, _plate_grade(m), st, local, []))
    er_joints = [j for j in joints_result["joints"] if j["type"] in ("end_rafter_ridge", "end_rafter_splice")]
    for m in out["members"]:
        if m.get("role") != "end_rafter" or not m.get("section"):
            continue
        end = "first" if m["id"][1] == "F" else "last"
        ef = efs.get(end)
        if ef is None:
            fw_rows.append({"member": m["id"], "role": m["role"], "status": NOT_EVALUATED,
                            "missing": [f"no end-rafter frame analysis for the {end} end wall"]})
            continue
        stations = end_rafter_stations(ef, m, k_slope)
        side = m["id"][-1]
        ys = [o["start"][1] for o in others if o.get("role") in ("purlin", "eave_strut") and o.get("side") == side]
        sp = _spacing(ys)
        fbs = any(o.get("role") == "flange_brace" and str(o.get("host", "")).startswith("end rafter")
                  and abs(o["start"][0] - m["start"][0]) < 1.0 for o in others)
        local = {"t_cleat": t_cleat or 0.0, "spacing": (sp * k_slope if sp else None) if t_cleat else None,
                 "carried_by": "purlins", "flange_braces": bool(fbs and t_cleat),
                 "rule": "as the frame rafters; forces: the end-rafter frame (LRFD rafter stations)"}
        zones = [{"joint": j["id"], "at": _along(m, j["point"])} for j in er_joints
                 if any(jm["id"] == m["id"] for jm in j["members"])]
        fw_rows.append(flange_web_member(m, stations, _plate_grade(m), st, local, zones))
    # bases
    base_rows = []
    by_joint = {b["joint"]: b for b in (bases_result or {}).get("bases", [])}
    for j in joints_result["joints"]:
        if j["type"] not in ("base", "wind_column_base"):
            continue
        m = mem[j["members"][0]["id"]]
        sec = column_section(m)
        b = by_joint.get(j["id"])
        grade = _plate_grade(m)
        row = {"joint": j["id"], "type": j["type"], "member": m["id"]}
        if j.get("status") != "EVALUATED" or not j.get("forces"):
            base_rows.append({**row, "status": NOT_EVALUATED, "missing": ["no forces at this base"]})
            continue
        F = j["forces"]
        if j["type"] == "base":
            cases = [{"name": "max compression", "combo": F["compression"]["combo"], "Pu": F["compression"]["value"],
                      "V_strong": abs(F["compression"].get("H", 0.0)), "V_weak": 0.0}]
            if F["uplift"].get("combo"):
                cases.append({"name": "max uplift", "combo": F["uplift"]["combo"], "Pu": -F["uplift"]["value"],
                              "V_strong": abs(F["uplift"].get("H", 0.0)), "V_weak": 0.0})
            if F["shear"].get("combo"):
                cases.append({"name": "max shear", "combo": F["shear"]["combo"], "Pu": F["shear"].get("V", 0.0),
                              "V_strong": abs(F["shear"]["value"]), "V_weak": 0.0})
        else:
            cases = [{"name": "max compression + max shear (paired conservatively, step 2)", "combo": "envelope",
                      "Pu": F["P_comp"], "V_strong": F["V_out_of_plane"], "V_weak": 0.0}]
            if F.get("uplift", 0.0) > 0:
                cases.append({"name": "max uplift + max shear (paired conservatively, step 2)", "combo": "envelope",
                              "Pu": -F["uplift"], "V_strong": F["V_out_of_plane"], "V_weak": 0.0})
        tp = None if b is None else b.get("t")
        res = base_weld(sec, tp, cases, grade, st)
        # braced bay (open item 6): the frame reaction + the wall brace of the SAME combination (longitudinal.py)
        lon = braced_base(j, m, out, analysis, flexible_diaphragm)
        if lon is not None:
            if lon["cases"]:
                res = base_weld(sec, tp, cases + lon["cases"], grade, st)
            res["longitudinal"] = lon
            if lon["status"] != "EVALUATED" and res.get("status") == "DESIGNED":
                res["status"] = PARTIAL
                res.setdefault("missing", []).append(lon["why"])
        row.update(res)
        # shear lug
        if b is not None and lug_needed(b):
            if st.shear_fix == "lug":
                Vmax = max(c["V_strong"] for c in cases)
                Pmin = min(c["Pu"] for c in cases)
                g = b.get("geometry", {})
                Abp = g.get("N", 0) * g.get("B", 0) or None
                lug = shear_lug(Vmax, Pmin, st.lug_width or sec["bf"], tp or 0.0, bst.fc, grade, st,
                                Nsa=anchor_Nsa(b), Abp=Abp)
                j0 = {**j, "forces": _no_shear(j)}
                lug["anchors_tension_only"] = design_base(j0, sec, m.get("material", "S355"), bst).get("status")
                row["shear_lug"] = lug
            else:
                row["shear_lug"] = {"status": "not selected", "note": "shear_fix = hairpins (step 2b anchor reinforcement)"}
        base_rows.append(row)
    counts: dict[str, dict] = {"flange_web": {}, "bases": {}}
    for r in fw_rows:
        counts["flange_web"][r["status"]] = counts["flange_web"].get(r["status"], 0) + 1
    for r in base_rows:
        counts["bases"][r["status"]] = counts["bases"].get(r["status"], 0) + 1
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "concrete_fc": bst.fc, "flange_web": fw_rows,
            "longitudinal": building_record(out, analysis, flexible_diaphragm),
            "bases": base_rows, "counts": counts, "notes": notes,
            "open_flags": sorted(f"engine.connections.welds.{k}" for k, v in VERIFIED.items() if not v)}


def end_rafter_stations(ef: dict, m: dict, k_slope: float) -> list:
    """[(combo, [(x along the member, V, M), ...])] of one end-wall rafter (A or B) from the end-rafter frame's LRFD
    rafter stations [y, P, V, M] (y across the building): the stations within the member's y range, x = |y − y_start| ×
    √(1 + slope²)."""
    y0, y1 = m["start"][1], m["end"][1]
    lo, hi = min(y0, y1), max(y0, y1)
    out = []
    for combo, r in ef["results"].items():
        if r.get("set") != "LRFD" or not r.get("rafter_stations"):
            continue
        rows = sorted((abs(y - y0) * k_slope, V, M) for y, _P, V, M in r["rafter_stations"] if lo - 1.0 <= y <= hi + 1.0)
        out.append((combo, rows))
    return out


def _plate_grade(m: dict) -> str:
    from .baseplates import PLATE_GRADE
    return PLATE_GRADE.get(m.get("material", "S355"), "S355JR")


def _no_shear(j: dict) -> dict:
    F = {k: (dict(v) if isinstance(v, dict) else v) for k, v in j["forces"].items()}
    for k in ("compression", "uplift", "shear"):
        if isinstance(F.get(k), dict) and "H" in F[k]:
            F[k]["H"] = 0.0
    if isinstance(F.get("shear"), dict):
        F["shear"]["value"] = 0.0
    if "V_out_of_plane" in F:
        F["V_out_of_plane"] = 0.0
    return F
