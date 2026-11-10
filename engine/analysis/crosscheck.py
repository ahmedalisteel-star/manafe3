# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 5a: an independent cross-check of one frame line with anastruct (a different FE code), first order.

The same layout (nodes, rigid knee arms) and the same loads, but its own discretisation: each tapered member cut into
`n` equal prismatic slices at mid-slice depth (bimsteelauto cuts by depth change), sections from WeldedI.
anastruct conventions, pinned down on cantilevers (engine/tests/test_crosscheck.py): q in "x" + = toward +x, q in "y"
+ = UP; get_node_results_system reports reactions and displacements as the NEGATIVE of the real values. NORMAL roof
loads are split into global x / y components here (anastruct's perpendicular direction follows the element's direction).
Units here: kN, m, kN·m (E = 200 000 MPa = 2e8 kN/m²).
"""

from __future__ import annotations

import math

from anastruct import SystemElements

from bimsteelauto.sections import WeldedI

E_KN_M2 = 2.0e8


def _sec(w: WeldedI):
    return E_KN_M2 * w.A * 1e-6, E_KN_M2 * w.Ix * 1e-12


def anastruct_frame(info, fl, case: str, n: int = 24) -> dict:
    lay = info.layout
    ss = SystemElements()
    elems: dict[str, list[tuple[int, float, float]]] = {}          # mark → [(element id, s0, s1)] as fractions
    for m in lay.members:
        (xi, yi), (xj, yj) = m.i_point, m.j_point
        k = 1 if info.roles[m.mark] == "link" else n
        out = []
        for s in range(k):
            f0, f1 = s / k, (s + 1) / k
            p0 = [(xi + (xj - xi) * f0) / 1000, (yi + (yj - yi) * f0) / 1000]
            p1 = [(xi + (xj - xi) * f1) / 1000, (yi + (yj - yi) * f1) / 1000]
            sec = m.taper.at(m.length * (f0 + f1) / 2)
            EA, EI = _sec(sec)
            out.append((ss.add_element(location=[p0, p1], EA=EA, EI=EI), f0, f1))
        elems[m.mark] = out
    node_at = lambda p: ss.find_node_id([p[0] / 1000, p[1] / 1000])
    for b in lay.base_nodes:
        ss.add_support_hinged(node_at(lay.nodes[b]))
    # anastruct keeps ONE q-load per element (a second q_load call REPLACES the first — pinned in the tests): every load on
    # a slice is summed here into one global vector (qx, qy; + = +x, + = up) at each end, applied once as q in "y" plus
    # q_perp (= +x for direction "y", pinned in the tests)
    acc: dict[int, list[float]] = {}
    for ld in fl.loads:
        if ld.case != case:
            continue
        m = next(x for x in lay.members if x.mark == ld.member_mark)
        (xi, yi), (xj, yj) = m.i_point, m.j_point
        L = m.length
        cos = abs(xj - xi) / L
        we = ld.w if ld.w_end is None else ld.w_end
        nx, ny = -(yj - yi), (xj - xi)
        if ny < 0:
            nx, ny = -nx, -ny
        h = math.hypot(nx, ny)
        nx, ny = nx / h, ny / h
        d = ld.direction.name
        for eid, f0, f1 in elems[ld.member_mark]:
            a = acc.setdefault(eid, [0.0, 0.0, 0.0, 0.0])            # qx0, qx1, qy0, qy1
            for k, f in ((0, f0), (1, f1)):
                w = ld.w + (we - ld.w) * f
                if d == "GLOBAL_Y":
                    a[2 + k] -= w
                elif d == "GLOBAL_Y_PROJECTED":
                    a[2 + k] -= w * cos
                elif d == "GLOBAL_X":
                    a[k] += w
                elif d == "NORMAL":                                  # presses onto the top face: −w · n_up
                    a[k] -= w * nx
                    a[2 + k] -= w * ny
                else:
                    raise ValueError(f"no anastruct mapping for {d}")
    for eid, (qx0, qx1, qy0, qy1) in acc.items():
        ss.q_load(q=[qy0, qy1], element_id=eid, direction="y", q_perp=[qx0, qx1])
    ss.solve()
    reactions = {}
    for b in lay.base_nodes:
        r = ss.get_node_results_system(node_at(lay.nodes[b]))
        reactions[b] = (-r["Fx"], -r["Fy"])
    max_m = {}
    for mark, es in elems.items():
        if info.roles[mark] == "link":
            continue
        max_m[mark] = max(max(abs(ss.get_element_results(eid)["Mmax"]), abs(ss.get_element_results(eid)["Mmin"])) for eid, _, _ in es)
    apex = -ss.get_node_results_system(node_at(lay.nodes[lay.ridge_nodes[0]]))["uy"] * 1000      # mm, real (up +)
    return {"reactions": reactions, "max_M": max_m, "apex_dy": apex}
