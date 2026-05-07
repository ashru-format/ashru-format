# Changelog

All notable changes to ASHRU will land here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/) where the SPEC version is the major number.

## [v1.0.0] — 2026-05-07

### First public release

Initial open release of the ASHRU specification + reference parsers.

#### Added
- **`SPEC.md`** — formal v1 specification (CC0 / public domain)
  - Version header line `ASHRU/1`
  - `V|` verb line, 10 positional columns: `verb_lemma`, kartā, karma, karaṇa, sampradāna, apādāna, adhikaraṇa, `tense` (`p|n|f|c`), `is_negated` (`0|1`), `attributes` (`k=v;k=v`)
  - `#` comment lines (skipped by parsers)
  - Pipe escape (`\|`) and backslash escape (`\\`)
  - Conformance rules: tolerant of malformed rows by default; reject on bad header; opt-in `strict=True` for fail-fast
- **`parsers/python/`** — reference parser + encoder, src layout, zero runtime dependencies, Python 3.9+
- **`parsers/javascript/`** — reference parser + encoder, ESM, zero runtime dependencies, Node 18+
- **`tests/python/test_ashru.py`** — unit tests (parsing, round-trip, tolerance, header validation, escapes, attributes)
- **`tests/javascript/test_ashru.mjs`** — unit tests, mirrors the Python suite
- **`tests/v1.0/conformance.json`** — language-agnostic conformance suite both reference parsers must pass
- **`examples/`** — example ASHRU documents:
  - `01-chat-message.ashru` — single-verb chat extraction
  - `04-negation-and-conditional.ashru` — negation flag + conditional/future tense
- **`benchmarks/`** — token-cost and parser-throughput benchmarks (real `tiktoken cl100k_base` tokenizer)
- **`CONTRIBUTING.md`** — what we accept, parser-in-new-language requirements
- **`LICENSE`** — MIT for parsers/tooling, CC0 noted for the spec itself

### Linguistic provenance

The 6 case roles (kartā, karma, karaṇa, sampradāna, apādāna, adhikaraṇa) trace to Pāṇini's *Aṣṭādhyāyī* (~5th century BCE). Rick Briggs at NASA Ames noted in *AI Magazine* (Vol 6 No 1, Spring 1985) that these roles map cleanly onto AI knowledge representation. ASHRU is a 21st-century wire format for that 2,500-year-old grammatical observation.

### License

Specification: CC0 1.0 Universal (public domain). Reference parsers and tests: MIT.
