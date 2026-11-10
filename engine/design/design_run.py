# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 9: "Design…" for one building — Check (analysis + every member check) and Size (step 8 + the end walls),
results keyed by MODEL member id, a summary and per-member calculation data. NOT FOR ISSUE.

    settings  code_basis "AISC" | "ECP" | "both" (ECP covers the main frames; the other members stay AISC 360 / AISI S100),
              governing "AISC" | "ECP" (the project setting: the ratio that colours and sizes), target 0.90, limits
              (ServiceLimits: sway, rafter_Lr, purlin), uplift_method "r_factor" (default, industry practice — user
              2026-11-09) with the strict-rule ratio shown beside it, stability "dg25" | "prismatic"
    Check     main frames: every distinct frame line, each code asked for (sizing.evaluate); wind columns, end rafters,
              bracing, purlins, girts, eave struts (secondary_checks with cfs_checks, by the uplift mode AND strict)
    Size      main frames by the step 8 loop (the governing code); purlin / eave strut / girt by the R-factor (sizing
              .size_cold_formed); wind columns and end rafters by the same plate lists on their held forces (size_end_walls);
              then a full Check of the proposed building. Nothing is written to the model here: the browser shows the
              proposal and "Apply" writes it (one undo step).
Every row: member id, kind, section, code, ratio (None = NOT EVALUATED), governing check + clause, combination, station,
VERIFIED (False while any flag it rests on is open) and the flags; the per-member calc data carries the check rows
(demand, capacity, ratio, clause, note), the section, restraints and forces.
"""

from __future__ import annotations

import dataclasses
import math

from bimsteelauto.design import check_member
from bimsteelauto.sections import TaperedMember, WeldedI

from ..peb.building import BuildingInput, peb_building, resolve
from ..peb.endwall import wind_column_section
from .serviceability import ServiceLimits

BANNER = "NOT FOR ISSUE — design results with unconfirmed (VERIFIED False) items; see the list in the summary"
STEEL_KG_MM3 = 7.85e-6
UPLIFT = ("r_factor", "strict")


# --------------------------------------------------------------------------------------------- settings and JSON

@dataclasses.dataclass(frozen=True)
class DesignSettings:
    code_basis: str = "both"
    governing: str = "AISC"
    target: float = 0.90
    limits: dict | None = None
    uplift_method: str = "r_factor"
    stability: str = "dg25"

    def check(self) -> "DesignSettings":
        if self.code_basis not in ("AISC", "ECP", "both"):
            raise ValueError("code basis must be AISC, ECP or both")
        if self.governing not in ("AISC", "ECP"):
            raise ValueError("governing code must be AISC or ECP")
        if self.code_basis != "both" and self.governing != self.code_basis:
            raise ValueError("the governing code must be the code basis (or choose both)")
        if not (0.5 <= self.target <= 1.0):
            raise ValueError("target utilisation must be 0.5 to 1.0")
        if self.uplift_method not in UPLIFT:
            raise ValueError("uplift mode must be r_factor or strict")
        if self.stability not in ("dg25", "prismatic"):
            raise ValueError("stability must be dg25 or prismatic")
        ServiceLimits.from_dict(self.limits)
        return self

    @property
    def codes(self) -> list[str]:
        return ["AISC", "ECP"] if self.code_basis == "both" else [self.code_basis]


def clean(o):
    """JSON-safe: inf / nan → None, numpy scalars → float, tuples → lists."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [clean(v) for v in o]
    if isinstance(o, bool) or o is None or isinstance(o, str):
        return o
    try:
        f = float(o)
    except (TypeError, ValueError):
        return str(o)
    if isinstance(o, int) and not isinstance(o, bool):
        return o
    return f if math.isfinite(f) else None


def _ratio(v):
    return None if v is None or not math.isfinite(float(v)) else round(float(v), 4)


# --------------------------------------------------------------------------------------------- weights

