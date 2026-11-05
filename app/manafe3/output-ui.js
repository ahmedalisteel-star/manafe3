/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * output-ui.js — Manafe3's Output buttons. Loaded by detailcraft.js:
 *   mountOutputs({ built: () => built, marks: () => marks, name: () => model name, download(name, data, type), print })
 * "Plate list" downloads the plate cut list (platelist.js) as CSV: every plate part by mark, with totals per grade and thickness.
 */
import { plateList, plateListCsv } from './platelist.js';

export function mountOutputs({ built, marks, name, download, print }) {
  if (document.querySelector('[data-m3-act="plate-list"]')) return;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'dc-tool';
  btn.dataset.m3Act = 'plate-list';
  btn.title = 'Plate cut list (CSV): every plate by mark — built-up webs and flanges, connection plates — with totals per grade and thickness';
  btn.innerHTML = '<i class="bi bi-grid-3x3" aria-hidden="true"></i><span>Plates</span>';
  const anchor = document.querySelector('[data-act="bom"]');
  if (anchor) anchor.after(btn); else document.querySelector('.dc-tools')?.append(btn);
  btn.addEventListener('click', () => {
    const list = plateList(built(), marks());
    if (!list.rows.length) { print('No plates in this model.'); return; }
    download((name() || 'model') + '-plates.csv', plateListCsv(list), 'text/csv');
    const kg = list.totals.reduce((a, g) => a + g.kg, 0);
    print(`Plate list: ${list.rows.length} marks, ${Math.round(kg * 10) / 10} kg gross.`);
  });
  return btn;
}
