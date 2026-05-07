#!/usr/bin/env python3
"""
ASHRU vs JSON parse-success benchmark — REAL LLM CALLS.

Compares first-pass parse-success rate of ASHRU and JSON across multiple
frontier models, then computes net token-cost savings AFTER retries.

This script is intentionally NOT a simulation. It refuses to run without
real API keys. Every number it outputs comes from a real API response.
We do this so the LinkedIn / blog claims can never be accused of fakery.

Required env vars (the script will skip any model whose key is missing):
    OPENAI_API_KEY      → enables gpt-4o, gpt-4o-mini
    ANTHROPIC_API_KEY   → enables claude-haiku-4.5, claude-sonnet-4.6
    GEMINI_API_KEY      → enables gemini-2.5-flash, gemini-2.5-flash-lite

Required pip packages:
    pip install openai anthropic google-generativeai ashru

Run:
    python benchmarks/parse_success_benchmark.py \
        --records 1000 \
        --models gpt-4o,claude-haiku-4.5,gemini-2.5-flash \
        --output benchmarks/parse_success_results.md

Cost warning: 1,000 records × 3 models × 2 formats = 6,000 LLM calls.
Estimated total cost at frontier rates: ~$5–$20 depending on model mix.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Make local parser importable
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "parsers" / "python" / "src"))
from ashru import parse as ashru_parse  # noqa: E402


# ─── Test prompts — each describes one kāraka extraction task ───────────

TEST_FACTS = [
    "Suman bought a Tesla Model Y from John yesterday in San Francisco for $60,000.",
    "Madhuri shipped 100 wire transfers via SWIFT from Chase Bank to Citibank in London.",
    "Dr Patel diagnosed the patient using an MRI scan at Boston General last week.",
    "The engineer deployed the api-service to production us-central1 with kubectl.",
    "Acme hired Suman as CEO in NYC for $220k annually.",
    "Maya sent a wire of $50000 from Wells Fargo to HDFC Bank yesterday.",
    "The PM scheduled the v1.2 release in Linear for next Q3.",
    "The author published the spec on GitHub under the MIT license.",
    "Vinay refactored the auth module in src/auth/google.py last Tuesday.",
    "Reyansh signed the lease with the landlord in Mumbai for ₹50000/month.",
]


# ─── Prompts (system + user pair per format) ────────────────────────────

JSON_PROMPT = """You extract structured kāraka (case-role) facts from sentences.
Return ONLY a JSON object with this exact shape:
{"verbs": [{"verb_lemma": "...", "karta": "...", "karma": "...", "karana": "...",
            "sampradana": "...", "apadana": "...", "adhikarana": "...",
            "tense": "p|n|f|c", "is_negated": false}]}
Use empty string "" for missing roles. Do not output anything except the JSON.

Sentence: {sentence}"""

ASHRU_PROMPT = """You extract structured kāraka (case-role) facts from sentences.
Return ONLY ASHRU/1 format. The ONLY format allowed is:

ASHRU/1
V|verb_lemma|karta|karma|karana|sampradana|apadana|adhikarana|tense|negated|attributes

Rules:
- 10 columns separated by | (pipe).
- Empty columns stay empty (||).
- tense ∈ {p,n,f,c}. negated ∈ {0,1}.
- Escape literal pipes inside values as \\|.
- One V| line per fact. No JSON, no markdown, no explanation. ONLY ASHRU/1.

