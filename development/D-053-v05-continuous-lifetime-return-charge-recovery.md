# D-053 — V0.5 continuous-lifetime return, charge, and recovery

**Status:** Protocol frozen at `934588d`; official five-seed characterization executed and results recorded. **Disposition:** CONTINUING.

## Question and classification

Across five seeded continuous lifetimes, does the unchanged D-052 Level-1 mechanism repeatedly interrupt unrelated stochastic roaming, return to physical charging contact, recharge, yield control, and permit roaming to resume without evaluator assistance? This is descriptive Development characterization, not confirmatory evidence. D-053 reports engineered innate competence only, not learned competence.

## Frozen protocol

- Authorized base: `4b7a8cf3a62cab41934d644af45e92ab3957daab`.
- Seeds: `22053, 22054, 22055, 22056, 22057`, guarded by the canonical formal-reservation validator and an exact-block D-053 guard.
- Each lifetime starts docked at body/station `(0.50, 0.50)`, heading `0`, energy `0.80 × 5,328 J`, ambient temperature, false charger latch, zero prior wheel delta, fresh D052Controller in NORMAL.
- Horizon 140,000 decisions, unchanged D-045 physics otherwise. Stop only at D-045 termination or horizon truncation; no rescue, teleport, injection, early stop, or accelerated charging.
- Every decision advances the exact EXP-001 `StochasticPersistentExplorer` constructed from `policy_rng_from_seed(seed)`, including D-052-preempted decisions. It receives fixed placeholder `ExternalObservation(0,0,0)` and contributes only evaluator-side wheel-command test vectors. `MOVE_FORWARD → (+M,+M)`, `TURN_LEFT → (-M,+M)`, `TURN_RIGHT → (+M,-M)`, `M = D045_MAX_WHEEL_DELTA_RAD`. No energy, observation, mode, pose, contact, or outcome enters the fixture.
- D052Controller alone arbitrates and delegates unchanged to D-050. D-045 reward remains `0.0`; reset/step `info` remains `{}`. No Level-2/3 learned or plastic state is used.
- Artifact floats are rounded only during serialization using `Decimal(x).quantize(Decimal("1e-12"), ROUND_HALF_EVEN)`, normalize negative zero, and reject non-finite values.
- Display sampling retains the first and last transitions; every transition from 50 before each `RETURN_ACTIVATED` through the earliest of 50 after that episode's `CHARGING_CONTACT`, 50 after the episode's first `RETURN_HOLD`, `TERMINAL_SPIN_EXHAUSTED`, or `INVALID_BEACON`, `RETURN_ACTIVATED`+2000, or the episode's end (a long no-contact pursuit such as a wall/corner wedge remains ordinary RETURN and is not causally detected; its remainder is simply strided); ±50 transitions around every `RECOVERY_YIELD`, incidental NORMAL pass-through contact acquisition/loss, `CHARGING_CONTACT`, `CHARGING_CONTACT_LOST`/`REACQUIRED`, `TERMINAL_SPIN_EXHAUSTED`, the first `INVALID_BEACON` of each consecutive run, and termination/truncation; and every 100th transition elsewhere, including the remainder of any hold. It does not affect execution or JSON.
- Event samples record D-052's executed `wheel_command` and, separately, the fixture's `proposed_wheel_command` and `symbolic_proposal`. Sample rows are RESET plus every decision with events or a D-052 mode, command-source, D-050 sub-mode, or contact change. Rows repeating the immediately preceding decision's events, mode, source, and D-050 sub-mode during an `INVALID_BEACON` or `RETURN_HOLD` hold are collapsed. At most 256 are kept per seed: RESET and the final row always; then cycle-defining/termination/first-invalid-beacon rows, other event rows, and event-free state changes (including D-050 sub-mode changes) fill the cap in that priority order, evenly spaced within any overflowing tier. `event_row_count`, `retained_sample_count`, and `samples_truncated` are recorded.

## Analytic budget stated before runs

Unobstructed full-effort roaming at a 1.15 W load takes approximately 27,800 transitions to move from 80% to 20%; bulk recharge from 20% to 80% takes approximately 18,800. Wall-boundary scaling can reduce effort and lengthen roaming. A full cycle is therefore approximately 46,700 transitions or more; roughly two yields per lifetime are expected, with a possible third cycle truncated near the horizon. This is not a success criterion. No pilot or tuning is permitted.

## Record and interpretation plan

The compact JSON records per-seed mode/source/preemption counts, return and contact events, incidental NORMAL contact acquisitions separately from D-052 acquisitions, energy minima, terminal-spin/exhaustion data, evaluator-only return-start geometry, cycle tables, bounded event samples, and a discrete outcome signature. The HTML replay uses the canonical neutral visualizer, contains all five seeds, and is fully offline. Actual cycles and any negative/partial outcomes will be preserved without tuning.

