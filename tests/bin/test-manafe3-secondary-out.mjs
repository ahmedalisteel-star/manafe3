#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * Phase 2 step 8: outputs for the secondary steel — DSTV NC, the C/Z punch list, IFC out and back in — on the engine's
 * building 1 + door (fixtures/manafe3/building1.json).
 *
 * Hand values for purlin piece RA1-2 (Z200x65x20x2.0, 5 400 → 12 600, 7 200 long):
 *   holes (from its start): frame / lap pairs at x 40, 600, 1 160, 6 040, 6 600, 7 160, y ±55 → DSTV y 100 ∓ 55 = 45 / 155;
 *   sag-rod holes at x 3 560, 3 640, y +33.333 → DSTV y 133.3; all Ø14  → 14 BO rows
 *   header: code SO (a Z: special), height 200, flange 65, both thicknesses 2, radius 2, 5.60 kg/m
 *   contours: web v 7 200 × 200, flanges o / u 7 200 × 65
 * Eave strut C200x65x20x2.0: code C. Rods (RD12 sag rods 84, RD20 braces 24 = 108): refused (cut and threaded).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/peb-building.js');
const { Model, emptyState } = await mod('model.js');
const { build } = await mod('build.js');
const { markParts } = await mod('marks.js');
const { writeNc1, readNc1, ncRefusal } = await mod('nc1.js');
const { punchList, punchListCsv } = await mod('manafe3/punchlist.js');
const { writeIfc } = await mod('ifc.js');
const { importIfc } = await mod('ifc-import.js');
const Rb = await mod('rebar.js');
const { W, api } = await (await import(pathToFileURL(path.join(REPO, 'tools/detailcraft-test/webifc-node.mjs')).href)).loadCcIfc(APP);
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 700) : '')); } };
const near = (a, b, tol = 0.01) => Math.abs(a - b) <= tol;

const RES = JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3/building1.json'), 'utf8'));
const m = new Model(emptyState('b1'));
m.change('PEB building', (tx) => B.applyBuilding(tx, RES, {}));
const built = build(m.state);
const marks = markParts(built);
const partOf = (name) => built.parts.find((p) => p.member === m.state.members.find((x) => x.name === name).id);

// ---- 1. DSTV --------------------------------------------------------------------------------------------------------
{
  const p = partOf('RA1-2');
  const nc = readNc1(writeNc1(p, { order: 'J1', mark: marks.partMark.get(p.id), count: 1 }));
  const H = nc.header;
  ok(H.code === 'SO' && H.profile === 'Z200x65x20x2.0' && H.length === 7200 && H.height === 200 && H.flangeWidth === 65 && H.flangeThickness === 2 && H.webThickness === 2 && H.radius === 2 && near(H.kgPerM, 5.60), 'Z header', H);
  const ak = nc.blocks.filter((b) => b.type === 'AK').map((b) => [b.rows[0].face, b.rows[2].nums[0], b.rows[2].nums[1]]);
  ok(JSON.stringify(ak) === JSON.stringify([['v', 7200, 200], ['o', 7200, 65], ['u', 7200, 65]]), 'contours: web and both flanges', ak);
  const bo = nc.blocks.find((b) => b.type === 'BO').rows.map((r) => [r.face, r.nums[0], Math.round(r.nums[1] * 10) / 10, r.nums[2]]);
  ok(bo.length === 14 && bo.every((r) => r[0] === 'v' && r[3] === 14), '14 web holes Ø14', bo.length);
  ok(bo.some((r) => r[1] === 40 && r[2] === 45) && bo.some((r) => r[1] === 40 && r[2] === 155) && bo.some((r) => r[1] === 3560 && r[2] === 133.3), 'hole positions by hand (y from the underside)', bo);
  const c = partOf('RA0-2');
  ok(readNc1(writeNc1(c, { mark: 'x' })).header.code === 'C', 'eave strut: code C');
  const rods = built.parts.filter((x) => x.profile.kind === 'RD');
  ok(rods.length === 108 && rods.every((x) => /cut and threaded/.test(ncRefusal(x))), 'rods refused with the reason (84 sag + 24 brace)', rods.length);
  const others = built.parts.filter((x) => x.profile.kind !== 'RD' && ncRefusal(x));
  ok(others.length === 0, 'every other part goes to NC (Z, C, angles, cleats, built-up plates)', others.slice(0, 3).map((x) => [x.profileName, ncRefusal(x)]));
}

