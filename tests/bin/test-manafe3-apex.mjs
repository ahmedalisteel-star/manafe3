#!/usr/bin/env node
/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * Open item 17: the apex haunch in the browser — the shop-welded apex segment as parts (BOM / NC follow the parts), the
 * Building… size fields and their defaults. Run by npm test.
 *
 * Hand values — building 1 apex rafter (engine fixture building1-apex.json, frame line 3, side A):
 *   segments (2 400, 475 → 300), (7 562.382, 300), (1 600, 300 → 450, joint shop); tw 6, flanges 200 × 10, S355,
 *   straight top, plumb cuts 0.1 at both ends; rafter line 11 562.382
 *   pieces: s1 (knee haunch) and s2 + s3 shop-welded = ONE assembly, main part m.s2.web
 *   web of the piece: ONE plate (9 162.382 ≤ 12 000): outline (9 962.382 − … ) area = 7 562.382 × 300 + the apex
 *     quadrilateral 592 875 (segmentPlates' plumb end: the end vertices at x1 + 0.1 v) = 2 268 714.6 + 592 875
 *     = 2 861 589.6 mm² × 6 × 7.85e-6 = 134.781 kg (the sum of the two webs cut separately — negative control)
 *   top flange: ONE plate 200 × 10 from x 2 400 to the plumb end at v −5: 11 562.382 − 0.5 − 2 400 = 9 161.882 mm
 *   bottom flange: TWO plates (CJP at the kink): 7 562.382 long, and from (9 962.382, −315) to (11 562.382 − 46.5, −465):
 *     √(1 553.5² + 150²) = 1 560.725 mm
 *   defaults: span 24 000 → 1 600, hw_rafter 300 → 450; span 24 750 → 16.5 → 1 700 (half up); 350 → 525 → 550
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/builtup.js');
const P = await mod('manafe3/builtup-parts.js');
const F = await mod('manafe3/peb-frame.js');
const D = await mod('manafe3/design.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, tol = 1e-3) => Math.abs(a - b) <= tol;
const throwsMsg = (f, re) => { try { f(); return 'no throw'; } catch (e) { return re.test(e.message) ? true : e.message; } };

const seg = (length, a, b, extra = {}) => ({ length, hw_start: a, hw_end: b, tw: 6, bf_top: 200, tf_top: 10, bf_bot: 200, tf_bot: 10, grade: 'S355', straight: 'top', ...extra });
const sec = (apexJoint = 'shop') => ({ segments: [seg(2400, 475, 300), seg(7562.382, 300, 300), seg(1600, 300, 450, apexJoint ? { joint: apexJoint } : {})], cut_start: 0.1, cut_end: 0.1 });
const L = 11562.382, c = Math.sqrt(1.01);
const member = (bu) => ({ id: 'm1', type: 'beam', start: [0, 495, 6049.5], end: [0, 495 + L / c, 6049.5 + 0.1 * L / c], rotation: 0, bu });

// buOf carries the joint (and only 'shop')
const bu = F.buOf(sec());
ok(bu.segments[2].joint === 'shop' && !('joint' in bu.segments[0]) && !('joint' in bu.segments[1]), 'buOf keeps joint shop on the apex segment only', bu.segments.map((s) => s.joint));

// the parts
{
  const r = P.builtUpParts(member(bu));
  const by = Object.fromEntries(r.parts.map((p) => [p.id, p]));
  ok(r.problems.length === 0, 'no problems', r.problems);
  ok(JSON.stringify(Object.keys(by)) === JSON.stringify(['m1.s1.web', 'm1.s1.top', 'm1.s1.bot', 'm1.s2.web', 'm1.s2.top', 'm1.s2.bot', 'm1.s3.bot']), 'parts: no s3 web / top (one plate each), two bottom flanges', Object.keys(by));
  const w = by['m1.s2.web'];
  ok(w.attachTo === null && w.type === 'beam' && w.segment === 2, 'the piece web is the main part of ONE assembly');
  ok(near(w.plateWeight, 134.781), 'one web plate 134.781 kg', w.plateWeight);
  ok(w.profileName === 'BUW6 300-300-450', 'web label', w.profileName);
  ok(near(by['m1.s2.top'].length, 9161.882) && by['m1.s2.top'].attachTo === 'm1.s2.web', 'one top flange plate 9 161.882', by['m1.s2.top'].length);
  ok(near(by['m1.s2.bot'].length, 7562.382) && !by['m1.s2.bot'].cjp, 'bottom flange 1: 7 562.382', by['m1.s2.bot'].length);
  const kb = by['m1.s3.bot'];
  ok(near(kb.length, 1560.725) && kb.cjp === true && kb.attachTo === 'm1.s2.web' && kb.segment === 2, 'bottom flange 2 (CJP at the kink): 1 560.725, in the piece', { L: kb.length, s: kb.segment });
  // NC (DSTV): the one web plate's contour = the piece outline (constant + taper), area 2 861 589.6 mm² by hand
  const { writeNc1, readNc1 } = await mod('nc1.js');
  const nc = readNc1(writeNc1(w, { order: 'J1', mark: 'W1', count: 1, phase: 1 }));
  const rows = nc.blocks.filter((k) => k.type === 'AK')[0].rows.map((q) => q.nums.slice(0, 2));
  const pts = rows.slice(0, -1);
  const area = Math.abs(pts.reduce((acc, [x1, y1], i) => { const [x2, y2] = pts[(i + 1) % pts.length]; return acc + x1 * y2 - x2 * y1; }, 0)) / 2;
  ok(near(area, 2861589.6, 1) && near(Math.max(...pts.map((q) => q[0])), 9161.382, 0.01) && near(Math.max(...pts.map((q) => q[1])), 450, 0.01), 'NC web contour: the piece outline (area, length 9 161.38, depth 450)', { area, pts });
  ok(r.parts.filter((p) => p.segment === 2).length === 4 && r.parts.filter((p) => p.segment === 1).length === 3, 'segment = the piece number (clash: one piece is not checked against itself)');
  // NEGATIVE CONTROL 1: the same plates as separate webs add up to the same weight
  const sep = B.segmentPlates(bu, L).slice(1).reduce((a, s) => a + B.polygonArea(s.web.outline) * 6 * 7.85e-6, 0);
  ok(near(sep, w.plateWeight), 'one web = the two webs cut separately', [sep, w.plateWeight]);
  // NEGATIVE CONTROL 2: no shop joint → three assemblies, the apex its own web and top flange (a field splice)
  const r2 = P.builtUpParts(member(F.buOf(sec(null))));
  const ids2 = r2.parts.map((p) => p.id);
  ok(ids2.includes('m1.s3.web') && ids2.includes('m1.s3.top') && r2.parts.find((p) => p.id === 'm1.s3.web').attachTo === null, 'without the joint: the apex is its own assembly', ids2);
}

// a piece longer than MAX_PLATE_LENGTH: two web plates, the second CJP-welded to the main web
{
  const long = { segments: [seg(2400, 475, 300), seg(10000, 300, 300), seg(2500, 300, 450, { joint: 'shop' })], cut_start: 0.1, cut_end: 0.1 };
  const LL = 14900, m = { id: 'm2', type: 'beam', start: [0, 0, 0], end: [0, LL / c, 0.1 * LL / c], rotation: 0, bu: F.buOf(long) };
  ok(P.MAX_PLATE_LENGTH === 12000, 'the plate length rule is 12 m (confirmed by the user 2026-11-24)');
  const r = P.builtUpParts(m), by = Object.fromEntries(r.parts.map((p) => [p.id, p]));
  ok(by['m2.s3.web'] && by['m2.s3.web'].cjp === true && by['m2.s3.web'].attachTo === 'm2.s2.web' && by['m2.s3.web'].type === 'plate', '12 500 > 12 000: two web plates, CJP', Object.keys(by));
  ok(by['m2.s2.web'].profileName === 'BUW6 300-300', 'the main web is the constant part', by['m2.s2.web'].profileName);
}

// cleanBuiltUp rules
{
  const s = (o = {}) => ({ length: 3000, hwStart: 300, hwEnd: 300, tw: 6, top: { b: 200, t: 10 }, bot: { b: 200, t: 10 }, grade: 'S355', straight: 'top', ...o });
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [s({ joint: 'shop' }), s()] }, 6000), /first segment/) === true, 'refused: shop on the first segment');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [s(), s({ joint: 'shop', top: { b: 200, t: 12 } })] }, 6000), /one top flange plate/) === true, 'refused: a shop joint with another top flange');
  ok(throwsMsg(() => B.cleanBuiltUp({ segments: [s(), s({ joint: 'bolted' })] }, 6000), /splice or shop/) === true, 'refused: an unknown joint');
  const k = B.cleanBuiltUp({ segments: [s(), s({ joint: 'shop', hwEnd: 450 })] }, 6000);
  ok(k.segments[1].joint === 'shop' && !('joint' in k.segments[0]), 'kept on save / open (cleanBuiltUp)');
  ok(!('joint' in B.cleanBuiltUp({ segments: [s(), s({ joint: 'splice' })] }, 6000).segments[1]), "'splice' is the default and not stored");
}