def member_kg(m: dict) -> float:
    """Steel mass of one generated member (built-up plates, lipped C / Z, rods, angles, plates)."""
    import re
    from .cfs_section import centreline, parse_name, properties
    from .secondary_checks import angle_props
    if "section" in m:
        return sum(((s["hw_start"] + s["hw_end"]) / 2 * s["tw"] + s["bf_top"] * s["tf_top"] + s["bf_bot"] * s["tf_bot"]) * s["length"]
                   for s in m["section"]["segments"]) * STEEL_KG_MM3
    L = m.get("length") or m.get("cut_length") or math.dist(m["start"], m["end"])
    p = str(m.get("profile", ""))
    if p[:1] in "CZ":
        try:
            g = parse_name(p)
            return properties(centreline(g["kind"], g["H"], g["B"], g["D"], g["t"]), g["t"], g["H"])["A"] * L * STEEL_KG_MM3
        except ValueError:
            return 0.0
    if (r := re.fullmatch(r"RD(\d+(?:\.\d+)?)", p)):
        return math.pi * float(r[1]) ** 2 / 4 * L * STEEL_KG_MM3
    if (r := re.fullmatch(r"L(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", p)):
        return angle_props(float(r[1]), float(r[2]))["A"] * L * STEEL_KG_MM3
    if (r := re.fullmatch(r"PL(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", p)):
        return float(r[1]) * float(r[2]) * L * STEEL_KG_MM3
    return 0.0


def building_weight(out: dict) -> dict:
    by = {}
    for m in out["members"]:
        by[m["role"]] = by.get(m["role"], 0.0) + member_kg(m)
    inp = out["input"]
    area = float(inp["span"]) * sum(float(v) for v in inp["bays"]) / 1e6
    tot = sum(by.values())
    return {"kg": round(tot, 1), "t": round(tot / 1000, 3), "kg_m2": round(tot / area, 2), "plan_m2": round(area, 1),
            "by_role_kg": {k: round(v, 1) for k, v in sorted(by.items())}}


# --------------------------------------------------------------------------------------------- end-wall members on held forces

SECTION_LISTS = {"tw": (6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 25.0), "tf": (8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 25.0),
                 "bf": (150.0, 180.0, 200.0, 220.0, 250.0, 300.0)}


def _sec_step(s: dict, k: str, d: int, hw_min=300.0, hw_max=1500.0):   # 300: the generator's web minimum, as the frames
    if k == "hw":
        v = s["hw"] + 25.0 * d
        return {**s, "hw": v} if hw_min <= v <= hw_max else None
    lad = SECTION_LISTS[k]
    up = [x for x in lad if (x > s[k] if d > 0 else x < s[k])]
    if not up:
        return None
    return {**s, k: up[0] if d > 0 else up[-1]}


def _area(s):
    return s["hw"] * s["tw"] + 2 * s["bf"] * s["tf"]


def size_section(ratio_of, start: dict, target: float) -> tuple[dict, float]:
    """Greedy on {hw, tw, bf, tf}: raise the best ratio drop per mm² until ≤ target, then lower the largest saving."""
    s = dict(start)
    for k in ("tw", "tf"):
        if s[k] not in SECTION_LISTS[k]:
            s[k] = min((x for x in SECTION_LISTS[k] if x >= s[k]), default=SECTION_LISTS[k][-1])
    if s["bf"] not in SECTION_LISTS["bf"]:
        s["bf"] = min((x for x in SECTION_LISTS["bf"] if x >= s["bf"]), default=300.0)
    cache = {}

    def R(x):
        key = tuple(x[k] for k in ("hw", "tw", "bf", "tf"))
        if key not in cache:
            cache[key] = ratio_of(x)
        return cache[key]
    r = R(s)
    for _ in range(80):
        if r <= target:
            break
        best = None
        for k in ("hw", "tw", "bf", "tf"):
            s2 = _sec_step(s, k, +1)
            if s2 is None:
                continue
            r2 = R(s2)
            score = (r - r2) / max(_area(s2) - _area(s), 1e-6)
            if best is None or score > best[0]:
                best = (score, s2, r2)
        if best is None:
            break
        s, r = best[1], best[2]
    moved = True
    while moved:
        moved = False
        for k in sorted(("hw", "tw", "bf", "tf"), key=lambda k: -(_area(s) - _area(_sec_step(s, k, -1) or s))):
            s2 = _sec_step(s, k, -1)
            if s2 is None or _area(s2) >= _area(s):
                continue
            r2 = R(s2)
            if r2 <= target:
                s, r, moved = s2, r2, True
                break
    return s, r


