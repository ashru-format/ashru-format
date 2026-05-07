# Contributing to ASHRU

Thanks for your interest. ASHRU is small on purpose — the format is intentionally tiny, and we want to keep it that way. The best contributions are usually one of:

1. **A reference parser in a new language** (Go, Rust, Java, Swift, Ruby, etc.)
2. **Real-world benchmarks** showing token-cost wins on your specific extraction workload
3. **Bug fixes** in the spec or reference parsers
4. **Better examples** that show ASHRU shining in a real domain

What we're *not* looking for:
- Adding columns to v1. The 10 columns are locked. New fields → discuss as v2.
- Adding new line types (`F|`, `S|`, `V|`) without a clearly motivated use case.
- Adding dependencies to the reference parsers. They MUST stay zero-dep.

## Repo layout

```
SPEC.md              — the authoritative spec (CC0)
README.md            — quick-start and overview
LICENSE              — MIT for parsers; CC0 noted for spec
parsers/python/      — reference parser (zero deps, Python 3.10+)
parsers/javascript/  — reference parser (zero deps, ESM, Node 18+)
examples/            — sample ASHRU documents
tests/               — test suites for the reference parsers
website/             — ashru.dev landing page
```

## Adding a parser in a new language

The bar for an "official-ish" reference parser:

1. **Zero runtime dependencies.** Standard library only.
2. **Same public API** as the existing Python and JS parsers — `parse(text) → document`, `encode(document) → text`. Variable names are language-idiomatic, but the shape is identical.
3. **Pass the same 19 tests** the Python and JS parsers pass. Translate `tests/python/test_ashru.py` and adapt — the test cases are the contract.
4. **Tolerant by default** — malformed `V|` rows log a warning and are skipped, never raise. Only the version header is hard-required.
5. **Round-trip** — `parse(encode(doc))` must be equivalent to the original `doc`.

Open a PR with the parser under `parsers/<language>/` and the test suite under `tests/<language>/`. Keep it under ~300 lines. If it's longer, the design is probably wrong.

## Bug reports

If you find a bug in the spec (ambiguity, contradiction, or an example that doesn't parse), open an issue with:

- The exact ASHRU document that triggers it
- What you expected to happen
- What actually happens (with which parser)

If you find a bug in a parser but the spec is fine, mark the issue `parser:<language>` and we'll fix the parser.

## Spec changes

The spec is at v1 and **it's intentionally hard to change.** Format stability is a feature — apps that integrate ASHRU need to know v1 won't shift under them.

If you want to propose a v2 (additional column, new line type, breaking change), open an issue tagged `spec:proposal` with:

1. The motivation — what real workload needs this?
2. The compatibility plan — how do v1 parsers behave on v2 documents? (Spec says they must reject. Confirm that's still right.)
3. The migration cost — what does it take to upgrade existing producers and consumers?

We err on the side of keeping the spec frozen unless the new use case is large.

## License

By contributing, you agree your contributions are released under:
- **MIT** for code (parsers, tests, tooling)
- **CC0** for spec changes (so the format remains public domain)

## Code of conduct

Be honest, be technical, be kind. No marketing speak in the technical discussion. Argue from numbers when you can. Disagree with the design, not the person.
