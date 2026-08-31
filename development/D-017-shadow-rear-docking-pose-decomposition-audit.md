# D-017 — Shadow rear-docking pose decomposition audit

- **id:** D-017
- **date:** 2026-08-31
- **authoritative_base_sha:** `c291f171da3098737920d7567f3c5ea01aad30a8`
- **accepted_executable_sha:** `bd778a3d3e767f124a61e8787d8e27124392169d`
- **development_seeds:** `18356, 18357, 18358`
- **horizon:** `1000` transitions per uninterrupted lifetime
- **disposition:** `CONTINUING`

The machine-readable JSON artifact is the numerical source for this record:
[`D-017-shadow-rear-docking-pose-decomposition-audit.json`](D-017-shadow-rear-docking-pose-decomposition-audit.json).

## Provenance and accepted execution

Before implementation, the canonical `validate_exp003_development_seeds`
validator accepted exactly `(18356, 18357, 18358)`. The D-017 exact guard then
accepts only those three seeds after the canonical reservation guard. No formal
reserved seed was used.

The implementation and tests were committed from the verified authoritative
main at `bd778a3d3e767f124a61e8787d8e27124392169d`. The relevant working tree
was clean at execution. The substantive run was executed once with the exact
accepted executable SHA, the three declared seeds, and horizon 1000. Geometry,
tolerance, orientation conditions, and seeds were not changed after observing
the result.

This is development-lane descriptive work. It is not confirmatory evidence and
was not promoted to an `EXP-NNN` claim.

## Scientific question and causal boundary

D-017 asks, at each real autonomous charging-contact entry, how close the
resulting pose is to a plausible rear two-contact conductive docking pose, and
whether incompatibility is decomposable into:

1. approach/translational body-pose incompatibility; and
2. dock-orientation incompatibility.

The run used unchanged `D014Controller`, `D002ThermalStationEnv`, EXP-003
station beacon and circular charging contact, energy/thermal dynamics, action
set, policy RNG semantics, and D-014 post-contact setup. Reward remained exactly
`0.0` and `info` remained `{}` on every transition. The shadow body and dock
were evaluator-only candidate geometry and could not affect observations,
action selection, transitions, charging, energy, thermal state, RNG, or
learning.

## Provenance categories

### PROGRAMMED

- Unchanged `D014Controller` and current D-002/EXP-003 ecology.
- Candidate shadow body constants: length `0.10`, width `0.08`, `+X` forward,
  `+Y` left, rear face `x=-0.05`.
- Candidate rear contacts `(-0.05,+0.025)` and `(-0.05,-0.025)`.
- Front-face midpoint comparator `(+0.05,0.0)`; this is not a proposed
  morphology.
- Station-centred candidate dock contacts at `±0.025*v(phi)`.
- Fixed dock orientation sweep:
  `0, pi/4, pi/2, 3*pi/4, pi, 5*pi/4, 3*pi/2, 7*pi/4`.
- Two-contact tolerance `<= 0.01`, applied to both corresponding contact
  errors.
- Pure evaluator rigid-body transforms and descriptive aggregation.

### ORGANISM-VISIBLE

- Unchanged D-011/D-014 observation only: normalized energy, normalized
  thermal, beacon left/forward/right, and physical `charging_contact`.
- The organism's own executed action is available as ordinary evaluator
  transition history where recorded.

### LEARNED

None. D-017 instantiated no learner, predictor, plastic state, model-guided
behaviour, or counterfactual action-selection path.

### EVALUATOR-ONLY

Actual coordinates and heading; candidate shadow body/contact coordinates;
hypothetical dock orientations; entry-pose decomposition; front comparator;
pair errors; success classifications; aggregates; and visualization overlays.

Current L/F/R is independent of the hypothetical dock-orientation variable.
D-016 showed that L/F/R strongly encodes station-centre-relative body-frame
geometry on visited support. D-017 does not show that Aweform itself computes
the evaluator geometry.

## Entry-event definition and geometry

The primary population contains only transitions satisfying:

```text
charging_contact_before == False
and charging_contact_after == True
```

These bits come from unchanged D-014/D-002 transition telemetry. Ordinary
subsequent `CHARGE`/`WAIT` transitions are not counted again. The artificial
initial post-contact setup at `(0.5,0.5)` for body and station starts in contact
and is excluded from the primary population; it is retained as setup
provenance.

At each entry, D-017 records the post-transition body centre, heading, station
centre, action, radial distance, body-frame `x_rel`/`y_rel`, incidence angle,
ahead/behind/exact-zero classifications, rear/front midpoint errors, and all
fixed-orientation pair metrics. Corresponding contact polarity is never swapped
post hoc.

For the orientation-matched diagnostic, `phi` is exactly the actual entry body
heading. With equal declared contact spacing, both matched pair errors equal the
rear-face positional error up to floating-point arithmetic; focused tests prove
this relationship. This is a hypothetical comparison, not a moving real dock.

## Behaviour and viability preservation

The accepted D-017 run produced 1000 transitions for every seed, with no
termination and horizon truncation in all three lifetimes. An independent
comparison of D-017 and unchanged D-014 summaries matched exactly for all three
seeds at horizon 1000, including transition/termination flags, action counts,
energy/thermal summaries, physical charger exits, reacquisitions, and completed
regulation cycles.

