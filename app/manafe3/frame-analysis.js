/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * frame-analysis.js — the "Analysis…" data side, DOM-free (tests/bin/test-manafe3-analysis.mjs). The engine solves on
 * demand (POST /peb/analysis, engine/analysis/building_analysis.py); nothing is stored in the model.
 *
 *   analysisRequest(state, {building}) → body   one kept building (state.m3buildings, by id; default the first) and the loads (state.m3loads)
 *   requestAnalysis(body, fetch)         → the engine's result (NOT FOR ISSUE: analysis only, members not designed)
 *   frameResult(res, line)               a frame line's result (following "same_as" for identical lines)
 *   combos(fr, set)                      [{ name, set }] — set "case" (unfactored), "LRFD" (strength), "ASD" (service)
 *   diagram(fr, combo, kind, scale)      SVG-ready geometry in frame mm: kind "M" | "V" | "N" | "shape"
 *   reactionRows(res) / reactionsCsv(res) every base reaction, every frame line (incl. the end-rafter frames), every
 *                                        case and combination, labelled by its set — for the foundation designer
 * Sign conventions (printed on the CSV): reactions are the forces the support gives the structure, H + toward column
 * line B (across the span), V + up, M + anticlockwise in the frame elevation drawn with column line A on the left. Diagrams: a
 * a + value is drawn on the side OPPOSITE the member's top face (sideOf below), so M is drawn on the TENSION side:
 * bimsteelauto 0.14.1 gives M + = the member's TOP flange in compression (rafter top flange, column outer flange; the
 * one conversion from PyNite is bimsteelauto's design_moment_factor). P + = compression.
 */
import { ENGINE_URL } from './peb-frame.js';
import { buildingRequest, buildingsOf } from './peb-building.js';
import { loadsRequest, LOADS_DEFAULTS } from './loads.js';

export const BANNER = 'NOT FOR ISSUE — analysis only, members not designed (Phase 4)';
const KIND_INDEX = { N: 1, V: 2, M: 3 };

/** The direction a + ordinate is drawn for a member, from its role: opposite its TOP face — a rafter's top flange faces
 *  up, a column's top (outer) flange faces out of the building (column A −X, column B +X). With M + = top flange in
 *  compression this puts every moment on its tension side, whatever way the member was drawn. */
export function sideOf(role) {
  const r = String(role || '');
  if (r.startsWith('rafter')) return [0, -1];
  if (r === 'column A') return [1, 0];
  if (r === 'column B') return [-1, 0];
  throw new Error(`no drawing side for member role ${role}`);
}

export function analysisRequest(state, { pDelta = true, building = null } = {}) {
  const list = buildingsOf(state);   // field fix 8: several buildings — the chosen one (default the first)
  const b = building ? list.find((x) => x.id === building) : list[0];
  if (!b) throw new Error(list.length ? `No PEB building ${building} in this model` : 'No PEB building in this model: make it first (PEB › Building…).');
  if (!state.m3loads) throw new Error('No loads in this model: enter them first (PEB › Loads…).');
  const loads = loadsRequest({ ...LOADS_DEFAULTS, ...state.m3loads });
  if (loads.V === null || loads.exposure === null) throw new Error('Wind speed V and exposure are site facts: enter them in PEB › Loads….');
  return { building: buildingRequest(b.spec, state), loads, p_delta: pDelta };
}

