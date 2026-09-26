# D-050 — Paired Level-1 homing control comparison

- **id:** D-050
- **status:** completed from frozen executable SHA
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

## Invalidated post-freeze provenance

The original official output from clean executable SHA
`218244d8e2fac7cd31ead1f84d5dc5ac38b628d4` is invalidated by the exact-HEAD
review finding recorded in the authorized correction. Its artifact SHA-256 was
`e59dd06d65903ff721eed1bed16caac05fbd4940679a9f736a6f80cfefa16778` and its
size was `3,383,487` bytes. Successful smooth-arm cases that contacted during
`CURVED_PURSUIT` before `TERMINAL_SPIN` entry incorrectly recorded both energy
components as null.

The first correction freeze `917818335e3024de2cf2ce8b4ed4f0a9172bcda4`
produced an unaccepted artifact with SHA-256
`5c126d2af0ad9b5c417568d3e6d6d2469f5bdf1a5c725c40695c71ccf51606b6` and
size `3,385,354` bytes. It is invalidated because its provenance metadata
carried the old artifact size incorrectly; no measured result from it is
accepted.

The replacement freeze `a7cfbc42f62f649425aefd44ba378148760c5d99` also has an
invalidated command output: the runner was given the non-existent SHA-shaped
value `a7cfbc4b6cbe42e6cc8f8c286e6a48c1c071f8d1`. That output has SHA-256
`c65020cd13bd4117e166881575e5060d0a808ceafc6a6c45f9aef376ce21dc38` and
size `3,385,929` bytes. It is not attributable to a verified executable SHA
and is not accepted.

All 96 pairs were rerun from the final verified freeze below. None of these
invalidated outputs is pooled into the corrected interpretation.

## Official result

The official run was generated from the clean, pushed executable/protocol
freeze:

- **clean_executable_sha:** `ab66eadc21c1542f508a7c078e7ebc4229b92962`
- **artifact:** [`D-050-level1-homing-controller-comparison.json`](D-050-level1-homing-controller-comparison.json)
- **artifact_bytes:** `3386482`
- **artifact_sha256:** `28e352ad57096c5c85de8beae546b48e6041b6b0ad8bed712bcf185efb024fa5`
- **independent regeneration:** byte-identical, same size and SHA-256

All `96` paired cases and both arms completed without termination or boundary
scaling. Arm A had `80/96` `DOCKED_AND_CHARGING` cases and `16/96`
`RETURN_HORIZON_CENSORED` cases. Arm B had `96/96` `DOCKED_AND_CHARGING`
cases. The success/failure cross-tab and all raw per-arm values remain in the
artifact; paired differences are null where a required cost was unavailable
for one arm rather than being censored into a scalar score.

For all `30` successful smooth-arm cases that acquired contact during
`CURVED_PURSUIT` before terminal-spin entry, homing energy is now total energy
from reset to first contact and terminal energy is exactly `0.0`. The paired
homing-energy and terminal-energy summaries therefore each retain `80` eligible
baseline/smooth differences rather than `50`; no controller, matrix, horizon,
or primary success interpretation changed.

The artifact validation records exact 96-case cardinality, identical paired
initial physical states, shared D-049 reconstruction and terminal constants,
observation-only controller inputs, fresh-environment order invariance, Level-1
authority on every transition, reward exactly `0.0`, and organism-facing
`info == {}`. The result is descriptive on the frozen idealized V0.5 support;
it does not establish general physical-robot superiority or robustness.

## What changed in understanding

**surprised_by:** On this frozen support, the smooth law reached charging in
all 96 cases while the unchanged stop-turn-straight arm was horizon-censored
in 16 cases. This is a descriptive paired observation, not a reason to alter
the frozen controller or to select a future return-margin rule here.

**disposition:** `CONTINUING`. The measured component-wise costs are preserved
for later separately authorized interpretation; D-050 does not implement the
return trigger/reserve stage or the planned visualizer.
