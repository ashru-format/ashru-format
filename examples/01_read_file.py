"""
01_read_file.py — read an ASHRU/1 file and print each fact as a sentence.

Run:  python examples/01_read_file.py
"""
import ashru

with open("examples/04-negation-and-conditional.ashru") as f:
    doc = ashru.parse(f)

for v in doc.verbs:
    print(ashru.to_sentence(v))

# Also access fields directly:
print(f"\nTotal verbs: {len(doc.verbs)}, skipped lines: {doc.skipped_lines}")
