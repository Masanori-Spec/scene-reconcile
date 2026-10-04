# SceneReconcile · work in progress

A bounded local-first prototype for reconciling parallel edits to OBS scene collections. **This early checkpoint is not a completed product and native compatibility has not yet been verified.**

The first hosted gate uses the official SHA-256-pinned OBS Studio 32.2.2 Ubuntu 24.04 package. It creates six native sources, imports prepared copies through the real OBS UI, edits the branches through the official OBS WebSocket API, then saves and reopens them. It never starts streaming, recording, virtual camera, webcam or microphone capture. Each run uses disposable configuration and authenticated ephemeral control.

The first gate must pass before native compatibility can be claimed. Subsequent acceptance requires actual application browser downloads, independent Python semantic checks against a pre-authored manifest, fresh native Import and save/reopen, runtime inspection of every scene, and human visual review of native previews.

## Early native gate

Hosted GitHub Actions Ubuntu 24.04 only:

```sh
bash native/install-obs.sh
dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' bash -c 'openbox >/tmp/scene-reconcile-openbox.log 2>&1 & /usr/bin/python3 native/obs_gate.py prepare --out evidence/native-prepare --fixtures tests/fixtures/native'
```

The installer and controller refuse local execution. No heavyweight consumer is installed in the development workspace. Credentials are generated for the disposable runner and are not committed or included in evidence. The pipeline uses read-only GitHub permissions.

## Intended workflow

Prepare a native export into baseline, operator and incoming copies with distinct collection names and preserved source UUIDs. Import each copy into the same OBS version/platform; do not use Duplicate. After editing, load the three exports and reconcile source settings separately from per-scene transforms, visibility, lock and membership/order. Resolve competing edits explicitly and download a new native collection with a hash-bound decision receipt.

See [scope](docs/SCOPE.md), [prior art](docs/PRIOR_ART.md), and the pre-authored [semantic manifest](oracle/expected.json). This is a configuration-collaboration prototype, with no universal compatibility or patent-novelty claim.
