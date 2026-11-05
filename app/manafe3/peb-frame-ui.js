/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-frame-ui.js — the "PEB frame…" button in the Place group and its small form. Loaded by detailcraft.js:
 *
 *   mountPebFrame({ model: () => Model, edit(label, fn), print(msg), fit() })
 *
 * The button opens a dialog (span, eave height, roof slope, bay spacing, number of bays); "Add frame" calls the
 * engine's POST /peb/frame and puts the returned grids, levels, columns and rafters into the model as ONE undo step.
 * The data mapping is peb-frame.js (DOM-free, tested in Node).
 */
import { FRAME_DEFAULTS, frameRequest, requestFrame, applyFrame } from './peb-frame.js';

const FIELDS = [
  ['span', 'Span (mm)', 'Column line A to B, centre lines', '100'],
  ['eave_height', 'Eave height (mm)', 'Ground to the eave', '100'],
  ['roof_slope', 'Roof slope (rise/run)', '0.1 = 1:10', '0.005'],
  ['bay_spacing', 'Bay spacing (mm)', 'Frame line to frame line', '100'],
  ['n_bays', 'Number of bays', 'Frames = bays + 1', '1'],
];

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids) if (k) e.append(k);
  return e;
}

function buildDialog() {
  const inputs = {};
  const rows = FIELDS.map(([k, label, hint, step]) => {
    const id = 'm3-peb-' + k;
    inputs[k] = h('input', { id, type: 'number', step, class: 'form-control form-control-sm', value: String(FRAME_DEFAULTS[k]), required: true });
    return h('div', { class: 'm3-peb-row', style: 'display:grid;grid-template-columns:12rem 9rem;gap:.5rem;align-items:center;margin:.35rem 0' },
      h('label', { for: id, text: label, title: hint }), inputs[k]);
  });
  const note = h('span', { class: 'dc-note', 'data-m3-peb-note': true, text: 'Placeholder IPE/HEA profiles: geometry only, not designed.' });
  const add = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', 'data-m3-peb-add': true });
  add.innerHTML = '<i class="bi bi-plus-lg" aria-hidden="true"></i> Add frame';
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' },
    h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-peb-h', text: 'PEB frame' }), close),
    h('div', { style: 'padding:.75rem 1rem' }, ...rows),
    h('div', { class: 'dc-dlg-foot' }, note, add));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-peb': true, 'aria-labelledby': 'm3-peb-h' }, h('div', { class: 'dc-dlg' }, form));
  close.addEventListener('click', () => dlg.close());
  return { dlg, form, inputs, note, add };
}

export function mountPebFrame({ model, edit, print, fit }) {
  if (document.querySelector('[data-m3-act="peb-frame"]')) return;
  const btn = h('button', { type: 'button', class: 'dc-tool', 'data-m3-act': 'peb-frame', title: 'Add a PEB portal frame on every grid line from the Manafe3 engine' });
  btn.innerHTML = '<i class="bi bi-house" aria-hidden="true"></i><span>PEB frame…</span>';
  const anchor = document.querySelector('[data-act="tool:stair"]') || document.querySelector('[data-act="tool:beam"]');
  if (anchor) anchor.after(btn); else document.querySelector('.dc-tools')?.append(btn);

  const ui = buildDialog();
  document.body.append(ui.dlg);
  btn.addEventListener('click', () => { ui.note.textContent = 'Placeholder IPE/HEA profiles: geometry only, not designed.'; ui.dlg.showModal(); });

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
      print(`PEB frame: ${frame.members.length} members on ${frame.grids.x.length} frame lines, apex ${frame.apex_height} mm. Placeholder profiles, not designed.`);
    } catch (err) {
      ui.note.textContent = err.message;
    } finally {
      ui.add.disabled = false;
    }
  });
  return { button: btn, dialog: ui.dlg };
}
