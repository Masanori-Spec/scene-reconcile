# SceneReconcile scope

A bounded collaboration prototype for OBS Studio 32.2.2 on Linux. Prepare parallel collections from one baseline, import each working copy into OBS, edit independently, and reconcile the exports. **Do not use OBS Duplicate**, because it regenerates source UUIDs.

## Supported profile

One canvas; matching coordinate mode, migration resolution and output resolution; at most 20 scenes, 200 sources, and 1,000 scene items. Color sources, native Linux FreeType text sources, and ordinary nested scenes. Source UUIDs provide identity; item IDs are local to each scene. Collection names may differ. Source-array ordering is irrelevant.

Existing built-in capture/media source settings remain operator-owned. Incoming unsupported changes require explicit exclusion, recorded in the receipt. Unknown semantic changes never disappear silently. Custom source plugins, groups, filters, scripts, multiple canvases, deletion, rename, media asset packaging, and cross-platform conversion are outside this profile.

## Merge units

- Source settings are atomic
- A scene item's complete transform is atomic: absolute and relative position/scale/bounds, scale reference, alignment, rotation, bounds mode/crop and four crop edges
- Visibility and lock are separate units
- Membership and stacking order form a joint unit; parallel added item IDs are not assumed to identify the same item
- Added scenes carry their new-source dependency closure and can reference existing shared sources

Every supported one-sided edit can be accepted. Equal edits are retained once. Different edits to the same unit need an explicit decision. Source settings changes report transitive affected scenes, including hidden uses. Export is blocked for unresolved decisions, invalid references, duplicate source names/UUIDs, and nesting cycles.

## Evidence standard

Compatibility is gated by native consumer tests, not by JSON readability. The independent oracle/expected.json manifest was fixed before application implementation. Native fixture generation, prepared-copy Import/save/reopen, actual browser downloads, a separate Python reader, and a fresh OBS Import/save/reopen must all pass. Every scene is inspected via the official runtime API and rendered for review. Unrun stages are explicitly unverified.

This project does not claim universal OBS compatibility or patent novelty.

New additions are stricter than preserved existing sources: new scene settings must use the supported native keys, added source metadata must use checked native defaults, and new item metadata must use normal blending/no transition/no custom metadata. Unsupported additions block the merge rather than entering unnoticed. Source versioned IDs and serialized transition/global-source objects are validated too. Built-in output-timer and auto-scene-switcher data remain operator-owned; scripts and nonempty custom module data are rejected.

Editable source settings are type-checked against the pinned native color/FreeType text profile. Color dimensions are 1–4096 pixels; text custom width 0–4096, log lines 1–1000, font size 1–65535 and native font flags 0–15. Values with wrong types, unrecognized setting/font keys, extra vector fields or malformed serialized-source objects block export. These are explicit prototype bounds, not universal OBS settings support.
