# V3 C1/400 one-shot Level-1 lifetime and D-058 reference protocol

**Status:** result-free lifetime-only freeze; no lifetime transition has been run by this revision. The only measured evidence consumed is the already committed v3 fixed-command Essential-B PASS. This protocol authorizes preparation and a supervisor preflight, but execution is blocked until the supervisor accepts the exact committed candidate/protocol preflight.

## Authority and preserved evidence

Inbox instruction `015.msg` supplies explicit authority for exactly one unchanged-controller Level-1 Pymunk lifetime and its original prescribed matched D-058 reference; instruction `016.msg` requires evaluator-only station/dock/charging/latch/energy reporting. That authority supersedes earlier no-lifetime language only for this exact pair. It authorizes no second lifetime, contact rerun, alternate seed/start, rescue tuning, controller/observation/charger change, obstacle, production migration, successor, push, merge, or publication.

The candidate must consume, without rerunning, the accepted v3 B result:

- V3 measured executable: `a0f3b3f4fac58d88a9ea0b1b706583ce3865639d`.
- V3 result-layer commit: `6ee02fd0e5b43143ec8ae944c071f089ecbfc980`.
- V3 protocol SHA-256: `6db905f6e6cd1501829ddb7e2f7f72bb9fc35ed1ea037ba9e12231ef1b455162`.
- V3 full result SHA-256: `ab70abcb5c5906fa1285ab526148a9c5c199e874c13346e217378d18c24b7513`.
- V3 focused result SHA-256: `6e0e4c0b7a1d99262d472eda4ee8897b7fc3943f3a46ed81f089fb3fd4945afb`.
- Primary/replay contact traces are byte-identical at SHA-256 `ea40109ad9b6e130aeba0296c586ba72f1914564edce17e9998324ceeff42c53`; all 21 B gates passed. Maximum conservative penetration was 0.212671 mm at 400 and 0.156330 mm at 800, below the unchanged 1 mm gate.

The V3 result field `lifetime_authorized_in_v3_record: false` records the earlier V3 protocol's then-current scope. It is not altered or rewritten; inbox `015.msg` is the later, narrowly scoped authority for this one lifetime pair. V1/V2/V3 sources, measured artifacts, interpretations, hashes, and commit history remain preserved.

## Frozen run

Execute exactly once, serially, and only after the supervisor accepts the preflight at the exact candidate HEAD and lifetime-protocol SHA. The pair consists of:

1. One Pymunk Level-1 lifetime using 400 fixed microsteps per 0.1 s transition, the same `C2_MIDPOINT_ARC_AVERAGE`, the same v3 `ContactWorld`, collision handling, clearance sampling, geometry, and solver values. The only world shapes are the four existing 3 m room walls; `posts=()` and the dock adds no colliding shape.
2. One original prescribed matched D-058 reference lifetime, using unchanged `D058Env`, the same D-052 Level-1 controller and D-053 seeded proposal stream, and the same initial state/horizon. It uses zero Pymunk engine steps.

Both start from seed `22571`, body `(0.75,0.75)`, heading `0`, battery `2664 J`, temperature `23 °C`, charger-termination latch `false`, station centre `(1.5,1.5)`, and the 3 m empty room. Maximum horizon is 100,000 transitions per trajectory. Stop each trajectory on its existing termination/truncation or at that fixed harness horizon. The D-053 proposal stream is instantiated independently from the same fixed seed in each trajectory. Substrate trajectories and later D-052 actions may diverge; the comparison is descriptive and makes no same-trajectory causal claim.

The organism receives only the existing eight `float32` observations. The exact D-052 controller and D-053 proposal source, action/shaft/encoder path, `reward == 0.0`, `info == {}`, D-058 constitutive energy/thermal/charging equations, termination conditions, and per-logical-step accounting remain unchanged. Evaluator pose, station distance, wall-contact manifold, dock errors, latch/charger telemetry, and outputs remain outside observation, reward, info, and controller inputs. No observation is added and no evaluator field can influence action selection.

### Immutable physical boundary

The candidate verifies byte-identical Git blobs against the accepted V3 executable for `fixture.py`, `cases.py`, `run_diagnostics.py`, `run_contact_check_v3.py`, `protocol-v3.md`, the relevant D-045/D-049/D-050/D-052/D-053/D-058 and D-053 seed-policy source, `pyproject.toml`, and `uv.lock`. The C1 lifetime selects only `microsteps=400`; it does not edit or tune the V3 `ContactWorld`/C2/solver implementation. The Python 3.14.7/Pymunk 7.2.0 pinned wheel SHA remains `497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c`.

The wrapper's only physics-facing difference from the prior unexecuted adapter is selecting 400 microsteps rather than its previous 10. Additional row fields and streaming callbacks are evaluator-only: they record rather than alter the transition, are never passed to the controller/physiology, and are not used to modify actions or state. The D-058 reference implementation and all production `src/aweform` source remain untouched.

## Frozen counts, wall clock, storage, and resource guards

