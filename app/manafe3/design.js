/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * design.js — PEB › "Design…" data side, DOM-free (tests/bin/test-manafe3-design.mjs). Phase 4 step 9.
 * The engine runs the checks and the sizing (POST /peb/design → job, GET /peb/design/{job}); nothing is stored in the
 * model except what "Apply" writes (the proposed sizes, as ONE undo step through applyBuilding). NOT FOR ISSUE while any
 * VERIFIED flag a result rests on is False.
 *
 *   DESIGN_DEFAULTS, cleanSettings(s)       code basis AISC / ECP / both, governing code, target 0.90, limits, uplift mode
 *   designRequest(state, {building, settings, action})   the engine body ("check" | "size")
 *   startDesign(body, fetch) → job;  pollDesign(job, fetch) → {status, progress, result?, error?}
 *   RATIO_BANDS, ratioColor(ratio)          blue < 0.5, green 0.5–0.90, orange 0.90–1.00, red > 1.00, grey NOT EVALUATED
 *   governingRows(result)                   one row per member: the governing code's for the main frames
 *   colorMap(state, result, buildingId)     Map(model member id → colour) for the 3D view
 *   memberIdsOf(state, buildingId, ids)     engine ids (= member names) → model member ids, within that building
 *   tableRows(result, {filter, sort, dir, code})   the results table
 *   proposalRows(spec, proposed)            what Size proposes, field by field (before → after)
 *   specWithProposal(spec, proposed)        the building spec with the proposed sizes (what Apply hands applyBuilding)
 *   calcSheetsHtml(result, keys, meta)      one HTML document, a calc sheet per member, print → PDF
 */
import { ENGINE_URL } from './peb-frame.js';
import { analysisRequest } from './frame-analysis.js';
import { membersOfBuilding } from './peb-building.js';

export const BANNER = 'NOT FOR ISSUE — design results rest on unconfirmed (VERIFIED False) items; see the summary';
export const DESIGN_DEFAULTS = { code_basis: 'both', governing: 'AISC', target: 0.9, sway: 100, rafter_Lr: 180, purlin: 150, uplift_method: 'r_factor', stability: 'dg25' };
export const RATIO_BANDS = [
  { key: 'low', label: '< 0.50', color: '#2f6fd6', test: (r) => r < 0.5 },
  { key: 'ok', label: '0.50 – 0.90', color: '#2e9e4f', test: (r) => r >= 0.5 && r <= 0.9 },
  { key: 'high', label: '0.90 – 1.00', color: '#f08c00', test: (r) => r > 0.9 && r <= 1.0 },
  { key: 'over', label: '> 1.00', color: '#d62828', test: (r) => r > 1.0 },
  { key: 'ne', label: 'NOT EVALUATED', color: '#8a8a8a', test: () => false },
];

export function ratioColor(r) {
  if (r === null || r === undefined || !Number.isFinite(Number(r))) return RATIO_BANDS[4].color;
  return (RATIO_BANDS.find((b) => b.test(Number(r))) || RATIO_BANDS[3]).color;
}

export function cleanSettings(s = {}) {
  const o = { ...DESIGN_DEFAULTS, ...s };
  const pos = (k, lo, hi) => { const v = Number(o[k]); if (!Number.isFinite(v) || v < lo || v > hi) throw new Error(`Design setting ${k}: ${lo} to ${hi}`); return v; };
  if (!['AISC', 'ECP', 'both'].includes(o.code_basis)) throw new Error('Code basis: AISC, ECP or both');
  if (!['AISC', 'ECP'].includes(o.governing)) throw new Error('Governing code: AISC or ECP');
  const governing = o.code_basis === 'both' ? o.governing : o.code_basis;
  return {
    code_basis: o.code_basis, governing, target: pos('target', 0.5, 1.0),
    limits: { sway: pos('sway', 20, 1000), rafter_Lr: pos('rafter_Lr', 50, 1000), purlin: pos('purlin', 50, 1000) },
    uplift_method: o.uplift_method === 'strict' ? 'strict' : 'r_factor', stability: o.stability === 'prismatic' ? 'prismatic' : 'dg25',
  };
}

export function designRequest(state, { building = null, settings = {}, action = 'check' } = {}) {
  const base = analysisRequest(state, { building });
  return { building: base.building, loads: base.loads, settings: cleanSettings({ ...(state.m3design || {}), ...settings }), action: action === 'size' ? 'size' : 'check' };
}

async function call(url, opts, fetchFn) {
  let r;
  try { r = await fetchFn(url, opts); } catch { throw new Error(`The Manafe3 engine is not running at ${ENGINE_URL}. Start everything with: python manafe3.py`); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const d = data.detail; throw new Error('Engine: ' + (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => (x.loc || []).slice(1).join('.') + ' ' + x.msg).join('; ') : `HTTP ${r.status}`)); }
  return data;
}
export async function startDesign(body, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  return (await call(base + '/peb/design', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, fetchFn)).job;
}
export async function pollDesign(job, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  return call(base + '/peb/design/' + encodeURIComponent(job), { method: 'GET' }, fetchFn);
}

