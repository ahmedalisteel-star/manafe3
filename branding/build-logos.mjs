// Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
// Manafe3 brand — logo concepts. Writes every SVG into branding/concepts/.
// Run from the repo root:  node branding/build-logos.mjs
// The wordmark is drawn as geometry (no font needed). Only the Arabic word and the small taglines use fonts.

import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'concepts');
mkdirSync(out, { recursive: true });

// ---- palette ---------------------------------------------------------------------------------------------------
export const C = {
  navy: '#0E1A2B',      // Steel Navy  — main ink / dark background
  orange: '#F26A21',    // Primer Orange — the accent (the "3", the front frame)
  galv: '#9AA7B8',      // Galvanised grey
  galvDark: '#5E6B7D',  // Shadow steel
  light: '#F4F6F9',     // Weld white
  blue: '#0B5CAD',      // Blueprint blue (the old placeholder colour, kept as a secondary)
};
const THEMES = {
  light: { ink: C.navy, accent: C.orange, rear1: '#7F8C9E', rear2: '#C3CBD6', muted: C.galvDark },
  dark: { ink: C.light, accent: C.orange, rear1: C.galv, rear2: C.galvDark, muted: C.galv },
};
const FONT = `'Segoe UI','Helvetica Neue',Arial,sans-serif`;
const FONT_AR = `'Cairo','Tajawal','Segoe UI','Tahoma',sans-serif`;

// ---- helpers ---------------------------------------------------------------------------------------------------
const f = (n) => +n.toFixed(2);
const pairs = (a) => a.reduce((r, v, i) => (i % 2 ? r[r.length - 1].push(v) : r.push([v]), r), []);
const poly = (pts, fill, extra = '') => `<polygon points="${pairs(pts).map(([x, y]) => `${f(x)},${f(y)}`).join(' ')}" fill="${fill}"${extra}/>`;
const scaleAbout = (pts, s, cx, cy) => pts.map((v, i) => (i % 2 ? cy + (v - cy) * s : cx + (v - cx) * s));
const svg = (w, h, body, title) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${title}">` +
  `<title>${title}</title>${body}</svg>\n`;
const save = (name, text) => writeFileSync(join(out, name), text);

// ---- the wordmark: MANAFE3 in geometric block capitals (cap height 100, stem 16) --------------------------------
// Both A's are gable portal frames; the 3 is a mirrored E (and the "ع" of منافع), in the accent colour.
const GLYPHS = {
  M: { w: 84, p: [[0, 100, 0, 0, 16, 0, 42, 34, 68, 0, 84, 0, 84, 100, 68, 100, 68, 30, 42, 64, 16, 30, 16, 100]] },
  A: { w: 76, p: [[0, 100, 0, 36, 38, 0, 76, 36, 76, 100, 60, 100, 60, 72, 16, 72, 16, 100], [16, 56, 16, 43, 38, 22.2, 60, 43, 60, 56]] },
  N: { w: 72, p: [[0, 100, 0, 0, 16, 0, 56, 66, 56, 0, 72, 0, 72, 100, 56, 100, 16, 34, 16, 100]] },
  F: { w: 60, p: [[0, 0, 60, 0, 60, 16, 16, 16, 16, 42, 52, 42, 52, 58, 16, 58, 16, 100, 0, 100]] },
  E: { w: 60, p: [[0, 0, 60, 0, 60, 16, 16, 16, 16, 42, 52, 42, 52, 58, 16, 58, 16, 84, 60, 84, 60, 100, 0, 100]] },
  3: { w: 60, p: [[60, 0, 0, 0, 0, 16, 44, 16, 44, 42, 8, 42, 8, 58, 44, 58, 44, 84, 0, 84, 0, 100, 60, 100]] },
};
function word(text, { x = 0, y = 0, h = 100, gap = 18, ink, accent }) {
  const s = h / 100;
  let cx = 0;
  const parts = [];
  for (const ch of text) {
    const g = GLYPHS[ch];
    const d = g.p.map((pl) => 'M' + pairs(pl).map(([a, b]) => `${f(cx + a)},${f(b)}`).join('L') + 'Z').join('');
    parts.push(`<path fill="${ch === '3' ? accent : ink}" fill-rule="evenodd" d="${d}"/>`);
    cx += g.w + gap;
  }
  return { svg: `<g transform="translate(${f(x)},${f(y)}) scale(${f(s)})">${parts.join('')}</g>`, width: (cx - gap) * s };
}
const WORD = 'MANAFE3';

