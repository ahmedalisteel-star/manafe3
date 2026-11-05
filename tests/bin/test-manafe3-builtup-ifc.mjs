#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * IFC4 out and back in for built-up members (ifc.js + ifc-import.js), read by cc-ifc as the upstream tests do.
 *
 * Model: column T1 at (0,0) rotation 270 (web 300 → 800, flanges 250×12), a two-segment rafter (haunch 2400 800 → 400 +
 * rafter 400), and one plain IPE400 beam (other imports must not change).
 * Expected in the file: 3 segments → 3 IfcElementAssembly with Manafe3_BuiltUp, 3 IfcArbitraryClosedProfileDef (webs),
 * 9 IfcPlate (3 per segment), 1 IfcBeam (the IPE).
 * Column web mesh (hand): x ∈ [−4, 4] (8 thick), depth 12 → 312 at the base and 12 → 812 at the top, height 0 → 6000.
 * Back in: the same members (type, line, rotation, segments) and the plain beam as before; no plates left over.
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const { Model, emptyState } = await mod('model.js');
const { build } = await mod('build.js');
const { markParts } = await mod('marks.js');
const { writeIfc } = await mod('ifc.js');
const { importIfc } = await mod('ifc-import.js');
const Rb = await mod('rebar.js');
const { W, api } = await (await import(pathToFileURL(path.join(REPO, 'tools/detailcraft-test/webifc-node.mjs')).href)).loadCcIfc(APP);
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, tol = 0.01) => Math.abs(a - b) <= tol;
const count = (txt, re) => (txt.match(re) || []).length;

const seg = (o) => ({ length: 6000, hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 }, grade: 'S355', straight: 'top', ...o });
const COL = { segments: [seg()] };
const RAF = { segments: [seg({ length: 2400, hwStart: 800, hwEnd: 400 }), seg({ length: 1, hwStart: 400, hwEnd: 400, tw: 6, top: { b: 250, t: 10 }, bot: { b: 250, t: 10 } })] };
const m = new Model(emptyState('ifc-bu'));
m.change('x', (tx) => {
  tx.addMember({ type: 'column', start: [0, 0, 0], end: [0, 0, 6000], rotation: 270, material: 'S355', bu: COL, name: 'CA' });
  tx.addMember({ type: 'beam', start: [0, 0, 6000], end: [0, 12000, 7200], rotation: 0, material: 'S355', bu: RAF, name: 'RA' });
  tx.addMember({ type: 'beam', start: [6000, 0, 3000], end: [6000, 6000, 3000], profile: 'IPE400', material: 'S355', position: 'top', name: 'B1' });
});
const built = build(m.state);
const marks = Object.assign(markParts(built), { footingMark: new Map() });
const txt = writeIfc(m.state, built, marks, Rb.bendingSchedule([]), { now: new Date('2026-11-05T00:00:00Z') });

