/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * punchlist.js — the CSV punch list for cold-formed C and Z (user decision 2026-11-05: DSTV and a CSV punch list).
 * One row per hole, per part mark:  Mark, Profile, Grade, Length mm, Qty, Face, Hole x mm, Hole y mm, Hole d mm
 *   x = along the piece from its cut start; y = across the face from its lower edge (web: from the underside of the bottom
 *   flange, as DSTV's y), so most roll-former / punching-line imports can read it. A piece without holes gets one row.
 *   punchList(built, marks) → rows;  punchListCsv(rows) → CSV text
 */

const r1 = (v) => Math.round(v * 10) / 10;

export function punchList(built, marks) {
  const rows = [];
  for (const row of marks.parts) {
    const p = built.byId.get(row.ids[0]);
    const k = p?.profile?.kind;
    if (k !== 'CFC' && k !== 'CFZ') continue;
    const base = { mark: row.mark, profile: p.profileName, grade: p.material, length: r1(p.length), qty: row.count };
    const holes = [...p.holes].sort((a, b) => a.x - b.x || a.y - b.y);
    if (!holes.length) rows.push({ ...base, face: '', x: '', y: '', d: '' });
    for (const h of holes) rows.push({ ...base, face: h.face, x: r1(h.x), y: r1(h.face === 'web' ? h.y + p.profile.H / 2 : h.y + p.profile.B / 2), d: h.d });
  }
  return rows;
}

export function punchListCsv(rows) {
  const head = ['Mark', 'Profile', 'Grade', 'Length mm', 'Qty', 'Face', 'Hole x mm', 'Hole y mm', 'Hole d mm'];
  const q = (v) => (/[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
  return [head, ...rows.map((r) => [r.mark, r.profile, r.grade, r.length, r.qty, r.face, r.x, r.y, r.d])].map((r) => r.map(q).join(',')).join('\r\n') + '\r\n';
}
