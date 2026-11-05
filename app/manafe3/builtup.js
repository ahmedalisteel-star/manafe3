/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * builtup.js — the built-up (welded I) member: tapered or constant segments joined at splice points. DOM-free.
 * The same rules as the engine (engine/sections/builtup.py); tests: tests/bin/test-manafe3-builtup.mjs.
 *
 * A member with `bu` is built up:   member.bu = { segments: [segment, …] }
 *   segment = { length, hwStart, hwEnd, tw, top: { b, t }, bot: { b, t }, grade, straight }
 *   hw = the WEB PLATE depth (what the web is cut to); overall d = hw + top.t + bot.t (user decision 2026-11-05)
 *   only the web depth varies inside a segment, linearly; a change of plates is a new segment
 *   straight = which flange lies on the member's line: 'top' → the +v flange's outer face is on the line and the section
 *     hangs towards −v (a rafter: the roof line; a column turned so −v points into the building: its outer face);
 *     'bottom' → the −v flange's outer face is on the line; 'centre' → the web is centred on the line, both flanges slope
 *   the LAST segment's length is whatever remains of the member's line, so moving an end never breaks the member
 *   at every splice the two segments have the same web depth and the same top and bottom flange widths (user decision
 *   2026-11-05; thicknesses may change); shop minimums web 6 mm, flange 8 mm
 *
 *   cleanBuiltUp(bu, L) → cleaned copy (last length = the remainder) or throws a plain message naming the segment/splice
 *   buMark(bu) → 'BU 300-800x8 250x12/250x12' (the member's profile text)
 *   segmentPlates(bu, L) → [{ index, x0, x1, web, top, bot }] in the member's local axes (x along the line from its
 *     start, v as geom.js frame(), mm):
 *       web: { t, outline: [[x, v] ×4] }  the trapezoid in the web's plane, counter-clockwise
 *       top / bot: { b, t, a: [x, v], c: [x, v], length }  the flange's mid-thickness line from x0 to x1 (square to the
 *         member at both ends) and its length along that line
 *   plateWeights(bu, L) → per segment { web, top, bot, total } kg, gross (outline area × t × 7850; holes not deducted)
 */

export const MIN_WEB_T = 6;
export const MIN_FLANGE_T = 8;
export const GRADES = ['S275', 'S355', 'A572 Gr 50', 'St 37', 'St 44', 'St 52'];
export const STRAIGHT = ['top', 'bottom', 'centre'];
export const STEEL_DENSITY = 7850;   // kg/m³
const TOL = 1e-6;
const MAX_SEGMENTS = 20;

const fmt = (v) => String(Number(Number(v).toFixed(2)));

function plate(o, which, label) {
  const b = Number(o?.b), t = Number(o?.t);
  if (!(b > 0 && b <= 2000)) throw new Error(`${label}: ${which} flange width must be 0 to 2000 mm`);
  if (!(t > 0 && t <= 200)) throw new Error(`${label}: ${which} flange thickness must be 0 to 200 mm`);
  if (t < MIN_FLANGE_T) throw new Error(`${label}: ${which} flange ${fmt(t)} mm is under the shop minimum ${MIN_FLANGE_T} mm`);
  return { b, t };
}

/** A checked copy of a built-up section for a member line of length L (mm). Throws a plain message. */
export function cleanBuiltUp(bu, L) {
  const rows = bu?.segments;
  if (!Array.isArray(rows) || !rows.length) throw new Error('A built-up member needs at least one segment');
  if (rows.length > MAX_SEGMENTS) throw new Error(`A built-up member has at most ${MAX_SEGMENTS} segments`);
  const segs = rows.map((s, i) => {
    const label = `Segment ${i + 1}`;
    const n = (k) => Number(s?.[k]);
    const hwStart = n('hwStart'), hwEnd = n('hwEnd'), tw = n('tw');
    for (const [k, v] of [['web depth at the start', hwStart], ['web depth at the end', hwEnd]]) if (!(v > 0 && v <= 5000)) throw new Error(`${label}: ${k} must be 0 to 5000 mm`);
    if (!(tw > 0 && tw <= 100)) throw new Error(`${label}: web thickness must be 0 to 100 mm`);
    if (tw < MIN_WEB_T) throw new Error(`${label}: web ${fmt(tw)} mm is under the shop minimum ${MIN_WEB_T} mm`);
    const top = plate(s?.top, 'top', label), bot = plate(s?.bot, 'bottom', label);
    if (top.b <= tw || bot.b <= tw) throw new Error(`${label}: the flanges must be wider than the web`);
    const grade = String(s?.grade ?? 'S355');
    if (!GRADES.includes(grade)) throw new Error(`${label}: grade ${grade} is not one of ${GRADES.join(', ')}`);
    const straight = String(s?.straight ?? 'top');
    if (!STRAIGHT.includes(straight)) throw new Error(`${label}: the straight flange must be top, bottom or centre`);
    const length = n('length');
    if (i < rows.length - 1 && !(length > 0)) throw new Error(`${label}: length must be more than 0 mm`);
    return { length, hwStart, hwEnd, tw, top, bot, grade, straight };
  });
  const before = segs.slice(0, -1).reduce((a, s) => a + s.length, 0);
  const last = L - before;
  if (!(last >= 1)) throw new Error(`The segments before the last add up to ${fmt(before)} mm; the member is only ${fmt(L)} mm long`);
  segs[segs.length - 1].length = last;
  for (let i = 0; i + 1 < segs.length; i++) {
    const a = segs[i], b = segs[i + 1], where = `Splice ${i + 1} (segment ${i + 1} | segment ${i + 2})`;
    if (Math.abs(a.hwEnd - b.hwStart) > TOL) throw new Error(`${where}: web depths differ (${fmt(a.hwEnd)} | ${fmt(b.hwStart)} mm); a splice joins equal webs`);
    if (Math.abs(a.top.b - b.top.b) > TOL) throw new Error(`${where}: top flange widths differ (${fmt(a.top.b)} | ${fmt(b.top.b)} mm)`);
    if (Math.abs(a.bot.b - b.bot.b) > TOL) throw new Error(`${where}: bottom flange widths differ (${fmt(a.bot.b)} | ${fmt(b.bot.b)} mm)`);
  }
  // member end cuts: the end face is x = end + k·v (k = 0 square; a rafter's plumb cut k = the roof slope)
  const cuts = { start: Number(bu.cuts?.start ?? 0), end: Number(bu.cuts?.end ?? 0) };
  for (const e of ['start', 'end']) if (!(Math.abs(cuts[e]) <= 2)) throw new Error(`The ${e} cut must be a slope from −2 to 2 (0 = square)`);
  const s0 = segs[0], sN = segs[segs.length - 1];
  const vs = (s, hw) => Object.values(levels(s, hw));
  const reach = (s, hw, k) => Math.max(...vs(s, hw).map((v) => Math.abs(k * v)));
  if (segs.length === 1 ? reach(s0, s0.hwStart, cuts.start) + reach(s0, s0.hwEnd, cuts.end) >= s0.length
    : reach(s0, s0.hwStart, cuts.start) >= s0.length || reach(sN, sN.hwEnd, cuts.end) >= sN.length) throw new Error('The end cuts are too steep for the end segments');
  return cuts.start || cuts.end ? { segments: segs, cuts } : { segments: segs };
}

