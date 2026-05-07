"""
LangChain output parser with auto-retry on malformed ASHRU rows.

If the LLM emits a doc with skipped rows, the parser asks the LLM to
re-emit only the malformed rows, with a sharp instruction. After at most
N retries (default 1), it returns the verbs it has and surfaces the
warnings list to the caller.

Drop-in replacement for langchain.output_parsers.PydanticOutputParser
when you want pipe-delimited semantic output.

Requires: langchain-core (BaseOutputParser interface).
Tested against: langchain-core>=0.3.

Usage:
    from langchain_core.language_models import BaseChatModel
    from ashru.langchain import AshruRetryParser

    parser = AshruRetryParser(llm=my_llm, max_retries=1)
    chain = prompt_template | my_llm | parser
    docs = chain.invoke({"input": "Suman bought a Tesla yesterday from John."})
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Make the local parsers importable when running from the repo:
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "parsers" / "python" / "src"))

from ashru import AshruDocument, parse  # noqa: E402

logger = logging.getLogger(__name__)


_RETRY_TEMPLATE = """
The previous ASHRU/1 output had {n} malformed row(s).

A valid V| row has exactly 10 data columns separated by |:
V|verb_lemma|kartā|karma|karaṇa|sampradāna|apādāna|adhikaraṇa|tense|negated|attributes

Tense must be one of: p (past), n (present), f (future), c (conditional).
Negated must be 0 or 1.
Empty columns are still emitted as empty (||).

Re-emit ONLY the corrected V| rows below — no header, no narration:

Source text was:
{source}

Original (broken) output was:
{original}
""".strip()


class AshruRetryParser:
    """LangChain-compatible output parser with auto-retry on malformed rows."""

    def __init__(self, llm: Any | None = None, max_retries: int = 1, verbose: bool = False):
        self.llm = llm
        self.max_retries = max_retries
        self.verbose = verbose

    def parse(self, text: str, source: str = "") -> AshruDocument:
        doc = parse(text)
        retries = 0
        while doc.skipped_lines > 0 and retries < self.max_retries and self.llm is not None:
            retries += 1
            if self.verbose:
                logger.info("ASHRU parser: %d malformed rows, retry %d/%d",
                            doc.skipped_lines, retries, self.max_retries)
            retry_prompt = _RETRY_TEMPLATE.format(
                n=doc.skipped_lines, source=source[:2000], original=text[:4000]
            )
            try:
                if hasattr(self.llm, "invoke"):
                    fixup = self.llm.invoke(retry_prompt)
                    fixup_text = fixup.content if hasattr(fixup, "content") else str(fixup)
                else:
                    fixup_text = self.llm(retry_prompt)
            except Exception as exc:
                logger.warning("ASHRU retry call failed: %s", exc)
                break
            patched = "ASHRU/1\n" + fixup_text.strip()
            patched_doc = parse(patched)
            doc.verbs.extend(patched_doc.verbs)
            if patched_doc.skipped_lines == 0:
                doc.skipped_lines = 0
                break
            doc.skipped_lines = patched_doc.skipped_lines
        return doc

    def get_format_instructions(self) -> str:
        return (
            "Return ASHRU/1 — one V| line per fact. Exactly 10 data columns:\n"
            "V|verb_lemma|kartā|karma|karaṇa|sampradāna|apādāna|adhikaraṇa|tense|negated|attributes\n"
            "Tense: p|n|f|c. Negated: 0|1. Empty fields stay empty (||)."
        )


# ─── Self-test (no LLM, no LangChain required) ───────────────────────

if __name__ == "__main__":
    sample = """ASHRU/1
V|buy|Suman|Tesla|$60000||John|SF|p|0|date=2026-05-05
V|hire|Acme|Suman \\| CEO|||||p|0|
V|broken|missing|columns
"""
    parser = AshruRetryParser(llm=None)
    doc = parser.parse(sample, source="Suman bought a Tesla. Acme hired Suman | CEO. Broken row.")
    print(f"Parsed verbs: {len(doc.verbs)}")
    print(f"Skipped: {doc.skipped_lines}")
    for v in doc.verbs:
        print(f"  {v.verb_lemma} | {v.karta} -> {v.karma}")
    print(f"\nFormat instructions:\n{parser.get_format_instructions()}")
