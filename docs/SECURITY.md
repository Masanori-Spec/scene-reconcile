# Privacy and safety boundary

The product is a standalone client-side HTML application. Native collection files are read into memory and are not uploaded; no backend, analytics, remote fonts or network API is needed. Exports occur only after explicit user review. Clear/Cancel and input replacement invalidate pending reads, previous decisions and export snapshots. Hashes cover the exact input text and exact generated collection bytes.

Collection files can contain private device names, filesystem paths and configuration. Review before sharing the files or receipt. A receipt is not a digital signature or authenticity certificate. Matching UUIDs establish the bounded workflow's identity relation, not proof against a maliciously fabricated export.

Input limits: 10 MiB each, 60 JSON levels, 20 scenes, 200 sources and 1,000 scene items. Duplicate JSON keys, unsafe object keys, duplicate UUIDs/names, invalid references and cycles are rejected. The app never opens referenced media, loads plugins, executes scripts, uses devices or contacts OBS.

Native CI is separate from the product. It uses the official hash-pinned OBS binary on an ephemeral Ubuntu 24.04 runner, isolated configuration, fixture-only sources and authenticated ephemeral WebSocket control. It asserts that capture-device globals, streaming, recording and virtual camera remain off. Browser CI uses Ubuntu 22.04 with the browser sandbox enabled; no host security protections are bypassed. Neither CI job accesses real user configuration.
