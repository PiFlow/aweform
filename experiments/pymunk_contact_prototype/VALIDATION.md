# Pymunk contact prototype — v2 validation and execution boundary

## Historical v1 record

The original v1 fixed-command experiment is complete and failed essential B. Its executable `bc8248c658397afd56dec307e4d344b16a86abb8`, protocol, `results/results.json`, receipt, and interpretations remain historical. **Do not rerun or replace v1 outputs.** The previous v1 measured CLI is retired; it now raises before constructing or stepping a world. V1 same-process replay labels are not fresh-process evidence.

## Runtime

The optional experimental group remains unchanged. Use Python 3.14.7, Pymunk 7.2.0, and the pinned native wheel:

```sh
uv sync --frozen --python 3.14.7 --group dev --group pymunk-probe
export PYMUNK_WHEEL_PATH=/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl
```

The corrected runner verifies the exact wheel SHA from the inherited #220 calibration and refuses an incorrect runtime/base/branch/dirty source. It writes only to the new path `experiments/pymunk_contact_prototype/results-v2/contact-check/`; v1 `results/` and bounded diagnosis artifacts are never overwritten.

## Software-only validation

These checks never run the frozen 255-case-per-resolution acceptance corpus, fresh-process replay worker, or either lifetime. The unit tests exercise parsing, pure geometry, one isolated fixture action/contact-reset interface, and early output/gate refusal behavior; that one logical action is not the measurement corpus and produces no science artifact.

```sh
uv run --frozen --group pymunk-probe pytest -q experiments/pymunk_contact_prototype/test_contact_prototype.py
uv run --frozen --group pymunk-probe ruff check experiments/pymunk_contact_prototype
MYPYPATH=src uv run --frozen --group dev --group pymunk-probe mypy --strict experiments/pymunk_contact_prototype
uv run --frozen --python 3.14.7 --group dev --group pymunk-probe python -m compileall -q experiments/pymunk_contact_prototype
```

Routine tests/CI/no-mistakes validation must not call `run_suite`, `measure`, the fresh-process replay worker, `run_once`, or `run_reference_once`.

## One bounded corrected contact check — explicit measurement only

Before this command, commit the complete corrected source, `protocol-v2.md`, tests and validation plan as one clean result-free freeze. Independently check CPU/memory/process availability, make sure no competing required scientific workload is active, and report the frozen case count/serial runtime budget. Do not run in parallel. The command refuses an existing output path before constructing a Pymunk Space; any started output path is one-shot. It runs the corrected 10/20 suites serially, then one identical replay in a separate fresh process. All failures remain in the artifact. Any essential B failure means STOP, preserve the new result, and do not run a lifetime or tune/repeat.

```sh
PYMUNK_WHEEL_PATH="$PYMUNK_WHEEL_PATH" uv run --frozen --python 3.14.7 --group pymunk-probe \
  python -m experiments.pymunk_contact_prototype.run_corrected_contact_check \
  --measure --output experiments/pymunk_contact_prototype/results-v2/contact-check
```

## Conditional one-time organism/reference lifetime

Only if the committed v2 `results.json` has `essential_B_pass: true`, the exact measured executable SHA still matches the clean frozen HEAD, and an independent resource review authorizes the declared one-time budget, run the previously unexecuted unchanged Level-1 lifetime and prescribed D-058 reference once. The wrapper preserves the frozen v1 seed/state/horizon and the lifetime room has 3 m walls/dock and zero interior obstacles. The output marker prevents any second attempt; if B fails, do not invoke it.

```sh
uv run --frozen --group dev --group pymunk-probe \
  python -m experiments.pymunk_contact_prototype.run_lifetime_once \
  --run-organism-once \
  --results experiments/pymunk_contact_prototype/results-v2/contact-check \
  --output experiments/pymunk_contact_prototype/results-v2/lifetime
```

No routine validation command executes the contact acceptance check, its fresh-process replay, or the single lifetime.
