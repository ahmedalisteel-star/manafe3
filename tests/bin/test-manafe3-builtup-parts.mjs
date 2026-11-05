#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * Built-up members as parts: build.js → 3 plates per segment, marks, assemblies, BOM, bar cut list, plate cut list.
 *
 * Model (hand values, mm, kg):
 *   two columns T1 at (0,0) and (6000,0), 0 → 6000 high, rotation 270 (v = −Y: the section hangs to +Y, into the building),
 *     hw 300 → 800, tw 8, flanges 250×12; per column web 207.240, top 141.300, bottom 141.790 → 490.330 kg
 *     web in the world: (0, 312, 0) (0, 812, 6000) (0, 12, 6000) (0, 12, 0); top flange mid-line y = 6; bottom y 318 → 818
 *   one rafter (0,0,6000) → (12000,0,6000), rotation 0 (v = +Z), straight top (the roof line):
 *     haunch 2400: hw 800 → 400, tw 8, flanges 250×12: web 2400·600·8 → 90.432; top 250·12·2400 → 56.520;
 *       bottom √(2400² + 400²) = 2433.105 → 250·12·2433.105 → 57.300
 *     rafter 9600: hw 400, tw 6, flanges 250×10: web 9600·400·6 → 180.864; top and bottom 250·10·9600 → 188.400 each
 *     rafter total 761.916 kg;   model total 2 × 490.330 + 761.916 = 1742.576 kg
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const { Model, emptyState } = await mod('model.js');
const { build } = await mod('build.js');
const { markParts, bomTables } = await mod('marks.js');
const { piecesFromMarks } = await mod('nest.js');
const { plateList, plateListCsv } = await mod('manafe3/platelist.js');
const { toWorld } = await mod('geom.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, tol = 1e-3) => Math.abs(a - b) <= tol;
const nearV = (a, b, tol = 1e-3) => a.every((v, i) => near(v, b[i], tol));

const seg = (o) => ({ length: 6000, hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 }, grade: 'S355', straight: 'top', ...o });
const T1 = { segments: [seg()] };
const RAFTER = { segments: [seg({ length: 2400, hwStart: 800, hwEnd: 400 }), seg({ length: 1, hwStart: 400, hwEnd: 400, tw: 6, top: { b: 250, t: 10 }, bot: { b: 250, t: 10 } })] };

const m = new Model(emptyState('t'));
const [c1, c2, r1] = m.change('frame', (tx) => [
  tx.addMember({ type: 'column', start: [0, 0, 0], end: [0, 0, 6000], rotation: 270, material: 'S355', bu: T1 }),
  tx.addMember({ type: 'column', start: [6000, 0, 0], end: [6000, 0, 6000], rotation: 270, material: 'S355', bu: T1 }),
  tx.addMember({ type: 'beam', start: [0, 0, 6000], end: [12000, 0, 6000], rotation: 0, material: 'S355', bu: RAFTER }),
]);
const built = build(m.state);
ok(built.problems.length === 0, 'builds without problems', built.problems);
ok(built.parts.length === 12, '3 parts per segment: 2 columns × 1 + rafter × 2 segments = 4 segments → 12 parts', built.parts.length);

// ---- 1. the parts in the world ---------------------------------------------------------------------------------------
{
  const web = built.byId.get(c1 + '.s1.web'), top = built.byId.get(c1 + '.s1.top'), bot = built.byId.get(c1 + '.s1.bot');
  ok(web && top && bot && web.member === c1 && top.member === c1 && web.type === 'column' && top.type === 'plate', 'ids, member and types', [web?.type, top?.type]);
  const W = (p) => toWorld(web.frame, p[0], 0, p[1]);
  const pts = web.profile.outline.map(W);
  ok(nearV(pts[0], [0, 312, 0]) && nearV(pts[1], [0, 812, 6000]) && nearV(pts[2], [0, 12, 6000]) && nearV(pts[3], [0, 12, 0]), 'column web corners in the world', pts);
  ok(nearV(top.start, [0, 6, 0]) && nearV(top.end, [0, 6, 6000]) && nearV(bot.start, [0, 318, 0]) && nearV(bot.end, [0, 818, 6000]), 'flange lines in the world', [top.start, top.end, bot.start, bot.end]);
  ok(nearV(top.frame.u, web.frame.u, 1e-9) && nearV(bot.frame.u, web.frame.u, 1e-9), 'flanges lie flat across the member (same u as the web)', [web.frame.u, bot.frame.u]);
  ok(top.profileName === 'PL12x250' && near(bot.length, 6020.797) && web.profileName === 'BUW8 300-800', 'profiles and the sloping flange length', [top.profileName, bot.length, web.profileName]);
  ok(near(web.weight, 207.240) && near(top.weight, 141.300) && near(bot.weight, 141.790), 'column plate weights by hand', [web.weight, top.weight, bot.weight]);
  ok(top.attachTo === web.id && bot.attachTo === web.id && web.attachTo === null, 'flanges are attached to the web (one assembly)');
  const rw = built.byId.get(r1 + '.s1.web');
  const rp = rw.profile.outline.map((p) => toWorld(rw.frame, p[0], 0, p[1]));
  ok(nearV(rp[0], [0, 0, 6000 - 812]) && nearV(rp[1], [2400, 0, 6000 - 412]) && nearV(rp[3], [0, 0, 6000 - 12]), 'rafter haunch hangs below the roof line', rp);
  const rw2 = built.byId.get(r1 + '.s2.web');
  ok(nearV(rw2.start, [2400, 0, 6000]) && near(rw2.length, 9600), 'segment 2 starts at the splice', [rw2.start, rw2.length]);
  const total = built.parts.reduce((s, p) => s + p.weight, 0);
  ok(near(total, 1742.576, 2e-3), 'model weight by hand', total);
}

