/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-footings.js — pad footings under the PEB columns, and footings with no column (field fix 9). DOM-free.
 *
 *   columnBases(state, { building, pebOnly }) → [{ member, point [x, y, z] }]   the bottom of each column: the centre of
 *       its section there (a built-up column: its base section's centre; a catalog one: its line + the position offset)
 *       pebOnly: the PEB building's main-frame columns (F<n>-CA / -CB) and wind columns (WF<n> / WL<n>); jambs of
 *       openings (O<n>-J<n>) stand on the slab and get none
 *   addPadFootings(tx, state, { building, size }) → { added, skipped }   a pad centred under every such column whose base
 *       has no footing yet (a footing already holding the point in plan is kept as it is); top = the column's base level
 *   footingsWithoutColumn(state) → [footing id]   no column of the model (any column, yours or generated) stands on it:
 *       none of their base points lies inside its plan within 1 000 mm of its top
 *   removeFootingsWithoutColumn(tx, state) → { removed }
 * Size: FOOTING_DEFAULTS (2000 × 2000 × 600) unless given — a placeholder, NOT designed (foundation design is the
 * foundation designer's, from the reaction CSV).
 */
import { frame, voffFor, add, mul } from '../geom.js';
import { getProfile } from '../profiles.js';
import { FOOTING_DEFAULTS } from '../rebar.js';
import { builtUpEndSection } from './builtup-parts.js';
import { membersOfBuilding } from './peb-building.js';

export const PEB_COLUMN = /^(F\d+-C[AB]|W[FL]\d+)$/;
const Z_TOL = 1000;

export function baseOf(m, profiles = []) {
  const bottom = m.start[2] <= m.end[2] ? 'start' : 'end';
  if (m.bu) return builtUpEndSection(m, bottom).point;
  const p = getProfile(m.profile, profiles);
  const f = frame(m.start, m.end, m.rotation);
  return add(m[bottom], mul(f.v, voffFor(m.position, p ? p.depth : 0)));
}

export function columnBases(state, { building = null, pebOnly = true } = {}) {
  const ms = building ? membersOfBuilding(state, building) : state.members;
  return ms.filter((m) => m.type === 'column' && (!pebOnly || (m.gen && PEB_COLUMN.test(m.name))))
    .map((m) => ({ member: m.id, point: baseOf(m, state.profiles).map((v) => Math.round(v * 1000) / 1000) }));
}

export function footingHolds(f, p, ztol = Z_TOL) {
  const a = (Number(f.rotation) || 0) * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  const dx = p[0] - f.x, dy = p[1] - f.y;
  const lx = c * dx + s * dy, ly = -s * dx + c * dy;
  return Math.abs(lx) <= f.L / 2 + 1e-6 && Math.abs(ly) <= f.B / 2 + 1e-6 && Math.abs(p[2] - f.top) <= ztol;
}

export function addPadFootings(tx, state, { building = null, size = {} } = {}) {
  let added = 0, skipped = 0;
  for (const b of columnBases(state, { building })) {
    if (tx.s.footings.some((f) => footingHolds(f, b.point))) { skipped++; continue; }
    tx.addFooting({ ...FOOTING_DEFAULTS, ...size, x: b.point[0], y: b.point[1], top: b.point[2] });
    added++;
  }
  return { added, skipped };
}

export function footingsWithoutColumn(state) {
  const bases = columnBases(state, { pebOnly: false });
  return state.footings.filter((f) => !bases.some((b) => footingHolds(f, b.point))).map((f) => f.id);
}

export function removeFootingsWithoutColumn(tx, state) {
  const ids = footingsWithoutColumn(state);
  if (ids.length) tx.removeFootings(ids);
  return { removed: ids.length };
}
