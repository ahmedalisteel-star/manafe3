#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * Regression project R1 (field fixes; anonymised — no client name or job number): the first real job rebuilt on its site
 * grids from the engine's buildings (fixtures/manafe3/r1-block1.json, r1-block2.json made by engine/peb/building.py with
 * the job's inputs), placed, with a crane runway, then geometry and totals checked.
 *
 * Site: lettered grids A B C D E F G H J K L at x = 0, 6600, 12600, 18600, 25100, 31100, 36600, 42600, 48600, 54600, 60000;
 *       rows 14 … 1 at y = 0, 6100, 11100, 16100, 21100, 26100, 31100, 37400, 38100, 43300, 48800, 54400, 59900, 65700
 *       (0.7 m expansion joint between rows 7 and 6).
 * Block 1 "STORE + F&S-1": frames on A–L (bays from the site grids), span row 6 → row 1 = 27 600 c/c of the columns
 *       (span measured to centreline), eave 5 400, slope 0.0435, no crane. Origin (0, 38 100), rotation 0.
 * Block 2 "F&S-2": frames on rows 14–7, span F → L = 28 900 c/c, eave 10 000, slope 0.0714; crane runway both sides,
 *       rail top +7 800, rail centre 324 mm from the column inner face. Origin (60 000, 0), rotation 90° (frames along +y,
 *       span toward −x: column line A on L, B on F).
 * Walls: 0.60 plinth + 3.40 blockwork, sheeting from +4.00 → girts from 4 000.
 * Baseline before the fixes (span-rule sizes, NOT designed, the user's earlier model): 86.5 t (Store 16.7, F&S-1 23.5,
 *       F&S-2 46.3 incl. 7.1 t crane) = 31.0 kg/m² over 2 788.5 m². The totals here are recorded, not asserted against it
 *       (different placeholder sizes; Phase 4 design will change them); they must contain NO concrete.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/peb-building.js');
