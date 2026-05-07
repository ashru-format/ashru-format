# ASHRU — Atomic Semantic Hyper-Relational Unit

[![License: MIT](https://img.shields.io/badge/parsers-MIT-yellow.svg)](LICENSE)
[![Spec License: CC0](https://img.shields.io/badge/spec-CC0%20public%20domain-blue.svg)](SPEC.md)

ASHRU is a positional, pipe-delimited wire format for emitting structured fact records from large language models (LLMs). One line per fact, ten columns mapped to grammatical case roles formalized in Pāṇini's *Aṣṭādhyāyī* (~5th century BCE).

> **Playground:** [json2ashru.com](https://json2ashru.com)

*Named in honor of Sanskrit अश्रु ("ashru") — the distilled essence, a tear that holds the whole.*

## Why ASHRU

When extracting fact-shaped information from text using an LLM, JSON forces the model to spend output tokens on braces, quotes, commas, and repeated key names. ASHRU drops the keys (column positions carry meaning) and uses a single delimiter, reducing emission cost meaningfully at production volume.

**JSON output (~120 tokens):**

```json
{
  "verbs": [
    {
      "verb_lemma": "buy",
      "kartā": "Suman",
      "karma": "Tesla",
      "karaṇa": "$60,000"
    }
  ]
}
```

**ASHRU/1 output (~25 tokens):**

```text
ASHRU/1
V|buy|Suman|Tesla|$60000||||p|0|
```

Same fact. Roughly 4× smaller in token count under the OpenAI `cl100k_base` tokenizer.

## The format in one paragraph

Every ASHRU document begins with the line `ASHRU/1`. Each subsequent fact is one line: `V|verb|kartā|karma|karaṇa|sampradāna|apādāna|adhikaraṇa|tense|negated|attributes`. Columns are separated by `|`. Empty columns stay empty (`||`). Pipes inside values are escaped as `\|`. Tense uses `p|n|f|c`. Negation is `0` or `1`. Attributes are free `key=value;key=value`.

The full spec is in [`SPEC.md`](SPEC.md).

## Reference parsers

| Language | Path | License |
|---|---|---|
| Python | [`parsers/python/`](parsers/python/) | MIT |
| JavaScript | [`parsers/javascript/`](parsers/javascript/) | MIT |

Each is small, zero runtime dependencies, and passes the conformance suite under `tests/v1.0/`.

## Repository layout

```
ashru-format/
├── SPEC.md                          The wire format specification (CC0)
├── LICENSE                          MIT for parsers and tests
├── parsers/
│   ├── python/                      Python reference parser
│   └── javascript/                  JavaScript reference parser
├── tests/v1.0/                      Conformance suite (both parsers)
├── benchmarks/                      Token-cost + parser-throughput benchmarks
└── examples/
    ├── 01-chat-message.ashru        Simple fact extraction
    ├── 04-negation-and-conditional.ashru
    └── extract_batch.py             BYOK CLI for Gemini/OpenAI/Anthropic
```

## Run the conformance suite

```bash
git clone https://github.com/ashru-format/ashru-format
cd ashru-format

python3 tests/v1.0/run_python.py
node    tests/v1.0/run_javascript.mjs
```

## Run the benchmarks

```bash
pip install tiktoken
python3 benchmarks/run_benchmark.py --records 1000
```

Real numbers, real tokenizer (`tiktoken cl100k_base`), reproducible.

## Linguistic provenance

Pāṇini formalized the six kāraka case roles in his *Aṣṭādhyāyī* around the 5th century BCE: *kartā* (agent), *karma* (object), *karaṇa* (instrument), *sampradāna* (recipient), *apādāna* (source), *adhikaraṇa* (locative). Rick Briggs at NASA Ames published in 1985 *(AI Magazine,* Vol. 6, No. 1) that these six roles map cleanly onto knowledge representation in artificial intelligence. ASHRU is a 21st-century wire format for that 2,500-year-old grammatical observation.

## License

- **Specification:** CC0 1.0 Universal — public domain
- **Reference parsers + tests:** MIT
- **Benchmarks + examples:** MIT

Use freely. No attribution required, though acknowledgment is appreciated.

## Reach

Questions, criticism, ideas — open an issue or use Discussions.
