/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * crane-ui.js — PEB › "Crane runway…" (field fixes 11–13): one form per building; the mapping is crane.js.
 *   mountCrane({ model: () => Model, edit(label, fn), print(msg) })
 * Geometry only: crane loads, analysis and design stay on the roadmap; the model then shows the crane warning.
 */
import { CRANE_DEFAULTS, CRANE_WARNING, applyCrane, removeCrane } from './crane.js';
import { buildingsOf } from './peb-building.js';
import { pebMenuItem } from './peb-menu.js';
import { onModelLoaded } from './panels.js';

const FIELDS = [
  ['building', 'Building', 'the PEB building the runway is in', []],
  ['sides', 'Sides', 'column line A, B or both', ['both', 'A', 'B']],
  ['from_line', 'From frame line', 'empty = the first main frame'], ['to_line', 'To frame line', 'empty = the last main frame'],
  ['rail_top', 'Rail top level (mm)', 'above the building\'s ground (origin Z)'],
  ['rail_offset', 'Rail centre from column inner face (mm)', 'measured at bracket level on the real tapered column'],
  ['rail_h', 'Rail height (mm)'], ['rail_w', 'Rail width (mm)'],
  ['girder_hw', 'Girder web depth (mm)'], ['girder_tw', 'Girder web thickness (mm)'],
  ['girder_top_b', 'Top flange width (mm)'], ['girder_top_t', 'Top flange thickness (mm)'],
  ['girder_bot_b', 'Bottom flange width (mm)'], ['girder_bot_t', 'Bottom flange thickness (mm)'],
  ['girder_grade', 'Girder grade', '', ['S355', 'S275', 'A572 Gr 50', 'St 37', 'St 44', 'St 52']],
  ['bracket', 'Bracket profile', 'catalog name, e.g. HEA300'],
];

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}

export function mountCrane({ model, edit, print }) {
  if (document.querySelector('[data-m3-act="crane"]')) return;
  const inputs = {};
  const rows = FIELDS.map(([k, label, hint, opts]) => {
    const id = 'm3-c-' + k;
    const inp = Array.isArray(opts) ? h('select', { id, class: 'form-select form-select-sm' }, ...opts.map((o) => h('option', { value: o, text: o })))
      : h('input', { id, type: ['bracket', 'from_line', 'to_line'].includes(k) ? 'text' : 'number', step: 'any', class: 'form-control form-control-sm' });
    inputs[k] = inp;
    return h('div', { style: 'display:grid;grid-template-columns:16rem 12rem;gap:.5rem;align-items:center;margin:.25rem 0' }, h('label', { for: id, text: label, title: hint || '' }), inp);
  });
  const note = h('span', { class: 'dc-note', 'data-m3-c-note': true, text: CRANE_WARNING });
  const del = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-c-remove': true, text: 'Remove runway' });
  const add = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', 'data-m3-c-add': true, text: 'Make runway' });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-c-h', text: 'Crane runway' }), close),
    h('div', { style: 'padding:.5rem 1rem;max-height:70vh;overflow:auto' }, ...rows), h('div', { class: 'dc-dlg-foot' }, note, del, add));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-crane': true, 'aria-labelledby': 'm3-c-h' }, h('div', { class: 'dc-dlg' }, form));
  document.body.append(dlg);
  close.addEventListener('click', () => dlg.close());
  const fill = () => {
    const b = buildingsOf(model().state).find((x) => x.id === inputs.building.value);
    const vals = { ...CRANE_DEFAULTS, ...(b?.crane || {}) };
    for (const [k, inp] of Object.entries(inputs)) if (k !== 'building') inp.value = vals[k] ?? '';
    add.textContent = b?.crane ? 'Update runway' : 'Make runway';
    del.hidden = !b?.crane;
  };
  inputs.building.addEventListener('change', fill);
  pebMenuItem('crane', 'Crane runway…', 'Crane runway of a PEB building: brackets, built-up girders, rails, end stops (geometry only — not analysed or designed)', () => {
    const list = buildingsOf(model().state);
    if (!list.length) { print('Make a PEB building first (PEB › Building…).'); return; }
    inputs.building.replaceChildren(...list.map((b) => h('option', { value: b.id, text: `${b.name} (${b.id})` })));
    fill();
    note.textContent = CRANE_WARNING;
    dlg.showModal();
  });
  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    const o = Object.fromEntries(Object.entries(inputs).filter(([k]) => k !== 'building').map(([k, i]) => [k, i.value]));
    const r = edit('Crane runway', (tx) => applyCrane(tx, inputs.building.value, o));
    if (!r) { note.textContent = 'The model refused the runway; see the status bar.'; return; }
    dlg.close();
    print(`Crane runway: ${r.members} members${r.replaced ? `, ${r.replaced} replaced` : ''}${r.problems.length ? '. ' + r.problems.join(' ') : ''}. ${CRANE_WARNING}`);
  });
  del.addEventListener('click', () => {
    const r = edit('Remove crane runway', (tx) => removeCrane(tx, inputs.building.value));
    if (r) { dlg.close(); print(`Crane runway removed: ${r.removed} members.`); }
  });
  onModelLoaded(() => { if (dlg.open) dlg.close(); });
  return { dialog: dlg };
}
