/**
 * ASHRU/1 reference parser — JavaScript / Node.js.
 *
 * Released under MIT. See LICENSE in the repo root.
 *
 * Usage:
 *   import { parse, encode } from './ashru.js';
 *   const doc = parse(text);
 *   for (const verb of doc.verbs) console.log(verb.verbLemma, verb.karta);
 *
 * Tolerant of malformed `V|` lines by default (logs to console.warn,
 * skips row). Pass { strict: true } to throw on the first malformed row.
 * The header `ASHRU/1` is the only hard requirement.
 */

const VERSION = "ASHRU/1";
const VERB_COLUMN_COUNT = 11; // marker "V" + 10 data columns
const VALID_TENSES = new Set(["p", "n", "f", "c", ""]);

// ─── Public API ────────────────────────────────────────────────────────

/**
 * Parse an ASHRU/1 document.
 * @param {string} text  The full document as a string.
 * @param {{strict?: boolean}} [opts]  Parser options.
 *   strict=true  → throw on first malformed row (fail-fast).
 *   strict=false → log warning, skip the row (default).
 * @returns {{
 *   version: string,
 *   verbs: Array,
 *   skippedLines: number
 * }}
 * @throws {Error} If the version header is missing/unrecognized, or if
 *   strict=true and any row is malformed.
 */
export function parse(text, opts = {}) {
  const lines = text.split(/\r?\n/);
  return parseLines(lines, opts);
}

export function parseLines(lines, opts = {}) {
  const strict = opts.strict === true;

  // Find the first non-empty non-comment line — must be the version header.
  let header = "";
  let startIdx = 0;
  for (let i = 0; i < lines.length; i++) {
    const stripped = lines[i].trim();
    if (stripped === "" || stripped.startsWith("#")) continue;
    header = stripped;
    startIdx = i + 1;
    break;
  }
  if (header !== VERSION) {
    throw new Error(
      `Expected ASHRU header "${VERSION}", got "${header}". ` +
      `Document is not a valid ASHRU/1 stream.`
    );
  }

  const doc = {
    version: VERSION,
    verbs: [],
    skippedLines: 0,
  };

  for (let i = startIdx; i < lines.length; i++) {
    const raw = lines[i];
    const stripped = raw.trim();
    if (!stripped) continue;
    if (stripped.startsWith("#")) continue;

    if (raw.startsWith("V|")) {
      const verb = parseVerbLine(raw, strict);
      if (verb === null) {
        doc.skippedLines++;
      } else {
        doc.verbs.push(verb);
      }
      continue;
    }

    // Unknown leading marker → silently skip (LLM prose), or raise in strict mode.
    if (strict) {
      throw new Error(`[ashru] Unrecognized line in strict mode: ${raw.slice(0, 200)}`);
    }
    doc.skippedLines++;
  }

  return doc;
}

// ─── Internal ──────────────────────────────────────────────────────────

function parseVerbLine(line, strict = false) {
  const cols = splitWithEscapes(line);
  if (cols.length !== VERB_COLUMN_COUNT) {
    const msg = `Malformed V| row (expected ${VERB_COLUMN_COUNT} columns, got ${cols.length}): ${line.slice(0, 200)}`;
    if (strict) throw new Error(`[ashru] ${msg}`);
    console.warn(`[ashru] Skipping ${msg}`);
    return null;
  }
  const [, lemma, karta, karma, karana, sampradana, apadana, adhikarana, tense, negated, attrs] = cols;
  if (!lemma.trim()) {
    const msg = `V| row with empty verb_lemma: ${line.slice(0, 200)}`;
    if (strict) throw new Error(`[ashru] ${msg}`);
    console.warn(`[ashru] Skipping ${msg}`);
    return null;
  }
  let normalizedTense = tense.trim();
  if (normalizedTense && !VALID_TENSES.has(normalizedTense)) {
    if (strict) throw new Error(`[ashru] Unknown tense "${normalizedTense}"`);
    console.warn(`[ashru] Unknown tense "${normalizedTense}", storing as null`);
    normalizedTense = "";
  }
  return {
    verbLemma: lemma.trim().toLowerCase(),
    karta: nz(karta),
    karma: nz(karma),
    karana: nz(karana),
    sampradana: nz(sampradana),
    apadana: nz(apadana),
    adhikarana: nz(adhikarana),
    tense: nz(normalizedTense),
    isNegated: negated.trim() === "1",
    attributes: parseAttributes(attrs),
  };
}

function splitWithEscapes(line) {
  const out = [];
  let buf = [];
  let i = 0;
  while (i < line.length) {
    const c = line[i];
    if (c === "\\" && i + 1 < line.length) {
      const nxt = line[i + 1];
      if (nxt === "|") { buf.push("|"); i += 2; continue; }
      if (nxt === "\\") { buf.push("\\"); i += 2; continue; }
    }
    if (c === "|") { out.push(buf.join("")); buf = []; i += 1; continue; }
    buf.push(c);
    i += 1;
  }
  out.push(buf.join(""));
  return out;
}

function parseAttributes(s) {
  const trimmed = s.trim();
  if (!trimmed) return {};
  const out = {};
  for (const pair of trimmed.split(";")) {
    const eq = pair.indexOf("=");
    if (eq === -1) continue;
    const k = pair.slice(0, eq).trim();
    if (!k) continue;
    out[k] = pair.slice(eq + 1).trim();
  }
  return out;
}

function nz(s) {
  const t = s.trim();
  return t ? t : null;
}

// ─── Encoder (round-trip support) ──────────────────────────────────────

export function encode(doc) {
  const lines = [VERSION];
  for (const v of doc.verbs) {
    lines.push(encodeVerb(v));
  }
  return lines.join("\n") + "\n";
}

function encodeVerb(v) {
  const cols = [
    "V",
    v.verbLemma,
    v.karta || "",
    v.karma || "",
    v.karana || "",
    v.sampradana || "",
    v.apadana || "",
    v.adhikarana || "",
    v.tense || "",
    v.isNegated ? "1" : "0",
    encodeAttrs(v.attributes),
  ];
  return cols.map(esc).join("|");
}

function esc(s) {
  return String(s).replace(/\\/g, "\\\\").replace(/\|/g, "\\|");
}

function encodeAttrs(attrs) {
  if (!attrs || Object.keys(attrs).length === 0) return "";
  return Object.entries(attrs).map(([k, v]) => `${k}=${v}`).join(";");
}

export { VERSION };
