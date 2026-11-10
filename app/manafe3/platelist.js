/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * platelist.js — the plate cut list: every plate part (built-up webs and flanges, connection plates), one row per part
 * mark, with totals per grade and thickness. DOM-free. (nest.js nests bars only; plates are cut from sheet.)
 *
 *   plateList(built, marks) → { rows, totals }
 *     row   { mark, grade, t, width, length, shape: 'rectangle' | 'trapezoid', area (m² each), count, unitKg, totalKg }
 *           width × length = the plate's bounding rectangle (what is set out on the sheet); area = its true face area
 *     totals [{ grade, t, count, area, kg }]   sorted by grade, then thickness
 *   plateListCsv(list) → CSV text
 * Weights are the parts' gross weights (holes not deducted).
 */

const r1 = (v) => Math.round(v * 10) / 10;
const r3 = (v) => Math.round(v * 1000) / 1000;

function isPlate(p) {
  return p && (p.profile?.kind === 'SPL' || (p.type === 'plate' && p.profile?.kind === 'PL'));
}

export function plateList(built, marks) {
  const rows = [];
  for (const row of marks.parts) {
    const p = built.byId.get(row.ids[0]);
    if (!isPlate(p)) continue;
    const spl = p.profile.kind === 'SPL';
    const width = spl ? p.profile.vmax - p.profile.vmin : p.profile.b;
    const areaMm2 = spl ? p.profile.outlineArea : p.profile.b * p.length;
    rows.push({
      mark: row.mark, grade: p.material, t: p.profile.t, width: r1(width), length: r1(p.length),
      shape: spl ? (p.profile.outline.length === 4 ? 'trapezoid' : 'polygon') : 'rectangle',
      area: r3(areaMm2 / 1e6), count: row.count, unitKg: r3(p.weight), totalKg: r3(p.weight * row.count),
    });
  }
  rows.sort((a, b) => a.grade.localeCompare(b.grade) || a.t - b.t || a.mark.localeCompare(b.mark, 'en', { numeric: true }));
  const by = new Map();
  for (const r of rows) {
    const k = r.grade + '|' + r.t;
    if (!by.has(k)) by.set(k, { grade: r.grade, t: r.t, count: 0, area: 0, kg: 0 });
    const g = by.get(k);
    g.count += r.count; g.area += r.area * r.count; g.kg += r.totalKg;
  }
  const totals = [...by.values()].map((g) => ({ ...g, area: r3(g.area), kg: r3(g.kg) }));
  return { rows, totals };
}

export function plateListCsv(list) {
  const q = (v) => (/[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  const out = [['Mark', 'Grade', 'Thickness mm', 'Width mm', 'Length mm', 'Shape', 'Area m2 each', 'Count', 'Weight kg each', 'Weight kg total']];
  for (const r of list.rows) out.push([r.mark, r.grade, r.t, r.width, r.length, r.shape, r.area, r.count, r.unitKg, r.totalKg]);
  out.push([]);
  out.push(['Grade', 'Thickness mm', 'Plates', 'Area m2', 'Weight kg']);
  for (const g of list.totals) out.push([g.grade, g.t, g.count, g.area, g.kg]);
  return out.map((r) => r.map(q).join(',')).join('\r\n') + '\r\n';
}
