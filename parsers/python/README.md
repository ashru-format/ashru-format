# ashru

> Pāṇini grammar in 10 columns. One pipe row → one sentence.
> Invented by Suman Addanki (2026)

`ashru` is a tiny Python package that reads ASHRU/1 — a 10-column,
pipe-delimited fact format — and turns each row into a Python object or a
natural-language sentence. You can ask any LLM to emit ASHRU instead of
JSON; the output is **~80% smaller** because columns are positional, not
keyed. The reverse direction (prose → ASHRU) is your LLM's job, not this
library's.

## Install

```bash
pip install ashru
```

## How to use it (3 steps)

### 1. Add the prompt instruction to your existing LLM call

```python
import ashru
import openai  # or anthropic, google.generativeai, anything

response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": ashru.PROMPT_INSTRUCTION},
        {"role": "user",   "content": "Suman bought a Tesla from John in SF for $60000 last week."},
    ],
)
text = response.choices[0].message.content
```

`ashru.PROMPT_INSTRUCTION` is a ~25-line string that tells the model to
emit pipe rows in the 10-column format. Drop it into your existing prompt
unchanged.

### 2. Parse the LLM's reply

```python
doc = ashru.parse(text)

for v in doc.verbs:
    print(v.karta, v.verb_lemma, v.karma, v.tense)
```

### 3. Or read each fact as a sentence

```python
for v in doc.verbs:
    print(ashru.to_sentence(v))
# → "Suman bought Tesla with $60000 from John at SF (date=2026-05-07)."
```

## What the LLM emits

```
ASHRU/1
V|buy|Suman|Tesla|$60000||John|SF|p|0|date=2026-05-07
V|deploy|engineer|api||||staging|f|0|
V|validate|fn_authenticate|user_token|||||n|0|
```

Each row has 10 fields after the leading `V`, in this fixed order:

| # | Column       | Pāṇini role | Plain English        |
|---|--------------|-------------|----------------------|
| 1 | `verb_lemma` | dhātu       | the verb (lowercase) |
| 2 | `karta`      | kartā       | who did it           |
| 3 | `karma`      | karma       | what was done        |
| 4 | `karana`     | karaṇa      | with what            |
| 5 | `sampradana` | sampradāna  | to whom              |
| 6 | `apadana`    | apādāna     | from where/whom      |
| 7 | `adhikarana` | adhikaraṇa  | where                |
| 8 | `tense`      | —           | `p`/`n`/`f`/`c`      |
| 9 | `negated`    | —           | `1` or `0`           |
| 10| `attributes` | —           | `k=v;k=v` or empty   |

Empty columns are written as adjacent pipes `||`. A literal `|` inside a
value is escaped as `\|`. The first line of every document MUST be
`ASHRU/1`. Lines starting with `#` are comments.

## Why this exists

LLM API pricing charges per output token. JSON output spends most of its
tokens on repeated keys and braces — 1,000 records × `"verb_lemma":` is
1,000× the same word. ASHRU drops the keys (column position carries the
meaning) and the braces (one row per fact, line-delimited). Same fact,
~⅕ the bytes, at the slice of your bill that's most expensive.

## Authorship & Background

The ASHRU format was invented by **Suman Addanki** (2026), operationalizing the theoretical work of Rick Briggs (NASA, 1985) which proposed that Sanskrit's Pāṇinian kāraka grammar is mathematically well-suited for AI knowledge representation. ASHRU maps this 2,500-year-old grammatical structure into a highly-compressed, positional wire format designed specifically for the token-economics of Large Language Models.

## License

MIT. Use it however you want.
