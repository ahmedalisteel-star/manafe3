# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 17: the web at the bottom-flange KINK of the apex haunch. NOT FOR ISSUE. SI: mm, kN, MPa.

User decision 2026-11-24 (D5): check the web at the kink for the kink force, both signs — AISC 360-16 J10.2 web local
yielding (tension or compression), J10.3 web local crippling where the force is compressive; a stiffener pair ONLY
if a check fails (reported, not designed here). Also report the distance from the kink to the nearest flange brace on
each rafter (no rule: the user decides later).

Where: the apex segment is shop-welded to the rafter piece (segment joint "shop", builtup_frame.py); the top flange is
straight, the bottom flange turns by θ = atan((hw_apex − hw_rafter) / apex_haunch_length) at the joint (the frame
model's node R<side>S<k>, a station of both analysis members).

Force (per LRFD combination of the DAM strength solve, the stations of both members at the node):
    bottom flange force C (compression +) = −M / ho + P × A_bot / A      (M + = top flange in compression; P + = compression;
                                                                          ho = d − (tf_top + tf_bot) / 2 at the kink)
    kink force R = 2 |C| sin(θ / 2), along the bisector of the two flange directions (≈ normal to the flange):
        C > 0 (compression): R pushes the flange INTO the web  → J10.2 and J10.3
        C < 0 (tension):     R pulls the flange off the web    → J10.2 only (crippling is a compression mode)
    The full resultant is applied as the concentrated force (its component along the web is R cos(θ / 2) — conservative).
Capacity (interior point: the kink is more than d from the member end — checked, else NOT EVALUATED):
    J10.2  φ = 1.00   Rn = Fyw tw (5k + lb)                          (J10-2)
    J10.3  φ = 0.75   Rn = 0.80 tw² [1 + 3 (lb / d)(tw / tf)^1.5] √(E Fyw tf / tw) Qf     (J10-4), Qf = 1.0
    Claude's conservative inputs (stated on every result): lb = 0 (a kink is a line across the flange, no bearing
    length); k = tf of the bottom flange (the flange-to-web fillet leg ignored); E = 200 000 MPa.
VERIFIED: J10-2 / J10-4 written from AISC 360-16 by Claude — not compared with the printed specification here
(VERIFIED["J10"] = False); the test checks the arithmetic longhand, which does not verify the clause.
"""

from __future__ import annotations

import math

from ..peb.building import BuildingInput, peb_building, resolve

BANNER = "NOT FOR ISSUE — apex-haunch kink (open item 17): AISC J10.2 / J10.3, Claude's conservative inputs, VERIFIED False"
VERIFIED = {"J10": False}
E = 200000.0
PHI_YIELD, PHI_CRIPPLE = 1.00, 0.75
ASSUMPTIONS = ("lb = 0 (a kink has no bearing length)", "k = tf of the bottom flange (fillet leg ignored)",
               "Qf = 1.0", "E = 200 000 MPa", "the full kink resultant 2|C| sin(θ/2) taken normal to the flange")
PASSES, FAILS, NOT_EVALUATED = "PASSES", "FAILS - STIFFENER PAIR REQUIRED (not designed)", "NOT EVALUATED"


def web_local_yielding(Fyw: float, tw: float, k: float, lb: float = 0.0) -> float:
    """J10-2 (interior), kN: φRn with φ = 1.00."""
    return PHI_YIELD * Fyw * tw * (5.0 * k + lb) / 1000.0


def web_crippling(Fyw: float, tw: float, tf: float, d: float, lb: float = 0.0, Qf: float = 1.0) -> float:
    """J10-4 (interior, ≥ d/2 from the end), kN: φRn with φ = 0.75."""
    return PHI_CRIPPLE * 0.80 * tw ** 2 * (1.0 + 3.0 * (lb / d) * (tw / tf) ** 1.5) * math.sqrt(E * Fyw * tf / tw) * Qf / 1000.0


def kink_force(C: float, theta: float) -> float:
    """kN: the resultant of the flange force C on both sides of a turn by θ (rad)."""
    return 2.0 * abs(C) * math.sin(theta / 2.0)


def flange_force(M: float, P: float, ho: float, A_bot: float, A: float) -> float:
    """Bottom flange force, kN, compression + (M kN·m, + = top flange in compression; P kN, + = compression; mm, mm²)."""
    return -M * 1000.0 / ho + P * A_bot / A


def _kinks(ms: list[dict], info) -> list[dict]:
    """The kink of each rafter of one frame line: geometry from the generator's segments, the node from the model."""
    out = []
    for m in ms:
        if m["role"] != "rafter":
            continue
        segs = m["section"]["segments"]
        for k in range(1, len(segs)):
            s = segs[k]
            if s.get("joint") != "shop" or s["hw_end"] == s["hw_start"]:
                continue
            node = f"R{m['side']}S{k}"
            if node not in info.shop:
                continue
            x_axis = sum(t["length"] for t in segs[:k])
            hw = s["hw_start"]
            A_bot = s["bf_bot"] * s["tf_bot"]
            A = s["bf_top"] * s["tf_top"] + A_bot + hw * s["tw"]
            out.append({"rafter": m["id"], "side": m["side"], "node": node, "marks": (f"R{m['side']}{k}", f"R{m['side']}{k + 1}"),
                        "x_along_rafter": round(x_axis, 3), "to_member_end": round(sum(t["length"] for t in segs[k:]), 3),
                        "theta_deg": math.degrees(math.atan((s["hw_end"] - s["hw_start"]) / s["length"])),
                        "hw": hw, "d": hw + s["tf_top"] + s["tf_bot"], "ho": hw + (s["tf_top"] + s["tf_bot"]) / 2.0,
                        "tw": s["tw"], "tf_bot": s["tf_bot"], "A_bot": A_bot, "A": A, "grade": s["grade"],
                        "start": m["start"], "end": m["end"]})
    return out