/** The member's profile text, from its first and deepest dimensions: 'BU 300-800x8 250x12/250x12' (+ ' +n' segments). */
export function buMark(bu) {
  const s = bu.segments[0];
  const lo = Math.min(...bu.segments.flatMap((x) => [x.hwStart, x.hwEnd])), hi = Math.max(...bu.segments.flatMap((x) => [x.hwStart, x.hwEnd]));
  const depth = lo === hi ? fmt(lo) : fmt(lo) + '-' + fmt(hi);
  const more = bu.segments.length > 1 ? ' +' + (bu.segments.length - 1) : '';
  return `BU ${depth}x${fmt(s.tw)} ${fmt(s.top.b)}x${fmt(s.top.t)}/${fmt(s.bot.b)}x${fmt(s.bot.t)}${more}`.slice(0, 40);
}

/** v of the top flange's outer face, the web's top and bottom edges and the bottom flange's outer face at web depth hw. */
function levels(seg, hw) {
  const tt = seg.top.t, tb = seg.bot.t;
  if (seg.straight === 'top') return { topOut: 0, webTop: -tt, webBot: -tt - hw, botOut: -tt - hw - tb };
  if (seg.straight === 'bottom') return { botOut: 0, webBot: tb, webTop: tb + hw, topOut: tb + hw + tt };
  return { webTop: hw / 2, webBot: -hw / 2, topOut: hw / 2 + tt, botOut: -hw / 2 - tb };
}

/** The plates of each segment in the member's local axes (see the header). bu: a cleanBuiltUp result. */
export function segmentPlates(bu, L) {
  const c = cleanBuiltUp(bu, L);
  const out = [];
  const n = c.segments.length, ks = c.cuts?.start || 0, ke = c.cuts?.end || 0;
  let x0 = 0;
  c.segments.forEach((s, index) => {
    const x1 = x0 + s.length;
    const at0 = (v) => (index === 0 ? x0 + ks * v : x0), at1 = (v) => (index === n - 1 ? x1 + ke * v : x1);   // member end cuts; splices square
    const a = levels(s, s.hwStart), b = levels(s, s.hwEnd);
    const flange = (o, side) => {
      const mid = (lv) => (side === 'top' ? lv.topOut - o.t / 2 : lv.botOut + o.t / 2);
      const A = [at0(mid(a)), mid(a)], C = [at1(mid(b)), mid(b)];
      return { b: o.b, t: o.t, a: A, c: C, length: Math.hypot(C[0] - A[0], C[1] - A[1]) };
    };
    out.push({
      index, x0, x1, grade: s.grade, straight: s.straight, hwStart: s.hwStart, hwEnd: s.hwEnd,
      web: { t: s.tw, outline: [[at0(a.webBot), a.webBot], [at1(b.webBot), b.webBot], [at1(b.webTop), b.webTop], [at0(a.webTop), a.webTop]] },
      top: flange(s.top, 'top'), bot: flange(s.bot, 'bot'),
    });
    x0 = x1;
  });
  return out;
}

/** Area of a polygon [[x, y], …] (shoelace, absolute). */
export function polygonArea(pts) {
  let s = 0;
  for (let i = 0; i < pts.length; i++) { const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length]; s += x1 * y2 - x2 * y1; }
  return Math.abs(s) / 2;
}

/** Gross plate weights per segment, kg (outline area × thickness × 7850; holes not deducted). */
export function plateWeights(bu, L) {
  const kg = (mm3) => mm3 * 1e-9 * STEEL_DENSITY;
  return segmentPlates(bu, L).map((p) => {
    const web = kg(polygonArea(p.web.outline) * p.web.t);
    const top = kg(p.top.b * p.top.t * p.top.length), bot = kg(p.bot.b * p.bot.t * p.bot.length);
    return { index: p.index, web, top, bot, total: web + top + bot };
  });
}
