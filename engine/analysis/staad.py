# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 5b: one frame line as a STAAD.Pro input file (.std), for the user to run in STAAD.Pro V8i and compare.

    STAAD PLANE, UNIT METER KN; joints = the layout's nodes (X across, Y up); members = the layout's members
    MEMBER PROPERTY: a built-up member as TAPERED f1..f7 = depth at start, web t, depth at end, top flange b, t, bottom
      flange b, t (m) — the technical reference's order; rigid knee / ridge arms as a stiff PRISMATIC (AX, IZ)
    SUPPORTS: PINNED (or FIXED)
    one primary LOAD per case (D, C, Lr, the wind cases); member loads:
      GLOBAL_Y → UNI GY −w (TRAP GY for a taper's self-weight); GLOBAL_Y_PROJECTED → UNI PY −w; GLOBAL_X → UNI GX w;
      NORMAL (roof pressure, + onto the top face) → UNI Y −w (local y up on a rafter)
    LOAD COMBINATION per LRFD / ASD combination, then PERFORM ANALYSIS (FIRST ORDER: compare with Manafe3's first-order
    results; for P-Delta replace it with PDELTA ANALYSIS and turn the combinations into REPEAT LOADs — noted in the file)
Not round-tripped here (no STAAD on this machine for the tests): the tests check the text by hand; the user runs it.
"""

from __future__ import annotations


def _f(v: float) -> str:
    return f"{v:.6g}"


def staad_frame(info, fl, *, title: str = "Manafe3 frame", base: str = "pinned") -> str:
    lay = info.layout
    names = list(lay.nodes)
    jid = {n: i + 1 for i, n in enumerate(names)}
    at = {lay.nodes[n]: n for n in names}
    out = ["STAAD PLANE", "START JOB INFORMATION", f"JOB NAME {title[:60]}", "ENGINEER NAME Manafe3 (not designed; Phase 3 check)",
           "END JOB INFORMATION", "INPUT WIDTH 79", "UNIT METER KN", "JOINT COORDINATES"]
    out += [f"{jid[n]} {_f(lay.nodes[n][0] / 1000)} {_f(lay.nodes[n][1] / 1000)} 0;" for n in names]
    out.append("MEMBER INCIDENCES")
    mid = {}
    for k, m in enumerate(lay.members, 1):
        mid[m.mark] = k
        out.append(f"{k} {jid[at[m.i_point]]} {jid[at[m.j_point]]};   * {m.mark} {info.marks[m.mark]}")
    out += ["DEFINE MATERIAL START", "ISOTROPIC STEEL", "E 2e+08", "POISSON 0.3", "DENSITY 76.982", "ALPHA 1.2e-05", "DAMP 0.03",
            "END DEFINE MATERIAL", "MEMBER PROPERTY"]
    for m in lay.members:
        if info.roles[m.mark] == "link":
            out.append(f"{mid[m.mark]} PRIS AX 1 IZ 1   * rigid arm")
        else:
            a, b = m.taper.start, m.taper.end
            out.append(f"{mid[m.mark]} TAPERED {_f(a.d / 1000)} {_f(a.tw / 1000)} {_f(b.d / 1000)} {_f(a.bf_top / 1000)} {_f(a.tf_top / 1000)} {_f(a.bf_bot / 1000)} {_f(a.tf_bot / 1000)}")
    out += ["CONSTANTS", "MATERIAL STEEL ALL", "SUPPORTS", " ".join(str(jid[b]) for b in lay.base_nodes) + (" FIXED" if base == "fixed" else " PINNED")]
    cid = {}
    for k, case in enumerate(fl.cases, 1):
        cid[case] = k
        out += [f"LOAD {k} TITLE {case}", "MEMBER LOAD"]
        for ld in fl.loads:
            if ld.case != case:
                continue
            m, w = mid[ld.member_mark], ld.w
            d = ld.direction.name
            if d == "GLOBAL_Y":
                out.append(f"{m} UNI GY {_f(-w)}" if ld.w_end is None or ld.w_end == w else f"{m} TRAP GY {_f(-w)} {_f(-ld.w_end)}")
            elif d == "GLOBAL_Y_PROJECTED":
                out.append(f"{m} UNI PY {_f(-w)}")
            elif d == "GLOBAL_X":
                out.append(f"{m} UNI GX {_f(w)}")
            elif d == "NORMAL":
                out.append(f"{m} UNI Y {_f(-w)}")
            else:
                raise ValueError(f"no STAAD mapping for {d}")
    for k, (name, factors, s) in enumerate(fl.combinations, 101):
        out.append(f"LOAD COMBINATION {k} {name[:70]}")
        out.append(" ".join(f"{cid[c]} {_f(f)}" for c, f in factors.items() if c in cid))
    out += ["* FIRST-ORDER analysis, to compare with Manafe3's first-order results.",
            "* For P-Delta: replace the next line with PDELTA ANALYSIS and make the combinations REPEAT LOADs.",
            "PERFORM ANALYSIS", "FINISH", ""]
    return "\n".join(out)
