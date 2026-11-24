/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * builtup-parts.js — a built-up member's parts, for build.js. DOM-free.
 *
 *   builtUpParts(m) → { parts, problems }   m: a stored member with m.bu (model.js has checked it)
 *
 * Each segment is one shipping assembly of three parts:
 *   web     id <member>.s<n>.web   type = the member's (column | beam), the assembly's MAIN part
 *           profile kind 'SPL' (shaped plate): the trapezoid `outline` [[x, v] …] in the web's own plane, x from the segment
 *           start, v as the member's frame; thickness t across (u). Its `loops` / width / depth are the bounding box, so code
 *           that only knows prisms still gets a sensible box; view3d, NC and IFC draw the outline (Phase 1 steps 4–6).
 *   flanges id <member>.s<n>.top / .bot   type 'plate', profile PL<t>x<b> along the flange's mid-thickness line, width across
 *           the member (u). A sloping flange is cut square to the MEMBER at a splice: its ends are skewed through the plate's
 *           thickness by the taper angle (in its own plane it stays a rectangle b × length); that skew is not cut in NC.
 * All three carry member = the stored member's id (picking any part selects the member) and segment = n.
 * SHOP JOINTS (open item 17, user decision 2026-11-24 D1 — the apex haunch): a segment with joint 'shop' is shop-welded
 * to the one before it — together ONE shipping assembly (segment = the first segment's n on every part, the web of the
 * first segment its main part):
 *   web     ONE shaped plate over the joined segments (constant + taper outline) when they have the same web thickness and
 *           grade and the plate is no longer than MAX_PLATE_LENGTH; otherwise a plate per segment, each joined to the
 *           main web by a CJP butt weld (`cjp: true`, attached to the main web)
 *   flanges one plate across a joint where the flange runs straight on with the same plate (the straight top flange);
 *           where it turns (the bottom flange at the apex kink) a plate per segment with a CJP weld at the kink
 *           (`<member>.s<n>.bot`, `cjp: true`). BOM, NC and IFC follow these parts.
 * Weights are gross: outline area × thickness × 7850 kg/m³ (holes not deducted), as plateWeights in builtup.js.
 * Holes, copes and connections on built-up members come in later phases: they are reported, not built.
 */
import { frame, add, mul, dot } from '../geom.js';
import { getProfile, plateName } from '../profiles.js';
import { segmentPlates, polygonArea, STEEL_DENSITY } from './builtup.js';

const ROLE = { column: 'Column web', beam: 'Rafter web', brace: 'Brace web', plate: 'Web' };
/** The longest web plate cut in one piece across a shop joint, mm (open item 17; confirmed by the user 2026-11-24 —
 *  the same 12 m as the transport rule). */
export const MAX_PLATE_LENGTH = 12000;
const TOLJ = 1e-6;
const r3 = (v) => Math.round(v * 1000) / 1000;

/** The rotation (deg) that makes geom.js frame(a, c, rotation) have the wanted u (u ⟂ the line a→c). */
export function rotationFor(a, c, u) {
  const f0 = frame(a, c, 0);
  const deg = Math.atan2(dot(u, f0.v), dot(u, f0.u)) * 180 / Math.PI;
  return r3(((deg % 360) + 360) % 360);
}

/** The web's pseudo-profile: a shaped plate. Outline points relative to the segment start. */
export function shapedPlateProfile(t, outline, label) {
  const vs = outline.map((p) => p[1]);
  const vmin = Math.min(...vs), vmax = Math.max(...vs), h = vmax - vmin;
  const area = polygonArea(outline);
  const L = Math.max(...outline.map((p) => p[0])) - Math.min(...outline.map((p) => p[0]));
  return Object.freeze({
    name: label, kind: 'SPL', family: 'SPL', source: 'param', t, outline, vmin, vmax, label,
    loops: [[[-t / 2, -h / 2], [t / 2, -h / 2], [t / 2, h / 2], [-t / 2, h / 2]]], width: t, depth: h,
    outlineArea: area,                                         // mm², the plate's face
    area: t * area / L,                                        // mm², the average cross-section along the segment
    mass: area * t * 1e-9 * STEEL_DENSITY / (L / 1000),        // kg/m along the segment, so mass × length = the plate's weight
    massFrom: 'Outline area × t × ' + STEEL_DENSITY + ' kg/m³',
  });
}

/**
 * The section at a built-up member's END (field fixes 9, 10): { point (world, the section's centre), profile (an I with
 * that end's depth, flanges and web: kind 'I', d, bf, tw, tf, depth, width, perimeter, loops), frame } — what the base
 * plate generator and the footing placer need. The flanges: the wider / thicker of the two (a base plate covers both).
 */
