#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * DSTV NC files for built-up plates (nc1.js with shaped plates). Run by npm test.
 *
 * Hand values:
 *   T1 column web (straight top): outline (0,−312) (6000,−812) (6000,−12) (0,−12); vmin −812, vmax −12 → width 800
 *     AK rows (y = v + 812): (0, 500) (6000, 0) (6000, 800) (0, 800) and back to (0, 500); shoelace > 0: counter-clockwise
 *     header: code B, profile PL8*800, length 6000, height 800, web thickness 8, 8 × 7.85 = 62.80 kg/m², paint 2
 *   T1 bottom flange: PL12x250, length √(6000² + 500²) = 6020.80 → AK (0,0) (6020.80,0) (6020.80,250) (0,250)
 *   T2 haunch web (800 → 400, straight top, tf_top 12): outline (0,−812) (4000,−412) (4000,−12) (0,−12)
 *     → AK (0,0) (4000,400) (4000,800) (0,800)
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const { Model, emptyState } = await mod('model.js');
const { build } = await mod('build.js');
const { markParts } = await mod('marks.js');
const { writeNc1, readNc1, ncRefusal } = await mod('nc1.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const seg = (o) => ({ length: 6000, hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 }, grade: 'S355', straight: 'top', ...o });
const m = new Model(emptyState('t'));
const [c, h] = m.change('x', (tx) => [
  tx.addMember({ type: 'column', start: [0, 0, 0], end: [0, 0, 6000], rotation: 270, material: 'S355', bu: { segments: [seg()] } }),
  tx.addMember({ type: 'beam', start: [0, 0, 6000], end: [4000, 0, 6000], rotation: 0, material: 'S355', bu: { segments: [seg({ length: 4000, hwStart: 800, hwEnd: 400, bot: { b: 250, t: 16 } })] } }),
]);
const built = build(m.state);
const marks = markParts(built);
const ncOf = (id) => readNc1(writeNc1(built.byId.get(id), { order: 'J1', mark: marks.partMark.get(id), count: 1, phase: 1 }));
const ak = (nc) => nc.blocks.filter((b) => b.type === 'AK').map((b) => b.rows.map((r) => [r.face, ...r.nums.slice(0, 2)]));

{
  const web = built.byId.get(c + '.s1.web');
  ok(ncRefusal(web) === null, 'a built-up web can go to NC', ncRefusal(web));
  const nc = ncOf(c + '.s1.web');
  const H = nc.header;
  ok(H.code === 'B' && H.profile === 'PL8*800' && H.length === 6000 && H.height === 800 && H.webThickness === 8 && H.flangeWidth === 0 && Math.abs(H.kgPerM - 62.8) < 1e-9 && H.paintPerM === 2 && H.steel === 'S355', 'web header: a sheet 8 mm, 800 wide, 6000 long', H);
  const rows = ak(nc);
  ok(rows.length === 1 && same(rows[0], [['v', 0, 500], ['v', 6000, 0], ['v', 6000, 800], ['v', 0, 800], ['v', 0, 500]]), 'web contour: the trapezoid, closed', rows);
  const pts = rows[0].slice(0, -1).map((r) => [r[1], r[2]]);
  let s = 0; for (let i = 0; i < pts.length; i++) { const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length]; s += x1 * y2 - x2 * y1; }
  ok(s > 0 && s / 2 === 3300000, 'counter-clockwise (DSTV p. 13), area 3.3 m²', s / 2);
  ok(!nc.blocks.some((b) => b.type === 'BO'), 'no holes');
}
{
  const nc = ncOf(c + '.s1.bot');
  ok(nc.header.code === 'B' && nc.header.profile === 'PL12*250' && nc.header.length === 6020.8, 'sloping flange: PL12*250, 6020.80 long', nc.header);
  ok(same(ak(nc)[0], [['v', 0, 0], ['v', 6020.8, 0], ['v', 6020.8, 250], ['v', 0, 250], ['v', 0, 0]]), 'flange contour: a rectangle', ak(nc));
}
{
  const nc = ncOf(h + '.s1.web');
  ok(same(ak(nc)[0], [['v', 0, 0], ['v', 4000, 400], ['v', 4000, 800], ['v', 0, 800], ['v', 0, 0]]) && nc.header.height === 800, 'haunch web contour by hand', ak(nc));
}
{
  const refused = built.parts.filter((p) => ncRefusal(p));
  ok(refused.length === 0, 'every built-up plate goes to NC: one file per part mark', refused.map((p) => p.id));
  ok(new Set(marks.parts.map((r) => r.mark)).size === 6, 'six part marks → six NC files', marks.parts.map((r) => r.mark));
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
