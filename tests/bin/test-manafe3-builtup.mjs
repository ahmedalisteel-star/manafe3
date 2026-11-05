#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * Built-up members (app/manafe3/builtup.js) and their place in the model (model.js). Run by npm test.
 *
 * Hand values (mm, kg; ρ = 7850 kg/m³; straight = 'top': top flange outer face on the line, section hangs to −v):
 *   T1  L 6000, hw 300 → 800, tw 8, flanges 250×12 / 250×12
 *       levels at hw 300: top face 0, web top −12, web bottom −312, bottom face −324; at hw 800: web bottom −812, face −824
 *       web outline (0,−312) (6000,−812) (6000,−12) (0,−12); area 6000 × (300 + 800)/2 = 3 300 000 mm²
 *       web 3 300 000 × 8 = 26.4e6 mm³ → 207.24 kg; top flange 250 × 12 × 6000 → 141.30 kg
 *       bottom flange mid-line −318 → −818: length √(6000² + 500²) = 6020.797 → 250 × 12 × 6020.797 → 141.790 kg
 *       total 490.330 kg (the engine's along-the-line mass is 489.84: the sloping flange is longer than its segment)
 *   T2  L 4000, hw 800 → 400, tw 8, top 250×12, bottom 250×16
 *       web 4000 × 600 × 8 = 19.2e6 mm³ → 150.72 kg; top 250 × 12 × 4000 → 94.20 kg
 *       bottom: √(4000² + 400²) = 4019.950 → 250 × 16 × 4019.950 → 126.226 kg
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/builtup.js');
const { Model, emptyState, readModel } = await mod('model.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, tol = 1e-6) => Math.abs(a - b) <= tol;
const nearPts = (a, b, tol = 1e-6) => a.length === b.length && a.every((p, i) => near(p[0], b[i][0], tol) && near(p[1], b[i][1], tol));
const throwsMsg = (f, re) => { try { f(); return 'no throw'; } catch (e) { return re.test(e.message) ? true : e.message; } };

const seg = (o = {}) => ({ length: 6000, hwStart: 600, hwEnd: 600, tw: 6, top: { b: 200, t: 10 }, bot: { b: 200, t: 10 }, grade: 'S355', straight: 'top', ...o });
const T1 = { segments: [seg({ hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 } })] };
const T2 = { segments: [seg({ length: 4000, hwStart: 800, hwEnd: 400, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 16 } })] };

// ---- 1. geometry by hand -------------------------------------------------------------------------------------------
{
  const [p] = B.segmentPlates(T1, 6000);
  ok(nearPts(p.web.outline, [[0, -312], [6000, -812], [6000, -12], [0, -12]]), 'T1 web trapezoid', p.web.outline);
  ok(nearPts([p.top.a, p.top.c], [[0, -6], [6000, -6]]) && near(p.top.length, 6000), 'T1 top flange straight on the line', p.top);
  ok(nearPts([p.bot.a, p.bot.c], [[0, -318], [6000, -818]]) && near(p.bot.length, 6020.797, 1e-3), 'T1 bottom flange slopes', p.bot);
  ok(near(B.polygonArea(p.web.outline), 3300000), 'T1 web area');
  const [w] = B.plateWeights(T1, 6000);
  ok(near(w.web, 207.24, 1e-3) && near(w.top, 141.30, 1e-3) && near(w.bot, 141.790, 1e-3) && near(w.total, 490.330, 1e-3), 'T1 plate weights by hand', w);
  const [w2] = B.plateWeights(T2, 4000);
  ok(near(w2.web, 150.72, 1e-3) && near(w2.top, 94.20, 1e-3) && near(w2.bot, 126.226, 1e-3), 'T2 plate weights by hand', w2);
  // the other straight sides
  const [pb] = B.segmentPlates({ segments: [seg({ hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 }, straight: 'bottom' })] }, 6000);
  ok(nearPts(pb.web.outline, [[0, 12], [6000, 12], [6000, 812], [0, 312]]) && near(pb.bot.a[1], 6) && near(pb.top.c[1], 818), 'straight bottom: bottom face on the line', pb.web.outline);
  const [pc] = B.segmentPlates({ segments: [seg({ hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 }, straight: 'centre' })] }, 6000);
  ok(nearPts(pc.web.outline, [[0, -150], [6000, -400], [6000, 400], [0, 150]]) && near(pc.top.a[1], 156) && near(pc.bot.c[1], -406), 'centre: web centred, both flanges slope', pc.web.outline);
}

