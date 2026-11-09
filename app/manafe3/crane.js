/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * crane.js — the crane runway of a PEB building: GEOMETRY ONLY (field fixes 11, 12, 13). DOM-free.
 * Crane loads, the analysis and the design of girders and brackets stay on the roadmap (Phase 4+).
 *
 *   CRANE_DEFAULTS                       the form's starting values (R1 block 2: rail top +7 800, rail centre 324 mm from the
 *                                        column's inner face; girder web 700 × 8, top 250 × 12, bottom 200 × 10)
 *   innerFace(m, z) → { point, inward, d }   a main-frame column's INNER face at height z on its real (tapered) section:
 *                                        point on the face (world), the horizontal unit vector into the building, depth d
 *   craneRunway(state, buildingId, opts) → { members: [Tx.addMember objects], problems: [text], rail: [{ side, line }] }
 *   applyCrane(tx, buildingId, opts)     ONE undo step: that building's crane members (gen 'crane:<id>') go, the new ones
 *                                        come; the inputs are kept on the building (m3buildings[i].crane) for re-editing
 *   removeCrane(tx, buildingId)
 *   hasCrane(state) / CRANE_WARNING      the warning every model with crane members shows (build.js problems)
 *
 * Per side (A, B or both) and per bay in the range covered:
 *   bracket   catalog profile (default HEA300), cantilevered square off the column's inner face at the frame line, its TOP
 *             at the girder's underside; length = rail offset + the girder's wider flange / 2 + 50 mm
 *   girder    a BUILT-UP member (the existing type: unequal flanges allowed), constant depth, straight top on its line =
 *             the girder's top of steel, frame line to frame line (simple spans; the joint over the bracket is Phase 5)
 *   rail      PL<h>x<w> on the girder's top, centred on the rail line (default 50 × 50)
 *   end stop  PL20x200, 250 high, on the girder top 150 mm inside each end of the runway
 * The rail line is measured from the column's inner face AT BRACKET LEVEL on the real tapered column (R1). The girder's
 * flange must clear the inner face up to the girder's top (a tapered column grows inward with height): checked, and
 * reported as a problem if the clearance is under 25 mm.
 */
import { frame, add, mul, sub, dot } from '../geom.js';
import { segmentPlates } from './builtup.js';
import { buildingsOf, membersOfBuilding } from './peb-building.js';
import { getProfile } from '../profiles.js';
import { rotationFor } from './builtup-parts.js';

export const CRANE_DEFAULTS = {
  sides: 'both', from_line: '', to_line: '', rail_top: 7800, rail_offset: 324, rail_h: 50, rail_w: 50,
  girder_hw: 700, girder_tw: 8, girder_top_b: 250, girder_top_t: 12, girder_bot_b: 200, girder_bot_t: 10, girder_grade: 'S355',
  bracket: 'HEA300',
};
export { CRANE_WARNING } from './crane-note.js';
const COLUMN = /^F(\d+)-C([AB])$/;
const CLEAR_MIN = 25;

export const genOfCrane = (id) => 'crane:' + id;
export const hasCrane = (state) => state.members.some((m) => m.gen?.startsWith('crane'));

/** v of a built-up section's outer face on side 'top' | 'bot' at x along the member, from the web depth at x on a SQUARE
 *  station (the end cuts shift the plates' end points, not the section): builtup.js's levels(). */
function faceV(m, x, side) {
  const F = frame(m.start, m.end, m.rotation);
  const segs = segmentPlates(m.bu, F.len);
  const s = segs.find((q) => x <= q.x1 + 1e-6) || segs[segs.length - 1];
  const seg = m.bu.segments[s.index];
  const hw = s.hwStart + (s.hwEnd - s.hwStart) * Math.min(1, Math.max(0, (x - s.x0) / (s.x1 - s.x0)));
  const tt = seg.top.t, tb = seg.bot.t;
  const lv = s.straight === 'top' ? { top: 0, bot: -tt - hw - tb } : s.straight === 'bottom' ? { bot: 0, top: tb + hw + tt } : { top: hw / 2 + tt, bot: -hw / 2 - tb };
  return lv[side];
}

