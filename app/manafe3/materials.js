/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * materials.js — what a member's material IS, for weights and checks. DOM-free (field fixes 2 and 15).
 *
 *   materialClass(name) → 'concrete' | 'steel'
 *       concrete: a concrete grade or word — C20 … C100, C30/37 (EN), fcu / fck (C30 fcu), "concrete", "RC", "B25"
 *       steel:    everything else (A992, S355, S350GD, St 37, SS400 …): a member is steel unless it says concrete
 *   isConcrete(name)
 *   concreteTotals(parts, footings) → { m3, parts }   the concrete volume: concrete members (area × length) + footings
 *
 * A steel profile given a concrete material is NOT weighed at 7850 kg/m³: build.js gives it weight 0, its concrete
 * volume (part.concreteM3), and a problem "geometry only — the RC member type is on the roadmap". It is left out of the
 * steel clash check (clash.js). Rebar stays the footings' bending schedule, a separate total.
 */
const CONCRETE = [
  /^C\s?\d{2,3}(\s?\/\s?\d{2,3})?(\s?(fcu|fck))?$/i,
  /\b(concrete|rc|fcu|fck)\b/i,
  /^B\s?\d{2}$/i,
  /^C\s?\d{2,3}\s?\/\s?\d{2,3}\b/i,   // 'C30/37 fck30 fcu37' (the job units' label, field fix 14)
];

export function materialClass(name) {
  const s = String(name ?? '').trim();
  return CONCRETE.some((re) => re.test(s)) ? 'concrete' : 'steel';
}
export const isConcrete = (name) => materialClass(name) === 'concrete';

export const CONCRETE_NOTE = 'concrete material on a steel profile: geometry only — not weighed as steel, left out of the steel clash check (an RC member type is on the roadmap)';

export function concreteTotals(parts, footings = []) {
  let m3 = 0, n = 0;
  for (const p of parts) if (p.concreteM3) { m3 += p.concreteM3; n++; }
  for (const f of footings) { const g = f.f || f; m3 += (g.L * g.B * g.H) / 1e9; }
  return { m3, parts: n };
}