`surprised_by`: Seed 22053 activated RETURN from evaluator station distance 0.547 m and remained in D-050 `CURVED_PURSUIT` through the 140,000-transition horizon, with no contact or hold/exhaustion/invalid-beacon event. It truncated in RETURN at 0.006316 observed energy (33.652 J), despite four other seeds docking and yielding. This is an observed wall/corner-wedge failure outside the successful examples, not a reason to tune; a similar wedge had already appeared before the freeze in a test-only 22056 variant (see provenance). The frozen 2,000-transition RETURN display cap kept the replay self-contained, though the actual five-seed HTML was 4,673,826 bytes, above the pre-run 1–3 MB estimate. NORMAL roaming before RETURN took 69,415–73,934 transitions, far above the pre-run estimate of about 27,800; boundary scaling affected 84,802–119,008 transitions per seed and reduced actual effort. Consequently, each lifetime completed at most one recovery yield rather than the roughly two estimated (22053 yielded none). This is a descriptive observation, not a tuning target.

`disposition`: CONTINUING — preserve the partial and negative outcomes; no tuning or successor is authorized.

## Executable and artifact provenance

The result-free executable/protocol freeze is pushed at `934588d55f38dc1cb3945e14d4225654dd3376f3`. Both official generation and the independent byte-identical regeneration used that exact clean freeze SHA. The official 80%-docked, 140,000-transition protocol was first run from that freeze. Pre-freeze test-only variants did run on official-block seeds: the frozen test suite's test-only `low_energy_life` fixture continues to run seed 22053 at 19% initial energy for 20,000 transitions and was left unchanged to preserve the freeze; a round-2 test-phase check ran seed 22056 at 22% for 25,000 transitions, where a RETURN wall/corner wedge was observed and motivated the frozen 2,000-transition display cap. No mechanism, fixture, seed, official initial state or horizon, JSON artifact, or other causal/protocol parameter was selected or changed from either variant. The protocol JSON is 45,396 bytes, SHA-256 `1f195c77829857ef0e2d664d66f746198d588d382ff404c837508dbeacd924f0`. The self-contained offline replay is 4,673,826 bytes, SHA-256 `428cceb14bc78b5914cd01bf0b3ff80e219a33510246cd16de67f019496e4c1a`. Both independent regenerations matched byte-for-byte. The JSON contains no full trajectory; display downsampling affected only the replay.

## Official descriptive results

All five lifetimes ran the full 140,000 transitions and truncated at the horizon. Each had one RETURN activation. Seeds 22054–22057 each acquired D-045 dual contact on RETURN, charged to the D-052 recovery threshold, yielded once, and resumed PASS_THROUGH roaming. Seed 22053 did not acquire contact and ended in RETURN; its result is retained unchanged. There were four completed yields and four D-052 dock acquisitions. No episode exhausted the terminal-spin bound, no `INVALID_BEACON` occurred, and there was no D-045 termination. Two incidental NORMAL/PASS_THROUGH contact acquisitions occurred on seed 22055; the initially docked state was not counted as an acquisition.

| Seed | NORMAL roam before RETURN | RETURN | CHARGE | Outcome | RETURN energy | First-contact energy | Yield energy | Incidental NORMAL contacts | Min observed energy | Max terminal spin / exhaustion |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| 22053 | 71,215 | 68,785 | 0 | TRUNCATED_IN_RETURN; no contact | 0.199986383319 | — | — | 0 | 0.006316144485 | 0 / no |
| 22054 | 69,415 | 38 | 18,829 | YIELDED, then horizon truncation in NORMAL | 0.199985563755 | 0.199252948165 | 0.800028085709 | 0 | 0.199239805341 | 11 / no |
| 22055 | 72,227 | 32 | 18,824 | YIELDED, then horizon truncation in NORMAL | 0.199999108911 | 0.199384406209 | 0.800000011921 | 2 | 0.199371263385 | 7 / no |
| 22056 | 71,649 | 29 | 18,823 | YIELDED, then horizon truncation in NORMAL | 0.199986577034 | 0.199442863464 | 0.800026595592 | 0 | 0.199429735541 | 9 / no |
| 22057 | 73,934 | 27 | 18,821 | YIELDED, then horizon truncation in NORMAL | 0.199999555945 | 0.199504509568 | 0.800024390221 | 0 | 0.199482247233 | 0 / no |

Across 700,000 transitions, Level 1 preempted 144,208 decisions (20.6011%). Boundary scaling (`boundary_scale < 1`) occurred on 119,008, 84,802, 86,240, 85,830, and 87,625 transitions for seeds 22053–22057 respectively. Minimum evaluator battery in joules was 33.652417741524, 1,061.549722025034, 1,062.250077008015, 1,062.561599145109, and 1,062.841390397019 respectively. Reward was exactly 0.0 throughout and organism-facing `info` remained `{}`. All runs were deterministic on regeneration.

These five fixed-state Development lifetimes describe only the unchanged constitutive Level-1 floor under an energy-blind evaluator-side proposal stream. Four yields do not establish a minimum-cycle criterion, learned self-preservation, optimal thresholds, general robustness, hardware transfer, or confirmatory evidence. The single no-contact truncated RETURN is a valid negative/partial result and is not rescued or retuned.
