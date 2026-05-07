#!/usr/bin/env python3
"""
extract_batch.py — drop-in batch extractor: prose → ASHRU/1 records.

The point of ASHRU is amortizing prompt overhead. Don't call the LLM once
per paragraph; send 10–50 paragraphs in ONE call and let the model emit
one ASHRU document with one V| line per fact. ~93% cheaper than the loop.

Bring-your-own-key. We never see your text or your API tokens — this
script runs entirely on your machine. No telemetry, no calls home.

═══════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════

    # 1. install one provider's SDK (only the one you use)
    pip install google-generativeai      # for --provider gemini
    pip install openai                   # for --provider openai
    pip install anthropic                # for --provider anthropic

    # 2. set your API key in the matching env var
    export GEMINI_API_KEY="..."          # for --provider gemini
    export OPENAI_API_KEY="..."          # for --provider openai
    export ANTHROPIC_API_KEY="..."       # for --provider anthropic

    # 3. pipe text in
    cat my_paragraphs.txt | python extract_batch.py
    # default provider is gemini, model is gemini-2.5-flash-lite

    # explicit provider + model
    cat my_paragraphs.txt | python extract_batch.py \\
        --provider gemini \\
        --model gemini-2.5-flash-lite

    cat my_paragraphs.txt | python extract_batch.py \\
        --provider openai \\
        --model gpt-4o-mini

    cat my_paragraphs.txt | python extract_batch.py \\
        --provider anthropic \\
        --model claude-haiku-4-5

═══════════════════════════════════════════════════════════════════════
WHAT YOU GET BACK
═══════════════════════════════════════════════════════════════════════

stdout: the ASHRU/1 document, one V| line per fact found in the input.

    ASHRU/1
    V|buy|Suman|Tesla|$60000||John|SF|p|0|date=2026-05-05
    V|deploy|engineer|api||||staging|f|0|
    V|meet|us|John||||SF|p|0|

Pipe that into the reference parser:
    cat output.ashru | python parsers/python/ashru.py
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable

# ──────────────────────────────────────────────────────────────────────
# THE PROMPT (public, MIT)
# ──────────────────────────────────────────────────────────────────────
# This is a clean, neutral kāraka extraction prompt. It is intentionally
# free of any product-specific tuning — anyone can use it as a baseline
# and refine it for their domain.
#
# Notes for prompt engineers:
#   * Kāraka roles in column order: kartā / karma / karaṇa / sampradāna /
#     apādāna / adhikaraṇa. Roles missing from the input → empty cells.
#   * Tense codes: p (past) | n (now/present) | f (future) | c (conditional)
#   * The LLM should output ONE document covering ALL input paragraphs.
#     One V| line per fact. Not one document per paragraph.

ASHRU_EXTRACTION_PROMPT = """\
You are a Pāṇinian kāraka extractor. Convert prose into ASHRU/1 records.

OUTPUT FORMAT — emit exactly this shape:

    ASHRU/1
    V|verb_lemma|kartā|karma|karaṇa|sampradāna|apādāna|adhikaraṇa|tense|negated|attributes
    V|...
    V|...

