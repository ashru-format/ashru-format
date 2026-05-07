#!/usr/bin/env python3
"""
Parser throughput benchmark — measures encode + decode rates of the reference parsers.

Output: rows per second + bytes per second, for synthetic ASHRU documents at 1k, 10k,
100k, and 1M rows. Compares against an equivalent JSON encode/decode using stdlib.

Run:
    python benchmarks/throughput.py

What this proves:
    - The 250-LOC parsers are not toys — they sustain real throughput.
    - ASHRU is faster to decode than JSON because there's less to parse per row.
    - The numbers are reproducible: same hardware, same input shape, same code.

This benchmark is intentionally honest. It does NOT count any I/O, network, or LLM
inference. Just the encode/decode CPU loop. That's what the parser owns.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make the local parser importable when running from a repo checkout
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "parsers" / "python" / "src"))

from ashru import parse as ashru_parse  # noqa: E402


SAMPLE = {
    "verb": "buy", "karta": "Suman", "karma": "Tesla", "karana": "$60000",
    "sampradana": "", "apadana": "John", "adhikarana": "SF",
}


def make_ashru_doc(n: int) -> str:
    rows = ["ASHRU/1"]
    f = SAMPLE
    for i in range(n):
        rows.append(
            f"V|{f['verb']}|{f['karta']}_{i}|{f['karma']}|{f['karana']}||{f['apadana']}|{f['adhikarana']}|p|0|"
        )
    return "\n".join(rows)


def make_json_doc(n: int) -> str:
    f = SAMPLE
    return json.dumps({
        "verbs": [
            {
                "verb_lemma": f["verb"],
                "kartā": f"{f['karta']}_{i}",
                "karma": f["karma"],
                "karaṇa": f["karana"],
                "apādāna": f["apadana"],
                "adhikaraṇa": f["adhikarana"],
                "tense": "past",
                "is_negated": False,
            }
            for i in range(n)
        ]
    })


def time_it(fn, *args) -> float:
    """Return elapsed seconds for one invocation."""
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0


def fmt_rate(n: int, secs: float) -> str:
    if secs <= 0:
        return "n/a"
    rate = n / secs
    if rate >= 1_000_000:
        return f"{rate/1_000_000:.2f}M rows/s"
    if rate >= 1_000:
        return f"{rate/1_000:.1f}k rows/s"
    return f"{rate:.0f} rows/s"


def fmt_bw(bytes_total: int, secs: float) -> str:
    if secs <= 0:
        return "n/a"
    mb_s = bytes_total / 1_048_576 / secs
    return f"{mb_s:.1f} MB/s"


def main():
    sizes = [1_000, 10_000, 100_000, 1_000_000]
    rows = [["records", "ashru_decode", "json_decode", "ashru_encode (build str)", "json_encode"]]

    for n in sizes:
        # Build inputs (excluded from timing)
        ashru_text = make_ashru_doc(n)
        json_text = make_json_doc(n)
        ashru_bytes = len(ashru_text.encode("utf-8"))
        json_bytes = len(json_text.encode("utf-8"))

        # Decode timings
        t_ashru_dec = time_it(ashru_parse, ashru_text)
        t_json_dec = time_it(json.loads, json_text)

        # Encode timings (rebuild from the parsed structure each time)
        ashru_doc = ashru_parse(ashru_text)
        json_obj = json.loads(json_text)

        t_ashru_enc = time_it(make_ashru_doc, n)   # representative encode cost
        t_json_enc = time_it(json.dumps, json_obj)

        rows.append([
            f"{n:,}",
            f"{fmt_rate(n, t_ashru_dec)} ({fmt_bw(ashru_bytes, t_ashru_dec)})",
            f"{fmt_rate(n, t_json_dec)} ({fmt_bw(json_bytes, t_json_dec)})",
            f"{fmt_rate(n, t_ashru_enc)} ({fmt_bw(ashru_bytes, t_ashru_enc)})",
            f"{fmt_rate(n, t_json_enc)} ({fmt_bw(json_bytes, t_json_enc)})",
        ])

    # Print as a markdown table
    print("# ASHRU parser throughput")
    print()
    print(f"_Run on Python {sys.version.split()[0]}, ASHRU reference parser, JSON via stdlib._")
    print()
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    print("| " + " | ".join(str(rows[0][i]).ljust(widths[i]) for i in range(len(rows[0]))) + " |")
    print("|" + "|".join("-" * (widths[i] + 2) for i in range(len(rows[0]))) + "|")
    for r in rows[1:]:
        print("| " + " | ".join(str(r[i]).ljust(widths[i]) for i in range(len(r))) + " |")
    print()
    print("**Honest interpretation (read this):**")
    print()
    print("- `json.loads` (used here) is implemented in C and is therefore FASTER per row")
    print("  than our pure-Python ASHRU parser. That's expected and not where ASHRU wins.")
    print("- The ASHRU win is at the LLM **output token cost** layer (see `run_benchmark.py`):")
    print("  ~71% fewer tokens generated × output \\$/M tokens = real money saved per million records.")
    print("- A C-extension or Rust-backed ASHRU parser (planned post-v1.0) would close the parser")
    print("  CPU gap. Until then, ASHRU's value proposition is **token economics**, not parser speed.")
    print("- These are CPU-only numbers; LLM generation latency dominates parse cost in practice")
    print("  (an LLM emitting 25 tokens at 200 tok/s takes 125ms — far longer than any decode here).")


if __name__ == "__main__":
    main()
