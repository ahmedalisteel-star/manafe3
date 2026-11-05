#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/** The "PEB frame…" button's data mapping (app/manafe3/peb-frame.js) into a real DetailCraft Model. Run by npm test. */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const { Model, emptyState } = await mod('model.js');
const { frameRequest, memberOf, applyFrame, requestFrame } = await mod('manafe3/peb-frame.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const throws = (f, re) => { try { f(); return false; } catch (e) { return re.test(e.message); } };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// 1. form → request body
const body = frameRequest({ span: '20000', eave_height: '6000', roof_slope: '0.1', bay_spacing: '6000', n_bays: '2' });
ok(same(body, { span: 20000, eave_height: 6000, roof_slope: 0.1, bay_spacing: 6000, n_bays: 2 }), 'form strings → numbers', body);
ok(throws(() => frameRequest({ span: 'abc', eave_height: 1, roof_slope: 0, bay_spacing: 1, n_bays: 1 }), /Span is not a number/), 'a bad number → a plain message');
ok(throws(() => frameRequest({ span: 1, eave_height: 1, roof_slope: 0, bay_spacing: 1, n_bays: 2.5 }), /whole number/), 'bays must be whole');

// 2. engine member → DetailCraft member (the engine's answer for case 1, frame line 2, written out by hand)
const frame = {
  apex_height: 7000,
  grids: { x: [{ label: '1', at: 0 }, { label: '2', at: 6000 }, { label: '3', at: 12000 }], y: [{ label: 'A', at: 0 }, { label: 'B', at: 20000 }] },
  levels: [{ name: 'Ground', z: 0 }, { name: 'Eave', z: 6000 }],
  members: [
    { id: 'F2-CA', role: 'column', profile: 'HEA400', material: 'S355', start: [6000, 0, 0], end: [6000, 0, 6000] },
    { id: 'F2-CB', role: 'column', profile: 'HEA400', material: 'S355', start: [6000, 20000, 0], end: [6000, 20000, 6000] },
    { id: 'F2-RA', role: 'rafter', profile: 'IPE500', material: 'S355', start: [6000, 0, 6000], end: [6000, 10000, 7000] },
    { id: 'F2-RB', role: 'rafter', profile: 'IPE500', material: 'S355', start: [6000, 20000, 6000], end: [6000, 10000, 7000] },
  ],
};
const col = memberOf(frame.members[0]), raf = memberOf(frame.members[2]);
ok(col.type === 'column' && raf.type === 'beam', 'column → column, rafter → beam', [col.type, raf.type]);
ok(same(raf.start, [6000, 0, 6000]) && same(raf.end, [6000, 10000, 7000]), 'points copied, axes not swapped', raf);
ok(col.profile === 'HEA400' && raf.profile === 'IPE500' && raf.material === 'S355' && raf.position === 'middle' && raf.name === 'F2-RA', 'profile, material, work line, name', raf);
ok(throws(() => memberOf({ role: 'purlin', start: [0, 0, 0], end: [1, 0, 0] }), /Unknown member role/), 'an unknown role is refused');

// 3. into a real Model, one undo step
const m = new Model(emptyState('t'));
const ids = m.change('PEB frame', (tx) => applyFrame(tx, frame));
const s = m.state;
ok(Array.isArray(ids) && ids.length === 4 && s.members.length === 4, 'four members added', ids);
ok(s.members.filter((x) => x.type === 'column').length === 2 && s.members.filter((x) => x.type === 'beam').length === 2, 'two columns, two rafters');
ok(same(s.grids.x.map((g) => g.at), [0, 6000, 12000]) && same(s.grids.y.map((g) => g.label), ['A', 'B']), 'grids from the frame', s.grids);
ok(same(s.levels.map((l) => l.z), [0, 6000]), 'levels ground and eave', s.levels);
ok(same(s.members.find((x) => x.name === 'F2-RB').end, [6000, 10000, 7000]), 'the B rafter ends at the apex');
ok(m.undoStack.length === 1, 'one undo step');
m.undo();
ok(m.state.members.length === 0, 'undo removes the whole frame');
ok(throws(() => m.change('x', (tx) => applyFrame(tx, { members: [] })), /no members/), 'an empty answer is refused');

// 4. the HTTP call, with a stand-in fetch
const seen = [];
const fakeOk = async (url, init) => { seen.push([url, JSON.parse(init.body)]); return { ok: true, status: 200, json: async () => frame }; };
const got = await requestFrame(body, fakeOk);
ok(seen[0][0] === 'http://127.0.0.1:8765/peb/frame' && same(seen[0][1], body) && got === frame, 'POSTs the body to the engine', seen);
let msg = '';
try { await requestFrame(body, async () => { throw new TypeError('Failed to fetch'); }); } catch (e) { msg = e.message; }
ok(/not running.*python manafe3\.py/.test(msg), 'engine down → says how to start it', msg);
try { await requestFrame(body, async () => ({ ok: false, status: 422, json: async () => ({ detail: 'number of bays must be 1 to 59' }) })); } catch (e) { msg = e.message; }
ok(msg === 'Engine: number of bays must be 1 to 59', 'engine refusal → its message', msg);

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
