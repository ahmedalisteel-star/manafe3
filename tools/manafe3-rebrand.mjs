#!/usr/bin/env node
/* SPDX-License-Identifier: Apache-2.0 */
/**
 * manafe3-rebrand.mjs — Manafe3 file (not part of upstream DetailCraft).
 *
 * Replaces the visible upstream product names with "Manafe3", as TRADEMARKS.md asks of a fork: the app bar, the
 * page title, devshell/app.json, the language files and the help. Re-run it after every merge of an upstream
 * DetailCraft release (`git merge detailcraft-vX.Y.Z`), then run the tests. It is idempotent.
 *
 *   node tools/manafe3-rebrand.mjs            rewrite the files
 *   node tools/manafe3-rebrand.mjs --check    list files that still need it; exit 1 if any
 *
 * Not touched on purpose (see HANDOVER.md § Rename): internal ids (slug "detailcraft", file names, the
 * detailcraft-clip / .detailcraft.json formats), code comments, and the producer strings written into exported
 * files (NC, IFC, PDF, KISS, USD), which upstream tests assert; those move in a later phase together with their tests.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const NAME = 'Manafe3';

/** Ordered: longer phrases first. Case-sensitive, so lowercase ids and getcadcraft.com URLs are never touched. */
const RULES = [
  ['CadCraft Studio', `${NAME} Desktop`],
  ['CadCraft classic', 'Classic'],
  ['DetailCraft', NAME],
  ['CadCraft', NAME],
];

/** Files whose every occurrence is visible text. */
function targets() {
  const out = [];
  const walk = (dir, test) => {
    if (!fs.existsSync(dir)) return;
    for (const n of fs.readdirSync(dir)) {
      const p = path.join(dir, n);
      if (fs.statSync(p).isDirectory()) walk(p, test);
      else if (test(p)) out.push(p);
    }
  };
  walk(path.join(ROOT, 'app/lang'), (p) => p.endsWith('.json'));
  walk(path.join(ROOT, 'app/help'), (p) => /\.(md|js)$/.test(p));
  walk(path.join(ROOT, 'devshell/site/assets/lang'), (p) => p.endsWith('.json'));
  walk(path.join(ROOT, 'devshell/site/assets/help'), (p) => p.endsWith('.md'));
  for (const f of ['devshell/index.html']) out.push(path.join(ROOT, f));
  return out;
}

/** Visible strings inside code files: [file, exact upstream text, replacement]. */
const SPOTS = [
  ['devshell/app.json', '"name": "DetailCraft"', '"name": "Manafe3"'],
  ['app/detailcraft.js', "model.state.name + ' — DetailCraft'", "model.state.name + ' — Manafe3'"],
  ['app/detailcraft.js', "[{ description: 'DetailCraft', extensions", "[{ description: 'Manafe3', extensions"],
  ['app/detailcraft.js', "[{ description: 'DetailCraft, IFC, project bundle'", "[{ description: 'Manafe3, IFC, project bundle'"],
];

function apply(text) {
  for (const [a, b] of RULES) text = text.split(a).join(b);
  return text;
}

const check = process.argv.includes('--check');
const pending = [];
for (const f of targets()) {
  const src = fs.readFileSync(f, 'utf8');
  const dst = apply(src);
  if (dst !== src) { pending.push(path.relative(ROOT, f)); if (!check) fs.writeFileSync(f, dst); }
}
for (const [rel, a, b] of SPOTS) {
  const f = path.join(ROOT, rel);
  const src = fs.readFileSync(f, 'utf8');
  if (src.includes(a)) { pending.push(rel + ' (' + b + ')'); if (!check) fs.writeFileSync(f, src.split(a).join(b)); }
}
console.log(`${check ? 'needs rebrand' : 'rebranded'}: ${pending.length} file(s)`);
if (check && pending.length) { for (const p of pending.slice(0, 40)) console.log('  ' + p); process.exit(1); }
