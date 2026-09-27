# D-053 — V0.5 continuous-lifetime return, charge, and recovery

**Status:** Protocol frozen; official runs not yet executed. **Disposition:** CONTINUING.

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
- Display sampling retains the first and last transitions; every transition from 50 before each `RETURN_ACTIVATED` through 50 after that episode's `CHARGING_CONTACT` (or through the episode's end if no contact is acquired); ±50 transitions around every `RECOVERY_YIELD`, incidental NORMAL pass-through contact acquisition/loss, `CHARGING_CONTACT_LOST`/`REACQUIRED`, `TERMINAL_SPIN_EXHAUSTED`, the first `INVALID_BEACON` of each consecutive run, and termination/truncation; and every 100th transition elsewhere. It does not affect execution or JSON.
- Event samples record D-052's executed `wheel_command` and, separately, the fixture's `proposed_wheel_command` and `symbolic_proposal`. At most 256 are kept per seed: repeated `INVALID_BEACON`-only rows after the first of a consecutive run are collapsed; RESET and the final row are always kept; then cycle-defining/termination/first-invalid-beacon rows, other event rows, and event-free state changes fill the cap in that priority order, evenly spaced within any overflowing tier. Candidate and collapsed counts and an `event_samples_truncated` flag are recorded.

## Analytic budget stated before runs

Unobstructed full-effort roaming at a 1.15 W load takes approximately 27,800 transitions to move from 80% to 20%; bulk recharge from 20% to 80% takes approximately 18,800. Wall-boundary scaling can reduce effort and lengthen roaming. A full cycle is therefore approximately 46,700 transitions or more; roughly two yields per lifetime are expected, with a possible third cycle truncated near the horizon. This is not a success criterion. No pilot or tuning is permitted.

## Record and interpretation plan

The compact JSON records per-seed mode/source/preemption counts, return and contact events, incidental NORMAL contact acquisitions separately from D-052 acquisitions, energy minima, terminal-spin/exhaustion data, evaluator-only return-start geometry, cycle tables, bounded event samples, and a discrete outcome signature. The HTML replay uses the canonical neutral visualizer, contains all five seeds, and is fully offline. Actual cycles and any negative/partial outcomes will be preserved without tuning.

`surprised_by`: Pending official characterization; no results inspected.

`disposition`: CONTINUING — execute only from the pushed frozen executable/protocol commit; preserve the observed result irrespective of cycle count.
