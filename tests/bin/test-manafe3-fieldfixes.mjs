#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * Field fixes from the first real project (R1) — one section per item, values by hand.
 *
 * 1. Building… never deletes or replaces existing grids, levels, footings or members: grids merge (default, no
 *    duplicates) / none / replace; levels merged.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/peb-building.js');
const { Model, emptyState } = await mod('model.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 600) : '')); } };
const RES = JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3/building1.json'), 'utf8'));
const spec = { ...B.BUILDING_DEFAULTS };

// ---- 1. grids, levels, footings, own members kept ---------------------------------------------------------------------
{
  // a site: grids 1–3 at 0 / 6000 / 13000, A at 0 and K at 40000; levels Ground 0 and Mezz 3500; a footing; my beam
  const site = () => {
    const m = new Model(emptyState('site'));
    m.change('site', (tx) => {
      tx.setGrids({ x: [{ label: '1', at: 0 }, { label: '2', at: 6000 }, { label: '3', at: 13000 }], y: [{ label: 'A', at: 0 }, { label: 'K', at: 40000 }] });
      tx.setLevels([{ name: 'Ground', z: 0 }, { name: 'Mezz', z: 3500 }]);
      tx.addFooting({ x: 50000, y: 50000, top: 0 });
      tx.addMember({ type: 'beam', profile: 'IPE300', material: 'S355', start: [0, -3000, 3000], end: [6000, -3000, 3000] });
    });
    return m;
  };
  // building 1's grids: x 1..5 at 0, 6000, 12000, 18000, 24000; y A 0, B 24000; levels Ground 0, Eave 6000
  const m = site();
  const r = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
  const gx = m.state.grids.x, gy = m.state.grids.y;
  // merged x by hand: 0 (1, kept), 6000 (2, kept), 12000 → "3" taken → "3'", 13000 (3, kept), 18000 (4), 24000 (5)
  ok(JSON.stringify(gx.map((g) => [g.label, g.at])) === JSON.stringify([['1', 0], ['2', 6000], ["3'", 12000], ['3', 13000], ['4', 18000], ['5', 24000]]), 'x grids merged, no duplicates, mine kept', gx);
  // y: A 0 kept; B 24000 added; K 40000 kept
  ok(JSON.stringify(gy.map((g) => [g.label, g.at])) === JSON.stringify([['A', 0], ['B', 24000], ['K', 40000]]), 'y grids merged', gy);
  ok(r.gridsAdded === 4 && r.grids === 'merge', 'four lines added (12000, 18000, 24000, B)', r);
  ok(JSON.stringify(m.state.levels) === JSON.stringify([{ name: 'Ground', z: 0 }, { name: 'Mezz', z: 3500 }, { name: 'Eave', z: 6000 }]), 'levels merged (Mezz kept, Eave added)', m.state.levels);
  ok(m.state.footings.length === 1 && m.state.members.filter((x) => !x.gen).length === 1, 'my footing and my beam stay', m.state.footings.length);
  // regenerating: no further grid lines, still my things
  const r2 = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
  ok(r2.gridsAdded === 0 && m.state.grids.x.length === 6 && m.state.footings.length === 1, 'regenerating adds no duplicates', r2);

  const n = site();
  n.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec, { grids: 'none' }));
  ok(n.state.grids.x.length === 3 && n.state.grids.y.length === 2, 'none: grids untouched', n.state.grids);
  const p = site();
  p.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec, { grids: 'replace' }));
  ok(p.state.grids.x.length === 5 && p.state.grids.y.map((g) => g.label).join() === 'A,B' && p.state.footings.length === 1 && p.state.levels.length === 3, 'replace: the building\'s grids; footings and levels still kept', p.state.grids);
  p.undo();
  ok(p.state.grids.x.length === 3, 'one undo brings my grids back');
}

// ---- 2 / 15. weight by material: concrete is a volume, never steel ------------------------------------------------------
{
  const M = await mod('manafe3/materials.js');
  const { build } = await mod('build.js');
  const { clashCheck } = await mod('clash.js');
  for (const s of ['C30', 'C 25', 'C30/37', 'C35 fcu', 'Concrete', 'RC', 'B25']) ok(M.isConcrete(s), 'concrete: ' + s);
  for (const s of ['S355', 'A992', 'S350GD', 'A572 Gr 50', 'St 37', 'SS400', 'CS Type B', '']) ok(!M.isConcrete(s), 'steel: ' + s);
  const m = new Model(emptyState('mat'));
  m.change('x', (tx) => {
    tx.addMember({ type: 'beam', profile: 'IPE300', material: 'S355', start: [0, 0, 3000], end: [6000, 0, 3000] });
    tx.addMember({ type: 'column', profile: 'PL300x300', material: 'C30', start: [3000, 0, 0], end: [3000, 0, 3000] });   // runs into the beam
    tx.addFooting({ x: 20000, y: 0, top: 0, L: 1500, B: 1500, H: 600 });
  });
  const b = build(m.state);
  const steel = b.parts.reduce((t, p) => t + p.weight, 0);
  // IPE300: 42.2 kg/m (EN 10365) × 6 m = 253.2 kg; the C30 "plate" 0 kg; 300 × 300 × 3000 = 0.27 m³; footing 1.5 × 1.5 × 0.6 = 1.35 m³
  ok(Math.abs(steel - 42.2 * 6) < 0.5, 'steel total = the IPE300 only', steel);
  const c = M.concreteTotals(b.parts, m.state.footings);
  ok(Math.abs(c.m3 - (0.27 + 1.35)) < 1e-9 && c.parts === 1, 'concrete 1.62 m³ (member 0.27 + footing 1.35)', c);
  ok(b.problems.some((p) => /concrete material on a steel profile/.test(p.text)), 'warned: geometry only, RC on the roadmap');
  const cl = clashCheck(m.state, b, { tol: 1 });
  ok(cl.clashes.length === 0, 'the concrete column is left out of the steel clash check', cl.clashes.length);
  m.change('steel', (tx) => tx.updateMember(m.state.members[1].id, { material: 'S355' }));
  ok(clashCheck(m.state, build(m.state), { tol: 1 }).clashes.length === 1, 'negative control: as S355 it clashes with the beam');
}

