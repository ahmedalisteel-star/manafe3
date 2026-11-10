/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * peb-building.js — the "PEB building…" data mapping, DOM-free (tests/bin/test-manafe3-building.mjs, test-manafe3-fieldfixes.mjs).
 *
 *   BUILDING_DEFAULTS                     the form's starting values
 *   buildingRequest(form, state?) → body  the form (strings) → POST /peb/building JSON; `bays` may name site grids ("A-L")
 *   parseOpenings(text) → [opening]       one per line: "<wall> <at> <width> <sill> <height>", wall A | B | first | last
 *   parseBayList(text, grids) → {bays, labels} | null   "6600 6000 …" or "A-L" / "A to L" (the spacings of those grid lines)
 *   memberFromEngine(m, gen) / cleatMember(c, gen)   engine members and cleats → Tx.addMember objects (holes added separately)
 *   placementXf(form, yShift) → transform  origin X, Y, Z and plan rotation (any angle) + the engine's span-reference shift
 *   placeGrids(grids, form) → grids | null the building's grid lines on site (null: a rotation that is not a multiple of 90°)
 *   buildingsOf(state) → [{ id, name, spec }]   the model's PEB buildings (an older file's single m3building is building B1)
 *   membersOfBuilding(state, id) → [member]     its generated members (gen 'peb:<id>'; the older 'peb' = B1)
 *   applyBuilding(tx, result, spec, { grids, id }) ONE undo step: that building's generated members go, the new ones come;
 *                                         grids merge (default, no duplicates) / none / replace; levels merged; footings,
 *                                         your own members and the OTHER buildings never touched. Returns { id, … }.
 *   removeBuilding(tx, id)                its generated members and its entry go
 *   requestBuilding(body, fetchFn)        calls the engine
 * Field fixes 1, 5, 6, 7, 8 (R1). Members you placed yourself are never touched; generated members you edited are replaced
 * (the form says so).
 */
import { ENGINE_URL, buOf, sizesOf, SIZE_FIELDS } from './peb-frame.js';
import { rotationFor } from './builtup-parts.js';
import { transformMember, applyPt } from '../transform.js';

export const BUILDING_DEFAULTS = {
  name: '', span: 24000, eave_height: 6000, roof_slope: 0.1, bay_spacing: 6000, n_bays: 4, bays: '',
  span_ref: 'outside', grid_inset: 0, origin_x: 0, origin_y: 0, origin_z: 0, plan_rotation: 0,
  roof_spacing_a: 1250, roof_spacing_b: 1250, roof_first_a: 0, roof_first_b: 0, apex_gap: 200,
  girt_spacing_a: 1250, girt_spacing_b: 1250, girt_first: 1250, gable_spacing: 1250,
  end_first: 'frame', end_last: 'frame', braced_bays: '', end_braced_bays: '', brace_type: 'rod', ridge_tie: 'rod', bolt: 'M12', lap: '',
  purlin: 'Z200x65x20x2.0', eave_strut: 'C200x65x20x2.0', girt: 'Z200x65x20x2.0', openings: '',
  grids_mode: 'merge', footings: 'none',
  wc_braces_first: 2, wc_braces_last: 2,   // wind-column flange braces at every n-th gable girt, per end wall; 0 = none (2026-11-09)
};
export const SPAN_REFS = ['outside', 'centreline', 'grid'];
export const MAX_BUILDINGS = 50;

