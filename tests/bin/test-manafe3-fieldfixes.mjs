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
  const r2 = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec, { id: r.id }));
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

// ---- 5. placement: origin X, Y, Z and plan rotation ----------------------------------------------------------------------
{
  const { build } = await mod('build.js');
  const X = await mod('transform.js');
  const at = (m, name) => m.state.members.find((x) => x.name === name);
  const base = new Model(emptyState('p0'));
  base.change('b', (tx) => B.applyBuilding(tx, RES, spec));
  const b0 = build(base.state);
  const place = { ...spec, origin_x: 100000, origin_y: 50000, origin_z: 500, plan_rotation: 90 };
  const m = new Model(emptyState('p1'));
  const r = m.change('b', (tx) => B.applyBuilding(tx, RES, place));
  const b1 = build(m.state);
  // by hand: (x, y, z) → (100000 − y, 50000 + x, z + 500)
  const ca = at(base, 'F2-CA'), ca1 = at(m, 'F2-CA');
  ok(JSON.stringify(ca1.start) === JSON.stringify([100000 - ca.start[1], 50000 + ca.start[0], ca.start[2] + 500]), 'a column base lands at (100000 − y, 50000 + x, z + 500)', [ca.start, ca1.start]);
  const xf = B.placementXf(place, 0);
  let bad = 0;
  for (const p of b0.parts) {
    const q = b1.byId.get(p.id.replace(/^m\d+/, (s) => s));   // same ids: the same order of adds
    const same = q && [0, 1, 2].every((i) => Math.abs(X.applyDir(xf, p.frame.u)[i] - q.frame.u[i]) < 1e-6 && Math.abs(X.applyDir(xf, p.frame.v)[i] - q.frame.v[i]) < 1e-6 && Math.abs(X.applyPt(xf, p.frame.o)[i] - q.frame.o[i]) < 1e-3);
    if (!same) bad++;
  }
  ok(bad === 0, 'every part (webs of columns and wind columns included) keeps its roll relative to the frame', bad);
  // grids rotated 90°: the frame lines 1–5 (x 0 … 24000) become y lines 50000 … 74000; span lines A (0), B (24000) become x 100000, 76000
  ok(JSON.stringify(m.state.grids.y.map((g) => [g.label, g.at])) === JSON.stringify([['1', 50000], ['2', 56000], ['3', 62000], ['4', 68000], ['5', 74000]])
    && JSON.stringify(m.state.grids.x.map((g) => [g.label, g.at])) === JSON.stringify([['B', 76000], ['A', 100000]]), 'grids placed (90°)', m.state.grids);
  ok(m.state.levels.some((l) => l.z === 500) && m.state.levels.some((l) => l.z === 6500), 'levels at origin Z (ground 500, eave 6500)', m.state.levels);
  const o = new Model(emptyState('p2'));
  const r30 = o.change('b', (tx) => B.applyBuilding(tx, RES, { ...spec, plan_rotation: 30 }));
  ok(r30.gridsSkipped && o.state.grids.x.length === 0, 'any angle: 30° places the members, grid lines are not added (said)', r30);
  ok(r.rotation === 90 && r.origin.join() === '100000,50000,500', 'the result says where it went');
}

// ---- 6. uneven bays, from site grids ------------------------------------------------------------------------------------
{
  const R1 = { x: 'A B C D E F G H J K L'.split(' ').map((label, i) => ({ label, at: [0, 6600, 12600, 18600, 25100, 31100, 36600, 42600, 48600, 54600, 60000][i] })), y: [] };
  const bl = B.parseBayList('A-L', R1);
  ok(JSON.stringify(bl.bays) === JSON.stringify([6600, 6000, 6000, 6500, 6000, 5500, 6000, 6000, 6000, 5400]) && bl.labels.join('') === 'ABCDEFGHJKL', 'A-L → the site spacings and labels', bl);
  ok(B.parseBayList('F to L', R1).bays.length === 5 &&   // F G H J K L: 6 lines, 5 bays
     B.parseBayList('L-F', R1).bays[0] === 5400, '"F to L" and the reverse');
  ok(JSON.stringify(B.parseBayList('6600 6000, 6000', R1).bays) === '[6600,6000,6000]' && B.parseBayList('', R1) === null, 'typed spacings; empty = even bays');
  const f = Object.fromEntries(Object.entries(B.BUILDING_DEFAULTS).map(([k, v]) => [k, String(v)]));
  const body = B.buildingRequest({ ...f, bays: 'A-L' }, { grids: R1 });
  ok(body.bays.length === 10 && body.n_bays === 10 && body.bay_spacing === 6600, 'the request carries the bays');
  let err = ''; try { B.parseBayList('A-Z', R1); } catch (e) { err = e.message; }
  ok(/no grid axis has both A and Z/.test(err), 'an unknown grid is refused', err);
}

