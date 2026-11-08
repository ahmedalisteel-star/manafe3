/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-building-ui.js — the "PEB building…" button (Place group) and its form. Loaded by detailcraft.js:
 *   mountPebBuilding({ model: () => Model, edit(label, fn), print(msg), fit(), selected?: () => refs })
 * One form per building (name, placement, span and its reference, bays — even or from site grids —, eave, slope, frame
 * sizes, purlins and girts, end walls, bracing, laps, bolts, sections, openings). A model holds several buildings
 * (state.m3buildings, field fix 8): the "Building" picker chooses one to edit (it opens on the building of the selected
 * member) or "New building". Updating regenerates only that building's generated members; your own members, footings
 * and the other buildings stay. The mapping is peb-building.js.
 */
import { BUILDING_DEFAULTS, buildingRequest, requestBuilding, applyBuilding, removeBuilding, buildingsOf, membersOfBuilding, buildingOfMember, SIZE_FIELDS, SPAN_REFS } from './peb-building.js';
import { requestDefaults } from './peb-frame.js';
import { STARTER } from './coldformed.js';
import { pebMenuItem } from './peb-menu.js';
import { onModelLoaded } from './panels.js';
import { addPadFootings, footingsWithoutColumn, removeFootingsWithoutColumn } from './peb-footings.js';
import { GRADES } from './builtup.js';

const NEW = '(new)';
const GROUPS = [
  ['Building', [['which', 'Building', 'the building to edit, or a new one', [NEW]], ['name', 'Name', 'e.g. STORE, F&S-1', null, 'text'],
    ['grids_mode', 'Building grids', 'merge: add the building\'s grid lines where none is (nothing removed); none: leave the grids; replace: the building\'s grids replace yours (asks first)', ['merge', 'none', 'replace']],
    ['span', 'Span (mm)', 'Column line A to B, measured as "Span measured to" says'], ['span_ref', 'Span measured to', 'outside: the columns\' outer faces; centreline: the column centrelines at the base; grid: grid lines "Grid inset" outside the steel', SPAN_REFS],
    ['grid_inset', 'Grid inset (mm)', 'span measured to grid: from the grid line in to the outer face of the column'],
    ['n_bays', 'Number of bays'], ['bay_spacing', 'Bay spacing (mm)'],
    ['bays', 'Uneven bays', 'overrides the two above: spacings "6600 6000 6000 …" or site grids "A-L" (their spacings, their labels)', null, 'text'],
    ['eave_height', 'Eave height (mm)', 'Where the roof line meets the outer column face'], ['roof_slope', 'Roof slope (rise/run)', '0.1 = 1:10'],
    ['footings', 'Footings', 'pads: a pad footing (2000 x 2000 x 600, placeholder, not designed) under every main-frame and wind column that has none', ['none', 'pads']]]],
  ['Placement on site', [['origin_x', 'Origin X (mm)', 'where the building\'s first frame line meets its span reference line A'], ['origin_y', 'Origin Y (mm)'], ['origin_z', 'Origin Z (mm)', 'the building\'s ground level'],
    ['plan_rotation', 'Plan rotation (°)', 'about Z, counter-clockwise seen from above; 90 = frames along +Y. Any angle; grids are added for multiples of 90° only']]],
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
  const del = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-b-delete': true, text: 'Delete this building', hidden: true });
  const add = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', 'data-m3-b-add': true, text: 'Make building' });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-b-h', text: 'PEB building' }), close),
    h('div', { style: 'padding:.5rem 1rem;max-height:70vh;overflow:auto' }, list, ...sets), h('div', { class: 'dc-dlg-foot' }, note, del, add));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-building': true, 'aria-labelledby': 'm3-b-h' }, h('div', { class: 'dc-dlg' }, form));
  close.addEventListener('click', () => dlg.close());
  return { dlg, form, inputs, note, add, del };
}

