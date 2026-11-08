# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 3: main-frame member checks, AISC 360-16 LRFD, through bimsteelauto's check_member.

One design member = a column, or a rafter HALF chained from the knee to the ridge across its splices (step 1). For each:
    forces     the strength (DAM) solve's LRFD combinations, every station of every analysis member of the chain, at
               its distance along the chain; M + = the member's top/outer flange in compression (bimsteelauto 0.14.1)
    section    the section AT the station (ChainTaper: the chain's own tapered pieces)
    Lb         from the model's restraints (step 1): outer flange at purlins / girts, inner flange at flange braces;
               the ends of the design member are braces; splices are NOT
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

from bimsteelauto.design import BracingSpec, MemberDesignInput, check_member
from bimsteelauto.design import nonprismatic
from bimsteelauto.design.members import VERIFIED as AISC_VERIFIED
from bimsteelauto.spec import DesignMethod, Materials, MemberForces, MemberType

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


def _check_row(c) -> dict:
    return {"name": c.name, "reference": c.reference, "demand": round(c.demand, 3), "capacity": round(c.capacity, 3),
            "ratio": round(c.ratio, 4), "unit": c.unit, "note": c.note}


def check_frame_line(info, result: dict, out: dict, x_frame: float, strengths: dict, *, stability: str = "dg25",
                     compare: bool = True) -> dict:
    """AISC 360-16 LRFD checks of every design member of one frame line (from its analysis result)."""
    members = []
    for dm, inp, notes in design_inputs(info, result, out, x_frame, strengths, stability=stability):
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
    open_flags = sorted([f"design.members.{k}" for k, v in AISC_VERIFIED.items() if not v]
                        + ([f"design.nonprismatic.{k}" for k, v in nonprismatic.VERIFIED.items() if not v] if stability == "dg25" else [])
                        + [f"engine.design.inputs.{k}" for k, v in INPUTS_VERIFIED.items() if not v])
    return {"banner": BANNER, "code": "AISC 360-16 LRFD", "stability": stability, "members": members,
            "max_ratio": max(m["ratio"] for m in members), "open_flags": open_flags, "designed": False}
