#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * PEB › "Design…" data side (app/manafe3/design.js), Phase 4 step 9 — offline (a synthetic engine result on building 1's
 * members from fixtures/manafe3/building1.json):
 *   colour bands at their edges (0.5 / 0.90 / 1.00, NOT EVALUATED grey), settings cleaned (the governing code follows a
 *   single code basis), the governing row per member (main frames: the governing code), the colour map onto the model's
 *   member ids by name, the table's sort / filter / band, the proposal rows and the spec Apply hands applyBuilding, Apply
 *   as ONE undo step (undo restores the model), the request body, calc sheets carrying NOT FOR ISSUE when a flag is open.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const D = await mod('manafe3/design.js');
const B = await mod('manafe3/peb-building.js');
const { Model, emptyState, readModel } = await mod('model.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 600) : '')); } };
const throws = (f, re) => { try { f(); return false; } catch (e) { return re.test(e.message); } };
const RES = JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3/building1.json'), 'utf8'));

// ---- colours -----------------------------------------------------------------------------------------------------------
const [blue, green, orange, red, grey] = D.RATIO_BANDS.map((b) => b.color);
ok(D.ratioColor(0.49) === blue && D.ratioColor(0.5) === green && D.ratioColor(0.9) === green && D.ratioColor(0.9001) === orange
  && D.ratioColor(1.0) === orange && D.ratioColor(1.01) === red && D.ratioColor(null) === grey && D.ratioColor(undefined) === grey, 'colour bands at their edges');

// ---- settings ----------------------------------------------------------------------------------------------------------
const s0 = D.cleanSettings({});
ok(s0.code_basis === 'both' && s0.governing === 'AISC' && s0.target === 0.9 && s0.limits.sway === 100 && s0.limits.rafter_Lr === 180 && s0.limits.purlin === 150
  && s0.uplift_method === 'r_factor', 'defaults: both codes, AISC governs, 0.90, H/100, L/180, L/150, R-factor', s0);
ok(D.cleanSettings({ code_basis: 'ECP', governing: 'AISC' }).governing === 'ECP', 'a single code basis governs');
ok(throws(() => D.cleanSettings({ target: 1.2 }), /target/) && throws(() => D.cleanSettings({ code_basis: 'BS' }), /Code basis/), 'bad settings refused');

// ---- a model with building 1 and a synthetic result ------------------------------------------------------------------
const m = new Model(emptyState('t'));
const spec = { ...B.BUILDING_DEFAULTS };
const r = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
const bid = r.id;
const names = new Set(B.membersOfBuilding(m.state, bid).map((x) => x.name));
const row = (id, kind, code, ratio, extra = {}) => ({ id, kind, section: 'S', code, ratio, not_evaluated: ratio === null, governing: 'G ' + id, clause: 'cl', combo: 'c', x: 0, verified: false, flags: ['f'], ...extra });
const result = {
  settings: { code_basis: 'both', governing: 'ECP' },
  rows: [row('F3-CA', 'column', 'AISC', 0.35), row('F3-CA', 'column', 'ECP', 0.56), row('F3-RA', 'rafter', 'AISC', 0.33), row('F3-RA', 'rafter', 'ECP', 0.95),
    row('RA1-1', 'purlin', 'AISI', 0.67, { strict_ratio: 1.78, line_id: 'RA1' }), row('GA1-1', 'girt', 'AISI', null), row('NOPE', 'girt', 'AISI', 1.2)],
  calc: { 'F3-CA|ECP': { id: 'F3-CA', code: 'ECP', section: 'BU', forces: { P: 1, combo: 'c' }, checks: [{ name: 'Flexure <x>', reference: 'cl. 5.1.3', demand: 1, capacity: 2, ratio: 0.5, unit: 'kN·m' }], flags: ['DG 25'] },
    'RA1|AISI': { id: 'RA1', code: 'AISI', checks: [{ name: 'Flexure', reference: 'App. 1', demand: 1, capacity: 1.5, ratio: 0.67 }], flags: [] } },
  summary: { max_ratio: 0.95 },
};
ok(['F3-CA', 'F3-RA', 'RA1-1', 'GA1-1'].every((n) => names.has(n)), 'the synthetic ids are building 1 member names');
const gov = D.governingRows(result);
ok(gov.find((x) => x.id === 'F3-CA').code === 'ECP' && gov.find((x) => x.id === 'F3-RA').ratio === 0.95 && gov.length === 5, 'the governing code\'s row per main-frame member', gov);
const cm = D.colorMap(m.state, result, bid);
const idOf = (n) => B.membersOfBuilding(m.state, bid).find((x) => x.name === n).id;
ok(cm.get(idOf('F3-CA')) === green && cm.get(idOf('F3-RA')) === orange && cm.get(idOf('RA1-1')) === green && cm.get(idOf('GA1-1')) === grey && cm.size === 4,
  'colours onto the model members by name (an id not in the model is skipped)', [...cm.values()]);
ok(JSON.stringify(D.memberIdsOf(m.state, bid, ['F3-CA'])) === JSON.stringify([idOf('F3-CA')]), 'a row selects its model member');

// ---- table -------------------------------------------------------------------------------------------------------------
const t1 = D.tableRows(result);
ok(t1[0].id === 'GA1-1' && t1[1].id === 'NOPE' && t1[2].id === 'F3-RA', 'sorted by ratio, NOT EVALUATED first', t1.map((x) => x.id));
ok(D.tableRows(result, { filter: 'rafter' }).length === 1 && D.tableRows(result, { band: 'ne' }).length === 1 && D.tableRows(result, { band: 'over' }).length === 1, 'filter and ratio band');
ok(D.tableRows(result, { code: 'all' }).length === 7 && D.tableRows(result, { code: 'AISC' }).length === 2, 'all codes / one code');
ok(D.tableRows(result, { sort: 'id', dir: 1 })[0].id === 'F3-CA', 'sorted by member');

// ---- proposal and Apply (one undo step) -------------------------------------------------------------------------------
const proposed = { sizes: { hw_knee: 475, hw_base: 300, hw_rafter: 300, haunch_length: 2400, bf: 200, tf: 10, grade: 'S355', tw_column: 6, tw_haunch: 6, tw_rafter: 6 },
  sections: { purlin: 'Z250x65x20x1.5', eave_strut: 'C200x65x20x1.8', girt: 'Z225x65x20x1.5' }, wind_column: { hw: 325, tw: 6, bf: 150, tf: 8 }, end_rafter: null };
const pr = D.proposalRows(spec, proposed);
ok(pr.find((x) => x.field === 'hw_knee').after === 475 && pr.find((x) => x.field === 'hw_knee').before === '(span rule)' && pr.find((x) => x.field === 'purlin').after === 'Z250x65x20x1.5'
  && pr.filter((x) => x.group === 'Wind columns').length === 4 && !pr.some((x) => x.group === 'End rafters'), 'proposal rows (before → after)', pr);
const spec2 = D.specWithProposal(spec, proposed);
const body = B.buildingRequest(spec2, m.state);
ok(body.sizes.hw_knee === 475 && body.sizes.tw_rafter === 6 && body.sections.purlin === 'Z250x65x20x1.5' && body.wind_column.hw === 325 && !('end_rafter' in body), 'Apply\'s spec → the engine request', body.sizes);
ok(spec.hw_knee === undefined, 'the old spec is not touched');
const before = JSON.stringify(m.state.members.length);
const r2 = m.change('Design: apply sizes', (tx) => B.applyBuilding(tx, RES, { ...spec2, grids_mode: 'none' }, { grids: 'none', id: bid }));
ok(r2.id === bid && B.buildingsOf(m.state).find((b) => b.id === bid).spec.purlin === 'Z250x65x20x1.5' && B.buildingsOf(m.state).find((b) => b.id === bid).spec.wind_column.hw === 325, 'applied: the building keeps the proposed sizes in its spec');
m.undo();
ok(JSON.stringify(m.state.members.length) === before && B.buildingsOf(m.state).find((b) => b.id === bid).spec.purlin === 'Z200x65x20x2.0', 'ONE undo step restores the model');

// ---- request and saving the settings ---------------------------------------------------------------------------------
ok(throws(() => D.designRequest(m.state, {}), /loads/i), 'no loads → refused');
m.change('loads', (tx) => { tx.s.m3loads = { V: 45, exposure: 'C' }; tx.s.m3design = { code_basis: 'AISC', target: 0.85 }; });
const req = D.designRequest(m.state, { action: 'size' });
ok(req.action === 'size' && req.settings.code_basis === 'AISC' && req.settings.governing === 'AISC' && req.settings.target === 0.85 && req.loads.V === 45 && req.building.span === 24000, 'the request: building, loads, the project\'s settings', req.settings);
ok(readModel(m.toJSON()).state.m3design.target === 0.85, 'the design settings are saved with the model');

// ---- calc sheets -------------------------------------------------------------------------------------------------------
const html = D.calcSheetsHtml(result, ['F3-CA|ECP', 'RA1|AISI'], { project: 'P', building: 'B1', date: '2026-11-10' });
ok(html.startsWith('<!DOCTYPE html>') && (html.match(/class="sheet"/g) || []).length === 2, 'one sheet per key');
ok(html.includes('NOT FOR ISSUE — rests on unconfirmed items: DG 25') && html.includes('cl. 5.1.3') && html.includes('Flexure &lt;x&gt;'), 'NOT FOR ISSUE with the open flags; clause; text escaped');
ok(html.includes('Checks on confirmed items only'), 'a sheet with no open flag says so (still for review)');

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
