# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 6 (2026-11-15): longitudinal wind (wind parallel to the ridge) at the braced-bay bases. NOT FOR ISSUE.

The frame lines already carry ASCE 7-16 Load Case B (Fig. 28.3-1, the longitudinal case of the envelope procedure: WB+ /
WB−); the longitudinal bracing is driven by Load Case B end-wall zones 5 / 6, scaled up to the §28.3.4 minimum when that
governs (bimsteelauto longitudinal_endwall_pressure, Phase 3 step 6). What was missing is the PAIRING: a braced-bay base
takes the frame reaction AND the bottom of a tension diagonal (T cos α across, T sin α up) from the SAME combination.

The user's decisions (2026-11-15, HANDOVER open item 6):
    1a  no new frame cases: pair the bracing with the frame's existing WB combinations — only where the Ch. 28 envelope
        procedure applies: a low-rise building, h ≤ 18 m (60 ft) and h ≤ the least plan dimension (ASCE 7-16 §26.2 /
        §28.1.2, from memory — TO CONFIRM); otherwise the pairing is NOT EVALUATED. The limits are printed.
    2a  every LRFD combination with WB±: the brace force of Case B ALONE × that combination's wind factor (1.0 / 0.5), with
        the frame reaction (Ry, and Rx as the strong-axis shear) of the same combination; WB+ and WB− share the brace force
        (internal pressure cancels across the two end walls)
    3a  the §28.3.4 minimum as its own family: 0.9D + 1.0 W_min and 1.2D + 1.0 W_min — the minimum brace force with the
        frame's DEAD-LOAD reaction only (the minimum is a horizontal pressure on the end walls: no roof uplift on a frame);
        never paired with a WB uplift
    4a  connections now (base plate, anchors, base weld); the braced-bay columns and the eave struts under the brace axial
        forces are NOT EVALUATED (HANDOVER open item 7, before step 7)
    6a  the torsional load cases of Fig. 28.3-1 are not covered; the exception used (from memory — TO CONFIRM): one-story
        buildings with h ≤ 30 ft (9.1 m), or buildings designed with flexible diaphragms, need not be designed for them —
        checked per building; not met → torsion NOT EVALUATED (and a braced-bay base never reads DESIGNED)
    7a  a braced-bay base is DESIGNED only when every paired combination is evaluated and passes; otherwise PARTIAL with
        the reason