// ---- 2. punch list --------------------------------------------------------------------------------------------------
{
  const rows = punchList(built, marks);
  const mk = marks.partMark.get(partOf('RA1-2').id);
  const mine = rows.filter((r) => r.mark === mk);
  ok(mine.length === 14 && mine[0].x === 40 && mine[0].profile === 'Z200x65x20x2.0' && mine[0].length === 7200, 'one row per hole', mine[0]);
  ok(new Set(mine.map((r) => r.y)).size === 3 && mine.some((r) => r.y === 133.3), 'y 45 / 133.3 / 155', [...new Set(mine.map((r) => r.y))]);
  ok(rows.every((r) => /^[CZ]/.test(r.profile)) && punchListCsv(rows).startsWith('Mark,Profile,Grade,Length mm,Qty,Face,Hole x mm'), 'C and Z only; CSV');
}

// ---- 3. IFC out and back in -----------------------------------------------------------------------------------------
{
  const txt = writeIfc(m.state, built, Object.assign(marks, { footingMark: new Map() }), Rb.bendingSchedule([]), { now: new Date('2026-11-05T00:00:00Z') });
  ok(/IFCCSHAPEPROFILEDEF\(/.test(txt) && /IFCCIRCLEPROFILEDEF\(\.AREA\.,'RD12'/.test(txt) && /IFCLSHAPEPROFILEDEF\(\.AREA\.,'L50x5'/.test(txt) && /IFCARBITRARYCLOSEDPROFILEDEF\(\.AREA\.,'Z200x65x20x2\.0'/.test(txt), 'C, rod, metric angle and Z profiles written');
  const { state, report } = await importIfc(W, api, new TextEncoder().encode(txt));
  const count = (s) => { const c = {}; for (const x of s.members) { const k = x.bu ? 'BU' : x.profile; c[k] = (c[k] || 0) + 1; } return c; };
  const a = count(m.state), b = count(state);
  ok(JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort()), 'every member comes back with its profile (built-up by its property set)', { a, b });
  ok(!report.notConverted.length, 'nothing left out', report.notConverted);
  const b2 = build(state);
  const kg = (bb) => bb.parts.reduce((s, p) => s + p.weight, 0);
  ok(b2.problems.length === 0 && b2.parts.length === built.parts.length && near(kg(b2), kg(built), 0.05), 'rebuilt: same parts and weight', { parts: [b2.parts.length, built.parts.length], kg: [kg(b2), kg(built)], probs: b2.problems.slice(0, 3) });
  const holes = (s) => s.members.reduce((n, x) => n + x.holes.length, 0);
  ok(holes(state) === holes(m.state), 'every hole comes back', [holes(state), holes(m.state)]);
  const z0 = m.state.members.find((x) => x.name === 'RA1-2'), z1 = state.members.find((x) => x.profile === 'Z200x65x20x2.0' && Math.abs(x.start[0] - z0.start[0]) < 0.5 && Math.abs(x.start[1] - z0.start[1]) < 0.5 && Math.abs(x.start[2] - z0.start[2]) < 0.5);
  ok(z1 && z1.position === 'bottom' && Math.abs(z1.end[0] - z0.end[0]) < 0.5 && Math.abs(z1.rotation - z0.rotation) < 0.01, 'a purlin piece back on its line, bottom on the roof, same rotation', [z0, z1]);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