/** One row per member: main frames by the governing code, everything else by its only code. */
export function governingRows(result) {
  const gov = result.settings?.governing || 'AISC';
  const out = new Map();
  for (const r of result.rows || []) {
    const frame = r.kind === 'column' || r.kind === 'rafter';
    if (frame && r.code !== gov && (result.settings?.code_basis === 'both')) continue;
    out.set(r.id, r);
  }
  return [...out.values()];
}

export function memberIdsOf(state, buildingId, ids) {
  const want = new Set(ids);
  return membersOfBuilding(state, buildingId).filter((m) => want.has(m.name)).map((m) => m.id);
}

export function colorMap(state, result, buildingId) {
  const byName = new Map(membersOfBuilding(state, buildingId).map((m) => [m.name, m.id]));
  const map = new Map();
  for (const r of governingRows(result)) { const id = byName.get(r.id); if (id) map.set(id, ratioColor(r.ratio)); }
  return map;
}

const KEYS = { id: (r) => r.id, section: (r) => r.section, ratio: (r) => (r.ratio ?? Infinity), governing: (r) => r.governing, combo: (r) => r.combo, code: (r) => r.code, kind: (r) => r.kind };
export function tableRows(result, { filter = '', sort = 'ratio', dir = -1, code = 'governing', band = '' } = {}) {
  let rows = code === 'governing' ? governingRows(result) : (result.rows || []).filter((r) => code === 'all' || r.code === code);
  const f = String(filter).trim().toLowerCase();
  if (f) rows = rows.filter((r) => [r.id, r.kind, r.section, r.governing, r.clause, r.combo, r.code].some((v) => String(v ?? '').toLowerCase().includes(f)));
  if (band) rows = rows.filter((r) => (band === 'ne' ? r.ratio === null : r.ratio !== null && RATIO_BANDS.find((b) => b.key === band)?.test(r.ratio)));
  const k = KEYS[sort] || KEYS.ratio;
  return [...rows].sort((a, b) => { const x = k(a), y = k(b); return (x < y ? -1 : x > y ? 1 : String(a.id).localeCompare(String(b.id), undefined, { numeric: true })) * dir; });
}

const SIZE_KEYS = ['hw_knee', 'hw_base', 'hw_rafter', 'haunch_length', 'bf', 'tf', 'tw_column', 'tw_haunch', 'tw_rafter'];
const SEC_KEYS = ['hw', 'tw', 'bf', 'tf'];
export function proposalRows(spec, proposed) {
  const rows = [];
  const s = proposed?.sizes || {};
  for (const k of SIZE_KEYS) if (s[k] != null) rows.push({ group: 'Main frames', field: k, before: spec?.[k] === '' || spec?.[k] == null ? '(span rule)' : spec[k], after: s[k] });
  for (const k of ['purlin', 'eave_strut', 'girt']) if (proposed?.sections?.[k]) rows.push({ group: 'Cold-formed', field: k, before: spec?.[k] ?? '', after: proposed.sections[k] });
  for (const g of ['wind_column', 'end_rafter']) {
    const v = proposed?.[g];
    if (v) for (const k of SEC_KEYS) rows.push({ group: g === 'wind_column' ? 'Wind columns' : 'End rafters', field: k, before: spec?.[g]?.[k] ?? '(default)', after: v[k] });
  }
  return rows;
}

export function specWithProposal(spec, proposed) {
  const out = JSON.parse(JSON.stringify(spec || {}));
  const s = proposed?.sizes || {};
  for (const k of SIZE_KEYS) if (s[k] != null) out[k] = s[k];
  if (s.grade) out.grade = s.grade;
  for (const k of ['purlin', 'eave_strut', 'girt']) if (proposed?.sections?.[k]) out[k] = proposed.sections[k];
  for (const g of ['wind_column', 'end_rafter']) if (proposed?.[g]) out[g] = Object.fromEntries(SEC_KEYS.map((k) => [k, Number(proposed[g][k])]));
  return out;
}

// ---- calc sheets (HTML → the browser's print → PDF) --------------------------------------------------------------------

