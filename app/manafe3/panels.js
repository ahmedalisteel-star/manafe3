/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * panels.js — one place every Manafe3 panel hears "a different model is open now" (field fix 3). DOM-free.
 *
 *   onModelLoaded(fn) → unsubscribe     a panel registers its reset (drop results of the old model, close a form that
 *                                       holds the old model's values)
 *   modelLoaded()                       detailcraft.js calls it on the model's 'load' event (File › Open, an agent's
 *                                       model.load / model.replace, a recovered autosave) and when a new Model is set
 * A panel's error never stops the others.
 */
const fns = new Set();

export function onModelLoaded(fn) { fns.add(fn); return () => fns.delete(fn); }

export function modelLoaded() {
  let n = 0;
  for (const fn of fns) { try { fn(); n++; } catch { /* one panel's trouble is not the others' */ } }
  return n;
}
