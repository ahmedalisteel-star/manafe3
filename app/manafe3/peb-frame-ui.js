/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-frame-ui.js — the "PEB frame…" button in the Place group and its form. Loaded by detailcraft.js:
 *
 *   mountPebFrame({ model: () => Model, edit(label, fn), print(msg), fit() })
 *
 * The form: span, eave height, roof slope, bay spacing, bays; the section (built-up, the default since Phase 1, or the
 * Phase 0 hot-rolled IPE/HEA); and the built-up sizes, filled from the engine's span rules (POST /peb/frame/defaults) and
 * filled again when the span changes, unless you edited them. "Add frame" calls POST /peb/frame and puts the grids,
 * levels and members into the model as ONE undo step. The data mapping is peb-frame.js (DOM-free, tested in Node).
 */
import { FRAME_DEFAULTS, frameRequest, requestFrame, requestDefaults, applyFrame, SIZE_FIELDS } from './peb-frame.js';
import { GRADES } from './builtup.js';

const FIELDS = [
  ['span', 'Span (mm)', 'Column line A to B: the columns\' outer faces (built-up) or centre lines (hot-rolled)', '100'],
  ['eave_height', 'Eave height (mm)', 'Ground to where the roof line meets the outer column face', '100'],
  ['roof_slope', 'Roof slope (rise/run)', '0.1 = 1:10', '0.005'],
  ['bay_spacing', 'Bay spacing (mm)', 'Frame line to frame line', '100'],
  ['n_bays', 'Number of bays', 'Frames = bays + 1', '1'],
];
const SIZE_LABELS = {
  hw_knee: ['Knee web depth', 'Web plate depth of the column top and the haunch at the knee (rule: span/30, up to 50 mm)'],
  hw_base: ['Column base web', 'Web plate depth at the column base (rule: 300)'],
  hw_rafter: ['Rafter web depth', 'Web plate depth of the rafter; the haunch ends at it (rule: max(300, knee/2))'],
  haunch_length: ['Haunch length', 'Along the rafter from the column face (rule: span/10)'],
  bf: ['Flange width', 'Every flange of the frame (rule: 200 / 250 / 300 by span)'],
  tf: ['Flange thickness', 'Every flange of the frame (rule: 10 / 12 / 16 by span; minimum 8)'],
};
const NOTE = 'Placeholder sizes from span rules: geometry only, NOT designed. Splices, knee and ridge are points only (Phase 5).';

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids) if (k) e.append(k);
  return e;
}
const row = (id, label, title, input) => h('div', { class: 'm3-peb-row', style: 'display:grid;grid-template-columns:12rem 9rem;gap:.5rem;align-items:center;margin:.3rem 0' }, h('label', { for: id, text: label, title }), input);

