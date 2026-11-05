/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
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
  return body;
}

/** One engine member → the object Tx.addMember takes. Work lines on the member's centre (position middle). */
export function memberOf(m) {
  const type = TYPE_OF[m.role];
  if (!type) throw new Error(`Unknown member role from the engine: ${m.role}`);
  return {
    type,
    profile: m.profile,
    material: m.material || 'S355',
    start: [Number(m.start[0]), Number(m.start[1]), Number(m.start[2])],
    end: [Number(m.end[0]), Number(m.end[1]), Number(m.end[2])],
    rotation: 0,
    position: 'middle',
    name: String(m.id || '').slice(0, 40),
  };
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
