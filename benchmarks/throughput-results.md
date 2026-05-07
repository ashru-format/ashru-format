# ASHRU parser throughput

_Run on Python 3.14.2, ASHRU reference parser, JSON via stdlib._

| records   | ashru_decode              | json_decode               | ashru_encode (build str)  | json_encode               |
|-----------|---------------------------|---------------------------|---------------------------|---------------------------|
| 1,000     | 277.0k rows/s (11.3 MB/s) | 1.42M rows/s (249.6 MB/s) | 4.63M rows/s (189.4 MB/s) | 1.54M rows/s (271.5 MB/s) |
| 10,000    | 264.7k rows/s (11.1 MB/s) | 1.34M rows/s (237.9 MB/s) | 4.84M rows/s (202.8 MB/s) | 1.63M rows/s (288.8 MB/s) |
| 100,000   | 257.2k rows/s (11.0 MB/s) | 1.25M rows/s (222.4 MB/s) | 4.97M rows/s (212.6 MB/s) | 1.66M rows/s (296.3 MB/s) |
| 1,000,000 | 255.6k rows/s (11.2 MB/s) | 1.28M rows/s (230.2 MB/s) | 5.16M rows/s (225.7 MB/s) | 1.71M rows/s (307.2 MB/s) |

**Honest interpretation (read this):**

- `json.loads` (used here) is implemented in C and is therefore FASTER per row
  than our pure-Python ASHRU parser. That's expected and not where ASHRU wins.
- The ASHRU win is at the LLM **output token cost** layer (see `run_benchmark.py`):
  ~71% fewer tokens generated × output \$/M tokens = real money saved per million records.
- A C-extension or Rust-backed ASHRU parser (planned post-v1.0) would close the parser
  CPU gap. Until then, ASHRU's value proposition is **token economics**, not parser speed.
- These are CPU-only numbers; LLM generation latency dominates parse cost in practice
  (an LLM emitting 25 tokens at 200 tok/s takes 125ms — far longer than any decode here).
