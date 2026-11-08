/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-building-ui.js — the "PEB building…" button (Place group) and its form. Loaded by detailcraft.js:
 *   mountPebBuilding({ model: () => Model, edit(label, fn), print(msg), fit() })
 * One form for the whole building (span, bays, eave, slope, frame sizes, purlins and girts, end walls, bracing, laps,
 * bolts, sections, openings). It reopens with the inputs kept in the model (state.m3building), so the same button edits
 * the building: the generated members are replaced, your own members stay. The mapping is peb-building.js.
 */
import { BUILDING_DEFAULTS, buildingRequest, requestBuilding, applyBuilding, SIZE_FIELDS } from './peb-building.js';
import { requestDefaults } from './peb-frame.js';
import { STARTER } from './coldformed.js';
import { pebMenuItem } from './peb-menu.js';
import { onModelLoaded } from './panels.js';
import { GRADES } from './builtup.js';

const GROUPS = [
  ['Building', [['grids_mode', 'Building grids', 'merge: add the building\'s grid lines where none is (nothing removed); none: leave the grids; replace: the building\'s grids replace yours (asks first)', ['merge', 'none', 'replace']], ['span', 'Span (mm)', 'Column line A to B: the columns\' outer faces'], ['n_bays', 'Number of bays'], ['bay_spacing', 'Bay spacing (mm)'],
    ['eave_height', 'Eave height (mm)', 'Where the roof line meets the outer column face'], ['roof_slope', 'Roof slope (rise/run)', '0.1 = 1:10']]],
  ['Frame sizes (span rules, editable)', [['hw_knee', 'Knee web depth (mm)'], ['hw_base', 'Column base web (mm)'], ['hw_rafter', 'Rafter web depth (mm)'],
    ['haunch_length', 'Haunch length (mm)'], ['bf', 'Flange width (mm)'], ['tf', 'Flange thickness (mm)'], ['grade', 'Grade', '', GRADES]]],
  ['Roof', [['roof_spacing_a', 'Purlin spacing A (mm)'], ['roof_spacing_b', 'Purlin spacing B (mm)'], ['roof_first_a', 'Eave strut A from eave (mm)'],
    ['roof_first_b', 'Eave strut B from eave (mm)'], ['apex_gap', 'Ridge purlin from apex (mm)', '150 to 300, along the roof']]],
  ['Walls', [['girt_spacing_a', 'Girt spacing A (mm)'], ['girt_spacing_b', 'Girt spacing B (mm)'], ['girt_first', 'First girt height (mm)'],
    ['gable_spacing', 'Gable girt spacing (mm)'], ['end_first', 'End wall at frame 1', '', ['frame', 'rafter']], ['end_last', 'End wall at the last frame', '', ['frame', 'rafter']]]],
  ['Bracing, laps, bolts', [['braced_bays', 'Braced bays', 'e.g. 1, 4 — empty = the first and the last bay', null, 'text'], ['end_braced_bays', 'End-wall braced bays', 'bays of the end walls counted from line A, e.g. 1 — empty = 1 on an end-rafter wall, none on a main-frame wall', null, 'text'], ['brace_type', 'Bracing', '', ['rod', 'angle']], ['ridge_tie', 'Ridge tie', 'Ties the two ridge purlins across the apex at every sag-rod row', ['rod', 'strap']],
    ['lap', 'Lap each side (mm)', 'empty = 10 % of each bay', null, 'text'], ['bolt', 'Bolts', '', ['M12', 'M16']]]],
  ['Sections', [['purlin', 'Purlin', 'e.g. Z200x65x20x2.0', 'cf', 'text'], ['eave_strut', 'Eave strut, jambs', 'e.g. C200x65x20x2.0', 'cf', 'text'], ['girt', 'Girt', '', 'cf', 'text']]],
  ['Openings', [['openings', 'One per line', 'wall at width sill height — e.g. A 7000 4000 0 4000 (wall A, B, first or last; sill 0 = door)', null, 'area']]],
];
const NOTE = 'Geometry only, NOT designed (Phase 4). Splices, knee, ridge and brace connections are points only (Phase 5).';

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}