// ---- 7. span reference --------------------------------------------------------------------------------------------------
{
  const f = Object.fromEntries(Object.entries(B.BUILDING_DEFAULTS).map(([k, v]) => [k, String(v)]));
  const body = B.buildingRequest({ ...f, span_ref: 'centreline' });
  ok(body.span_ref === 'centreline' && body.grid_inset === 0 && B.buildingRequest({ ...f, span_ref: 'nonsense' }).span_ref === 'outside', 'span reference in the request');
  // the engine's y_shift (here −400: centreline, d_base 800) moves every member onto the reference lines
  const a = new Model(emptyState('s0')), c = new Model(emptyState('s1'));
  a.change('b', (tx) => B.applyBuilding(tx, RES, spec));
  c.change('b', (tx) => B.applyBuilding(tx, { ...RES, y_shift: -400 }, spec));
  const ya = a.state.members.find((x) => x.name === 'F2-CA').start, yc = c.state.members.find((x) => x.name === 'F2-CA').start;
  ok(yc[1] === ya[1] - 400 && yc[0] === ya[0] && yc[2] === ya[2], 'y_shift applied: the column 400 mm toward −y', [ya, yc]);
  ok(JSON.stringify(c.state.grids.y.map((g) => g.at)) === '[0,24000]', 'grids stay on the reference lines');
}

// ---- 8. several buildings -----------------------------------------------------------------------------------------------
{
  const { readModel } = await mod('model.js');
  const m = new Model(emptyState('two'));
  const r1 = m.change('b1', (tx) => B.applyBuilding(tx, RES, { ...spec, name: 'STORE' }, { id: null }));
  const r2 = m.change('b2', (tx) => B.applyBuilding(tx, RES, { ...spec, name: 'F&S-2', origin_x: 40000 }, { id: null }));
  ok(r1.id === 'B1' && r2.id === 'B2' && B.buildingsOf(m.state).map((b) => b.name).join() === 'STORE,F&S-2', 'two buildings, each with id and name', B.buildingsOf(m.state));
  const ids2 = B.membersOfBuilding(m.state, 'B2').map((x) => x.id).join();
  const r1b = m.change('edit B1', (tx) => B.applyBuilding(tx, RES, { ...spec, name: 'STORE', eave_height: 6000 }, { id: 'B1' }));
  ok(r1b.replaced === 566 && B.membersOfBuilding(m.state, 'B2').map((x) => x.id).join() === ids2 && B.membersOfBuilding(m.state, 'B1').length === 566, '"Edit building" regenerates only that building', r1b);
  const back = readModel(m.toJSON());
  ok(back.state.m3buildings.length === 2 && back.state.m3buildings[1].spec.origin_x === 40000, 'saved and opened: both buildings and their placement');
  const rm = m.change('del', (tx) => B.removeBuilding(tx, 'B2'));
  ok(rm.removed === 566 && B.buildingsOf(m.state).length === 1 && B.membersOfBuilding(m.state, 'B1').length === 566, 'delete one building, the other stays');
  // an older file: one m3building and gen 'peb' members → building B1, edited in place, its members re-tagged
  const old = new Model(emptyState('old'));
  old.change('legacy', (tx) => { B.applyBuilding(tx, RES, spec); tx.s.m3building = tx.s.m3buildings[0].spec; delete tx.s.m3buildings; for (const x of tx.s.members) x.gen = 'peb'; });
  ok(B.buildingsOf(old.state)[0].id === 'B1' && B.membersOfBuilding(old.state, 'B1').length === 566, 'an older model reads as building B1');
  const rl = old.change('edit', (tx) => B.applyBuilding(tx, RES, spec));
  ok(rl.id === 'B1' && rl.replaced === 566 && old.state.members.every((x) => x.gen === 'peb:B1') && !old.state.m3building, 'edited in place, members re-tagged peb:B1', rl);
}

