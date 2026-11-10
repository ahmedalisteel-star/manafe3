#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
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

// 5. Phase 1: a built-up frame (the engine's answer for span 24 000, eave 6 000, slope 0.1 — engine/tests/test_builtup_frame.py
//    case A — written out by hand, side A of frame line 1). Plumb cuts by hand: every corner of the rafter's start face lies on
//    the column's inner face y = 824, every corner of its apex end on the ridge y = 12 000; the column top follows the roof
//    z = 6 000 + 0.1·y; the column's inner face at the eave is y = 800 + 2·12 = 824, where the rafter starts: no overlap.
{
  const { build } = await mod('build.js');
  const { toWorld } = await mod('geom.js');
  const S = (length, a, b, tw) => ({ length, hw_start: a, hw_end: b, tw, bf_top: 250, tf_top: 12, bf_bot: 250, tf_bot: 12, grade: 'S355', straight: 'top' });
  const bframe = {
    section: 'builtup', apex_height: 7200,
    grids: { x: [{ label: '1', at: 0 }], y: [{ label: 'A', at: 0 }, { label: 'B', at: 24000 }] },
    levels: [{ name: 'Ground', z: 0 }, { name: 'Eave', z: 6000 }],
    members: [
      { id: 'F1-CA', role: 'column', rotation: 270, material: 'S355', start: [0, 0, 0], end: [0, 0, 6000], section: { segments: [S(6000, 300, 800, 8)], cut_start: 0, cut_end: -0.1 } },
      { id: 'F1-RA', role: 'rafter', rotation: 0, material: 'S355', start: [0, 824, 6082.4], end: [0, 12000, 7200], section: { segments: [S(2400, 800, 400, 8), S(8831.741, 400, 400, 6)], cut_start: 0.1, cut_end: 0.1 } },
    ],
  };
  const bm = memberOf(bframe.members[1]);
  ok(bm.type === 'beam' && bm.rotation === 0 && bm.bu.segments.length === 2 && bm.bu.segments[0].hwStart === 800 && bm.bu.segments[1].tw === 6 && bm.bu.cuts.start === 0.1 && bm.bu.cuts.end === 0.1, 'engine section → bu (camelCase, cuts)', bm.bu);
  ok(memberOf(bframe.members[0]).rotation === 270, 'column rotation kept');
  const mb = new Model(emptyState('b'));
  mb.change('PEB frame', (tx) => applyFrame(tx, bframe));
  const bb = build(mb.state);
  ok(bb.problems.length === 0 && bb.parts.length === 9, 'built: column 3 parts + rafter 2 segments × 3', [bb.problems, bb.parts.length]);
  const [col, raf] = mb.state.members.map((x) => x.id);
  const corners = (id) => { const p = bb.byId.get(id); return p.profile.outline.map(([x, v]) => toWorld(p.frame, x, 0, v)); };
  const rw1 = corners(raf + '.s1.web'), rw2 = corners(raf + '.s2.web');
  const startFace = [rw1[0], rw1[3]], endFace = [rw2[1], rw2[2]];
  ok(startFace.every((p) => Math.abs(p[1] - 824) < 1e-3), 'rafter start cut plumb on the column face y = 824', startFace);
  ok(endFace.every((p) => Math.abs(p[1] - 12000) < 1e-3), 'rafter end cut plumb on the ridge y = 12000', endFace);
  ok(Math.abs(rw1[0][2] - (6082.4 - 812 * Math.sqrt(1.01))) < 1e-3, 'bottom web corner at the knee: 6082.4 − 812·√1.01 below the roof line', rw1[0]);
  const cw = corners(col + '.s1.web');
  ok([cw[1], cw[2]].every((p) => Math.abs(p[2] - (6000 + 0.1 * p[1])) < 1e-3), 'column top follows the roof line z = 6000 + 0.1·y', [cw[1], cw[2]]);
  const cbot = bb.byId.get(col + '.s1.bot');
  ok(Math.abs(cbot.end[1] - 818) < 1e-3, 'column inner flange mid-line at the eave y = 818 (face 824: the rafter starts there)', cbot.end);
  ok(bb.byId.get(raf + '.s1.web').profile.outline.every(([x]) => x >= 0), 'web outline x ≥ 0 (DSTV: the smallest x is 0)');
  // sizes in the request
  const withSizes = frameRequest({ span: '24000', eave_height: '6000', roof_slope: '0.1', bay_spacing: '6000', n_bays: '1', hw_knee: '900', hw_base: '300', hw_rafter: '450', haunch_length: '2400', bf: '250', tf: '12', grade: 'S275' });
  ok(same(withSizes.sizes, { hw_knee: 900, hw_base: 300, hw_rafter: 450, haunch_length: 2400, bf: 250, tf: 12, grade: 'S275' }), 'form sizes → request', withSizes);
  ok(throws(() => frameRequest({ span: 1, eave_height: 1, roof_slope: 0, bay_spacing: 1, n_bays: 1, hw_knee: '900' }), /must be a number above 0/), 'half-filled sizes refused');
  ok(frameRequest({ span: 1, eave_height: 1, roof_slope: 0, bay_spacing: 1, n_bays: 1, section: 'hot_rolled', hw_knee: '900' }).section === 'hot_rolled', 'hot-rolled: sizes ignored');
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
