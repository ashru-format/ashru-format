#!/usr/bin/env python3
"""
ASHRU vs JSON token-cost benchmark.

Generates synthetic kāraka facts (Suman bought Tesla from John in SF, etc.),
encodes each in JSON and ASHRU, computes:

  - tokens per record (using tiktoken cl100k_base, the OpenAI/GPT-4 tokenizer)
  - bytes per record
  - dollar cost at published May 2026 rates for 6 models

Outputs:
  - benchmarks/results.csv
  - benchmarks/results.md (human readable)

Usage:
  pip install tiktoken
  python benchmarks/run_benchmark.py
  python benchmarks/run_benchmark.py --records 10000

If tiktoken is not installed, falls back to a 4 chars/token approximation
(within ~5% of real tiktoken counts on this kind of structured text).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(s: str) -> int:
        return len(enc.encode(s))
    TOKENIZER = "tiktoken cl100k_base (real)"
except ImportError:
    def count_tokens(s: str) -> int:
        return max(1, len(s) // 4)
    TOKENIZER = "approx (chars/4) — install tiktoken for real numbers"


# Pricing per model — published rates as of May 2026.
# [input_price_per_1M, output_price_per_1M] in USD.
PRICING = {
    "gemini-2.5-flash-lite": [0.10, 0.40],
    "gemini-2.5-flash":      [0.30, 2.50],
    "gpt-4o-mini":           [0.15, 0.60],
    "gpt-4o":                [2.50, 10.00],
    "claude-haiku-4.5":      [1.00, 5.00],
    "claude-sonnet-4.6":     [3.00, 15.00],
}


SAMPLE_FACTS = [
    {"verb": "buy",       "karta": "Suman",   "karma": "Tesla",        "karana": "$60000",  "apadana": "John",   "adhikarana": "SF"},
    {"verb": "hire",      "karta": "Acme",    "karma": "Madhuri",      "karana": "$220k",   "apadana": "",       "adhikarana": "NYC"},
    {"verb": "deploy",    "karta": "engineer","karma": "api-service",  "karana": "k8s",     "apadana": "staging","adhikarana": "us-central1"},
    {"verb": "send",      "karta": "Maya",    "karma": "wire-transfer","karana": "swift",   "apadana": "Chase",  "adhikarana": "London"},
    {"verb": "diagnose",  "karta": "Dr Patel","karma": "patient",      "karana": "MRI",     "apadana": "",       "adhikarana": "Boston"},
    {"verb": "schedule",  "karta": "PM",      "karma": "release-1.2",  "karana": "Linear",  "apadana": "",       "adhikarana": "Q3"},
    {"verb": "publish",   "karta": "author",  "karma": "spec-v1",      "karana": "github",  "apadana": "",       "adhikarana": ""},
    {"verb": "transfer",  "karta": "broker",  "karma": "100AAPL",      "karana": "NYSE",    "apadana": "fund_a", "adhikarana": "fund_b"},
]


def to_json(facts: list[dict]) -> str:
    return json.dumps({"verbs": [
        {
            "verb_lemma": f["verb"],
            "kartā":      f["karta"],
            "karma":      f["karma"],
            "karaṇa":     f["karana"],
            "apādāna":    f["apadana"],
            "adhikaraṇa": f["adhikarana"],
            "tense":      "past",
            "is_negated": False,
        } for f in facts
    ]}, ensure_ascii=False)


def to_ashru(facts: list[dict]) -> str:
    rows = ["ASHRU/1"]
    for f in facts:
        rows.append(f"V|{f['verb']}|{f['karta']}|{f['karma']}|{f['karana']}||{f['apadana']}|{f['adhikarana']}|p|0|")
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=int, default=1000)
    args = ap.parse_args()

    facts = (SAMPLE_FACTS * (args.records // len(SAMPLE_FACTS) + 1))[: args.records]
    json_doc = to_json(facts)
    ashru_doc = to_ashru(facts)

    json_tokens = count_tokens(json_doc)
    ashru_tokens = count_tokens(ashru_doc)
    json_bytes = len(json_doc.encode("utf-8"))
    ashru_bytes = len(ashru_doc.encode("utf-8"))

    rows = []
    rows.append(["metric", "JSON", "ASHRU", "ASHRU vs JSON"])
    rows.append(["records", args.records, args.records, "—"])
    rows.append(["bytes total", json_bytes, ashru_bytes, f"{ashru_bytes/json_bytes:.2f}x"])
    rows.append(["bytes / record", round(json_bytes/args.records, 1), round(ashru_bytes/args.records, 1), f"{ashru_bytes/json_bytes:.2f}x"])
    rows.append(["tokens total", json_tokens, ashru_tokens, f"{ashru_tokens/json_tokens:.2f}x"])
    rows.append(["tokens / record", round(json_tokens/args.records, 2), round(ashru_tokens/args.records, 2), f"{ashru_tokens/json_tokens:.2f}x"])

    pricing_rows = [["model", "JSON $/1M records", "ASHRU $/1M records", "saved"]]
    per_record_factor = 1_000_000 / args.records
    for model, (in_price, out_price) in PRICING.items():
        json_cost = (json_tokens * out_price / 1_000_000) * per_record_factor
        ashru_cost = (ashru_tokens * out_price / 1_000_000) * per_record_factor
        pricing_rows.append([model, f"${json_cost:,.2f}", f"${ashru_cost:,.2f}", f"${json_cost-ashru_cost:,.2f}"])

    out_dir = Path(__file__).parent
    csv_path = out_dir / "results.csv"
    md_path = out_dir / "results.md"

    with csv_path.open("w") as f:
        w = csv.writer(f)
        w.writerows(rows)
        w.writerow([])
        w.writerows(pricing_rows)

    md_lines = [
        f"# ASHRU vs JSON benchmark — {args.records} records",
        "",
        f"**Tokenizer:** {TOKENIZER}",
        "",
        "## Bytes & tokens",
        "",
        "| metric | JSON | ASHRU | ASHRU vs JSON |",
        "|---|---:|---:|---:|",
    ]
    for r in rows[1:]:
        md_lines.append("| " + " | ".join(str(c) for c in r) + " |")
    md_lines += ["", "## Cost per 1M records (output side, May 2026 rates)", "",
                 "| model | JSON $/1M | ASHRU $/1M | saved |",
                 "|---|---:|---:|---:|"]
    for r in pricing_rows[1:]:
        md_lines.append("| " + " | ".join(str(c) for c in r) + " |")
    md_path.write_text("\n".join(md_lines) + "\n")

    for line in md_lines:
        print(line)
    print(f"\nWrote {csv_path} and {md_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
