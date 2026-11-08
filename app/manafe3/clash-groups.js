/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * clash-groups.js — clashes grouped by type, and the generated connection points hidden until Phase 5 (field fix 16).
 * DOM-free.
 *
 *   clashKind(state, clash) → { key, label, generatedJoint }   key = the two members' roles (the PEB generator's m3role,
 *       else the member type; a connection's parts "connection", a footing "footing"), sorted, e.g. "flange_brace × rafter"
 *   groupClashes(state, clashes, { hideGenerated }) → { groups: [{ key, label, generatedJoint, clashes }], hidden, shown }
 *
 * A clash is a GENERATED CONNECTION POINT when both members were made by the PEB generator (gen 'peb…') and their roles
 * are a joint the generator leaves as a point until Phase 5 designs the connections (GENERATED_JOINTS): flange braces
 * into rafters / columns / purlins / girts (and two of them at one purlin), crossing rods and their ends at rafters and
 * columns, rafter to column at the knee, rafter to rafter at the ridge, the cap plate into the wind column and under the
 * rafter, the wind column's top into the rafter, the eave strut on the column. Everything else is real and always shown
 * — a member you placed, a crane girder into a column, a bracket inside a column, a member through a plate.
 */
export const GENERATED_JOINTS = new Set([
  'flange_brace×rafter', 'column×flange_brace', 'flange_brace×purlin', 'flange_brace×girt', 'flange_brace×flange_brace',
  'roof_brace×roof_brace', 'wall_brace×wall_brace', 'rafter×roof_brace', 'column×roof_brace', 'column×wall_brace',
  'column×rafter', 'rafter×rafter',
  'cap_plate×wind_column', 'cap_plate×rafter', 'rafter×wind_column',
  'column×eave_strut',
]);

const LABEL = (r) => String(r).replace(/_/g, ' ');

function roleOf(state, ref) {
  if (ref.kind === 'footing') return { role: 'footing', gen: false };
  if (ref.kind === 'conn') return { role: 'connection', gen: false };
  if (ref.kind === 'stair') return { role: 'stair', gen: false };
  const m = state.members.find((x) => x.id === ref.id);
  if (!m) return { role: '?', gen: false };
  return { role: m.m3role || m.type, gen: !!(m.gen && m.gen.startsWith('peb')) };
}

export function clashKind(state, c) {
  const a = roleOf(state, c.a), b = roleOf(state, c.b);
  const [r1, r2] = [a.role, b.role].sort();
  const key = r1 + '×' + r2;
  return { key, label: LABEL(r1) + ' × ' + LABEL(r2), generatedJoint: a.gen && b.gen && GENERATED_JOINTS.has(key) };
}

export function groupClashes(state, clashes, { hideGenerated = false } = {}) {
  const by = new Map();
  let hidden = 0;
  for (const c of clashes) {
    const k = clashKind(state, c);
    if (hideGenerated && k.generatedJoint) { hidden++; continue; }
    const id = k.key + (k.generatedJoint ? ' (generated)' : '');
    if (!by.has(id)) by.set(id, { key: k.key, label: k.label, generatedJoint: k.generatedJoint, clashes: [] });
    by.get(id).clashes.push(c);
  }
  // real clashes first, then by count
  const groups = [...by.values()].sort((p, q) => (p.generatedJoint - q.generatedJoint) || (q.clashes.length - p.clashes.length) || p.label.localeCompare(q.label));
  return { groups, hidden, shown: clashes.length - hidden };
}
