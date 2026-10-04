# Verification status

This is an in-progress checkpoint. Native, browser and visual acceptance have not yet passed. Do not read authored harnesses as evidence of execution.

## Independent expectation fixed first

oracle/expected.json and oracle/expected.sha256 were written before the application. The manifest fixes source symbols, required exact native UUID ancestry, the six-to-eight-source outcome, every scene membership, all expected positions/visibility/lock/default transforms, branch-winning complete transform atoms, and hidden transitive shared-source impact. Native UUIDs are read from the baseline/incoming sources before application output exists. Expected semantic values are never derived from the merged output.

## Layers

1. Product tests exercise merge atoms, unsupported changes, references, conflicts, limit checks, reordered arrays and parallel item-ID collisions
2. Independent Python reader rejects wrong UUIDs, wrong text/color, wrong transforms, omitted relative fields, hidden visibility loss, reordered stack and wrong references
3. CI-only native first gate creates and edits real OBS sources, uses native UI Import of prepared copies, saves and reopens every branch
4. Sandboxed browser test must download the actual collection and receipt through the UI, including a conflict decision
5. Python compares the exact downloaded bytes to the independent manifest and receipt hashes
6. Fresh native UI Import of the downloaded collection must activate every scene, record runtime source/item settings and previews, save, close and reopen; the independent runtime reader checks both passes
7. A reviewer inspects browser screenshots, native screenshots/previews, source ZIP parity and all known limitations

Native and browser artifacts must remain separate so a browser pass cannot stand in for consumer compatibility. Evidence shall bind the exact tested commit and downloaded output hash. Unrun/failed checks remain explicit until resolved.
