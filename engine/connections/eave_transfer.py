# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5d (with step 6 merged — user 2026-11-17): the eave transfer of the roof bracing, and the end-wall wind
column tops (top clip with vertical slots) under longitudinal wind. NOT FOR ISSUE. SI: mm, kN, MPa.

The user's decisions (2026-11-15, step 5d: 1a, 2a + the top-flange-alone check, 3a, 4a, 5a, 6a, 7a, 8a; 2026-11-17: step 6
merged):
    EAVE TRANSFER — at every roof-bracing node over the eave (the lowest roof-brace end on a rafter: the first purlin past
    the knee), the brace's component along the building F_x = T |u·X| travels down the rafter end, through the knee, into
    the column top and the wall bracing.
        pairing (1a)   as open item 6: every LRFD combination with Load Case B takes the Case B roof-diagonal force × its
                       wind factor; the ASCE 7-16 §28.3.4 minimum family (0.9D / 1.2D + 1.0 W_min) the minimum force with
                       the dead load only (longitudinal.brace_forces split, the ROOF diagonal here).
        rafter end (2a)  weak-axis bending M = F_x × a (a = the node's distance from the knee along the rafter) added to the
                       Phase 4 check at that station of the SAME combination: U = U_P4 + Mry / φMny (the H1 minor-axis
                       term with coefficient 1 — conservative for H1-1a's 8/9), φMny by AISC 360-16 F6 (Claude, from
                       memory — flange local buckling of the built-up section).
                       Torsion as the TOP FLANGE ALONE (user): all F_x on the top flange, M = F_x × a against Z = tf bf² / 4,
                       with the flange axial Mx / (d − tf) + P / 2 of the same combination: U = Ff / (0.9 Fy Af) + M /
                       (0.9 Fy Zf) (linear, Claude — TO CONFIRM).
        knee bolts (3a)  F_x shared by all the knee's end-plate bolts: the compression-side bolts (step 3's shear method)
                       carry √(V² + (F_x n_c / n)²), the tension bolts J3.7 with their tension scaled from step 3 (T_bolt =
                       the step 3 prying-design bolt force × |M_knee| / Mu_design of that sign) and shear F_x / n, against
                       min(step 3's T available, φRnt') — same combination.
        column top (4a)  its OWN line — it does NOT close open item 7: weak-axis bending M = F_x × the lever from the eave
                       to the top wall-brace hole (bracing.WALL_BRACE_TOP, 100 mm) added to the Phase 4 column check at
                       its top station; weak-axis shear F_x against G6 φ 0.9 × 0.6 Fy × 2 bf tf (Cv2 = 1, from memory).
        failure (5a)   report only: the failing check and the suggestion "an eave-panel strut (move the roof brace's lowest
                       node to the eave strut) or an eave-panel brace".
    WIND-COLUMN TOPS (6a, 7a; step 6 slots):
        force          the wind column's top reaction of its member check (step 1 joint force: C&C 1.0 W simple beam).
        clip           PL10 S355 + 2 × M16 8.8 (settings, VERIFIED False); the clip has VERTICAL SLOTS so the rafter can
                       deflect: bolt shear J3.6; bearing / tear-out J3.10 on the clip with the long slot PERPENDICULAR to
                       the force (pyaisc360 long_slot_perpendicular) and on the connected part (the wind column web,
                       standard holes) — the model has no detail: Claude's reading of "bearing on clip and flange", TO
                       CONFIRM; clip bending with the 100 mm offset of the wind column outside the end frame as the
                       eccentricity: M = F × e against the clip's minor axis Z = b t² / 4 (the conservative orientation —
                       TO CONFIRM); no J10.1 (the force acts along the building, in the plane of the flange — user).
        slots          length = d0 + δ_down + δ_up + tolerance, δ = the end-frame rafter's vertical movement at the wind
                       column under every ASD (service) combination (the frame result's displacements, interpolated), the
                       tolerance 6 mm (setting, TO CONFIRM), rounded up to 1 mm; flagged when longer than the AISC Table
                       J3.3M long slot (2.5 d).
        rafter (7a)    the end-frame rafter's BOTTOM flange ALONE in lateral bending between the flange-brace points either
                       side of the wind column (a simple span, M = F a b / L; the brace groups of step 5c), with the flange
                       axial Mx / (d − tf) + P / 2 at that station — the largest over the frame's LRFD combinations (the
                       wind column's C&C reaction does not belong to one frame combination: an envelope, TO CONFIRM); FLAG
                       when no flange brace sits at the wind-column top.
    Status: DESIGNED / FAILS (with the suggestion) / NOT EVALUATED / PARTIAL; never a pass for a missing input.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import asdict, dataclass

from bimsteelauto.design import check_member
from bimsteelauto_connections.bolts import bolt_shear_capacity, bolt_tension_capacity, get_grade
from pyaisc360 import chapter_j as J

from ..peb.bracing import WALL_BRACE_TOP
from .cleats import IN, KIP, KSI, _host_at
from .longitudinal import MIN_FAMILY, low_rise_limits, torsion_exception, wind_factor

BANNER = "NOT FOR ISSUE — eave transfer and wind-column tops (Phase 5 step 5d + step 6 slots); Claude's rules VERIFIED False"
DESIGNED, FAILS, NOT_EVALUATED, PARTIAL = "DESIGNED", "FAILS", "NOT EVALUATED", "PARTIAL"
E_STEEL = 200000.0
SUGGEST = "an eave-panel strut (move the roof brace's lowest node to the eave strut) or an eave-panel brace"
VERIFIED = {"f6_minor_axis": False, "g6_minor_shear": False, "top_flange_alone": False, "knee_bolt_share": False,
            "clip_detail": False, "clip_orientation": False, "slot_rule": False, "flange_lateral_envelope": False}


@dataclass
class EaveSettings:
    """Every default of step 5d — editable per job, listed on each result (TO CONFIRM in the step's batch review)."""
    clip_t: float = 10.0
    clip_width: float = 150.0
    clip_grade: str = "S355JR"
    wc_bolt_d: float = 16.0
    wc_bolt_grade: str = "8.8"
    wc_bolts: int = 2
    threads: str = "N"
    clip_edge: float = 40.0             # bolt to the clip's edge in the force direction, mm
    slot_tol: float = 6.0               # slot length = d0 + δ_down + δ_up + this, mm
    column_lever: float = WALL_BRACE_TOP  # eave to the top wall-brace hole, mm

    def check(self) -> "EaveSettings":
        for k in ("clip_t", "clip_width", "wc_bolt_d", "clip_edge", "slot_tol", "column_lever"):
            if not getattr(self, k) > 0:
                raise ValueError(f"{k} must be > 0")
        if not (isinstance(self.wc_bolts, int) and self.wc_bolts >= 1):
            raise ValueError("wc_bolts must be a whole number ≥ 1")
        return self


# ------------------------------------------------------------------------------------------------- section strengths

def minor_axis(sec: dict, Fy: float) -> dict:
    """φMny (AISC 360-16 F6: yielding / flange local buckling, from memory) and φVny (G6, 0.9 × 0.6 Fy × Σ bf tf, Cv2 = 1)
    of a built-up I, kN·mm and kN."""
    bt, tt, bb, tb, hw, tw = sec["bf_top"], sec["tf_top"], sec["bf_bot"], sec["tf_bot"], sec["hw"], sec["tw"]
    Zy = tt * bt ** 2 / 4 + tb * bb ** 2 / 4 + hw * tw ** 2 / 4
    Iy = tt * bt ** 3 / 12 + tb * bb ** 3 / 12 + hw * tw ** 3 / 12
    Sy = Iy / (max(bt, bb) / 2)
    Mp = min(Fy * Zy, 1.6 * Fy * Sy)
    lam = max(bt / (2 * tt), bb / (2 * tb))
    lp, lr = 0.38 * math.sqrt(E_STEEL / Fy), 1.0 * math.sqrt(E_STEEL / Fy)
    if lam <= lp:
        Mn, rule = Mp, "F6-1"
    elif lam <= lr:
        Mn, rule = Mp - (Mp - 0.7 * Fy * Sy) * (lam - lp) / (lr - lp), "F6-2"
    else:
        Mn, rule = 0.69 * E_STEEL / lam ** 2 * Sy, "F6-3"
    return {"phiMny": 0.9 * Mn / 1000.0, "rule": rule, "lambda": lam, "phiVny": 0.9 * 0.6 * Fy * (bt * tt + bb * tb) / 1000.0}


def top_flange_alone(sec: dict, Fy: float, Mx: float, P: float, Fx: float, a: float) -> dict:
    """The user's torsion check (2026-11-15): the top flange alone, F_x × a laterally (Z = tf bf² / 4) with the flange axial
    |Mx| / (d − tf) + |P| / 2 (kN, kN·m, mm)."""
    bt, tt, d = sec["bf_top"], sec["tf_top"], sec["d"]
    Ff = abs(Mx) * 1000.0 / (d - tt) + abs(P) / 2.0
    Af, Zf = bt * tt, tt * bt ** 2 / 4.0
    ua, ub = Ff / (0.9 * Fy * Af / 1000.0), Fx * a / (0.9 * Fy * Zf / 1000.0)
    return {"Ff": Ff, "M_lat": Fx * a, "axial": ua, "bending": ub, "U": ua + ub}


def flange_lateral(F: float, a: float, b: float) -> float:
    """M (kN·mm) of a flange as a simple span a + b with F at a from one end."""
    return F * a * b / (a + b)


def slot_length(d0: float, d_down: float, d_up: float, tol: float) -> float:
    return math.ceil(d0 + max(d_down, 0.0) + max(d_up, 0.0) + tol)


def bolt_tension_shear_U(T: float, V: float, phiRt: float, phiRv: float, T_avail: float) -> float:
    cap = min(T_avail, phiRt, 1.3 * phiRt - phiRt * V / phiRv)
    return T / cap if cap > 0 else math.inf


# ------------------------------------------------------------------------------------------------- frame data

def _scaled_result(fres: dict, fd_list) -> dict:
    """A frame result whose 'LRFD' combinations are the dead load case × each factor (the §28.3.4 minimum family)."""
    D = fres["results"]["D"]
    res = {name: {"set": "LRFD", "members": {k: [(x, fd * P, fd * V, fd * M) for x, P, V, M in rows] for k, rows in D["members"].items()}}
           for name, fd in fd_list}
    return {**fres, "combos": [(name, "LRFD") for name, _ in fd_list], "results": res}


def _p4_at(inputs: dict, name: str, s: float) -> dict:
    """{combo: (U_P4 at the station nearest s, MemberForces)} of one design member (forces of that combination only)."""
    inp = inputs[name]
    out = {}
    for c, sts in inp.forces.items():
        f = min(sts, key=lambda x: abs(x.station - s))
        r = check_member(dataclasses.replace(inp, forces={c: [f]}))
        out[c] = (r.utilisation, f)
    return out


def _inputs(b, i: int, fres: dict, out: dict):
    from ..connections.joints import _frame_info
    from ..design.frame_checks import design_inputs, strengths_by_mark
    ms, info = _frame_info(b, i)
    st = strengths_by_mark(ms)
    return {dm["name"]: inp for dm, inp, _ in design_inputs(info, fres, out, b.frame_xs()[i], st)}, info, st


def _row(key, name, ref, dem, cap, U, combo=None):
    U = float(U)
    return {"key": key, "name": name, "ref": ref, "demand": None if dem is None else round(float(dem), 3),
            "capacity": None if cap is None else round(float(cap), 3), "U": round(U, 4) if math.isfinite(U) else math.inf,
            **({"combo": combo} if combo else {})}


# ------------------------------------------------------------------------------------------------- the building

def building_eave_transfer(b, jr: dict, out: dict, analysis: dict, endplates: dict, settings: EaveSettings | None = None,
                           flexible_diaphragm: bool | None = None) -> dict:
    """Step 5d over a building. b = the resolved BuildingInput; jr = building_joints(); endplates = building_endplates()."""
    from .brace_ends import _unit
    from .longitudinal import _frame_result
    st = (settings or EaveSettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    br = analysis.get("bracing", {}) or {}
    s_lrfd = br.get("sets", {}).get("LRFD", {})
    k, r_ = br.get("minimum_scale"), br.get("minimum_ratio")
    roof_T = s_lrfd.get("roof_diagonal")
    forces = None if roof_T is None or k is None or r_ is None else {"T_caseB": roof_T / k, "T_minimum": roof_T / k * r_}
    limits, torsion = low_rise_limits(out), torsion_exception(out, flexible_diaphragm)
    knees = {j["joint"]: j for j in endplates.get("joints", []) if j["type"] == "knee"}
    frames = sorted(b.frame_xs())
    eave, wct = [], []
    cache = {}

    def frame_data(x):
        if x in cache:
            return cache[x]
        i = min(range(len(frames)), key=lambda q: abs(frames[q] - x))
        fres = _frame_result(analysis, x)
        if fres is None:
            cache[x] = None
            return None
        inp, info, stg = _inputs(b, i, fres, out)
        mins = None
        if "D" in fres["results"]:
            from ..design.frame_checks import design_inputs
            mins = {dm["name"]: v for dm, v, _ in design_inputs(info, _scaled_result(fres, MIN_FAMILY), out, frames[i], stg)}
        cache[x] = (i, fres, inp, mins)
        return cache[x]

    # ---- the eave nodes: the lowest roof-brace end on each rafter
    lows = {}
    for j in jr["joints"]:
        if j["type"] != "brace_end":
            continue
        bm = mem[j["members"][0]["id"]]
        if bm["role"] != "roof_brace" or len(j["members"]) < 2:
            continue
        hm = mem[j["members"][1]["id"]]
        if hm["role"] != "rafter":
            continue
        hs = _host_at(hm, j["point"])
        if hs is None:
            continue
        key = (round(j["point"][0]), hm["side"])
        if key not in lows or hs["s"] < lows[key][2]["s"]:
            lows[key] = (j, bm, hs, hm)
    for (xf, side), (j, bm, hs, hm) in sorted(lows.items()):
        rec = {"joint": j["id"], "frame_x": xf, "side": side, "rafter": hm["id"], "a_from_knee": round(hs["s"], 1),
               "status": NOT_EVALUATED, "limits": limits, "torsion": torsion}
        far = bm["end"] if math.dist(bm["start"], j["point"]) < math.dist(bm["end"], j["point"]) else bm["start"]
        u = _unit([far[q] - j["point"][q] for q in range(3)])
        ux = abs(u[0])
        why = []
        if forces is None:
            why.append("the bracing result has no Case B / minimum split (re-run the analysis)")
        if not limits["ok"]:
            why.append("the Ch. 28 envelope limits are not met: the longitudinal pairing is NOT EVALUATED")
        fd = frame_data(xf)
        if fd is None:
            why.append("no frame-line analysis at this frame")
        if why:
            eave.append({**rec, "missing": why})
            continue
        i, fres, inp, mins = fd
        rname, cname = f"rafter {side}", f"column {side}"
        sec = hs["sec"]
        Fy_r = get_grade(hs["grade"], max(sec["tf_top"], sec["tf_bot"]))[0]
        mr = minor_axis(sec, Fy_r)
        col = mem.get(f"F{i + 1}-C{side}")
        cs = _host_at(col, [col["end"][0], col["end"][1], col["end"][2] - st.column_lever]) if col else None
        mc = minor_axis(cs["sec"], get_grade(cs["grade"], max(cs["sec"]["tf_top"], cs["sec"]["tf_bot"]))[0]) if cs else None
        Lc = inp[cname].taper.length
        p4r = _p4_at(inp, rname, hs["s"])
        p4c = _p4_at(inp, cname, Lc - st.column_lever)
        p4k = _p4_at(inp, rname, 0.0)
        mins_r = _p4_at(mins, rname, hs["s"]) if mins else {}
        mins_c = _p4_at(mins, cname, Lc - st.column_lever) if mins else {}
        mins_k = _p4_at(mins, rname, 0.0) if mins else {}
        cases = []
        for c in p4r:
            f = wind_factor(fres.get("factors", {}).get(c, {}))
            if f is not None:
                cases.append((c, "Case B", forces["T_caseB"] * f, p4r[c], p4c[c], p4k[c]))
        for c in mins_r:
            cases.append((c, "minimum", forces["T_minimum"], mins_r[c], mins_c[c], mins_k[c]))
        if not any(cs_[1] == "Case B" for cs_ in cases):
            eave.append({**rec, "missing": ["the frame line has no Load Case B combination"]})
            continue
        knee = knees.get(f"F{i + 1}-K{side}")
        rows = []
        for c, fam, T, (ur, fr), (uc, fc), (_uk, fk) in cases:
            Fx = T * ux
            rows.append(_row("rafter", "rafter end: Phase 4 + weak-axis F_x × a (H1 minor term)", "AISC 360-16 H1-1, F6",
                             Fx * hs["s"] / 1000.0, mr["phiMny"] / 1000.0, ur + Fx * hs["s"] / mr["phiMny"], c))
            tf = top_flange_alone(sec, Fy_r, fr.Mz, fr.P, Fx, hs["s"])
            rows.append(_row("rafter", "top flange alone: F_x × a + Mx/(d − tf) + P/2", "user rule (TO CONFIRM interaction)",
                             None, None, tf["U"], c))
            if cs:
                rows.append(_row("column", "column top (own line, not item 7): Phase 4 + weak-axis F_x × lever", "AISC 360-16 H1-1, F6",
                                 Fx * st.column_lever / 1000.0, mc["phiMny"] / 1000.0, uc + Fx * st.column_lever / mc["phiMny"], c))
                rows.append(_row("column", "column top weak-axis shear", "AISC 360-16 G6 (from memory)", Fx, mc["phiVny"], Fx / mc["phiVny"], c))
            if knee:
                bolt = knee["bolt"]
                nb_side = next(iter(knee["sides"].values()))["rows"]["n_bolts"]
                n_all = 2 * nb_side
                sh = knee["shear"][next(iter(knee["shear"]))]
                V = abs(fk.Vy)
                rows.append(_row("knee", "knee bolts, compression side: √(V² + (F_x/2)²)", "AISC 360-16 J3.6 / J3.10 (step 3 method)",
                                 math.hypot(V, Fx * nb_side / n_all), sh["phiVn"], math.hypot(V, Fx * nb_side / n_all) / sh["phiVn"], c))
                sign = "-M (top flange in tension)" if fk.Mz < 0 else "+M (bottom flange in tension)"
                sd = knee["sides"].get(sign)
                if sd and sd.get("prying_check"):
                    T_b = sd["prying_check"]["Tu_per_bolt"] * abs(fk.Mz) / sd["Mu"]
                    phiRt = bolt_tension_capacity(bolt["grade"], bolt["d"])
                    phiRv = bolt_shear_capacity(bolt["grade"], bolt["d"], threads="N" if bolt.get("threads") == "included" else "X")
                    rows.append(_row("knee", "knee bolts, tension side: J3.7 with F_x / n", "AISC 360-16 J3.7 (J3-3a)",
                                     T_b, None, bolt_tension_shear_U(T_b, Fx / n_all, phiRt, phiRv, sd["prying_check"]["T_available"]), c))
            else:
                rows.append(_row("knee", "knee bolts — NOT EVALUATED (no step 3 knee result)", "-", None, None, math.inf, c))
        worst = {}
        for r in rows:
            if r["name"] not in worst or r["U"] > worst[r["name"]]["U"]:
                worst[r["name"]] = r
        checks = sorted(worst.values(), key=lambda r: -r["U"])
        bad = [r for r in checks if r["U"] > 1.0]
        notes = []
        if torsion["status"] != "EXEMPT":
            notes.append(torsion.get("why", "torsional load cases not exempt"))
        status = FAILS if bad else (PARTIAL if notes else DESIGNED)
        rec.update(status=status, checks=checks, governing={kk: checks[0][kk] for kk in ("name", "U")},
                   brace=bm["id"], u_x=round(ux, 4), F_x_caseB=round(forces["T_caseB"] * ux, 3),
                   F_x_minimum=round(forces["T_minimum"] * ux, 3), minor_axis={"rafter": mr, "column": mc},
                   suggestion=(f"{', '.join(r['name'] for r in bad)} fail: {SUGGEST}" if bad else None), notes=notes)
        eave.append(rec)
    # ---- the wind-column tops
    d0 = st.wc_bolt_d + 2.0
    phiRv = bolt_shear_capacity(st.wc_bolt_grade, st.wc_bolt_d, threads=st.threads)
    Fy_c, Fu_c = get_grade(st.clip_grade, st.clip_t)
    efs = {e["end"]: e for e in out.get("end_walls", [])}
    for j in jr["joints"]:
        if j["type"] != "wind_column_top":
            continue
        wc = mem[j["members"][0]["id"]]
        rafter = mem.get(j["members"][1]["id"]) if len(j["members"]) > 1 else None
        rec = {"joint": j["id"], "wind_column": wc["id"], "rafter": rafter["id"] if rafter else None, "status": NOT_EVALUATED}
        F = ((j.get("design") or {}).get("Vu") or {}).get("value")
        missing = []
        if F is None:
            missing.append("the wind column's top reaction (step 1)")
        if rafter is None or rafter.get("role") != "rafter":
            missing.append("a main-frame rafter above the wind column (an end-rafter wall: not wired in 5d)")
        if missing:
            wct.append({**rec, "missing": missing})
            continue
        ew = next((e for e in efs.values() if abs(e["x_face"] - wc["start"][0]) < 1.0 or abs(e["x_frame"] - rafter["start"][0]) < 1.0), None)
        offset = abs(ew["x_face"] - ew["x_frame"]) if ew else None
        wsec = (_host_at(wc, j["point"]) or {}).get("sec")
        fd = frame_data(rafter["start"][0])
        rows, notes = [], []
        n = st.wc_bolts
        rows.append(_row("clip", f"bolt shear ({n} × M{st.wc_bolt_d:g} {st.wc_bolt_grade})", "AISC 360-16 J3.6", F / n, phiRv, F / n / phiRv))
        lc = st.clip_edge - d0 / 2
        cap_clip = n * J.bolt_hole_strength(d=st.wc_bolt_d / IN, lc=lc / IN, t=st.clip_t / IN, Fu=Fu_c / KSI,
                                            long_slot_perpendicular=True).available * KIP
        rows.append(_row("clip", "bearing / tear-out on the clip (long slot ⊥ force)", "AISC 360-16 J3.10", F, cap_clip, F / cap_clip))
        if wsec:
            Fu_w = get_grade((_host_at(wc, j["point"]) or {}).get("grade") or "S355JR", wsec["tw"])[1]
            cap_w = n * J.bolt_hole_strength(d=st.wc_bolt_d / IN, lc=10 * st.wc_bolt_d / IN, t=wsec["tw"] / IN, Fu=Fu_w / KSI).available * KIP
            rows.append(_row("clip", "bearing on the connected part (the wind column web, standard holes)", "AISC 360-16 J3.10",
                             F, cap_w, F / cap_w))
        else:
            notes.append("the wind column's section: bearing on it NOT EVALUATED")
        if offset is not None:
            Zc = st.clip_width * st.clip_t ** 2 / 4.0
            M = F * offset
            rows.append(_row("clip", f"clip bending with the {offset:g} mm offset (minor axis, b t²/4)", "AISC 360-16 F11 (TO CONFIRM orientation)",
                             M / 1000.0, 0.9 * Fy_c * Zc / 1e6, M / (0.9 * Fy_c * Zc / 1000.0)))
        else:
            notes.append("the end wall's offset: the clip bending NOT EVALUATED")
        # step 6: the slot from the rafter's vertical movement at the wind column (service)
        slot = None
        if fd:
            i, fres, inp, mins = fd
            ycol = wc["start"][1]                          # the frame plane's x (across) = the model's y
            dd, du, gov = 0.0, 0.0, None
            nodes = fres["nodes"]
            names = sorted((nm for nm in nodes if nm.startswith(("RA", "RB", "RIDGE"))), key=lambda nm: nodes[nm][0])
            xs = [nodes[nm][0] for nm in names]
            for c, s_ in fres.get("combos", []):
                if s_ != "ASD":
                    continue
                disp = fres["results"][c].get("displacements", {})
                ys = [disp[nm][1] for nm in names if nm in disp]
                if len(ys) != len(names):
                    continue
                v = _interp_xy(xs, ys, ycol)
                if -v > dd:
                    dd, gov = -v, c
                du = max(du, v)
            L_slot = slot_length(d0, dd, du, st.slot_tol)
            slot = {"d0": d0, "delta_down": round(float(dd), 2), "delta_up": round(float(du), 2), "tolerance": st.slot_tol, "length": L_slot,
                    "governing_down": gov, "aisc_long_slot_max": 2.5 * st.wc_bolt_d,
                    "exceeds_long_slot": L_slot > 2.5 * st.wc_bolt_d}
            if slot["exceeds_long_slot"]:
                notes.append(f"slot {L_slot:g} mm is longer than the AISC Table J3.3M long slot ({2.5 * st.wc_bolt_d:g} mm): "
                             "a custom slot — the J3 long-slot strength used, flagged")
            # 7a: the rafter's bottom flange alone between the flange-brace points either side of the wind column
            rname = f"rafter {rafter['side']}"
            hs = _host_at(rafter, [rafter["start"][0], ycol, rafter["start"][2]])
            rafters = {m["side"]: m for m in out["members"] if m.get("role") == "rafter" and abs(m["start"][0] - rafter["start"][0]) < 1.0}
            LA = math.dist(rafters["A"]["start"], rafters["A"]["end"]) if "A" in rafters else 0.0
            LB = math.dist(rafters["B"]["start"], rafters["B"]["end"]) if "B" in rafters else 0.0
            Ltot = LA + LB

            def to_u(side_, s_):                           # the inner flange knee A → ridge → knee B
                return s_ if side_ == "A" else LA + (LB - s_)
            bps = sorted({round(to_u(m["host"][-1], _host_at(rafters[m["host"][-1]], m["start"])["s"]), 1)
                          for m in out["members"] if m.get("role") == "flange_brace" and m.get("host", "").startswith("rafter")
                          and abs(m["start"][0] - rafter["start"][0]) < 1.0 and m["host"][-1] in rafters})
            uw = to_u(rafter["side"], hs["s"])
            at_brace = any(abs(x - uw) < 150.0 for x in bps)
            left = max((x for x in bps if x < uw - 1.0), default=0.0)
            right = min((x for x in bps if x > uw + 1.0), default=Ltot)
            if at_brace:
                notes.append("a flange brace sits at the wind-column top")
                Ml = 0.0
            else:
                notes.append("FLAG: no flange brace at the wind-column top — the bottom flange spans between the brace "
                             f"points {left:.1f} and {right:.1f} mm")
                Ml = flange_lateral(F, uw - left, right - uw)
            sec = hs["sec"]
            Fy_r = get_grade(hs["grade"], sec["tf_bot"])[0]
            Af, Zf = sec["bf_bot"] * sec["tf_bot"], sec["tf_bot"] * sec["bf_bot"] ** 2 / 4.0
            best = None
            for c, sts in inp[rname].forces.items():
                f_ = min(sts, key=lambda x: abs(x.station - hs["s"]))
                Ff = abs(f_.Mz) * 1000.0 / (sec["d"] - sec["tf_bot"]) + abs(f_.P) / 2.0
                u_ = Ff / (0.9 * Fy_r * Af / 1000.0) + Ml / (0.9 * Fy_r * Zf / 1000.0)
                if best is None or u_ > best[0]:
                    best = (u_, c, Ff)
            rows.append(_row("rafter", "rafter bottom flange alone: lateral F a b / L + flange axial (envelope)",
                             "user rule 7a (TO CONFIRM envelope)", Ml / 1000.0, 0.9 * Fy_r * Zf / 1e6, best[0], best[1]))
            rec["flange"] = {"u_wind_column": round(uw, 1), "left": left, "right": right, "M_lat": round(float(Ml) / 1000.0, 3),
                             "Ff_axial": round(float(best[2]), 3), "at_brace": at_brace}
        else:
            notes.append("no frame result: the slot and the rafter flange NOT EVALUATED")
        checks = sorted(rows, key=lambda r: -r["U"])
        bad = [r for r in checks if r["U"] > 1.0]
        ne = [n_ for n_ in notes if "NOT EVALUATED" in n_]
        status = FAILS if bad else (PARTIAL if ne else DESIGNED)
        rec.update(status=status, F=F, offset=offset, checks=checks, governing={kk: checks[0][kk] for kk in ("name", "U")},
                   slot=slot, notes=notes)
        wct.append(rec)
    counts = {}
    for grp, rs in (("eave", eave), ("wind_column_tops", wct)):
        c_ = {}
        for r in rs:
            c_[r["status"]] = c_.get(r["status"], 0) + 1
        counts[grp] = c_
    return {"banner": BANNER, "designed": False, "settings": asdict(st), "verified": dict(VERIFIED),
            "brace_forces_roof": forces, "eave": eave, "wind_column_tops": wct, "counts": counts}


def _interp_xy(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 > x0 else 0.0)
    return ys[-1]