// ---- symbols (each drawn in a 120 x 120 box) -------------------------------------------------------------------
// A tapered PEB portal frame: narrow column bases, deep haunches, shallow apex — the member type Manafe3 is built for.
const FRAME = [10, 108, 18, 108, 26, 62, 60, 30, 94, 62, 102, 108, 110, 108, 110, 46, 60, 20, 10, 46];
const SYMBOLS = {
  // 1. Tapered frame: the front frame in orange, two more bays receding behind it, on a slab.
  taper: (t, { rear = true, slab = true } = {}) =>
    (rear ? poly(scaleAbout(FRAME, 0.48, 60, 70), t.rear2) + poly(scaleAbout(FRAME, 0.72, 60, 70), t.rear1) : '') +
    poly(FRAME, t.accent) +
    (slab ? `<rect x="2" y="111" width="116" height="5" rx="1" fill="${t.ink}"/>` : ''),

  // 2. M-frame: the letter M drawn as a two-span tapered frame with a valley.
  mframe: (t) => poly([14, 104, 24, 104, 30, 44, 60, 72, 90, 44, 96, 104, 106, 104, 106, 16, 60, 56, 14, 16], t.accent),

  // 3. Hex nut + I-section: the bolt and the beam.
  hex: (t) =>
    `<polygon points="60,7 106,33.5 106,86.5 60,113 14,86.5 14,33.5" fill="none" stroke="${t.ink}" stroke-width="8" stroke-linejoin="round"/>` +
    `<path fill="${t.accent}" d="M32,32H88V44H66V76H88V88H32V76H54V44H32Z"/>` +
    `<path fill="${t.accent}" d="M54,44v6l-5,-6ZM66,44v6l5,-6ZM54,76v-6l-5,6ZM66,76v-6l5,6Z"/>`,

  // 4. Isometric bay: two frames joined by purlins — the 3D model.
  iso: (t) => {
    const s = 0.72, F = (dx, dy) => FRAME.map((v, i) => (i % 2 ? dy + v * s : dx + v * s));
    const front = F(4, 30), back = F(32, 14);
    const pts = [[10, 46], [35, 33], [60, 20], [85, 33], [110, 46], [10, 108], [110, 108]];
    const lines = pts.map(([x, y]) =>
      `<line x1="${f(4 + x * s)}" y1="${f(30 + y * s)}" x2="${f(32 + x * s)}" y2="${f(14 + y * s)}" stroke="${t.rear1}" stroke-width="2.6" stroke-linecap="round"/>`).join('');
    return poly(back, t.rear2) + lines + poly(front, t.accent);
  },

  // 5. Grid bubble: a drawing grid marker reading M3, with its chain line.
  grid: (t) => {
    const m = word('M', { h: 30, ink: t.ink, accent: t.accent, x: 0, y: 0 });
    const three = word('3', { h: 30, ink: t.ink, accent: t.accent, x: 0, y: 0 });
    const s = 0.3, w = 84 * s + 6 + 60 * s, x0 = 60 - w / 2;
    return `<circle cx="60" cy="50" r="40" fill="none" stroke="${t.ink}" stroke-width="7"/>` +
      `<g transform="translate(${f(x0)},35)">${m.svg}</g><g transform="translate(${f(x0 + 84 * s + 6)},35)">${three.svg}</g>` +
      `<line x1="60" y1="93.5" x2="60" y2="120" stroke="${t.accent}" stroke-width="5" stroke-dasharray="12 4 3 4"/>`;
  },
};

