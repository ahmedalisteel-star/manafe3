#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * The built-up section editor's rules (app/manafe3/builtup-ui.js, DOM-free part) and the 3D shape of a web
 * (view3d.js partGeometry for a shaped plate). Run by npm test.
 *
 * Hand values:
 *   IPE400 (d 400, bf 180, tw 8.6, tf 13.5) → one welded segment: tf 14 (13.5 rounded), hw 400 − 2·14 = 372, tw 9, b 180
 *   T1 (6000, hw 300 → 800, tw 8, 250×12) split at its middle: 3000 300 → 550 and 3000 550 → 800; the total weight stays
 *   490.330 kg (the web's two trapezoids add up to the one; the sloping flange's two halves to its length)
 */
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const U = await mod('manafe3/builtup-ui.js');
const B = await mod('manafe3/builtup.js');
const { getProfile } = await mod('profiles.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x) : '')); } };
const near = (a, b, tol = 1e-3) => Math.abs(a - b) <= tol;
const throwsMsg = (f, re) => { try { f(); return 'no throw'; } catch (e) { return re.test(e.message) ? true : e.message; } };
const total = (bu, L) => B.plateWeights(bu, L).reduce((a, w) => a + w.total, 0);

const seg = (o) => ({ length: 6000, hwStart: 300, hwEnd: 800, tw: 8, top: { b: 250, t: 12 }, bot: { b: 250, t: 12 }, grade: 'S355', straight: 'top', ...o });
const T1 = { segments: [seg()] };

{
  const b = U.builtUpFrom(getProfile('IPE400'));
  const s = b.segments[0];
  ok(s.hwStart === 372 && s.hwEnd === 372 && s.tw === 9 && s.top.b === 180 && s.top.t === 14 && s.bot.t === 14 && s.straight === 'centre', 'IPE400 → welded segment', s);
  ok(B.cleanBuiltUp(b, 5000).segments[0].length === 5000, 'it fits any member length');
  const plain = U.builtUpFrom(getProfile('HSS6X6X1/4'));
  ok(plain.segments[0].hwStart === 380 && plain.segments[0].tw === 6, 'a non-I profile → a 400-deep starting section', plain.segments[0]);
}
{
  const two = U.addSegment(T1, 6000);
  ok(two.segments.length === 2 && two.segments[0].length === 3000 && two.segments[0].hwEnd === 550 && two.segments[1].hwStart === 550, 'add segment splits the last at its middle', two.segments);
  ok(near(total(two, 6000), 490.330) && near(total(T1, 6000), 490.330), 'splitting does not change the weight', total(two, 6000));
  const e1 = U.setField(two, 0, 'hwEnd', 600);
  ok(e1.segments[0].hwEnd === 600 && e1.segments[1].hwStart === 600 && B.cleanBuiltUp(e1, 6000), 'a web depth at a splice moves both sides', e1.segments.map((s) => [s.hwStart, s.hwEnd]));
  const e2 = U.setField(two, 1, 'hwStart', 500);
  ok(e2.segments[0].hwEnd === 500, 'and from the other side');
  const e3 = U.setField(two, 1, 'top.b', 300);
  ok(e3.segments.every((s) => s.top.b === 300) && B.cleanBuiltUp(e3, 6000), 'a flange width is the whole member\'s');
  const e4 = U.setField(two, 1, 'top.t', 16);
  ok(e4.segments[0].top.t === 12 && e4.segments[1].top.t === 16 && B.cleanBuiltUp(e4, 6000), 'a thickness is per segment');
  ok(two.segments[0].hwEnd === 550, 'edits never change the original (copies)');
  ok(throwsMsg(() => B.cleanBuiltUp(U.setField(two, 0, 'tw', 4), 6000), /shop minimum 6/) === true, 'an edit under the minimum is caught by the check');
  const back = U.removeSegment(two, 1, 6000);
  ok(back.segments.length === 1 && back.segments[0].hwStart === 300 && back.segments[0].hwEnd === 800, 'remove segment merges it back', back.segments);
  const three = U.addSegment(U.addSegment(T1, 6000), 6000);
  const mid = U.removeSegment(three, 1, 6000);
  ok(mid.segments.length === 2 && mid.segments[0].length === 4500 && mid.segments[0].hwEnd === 675 && mid.segments[1].hwStart === 675, 'removing a middle segment: the one before takes it over', mid.segments.map((s) => [s.length, s.hwStart, s.hwEnd]));
  ok(throwsMsg(() => U.removeSegment(T1, 0, 6000), /at least one segment/) === true, 'the last segment stays');
  const rows = U.segmentRows(two, 6000);
  ok(rows[0].dStart === 324 && rows[0].dEnd === 574 && rows[1].x0 === 3000 && rows[1].dEnd === 824, 'panel rows: x range and overall depth', rows);
  ok(throwsMsg(() => U.setField(two, 5, 'tw', 8), /No segment 6/) === true && throwsMsg(() => U.setField(two, 0, 'xx', 8), /Unknown field/) === true, 'bad edits refused');
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
