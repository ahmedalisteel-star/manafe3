#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/** Phase 3 step 1: the "Loads…" mapping (app/manafe3/loads.js) and its place in the model. Run by npm test. */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const L = await mod('manafe3/loads.js');
const { Model, emptyState, readModel } = await mod('model.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const throwsMsg = (f, re) => { try { f(); return 'no throw'; } catch (e) { return re.test(e.message) ? true : e.message; } };

{
  const d = L.LOADS_DEFAULTS;
  ok(d.V === '' && d.exposure === '' && d.collateral === '0.10' && d.Lo === '0.96' && d.base === 'pinned' && d.roof_cladding === 'single', 'defaults: V and exposure empty (site facts); the decisions\' values', d);
  const b = L.loadsRequest({ ...d, V: '45', exposure: 'C', roof_cladding: 'sandwich' });
  ok(b.V === 45 && b.exposure === 'C' && b.Kzt === 1 && b.roof_cladding === 'sandwich' && b.roof_cladding_kpa === null && b.collateral === 0.1 && b.lrfd === true && b.asd === true, 'form → request', b);
  ok(L.loadsRequest(d).V === null && L.loadsRequest(d).exposure === null, 'empty site facts go to the engine as missing (it refuses them)');
  ok(L.loadsRequest({ ...d, asd: 'no' }).asd === false, 'ASD off');
  ok(throwsMsg(() => L.loadsRequest({ ...d, V: 'fast' }), /not a number/) === true, 'bad number refused');
}
{
  const m = new Model(emptyState('t'));
  m.change('Loads', (tx) => L.applyLoads(tx, { ...L.LOADS_DEFAULTS, V: '45', exposure: 'C' }));
  ok(m.state.m3loads.V === '45' && m.state.m3loads.exposure === 'C', 'kept in the model');
  const back = readModel(m.toJSON());
  ok(back.state.m3loads && back.state.m3loads.V === '45' && back.warnings.length === 0, 'save and open keep them');
  m.undo();
  ok(!m.state.m3loads, 'one undo step');
}
{
  const seen = [];
  const res = await L.requestLoadsCheck({ V: 45 }, async (u, init) => { seen.push(u); return { ok: true, status: 200, json: async () => ({ Kd: 0.85 }) }; });
  ok(seen[0] === 'http://127.0.0.1:8765/peb/loads/check' && res.Kd === 0.85, 'asks the engine');
  let msg = '';
  try { await L.requestLoadsCheck({}, async () => ({ ok: false, status: 422, json: async () => ({ detail: 'basic wind speed V is required' }) })); } catch (e) { msg = e.message; }
  ok(msg === 'Engine: basic wind speed V is required', 'the engine\'s refusal is shown', msg);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
