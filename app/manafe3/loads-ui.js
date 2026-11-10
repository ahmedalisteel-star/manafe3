/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * loads-ui.js — the "Loads…" button (Place group) and its form. Loaded by detailcraft.js:
 *   mountLoads({ model: () => Model, edit(label, fn), print(msg) })
 * The engine checks the inputs before they are kept (V and exposure are required: site facts, never defaulted).
 */
import { LOADS_DEFAULTS, loadsRequest, applyLoads, requestLoadsCheck } from './loads.js';
import { pebMenuItem } from './peb-menu.js';
import { onModelLoaded } from './panels.js';

const FIELDS = [
  ['Wind (ASCE 7-16 Ch. 28)', [['V', 'Basic wind speed V (m/s)', 'Site fact: 3-s gust at 10 m, Exposure C (ASCE 7-16 Fig. 26.5-1 or the local map)'],
    ['exposure', 'Exposure', 'Site fact', ['', 'B', 'C', 'D']], ['enclosure', 'Enclosure', '', ['enclosed', 'partially_enclosed', 'partially_open', 'open']],
    ['Kzt', 'Kzt (topography)', '1.0 on flat ground'], ['risk', 'Risk category', '', ['I', 'II', 'III', 'IV']]]],
  ['Dead and collateral (kN/m²)', [['roof_cladding', 'Roof sheeting', '', ['single', 'sandwich']], ['roof_cladding_kpa', 'Roof sheeting load', 'empty = 0.07 single / 0.12 sandwich, per m² of sloping roof'],
    ['wall_cladding', 'Wall sheeting', '', ['single', 'sandwich']], ['wall_cladding_kpa', 'Wall sheeting load', 'empty = 0.07 / 0.12, per m² of wall'],
    ['collateral', 'Collateral', 'per m² of PLAN; its own case, not in the uplift combinations']]],
  ['Roof live, analysis', [['Lo', 'Roof live Lo (kN/m²)', 'ASCE 7-16 §4.8: reduced from each member\'s tributary area by the engine'],
    ['base', 'Column bases', '', ['pinned', 'fixed']], ['lrfd', 'LRFD (strength)', '', ['yes', 'no']], ['asd', 'ASD (deflection, drift)', '', ['yes', 'no']]]],
];

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}

export function mountLoads({ model, edit, print }) {
  if (document.querySelector('[data-m3-act="loads"]')) return;
  const btn = pebMenuItem('loads', 'Loads…', 'Loads: wind, dead, collateral, roof live, bases, combinations (kept in the model)', () => {});
  const inputs = {};
  const sets = FIELDS.map(([title, fields]) => h('fieldset', { style: 'border-top:1px solid var(--cc-line, #ccc);margin:.4rem 0;padding-top:.2rem' },
    h('legend', { style: 'font-size:.9em;margin:0', text: title }),
    ...fields.map(([k, label, hint, opts]) => {
      const id = 'm3-l-' + k;
      const inp = opts ? h('select', { id, class: 'form-select form-select-sm' }, ...opts.map((o) => h('option', { value: o, text: o || '— choose —' })))
        : h('input', { id, type: 'text', inputmode: 'decimal', class: 'form-control form-control-sm' });
      inputs[k] = inp;
      return h('div', { style: 'display:grid;grid-template-columns:14rem 12rem;gap:.5rem;align-items:center;margin:.25rem 0' }, h('label', { for: id, text: label, title: hint || '' }), inp);
    })));
  const note = h('span', { class: 'dc-note', 'data-m3-l-note': true });
  const save = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', 'data-m3-l-save': true, text: 'Keep loads' });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-l-h', text: 'Loads' }), close),
    h('div', { style: 'padding:.5rem 1rem;max-height:70vh;overflow:auto' }, ...sets), h('div', { class: 'dc-dlg-foot' }, note, save));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-loads': true, 'aria-labelledby': 'm3-l-h' }, h('div', { class: 'dc-dlg' }, form));
  document.body.append(dlg);
  close.addEventListener('click', () => dlg.close());
  btn.addEventListener('click', () => {
    const vals = { ...LOADS_DEFAULTS, ...(model().state.m3loads || {}) };
    for (const [k, inp] of Object.entries(inputs)) inp.value = vals[k] ?? '';
    note.textContent = 'Basic wind speed and exposure are site facts: no defaults.';
    dlg.showModal();
  });
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(Object.entries(inputs).map(([k, i]) => [k, i.value]));
    let body;
    try { body = loadsRequest(f); } catch (err) { note.textContent = err.message; return; }
    save.disabled = true; note.textContent = 'Checking with the engine…';
    try {
      const s = await requestLoadsCheck(body);
      if (!edit('Loads', (tx) => applyLoads(tx, f))) return;
      dlg.close();
      print(`Loads kept: V ${s.V} m/s, exposure ${s.exposure}, ${s.enclosure} (GCpi ±${s.GCpi[0]}), roof ${s.roof_sheeting} + collateral ${s.collateral} kN/m², Lo ${s.Lo}, bases ${s.base}, ${s.sets.join(' + ')}.`);
    } catch (err) { note.textContent = err.message; }
    finally { save.disabled = false; }
  });
  onModelLoaded(() => { if (dlg.open) dlg.close(); });   // field fix 3: refills from the open model next time
  return { button: btn, dialog: dlg };
}
