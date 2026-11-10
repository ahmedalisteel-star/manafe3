/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * units.js — the job's footing units (field fix 14), kept in the model (state.m3units). DOM-free.
 *
 *   UNITS_DEFAULTS   { system: 'imperial' | 'metric', bar: 'T' | 'Y' | 'Ø' | 'H', concrete: 'C30/37' }
 *   CONCRETE_GRADES  EN 206 Table 12 strength classes used here: C25/30, C30/37, C35/45 — fck (cylinder) / fck,cube (the
 *                    "fcu" of BS 8110 practice), MPa
 *   METRIC_BARS      BS 4449 B500 sizes 8 – 32 mm (the bar table is rebar.js: mass from the nominal section × 7850,
 *                    bends to BS 8666:2020)
 *   unitsOf(state)   the job's units (defaults filled in; unknown values refused back to the default)
 *   barNaming(state, fallback)   the bar-name style for labels and the bending schedule: metric → 'T' / 'Y' / 'Ø' / 'H'
 *                    (T16, Y16, Ø16, H16 — the same BS 4449 bar); imperial → the app's own setting (fallback)
 *   concreteLabel(name) 'C30/37 fck30 fcu37'   (≤ 30 characters, the footing's concrete field)
 *   footingDefaults(state) → { concrete, mat, starters }  metric: H16 @ 250 both ways, starters H20 (as upstream's EU
 *                    setting), the job's grade; imperial: FOOTING_DEFAULTS. Placeholders, NOT designed.
 */
import { FOOTING_DEFAULTS } from '../rebar.js';

export const UNITS_DEFAULTS = Object.freeze({ system: 'imperial', bar: 'T', concrete: 'C30/37' });
export const CONCRETE_GRADES = Object.freeze([
  { name: 'C25/30', fck: 25, fcu: 30 },
  { name: 'C30/37', fck: 30, fcu: 37 },
  { name: 'C35/45', fck: 35, fcu: 45 },
]);
export const METRIC_BARS = ['H8', 'H10', 'H12', 'H16', 'H20', 'H25', 'H32'];
export const BAR_STYLES = ['T', 'Y', 'Ø', 'H'];

export function unitsOf(state) {
  const u = { ...UNITS_DEFAULTS, ...(state?.m3units || {}) };
  if (!['imperial', 'metric'].includes(u.system)) u.system = UNITS_DEFAULTS.system;
  if (!BAR_STYLES.includes(u.bar)) u.bar = UNITS_DEFAULTS.bar;
  if (!CONCRETE_GRADES.some((g) => g.name === u.concrete)) u.concrete = UNITS_DEFAULTS.concrete;
  return u;
}

export function barNaming(state, fallback = 'imperial') {
  const u = unitsOf(state);
  return u.system === 'metric' ? u.bar : fallback;
}

export function concreteLabel(name) {
  const g = CONCRETE_GRADES.find((x) => x.name === name) || CONCRETE_GRADES[1];
  return `${g.name} fck${g.fck} fcu${g.fcu}`;
}

export function footingDefaults(state) {
  const u = unitsOf(state);
  if (u.system !== 'metric') return { concrete: FOOTING_DEFAULTS.concrete, mat: { ...FOOTING_DEFAULTS.mat }, starters: { ...FOOTING_DEFAULTS.starters } };
  return { concrete: concreteLabel(u.concrete), mat: { ...FOOTING_DEFAULTS.mat, barX: 'H16', barY: 'H16' }, starters: { ...FOOTING_DEFAULTS.starters, bar: 'H20' } };
}

/** Sets the job's units (inside model.change). */
export function setUnits(tx, u) {
  const clean = unitsOf({ m3units: u });
  tx.s.m3units = clean;
  return clean;
}
