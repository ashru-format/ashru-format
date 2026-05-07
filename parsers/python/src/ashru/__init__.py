"""
ashru — Pāṇini grammar in 10 columns. One pipe row → one sentence.

Read-only library. ASHRU is a wire format LLMs emit to save tokens; this
package reads those rows back into Python objects and natural-language
sentences. Released under MIT.

Quick start:

    import ashru

    # 1. Add ashru.PROMPT_INSTRUCTION to your existing LLM call
    response = my_llm.generate(ashru.PROMPT_INSTRUCTION + "\\n\\n" + question)

    # 2. Parse the LLM's reply
    doc = ashru.parse(response)

    # 3. Read each fact as Python or as English
    for v in doc.verbs:
        print(v.karta, v.verb_lemma, v.karma)   # structured
        print(ashru.to_sentence(v))             # English sentence

The first line of every document MUST be `ASHRU/1`. Comments start with `#`.
Malformed rows are logged and skipped (use `strict=True` to raise instead).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Iterator, TextIO

logger = logging.getLogger(__name__)

VERSION = "ASHRU/1"
VERB_COLUMN_COUNT = 11
VALID_TENSES = frozenset({"p", "n", "f", "c", ""})

PROMPT_INSTRUCTION = """\
Output your response as ASHRU/1 — a 10-column pipe-delimited fact format.

Each fact = one line. Format:
V|verb_lemma|karta|karma|karana|sampradana|apadana|adhikarana|tense|negated|attributes

Columns:
 1. V          — row marker (always the literal letter V)
 2. verb_lemma — base verb, lowercase (e.g. "buy", "deploy", "validate")
 3. karta      — agent / who did it
 4. karma      — direct object / what was done
 5. karana     — instrument (with what)
 6. sampradana — recipient (to whom)
 7. apadana    — source (from where / from whom)
 8. adhikarana — locative (where)
 9. tense      — p (past) | n (present) | f (future) | c (conditional)
10. negated    — 1 if negated, otherwise 0
11. attributes — k=v;k=v pairs (e.g. date=2026-05-07;amount=60000) or empty

Empty columns are written as adjacent pipes ||. A literal pipe inside a
value is escaped as \\|. A literal backslash is escaped as \\\\.

The first line of the document MUST be: ASHRU/1
Do not add prose, JSON, or markdown around the rows. Pipe rows only.

