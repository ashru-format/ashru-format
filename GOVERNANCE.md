# ASHRU Protocol Governance

ASHRU is designed to be a foundational open standard for LLM-emitted structured fact records. Because it sits at the bottom of the stack, stability is critical.

This document outlines how the protocol is governed, avoiding the "vendor-controlled standard" anti-pattern.

## 1. Licensing

The core protocol specification (`SPEC.md`) is released under **CC0 1.0 Universal** (public domain). The reference parsers and the test/benchmark code in this repository are released under the **MIT License**. They will remain so forever. You do not need commercial permission to build any product on top of the ASHRU format.

## 2. Request For Comments (RFC) Process

No breaking changes will be made to the ASHRU specification without a formal RFC.

If you wish to propose an extension to the format, you must:

1. Open an issue using the `[RFC]` template.
2. Provide a Python or JavaScript reference implementation demonstrating how existing `strict=True` parsers will handle the change.
3. Allow a 14-day community review period.

## 3. Versioning

We follow Semantic Versioning (SemVer) for the parsers and the spec.

- **MAJOR** version bumps: Protocol-level changes (e.g., changing the `|` delimiter or column count).
- **MINOR** version bumps: New parsing features that are fully backwards-compatible with older protocol versions.
- **PATCH** version bumps: Bug fixes and parser hardening that do not change the format.
