# Lifetime v3 — software-only validation and gated command

Read `protocol-lifetime-v3.md` before operating this path. The protocol and source are prospective until committed at one result-free SHA. Routine validation may not launch either lifetime.

## Software-only checks

```sh
uv run --frozen --group pymunk-probe ruff check experiments/pymunk_contact_prototype
MYPYPATH=src uv run --frozen --group dev --group pymunk-probe mypy --strict experiments/pymunk_contact_prototype
uv run --frozen --python 3.14.7 --group dev --group pymunk-probe python -m compileall -q experiments/pymunk_contact_prototype
MYPYPATH=src uv run --frozen --group dev --group pymunk-probe pytest -q experiments/pymunk_contact_prototype/test_contact_prototype.py
```

These verify the adapter reset/observation boundary, pure v3-result/provenance gates, exact transition/charging checks, counts, charging-interval reducer, approval binding, and existing one-shot output refusal. They do not call `run_once`, `run_reference_once`, `run_pair_once`, `PymunkPhysiologyAdapter.step`, `D058Env.step`, or the lifetime measurement CLI. The existing Pymunk fixture callback test and declared fixture-interface test remain fixed-command software checks; they are not organism/reference transitions. The adapter test calls reset only and asserts zero Pymunk engine steps.

After source/protocol/tests pass, commit the result-free freeze. Confirm clean committed HEAD, exact base, unchanged V3/B files, B artifact hashes, pinned runtime and absent `results-v3/lifetime` path. A read-only preflight is:

```sh
PYMUNK_WHEEL_PATH="$PYMUNK_WHEEL_PATH" uv run --frozen --python 3.14.7 --group pymunk-probe \
  python -m experiments.pymunk_contact_prototype.run_lifetime_v3 \
  --preflight --output experiments/pymunk_contact_prototype/results-v3/lifetime
```

`--preflight` verifies saved V3 PASS provenance and hashes, exact V3/candidate Git-blob identity for the measured ContactWorld/controller inputs, the runtime pin, output absence, disk space, and live memory/CPU/load snapshot. It lists exact source/protocol/output paths and planned counts, and does so without constructing a Pymunk world or D-058 environment, creating output files, or taking a transition. Its JSON is part of the supervisor preflight. **Do not execute a lifetime until the supervisor accepts the exact frozen HEAD and lifetime protocol SHA.**

## Only after supervisor acceptance

Repeat the read-only preflight and live CPU/memory/disk/workload check. If unchanged and safe, use one serial reduced-priority invocation bound to the acceptance receipt:

```sh
PYMUNK_WHEEL_PATH="$PYMUNK_WHEEL_PATH" nice -n 10 uv run --frozen --python 3.14.7 --group pymunk-probe \
  python -m experiments.pymunk_contact_prototype.run_lifetime_v3 \
  --run-once \
  --approval-head "$APPROVED_CANDIDATE_HEAD" \
  --approval-protocol-sha256 "$APPROVED_LIFETIME_PROTOCOL_SHA256" \
  --approval-receipt-sha256 "$SUPERVISOR_ACCEPTANCE_RECEIPT_SHA256" \
  --output experiments/pymunk_contact_prototype/results-v3/lifetime
```

Never run this command from pytest, CI, a generic validation script, a replay, or a background duplicate worker. The runtime refuses a mismatched approval binding, dirty or altered candidate, mismatched V3 result, unexpected output path, or existing one-shot output before constructing the organism or stepping. It runs at most one Pymunk lifetime followed by its single D-058 reference, under the combined 10,800-second monotonic hard cap. A partial/failed output is terminal and must not be resumed or reused.
