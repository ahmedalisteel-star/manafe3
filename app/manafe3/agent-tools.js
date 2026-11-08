/* Manafe3 file. Copyright (c) 2026 Ahmed Ali. All rights reserved. (Not part of upstream DetailCraft.) */
/* i18n-ignore-file — tool names, descriptions and results are read by the assistant program, not shown to the person. */
/**
 * agent-tools.js — Manafe3's tools for the person's own assistant (field fix 26), next to DetailCraft's (agents.js),
 * registered on the same host.control (window.detailcraftControl). DOM-free: tests/bin/test-manafe3-fieldfixes.mjs
 * runs them through host.js's dispatcher.
 *
 *   m3Tools(app) → [tool definitions]   app = { model(), built(), marks(), busy?(), requestBuilding(body) (the engine),
 *                                         exportSheets({ numbers, format }) }
 * Every edit tool is ONE undo step labelled "Assistant: …" (the "undo" tool takes it back).
 *   peb_buildings        read    the PEB buildings: id, name, placement, span, bays, eave, slope, generated members
 *   peb_building_set     edit    make a building, or regenerate one (id) — placement, uneven bays, span reference; with
 *                                pad footings and base plates if asked; grids merge (default) / none / replace
 *   members_add          edit    several members in one step
 *   members_transform    edit    move, rotate (about Z) or mirror members / footings: the app's own transform (roll, holes
 *                                and connections follow)
 *   members_delete       edit    delete by filter (ids, building, type, profile, name pattern, generated or not); a filter
 *                                is required, and the count must be confirmed by `expect` (no "delete everything" by accident)
 *   clash_groups         read    the clash check grouped by type; generated connection points can be left out
 *   sheets_export        export  the drawing set's chosen sheets as one merged PDF or a DXF zip (downloaded)
 * Turning the assistant on stays the person's: Settings › Assistants (off by default — then list() is empty).
 */
import { buildingRequest, applyBuilding, buildingsOf, membersOfBuilding, BUILDING_DEFAULTS, buildingOfMember } from './peb-building.js';
import { addPadFootings, addBasePlates, columnBases, footingHolds } from './peb-footings.js';
import { groupClashes } from './clash-groups.js';
import { clashCheck } from '../clash.js';
import { moveXf, rotateXf, mirrorXf, transformRefs, selectionCenter } from '../transform.js';

const obj = (properties, required = []) => ({ type: 'object', properties, required, additionalProperties: false });
const PT = { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 };
const P2 = { type: 'array', items: { type: 'number' }, minItems: 2, maxItems: 2 };
const NUM = (d) => ({ type: 'number', description: d });
const REF = obj({ kind: { type: 'string', enum: ['member', 'footing', 'stair'] }, id: { type: 'string', maxLength: 255 } }, ['kind', 'id']);
const SPEC_KEYS = Object.keys(BUILDING_DEFAULTS);

