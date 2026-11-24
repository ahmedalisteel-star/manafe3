# Manafe3 tool. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 17 stop rule: old (building1-sized.json, apex OFF) → new (building1-apex.json, apex ON) for the rafters,
the ridge end plates, the ridge flange braces, the wind-column tops at the ridge and the kink check.

    uv run python tools/item17-compare.py OUT.json        (slow: two building analyses + two frame checks)
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(fixture: str) -> dict:
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.eave_transfer import building_eave_transfer
    from engine.connections.endplates import building_endplates
    from engine.connections.joints import building_joints
    from engine.connections.kink import building_kinks
    from engine.connections.stability_braces import building_stability_braces
    from engine.design.design_run import frame_rows
    from engine.design.sizing import evaluate, explicit
    from engine.peb.building import BuildingInput, peb_building, resolve
    from engine.peb.builtup_frame import BuiltUpSizes
    from engine.peb.loads_input import LoadsInput

    fx = json.loads((ROOT / "fixtures" / "manafe3" / fixture).read_text(encoding="utf-8"))
    b0, li = BuildingInput(**fx["building"], sizes=BuiltUpSizes(**fx["sizes"])), LoadsInput(**fx["loads"])
    b, _ = resolve(b0)
    out = peb_building(b)
    an = analyse_building(b, li)
    jr = building_joints(b0, li, analysis=an, out=out)
    ep = building_endplates(jr, out)
    sb = building_stability_braces(jr, out, an, li, b=b)
    et = building_eave_transfer(b, jr, out, an, ep)
    kk = building_kinks(b0, li, analysis=an, out=out)
    ev = evaluate(b, li, explicit(b.sizes), code="AISC", stability="dg25")
    rows, _ = frame_rows(ev, "AISC")
    wc = {m["id"]: m for m in out["members"] if m["role"] == "wind_column"}
    return {"fixture": fixture, "sizes": fx["sizes"], "joints": jr, "endplates": ep, "stability": sb, "eave": et, "kinks": kk,
            "frame_rows": rows, "frame_max": ev["max_ratio"], "service": ev["service_ratio"],
            "wind_columns": {k: {"start": v["start"], "end": v["end"]} for k, v in wc.items()}}


if __name__ == "__main__":
    res = {"old": run("building1-sized.json"), "new": run("building1-apex.json")}
    pathlib.Path(sys.argv[1]).write_text(json.dumps(res, default=str, indent=1), encoding="utf-8")
    print("written", sys.argv[1])