- Primary planned maximum: 100,000 transitions × 400 `Space.step` calls = **40,000,000 Pymunk engine steps**. An ordinary earlier termination records fewer actual steps; it does not authorize another run.
- Matched reference planned maximum: **100,000 D-058 transitions**, **0 Pymunk engine steps**.
- Combined maximum: **200,000 transitions** over two separately initialized trajectories; exactly one pair, with no replay or second seed.
- Proposed hard wall-clock cap: **10,800 seconds (3 hours)** for setup, both serial trajectories, durable per-transition logging, summaries, and final checksums. The primary stage has a 9,600-second cap; the reference stage has a 600-second cap; each trace finalization reserves 120 seconds. The outer runner also checks the overall monotonic deadline between transitions and before final artifact writes. A cap or resource failure leaves a one-shot `FAILED-INCOMPLETE` artifact; no resume/retry.
- Runtime estimate, not a trial lifetime: V3 B required 372.862 s for 1,912,800 Pymunk steps with the same per-substep 64-interval clearance/contact checks. Linear extrapolation gives 7,797 s (2.166 h) for 40 million steps. This is an extrapolation from an already accepted fixed-command measurement, not a confidence bound; the lifetime's per-row safety/charge logging and flushes may differ. The primary cap allows about 30 minutes above the extrapolation; the D-058 reference is budgeted at 10 minutes, plus 2 minutes per trace finalization and 6 minutes remaining runtime variance. No trial lifetime is permitted to refine the estimate.
- Synthetic schema sizing, not a simulated transition, estimates under 500 MB peak disk (one JSONL trace per trajectory plus summaries/manifests); preflight requires at least 1 GB free disk. Reserve 2 GB peak process memory for both retained traces and serialization; the software preflight requires at least 4 GB of free/inactive/speculative memory estimate and reports physical memory, page counts, CPU count, and load averages. No compression or dropping contact/clearance controls is planned.
- Immediately before actual execution, after supervisor acceptance, repeat CPU/load, memory, free-disk and active-scientific-workload checks. Run serially at reduced priority. Do not kill, suspend, or compete with another required workload. Any material resource deterioration prevents launch or stops the one-shot run.

## Safety, accounting, and stop conditions

Every completed Pymunk transition is streamed to disk before the next one. Preserve actual and evaluator-only fields including proposal/command/shaft deltas, pose, station distance, wall contact identities/impulses, sampled minimum clearance, conservative maximum penetration, crossing indicator, sampling bound, battery and thermal state, paired dock errors/contact, charge phase/request/stored energy/input, and latch before/after.

The unchanged Essential-B penetration criterion remains **0.001 m**. Stop immediately and preserve the failing row if penetration exceeds 1 mm, a swept crossing is detected, the clearance-sampling bound exceeds 0.0002 m, any value is non-finite, impulse is negative, a contact shape is unidentified, step accounting disagrees, battery/charging accounting is inconsistent, or the organism API/information boundary changes. Stop on any source/protocol/result/pin mismatch, I/O failure, wall-clock cap, unsafe resource change, or unresolved contact/constitutive ambiguity. A stopped output path is permanently one-shot; never resume or rerun it.

Energy/thermal death or ordinary termination is an observed outcome, not a failure or reason to rerun. If the primary ends ordinarily, execute the one prescribed D-058 reference unless the cap or a safety/provenance stop condition prevents it. If it never reaches paired dock contact, classify charging as **not exercised**, not a charger PASS/FAIL. Report station proximity separately from the exact paired dock predicate; report latch state/changes, charger phase, intervals with paired contact, actual stored energy, charger input, and battery trajectory. Contact with no energy request (for example an already latched/full charger state) is not itself a fault. A positive charging request with zero delivered energy, or an accounting mismatch, is a stop/review condition. No forced docking or separate charger test is authorized.

## One-shot paths and supervisor gate

The only future output path is `experiments/pymunk_contact_prototype/results-v3/lifetime/`. Preflight and runtime reject any other path or a pre-existing path before creating a `ContactWorld`, `D058Env`, or taking a transition. The output contains `LIFETIME_STARTED`, `pymunk-transitions.jsonl`, `reference-transitions.jsonl`, `lifetime-results.json`, and `SHA256SUMS`; failure retains partial JSONL plus `FAILED-INCOMPLETE.json`. No test, routine validation, CI, import, or `--preflight` call may call either lifetime loop.

The result-free adapter/protocol/test freeze must be committed cleanly. Run `--preflight` only: it verifies exact B provenance, all gates and trace identity; candidate/source hashes; unchanged measured physics/controller blobs; runtime pin; step plan; output-path absence; and disk availability without constructing a world or stepping. Send the resulting candidate HEAD, protocol SHA, complete estimates/counts, checks, and live resource snapshot to the supervisor. **Wait for supervisor acceptance before any lifetime call.** After acceptance, bind the one-shot CLI invocation to the exact approved candidate HEAD, protocol SHA, and SHA-256 of the acceptance receipt. Re-run the non-stepping preflight and live resource checks immediately before launch. No source/protocol commit may occur after approval.
