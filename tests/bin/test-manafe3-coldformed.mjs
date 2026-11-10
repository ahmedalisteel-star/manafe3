#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * Phase 2 step 1: lipped C and Z, round rods, metric angles (app/manafe3/coldformed.js through profiles.js).
 *
 * Hand values (ρ = 7850 kg/m³). Lipped C / Z: A = t·[(H − 2(r+t)) + 2(B − 2(r+t)) + 2(D − (r+t)) + 4·(π/2)·(r + t/2)]
 *   C200x65x20x2.0, r 2:  192 + 2·57 + 2·16 + 6π = 356.850 → A = 713.699 mm² → 5.60254 kg/m
 *   C250x75x20x2.5, r 2.5: 240 + 2·65 + 2·15 + 7.5π = 423.562 → A = 1058.905 mm² → 8.31240 kg/m
 *   the same section with r 3 (a job-catalogue entry): 190 + 2·55 + 2·15 + 8π = 355.133 → A = 710.265 mm²
 *   Z sections: the same lengths → the same areas; Z200x65 box width 2·65 − 2 = 128, depth 200; C200x65 box 65 × 200
 *   RD20: π·10² = 314.159 mm² → 2.46615 kg/m;  RD12: π·6² = 113.097 → 0.88782 kg/m
 *   L50x5: 5·(2·50 − 5) = 475 mm² → 3.72875 kg/m (no root radius)
 *   a Z200x65x20x2.0 purlin 6000 long: 5.60254 × 6 = 33.6152 kg
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const P = await mod('profiles.js');
const CF = await mod('manafe3/coldformed.js');
const { Model, emptyState } = await mod('model.js');
const { build } = await mod('build.js');
const { markParts } = await mod('marks.js');
const { piecesFromMarks } = await mod('nest.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, tol = 1e-3) => Math.abs(a - b) <= tol;
const shoelace = (l) => { let s = 0; for (let i = 0; i < l.length; i++) { const [a, b] = l[i], [c, d] = l[(i + 1) % l.length]; s += a * d - c * b; } return s / 2; };
const box = (l) => { const us = l.map((p) => p[0]), vs = l.map((p) => p[1]); return [Math.max(...us) - Math.min(...us), Math.max(...vs) - Math.min(...vs)]; };

// ---- 1. areas and masses by hand -----------------------------------------------------------------------------------
for (const [name, A, kg] of [['C200x65x20x2.0', 713.699, 5.60254], ['Z200x65x20x2.0', 713.699, 5.60254], ['C250x75x20x2.5', 1058.905, 8.31240], ['Z250x75x20x2.5', 1058.905, 8.31240], ['RD20', 314.159, 2.46615], ['RD12', 113.097, 0.88782], ['L50x5', 475, 3.72875]]) {
  const p = P.getProfile(name);
  ok(p && near(p.area, A) && near(p.mass, kg, 1e-4), name + ': area and kg/m by hand', p && [p.area, p.mass]);
}
{
  const c = P.getProfile('C200x65x20x2.0'), z = P.getProfile('Z200x65x20x2.0');
  ok(c.kind === 'CFC' && z.kind === 'CFZ' && c.r === 2 && c.H === 200 && c.D === 20, 'kinds and dimensions; a bare name uses r = t');
  ok(near(box(c.loops[0])[0], 65) && near(box(c.loops[0])[1], 200) && near(c.width, 65) && near(c.depth, 200), 'C box 65 × 200', box(c.loops[0]));
  ok(near(box(z.loops[0])[0], 128) && near(box(z.loops[0])[1], 200), 'Z box 128 × 200 (2B − t)', box(z.loops[0]));
  for (const p of [c, z, P.getProfile('C250x75x20x2.5'), P.getProfile('RD20')]) {
    const a = shoelace(p.loops[0]);
    ok(a > 0 && Math.abs(a / p.area - 1) < 0.005, p.name + ': the drawn outline is counter-clockwise and within 0.5 % of the exact area', [a, p.area]);
  }
  // the lips point the right way: C's top lip hangs down at +u, Z's bottom lip stands up at −u
  const cl = c.loops[0], zl = z.loops[0];
  ok(cl.some(([u, v]) => near(u, 32.5) && near(v, 100 - 20)) && zl.some(([u, v]) => near(u, -64) && near(v, -100 + 20)), 'lip ends where expected', null);
  ok(P.getProfile('C200x65x20x10') === null && P.getProfile('Z100x65x60x2') === null && P.getProfile('L50x30') === null, 'impossible sizes are not profiles');
  ok(P.getProfile('L4X4X1/2').source !== 'param' && P.getProfile('C8X11.5').kind === 'C', 'catalog names are untouched (AISC L and C)');
  ok(JSON.stringify(P.holeFaces(z)) === '["web","top","bottom"]' && P.faceThickness(z, 'web') === 2 && P.faceThickness(c, 'top') === 2, 'hole faces and thickness');
}

// ---- 2. the job catalogue: custom entries with their own radius, and the generic starter list ---------------------------
{
  const r = P.cleanCustom({ name: 'C200-R3', kind: 'CFC', H: 200, B: 65, D: 20, t: 2, r: 3 });
  ok(r.ok && near(P.getProfile('C200-R3', [r.profile]).area, 710.265), 'catalogue entry with r 3: 710.265 mm²', r);
  ok(!P.cleanCustom({ name: 'bad', kind: 'CFZ', H: 200, B: 65, D: 20, t: 10, r: 2 }).ok, 'a 10 mm "cold-formed" entry is refused');
  ok(CF.STARTER.length === 20 && CF.STARTER.every((s) => P.getProfile(s.name) && s.designProps === 'from supplier'), 'starter catalogue: 20 generic sizes, design properties from the supplier', CF.STARTER.length);
}

// ---- 3. as members: parts, weights, marks, bar cut list ----------------------------------------------------------------
{
  const m = new Model(emptyState('t'));
  m.change('x', (tx) => {
    tx.addMember({ type: 'beam', profile: 'Z200x65x20x2.0', material: 'S350GD', start: [0, 0, 6000], end: [6000, 0, 6000], position: 'middle' });
    tx.addMember({ type: 'beam', profile: 'Z200x65x20x2.0', material: 'S350GD', start: [0, 1250, 6000], end: [6000, 1250, 6000], position: 'middle', rotation: 180 });
    tx.addMember({ type: 'brace', profile: 'RD20', material: 'S275', start: [0, 0, 0], end: [6000, 0, 6000], position: 'middle' });
    tx.addMember({ type: 'brace', profile: 'L50x5', material: 'S275', start: [0, 0, 0], end: [0, 0, 900], position: 'middle' });
  });
  const b = build(m.state), mk = markParts(b);
  ok(b.problems.length === 0 && b.parts.length === 4, 'builds', b.problems);
  ok(near(b.parts[0].weight, 33.6152, 1e-3), 'Z purlin 6000: 33.615 kg', b.parts[0].weight);
  ok(mk.partMark.get(b.parts[0].id) === mk.partMark.get(b.parts[1].id), 'a Z turned 180° about its axis is the same part');
  ok(near(b.parts[2].weight, 2.46615 * Math.hypot(6000, 6000) / 1000, 1e-3), 'rod weight = kg/m × length');
  const pcs = piecesFromMarks(mk);
  ok(pcs.length === 3 && pcs.some((p) => p.profile === 'Z200x65x20x2.0' && p.count === 2), 'bar cut list: the Z ×2, the rod, the angle', pcs);
}

// ---- 4. step 3: lapped pieces with their holes (engine/tests/test_secondary_pieces.py, building 1, line RA1, by hand) --------
{
  const m = new Model(emptyState('t'));
  const piece = (x0, len, xs) => m.change('p', (tx) => {
    const id = tx.addMember({ type: 'beam', profile: 'Z200x65x20x2.0', material: 'S350GD', start: [x0, 0, 6000], end: [x0 + len, 0, 6000], position: 'bottom', rotation: 5.711 });
    for (const x of xs) for (const y of [-55, 55]) tx.addHole(id, { face: 'web', x, y, d: 14 });
    return id;
  });
  const p1 = piece(-325, 6925, [325, 5765, 6325, 6885]);
  const p2 = piece(5400, 7200, [40, 600, 1160, 6040, 6600, 7160]);
  const p3 = piece(11400, 7200, [40, 600, 1160, 6040, 6600, 7160]);
  const b = build(m.state), mk = markParts(b);
  ok(b.problems.length === 0, 'lapped pieces with holes build cleanly', b.problems);
  ok(b.byId.get(p2).holes.length === 12 && b.byId.get(p1).holes.length === 8, 'holes on the parts: 12 and 8');
  ok(mk.partMark.get(p2) === mk.partMark.get(p3) && mk.partMark.get(p1) !== mk.partMark.get(p2), 'identical interior pieces share a mark; the end piece differs');
  ok(near(b.byId.get(p2).weight, 5.60254 * 7.2, 1e-3), 'interior piece 7 200: 40.338 kg gross (holes not deducted)', b.byId.get(p2).weight);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
