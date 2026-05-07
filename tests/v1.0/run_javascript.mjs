#!/usr/bin/env node
// Run conformance.json against the JavaScript reference parser.
// Usage: node tests/v1.0/run_javascript.mjs
// Exit code 0 on all pass, 1 on any failure.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from '../../parsers/javascript/ashru.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, 'conformance.json'), 'utf-8')).cases;

// Suppress console.warn for the test run
const origWarn = console.warn;
console.warn = () => {};

function deepSubsetMatch(expected, actual, prefix = '') {
  for (const [k, v] of Object.entries(expected)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      const sub = actual?.[k];
      if (sub === null || typeof sub !== 'object') {
        return { ok: false, msg: `${path}: expected object, got ${typeof sub}` };
      }
      const r = deepSubsetMatch(v, sub, path);
      if (!r.ok) return r;
    } else {
      const av = actual?.[k];
      if (JSON.stringify(av) !== JSON.stringify(v)) {
        return { ok: false, msg: `${path}: expected ${JSON.stringify(v)}, got ${JSON.stringify(av)}` };
      }
    }
  }
  return { ok: true, msg: '' };
}

function verbToCanonical(v) {
  return {
    verb_lemma: v.verbLemma,
    karta: v.karta,
    karma: v.karma,
    karana: v.karana,
    sampradana: v.sampradana,
    apadana: v.apadana,
    adhikarana: v.adhikarana,
    tense: v.tense,
    is_negated: v.isNegated,
    attributes: v.attributes,
  };
}

let passed = 0, failed = 0;
for (const c of cases) {
  const cid = c.id;
  try {
    const doc = parse(c.input, { strict: c.strict === true });
    if (c.expect_throws) {
      console.log(`  ${cid}: FAIL — expected throw, got ${doc.verbs.length} verbs`);
      failed++; continue;
    }
    const exp = c.expect || {};
    const errors = [];
    if (exp.verb_count !== undefined && doc.verbs.length !== exp.verb_count)
      errors.push(`verb_count: expected ${exp.verb_count}, got ${doc.verbs.length}`);
    if (exp.skipped_lines !== undefined && doc.skippedLines !== exp.skipped_lines)
      errors.push(`skipped_lines: expected ${exp.skipped_lines}, got ${doc.skippedLines}`);
    if (exp.first_verb && doc.verbs[0]) {
      const r = deepSubsetMatch(exp.first_verb, verbToCanonical(doc.verbs[0]));
      if (!r.ok) errors.push(`first_verb.${r.msg}`);
    }
    if (errors.length) { console.log(`  ${cid}: FAIL — ${errors.join('; ')}`); failed++; }
    else { console.log(`  ${cid}: PASS`); passed++; }
  } catch (e) {
    if (c.expect_throws) {
      console.log(`  ${cid}: PASS (threw ${e.constructor.name})`);
      passed++;
    } else {
      console.log(`  ${cid}: FAIL — unexpected ${e.constructor.name}: ${e.message}`);
      failed++;
    }
  }
}
console.warn = origWarn;
console.log(`\n${passed}/${passed + failed} passed.`);
process.exit(failed === 0 ? 0 : 1);
