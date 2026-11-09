/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * units-ui.js — PEB › "Job units…" (field fix 14): footings metric or imperial, the metric bar mark (T / Y / Ø / H) and the
 * concrete grade (C25/30, C30/37, C35/45 — fck / fcu), kept in the model. The mapping is units.js.
 *   mountUnits({ model: () => Model, edit(label, fn), print(msg) })
 */
import { CONCRETE_GRADES, BAR_STYLES, unitsOf, setUnits, concreteLabel } from './units.js';
import { pebMenuItem } from './peb-menu.js';
import { onModelLoaded } from './panels.js';

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}

export function mountUnits({ model, edit, print }) {
  if (document.querySelector('[data-m3-act="units"]')) return;
  const sel = (id, opts) => h('select', { id, class: 'form-select form-select-sm' }, ...opts.map(([v, t]) => h('option', { value: v, text: t })));
  const system = sel('m3-u-system', [['imperial', 'Imperial — ASTM A615 bars (#3–#11), psi'], ['metric', 'Metric — BS 4449 B500 bars 8–32 mm, C-grades']]);
  const bar = sel('m3-u-bar', BAR_STYLES.map((s) => [s, s + '16 (' + { T: 'Gulf / high yield', Y: 'UK high yield', Ø: 'diameter', H: 'BS 4449 / BS 8666' }[s] + ')']));
  const conc = sel('m3-u-conc', CONCRETE_GRADES.map((g) => [g.name, concreteLabel(g.name) + ' MPa']));
  const row = (label, e) => h('div', { style: 'display:grid;grid-template-columns:11rem 20rem;gap:.5rem;align-items:center;margin:.3rem 0' }, h('label', { for: e.id, text: label }), e);
  const note = h('span', { class: 'dc-note', text: 'Applies to new PEB pad footings and to bar names in labels and the bending schedule (BS 8666 shapes when metric). Footings already placed keep their bars.' });
  const ok = h('button', { type: 'submit', class: 'btn-plot btn-sm-dc', text: 'Save units' });
  const close = h('button', { type: 'button', class: 'dc-x', 'aria-label': 'Close' });
  close.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
  const form = h('form', { method: 'dialog' }, h('div', { class: 'dc-dlg-head' }, h('h2', { class: 'dc-h', id: 'm3-u-h', text: 'Job units' }), close),
    h('div', { style: 'padding:.5rem 1rem' }, row('Footings', system), row('Metric bar mark', bar), row('Concrete grade', conc)), h('div', { class: 'dc-dlg-foot' }, note, ok));
  const dlg = h('dialog', { class: 'dc-dialog', 'data-m3-units': true, 'aria-labelledby': 'm3-u-h' }, h('div', { class: 'dc-dlg' }, form));
  document.body.append(dlg);
  close.addEventListener('click', () => dlg.close());
  pebMenuItem('units', 'Job units…', 'Footings metric or imperial, bar marks (T / Y / Ø), concrete grade', () => {
    const u = unitsOf(model().state);
    system.value = u.system; bar.value = u.bar; conc.value = u.concrete;
    dlg.showModal();
  });
  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    const r = edit('Job units', (tx) => setUnits(tx, { system: system.value, bar: bar.value, concrete: conc.value }));
    if (r) { dlg.close(); print(r.system === 'metric' ? `Job units: metric — bars ${r.bar}8–${r.bar}32, ${concreteLabel(r.concrete)} MPa.` : 'Job units: imperial (ASTM bars, psi).'); }
  });
  onModelLoaded(() => { if (dlg.open) dlg.close(); });
  return { dialog: dlg };
}
