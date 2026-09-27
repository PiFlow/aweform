# D-052 — V0.5 innate autonomous return-charge-recovery loop

- **id:** D-052
- **lane:** Development / Level-1 Innate Autonomous Viability
- **authorized_base_sha:** `0a273f6e10c9dff155d4ade15e04684d674b60fd`
- **authorization:** issue [#182](https://github.com/PiFlow/aweform/issues/182), including the adopted amendment and `[FIRST-MATE-REVIEW]` Opus 5.5 PASS
- **disposition:** CONTINUING
- **result status:** official frozen Development characterization completed from the pushed executable/protocol freeze

## Question and boundary

D-052 implements the narrow Level-1 energetic locomotor preemption already
permitted by ADR 0018 Decisions E and F. It tests a fixed return trigger,
unchanged D-050 smooth beacon homing and terminal docking, stationary physical
charging, and yield at a fixed recovery condition. This is constitutive,
programmed Level-1 competence, not learned competence.

The arbiter compares only the organism-visible D-045 float32 energy channel
`observation[0]` widened to Python `float`; it does not read evaluator-side
battery state. The fixed founder-selected normalized thresholds are the
float32 encodings `RETURN_THRESHOLD = float(np.float32(0.20)) =
0.20000000298023224` and `RECOVERY_THRESHOLD = float(np.float32(0.80)) =
0.800000011920929`. It enters RETURN for `observation[0] <= RETURN_THRESHOLD`
and yields from CHARGE for `observation[0] >= RECOVERY_THRESHOLD`. At the
specified initial battery `0.20 * D045_BATTERY_CAPACITY_J`, the float32
observation equals the encoded return threshold and preempts the caller's
command on the first decision. One float32 ULP below recovery is
`0.7999999523162842` and does not yield.

NORMAL passes a legal proposed bilateral command through unchanged unless the
return threshold is active. RETURN delegates to the exact
`aweform.d050.D050SmoothController`; it does not copy its homing law. Charging
contact takes priority and enters CHARGE with zero wheels. CHARGE holds zero
wheels below recovery, returns to RETURN if contact is lost, and passes the
proposed command through on the same decision that reaches recovery. Level 1
does not choose elective departure.

The arbiter counts D-050 `TERMINAL_SPIN` decisions using the accepted
`D049_TERMINAL_SPIN_MAX_STEPS = 20`. The twentieth spin command executes. If
charging contact is still absent on the next RETURN decision, the arbiter
latches `TERMINAL_SPIN_EXHAUSTED`, remains in RETURN, and emits `RETURN_HOLD`
zero wheels. Contact still takes priority over an existing exhaustion latch.
The spin counter resets at every entry to RETURN, including contact-loss
reacquisition. D-050 remains unchanged. Invalid beacon output remains
D050_SMOOTH's zero-wheel command and is logged without evaluator rescue.

Every decision records its active mode, command source, pass-through or
preemption status, D-050 mode when delegated, spin count, exhaustion state,
and events. The characterization reports transition and preemption counts
and fraction; time spent in RETURN and CHARGE; energy at return activation,
first charging contact, and recovery/yield; contact loss/reacquisition;
energy-depletion and thermal termination; terminal-spin exhaustion and the
per-case maximum spin count.

Energy fields sample the organism-visible `observation[0]`.
`energy_at_return_activation` and `energy_at_recovery_yield` are the values
observed before the `RETURN_ACTIVATED` and `RECOVERY_YIELD` decisions' steps,
that is, the values those decisions compared against the thresholds.
`energy_at_first_charging_contact` is the value observed after the step that
first acquired physical contact, so it already includes any charge accepted on
that step; `first_charging_contact_transition` is the index of the decision
that produced that step.

## Frozen characterization protocol

The seedless matrix has station centre `(0.50, 0.50)`, radii `(0.15, 0.30,
0.45) m`, position bearings `(15, 105, 195, 285)°`, and source-relative
heading errors `(+0.40, -1.20) rad`, exactly 24 cases. Each fresh unchanged
D-045 environment starts at `0.20 * D045_BATTERY_CAPACITY_J`, with charging
contact false. Its `D045PhysicalConfig` sets only `episode_horizon=25000`;
no physics or charging parameter changes. A fixed legal non-zero wheel command
`(0.10, 0.10) rad` is supplied only as a pass-through fixture. It must be
preempted on the initial decision and pass through unchanged at the first
recovery/yield decision. Each case runs through docking, physical charging to
recovery, yield and one passed-through command, or until genuine environment
termination/truncation. The evaluator may stop after one executed invalid-
beacon hold or one executed terminal-spin-exhaustion hold. No charging
acceleration or result-driven tuning is permitted.

The result artifact is event-based and bounded to at most 64 transition/state
samples per case; it does not retain a full trajectory. It includes sufficient
samples and counts to audit mode/source transitions, pass-through and
preemption, D-050 modes, contacts, events, and outcomes. Artifact-only floats
are canonicalized at serialization using the adopted #180 rule:

```python
float(Decimal(x).quantize(Decimal("1e-12"), rounding=ROUND_HALF_EVEN))
```

This is exact from the binary float, applies only to output, maps `-0.0` to
`0.0`, and rejects non-finite values. It never changes controller or
simulation arithmetic.

The support spans only initial radii 0.15–0.45 m and the two specified
heading errors. It does not represent the whole arena or establish general
robustness. Negative or partial outcomes remain valid Development results
and must not trigger threshold or homing changes. The artifact's
`execution_status` is `COMPLETED` whenever all 24 frozen cases ran to their
stop condition, whatever their outcomes; the per-outcome split is reported in
`outcome_counts`.

## Frozen boundaries and non-goals

D-045 deterministic body physics, energy/thermal/charger bookkeeping, wheel
envelope, geometry, eight-channel observation, zero reward, and empty
organism-facing `info` remain unchanged. D-050 homing/controller behavior
remains unchanged. No Level-2/3 learned/plastic state or evaluator geometry
enters causal control. Historical D-045 through D-050 and EXP records,
artifacts, and semantics are preserved. This work adds no sensor, learner,
reserve equation, adaptive threshold, elective departure, planner, rescue,
teleport, energy injection, or confirmation claim. See issue #182 for the
complete scope, STOP boundaries, and focused validation contract.

## Executable/protocol provenance

The result-free source, focused tests, and protocol record were committed and
pushed before official characterization. The run and its independent
byte-identical regeneration used that exact clean pushed freeze commit:
`9a521f2922febe98a588cb8ee6d29b66352d01a6`. The compact artifact is
`D-052-v05-innate-autonomous-return-charge-recovery.json` (137,739 bytes;
SHA-256 `e8efdc14a95c1990b4c14ff1d2d87fe7b616e84f970724efe616d2f5e67a79db`).
The result-layer commit is the single result-only commit containing this
completed record, artifact, and `development/INDEX.md` row.

## Frozen characterization results

All 24 prescribed cases ran to the complete-loop stop condition: 24
`COMPLETE_LOOP`, with no failed or partial cases. Every case preempted the
non-zero fixture command on its first decision, docked and charged using the
unchanged D-045 substrate, yielded at recovery, and passed the fixture command
through after yield. The characterization covered only the frozen 0.15–0.45 m
initial-radius support and specified headings, not the whole arena.

Across 452,213 total transitions, Level 1 preempted 452,189 (fraction
0.999946927665); 549 transitions were spent in RETURN and 451,640 in CHARGE.
Return activation energy was `0.20000000298` in every case. First charging
contact energy ranged from `0.199282824993` to `0.199871078134`; recovery/yield
energy ranged from `0.800001621246` to `0.800030767918`. No case lost or
reacquired contact, depleted energy, underwent thermal termination, or
exhausted the terminal-spin bound. The maximum terminal-spin count was 19.
The result confirms the quantized thresholds and complete loop on this frozen
support only; it does not establish optimal thresholds, learning, general
robotics robustness, hardware transfer, or a broader viability claim.

The artifact's discrete outcome signature was regenerated independently from
the same freeze and its bytes matched exactly. Its SHA-256 and size are recorded
above. Artifact-only floats use the frozen exact-binary Decimal/12-place,
half-even rule; no causal simulation or controller values were rounded.