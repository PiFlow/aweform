# D-056 — V0.5 multi-cycle stall-turn lifetime characterization

## Frozen protocol (result-free)

- **id:** D-056
- **lane:** Ordinary in-boundary Development; prospective, descriptive, and non-confirmatory.
- **authorized base:** `1a9dee3321842230b5f5aa71423917ec79419918`
- **status:** executable/protocol freeze; official execution pending.
- **disposition:** CONTINUING
- **predecessors:** D-053, D-054, D-055.

### Question and rationale

Over continuous 300,000-transition lifetimes (up to three roam→return→charge→yield cycles), does the unchanged D-055 stall-turn candidate sustain repeated autonomous return, docking, recharge, and yield on never-executed legal Development seeds? Where it first diverges from the unchanged floor, what is the paired outcome, and does a later-cycle failure mode appear?

D-053 and D-055 recorded one RETURN episode per lifetime at 140,000 transitions. Repeated return after a yield, including the candidate's post-yield behaviour, is therefore unobserved. D-055's allocated `22550–22569` block was executed in an invalidated run, so it is not treated as an untouched prospective block and is excluded here. D-056 uses the committed cycle-duration range (88,283–93,616 transitions) to select a horizon allowing approximately three complete cycles; this is rationale, not a success criterion.

### Unchanged arms and lifetime protocol

Both arms import the unchanged D-045, D-049, D-050, D-052, D-053, D-054, and D-055 modules. No controller logic is copied into the D-056 evaluator harness.

- **Arm U:** `aweform.d053.run_d053_lifetime(seed, horizon=300_000)`.
- **Arm C:** `aweform.d055.run_d055_lifetime(seed, horizon=300_000)` (`D055StallTurnCandidate` around a fresh D-052 controller).

The D-053 lifetime protocol is otherwise unchanged: centre dock `(0.50, 0.50)`, heading `0`, initial battery `0.80 × D045_BATTERY_CAPACITY_J`, ambient temperature, false charger latch, and the unchanged `D053RoamingFixture(seed)` queried once per decision. Lifetimes stop only on D-045 termination or truncation. There is no rescue, teleport, injection, early stop, or accelerated charging. Reward is `0.0`, organism-facing `info` is `{}`, and no added field or evaluator diagnostic is sent to either controller.

### Seed blocks and execution roles

- **Fresh primary:** exactly `22600–22619`, checked by `validate_exp003_development_seeds` and the exact-block guard. These legal Development seeds were never executed or named as seeds on the authorized base; substring-only appearances inside hashes/digests do not count as seed allocation.
- **Support anchor:** exactly `22053–22057`, reported separately. Their first 140,000 transitions reproduce committed D-055 and are not prospective; only continuation beyond that anchor is new.
- **Test-only:** `22620`, only at horizon `1–5,000` and initial battery fraction `0–0.21`.
- **Excluded:** `22550–22569`, already observed in D-055's invalidated execution; extending them is outside D-056.

### Episode construction and frozen classes

Each D-053 `cycles` entry defines a RETURN episode from activation through yield or lifetime end. Per episode, retain the D-053 cycle fields (roam, return and charge lengths; activation, first-contact and yield energies/transitions; maximum terminal spin count; outcome), plus docked status, Arm-C per-cycle stall-turn/detection counts, wall-pinned status at the last transition (centre within `D054_BOUNDARY_TOLERANCE_M = 1e-9 m` of any arena boundary), final-100-transition centre path, and the lifetime termination reason if this episode ends the lifetime.

The class is the first applicable rule, in this precedence order:

1. `DOCKED`: first charging-contact transition is non-null.
2. `SPIN_EXHAUSTED`: D-052 terminal-spin exhaustion occurred during the episode.
3. `WEDGED`: wall-pinned at episode end and final-100 centre path is at most `1e-9 m`.
4. `CENSORED_IN_PROGRESS`: the lifetime truncated at the horizon and this non-wedged episode is still in progress.
5. `OTHER_NOT_DOCKED`.

Failure classes are `SPIN_EXHAUSTED`, `WEDGED`, and `OTHER_NOT_DOCKED`. Censoring is uninformative and is neither success nor failure.

### Pairing

The arms must be trace-identical through the transition before Arm C's first `STALL_TURN`. The divergent episode `k*` is the cycle containing that first stall-turn transition; both arms enter `k*` from an identical activation state. Its paired class is `NO_DIVERGENCE` (no stall in lifetime), `BOTH_DOCK`, `U_ONLY_FAIL` (U failure, C docks), `C_ONLY_FAIL` (U docks, C failure), `BOTH_FAIL`, or `CENSORED` (either class is censored). Episodes after `k*` are unpaired and descriptive.

### Controls — STOP on any failure