export function m3Tools(app) {
  const M = () => app.model();
  const step = (label, fn) => {
    const why = app.busy?.();
    if (why) throw new Error('The person is ' + why + ': try again when they finish.');
    return M().change('Assistant: ' + label, fn);
  };
  const pickMembers = (s, f) => {
    let re = null;
    if (f.name) { try { re = new RegExp(f.name, 'i'); } catch { throw new Error('name: not a valid pattern'); } }
    const ids = f.ids ? new Set(f.ids) : null;
    return s.members.filter((m) => (!ids || ids.has(m.id)) && (!f.building || buildingOfMember(m) === f.building) && (!f.type || m.type === f.type)
      && (!f.profile || String(m.profile).toUpperCase() === String(f.profile).toUpperCase()) && (!re || re.test(m.name || ''))
      && (f.generated === undefined || !!(m.gen && m.gen.startsWith('peb')) === f.generated));
  };
  return [
    {
      name: 'peb_buildings', group: 'read', title: 'PEB buildings',
      description: 'The PEB buildings in the model: id (B1, B2 …), name, placement (origin_x/y/z mm, plan_rotation degrees), span and what it is measured to, bays, eave height, roof slope, and how many generated members each has.',
      run: () => ({ buildings: buildingsOf(M().state).map((b) => ({ id: b.id, name: b.name, members: membersOfBuilding(M().state, b.id).length,
        spec: Object.fromEntries(SPEC_KEYS.filter((k) => b.spec[k] !== undefined && b.spec[k] !== '').map((k) => [k, b.spec[k]])) })) }),
    },
    {
      name: 'peb_building_set', group: 'edit', title: 'Make or regenerate a PEB building',
      description: 'Make a new PEB building, or regenerate an existing one (give its id) — only that building\'s generated members are replaced; your own members, footings and other buildings stay. Units mm. span is measured as span_ref says (outside of steel, column centreline at the base, or grid lines grid_inset outside the steel). bays: "6600 6000 6000" or a site-grid range "A-L" (their spacings); else n_bays x bay_spacing. Placement: origin_x/y/z and plan_rotation (degrees about Z; grid lines are added only for multiples of 90). Other building fields (purlin spacing, sections, end walls, openings …) as in the Building form, in `more`. One undo step.',
      inputSchema: obj({
        id: { type: 'string', description: 'The building to regenerate (B1 …); leave out for a new one.', maxLength: 8 },
        name: { type: 'string', maxLength: 40 }, span: NUM('mm'), span_ref: { type: 'string', enum: ['outside', 'centreline', 'grid'] }, grid_inset: NUM('mm, span_ref grid'),
        eave_height: NUM('mm'), roof_slope: NUM('rise / run'), n_bays: { type: 'integer', minimum: 1, maximum: 40 }, bay_spacing: NUM('mm'), bays: { type: 'string', maxLength: 400 },
        origin_x: NUM('mm'), origin_y: NUM('mm'), origin_z: NUM('mm'), plan_rotation: NUM('degrees'),
        grids: { type: 'string', enum: ['merge', 'none', 'replace'] }, footings: { type: 'boolean', description: 'pad footings under its columns' }, base_plates: { type: 'boolean', description: 'base plates under its columns' },
        more: { type: 'object', description: 'Other Building-form fields by their keys (roof_spacing_a, purlin, end_first, openings …).', additionalProperties: true },
      }),
      run: async (a) => {
        const s = M().state;
        const old = a.id ? buildingsOf(s).find((b) => b.id === a.id) : null;
        if (a.id && !old) throw new Error('No building ' + a.id + ': see peb_buildings.');
        const form = { ...BUILDING_DEFAULTS, grade: 'S355', ...(old?.spec || {}), ...(a.more || {}) };
        for (const k of SPEC_KEYS) if (a[k] !== undefined) form[k] = String(a[k]);
        const body = buildingRequest(form, s);
        const res = await app.requestBuilding(body);
        return step((old ? 'regenerate ' : 'add ') + 'PEB building', (tx) => {
          const r = applyBuilding(tx, res, form, { grids: a.grids || 'merge', id: a.id || null });
          if (a.footings) r.footings = addPadFootings(tx, tx.s, { building: r.id });
          if (a.base_plates) r.basePlates = addBasePlates(tx, tx.s, { building: r.id });
          return r;
        });
      },
    },
    {
      name: 'members_add', group: 'edit', title: 'Add several members',
      description: 'Add several beams, columns, braces or plates in ONE undo step: each { type, profile, material, start [x,y,z], end [x,y,z], position, rotation, name } (mm). Returns their ids.',
      inputSchema: obj({ members: { type: 'array', minItems: 1, maxItems: 2000, items: obj({ type: { type: 'string', enum: ['beam', 'column', 'brace', 'plate'] }, profile: { type: 'string', maxLength: 255 }, material: { type: 'string', maxLength: 30 },
        start: PT, end: PT, position: { type: 'string', enum: ['top', 'middle', 'bottom'] }, rotation: { type: 'number' }, name: { type: 'string', maxLength: 40 }, phase: { type: 'integer', minimum: 1 } }, ['type', 'start', 'end']) } }, ['members']),
      run: (a) => ({ ids: step('add ' + a.members.length + ' members', (tx) => a.members.map((m) => tx.addMember({ ...m }))) }),
    },
    {
      name: 'members_transform', group: 'edit', title: 'Move, rotate or mirror',
      description: 'Move, rotate (about the vertical line through center, counter-clockwise from above; default the middle of what is moved) or mirror (in the vertical plane through two plan points) members, footings and stairs — the app\'s own transform: each member keeps its roll relative to the rest, holes and connections follow. refs or a building id picks what moves (a building takes the footings under its columns along). One undo step.',
      inputSchema: obj({ refs: { type: 'array', items: REF, maxItems: 100000 }, building: { type: 'string', maxLength: 8 }, op: { type: 'string', enum: ['move', 'rotate', 'mirror'] },
        offset: PT, degrees: { type: 'number' }, center: P2, p1: P2, p2: P2 }, ['op']),
      run: (a) => {
        const s = M().state;
        // a building: its generated members AND the footings under its columns (they go with it)
        const refs = a.refs || (a.building ? [...membersOfBuilding(s, a.building).map((m) => ({ kind: 'member', id: m.id })),
          ...s.footings.filter((f) => columnBases(s, { building: a.building }).some((b) => footingHolds(f, b.point))).map((f) => ({ kind: 'footing', id: f.id }))] : null);
        if (!refs || !refs.length) throw new Error('Give refs or a building id.');
        const xf = a.op === 'move' ? moveXf(...(a.offset || [0, 0, 0]))
          : a.op === 'rotate' ? rotateXf(a.center || selectionCenter(s, refs).slice(0, 2), a.degrees ?? 0)
            : mirrorXf(a.p1 || [0, 0], a.p2 || [0, 1]);
        const r = step(a.op, (tx) => transformRefs(tx, tx.s, refs, xf));
        return { members: r.members, footings: r.footings, stairs: r.stairs, splitConnections: r.connections };
      },
    },
    {
      name: 'members_delete', group: 'edit', title: 'Delete members by filter',
      description: 'Delete the members that match ALL given filters (ids, building, type, profile, name pattern, generated true/false); their connections go with them. A filter is required, and `expect` must equal the number that match (call with expect: -1 first to see the count; nothing is deleted then). One undo step.',
      inputSchema: obj({ ids: { type: 'array', items: { type: 'string', maxLength: 255 }, maxItems: 100000 }, building: { type: 'string', maxLength: 8 }, type: { type: 'string', enum: ['beam', 'column', 'brace', 'plate'] },
        profile: { type: 'string', maxLength: 255 }, name: { type: 'string', maxLength: 200, description: 'regular expression on the member name' }, generated: { type: 'boolean' }, expect: { type: 'integer', minimum: -1 } }, ['expect']),
      run: (a) => {
        const { expect, ...f } = a;
        if (!Object.keys(f).length) throw new Error('Give at least one filter: this tool never deletes everything.');
        const hit = pickMembers(M().state, f);
        if (expect !== hit.length) return { matched: hit.length, deleted: 0, note: expect === -1 ? 'Count only: call again with expect: ' + hit.length + ' to delete.' : 'expect (' + expect + ') does not match ' + hit.length + ': nothing deleted.' };
        if (!hit.length) return { matched: 0, deleted: 0 };
        step('delete ' + hit.length + ' members', (tx) => tx.removeMembers(hit.map((m) => m.id)));
        return { matched: hit.length, deleted: hit.length };
      },
    },
    {
      name: 'clash_groups', group: 'read', title: 'Clashes by type',
      description: 'The clash check grouped by type (the two members\' roles); hide_generated leaves out clashes at connection points the PEB generator leaves as points until Phase 5 (flange braces, crossing rods, knee, ridge, cap plates …). Real clashes always show.',
      inputSchema: obj({ tolerance: { type: 'number', minimum: 0, maximum: 50 }, hide_generated: { type: 'boolean' } }),
      run: (a) => {
        const r = clashCheck(M().state, app.built(), { tol: a.tolerance ?? 1 });
        const g = groupClashes(M().state, r.clashes, { hideGenerated: !!a.hide_generated });
        return { total: r.clashes.length, hidden: g.hidden, shown: g.shown, groups: g.groups.map((x) => ({ type: x.label, generatedJoint: x.generatedJoint, count: x.clashes.length,
          first: x.clashes.slice(0, 5).map((c) => ({ a: c.a, b: c.b, depth: c.depth, at: c.at })) })) };
      },
    },
    {
      name: 'model_replace', group: 'edit', title: 'Replace the model',
      description: 'Replace the whole open model with a model file\'s JSON text (the .detailcraft.json format; checked field by field) as ONE undoable step — "undo" brings the previous model back (unlike opening a file, which clears the history).',
      inputSchema: obj({ label: { type: 'string', maxLength: 80 }, model: { type: 'string', maxLength: 50000000, description: 'the model file\'s JSON text' } }, ['model']),
      run: (a) => {
        const why = app.busy?.();
        if (why) throw new Error('The person is ' + why + ': try again when they finish.');
        const r = M().replace('Assistant: ' + (a.label || 'replace model'), a.model);
        return { name: M().state.name, members: M().state.members.length, warnings: r.warnings };
      },
    },
    {
      name: 'sheets_export', group: 'export', title: 'Export drawing sheets',
      description: 'The drawing set\'s sheets (by number, e.g. ["GA-01", "GA-03"]; none = all) as ONE merged PDF or a zip of DXF files, downloaded as the Drawings dialog does.',
      inputSchema: obj({ numbers: { type: 'array', items: { type: 'string', maxLength: 40 }, maxItems: 1000 }, format: { type: 'string', enum: ['pdf', 'dxf'] } }),
      run: (a) => app.exportSheets({ numbers: a.numbers || null, format: a.format || 'pdf' }),
    },
  ];
}
