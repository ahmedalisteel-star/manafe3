/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * design-ui.js — PEB › "Design…" (Phase 4 step 9), per building. NOT FOR ISSUE while unverified items remain.
 *   Settings (the project's, kept in the model as state.m3design): code basis AISC / ECP / both and the governing code,
 *   target utilisation, deflection limits, uplift mode (R-factor default, the strict ratio shown beside it), stability.
 *   "Check": analysis + every member check. "Size members": the step 8 loop + purlins / girts / eave struts + wind columns
 *   and end rafters; the proposal (sizes and weight before → after) is applied with "Apply" as ONE undo step (the building
 *   regenerated with the new sizes, like the Building form); "Cancel" changes nothing.
 *   3D colours by utilisation with a legend; the results table (sort, filter, a click selects the member); the summary;
 *   calc sheets for the ticked rows or all → one printable document (print → PDF).
 * Loaded by detailcraft.js: mountDesign({ model, edit, print, select(refs), colorize(map | null), download }).
 * Data side: design.js.
 */
import { BANNER, DESIGN_DEFAULTS, RATIO_BANDS, calcSheetsHtml, cleanSettings, colorMap, designRequest, memberIdsOf, pollDesign, proposalRows,
  specWithProposal, startDesign, tableRows } from './design.js';
import { pebMenuItem } from './peb-menu.js';
import { applyBuilding, buildingRequest, buildingsOf, requestBuilding } from './peb-building.js';
import { onModelLoaded } from './panels.js';

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}
const fmt = (v, d = 3) => (v === null || v === undefined ? 'NOT EVALUATED' : Number.isFinite(Number(v)) ? Number(v).toFixed(d) : String(v));

