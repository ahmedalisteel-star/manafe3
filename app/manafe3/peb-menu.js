/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * peb-menu.js — one "PEB" button in the Place group with a small menu of Manafe3's tools (Building…, Loads…, Analysis…),
 * so the upstream toolbar stays on one row however many tools Manafe3 adds.
 *   pebMenuItem(act, label, title, onClick) → the menu item (a button with data-m3-act = act)
 */

let menu = null;

function ensure() {
  if (menu) return menu;
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'dc-tool'; btn.dataset.m3Act = 'peb-menu'; btn.setAttribute('aria-haspopup', 'menu');
  btn.title = 'Manafe3 PEB tools: building, loads, analysis';
  btn.innerHTML = '<i class="bi bi-buildings" aria-hidden="true"></i><span>PEB</span>';
  const anchor = document.querySelector('[data-act="tool:stair"]') || document.querySelector('[data-act="tool:beam"]');
  if (anchor) anchor.after(btn); else document.querySelector('.dc-tools')?.append(btn);
  menu = document.createElement('div');
  menu.setAttribute('role', 'menu'); menu.dataset.m3PebMenu = ''; menu.hidden = true;
  menu.style.cssText = 'position:fixed;z-index:1000;background:var(--cc-bg, #fff);border:1px solid var(--cc-line, #999);padding:.25rem;display:flex;flex-direction:column;gap:.15rem';
  document.body.append(menu);
  btn.addEventListener('click', () => { const r = btn.getBoundingClientRect(); menu.style.left = r.left + 'px'; menu.style.top = r.bottom + 'px'; menu.hidden = !menu.hidden; });
  document.addEventListener('click', (e) => { if (!menu.hidden && !btn.contains(e.target) && !menu.contains(e.target)) menu.hidden = true; });
  return menu;
}

export function pebMenuItem(act, label, title, onClick) {
  const m = ensure();
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'btn-line btn-sm-dc'; b.dataset.m3Act = act; b.textContent = label; b.title = title; b.setAttribute('role', 'menuitem');
  b.addEventListener('click', () => { m.hidden = true; onClick(); });
  m.append(b);
  return b;
}
