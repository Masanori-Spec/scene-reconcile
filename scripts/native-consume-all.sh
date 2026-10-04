#!/usr/bin/env bash
set -euo pipefail
openbox > /tmp/scene-reconcile-openbox-consumer.log 2>&1 &
for role in baseline operator incoming; do
  /usr/bin/python3 native/obs_gate.py prepared \
    --input "test-results/browser/prepared-$role.json" \
    --original tests/fixtures/native/baseline.json \
    --reference-observation tests/fixtures/native/baseline-observation.json \
    --out "evidence/native-consumer/prepared-$role"
done
for variant in merged conflict-resolved; do
  incoming=test-results/browser/incoming-input.json
  if [[ "$variant" == conflict-resolved ]]; then incoming=test-results/browser/conflict-input.json; fi
  /usr/bin/python3 native/obs_gate.py consume \
    --input "test-results/browser/$variant.json" \
    --out "evidence/native-consumer/$variant"
  for phase in first-load reopened; do
    /usr/bin/python3 oracle/runtime_check.py \
      "evidence/native-consumer/$variant/$phase.json" \
      test-results/browser/baseline-input.json "$incoming" \
      --report "evidence/native-consumer/$variant/oracle-$phase.json"
  done
  for saved in native-saved-first native-saved; do
    /usr/bin/python3 oracle/check.py \
      "evidence/native-consumer/$variant/$saved.json" \
      test-results/browser/baseline-input.json test-results/browser/operator-input.json "$incoming" \
      --report "evidence/native-consumer/$variant/oracle-$saved.json"
  done

done
