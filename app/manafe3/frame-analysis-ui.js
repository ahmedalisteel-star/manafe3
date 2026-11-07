/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * frame-analysis-ui.js — PEB › "Analysis…": runs the engine's analysis of the kept building and loads, then shows per frame
 * line and per case / combination the deflected shape and the N / V / M diagrams (SVG), the summary (ASD drift and apex,
 * LRFD peaks), the base reactions, and a CSV of every base reaction (unfactored cases included) for the foundation
 * designer. Loaded by detailcraft.js: mountFrameAnalysis({ model: () => Model, print, download? }).
 * Every view carries NOT FOR ISSUE. Data side: frame-analysis.js.
 */
import { BANNER, analysisRequest, requestAnalysis, frameResult, combos, diagram, maxValue, reactionsCsv, summaryRows } from './frame-analysis.js';
import { pebMenuItem } from './peb-menu.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
const W = 960, H = 440, PAD = 50;
const KINDS = [['shape', 'Deflected shape'], ['M', 'Moment M (kN·m)'], ['V', 'Shear V (kN)'], ['N', 'Axial P (kN, + compression)']];
const SETS = [['LRFD', 'LRFD — strength'], ['ASD', 'ASD — deflection, drift'], ['case', 'Load cases (unfactored)']];

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}
function s(tag, attrs = {}) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}
const fmt = (v, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : '—');

