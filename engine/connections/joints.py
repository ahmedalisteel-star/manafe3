# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 1: every joint of a generated building, the members it joins, and its design forces. NOT FOR ISSUE.

Joints (from the MODEL — the generator's members, cleats and end walls):
    base              main-frame column base (frame lines whose end is a main frame)
    knee              column top + rafter start (the knee panel's rigid link between them)
    ridge             the two rafter ends at the apex
    rafter_splice     between two rafter segments (haunch end, transport splits)
    wind_column_top   wind column (incl. an end-rafter wall's corner columns) under the rafter / end rafter
    wind_column_base  its base
    end_rafter_ridge, end_rafter_splice   on an end-rafter wall
    brace_end         each end of a roof / side-wall / end-wall X-brace (rod or angle)
    cleat             each purlin / girt / eave-strut / gable-girt cleat on its frame member or wind column
Not joints here (stated): sag rods, ridge ties, flange braces (no analysed force — stability bracing).
The host of a brace end / cleat is the primary member (column, rafter, end rafter, wind column) whose line passes
nearest to it (the generator's cleat "host" labels are not used: on an end-rafter wall they still say "rafter").

Forces (LRFD, the strength solve = Direct Analysis Method, Phase 4 step 2):
    frame joints   every LRFD combination, the station AT the joint of every member end that meets there (a station
                   more than 1 mm from the joint does not count); per joint: the largest +M and the largest −M with their
                   V and P, the largest |V|, the largest compression and the largest tension, each with its combination
                   and member. M + = the member's TOP / OUTER flange in compression (bimsteelauto 0.14.1); P + = compression.
    bases          the support reactions (what the support gives the frame): compression, uplift, |H|, |M| (fixed bases)
    wind columns   the forces their member check uses (secondary_checks.wind_column_inputs: C&C 1.0 W simple beam, 1.2 ×
                   self weight, + the end-rafter frame's column load); uplift at an end-rafter wall's column base from that
                   frame's reactions
    end rafters    the end-rafter frame's rafter stations at the ridge and at each splice (the frame has a node at every
                   end-rafter splice: endwall_analysis.end_rafter_splice_ys)
    braces         the tension-only diagonal force (longitudinal bracing; end walls: the end-rafter frame)
    cleats         NOT EVALUATED here — the cold-formed lines' support reactions and the cleat checks: engine/connections/cleats.py (step 5a)
Capacity rule. SOURCE: a project setting, not a code clause — user decision 2026-11-10 (Phase 5 plan); AISC 360-16 has no
general minimum connection strength as a fraction of the member's. Default fraction 0.50 = bimsteelauto_connections.
CAPACITY_FRACTION; editable per job (ConnectionSettings), applied through bimsteelauto_connections.design_force:
    ONLY at knee, ridge and rafter-splice joints (user decision 2026-11-11): Mu+ = max(analysis +M, f × φMn+) and Mu−
    likewise (switch capacity_moment); Vu = max(|V|, f × φVn) (switch capacity_shear, separate). Axial forces, bases, wind
    columns, end rafters, braces: the analysis force alone.
    φMn, φVn = the SECTION strength (user decision 2026-11-11) of the shallower section at the joint (smaller Zx — the
    library's rule): yielding and local buckling, no LTB (Lb = 0), AISC 360-16 F2–F5 / G2.1 through bimsteelauto
    design.available_strengths; Fy = the lowest plate of that piece.
A joint whose forces are not available reads NOT EVALUATED with the missing items — never a value.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from bimsteelauto.design.members import available_strengths
from bimsteelauto.spec import DesignMethod
from bimsteelauto_connections import CAPACITY_FRACTION, CAPACITY_FRACTION_SOURCE, design_force

from ..analysis.frame_model import frame_line_model
from ..design.frame_checks import _materials, strengths_by_mark
from ..peb.building import BuildingInput, peb_building, resolve
from ..peb.builtup_frame import builtup_frame_members, default_sizes

BANNER = "NOT FOR ISSUE — connection joints and design forces (Phase 5 step 1); connections not designed"
SECTION_LB = 1.0             # mm: "Lb = 0" for the section strength (available_strengths needs a length > 0)
CAPACITY_BASIS = ("section strength of the shallower section at the joint (smaller Zx): yielding and local buckling, "
                  "no lateral-torsional buckling (Lb = 0); Fy = the lowest plate of that piece; AISC 360-16 Ch. F, G2.1")
#: Where the 50 % rule comes from — stated on every result.
CAPACITY_RULE_SOURCE = (
    "Project setting, not a code clause: user decision 2026-11-10 (Manafe3 Phase 5 plan) - a connection is designed for "
    "the larger of the analysis force and a fraction (default 0.50, editable per job) of the connected member's design "
    "strength. AISC 360-16 has no such general minimum. The default is bimsteelauto_connections.CAPACITY_FRACTION, whose "
    "own source reads: " + CAPACITY_FRACTION_SOURCE + ".")
TOL_STATION = 1.0           # mm: a station counts for a joint only this close to it
SEC_TOL = 50.0              # mm: an eave strut stops 5 mm short of the frame line (10 mm butt gap); its cleat still holds it
HOST_TOL = 1000.0            # mm: a brace end / cleat farther than this from every primary member has no host
PRIMARY = ("column", "rafter", "end_rafter", "wind_column")
END_PLATE_TYPES = ("knee", "ridge", "rafter_splice")
EVALUATED, NOT_EVALUATED = "EVALUATED", "NOT EVALUATED"


@dataclass
class ConnectionSettings:
    """Project connection settings (editable per job). capacity_fraction None = analysis forces alone; the rule applies to
    the moments (capacity_moment) and the shear (capacity_shear) of knee / ridge / rafter-splice joints, each switchable."""
    capacity_fraction: float | None = CAPACITY_FRACTION
    capacity_moment: bool = True
    capacity_shear: bool = True

    def check(self) -> "ConnectionSettings":
        f = self.capacity_fraction
        if f is not None and not (isinstance(f, (int, float)) and 0.0 < f <= 1.0):
            raise ValueError(f"capacity_fraction must be in (0, 1] or None, got {f!r}")
        for k in ("capacity_moment", "capacity_shear"):
            if not isinstance(getattr(self, k), bool):
                raise ValueError(f"{k} must be true or false, got {getattr(self, k)!r}")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "ConnectionSettings":
        d = dict(d or {})
        bad = set(d) - {"capacity_fraction", "capacity_moment", "capacity_shear"}
        if bad:
            raise ValueError(f"unknown connection settings: {', '.join(sorted(bad))}")
        return cls(**d).check()


# ----------------------------------------------------------------------------------------------------------- geometry

def _dist_point_segment(p, a, b) -> float:
    ab = [b[i] - a[i] for i in range(3)]
    L2 = sum(v * v for v in ab)
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, sum((p[i] - a[i]) * ab[i] for i in range(3)) / L2))
    return math.dist(p, [a[i] + t * ab[i] for i in range(3)])


def _host(p, out: dict) -> tuple[str | None, float]:
    best = (None, math.inf)
    for m in out["members"]:
        if m["role"] in PRIMARY:
            d = _dist_point_segment(p, m["start"], m["end"])
            if d < best[1]:
                best = (m["id"], d)
    return best if best[1] <= HOST_TOL else (None, best[1])


def _mref(m: dict, **kw) -> dict:
    return {"id": m.get("id"), "role": m["role"], "profile": m.get("profile"), **kw}


def _section(w) -> dict:
    return {"d": round(w.d, 3), "tw": w.tw, "bf_top": w.bf_top, "tf_top": w.tf_top, "bf_bot": w.bf_bot, "tf_bot": w.tf_bot,
            "Zx": round(w.Zx, 1)}


def _frame_lines(b: BuildingInput) -> list[int]:
    kinds = {0: b.end_first, b.n_bays: b.end_last}
    return [i for i in range(b.n_bays + 1) if kinds.get(i, "frame") == "frame"]


def _frame_info(b: BuildingInput, i: int, base: str = "pinned"):
    ms = builtup_frame_members(b.span, b.eave_height, b.roof_slope, b.frame_xs()[i], str(i + 1), b.sizes)
    return ms, frame_line_model(ms, b.span, b.eave_height, b.roof_slope, b.bay_list(), base=base)


def _frame_joints(b: BuildingInput, i: int, info) -> list[dict]:
    """The joints of frame line i: (id, type, point, [(analysis mark, station)])."""
    lay = info.layout
    L = {m.mark: m.length for m in lay.members}
    x = b.frame_xs()[i]
    n = str(i + 1)

    def pt(node):
        y, z = lay.nodes[node]
        return [x, round(y, 3), round(z, 3)]
    js = []
    for s in "AB":
        js.append({"id": f"F{n}-B{s}", "type": "base", "frame_line": n, "point": pt(f"B{s}"), "ends": [(f"C{s}", 0.0)], "node": f"B{s}"})
        js.append({"id": f"F{n}-K{s}", "type": "knee", "frame_line": n, "point": pt(f"K{s}"),
                   "ends": [(f"C{s}", L[f"C{s}"]), (f"R{s}1", 0.0)]})
    for s in "AB":
        k = 1
        while f"R{s}{k + 1}" in L:
            js.append({"id": f"F{n}-S{s}{k}", "type": "rafter_splice", "frame_line": n, "point": pt(f"R{s}S{k}"),
                       "ends": [(f"R{s}{k}", L[f"R{s}{k}"]), (f"R{s}{k + 1}", 0.0)]})
            k += 1
    last = {s: max(int(mk[2:]) for mk in L if mk.startswith(f"R{s}") and mk[2:].isdigit()) for s in "AB"}
    js.append({"id": f"F{n}-R", "type": "ridge", "frame_line": n, "point": pt("RIDGE"),
               "ends": [(f"RA{last['A']}", L[f"RA{last['A']}"]), (f"RB{last['B']}", L[f"RB{last['B']}"])]})
    by_id = {mk: info.marks[mk] for mk in L}
    for j in js:
        j["members"] = [{"id": by_id[mk], "mark": mk, "station": round(st, 1),
                         "role": "column" if mk.startswith("C") else "rafter"} for mk, st in j["ends"]]
        for mm, (_, st) in zip(j["members"], j["ends"]):
            mm["_s"] = st
    return js


def joint_list(b: BuildingInput, out: dict | None = None) -> list[dict]:
    """Every joint of the building from the model alone (no forces): id, type, point, members (with sections at frame joints)."""
    b, _ = resolve(b)
    out = out or peb_building(b)
    joints: list[dict] = []
    for i in _frame_lines(b):
        ms, info = _frame_info(b, i)
        tap = {m.mark: m.taper for m in info.layout.members}
        for j in _frame_joints(b, i, info):
            for mm in j["members"]:
                mm["section"] = _section(tap[mm["mark"]].at(mm.pop("_s")))
            j.pop("ends"); j.pop("node", None)
            joints.append(j)
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    # wind columns (and an end-rafter wall's corner columns)
    for m in out["members"]:
        if m["role"] != "wind_column":
            continue
        top_host = [h for h in (_host_excluding(m["end"], out, m["id"]),) if h[0]]
        joints.append({"id": f"{m['id']}-T", "type": "wind_column_top", "point": [round(v, 3) for v in m["end"]],
                       "members": [_mref(m, station="top")] + [_mref(mem[h[0]], station="at the column") for h in top_host]})
        joints.append({"id": f"{m['id']}-B", "type": "wind_column_base", "point": [round(v, 3) for v in m["start"]],
                       "members": [_mref(m, station="base")]})
    # end rafters: ridge and splices
    ers = [m for m in out["members"] if m["role"] == "end_rafter"]
    for wall in sorted({m["start"][0] for m in ers}):
        pair = [m for m in ers if m["start"][0] == wall]
        tag = pair[0]["id"][:2]                                   # EF / EL
        joints.append({"id": f"{tag}-R", "type": "end_rafter_ridge", "point": [round(v, 3) for v in pair[0]["end"]],
                       "members": [_mref(m, station="ridge") for m in pair]})
        for m in pair:
            segs = m["section"]["segments"]
            s0 = 0.0
            for k in range(len(segs) - 1):
                s0 += segs[k]["length"]
                joints.append({"id": f"{m['id']}-S{k + 1}", "type": "end_rafter_splice", "s": round(s0, 1),
                               "point": _along(m, s0), "members": [_mref(m, station=round(s0, 1))]})
    # X-brace ends
    for m in out["members"]:
        if m["role"] not in ("roof_brace", "wall_brace", "endwall_brace"):
            continue
        for end, p in (("a", m["start"]), ("b", m["end"])):
            h, d = _host(p, out)
            joints.append({"id": f"{m['id']}-{end}", "type": "brace_end", "point": [round(v, 3) for v in p],
                           "members": [_mref(m, end=end)] + ([_mref(mem[h], distance=round(d, 1))] if h else []),
                           **({} if h else {"notes": [f"no primary member within {HOST_TOL:g} mm"]})})
    # cleats
    for k, c in enumerate(out["cleats"]):
        h, d = _host(c["base"], out)
        sec = _cleat_secondaries(c, out)
        joints.append({"id": f"CL{k + 1}", "type": "cleat", "point": [round(v, 3) for v in c["base"]], "line": c["line"],
                       "cleat": c["profile"],
                       "members": [_mref(m) for m in sec] + ([_mref(mem[h], distance=round(d, 1))] if h else []),
                       **({} if h else {"notes": [f"no primary member within {HOST_TOL:g} mm"]})})
    return joints


def _host_excluding(p, out: dict, skip: str):
    best = (None, math.inf)
    for m in out["members"]:
        if m["role"] in ("rafter", "end_rafter") and m["id"] != skip:
            d = _dist_point_segment(p, m["start"], m["end"])
            if d < best[1]:
                best = (m["id"], d)
    return best if best[1] <= HOST_TOL else (None, best[1])


def _along(m: dict, s: float) -> list[float]:
    a, b = m["start"], m["end"]
    L = math.dist(a, b)
    return [round(a[i] + (b[i] - a[i]) * s / L, 3) for i in range(3)]


def _cleat_secondaries(c: dict, out: dict) -> list[dict]:
    """The purlin / girt / eave-strut / gable-girt pieces that sit on this cleat (two at a lap)."""
    p = c["base"]
    res = []
    for m in out["members"]:
        r = m["role"]
        if r in ("purlin", "ridge_purlin", "eave_strut", "girt") and m.get("line") == c["line"]:
            if min(m["start"][0], m["end"][0]) - SEC_TOL <= p[0] <= max(m["start"][0], m["end"][0]) + SEC_TOL:
                res.append(m)
        elif r == "gable_girt" and c["line"].startswith(m["id"][:2]):
            if (abs(m["start"][0] - p[0]) < 400 and abs(m.get("z", m["start"][2]) - p[2]) < 1.0
                    and min(m["start"][1], m["end"][1]) - 1 <= p[1] <= max(m["start"][1], m["end"][1]) + 1):
                res.append(m)
    return res


# ------------------------------------------------------------------------------------------------------------- forces

def _station(rows: list, target: float):
    if not rows:
        return None
    s = min(rows, key=lambda r: abs(r[0] - target))
    return s if abs(s[0] - target) <= TOL_STATION else None


def _pick(cands: list[dict], key, sign: float) -> dict:
    """The candidate with the largest sign × key; value 0 with combo None when no candidate has that sign."""
    best = max(cands, key=lambda c: sign * c[key], default=None)
    if best is None or sign * best[key] <= 0:
        return {"value": 0.0, "combo": None, "note": "does not occur under any LRFD combination"}
    return {"value": round(float(abs(best[key])), 3), **{k: best[k] for k in ("M", "V", "P", "combo", "member", "x")}}


def frame_joint_forces(joints: list[dict], result: dict) -> None:
    """Fills "forces" (or "missing") of the frame joints of ONE line from its analysis result (in place)."""
    lrfd = [c for c, s in result.get("combos", []) if s == "LRFD"]
    for j in joints:
        missing = []
        if not lrfd:
            missing.append("no LRFD combinations in the analysis result")
        if j["type"] == "base":
            node = j["node"]
            rs = [(c, result["results"][c]["reactions"].get(node)) for c in lrfd]
            if any(r is None for _, r in rs):
                missing.append(f"no reactions at {node}")
            if missing:
                j.update(forces=None, missing=missing)
                continue
            cands = [{"H": r[0], "Ry": r[1], "Mr": r[2], "combo": c} for c, r in rs]

            def best(key, sign):
                b_ = max(cands, key=lambda c: sign * c[key])
                if sign * b_[key] <= 0:
                    return {"value": 0.0, "combo": None, "note": "does not occur under any LRFD combination"}
                return {"value": round(float(abs(b_[key])), 3), "H": b_["H"], "V": b_["Ry"], "M": b_["Mr"], "combo": b_["combo"]}
            j["forces"] = {"compression": best("Ry", 1.0), "uplift": best("Ry", -1.0),
                           "shear": max((best("H", 1.0), best("H", -1.0)), key=lambda d: d["value"]),
                           "moment": max((best("Mr", 1.0), best("Mr", -1.0)), key=lambda d: d["value"]),
                           "source": "support reactions (on the frame), LRFD strength solve"}
            continue
        cands = []
        for mk, st in j["ends"]:
            for c in lrfd:
                rows = result["results"][c]["members"].get(mk)
                s = _station(rows or [], st)
                if s is None:
                    missing.append(f"{mk}: no station within {TOL_STATION:g} mm of the joint ({c})")
                    continue
                cands.append({"x": s[0], "P": s[1], "V": s[2], "M": s[3], "combo": c, "member": mk})
        if missing:
            j.update(forces=None, missing=sorted(set(missing))[:5])
            continue
        vmax = max(cands, key=lambda c: abs(c["V"]))
        j["forces"] = {"M_pos": _pick(cands, "M", 1.0), "M_neg": _pick(cands, "M", -1.0),
                       "V_max": {"value": round(float(abs(vmax["V"])), 3), **{k: vmax[k] for k in ("M", "V", "P", "combo", "member", "x")}},
                       "P_comp": _pick(cands, "P", 1.0), "P_tens": _pick(cands, "P", -1.0),
                       "source": "member-end stations at the joint, LRFD strength solve (DAM)"}


def frame_joint_capacities(joints: list[dict], info, out: dict, x_frame: float, ms: list[dict], settings: ConnectionSettings) -> None:
    """Section strength at the joint and the design forces by the capacity rule (end-plate joints) — in place.

    Basis (user decision 2026-11-11): the SECTION strength of the shallower section at the joint — yielding and local
    buckling, NO lateral-torsional buckling (Lb = 0: bimsteelauto available_strengths with Lb = Lc = 1 mm, below every
    Lp). Fy = the lowest plate of that piece."""
    lay = {m.mark: m for m in info.layout.members}
    strengths = strengths_by_mark(ms)
    f = settings.capacity_fraction
    for j in joints:
        if j.get("forces") is None:
            j["status"] = NOT_EVALUATED
            j["design"] = None
            continue
        F = j["forces"]
        if j["type"] == "base":
            j["design"] = {k: _df(design_force(analysis=F[k]["value"], label=lbl, unit=u))
                           for k, lbl, u in (("compression", "Pu", "kN"), ("uplift", "Tu", "kN"), ("shear", "Vu", "kN"), ("moment", "Mu", "kNm"))}
            j["status"] = EVALUATED
            continue
        secs = [(mk, st, lay[mk].taper.at(st)) for mk, st in j["ends"]]
        mk, st, sec = min(secs, key=lambda t: t[2].Zx)
        stg = strengths[mk]
        mat = _materials(stg["Fy"], stg["Fu"])
        cp = available_strengths(sec, mat, Lb=SECTION_LB, Lc=SECTION_LB, compression_flange="top", method=DesignMethod.LRFD)
        cn = available_strengths(sec, mat, Lb=SECTION_LB, Lc=SECTION_LB, compression_flange="bottom", method=DesignMethod.LRFD)
        j["capacity"] = {"section_of": mk, "member": info.marks[mk], "station": round(st, 1), "section": _section(sec),
                         "Fy": stg["Fy"], "Fy_from": stg["governed_by"], "Lb": 0.0,
                         "phiMn_pos": round(cp.Mc, 3), "phiMn_neg": round(cn.Mc, 3), "phiVn": round(cp.Vc, 3),
                         "citations": {k: v for k, v in cp.citations.items() if k in ("Flexure", "Shear")},
                         "basis": CAPACITY_BASIS}
        fm = f if (f is not None and settings.capacity_moment) else None
        fv = f if (f is not None and settings.capacity_shear) else None
        j["design"] = {
            "Mu_pos": _dfc(F["M_pos"]["value"], cp.Mc, fm, "Mu+", "kNm"),
            "Mu_neg": _dfc(F["M_neg"]["value"], cn.Mc, fm, "Mu-", "kNm"),
            "Vu": _dfc(F["V_max"]["value"], cp.Vc, fv, "Vu", "kN"),
            "Pu": _dfc(F["P_comp"]["value"], None, None, "Pu", "kN"),
            "Tu": _dfc(F["P_tens"]["value"], None, None, "Tu", "kN"),
        }
        j["status"] = EVALUATED


def _dfc(analysis: float, capacity: float | None, fraction: float | None, label: str, unit: str) -> dict:
    """bimsteelauto_connections.design_force: with the capacity rule when a fraction is given, else the analysis alone."""
    if fraction is None:
        return _df(design_force(analysis=analysis, label=label, unit=unit))
    return _df(design_force(analysis=analysis, member_capacity=capacity, fraction=fraction, label=label, unit=unit))


def _df(d) -> dict:
    out = {k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in asdict(d).items()}
    out["criterion"] = d.criterion.value
    return out


def _analysis_only(j: dict, items: dict) -> None:
    """Design forces = the analysis values; any None → NOT EVALUATED listing it."""
    missing = [k for k, v in items.items() if v is None]
    if missing:
        j.update(status=NOT_EVALUATED, design=None, missing=missing)
        return
    j["design"] = {k: _df(design_force(analysis=round(float(abs(v)), 3), label=k, unit="kNm" if k.startswith("M") else "kN"))
                   for k, v in items.items()}
    j["status"] = EVALUATED


def placeholder_warnings(b: BuildingInput) -> list[str]:
    """Warnings when the members the connections develop still have the generator's PLACEHOLDER sizes (user decision
    2026-11-11): frames on the span rules (sizes not given, or equal to default_sizes of the typed span), wind columns /
    end rafters on the generator's constant section. The 50 % rule then follows an undesigned section."""
    w = []
    if b.sizes is None or b.sizes == default_sizes(b.span):
        w.append("Main frames have the span-rule PLACEHOLDER sizes (not sized by PEB > Design...): the capacity-based "
                 "connection forces follow an undesigned section - size the frames first.")
    if getattr(b, "wind_column", None) is None:
        w.append("Wind columns have the generator's placeholder section (not sized).")
    if "rafter" in (b.end_first, b.end_last) and getattr(b, "end_rafter", None) is None:
        w.append("End rafters have the generator's placeholder section (not sized).")
    return w


def building_joints(b: BuildingInput, li, *, analysis: dict | None = None, settings: ConnectionSettings | None = None,
                    out: dict | None = None) -> dict:
    """Every joint with its LRFD forces and design forces. analysis = analyse_building(b, li) (run here when None)."""
    from ..analysis.building_analysis import analyse_building
    from ..design.secondary_checks import wind_column_inputs

    settings = (settings or ConnectionSettings()).check()
    warnings = placeholder_warnings(b)                  # before resolve(): it fills sizes with the defaults
    b, _ = resolve(b)
    out = out or peb_building(b)
    if analysis is None:
        analysis = analyse_building(b, li)
    joints = joint_list(b, out)
    by_line = {f["line"]: f for f in analysis.get("frames", [])}
    # frame lines
    for i in _frame_lines(b):
        n = str(i + 1)
        js = [j for j in joints if j.get("frame_line") == n]
        f = by_line.get(n)
        res = None if f is None else (f.get("result") or by_line.get(f.get("same_as"), {}).get("result"))
        if res is None:
            for j in js:
                j.update(forces=None, status=NOT_EVALUATED, design=None, missing=[f"frame line {n} is not in the analysis result"])
            continue
        ms, info = _frame_info(b, i, base=analysis.get("input", {}).get("base", "pinned"))
        tmp = _frame_joints(b, i, info)
        ends = {t["id"]: t for t in tmp}
        for j in js:
            j["ends"], j["node"] = ends[j["id"]]["ends"], ends[j["id"]].get("node")
        frame_joint_forces(js, res)
        frame_joint_capacities(js, info, out, b.frame_xs()[i], ms, settings)
        if f.get("same_as") != n:
            for j in js:
                j.setdefault("notes", []).append(f"forces of frame line {f['same_as']} (identical members and loads)")
    # wind columns
    efs = {e["end"]: e for e in analysis.get("end_frames", [])}
    wci = {}
    try:
        wci = {row["id"]: (row, inp) for row, inp in wind_column_inputs(out, li, efs)}
    except Exception as exc:                                            # stated, never a silent pass
        wci_error = str(exc)
    else:
        wci_error = None
    for j in joints:
        if j["type"] not in ("wind_column_top", "wind_column_base"):
            continue
        cid = j["id"][:-2]
        if cid not in wci:
            j.update(status=NOT_EVALUATED, design=None, missing=[f"wind column {cid}: no member forces ({wci_error or 'not in the analysis'})"])
            continue
        row, inp = wci[cid]
        top = j["type"] == "wind_column_top"
        V = P = None
        combo = {}
        for cname, sts in inp.forces.items():
            s = sts[-1] if top else sts[0]
            if V is None or abs(s.Vy) > V:
                V, combo["V"] = abs(s.Vy), cname
            if P is None or s.P > P:
                P, combo["P"] = s.P, cname
        T = 0.0
        ef = efs.get(row["end"])
        if not top and ef:                                              # uplift at an end-rafter wall's column base
            T = max([0.0] + [-r["reactions"][cid][1] for r in ef["results"].values() if r["set"] == "LRFD" and cid in r["reactions"]])
        j["forces"] = {"V_out_of_plane": round(V, 3), "P_comp": round(P, 3), **({} if top else {"uplift": round(T, 3)}),
                       "combos": combo, "source": "the wind column's member-check forces (C&C 1.0 W, 1.2 × self weight, + end-rafter frame load)"}
        if ef and not top:
            j["forces"]["H_in_plane"] = round(max([0.0] + [abs(r["reactions"][cid][0]) for r in ef["results"].values()
                                                           if r["set"] == "LRFD" and cid in r["reactions"]]), 3)
        _analysis_only(j, {"Vu": V, "Pu": P, **({} if top else {"Tu": T})})
    # end rafters
    for j in joints:
        if j["type"] == "end_rafter_ridge":
            end = "first" if j["id"].startswith("EF") else "last"
            ef = efs.get(end)
            if not ef:
                j.update(status=NOT_EVALUATED, design=None, missing=[f"no end-rafter frame result for the {end} wall"])
                continue
            yr = float(b.span) / 2
            M = V = P = None
            for c, r in ef["results"].items():
                if r["set"] != "LRFD" or not r.get("rafter_stations"):
                    continue
                for y, p_, v_, m_ in r["rafter_stations"]:
                    if abs(y - yr) <= TOL_STATION:
                        M, V, P = max(M or 0.0, abs(m_)), max(V or 0.0, abs(v_)), max(P or 0.0, abs(p_))
            j["forces"] = None if M is None else {"M_abs": M, "V_abs": V, "P_abs": P, "source": "end-rafter frame, rafter stations at the ridge (LRFD)"}
            _analysis_only(j, {"Mu": M, "Vu": V, "Pu": P})
        elif j["type"] == "end_rafter_splice":
            end = "first" if j["id"].startswith("EF") else "last"
            ef = efs.get(end)
            ys = j["point"][1]
            cands = [] if not ef else [row for r in ef["results"].values() if r["set"] == "LRFD"
                                       for row in (r.get("rafter_stations") or []) if abs(row[0] - ys) <= TOL_STATION]
            if not cands:
                j.update(status=NOT_EVALUATED, design=None,
                         missing=[f"no end-rafter frame station within {TOL_STATION:g} mm of the splice (y = {ys})"])
                continue
            M, V, P = (max(abs(r[k]) for r in cands) for k in (3, 2, 1))
            j["forces"] = {"M_abs": M, "V_abs": V, "P_abs": P, "source": "end-rafter frame, rafter stations at the splice node (LRFD)"}
            _analysis_only(j, {"Mu": M, "Vu": V, "Pu": P})
    # braces
    br = analysis.get("bracing", {}).get("sets", {}).get("LRFD", {})
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    for j in joints:
        if j["type"] != "brace_end":
            continue
        bid = j["id"][:-2]
        role = mem[bid]["role"]
        T = None
        if role == "roof_brace":
            T = br.get("roof_diagonal")
        elif role == "wall_brace":
            T = br.get("wall_diagonal")
        else:
            ef = efs.get(mem[bid].get("wall"))
            if ef:
                vals = [r["braces"][bid] for r in ef["results"].values() if r["set"] == "LRFD" and bid in r.get("braces", {})]
                T = max(vals) if vals else None
        j["forces"] = None if T is None else {"tension": T, "source": "tension-only diagonal force, LRFD"}
        _analysis_only(j, {"Tu": T})
    # cleats
    for j in joints:
        if j["type"] == "cleat":
            j.update(forces=None, status=NOT_EVALUATED, design=None,
                     missing=["support reactions of the cold-formed lines (engine/connections/cleats.py, step 5a)"])
    for j in joints:
        j.pop("ends", None)
        j.pop("node", None)
        j.setdefault("status", NOT_EVALUATED)
    counts: dict[str, dict] = {}
    for j in joints:
        c = counts.setdefault(j["type"], {"joints": 0, "evaluated": 0, "not_evaluated": 0})
        c["joints"] += 1
        c["evaluated" if j["status"] == EVALUATED else "not_evaluated"] += 1
    counts["total"] = {k: sum(v[k] for v in counts.values()) for k in ("joints", "evaluated", "not_evaluated")}
    return {"banner": BANNER, "designed": False, "warnings": warnings, "settings": asdict(settings),
            "capacity_rule": {"fraction": settings.capacity_fraction, "source": CAPACITY_RULE_SOURCE, "basis": CAPACITY_BASIS,
                              "applies_to": ("knee / ridge / rafter-splice joints only: "
                                             + (", ".join(x for x, on in (("Mu+ and Mu-", settings.capacity_moment),
                                                                         ("Vu", settings.capacity_shear)) if on) or "nothing (both switched off)")
                                             + "; every other force and joint: the analysis force alone")},
            "joints": joints, "counts": counts,
            "not_evaluated": sum(j["status"] == NOT_EVALUATED for j in joints)}
