/**
 * ASHRU v1 reference test suite — JavaScript / Node.js.
 *
 * Run from repo root:
 *     node tests/javascript/test_ashru.mjs
 *
 * Exits with code 0 on all-pass, 1 on any failure. No external dependencies.
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, "..", "..");

// Import via relative path so this works without npm install.
const { parse, encode, VERSION } = await import(
  resolve(ROOT, "parsers/javascript/ashru.js")
);

const EXAMPLES = resolve(ROOT, "examples");

let pass = 0;
let fail = 0;
const failures = [];

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    pass++;
  } catch (e) {
    console.log(`  ✗ ${name}`);
    console.log(`     ${e.message}`);
    failures.push({ name, error: e });
    fail++;
  }
}

function suite(name, body) {
  console.log(`\n${name}`);
  body();
}

function eq(actual, expected, label = "values") {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${label} mismatch — expected ${e}, got ${a}`);
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}

function throws(fn, msg = "expected throw") {
  let didThrow = false;
  try { fn(); } catch (e) { didThrow = true; }
  if (!didThrow) throw new Error(msg);
}

// ─── Parsing the four examples ──────────────────────────────────────────

suite("Examples", () => {
  test("01 chat message — single verb", () => {
    const doc = parse(readFileSync(resolve(EXAMPLES, "01-chat-message.ashru"), "utf8"));
    eq(doc.verbs.length, 1, "verb count");
    const v = doc.verbs[0];
    eq(v.verbLemma, "buy");
    eq(v.karta, "Suman");
    eq(v.karma, "Tesla");
    eq(v.karana, "$60000");
    eq(v.tense, "p");
    assert(v.isNegated === false);
    eq(v.attributes.date, "2026-05-05");
  });

  test("04 negation/conditional — flags + tense correct", () => {
    const doc = parse(readFileSync(resolve(EXAMPLES, "04-negation-and-conditional.ashru"), "utf8"));
    assert(doc.verbs.length >= 2);
    eq(doc.verbs[0].isNegated, true);
  });
});

// ─── Round-trip ─────────────────────────────────────────────────────────

suite("Round-trip", () => {
  test("encode → parse preserves verb fields", () => {
    const original = parse(readFileSync(resolve(EXAMPLES, "04-negation-and-conditional.ashru"), "utf8"));
    const encoded = encode(original);
    const parsed = parse(encoded);
    eq(parsed.verbs.length, original.verbs.length);
    for (let i = 0; i < original.verbs.length; i++) {
      eq(parsed.verbs[i].verbLemma, original.verbs[i].verbLemma);
      eq(parsed.verbs[i].isNegated, original.verbs[i].isNegated);
      eq(parsed.verbs[i].tense, original.verbs[i].tense);
      eq(parsed.verbs[i].attributes, original.verbs[i].attributes);
    }
  });

});

// ─── Tolerance ──────────────────────────────────────────────────────────

suite("Tolerance", () => {
  // Silence the parser's console.warn during these tests
  const originalWarn = console.warn;
  console.warn = () => {};

  test("malformed V| lines + prose are skipped", () => {
    const text = `ASHRU/1
V|buy|Suman|Tesla|||||p|0|
this is some prose the LLM emitted by mistake
V|broken|but|too|few|cols
V|deploy|engineer|api||||staging|n|0|
`;
    const doc = parse(text);
    eq(doc.verbs.length, 2);
    assert(doc.skippedLines >= 2, `skipped >= 2, got ${doc.skippedLines}`);
  });

  test("unknown tense stored as null", () => {
    const doc = parse("ASHRU/1\nV|buy|Suman|Tesla|||||xyzzy|0|\n");
    eq(doc.verbs.length, 1);
    eq(doc.verbs[0].tense, null);
  });

  test("empty verb_lemma row dropped", () => {
    const doc = parse("ASHRU/1\nV||Suman|Tesla|||||p|0|\n");
    eq(doc.verbs.length, 0);
    assert(doc.skippedLines >= 1);
  });

  console.warn = originalWarn;
});

// ─── Header validation ──────────────────────────────────────────────────

suite("Header validation", () => {
  test("missing header rejected", () => {
    throws(() => parse("V|buy|Suman|Tesla|||||p|0|"));
  });
  test("wrong version rejected", () => {
    throws(() => parse("ASHRU/2\nV|buy|Suman|Tesla|||||p|0|"));
  });
  test("XML rejected", () => {
    throws(() => parse("<?xml version='1.0'?><verbs/>"));
  });
  test("blank lines before header are tolerated", () => {
    const doc = parse("\n\n\nASHRU/1\nV|buy|Suman|Tesla|||||p|0|\n");
    eq(doc.verbs.length, 1);
  });
});

// ─── Escape handling ────────────────────────────────────────────────────

suite("Escape handling", () => {
  test("escaped pipe in value", () => {
    const doc = parse("ASHRU/1\nV|run|engineer|cmd \\| grep|||||p|0|\n");
    eq(doc.verbs[0].karma, "cmd | grep");
  });
  test("escaped backslash in value", () => {
    const doc = parse("ASHRU/1\nV|set|user|path \\\\to\\\\file|||||p|0|\n");
    eq(doc.verbs[0].karma, "path \\to\\file");
  });
  test("round-trip preserves pipe escape", () => {
    const doc = { version: VERSION, verbs: [{
      verbLemma: "run", karta: "engineer", karma: "cmd | grep",
      karana: null, sampradana: null, apadana: null, adhikarana: null,
      tense: null, isNegated: false, attributes: {},
    }] };
    const encoded = encode(doc);
    const reParsed = parse(encoded);
    eq(reParsed.verbs[0].karma, "cmd | grep");
  });
});

// ─── Attributes ─────────────────────────────────────────────────────────

suite("Attributes", () => {
  test("multiple attributes parsed", () => {
    const doc = parse("ASHRU/1\nV|buy|Suman|Tesla|||||p|0|price=60000;currency=USD;model=Y\n");
    eq(doc.verbs[0].attributes, { price: "60000", currency: "USD", model: "Y" });
  });
  test("empty attribute value preserved", () => {
    const doc = parse("ASHRU/1\nV|buy|Suman|Tesla|||||p|0|note=\n");
    eq(doc.verbs[0].attributes, { note: "" });
  });
  test("malformed attribute pair skipped", () => {
    const doc = parse("ASHRU/1\nV|buy|Suman|Tesla|||||p|0|valid=1;junk;also=2\n");
    eq(doc.verbs[0].attributes, { valid: "1", also: "2" });
  });
});

// ─── Summary ────────────────────────────────────────────────────────────

console.log(`\n${pass}/${pass + fail} tests passed`);
if (fail > 0) {
  console.log(`\n${fail} failure(s):`);
  for (const f of failures) console.log(`  - ${f.name}: ${f.error.message}`);
  process.exit(1);
}
process.exit(0);