def check_kink(kk: dict, cands: list[dict], Fyw: float) -> dict:
    """One kink: cands = [{M, P, combo, member}] at the node (both members, every LRFD combination)."""
    th = math.radians(kk["theta_deg"])
    rows = []
    for c in cands:
        C = flange_force(c["M"], c["P"], kk["ho"], kk["A_bot"], kk["A"])
        rows.append({**c, "C": C, "R": kink_force(C, th)})
    comp = max((r for r in rows if r["C"] > 0), key=lambda r: r["R"], default=None)
    tens = max((r for r in rows if r["C"] < 0), key=lambda r: r["R"], default=None)
    y = web_local_yielding(Fyw, kk["tw"], kk["tf_bot"])
    cr = web_crippling(Fyw, kk["tw"], kk["tf_bot"], kk["d"])
    checks = []
    if comp:
        checks.append({"check": "J10.2 web local yielding (flange in compression)", "Ru": round(comp["R"], 3), "phiRn": round(y, 3),
                       "ratio": round(comp["R"] / y, 4), "C": round(comp["C"], 3), "combo": comp["combo"], "member": comp["member"]})
        checks.append({"check": "J10.3 web local crippling (flange in compression)", "Ru": round(comp["R"], 3), "phiRn": round(cr, 3),
                       "ratio": round(comp["R"] / cr, 4), "C": round(comp["C"], 3), "combo": comp["combo"], "member": comp["member"]})
    if tens:
        checks.append({"check": "J10.2 web local yielding (flange in tension)", "Ru": round(tens["R"], 3), "phiRn": round(y, 3),
                       "ratio": round(tens["R"] / y, 4), "C": round(tens["C"], 3), "combo": tens["combo"], "member": tens["member"]})
    gov = max(checks, key=lambda r: r["ratio"], default=None)
    return {"checks": checks, "governing": gov, "status": (PASSES if gov and gov["ratio"] <= 1.0 else FAILS) if gov else NOT_EVALUATED,
            "stiffener_pair": bool(gov and gov["ratio"] > 1.0)}


