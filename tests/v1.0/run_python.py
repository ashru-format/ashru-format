#!/usr/bin/env python3
"""Run conformance.json against the Python reference parser.

Usage: python tests/v1.0/run_python.py
Exit code 0 on all pass, 1 on any failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add Python parser src to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "parsers" / "python" / "src"))

from ashru import parse  # noqa: E402


def deep_subset_match(expected: dict, actual: dict) -> tuple[bool, str]:
    """Check that every key in expected matches actual (subset semantics)."""
    for k, v in expected.items():
        if isinstance(v, dict):
            sub = actual.get(k, {})
            if not isinstance(sub, dict):
                return False, f"{k}: expected dict, got {type(sub).__name__}"
            ok, msg = deep_subset_match(v, sub)
            if not ok:
                return False, f"{k}.{msg}"
        else:
            if actual.get(k) != v:
                return False, f"{k}: expected {v!r}, got {actual.get(k)!r}"
    return True, ""


def verb_to_dict(v) -> dict:
    return {
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


def main() -> int:
    cases = json.loads((Path(__file__).parent / "conformance.json").read_text())["cases"]
    passed = 0
    failed = 0
    for c in cases:
        cid = c["id"]
        inp = c["input"]
        strict = c.get("strict", False)
        try:
            doc = parse(inp, strict=strict)
            if c.get("expect_throws"):
                print(f"  {cid}: FAIL — expected throw, got doc with {len(doc.verbs)} verbs")
                failed += 1
                continue
            expected = c.get("expect", {})
            errors: list[str] = []
            if "verb_count" in expected and len(doc.verbs) != expected["verb_count"]:
                errors.append(f"verb_count: expected {expected['verb_count']}, got {len(doc.verbs)}")
            if "skipped_lines" in expected and doc.skipped_lines != expected["skipped_lines"]:
                errors.append(f"skipped_lines: expected {expected['skipped_lines']}, got {doc.skipped_lines}")
            if "first_verb" in expected and doc.verbs:
                ok, msg = deep_subset_match(expected["first_verb"], verb_to_dict(doc.verbs[0]))
                if not ok:
                    errors.append(f"first_verb.{msg}")
            if errors:
                print(f"  {cid}: FAIL — {'; '.join(errors)}")
                failed += 1
            else:
                print(f"  {cid}: PASS")
                passed += 1
        except Exception as e:
            if c.get("expect_throws"):
                print(f"  {cid}: PASS (threw {type(e).__name__})")
                passed += 1
            else:
                print(f"  {cid}: FAIL — unexpected {type(e).__name__}: {e}")
                failed += 1
    total = passed + failed
    print(f"\n{passed}/{total} passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