/** A (vertical, built-up) column's inner face at height z. 'Inner' = away from its straight (outer) flange. */
export function innerFace(m, z) {
  if (!m.bu) throw new Error(`${m.name}: the crane generator needs the PEB's built-up columns`);
  const F = frame(m.start, m.end, m.rotation);
  if (Math.abs(F.x[2]) < 0.999) throw new Error(`${m.name}: not vertical`);
  const x = (z - m.start[2]) / F.x[2];
  if (x < 0 || x > F.len) throw new Error(`${m.name}: height ${z} is outside the column`);
  const straight = m.bu.segments[0].straight;
  const outerTop = straight !== 'bottom';                          // 'top' (and 'centre': take −v as inward)
  const vIn = outerTop ? faceV(m, x, 'bot') : faceV(m, x, 'top');
  const vOut = outerTop ? faceV(m, x, 'top') : faceV(m, x, 'bot');
  const inward = mul(F.v, outerTop ? -1 : 1);
  const line = add(m.start, mul(F.x, x));
  return { point: add(line, mul(F.v, vIn)), inward, d: Math.abs(vOut - vIn) };
}

function girderBu(o, L) {
  return { segments: [{ length: L, hwStart: o.girder_hw, hwEnd: o.girder_hw, tw: o.girder_tw, top: { b: o.girder_top_b, t: o.girder_top_t }, bot: { b: o.girder_bot_b, t: o.girder_bot_t }, grade: o.girder_grade, straight: 'top' }] };
}