export function builtUpEndSection(m, end = 'start') {
  const F = frame(m.start, m.end, m.rotation);
  const segs = segmentPlates(m.bu, F.len);
  const s = end === 'start' ? segs[0] : segs[segs.length - 1];
  const vTop = end === 'start' ? s.top.a[1] + s.top.t / 2 : s.top.c[1] + s.top.t / 2;
  const vBot = end === 'start' ? s.bot.a[1] - s.bot.t / 2 : s.bot.c[1] - s.bot.t / 2;
  const x = end === 'start' ? 0 : F.len;
  const vc = (vTop + vBot) / 2, d = vTop - vBot;
  const bf = Math.max(s.top.b, s.bot.b), tf = Math.max(s.top.t, s.bot.t), tw = s.web.t;
  const loops = [[[-bf / 2, -d / 2], [bf / 2, -d / 2], [bf / 2, -d / 2 + tf], [tw / 2, -d / 2 + tf], [tw / 2, d / 2 - tf], [bf / 2, d / 2 - tf], [bf / 2, d / 2],
    [-bf / 2, d / 2], [-bf / 2, d / 2 - tf], [-tw / 2, d / 2 - tf], [-tw / 2, -d / 2 + tf], [-bf / 2, -d / 2 + tf]]];
  const profile = { name: `BU ${r3(d)}x${r3(bf)}`, kind: 'I', family: 'BU', source: 'param', d, bf, tw, tf, r: 0, depth: d, width: bf,
    perimeter: 4 * bf + 2 * d - 2 * tw, loops, area: 2 * bf * tf + (d - 2 * tf) * tw };
  return { point: add(add(F.o, mul(F.x, x)), mul(F.v, vc)), profile, frame: F, vc };
}

