# Pymunk contact prototype v3 — validation and one-shot stages

Read `protocol-v3.md` before any measured command. All commands are serial. V1/v2 outputs are immutable.

## Stage 0: software-only checks

These tests never run a case corpus, Stage 1, Stage 2, fresh-process replay, or lifetime. They retain the prior 10-step callback test and add one separately declared fixture-interface logical action at 400 microsteps; neither produces a science artifact.

```sh
uv run --frozen --group pymunk-probe pytest -q experiments/pymunk_contact_prototype/test_contact_prototype.py
uv run --frozen --group pymunk-probe ruff check experiments/pymunk_contact_prototype
MYPYPATH=src uv run --frozen --group dev --group pymunk-probe mypy --strict experiments/pymunk_contact_prototype
uv run --frozen --python 3.14.7 --group dev --group pymunk-probe python -m compileall -q experiments/pymunk_contact_prototype
```

Commit the complete result-free source/protocol/test freeze, verify a clean branch and exact base, then independently inspect CPU, memory and active scientific workloads before Stage 1. Never launch a measured stage from tests or CI.

## Stage 1: single focused falsifier (132,000 engine steps; 3-minute cap)

Only after the result-free freeze and resource report:

```sh
PYMUNK_WHEEL_PATH="$PYMUNK_WHEEL_PATH" nice -n 10 uv run --frozen --python 3.14.7 --group pymunk-probe \
  python -m experiments.pymunk_contact_prototype.run_contact_check_v3 \
  --focused-probe --output experiments/pymunk_contact_prototype/results-v3/focused-probe
```

The exact command refusal, output marker, case selection, thresholds, prediction checks and STOP behavior are in `protocol-v3.md`. Stage 2 is prohibited unless the saved Stage-1 artifact passes every gate, has the exact same executable/protocol SHA and 132,000 actual steps, and the new resource check is safe.

## Stage 2: one full corpus plus one fresh-process replay (1,912,800 engine steps; 15-minute cap)

Run only after a Stage-1 PASS and a separate safe resource recheck:

```sh
PYMUNK_WHEEL_PATH="$PYMUNK_WHEEL_PATH" nice -n 10 uv run --frozen --python 3.14.7 --group pymunk-probe \
  python -m experiments.pymunk_contact_prototype.run_contact_check_v3 \
  --measure --output experiments/pymunk_contact_prototype/results-v3/contact-check
```

The v3 runner independently enforces the Stage-1 prerequisite, exact one-shot path, base/source guard, declared step count, case-by-case wall-clock cap and fresh-process source/replay checks. Any essential failure or cap is recorded and terminal: no rerun, alternate resolution, tuning rescue, or lifetime.

No organism/reference lifetime command is authorized in v3.
