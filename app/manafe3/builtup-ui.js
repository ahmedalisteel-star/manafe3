/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * builtup-ui.js — the built-up member in the Properties panel.
 *
 * DOM-free editing rules (tested in tests/bin/test-manafe3-builtup-ui.mjs):
 *   builtUpFrom(profile) → bu        a catalog I-shape as one welded segment (hw = d − 2·tf; raised to the shop minimums)
 *   setField(bu, i, key, value) → bu  one edit; keeps every splice valid: a web depth at a splice moves the neighbour's matching
 *                                     end too, and a flange WIDTH is the member's (all segments); thicknesses stay per segment
 *   addSegment(bu, L) → bu           splits the last segment at its middle (the shape does not change)
 *   removeSegment(bu, i, L) → bu     merges segment i into its neighbour
 *   segmentRows(bu, L) → rows        what the panel shows per segment: x range, d at both ends, plate weights
 * DOM:
 *   builtUpBlock(m, { edit, marks, built }) → elements for memberProps   (edit = detailcraft.js's edit(label, fn))
 *   makeBuiltUpButton(m, { edit, getProfile }) → a button that converts a member to built-up
 */
import { GRADES, STRAIGHT, MIN_WEB_T, MIN_FLANGE_T, cleanBuiltUp, plateWeights, segmentPlates } from './builtup.js';

const r1 = (v) => Math.round(v * 10) / 10;
const copy = (bu) => ({ segments: bu.segments.map((s) => ({ ...s, top: { ...s.top }, bot: { ...s.bot } })) });

export function builtUpFrom(p) {
  const I = p && p.kind === 'I';
  const tf = Math.max(MIN_FLANGE_T, Math.round(I ? p.tf : 10));
  const d = I ? p.d : 400;
  return {
    segments: [{
      length: 0, hwStart: Math.round(d - 2 * tf), hwEnd: Math.round(d - 2 * tf), tw: Math.max(MIN_WEB_T, Math.round(I ? p.tw : 6)),
      top: { b: Math.round(I ? p.bf : 200), t: tf }, bot: { b: Math.round(I ? p.bf : 200), t: tf }, grade: 'S355', straight: 'centre',
    }],
  };
}

export function setField(bu, i, key, value) {
  const b = copy(bu), s = b.segments[i];
  if (!s) throw new Error('No segment ' + (i + 1));
  const num = Number(value);
  switch (key) {
    case 'grade': s.grade = String(value); break;
    case 'straight': s.straight = String(value); break;
    case 'length': case 'tw': s[key] = num; break;
    case 'hwStart': s.hwStart = num; if (i > 0) b.segments[i - 1].hwEnd = num; break;
    case 'hwEnd': s.hwEnd = num; if (i + 1 < b.segments.length) b.segments[i + 1].hwStart = num; break;
    case 'top.t': s.top.t = num; break;
    case 'bot.t': s.bot.t = num; break;
    case 'top.b': for (const x of b.segments) x.top.b = num; break;
    case 'bot.b': for (const x of b.segments) x.bot.b = num; break;
    default: throw new Error('Unknown field ' + key);
  }
  return b;
}

export function addSegment(bu, L) {
  const c = cleanBuiltUp(bu, L);
  const b = copy(c), last = b.segments[b.segments.length - 1];
  const half = last.length / 2, mid = (last.hwStart + last.hwEnd) / 2;
  const a = { ...last, top: { ...last.top }, bot: { ...last.bot }, length: half, hwEnd: mid };
  const z = { ...last, top: { ...last.top }, bot: { ...last.bot }, length: last.length - half, hwStart: mid };
  b.segments.splice(b.segments.length - 1, 1, a, z);
  return b;
}

export function removeSegment(bu, i, L) {
  const b = copy(cleanBuiltUp(bu, L));
  if (b.segments.length < 2) throw new Error('A built-up member keeps at least one segment');
  const s = b.segments[i];
  if (i > 0) { const p = b.segments[i - 1]; p.length += s.length; p.hwEnd = s.hwEnd; if (i + 1 < b.segments.length) b.segments[i + 1].hwStart = s.hwEnd; }
  else { const n = b.segments[1]; n.length += s.length; n.hwStart = s.hwStart; }
  b.segments.splice(i, 1);
  return b;
}

export function segmentRows(bu, L) {
  const ps = segmentPlates(bu, L), ws = plateWeights(bu, L);
  return ps.map((p, i) => {
    const s = bu.segments[i];
    return { n: i + 1, x0: r1(p.x0), x1: r1(p.x1), dStart: r1(p.hwStart + s.top.t + s.bot.t), dEnd: r1(p.hwEnd + s.top.t + s.bot.t), kg: r1(ws[i].total) };
  });
}

// ---- DOM ----------------------------------------------------------------------------------------------------------

function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'text') e.textContent = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v); else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids) if (k != null) e.append(k);
  return e;
}