export async function requestAnalysis(body, fetchFn = globalThis.fetch, base = ENGINE_URL) {
  let r;
  try { r = await fetchFn(base + '/peb/analysis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); }
  catch { throw new Error(`The Manafe3 engine is not running at ${base}. Start everything with: python manafe3.py`); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const d = data.detail; throw new Error('Engine: ' + (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => (x.loc || []).slice(1).join('.') + ' ' + x.msg).join('; ') : `HTTP ${r.status}`)); }
  return data;
}

export function frameResult(res, line) {
  const f = res.frames.find((x) => x.line === String(line));
  if (!f) return null;
  return f.result || res.frames.find((x) => x.line === f.same_as)?.result || null;
}

export function combos(fr, set = null) {
  return fr.combos.map(([name, s]) => ({ name, set: s })).filter((c) => !set || c.set === set);
}

/** Geometry for one diagram. Points in frame mm (X across the span, Y up); the caller flips Y for SVG. */
export function diagram(fr, combo, kind, scale) {
  const r = fr.results[combo];
  if (!r) throw new Error(`no result for ${combo}`);
  const out = { kind, combo, set: r.set, members: [], peak: null };
  if (kind === 'shape') {
    const d = r.displacements;
    const mv = (n) => [fr.nodes[n][0] + d[n][0] * scale, fr.nodes[n][1] + d[n][1] * scale];
    const at = new Map(Object.entries(fr.nodes).map(([n, p]) => [p[0] + ',' + p[1], n]));
    for (const m of fr.members) {
      const ni = at.get(m.i[0] + ',' + m.i[1]), nj = at.get(m.j[0] + ',' + m.j[1]);
      out.members.push({ mark: m.mark, role: m.role, base: [m.i, m.j], curve: [mv(ni), mv(nj)] });
    }
    let best = null;
    for (const [n, v] of Object.entries(d)) { const s = Math.hypot(v[0], v[1]); if (!best || s > best.v) best = { v: s, node: n, at: fr.nodes[n], dx: v[0], dy: v[1] }; }
    out.peak = best;
    return out;
  }
  const k = KIND_INDEX[kind];
  if (!k) throw new Error(`unknown diagram ${kind}`);
  for (const m of fr.members) {
    const st = r.members[m.mark];
    if (!st) continue;                                  // rigid links carry no diagram
    const [xi, yi] = m.i, [xj, yj] = m.j;
    const L = Math.hypot(xj - xi, yj - yi), ux = (xj - xi) / L, uy = (yj - yi) / L, [nx, ny] = sideOf(m.role);
    const curve = st.map((s) => [xi + ux * s[0] + nx * s[k] * scale, yi + uy * s[0] + ny * s[k] * scale]);
    let pk = st[0];
    for (const s of st) if (Math.abs(s[k]) > Math.abs(pk[k])) pk = s;
    const peak = { v: pk[k], x: pk[0], at: [xi + ux * pk[0] + nx * pk[k] * scale, yi + uy * pk[0] + ny * pk[k] * scale] };
    out.members.push({ mark: m.mark, role: m.role, base: [m.i, m.j], curve: [m.i, ...curve, m.j], peak });
    if (!out.peak || Math.abs(peak.v) > Math.abs(out.peak.v)) out.peak = { ...peak, mark: m.mark };
  }
  return out;
}

/** The largest |value| of a diagram over all members, for choosing a scale. */
export function maxValue(fr, combo, kind) {
  const r = fr.results[combo];
  if (kind === 'shape') return Math.max(0, ...Object.values(r.displacements).map((v) => Math.hypot(v[0], v[1])));
  const k = KIND_INDEX[kind];
  return Math.max(0, ...Object.values(r.members).flatMap((st) => st.map((s) => Math.abs(s[k]))));
}

const COL = { BA: 'A', BB: 'B' };
export function reactionRows(res) {
  const rows = [];
  for (const f of res.frames) {
    const fr = frameResult(res, f.line);
    for (const [name, set] of fr.combos) {
      for (const b of fr.base_nodes) {
        const [H, V, M] = fr.results[name].reactions[b];
        rows.push({ line: f.line, column: COL[b] || b, set, combo: name, H, V, M });
      }
    }
  }
  for (const e of res.end_frames || []) {
    const line = e.end === 'first' ? '1' : String(res.input.n_bays + 1);
    for (const [name, r] of Object.entries(e.results)) {
      for (const [cid, [H, V]] of Object.entries(r.reactions)) rows.push({ line, column: cid, set: r.set, combo: name, H, V, M: 0 });
    }
  }
  return rows;
}

const q = (s) => (/[",\n]/.test(String(s)) ? '"' + String(s).replace(/"/g, '""') + '"' : String(s));
export function reactionsCsv(res) {
  const lines = [
    q(BANNER),
    q('Base reactions = forces from the support on the structure: H + toward column line B, V + up, M + anticlockwise in the frame elevation drawn with column line A on the left. kN, kN·m.'),
    q(`Set: case = unfactored load case (for the foundation designer); LRFD = strength; ASD = deflection / drift. Bases ${res.input.base}; P-Delta ${res.p_delta ? 'on' : 'off'}.`),
    'Frame line,Column,Set,Case / combination,H (kN),V (kN),M (kN·m)',
  ];
  for (const r of reactionRows(res)) lines.push([r.line, r.column, r.set, q(r.combo), r.H.toFixed(3), r.V.toFixed(3), r.M.toFixed(3)].join(','));
  return lines.join('\r\n') + '\r\n';
}

/** One line per frame line, each with its combination: from ASD the largest eave movement ("drift": the knees' spread
 *  under gravity included), the largest SWAY (the eaves' mean sideways movement) and the apex deflection; the LRFD peak M. */
export function summaryRows(res) {
  const H = Number(res.input.eave_height);
  return res.frames.map((f) => {
    const fr = frameResult(res, f.line), s = fr.summary;
    const drift = s.drift_ASD, apex = s.apex_ASD, sway = s.sway_ASD;
    const mPeak = Object.entries(s.max_M_LRFD).reduce((a, [mk, v]) => (!a || Math.abs(v.M) > Math.abs(a.M) ? { mark: mk, ...v } : a), null);
    return {
      line: f.line, same_as: f.same_as === f.line ? '' : f.same_as,
      drift: drift ? { combo: drift[0], mm: drift[1], ratio: drift[1] > 0 ? Math.round(H / drift[1]) : Infinity } : null,
      sway: sway ? { combo: sway[0], mm: sway[1], ratio: Math.abs(sway[1]) > 0 ? Math.round(H / Math.abs(sway[1])) : Infinity } : null,
      apex: apex ? { combo: apex[0], mm: apex[1], ratio: apex[1] < 0 ? Math.round(Number(res.input.span) / -apex[1]) : Infinity } : null,
      maxM: mPeak,
    };
  });
}
