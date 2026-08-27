# D-001 — Current ecology degeneracy probe

- **id:** D-001
- **date:** 2026-08-27
- **exact_sha:** `4058d7ad0bc529afc0d52d40b4671eb80b254698`
- **development_seeds:** `18141, 18142, 18143`
- **disposition:** `CONTINUING`

## Question

Once genuine charging contact has been established in the current EXP-003 station ecology, can trivial constant action policies preserve viability to the existing 1000-transition horizon without any learning, planning, beacon use, or departure from the charger?

## World

The probe used the existing `LocalizedChargingStationEnv` and unchanged EXP-003 defaults. No world dynamics, sensor boundary, viability rule, controller observation, or seed reservation was changed.

To isolate post-acquisition ecology from station-finding performance, the development harness placed the simulator-side body at the existing station centre before the first probe transition. This was an evaluator-side intervention only; it was not exposed as an organism observation or policy input.

Current relevant energy arithmetic is:

- docked `WAIT`: `+0.5` charge, `-0.1` basal, `-0.0` action = `+0.4` before clipping;
- docked `TURN_LEFT`: `+0.5` charge, `-0.1` basal, `-0.02` action = `+0.38` before clipping;
- maximum energy is `10.0`, with energy clipped to that bound.

## Organism / mechanism

Two fixed constant-action probes were used after charging contact:

- `DOCK_WAIT` — always choose `WAIT`;
- `DOCK_TURN_LEFT` — always choose `TURN_LEFT`.

Neither probe reads beacon values, energy, hidden evaluator state, or history after the initial evaluator-side placement. There is no learner or plastic state.

## Observed

The executable probe at exact SHA `4058d7ad0bc529afc0d52d40b4671eb80b254698` was run directly in a clean isolated worktree. The D-record itself was committed afterward, so later documentation-only commits do not claim to have been part of the executed artifact.

Only the encoded development seeds `18141`, `18142`, and `18143` were used. No formal, calibration, confirmatory, acceptance, or otherwise reserved seed was executed.

Across all three seeds and both policies (six runs total):

- every run reached all `1000` transitions;
- every run ended by horizon truncation, not viability termination;
- charging contact was preserved for the full run;
- body position was preserved for the full run;
- initial energy was `5.0` and minimum observed energy remained `5.0`;
- final energy was `10.0` in every run;
- `DOCK_WAIT` first reached full energy on transition `13`;
- `DOCK_TURN_LEFT` first reached full energy on transition `14`.

The three seeds produced the same post-contact outcome for each policy. This is unsurprising because the probe removes acquisition geometry from the question and the retained contact/energy dynamics contain no disturbance that would make the constant policies seed-sensitive after placement.

These are descriptive development observations, not confirmatory evidence.

## Surprised by

The degeneracy is broader than complete inactivity. A body can continuously spend actuator energy turning in place and still remain on the charger, reach full energy, and survive to the horizon. The current ecology therefore does not merely reward stillness; it permits at least one permanently active but spatially stationary policy to be equally viable.

## Provisional reading

For the current station ecology, post-acquisition viability does not require learning, exploration, departure, or regulation beyond remaining inside charging contact. The finite-horizon execution directly demonstrates this only through 1000 transitions.

Separately, the unchanged source arithmetic implies a stronger mechanical expectation: while charging contact is preserved, both tested policies have positive net energy before the maximum-energy clip on every transition. With no charger depletion, thermal cost, dwell penalty, stochastic disturbance, or second viability variable, there is no current mechanism that would make either policy lose viability after the measured horizon. That is an inference from the implemented dynamics, not an additional empirical run.

This does not show that the existing EXP-003 controllers are defective. It shows that the ecology itself admits trivial post-contact optima, so introducing a learner now would risk rewarding a degenerate solution rather than testing adaptive regulation.

## Next

Proceed to D-002: design the smallest coherent thermal ecology that introduces a second internal viability variable and a genuine energy/temperature regulation conflict, without adding a learner.

Before D-002 implementation, follow the durable sensory/information-boundary review requirement recorded in ADR 0010 / AGENTS and the D-002 checkpoint issue. State the intended regulation problem in advance, preserve the charging-clipping/heat-coupling caution, and do not tune the ecology merely to make fixed controllers fail.

---

D-001 does not reserve or consume any formal calibration, confirmatory, or acceptance seed and does not alter historical EXP-003 evidence or claims.