1. **Protected source:** no diff from the authorized base in `d045.py`, `d049.py`, `d050.py`, `d052.py`, `d053.py`, `d054.py`, `d055.py`, or `development_visualizer.py`.
2. **Committed-evidence identity:** for each support seed, both arms at horizon 140,000 must reproduce the corresponding committed D-055 `part_b` `arm_u`/`arm_c` summary under `d053._canonicalize`.
3. **Horizon-prefix identity:** for each support seed and arm, the 140,000 run has 140,001 rows (transition 0 reset row plus transitions 1–140,000) and must equal the prefix of the 300,000 run after normalizing only the short final row: `truncated=True` to `False` and removal of exactly its one horizon-added `TRUNCATED` event. No other metadata, physical/controller field, event, termination, earlier row, or value is normalized.
4. **Candidate-prefix identity:** each candidate trace equals its matched floor trace row-for-row before the first `STALL_TURN`. If there is no stall turn, the complete candidate summary equals the floor summary after removing only D-055's additive stall fields and zero `STALL_TURN` source count.
5. **Seed guards:** exact official blocks and test-only seed/horizon/initial-energy restrictions above.
6. **Information boundary:** the unchanged runners receive no new input; reward and organism-facing info remain exactly zero and empty.

The horizon-prefix unit test uses test-only seed `22620` at paired horizons (300 and 600). It enforces `len(short)=short_horizon+1`, precisely the final-row normalization above, and STOPs on synthetic physical/controller changes, extra/changed non-`TRUNCATED` events, or earlier-row differences. Candidate prefix validation also uses only `22620` at the permitted short horizon.

### Frozen readouts and interpretation

Report separately for fresh and support blocks:

- divergent-episode paired-class counts and the `k*` index distribution;
- all episode-class counts by arm;
- per lifetime: RETURN activations, docks, completed yields, termination reason, final mode, minimum observed energy and battery joules, Level-1 preemption count/fraction, and boundary-scaled transitions;
- every per-episode field above;
- Arm C stall turns and detections per episode, number of episodes with a stall turn, maximum stall turns in one episode, non-pursuit detections, and detector audit;
- Arm U first-episode `DOCKED` count on the fresh block (the first prospective unchanged-floor first-episode count on untouched seeds).

The Arm-C detector audit reports the preceding transition's evaluator `boundary_scale` at every reconstructed candidate detection (maximum and counts at exactly zero, in `(0, 1e-9]`, and above `1e-9`), plus missed-stall count using the D-055 lifetime analogue. These are post-hoc evaluator readouts and never causal inputs.

The discrete signature is `FRESH_DIVERGENT_PAIRS`, `SUPPORT_DIVERGENT_PAIRS`, `FRESH_C_FAILED_EPISODES`, `C_HARM` (`NONE`/`SOME`), `FRESH_C_YIELDS_PER_LIFETIME`, and `FRESH_U_FIRST_EPISODE_DOCKED` (`k/20`). Any Arm-C failed episode in any cycle is negative evidence against adoption as-is and is not repaired here. A `C_ONLY_FAIL` is paired harm; failures after `k*` are unpaired. If Arm U has no failures in the fresh block, that block is uninformative about rescue but remains informative about harm and multi-cycle candidate viability. Counts are descriptive; no rate estimates an EXP claim.

Registered expectations (not criteria or tuning targets): roughly three RETURN episodes per surviving lifetime; an unchanged-floor wedge may end in D-045 energy termination roughly 71,000 transitions after activation; and Arm C is bit-identical to Arm U for lifetimes with no stall turn.

### Artifact and provenance discipline

The sole result artifact is `development/D-056-v05-multi-cycle-stall-turn-lifetimes.json`. It contains the protocol/constants, controls, 50 D-053/D-055-schema lifetime summaries (event samples capped at 256 per lifetime), per-episode table, pairs, aggregates, detector audit, and signature. It contains no per-transition traces and no visualization. Floats use output-only `Decimal(x).quantize(Decimal('1e-12'), ROUND_HALF_EVEN)`, normalize `-0.0` to `0.0`, and reject non-finite values; causal arithmetic is never rounded.

No scientific pilot was run for D-056. No fresh seed or test seed has been executed, and no execution beyond the committed 140,000-transition protocol has been run on any seed. Prior bounded test-only runner checks, and the already disclosed unrelated D-053 support-seed visualization replay, are not D-056 outcomes; no second or later RETURN cycle has been observed. No seed, horizon, mechanism, classifier, readout, or interpretation rule was selected from those checks.

First run the official protocol only from the pushed clean executable/protocol freeze. Independently regenerate from that exact freeze and require byte-identical JSON. After the freeze, only this completed record, its JSON, and one INDEX row may change; a code/test/protocol defect is a STOP and requires clarification rather than editing frozen files.

**surprised_by:** Pending official execution; no outcome inspected.

**disposition:** CONTINUING. Preserve null or negative results unchanged. Flow retains any later adoption, substrate, or pause decision. No successor is authorized by this record.