def size_end_walls(b: BuildingInput, li, target: float = 0.90) -> dict:
    """Wind columns (one section for all) and end rafters (one section) on their held forces (the current building)."""
    from .frame_checks import _materials
    from .inputs import section_strength
    from .secondary_checks import end_rafter_frame, end_rafter_inputs, secondary_kpa, wind_column_inputs
    b, _ = resolve(b)
    out = peb_building(b)
    sec = secondary_kpa(out)
    efs = {e["end"]: end_rafter_frame(out, e["end"], li, roof_secondary_kpa=sec["roof_kpa"], wall_secondary_kpa=sec["wall_kpa"])
           for e in out["end_walls"] if e["kind"] == "rafter"}
    res = {}
    grade = "S355"

    def ratio_for(inputs):
        def f(s):
            wi = WeldedI(d=s["hw"] + 2 * s["tf"], tw=s["tw"], bf_top=s["bf"], tf_top=s["tf"], bf_bot=s["bf"], tf_bot=s["tf"])
            st = section_strength(dict(tw=s["tw"], tf_top=s["tf"], tf_bot=s["tf"], grade=grade))
            worst = 0.0
            for meta, inp in inputs:
                L = inp.taper.length
                d = check_member(dataclasses.replace(inp, taper=TaperedMember(wi, wi, L), materials=_materials(st["Fy"], st["Fu"])))
                worst = max(worst, float(d.utilisation))
            return worst
        return f
    wc_in = wind_column_inputs(out, li, efs)
    if wc_in:
        cur = wind_column_section(b.wind_column)
        s, r = size_section(ratio_for(wc_in), {k: cur[k] for k in ("hw", "tw", "bf", "tf")}, target)
        res["wind_column"] = {"from": {k: cur[k] for k in ("hw", "tw", "bf", "tf")}, "to": s, "quick_ratio": round(r, 4)}
    er_in = [x for ef in efs.values() for x in end_rafter_inputs(out, ef)]
    if er_in:
        m = next(x for x in out["members"] if x["role"] == "end_rafter")
        seg = m["section"]["segments"][0]
        cur = {"hw": seg["hw_start"], "tw": seg["tw"], "bf": seg["bf_top"], "tf": seg["tf_top"]}
        s, r = size_section(ratio_for(er_in), cur, target)
        res["end_rafter"] = {"from": cur, "to": s, "quick_ratio": round(r, 4),
                             "note": "end-rafter forces held from the current section's analysis; the final Check re-analyses"}
    return res


# --------------------------------------------------------------------------------------------- rows

def _row(mid, kind, section, code, ratio, governing, clause, combo, x, flags, extra=None):
    return {"id": mid, "kind": kind, "section": section, "code": code, "ratio": _ratio(ratio), "not_evaluated": _ratio(ratio) is None,
            "governing": governing, "clause": clause, "combo": combo, "x": None if x is None else round(float(x), 1),
            "verified": not flags, "flags": sorted(set(flags)), **(extra or {})}


def _gov_clause(checks, name):
    c = next((c for c in checks if c.get("name") == name), None)
    return (c or {}).get("reference") or (c or {}).get("clause") or ""


def frame_rows(ev: dict, code: str) -> tuple[list[dict], dict]:
    rows, calc = [], {}
    flags = list(ev["lines"][0]["check"].get("open_flags", []))
    for l in ev["lines"]:
        for m in l["check"]["members"]:
            suffix = m["id"].split("-", 1)[1]
            for ln in l["lines"]:
                mid = f"F{ln}-{suffix}"
                rows.append(_row(mid, "column" if m["name"].startswith("column") else "rafter", m.get("section", ""), code, m["ratio"],
                                 m["governing"], _gov_clause(m["checks"], m["governing"]), m["combo"], m["x"], flags,
                                 {"line": ln, "same_as_line": l["lines"][0]}))
                calc[f"{mid}|{code}"] = {"id": mid, "code": code, "design_member": m["name"], "length": m.get("length"), "Fy": m.get("Fy"),
                                         "section": m.get("section"), "restraints": m.get("Lb_points") or {"KL_in_plane": m.get("KL_in_plane"), "KL_out_of_plane": m.get("KL_out_of_plane"), "K": m.get("K_in_plane")},
                                         "forces": {**(m.get("forces") or {}), "combo": m["combo"], "x": m["x"]}, "checks": m["checks"], "flags": flags}
    return rows, calc


