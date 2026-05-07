"""
LangChain integration — drop-in ASHRU extraction.

Replaces the typical Pydantic-JSON output parser with an ASHRU parser.
Same prompt structure, ~4x fewer output tokens, identical downstream
processing. Works with any LangChain LLM (ChatOpenAI, ChatAnthropic,
ChatGoogleGenerativeAI, etc.).
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import BaseOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

# Add this repo to your path, or pip install once we publish to PyPI:
# from ashru import parse  # see parsers/python/ashru.py
import sys
sys.path.insert(0, "../../parsers/python")
from ashru import parse


# ──────────────────────────────────────────────────────────────────────
# 1. The prompt — same kāraka instructions as extract_batch.py
# ──────────────────────────────────────────────────────────────────────

ASHRU_PROMPT = ChatPromptTemplate.from_template("""\
You are a Pāṇinian kāraka extractor. Output ASHRU/1 with one V| line per fact.
Format: V|verb_lemma|kartā|karma|karaṇa|sampradāna|apādāna|adhikaraṇa|tense|negated|attributes
Tense codes: p (past) | n (now) | f (future) | c (conditional). Negated: 0 or 1.
Empty cells stay empty. Lowercase verb_lemma. One header, many V| lines.
No commentary — ASHRU/1 ONLY.

Input:
{text}
""")


# ──────────────────────────────────────────────────────────────────────
# 2. The output parser — wraps the reference ashru.parse()
# ──────────────────────────────────────────────────────────────────────

class AshruOutputParser(BaseOutputParser):
    """LangChain output parser for ASHRU/1 documents."""
    @property
    def _type(self) -> str:
        return "ashru"

    def parse(self, text: str):
        # Strip any markdown fences the LLM might add
        text = text.strip()
        for fence in ("```ashru", "```text", "```", "~~~"):
            if text.startswith(fence):
                text = text[len(fence):].strip()
            if text.endswith("```") or text.endswith("~~~"):
                text = text.rsplit("```", 1)[0].rsplit("~~~", 1)[0].strip()
        # Find the ASHRU/1 header — strip any preamble
        idx = text.find("ASHRU/1")
        if idx > 0:
            text = text[idx:]
        # Use the reference parser
        doc = parse(text)
        return [
            {
                "verb_lemma": v.verb_lemma,
                "karta": v.karta,
                "karma": v.karma,
                "karana": v.karana,
                "sampradana": v.sampradana,
                "apadana": v.apadana,
                "adhikarana": v.adhikarana,
                "tense": v.tense,
                "is_negated": v.is_negated,
                "attributes": v.attributes,
            }
            for v in doc.verbs
        ]


# ──────────────────────────────────────────────────────────────────────
# 3. Wire it up — your existing LangChain chain, ASHRU edition
# ──────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)

chain = ASHRU_PROMPT | llm | AshruOutputParser()


if __name__ == "__main__":
    text = """
    Suman bought a Tesla yesterday from John in SF for $60K.
    Naveen deployed the staging API last Tuesday.
    The team will meet investors next month if QA passes.
    """
    facts = chain.invoke({"text": text})
    for f in facts:
        print(f)
    # → 3 dicts, ~4x fewer output tokens than the equivalent Pydantic-JSON chain