Sentence: {sentence}"""


# ─── Result dataclasses ─────────────────────────────────────────────────

@dataclass
class ModelResult:
    model: str
    samples: int = 0
    json_first_pass_ok: int = 0
    json_total_tokens: int = 0
    json_errors: list[str] = field(default_factory=list)
    ashru_first_pass_ok: int = 0
    ashru_after_retry_ok: int = 0
    ashru_total_tokens: int = 0
    ashru_retry_tokens: int = 0
    ashru_errors: list[str] = field(default_factory=list)


# ─── Provider adapters (return: (text, output_tokens)) ──────────────────

def _call_openai(model: str, system: str, user: str) -> tuple[str, int]:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0,
    )
    return resp.choices[0].message.content or "", resp.usage.completion_tokens


def _call_anthropic(model: str, system: str, user: str) -> tuple[str, int]:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=1024,
        temperature=0,
    )
    text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    return text, resp.usage.output_tokens


def _call_gemini(model: str, system: str, user: str) -> tuple[str, int]:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    m = genai.GenerativeModel(model_name=model, system_instruction=system)
    resp = m.generate_content(user, generation_config={"temperature": 0})
    text = resp.text or ""
    out_tokens = getattr(resp.usage_metadata, "candidates_token_count", 0)
    return text, out_tokens


def _route(model: str) -> callable:
    """Pick the right SDK adapter for this model name."""
    if model.startswith(("gpt-", "o1-", "o3-")):
        return _call_openai
    if model.startswith("claude-"):
        return _call_anthropic
    if model.startswith("gemini-"):
        return _call_gemini
    raise ValueError(f"Unknown model family: {model}")


# ─── Single-record runner ───────────────────────────────────────────────

def run_one(model: str, fact: str, fmt: str) -> dict:
    """Returns: {ok, tokens, retry_tokens, error, raw}."""
    sys_prompt = "You are a precise structured-data extractor."
    user = (JSON_PROMPT if fmt == "json" else ASHRU_PROMPT).format(sentence=fact)
    out = {"ok": False, "tokens": 0, "retry_tokens": 0, "error": None, "raw": ""}

    try:
        adapter = _route(model)
        raw, tokens = adapter(model, sys_prompt, user)
        out["raw"] = raw
        out["tokens"] = tokens
    except Exception as exc:
        out["error"] = f"api_error: {exc}"
        return out

    # Parse and check correctness
    if fmt == "json":
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "verbs" in obj and len(obj["verbs"]) > 0:
                out["ok"] = True
            else:
                out["error"] = "json_shape_wrong"
        except json.JSONDecodeError as exc:
            out["error"] = f"json_decode: {exc}"
    else:  # ashru
        try:
            doc = ashru_parse(raw, strict=True)
            if len(doc.verbs) > 0:
                out["ok"] = True
            else:
                out["error"] = "ashru_no_verbs"
        except Exception as exc:
            out["error"] = f"ashru_strict: {exc}"
            # Retry: ask the model to re-emit cleanly with the failure quoted
            try:
                retry_user = (
                    f"Your previous output was malformed. Re-emit ASHRU/1 ONLY.\n"
                    f"Previous output:\n{raw[:500]}\nSentence: {fact}"
                )
                retry_raw, retry_tokens = adapter(model, sys_prompt, retry_user)
                out["retry_tokens"] = retry_tokens
                doc = ashru_parse(retry_raw, strict=True)
                if len(doc.verbs) > 0:
                    out["ok"] = True
                    out["error"] = f"recovered_after_retry: {out['error']}"
            except Exception as retry_exc:
                out["error"] = f"ashru_retry_failed: {retry_exc}"
    return out


# ─── Driver ─────────────────────────────────────────────────────────────

def benchmark_model(model: str, n: int) -> ModelResult:
    r = ModelResult(model=model, samples=n)
    print(f"\n[{model}] running {n} JSON + {n} ASHRU samples...")
    for i in range(n):
        fact = TEST_FACTS[i % len(TEST_FACTS)]

        j = run_one(model, fact, "json")
        r.json_total_tokens += j["tokens"]
        if j["ok"]:
            r.json_first_pass_ok += 1
        elif len(r.json_errors) < 5:
            r.json_errors.append(j["error"])

        a = run_one(model, fact, "ashru")
        r.ashru_total_tokens += a["tokens"]
        r.ashru_retry_tokens += a["retry_tokens"]
        if a["ok"] and a["retry_tokens"] == 0:
            r.ashru_first_pass_ok += 1
        elif a["ok"]:
            r.ashru_after_retry_ok += 1
        elif len(r.ashru_errors) < 5:
            r.ashru_errors.append(a["error"])

        if (i + 1) % 25 == 0:
            print(f"  [{model}] {i+1}/{n} · "
                  f"json_ok={r.json_first_pass_ok} · "
                  f"ashru_first={r.ashru_first_pass_ok} · "
                  f"ashru_retry={r.ashru_after_retry_ok}")
    return r


def write_report(results: list[ModelResult], out_path: str, n: int) -> None:
    lines = [
        "# ASHRU vs JSON — parse-success benchmark",
        "",
        f"_Real LLM calls. {n} records × {len(results)} models × 2 formats = "
        f"{n * len(results) * 2} API calls. Tokenizer: provider-native counts._",
        "",
        "## Per-model results",
        "",
        "| Model | JSON 1-pass | ASHRU 1-pass | ASHRU after retry | "
        "JSON tokens | ASHRU tokens | Retry tokens | Net savings |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        json_pct = r.json_first_pass_ok / max(r.samples, 1) * 100
        ashru_first_pct = r.ashru_first_pass_ok / max(r.samples, 1) * 100
        ashru_retry_pct = (r.ashru_first_pass_ok + r.ashru_after_retry_ok) / max(r.samples, 1) * 100
        ashru_total = r.ashru_total_tokens + r.ashru_retry_tokens
        net_savings = (1 - ashru_total / r.json_total_tokens) * 100 if r.json_total_tokens else 0
        lines.append(
            f"| {r.model} | {json_pct:.1f}% | {ashru_first_pct:.1f}% | {ashru_retry_pct:.1f}% | "
            f"{r.json_total_tokens:,} | {r.ashru_total_tokens:,} | {r.ashru_retry_tokens:,} | "
            f"**{net_savings:.1f}%** |"
        )

    lines += ["", "## Sample errors", ""]
    for r in results:
        if r.json_errors:
            lines.append(f"**{r.model} — JSON sample errors:**")
            for e in r.json_errors:
                lines.append(f"- `{e[:200]}`")
        if r.ashru_errors:
            lines.append(f"**{r.model} — ASHRU sample errors:**")
            for e in r.ashru_errors:
                lines.append(f"- `{e[:200]}`")
    lines += ["", "## Honest interpretation", "",
              "- 1-pass = parsed strictly without retry.",
              "- 'After retry' = parsed strictly after one re-prompt to the model.",
              "- Net savings counts retry tokens against ASHRU's column.",
              "- If ASHRU's net savings are negative, JSON wins on this workload.",
              "  Don't ship marketing claims that contradict this number."]

    Path(out_path).write_text("\n".join(lines) + "\n")
    print(f"\n✅ Report saved to {out_path}")


def main():
    ap = argparse.ArgumentParser(description="ASHRU vs JSON parse-success benchmark (real LLM calls)")
    ap.add_argument("--records", type=int, default=100,
                    help="Records per model per format (default 100; 1000 = full run)")
    ap.add_argument("--models", type=str,
                    default="gpt-4o,claude-haiku-4.5,gemini-2.5-flash",
                    help="Comma-separated model names")
    ap.add_argument("--output", type=str,
                    default="benchmarks/parse_success_results.md")
    args = ap.parse_args()

    # Refuse to run without keys — never produce fake numbers
    requested = args.models.split(",")
    available = []
    for m in requested:
        family = ("openai" if m.startswith(("gpt-", "o1-", "o3-")) else
                  "anthropic" if m.startswith("claude-") else
                  "gemini" if m.startswith("gemini-") else None)
        env_key = {"openai": "OPENAI_API_KEY",
                   "anthropic": "ANTHROPIC_API_KEY",
                   "gemini": "GEMINI_API_KEY"}.get(family)
        if env_key and os.environ.get(env_key):
            available.append(m)
        else:
            print(f"⚠️  Skipping {m} — {env_key} not set in environment")

    if not available:
        print("\n❌ Cannot run: no API keys found. Set at least one of:")
        print("   export OPENAI_API_KEY=sk-...")
        print("   export ANTHROPIC_API_KEY=sk-ant-...")
        print("   export GEMINI_API_KEY=AI...")
        print("\nThis script refuses to produce fake numbers. Add real keys and re-run.")
        sys.exit(2)

    print(f"==================================================")
    print(f"🚀 Parse-success benchmark — REAL LLM CALLS")
    print(f"   Records per format per model: {args.records}")
    print(f"   Models: {', '.join(available)}")
    print(f"   Total API calls: {args.records * len(available) * 2}")
    print(f"==================================================")

    t0 = time.time()
    results = [benchmark_model(m, args.records) for m in available]
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed/60:.1f} min")

    write_report(results, args.output, args.records)


if __name__ == "__main__":
    main()
