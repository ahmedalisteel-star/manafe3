#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * "PEB building…" mapping (app/manafe3/peb-building.js) with the engine's real answer for building 1 + a door
 * (fixtures/manafe3/building1.json, made by engine/peb/building.py; engine tests check its geometry by hand).
 *
 * Hand counts: 370 members (364 + the door: 3 girt rows each cut into one more piece, 2 jambs, 1 header) and 196 cleats
 * (150 on frames + 46 gable-girt cleats on the wind / corner columns).
 * Parts: main frames 5 × (2 columns × 3 + 2 rafters × 2 segments × 3) = 90; wind columns 6 × 3 = 18; the other
 * 370 − 20 − 6 = 344 members one part each (incl. 6 cap plates); 196 cleats → 90 + 18 + 344 + 196 = 648 parts.
 * Wind column WF1 (y 6 000, top 6 163.835): flanges 150×8 cut across along the roof (0.1): a trapezoid, x 0 → L ∓ 7.5 at
 * w = ∓75; area = 150 × 6 163.835 → 150 × 6 163.835 × 8 × 7.85e-6 = 58.063 kg.
 * A girt cleat (wall A): PL8x100 from (x, 0, z + 5) to (x, −180, z + 5), its width along X → its section u = ±X.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/peb-building.js');
const { Model, emptyState, readModel } = await mod('model.js');
const { build } = await mod('build.js');
const { markParts } = await mod('marks.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 600) : '')); } };
const throwsMsg = (f, re) => { try { f(); return 'no throw'; } catch (e) { return re.test(e.message) ? true : e.message; } };
const RES = JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3/building1.json'), 'utf8'));

// ---- 1. the form → request ------------------------------------------------------------------------------------------
{
  const f = Object.fromEntries(Object.entries(B.BUILDING_DEFAULTS).map(([k, v]) => [k, String(v)]));
  const body = B.buildingRequest({ ...f, braced_bays: '1, 4', lap: '500', openings: 'A 7000 4000 0 4000\nfirst 9000 6000 0 4500' });
  ok(body.span === 24000 && body.n_bays === 4 && body.roof_a.spacing === 1250 && body.roof_b.apex_gap === 200 && body.wall_a.first === 1250, 'numbers', body);
  ok(JSON.stringify(body.braced_bays) === '[1,4]' && body.fixed_lap === 500 && body.bolt === 'M12' && body.end_first === 'frame', 'bays, lap, bolt, end walls');
  ok(body.openings.length === 2 && body.openings[1].wall === 'first' && body.openings[0].height === 4000, 'openings parsed', body.openings);
  ok(B.buildingRequest(f).braced_bays === null && B.buildingRequest(f).fixed_lap === null && !('sizes' in B.buildingRequest(f)), 'empty fields → the engine\'s defaults');
  ok(throwsMsg(() => B.parseOpenings('C 1 2 3 4'), /Opening line 1/) === true && throwsMsg(() => B.parseBays('1, x'), /Braced bays/) === true, 'bad text refused');
}

// ---- 2. the engine's building into a model ---------------------------------------------------------------------------
const m = new Model(emptyState('t'));
const mine = m.change('mine', (tx) => tx.addMember({ type: 'beam', profile: 'IPE300', material: 'S355', start: [0, -3000, 3000], end: [6000, -3000, 3000] }));
const spec = { ...B.BUILDING_DEFAULTS, openings: 'A 7000 4000 0 4000' };
const r = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
ok(r.members === 370 && r.cleats === 196 && r.replaced === 0, 'members and cleats added', r);
const b = build(m.state);
ok(b.problems.length === 0, 'the whole building builds without problems', b.problems.slice(0, 5));
ok(b.parts.length === 648 + 1, '648 parts by hand (+ my own beam)', b.parts.length);
{
  const gc = m.state.members.find((x) => x.name === 'Cleat GA1' && x.start[0] === 6000);
  const part = b.byId.get(gc.id);
  ok(Math.abs(Math.abs(part.frame.u[0]) - 1) < 1e-9 && part.length === 180 && part.holes.length === 2, 'girt cleat: width along X, 180 long, 2 holes', { u: part.frame.u, L: part.length });
  const pieces = m.state.members.filter((x) => x.name === 'RA1-2');
  ok(pieces.length === 1 && pieces[0].holes.length === 14, 'purlin piece 5 400 → 12 600: 12 frame/lap holes + 2 sag-rod holes (row 9 000: x 8 960, 9 040)', pieces[0]?.holes.length);
  const mk = markParts(b);
  ok(mk.parts.length > 20 && mk.assemblies.length > 5, 'marks made', [mk.parts.length, mk.assemblies.length]);
}

// ---- 3. edit = replace the generated members only; save and open keep everything ----------------------------------------
{
  const r2 = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
  ok(r2.replaced === 370 + 196 && m.state.members.length === 370 + 196 + 1 && m.state.members.some((x) => x.id === mine), 'regenerating replaces the generated members, mine stays', r2);
  const back = readModel(m.toJSON());
  ok(back.warnings.length === 0 && back.state.members.length === 567 && back.state.members.filter((x) => x.gen === 'peb').length === 566, 'save / open keep the members and their gen tag', back.warnings);
  ok(back.state.m3building && back.state.m3building.openings === 'A 7000 4000 0 4000', 'the building inputs are kept for "Edit building"');
  m.undo();
  ok(m.state.members.length === 567, 'one undo step per building edit');
}
{
  const wc = m.state.members.find((x) => x.name === 'WF1');
  const f = build(m.state).byId.get(wc.id + '.s1.top');
  const o = f.profile.outline, L = 6163.835;
  ok(f.profile.kind === 'SPL' && Math.abs(o[1][0] - (L - 7.5)) < 1e-3 && Math.abs(o[2][0] - (L + 7.5)) < 1e-3 && o[0][1] === -75 && o[2][1] === 75, 'wind column flange: a trapezoid cut along the roof', o);
  ok(Math.abs(f.weight - 58.063) < 1e-3, 'its weight by hand 58.063 kg', f.weight);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
