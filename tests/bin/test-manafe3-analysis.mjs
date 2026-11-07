#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/** Phase 3 step 8: the "Analysis…" data side (app/manafe3/frame-analysis.js) on a hand-made result. Run by npm test.
 *  A 10 m × 6 m portal: column CA up (i base → j knee), rafter R left → right, column CB up. Every diagram point below is
 *  worked by hand: a value is drawn on PyNite's local +y — −X for an exactly vertical member going up, +Y for a rafter. */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const A = await mod('manafe3/frame-analysis.js');
const { LOADS_DEFAULTS } = await mod('manafe3/loads.js');
const { BUILDING_DEFAULTS } = await mod('manafe3/peb-building.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, t = 1e-9) => Math.abs(a - b) <= t;
const throwsMsg = (f, re) => { try { f(); return 'no throw'; } catch (e) { return re.test(e.message) ? true : e.message; } };

const C = 'LRFD: 1.2D+1.6Lr (+C)';
const fr = {
  combos: [['D', 'case'], [C, 'LRFD'], ['ASD: 1.0D+1.0Lr (+C)', 'ASD']], base_nodes: ['BA', 'BB'],
  nodes: { BA: [0, 0], KA: [0, 6000], KB: [10000, 6000], BB: [10000, 0] },
  members: [{ mark: 'CA', role: 'column A', i: [0, 0], j: [0, 6000] }, { mark: 'R', role: 'rafter A', i: [0, 6000], j: [10000, 6000] },
    { mark: 'K', role: 'link', i: [0, 6000], j: [0, 6000] }, { mark: 'CB', role: 'column B', i: [10000, 0], j: [10000, 6000] }],
  results: {},
  summary: { max_M_LRFD: { CA: { combo: C, x: 6000, M: -12, set: 'LRFD' }, R: { combo: C, x: 5000, M: 24.5, set: 'LRFD' } }, drift_ASD: ['ASD: 1.0D+1.0Lr (+C)', 12.0],
    sway_ASD: ['ASD: 1.0D+0.6WA+L (+C)', -20.0], apex_ASD: ['ASD: 1.0D+1.0Lr (+C)', -40.0] },
};
for (const [name, set] of fr.combos) {
  fr.results[name] = {
    set, drift: 2, sway: 0, apex: -10,
    reactions: { BA: [3.5, 20, 0], BB: [-3.5, 20, 0] },
    displacements: { BA: [0, 0], KA: [2, -1], KB: [-2, -1], BB: [0, 0] },
    members: { CA: [[0, 20, -3.5, 0], [6000, 20, -3.5, -12]], R: [[0, 3.5, 10, -12], [5000, 3.5, 0, 24.5], [10000, 3.5, -10, -12]], CB: [[0, 20, 3.5, 0], [6000, 20, 3.5, -12]] },
  };
}
const res = { banner: A.BANNER, p_delta: true, input: { span: 10000, eave_height: 6000, n_bays: 2, base: 'pinned' },
  frames: [{ line: '1', kind: 'frame', same_as: '1', result: fr }, { line: '2', kind: 'frame', same_as: '1' }],
  end_frames: [{ end: 'last', results: { D: { set: 'case', reactions: { WL1: [0, 4.25], WL2: [0, 9.5] } } } }] };

{ // diagrams
  const d = A.diagram(fr, C, 'M', 100);
  const ca = d.members.find((m) => m.mark === 'CA'), r = d.members.find((m) => m.mark === 'R');
  ok(ca.curve.length === 4 && near(ca.curve[2][0], 1200) && near(ca.curve[2][1], 6000), 'column going up: M −12 drawn at −(−12)·100 = +1200 in X (left of i→j is −X)', ca.curve);
  ok(near(r.curve[2][0], 5000) && near(r.curve[2][1], 6000 + 2450), 'rafter going right: M 24.5 at 5 m drawn 2450 above', r.curve[2]);
  ok(d.peak.mark === 'R' && d.peak.v === 24.5 && !d.members.some((m) => m.mark === 'K'), 'peak 24.5 in R; the rigid link has no diagram', d.peak);
  ok(A.maxValue(fr, C, 'M') === 24.5 && A.maxValue(fr, C, 'V') === 10 && A.maxValue(fr, C, 'N') === 20, 'largest ordinates M / V / N');
  const s = A.diagram(fr, C, 'shape', 10);
  ok(near(s.members[0].curve[1][0], 20) && near(s.members[0].curve[1][1], 5990), 'deflected shape: KA moved (2, −1) mm × 10', s.members[0].curve);
  // PyNite's local +y (Member3D.T): vertical up → −X; vertical down → +X; otherwise the normal with +Y component
  const eq = (a, b) => near(a[0], b[0]) && near(a[1], b[1]);
  ok(eq(A.localY([0, 0], [0, 6000]), [-1, 0]) && eq(A.localY([0, 6000], [0, 0]), [1, 0]), 'vertical members', [A.localY([0, 0], [0, 6000]), A.localY([0, 6000], [0, 0])]);
  ok(eq(A.localY([0, 0], [10, 0]), [0, 1]) && eq(A.localY([10, 0], [0, 0]), [0, 1]), 'horizontal either way: up');
  const lb = A.localY([23838, 0], [23602, 5668]), la = A.localY([162, 0], [398, 5668]);
  ok(lb[0] > 0.99 && la[0] < -0.99, 'inclined columns (building 1): outside on BOTH sides — B +X, A −X', [la, lb]);
  ok(near(s.peak.v, Math.hypot(2, 1)) && near(A.maxValue(fr, C, 'shape'), Math.hypot(2, 1)), 'largest movement √5 mm');
  ok(throwsMsg(() => A.diagram(fr, C, 'Q', 1), /unknown/) === true && throwsMsg(() => A.diagram(fr, 'nope', 'M', 1), /no result/) === true, 'bad kind / combination refused');
}
{ // sets, same_as, reactions, CSV, summary
  ok(A.combos(fr, 'LRFD').length === 1 && A.combos(fr, 'case')[0].name === 'D' && A.combos(fr).length === 3, 'combinations filtered by set');
  ok(A.frameResult(res, 2) === fr && A.frameResult(res, '9') === null, 'line 2 shows line 1\'s result (same_as)');
  const rows = A.reactionRows(res);
  ok(rows.length === 2 * 3 * 2 + 2, 'two lines × 3 combos × 2 bases + 2 end-frame bases', rows.length);
  ok(rows.some((r) => r.line === '2' && r.column === 'A' && r.set === 'case' && r.combo === 'D' && r.V === 20), 'a de-duplicated line has its own rows');
  ok(rows.some((r) => r.line === '3' && r.column === 'WL2' && r.V === 9.5 && r.M === 0), 'end-rafter frame at the last line (n_bays + 1 = 3)');
  const csv = A.reactionsCsv(res).split('\r\n');
  ok(csv[0] === '"' + A.BANNER + '"' &&   // it holds a comma: quoted
     /H \+ toward column line B, V \+ up/.test(csv[1]) && /unfactored/.test(csv[2]), 'banner, sign convention, sets', csv.slice(0, 3));
  ok(csv[3] === 'Frame line,Column,Set,Case / combination,H (kN),V (kN),M (kN·m)' && csv.includes('1,A,LRFD,LRFD: 1.2D+1.6Lr (+C),3.500,20.000,0.000'), 'header and a row', csv.slice(3, 6));
  const sm = A.summaryRows(res);
  ok(sm[0].drift.ratio === 500 && sm[0].sway.ratio === 300 && sm[0].apex.ratio === 250 && sm[0].maxM.mark === 'R' && sm[1].same_as === '1', 'H/500 (6000/12), sway H/300 (6000/20), L/250 (10000/40), peak member', sm[0]);
}
{ // the request from the model
  ok(throwsMsg(() => A.analysisRequest({}), /make it first/) === true, 'no building → refused');
  const st = { m3building: { ...BUILDING_DEFAULTS }, m3loads: { ...LOADS_DEFAULTS } };
  ok(throwsMsg(() => A.analysisRequest(st), /site facts/) === true, 'no wind speed / exposure → refused, never assumed');
  const b = A.analysisRequest({ ...st, m3loads: { ...LOADS_DEFAULTS, V: '45', exposure: 'C' } });
  ok(b.loads.V === 45 && b.p_delta === true && b.building.span === Number(BUILDING_DEFAULTS.span) && b.building.n_bays === Number(BUILDING_DEFAULTS.n_bays), 'request body', b.building);
}
console.log(`manafe3 analysis: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