const num = (form, k, label, { int = false, blank = false, dflt } = {}) => {
  const s = String(form[k] ?? dflt ?? '').trim();
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

/**
 * Uneven bays (field fix 6): "6600 6000 6000 …" (mm, frame line to frame line), or "A-L" / "A to L": the spacings of the
 * model's grid lines from A to L on whichever axis has both labels (in order of position, either direction).
 * Returns { bays, labels (the frame lines' grid labels, or null) } or null when the text is empty.
 */
export function parseBayList(text, grids) {
  const s = String(text || '').trim();
  if (!s) return null;
  const range = s.match(/^(\S+?)\s*(?:-|–|to)\s*(\S+)$/i);
  // a range of grid labels — numbered rows too ("14-7"): spacings never contain a dash, so it is a range whenever both
  // labels are on one axis; otherwise a non-numeric range is refused
  const onAxis = range && ['x', 'y'].some((ax) => (grids?.[ax] || []).some((g) => g.label === range[1]) && (grids?.[ax] || []).some((g) => g.label === range[2]));
  if (range && (onAxis || !/^[\d.]+$/.test(range[1]))) {
    const [, a, b] = range;
    for (const axis of ['x', 'y']) {
      const lines = [...(grids?.[axis] || [])].sort((p, q) => p.at - q.at);
      const i = lines.findIndex((g) => g.label === a), j = lines.findIndex((g) => g.label === b);
      if (i < 0 || j < 0) continue;
      if (i === j) throw new Error(`Bays: grid ${a} to ${b} is no length`);
      const run = i < j ? lines.slice(i, j + 1) : lines.slice(j, i + 1).reverse();
      return { bays: run.slice(1).map((g, k) => Math.round(Math.abs(g.at - run[k].at) * 1000) / 1000), labels: run.map((g) => g.label), axis, from: run[0].at };
    }
    throw new Error(`Bays: no grid axis has both ${a} and ${b} (write the spacings instead, e.g. "6600 6000 6000")`);
  }
  const v = s.split(/[\s,;]+/).map(Number);
  if (v.some((x) => !Number.isFinite(x) || x <= 0)) throw new Error('Bays: spacings in mm ("6600 6000 6000 …") or a grid range ("A-L")');
  return { bays: v, labels: null };
}

export function buildingRequest(form, state = null) {
  const bl = parseBayList(form.bays, state?.grids);
  const body = {
    span: num(form, 'span', 'Span'), eave_height: num(form, 'eave_height', 'Eave height'), roof_slope: num(form, 'roof_slope', 'Roof slope'),
    bay_spacing: bl ? bl.bays[0] : num(form, 'bay_spacing', 'Bay spacing'), n_bays: bl ? bl.bays.length : num(form, 'n_bays', 'Number of bays', { int: true }),
    roof_a: { spacing: num(form, 'roof_spacing_a', 'Purlin spacing A'), first: num(form, 'roof_first_a', 'Eave strut A'), apex_gap: num(form, 'apex_gap', 'Ridge purlin from apex') },
    roof_b: { spacing: num(form, 'roof_spacing_b', 'Purlin spacing B'), first: num(form, 'roof_first_b', 'Eave strut B'), apex_gap: num(form, 'apex_gap', 'Ridge purlin from apex') },
    wall_a: { spacing: num(form, 'girt_spacing_a', 'Girt spacing A'), first: num(form, 'girt_first', 'First girt') },
    wall_b: { spacing: num(form, 'girt_spacing_b', 'Girt spacing B'), first: num(form, 'girt_first', 'First girt') },
    gable: { spacing: num(form, 'gable_spacing', 'Gable girt spacing'), first: num(form, 'girt_first', 'First girt') },
    sections: { purlin: String(form.purlin || '').trim(), eave_strut: String(form.eave_strut || '').trim(), girt: String(form.girt || '').trim() },
    end_first: form.end_first === 'rafter' ? 'rafter' : 'frame', end_last: form.end_last === 'rafter' ? 'rafter' : 'frame',
    brace_type: form.brace_type === 'angle' ? 'angle' : 'rod', ridge_tie: form.ridge_tie === 'strap' ? 'strap' : 'rod', bolt: form.bolt === 'M16' ? 'M16' : 'M12',
    fixed_lap: num(form, 'lap', 'Lap', { blank: true }), braced_bays: parseBays(form.braced_bays), end_braced_bays: parseBays(form.end_braced_bays), openings: parseOpenings(form.openings),
    span_ref: SPAN_REFS.includes(form.span_ref) ? form.span_ref : 'outside', grid_inset: num(form, 'grid_inset', 'Grid inset', { dflt: 0 }),
    wc_braces_first: num(form, 'wc_braces_first', 'Wind-column braces (frame 1 wall)', { int: true, dflt: 2 }), wc_braces_last: num(form, 'wc_braces_last', 'Wind-column braces (last wall)', { int: true, dflt: 2 }),
  };
  if (bl) body.bays = bl.bays;
  const sizes = sizesOf(form);
  if (sizes) body.sizes = sizes;
  for (const g of ['wind_column', 'end_rafter']) {   // Phase 4 step 9: the sections Design… sizes ({hw, tw, bf, tf}; absent = default)
    const v = form[g];
    if (v && typeof v === 'object') body[g] = Object.fromEntries(['hw', 'tw', 'bf', 'tf'].map((k) => [k, Number(v[k])]));
  }
  return body;
}

export function memberFromEngine(m, gen = 'peb') {
  const out = {
    type: m.type || 'beam', material: m.material || 'S355', name: String(m.id || '').slice(0, 40), gen, m3role: m.role || '',
    start: m.start.map(Number), end: m.end.map(Number), rotation: Number(m.rotation || 0), position: m.position || 'middle',
  };
  if (m.section) { out.bu = buOf(m.section); out.position = 'middle'; } else out.profile = m.profile;
  if (m.width_dir) out.rotation = rotationFor(out.start, out.end, m.width_dir);   // a plate (cap plate): its width this way
  return out;
}

export function cleatMember(c, gen = 'peb') {
  return {
    type: 'plate', profile: 'PL8x100', material: 'S275', name: ('Cleat ' + c.line).slice(0, 40), gen, m3role: 'cleat', position: 'middle',
    start: c.start.map(Number), end: c.end.map(Number), rotation: rotationFor(c.start, c.end, c.width_dir),
  };
}

// ---- placement (field fixes 5, 7) ----------------------------------------------------------------------------------------

/** p → R(θ)·(p + [0, yShift, 0]) + origin: the engine's span-reference shift, then the plan rotation about Z, then the origin. */
export function placementXf(form = {}, yShift = 0) {
  const n = (k) => { const v = Number(String(form[k] ?? 0).trim() || 0); if (!Number.isFinite(v)) throw new Error(`Placement: ${k} is not a number`); return v; };
  const ox = n('origin_x'), oy = n('origin_y'), oz = n('origin_z'), deg = n('plan_rotation'), y0 = Number(yShift) || 0;
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
  const A = [[c, -s, 0], [s, c, 0], [0, 0, 1]];
  return { kind: 'rotate', A, t: [ox - s * y0, oy + c * y0, oz], det: 1, deg, origin: [ox, oy, oz], yShift: y0 };
}
const isIdentity = (xf) => xf.deg === 0 && xf.t.every((v) => v === 0);

/** The building's grid lines on site; null when the plan rotation is not a multiple of 90° (grid lines here are x = c / y = c). */
export function placeGrids(grids, form = {}, labels = null) {
  const deg = Number(form.plan_rotation || 0), q = ((Math.round(deg / 90) % 4) + 4) % 4;
  if (Math.abs(deg - Math.round(deg / 90) * 90) > 1e-9) return null;
  const ox = Number(form.origin_x || 0), oy = Number(form.origin_y || 0);
  const gx = (grids.x || []).map((g, i) => ({ label: labels?.[i] ?? g.label, at: g.at })), gy = (grids.y || []).map((g) => ({ ...g }));
  const sh = (list, sgn, o) => list.map((g) => ({ label: g.label, at: Math.round((sgn * g.at + o) * 1000) / 1000 }));
  if (q === 0) return { x: sh(gx, 1, ox), y: sh(gy, 1, oy) };
  if (q === 1) return { x: sh(gy, -1, ox), y: sh(gx, 1, oy) };          // (x, y) → (−y + ox, x + oy)
  if (q === 2) return { x: sh(gx, -1, ox), y: sh(gy, -1, oy) };
  return { x: sh(gy, 1, ox), y: sh(gx, -1, oy) };                       // (x, y) → (y + ox, −x + oy)
}

// ---- several buildings (field fix 8) -------------------------------------------------------------------------------------

export function buildingsOf(state) {
  const list = Array.isArray(state?.m3buildings) ? state.m3buildings : [];
  if (list.length) return list;
  if (state?.m3building && Object.keys(state.m3building).length) return [{ id: 'B1', name: state.m3building.name || 'Building 1', spec: state.m3building }];
  return [];
}
export const genOf = (id) => 'peb:' + id;
const belongs = (m, id) => m.gen === genOf(id) || (id === 'B1' && m.gen === 'peb');
export function membersOfBuilding(state, id) { return state.members.filter((m) => belongs(m, id)); }
/** The building a member was generated for (its id), or null. */
export function buildingOfMember(m) { return !m?.gen ? null : m.gen === 'peb' ? 'B1' : m.gen.startsWith('peb:') ? m.gen.slice(4) : null; }

function nextBuildingId(list) {
  let n = 1;
  while (list.some((b) => b.id === 'B' + n)) n++;
  return 'B' + n;
}

/** Levels merged: existing ones stay; an incoming level at an existing z is that level; a taken name at another z gets the building's name. */
export function mergeLevels(existing, incoming, tag = '') {
  const out = (existing || []).map((l) => ({ ...l }));
  for (const l of incoming || []) {
    if (out.some((e) => Math.abs(e.z - l.z) <= SAME)) continue;
    let name = l.name;
    if (out.some((e) => e.name === name)) name = tag ? `${l.name} ${tag}`.slice(0, 40) : name;
    while (out.some((e) => e.name === name)) name += "'";
    out.push({ name, z: l.z });
  }
  return out.sort((a, b) => a.z - b.z);
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

/** A member object through the placement (start, end and the roll; holes are on the member, they follow). */
function place(obj, xf) {
  if (isIdentity(xf)) return obj;
  const r = transformMember({ ...obj, holes: [], cuts: [] }, xf);
  return { ...obj, start: r.start, end: r.end, rotation: r.rotation };
}

/**
 * opts.grids: 'merge' (default: the building's grid lines added where none is, nothing removed), 'none' (grids left
 * as they are), 'replace' (the building's grids replace them — the UI asks first). opts.id: the building to regenerate
 * (absent: a new building). Levels are always merged; footings, your own members and other buildings are never touched.
 */
export function applyBuilding(tx, result, spec, opts = {}) {
  if (!result || !Array.isArray(result.members) || !result.members.length) throw new Error('The engine returned no members');
  const mode = GRID_MODES.includes(opts.grids) ? opts.grids : 'merge';
  const list = buildingsOf(tx.s).map((b) => ({ ...b }));
  let id = opts.id && list.some((b) => b.id === opts.id) ? opts.id : null;
  if (!id && opts.id === undefined && !Array.isArray(tx.s.m3buildings) && list.length === 1) id = list[0].id;   // an older file: its one building is edited in place
  if (!id) { if (list.length >= MAX_BUILDINGS) throw new Error(`At most ${MAX_BUILDINGS} PEB buildings in one model`); id = nextBuildingId(list); }
  const gen = genOf(id);
  const old = tx.s.members.filter((m) => belongs(m, id)).map((m) => m.id);
  if (old.length) tx.removeMembers(old);
  const form = spec || {};
  const xf = placementXf(form, result.y_shift || 0);
  const bl = (() => { try { return parseBayList(form.bays, tx.s.grids); } catch { return null; } })();
  let gridsAdded = 0, gridsSkipped = false;
  const placed = result.grids ? placeGrids(result.grids, form, bl?.labels) : null;
  if (result.grids && !placed && mode !== 'none') gridsSkipped = true;
  if (placed && mode === 'replace') tx.setGrids(placed);
  else if (placed && mode === 'merge') {
    const gx = mergeLines(tx.s.grids?.x, placed.x), gy = mergeLines(tx.s.grids?.y, placed.y);
    gridsAdded = gx.added + gy.added;
    tx.setGrids({ x: gx.lines, y: gy.lines });
  }
  const name = String(form.name || '').trim() || (list.find((b) => b.id === id)?.name) || 'Building ' + id.slice(1);
  if (Array.isArray(result.levels) && result.levels.length) tx.setLevels(mergeLevels(tx.s.levels, result.levels.map((l) => ({ name: l.name, z: l.z + xf.t[2] })), name));
  let members = 0, holes = 0, cleats = 0;
  for (const m of result.members) {
    const mid = tx.addMember(place(memberFromEngine(m, gen), xf));
    members++;
    for (const h of m.holes || []) { tx.addHole(mid, { face: h.face || 'web', x: h.x, y: h.y, d: h.d }); holes++; }
  }
  for (const c of result.cleats || []) {
    const mid = tx.addMember(place(cleatMember(c, gen), xf));
    cleats++;
    for (const h of c.holes || []) { tx.addHole(mid, { face: 'plate', x: h.up, y: h.along, d: h.d }); holes++; }
  }
  // a model written before field fix 8: its single building's generated members are B1's ('peb' → 'peb:B1')
  for (const m of tx.s.members) if (m.gen === 'peb') m.gen = genOf('B1');
  const entry = { id, name, spec: JSON.parse(JSON.stringify({ ...form, name, grids_mode: undefined })) };
  const i = list.findIndex((b) => b.id === id);
  if (i >= 0) list[i] = entry; else list.push(entry);
  tx.s.m3buildings = list;
  delete tx.s.m3building;
  return { id, name, members, cleats, holes, replaced: old.length, gridsAdded, gridsSkipped, grids: mode, origin: xf.origin, rotation: xf.deg };
}

export function removeBuilding(tx, id) {
  const list = buildingsOf(tx.s).filter((b) => b.id !== id);
  const old = tx.s.members.filter((m) => belongs(m, id)).map((m) => m.id);
  if (old.length) tx.removeMembers(old);
  tx.s.m3buildings = list;
  delete tx.s.m3building;
  return { removed: old.length };
}

/** The point of the building's own coordinates (x along, y across from its steel line A, z up) on site. */
export function sitePoint(spec, yShift, p) { return applyPt(placementXf(spec, yShift), p); }

export async function requestBuilding(body, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  let r;
  try { r = await fetchFn(base + '/peb/building', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
  catch { throw new Error(`The Manafe3 engine is not running at ${base}. Start everything with: python manafe3.py`); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const d = data.detail; throw new Error('Engine: ' + (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => (x.loc || []).slice(1).join('.') + ' ' + x.msg).join('; ') : `HTTP ${r.status}`)); }
  return data;
}

export { SIZE_FIELDS };
