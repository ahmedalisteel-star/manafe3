#!/usr/bin/env node
/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/**
 * manafe3-smoke.mjs — opens Manafe3's own dialogs in headless Chrome / Edge over the DevTools Protocol (no packages) and
 * prints every page error, console error and failed load. Start the app first (python manafe3.py, or the engine on 8765
 * and `node devshell/serve.mjs --port 8000`), then:   node tools/manafe3-smoke.mjs [http://localhost:8000/]
 * Browser: MANAFE3_CHROME, else Chrome or Edge in their standard Program Files folders. The profile is a temp folder.
 * Steps: Building… (placement, pads), a second building rotated 90°, Crane runway…, Job units…, base plates and footing
 * clean-up, Analysis… picker, Drawings settings + tick-box export, Elevation view on an x grid line.
 */import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
const CHROME = [process.env.MANAFE3_CHROME, ...['ProgramFiles', 'ProgramFiles(x86)'].flatMap((k) => process.env[k] ? [path.join(process.env[k], 'Google/Chrome/Application/chrome.exe'), path.join(process.env[k], 'Microsoft/Edge/Application/msedge.exe')] : [])].find((p) => p && fs.existsSync(p));
if (!CHROME) { console.error('No Chrome or Edge found: set MANAFE3_CHROME to its path.'); process.exit(2); }
const URL0 = process.argv[2] || 'http://localhost:8000/';
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), 'manafe3-smoke-'));
fs.mkdirSync(PROFILE, { recursive: true });
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=9333', '--user-data-dir=' + PROFILE, '--no-first-run', '--no-default-browser-check', '--window-size=1600,1000', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ver;
for (let i = 0; i < 40 && !ver; i++) { try { ver = await (await fetch('http://127.0.0.1:9333/json/version')).json(); } catch { await sleep(250); } }
const tgt = await (await fetch('http://127.0.0.1:9333/json/new?about:blank', { method: 'PUT' })).json();
const ws = new WebSocket(tgt.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
let id = 0; const wait = new Map(); const problems = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && wait.has(m.id)) { wait.get(m.id)(m); wait.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') problems.push('EXCEPTION ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) problems.push('CONSOLE.' + m.params.type + ' ' + m.params.args.map((a) => a.value ?? a.description ?? '').join(' '));
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') problems.push('LOG ' + m.params.entry.text + ' ' + (m.params.entry.url || ''));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; wait.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const run = async (expr) => { const r = await send('Runtime.evaluate', { expression: `(async () => { ${expr} })()`, awaitPromise: true, returnByValue: true }); if (r.result?.exceptionDetails) return { error: r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text }; return r.result?.result?.value; };
await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
await send('Page.navigate', { url: URL0 });
await sleep(8000);
const step = async (name, expr) => { const before = problems.length; const v = await run(expr); console.log('== ' + name + ':', JSON.stringify(v)); for (const p of problems.slice(before)) console.log('   ' + p); };
const H = `const $ = (s) => document.querySelector(s); const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const M = () => { let m; window.ccAddonModel.read((x) => { m = x; }); return m; };
  const set = (sel, v) => { const e = $(sel); e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); };`;
console.log('== load problems:'); for (const p of problems) console.log('   ' + p);
await step('PEB menu items', H + `return [...document.querySelectorAll('[data-m3-act]')].map((b) => b.dataset.m3Act);`);
await step('Building dialog: open, fill placement, make', H + `
  $('[data-m3-act="peb-building"]').click(); await sleep(1500);
  const d = $('dialog[data-m3-building]'); if (!d.open) return 'not open';
  const fields = ['which', 'name', 'span_ref', 'grid_inset', 'bays', 'origin_x', 'origin_y', 'origin_z', 'plan_rotation', 'footings'].filter((k) => !$('#m3-b-' + k));
  set('#m3-b-name', 'STORE'); set('#m3-b-origin_x', '1000'); set('#m3-b-origin_y', '2000'); set('#m3-b-footings', 'pads');
  $('[data-m3-b-add]').click(); await sleep(6000);
  return { missingFields: fields, open: d.open, note: $('[data-m3-b-note]').textContent.slice(0, 160), members: M().state.members.length, buildings: (M().state.m3buildings || []).map((b) => b.name), footings: M().state.footings.length };`);
