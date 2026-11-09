/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * drawings-ui.js — two panels added to the Drawings dialog (field fixes 18, 19, 23, 24), from JS (no ui.inc edit):
 *   "Drawing settings"  readability (text, dimension text, line weights, hide marks on GA plans), the GA paper, the title
 *                       block's fields (client, project, job no., revision, status) and, for the sheet shown, its paper,
 *                       scale and drawing number — kept in the model (state.m3drawings), one undo step per change
 *   "Export sheets"     tick the sheets → ONE merged PDF, or a zip of DXF files
 *   mountDrawingsUi({ dialog, model, edit, print, sheets: () => [sheet], current: () => sheet, exportSheets, remake })
 *     → { refresh() }  call it after the set is (re)made
 */
import { DRAWING_DEFAULTS, STATUSES, SCALES, cleanDrawingSettings } from '../drawings.js';
import { PAPER_KEYS, paperLabel } from '../paper.js';

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === 'text') e.textContent = v; else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v); }
  for (const k of kids) if (k) e.append(k);
  return e;
}

export function mountDrawingsUi({ dialog, model, edit, print, sheets, current, exportSheets, remake }) {
  const body = dialog.querySelector('.dc-dlg') || dialog;
  const cur = () => cleanDrawingSettings(model().state.m3drawings || {});
  const save = (label, fn) => {
    const next = cur(); fn(next);
    if (edit(label, (tx) => { tx.s.m3drawings = cleanDrawingSettings(next); })) remake();
  };
  const num = (id, step, min, max) => h('input', { id, type: 'number', step, min, max, class: 'form-control form-control-sm', style: 'width:6rem' });
  const txt = (id, w = '12rem') => h('input', { id, type: 'text', class: 'form-control form-control-sm', style: 'width:' + w });
  const sel = (id, opts) => h('select', { id, class: 'form-select form-select-sm', style: 'width:auto' }, ...opts.map(([v, t]) => h('option', { value: v, text: t })));
  const F = {
    text: num('m3d-text', '0.1', '0.5', '3'), dimText: num('m3d-dim', '0.1', '1', '10'), line: num('m3d-line', '0.1', '0.5', '3'),
    hideMarks: h('input', { id: 'm3d-hide', type: 'checkbox' }), gaPaper: sel('m3d-gapaper', PAPER_KEYS.map((k) => [k, paperLabel(k)])),
    client: txt('m3d-client'), project: txt('m3d-project'), job: txt('m3d-job', '8rem'), revision: txt('m3d-rev', '4rem'), status: sel('m3d-status', STATUSES.map((s) => [s, s])),
    sPaper: sel('m3d-spaper', [['', '(GA / set default)'], ...PAPER_KEYS.map((k) => [k, paperLabel(k)])]), sScale: sel('m3d-sscale', [['', '(largest that fits)'], ...SCALES.map((n) => [String(n), '1:' + n])]), sNumber: txt('m3d-snum', '8rem'),
  };
  const lab = (t, e) => h('label', { style: 'display:inline-flex;gap:.3rem;align-items:center;margin:.15rem .6rem .15rem 0' }, h('span', { text: t }), e);
  const shown = h('span', { class: 'dc-muted' });
  const settings = h('details', { 'data-m3-dwg-settings': true, style: 'margin:.3rem 1rem' }, h('summary', { text: 'Drawing settings (readability, paper, title block)' }),
    h('div', {}, lab('Text ×', F.text), lab('Dimension text (mm)', F.dimText), lab('Line weights ×', F.line), lab('Hide marks on GA plans', F.hideMarks), lab('GA sheets paper', F.gaPaper)),
    h('div', {}, lab('Client', F.client), lab('Project', F.project), lab('Job no.', F.job), lab('Revision', F.revision), lab('Status', F.status)),
    h('div', {}, h('strong', { text: 'This sheet ' }), shown, lab(' paper', F.sPaper), lab('scale', F.sScale), lab('drawing no.', F.sNumber)));
  const list = h('div', { style: 'max-height:9rem;overflow:auto;columns:3;font-size:.9em' });
  const pdf = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-dwg-pdf': true, text: 'Ticked → one PDF' });
  const dxf = h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-dwg-dxf': true, text: 'Ticked → DXF zip' });
  const all = h('button', { type: 'button', class: 'dc-linkbtn', text: 'all' }), none = h('button', { type: 'button', class: 'dc-linkbtn', text: 'none' });
  const exp = h('details', { 'data-m3-dwg-export': true, style: 'margin:.3rem 1rem' }, h('summary', { text: 'Export sheets (tick several)' }), h('div', {}, all, ' · ', none, ' ', pdf, ' ', dxf), list);
  const foot = dialog.querySelector('.dc-dlg-foot');
  if (foot) foot.before(settings, exp); else body.append(settings, exp);

  const ticked = () => [...list.querySelectorAll('input:checked')].map((i) => i.value);
  all.addEventListener('click', () => list.querySelectorAll('input').forEach((i) => { i.checked = true; }));
  none.addEventListener('click', () => list.querySelectorAll('input').forEach((i) => { i.checked = false; }));
  const go = async (format) => {
    const n = ticked();
    if (!n.length) { print('Tick the sheets to export first.'); return; }
    try { const r = await exportSheets({ numbers: n, format }); print(`${r.sheets.length} sheet(s) saved as ${r.file}.`); } catch (e) { print(e.message); }
  };
  pdf.addEventListener('click', () => go('pdf'));
  dxf.addEventListener('click', () => go('dxf'));

  const on = (el, label, fn) => el.addEventListener('change', () => save(label, fn));
  on(F.text, 'Drawing text size', (o) => { o.text = Number(F.text.value); });
  on(F.dimText, 'Dimension text size', (o) => { o.dimText = Number(F.dimText.value); });
  on(F.line, 'Drawing line weights', (o) => { o.line = Number(F.line.value); });
  on(F.hideMarks, 'Marks on GA plans', (o) => { o.hideMarks = F.hideMarks.checked; });
  on(F.gaPaper, 'GA paper', (o) => { o.gaPaper = F.gaPaper.value; });
  for (const k of ['client', 'project', 'job', 'revision', 'status']) on(F[k], 'Title block', (o) => { o.title[k] = F[k].value; });
  const sheetSet = (k, v) => (o) => { const id = current()?.id; if (!id) return; o.sheets[id] = { ...(o.sheets[id] || {}) }; if (v() === '' || v() == null) delete o.sheets[id][k]; else o.sheets[id][k] = k === 'scale' ? Number(v()) : v(); };
  on(F.sPaper, 'Sheet paper', sheetSet('paper', () => F.sPaper.value));
  on(F.sScale, 'Sheet scale', sheetSet('scale', () => F.sScale.value));
  on(F.sNumber, 'Drawing number', sheetSet('number', () => F.sNumber.value.trim()));

  function refresh() {
    const o = cur();
    F.text.value = o.text; F.dimText.value = o.dimText; F.line.value = o.line; F.hideMarks.checked = o.hideMarks; F.gaPaper.value = o.gaPaper;
    for (const k of ['client', 'project', 'job', 'revision', 'status']) F[k].value = o.title[k];
    const sh = current(), s = (sh && o.sheets[sh.id]) || {};
    shown.textContent = sh ? `${sh.number} (${sh.paper}, ${sh.scale})` : '';
    F.sPaper.value = s.paper || ''; F.sScale.value = s.scale ? String(s.scale) : ''; F.sNumber.value = s.number || '';
    const keep = new Set(ticked());
    list.replaceChildren(...(sheets() || []).map((x) => h('label', { style: 'display:block' }, h('input', { type: 'checkbox', value: x.number, checked: keep.has(x.number) }), ' ' + x.number + ' ' + x.title)));
  }
  return { refresh, defaults: DRAWING_DEFAULTS };
}
