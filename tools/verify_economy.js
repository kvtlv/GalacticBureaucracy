#!/usr/bin/env node
/**
 * Runs the same scenario as reference_chain.py using the REAL advanceCompound
 * and CONFIG extracted from assets/game.html (file is NOT modified).
 *
 * Scenario: formsworth=50, subclerk=10, datastack=5, others=0
 * Duration:  3600 s, dt=10 s (360 steps)
 * sun=0, no upgrades  →  ccMultiplier() = 1.0
 */
'use strict';
const fs   = require('fs');
const path = require('path');
const vm   = require('vm');

// ── DOM / browser stubs ──────────────────────────────────────────────────────
function fakeEl() {
  const el = {
    textContent: '', innerHTML: '', className: '', style: {},
    id: '', disabled: false, dataset: {},
    appendChild:      () => fakeEl(),
    querySelector:    () => fakeEl(),
    querySelectorAll: () => [],
    addEventListener: () => {},
    setAttribute:     () => {},
    getAttribute:     () => null,
    cloneNode:        () => fakeEl(),
    classList: { add: () => {}, remove: () => {}, contains: () => false, toggle: () => {} },
  };
  return el;
}
global.document = {
  getElementById:    () => fakeEl(),
  querySelector:     () => fakeEl(),
  querySelectorAll:  () => [],
  createElement:     () => fakeEl(),
  createTextNode:    () => fakeEl(),
  addEventListener:  () => {},
  body: fakeEl(),
};
global.window            = { addEventListener: () => {}, location: { reload: () => {} } };
global.localStorage      = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
global.requestAnimationFrame = () => {};
global.setInterval       = () => {};
global.clearInterval     = () => {};
global.performance       = { now: () => Date.now() };

// ── Load game script ─────────────────────────────────────────────────────────
const html  = fs.readFileSync(path.join(__dirname, '../assets/game.html'), 'utf8');
const start = html.indexOf('<script>') + '<script>'.length;
const end   = html.indexOf('</script>', start);
vm.runInThisContext(html.substring(start, end));  // defines CONFIG, state, advanceCompound, etc.

// ── Override state with test scenario ────────────────────────────────────────
// (loadGame() ran with localStorage=null, so state is already default; override counts)
const ids = CONFIG.generators.map(g => g.id);
for (const id of ids) {
  state.genCounts[id]    = 0;
  state.genPurchased[id] = 0;
}
state.genCounts.formsworth = 50;
state.genCounts.subclerk   = 10;
state.genCounts.datastack  = 5;
state.cc         = 0;
state.lifetimeCC = 0;
state.sun        = 0;    // ensures ccMultiplier() = 1.0
state.upgLevels  = { crystalOverclock: 0, expeditedWarfare: 0, bulkEnlistment: 0 };

// ── Run simulation ────────────────────────────────────────────────────────────
const DT    = 10;
const STEPS = 3600 / DT;
for (let i = 0; i < STEPS; i++) {
  advanceCompound(DT);
}

// ── Output ────────────────────────────────────────────────────────────────────
const result = { genCounts: {}, cc: state.cc };
for (const id of ids) result.genCounts[id] = state.genCounts[id];
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