// ---- seal (200 x 200): for calc sheets, drawings and the "NOT FOR ISSUE" stamp ----------------------------------
function seal(t, { top = 'PEB ENGINEERING', bottom = 'DESIGN · DETAIL · FABRICATE', ring = t.ink, id = 's', sym = 'mframe' } = {}) {
  return `<defs><path id="${id}t" d="M25,100A75,75 0 0 1 175,100"/><path id="${id}b" d="M21,100A79,79 0 0 0 179,100"/></defs>` +
    `<circle cx="100" cy="100" r="95" fill="none" stroke="${ring}" stroke-width="5"/>` +
    `<circle cx="100" cy="100" r="66" fill="none" stroke="${ring}" stroke-width="2"/>` +
    `<text font-family="${FONT}" font-weight="700" font-size="13" letter-spacing="3" fill="${ring}">` +
    `<textPath href="#${id}t" startOffset="50%" text-anchor="middle">${top}</textPath></text>` +
    `<text font-family="${FONT}" font-weight="700" font-size="10.5" letter-spacing="1.5" fill="${ring}">` +
    `<textPath href="#${id}b" startOffset="50%" text-anchor="middle">${bottom}</textPath></text>` +
    `<circle cx="20" cy="100" r="3.5" fill="${t.accent}"/><circle cx="180" cy="100" r="3.5" fill="${t.accent}"/>` +
    `<g transform="translate(62.8,${sym === 'taper' ? 52 : 54}) scale(0.62)">${SYMBOLS[sym](t)}</g>` +
    word(WORD, { x: 61.26, y: 130, h: 13, ink: t.ink, accent: t.accent }).svg;
}

// ---- lockups ---------------------------------------------------------------------------------------------------
function lockupH(t, sym, tagline = 'DESIGN · DETAIL · FABRICATE') {
  const w = word(WORD, { x: 140, y: 22, h: 44, ...t });
  return svg(Math.ceil(140 + w.width + 6), 120,
    `<g>${SYMBOLS[sym](t)}</g>${w.svg}` +
    `<text x="141" y="101" font-family="${FONT}" font-weight="600" font-size="12" fill="${t.muted}" textLength="${f(w.width - 2)}" lengthAdjust="spacing">${tagline}</text>`,
    'Manafe3');
}
function lockupStacked(t, sym) {
  const w = word(WORD, { h: 34, ...t });
  const x = (300 - w.width) / 2;
  return svg(300, 222,
    `<g transform="translate(90,0)">${SYMBOLS[sym](t)}</g>` +
    word(WORD, { x, y: 142, h: 34, ...t }).svg +
    `<text x="${f(x + 1)}" y="210" font-family="${FONT}" font-weight="600" font-size="11" fill="${t.muted}" textLength="${f(w.width - 2)}" lengthAdjust="spacing">DESIGN · DETAIL · FABRICATE</text>`,
    'Manafe3');
}
function lockupBilingual(t, sym) {
  const w = word(WORD, { x: 140, y: 38, h: 44, ...t });
  const dx = 140 + w.width + 22;
  return svg(Math.ceil(dx + 150), 120,
    `<g>${SYMBOLS[sym](t)}</g>${w.svg}` +
    `<rect x="${f(dx)}" y="30" width="3" height="60" fill="${t.accent}"/>` +
    `<text x="${f(dx + 145)}" y="80" text-anchor="end" font-family="${FONT_AR}" font-weight="700" font-size="54" fill="${t.ink}">منافع</text>`,
    'Manafe3 — منافع');
}
function wordOnly(t) {
  const w = word(WORD, { h: 100, ...t });
  return svg(Math.ceil(w.width), 100, w.svg, 'Manafe3');
}