Brace force split: bracing["sets"]["LRFD"]["wall_diagonal"] is the governing one (k × Case B, k = minimum_scale); Case B
alone = T / k; the minimum alone = T / k × minimum_ratio (F_minimum / F_computed of the end-wall projection).
"""

from __future__ import annotations

import math

NOT_EVALUATED = "NOT EVALUATED"
H_LOW_RISE = 18000.0            # mm, 60 ft — ASCE 7-16 §26.2 "low-rise building" (TO CONFIRM)
H_TORSION = 9144.0              # mm, 30 ft — ASCE 7-16 Fig. 28.3-1 torsional-case exception (TO CONFIRM; user wrote 9 m)
VERIFIED = {"low_rise_limits": False, "torsion_exception": False, "pairing_rule": False}
LIMITS_CLAUSE = ("ASCE 7-16 §26.2 low-rise building / §28.1.2 envelope procedure: mean roof height h <= 60 ft (18 m) and "
                 "h <= the least horizontal dimension (from memory - TO CONFIRM)")
TORSION_CLAUSE = ("ASCE 7-16 Fig. 28.3-1 note (from memory - TO CONFIRM): one-story buildings with h <= 30 ft (9.1 m), "
                  "buildings two stories or less framed with light-frame construction, and buildings two stories or less "
                  "designed with flexible diaphragms need not be designed for the torsional load cases")
MIN_FAMILY = (("0.9D + 1.0W minimum (ASCE 7-16 §28.3.4), dead load only", 0.9),
              ("1.2D + 1.0W minimum (ASCE 7-16 §28.3.4), dead load only", 1.2))


def mean_roof_height(out: dict) -> float:
    """Gable: eave + (apex − eave) / 2, mm."""
    eave = float(out["input"]["eave_height"])
    apex = float(out.get("apex_height") or eave)
    return eave + (apex - eave) / 2.0


def low_rise_limits(out: dict) -> dict:
    inp = out["input"]
    h = mean_roof_height(out)
    length = float(sum(inp.get("bays") or [])) or float(inp["bay_spacing"]) * int(inp["n_bays"])
    least = min(float(inp["span"]), length)
    ok_h, ok_l = h <= H_LOW_RISE + 1e-9, h <= least + 1e-9
    return {"clause": LIMITS_CLAUSE, "h": round(h, 1), "h_max": H_LOW_RISE, "least_plan": round(least, 1),
            "h_ok": ok_h, "h_le_least_ok": ok_l, "ok": ok_h and ok_l, "verified": False}


def torsion_exception(out: dict, flexible_diaphragm: bool | None = None) -> dict:
    """PEB buildings here are one story; flexible_diaphragm = the user's statement (None = not stated)."""
    h = mean_roof_height(out)
    by_h = h <= H_TORSION + 1e-9
    exempt = by_h or bool(flexible_diaphragm)
    return {"clause": TORSION_CLAUSE, "one_story": True, "h": round(h, 1), "h_limit": H_TORSION,
            "one_story_h_ok": by_h, "flexible_diaphragm": flexible_diaphragm,
            "status": "EXEMPT" if exempt else NOT_EVALUATED,
            "why": ("one-story, h <= 30 ft" if by_h else "flexible diaphragm (stated)") if exempt else
                   (f"h = {h:.0f} mm > {H_TORSION:.0f} mm and no flexible diaphragm stated: the torsional load cases are "
                    "NOT EVALUATED"), "verified": False}


def brace_forces(bracing: dict) -> dict | None:
    """The wall-diagonal force (LRFD, 1.0 W) split into Case B alone and the §28.3.4 minimum alone."""
    s = (bracing or {}).get("sets", {}).get("LRFD", {})
    T, k, r = s.get("wall_diagonal"), bracing.get("minimum_scale"), bracing.get("minimum_ratio")
    if T is None or k is None or r is None:
        return None
    TB = T / k
    return {"T_governing": T, "minimum_scale": k, "minimum_ratio": r, "T_caseB": round(TB, 4), "T_minimum": round(TB * r, 4),
            "minimum_governs": bool(r > 1.0 + 1e-9)}


def _frame_result(an: dict, x: float):
    by_line = {f["line"]: f for f in an.get("frames", [])}
    for f in an.get("frames", []):
        if abs(f["x"] - x) < 1.0:
            src = by_line.get(f.get("same_as") or f["line"], f)
            return src.get("result")
    return None


def wind_factor(factors: dict) -> float | None:
    """The WB± factor of one combination (None: the combination has no Load Case B)."""
    for k in ("WB+", "WB-"):
        if k in factors:
            return float(factors[k])
    return None


def _br_direction(fres: dict, fac: dict) -> str | None:
    """Open item 7: the wind direction ("+x" / "-x") of a frame combination with a brace case, else None. Reads THIS
    line's own brace record (`own_brace`, put there by the caller): a line solved as "same_as" another may have its wind
    directions mirrored (the case roles BRA / BRB match, the directions need not)."""
    cases = (fres.get("own_brace") or fres.get("brace") or {}).get("cases", {})
    for k in fac:
        if k.startswith("BR") and k in cases:
            return cases[k]["direction"]
    return None