// ---- 9. pad footings under the PEB columns; footings with no column -------------------------------------------------------
{
  const F = await mod('manafe3/peb-footings.js');
  const m = new Model(emptyState('ft'));
  m.change('b', (tx) => { const r = B.applyBuilding(tx, RES, spec); tx.addFooting({ x: 6000, y: 162, top: 0, L: 2500, B: 2500, H: 700 }); return r; });   // one already there (F2-CA)
  const r = m.change('pads', (tx) => F.addPadFootings(tx, tx.s, { building: 'B1' }));
  // 5 frames × 2 columns + 6 wind columns = 16 bases; F2-CA already has one → 15 added; the 2 door jambs get none
  ok(r.added === 15 && r.skipped === 1 && m.state.footings.length === 16, '15 pads added, the existing one kept, jambs none', r);
  // F2-CA: base web 300 + 2 × 12 = 324 deep, outer face on y = 0 (straight top) → centre (6000, 162, 0); F2-CB at y = 24000 − 162
  ok(m.state.footings.some((f) => f.x === 6000 && f.y === 23838 && f.top === 0 && f.L === 2000), 'F2-CB pad centred at (6000, 23838, 0) by hand');
  ok(m.state.footings.find((f) => f.x === 6000 && f.y === 162).L === 2500, 'my own footing untouched');
  ok(F.footingsWithoutColumn(m.state).length === 0, 'every footing has a column');
  // move one column away (with the transform) and add a stray footing: two footings without a column
  const X = await mod('transform.js');
  const col = m.state.members.find((x) => x.name === 'F4-CA');   // (F3-CA's pad also holds the door jamb at x 11 000: still a column)
  m.change('move', (tx) => { X.transformRefs(tx, tx.s, [{ kind: 'member', id: col.id }], X.moveXf(0, -5000, 0)); tx.addFooting({ x: -20000, y: -20000, top: 0 }); });
  ok(F.footingsWithoutColumn(m.state).length === 2, 'the moved column\'s pad and the stray one have no column', F.footingsWithoutColumn(m.state));
  const rm = m.change('clean', (tx) => F.removeFootingsWithoutColumn(tx, tx.s));
  ok(rm.removed === 2 && m.state.footings.length === 15, 'removed, one undo step', rm);
  m.undo();
  ok(m.state.footings.length === 17, 'undo brings them back');
}

// ---- 10. base plates for all PEB columns; the anchor bolt plan sheet -----------------------------------------------------
{
  const F = await mod('manafe3/peb-footings.js');
  const { build } = await mod('build.js');
  const { markParts } = await mod('marks.js');
  const { anchorSheet } = await mod('drawings.js');
  const m = new Model(emptyState('bp'));
  m.change('b', (tx) => B.applyBuilding(tx, RES, spec));
  const r = m.change('bp', (tx) => F.addBasePlates(tx, tx.s));
  ok(r.added === 16 && m.change('again', (tx) => F.addBasePlates(tx, tx.s)).skipped === 16, '16 base plates (10 frame + 6 wind columns), none twice', r);
  const b = build(m.state);
  ok(!b.problems.some((p) => p.hard), 'they build without hard problems', b.problems.filter((p) => p.hard).slice(0, 3));
  // F2-CA: base 324 deep × 250 wide → plate PL20x350 × 525 long (324 + 200 → 525), centred on the section centre (6000, 162), top of plate z 20
  const ca = m.state.members.find((x) => x.name === 'F2-CA');
  const c = m.state.connections.find((x) => x.column === ca.id);
  const pl = b.byId.get(c.id + '.plate');
  const mid = [0, 1, 2].map((i) => (pl.start[i] + pl.end[i]) / 2);
  ok(pl.profileName === 'PL20x350' && Math.abs(pl.length - 525) < 1e-6 && Math.abs(mid[0] - 6000) < 1e-6 && Math.abs(mid[1] - 162) < 1e-6 && Math.abs(mid[2] - 10) < 1e-6, 'F2-CA plate PL20x350 × 525 at (6000, 162) by hand', { n: pl.profileName, L: pl.length, mid });
  ok(pl.attachTo === ca.id + '.s1.web', 'welded to the column\'s bottom web (its assembly)', pl.attachTo);
  const rods = b.bolts.filter((x) => x.kind === 'ANCHORBOLT');
  ok(rods.length === 64, '4 anchor rods each: 64', rods.length);
  // rods at sx 425 along the depth (x of the plate's line) and sy 250 across: (6000 ± 125, 162 ± 212.5) for a column whose depth runs along y
  const mine = rods.filter((x) => x.conn === c.id).map((x) => [Math.round(x.head[0] * 10) / 10, Math.round(x.head[1] * 10) / 10]).sort((p, q) => p[0] - q[0] || p[1] - q[1]);
  ok(JSON.stringify(mine) === JSON.stringify([[5875, -50.5], [5875, 374.5], [6125, -50.5], [6125, 374.5]]), 'rod pattern by hand: x 6000 ± 125, y 162 ± 212.5', mine);
  const sheet = anchorSheet(m.state, b, markParts(b), 0);
  ok(!!sheet, 'the anchor bolt plan sheet is made');
}