| Seed | MOVE / LEFT / RIGHT / WAIT | Min / final energy | Max / final thermal | Exits | Reacquisitions | Cycles |
|---:|---:|---:|---:|---:|---:|---:|
| 18356 | 555 / 83 / 65 / 297 | 0.144 / 0.854 | 0.340 / 0.180 | 15 | 15 | 15 |
| 18357 | 522 / 96 / 95 / 287 | 0.028 / 0.380 | 0.340 / 0.000 | 15 | 13 | 13 |
| 18358 | 557 / 64 / 77 / 302 | 0.148 / 1.000 | 0.350 / 0.210 | 15 | 15 | 15 |

The pooled audit population contains `44` autonomous contact entries: `43`
station-ahead entries, `1` station-behind entry, and `0` exact-zero entries.
There were `0` rear positional successes, `0` front comparator successes,
`0` orientation-matched two-contact successes, and `0` successes at every
fixed orientation under the declared `0.01` tolerance.

## Continuous results

All values below are pooled entry distributions. The complete per-seed
mean/median/min/max distributions and every raw entry are in the JSON artifact.

| Quantity | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|
| Body-centre entry radius | 0.079133 | 0.080255 | 0.056296 | 0.096857 |
| `x_rel` | 0.067533 | 0.070978 | -0.005861 | 0.090828 |
| `y_rel` | -0.003699 | -0.019464 | -0.096172 | 0.048789 |
| Incidence angle (radians) | -0.060408 | -0.269171 | -1.631661 | 0.676455 |
| Rear positional error | 0.124568 | 0.127492 | 0.104797 | 0.144789 |
| Front midpoint comparator error | 0.044148 | 0.045509 | 0.018868 | 0.111218 |
| Matched-orientation max pair error | 0.124568 | 0.127492 | 0.104797 | 0.144789 |
| Minimum fixed-sweep max pair error | 0.129932 | 0.131661 | 0.108597 | 0.148748 |

Per-seed entry counts were `15` (18356), `14` (18357), and `15` (18358).
The orientation-matched max pair error is the rear positional error, as
expected from the declared equal spacing. The fixed eight-orientation sweep
has a slightly larger minimum max error because it cannot generally match the
continuous entry heading.

### Fixed-orientation pair-error distributions

The table reports pooled `max_pair_error` distributions; success counts were
zero for every orientation.

| Dock orientation | Mean | Median | Min | Max | Successes |
|---:|---:|---:|---:|---:|---:|
| `0` | 0.145736 | 0.148400 | 0.108729 | 0.174337 | 0 |
| `pi/4` | 0.143317 | 0.144240 | 0.115090 | 0.176961 | 0 |
| `pi/2` | 0.146050 | 0.145800 | 0.115621 | 0.172744 | 0 |
| `3*pi/4` | 0.146501 | 0.148143 | 0.119836 | 0.173275 | 0 |
| `pi` | 0.145727 | 0.146740 | 0.116170 | 0.174534 | 0 |
| `5*pi/4` | 0.142500 | 0.142100 | 0.115090 | 0.176298 | 0 |
| `3*pi/2` | 0.141767 | 0.141711 | 0.111103 | 0.167704 | 0 |
| `7*pi/4` | 0.144371 | 0.147026 | 0.108597 | 0.170383 | 0 |

## Interpretation, surprises, and limitations

Direct descriptive observations:

- The rear-face positional error is large relative to the declared `0.01`
  tolerance at every observed entry; orientation matching does not repair it.
- The front midpoint comparator is closer on average, but it also has zero
  tolerance successes and is only a diagnostic comparator. It must not be
  interpreted as a proposed morphology.
- The coarse fixed orientation sweep does not produce a two-contact success at
  any visited entry. The continuous orientation-matched best case is better
  than the coarse sweep but still has zero successes.
- Almost all entries had the station ahead in the current body frame; one
  entry was station-behind. No exact-zero `x_rel` event occurred.

The central decomposition result is that the translational/rear-face mismatch
is already present in the orientation-matched diagnostic. The fixed sweep adds
a smaller discrete orientation component on this support, but does not make
the rear pose compatible. This is a descriptive result on three development
seeds, not a universal statement about all trajectories or docking designs.

Limitations include one deterministic ecology, three seeds, one 1000-transition
horizon, and a point-contact candidate geometry that is not a body-collision or
charger-mechanics model. The fixed sweep is intentionally discrete. One seed
had a horizon-censored regulation episode after its observed entry population;
that null/censoring outcome is retained rather than repaired. No post-hoc
scientific success threshold was introduced.

## What D-017 does not justify

A poor rear-docking compatibility result does not by itself justify reverse
motion. A poor fixed-orientation result does not by itself justify an
orientation sensor. D-017 does not justify proprioception merely because
ordinary robots use it, and it does not justify incoming-current sensing. It
does not justify a new learner, predictor, plastic state, beacon channel,
camera, dock-orientation cue, altered charging semantics, or any other durable
organism boundary.

In particular, this audit does not claim consciousness, subjective experience,
emotion, biological life, or emergent intelligence. A null or negative result
is scientifically valid and is preserved here. On this descriptive audit alone,
I do not believe a new durable boundary is scientifically motivated. Any such
boundary would require an explicit later task and the applicable authorization
and review process.

## Validation and disposition

At the accepted executable candidate:

- `uv run pytest -q`: **725 passed**, 8 existing Matplotlib warnings.
- `uv run ruff check .`: **passed**.
- `uv run mypy src --strict`: **passed**.
- `git diff --check`: **passed**.

Focused tests cover exact ideal alignment, translation and rotation
consistency, midpoint/body-frame formulas, exact sweep and inclusive
tolerance, event filtering, setup exclusion, seed guards, reward/info and
observation boundaries, no shadow RNG influence, exact D-014 summary equality,
and shared visualizer overlay registration. The disposition is
`CONTINUING`; this result is not promoted to confirmatory evidence.
