# SceneReconcile · work in progress

A bounded local-first prototype for reconciling parallel edits to OBS scene collections. **This is a release-candidate checkpoint. The first native fixture/Import/save/reopen gate passed; product browser downloads and final native merged-output acceptance remain pending.**

The first hosted gate uses the official SHA-256-pinned OBS Studio 32.2.2 Ubuntu 24.04 package. It creates six native sources, imports prepared copies through the real OBS UI, edits the branches through the official OBS WebSocket API, then saves and reopens them. It never starts streaming, recording, virtual camera, webcam or microphone capture. Each run uses disposable configuration and authenticated ephemeral control.

The [first gate passed](https://github.com/Masanori-Spec/scene-reconcile/actions/runs/37231268860), preserving all baseline UUIDs across native imports and reopened branches. Final acceptance still requires actual application browser downloads, independent Python semantic checks against a pre-authored manifest, fresh native Import and save/reopen, runtime inspection of every scene, and human visual review of native previews.

## Early native gate

Hosted GitHub Actions Ubuntu 24.04 only:

```sh
bash native/install-obs.sh
dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' bash -c 'openbox >/tmp/scene-reconcile-openbox.log 2>&1 & /usr/bin/python3 native/obs_gate.py prepare --out evidence/native-prepare --fixtures evidence/native-fixtures-generated'
```

The installer and controller refuse local execution. No heavyweight consumer is installed in the development workspace. Credentials are generated for the disposable runner and are not committed or included in evidence. The pipeline uses read-only GitHub permissions.

## Intended workflow

Prepare a native export into baseline, operator and incoming copies with distinct collection names and preserved source UUIDs. Import each copy into the same OBS version/platform; do not use Duplicate. After editing, load the three exports and reconcile source settings separately from per-scene transforms, visibility, lock and membership/order. Resolve competing edits explicitly and download a new native collection with a hash-bound decision receipt.

See [scope](docs/SCOPE.md), [prior art](docs/PRIOR_ART.md), and the pre-authored [semantic manifest](oracle/expected.json). This is a configuration-collaboration prototype, with no universal compatibility or patent-novelty claim.


## Local development and checks

```sh
npm ci --ignore-scripts
npm run check
npm run serve
```

Open the reported localhost address, or open dist/index.html directly. The distribution is standalone and uses no network service. `npm run check` runs product/state tests, independent oracle tests, lightweight native-controller tests, genuine native fixture checks, sample output generation and a deterministic build. Native/browser execution is hosted separately. The manually dispatchable first-gate workflow can regenerate native fixtures; normal CI uses the committed verified fixtures so the exact shipped build is tested.

The app's output validation is structural, not a universal runtime guarantee. Existing capture/media preservation is covered by synthetic cases; the native consumer fixture uses only colors, FreeType text and nested scenes. Review all final OBS scenes before production use.