def secondary_rows(sc: dict, strict: dict | None, out: dict) -> tuple[list[dict], dict]:
    from ..analysis.cc_wind import VERIFIED as CC_VERIFIED
    from .cfs_checks import R_VERIFIED
    from .cfs_section import VERIFIED as CFS_VERIFIED
    rows, calc = [], {}
    ids = {m["id"]: m for m in out["members"]}
    aisc_flags = [f"engine.analysis.cc_wind.{k}" for k, v in CC_VERIFIED.items() if not v]
    cf_flags = [f"engine.design.cfs_section.{k}" for k, v in CFS_VERIFIED.items() if not v] + ["aisi_s100.shear_strength phi 0.90 (vendored, vs S100-16 G2.1)"]
    for w in sc["wind_columns"]:
        rows.append(_row(w["id"], "wind column", ids[w["id"]].get("profile", ""), "AISC", w["ratio"], w["governing"], _gov_clause(w["checks"], w["governing"]),
                         w["combo"], w["x"], aisc_flags))
        calc[w["id"] + "|AISC"] = {"id": w["id"], "code": "AISC", "section": ids[w["id"]].get("profile"), "restraints": {"outer flange (girts)": w.get("girts"), "inner flange (flange braces)": w.get("flange_braces")},
                                   "forces": {**w["forces"], "combo": w["combo"], "x": w["x"]}, "checks": w["checks"], "flags": aisc_flags}
    for e in sc["end_rafters"]:
        rows.append(_row(e["id"], "end rafter", ids[e["id"]].get("profile", ""), "AISC", e["ratio"], e["governing"], _gov_clause(e["checks"], e["governing"]),
                         e["combo"], e["x"], []))
        calc[e["id"] + "|AISC"] = {"id": e["id"], "code": "AISC", "section": ids[e["id"]].get("profile"), "restraints": {"top": e.get("Lb_top"), "bottom": e.get("Lb_bottom")},
                                   "forces": {**e["forces"], "combo": e["combo"], "x": e["x"]}, "checks": e["checks"], "flags": []}
    role_of = {"roof brace": "roof_brace", "wall brace": "wall_brace"}
    for br in sc["bracing"]:
        role = role_of.get(br["what"])
        members = [m for m in out["members"] if (m["role"] == role if role else (m["role"] == "endwall_brace" and br["what"].endswith(f"({m.get('wall')} end)")))]
        for m in members:
            rows.append(_row(m["id"], br["what"], br["profile"], "AISC", br["ratio"], br["governing"], _gov_clause(br["checks"], br["governing"]), "LRFD", None,
                             ["U = 0.6 placeholder (Phase 5)"] if br["profile"].startswith("L") else []))
            calc[m["id"] + "|AISC"] = {"id": m["id"], "code": "AISC", "section": br["profile"], "forces": {"T": br["T"], "combo": "LRFD, largest"}, "checks": br["checks"], "flags": []}
    cf = sc["cold_formed"]
    st = {}
    if strict:
        for g in ("purlins", "eave_struts", "girts", "gable_girts"):
            for r in strict[g]:
                st[r["id"]] = r
    r_flags = ([] if R_VERIFIED else ["AISI S100-16 Table I6.2.1-1 R values unconfirmed"])
    for g in ("purlins", "eave_struts", "girts", "gable_girts"):
        for r in cf[g]:
            pieces = [m for m in out["members"] if m.get("line") == r["id"] or m["id"] == r["id"] or (g == "gable_girts" and m["id"].split("-")[0] == r["id"])]
            flags = list(cf_flags) + (r_flags if r.get("uplift_method") == "r_factor" else [])
            s = st.get(r["id"])
            for m in pieces:
                rows.append(_row(m["id"], r["kind"].replace("_", " "), r["profile"], "AISI", r["ratio"], r["governing"], _gov_clause(r["checks"], r["governing"]),
                                 r["combo"], r["x"], flags, {"uplift_method": r.get("uplift_method"), "strict_ratio": _ratio(s["ratio"]) if s else None, "line_id": r["id"]}))
            calc[r["id"] + "|AISI"] = {"id": r["id"], "code": "AISI", "pieces": [m["id"] for m in pieces], "section": r["section"], "zones": r["zones"],
                                       "loads": r["loads_kN_m"], "r_factor": r.get("r_factor"), "forces": {**r["forces"], "combo": r["combo"], "x": r["x"]},
                                       "checks": r["checks"], "strict": {"ratio": s["ratio"], "governing": s["governing"]} if s else None, "flags": flags}
    return rows, calc


# --------------------------------------------------------------------------------------------- check and size

