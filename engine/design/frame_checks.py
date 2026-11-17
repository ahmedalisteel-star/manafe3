# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 4 step 3: main-frame member checks, AISC 360-16 LRFD, through bimsteelauto's check_member.

One design member = a column, or a rafter HALF chained from the knee to the ridge across its splices (step 1). For each:
    forces     the strength (DAM) solve's LRFD combinations, every station of every analysis member of the chain, at
               its distance along the chain; M + = the member's top/outer flange in compression (bimsteelauto 0.14.1)
    section    the section AT the station (ChainTaper: the chain's own tapered pieces)
    Lb         from the model's restraints (step 1): outer flange at purlins / girts, inner flange at flange braces;
               the ends of the design member are braces; splices are NOT. THE RIDGE IS NOT AN INNER-FLANGE BRACE (user
               2026-11-16, open item 11: a member end braces the inner flange only where a support or a modelled flange
               brace exists): the two rafter halves are ALSO checked as one member across the ridge (rafter B read from its
               ridge end), the inner flange continuous between the last flange braces of the two halves; each half takes
               the larger ratio (ridge_member / "across_ridge"). check_member braces a design member's ends, so this is how
               the ridge is left unbraced. DECISIONS (user 2026-11-16): flange braces at the ridge purlin on both sides
               (or within 150 mm of the ridge) brace the ridge → the half-rafter checks stand; with no ridge brace the
               combined member gives the inner-flange FLEXURE only (P = 0), combined by H1 with the half's own axial term
               — never its in-plane buckling. The KNEE braces the inner flange only with flange braces within 1500 mm of
               the corner on the rafter AND the column (KNEE_TOL, engineering judgement, VERIFIED False); otherwise the
               inner-flange LTB at the knee is NOT EVALUATED (ratio inf) — a corner-continuous segment is not modelled.
    strength   Fy / Fu = the lowest over every plate of every piece of the design member (conservative, stated)
    K          1.0 in plane — the Direct Analysis Method (step 2)
    checks     bimsteelauto 0.15.0: E3 / E4 with E7 on the actual plates; F2 / F3 / F4 / F5 by class; G2.1 without
               tension field action; D2; H1
    stability  "dg25" (default, the user's addition A): compression and LTB from the member's own elastic buckling
               loads — bimsteelauto design.nonprismatic, NOT VERIFIED until confirmed against the printed DG 25.
               The station-wise prismatic check is reported alongside ("prismatic_ratio") for comparison.

Every result carries the NOT FOR ISSUE banner and the list of open VERIFIED flags it depends on.
"""

from __future__ import annotations

import dataclasses
import math

from bimsteelauto.design import BracingSpec, MemberDesignInput, check_member
from bimsteelauto.design import nonprismatic
from bimsteelauto.design.members import VERIFIED as AISC_VERIFIED
from bimsteelauto.spec import DesignMethod, Materials, MemberForces, MemberType  # noqa: F401 (MemberForces: ridge_member)

from engine.design.inputs import GRADES, VERIFIED as INPUTS_VERIFIED, design_members, restraints, section_strength

BANNER = "NOT FOR ISSUE — member checks with open verification flags (DG 25 application unconfirmed)"
EPS = 0.01          # mm: stations at a splice are nudged into their own piece, so each takes its own section


class ChainTaper:
    """A design member's pieces as one 'taper' for check_member: .length, .at(s), .mark, .weight."""

    def __init__(self, mark: str, pieces: list[tuple[float, object]]):
        self.mark = mark
        self.pieces = pieces                                   # [(s0, TaperedMember)], in chain order
        self.length = pieces[-1][0] + pieces[-1][1].length
        self.weight = sum(t.weight for _, t in pieces)

    def at(self, s: float):
        for s0, t in self.pieces:
            if s < s0 + t.length:
                return t.at(min(max(s - s0, 0.0), t.length))
        s0, t = self.pieces[-1]
        return t.at(t.length)


def strengths_by_mark(ms: list[dict]) -> dict:
    """{analysis mark: section_strength} for the frame line's built-up members (CA, CB, RA1, RA2, …)."""
    out = {}
    for m in ms:
        segs = m["section"]["segments"]
        if m["role"] == "column":
            out["C" + m["side"]] = section_strength(segs[0])
        else:
            for k, s in enumerate(segs):
                out[f"R{m['side']}{k + 1}"] = section_strength(s)
    return out


def _materials(fy: float, fu: float) -> Materials:
    cf = GRADES["S350GD"][0]
    # bolts, anchors and concrete are not used by the member checks; stated as such rather than given a value
    return Materials(Fy_builtup=fy, Fu_builtup=fu, Fy_cold_formed=cf[1], Fu_cold_formed=cf[2],
                     bolt_grade="not used by the member check", anchor_grade="not used by the member check",
                     fc_concrete=float("nan"))


def design_inputs(info, result: dict, out: dict, x_frame: float, strengths: dict, *, stability: str = "dg25") -> list[tuple[dict, MemberDesignInput, dict]]:
    """(design member, MemberDesignInput, notes) for each design member of the frame line."""
    rs = restraints(out, info, x_frame)
    lay = {m.mark: m for m in info.layout.members}
    lrfd = [c for c, s in result["combos"] if s == "LRFD"]
    if not lrfd:
        raise ValueError("no LRFD combinations in the analysis result: nothing to check")
    res = []
    for dm in design_members(info):
        pieces = [(c["s0"], lay[c["mark"]].taper) for c in dm["chain"]]
        taper = ChainTaper(dm["name"], pieces)
        forces = {}
        for combo in lrfd:
            sts = []
            for c in dm["chain"]:
                L = c["length"]
                for x, P, V, M in result["results"][combo]["members"][c["mark"]]:
                    s = c["s0"] + min(max(x, EPS), L - EPS)
                    sts.append(MemberForces(P=P, Vy=V, Mz=M, station=s))
            forces[combo] = sts
        st = [strengths[c["mark"]] for c in dm["chain"]]
        gov = min(st, key=lambda r: r["Fy"])
        inp = MemberDesignInput(
            mark=dm["id"], member_type=MemberType.COLUMN if dm["kind"] == "column" else MemberType.RAFTER,
            taper=taper, forces=forces,
            bracing=BracingSpec(top_flange=tuple(rs[dm["name"]]["top"]), bottom_flange=tuple(rs[dm["name"]]["bottom"])),
            materials=_materials(gov["Fy"], min(r["Fu"] for r in st)), method=DesignMethod.LRFD, K_in_plane=1.0,
            stability=stability)
        res.append((dm, inp, {"Fy": gov["Fy"], "Fy_from": gov["governed_by"], "restraints": rs[dm["name"]]}))
    return res


class _Reversed:
    """A tapered piece read from its j end (rafter B from the ridge back to the knee)."""

    def __init__(self, t):
        self.t, self.length, self.weight, self.mark = t, t.length, t.weight, getattr(t, "mark", "reversed")

    def at(self, s: float):
        return self.t.at(self.t.length - s)


def ridge_member(iA: MemberDesignInput, nA: dict, iB: MemberDesignInput, nB: dict) -> MemberDesignInput:
    """Rafter A then rafter B reversed as ONE design member (knee A → ridge → knee B): its ends are the two knees, so the
    ridge is an interior station and NOT a brace; the purlins (top) and flange braces (bottom) of both halves."""
    LA, LB = iA.taper.length, iB.taper.length
    pieces = list(iA.taper.pieces) + [(LA + (LB - (s0 + t.length)), _Reversed(t)) for s0, t in reversed(iB.taper.pieces)]
    forces = {c: sorted(list(iA.forces[c]) + [MemberForces(P=x.P, Vy=-x.Vy, Mz=x.Mz, station=LA + (LB - x.station))
                                              for x in iB.forces[c]], key=lambda x: x.station) for c in iA.forces}
    top = tuple(sorted(set(nA["restraints"]["top"]) | {LA + LB - v for v in nB["restraints"]["top"]}))
    bot = tuple(sorted(set(nA["restraints"]["bottom"]) | {LA + LB - v for v in nB["restraints"]["bottom"]}))
    return dataclasses.replace(iA, mark=f"{iA.mark}+{iB.mark}", taper=ChainTaper(f"{iA.mark}+{iB.mark}", pieces), forces=forces,
                               bracing=BracingSpec(top_flange=top, bottom_flange=bot),
                               materials=iA.materials if nA["Fy"] <= nB["Fy"] else iB.materials)


KNEE_TOL = 1500.0         # mm: the knee braces the inner flange only with flange braces this close to the corner on BOTH
                          # the rafter (its first purlin) and the column (its first girt) — user 2026-11-16, VERIFIED False
RIDGE_MERGE_TOL = 150.0   # mm: a flange brace this close to the ridge braces it (step 5c merge distance)


def knee_braced(rafter, column, tol: float = KNEE_TOL) -> dict:
    """The knee as an inner-flange brace (engineering judgement, user 2026-11-16): only when the rafter has a flange brace
    within tol of its knee end AND the column within tol of its top."""
    if rafter is None or column is None:
        return {"braced": True, "rule": "no knee on this line"}
    rb = [p for p in rafter[1]["restraints"]["bottom"] if p <= tol]
    Lc = column[0].taper.length
    cb = [p for p in column[1]["restraints"]["bottom"] if Lc - p <= tol]
    return {"braced": bool(rb and cb), "rafter_brace": min(rb) if rb else None,
            "column_brace_below_top": round(Lc - max(cb), 1) if cb else None, "tol": tol}


def ridge_braced(out: dict, x_frame: float, side: str, rafter, tol: float = RIDGE_MERGE_TOL) -> dict:
    """Is the ridge an inner-flange brace for rafter `side`: a modelled flange brace at its ridge purlin, or one within tol
    of the ridge end."""
    ridge_lines = {m["line"] for m in out["members"] if m.get("role") == "ridge_purlin" and m.get("side") == side}
    at_rp = any(m["role"] == "flange_brace" and m.get("host") == f"rafter {side}" and abs(m["start"][0] - x_frame) < 1.0
                and (m.get("line") in ridge_lines or str(m.get("line", "")).split("-")[0] in ridge_lines) for m in out["members"])
    L = rafter[0].taper.length
    near = [p for p in rafter[1]["restraints"]["bottom"] if L - p <= tol]
    return {"braced": at_rp or bool(near), "by": "flange brace at the ridge purlin" if at_rp else
            (f"flange brace {L - max(near):.1f} mm from the ridge" if near else None)}


def _axial_ratio(d) -> float:
    return max((c.ratio for c in d.checks if c.name.startswith(("Compression", "Tension"))), default=0.0)


def _flexure_ratio(d) -> float:
    return max((c.ratio for c in d.checks if c.name.startswith("Flexure")), default=0.0)


def across_ridge_ltb(A: tuple, B: tuple) -> dict:
    """No ridge brace (user 2026-11-16): the two halves as ONE member across the ridge for the inner-flange FLEXURE only —
    every combination with P = 0 (so the combined member is never used for in-plane buckling) — combined by H1 with the
    HALF rafter's own axial term of the same combination: Pr/Pc ≥ 0.2 → a + 8/9 f, else a/2 + f (a = the larger half's
    axial ratio, f = the combined flexure ratio; their stations may differ: conservative)."""
    rm = ridge_member(*A, *B)
    best = None
    for c, sts in rm.forces.items():
        f = _flexure_ratio(check_member(dataclasses.replace(
            rm, forces={c: [MemberForces(P=0.0, Vy=x.Vy, Mz=x.Mz, station=x.station) for x in sts]})))
        a = max(_axial_ratio(check_member(dataclasses.replace(X[0], forces={c: X[0].forces[c]}))) for X in (A, B))
        u = a + 8.0 / 9.0 * f if a >= 0.2 else a / 2.0 + f
        if best is None or u > best["ratio"]:
            best = {"ratio": round(u, 4), "combo": c, "flexure_across": round(f, 4), "axial_half": round(a, 4)}
    bot = rm.bracing.bottom_flange
    LA = A[0].taper.length
    seg = next(((p, q) for p, q in zip((0.0,) + bot, bot + (rm.taper.length,)) if p < LA < q), None)
    return {**best, "inner_flange_segment_across_ridge": None if seg is None else [round(seg[0], 1), round(seg[1], 1)],
            "rule": "no ridge brace: inner-flange LTB across the ridge (P = 0) + the half's axial term by H1 (open item 11)"}


def _check_row(c) -> dict:
    return {"name": c.name, "reference": c.reference, "demand": round(c.demand, 3), "capacity": round(c.capacity, 3),
            "ratio": round(c.ratio, 4), "unit": c.unit, "note": c.note}


def check_frame_line(info, result: dict, out: dict, x_frame: float, strengths: dict, *, stability: str = "dg25",
                     compare: bool = True, knee_tol: float = KNEE_TOL, merge_tol: float = RIDGE_MERGE_TOL) -> dict:
    """AISC 360-16 LRFD checks of every design member of one frame line (from its analysis result)."""
    members = []
    ins = {}
    for dm, inp, notes in design_inputs(info, result, out, x_frame, strengths, stability=stability):
        ins[dm["name"]] = (inp, notes)
        d = check_member(inp)
        row = {"name": dm["name"], "id": dm["id"], "length": round(inp.taper.length, 1), "Fy": notes["Fy"],
               "Fy_from": notes["Fy_from"], "combo": d.governing_combination, "x": round(d.forces.station, 1),
               "section": d.note, "ratio": round(d.utilisation, 4), "passed": d.passed,
               "governing": d.governing_check.name if d.governing_check else None,
               "checks": [_check_row(c) for c in d.checks],
               "forces": {"P": d.forces.P, "V": d.forces.Vy, "M": d.forces.Mz},
               "Lb_points": {"top": notes["restraints"]["top"], "bottom": notes["restraints"]["bottom"]}}
        if compare and stability != "prismatic":
            p = check_member(dataclasses.replace(inp, stability="prismatic"))
            row["prismatic_ratio"] = round(p.utilisation, 4)
            row["prismatic_governing"] = p.governing_check.name if p.governing_check else None
        members.append(row)
    # open item 11 (user 2026-11-16): the ridge and the knee brace the inner flange only where flange braces are modelled
    for side in "AB":
        knee = knee_braced(ins.get(f"rafter {side}"), ins.get(f"column {side}"), knee_tol)
        for row in members:
            if row["name"] in (f"rafter {side}", f"column {side}"):
                row["knee"] = knee
                if not knee["braced"]:
                    row.update(ratio=math.inf, passed=False, status="NOT EVALUATED",   # JSON / UI: None → "NOT EVALUATED"
                               governing="inner-flange LTB at the knee NOT EVALUATED (no flange brace within "
                                         f"{knee_tol:g} mm of the corner on the rafter and the column)")
    if "rafter A" in ins and "rafter B" in ins:
        rb = {sd: ridge_braced(out, x_frame, sd, ins[f"rafter {sd}"], merge_tol) for sd in "AB"}
        if all(v["braced"] for v in rb.values()):
            across = {"ridge_braced": True, "by": {sd: v["by"] for sd, v in rb.items()},
                      "rule": "flange braces at the ridge purlin both sides (or within the merge distance): the half-rafter "
                              "checks stand (open item 11)"}
        else:
            across = {"ridge_braced": False, "by": {sd: v["by"] for sd, v in rb.items()},
                      **across_ridge_ltb(ins["rafter A"], ins["rafter B"])}
        for row in members:
            if row["name"] in ("rafter A", "rafter B"):
                row["across_ridge"] = across
                if not across["ridge_braced"] and across["ratio"] > row["ratio"]:
                    row.update(ratio=across["ratio"], passed=across["ratio"] <= 1.0, combo=across["combo"],
                               governing="across the ridge: inner-flange LTB + the half's axial term (H1)")
    open_flags = sorted([f"design.members.{k}" for k, v in AISC_VERIFIED.items() if not v]
                        + ([f"design.nonprismatic.{k}" for k, v in nonprismatic.VERIFIED.items() if not v] if stability == "dg25" else [])
                        + [f"engine.design.inputs.{k}" for k, v in INPUTS_VERIFIED.items() if not v])
    return {"banner": BANNER, "code": "AISC 360-16 LRFD", "stability": stability, "members": members,
            "max_ratio": max(m["ratio"] for m in members), "open_flags": open_flags, "designed": False}
