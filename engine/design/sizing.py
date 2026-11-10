# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 4 step 8: the sizing loop for the main frames (and the cold-formed roles). NOT FOR ISSUE.

Decisions (user, 2026-11-08): target utilisation 0.90, never above 1.00; plates 6, 8, 10, 12, 14, 16, 18, 20, 22, 25 mm
(web ≥ 6, flange ≥ 8); flange widths 150, 180, 200, 220, 250, 300 mm; web depths in 25 mm steps; re-analyse until stable.

Main frames — what is sized (the generator's own parameters, BuiltUpSizes; the same on every frame line):
    bf, tf          one flange plate on every member (the generator's splice rule)
    hw_knee         the column's top and the haunch's deep end;  hw_base the column's base;  hw_rafter the rafter
    tw_column, tw_haunch, tw_rafter   the webs
    kept: hw_base ≥ 300 and hw_rafter ≥ 300 (the generator's minimums), hw_rafter and hw_base ≤ hw_knee, the haunch
    length (span / 10) and the grade as given
The loop (a design office's):
    1. analyse every DISTINCT frame line (the same loads → one solve) with the current sizes: the governing code's own
       solve (AISC: the DAM solve; ECP: ecp_checks.ecp_solve), and check them fully (+ serviceability, step 4)
    2. with those forces held (each analysis member's stations scaled to its new length), size by quick checks on the
       few governing combinations of each member (the largest |M| and the largest P per member): raise the variable
       with the best ratio drop per kg until every member ≤ the target, then lower variables (the largest saving
       first) while every member stays ≤ the target; serviceability above 1.0 is steered by the knee / rafter I
    3. re-analyse; stop when the sizes repeat (converged) — at most MAX_ROUNDS rounds; a repeat of an earlier set
       (oscillation) ends the loop with the lightest set seen whose full check is ≤ 1.00
    The result is the FULL check of the final sizes (every combination), never the quick one.
Cold-formed roles (purlin, eave strut, girt — one profile each, building-wide): the lightest profile of CF_LADDER (the
    generated profile's flange and lip kept; depth and thickness from the ladder) whose step-6 check is ≤ the target —
    Claude's ladder, no supplier catalogue yet. Sized by the R-FACTOR mode (user decision 2026-11-09: industry practice),
    with the strict-rule ratio of the chosen profile shown beside it; the R-factor results are NOT FOR ISSUE until the
    user confirms the R values from the printed AISI S100-16 Table I6.2.1-1 (cfs_checks.R_VERIFIED).
"""

from __future__ import annotations

import dataclasses
import math
from concurrent.futures import ProcessPoolExecutor

from ..analysis.building_analysis import _line_setup, _signature
from ..analysis.frame_model import frame_line_model
from ..analysis.secondary_weight import secondary_kpa
from ..analysis.solve import analyse_frame_line
from ..peb.building import BuildingInput, peb_building, resolve
from ..peb.builtup_frame import builtup_frame_members, web_t
from .cfs_section import parse_name
from .serviceability import ServiceLimits, frame_serviceability

PLATES = (6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 25.0)
WEB_MIN, FLANGE_MIN = 6.0, 8.0
FLANGE_WIDTHS = (150.0, 180.0, 200.0, 220.0, 250.0, 300.0)
DEPTH_STEP = 25.0
HW_MIN = 300.0
HW_MAX = 2500.0
TARGET, LIMIT = 0.90, 1.00
MAX_ROUNDS = 8
VARS = ("tf", "bf", "hw_knee", "hw_rafter", "hw_base", "tw_column", "tw_haunch", "tw_rafter")
STEEL = 7.85e-6                       # kg / mm³
CF_LADDER = {"depth": (150.0, 175.0, 200.0, 225.0, 250.0, 300.0), "t": (1.5, 1.8, 2.0, 2.3, 2.5, 3.0)}
BANNER = "NOT FOR ISSUE — sizes from the sizing loop (checks with open verification flags)"


# --------------------------------------------------------------------------------------------- sizes

def explicit(z):
    """The rule's web thicknesses written out, so every web is a sizing variable."""
    return dataclasses.replace(z, tw_column=z.tw_column or web_t(max(z.hw_base, z.hw_knee)),
                               tw_haunch=z.tw_haunch or web_t(max(z.hw_knee, z.hw_rafter)), tw_rafter=z.tw_rafter or web_t(z.hw_rafter))


def _ladder(var, v):
    if var == "tf":
        return [p for p in PLATES if p >= FLANGE_MIN]
    if var.startswith("tw"):
        return [p for p in PLATES if p >= WEB_MIN]
    if var == "bf":
        return list(FLANGE_WIDTHS)
    return None


def step(z, var: str, d: int):
    """The next size of one variable up (d = +1) or down (−1), or None at the end of its range / against a rule."""
    v = getattr(z, var)
    lad = _ladder(var, v)
    if lad is not None:
        if v not in lad:
            nxt = [p for p in lad if (p > v if d > 0 else p < v)]
            if not nxt:
                return None
            nv = nxt[0] if d > 0 else nxt[-1]
        else:
            i = lad.index(v) + d
            if not (0 <= i < len(lad)):
                return None
            nv = lad[i]
    else:
        nv = v + d * DEPTH_STEP
        if not (HW_MIN <= nv <= HW_MAX):
            return None
    z2 = dataclasses.replace(z, **{var: nv})
    if z2.hw_rafter > z2.hw_knee or z2.hw_base > z2.hw_knee:
        return None
    return z2


def frame_weight(b: BuildingInput, z) -> float:
    """kg of one frame line's built-up members (plates × lengths)."""
    ms = builtup_frame_members(b.span, b.eave_height, b.roof_slope, 0.0, "1", z)
    kg = 0.0
    for m in ms:
        for s in m["section"]["segments"]:
            hw = (s["hw_start"] + s["hw_end"]) / 2
            kg += (hw * s["tw"] + s["bf_top"] * s["tf_top"] + s["bf_bot"] * s["tf_bot"]) * s["length"] * STEEL
    return kg


def _valid(b, z) -> bool:
    try:
        builtup_frame_members(b.span, b.eave_height, b.roof_slope, 0.0, "1", z)
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------------------------- analysis and checks

def _check(code, info, result, out, x, st, stability, base):
    if code == "AISC":
        from .frame_checks import check_frame_line
        return check_frame_line(info, result, out, x, st, stability=stability, compare=False)
    from .ecp_checks import ecp_frame_line
    return ecp_frame_line(info, result, out, x, st, base=base)


def _solve(args):
    code, b, li, i, sec = args
    info, fl, fy = _line_setup(b, li, i, sec, 0.10, with_fy=True)
    if code == "AISC":
        return analyse_frame_line(info, fl, fy=fy, label=f"Frame line {i + 1}")
    from .ecp_checks import ecp_solve
    return ecp_solve(info, fl, label=f"Frame line {i + 1} (ECP)")


def distinct_lines(b: BuildingInput, li, sec: dict) -> list[list[int]]:
    """Frame lines (0-based) grouped by identical loads: one solve per group."""
    groups: dict = {}
    n = len(b.frame_xs()) - 1
    for i in range(n + 1):
        if (i == 0 and b.end_first == "rafter") or (i == n and b.end_last == "rafter"):
            continue                                     # an end-rafter wall: no main frame on that line
        _, fl = _line_setup(b, li, i, sec, 0.10)
        groups.setdefault(_signature(fl), []).append(i)
    return list(groups.values())


def evaluate(b: BuildingInput, li, z, *, code="AISC", stability="dg25", limits: ServiceLimits | None = None, workers=None) -> dict:
    """Full analysis and check of every distinct frame line at sizes z."""
    from .frame_checks import strengths_by_mark
    limits = limits or ServiceLimits()
    bz = dataclasses.replace(b, sizes=z)
    out = peb_building(bz)
    sec = secondary_kpa(out)
    groups = distinct_lines(bz, li, sec)
    jobs = [(code, bz, li, g[0], sec) for g in groups]
    if workers == 1 or len(jobs) == 1:
        results = [_solve(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers or min(len(jobs), 4)) as ex:
            results = list(ex.map(_solve, jobs))
    lines = []
    for g, res in zip(groups, results):
        i = g[0]
        info, fl = _line_setup(bz, li, i, sec, 0.10)
        x = bz.frame_xs()[i]
        ms = builtup_frame_members(bz.span, bz.eave_height, bz.roof_slope, x, str(i + 1), z)
        st = strengths_by_mark(ms)
        chk = _check(code, info, res, out, x, st, stability, li.base)
        sv = frame_serviceability(res, bz.span, limits)
        lines.append({"lines": [k + 1 for k in g], "i": i, "x": x, "info": info, "result": res, "strengths": st, "check": chk,
                      "service": sv, "ratio": chk["max_ratio"], "service_ratio": max((c["ratio"] for c in sv["checks"]), default=0.0)})
    return {"sizes": z, "out": out, "lines": lines, "max_ratio": max(l["ratio"] for l in lines),
            "service_ratio": max(l["service_ratio"] for l in lines), "weight_kg_per_frame": frame_weight(bz, z)}


# --------------------------------------------------------------------------------------------- the quick check

def _governing_combos(result, k_m=3, k_p=2) -> list[str]:
    lrfd = [c for c, s in result["combos"] if s == "LRFD"]
    keep = set()
    for mark in result["results"][lrfd[0]]["members"]:
        byM = sorted(lrfd, key=lambda c: -max(abs(s[3]) for s in result["results"][c]["members"][mark]))
        byP = sorted(lrfd, key=lambda c: -max(s[1] for s in result["results"][c]["members"][mark]))
        keep.update(byM[:k_m])
        keep.update(byP[:k_p])
    return [c for c in lrfd if c in keep]


def remap(result, info_old, info_new, combos):
    """The result's stations on the candidate's analysis members (same marks; x scaled to the new lengths)."""
    Lo = {m.mark: m.length for m in info_old.layout.members}
    Ln = {m.mark: m.length for m in info_new.layout.members}
    if set(Lo) != set(Ln):
        return None
    res = {"combos": [[c, "LRFD"] for c in combos], "results": {}}
    for c in combos:
        mem = {}
        for mark, sts in result["results"][c]["members"].items():
            k = Ln[mark] / Lo[mark]
            mem[mark] = [[x * k, P, V, M] for x, P, V, M in sts]
        res["results"][c] = {"members": mem}
    return res


class Quick:
    """Quick checks of candidate sizes on the held forces (cached)."""

    def __init__(self, b, li, ev, code, stability):
        from .frame_checks import strengths_by_mark
        self.b, self.li, self.ev, self.code, self.stability = b, li, ev, code, stability
        self.combos = [_governing_combos(l["result"]) for l in ev["lines"]]
        self.sm = strengths_by_mark
        self.cache = {}
        self.service = ev["service_ratio"]
        z0 = ev["sizes"]
        self.I0 = self._stiff(z0)

    def _stiff(self, z):
        d_k = z.hw_knee + 2 * z.tf
        d_r = z.hw_rafter + 2 * z.tf
        I = lambda d, hw, tw: z.bf * (d ** 3 - (d - 2 * z.tf) ** 3) / 12 + tw * hw ** 3 / 12
        return I(d_k, z.hw_knee, z.tw_column) + I(d_r, z.hw_rafter, z.tw_rafter)

    def ratio(self, z) -> float:
        key = dataclasses.astuple(z)
        if key in self.cache:
            return self.cache[key]
        if not _valid(self.b, z):
            self.cache[key] = math.inf
            return math.inf
        r = 0.0
        bz = dataclasses.replace(self.b, sizes=z)
        for l, combos in zip(self.ev["lines"], self.combos):
            i = l["i"]
            ms = builtup_frame_members(bz.span, bz.eave_height, bz.roof_slope, l["x"], str(i + 1), z)
            info = frame_line_model(ms, bz.span, bz.eave_height, bz.roof_slope, bz.bay_list(), base=self.li.base, max_taper_step=0.10)
            res = remap(l["result"], l["info"], info, combos)
            if res is None:
                r = math.inf
                break
            chk = _check(self.code, info, res, self.ev["out"], l["x"], self.sm(ms), self.stability, self.li.base)
            r = max(r, chk["max_ratio"])
        # serviceability steered by the frame's bending stiffness (the knee + rafter I), only when it governs
        if self.service > TARGET:
            r = max(r, self.service * self.I0 / self._stiff(z))
        self.cache[key] = r
        return r


def size_frames_once(b, li, ev, *, code="AISC", stability="dg25", target=TARGET) -> tuple[object, dict]:
    """One inner pass on held forces: raise until ≤ target, then lower while ≤ target."""
    q = Quick(b, li, ev, code, stability)
    z = ev["sizes"]
    log = []
    r = q.ratio(z)
    guard = 0
    while r > target and guard < 60:
        guard += 1
        w0 = frame_weight(b, z)
        best = None
        for var in VARS:
            z2 = step(z, var, +1)
            if z2 is None:
                continue
            r2 = q.ratio(z2)
            if not math.isfinite(r2):
                continue
            dw = max(frame_weight(b, z2) - w0, 1e-6)
            score = (r - r2) / dw
            if best is None or score > best[0] or (best[0] <= 0 and r2 < best[2]):
                best = (score, z2, r2, var)
        if best is None:
            log.append({"stop": "no variable can be raised"})
            break
        z, r = best[1], best[2]
        log.append({"up": best[3], "ratio": round(r, 4)})
    changed = True
    while changed and guard < 160:
        changed = False
        guard += 1
        w0 = frame_weight(b, z)
        cands = []
        for var in VARS:
            z2 = step(z, var, -1)
            if z2 is not None and _valid(b, z2):
                cands.append((w0 - frame_weight(b, z2), var, z2))
        for saving, var, z2 in sorted(cands, key=lambda c: -c[0]):
            if saving <= 0:
                continue
            r2 = q.ratio(z2)
            if r2 <= target:
                z, r, changed = z2, r2, True
                log.append({"down": var, "ratio": round(r, 4)})
                break
    return z, {"quick_ratio": round(float(r), 4), "steps": log, "checks": len(q.cache)}


def size_frames(b: BuildingInput, li, *, code: str = "AISC", stability: str = "dg25", target: float = TARGET,
                limits: ServiceLimits | None = None, max_rounds: int = MAX_ROUNDS, workers=None) -> dict:
    """The main frames' sizing loop. Returns the final sizes with their FULL check, and the history."""
    if code not in ("AISC", "ECP"):
        raise ValueError("governing code must be AISC or ECP")
    if not (0.5 <= target <= LIMIT):
        raise ValueError("target must be 0.5 to 1.0")
    b, _ = resolve(b)
    z = explicit(b.sizes)
    hist = []
    seen = {}
    final = None
    for k in range(max_rounds):
        ev = evaluate(b, li, z, code=code, stability=stability, limits=limits, workers=workers)
        key = dataclasses.astuple(z)
        rec = {"round": k + 1, "sizes": dataclasses.asdict(z), "max_ratio": round(float(ev["max_ratio"]), 4),
               "service_ratio": round(float(ev["service_ratio"]), 4), "kg_per_frame": round(float(ev["weight_kg_per_frame"]), 1)}
        hist.append(rec)
        if key in seen:                                     # a repeat: converged (the same set) or an oscillation
            final = ev if seen[key] == k - 1 else None
            rec["repeat_of_round"] = seen[key] + 1
            if final is None:
                ok = [h for h in hist if h["max_ratio"] <= LIMIT and h["service_ratio"] <= LIMIT]
                if ok:
                    best = min(ok, key=lambda h: h["kg_per_frame"])
                    final = evaluate(b, li, dataclasses.replace(z, **best["sizes"]), code=code, stability=stability, limits=limits, workers=workers)
            break
        seen[key] = k
        z2, info = size_frames_once(b, li, ev, code=code, stability=stability, target=target)
        rec["inner"] = info
        if z2 == z:
            final = ev
            rec["converged"] = True
            break
        z = z2
    if final is None:
        final = ev
    ok = bool(final["max_ratio"] <= LIMIT and final["service_ratio"] <= LIMIT)
    f = lambda v, n=4: round(float(v), n)                              # plain floats (JSON)
    return {"banner": BANNER, "code": code, "stability": stability, "target": target, "sizes": dataclasses.asdict(final["sizes"]),
            "max_ratio": f(final["max_ratio"]), "service_ratio": f(final["service_ratio"]),
            "kg_per_frame": f(final["weight_kg_per_frame"], 1), "passed": ok, "converged": bool(any(h.get("converged") for h in hist)),
            "rounds": hist, "lines": [{"lines": l["lines"], "ratio": f(l["ratio"]), "service_ratio": f(l["service_ratio"]),
                                       "members": [{"name": m["name"], "ratio": f(m["ratio"]), "governing": m["governing"]} for m in l["check"]["members"]]}
                                      for l in final["lines"]], "designed": False}


# --------------------------------------------------------------------------------------------- cold-formed roles

def cf_candidates(profile: str) -> list[str]:
    """The ladder for one generated profile: its flange and lip kept, depth × thickness from CF_LADDER, by area."""
    g = parse_name(profile)
    out = []
    for d in CF_LADDER["depth"]:
        for t in CF_LADDER["t"]:
            out.append((f"{g['kind']}{d:g}x{g['B']:g}x{g['D']:g}x{t:g}", (d + 2 * g["B"] + 2 * g["D"]) * t))
    return [n for n, _ in sorted(out, key=lambda v: v[1])]


def size_cold_formed(b: BuildingInput, li, *, uplift_method: str = "r_factor", target: float = TARGET, limits=None) -> dict:
    """Purlin, eave strut and girt profiles (building-wide, one each): the lightest ladder profile ≤ the target."""
    from .cfs_checks import R_VERIFIED, building_lines, check_line, r_factor, section_data, tied_rows
    from ..peb.secondary import Sections
    limits = limits or ServiceLimits()
    b, _ = resolve(b)
    out = peb_building(b)
    lines = building_lines(out, li)
    tied, untied = tied_rows(out)
    roles = {"purlin": ("purlin", "ridge_purlin"), "eave_strut": ("eave_strut",), "girt": ("girt", "gable_girt")}
    chosen, report = {}, {}
    for role, kinds in roles.items():
        mine = [l for l in lines if l["kind"] in kinds]
        if not mine:
            continue
        cur = getattr(b.sections, role)
        pick = None
        tried = []
        def worst_of(prof, method):
            w, gov, used = 0.0, None, set()
            for l in mine:
                l2 = dict(l, profile=prof)
                try:
                    sd = section_data(prof, l["grade"])
                except ValueError:
                    return math.inf, "invalid profile", used
                l2["rfactor"] = r_factor(l2, sd, tied_ok=bool(tied) and not untied)
                r = check_line(l2, sd, l2["combos"], limits.purlin, method)
                used.add(r["uplift_method"])
                if r["ratio"] > w:
                    w, gov = r["ratio"], f"{l['id']}: {r['governing']} ({r['combo']})"
            return float(w), gov, used

        for prof in cf_candidates(cur):
            worst, gov, used = worst_of(prof, uplift_method)
            tried.append((prof, round(worst, 4) if math.isfinite(worst) else math.inf))
            if worst <= target:
                pick = prof
                break
        chosen[role] = pick
        strict = worst_of(pick, "strict") if pick else (math.inf, None, set())
        report[role] = {"from": cur, "to": pick, "ratio": tried[-1][1] if pick else None, "governing": gov if pick else None,
                        "uplift_method_used": sorted(used) if pick else None,
                        "strict_ratio": round(strict[0], 4) if math.isfinite(strict[0]) else math.inf, "strict_governing": strict[1],
                        "tried": tried, "note": None if pick else "no ladder profile meets the target"}
    note = ("loads per line from the generated building at the CURRENT profiles (self weight of a heavier profile is "
            "small; the next run re-checks)")
    sections = dataclasses.replace(b.sections, **{k: v for k, v in chosen.items() if v})
    r_used = uplift_method == "r_factor"
    banner = BANNER + (" — R-FACTOR RESULTS NOT FOR ISSUE: the R values (AISI S100-16 Table I6.2.1-1) are unconfirmed"
                       if r_used and not R_VERIFIED else "")
    return {"banner": banner, "uplift_method": uplift_method, "R_VERIFIED": R_VERIFIED, "target": target, "roles": report,
            "sections": dataclasses.asdict(sections), "passed": all(chosen.values()), "note": note, "designed": False}
