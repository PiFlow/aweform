# D-050 — Paired Level-1 homing control comparison

- **id:** D-050
- **status:** frozen protocol; result pending
- **lane:** Development / Level-1 Innate Autonomous Viability controller comparison
- **authorized_base_sha:** `75bca69261b9a91095ca0eb6bdb0c7485c626269`
- **disposition:** CONTINUING

## Question and boundary

D-050 compares the accepted D-049 stop-turn-straight controller with one
deterministic smooth curved-pursuit controller on the unchanged D-045 V0.5
substrate. It is a component-wise descriptive Development comparison. It does
not implement or fit a return trigger, reserve equation, safety factor,
recovery threshold, learning mechanism, new sensor, planner, robustness
condition, or visualizer.

Arm A delegates directly to the merged `aweform.d049.D049Controller` without
changing its source or constants. Arm B uses the imported D-049 float32 L/F/R
reconstruction and, before terminal mode, applies exactly:

```text
u_raw = clamp(beta*b/(2*r), +/-delta_max)
v_distance = min(D/r, delta_max)
forward_gate = max(0, 1 - abs(beta)/(pi/2))
v_raw = v_distance*forward_gate
left_raw = v_raw-u_raw
right_raw = v_raw+u_raw
```

The pair is proportionally scaled only when either wheel exceeds the existing
D-045 command envelope. Both arms use the D-049 `1e-6 m` reconstructed-centre
tolerance, fixed positive maximum in-place spin, 20-step terminal bound,
contact-first zero, and stationary charging verification.

## Frozen protocol

- Station centre: `(0.50, 0.50)`.
- Radii: `0.15`, `0.30`, `0.45` m.
- Position bearings: `22.5 + 45*k` degrees for `k=0..7`.
- Source-relative initial bearing errors: `+0.31`, `+1.29`, `-1.17`, and
  `pi - 0.37` rad.
- Exactly `3 * 8 * 4 = 96` paired seedless initial states.
- Per-arm horizon: `256` transitions, frozen before official execution.
- Each pair starts two fresh D-045 environments from identical explicit
  physical state and executes without cross-arm communication.
- Organism causal inputs remain the D-049 observation channels only: L/F/R
  beacon and charging contact; evaluator pose, heading, station geometry,
  true distance/bearing, contact geometry, outcomes, labels, and metrics stay
  post hoc.

The artifact retains raw per-arm success/failure, energy to first contact,
homing energy, terminal energy, transition counts, path length, cumulative
absolute heading change, normalized wheel effort, terminal-spin burden,
boundary interaction counts/scaling, termination/truncation, failure state,
and compact reset/per-transition `x/y/heading/mode/contact/battery` traces.
It also retains raw paired values and `smooth - baseline` differences with
mean, median, minimum, maximum, and negative/zero/positive counts. A missing
cost for a failed arm remains missing rather than being censored into a score.

## Provenance and execution discipline

The result-free executable/protocol freeze is the exact commit containing
`src/aweform/d050.py`, `tests/test_d050.py`, and this result-free record. The
official artifact must be generated only from that pushed clean executable
SHA with the CLI's explicit `--executed-commit-sha` value. The completed
record, artifact, and one index row are the only permitted result-layer
changes. Independent regeneration from the same executable SHA must be
byte-identical.

This is a Development diagnostic, not confirmatory evidence. Results may
describe only measured behaviour on this deterministic idealized V0.5 support;
they do not establish hardware performance, noise/slip robustness, or general
controller superiority. Negative and failed cases remain in the artifact.

## Validation contract

Focused checks cover exact matrix cardinality, D-049 delegation, curved-law
sign/unit/gating/scaling semantics, shared terminal behaviour, identical pair
initial states, branch-order independence, reward `0.0`, organism-facing
`info == {}`, Level-1 authority, deterministic execution, compact traces, and
byte-identical artifact regeneration. The repository-wide checks required by
issue #176 remain `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src
--strict`, compile/import checks, `git diff --check`, and exact-current-HEAD
GitHub checks.