def nearest_flange_brace(kk: dict, out: dict, x_frame: float, slope: float) -> dict | None:
    """The nearest rafter flange brace (its bottom-flange end) to the kink on the same rafter, toward the ridge and toward
    the eave, measured along the rafter (plan distance × √(1 + slope²)). Reported only (user 2026-11-24: no rule yet)."""
    c = math.sqrt(1.0 + slope * slope)
    y0, y1 = kk["start"][1], kk["end"][1]
    yk = y0 + (y1 - y0) * kk["x_along_rafter"] / math.hypot(y1 - y0, kk["end"][2] - kk["start"][2])
    # the kink's BOTTOM-flange point (mid-thickness), square below the top line — where the flange braces end too
    yk += math.copysign(1.0, y1 - y0) * (kk["d"] - kk["tf_bot"] / 2.0) * slope / c
    host = f"rafter {kk['side']}"
    pts = [m for m in out["members"] if m["role"] == "flange_brace" and m.get("host") == host and abs(m["start"][0] - x_frame) < 1.0]
    if not pts:
        return None
    res = {}
    for toward, sgn in (("ridge", 1.0), ("eave", -1.0)):
        cand = [m for m in pts if (m["start"][1] - yk) * (y1 - y0) * sgn > 0]
        if not cand:
            res[toward] = None
            continue
        best = min(cand, key=lambda m: abs(m["start"][1] - yk))
        res[toward] = {"distance_along_rafter": round(abs(best["start"][1] - yk) * c, 1), "purlin_line": best.get("line"),
                       "brace_ids": sorted({m["id"] for m in cand if m["start"][1] == best["start"][1]})}
    near = min((v for v in res.values() if v), key=lambda v: v["distance_along_rafter"])
    return {"nearest": near["distance_along_rafter"], **res}


def building_kinks(b: BuildingInput, li=None, *, analysis: dict | None = None, out: dict | None = None) -> dict:
    """Every apex-haunch kink of the main frames: the J10 checks and the nearest flange brace. analysis = analyse_building."""
    from ..analysis.building_analysis import analyse_building
    from ..design.frame_checks import strengths_by_mark
    from .joints import TOL_STATION, _frame_info, _frame_lines, _station

    b, _ = resolve(b)
    out = out or peb_building(b)
    if not getattr(b.sizes, "apex", False):
        return {"banner": BANNER, "verified": dict(VERIFIED), "assumptions": list(ASSUMPTIONS), "kinks": [],
                "note": "no apex haunch (apex_haunch_length = 0)"}
    if analysis is None:
        analysis = analyse_building(b, li)
    by_line = {f["line"]: f for f in analysis.get("frames", [])}
    rows = []
    for i in _frame_lines(b):
        n = str(i + 1)
        f = by_line.get(n)
        res = None if f is None else (f.get("result") or by_line.get(f.get("same_as"), {}).get("result"))
        ms, info = _frame_info(b, i, base=analysis.get("input", {}).get("base", "pinned"))
        L = {m.mark: m.length for m in info.layout.members}
        stg = strengths_by_mark(ms)
        x = b.frame_xs()[i]
        for kk in _kinks(ms, info):
            row = {"id": f"F{n}-K{kk['side']}-APEX", "frame_line": n, **{k: kk[k] for k in ("rafter", "side", "node", "x_along_rafter", "hw", "d", "ho", "tw", "tf_bot", "grade")},
                   "theta_deg": round(kk["theta_deg"], 3), "flange_brace": nearest_flange_brace(kk, out, x, b.roof_slope)}
            if kk["to_member_end"] < kk["d"]:
                row.update(status=NOT_EVALUATED, missing=[f"the kink is {kk['to_member_end']:g} mm from the member end (< d): the J10 end cases are not built"])
                rows.append(row)
                continue
            lrfd = [] if res is None else [c for c, s in res.get("combos", []) if s == "LRFD"]
            a, bb = kk["marks"]
            cands, missing = [], []
            for c in lrfd:
                for mk, st in ((a, L[a]), (bb, 0.0)):
                    s = _station(res["results"][c]["members"].get(mk) or [], st)
                    if s is None:
                        missing.append(f"{mk}: no station within {TOL_STATION:g} mm of the kink ({c})")
                        continue
                    cands.append({"M": s[3], "P": s[1], "combo": c, "member": mk})
            if not lrfd or missing:
                row.update(status=NOT_EVALUATED, missing=sorted(set(missing))[:5] or ["no LRFD result for this frame line"])
                rows.append(row)
                continue
            Fyw = min(stg[a]["Fy"], stg[bb]["Fy"])
            row.update(Fyw=Fyw, **check_kink(kk, cands, Fyw))
            rows.append(row)
    return {"banner": BANNER, "verified": dict(VERIFIED), "assumptions": list(ASSUMPTIONS), "kinks": rows,
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in (PASSES, FAILS, NOT_EVALUATED)}}