export function mountFrameAnalysis({ model, print, download }) {
  if (document.querySelector('[data-m3-act="analysis"]')) return;
  const btn = pebMenuItem('analysis', 'Analysis…', 'Analyse every frame line, the end walls and the bracing (on demand; NOT FOR ISSUE)', () => {});
  let res = null;
  const sel = (attrs) => h('select', { class: 'form-select form-select-sm', ...attrs });
  const lineSel = sel({ 'data-m3-a-line': true }), kindSel = sel({ 'data-m3-a-kind': true }), setSel = sel({ 'data-m3-a-set': true }), comboSel = sel({ 'data-m3-a-combo': true, style: 'min-width:20rem' });
  for (const [v, t] of KINDS) kindSel.append(h('option', { value: v, text: t }));
  for (const [v, t] of SETS) setSel.append(h('option', { value: v, text: t }));
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', 'data-m3-a-svg': '' });
  svg.style.cssText = 'background:var(--cc-bg, #fff);border:1px solid var(--cc-line, #ccc);max-height:46vh';
  const banner = h('div', { 'data-m3-a-banner': true, style: 'color:#b00020;font-weight:600;margin:.25rem 0', text: BANNER });
  const info = h('div', { 'data-m3-a-info': true, style: 'font-size:.85em;margin:.25rem 0' });
  const summary = h('div', { 'data-m3-a-summary': true, style: 'font-size:.85em;overflow:auto;max-height:18vh' });
  const reactions = h('div', { 'data-m3-a-reactions': true, style: 'font-size:.85em;overflow:auto;max-height:22vh' });
  const note = h('span', { class: 'dc-note', 'data-m3-a-note': true });
  const run = h('button', { type: 'button', class: 'btn-plot btn-sm-dc', 'data-m3-a-run': true, text: 'Run analysis' });
  const csv = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-a-csv': true, text: 'Reactions CSV', disabled: true });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const lab = (t, e) => h('label', { style: 'display:flex;gap:.3rem;align-items:center' }, h('span', { text: t }), e);
  const controls = h('div', { style: 'display:flex;flex-wrap:wrap;gap:.6rem;align-items:center' },
    lab('Frame line', lineSel), lab('Show', kindSel), lab('Set', setSel), lab('Case / combination', comboSel));
  const body = h('div', { style: 'padding:.5rem 1rem;max-height:80vh;overflow:auto;width:min(1000px,92vw)' }, banner, controls, svg, info,
    h('h3', { class: 'dc-h', style: 'font-size:.95em;margin:.5rem 0 .2rem', text: 'Summary (sway, eave movement and apex from ASD; peaks from LRFD)' }), summary,
    h('h3', { class: 'dc-h', style: 'font-size:.95em;margin:.5rem 0 .2rem', text: 'Base reactions — this frame line, this set (kN, kN·m)' }), reactions);
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-analysis': true, 'aria-labelledby': 'm3-a-h' },
    h('div', { class: 'dc-dlg' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-a-h', text: 'Analysis' }), close), body,
      h('div', { class: 'dc-dlg-foot' }, note, csv, run)));
  document.body.append(dlg);
  close.addEventListener('click', () => dlg.close());

  const fr = () => (res ? frameResult(res, lineSel.value) : null);
  function fillCombos() {
    const f = fr();
    comboSel.replaceChildren(...(f ? combos(f, setSel.value) : []).map((c) => h('option', { value: c.name, text: c.name })));
  }
  function draw() {
    svg.replaceChildren();
    const f = fr();
    if (!f || !comboSel.value) return;
    const nx = Object.values(f.nodes).map((p) => p[0]);
    const kind = kindSel.value, mx = maxValue(f, comboSel.value, kind);
    // the largest ordinate drawn at 1/8 of the frame's width (diagrams) or 1/10 (deflections) — the scale is printed
    const scale = mx > 0 ? (kind === 'shape' ? 0.10 : 0.125) * (Math.max(...nx) - Math.min(...nx)) / mx : 0;
    const d = diagram(f, comboSel.value, kind, scale);
    // the view holds the frame AND the diagram (a column's moment is drawn outside the frame)
    const pts = [...Object.values(f.nodes), ...d.members.flatMap((m) => m.curve)];
    const x0 = Math.min(...pts.map((p) => p[0])), x1 = Math.max(...pts.map((p) => p[0]));
    const y0 = Math.min(...pts.map((p) => p[1])), y1 = Math.max(...pts.map((p) => p[1]));
    const k = Math.min((W - 2 * PAD) / (x1 - x0), (H - 2 * PAD) / (y1 - y0));
    const ox = (W - (x1 - x0) * k) / 2, oy = (H - (y1 - y0) * k) / 2;
    const P = ([x, y]) => [ox + (x - x0) * k, H - oy - (y - y0) * k];
    const pl = (pts2, attrs) => svg.append(s('polyline', { points: pts2.map((p) => P(p).join(',')).join(' '), fill: 'none', ...attrs }));
    for (const m of f.members) pl([m.i, m.j], { stroke: '#999', 'stroke-width': 2 });
    for (const m of d.members) {
      if (kind === 'shape') pl(m.curve, { stroke: '#0057b8', 'stroke-width': 2 });
      else {
        svg.append(s('polygon', { points: m.curve.map((p) => P(p).join(',')).join(' '), fill: 'rgba(0,87,184,.15)', stroke: '#0057b8', 'stroke-width': 1 }));
        const [px, py] = P(m.peak.at);
        const t = s('text', { x: px + 3, y: py - 3, 'font-size': 11, fill: '#003a7a' });
        t.textContent = fmt(m.peak.v, 1);
        svg.append(t);
      }
    }
    for (const b of f.base_nodes) { const [px, py] = P(f.nodes[b]); svg.append(s('path', { d: `M${px},${py} l-7,12 h14 z`, fill: 'none', stroke: '#333' })); }
    const r = f.results[comboSel.value];
    const unit = kind === 'shape' ? 'mm' : kind === 'M' ? 'kN·m' : 'kN';
    info.textContent = `${comboSel.value} [${r.set}] — ${kind === 'shape' ? `largest movement ${fmt(d.peak?.v)} mm at ${d.peak?.node} (drawn × ${fmt(scale, 0)})` : `peak ${fmt(d.peak?.v)} ${unit} in ${d.peak?.mark}; drawn on each member's local +y side${kind === 'M' ? ' = the tension side' : ''}`}`
      + ` · largest eave movement ${fmt(r.drift)} mm, sway ${fmt(r.sway)} mm, apex ${fmt(r.apex)} mm.`;
    const rows = combos(f, setSel.value).map((c) => {
      const x = f.results[c.name].reactions;
      return h('tr', {}, h('td', { text: c.name }), ...f.base_nodes.flatMap((b) => x[b].map((v) => h('td', { style: 'text-align:right', text: fmt(v, 2) }))));
    });
    reactions.replaceChildren(h('table', { class: 'table table-sm' }, h('thead', {}, h('tr', {}, h('th', { text: 'Case / combination' }),
      ...f.base_nodes.flatMap((b) => ['H', 'V', 'M'].map((c) => h('th', { text: `${c} ${b === 'BA' ? 'A' : 'B'}` }))))), h('tbody', {}, ...rows)));
  }
  function fillSummary() {
    const rows = summaryRows(res).map((r) => h('tr', {}, h('td', { text: r.line + (r.same_as ? ` (= ${r.same_as})` : '') }),
      h('td', { text: r.sway ? `${fmt(r.sway.mm)} mm = H/${r.sway.ratio} — ${r.sway.combo}` : '—' }),
      h('td', { text: r.drift ? `${fmt(r.drift.mm)} mm — ${r.drift.combo}` : '—' }),
      h('td', { text: r.apex ? `${fmt(r.apex.mm)} mm = L/${r.apex.ratio} — ${r.apex.combo}` : '—' }),
      h('td', { text: r.maxM ? `${fmt(r.maxM.M)} kN·m in ${r.maxM.mark} — ${r.maxM.combo}` : '—' })));
    const b = res.bracing.sets.LRFD, w = res.wind_columns;
    const wmax = w.columns.reduce((a, c) => Math.max(a, Math.abs(c.sets.LRFD.inward.M), Math.abs(c.sets.LRFD.outward.M)), 0);
    summary.replaceChildren(h('table', { class: 'table table-sm' }, h('thead', {}, h('tr', {}, ...['Frame line', 'Sway (ASD)', 'Largest eave movement (ASD, incl. gravity spread)', 'Apex (ASD)', 'Max M (LRFD)'].map((t) => h('th', { text: t })))), h('tbody', {}, ...rows)),
      h('div', { text: `Longitudinal bracing (LRFD): roof diagonal ${fmt(b.roof_diagonal, 2)} kN, wall diagonal ${fmt(b.wall_diagonal, 2)} kN, strut up to ${fmt(b.max_strut, 2)} kN (end-wall pressure ${fmt(res.bracing.pressure_kpa, 3)} kN/m²).` }),
      h('div', { text: `Wind columns (LRFD, simple beams): max M ${fmt(wmax, 2)} kN·m. ${w.notes[1]}` }),
      ...(res.end_frames || []).map((e) => h('div', { text: `End-rafter frame (${e.end} end): rafter M ${fmt(e.summary.rafter_M_LRFD[1], 2)} kN·m (LRFD), wind column P ${fmt(e.summary.column_P_LRFD[2], 2)} kN; lateral restraint assumed (end-wall bracing).` })),
      h('div', { text: `Secondary steel in D: roof ${fmt(res.secondary.roof_kpa, 3)} kN/m², walls ${fmt(res.secondary.wall_kpa, 3)} kN/m² (weighed from the model).` }));
  }
  lineSel.addEventListener('change', () => { fillCombos(); draw(); });
  setSel.addEventListener('change', () => { fillCombos(); draw(); });
  kindSel.addEventListener('change', draw);
  comboSel.addEventListener('change', draw);
  btn.addEventListener('click', () => { note.textContent = res ? 'Results of the last run (not stored in the model).' : 'Run the analysis of the kept building and loads.'; dlg.showModal(); });
  run.addEventListener('click', async () => {
    let req;
    try { req = analysisRequest(model().state); } catch (err) { note.textContent = err.message; return; }
    run.disabled = true; csv.disabled = true; note.textContent = 'Solving every frame line, P-Delta (about 20 s to a minute)…';
    try {
      res = await requestAnalysis(req);
      lineSel.replaceChildren(...res.frames.map((f) => h('option', { value: f.line, text: `Line ${f.line}` + (f.same_as !== f.line ? ` (= line ${f.same_as})` : '') })));
      fillCombos(); fillSummary(); draw();
      csv.disabled = false;
      note.textContent = `Solved ${res.frames.filter((f) => f.result).length} distinct frame line(s) of ${res.frames.length}. ${BANNER}`;
      print?.(`Analysis done: ${res.frames.length} frame lines, ${res.frames[0] ? frameResult(res, res.frames[0].line).combos.length : 0} cases and combinations. ${BANNER}`);
    } catch (err) { note.textContent = err.message; }
    finally { run.disabled = false; }
  });
  csv.addEventListener('click', () => {
    if (!res) return;
    const text = reactionsCsv(res);
    if (download) { download('base-reactions.csv', text, 'text/csv'); return; }
    const a = h('a', { href: URL.createObjectURL(new Blob([text], { type: 'text/csv' })), download: 'base-reactions.csv' });
    document.body.append(a); a.click(); a.remove();
  });
  return { button: btn, dialog: dlg };
}