// ---- 16. clashes grouped by type; generated connection points hidden until Phase 5 ----------------------------------------
{
  const G = await mod('manafe3/clash-groups.js');
  const { build } = await mod('build.js');
  const { clashCheck } = await mod('clash.js');
  const m = new Model(emptyState('cl'));
  m.change('b', (tx) => B.applyBuilding(tx, RES, spec));
  const r0 = clashCheck(m.state, build(m.state), { tol: 1 });
  // building 1 had 327; 20 were a tapered segment's web box against its own sloping flange (10 columns, 10 rafter haunches)
  ok(r0.clashes.length === 307 && !r0.clashes.some((c) => c.a.id === c.b.id), 'no clash between plates of one built-up segment: 327 − 20 = 307 (splices between segments still listed)', r0.clashes.length);
  const all = G.groupClashes(m.state, r0.clashes);
  const fb = all.groups.find((g) => g.key === 'flange_brace×rafter');
  ok(fb && fb.clashes.length === 72 && fb.generatedJoint && fb.label === 'flange brace × rafter', 'grouped by type: flange brace × rafter, 72, a generated joint', fb && [fb.label, fb.clashes.length]);
  const hid = G.groupClashes(m.state, r0.clashes, { hideGenerated: true });
  ok(hid.hidden === 307 && hid.shown === 0 && hid.groups.length === 0, 'filter on: every generated connection point hidden', hid);
  // a real clash: my own beam through column F2-CA at 3 m, and a beam the PEB generator did not join (purlin role) through a wind column
  const ca = m.state.members.find((x) => x.name === 'F2-CA');
  m.change('mine', (tx) => tx.addMember({ type: 'beam', profile: 'IPE300', material: 'S355', start: [6000, -2000, 3000], end: [6000, 3000, 3000] }));
  const r1 = clashCheck(m.state, build(m.state), { tol: 1 });
  const g1 = G.groupClashes(m.state, r1.clashes, { hideGenerated: true });
  ok(g1.shown >= 1 && g1.groups.every((g) => !g.generatedJoint) && g1.groups.some((g) => g.clashes.some((c) => c.a.id === ca.id || c.b.id === ca.id)), 'filter on: my beam into the column is still shown', g1.groups.map((g) => [g.label, g.clashes.length]));
  ok(g1.hidden === 307, 'the generated ones stay hidden', g1.hidden);
  // a generated pair that is NOT a known joint shows (e.g. a girt into a rafter would be a real fault)
  ok(!G.clashKind({ members: [{ id: 'a', gen: 'peb:B1', m3role: 'girt' }, { id: 'b', gen: 'peb:B1', m3role: 'rafter' }] }, { a: { kind: 'member', id: 'a' }, b: { kind: 'member', id: 'b' } }).generatedJoint, 'girt × rafter is not a generated joint: shown');
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