def check_building(b: BuildingInput, li, settings: DesignSettings, progress=lambda s: None, workers=None) -> dict:
    from .cfs_checks import cfs_checks
    from .secondary_checks import secondary_checks
    from .sizing import evaluate, explicit
    settings.check()
    limits = ServiceLimits.from_dict(settings.limits)
    b, _ = resolve(b)
    out = peb_building(b)
    z = explicit(b.sizes)
    rows, calc, frames, service = [], {}, {}, []
    for code in settings.codes:
        progress(f"Main frames, {code}: analysing every distinct frame line…")
        ev = evaluate(b, li, z, code=code, stability=settings.stability, limits=limits, workers=workers)
        r, c = frame_rows(ev, code)
        rows += r
        calc.update(c)
        frames[code] = {"max_ratio": _ratio(ev["max_ratio"]), "service_ratio": _ratio(ev["service_ratio"]),
                        "lines": [{"lines": l["lines"], "ratio": _ratio(l["ratio"]), "service": l["service"]} for l in ev["lines"]]}
        if code == settings.governing or len(settings.codes) == 1:
            service = [{"lines": l["lines"], **{k: l["service"][k] for k in ("checks", "max_ratio")}} for l in ev["lines"]]
    progress("Wind columns, end rafters, bracing, purlins, girts, eave struts…")
    sc = secondary_checks(b, li, limits=limits, uplift_method=settings.uplift_method)
    strict = cfs_checks(b, li, limits=limits, out=out, uplift_method="strict") if settings.uplift_method == "r_factor" else None
    r, c = secondary_rows(sc, strict, out)
    rows += r
    calc.update(c)
    # the governing ratio per member: main frames by the governing code; the rest by their only code
    gov = {}
    for row in rows:
        if row["code"] in ("AISC", "ECP") and row["kind"] in ("column", "rafter"):
            if row["code"] == settings.governing:
                gov[row["id"]] = row
        else:
            gov[row["id"]] = row
    by_type = {}
    for row in gov.values():
        t = row["kind"]
        cur = by_type.get(t)
        if row["ratio"] is None:
            by_type[t] = {**(cur or {}), "not_evaluated": (cur or {}).get("not_evaluated", 0) + 1, "max_ratio": (cur or {}).get("max_ratio")}
        elif cur is None or cur.get("max_ratio") is None or row["ratio"] > cur["max_ratio"]:
            by_type[t] = {**(cur or {}), "max_ratio": row["ratio"], "id": row["id"], "governing": row["governing"]}
    unverified = sorted({f for row in rows for f in row["flags"]})
    summary = {"weight": building_weight(out), "max_by_type": by_type, "frames": frames, "service": service,
               "not_evaluated": sum(1 for r in gov.values() if r["not_evaluated"]), "unverified_items": unverified,
               "unverified_rows": sum(1 for r in gov.values() if not r["verified"]),
               "max_ratio": max((r["ratio"] for r in gov.values() if r["ratio"] is not None), default=None)}
    return clean({"banner": BANNER, "settings": dataclasses.asdict(settings), "rows": rows, "governing_ids": sorted(gov),
                  "summary": summary, "calc": calc, "designed": False})


def size_building(b: BuildingInput, li, settings: DesignSettings, progress=lambda s: None, workers=None) -> dict:
    from .sizing import size_cold_formed, size_frames
    settings.check()
    limits = ServiceLimits.from_dict(settings.limits)
    b, _ = resolve(b)
    before = building_weight(peb_building(b))
    progress(f"Sizing the main frames ({settings.governing}): analyse, size on held forces, re-analyse until stable…")
    fr = size_frames(b, li, code=settings.governing, stability=settings.stability, target=settings.target, limits=limits, workers=workers)
    from ..peb.builtup_frame import BuiltUpSizes
    z = BuiltUpSizes(**fr["sizes"])
    b1 = dataclasses.replace(b, sizes=z)
    progress("Sizing purlins, eave struts and girts (R-factor, strict beside)…")
    cf = size_cold_formed(b1, li, uplift_method=settings.uplift_method, target=settings.target, limits=limits)
    from ..peb.secondary import Sections
    b2 = dataclasses.replace(b1, sections=Sections(**cf["sections"]))
    progress("Sizing wind columns and end rafters on their held forces…")
    ew = size_end_walls(b2, li, settings.target)
    b3 = dataclasses.replace(b2, wind_column=ew["wind_column"]["to"] if "wind_column" in ew else b2.wind_column,
                             end_rafter=ew["end_rafter"]["to"] if "end_rafter" in ew else b2.end_rafter)
    progress("Checking the proposed building fully…")
    chk = check_building(b3, li, settings, progress, workers)
    proposed = {"sizes": fr["sizes"], "sections": cf["sections"], "wind_column": b3.wind_column, "end_rafter": b3.end_rafter}
    return clean({**chk, "action": "size", "proposed": proposed, "weight_before": before, "weight_after": chk["summary"]["weight"],
                  "sizing": {"frames": {k: fr[k] for k in ("max_ratio", "service_ratio", "kg_per_frame", "converged", "passed", "rounds")},
                             "cold_formed": cf["roles"], "end_walls": ew, "cold_formed_banner": cf["banner"]}})