// ---- app icons (rounded tile) -----------------------------------------------------------------------------------
function tile(sym, opts = {}) {
  const t = THEMES.dark;
  const k = opts.scale ?? 0.78, o = (120 - 120 * k) / 2;
  return svg(120, 120,
    `<rect width="120" height="120" rx="26" fill="${C.navy}"/>` +
    `<g transform="translate(${f(o)},${f(o + (opts.dy ?? 0))}) scale(${k})">${SYMBOLS[sym](t, opts)}</g>`,
    'Manafe3');
}

// ---- animated loader: the bays are erected back to front, then the slab ----------------------------------------
function loader(t) {
  return svg(120, 120,
    `<style>.p{transform-box:fill-box;transform-origin:50% 100%;animation:up 2.8s cubic-bezier(.2,.8,.2,1) infinite;opacity:0}` +
    `.d1{animation-delay:.35s}.d2{animation-delay:.7s}.s{transform-box:fill-box;transform-origin:0 50%;animation:slab 2.8s ease-out infinite}` +
    `@keyframes up{0%{opacity:0;transform:translateY(10px) scaleY(.4)}22%,82%{opacity:1;transform:none}100%{opacity:0}}` +
    `@keyframes slab{0%{transform:scaleX(0)}18%,82%{transform:scaleX(1);opacity:1}100%{opacity:0}}` +
    `@media (prefers-reduced-motion:reduce){.p,.s{animation:none;opacity:1}}</style>` +
    poly(scaleAbout(FRAME, 0.48, 60, 70), t.rear2, ' class="p"') +
    poly(scaleAbout(FRAME, 0.72, 60, 70), t.rear1, ' class="p d1"') +
    poly(FRAME, t.accent, ' class="p d2"') +
    `<rect class="s" x="2" y="111" width="116" height="5" rx="1" fill="${t.ink}"/>`,
    'Manafe3 loading');
}

// ---- write everything ------------------------------------------------------------------------------------------
for (const [mode, t] of Object.entries(THEMES)) {
  for (const sym of Object.keys(SYMBOLS)) {
    save(`symbol-${sym}-${mode}.svg`, svg(120, 120, SYMBOLS[sym](t), 'Manafe3'));
    save(`lockup-${sym}-${mode}.svg`, lockupH(t, sym));
  }
  save(`stacked-taper-${mode}.svg`, lockupStacked(t, 'taper'));
  save(`stacked-mframe-${mode}.svg`, lockupStacked(t, 'mframe'));
  save(`bilingual-taper-${mode}.svg`, lockupBilingual(t, 'taper'));
  save(`bilingual-mframe-${mode}.svg`, lockupBilingual(t, 'mframe'));
  save(`wordmark-${mode}.svg`, wordOnly(t));
  save(`seal-${mode}.svg`, svg(200, 200, seal(t), 'Manafe3 seal'));
  save(`loader-${mode}.svg`, loader(t));
}
const red = '#C62828';
save('stamp-not-for-issue.svg', svg(200, 200,
  `<g transform="rotate(-12 100 100)" opacity="0.92">${seal({ ink: red, accent: red, rear1: '#E08A8A', rear2: '#F2C4C4' },
    { top: 'NOT FOR ISSUE', bottom: 'CHECKS NOT VERIFIED', ring: red, id: 'n' })}</g>`, 'NOT FOR ISSUE'));
save('icon-taper.svg', tile('taper'));
save('icon-taper-small.svg', tile('taper', { rear: false, slab: false, scale: 0.9, dy: -3 }));
// The app's favicon and app-bar mark: concept B, the M-frame (chosen 2026-11-05). favicon-32.png and favicon.ico are
// rendered from this file — see branding/README.md.
writeFileSync(join(here, '..', 'devshell', 'site', 'favicon.svg'),
  tile('mframe', { scale: 0.8 }).replace('<title>', '<!-- Manafe3 logo, concept B M-frame (branding/build-logos.mjs) --><title>'));
save('icon-mframe.svg', tile('mframe', { scale: 0.8 }));
save('icon-hex.svg', tile('hex', { scale: 0.8 }));
save('icon-grid.svg', tile('grid', { scale: 0.8 }));
console.log('logo concepts written to', out);