const F = await mod('manafe3/peb-footings.js');
const K = await mod('manafe3/crane.js');
const M = await mod('manafe3/materials.js');
const { Model, emptyState } = await mod('model.js');
const { build } = await mod('build.js');
const { clashCheck } = await mod('clash.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 600) : '')); } };
const fx = (n) => JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3', n), 'utf8'));

const LETTERS = 'A B C D E F G H J K L'.split(' ');
const XS = [0, 6600, 12600, 18600, 25100, 31100, 36600, 42600, 48600, 54600, 60000];
const ROWS = ['14', '13', '12', '11', '10', '9', '8', '7', '6', '5', '4', '3', '2', '1'];
const YS = [0, 6100, 11100, 16100, 21100, 26100, 31100, 37400, 38100, 43300, 48800, 54400, 59900, 65700];
const GX = (l) => XS[LETTERS.indexOf(l)], GY = (r) => YS[ROWS.indexOf(r)];
const WALLS = { girt_first: 4000 };

const m = new Model(emptyState('R1'));
m.change('site', (tx) => { tx.setGrids({ x: LETTERS.map((label, i) => ({ label, at: XS[i] })), y: ROWS.map((label, i) => ({ label, at: YS[i] })) }); });
const base = { ...B.BUILDING_DEFAULTS, ...WALLS, span_ref: 'centreline' };
const r1 = m.change('block 1', (tx) => B.applyBuilding(tx, fx('r1-block1.json'), { ...base, name: 'STORE + F&S-1', span: 27600, eave_height: 5400, roof_slope: 0.0435, bays: 'A-L', origin_x: 0, origin_y: GY('6') }, { id: null }));
const r2 = m.change('block 2', (tx) => B.applyBuilding(tx, fx('r1-block2.json'), { ...base, name: 'F&S-2', span: 28900, eave_height: 10000, roof_slope: 0.0714, bays: '14-7', origin_x: GX('L'), origin_y: 0, plan_rotation: 90 }, { id: null }));
const rc = m.change('crane', (tx) => K.applyCrane(tx, r2.id, { sides: 'both', rail_top: 7800, rail_offset: 324 }));

// ---- the bays come from the site grids; the buildings land ON them (no grid line added) --------------------------------
ok(JSON.stringify(B.parseBayList('A-L', m.state.grids).bays) === JSON.stringify([6600, 6000, 6000, 6500, 6000, 5500, 6000, 6000, 6000, 5400]), 'block 1 bays A–L from the site grids');
ok(JSON.stringify(B.parseBayList('14-7', m.state.grids).bays) === JSON.stringify([6100, 5000, 5000, 5000, 5000, 5000, 6300]), 'block 2 bays rows 14–7 (numbered labels) from the site grids');
ok(r1.gridsAdded === 0 && r2.gridsAdded === 0 && m.state.grids.x.length === 11 && m.state.grids.y.length === 14, 'both buildings fall on the site grids: no grid line added', [r1.gridsAdded, r2.gridsAdded]);

// ---- columns on their grid intersections (base section centres: span measured to the column centrelines) -----------------
const near = (p, q) => Math.abs(p[0] - q[0]) < 1e-3 && Math.abs(p[1] - q[1]) < 1e-3;
const col = (bid, name) => B.membersOfBuilding(m.state, bid).find((x) => x.name === name);
let bad1 = [];
LETTERS.forEach((l, i) => {
  const a = F.baseOf(col(r1.id, `F${i + 1}-CA`)), b = F.baseOf(col(r1.id, `F${i + 1}-CB`));
  if (!near(a, [GX(l), GY('6')]) || !near(b, [GX(l), GY('1')])) bad1.push([l, a, b]);
});
ok(!bad1.length, 'block 1: frame columns on A–L × rows 6 and 1', bad1.slice(0, 2));
const bad2 = [];
['14', '13', '12', '11', '10', '9', '8', '7'].forEach((r, i) => {
  const a = F.baseOf(col(r2.id, `F${i + 1}-CA`)), b = F.baseOf(col(r2.id, `F${i + 1}-CB`));
  if (!near(a, [GX('L'), GY(r)]) || !near(b, [GX('F'), GY(r)])) bad2.push([r, a, b]);
});
ok(!bad2.length, 'block 2: frame columns on rows 14–7 × L and F', bad2.slice(0, 2));
const eave1 = Math.max(...B.membersOfBuilding(m.state, r1.id).filter((x) => /-C[AB]$/.test(x.name)).map((x) => Math.max(x.start[2], x.end[2])));
ok(eave1 === 5400, 'block 1 eave 5 400', eave1);
const girts = m.state.members.filter((x) => x.m3role === 'girt');
ok(girts.length > 0 && Math.min(...girts.map((x) => Math.min(x.start[2], x.end[2]))) >= 4000 - 1e-6, 'sheeting from +4.00: no girt below 4 000');

// ---- crane runway on block 2 ----------------------------------------------------------------------------------------------
ok(rc.members === 48 && !rc.problems.length, 'crane runway both sides: 48 members, no problems', rc);
const b = build(m.state);
const cl = clashCheck(m.state, b, { tol: 1 });
const crane = new Set(m.state.members.filter((x) => x.gen === 'crane:' + r2.id).map((x) => x.id));
const cols = new Set(m.state.members.filter((x) => /^F\d+-C[AB]$/.test(x.name)).map((x) => x.id));
ok(!cl.clashes.some((c) => (crane.has(c.a.id) && cols.has(c.b.id)) || (crane.has(c.b.id) && cols.has(c.a.id))), 'no clash between the runway and the tapered columns of block 2');
ok(b.problems.some((p) => p.text === K.CRANE_WARNING), 'the crane warning shows');

// ---- totals: steel only, by block (Store / F&S-1 split at the common frame on E) ------------------------------------------
const byMember = new Map(m.state.members.map((x) => [x.id, x]));
const t = { store: 0, fs1: 0, fs2: 0, crane: 0, other: 0 };
for (const p of b.parts) {
  const mem = byMember.get(p.member) || byMember.get(b.byId.get(p.attachTo)?.member);
  const gen = mem?.gen || '';
  if (gen === 'crane:' + r2.id) t.crane += p.weight;
  else if (gen === 'peb:' + r2.id) t.fs2 += p.weight;
  else if (gen === 'peb:' + r1.id) {
    const x = (p.start[0] + p.end[0]) / 2;
    if (Math.abs(x - GX('E')) < 1) { t.store += p.weight / 2; t.fs1 += p.weight / 2; } else if (x < GX('E')) t.store += p.weight; else t.fs1 += p.weight;
  } else t.other += p.weight;
}
const total = t.store + t.fs1 + t.fs2 + t.crane;
const conc = M.concreteTotals(b.parts, m.state.footings);
ok(conc.parts === 0 && !b.parts.some((p) => p.concrete) && t.other === 0, 'the steel total contains no concrete (and nothing outside the two buildings)', conc);
ok(total > 50000 && total < 200000, 'a plausible steel total', total);
const tn = (kg) => (kg / 1000).toFixed(1);
console.log(`R1 totals (placeholder sizes, NOT designed): Store ${tn(t.store)} t, F&S-1 ${tn(t.fs1)} t, F&S-2 ${tn(t.fs2 + t.crane)} t incl. crane ${tn(t.crane)} t; total ${tn(total)} t = ${(total / 2788.5).toFixed(1)} kg/m² over 2 788.5 m² (baseline 86.5 t, 31.0 kg/m²)`);

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
