"""
ASHRU/1 reference test suite — Python.

Run from repo root:
    PYTHONPATH=parsers/python/src python3 -m unittest tests.python.test_ashru -v

Or with pytest:
    PYTHONPATH=parsers/python/src pytest tests/python -v

Covers:
    1. Parsing each shipped example.
    2. Round-trip encode → parse → match.
    3. Tolerance for malformed and prose-mixed input.
    4. Header validation rejection.
    5. Escape handling for pipes inside values.
    6. Attribute parsing edge cases.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Make the parser importable when running from repo root
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "parsers" / "python" / "src"))

from ashru import (  # noqa: E402
    parse,
    encode,
    AshruDocument,
    Verb,
    VERSION,
)

EXAMPLES = ROOT / "examples"


class ParseExamplesTest(unittest.TestCase):
    """Each shipped example must parse cleanly."""

    def test_chat_message(self):
        doc = parse((EXAMPLES / "01-chat-message.ashru").read_text())
        self.assertEqual(len(doc.verbs), 1)
        v = doc.verbs[0]
        self.assertEqual(v.verb_lemma, "buy")
        self.assertEqual(v.karta, "Suman")
        self.assertEqual(v.karma, "Tesla")
        self.assertEqual(v.karana, "$60000")
        self.assertEqual(v.apadana, "John")
        self.assertEqual(v.adhikarana, "SF")
        self.assertEqual(v.tense, "p")
        self.assertFalse(v.is_negated)
        self.assertEqual(v.attributes["date"], "2026-05-05")

    def test_negation_and_conditional(self):
        doc = parse((EXAMPLES / "04-negation-and-conditional.ashru").read_text())
        self.assertGreaterEqual(len(doc.verbs), 2)
        self.assertTrue(doc.verbs[0].is_negated)


class RoundTripTest(unittest.TestCase):
    """encode → parse should preserve all data."""

    def test_simple_round_trip(self):
        original = parse((EXAMPLES / "04-negation-and-conditional.ashru").read_text())
        encoded = encode(original)
        parsed = parse(encoded)
        self.assertEqual(len(parsed.verbs), len(original.verbs))
        for orig, rt in zip(original.verbs, parsed.verbs):
            self.assertEqual(orig.verb_lemma, rt.verb_lemma)
            self.assertEqual(orig.is_negated, rt.is_negated)
            self.assertEqual(orig.tense, rt.tense)
            self.assertEqual(orig.attributes, rt.attributes)


class ToleranceTest(unittest.TestCase):
    """Malformed lines should be skipped, never crash."""

    def test_malformed_lines_skipped(self):
        text = (
            "ASHRU/1\n"
            "V|buy|Suman|Tesla|||||p|0|\n"
            "this is some prose the LLM emitted by mistake\n"
            "V|broken|but|too|few|cols\n"
            "V|deploy|engineer|api||||staging|n|0|\n"
        )
        doc = parse(text)
        self.assertEqual(len(doc.verbs), 2)
        self.assertGreaterEqual(doc.skipped_lines, 2)

    def test_unknown_tense_stored_as_none(self):
        text = "ASHRU/1\nV|buy|Suman|Tesla|||||xyzzy|0|\n"
        doc = parse(text)
        self.assertEqual(len(doc.verbs), 1)
        self.assertIsNone(doc.verbs[0].tense)

    def test_empty_verb_lemma_skipped(self):
        text = "ASHRU/1\nV||Suman|Tesla|||||p|0|\n"
        doc = parse(text)
        self.assertEqual(len(doc.verbs), 0)
        self.assertGreaterEqual(doc.skipped_lines, 1)


class HeaderValidationTest(unittest.TestCase):
    """The version header is the only hard requirement."""

    def test_missing_header_rejected(self):
        with self.assertRaises(ValueError):
            parse("V|buy|Suman|Tesla|||||p|0|")

    def test_wrong_version_rejected(self):
        with self.assertRaises(ValueError):
            parse("ASHRU/2\nV|buy|Suman|Tesla|||||p|0|")

    def test_xml_rejected(self):
        with self.assertRaises(ValueError):
            parse("<?xml version='1.0'?><verbs/>")

    def test_blank_lines_before_header_ok(self):
        text = "\n\n\nASHRU/1\nV|buy|Suman|Tesla|||||p|0|\n"
        doc = parse(text)
        self.assertEqual(len(doc.verbs), 1)


class EscapeTest(unittest.TestCase):
    """Pipe-in-value and backslash-in-value escapes."""

    def test_escaped_pipe_in_value(self):
        text = "ASHRU/1\nV|run|engineer|cmd \\| grep|||||p|0|\n"
        doc = parse(text)
        self.assertEqual(len(doc.verbs), 1)
        self.assertEqual(doc.verbs[0].karma, "cmd | grep")

    def test_escaped_backslash_in_value(self):
        text = "ASHRU/1\nV|set|user|path \\\\to\\\\file|||||p|0|\n"
        doc = parse(text)
        self.assertEqual(doc.verbs[0].karma, "path \\to\\file")

    def test_round_trip_preserves_escapes(self):
        v = Verb(verb_lemma="run", karta="engineer", karma="cmd | grep")
        doc = AshruDocument(version=VERSION, verbs=[v])
        encoded = encode(doc)
        re_parsed = parse(encoded)
        self.assertEqual(re_parsed.verbs[0].karma, "cmd | grep")


class AttributesTest(unittest.TestCase):
    def test_multiple_attributes(self):
        text = "ASHRU/1\nV|buy|Suman|Tesla|||||p|0|price=60000;currency=USD;model=Y\n"
        doc = parse(text)
        self.assertEqual(doc.verbs[0].attributes, {
            "price": "60000",
            "currency": "USD",
            "model": "Y",
        })

    def test_empty_attribute_value(self):
        text = "ASHRU/1\nV|buy|Suman|Tesla|||||p|0|note=\n"
        doc = parse(text)
        self.assertEqual(doc.verbs[0].attributes, {"note": ""})

    def test_malformed_attribute_pair_skipped(self):
        text = "ASHRU/1\nV|buy|Suman|Tesla|||||p|0|valid=1;junk;also=2\n"
        doc = parse(text)
        self.assertEqual(doc.verbs[0].attributes, {"valid": "1", "also": "2"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