function buildDialog() {
  const inputs = {};
  const list = h('datalist', { id: 'm3-cf-list' }, ...STARTER.map((s) => h('option', { value: s.name })));
  const sets = GROUPS.map(([title, fields]) => h('fieldset', { style: 'border-top:1px solid var(--cc-line, #ccc);margin:.4rem 0;padding-top:.2rem' },
    h('legend', { style: 'font-size:.9em;margin:0', text: title }),
    ...fields.map(([k, label, hint, opts, kind]) => {
      const id = 'm3-b-' + k;
      let inp;
      if (Array.isArray(opts)) { inp = h('select', { id, class: 'form-select form-select-sm' }, ...opts.map((o) => h('option', { value: o, text: o }))); }
      else if (kind === 'area') inp = h('textarea', { id, rows: '3', class: 'form-control form-control-sm', placeholder: 'A 7000 4000 0 4000' });
      else inp = h('input', { id, type: kind === 'text' ? 'text' : 'number', step: 'any', class: 'form-control form-control-sm', list: opts === 'cf' ? 'm3-cf-list' : null });
      inputs[k] = inp;
      return h('div', { style: 'display:grid;grid-template-columns:13rem 12rem;gap:.5rem;align-items:center;margin:.25rem 0' }, h('label', { for: id, text: label, title: hint || '' }), inp);
    })));
  const note = h('span', { class: 'dc-note', 'data-m3-b-note': true, text: NOTE });
  const add = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', 'data-m3-b-add': true, text: 'Make building' });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-b-h', text: 'PEB building' }), close),
    h('div', { style: 'padding:.5rem 1rem;max-height:70vh;overflow:auto' }, list, ...sets), h('div', { class: 'dc-dlg-foot' }, note, add));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-building': true, 'aria-labelledby': 'm3-b-h' }, h('div', { class: 'dc-dlg' }, form));
  close.addEventListener('click', () => dlg.close());
  return { dlg, form, inputs, note, add };
}

export function mountPebBuilding({ model, edit, print, fit }) {
  if (document.querySelector('[data-m3-act="peb-building"]')) return;
  const btn = pebMenuItem('peb-building', 'Building…', 'Make or edit the whole PEB building: frames, purlins, girts, bracing, end walls, openings', () => {});
  const ui = buildDialog();
  document.body.append(ui.dlg);
  const edited = new Set();
  for (const k of SIZE_FIELDS) ui.inputs[k].addEventListener('input', () => edited.add(k));
  const fill = async () => {
    try { const z = await requestDefaults(ui.inputs.span.value); for (const k of SIZE_FIELDS) if (!edited.has(k)) ui.inputs[k].value = String(Math.round(z[k] * 10) / 10); }
    catch (err) { ui.note.textContent = err.message; }
  };
  ui.inputs.span.addEventListener('change', fill);
  btn.addEventListener('click', () => {
    const kept = model().state.m3building;
    const vals = { ...BUILDING_DEFAULTS, grade: 'S355', ...(kept || {}), grids_mode: 'merge' };   // never remembers 'replace'
    for (const [k, inp] of Object.entries(ui.inputs)) inp.value = vals[k] ?? '';
    edited.clear();
    if (kept) SIZE_FIELDS.forEach((k) => { if (kept[k] !== undefined && kept[k] !== '') edited.add(k); });
    const n = model().state.members.filter((m) => m.gen === 'peb').length;
    ui.note.textContent = n ? `Editing the building: its ${n} generated members will be replaced (your own members stay). ` + NOTE : NOTE;
    ui.add.textContent = n ? 'Update building' : 'Make building';
    ui.dlg.showModal();
    if (!kept) fill();
  });
  ui.form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const form = Object.fromEntries(Object.entries(ui.inputs).map(([k, i]) => [k, i.value]));
    let body;
    try { body = buildingRequest(form); } catch (err) { ui.note.textContent = err.message; return; }
    if (form.grids_mode === 'replace' && !window.confirm('Replace ALL grid lines of the model with the building\'s grids? Your other grid lines will be removed (Undo brings them back).')) return;
    ui.add.disabled = true; ui.note.textContent = 'Asking the engine…';
    try {
      const res = await requestBuilding(body);
      const r = edit('PEB building', (tx) => applyBuilding(tx, res, form, { grids: form.grids_mode }));
      if (!r) { ui.note.textContent = 'The model refused the building; see the status bar.'; return; }
      ui.dlg.close();
      fit?.();
      print(`PEB building: ${r.members} members, ${r.cleats} cleats, ${r.holes} holes${r.replaced ? `, ${r.replaced} replaced` : ''}${r.gridsAdded ? `, ${r.gridsAdded} grid lines added` : ''}; braced bays ${res.braced_bays.join(', ')}. Not designed.`);
    } catch (err) { ui.note.textContent = err.message; }
    finally { ui.add.disabled = false; }
  });
  onModelLoaded(() => { if (ui.dlg.open) ui.dlg.close(); });   // field fix 3: the form held the old model's values; it refills on open
  return { button: btn, dialog: ui.dlg };
}
