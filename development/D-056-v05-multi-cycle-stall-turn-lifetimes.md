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

No scientific pilot was run for D-056. Before official execution, no fresh seed or test seed had been run under the D-056 official protocol, and no execution beyond the committed 140,000-transition protocol had been run on any seed. The separately disclosed D-053 visualization replay did not observe beyond that committed horizon. No seed, horizon, mechanism, classifier, readout, or interpretation rule was selected from prior checks.

**Pre-run protected-source verification (Sol clarification ACK).** Immediately before the official run, the checkout was clean at freeze `9e03dbfe3de4e5bfa112c2420b97201118fa8bfb`, and the authorized base commit object was present. `uv run pytest -v -rs tests/test_d056.py::test_protected_sources_unchanged` **PASSED, not skipped**. The exact protected-source `git diff --exit-code 1a9dee3321842230b5f5aa71423917ec79419918 9e03dbfe3de4e5bfa112c2420b97201118fa8bfb -- ...` also exited 0 for D-045/D-049/D-050/D-052/D-053/D-054/D-055 and `development_visualizer.py`. GitHub CI had already run the full suite at the exact freeze (1,153 passed, 1 skipped); its depth-1 checkout skips this history-dependent protected-source test because the authorized base commit is absent. After official execution, the complete local suite was run from the clean exact-freeze checkout with the base present: **1,154 passed, 7 warnings, no skips**. This full local suite was post hoc, not a pre-run validation; the pre-run validations were the standalone protected test and the explicit protected-file diff above.

### Official results

The frozen protocol ran from executable/protocol freeze `9e03dbfe3de4e5bfa112c2420b97201118fa8bfb`. All artifact controls passed: support D-055 committed-evidence identity at 140,000 transitions for both arms on all five support seeds; horizon-prefix identity from 140,000 to 300,000 on both arms/all five support seeds; candidate prefix identity for every lifetime; zero-stall summary identity whenever applicable; exact seed-block guards; reward exactly zero; organism-facing info exactly empty; and the protected-source test and exact-file diff described above. Sol ACKed the evaluator detector-audit reconstruction and its count-equality STOP guard without a re-freeze. During the official execution the reconstructed Arm-C detector counts equalled unchanged D-055's `stall_detected_count` for every lifetime; there was no mismatch STOP.

Independent regeneration from `git archive` of the exact freeze was byte-identical (`cmp` PASS). Artifact SHA-256 is `d401ade08bf6320e2d339e0c793149f77737313b4a7196441c23e78e7f7af519`; size is 1,083,133 bytes.

**Fresh block, seeds 22600–22619.** Paired classes: 15 `U_ONLY_FAIL` (candidate rescue), 5 `NO_DIVERGENCE`, and zero `C_ONLY_FAIL`, `BOTH_FAIL`, `BOTH_DOCK`, or `CENSORED`. Divergence episode indices were k*=1 for 9 lifetimes, k*=2 for 3, and k*=3 for 3. Arm U's 39 episodes comprised 24 `DOCKED` and 15 `WEDGED`; Arm C's 60 episodes were all `DOCKED`. Arm U's first episode docked on 11/20 seeds. Every Arm-C lifetime completed three yields (histogram `3:20`), with zero failed episodes and no paired harm.

**Support anchor, seeds 22053–22057.** Paired classes: 3 `U_ONLY_FAIL`, 2 `NO_DIVERGENCE`, and zero other paired classes. Divergence indices were k*=1 for 1 lifetime and k*=2 for 2. Arm U's 11 episodes comprised 8 `DOCKED` and 3 `WEDGED`; all 15 Arm-C episodes were `DOCKED`. Each Arm-C lifetime completed three yields.

**Arm-C detector audit.** Fresh: 44 detections/turns, zero non-pursuit detections and zero missed stalls; preceding-scale counts were 23 at exactly zero, 21 in `(0, 1e-9]`, and zero above `1e-9`. Support: 6 detections/turns, zero non-pursuit detections and zero missed stalls; scale counts were zero at exactly zero, 6 in `(0, 1e-9]`, and zero above `1e-9`. The maximum is `0.0` in the artifact after the frozen 12-decimal output-only rounding; positive-scale strata are counted from unrounded values before serialization. The discrete signature is `FRESH_DIVERGENT_PAIRS={U_ONLY_FAIL:15, NO_DIVERGENCE:5}`, `SUPPORT_DIVERGENT_PAIRS={U_ONLY_FAIL:3, NO_DIVERGENCE:2}`, `FRESH_C_FAILED_EPISODES=0`, `C_HARM=NONE`, `FRESH_C_YIELDS_PER_LIFETIME={3:20}`, and `FRESH_U_FIRST_EPISODE_DOCKED=11/20`.

**Interpretation and limits.** On the fresh block the candidate sustained three dock/recharge/yield cycles per lifetime with no failed episode; 15 paired U failures were rescued and five lifetimes had no divergence. The unchanged floor's first RETURN episode docked on 11/20 fresh seeds. These are descriptive Development counts, not prospective EXP rates. They do not authorize permanent adoption, a substrate change, or a successor, and say nothing about hardware, general robustness, or learning.

After the freeze, only this completed record, its JSON artifact, and the D-056 INDEX row changed. The executable and tests remain unchanged. No merge is authorized here.

**surprised_by:** The unchanged floor's 11/20 first-episode fresh docking count did not capture the entire continuous-lifetime failure picture: 15 paired divergent episodes failed on Arm U and were rescued by the unchanged candidate, while five fresh lifetimes never diverged. The candidate then completed three full cycles in every fresh lifetime, with no observed later-cycle failure or harm. This is descriptive evidence only and does not establish a prospective rate.

**disposition:** CONTINUING. Preserve these outcomes and provenance unchanged. Flow retains any later adoption, substrate, or pause decision. No successor is authorized by this record.