// ---- 2. segments, splices, minimums --------------------------------------------------------------------------------
{
  const haunch = seg({ length: 2400, hwStart: 800, hwEnd: 400, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 } });
  const rafter = seg({ length: 1, hwStart: 400, hwEnd: 400, tw: 6, top: { b: 250, t: 10 }, bot: { b: 250, t: 10 } });
  const c = B.cleanBuiltUp({ segments: [haunch, rafter] }, 12000);
  ok(c.segments[1].length === 9600, 'the last segment takes the rest of the line', c.segments[1].length);
  const ps = B.segmentPlates({ segments: [haunch, rafter] }, 12000);
  ok(ps[1].x0 === 2400 && ps[1].x1 === 12000 && nearPts([ps[0].web.outline[1], ps[0].web.outline[2]], [[2400, -412], [2400, -12]]) && nearPts([ps[1].web.outline[0], ps[1].web.outline[3]], [[2400, -410], [2400, -10]]), 'splice at 2400; equal webs (flange thickness may change)', ps.map((p) => p.web.outline));
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [haunch, { ...rafter, hwStart: 450, hwEnd: 450 }] }, 12000), /^Splice 1 \(segment 1 \| segment 2\): web depths differ \(400 \| 450 mm\)/) === true, 'unequal webs at a splice refused');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [haunch, { ...rafter, top: { b: 200, t: 10 } }] }, 12000), /top flange widths differ/) === true, 'top flange width change refused');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [haunch, { ...rafter, bot: { b: 300, t: 10 } }] }, 12000), /bottom flange widths differ/) === true, 'bottom flange width change refused');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [seg({ tw: 5 })] }, 6000), /web 5 mm is under the shop minimum 6 mm/) === true, 'web under 6 refused');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [seg({ top: { b: 200, t: 6 } })] }, 6000), /top flange 6 mm is under the shop minimum 8 mm/) === true, 'flange under 8 refused');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [seg({ grade: 'Q235' })] }, 6000), /grade Q235 is not one of/) === true, 'unknown grade refused');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [seg({ length: 7000 }), seg()] }, 6000), /add up to 7000 mm; the member is only 6000 mm/) === true, 'segments longer than the member refused');
  ok(B.cleanBuiltUp({ segments: [seg({ tw: 6, top: { b: 200, t: 8 }, bot: { b: 200, t: 8 } })] }, 6000).segments.length === 1, 'exactly the minimums is allowed');
  ok(B.buMark(T1) === 'BU 300-800x8 250x12/250x12' && B.buMark(c) === 'BU 400-800x8 250x12/250x12 +1', 'marks', [B.buMark(T1), B.buMark(c)]);
}

// ---- 3. in the model: add, undo, move an end, save and open, back to a catalog profile -------------------------------
{
  const m = new Model(emptyState('t'));
  const id = m.change('bu', (tx) => tx.addMember({ type: 'column', start: [0, 0, 0], end: [0, 0, 6000], rotation: 270, position: 'middle', material: 'S355', bu: T1 }));
  const mem = m.state.members[0];
  ok(mem.id === id && mem.profile === 'BU 300-800x8 250x12/250x12' && mem.bu.segments[0].hwEnd === 800, 'added with its profile text', mem.profile);
  m.change('longer', (tx) => tx.updateMember(id, { end: [0, 0, 7000] }));
  ok(m.state.members[0].bu.segments[0].length === 7000, 'moving the end lengthens the last segment');
  ok(throwsMsg(() => m.change('bad', (tx) => tx.updateMember(id, { bu: { segments: [seg({ tw: 5 })] } })), /shop minimum/) === true && m.state.members[0].bu.segments[0].tw === 8, 'a bad edit is refused and nothing changes');
  const back = readModel(m.toJSON());
  ok(back.warnings.length === 0 && JSON.stringify(back.state.members[0].bu) === JSON.stringify(m.state.members[0].bu), 'save and open keep the segments', back.warnings);
  m.change('plain', (tx) => tx.updateMember(id, { bu: null, profile: 'HEA300' }));
  ok(!('bu' in m.state.members[0]) && m.state.members[0].profile === 'HEA300', 'back to a catalog profile');
  m.undo(); m.undo();
  ok(m.state.members[0].bu.segments[0].length === 6000, 'undo restores the built-up member');
  const j = JSON.parse(m.toJSON());
  j.members[0].bu.segments[0].tw = 3;
  const r = readModel(JSON.stringify(j));
  ok(r.state.members.length === 0 && r.warnings.length === 1, 'a file with a bad built-up member: dropped with a warning', r.warnings);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
