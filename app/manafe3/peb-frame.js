/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * peb-frame.js — the "PEB frame…" data mapping, DOM-free (tested by tests/bin/test-manafe3-pebframe.mjs).
 *
 *   ENGINE_URL                              the engine (manafe3.py starts it at http://127.0.0.1:8765)
 *   frameRequest(form) → body               the dialog's fields (mm, slope as rise/run) → POST /peb/frame JSON
 *   memberOf(m) → DetailCraft member        one engine member (role column|rafter) → a member for Tx.addMember
 *   applyFrame(tx, frame) → ids             one undo step: grids and levels from the frame, then every member
 *   requestFrame(body, fetchFn) → frame     calls the engine; a plain message when it is not running
 *
 * The engine already returns the Manafe3 / DetailCraft model axes (X along the building = numbered grids, Y across
 * the span = lettered grids, Z up, mm), so the mapping copies points and never swaps axes.
 */

export const ENGINE_URL = 'http://127.0.0.1:8765';

export const FRAME_DEFAULTS = { span: 20000, eave_height: 6000, roof_slope: 0.1, bay_spacing: 6000, n_bays: 4 };

/** Engine role → DetailCraft member type. A rafter is a sloped beam. */
const TYPE_OF = { column: 'column', rafter: 'beam' };

/** The form's values (strings or numbers) → the request body; throws a plain message on a bad number. */
export function frameRequest(form) {
  const num = (k, label) => {
    const v = Number(String(form[k] ?? '').trim());
    if (!Number.isFinite(v)) throw new Error(`${label} is not a number`);
    return v;
  };
  const body = {
    span: num('span', 'Span'),
    eave_height: num('eave_height', 'Eave height'),
    roof_slope: num('roof_slope', 'Roof slope'),
    bay_spacing: num('bay_spacing', 'Bay spacing'),
    n_bays: num('n_bays', 'Number of bays'),
  };
  if (!Number.isInteger(body.n_bays)) throw new Error('Number of bays must be a whole number');
  if (form.section === 'hot_rolled') body.section = 'hot_rolled';   // Phase 0 IPE/HEA; the default is built-up
  else { const sizes = sizesOf(form); if (sizes) body.sizes = sizes; }
  return body;
}

/** One engine member → the object Tx.addMember takes. Work lines on the member's centre (position middle). */
export function memberOf(m) {
  const type = TYPE_OF[m.role];
  if (!type) throw new Error(`Unknown member role from the engine: ${m.role}`);
  const out = {
    type,
    profile: m.profile,
    material: m.material || 'S355',
    start: [Number(m.start[0]), Number(m.start[1]), Number(m.start[2])],
    end: [Number(m.end[0]), Number(m.end[1]), Number(m.end[2])],
    rotation: Number(m.rotation || 0),
    position: 'middle',
    name: String(m.id || '').slice(0, 40),
  };
  if (m.section) out.bu = buOf(m.section);   // Phase 1: a built-up member (the model checks it)
  return out;
}

/** The engine's built-up section (snake_case, engine/peb/builtup_frame.py) → the app's (camelCase, builtup.js). */
export function buOf(sec) {
  const bu = {
    segments: sec.segments.map((s) => ({
      length: Number(s.length), hwStart: Number(s.hw_start), hwEnd: Number(s.hw_end), tw: Number(s.tw),
      top: { b: Number(s.bf_top), t: Number(s.tf_top) }, bot: { b: Number(s.bf_bot), t: Number(s.tf_bot) },
      grade: String(s.grade || 'S355'), straight: String(s.straight || 'top'),
    })),
  };
  const cs = Number(sec.cut_start || 0), ce = Number(sec.cut_end || 0), cu = Number(sec.cut_end_u || 0);
  if (cs || ce || cu) bu.cuts = { start: cs, end: ce, ...(cu ? { endU: cu } : {}) };
  return bu;
}

/** The built-up size fields of the form (mm) → the request's `sizes`; empty fields → null (the engine's span rules). */
export const SIZE_FIELDS = ['hw_knee', 'hw_base', 'hw_rafter', 'haunch_length', 'bf', 'tf'];
export function sizesOf(form) {
  const vals = SIZE_FIELDS.map((k) => String(form[k] ?? '').trim());
  if (vals.every((v) => v === '')) return null;
  const out = {};
  SIZE_FIELDS.forEach((k, i) => {
    const v = Number(vals[i]);
    if (vals[i] === '' || !Number.isFinite(v) || v <= 0) throw new Error(`Size ${k.replace('_', ' ')} must be a number above 0 (or leave them all empty for the span rules)`);
    out[k] = v;
  });
  out.grade = String(form.grade || 'S355');
  for (const k of TW_FIELDS) {   // Phase 4 step 9: the webs Design… sizes (optional; empty = the 6 / 8 mm rule)
    const s = String(form[k] ?? '').trim();
    if (s === '') continue;
    const v = Number(s);
    if (!Number.isFinite(v) || v <= 0) throw new Error(`Size ${k.replace('_', ' ')} must be a number above 0 (or empty for the rule)`);
    out[k] = v;
  }
  return out;
}
export const TW_FIELDS = ['tw_column', 'tw_haunch', 'tw_rafter'];

/** POST /peb/frame/defaults: the span rules' sizes, for the form. */
export async function requestDefaults(span, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  let r;
  try { r = await fetchFn(base + '/peb/frame/defaults', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ span: Number(span) }) }); }
  catch { throw new Error(`The Manafe3 engine is not running at ${base}. Start everything with: python manafe3.py`); }
  if (!r.ok) throw new Error('Engine: HTTP ' + r.status);
  return (await r.json()).sizes;
}

/** Puts the frame into the model inside one edit (Model.change): the grids and levels, then the members. */
export function applyFrame(tx, frame) {
  if (!frame || !Array.isArray(frame.members) || !frame.members.length) throw new Error('The engine returned no members');
  if (frame.grids) tx.setGrids(frame.grids);
  if (Array.isArray(frame.levels) && frame.levels.length) tx.setLevels(frame.levels);
  return frame.members.map((m) => tx.addMember(memberOf(m)));
}

/** POST /peb/frame. fetchFn is injectable for tests. */
export async function requestFrame(body, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  let r;
  try {
    r = await fetchFn(base + '/peb/frame', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  } catch {
    throw new Error(`The Manafe3 engine is not running at ${base}. Start everything with: python manafe3.py`);
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    throw new Error('Engine: ' + (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg).join('; ') : `HTTP ${r.status}`));
  }
  return data;
}
