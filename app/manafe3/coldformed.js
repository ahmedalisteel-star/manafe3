/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * coldformed.js — Phase 2 shapes the DetailCraft table does not have. DOM-free. mm. Hooked into profiles.js.
 *
 *   lipped C   kind CFC  name 'C200x65x20x2.0'   H (depth) × B (flange) × D (lip) × t, inside radius r (default r = t)
 *   lipped Z   kind CFZ  name 'Z200x65x20x2.0'   the same dimensions; equal flanges, top flange to +u, bottom to −u
 *   round rod  kind RD   name 'RD20'             a sag rod or a bracing rod, d = the nominal (thread) diameter
 *   metric angle         name 'L50x5'            → the table's own L kind (b, t; equal legs, no root radius)
 * A job catalogue entry (a custom profile of kind CFC / CFZ in state.profiles) carries its own r; a bare name uses r = t.
 *
 *   m3Parse(name) → profile fields or null      m3Shape(p) → { loops, area } for CFC / CFZ / RD, else null
 *   m3Check(p) → null or a plain message        cfArea(p) → exact area of a lipped C / Z, mm²
 *   STARTER — the generic starter catalogue (user decision 2026-11-05): geometry only; design properties (A, Ix, Se …)
 *   come from the supplier's table before Phase 4 (bimsteelauto design/purlins.py never derives them from dimensions).
 *
 * Exact area of a lipped C or Z (centreline × t, corners as quarter circles of centreline radius rm = r + t/2):
 *   A = t · [ (H − 2(r+t)) + 2(B − 2(r+t)) + 2(D − (r+t)) + 4 · (π/2) · rm ]
 * The outline drawn for the 3D view follows the same centreline offset by ±t/2 (arcs in a few segments).
 */

const NUM = '(\\d+(?:\\.\\d+)?)';
const X = '\\s*[xX*]\\s*';
const CZ_RE = new RegExp('^([CZ])\\s*' + NUM + X + NUM + X + NUM + X + NUM + '$', 'i');
const RD_RE = new RegExp('^RD\\s*' + NUM + '$', 'i');
const LM_RE = new RegExp('^L\\s*' + NUM + X + NUM + '$', 'i');
const fmt = (v) => String(Number(Number(v).toFixed(2)));

export function cfName(kind, H, B, D, t) { return (kind === 'CFZ' ? 'Z' : 'C') + fmt(H) + 'x' + fmt(B) + 'x' + fmt(D) + 'x' + Number(t).toFixed(1); }

export function m3Check(p) {
  if (p.kind === 'CFC' || p.kind === 'CFZ') {
    const { H, B, D, t, r } = p;
    if (!(t > 0 && t <= 8)) return 'Cold-formed thickness must be above 0 and at most 8 mm';
    if (!(r >= 0 && r <= 4 * t)) return 'The inside radius must be 0 to 4 × t';
    if (!(B > 2 * (r + t) && H > 4 * (r + t) && D > r + t && D < H / 2)) return 'Depth, flange and lip do not make a lipped section with that thickness and radius';
    return null;
  }
  if (p.kind === 'RD') return p.d > 0 && p.d <= 100 ? null : 'A rod diameter must be above 0 and at most 100 mm';
  return null;
}

/** Profile fields from a name, or null. */
export function m3Parse(name) {
  const s = String(name || '').trim();
  let m;
  if ((m = s.match(CZ_RE))) {
    const kind = m[1].toUpperCase() === 'Z' ? 'CFZ' : 'CFC', H = +m[2], B = +m[3], D = +m[4], t = +m[5];
    const p = { name: cfName(kind, H, B, D, t), kind, family: kind, source: 'param', H, B, D, t, r: t };
    return m3Check(p) ? null : p;
  }
  if ((m = s.match(RD_RE))) { const d = +m[1]; const p = { name: 'RD' + fmt(d), kind: 'RD', family: 'RD', source: 'param', d }; return m3Check(p) ? null : p; }
  if ((m = s.match(LM_RE))) {
    const b = +m[1], t = +m[2];
    if (!(b > 0 && t > 0 && t < b / 2 && b <= 300)) return null;
    return { name: 'L' + fmt(b) + 'x' + fmt(t), kind: 'L', family: 'L-EN', source: 'param', b, t };
  }
  return null;
}

export function cfArea({ H, B, D, t, r }) {
  const rm = r + t / 2;
  return t * ((H - 2 * (r + t)) + 2 * (B - 2 * (r + t)) + 2 * (D - (r + t)) + 4 * (Math.PI / 2) * rm);
}