def paired_cases(fres: dict, node: str, forces: dict, cos_a: float, sin_a: float, direction: int | None = None) -> list[dict]:
    """Every LRFD combination with WB± (Case B brace force × its wind factor) + the minimum family (dead load only).
    Open item 7: a frame combination that carries the brace loads (BRA / BRB, BRminA / BRminB: the top-end column's ΔP and
    the roof-X chord forces, in ONE wind direction) is paired with −T sin α only when THIS base's diagonal is the tension
    one in that direction (`direction` = +1: tension for wind along +x); otherwise its frame reaction stands alone
    (it is in the frame reactions the base plates read). The frame-alone combinations stay paired as before."""
    out = []
    for name, r in fres["results"].items():
        if r.get("set") != "LRFD":
            continue
        fac = fres.get("factors", {}).get(name, {})
        if node not in r.get("reactions", {}):
            continue
        d = _br_direction(fres, fac)
        if d is not None:
            if direction is None or (1 if d == "+x" else -1) != direction:
                continue
            fam = "minimum" if any(k.startswith("BRmin") for k in fac) else "Case B"
            f = 1.0 if fam == "minimum" else wind_factor(fac)
            T = forces["T_minimum"] if fam == "minimum" else forces["T_caseB"] * f
            Rx, Ry = float(r["reactions"][node][0]), float(r["reactions"][node][1])
            out.append({"name": f"{fam} + its brace force, frame with the brace loads ({d})", "combo": name, "family": fam,
                        "wind_factor": f, "T_brace": round(T, 3), "Ry_frame": round(Ry, 3), "Pu": round(Ry - T * sin_a, 3),
                        "V_strong": round(abs(Rx), 3), "V_weak": round(T * cos_a, 3), "direction": d})
            continue
        f = wind_factor(fac)
        if f is None:
            continue
        Rx, Ry = float(r["reactions"][node][0]), float(r["reactions"][node][1])
        T = forces["T_caseB"] * f
        out.append({"name": "Case B + its brace force (same combination)", "combo": name, "family": "Case B",
                    "wind_factor": f, "T_brace": round(T, 3), "Ry_frame": round(Ry, 3), "Pu": round(Ry - T * sin_a, 3),
                    "V_strong": round(abs(Rx), 3), "V_weak": round(T * cos_a, 3)})
    D = fres["results"].get("D", {}).get("reactions", {}).get(node)
    if D is not None:
        for name, fd in MIN_FAMILY:
            T = forces["T_minimum"]
            Rx, Ry = fd * float(D[0]), fd * float(D[1])
            out.append({"name": name, "combo": name, "family": "minimum", "wind_factor": 1.0, "T_brace": round(T, 3),
                        "Ry_frame": round(Ry, 3), "Pu": round(Ry - T * sin_a, 3), "V_strong": round(abs(Rx), 3),
                        "V_weak": round(T * cos_a, 3)})
    return out


def landing_brace(j: dict, col: dict, out: dict) -> dict | None:
    """The wall brace whose lower end is at this frame base (same side, same frame line x)."""
    bx = j["point"][0]
    for o in out["members"]:
        if o.get("role") != "wall_brace" or o.get("side") != col.get("side"):
            continue
        lo, hi = (o["start"], o["end"]) if o["start"][2] < o["end"][2] else (o["end"], o["start"])
        if abs(lo[2]) < 1.0 and abs(lo[0] - bx) < 1.0:
            L = math.dist(lo, hi)
            return {"id": o.get("id"), "cos_a": abs(hi[0] - lo[0]) / L, "sin_a": abs(hi[2] - lo[2]) / L, "length": round(L, 1),
                    "direction": 1 if hi[0] > lo[0] else -1}
    return None