const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = (v, d = 3) => (v === null || v === undefined ? 'NOT EVALUATED' : typeof v === 'number' ? (Number.isInteger(v) ? String(v) : v.toFixed(d)) : esc(v));
function kv(obj) {
  if (!obj || typeof obj !== 'object') return '';
  return '<table class="kv">' + Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object').map(([k, v]) => `<tr><th>${esc(k)}</th><td>${num(v)}</td></tr>`).join('')
    + Object.entries(obj).filter(([, v]) => v && typeof v === 'object').map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(Array.isArray(v) ? v.join(', ') : JSON.stringify(v))}</td></tr>`).join('') + '</table>';
}

/** keys: calc keys "id|CODE" (result.calc). meta: {project, building, date}. */
export function calcSheetsHtml(result, keys, meta = {}) {
  const sheets = [];
  for (const key of keys) {
    const c = result.calc?.[key];
    if (!c) continue;
    const open = (c.flags || []).length > 0;
    const rows = (c.checks || []).map((k) => `<tr class="${k.ratio === null ? 'ne' : k.ratio > 1 ? 'over' : ''}"><td>${esc(k.name)}</td><td>${esc(k.reference || k.clause || '')}</td><td class="n">${num(k.demand)}</td><td class="n">${num(k.capacity)}</td><td>${esc(k.unit || '')}</td><td class="n">${num(k.ratio, 4)}</td><td>${esc([k.governing, k.note].filter(Boolean).join(' — '))}</td></tr>`).join('');
    const ratio = Math.max(...(c.checks || []).map((k) => (k.ratio === null ? Infinity : Number(k.ratio))), -Infinity);
    sheets.push(`<section class="sheet">
<header><div class="banner${open ? '' : ' ok'}">${open ? 'NOT FOR ISSUE — rests on unconfirmed items: ' + esc((c.flags || []).join('; ')) : 'Checks on confirmed items only — still subject to the engineer\'s review'}</div>
<h1>${esc(c.id)} <small>${esc(c.code)} — ${esc(c.design_member || '')}</small></h1>
<p class="meta">${esc(meta.project || '')} · ${esc(meta.building || '')} · ${esc(meta.date || '')} · Manafe3 engine</p></header>
<h2>Member and section</h2>${kv({ section: c.section, length: c.length, Fy: c.Fy, pieces: c.pieces, zones: c.zones })}
${c.section && typeof c.section === 'object' ? '<h2>Properties</h2>' + kv(c.section) : ''}
<h2>Restraints</h2>${kv(c.restraints) || '<p>—</p>'}
${c.loads ? '<h2>Loads (kN/m)</h2>' + kv(c.loads) : ''}
<h2>Forces at the governing station</h2>${kv(c.forces)}
<h2>Checks</h2><table class="checks"><thead><tr><th>Check</th><th>Clause / equation</th><th>Demand</th><th>Capacity</th><th>Unit</th><th>Ratio</th><th>Basis</th></tr></thead><tbody>${rows}</tbody></table>
${c.strict ? `<p>Strict rule (free flange braced at supports / flange braces only): ratio ${num(c.strict.ratio, 4)} — ${esc(c.strict.governing)}</p>` : ''}
${c.r_factor ? '<h2>R-factor (AISI S100-16 I6.2.1) — R VERIFIED ' + (c.r_factor.VERIFIED ? 'True' : 'False') + '</h2>' + kv({ R: c.r_factor.R, system: c.r_factor.system, applicable_from_model: c.r_factor.applicable_from_model })
  + '<table class="kv">' + (c.r_factor.conditions || []).map((x) => `<tr><th>${esc(x.name)}</th><td>${num(x.value)}</td><td>${x.ok ? 'ok' : 'NOT MET'}</td></tr>`).join('') + '</table><p>To confirm (not in the model): ' + esc((c.r_factor.to_confirm || []).join('; ')) + '</p>' : ''}
<p class="result">Result: utilisation ${Number.isFinite(ratio) ? ratio.toFixed(4) : 'NOT EVALUATED'} — ${Number.isFinite(ratio) && ratio <= 1 ? 'adequate on the checks above' : 'NOT ADEQUATE / NOT EVALUATED'}</p>
</section>`);
  }
  const css = `body{font:11px/1.35 system-ui,Segoe UI,Arial,sans-serif;color:#111;margin:0}.sheet{padding:14mm;page-break-after:always}
.banner{background:#b00020;color:#fff;font-weight:700;padding:4px 8px;margin-bottom:6px}.banner.ok{background:#2e7d32}
h1{font-size:16px;margin:4px 0}h1 small{font-weight:400;color:#555}h2{font-size:12px;margin:10px 0 3px;border-bottom:1px solid #999}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:2px 4px;text-align:left;vertical-align:top}.n{text-align:right;font-variant-numeric:tabular-nums}
.kv th{width:30%;background:#f4f4f4}tr.over td{background:#fde2e2}tr.ne td{background:#eee}.meta{color:#555;margin:0}.result{font-weight:700}
@media print{.sheet{padding:10mm}}`;
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Manafe3 calc sheets — NOT FOR ISSUE</title><style>${css}</style></head><body>${sheets.join('\n') || '<p>No calc sheet selected.</p>'}</body></html>`;
}
