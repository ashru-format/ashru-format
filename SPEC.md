# ASHRU/1 — Wire Format Specification

**Version:** 1.0
**License:** CC0 1.0 Universal (public domain)
**Reference parsers:** MIT-licensed, in this repository

---

## What ASHRU is

ASHRU is a positional, pipe-delimited wire format for emitting structured fact records from large language models (LLMs). Each record is a single line. Each column maps by position to a Sanskrit grammatical case role formalized in Pāṇini's *Aṣṭādhyāyī* around the 5th century BCE.

The format is designed to minimize output tokens compared to JSON when extracting fact-shaped data. Keys do not appear on the wire — column positions carry meaning per this specification.

## Document structure

An ASHRU document is plain UTF-8 text. The first non-blank line MUST be the version header. Subsequent lines are records or comments.

```
ASHRU/1
V|<10 columns separated by |>
V|<10 columns separated by |>
# this is a comment, ignored by parsers
```

### 1. The version header

The first non-blank, non-comment line of every ASHRU document MUST be exactly `ASHRU/1`. A parser receiving any other header MUST reject the document.

### 2. The `V|` (verb) record — 10 data columns

A `V|` line consists of the marker `V`, the delimiter `|`, and exactly 10 data columns separated by `|`. Empty columns are emitted as empty (`||`).

| # | Column | Sanskrit | Meaning |
|---|---|---|---|
| 1 | `verb_lemma` | धातु | The action (atomic verb in canonical lowercase form) |
| 2 | `kartā` | कर्ता | Agent — who performed the action |
| 3 | `karma` | कर्म | Object — what received the action |
| 4 | `karaṇa` | करण | Instrument — by what means |
| 5 | `sampradāna` | सम्प्रदान | Recipient — for whose benefit |
| 6 | `apādāna` | अपादान | Source — from where, from whom |
| 7 | `adhikaraṇa` | अधिकरण | Locative — where, when |
| 8 | `tense` | — | `p` (past), `n` (now), `f` (future), `c` (conditional), or empty |
| 9 | `negated` | — | `0` (true) or `1` (the action did NOT happen) |
| 10 | `attributes` | — | free-form `key=value;key=value` list, or empty |

A V| line therefore always contains exactly 11 segments (the marker `V` plus 10 data columns).

### 3. Comments

A line beginning with `#` is a comment. Parsers MUST ignore comments.

### 4. Blank lines

Blank lines are ignored.

### 5. Escaping

The pipe character `|` is the column separator and cannot appear unescaped inside a column value. Two rules:

- A literal pipe inside a value MUST be encoded as `\|`. Example: `V|hire|Acme|Suman \| CEO|||||p|0|`
- A literal backslash MUST be encoded as `\\`.

A conformant parser MUST un-escape these sequences during column splitting.

## Worked example

Input prose: *"Suman bought a Tesla yesterday from John in SF for $60,000."*

Output:

```
ASHRU/1
V|buy|Suman|Tesla|$60000||John|SF|p|0|date=2026-05-05
```

JSON equivalent (illustrative, ~120 tokens):

```json
{
  "verbs": [{
    "verb_lemma": "buy",
    "kartā": "Suman",
    "karma": "Tesla",
    "karaṇa": "$60000",
    "apādāna": "John",
    "adhikaraṇa": "SF",
    "tense": "past",
    "is_negated": false,
    "attributes": {"date": "2026-05-05"}
  }]
}
```

The same fact in ASHRU is roughly 4× smaller in token count under the OpenAI `cl100k_base` tokenizer.

## Negation example

Input: *"I did not buy the Tesla."*

Output:

```
ASHRU/1
V|buy|Suman|Tesla|||||p|1|
```

The `1` in column 9 stores the negated truth (the buy did NOT happen).

## Conditional example

Input: *"I would buy a Tesla if the price drops below $50K."*

Output:

```
ASHRU/1
V|buy|Suman|Tesla|$50000||||c|0|condition=price_drops
```

Tense `c` (conditional) signals to consumers that this row is hypothetical.

## Parser conformance

A conformant ASHRU/1 parser MUST:

1. Read the first non-blank non-comment line and verify it equals `ASHRU/1`. If not, reject the document.
2. Process each subsequent line by its leading marker (`V|`, `#`) or skip if no marker is recognized.
3. For `V|` lines, split on `|` (respecting `\|` and `\\` escapes) and verify column count is exactly 11. On mismatch:
   - Default (tolerant) mode: log a warning, skip the row, continue parsing.
   - Strict mode (`strict=True`): raise a parse error.
4. Emit records to the consumer with named fields per the table above.

Reference parsers in Python and JavaScript ship in this repository under `parsers/`. The `tests/` directory contains the conformance suite both parsers must pass.

## Why the 6 kāraka roles

The six case roles formalized in Pāṇini's *Aṣṭādhyāyī* (~5th century BCE) provide a complete grammatical decomposition of action-bearing sentences. Every transitive event in any natural language can be described in terms of an agent, an object, an instrument, a recipient, a source, and a locative. These six roles plus a verb plus a tense plus a negation flag plus a free attribute slot give 10 columns — the V| record.

The kāraka grammar is part of humanity's open intellectual heritage. The ASHRU specification places it on a wire format suitable for high-volume LLM emission.

## License

This specification is released under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). Public domain. Use freely. No attribution required.

Reference parsers in this repository are released under [MIT](LICENSE).

## Linguistic provenance

The six case roles (kartā, karma, karaṇa, sampradāna, apādāna, adhikaraṇa) come from Pāṇini's *Aṣṭādhyāyī* (~5th century BCE), the grammar of Sanskrit. Rick Briggs at NASA Ames noted in *AI Magazine* (Vol 6 No 1, Spring 1985) that these roles map cleanly onto AI knowledge representation. ASHRU is a 21st-century wire format for that 2,500-year-old grammatical observation.
