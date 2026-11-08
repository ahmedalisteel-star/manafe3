/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-building.js — the "PEB building…" data mapping, DOM-free (tests/bin/test-manafe3-building.mjs).
 *
 *   BUILDING_DEFAULTS                     the form's starting values
 *   buildingRequest(form) → body          the form (strings) → POST /peb/building JSON
 *   parseOpenings(text) → [opening]       one per line: "<wall> <at> <width> <sill> <height>", wall A | B | first | last
 *   memberFromEngine(m) / cleatMember(c)  engine members and cleats → Tx.addMember objects (holes added separately)
 *   applyBuilding(tx, result, spec, {grids}) ONE undo step: the members generated before (gen 'peb') go, the new ones come,
 *                                         and the form's inputs are kept in state.m3building for "Edit building…".
 *                                         Grids: merge (default, no duplicates) / none / replace; levels merged; footings
 *                                         and your own members never touched (field fix 1, R1)
 *   requestBuilding(body, fetchFn)        calls the engine
 * Members you placed yourself are never touched; generated members you edited are replaced (the form says so).
 */
import { ENGINE_URL, buOf, sizesOf, SIZE_FIELDS } from './peb-frame.js';
import { rotationFor } from './builtup-parts.js';

export const BUILDING_DEFAULTS = {
  span: 24000, eave_height: 6000, roof_slope: 0.1, bay_spacing: 6000, n_bays: 4,
  roof_spacing_a: 1250, roof_spacing_b: 1250, roof_first_a: 0, roof_first_b: 0, apex_gap: 200,
  girt_spacing_a: 1250, girt_spacing_b: 1250, girt_first: 1250, gable_spacing: 1250,
  end_first: 'frame', end_last: 'frame', braced_bays: '', end_braced_bays: '', brace_type: 'rod', ridge_tie: 'rod', bolt: 'M12', lap: '',
  purlin: 'Z200x65x20x2.0', eave_strut: 'C200x65x20x2.0', girt: 'Z200x65x20x2.0', openings: '',
  grids_mode: 'merge',
};

const num = (form, k, label, { int = false, blank = false } = {}) => {
  const s = String(form[k] ?? '').trim();
  if (blank && s === '') return null;
  const v = Number(s);
  if (s === '' || !Number.isFinite(v)) throw new Error(`${label} is not a number`);
  if (int && !Number.isInteger(v)) throw new Error(`${label} must be a whole number`);
  return v;
};

export function parseOpenings(text) {
  const out = [];
  String(text || '').split(/\r?\n/).forEach((line, i) => {
    const s = line.trim();
    if (!s) return;
    const p = s.split(/[\s,;]+/);
    const wall = { a: 'A', b: 'B', first: 'first', last: 'last' }[String(p[0]).toLowerCase()];
    const v = p.slice(1).map(Number);
    if (!wall || v.length !== 4 || v.some((x) => !Number.isFinite(x))) throw new Error(`Opening line ${i + 1}: write "wall at width sill height", e.g. "A 7000 4000 0 4000" (wall A, B, first or last)`);
    out.push({ wall, at: v[0], width: v[1], sill: v[2], height: v[3] });
  });
  return out;
}

export function parseBays(text) {
  const s = String(text || '').trim();
  if (!s) return null;
  const v = s.split(/[\s,;]+/).map(Number);
  if (v.some((x) => !Number.isInteger(x) || x < 1)) throw new Error('Braced bays: whole bay numbers from 1, e.g. "1, 4" (empty = the first and the last bay)');
  return v;
}

export function buildingRequest(form) {
  const body = {
    span: num(form, 'span', 'Span'), eave_height: num(form, 'eave_height', 'Eave height'), roof_slope: num(form, 'roof_slope', 'Roof slope'),
    bay_spacing: num(form, 'bay_spacing', 'Bay spacing'), n_bays: num(form, 'n_bays', 'Number of bays', { int: true }),
    roof_a: { spacing: num(form, 'roof_spacing_a', 'Purlin spacing A'), first: num(form, 'roof_first_a', 'Eave strut A'), apex_gap: num(form, 'apex_gap', 'Ridge purlin from apex') },
    roof_b: { spacing: num(form, 'roof_spacing_b', 'Purlin spacing B'), first: num(form, 'roof_first_b', 'Eave strut B'), apex_gap: num(form, 'apex_gap', 'Ridge purlin from apex') },
    wall_a: { spacing: num(form, 'girt_spacing_a', 'Girt spacing A'), first: num(form, 'girt_first', 'First girt') },
    wall_b: { spacing: num(form, 'girt_spacing_b', 'Girt spacing B'), first: num(form, 'girt_first', 'First girt') },
    gable: { spacing: num(form, 'gable_spacing', 'Gable girt spacing'), first: num(form, 'girt_first', 'First girt') },
    sections: { purlin: String(form.purlin || '').trim(), eave_strut: String(form.eave_strut || '').trim(), girt: String(form.girt || '').trim() },
    end_first: form.end_first === 'rafter' ? 'rafter' : 'frame', end_last: form.end_last === 'rafter' ? 'rafter' : 'frame',
    brace_type: form.brace_type === 'angle' ? 'angle' : 'rod', ridge_tie: form.ridge_tie === 'strap' ? 'strap' : 'rod', bolt: form.bolt === 'M16' ? 'M16' : 'M12',
    fixed_lap: num(form, 'lap', 'Lap', { blank: true }), braced_bays: parseBays(form.braced_bays), end_braced_bays: parseBays(form.end_braced_bays), openings: parseOpenings(form.openings),
  };
  const sizes = sizesOf(form);
  if (sizes) body.sizes = sizes;
  return body;
}

