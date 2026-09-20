# Canonical development visualizer

`aweform-visualize` is the canonical forward visualizer for compatible Aweform development traces. It runs a complete lifetime, adapts the completed evaluator trace into `DevelopmentVisualizationData`, and then replays that data in one shared Matplotlib renderer.

Historical EXP visualizers remain untouched for reproducibility and history. New developmental mechanisms should normally provide a small adapter from their evaluator trace into `DevelopmentVisualizationData`; they should not create another complete renderer. Extend the shared renderer only when a new display capability is broadly useful and scientifically earned. Do not add mechanism-specific diagnostics speculatively.

The view is evaluator-side: showing evaluator state does not imply that the organism could observe it. Playback is post-hoc and cannot alter lifetime causality, because all environment/controller execution finishes before rendering. Every source adapter must explicitly declare controller/organism versus evaluator visibility metadata; visibility from one developmental mechanism must never be inherited by another source.

## Source-of-truth rule

The actual source registry in `src/aweform/development_visualizer.py` is authoritative for the generic `aweform-visualize --source ...` command. This document explains the architecture and useful examples; it must not be treated as a manually maintained substitute for the live registry.

At this documentation refresh, the generic `DEVELOPMENT_VISUALIZATION_ADAPTERS` registry contains:

`d003`, `d005`, `d006`, `d011`, `d012`, `d013-reference`, `d013`, `d014`, `d015-reference`, `d015`, `d017`, `d018`, `d021`, `d023`, `d024`, `d025`, `d026`, and `d043`.

D-043 is also registered as `d043` and replays the accepted D-042 front-contact
embodiment over the merged D-043 support. The specialized command defaults to
the two-cycle example seed `19045`; seed `19048` is an artifact-confirmed
energy-depletion example:

```text
uv run aweform-visualize-d043 --seed 19045 --interval-ms 90
uv run aweform-visualize-d043 --seed 19048 --interval-ms 90
```

The replay retains deterministic stride samples plus windows around mode,
front-contact/reacquisition, full-recharge, departure, and terminal events.
Coordinates, heading, contact geometry, event labels, and display sampling are
evaluator-only; the canonical six-channel organism observation, actions,
learner, reward, and `info == {}` remain unchanged.

Representative commands:

```text
uv run aweform-visualize --source d003 --seed 18141 --horizon 1000
uv run aweform-visualize --source d005 --seed 18141 --horizon 1000
uv run aweform-visualize --source d006 --seed 18141 --horizon 1000
uv run aweform-visualize --source d011 --seed 18141 --horizon 1000
uv run aweform-visualize \
  --source d012 \
  --seed 18144 \
  --horizon 1000 \
  --interval-ms 60

uv run aweform-visualize \
  --source d013-reference \
  --seed 18344 \
  --horizon 1000 \
  --interval-ms 60

uv run aweform-visualize \
  --source d013 \
  --seed 18344 \
  --horizon 1000 \
  --interval-ms 60

uv run aweform-visualize \
  --source d014 \
  --seed 18347 \
  --horizon 1000 \
  --interval-ms 60

uv run aweform-visualize \
  --source d015-reference \
  --seed 18350 \
  --horizon 1000 \
  --interval-ms 60

uv run aweform-visualize \
  --source d015 \
  --seed 18350 \
  --horizon 1000 \
  --interval-ms 60

uv run aweform-visualize \
  --source d018 \
  --seed 18361 \
  --horizon 1000 \
  --interval-ms 90

uv run aweform-visualize \
  --source d021 \
  --seed 18365 \
  --horizon 70000

uv run aweform-visualize \
  --source d023 \
  --seed 18365 \
  --horizon 210000

uv run aweform-visualize \
  --source d026 \
  --seed 18379 \
  --horizon 70000
```

## Specialized entry points

Not every compatible visualization is exposed through the generic source registry. `pyproject.toml` currently also defines specialized shared-renderer entry points:

```text
aweform-visualize-d020
aweform-visualize-d021
aweform-visualize-d024
aweform-visualize-d030
aweform-visualize-d043
```

D-030 is the important current example. `development_visualizer.py` contains matched D-030 shared-renderer adapters for `REFERENCE_NO_INFLUENCE`, `LEARNED_FORWARD`, and `PERMUTED_FORWARD`, exposed through:

```text
uv run aweform-visualize-d030 --seed <legal-D030-seed>
```

The generic `DEVELOPMENT_VISUALIZATION_ADAPTERS` mapping does not currently register `d030`, so documentation should not claim that `aweform-visualize --source d030` is supported.

