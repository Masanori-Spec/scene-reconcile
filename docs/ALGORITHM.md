# Reconciliation algorithm

## Identity and profile validation

Parse bounded JSON and reject duplicate object keys, unsafe keys, nonfinite numbers and excessive nesting. Validate a single-canvas OBS scene collection, source UUID/name uniqueness, native Linux source kinds, complete transforms, local item IDs, current scenes and scene order. Resolve every reference by UUID and require the associated native name to agree. Reject scene cycles before comparison and again after merge.

Every baseline UUID must appear with the same name/kind in both branches. This explicitly rejects source deletion, rename and a Duplicate-generated UUID set instead of guessing from names. The coordinate version, output resolution and migration resolution must match. UUID matching is not a cryptographic ancestry proof; copies must follow the prepared Import workflow.

## Three-way units

For each supported unit, compare canonical values to the common baseline. If only one branch changed, choose it. If both branches chose the same value, retain it once. If they differ, require the operator/incoming decision. Source-array order does not participate in identity.

- Each non-scene source's full settings object is one unit
- Every original scene item's entire transform is one unit, including all absolute/relative pairs, scale reference, rotation, alignment, bounds and crop values
- Visibility and lock are independent units
- A scene's ordered list of item-ID/source-UUID pairs is a membership/order unit
- Added sources are carried with added scene dependencies, while pre-existing shared references retain their UUIDs

New item IDs are branch-local allocations, not evidence of shared ancestry. Parallel additions reusing one ID with different contents require a membership decision and take the complete selected new item. If one branch removes an item while the other edits it, the complete scene-settings choice is raised explicitly; otherwise a removal would silently lose the edit. ID counters reserve the maximum used on either branch.

Disjoint new sources are unioned. Conflicting objects with the same added UUID require a whole-additions choice. A selection leaving a missing dependency is rejected by final validation, never silently patched by name. All selected source names must remain unique.

## Unsupported semantics

Existing native capture/media settings remain operator-owned. Incoming changes to unsupported source settings, source/item metadata or unrecognized collection-level semantics require an explicit exclusion, unless their value already equals the operator's retained value. Exclusions appear in the receipt. Groups, filters, scripts, custom source plugins and multiple canvases are rejected as outside the profile.

Collection display name, currently selected preview/program scene and frontend viewing state are not content merge units; the operator's viewing state is retained. Scene order is separately reconciled and then adjusted to the selected source closure. No unknown source/item content field is silently discarded.

## Impact and receipts

Build a reverse reference graph from scene items and traverse it to every ancestor scene. Visibility does not prune the graph. Thus Title can affect LowerThird, Main, hidden Break and added Thanks. Final receipt impacts are computed against the selected result, not merely the incoming graph.

The receipt binds SHA-256 of the exact three input texts and the exact output collection bytes. It lists each changed unit, decision, affected scenes, added source UUIDs/dependencies and explicit exclusions. The output and receipt are generated together and cached as one stable pair; changing inputs, decisions or name invalidates that pair.
