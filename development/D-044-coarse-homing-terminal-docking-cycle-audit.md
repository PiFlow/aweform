# D-044 — Coarse homing versus terminal docking and cycle-order attribution audit

- **id:** D-044
- **issue:** [#153](https://github.com/PiFlow/aweform/issues/153)
- **lane:** Development / evaluator-only diagnostic
- **authorized_base_sha:** `26ef630b23af01028971cadbddbd38e79d562610`
- **implementation_probe_sha:** `a1538d9455621fac456b30a974e2e5fe497707b4`
- **development_seeds:** `19045..19064` (the exact accepted D-043 support)
- **horizon:** `140,000` transitions per uninterrupted lifetime unless canonical termination
- **disposition:** `CONTINUING`

The compact machine-readable artifact is
[`D-044-coarse-homing-terminal-docking-cycle-audit.json`](D-044-coarse-homing-terminal-docking-cycle-audit.json).
It is a descriptive Development artifact, not confirmatory evidence.

## Frozen protocol and boundary

D-044 replayed the accepted D-043 lifetime exactly: D-042 front dual-contact
geometry, 5° turns, 0.1 s action timing, canonical 0.05-world-unit
`MOVE_FORWARD`, four actions, six visible channels, station-centred L/F/R
beacon, unchanged D-026 delegation/RNG, D-030 arbitration, D-027 executed-action
updates, energy/thermal equations, reward `0.0`, and organism-facing `info == {}`.
No terminal-docking state, variable-distance causal action, new sensor, learner
change, or controller change was added.

The D-044 implementation compared every per-seed replay with the independent
D-043 runner on canonical identity fields: termination/truncation, reason,
action/mode counts, contacts, SEEK episode outcomes, recharge/departure/cycle
events, energy/thermal summaries, and the reconstructible SEEK episode fields.
All 20/20 identities matched. The accepted D-043 trace sink was also used as an
evaluator-only comparator: D-044's streaming completed-transition digest,
executed-action update digest, and final D-027 weight digest all matched a
fresh D-043 trace replay on all 20 seeds (20/20 for each provenance field).
The trace was not retained in the artifact.

## Descriptive results

- The support contained 31 SEEK episodes across 20 lifetimes; 11 lifetimes had
  both a first and second episode, and all episode ordinals are retained in the
  artifact.
- In the matched first-vs-second cohort, first episodes reacquired on 11/11;
  second episodes reacquired on 2/11 and terminated unresolved on 9/11.
  Mean entry station distance was comparable (0.6879 first vs 0.6815 second),
  while mean minimum station distance was also comparable (0.00463 vs
  0.00385). Mean minimum `max_pair_error` was lower for first episodes (0.00721)
  than second episodes (0.01424). This supports a descriptive coarse-homing /
  terminal-pose mismatch and records cycle-order geometry as insufficient by
  itself to explain the later failure; a later learner/controller-state audit
  would be needed, but is not part of D-044.
- The D-016 evaluator-only inverse used 675,372 real SEEK states. Absolute
  reconstruction error means were `9.92e-8` for `x_rel`, `2.34e-8` for `y_rel`,
  and `5.85e-8` for radial distance; maxima were below `8.9e-7`. This supports
  useful station-relative distance information being latent in the existing
  float32 beacon, without claiming that Aweform currently computes it.
- The evaluator-only forward branch had 222,228 visited false-contact SEEK
  `MOVE_FORWARD` states for each candidate. Candidate dual-contact results were
  9/222,228 for `0.05`, 4/222,228 for `0.01`, and 0/222,228 for `0.005`.
  Mean station-distance changes were `-6.66e-5`, `-4.67e-4`, and `-2.62e-4`,
  respectively; mean `max_pair_error` changes were `+0.00606`, `+0.000780`, and
  `+0.000363`. The shorter candidates therefore show a mixed local geometry
  signal, not a robust docking-compatible result; none authorizes a new action.
- Delegated-action attribution had 224,935 matched one-step branches per label.
  Mean `max_pair_error` change was `+0.00628` for the actual delegated action,
  `-0.00313` for the same-state D-030 learned alternative, and `-0.00461` for
  the historical greedy action. Mean station-distance changes were `+0.000600`,
  `-0.000291`, and `-0.00223`, respectively. This is a descriptive local-cost
  signal against the delegated action on visited support, not a sequential
  de-trap-disabled treatment.

These are descriptive observations on reused Development seeds. They do not
establish a universal threshold, a causal mechanism beyond the isolated
one-step branches, or an Evidence-lane claim.

## Isolation and artifact provenance

- D-016 reconstruction was computed from current L/F/R only and never entered
  action selection, learning, reward, or `info`.
- D-043 replay identity passed for canonical fields, completed-transition
  trajectory digest, executed-action update digest, final learner-weight digest,
  and transition count on all 20/20 seeds.
- Kinematic forward branches did not step the real environment and changed no
  energy, thermal, learner, controller, or RNG state.
- Delegated alternatives used read-only D-030 predictor queries and cloned
  canonical one-step environment branches. Across the support there were zero
  branch-order mismatches; source environment/controller/learner/RNG checks and
  predictor read-only checks all passed.
- The real trajectory recorded zero violations of the canonical 0.05
  `MOVE_FORWARD` distance. No formal reserved seeds were executed.
- Corrected executable/protocol SHA: `a1538d9455621fac456b30a974e2e5fe497707b4`.
- Artifact size: `1,770,916` bytes.
- Artifact SHA-256:
  `cc8d7dba5284626688d75632a92f28624557c79274f3c75d3e6ec54bb44aabe6`.
- Focused D-043/D-044 tests: `13 passed`.
- Full repository pytest: `1023 passed, 7 warnings`.
- Ruff: passed; strict mypy: passed for all 74 source files; compile/import and
  `git diff --check`: passed.
- Independent regeneration from the same executable SHA and command was
  byte-identical (`cmp` pass), with the same hash and `1,770,916` bytes.
- Regeneration command:
  `uv run python -m aweform.d044 --output development/D-044-coarse-homing-terminal-docking-cycle-audit.json --executed-commit-sha a1538d9455621fac456b30a974e2e5fe497707b4`

## Superseded validation provenance

The prior validation was invalidated by the Sol correction. Its executable
SHA was `743af5649767885f9dc60f63ad3843771349eddb`; its record-only PR HEAD
was `43f745700049fdb0b1f55400f97f122af7eb4012`; and its artifact was
`1,758,965` bytes with SHA-256
`c398ee4963910be0f7d8c8d66b1884b4d6c67f820904c8746ca384c2ba5df07e`.
That output did not compare the reconstructible D-043 transition/update/final
learner provenance, and its focused isolation test stopped before SEEK. It is
preserved here only as superseded provenance and is not pooled with the
corrected result.

No result authorizes D-045 or any organism-facing change. The recorded founder
preference for a future variable-distance action remains non-authorizing.