Later D-stages are often evaluator audits rather than forward lifetime mechanisms. They do **not** need a visualizer adapter merely to keep numbering contiguous. Add visualization only when it materially helps interpret the scientific question and can be represented without leaking evaluator state into organism semantics.

## Shared-renderer semantics

All generic adapters return the same neutral model. D-006 regime and learned-state diagnostics remain in its evaluator trace/result record; the shared renderer does not display them as organism observations.

D-012 replays the unchanged D-011 controller and ecology through the same adapter path; its single-seed visualization guard checks the canonical EXP-003 reservation guard and then membership in D-012's declared development block.

The two D-013 sources are a matched evaluator-side comparison. Both use the same fixed D-011 controller and ecology, and both accept only D-013's declared development seeds `18344`, `18345`, and `18346`, after the canonical formal reservation guard has run. `d013-reference` constructs no learner. `d013` constructs the accepted 84-weight `D013ActionConsequencePredictor`, replaying the current typed D-011 observation, executed action, physical transition, typed next observation, and then the predictor update. Its predictions have **zero behavioural influence**: they cannot change actions, controller mode, randomness, ecology, termination, timing, or future observations.

The D-013 learner panel is evaluator-side development visualization only. It shows cumulative pre-update MAE for energy delta, thermal delta, and charging-contact delta against a zero-change baseline, with the visible curves ending at the current playback transition. It is not confirmatory evidence. For the same seed and horizon, `d013-reference` and `d013` therefore have identical physical trajectories, charging behaviour, thermal/energy history, and controller actions; only `d013` adds the shadow-learning diagnostics.

D-014 replays the unchanged D-002 ecology and D-011 remainder with `D014Controller`. While in contact and charging, it begins departure when either normalized energy is fully charged (`energy >= 1.0`) or the existing hot-depart thermal threshold (`0.60`) is reached first. It has no learner or consequence diagnostics and uses the ordinary two-panel evaluator view.

D-015 provides the same matched two-source pattern on the corrected D-014 scaffold. `d015-reference` uses `D014Controller` with no learner and the ordinary two-panel evaluator view. `d015` attaches the unchanged D-013 84-weight action-conditioned consequence predictor in shadow only; its existing three-target cumulative pre-update MAE panel is labelled **SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE**. Both sources accept only D-015 development seeds `18350`, `18351`, and `18352`. For the same seed and horizon, their physical/controller trajectories are identical. The event-conditioned contact diagnostics are retained in the D-015 evaluator artifact rather than added as a new live renderer panel.

D-018 adds a four-row evaluator-only action-alternative panel beside the real D-014 lifetime. The real D-014 trajectory remains behaviourally authoritative; all four unchanged D-013 action predictions are shown pre-update, and the unexecuted actuals come from isolated evaluator clone results. Only the physically executed transition updates the learner afterward. Exact prior support means prior physically executed exact visible-state/action support, with no rounding or nearest-neighbour matching. This is a development/evaluator display only and is not new D-018 evidence.

D-021 and D-023 replay completed continuous V0.4 lifetimes through the shared evaluator renderer. D-021 is fixed to seed `18365` and its 70,000-transition horizon. D-023 uses its exact 210,000-transition horizon and accepts the declared development seeds `18365`, `18366`, and `18367`. Deterministic display downsampling does not create lifecycle trajectory breaks; explicit breaks in neutral display data remain available for sources that contain a genuine reset or discontinuity.

D-024, D-025, and D-026 reuse the same causal finite-body renderer and exact two-contact geometry. Their rear-contact markers are evaluator-only: each marker is colored according to the corresponding inclusive `<= 0.01` pair tolerance, while the organism-visible charging channel remains the unchanged binary dual-contact predicate. D-026 runs the real merged D-026 lifetime trace; its primary smoke/demo seed is `18379`, with `18382` available as a slower reacquisition example.

D-030 also reuses the causal finite-body renderer. Its three-arm specialized visualization exists to compare the matched reference, correctly associated learned steering, and fixed-permutation control without inventing a new renderer. It remains evaluator-side Development visualization and does not turn later D-031R1→D-040 audit diagnostics into organism observations.

## Adding future visualization support

For a future stage:

1. first determine whether visualization materially helps answer the current scientific question;
2. reuse a completed evaluator trace whenever possible;
3. adapt it into `DevelopmentVisualizationData`;
4. add only broadly useful optional neutral-model fields;
5. register the source in `DEVELOPMENT_VISUALIZATION_ADAPTERS` if it belongs in the generic CLI, or use a specialized shared-renderer entry point only when the invocation genuinely differs;
6. update this document only to describe architecture or materially useful examples, not to duplicate every D-stage number.

Historical experiment-specific visualizers remain valid for reproducibility, but they are not the default pattern for new D-lane work.