Example:
ASHRU/1
V|buy|Suman|Tesla|$60000||John|SF|p|0|date=2026-05-07
V|deploy|engineer|api||||staging|f|0|
"""


@dataclass
class Verb:
    verb_lemma: str
    karta: str | None = None
    karma: str | None = None
    karana: str | None = None
    sampradana: str | None = None
    apadana: str | None = None
    adhikarana: str | None = None
    tense: str | None = None
    is_negated: bool = False
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class AshruDocument:
    version: str
    verbs: list[Verb] = field(default_factory=list)
    skipped_lines: int = 0


def parse(source: str | TextIO, strict: bool = False) -> AshruDocument:
    """Parse an ASHRU/1 document from a string or file handle."""
    text = source.read() if hasattr(source, "read") else source
    return _parse_lines(iter(text.splitlines()), strict=strict)


def parse_lines(lines: Iterable[str], strict: bool = False) -> AshruDocument:
    """Parse from any iterable of lines."""
    return _parse_lines(iter(lines), strict=strict)


def to_sentence(v: Verb) -> str:
    """Convert one parsed Verb into a readable English sentence."""
    parts: list[str] = []
    if v.karta:
        parts.append(v.karta)

    verb = v.verb_lemma
    tense = v.tense or "n"

    if tense == "f":
        parts.extend(["will not", verb] if v.is_negated else ["will", verb])
    elif tense == "c":
        parts.extend(["would not", verb] if v.is_negated else ["would", verb])
    elif tense == "p":
        if v.is_negated:
            parts.extend(["did not", verb])
        else:
            parts.append(_past(verb))
    else:  # present
        if v.is_negated:
            parts.extend(["does not", verb])
        else:
            parts.append(_present(verb, v.karta))

    if v.karma:
        parts.append(v.karma)
    if v.karana:
        parts.append(f"with {v.karana}")
    if v.sampradana:
        parts.append(f"to {v.sampradana}")
    if v.apadana:
        parts.append(f"from {v.apadana}")
    if v.adhikarana:
        parts.append(f"at {v.adhikarana}")

    sentence = " ".join(parts)
    if v.attributes:
        attrs = ", ".join(f"{k}={x}" for k, x in v.attributes.items())
        sentence = f"{sentence} ({attrs})"
    return sentence + "."


# ─── Internal ──────────────────────────────────────────────────────────


_IRREGULAR_PAST = {
    "be": "was", "begin": "began", "break": "broke", "bring": "brought",
    "build": "built", "buy": "bought", "catch": "caught", "choose": "chose",
    "come": "came", "cost": "cost", "cut": "cut", "deal": "dealt",
    "do": "did", "draw": "drew", "drink": "drank", "drive": "drove",
    "eat": "ate", "fall": "fell", "feed": "fed", "feel": "felt",
    "fight": "fought", "find": "found", "fly": "flew", "forget": "forgot",
    "get": "got", "give": "gave", "go": "went", "grow": "grew",
    "have": "had", "hear": "heard", "hit": "hit", "hold": "held",
    "keep": "kept", "know": "knew", "leave": "left", "lend": "lent",
    "let": "let", "lose": "lost", "make": "made", "mean": "meant",
    "meet": "met", "pay": "paid", "put": "put", "read": "read",
    "ride": "rode", "ring": "rang", "rise": "rose", "run": "ran",
    "say": "said", "see": "saw", "sell": "sold", "send": "sent",
    "set": "set", "shut": "shut", "sing": "sang", "sit": "sat",
    "sleep": "slept", "speak": "spoke", "spend": "spent", "stand": "stood",
    "swim": "swam", "take": "took", "teach": "taught", "tell": "told",
    "think": "thought", "throw": "threw", "understand": "understood",
    "wake": "woke", "wear": "wore", "win": "won", "write": "wrote",
}

_IRREGULAR_PRESENT_3RD = {
    "be": "is", "have": "has", "do": "does", "go": "goes",
}


def _past(lemma: str) -> str:
    if lemma in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[lemma]
    if lemma.endswith("e"):
        return lemma + "d"
    if (len(lemma) > 1 and lemma.endswith("y")
            and lemma[-2] not in "aeiou"):
        return lemma[:-1] + "ied"
    return lemma + "ed"


def _present(lemma: str, subject: str | None) -> str:
    """Third-person singular only when the subject looks singular."""
    if not subject or _looks_plural(subject):
        return lemma
    if lemma in _IRREGULAR_PRESENT_3RD:
        return _IRREGULAR_PRESENT_3RD[lemma]
    if lemma.endswith(("s", "x", "z", "ch", "sh")):
        return lemma + "es"
    if (len(lemma) > 1 and lemma.endswith("y")
            and lemma[-2] not in "aeiou"):
        return lemma[:-1] + "ies"
    return lemma + "s"


def _looks_plural(subject: str) -> bool:
    s = subject.strip().lower()
    return s in {"we", "they", "you", "i"} or s.endswith("s")


def _parse_lines(lines: Iterator[str], strict: bool = False) -> AshruDocument:
    header = ""
    for raw in lines:
        line = raw.rstrip("\r\n").strip()
        if not line or line.startswith("#"):
            continue
        header = line
        break
    if header != VERSION:
        raise ValueError(
            f"Expected ASHRU header {VERSION!r}, got {header!r}. "
            f"Document is not a valid ASHRU/1 stream."
        )

    doc = AshruDocument(version=VERSION)
    for raw in lines:
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("V|"):
            v = _parse_verb_line(line, strict=strict)
            if v is None:
                doc.skipped_lines += 1
            else:
                doc.verbs.append(v)
            continue
        if strict:
            raise ValueError(f"Unknown leading marker in row: {line!r}")
        doc.skipped_lines += 1
    return doc


def _parse_verb_line(line: str, strict: bool = False) -> Verb | None:
    cols = _split_with_escapes(line)
    if len(cols) != VERB_COLUMN_COUNT:
        msg = (f"Malformed V| row (expected {VERB_COLUMN_COUNT} columns, "
               f"got {len(cols)}): {line[:200]!r}")
        if strict:
            raise ValueError(msg)
        logger.warning("Skipping %s", msg)
        return None
    _, lemma, karta, karma, karana, sampradana, apadana, adhikarana, tense, neg, attrs = cols
    if not lemma:
        if strict:
            raise ValueError(f"Empty verb_lemma in row: {line[:200]!r}")
        logger.warning("Skipping V| row with empty verb_lemma: %r", line[:200])
        return None
    if tense and tense not in VALID_TENSES:
        if strict:
            raise ValueError(f"Unknown tense {tense!r} in row: {line[:200]!r}")
        logger.warning("Unknown tense %r, storing as None", tense)
        tense = ""
    return Verb(
        verb_lemma=lemma.strip().lower(),
        karta=_n(karta),
        karma=_n(karma),
        karana=_n(karana),
        sampradana=_n(sampradana),
        apadana=_n(apadana),
        adhikarana=_n(adhikarana),
        tense=_n(tense),
        is_negated=neg.strip() == "1",
        attributes=_parse_attributes(attrs),
    )


def _split_with_escapes(line: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            nxt = line[i + 1]
            if nxt in ("|", "\\"):
                buf.append(nxt)
                i += 2
                continue
        if c == "|":
            out.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    out.append("".join(buf))
    return out


def _parse_attributes(s: str) -> dict[str, str]:
    s = s.strip()
    if not s:
        return {}
    out: dict[str, str] = {}
    for pair in s.split(";"):
        if "=" not in pair:
            continue
        k, _, v = pair.partition("=")
        k = k.strip()
        if not k:
            continue
        out[k] = v.strip()
    return out


def _n(s: str) -> str | None:
    s = s.strip()
    return s if s else None


__all__ = [
    "Verb",
    "AshruDocument",
    "parse",
    "parse_lines",
    "to_sentence",
    "PROMPT_INSTRUCTION",
    "VERSION",
]
