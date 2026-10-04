# Native OBS consumer gate

This gate targets **official OBS Studio 32.2.2 on Ubuntu 24.04 x86_64**. It is
intentionally refused outside a disposable GitHub Actions Linux runner. A local
syntax or controller unit test is not an OBS compatibility result.

## Pinned binary

`install-obs.sh` downloads the official release asset and checks SHA-256 before
installation:

- Asset: `OBS-Studio-32.2.2-Ubuntu-24.04-x86_64.deb`
- SHA-256: `b6557ca2059287210332accc94c267094050489cffffc5c832e746e3a418dab0`
- [Official release](https://github.com/obsproject/obs-studio/releases/tag/32.2.2)

No local heavyweight installation is needed or permitted by this harness. CI
uses standard Ubuntu packages for Xvfb, Openbox, xdotool, screenshots, OCR and the
Python websocket transport. OBS's bundled websocket server uses a random,
authenticated, ephemeral configuration. The controller connects on loopback.

## First gate: native fixtures, UI import, native save and reopen

```sh
bash native/install-obs.sh
dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' bash -c '
  openbox >/tmp/scene-reconcile-openbox.log 2>&1 &
  /usr/bin/python3 native/obs_gate.py prepare \
    --out evidence/native-prepare --fixtures tests/fixtures/native
'
```

1. Bootstrap an isolated, empty collection containing only an empty `Bootstrap`
   scene. This is startup plumbing, not a claimed native fixture/export. No audio
   devices, media files or capture inputs are seeded.
2. Create Main, Break, LowerThird, Background, Banner and Title via the running
   official OBS API, then remove Bootstrap. OBS allocates the UUIDs and item IDs.
3. Set fixture settings and transforms through the native API. Read every scene,
   explicitly switch it into the program view, capture OBS's rendered PNG and
   the native GUI, then gracefully quit and reopen OBS.
4. Copy the collection written by OBS's serializer to `baseline.json`. This is a
   native saved collection, not a handcrafted approximation of an export.
5. Prepare each branch by changing **only its collection name**, preserving all
   source UUIDs. Invoke the real **Scene Collection > Import** GUI, browse to that
   file, click Import, activate it, and assert every native source UUID matches
   the file. OBS's Duplicate action is deliberately not used: it regenerates
   source UUIDs.
6. Make the operator and incoming edits through OBS's API, then save, close,
   reopen, inspect, and copy the resulting native files. The conflict branch is
   imported from incoming, preserving the native UUIDs of Thanks and ThanksText.
7. Record the baseline/incoming identity maps before any application merge.

The first gate's prepared copies are harness-produced name-only copies. They
prove the native import route, not the application's preparation implementation.
The actual application downloads must pass that route in the later gate.

Outputs are `baseline.json`, `operator.json`, `incoming.json`,
`incoming-conflict.json` and `identities.json`. `prepare-result.json` is written
only after the complete native sequence succeeds.

## Final gate: the actual browser download

```sh
dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' bash -c '
  openbox >/tmp/scene-reconcile-openbox.log 2>&1 &
  /usr/bin/python3 native/obs_gate.py consume \
    --input evidence/browser/merged.json --out evidence/native-consumer
'
/usr/bin/python3 oracle/runtime_check.py evidence/native-consumer/first-load.json \
  tests/fixtures/native/baseline.json tests/fixtures/native/incoming.json
/usr/bin/python3 oracle/runtime_check.py evidence/native-consumer/reopened.json \
  tests/fixtures/native/baseline.json tests/fixtures/native/incoming.json
```

Supply the file actually downloaded in the browser test, without rewriting its
bytes. The controller hashes it, imports it via the native UI into a fresh
isolated profile, switches every scene, records native sources/settings/items,
then closes and reopens OBS and repeats the observations. It checks the supplied
file's hash again at the end. `native-saved-first.json` and `native-saved.json`
are native serializer output after each clean close.

`consumer-result.json` deliberately says **runtime-observed**, not semantic
pass. The separate pre-authored oracle must check both runtime observations and
native-saved JSON against the original branch exports. For conflict resolution,
run consume again on the actual conflict-resolved browser download, in another
fresh controller session.

## Observation contract

Each `<phase>.json` includes:

- `observationVersion: 1`, `phase`, full `GetVersion`, `GetVideoSettings` and
  `GetSceneCollectionList` results
- `inputs`: native `inputName`, `inputUuid`, `inputKind` and `settings` from
  `GetInputSettings`
- `scenes`: native `sceneName`, `sceneUuid`, `sceneIndex`,
  `activeProgramSceneVerified`, `screenshot`, and `items`
- each item: native `GetSceneItemList` fields, an explicit `GetSceneItemSource`
  result, an explicit `sceneItemTransform`, `sceneItemEnabled`, `sceneItemLocked`
- `outputs`: stream, recording and virtual-camera state; every output must be
  inactive

Scene item ordering is the native `sceneItemIndex`, not array iteration order.
The source UUID check is native runtime data, not a UUID copied from app output.
PNG previews are OBS `GetSourceScreenshot` renderings. Additional desktop PNGs
show the native app and each UI import stage. Native logs are copied separately;
ephemeral configuration/passwords are not artifacts.

## Serialization findings and intentionally narrow scope

OBS 32.2.2 uses collection `version` and resolution migration metadata to select
coordinate mode. A made-up top-level `private_settings.AbsoluteCoordinates` does
not select it. This harness uses version 2 and a 1280 × 720 canvas. Native APIs
expose absolute pixels, while the saved JSON contains relative transform fields
as well as compatibility absolute fields. A merge must preserve the complete
winning transform atom: changing only `pos` can be ignored by the native loader.

`SetSceneItemTransform` rejects a bounds width/height below 1, even for
`OBS_BOUNDS_NONE`. Newly-created native items have zero NONE bounds. The harness
preserves and immediately asserts those zeros instead of sending an invalid
setter request. Other fixture defaults are explicitly set through the API.

Only built-in color, FreeType text and nested scenes are exercised. There is no
streaming, recording, webcam, microphone, browser source, private user profile or
security-setting change. This is not evidence for every OBS source/plugin,
platform, group, animation, transition or multi-canvas format.

## Official implementation references

- [Native import dialog](https://github.com/obsproject/obs-studio/blob/32.2.2/frontend/importer/OBSImporter.cpp)
- [OBS JSON importer preserves the collection and source fields](https://github.com/obsproject/obs-studio/blob/32.2.2/frontend/importers/studio.cpp)
- [Collection save/load, coordinate modes, and Duplicate UUID regeneration](https://github.com/obsproject/obs-studio/blob/32.2.2/frontend/widgets/OBSBasic_SceneCollections.cpp)
- [Scene-item UUID resolution and paired absolute/relative serialization](https://github.com/obsproject/obs-studio/blob/32.2.2/libobs/obs-scene.c)
- [Bundled websocket protocol at OBS 32.2.2's pinned submodule revision](https://github.com/obsproject/obs-websocket/blob/1ef34bf48110c2a18184e50e41cd0b1a855e2147/docs/generated/protocol.md)
- [Native scene-item requests and bounds validation](https://github.com/obsproject/obs-websocket/blob/1ef34bf48110c2a18184e50e41cd0b1a855e2147/src/requesthandler/RequestHandler_SceneItems.cpp)

## Evidence rules

A passing local unit suite, a JSON parse, a Playwright run or a populated output
folder is insufficient. Require the exact commit's hosted native job to succeed,
inspect its logs and PNG artifacts, and run the independent oracle on both
first-load and reopened observations. Preserve failed-run artifacts for
reproducibility and fix the actual failed stage rather than weakening the gate.
