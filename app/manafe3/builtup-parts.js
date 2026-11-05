/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
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
 * Weights are gross: outline area × thickness × 7850 kg/m³ (holes not deducted), as plateWeights in builtup.js.
 * Holes, copes and connections on built-up members come in later phases: they are reported, not built.
 */
import { frame, add, mul, dot } from '../geom.js';
import { getProfile, plateName } from '../profiles.js';
import { segmentPlates, polygonArea, STEEL_DENSITY } from './builtup.js';

const ROLE = { column: 'Column web', beam: 'Rafter web', brace: 'Brace web', plate: 'Web' };
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

export function builtUpParts(m) {
  const problems = [];
  const F = frame(m.start, m.end, m.rotation);
  const world = (x, v) => add(add(F.o, mul(F.x, x)), mul(F.v, v));
  const parts = [];
  if (m.holes?.length) problems.push({ ref: m.id, text: 'Holes on a built-up member are not built yet (Phase 5): ' + m.holes.length + ' left out.' });
  if (m.cuts?.length) problems.push({ ref: m.id, text: 'Copes on a built-up member are not built yet: ' + m.cuts.length + ' left out.' });
  for (const s of segmentPlates(m.bu, F.len)) {
    const n = s.index + 1, base = m.id + '.s' + n;
    // the web part runs from its outline's smallest x (a plumb end cut reaches behind the segment start) to its largest
    const xs = s.web.outline.map((p) => p[0]), xa = Math.min(...xs), L = Math.max(...xs) - xa;
    const local = s.web.outline.map(([x, v]) => [r3(x - xa), r3(v)]);
    const prof = shapedPlateProfile(s.web.t, local, `BUW${s.web.t} ${r3(s.hwStart)}-${r3(s.hwEnd)}`);
    const o = world(xa, 0);
    const webFrame = { o, x: F.x, u: F.u, v: F.v, len: L };   // = frame(o, o + L·x, m.rotation)
    const voff = (prof.vmin + prof.vmax) / 2;
    const common = { member: m.id, conn: null, segment: n, material: s.grade, phase: m.phase || 1, holes: [], cuts: [], setback: { start: 0, end: 0 }, endCuts: null, builtUp: true };
    parts.push({
      ...common, id: base + '.web', type: m.type === 'brace' ? 'brace' : m.type, role: ROLE[m.type] || 'Web', ifc: 'IfcPlate', name: m.name ? `${m.name} s${n}` : `s${n}`,
      profile: prof, profileName: prof.name, frame: webFrame, voff, length: L, start: o, end: add(o, mul(F.x, L)),
      position: 'middle', rotation: m.rotation, attachTo: null, plateWeight: prof.outlineArea * s.web.t * 1e-9 * STEEL_DENSITY,
    });
    for (const side of ['top', 'bot']) {
      const fl = s[side];
      const a = world(fl.a[0], fl.a[1]), c = world(fl.c[0], fl.c[1]);
      if (fl.outlineW) {   // cut across the flange (a wind column's sloping top): a shaped plate, its outline in its own plane
        const xd = [(c[0] - a[0]) / fl.length, (c[1] - a[1]) / fl.length, (c[2] - a[2]) / fl.length];
        const vp = F.u, up = [vp[1] * xd[2] - vp[2] * xd[1], vp[2] * xd[0] - vp[0] * xd[2], vp[0] * xd[1] - vp[1] * xd[0]];   // v × x
        const sp = shapedPlateProfile(fl.t, fl.outlineW.map(([x, w]) => [r3(x), r3(w)]), plateName(fl.t, fl.b) + ' cut');
        const len = Math.max(...fl.outlineW.map((q) => q[0]));
        parts.push({
          ...common, id: base + '.' + side, type: 'plate', role: side === 'top' ? 'Top flange' : 'Bottom flange', ifc: 'IfcPlate', name: side === 'top' ? 'Top flange' : 'Bottom flange',
          look: m.type === 'beam' || m.type === 'column' || m.type === 'brace' ? m.type : undefined,
          profile: sp, profileName: sp.name, frame: { o: a, x: xd, u: up, v: vp, len }, voff: (sp.vmin + sp.vmax) / 2, length: len, start: a, end: add(a, mul(xd, len)),
          position: 'middle', rotation: m.rotation, attachTo: base + '.web', plateWeight: sp.outlineArea * fl.t * 1e-9 * STEEL_DENSITY,
        });
        continue;
      }
      const rot = rotationFor(a, c, F.u);
      const p = getProfile(plateName(fl.t, fl.b));
      parts.push({
        ...common, id: base + '.' + side, type: 'plate', role: side === 'top' ? 'Top flange' : 'Bottom flange', ifc: 'IfcPlate', name: side === 'top' ? 'Top flange' : 'Bottom flange',
        profile: p, profileName: p.name, frame: frame(a, c, rot), voff: 0, length: fl.length, start: a, end: c,
        look: m.type === 'beam' || m.type === 'column' || m.type === 'brace' ? m.type : undefined,   // view3d: drawn in the member's colour
        position: 'middle', rotation: rot, attachTo: base + '.web', plateWeight: fl.b * fl.t * fl.length * 1e-9 * STEEL_DENSITY,
      });
    }
  }
  return { parts, problems };
}
