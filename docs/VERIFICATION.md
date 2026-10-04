# Verification status

The full functional/native acceptance run passed: [run 37233092875](https://github.com/Masanori-Spec/scene-reconcile/actions/runs/37233092875), exact tested commit `b313431a1739bb9839f72687e2154f0e60fa1235`.

- 87 Node tests, including 12 lightweight UI state/integrity scenarios; Node 22 and 24 both passed
- 16 independent semantic-oracle mutation tests; 14 native-controller tests
- Deterministic standalone distribution matched the committed file
- 15 sandboxed Chrome browser groups using genuine native fixtures, actual inputs and actual downloads; zero external requests or page errors
- Independent hashes/manifests passed for normal and conflict-resolved browser outputs
- All three actual browser-prepared copies passed fresh native UI Import, UUID/runtime equality, save, close and reopen
- Actual normal and conflict-resolved downloads each passed fresh native UI Import, all-scene activation, both runtime phases and both native-saved serializer checks
- Japanese/English desktop/mobile screenshots and native previews were reviewed. One decorative font-dependent symbol was replaced with inline SVG after this run; subsequent commits run the same full gate again

First native fixture evidence: [run 37231268860](https://github.com/Masanori-Spec/scene-reconcile/actions/runs/37231268860), commit `e1510e784c75ed5d02ba4478c15a4b5df1738d4e`. All baseline source UUIDs survived prepared native imports and reopened branches. The fixture files are committed with byte hashes and provenance.

| Artifact | SHA-256 |
|---|---|
| First native gate | `bdfa89235a8b7eeb1e325b628a4d556a4c8f65352172e9f5bd864a1d2816c42b` |
| Corrected browser gate | `6e7008bf75ba8cdb76aa304a2d2bb2318fc4c9bab5fe739bd97d0374354113e5` |
| Corrected native consumer | `ce6e22c15c85a26c9544a99f4cab344c949f48bb91e53eced103dad5ed57a296` |
| Actual normal browser output | `a653e6e4cda49f6685dabd885af74b7bf5db0fad6d7ec8e995977ed1a3b5dd96` |
| Actual conflict-resolved browser output | `8e17ec066548b16ccce13c7fd4fde8afed2c5fc47508f5daf2d008e10d93a9c1` |

All ten final native launch logs had zero targeted source/UUID/load semantic failures. Optional GPU/DeckLink/VLC/portal and shutdown diagnostics remain recorded for review; this is not a warning-free-log claim. Native tests use only colors, FreeType text and nested scenes. Existing capture/media preservation has synthetic coverage, without opening devices or media.

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