export function craneRunway(state, id, opts = {}) {
  const o = { ...CRANE_DEFAULTS, ...opts };
  for (const k of ['rail_top', 'rail_offset', 'rail_h', 'rail_w', 'girder_hw', 'girder_tw', 'girder_top_b', 'girder_top_t', 'girder_bot_b', 'girder_bot_t']) {
    o[k] = Number(o[k]);
    if (!Number.isFinite(o[k]) || o[k] <= 0) throw new Error(`Crane: ${k.replace(/_/g, ' ')} must be a positive number`);
  }
  const b = buildingsOf(state).find((x) => x.id === id);
  if (!b) throw new Error(`No PEB building ${id}`);
  const brk = getProfile(String(o.bracket), state.profiles);
  if (!brk) throw new Error(`Crane: bracket profile ${o.bracket} is not known`);
  const origin_z = Number(b.spec.origin_z || 0);
  const railTop = origin_z + o.rail_top;
  const dg = o.girder_hw + o.girder_top_t + o.girder_bot_t, bfw = Math.max(o.girder_top_b, o.girder_bot_b);
  const zTop = railTop - o.rail_h, zBot = zTop - dg;              // girder top of steel, underside (= bracket top)
  const gen = genOfCrane(id);
  const cols = new Map();                                         // side → [{ line, m }] in frame order
  for (const m of membersOfBuilding(state, id)) {
    const k = COLUMN.exec(m.name || '');
    if (!k) continue;
    if (!cols.has(k[2])) cols.set(k[2], []);
    cols.get(k[2]).push({ line: Number(k[1]), m });
  }
  const sides = o.sides === 'A' || o.sides === 'B' ? [o.sides] : ['A', 'B'];
  const members = [], problems = [], rail = [];
  for (const side of sides) {
    const list = (cols.get(side) || []).sort((p, q) => p.line - q.line);
    const lo = Number(o.from_line) || list[0]?.line, hi = Number(o.to_line) || list[list.length - 1]?.line;
    const run = list.filter((c) => c.line >= lo && c.line <= hi);
    if (run.length < 2) { problems.push(`Side ${side}: fewer than two main-frame columns between lines ${lo} and ${hi} — no runway there (an end-rafter wall has no main column)`); continue; }
    const pts = [];
    for (const c of run) {
      const f = innerFace(c.m, zBot);
      const railPt = add(f.point, mul(f.inward, o.rail_offset));
      // clearance: the girder's flange edge to the column face at the girder's TOP (the tapered face comes inward with height)
      const fTop = innerFace(c.m, zTop);
      const clear = dot(sub(railPt, fTop.point), f.inward) - bfw / 2;
      if (clear < CLEAR_MIN) problems.push(`${c.m.name}: the girder flange clears the column face by ${Math.round(clear)} mm only at the girder top (rail offset ${o.rail_offset} mm)`);
      const bl = o.rail_offset + bfw / 2 + 50;
      members.push({ type: 'beam', profile: brk.name, material: 'S355', name: `CB${side}${c.line}`.slice(0, 40), gen, m3role: 'crane_bracket', position: 'top',
        start: f.point.map(r3), end: add(f.point, mul(f.inward, bl)).map(r3), rotation: 0 });
      pts.push({ line: c.line, p: railPt, clear });
    }
    for (let i = 0; i + 1 < pts.length; i++) {
      const a = [pts[i].p[0], pts[i].p[1], zTop], c = [pts[i + 1].p[0], pts[i + 1].p[1], zTop];
      const L = Math.hypot(c[0] - a[0], c[1] - a[1]);
      members.push({ type: 'beam', material: o.girder_grade, name: `CG${side}${pts[i].line}-${pts[i + 1].line}`.slice(0, 40), gen, m3role: 'crane_girder', position: 'middle',
        start: a.map(r3), end: c.map(r3), rotation: 0, bu: girderBu(o, L) });
      members.push({ type: 'plate', profile: `PL${o.rail_h}x${o.rail_w}`, material: 'S355', name: `CR${side}${pts[i].line}-${pts[i + 1].line}`.slice(0, 40), gen, m3role: 'crane_rail', position: 'bottom',
        start: a.map(r3), end: c.map(r3), rotation: 0 });
    }
    // end stops, 150 mm inside each end, on the girder top beside the rail
    const A = pts[0].p, Z = pts[pts.length - 1].p, dir = [Z[0] - A[0], Z[1] - A[1], 0], Ld = Math.hypot(dir[0], dir[1]), u = [dir[0] / Ld, dir[1] / Ld, 0];
    for (const [k, P] of [['1', add([A[0], A[1], zTop], mul(u, 150))], ['2', add([Z[0], Z[1], zTop], mul(u, -150))]]) {
      const side2 = mul([-u[1], u[0], 0], o.rail_w / 2 + 30);       // beside the rail, on the flange
      const s0 = add(P, side2);
      const e0 = add(s0, [0, 0, 250]);
      members.push({ type: 'plate', profile: 'PL20x200', material: 'S355', name: `CS${side}${k}`, gen, m3role: 'crane_stop', position: 'middle',
        start: s0.map(r3), end: e0.map(r3), rotation: rotationFor(s0, e0, u) });   // its 200 along the runway, 20 across
    }
    rail.push({ side, from: pts[0].line, to: pts[pts.length - 1].line, z: railTop, clearMin: Math.round(Math.min(...pts.map((q) => q.clear))) });
  }
  return { members, problems, rail, zTop: r3(zTop), zBot: r3(zBot), girderDepth: dg };
}
const r3 = (v) => Math.round(v * 1000) / 1000;

export function applyCrane(tx, id, opts = {}) {
  const r = craneRunway(tx.s, id, opts);
  const old = tx.s.members.filter((m) => m.gen === genOfCrane(id)).map((m) => m.id);
  if (old.length) tx.removeMembers(old);
  for (const m of r.members) tx.addMember(m);
  const list = buildingsOf(tx.s).map((b) => (b.id === id ? { ...b, crane: { ...CRANE_DEFAULTS, ...opts } } : b));
  tx.s.m3buildings = list;
  delete tx.s.m3building;
  return { members: r.members.length, replaced: old.length, problems: r.problems, rail: r.rail };
}

export function removeCrane(tx, id) {
  const old = tx.s.members.filter((m) => m.gen === genOfCrane(id)).map((m) => m.id);
  if (old.length) tx.removeMembers(old);
  tx.s.m3buildings = buildingsOf(tx.s).map((b) => { if (b.id !== id) return b; const { crane, ...rest } = b; void crane; return rest; });
  return { removed: old.length };
}