// the form: both fields or neither, defaults, Design… Apply carries them
{
  const base = { hw_knee: 475, hw_base: 300, hw_rafter: 300, haunch_length: 2400, bf: 200, tf: 10 };
  ok(!('hw_apex' in F.sizesOf(base)), 'apex fields empty → OFF (nothing sent)');
  const z = F.sizesOf({ ...base, apex_haunch_length: '1600', hw_apex: '450' });
  ok(z.apex_haunch_length === 1600 && z.hw_apex === 450, 'both given → sent', z);
  ok(throwsMsg(() => F.sizesOf({ ...base, apex_haunch_length: '1600' }), /both/) === true, 'one field only → refused');
  ok(throwsMsg(() => F.sizesOf({ apex_haunch_length: '1600', hw_apex: '450' }), /frame sizes/) === true, 'apex without sizes → refused (never silently dropped)');
  ok(JSON.stringify(F.apexDefaults(24000, 300)) === JSON.stringify({ apex_haunch_length: 1600, hw_apex: 450 }), 'defaults 24 m');
  ok(F.apexDefaults(20000, 300).apex_haunch_length === 1500 && F.apexDefaults(24750, 300).apex_haunch_length === 1700 && F.apexDefaults(0, 350).hw_apex === 550, 'minimum and half-up rounding (as the engine)');
  const spec = D.specWithProposal({ apex_haunch_length: 1600, hw_apex: 450 }, { sizes: { hw_rafter: 325, hw_apex: 500, apex_haunch_length: 1600 } });
  ok(spec.hw_apex === 500 && spec.hw_rafter === 325, 'Design… Apply writes hw_apex with hw_rafter', spec);
  ok(!('hw_apex' in D.specWithProposal({}, { sizes: { hw_rafter: 325 } })), 'a proposal without the apex leaves a saved project OFF');
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