export function mountDesign({ model, edit, print, select, colorize, download }) {
  if (document.querySelector('[data-m3-act="design"]')) return;
  const btn = pebMenuItem('design', 'Design…', 'Check and size every member of a building (NOT FOR ISSUE until the unverified items are confirmed)', () => {});
  let res = null, resBuilding = null, busy = false, colours = false;
  const sort = { key: 'ratio', dir: -1 };
  const ticked = new Set();

  const inp = (k, attrs = {}) => h('input', { class: 'form-control form-control-sm', 'data-m3-d': k, style: 'width:6rem', ...attrs });
  const sel = (k, opts) => { const s = h('select', { class: 'form-select form-select-sm', 'data-m3-d': k }); for (const [v, t] of opts) s.append(h('option', { value: v, text: t })); return s; };
  const bld = h('select', { class: 'form-select form-select-sm', 'data-m3-d-building': true });
  const f = {
    code_basis: sel('code_basis', [['both', 'AISC 360-16 and ECP 205 (side by side)'], ['AISC', 'AISC 360-16 only'], ['ECP', 'ECP 205 only']]),
    governing: sel('governing', [['AISC', 'AISC 360-16 (GCC / Oman)'], ['ECP', 'ECP 205 (Egypt)']]),
    target: inp('target', { type: 'number', step: '0.01', min: '0.5', max: '1' }),
    sway: inp('sway', { type: 'number', title: 'eave sway under wind ≤ H / n' }), rafter_Lr: inp('rafter_Lr', { type: 'number', title: 'rafter deflection under Lr ≤ L / n' }),
    purlin: inp('purlin', { type: 'number', title: 'purlins and girts ≤ L / n' }),
    uplift_method: sel('uplift_method', [['r_factor', 'R-factor (AISI I6.2.1, industry practice) — strict shown beside'], ['strict', 'Strict (free flange braced at supports only)']]),
    stability: sel('stability', [['dg25', 'Tapered members by DG 25'], ['prismatic', 'Station by station (prismatic)']]),
  };
  const lab = (t, e) => h('label', { style: 'display:flex;gap:.3rem;align-items:center' }, h('span', { text: t }), e);
  const settingsBox = h('div', { style: 'display:flex;flex-wrap:wrap;gap:.5rem .9rem;align-items:center;margin:.3rem 0' },
    lab('Building', bld), lab('Codes', f.code_basis), lab('Governing', f.governing), lab('Target', f.target), lab('Sway H /', f.sway), lab('Rafter L /', f.rafter_Lr),
    lab('Purlins, girts L /', f.purlin), lab('Uplift', f.uplift_method), lab('Stability', f.stability));
  const saveSet = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-d-save': true, text: 'Keep as project settings' });
  const check = h('button', { type: 'button', class: 'btn-plot btn-sm-dc', 'data-m3-d-check': true, text: 'Check' });
  const size = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-d-size': true, text: 'Size members' });
  const colBtn = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-d-colours': true, text: '3D colours', disabled: true });
  const calcSel = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-d-calc': true, text: 'Calc sheets (ticked)', disabled: true });
  const calcAll = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-d-calc-all': true, text: 'Calc sheets (all)', disabled: true });
  const banner = h('div', { 'data-m3-d-banner': true, style: 'color:#b00020;font-weight:600;margin:.25rem 0', text: BANNER });
  const note = h('div', { class: 'dc-note', 'data-m3-d-note': true, style: 'min-height:1.2em' });
  const legend = h('div', { 'data-m3-d-legend': true, style: 'display:flex;gap:.8rem;flex-wrap:wrap;font-size:.85em;margin:.3rem 0' },
    ...RATIO_BANDS.map((b) => h('span', { style: 'display:inline-flex;gap:.3rem;align-items:center' }, h('span', { style: `display:inline-block;width:.9em;height:.9em;background:${b.color};border:1px solid #555` }), h('span', { text: b.label }))));
  const summary = h('div', { 'data-m3-d-summary': true, style: 'font-size:.85em' });
  const proposal = h('div', { 'data-m3-d-proposal': true, style: 'font-size:.85em' });
  const filter = h('input', { class: 'form-control form-control-sm', 'data-m3-d-filter': true, placeholder: 'Filter: member, section, check, clause…', style: 'width:18rem' });
  const codeSel = sel('table_code', [['governing', 'Governing'], ['all', 'All codes'], ['AISC', 'AISC'], ['ECP', 'ECP'], ['AISI', 'AISI']]);
  const bandSel = sel('table_band', [['', 'All ratios'], ...RATIO_BANDS.map((b) => [b.key, b.label])]);
  const table = h('div', { 'data-m3-d-table': true, style: 'font-size:.82em;overflow:auto;max-height:34vh' });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const H3 = (t) => h('h3', { class: 'dc-h', style: 'font-size:.95em;margin:.5rem 0 .2rem', text: t });
  const body = h('div', { style: 'padding:.5rem 1rem;max-height:82vh;overflow:auto;width:min(1200px,94vw)' }, banner, settingsBox,
    h('div', { style: 'display:flex;gap:.5rem;flex-wrap:wrap;align-items:center' }, check, size, saveSet, colBtn, calcSel, calcAll), note, legend,
    H3('Summary'), summary, proposal, H3('Results'), h('div', { style: 'display:flex;gap:.5rem;align-items:center;margin:.2rem 0' }, filter, codeSel, bandSel), table);
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-design': true, 'aria-labelledby': 'm3-d-h' },
    h('div', { class: 'dc-dlg' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-d-h', text: 'Design' }), close), body));
  document.body.append(dlg);
  close.addEventListener('click', () => dlg.close());

  const settings = () => ({ code_basis: f.code_basis.value, governing: f.governing.value, target: f.target.value, sway: f.sway.value, rafter_Lr: f.rafter_Lr.value,
    purlin: f.purlin.value, uplift_method: f.uplift_method.value, stability: f.stability.value });
  function fillSettings() {
    const s = { ...DESIGN_DEFAULTS, ...(model().state.m3design || {}) };
    for (const [k, e] of Object.entries(f)) e.value = String(s[k] ?? '');
  }
  function fillBuildings() {
    const keep = bld.value;
    bld.replaceChildren(...buildingsOf(model().state).map((b) => h('option', { value: b.id, text: `${b.name} (${b.id})` })));
    if ([...bld.options].some((o) => o.value === keep)) bld.value = keep;
  }

  function drawSummary() {
    if (!res) { summary.replaceChildren(); return; }
    const s = res.summary;
    const w = s.weight;
    const rows = Object.entries(s.max_by_type || {}).sort().map(([t, v]) => h('tr', {}, h('td', { text: t }), h('td', { style: `color:${v.max_ratio > 1 ? '#d62828' : 'inherit'}`, text: fmt(v.max_ratio) }),
      h('td', { text: v.id || '' }), h('td', { text: v.governing || '' }), h('td', { text: v.not_evaluated ? `${v.not_evaluated} NOT EVALUATED` : '' })));
    const sv = (s.service || []).flatMap((l) => (l.checks || []).map((c) => `lines ${l.lines.join(', ')}: ${c.name} ${fmt(c.demand, 1)} mm (${c.limit}, ratio ${fmt(c.ratio)})`));
    summary.replaceChildren(
      h('div', { 'data-m3-d-weight': true, text: `Steel ${fmt(w.t, 2)} t, ${fmt(w.kg_m2, 1)} kg/m² of plan (${fmt(w.plan_m2, 0)} m²)` + (res.weight_before ? ` — before ${fmt(res.weight_before.t, 2)} t, ${fmt(res.weight_before.kg_m2, 1)} kg/m²` : '') }),
      h('div', { text: `Largest governing ratio ${fmt(s.max_ratio)}; NOT EVALUATED ${s.not_evaluated}; members resting on unconfirmed items ${s.unverified_rows}` }),
      h('table', { class: 'table table-sm' }, h('thead', {}, h('tr', {}, ...['Member type', 'Max ratio', 'Member', 'Governing check', ''].map((t) => h('th', { text: t })))), h('tbody', {}, ...rows)),
      h('div', { text: 'Serviceability: ' + (sv.join(' · ') || '—') }),
      h('details', {}, h('summary', { text: `Unconfirmed (VERIFIED False) items — ${s.unverified_items.length}` }), h('ul', {}, ...s.unverified_items.map((x) => h('li', { text: x })))));
  }

  function drawProposal() {
    proposal.replaceChildren();
    if (!res?.proposed) return;
    const spec = buildingsOf(model().state).find((b) => b.id === resBuilding)?.spec || {};
    const rows = proposalRows(spec, res.proposed);
    const apply = h('button', { type: 'button', class: 'btn-plot btn-sm-dc', 'data-m3-d-apply': true, text: 'Apply (one undo step)' });
    const cancel = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-d-cancel': true, text: 'Cancel' });
    proposal.append(H3('Proposed sizes'),
      h('div', { text: `Weight ${fmt(res.weight_before?.t, 2)} t → ${fmt(res.weight_after?.t, 2)} t (${fmt(res.weight_before?.kg_m2, 1)} → ${fmt(res.weight_after?.kg_m2, 1)} kg/m²). ${res.sizing?.cold_formed_banner || ''}` }),
      h('table', { class: 'table table-sm', 'data-m3-d-proposal-table': true }, h('thead', {}, h('tr', {}, ...['Group', 'Size', 'Now', 'Proposed'].map((t) => h('th', { text: t })))),
        h('tbody', {}, ...rows.map((r) => h('tr', { style: String(r.before) !== String(r.after) ? 'font-weight:600' : '' }, h('td', { text: r.group }), h('td', { text: r.field }), h('td', { text: String(r.before) }), h('td', { text: String(r.after) }))))),
      h('div', { style: 'display:flex;gap:.5rem' }, apply, cancel));
    cancel.addEventListener('click', () => { res = { ...res, proposed: null }; drawProposal(); note.textContent = 'Proposal cancelled: nothing changed.'; });
    apply.addEventListener('click', async () => {
      const st = model().state;
      const entry = buildingsOf(st).find((b) => b.id === resBuilding);
      if (!entry) { note.textContent = 'That building is no longer in the model.'; return; }
      const spec2 = specWithProposal(entry.spec, res.proposed);
      apply.disabled = true;
      note.textContent = 'Regenerating the building with the proposed sizes…';
      try {
        const out = await requestBuilding(buildingRequest(spec2, st));
        const crane = entry.crane;
        const r = edit('Design: apply sizes', (tx) => {
          const o = applyBuilding(tx, out, { ...spec2, grids_mode: 'none' }, { grids: 'none', id: resBuilding });
          if (crane) tx.s.m3buildings = tx.s.m3buildings.map((b) => (b.id === resBuilding ? { ...b, crane } : b));   // keep the crane runway's settings
          return o;
        });
        if (r) { note.textContent = 'Applied as one undo step. Run Check again to see the results on the model.'; print?.('Design: proposed sizes applied (NOT FOR ISSUE).'); res = null; drawAll(); setColours(false); }
      } catch (err) { note.textContent = err.message; }
      finally { apply.disabled = false; }
    });
  }

  function drawTable() {
    if (!res) { table.replaceChildren(); return; }
    const rows = tableRows(res, { filter: filter.value, sort: sort.key, dir: sort.dir, code: codeSel.value, band: bandSel.value });
    const cols = [['', null], ['Member', 'id'], ['Type', 'kind'], ['Section', 'section'], ['Ratio', 'ratio'], ['Strict', null], ['Governing check', 'governing'], ['Clause', null], ['Combination', 'combo'], ['Station', null], ['Code', 'code'], ['VERIFIED', null]];
    const head = h('tr', {}, ...cols.map(([t, k]) => {
      const th = h('th', { style: k ? 'cursor:pointer;white-space:nowrap' : '', text: t + (k && sort.key === k ? (sort.dir < 0 ? ' ▼' : ' ▲') : '') });
      if (k) th.addEventListener('click', () => { sort.dir = sort.key === k ? -sort.dir : (k === 'ratio' ? -1 : 1); sort.key = k; drawTable(); });
      return th;
    }));
    const tb = h('tbody', {}, ...rows.slice(0, 2000).map((r) => {
      const key = `${r.line_id || r.id}|${r.code}`;
      const cb = h('input', { type: 'checkbox', 'data-m3-d-tick': key });
      cb.checked = ticked.has(key);
      cb.addEventListener('click', (e) => { e.stopPropagation(); if (cb.checked) ticked.add(key); else ticked.delete(key); });
      const tr = h('tr', { 'data-m3-d-row': r.id, style: 'cursor:pointer' }, h('td', {}, cb), h('td', { text: r.id }), h('td', { text: r.kind }), h('td', { text: r.section }),
        h('td', { style: `font-weight:600;color:${r.ratio === null ? '#8a8a8a' : r.ratio > 1 ? '#d62828' : r.ratio > 0.9 ? '#f08c00' : 'inherit'}`, text: fmt(r.ratio) }),
        h('td', { text: r.strict_ratio == null ? '' : fmt(r.strict_ratio) }), h('td', { text: r.governing || '' }), h('td', { text: r.clause || '' }), h('td', { text: r.combo || '' }),
        h('td', { text: r.x == null ? '' : String(r.x) }), h('td', { text: r.code }), h('td', { title: (r.flags || []).join('\n'), text: r.verified ? 'yes' : 'NO' }));
      tr.addEventListener('click', () => {
        const ids = memberIdsOf(model().state, resBuilding, [r.id]);
        if (ids.length) select?.(ids.map((id) => ({ kind: 'member', id })));
        note.textContent = ids.length ? `${r.id} selected in the model.` : `${r.id} is not in the model (changed since the run?).`;
      });
      return tr;
    }));
    table.replaceChildren(h('table', { class: 'table table-sm' }, h('thead', {}, head), tb), rows.length > 2000 ? h('div', { text: `${rows.length - 2000} more — filter to see them` }) : '');
  }
  function drawAll() {
    drawSummary(); drawProposal(); drawTable();
    for (const b of [colBtn, calcSel, calcAll]) b.disabled = !res;
  }
  function setColours(on) {
    colours = !!on && !!res;
    colorize?.(colours ? colorMap(model().state, res, resBuilding) : null);
    colBtn.textContent = colours ? '3D colours: on' : '3D colours';
  }
  colBtn.addEventListener('click', () => setColours(!colours));
  for (const e of [filter, codeSel, bandSel]) e.addEventListener('input', drawTable);

  async function run(action) {
    if (busy) return;
    let body;
    try { body = designRequest(model().state, { building: bld.value || null, settings: settings(), action }); } catch (err) { note.textContent = err.message; return; }
    busy = true; check.disabled = true; size.disabled = true;
    const t0 = Date.now();
    note.textContent = action === 'size' ? 'Sizing (several minutes: every frame line is re-analysed until the sizes repeat)…' : 'Checking (a minute or two)…';
    try {
      const job = await startDesign(body);
      for (;;) {
        await new Promise((r) => setTimeout(r, 2000));
        const st = await pollDesign(job);
        if (st.status === 'running') { note.textContent = `${st.progress} (${Math.round((Date.now() - t0) / 1000)} s)`; continue; }
        if (st.status === 'error') throw new Error('Engine: ' + st.error);
        res = st.result; resBuilding = bld.value || buildingsOf(model().state)[0]?.id;
        break;
      }
      ticked.clear();
      drawAll();
      setColours(true);
      note.textContent = `${action === 'size' ? 'Sizing' : 'Check'} done in ${Math.round((Date.now() - t0) / 1000)} s. ${BANNER}`;
      print?.(`Design ${action} done: largest ratio ${fmt(res.summary.max_ratio)}. NOT FOR ISSUE.`);
    } catch (err) { note.textContent = err.message; }
    finally { busy = false; check.disabled = false; size.disabled = false; }
  }
  check.addEventListener('click', () => run('check'));
  size.addEventListener('click', () => run('size'));
  saveSet.addEventListener('click', () => {
    let s;
    try { s = cleanSettings(settings()); } catch (err) { note.textContent = err.message; return; }
    const flat = { code_basis: s.code_basis, governing: s.governing, target: s.target, ...s.limits, uplift_method: s.uplift_method, stability: s.stability };
    if (edit('Design settings', (tx) => { tx.s.m3design = flat; })) note.textContent = 'Kept in the model as the project\'s design settings.';
  });
  const sheets = (keys) => {
    if (!res) return;
    const meta = { project: model().state.name || '', building: buildingsOf(model().state).find((b) => b.id === resBuilding)?.name || resBuilding, date: new Date().toISOString().slice(0, 10) };
    const html = calcSheetsHtml(res, keys, meta);
    const w = window.open('', '_blank');
    if (w) { w.document.open(); w.document.write(html); w.document.close(); setTimeout(() => { try { w.focus(); w.print(); } catch { /* the user prints from the window */ } }, 400); }
    else if (download) download('calc-sheets.html', html, 'text/html');
    note.textContent = `${keys.length} calc sheet(s) opened for printing to PDF (NOT FOR ISSUE where flagged).`;
  };
  calcSel.addEventListener('click', () => { if (!ticked.size) { note.textContent = 'Tick the rows to print first (or use "all").'; return; } sheets([...ticked]); });
  calcAll.addEventListener('click', () => sheets(Object.keys(res?.calc || {})));
  btn.addEventListener('click', () => { fillBuildings(); fillSettings(); note.textContent = res ? 'Results of the last run (not stored in the model).' : 'Check a building, or size its members.'; dlg.showModal(); });
  onModelLoaded(() => { res = null; ticked.clear(); drawAll(); setColours(false); if (dlg.open) dlg.close(); });
  return { button: btn, dialog: dlg };
}
