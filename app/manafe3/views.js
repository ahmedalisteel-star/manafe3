/* Manafe3 file. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE). (Not part of upstream DetailCraft.) */
/**
 * views.js — the Elevation view on EVERY grid line, both axes (field fix 17). DOM-free.
 *
 *   elevationChoices(state) → [{ value, label, grid: { label, at, axis } }]
 *       the y lines (y = at) first, value = their label (as upstream, so saved view tabs keep working), then the x lines
 *       (x = at), value 'x:' + label. A site whose lettered grids run along x (R1: A–L at x = 0 … 60 000) gets them too.
 *   gridForChoice(state, value) → { label, at, axis } | null   (unknown → the first choice)
 */
export function elevationChoices(state) {
  const ys = (state.grids?.y || []).map((g) => ({ value: g.label, label: 'Grid ' + g.label, grid: { label: g.label, at: g.at, axis: 'y' } }));
  const xs = (state.grids?.x || []).map((g) => ({ value: 'x:' + g.label, label: 'Grid ' + g.label, grid: { label: g.label, at: g.at, axis: 'x' } }));
  return [...ys, ...xs];
}

export function gridForChoice(state, value) {
  const all = elevationChoices(state);
  return (all.find((c) => c.value === value) || all[0])?.grid || null;
}
