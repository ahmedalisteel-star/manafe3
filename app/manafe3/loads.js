/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * loads.js — the "Loads…" data mapping, DOM-free (tests/bin/test-manafe3-loads.mjs). The inputs live in the model as
 * state.m3loads (one undo step per edit) and go to the engine (engine/peb/loads_input.py) for every analysis.
 *
 *   LOADS_DEFAULTS                  the form's starting values (user decisions 2026-11-05; V and exposure EMPTY: site facts)
 *   loadsRequest(form) → body       the form (strings) → POST /peb/loads/check JSON (and the analysis requests later)
 *   applyLoads(tx, form)            keeps the form's values in the model
 *   requestLoadsCheck(body, fetch)  the engine checks them and returns Kd, GCpi and the sheeting values it will use
 */
import { ENGINE_URL } from './peb-frame.js';

export const LOADS_DEFAULTS = {
  V: '', exposure: '', enclosure: 'enclosed', Kzt: '1.0', risk: 'II',
  roof_cladding: 'single', roof_cladding_kpa: '', wall_cladding: 'single', wall_cladding_kpa: '',
  collateral: '0.10', Lo: '0.96', base: 'pinned', lrfd: 'yes', asd: 'yes',
};

const opt = (s) => { const v = String(s ?? '').trim(); return v === '' ? null : v; };
function number(form, k, label, { blank = false } = {}) {
  const s = opt(form[k]);
  if (s === null) { if (blank) return null; throw new Error(`${label} is required`); }
  const v = Number(s);
  if (!Number.isFinite(v)) throw new Error(`${label} is not a number`);
  return v;
}

export function loadsRequest(form) {
  return {
    V: number(form, 'V', 'Basic wind speed V (m/s) — a site fact', { blank: true }),
    exposure: opt(form.exposure), enclosure: opt(form.enclosure) || 'enclosed', Kzt: number(form, 'Kzt', 'Kzt'), risk: opt(form.risk) || 'II',
    roof_cladding: form.roof_cladding === 'sandwich' ? 'sandwich' : 'single', roof_cladding_kpa: number(form, 'roof_cladding_kpa', 'Roof sheeting', { blank: true }),
    wall_cladding: form.wall_cladding === 'sandwich' ? 'sandwich' : 'single', wall_cladding_kpa: number(form, 'wall_cladding_kpa', 'Wall sheeting', { blank: true }),
    collateral: number(form, 'collateral', 'Collateral'), Lo: number(form, 'Lo', 'Roof live load Lo'),
    base: form.base === 'fixed' ? 'fixed' : 'pinned', lrfd: form.lrfd !== 'no', asd: form.asd !== 'no',
  };
}

export function applyLoads(tx, form) {
  const keep = {};
  for (const k of Object.keys(LOADS_DEFAULTS)) keep[k] = String(form[k] ?? '');
  tx.s.m3loads = keep;
  return keep;
}

export async function requestLoadsCheck(body, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  let r;
  try { r = await fetchFn(base + '/peb/loads/check', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
  catch { throw new Error(`The Manafe3 engine is not running at ${base}. Start everything with: python manafe3.py`); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error('Engine: ' + (typeof data.detail === 'string' ? data.detail : `HTTP ${r.status}`));
  return data;
}