export function mountPebBuilding({ model, edit, print, fit, selected }) {
  if (document.querySelector('[data-m3-act="peb-building"]')) return;
  const btn = pebMenuItem('peb-building', 'Building…', 'Make or edit a PEB building (several per model): frames, purlins, girts, bracing, end walls, openings', () => {});
  const ui = buildDialog();
  document.body.append(ui.dlg);
  const edited = new Set();
  for (const k of SIZE_FIELDS) ui.inputs[k].addEventListener('input', () => edited.add(k));
  const fill = async () => {
    try { const z = await requestDefaults(ui.inputs.span.value); for (const k of SIZE_FIELDS) if (!edited.has(k)) ui.inputs[k].value = String(Math.round(z[k] * 10) / 10); }
    catch (err) { ui.note.textContent = err.message; }
  };
  ui.inputs.span.addEventListener('change', fill);

  const which = () => (ui.inputs.which.value === NEW ? null : ui.inputs.which.value);
  function load(id) {
    const st = model().state, b = buildingsOf(st).find((x) => x.id === id) || null;
    const kept = b?.spec || null;
    const vals = { ...BUILDING_DEFAULTS, grade: 'S355', ...(kept || {}), name: b?.name ?? '', grids_mode: 'merge' };   // never remembers 'replace'
    for (const [k, inp] of Object.entries(ui.inputs)) if (k !== 'which') inp.value = vals[k] ?? '';
    edited.clear();
    if (kept) SIZE_FIELDS.forEach((k) => { if (kept[k] !== undefined && kept[k] !== '') edited.add(k); });
    const n = b ? membersOfBuilding(st, b.id).length : 0;
    ui.note.textContent = b ? `Editing ${b.name}: its ${n} generated members will be replaced (your own members and the other buildings stay). ` + NOTE : NOTE;
    ui.add.textContent = b ? 'Update building' : 'Make building';
    ui.del.hidden = !b;
    if (!kept) fill();
  }
  ui.inputs.which.addEventListener('change', () => load(which()));
  btn.addEventListener('click', () => {
    const st = model().state, list = buildingsOf(st);
    ui.inputs.which.replaceChildren(...list.map((b) => h('option', { value: b.id, text: `${b.name} (${b.id})` })), h('option', { value: NEW, text: 'New building' }));
    // opens on the building of the selected member; else the first building; else a new one
    const ref = (selected?.() || []).find((r) => r.kind === 'member');
    const mine = ref ? buildingOfMember(st.members.find((m) => m.id === ref.id)) : null;
    ui.inputs.which.value = mine && list.some((b) => b.id === mine) ? mine : list[0]?.id ?? NEW;
    load(which());
    ui.dlg.showModal();
  });
  ui.del.addEventListener('click', () => {
    const id = which(); if (!id) return;
    const b = buildingsOf(model().state).find((x) => x.id === id);
    if (!window.confirm(`Delete ${b?.name || id} and its generated members? Your own members, footings and the other buildings stay (Undo brings it back).`)) return;
    const r = edit('Delete PEB building', (tx) => removeBuilding(tx, id));
    if (r) { ui.dlg.close(); print(`${b?.name || id} deleted: ${r.removed} generated members.`); }
  });
  ui.form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const form = Object.fromEntries(Object.entries(ui.inputs).filter(([k]) => k !== 'which').map(([k, i]) => [k, i.value]));
    let body;
    try { body = buildingRequest(form, model().state); } catch (err) { ui.note.textContent = err.message; return; }
    if (form.grids_mode === 'replace' && !window.confirm('Replace ALL grid lines of the model with the building\'s grids? Your other grid lines will be removed (Undo brings them back).')) return;
    ui.add.disabled = true; ui.note.textContent = 'Asking the engine…';
    try {
      const res = await requestBuilding(body);
      const r = edit('PEB building', (tx) => {
        const out = applyBuilding(tx, res, form, { grids: form.grids_mode, id: which() });
        if (form.footings === 'pads') out.footings = addPadFootings(tx, tx.s, { building: out.id });   // field fix 9, same undo step
        return out;
      });
      if (!r) { ui.note.textContent = 'The model refused the building; see the status bar.'; return; }
      ui.dlg.close();
      fit?.();
      print(`${r.name}: ${r.members} members, ${r.cleats} cleats, ${r.holes} holes${r.replaced ? `, ${r.replaced} replaced` : ''}${r.gridsAdded ? `, ${r.gridsAdded} grid lines added` : ''}${r.gridsSkipped ? ' (rotated: grid lines not added)' : ''}${r.footings ? `, ${r.footings.added} footings added` : ''}; braced bays ${res.braced_bays.join(', ')}. Not designed.`);
    } catch (err) { ui.note.textContent = err.message; }
    finally { ui.add.disabled = false; }
  });
  // field fix 9: footings no column stands on (after columns were moved or deleted)
  pebMenuItem('peb-footings-clean', 'Remove footings with no column', 'Deletes every footing that no column of the model stands on (one undo step)', () => {
    const n = footingsWithoutColumn(model().state).length;
    if (!n) { print('Every footing has a column on it.'); return; }
    const r = edit('Remove footings with no column', (tx) => removeFootingsWithoutColumn(tx, tx.s));
    if (r) print(`Removed ${r.removed} footing(s) with no column.`);
  });
  onModelLoaded(() => { if (ui.dlg.open) ui.dlg.close(); });   // field fix 3: the form held the old model's values; it refills on open
  return { button: btn, dialog: ui.dlg };
}