function buildDialog() {
  const inputs = {};
  const rows = FIELDS.map(([k, label, hint, step]) => {
    const id = 'm3-peb-' + k;
    inputs[k] = h('input', { id, type: 'number', step, class: 'form-control form-control-sm', value: String(FRAME_DEFAULTS[k]), required: true });
    return row(id, label, hint, inputs[k]);
  });
  inputs.section = h('select', { id: 'm3-peb-section', class: 'form-select form-select-sm' },
    h('option', { value: 'builtup', text: 'Built-up, tapered', selected: true }), h('option', { value: 'hot_rolled', text: 'Hot-rolled IPE/HEA' }));
  rows.push(row('m3-peb-section', 'Section', 'Built-up: welded tapered columns, a haunch at the knee, rafters (Phase 1). Hot-rolled: the Phase 0 placeholders.', inputs.section));
  const sizeRows = SIZE_FIELDS.map((k) => {
    const id = 'm3-peb-' + k;
    inputs[k] = h('input', { id, type: 'number', step: 'any', min: '1', class: 'form-control form-control-sm', 'data-m3-size': k });   // step 'any': min 1 + step 10 would allow only 1, 11, 21 …
    return row(id, SIZE_LABELS[k][0] + ' (mm)', SIZE_LABELS[k][1], inputs[k]);
  });
  inputs.grade = h('select', { id: 'm3-peb-grade', class: 'form-select form-select-sm' }, ...GRADES.map((g) => h('option', { value: g, text: g, selected: g === 'S355' })));
  sizeRows.push(row('m3-peb-grade', 'Grade', 'Steel grade of every plate', inputs.grade));
  const sizes = h('fieldset', { 'data-m3-sizes': true, style: 'border-top:1px solid var(--cc-line, #ccc);margin-top:.5rem;padding-top:.3rem' }, h('legend', { style: 'font-size:.9em;margin:0', text: 'Built-up sizes' }), ...sizeRows);
  const note = h('span', { class: 'dc-note', 'data-m3-peb-note': true, text: NOTE });
  const add = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', 'data-m3-peb-add': true });
  add.innerHTML = '<i class="bi bi-plus-lg" aria-hidden="true"></i> Add frame';
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' },
    h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-peb-h', text: 'PEB frame' }), close),
    h('div', { style: 'padding:.75rem 1rem;max-height:70vh;overflow:auto' }, ...rows, sizes),
    h('div', { class: 'dc-dlg-foot' }, note, add));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-peb': true, 'aria-labelledby': 'm3-peb-h' }, h('div', { class: 'dc-dlg' }, form));
  close.addEventListener('click', () => dlg.close());
  return { dlg, form, inputs, note, add, sizes };
}

export function mountPebFrame({ model, edit, print, fit }) {
  if (document.querySelector('[data-m3-act="peb-frame"]')) return;
  const btn = h('button', { type: 'button', class: 'dc-tool', 'data-m3-act': 'peb-frame', title: 'Add a PEB portal frame on every grid line from the Manafe3 engine' });
  btn.innerHTML = '<i class="bi bi-house" aria-hidden="true"></i><span>PEB frame…</span>';
  const anchor = document.querySelector('[data-act="tool:stair"]') || document.querySelector('[data-act="tool:beam"]');
  if (anchor) anchor.after(btn); else document.querySelector('.dc-tools')?.append(btn);

  const ui = buildDialog();
  document.body.append(ui.dlg);
  const edited = new Set();
  for (const k of SIZE_FIELDS) ui.inputs[k].addEventListener('input', () => edited.add(k));
  const fill = async () => {   // the span rules' sizes into the fields you have not edited
    try {
      const z = await requestDefaults(ui.inputs.span.value);
      for (const k of SIZE_FIELDS) if (!edited.has(k)) ui.inputs[k].value = String(Math.round(z[k] * 10) / 10);
    } catch (err) { ui.note.textContent = err.message; }
  };
  ui.inputs.span.addEventListener('change', fill);
  ui.inputs.section.addEventListener('change', () => { ui.sizes.hidden = ui.inputs.section.value === 'hot_rolled'; });
  btn.addEventListener('click', () => { ui.note.textContent = NOTE; ui.dlg.showModal(); fill(); });

  ui.form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    let body;
    try { body = frameRequest(Object.fromEntries(Object.entries(ui.inputs).map(([k, i]) => [k, i.value]))); }
    catch (err) { ui.note.textContent = err.message; return; }
    ui.add.disabled = true; ui.note.textContent = 'Asking the engine…';
    try {
      const frame = await requestFrame(body);
      const ids = edit('PEB frame', (tx) => applyFrame(tx, frame));
      if (!ids) { ui.note.textContent = 'The model refused the frame; see the status bar.'; return; }
      ui.dlg.close();
      fit?.();
      print(`PEB frame: ${frame.members.length} members on ${frame.grids.x.length} frame lines, apex ${frame.apex_height} mm. ${frame.section === 'builtup' ? 'Built-up' : 'Hot-rolled'} placeholders, not designed.`);
    } catch (err) {
      ui.note.textContent = err.message;
    } finally {
      ui.add.disabled = false;
    }
  });
  return { button: btn, dialog: ui.dlg };
}