// ---- 1. the file ----------------------------------------------------------------------------------------------------
ok(count(txt, /IFCELEMENTASSEMBLY\(/g) === 3, 'one assembly per segment', count(txt, /IFCELEMENTASSEMBLY\(/g));
ok(count(txt, /'Manafe3_BuiltUp'/g) === 3, 'each carries Manafe3_BuiltUp');
ok(count(txt, /IFCARBITRARYCLOSEDPROFILEDEF\(/g) === 3 && count(txt, /IFCPLATE\(/g) === 9 && count(txt, /IFCBEAM\(/g) === 1, 'webs as arbitrary profiles, 9 plates, the plain beam');
ok(count(txt, /'DetailCraft',\$,\(/g) === built.parts.length, 'every part keeps its part property set', [count(txt, /'DetailCraft',\$,\(/g), built.parts.length]);

// ---- 2. read by cc-ifc: the column web where it belongs -------------------------------------------------------------------
{
  const mid = api.OpenModel(new TextEncoder().encode(txt));
  const ids = (type) => { const v = api.GetLineIDsWithType(mid, type), o = []; for (let i = 0; i < v.size(); i++) o.push(v.get(i)); return o; };
  const val = (x) => (x && typeof x === 'object' && 'value' in x ? x.value : x);
  const webMark = marks.partMark.get(built.parts.find((p) => p.member === m.state.members[0].id && p.profile.kind === 'SPL').id);
  const webId = ids(W.IFCPLATE).find((i) => val(api.GetLine(mid, i).Tag) === webMark);
  const meshes = new Map();
  api.StreamAllMeshes(mid, (mesh) => {
    const pts = [];
    for (let i = 0; i < mesh.geometries.size(); i++) {
      const pg = mesh.geometries.get(i), geo = api.GetGeometry(mid, pg.geometryExpressID);
      const v = api.GetVertexArray(geo.GetVertexData(), geo.GetVertexDataSize()), mx = pg.flatTransformation;
      for (let k = 0; k < v.length; k += 6) { const x = v[k], y = v[k + 1], z = v[k + 2]; pts.push([mx[0] * x + mx[4] * y + mx[8] * z + mx[12], mx[1] * x + mx[5] * y + mx[9] * z + mx[13], mx[2] * x + mx[6] * y + mx[10] * z + mx[14]]); }
      geo.delete?.();
    }
    meshes.set(mesh.expressID, pts);
  });
  const pts = meshes.get(webId) || [];
  ok(pts.length > 0, 'cc-ifc made the web\'s geometry', pts.length);
  if (pts.length) {
    const ext = (a) => Math.max(...pts.map((p) => p[a])) - Math.min(...pts.map((p) => p[a]));
    const exts = [0, 1, 2].map(ext);
    const scale = Math.max(...exts) / 6000;
    const order = [0, 1, 2].sort((a, b) => exts[a] - exts[b]);
    const [tA, dA, hA] = order;
    ok(near(exts[tA] / scale, 8) && near(exts[dA] / scale, 800) && near(exts[hA] / scale, 6000), 'web box 8 × 800 × 6000', exts.map((e) => e / scale));
    const H = (p) => p[hA] / scale, D = (p) => Math.abs(p[dA] / scale);
    const hMin = Math.min(...pts.map(H)), hMax = Math.max(...pts.map(H));
    const at = (h) => pts.filter((p) => near(H(p), h, 0.5)).map(D);
    const lo = at(hMin), hi = at(hMax);
    ok(near(Math.min(...lo), 12) && near(Math.max(...lo), 312) && near(Math.min(...hi), 12) && near(Math.max(...hi), 812), 'tapered the right way: 12–312 at the base, 12–812 at the top', [Math.min(...lo), Math.max(...lo), Math.min(...hi), Math.max(...hi)]);
    ok(near(Math.min(...pts.map((p) => p[tA] / scale)), -4) && near(Math.max(...pts.map((p) => p[tA] / scale)), 4), 'through the thickness: centred on the column line', [Math.min(...pts.map((p) => p[tA] / scale)), Math.max(...pts.map((p) => p[tA] / scale))]);
  }
  api.CloseModel(mid);
}

// ---- 3. back in -------------------------------------------------------------------------------------------------------------
{
  const { state, report } = await importIfc(W, api, new TextEncoder().encode(txt));
  const bu = state.members.filter((x) => x.bu), plain = state.members.filter((x) => !x.bu);
  ok(bu.length === 2 && plain.length === 1, 'two built-up members and the plain beam come back; no loose plates', state.members.map((x) => [x.type, x.profile]));
  const strip = (x) => JSON.stringify({ type: x.type, name: x.name, start: x.start, end: x.end, rotation: x.rotation, bu: x.bu });
  const before = m.state.members.filter((x) => x.bu).map(strip).sort(), after = bu.map(strip).sort();
  ok(JSON.stringify(before) === JSON.stringify(after), 'built-up members exactly as written', { before, after });
  ok(plain[0].profile === 'IPE400' && plain[0].type === 'beam', 'the plain beam as before', plain[0]);
  ok(report.converted['Manafe3 built-up member'] === 2, 'the report counts them', report.converted);
  ok(!report.notConverted.some((n) => /IfcElementAssembly|IfcPlate/.test(n.cls)), 'no assembly or plate reported as left out', report.notConverted);
  const b2 = build(state), mk2 = markParts(b2);
  ok(b2.parts.length === built.parts.length && Math.abs(b2.parts.reduce((s, p) => s + p.weight, 0) - built.parts.reduce((s, p) => s + p.weight, 0)) < 1e-6 && mk2.parts.length === marks.parts.length, 'rebuilt: same parts, weight and marks');
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
