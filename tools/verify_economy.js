#!/usr/bin/env node
/**
 * Verifies that the JS compound chain (advanceCompound in assets/game.html)
 * produces the same result as the Python reference (tools/reference_chain.py)
 * from a fixed starting state.
 *
 * Scope: confirms the JS port of the chain maths matches the Python reference.
 *        Does NOT validate game balance.
 *
 * Scenario: formsworth=50, subclerk=10, datastack=5, others=0
 * Duration:  3600 s, dt=10 s (360 steps)
 * sun=0, no upgrades  →  ccMultiplier() = 1.0
 *
 * Usage: node tools/verify_economy.js
 * Exit 0 = all pass, exit 1 = any failure.
 */
'use strict';
const fs             = require('fs');
const path           = require('path');
const vm             = require('vm');
const { execFileSync } = require('child_process');

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
state.sun        = 0;
state.upgLevels  = { crystalOverclock: 0, expeditedWarfare: 0, bulkEnlistment: 0 };

// ── Run JS simulation ─────────────────────────────────────────────────────────
const DT    = 10;
const STEPS = 3600 / DT;
for (let i = 0; i < STEPS; i++) advanceCompound(DT);

const jsResult = { cc: state.cc, genCounts: {} };
for (const id of ids) jsResult.genCounts[id] = state.genCounts[id];

// ── Run Python reference ──────────────────────────────────────────────────────
const pyScript = path.join(__dirname, 'reference_chain.py');
const pyOutput = execFileSync('python3', [pyScript], { encoding: 'utf8' });
const pyResult = JSON.parse(pyOutput);

// ── Compare ───────────────────────────────────────────────────────────────────
const TOLERANCE = 1e-6;
const keys = [...ids, 'cc'];

const col = { key: 14, val: 18, rel: 14, status: 6 };
const line = '-'.repeat(col.key + col.val * 2 + col.rel + col.status + 3);
console.log(
  'Key'.padEnd(col.key) +
  'Python'.padStart(col.val) +
  'JS'.padStart(col.val) +
  'Rel diff'.padStart(col.rel) +
  'Pass?'.padStart(col.status)
);
console.log(line);

let allPass = true;
for (const key of keys) {
  const pyVal = key === 'cc' ? pyResult.cc         : pyResult.genCounts[key];
  const jsVal = key === 'cc' ? jsResult.cc         : jsResult.genCounts[key];
  const rel   = pyVal === 0 && jsVal === 0 ? 0
              : pyVal === 0 ? Math.abs(jsVal)
              : Math.abs(pyVal - jsVal) / Math.abs(pyVal);
  const pass  = rel < TOLERANCE;
  if (!pass) allPass = false;
  console.log(
    key.padEnd(col.key) +
    pyVal.toFixed(6).padStart(col.val) +
    jsVal.toFixed(6).padStart(col.val) +
    rel.toExponential(2).padStart(col.rel) +
    (pass ? 'OK' : 'FAIL').padStart(col.status)
  );
}

console.log('');
console.log('Overall:', allPass ? 'ALL PASS' : 'FAILURES DETECTED');
process.exit(allPass ? 0 : 1);