// ---- 3. every panel hears a load ---------------------------------------------------------------------------------------
{
  const P = await mod('manafe3/panels.js');
  const seen = [];
  const off1 = P.onModelLoaded(() => seen.push('analysis'));
  P.onModelLoaded(() => { throw new Error('a broken panel'); });
  P.onModelLoaded(() => seen.push('building'));
  const m = new Model(emptyState('first'));
  const whys = [];
  m.on((why) => { whys.push(why); if (why === 'load') P.modelLoaded(); });   // what detailcraft.js onModelEvent does
  const other = new Model(emptyState('R1 site'));
  m.load(other.toJSON());
  ok(whys.includes('load') && m.state.name === 'R1 site', 'model.load emits "load" with the new name', whys);
  ok(seen.join() === 'analysis,building', 'every panel told, a broken one does not stop the others', seen);
  off1();
  // the wiring in detailcraft.js: the Name field is rewritten after a load even when it has focus
  const src = fs.readFileSync(path.join(APP, 'detailcraft.js'), 'utf8');
  ok(/model\.on\(onModelEvent\)/.test(src) && /if \(why === 'load'\) \{[^}]*forceName = true; m3ModelLoaded\(\)/.test(src) && /focused !== ui\.name \|\| forceName/.test(src), 'detailcraft.js wires the load event');
}

// ---- 4. move / rotate / mirror keep every part's roll, holes and plates --------------------------------------------------
{
  const { build } = await mod('build.js');
  const X = await mod('transform.js');
  const { getProfile } = await mod('profiles.js');
  const make = () => { const m = new Model(emptyState('xf')); m.change('b', (tx) => B.applyBuilding(tx, RES, spec)); return m; };
  const all = (m) => m.state.members.map((x) => ({ kind: 'member', id: x.id }));
  const cen = (p) => [0, 1, 2].map((i) => p.frame.o[i] + p.frame.x[i] * p.length / 2 + p.frame.v[i] * p.voff);
  const near = (a, b, tol) => a.every((v, i) => Math.abs(v - b[i]) <= tol);
  for (const [label, xf] of [['rotate 90 about Z', X.rotateXf([0, 0], 90)], ['rotate 37 about (1234, -567)', X.rotateXf([1234, -567], 37)], ['move', X.moveXf(1000, -2000, 300)]]) {
    const m = make(), b0 = build(m.state);
    m.change(label, (tx) => X.transformRefs(tx, m.state, all(m), xf));
    const b1 = build(m.state);
    let bad = 0, cols = 0;
    for (const p of b0.parts) {
      const q = b1.byId.get(p.id);
      // a rigid motion: u, v (the roll: which way a web faces), the part's centre and every hole go with it
      const same = q && near(X.applyDir(xf, p.frame.u), q.frame.u, 1e-6) && near(X.applyDir(xf, p.frame.v), q.frame.v, 1e-6) && near(X.applyPt(xf, cen(p)), cen(q), 1e-3)
        && p.holes.length === q.holes.length && p.holes.every((h, i) => Math.abs(h.x - q.holes[i].x) < 1e-6 && Math.abs(h.y - q.holes[i].y) < 1e-6 && h.face === q.holes[i].face);
      if (!same) bad++;
      if (p.type === 'column') cols++;
    }
    ok(bad === 0 && b1.parts.length === 648 && cols === 10 + 6 + 2, `${label}: all 648 parts (10 frame-column webs, 6 wind-column webs, 2 jambs) keep roll, centre and holes`, { bad, cols });
  }
  // a mirror: the image of a lipped C (CFC) is the channel turned over about u — v flips, as a hot-rolled C (was: kept, wrong)
  const m = make(), b0 = build(m.state);
  const kind = new Map(m.state.members.map((x) => [x.id, getProfile(x.profile, [])?.kind]));
  const xf = X.mirrorXf([0, 1000], [5000, 4000]);
  m.change('mirror', (tx) => X.transformRefs(tx, m.state, all(m), xf));
  const b1 = build(m.state);
  const cfc = b0.parts.filter((p) => kind.get(p.member) === 'CFC');
  ok(cfc.length === 11 && cfc.every((p) => { const q = b1.byId.get(p.id); return near(X.applyDir(xf, p.frame.v).map((n) => -n), q.frame.v, 1e-6) && near(X.applyPt(xf, cen(p)), cen(q), 1e-3); }), 'mirror: lipped C eave struts / jambs turned over like a channel, in the image place', cfc.length);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
