#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * Field fixes from the first real project (R1) — one section per item, values by hand.
 *
 * 1. Building… never deletes or replaces existing grids, levels, footings or members: grids merge (default, no
 *    duplicates) / none / replace; levels merged.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const APP = path.join(REPO, 'public_html/assets/apps/detailcraft/dev');
const mod = (f) => import(pathToFileURL(path.join(APP, f)).href);
const B = await mod('manafe3/peb-building.js');
const { Model, emptyState } = await mod('model.js');
let pass = 0, fail = 0;
const ok = (c, m, x) => { if (c) pass++; else { fail++; console.log('FAIL ' + m + (x !== undefined ? ' — ' + JSON.stringify(x).slice(0, 600) : '')); } };
const RES = JSON.parse(fs.readFileSync(path.join(REPO, 'fixtures/manafe3/building1.json'), 'utf8'));
const spec = { ...B.BUILDING_DEFAULTS };

// ---- 1. grids, levels, footings, own members kept ---------------------------------------------------------------------
{
  // a site: grids 1–3 at 0 / 6000 / 13000, A at 0 and K at 40000; levels Ground 0 and Mezz 3500; a footing; my beam
  const site = () => {
    const m = new Model(emptyState('site'));
    m.change('site', (tx) => {
      tx.setGrids({ x: [{ label: '1', at: 0 }, { label: '2', at: 6000 }, { label: '3', at: 13000 }], y: [{ label: 'A', at: 0 }, { label: 'K', at: 40000 }] });
      tx.setLevels([{ name: 'Ground', z: 0 }, { name: 'Mezz', z: 3500 }]);
      tx.addFooting({ x: 50000, y: 50000, top: 0 });
      tx.addMember({ type: 'beam', profile: 'IPE300', material: 'S355', start: [0, -3000, 3000], end: [6000, -3000, 3000] });
    });
    return m;
  };
  // building 1's grids: x 1..5 at 0, 6000, 12000, 18000, 24000; y A 0, B 24000; levels Ground 0, Eave 6000
  const m = site();
  const r = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
  const gx = m.state.grids.x, gy = m.state.grids.y;
  // merged x by hand: 0 (1, kept), 6000 (2, kept), 12000 → "3" taken → "3'", 13000 (3, kept), 18000 (4), 24000 (5)
  ok(JSON.stringify(gx.map((g) => [g.label, g.at])) === JSON.stringify([['1', 0], ['2', 6000], ["3'", 12000], ['3', 13000], ['4', 18000], ['5', 24000]]), 'x grids merged, no duplicates, mine kept', gx);
  // y: A 0 kept; B 24000 added; K 40000 kept
  ok(JSON.stringify(gy.map((g) => [g.label, g.at])) === JSON.stringify([['A', 0], ['B', 24000], ['K', 40000]]), 'y grids merged', gy);
  ok(r.gridsAdded === 4 && r.grids === 'merge', 'four lines added (12000, 18000, 24000, B)', r);
  ok(JSON.stringify(m.state.levels) === JSON.stringify([{ name: 'Ground', z: 0 }, { name: 'Mezz', z: 3500 }, { name: 'Eave', z: 6000 }]), 'levels merged (Mezz kept, Eave added)', m.state.levels);
  ok(m.state.footings.length === 1 && m.state.members.filter((x) => !x.gen).length === 1, 'my footing and my beam stay', m.state.footings.length);
  // regenerating: no further grid lines, still my things
  const r2 = m.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec));
  ok(r2.gridsAdded === 0 && m.state.grids.x.length === 6 && m.state.footings.length === 1, 'regenerating adds no duplicates', r2);

  const n = site();
  n.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec, { grids: 'none' }));
  ok(n.state.grids.x.length === 3 && n.state.grids.y.length === 2, 'none: grids untouched', n.state.grids);
  const p = site();
  p.change('PEB building', (tx) => B.applyBuilding(tx, RES, spec, { grids: 'replace' }));
  ok(p.state.grids.x.length === 5 && p.state.grids.y.map((g) => g.label).join() === 'A,B' && p.state.footings.length === 1 && p.state.levels.length === 3, 'replace: the building\'s grids; footings and levels still kept', p.state.grids);
  p.undo();
  ok(p.state.grids.x.length === 3, 'one undo brings my grids back');
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
