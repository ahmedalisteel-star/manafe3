/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * output-ui.js — Manafe3's Output button "Lists" (one button, so the toolbar stays on one row), a small menu of:
 *   Plate list (CSV)       platelist.js: every plate part by mark, totals per grade and thickness
 *   C/Z punch list (CSV)   punchlist.js: every hole of every cold-formed C/Z part mark, for the roll-former
 * Loaded by detailcraft.js: mountOutputs({ built: () => built, marks: () => marks, name: () => model name, download, print })
 */
import { plateList, plateListCsv } from './platelist.js';
import { punchList, punchListCsv } from './punchlist.js';

export function mountOutputs({ built, marks, name, download, print }) {
  if (document.querySelector('[data-m3-act="lists"]')) return;
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'dc-tool'; btn.dataset.m3Act = 'lists';
  btn.title = 'Plate list and C/Z punch list (CSV)';
  btn.setAttribute('aria-haspopup', 'menu');
  btn.innerHTML = '<i class="bi bi-list-columns" aria-hidden="true"></i><span>Lists</span>';
  const anchor = document.querySelector('[data-act="bom"]');
  if (anchor) anchor.after(btn); else document.querySelector('.dc-tools')?.append(btn);
  const menu = document.createElement('div');
  menu.setAttribute('role', 'menu');
  menu.dataset.m3ListsMenu = '';
  menu.hidden = true;
  menu.style.cssText = 'position:fixed;z-index:1000;background:var(--cc-bg, #fff);border:1px solid var(--cc-line, #999);padding:.25rem;display:flex;flex-direction:column;gap:.15rem';
  const item = (act, text, run) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'btn-line btn-sm-dc'; b.dataset.m3Act = act; b.textContent = text; b.setAttribute('role', 'menuitem');
    b.addEventListener('click', () => { menu.hidden = true; run(); });
    menu.append(b);
  };
  item('plate-list', 'Plate list (CSV)', () => {
    const list = plateList(built(), marks());
    if (!list.rows.length) { print('No plates in this model.'); return; }
    download((name() || 'model') + '-plates.csv', plateListCsv(list), 'text/csv');
    print(`Plate list: ${list.rows.length} marks, ${Math.round(list.totals.reduce((a, g) => a + g.kg, 0) * 10) / 10} kg gross.`);
  });
  item('punch-list', 'C/Z punch list (CSV)', () => {
    const rows = punchList(built(), marks());
    if (!rows.length) { print('No cold-formed C or Z in this model.'); return; }
    download((name() || 'model') + '-punch.csv', punchListCsv(rows), 'text/csv');
    print(`Punch list: ${new Set(rows.map((r) => r.mark)).size} C/Z marks, ${rows.filter((r) => r.x !== '').length} holes.`);
  });
  document.body.append(menu);
  btn.addEventListener('click', () => {
    const r = btn.getBoundingClientRect();
    menu.style.left = r.left + 'px'; menu.style.top = r.bottom + 'px';
    menu.hidden = !menu.hidden;
  });
  document.addEventListener('click', (e) => { if (!menu.hidden && e.target !== btn && !btn.contains(e.target) && !menu.contains(e.target)) menu.hidden = true; });
  return btn;
}