export function builtUpParts(m) {
  const problems = [];
  const F = frame(m.start, m.end, m.rotation);
  const world = (x, v) => add(add(F.o, mul(F.x, x)), mul(F.v, v));
  const parts = [];
  if (m.holes?.length) problems.push({ ref: m.id, text: 'Holes on a built-up member are not built yet (Phase 5): ' + m.holes.length + ' left out.' });
  if (m.cuts?.length) problems.push({ ref: m.id, text: 'Copes on a built-up member are not built yet: ' + m.cuts.length + ' left out.' });
  const rows = segmentPlates(m.bu, F.len);
  const groups = [];   // shipping pieces: a segment and the shop-joined segments after it (open item 17)
  for (const r of rows) { if (r.joint === 'shop' && groups.length) groups[groups.length - 1].push(r); else groups.push([r]); }
  for (const g of groups) {
    const n = g[0].index + 1, base = m.id + '.s' + n;
    const common = { member: m.id, conn: null, segment: n, material: g[0].grade, phase: m.phase || 1, holes: [], cuts: [], setback: { start: 0, end: 0 }, endCuts: null, builtUp: true };
    // webs: one shaped plate over the piece, or one per segment (CJP butt welds) — see the header
    const oneWeb = g.every((r) => Math.abs(r.web.t - g[0].web.t) < TOLJ && r.grade === g[0].grade) && (g[g.length - 1].x1 - g[0].x0) <= MAX_PLATE_LENGTH + TOLJ;
    const webs = oneWeb && g.length > 1
      ? [{ r: g[0], n, t: g[0].web.t, grade: g[0].grade, hw: [g[0].hwStart, ...g.map((r) => r.hwEnd)],
        outline: [...g.map((r) => r.web.outline[0]), g[g.length - 1].web.outline[1], g[g.length - 1].web.outline[2], ...g.slice().reverse().map((r) => r.web.outline[3])] }]
      : g.map((r) => ({ r, n: r.index + 1, t: r.web.t, grade: r.grade, hw: [r.hwStart, r.hwEnd], outline: r.web.outline }));
    webs.forEach((w, k) => {
      // the web part runs from its outline's smallest x (a plumb end cut reaches behind the segment start) to its largest
      const xs = w.outline.map((q) => q[0]), xa = Math.min(...xs), L = Math.max(...xs) - xa;
      const local = w.outline.map(([x, v]) => [r3(x - xa), r3(v)]);
      const prof = shapedPlateProfile(w.t, local, `BUW${w.t} ${w.hw.map(r3).join('-')}`);
      const o = world(xa, 0);
      const webFrame = { o, x: F.x, u: F.u, v: F.v, len: L };   // = frame(o, o + L·x, m.rotation)
      const voff = (prof.vmin + prof.vmax) / 2;
      const main = k === 0;
      parts.push({
        ...common, material: w.grade, id: m.id + '.s' + w.n + '.web', type: main ? (m.type === 'brace' ? 'brace' : m.type) : 'plate', role: ROLE[m.type] || 'Web', ifc: 'IfcPlate',
        name: m.name ? `${m.name} s${w.n}` : `s${w.n}`,
        profile: prof, profileName: prof.name, frame: webFrame, voff, length: L, start: o, end: add(o, mul(F.x, L)),
        position: 'middle', rotation: m.rotation, attachTo: main ? null : base + '.web', plateWeight: prof.outlineArea * w.t * 1e-9 * STEEL_DENSITY,
        ...(main ? {} : { cjp: true, look: m.type === 'beam' || m.type === 'column' || m.type === 'brace' ? m.type : undefined }),
      });
    });
    for (const side of ['top', 'bot']) {
      // runs of segments whose flange goes straight on with the same plate are one plate; a turn or a change of plate starts another
      const runs = [];
      for (const r of g) {
        const cur = runs[runs.length - 1], fl = r[side];
        const prev = cur && cur[cur.length - 1][side];
        const straightOn = prev && !fl.outlineW && !prev.outlineW && Math.abs(prev.b - fl.b) < TOLJ && Math.abs(prev.t - fl.t) < TOLJ && cur[cur.length - 1].grade === r.grade
          && Math.abs((prev.c[1] - prev.a[1]) / (prev.c[0] - prev.a[0]) - (fl.c[1] - fl.a[1]) / (fl.c[0] - fl.a[0])) < 1e-9
          && Math.abs(prev.c[0] - fl.a[0]) < 1e-6 && Math.abs(prev.c[1] - fl.a[1]) < 1e-6;
        if (straightOn) cur.push(r); else runs.push([r]);
      }
      runs.forEach((run, k) => {
        const r0 = run[0], f0 = r0[side], fz = run[run.length - 1][side];
        const fl = run.length === 1 ? f0 : { b: f0.b, t: f0.t, a: f0.a, c: fz.c, length: Math.hypot(fz.c[0] - f0.a[0], fz.c[1] - f0.a[1]) };
        const pn = r0.index + 1, id = m.id + '.s' + (k === 0 ? n : pn) + '.' + side;
        const extra = k === 0 ? {} : { cjp: true };
        const look = m.type === 'beam' || m.type === 'column' || m.type === 'brace' ? m.type : undefined;   // view3d: drawn in the member's colour
        const role = side === 'top' ? 'Top flange' : 'Bottom flange';
        const a = world(fl.a[0], fl.a[1]), c = world(fl.c[0], fl.c[1]);
        if (fl.outlineW) {   // cut across the flange (a wind column's sloping top): a shaped plate, its outline in its own plane
          const xd = [(c[0] - a[0]) / fl.length, (c[1] - a[1]) / fl.length, (c[2] - a[2]) / fl.length];
          const vp = F.u, up = [vp[1] * xd[2] - vp[2] * xd[1], vp[2] * xd[0] - vp[0] * xd[2], vp[0] * xd[1] - vp[1] * xd[0]];   // v × x
          const sp = shapedPlateProfile(fl.t, fl.outlineW.map(([x, w]) => [r3(x), r3(w)]), plateName(fl.t, fl.b) + ' cut');
          const len = Math.max(...fl.outlineW.map((q) => q[0]));
          parts.push({
            ...common, material: r0.grade, id, type: 'plate', role, ifc: 'IfcPlate', name: role, look,
            profile: sp, profileName: sp.name, frame: { o: a, x: xd, u: up, v: vp, len }, voff: (sp.vmin + sp.vmax) / 2, length: len, start: a, end: add(a, mul(xd, len)),
            position: 'middle', rotation: m.rotation, attachTo: base + '.web', plateWeight: sp.outlineArea * fl.t * 1e-9 * STEEL_DENSITY, ...extra,
          });
          return;
        }
        const rot = rotationFor(a, c, F.u);
        const p = getProfile(plateName(fl.t, fl.b));
        parts.push({
          ...common, material: r0.grade, id, type: 'plate', role, ifc: 'IfcPlate', name: role,
          profile: p, profileName: p.name, frame: frame(a, c, rot), voff: 0, length: fl.length, start: a, end: c, look,
          position: 'middle', rotation: rot, attachTo: base + '.web', plateWeight: fl.b * fl.t * fl.length * 1e-9 * STEEL_DENSITY, ...extra,
        });
      });
    }
  }
  return { parts, problems };
}