10 pipe-separated columns after the leading V|, in this order:
  1. verb_lemma   — atomic action, lowercase canonical form (e.g., "buy")
  2. kartā        — agent / who did the action
  3. karma        — object / what was acted upon
  4. karaṇa       — instrument / by-what-means / amount
  5. sampradāna   — recipient / for-whom
  6. apādāna      — source / from-whom / origin
  7. adhikaraṇa   — locative / where or when
  8. tense        — p (past) | n (now/present) | f (future) | c (conditional)
  9. negated      — 0 or 1 (1 if the input says NOT, NEVER, did not, won't, etc.)
 10. attributes   — k=v;k=v pairs for anything else (price, status, dates, etc.)

RULES:
  - Empty cells stay empty (just "||" between two pipes).
  - One V| line per distinct fact. If a paragraph has 3 facts, emit 3 lines.
  - Cover ALL paragraphs in ONE document. Do not loop or repeat the header.
  - Lowercase verb_lemma. "bought" → "buy". "deployed" → "deploy".
  - Keep entity names as they appear (proper case for people, places).
  - Do NOT add commentary, explanation, or markdown. Only the ASHRU document.
  - No trailing whitespace, no blank lines inside the document.

EXAMPLE INPUT:
    Suman bought a Tesla yesterday from John in SF for $60,000.
    He didn't tell his wife.

EXAMPLE OUTPUT:
    ASHRU/1
    V|buy|Suman|Tesla|$60000||John|SF|p|0|date=yesterday;currency=USD
    V|tell|Suman|wife|||||p|1|

Now extract from the following input. Reply with ASHRU/1 ONLY.

INPUT:
"""


# ──────────────────────────────────────────────────────────────────────
# Provider adapters — each takes (text, model) → returns ASHRU string
# ──────────────────────────────────────────────────────────────────────


def _gemini(text: str, model: str) -> str:
    """Gemini via the official google-generativeai SDK."""
    try:
        import google.generativeai as genai
    except ImportError:
        sys.exit("Install: pip install google-generativeai")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        sys.exit("Set GEMINI_API_KEY in env (or GOOGLE_AI_API_KEY).")
    genai.configure(api_key=api_key)
    m = genai.GenerativeModel(model)
    resp = m.generate_content(ASHRU_EXTRACTION_PROMPT + text)
    return resp.text.strip()


def _openai(text: str, model: str) -> str:
    """OpenAI via the official openai SDK."""
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("Install: pip install openai")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Set OPENAI_API_KEY in env.")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": ASHRU_EXTRACTION_PROMPT + text}],
    )
    return resp.choices[0].message.content.strip()


def _anthropic(text: str, model: str) -> str:
    """Anthropic via the official anthropic SDK."""
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("Install: pip install anthropic")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Set ANTHROPIC_API_KEY in env.")
    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": ASHRU_EXTRACTION_PROMPT + text}],
    )
    return resp.content[0].text.strip()


PROVIDERS: dict[str, Callable[[str, str], str]] = {
    "gemini": _gemini,
    "openai": _openai,
    "anthropic": _anthropic,
}

DEFAULT_MODEL = {
    "gemini": "gemini-2.5-flash-lite",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",
}


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────


def main() -> None:
    p = argparse.ArgumentParser(
        description="Extract ASHRU/1 records from prose. Bring your own LLM key.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="No telemetry. No calls home. Your text and your API key never leave your machine.",
    )
    p.add_argument(
        "--provider", choices=list(PROVIDERS), default="gemini",
        help="Which LLM provider to call (default: gemini)",
    )
    p.add_argument(
        "--model", default=None,
        help="Model name (default: provider-specific cheap model)",
    )
    args = p.parse_args()

    text = sys.stdin.read().strip()
    if not text:
        sys.exit("No input on stdin. Try: cat my_paragraphs.txt | extract_batch.py")

    model = args.model or DEFAULT_MODEL[args.provider]
    extractor = PROVIDERS[args.provider]
    ashru_doc = extractor(text, model)

    # Sanity check: must start with ASHRU/1
    if not ashru_doc.startswith("ASHRU/1"):
        # Some models add stray markdown or commentary; strip any preamble.
        idx = ashru_doc.find("ASHRU/1")
        if idx == -1:
            sys.exit(f"Model returned non-ASHRU output:\n{ashru_doc[:500]}")
        ashru_doc = ashru_doc[idx:]
        # Remove trailing markdown fences if present.
        for fence in ("```", "~~~"):
            if ashru_doc.endswith(fence):
                ashru_doc = ashru_doc.rsplit(fence, 1)[0].strip()

    print(ashru_doc)


if __name__ == "__main__":
    main()