def braced_base(j: dict, col: dict, out: dict, analysis: dict, flexible_diaphragm: bool | None = None) -> dict | None:
    """The longitudinal record of one frame base: None when no wall brace lands there."""
    if j["type"] != "base":
        return None
    br = landing_brace(j, col, out)
    if br is None:
        return None
    rec = {"brace": br["id"], "cos_a": round(br["cos_a"], 5), "sin_a": round(br["sin_a"], 5), "cases": [],
           "limits": low_rise_limits(out), "torsion": torsion_exception(out, flexible_diaphragm)}
    forces = brace_forces(analysis.get("bracing", {}))
    rec["brace_forces"] = forces
    why = []
    if not rec["limits"]["ok"]:
        why.append("the Ch. 28 envelope limits are not met (h <= 18 m and h <= the least plan dimension): the longitudinal "
                   "pairing is NOT EVALUATED")
    if forces is None:
        why.append("the bracing result has no Case B / minimum split (re-run the analysis)")
    fres = _frame_result(analysis, j["point"][0])
    own = next((f.get("brace") for f in analysis.get("frames", []) if abs(f["x"] - j["point"][0]) < 1.0), None)
    if fres is not None and own is not None:
        fres = {**fres, "own_brace": own}
    if fres is None:
        why.append("no frame-line analysis for this base")
    if not why:
        node = "BA" if col.get("side") == "A" else "BB"
        rec["cases"] = paired_cases(fres, node, forces, br["cos_a"], br["sin_a"], br["direction"])
        if not any(c["family"] == "Case B" for c in rec["cases"]):
            why.append("the frame line has no Load Case B combination")
    if rec["torsion"]["status"] != "EXEMPT":
        why.append(rec["torsion"]["why"])
    rec["status"] = "EVALUATED" if not why else NOT_EVALUATED
    if why:
        rec["why"] = "; ".join(why)
    return rec


def members_not_evaluated(out: dict) -> list[dict]:
    """Open item 7 (built 2026-11-17): what the brace axial forces load and the checks still do not include —
    with the setting `brace_axial` off, every braced-bay column and eave strut (as before); with it on, only an end-rafter
    wall's columns under a wall brace and its end rafter as a roof-X chord (no main frame on that line to load); the eave
    struts between two braced bays take the user's 1c rule (design/cfs_checks.py)."""
    rows = []
    on = out.get("input", {}).get("brace_axial", True)
    rafter_xs = set()
    for ew in out.get("end_walls", []):
        if ew.get("kind") == "rafter":
            rafter_xs.add(float(ew.get("x_frame", 0.0)))
    for o in out["members"]:
        if o.get("role") == "column" and any(abs(o["start"][0] - b["start"][0]) < 1.0 or abs(o["start"][0] - b["end"][0]) < 1.0
                                                             for b in out["members"] if b.get("role") == "wall_brace"
                                                             and b.get("side") == o.get("side")):
            if not on or any(abs(o["start"][0] - x) < 1.0 for x in rafter_xs):
                rows.append({"member": o["id"], "role": "braced-bay column", "check": "axial force from the wall bracing",
                             "status": f"{NOT_EVALUATED} (HANDOVER open item 7" + ("" if not on else ": end-rafter wall column") + ")"})
        elif on and o.get("role") == "end_rafter" and any(abs(o["start"][0] - x) < 1.0 for x in rafter_xs) and any(
                b.get("role") == "roof_brace" and any(abs(p[0] - o["start"][0]) < 1.0 for p in (b["start"], b["end"]))
                for b in out["members"]):
            rows.append({"member": o["id"], "role": "end rafter (roof-X chord)", "check": "chord axial force from the roof bracing",
                         "status": f"{NOT_EVALUATED} (HANDOVER open item 7: end-rafter wall, no main frame on that line)"})
        elif o.get("role") == "eave_strut":
            if not on:
                rows.append({"member": o.get("id"), "role": "eave strut", "check": "strut force from the bracing",
                             "status": f"{NOT_EVALUATED} (HANDOVER open item 7)"})
    return rows


def building_record(out: dict, analysis: dict, flexible_diaphragm: bool | None = None) -> dict:
    return {"limits": low_rise_limits(out), "torsion": torsion_exception(out, flexible_diaphragm),
            "brace_forces": brace_forces(analysis.get("bracing", {})), "members_not_evaluated": members_not_evaluated(out),
            "verified": dict(VERIFIED)}