const FIELDS = [
  ['length', 'Length', 'Segment length along the member, mm (the last segment takes the rest)'],
  ['hwStart', 'Web start', 'Web plate depth at the segment start, mm'],
  ['hwEnd', 'Web end', 'Web plate depth at the segment end, mm'],
  ['tw', 'Web t', 'Web thickness, mm (minimum 6)'],
  ['top.b', 'Top b', 'Top flange width, mm (the same on every segment)'],
  ['top.t', 'Top t', 'Top flange thickness, mm (minimum 8)'],
  ['bot.b', 'Bot b', 'Bottom flange width, mm (the same on every segment)'],
  ['bot.t', 'Bot t', 'Bottom flange thickness, mm (minimum 8)'],
];
const get = (s, k) => (k.includes('.') ? s[k.split('.')[0]][k.split('.')[1]] : s[k]);

export function builtUpBlock(m, { edit, marks, built }) {
  const L = Math.hypot(m.end[0] - m.start[0], m.end[1] - m.start[1], m.end[2] - m.start[2]);
  const save = (label, bu) => edit(label, (tx) => tx.updateMember(m.id, { bu }));
  const try1 = (label, fn) => { try { save(label, fn()); } catch (e) { edit(label, () => { throw e; }); } };
  const rows = segmentRows(m.bu, L);
  const box = h('div', { class: 'dc-block m3-bu', 'data-m3-bu': m.id });
  box.append(h('p', { class: 'dc-sub', text: `Built-up section — ${m.bu.segments.length} segment${m.bu.segments.length > 1 ? 's' : ''}` }));
  m.bu.segments.forEach((s, i) => {
    const last = i === m.bu.segments.length - 1;
    const seg = h('fieldset', { class: 'm3-bu-seg', style: 'border:1px solid var(--cc-line, #ccc);margin:.4rem 0;padding:.3rem .5rem' });
    const asm = marks?.asmMark?.get(m.id + '.s' + (i + 1) + '.web');
    seg.append(h('legend', { style: 'font-size:.85em;width:auto;margin:0;padding:0 .3rem', text: `Segment ${i + 1}${asm ? ' · ' + asm : ''} · x ${rows[i].x0}–${rows[i].x1} · d ${rows[i].dStart}→${rows[i].dEnd} · ${rows[i].kg} kg` }));
    const grid = h('div', { style: 'display:grid;grid-template-columns:minmax(0,1fr);gap:.2rem' });
    const cell = 'display:grid;grid-template-columns:6.5em minmax(0,1fr);align-items:center;gap:.4rem;font-size:.85em;margin:0';
    const box1 = 'width:100%;min-width:0;padding:.1rem .3rem;font-size:1em';
    for (const [k, label, title] of FIELDS) {
      const inp = h('input', { type: 'number', class: 'form-control form-control-sm', style: box1, value: String(r1(get(s, k))), title, 'aria-label': `Segment ${i + 1} ${title}`, 'data-m3-field': k, disabled: k === 'length' && last });
      inp.addEventListener('change', () => try1('Built-up ' + label, () => setField(m.bu, i, k, inp.value)));
      grid.append(h('label', { style: cell, title }, label, inp));
    }
    const sel = (k, options, title) => {
      const e = h('select', { class: 'form-select form-select-sm', style: box1, title, 'data-m3-field': k });
      for (const o of options) e.append(h('option', { value: o, text: o, selected: s[k] === o }));
      e.addEventListener('change', () => try1('Built-up ' + k, () => setField(m.bu, i, k, e.value)));
      return h('label', { style: cell, title }, k === 'grade' ? 'Grade' : 'Straight', e);
    };
    grid.append(sel('grade', GRADES, 'Steel grade'), sel('straight', STRAIGHT, 'Which flange lies on the member line'));
    seg.append(grid);
    if (m.bu.segments.length > 1) seg.append(h('button', { type: 'button', class: 'btn-line btn-sm-dc', onclick: () => try1('Remove segment', () => removeSegment(m.bu, i, L)), text: 'Remove segment' }));
    box.append(seg);
  });
  const acts = h('div', { class: 'dc-actions' },
    h('button', { type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-act': 'bu-add', onclick: () => try1('Add segment', () => addSegment(m.bu, L)), text: 'Add segment' }),
    h('button', { type: 'button', class: 'btn-line btn-sm-dc', onclick: () => edit('Catalog profile', (tx) => tx.updateMember(m.id, { bu: null, profile: m.type === 'column' ? 'HEA300' : 'IPE400' })), text: 'Back to a catalog profile' }));
  box.append(acts);
  const total = (built?.parts || []).filter((p) => p.member === m.id).reduce((a, p) => a + p.weight, 0);
  if (total) box.append(h('p', { class: 'dc-muted', style: 'font-size:.85em', text: `Plates: ${r1(total)} kg gross (outline area × t × 7850; holes not deducted). Splices are points only until Phase 5. Not designed.` }));
  return box;
}

export function makeBuiltUpButton(m, { edit, getProfile }) {
  return h('button', {
    type: 'button', class: 'btn-line btn-sm-dc', 'data-m3-act': 'bu-make', title: 'Make this member a welded built-up section (tapered or constant, in segments)', text: 'Make built-up…',
    onclick: () => edit('Make built-up', (tx) => tx.updateMember(m.id, { bu: builtUpFrom(getProfile(m.profile)) })),
  });
}
