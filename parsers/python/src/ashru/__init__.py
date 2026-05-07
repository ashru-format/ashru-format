"""
ASHRU/1 reference parser — Python.

Released under MIT. See LICENSE in the repo root.

Usage:
    from ashru import parse, AshruDocument, Verb

    doc = parse(text_or_file_handle)
    for verb in doc.verbs:
        print(verb.verb_lemma, verb.karta, verb.karma, verb.tense)

The parser is intentionally tolerant by default: malformed `V|` rows are
logged via the standard `logging` module and skipped, never crash the
document. Pass `strict=True` to raise on the first malformed row.

The header `ASHRU/1` is the only hard requirement — every document MUST
start with that line. Comments (`#`) and blank lines are ignored.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Iterator, TextIO

logger = logging.getLogger(__name__)

VERSION = "ASHRU/1"
VERB_COLUMN_COUNT = 11  # marker "V" + 10 data columns
VALID_TENSES = frozenset({"p", "n", "f", "c", ""})


# ─── Public dataclasses ────────────────────────────────────────────────


@dataclass
class Verb:
    verb_lemma: str
    karta: str | None = None       # kartā — agent
    karma: str | None = None       # karma — object
    karana: str | None = None      # karaṇa — instrument
    sampradana: str | None = None  # sampradāna — recipient
    apadana: str | None = None     # apādāna — source
    adhikarana: str | None = None  # adhikaraṇa — locative
    tense: str | None = None       # 'p' | 'n' | 'f' | 'c' | None
    is_negated: bool = False
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class AshruDocument:
    version: str
    verbs: list[Verb] = field(default_factory=list)
    skipped_lines: int = 0


# ─── Public API ────────────────────────────────────────────────────────


def parse(source: str | TextIO, strict: bool = False) -> AshruDocument:
    """Parse an ASHRU/1 document from a string or file handle.

    Raises ValueError if the version header is missing or unrecognized.
    If strict=True, raises ValueError on the first malformed row.
    Otherwise, malformed individual rows are skipped (with a warning).
    """
    if hasattr(source, "read"):
        text = source.read()
    else:
        text = source
    lines = iter(text.splitlines())
    return _parse_lines(lines, strict=strict)


def parse_lines(lines: Iterable[str], strict: bool = False) -> AshruDocument:
    """Parse from any iterable of lines (no trailing newlines required)."""
    return _parse_lines(iter(lines), strict=strict)


# ─── Internal ──────────────────────────────────────────────────────────


def _parse_lines(lines: Iterator[str], strict: bool = False) -> AshruDocument:
    # First non-empty non-comment line MUST be the version header.
    header = ""
    for line in lines:
        line = line.rstrip("\r\n")
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        header = stripped
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
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue  # comment

        if line.startswith("V|"):
            verb = _parse_verb_line(line, strict=strict)
            if verb is None:
                doc.skipped_lines += 1
            else:
                doc.verbs.append(verb)
            continue

        # Unknown leading marker → silently skip (LLM may emit prose) or raise if strict.
        if strict:
            raise ValueError(f"Unknown leading marker in row: {line!r}")
        doc.skipped_lines += 1

    return doc


def _parse_verb_line(line: str, strict: bool = False) -> Verb | None:
    """Parse a single V|... line. Returns None and logs on malformed input. Raises ValueError if strict=True."""
    cols = _split_with_escapes(line)
    if len(cols) != VERB_COLUMN_COUNT:
        msg = f"Malformed V| row (expected {VERB_COLUMN_COUNT} columns, got {len(cols)}): {line[:200]!r}"
        if strict:
            raise ValueError(msg)
        logger.warning("Skipping %s", msg)
        return None
    _, lemma, karta, karma, karana, sampradana, apadana, adhikarana, tense, negated, attrs = cols
    if not lemma:
        if strict:
            raise ValueError(f"Empty verb_lemma in row: {line[:200]!r}")
        logger.warning("Skipping V| row with empty verb_lemma: %r", line[:200])
        return None
    if tense and tense not in VALID_TENSES:
        if strict:
            raise ValueError(f"Unknown tense {tense!r} in row: {line[:200]!r}")
        logger.warning("Unknown tense %r in row, storing as None", tense)
        tense = ""
    is_negated = negated.strip() == "1"
    attributes = _parse_attributes(attrs)
    return Verb(
        verb_lemma=lemma.strip().lower(),
        karta=_n(karta),
        karma=_n(karma),
        karana=_n(karana),
        sampradana=_n(sampradana),
        apadana=_n(apadana),
        adhikarana=_n(adhikarana),
        tense=_n(tense),
        is_negated=is_negated,
        attributes=attributes,
    )


def _split_with_escapes(line: str) -> list[str]:
    """Split on '|' but respect '\\|' escape and '\\\\' double-backslash."""
    out: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            nxt = line[i + 1]
            if nxt == "|":
                buf.append("|")
                i += 2
                continue
            if nxt == "\\":
                buf.append("\\")
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
    """Parse 'k1=v1;k2=v2' into a dict. Tolerate empty input + malformed pairs."""
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
    """Empty string → None; otherwise stripped string."""
    s = s.strip()
    return s if s else None


# ─── Encoder (round-trip support) ──────────────────────────────────────


def encode(doc: AshruDocument) -> str:
    """Encode an AshruDocument back into ASHRU/1 wire format."""
    lines = [VERSION]
    for v in doc.verbs:
        lines.append(_encode_verb(v))
    return "\n".join(lines) + "\n"


def _encode_verb(v: Verb) -> str:
    cols = [
        "V",
        v.verb_lemma,
        v.karta or "",
        v.karma or "",
        v.karana or "",
        v.sampradana or "",
        v.apadana or "",
        v.adhikarana or "",
        v.tense or "",
        "1" if v.is_negated else "0",
        _encode_attrs(v.attributes),
    ]
    return "|".join(_escape(c) for c in cols)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("|", "\\|")


def _encode_attrs(attrs: dict[str, str]) -> str:
    if not attrs:
        return ""
    return ";".join(f"{k}={v}" for k, v in attrs.items())


__all__ = [
    "Verb",
    "AshruDocument",
    "parse",
    "parse_lines",
    "encode",
    "VERSION",
]