await step('Building dialog again: picker and a second building rotated 90', H + `
  $('[data-m3-act="peb-building"]').click(); await sleep(800);
  const opts = [...$('#m3-b-which').options].map((o) => o.textContent);
  set('#m3-b-which', '(new)'); await sleep(800);
  set('#m3-b-name', 'F&S-2'); set('#m3-b-origin_x', '60000'); set('#m3-b-plan_rotation', '90'); set('#m3-b-eave_height', '10000');
  $('[data-m3-b-add]').click(); await sleep(6000);
  return { pickerBefore: opts, open: $('dialog[data-m3-building]').open, note: $('[data-m3-b-note]').textContent.slice(0, 160), buildings: (M().state.m3buildings || []).map((b) => b.id + ' ' + b.name) };`);
await step('Crane runway dialog: open, make on B2', H + `
  $('[data-m3-act="crane"]').click(); await sleep(800);
  const d = $('dialog[data-m3-crane]'); if (!d.open) return 'not open';
  set('#m3-c-building', 'B2'); await sleep(300);
  $('[data-m3-c-add]').click(); await sleep(2000);
  return { open: d.open, crane: M().state.members.filter((m) => (m.gen || '').startsWith('crane')).length, keptOn: (M().state.m3buildings || []).filter((b) => b.crane).map((b) => b.id) };`);
await step('Job units dialog: metric, Y, C35/45', H + `
  $('[data-m3-act="units"]').click(); await sleep(500);
  const d = $('dialog[data-m3-units]'); if (!d.open) return 'not open';
  set('#m3-u-system', 'metric'); set('#m3-u-bar', 'Y'); set('#m3-u-conc', 'C35/45');
  d.querySelector('button[type="submit"]').click(); await sleep(800);
  return { open: d.open, units: M().state.m3units };`);
await step('Remove footings with no column + base plates', H + `
  $('[data-m3-act="peb-baseplates"]').click(); await sleep(2500);
  $('[data-m3-act="peb-footings-clean"]').click(); await sleep(2500);
  return { baseplates: M().state.connections.filter((c) => c.type === 'baseplate').length, footings: M().state.footings.length };`);
await step('Analysis dialog: building picker', H + `
  $('[data-m3-act="analysis"]').click(); await sleep(800);
  const d = $('dialog[data-m3-analysis]'); const o = [...$('[data-m3-a-building]').options].map((x) => x.textContent); d.close(); return { open0: true, picker: o };`);
await step('Drawings: open, settings panel, change, tick export', H + `
  document.querySelector('[data-act="drawings"]').click(); await sleep(9000);
  const d = document.querySelector('dialog[open]'); if (!d) return 'no dialog open';
  const st = d.querySelector('[data-m3-dwg-settings]'), ex = d.querySelector('[data-m3-dwg-export]'); if (!st || !ex) return 'panels missing';
  st.open = true; ex.open = true;
  set('#m3d-client', 'Test client'); await sleep(6000);
  set('#m3d-status', 'For construction'); await sleep(6000);
  const boxes = [...ex.querySelectorAll('input[type="checkbox"]')]; boxes.slice(0, 2).forEach((b) => { b.checked = true; });
  ex.querySelector('[data-m3-dwg-pdf]').click(); await sleep(6000);
  ex.querySelector('[data-m3-dwg-dxf]').click(); await sleep(3000);
  return { sheets: boxes.length, m3drawings: M().state.m3drawings?.title, issueNote: document.querySelector('[data-issue-note]')?.value, first: boxes.slice(0, 2).map((b) => b.value), status: document.querySelector('[data-status], .dc-status')?.textContent?.slice(0, 200) };`);
await step('Elevation view on an x grid', H + `
  const s = document.querySelector('[data-vgrid]'); const vals = [...s.options].map((o) => o.value);
  document.querySelector('[data-view="elevation"]').click(); await sleep(500);
  const x = vals.find((v) => v.startsWith('x:')); if (x) { s.value = x; s.dispatchEvent(new Event('change', { bubbles: true })); await sleep(800); }
  return { options: vals.length, xOptions: vals.filter((v) => v.startsWith('x:')).length, chosen: s.value };`);
console.log('== ALL problems (' + problems.length + ')'); for (const p of problems) console.log('   ' + p);
ws.close(); chrome.kill();
process.exit(problems.some((p) => p.startsWith('EXCEPTION')) ? 1 : 0);