// ---- 2. marks, assemblies, BOM, bar cut list ---------------------------------------------------------------------------
const marks = markParts(built);
{
  const mk = (id) => marks.partMark.get(id);
  ok(mk(c1 + '.s1.web') === mk(c2 + '.s1.web') && mk(c1 + '.s1.top') === mk(c2 + '.s1.top') && mk(c1 + '.s1.bot') === mk(c2 + '.s1.bot'), 'identical columns: identical part marks');
  ok(mk(c1 + '.s1.top') !== mk(c1 + '.s1.bot'), 'straight and sloping flanges differ (lengths 6000 / 6020.8)');
  ok(mk(r1 + '.s1.web') !== mk(r1 + '.s2.web') && mk(r1 + '.s1.web') !== mk(c1 + '.s1.web'), 'different webs, different marks');
  const colAsm = marks.assemblies.find((a) => a.ids.includes(c1 + '.s1.web'));
  ok(colAsm && colAsm.count === 2 && colAsm.members.length === 3 && near(colAsm.weight, 490.330) && /^C\d/.test(colAsm.mark), 'one column assembly × 2, 3 parts, 490.33 kg', colAsm);
  ok(marks.assemblies.length === 3, 'assemblies: the column, the haunch and the rafter segment', marks.assemblies.map((a) => a.mark));
  const bom = bomTables(marks, built.bolts);
  ok(bom && typeof bom === 'object', 'the BOM tables are made');
  ok(piecesFromMarks(marks).length === 0, 'no bars to nest: webs and flanges are plates');
}

// ---- 3. plate cut list ---------------------------------------------------------------------------------------------------
{
  const pl = plateList(built, marks);
  const webRow = pl.rows.find((r) => r.mark === marks.partMark.get(c1 + '.s1.web'));
  ok(webRow && webRow.shape === 'trapezoid' && webRow.t === 8 && webRow.width === 800 && webRow.length === 6000 && near(webRow.area, 3.3) && webRow.count === 2 && near(webRow.totalKg, 414.48), 'web row: trapezoid 8 mm, 800 × 6000, 3.3 m², ×2, 414.48 kg', webRow);
  const kg = pl.totals.reduce((s, g) => s + g.kg, 0);
  ok(near(kg, 1742.576, 5e-3), 'plate list total = model weight', kg);
  const t8 = pl.totals.find((g) => g.t === 8 && g.grade === 'S355');
  ok(t8 && t8.count === 3 && near(t8.kg, 2 * 207.24 + 90.432, 2e-3), '8 mm S355: two column webs + the haunch web', t8);
  const csv = plateListCsv(pl);
  ok(csv.startsWith('Mark,Grade,Thickness mm') && csv.includes('trapezoid'), 'CSV');
}

// ---- 4. what is not built yet is said, not crashed --------------------------------------------------------------------------
{
  const m2 = new Model(emptyState('t'));
  const c = m2.change('c', (tx) => tx.addMember({ type: 'column', start: [0, 0, 0], end: [0, 0, 6000], rotation: 270, material: 'S355', bu: T1 }));
  m2.change('h', (tx) => tx.addHole(c, { face: 'web', x: 100, y: 0, d: 22 }));
  let b2, err = null;
  try { m2.change('bp', (tx) => tx.addConnection({ type: 'baseplate', column: c })); } catch (e) { err = e.message; }
  try { b2 = build(m2.state); } catch (e) { err = 'build threw: ' + e.message; }
  ok(b2 && b2.parts.length >= 3 && b2.problems.some((p) => /Holes on a built-up member/.test(p.text)), 'a hole on a built-up member is reported', b2?.problems || err);
  ok(!/build threw/.test(String(err)), 'a connection to a built-up member does not break the build', err);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
