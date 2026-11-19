#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * The DetailCraft 0.10 merge (user 2026-11-18): Manafe3's edits on 0.10's change-record history and shared geometries.
 *
 * 1. Undo: "PEB building…" Apply and "Design…" Apply (applyBuilding inside one model.change, as the dialogs do) are ONE
 *    undo step each; undo then redo gives back the model exactly (JSON equal, before and after). Model.replace (field
 *    fix 27): one undo step, undo gives back the previous model.
 * 2. Shared geometry (view3d.js partEntry, 0.10 PERF.36): two built-up webs (SPL) with the same name, width, depth, area
 *    and outline point count but a different taper get DIFFERENT geometries; two with a different offset (voff) too.
 *    Negative control: two identical webs share ONE geometry (the cache still works).
 */
import fs from 'node:fs';
import path from 'node:path';
import { register } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 400) : '')); } };

// ---- 1. undo steps ------------------------------------------------------------------------------------------------
{
  const B = await mod('manafe3/peb-building.js');
  const { Model, emptyState } = await mod('model.js');
  const RES = JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3/building1.json'), 'utf8'));
  const snap = (m) => JSON.stringify(m.toJSON());
  const m = new Model(emptyState('undo test'));
  const s0 = snap(m), n0 = m.undoStack.length;
  const spec = { ...B.BUILDING_DEFAULTS, name: 'B1' };
  const r = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
  const s1 = snap(m);
  ok(r && m.state.members.length > 300 && m.undoStack.length === n0 + 1, 'Building… Apply = ONE undo step', [m.undoStack.length - n0, m.state.members.length]);
  m.undo();
  ok(snap(m) === s0, 'undo after Building… Apply gives back the empty model exactly');
  m.redo();
  ok(snap(m) === s1, 'redo gives back the building exactly');
  // Design… Apply: the same building regenerated with other sizes (here: the braced-bay eave struts at C200x1.8)
  const id = (m.state.m3buildings || [])[0]?.id;
  const RES2 = JSON.parse(JSON.stringify(RES));
  let changed = 0;
  for (const x of RES2.members) if (x.role === 'eave_strut' && /0-(1|4)$/.test(String(x.id))) { x.profile = 'C200x65x20x1.8'; changed++; }
  const n1 = m.undoStack.length;
  const r2 = m.change('Design: apply sizes', (tx) => B.applyBuilding(tx, RES2, { ...spec, grids_mode: 'none' }, { grids: 'none', id }));
  const s2 = snap(m);
  ok(id && changed > 0 && r2 && m.undoStack.length === n1 + 1 && m.state.members.some((x) => x.profile === 'C200x65x20x1.8'), 'Design… Apply = ONE undo step', [id, changed, m.undoStack.length - n1]);
  m.undo();
  ok(snap(m) === s1, 'undo after Design… Apply gives back the building as it was exactly');
  m.redo();
  ok(snap(m) === s2, 'redo gives back the applied sizes exactly');
  // Model.replace (field fix 27): one step; undo brings the previous model back
  const other = new Model(emptyState('R1 site'));
  other.change('m', (tx) => tx.addMember({ type: 'beam', profile: 'IPE200', material: 'S355', start: [0, 0, 0], end: [5000, 0, 0] }));
  const n2 = m.undoStack.length, whys = [];
  m.on((w) => whys.push(w));
  m.replace('load R1', other.toJSON());
  ok(m.state.name === 'R1 site' && m.state.members.length === 1 && m.undoStack.length === n2 + 1 && whys.includes('load'), 'Model.replace = ONE undo step, panels told', [m.undoStack.length - n2, whys]);
  m.undo();
  ok(snap(m) === s2, 'undo after Model.replace gives back the previous model exactly');
}

// ---- 2. shared geometries keep tapered webs apart -------------------------------------------------------------------
{
  const VENDOR = pathToFileURL(path.join(REPO, 'public_html/assets/vendor/three/0.186.1/')).href;
  if (!fs.existsSync(fileURLToPath(VENDOR + 'three.module.js'))) {
    console.log('SKIP view3d cache test: three.js is not in the test mirror (run npm test, which fetches it)');
  } else {
    register('data:text/javascript,' + encodeURIComponent(
      `export async function resolve(s, c, n) {
         if (s === 'three') return { url: ${JSON.stringify(VENDOR + 'three.module.js')}, shortCircuit: true };
         if (s.startsWith('three/addons/')) return { url: ${JSON.stringify(VENDOR + 'addons/')} + s.slice(13), shortCircuit: true };
         return n(s, c);
       }`));
    const { View3D } = await mod('view3d.js');
    const entry = (self, p) => View3D.prototype.partEntry.call(self, p);
    // the same name, width, depth, area (3.3e6 mm²) and 4 outline points — only the taper differs
    const web = (outline, voff = 0) => ({
      profile: { kind: 'SPL', name: 'BU-W 6x800', width: 6, depth: 800, area: 3.3e6, t: 6, outline, loops: [outline] },
      length: 6000, cuts: [], endCuts: null, voff,
    });
    const A = [[0, 0], [6000, 0], [6000, 800], [0, 300]];          // 300 → 800
    const Brev = [[0, 0], [6000, 0], [6000, 300], [0, 800]];       // 800 → 300: same size, the other way
    const self = {};
    const ea = entry(self, web(A)), eb = entry(self, web(Brev)), ea2 = entry(self, web(A)), ev = entry(self, web(A, 50));
    ok(ea !== eb && ea.geo !== eb.geo, 'two webs alike in name and size but not in taper get DIFFERENT geometries');
    const za = ea.bbox, zb = eb.bbox;
    ok(Math.abs((za.max.y - za.min.y) - (zb.max.y - zb.min.y)) < 1e-6, 'same overall size (the bug the key would hide)');
    ok(ea !== ev, 'a different offset (voff) gets its own geometry');
    ok(ea2 === ea && self.geoCache.size === 3, 'negative control: two identical webs share ONE geometry', self.geoCache?.size);
  }
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