export function memberFromEngine(m) {
  const out = {
    type: m.type || 'beam', material: m.material || 'S355', name: String(m.id || '').slice(0, 40), gen: 'peb',
    start: m.start.map(Number), end: m.end.map(Number), rotation: Number(m.rotation || 0), position: m.position || 'middle',
  };
  if (m.section) { out.bu = buOf(m.section); out.position = 'middle'; } else out.profile = m.profile;
  if (m.width_dir) out.rotation = rotationFor(out.start, out.end, m.width_dir);   // a plate (cap plate): its width this way
  return out;
}

export function cleatMember(c) {
  return {
    type: 'plate', profile: 'PL8x100', material: 'S275', name: ('Cleat ' + c.line).slice(0, 40), gen: 'peb', position: 'middle',
    start: c.start.map(Number), end: c.end.map(Number), rotation: rotationFor(c.start, c.end, c.width_dir),
  };
}

export const GRID_MODES = ['none', 'merge', 'replace'];
const SAME = 1;   // mm: a line within this of an existing one IS that line

/**
 * One axis of grid lines merged: every existing line stays (label and position); an incoming line at an existing
 * position is that line; a new position is added with its label, or label' (label'', …) if the label is taken.
 */
export function mergeLines(existing, incoming) {
  const out = (existing || []).map((g) => ({ ...g }));
  let added = 0;
  for (const g of incoming || []) {
    if (out.some((e) => Math.abs(e.at - g.at) <= SAME)) continue;
    let label = String(g.label);
    while (out.some((e) => e.label === label)) label += "'";
    out.push({ label, at: g.at });
    added++;
  }
  out.sort((a, b) => a.at - b.at);
  return { lines: out, added };
}

/** Levels merged: existing ones stay; an incoming level at an existing z or with an existing name is not added. */
export function mergeLevels(existing, incoming) {
  const out = (existing || []).map((l) => ({ ...l }));
  for (const l of incoming || []) {
    if (out.some((e) => Math.abs(e.z - l.z) <= SAME || e.name === l.name)) continue;
    out.push({ name: l.name, z: l.z });
  }
  return out.sort((a, b) => a.z - b.z);
}

/**
 * opts.grids: 'merge' (default: the building's grid lines added where none is, nothing removed), 'none' (grids left
 * as they are), 'replace' (the building's grids replace them — the UI asks first). Levels are always merged; footings
 * and members you placed are never touched.
 */
export function applyBuilding(tx, result, spec, opts = {}) {
  if (!result || !Array.isArray(result.members) || !result.members.length) throw new Error('The engine returned no members');
  const mode = GRID_MODES.includes(opts.grids) ? opts.grids : 'merge';
  const old = tx.s.members.filter((m) => m.gen === 'peb').map((m) => m.id);
  if (old.length) tx.removeMembers(old);
  let gridsAdded = 0;
  if (result.grids && mode === 'replace') tx.setGrids(result.grids);
  else if (result.grids && mode === 'merge') {
    const gx = mergeLines(tx.s.grids?.x, result.grids.x), gy = mergeLines(tx.s.grids?.y, result.grids.y);
    gridsAdded = gx.added + gy.added;
    tx.setGrids({ x: gx.lines, y: gy.lines });
  }
  if (Array.isArray(result.levels) && result.levels.length) tx.setLevels(mergeLevels(tx.s.levels, result.levels));
  let members = 0, holes = 0, cleats = 0;
  for (const m of result.members) {
    const id = tx.addMember(memberFromEngine(m));
    members++;
    for (const h of m.holes || []) { tx.addHole(id, { face: h.face || 'web', x: h.x, y: h.y, d: h.d }); holes++; }
  }
  for (const c of result.cleats || []) {
    const id = tx.addMember(cleatMember(c));
    cleats++;
    for (const h of c.holes || []) { tx.addHole(id, { face: 'plate', x: h.up, y: h.along, d: h.d }); holes++; }
  }
  tx.s.m3building = JSON.parse(JSON.stringify(spec || {}));
  return { members, cleats, holes, replaced: old.length, gridsAdded, grids: mode };
}

export async function requestBuilding(body, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  let r;
  try { r = await fetchFn(base + '/peb/building', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
  catch { throw new Error(`The Manafe3 engine is not running at ${base}. Start everything with: python manafe3.py`); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const d = data.detail; throw new Error('Engine: ' + (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => (x.loc || []).slice(1).join('.') + ' ' + x.msg).join('; ') : `HTTP ${r.status}`)); }
  return data;
}

export { SIZE_FIELDS };
