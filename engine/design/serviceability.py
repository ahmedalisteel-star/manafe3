# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 4 step 4: serviceability of the main frames — from the service (nominal stiffness, no notional loads) results
of analyse_frame_line; limits editable per job (user decision 2026-11-08).

    sway     every ASD combination that contains a wind case: |horizontal movement of each eave (knee) node| ≤ H / 100,
             H = that knee node's height above its base node (the frame's own eave height on its centroid line)
    rafter   the roof live load case Lr ALONE (unfactored): the downward vertical movement of every rafter node (knees,
             splices, ridge) relative to the straight line joining the two knee-end rafter nodes ≤ L / 180,
             L = the frame span (column line to column line). Measured at the model's nodes only — for a gable frame
             under uniform Lr the ridge governs; a peak between nodes is not seen (stated in the note).
    purlins  L / 150 — kept in the limits here, CHECKED in step 6 (AISI S100)
    crane    the hook: no crane loads are modelled. A frame with crane members gets a crane line with ratio = inf
             ("not evaluated"), never a pass.

Ratios are demand / allowed (≤ 1.00 passes). Signs: the result's displacements are mm in the frame plane (X across,
Y up).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

WIND_PREFIX = "W"


@dataclass(frozen=True)
class ServiceLimits:
    """Denominators: sway H / sway, rafter L / rafter_Lr, purlins and girts L / purlin. Editable per job."""
    sway: float = 100.0
    rafter_Lr: float = 180.0
    purlin: float = 150.0
    crane_sway: float | None = None          # the hook: an H / n limit under crane loads, once cranes are analysed

    def check(self) -> "ServiceLimits":
        for k in ("sway", "rafter_Lr", "purlin"):
            v = getattr(self, k)
            if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
                raise ValueError(f"serviceability limit {k}: must be a positive number (L / n), got {v!r}")
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "ServiceLimits":
        d = dict(d or {})
        unknown = set(d) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown serviceability limit(s): {sorted(unknown)}")
        return cls(**d).check()


def _rafter_nodes(result: dict) -> list[str]:
    """Rafter node names in order from knee A to knee B (RA0, RAS1, …, RIDGE, …, RBS1, RB0)."""
    ra = sorted((n for n in result["nodes"] if n.startswith("RAS")), key=lambda n: int(n[3:]))
    rb = sorted((n for n in result["nodes"] if n.startswith("RBS")), key=lambda n: int(n[3:]), reverse=True)
    mid = ["RIDGE"] + (["RIDGEB"] if "RIDGEB" in result["nodes"] else [])
    return ["RA0", *ra, *mid, *rb, "RB0"]


def rafter_deflection(result: dict, combo: str = "Lr") -> dict:
    """The largest downward movement of a rafter node relative to the chord between the two knee-end rafter nodes."""
    if combo not in result["results"]:
        raise ValueError(f"no result for {combo!r}: the rafter check needs the {combo} case solved on its own")
    disp = result["results"][combo]["displacements"]
    nodes = result["nodes"]
    names = _rafter_nodes(result)
    a, b = names[0], names[-1]
    xa, xb = nodes[a][0], nodes[b][0]
    da, db = disp[a][1], disp[b][1]
    worst = (0.0, a)
    for n in names:
        t = (nodes[n][0] - xa) / (xb - xa)
        rel = disp[n][1] - (da + t * (db - da))               # + up
        if -rel > worst[0]:
            worst = (-rel, n)
    return {"delta": worst[0], "node": worst[1], "chord": (a, b)}


def frame_serviceability(result: dict, span: float, limits: ServiceLimits | None = None, *, has_crane: bool = False) -> dict:
    """The serviceability checks of one solved frame line (analyse_frame_line output)."""
    lim = (limits or ServiceLimits()).check()
    nodes = result["nodes"]
    eaves = [n for n in ("KA", "KB") if n in nodes]
    bases = {"KA": "BA", "KB": "BB"}
    checks = []

    asd_wind = [c for c, s in result["combos"] if s == "ASD"
                and any(k.startswith(WIND_PREFIX) for k in _factors_of(result, c))]
    worst = None
    for c in asd_wind:
        d = result["results"][c]["displacements"]
        for n in eaves:
            H = nodes[n][1] - nodes[bases[n]][1]
            allowed = H / lim.sway
            r = abs(d[n][0]) / allowed
            if worst is None or r > worst["ratio"]:
                worst = {"name": "Sway under wind", "combo": c, "node": n, "demand": abs(d[n][0]), "allowed": allowed,
                         "ratio": r, "limit": f"H/{lim.sway:g}", "H": H}
    if worst is None:
        checks.append({"name": "Sway under wind", "ratio": math.inf, "note": "not evaluated: no ASD combination with wind"})
    else:
        worst["note"] = f"eave {worst['node']} moves {worst['demand']:.1f} mm under {worst['combo']}; H = {worst['H']:.0f} mm"
        checks.append(worst)

    if "Lr" in result["results"]:
        rd = rafter_deflection(result, "Lr")
        allowed = span / lim.rafter_Lr
        checks.append({"name": "Rafter vertical under Lr", "combo": "Lr", "node": rd["node"], "demand": rd["delta"],
                       "allowed": allowed, "ratio": rd["delta"] / allowed, "limit": f"L/{lim.rafter_Lr:g}", "L": span,
                       "note": f"{rd['node']} {rd['delta']:.1f} mm below the chord {rd['chord'][0]}–{rd['chord'][1]} "
                               "(model nodes only: knees, splices, ridge)"})
    else:
        checks.append({"name": "Rafter vertical under Lr", "ratio": math.inf, "note": "not evaluated: no Lr case"})

    if has_crane:
        checks.append({"name": "Crane runway / frame sway under crane", "ratio": math.inf,
                       "note": "not evaluated: crane members are geometry only — crane loads are not analysed"})
    for c in checks:
        for k in ("demand", "allowed", "ratio"):
            if k in c and math.isfinite(c[k]):
                c[k] = round(c[k], 4 if k == "ratio" else 2)
        c["passed"] = bool(math.isfinite(c["ratio"]) and c["ratio"] <= 1.0)
    return {"limits": asdict(lim), "checks": checks, "max_ratio": max(c["ratio"] for c in checks),
            "passed": all(c["passed"] for c in checks), "set": "service (nominal stiffness; ASD combinations, Lr alone)"}


def _factors_of(result: dict, combo: str) -> tuple[str, ...]:
    """The load cases with a non-zero factor in a combination (analyse_frame_line's "factors")."""
    if "factors" not in result or combo not in result["factors"]:
        raise ValueError(f"the analysis result has no factors for {combo!r} (re-run the analysis)")
    return tuple(k for k, v in result["factors"][combo].items() if v)
