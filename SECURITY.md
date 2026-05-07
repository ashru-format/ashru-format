# Security Policy

## Supported Versions
Only the latest major version of the ASHRU parsers (Python and JavaScript) receive security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

ASHRU is a parsing protocol. The primary security vectors we track are **ReDoS (Regular Expression Denial of Service)**, **Memory Exhaustion**, and **Malformed Escape Injection**.

If you discover a vulnerability in the reference parsers that allows for catastrophic backtracking or arbitrary code execution via maliciously crafted ASHRU tuples, **do not open a public issue.**

Please email `security@ashru.dev`.

We will respond within 48 hours and issue a coordinated patch and advisory across both PyPI and npm ecosystems simultaneously to protect downstream consumers.