/** The sharp centreline of a lipped C / Z (C: web at −u, flanges to +u; Z: top flange to +u, bottom to −u). */
function centreline(p) {
  const { H, B, D, t } = p;
  const vt = H / 2 - t / 2, vb = -H / 2 + t / 2, lip = D - t / 2;
  if (p.kind === 'CFC') {
    const u0 = -B / 2 + t / 2, u1 = B / 2 - t / 2;
    return [[u1, vt - lip], [u1, vt], [u0, vt], [u0, vb], [u1, vb], [u1, vb + lip]];
  }
  const a = B - t;
  return [[a, vt - lip], [a, vt], [0, vt], [0, vb], [-a, vb], [-a, vb + lip]];
}

/** Round the interior corners of a polyline with radius rm (arcs in n segments). */
function fillet(pts, rm, n = 4) {
  if (!(rm > 0)) return pts;
  const out = [pts[0]];
  for (let i = 1; i < pts.length - 1; i++) {
    const [A, P, Bq] = [pts[i - 1], pts[i], pts[i + 1]];
    const d1 = norm2([P[0] - A[0], P[1] - A[1]]), d2 = norm2([Bq[0] - P[0], Bq[1] - P[1]]);
    const cross = d1[0] * d2[1] - d1[1] * d2[0], cosT = d1[0] * d2[0] + d1[1] * d2[1];
    const theta = Math.atan2(Math.abs(cross), cosT);               // the turn
    const L = rm * Math.tan(theta / 2);
    const T1 = [P[0] - d1[0] * L, P[1] - d1[1] * L];
    const side = cross > 0 ? 1 : -1;                                // centre on the inside of the turn
    const C = [T1[0] - side * d1[1] * rm, T1[1] + side * d1[0] * rm];
    const a0 = Math.atan2(T1[1] - C[1], T1[0] - C[0]);
    for (let k = 0; k <= n; k++) { const a = a0 + side * theta * k / n; out.push([C[0] + rm * Math.cos(a), C[1] + rm * Math.sin(a)]); }
  }
  out.push(pts[pts.length - 1]);
  return out;
}
function norm2(v) { const l = Math.hypot(v[0], v[1]); return [v[0] / l, v[1] / l]; }

/** Offset an open polyline by ±h (mitred) into one closed outline, counter-clockwise, centred on its box. */
function thicken(pts, h) {
  const nrm = (a, b) => { const d = norm2([b[0] - a[0], b[1] - a[1]]); return [-d[1], d[0]]; };
  const off = (sgn) => pts.map((P, i) => {
    const n1 = i > 0 ? nrm(pts[i - 1], P) : null, n2 = i < pts.length - 1 ? nrm(P, pts[i + 1]) : null;
    let n = n1 && n2 ? norm2([n1[0] + n2[0], n1[1] + n2[1]]) : (n1 || n2);
    const k = n1 && n2 ? 1 / Math.max(0.2, n[0] * n1[0] + n[1] * n1[1]) : 1;
    return [P[0] + sgn * n[0] * h * k, P[1] + sgn * n[1] * h * k];
  });
  let loop = [...off(1), ...off(-1).reverse()];
  if (area2(loop) < 0) loop = loop.reverse();
  const us = loop.map((p) => p[0]), vs = loop.map((p) => p[1]);
  const cu = (Math.min(...us) + Math.max(...us)) / 2, cv = (Math.min(...vs) + Math.max(...vs)) / 2;
  return loop.map(([u, v]) => [u - cu, v - cv]);
}
function area2(pts) { let s = 0; for (let i = 0; i < pts.length; i++) { const [a, b] = pts[i], [c, d] = pts[(i + 1) % pts.length]; s += a * d - c * b; } return s / 2; }

export function m3Shape(p) {
  if (p.kind === 'CFC' || p.kind === 'CFZ') return { loops: [thicken(fillet(centreline(p), p.r + p.t / 2), p.t / 2)], area: cfArea(p) };
  if (p.kind === 'RD') {
    const n = 48, r = p.d / 2;   // 48 sides: the drawn circle is within 0.3 % of π r² (the weight uses π r² exactly)
    return { loops: [Array.from({ length: n }, (_, i) => [r * Math.cos(2 * Math.PI * i / n), r * Math.sin(2 * Math.PI * i / n)])], area: Math.PI * r * r };
  }
  return null;
}

/** Generic starter catalogue: common lipped C and Z sizes, geometry only (r = t). */
export const STARTER = (() => {
  const rows = [[150, 60, 20, [1.5, 2.0]], [200, 65, 20, [1.5, 2.0, 2.5]], [250, 75, 20, [2.0, 2.5, 3.0]], [300, 75, 20, [2.5, 3.0]]];
  const out = [];
  for (const kind of ['CFC', 'CFZ']) for (const [H, B, D, ts] of rows) for (const t of ts) out.push({ name: cfName(kind, H, B, D, t), kind, H, B, D, t, r: t, source: 'generic', designProps: 'from supplier' });
  return out;
})();
