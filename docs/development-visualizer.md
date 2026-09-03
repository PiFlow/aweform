# Canonical development visualizer

`aweform-visualize` is the canonical forward visualizer for compatible Aweform
development traces. It runs a complete lifetime, adapts the completed
evaluator trace into `DevelopmentVisualizationData`, and then replays that
data in one shared Matplotlib renderer.

Historical EXP visualizers remain untouched for reproducibility and history.
New developmental mechanisms should normally provide a small adapter from
their evaluator trace into `DevelopmentVisualizationData`; they should not
create another complete renderer. Extend the shared renderer only when a new
display capability is broadly useful and scientifically earned. Do not add
mechanism-specific diagnostics speculatively.

The view is evaluator-side: showing evaluator state does not imply that the
organism could observe it. The D-003 view labels each quantity's visibility
boundary explicitly. Playback is post-hoc and cannot alter lifetime causality,
because all environment/controller execution finishes before rendering.
Every source adapter must explicitly declare controller/organism versus
evaluator visibility metadata; visibility from one developmental mechanism must
never be inherited by another source.

The registered development sources are `d003`, `d005`, `d006`, `d011`,
`d012`, `d013-reference`, `d013`, `d014`, `d015-reference`, `d015`, `d017`,
`d018`, `d021`, and `d023`:

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
```

All adapters return the same neutral model. D-006 regime and learned-state
diagnostics remain in its evaluator trace/result record; the shared renderer
does not display them as organism observations. New D-007 support should
follow this adapter pattern and should not add another Matplotlib visualizer
module. D-012 replays the unchanged D-011 controller and ecology through the
same adapter path; its single-seed visualization guard checks the canonical
EXP-003 reservation guard and then membership in D-012's declared development
block.

The two D-013 sources are a matched evaluator-side comparison. Both use the
same fixed D-011 controller and ecology, and both accept only D-013's declared
development seeds `18344`, `18345`, and `18346`, after the canonical formal
reservation guard has run. `d013-reference` constructs no learner. `d013`
constructs the accepted 84-weight `D013ActionConsequencePredictor`, replaying
the current typed D-011 observation, executed action, physical transition,
typed next observation, and then the predictor update. Its predictions have
**zero behavioural influence**: they cannot change actions, controller mode,
randomness, ecology, termination, timing, or future observations.

The D-013 learner panel is evaluator-side development visualization only. It
shows cumulative pre-update MAE for energy delta, thermal delta, and charging-
contact delta against a zero-change baseline, with the visible curves ending
at the current playback transition. It is not confirmatory evidence. For the
same seed and horizon, `d013-reference` and `d013` therefore have identical
physical trajectories, charging behaviour, thermal/energy history, and
controller actions; only `d013` adds the shadow-learning diagnostics.

D-014 replays the unchanged D-002 ecology and D-011 remainder with
`D014Controller`. While in contact and charging, it begins departure when
either normalized energy is fully charged (`energy >= 1.0`) or the existing
hot-depart thermal threshold (`0.60`) is reached first. It has no learner or
consequence diagnostics and uses the ordinary two-panel evaluator view.

D-015 provides the same matched two-source pattern on the corrected D-014
scaffold. `d015-reference` uses `D014Controller` with no learner and the
ordinary two-panel evaluator view. `d015` attaches the unchanged D-013
84-weight action-conditioned consequence predictor in shadow only; its
existing three-target cumulative pre-update MAE panel is labelled
**SHADOW ONLY — ZERO BEHAVIOURAL INFLUENCE**. Both sources accept only D-015
development seeds `18350`, `18351`, and `18352`. For the same seed and horizon,
their physical/controller trajectories are identical. The event-conditioned
contact diagnostics are retained in the D-015 evaluator artifact rather than
added as a new live renderer panel.

D-018 adds a four-row evaluator-only action-alternative panel beside the real
D-014 lifetime. The real D-014 trajectory remains behaviourally authoritative;
all four unchanged D-013 action predictions are shown pre-update, and the
unexecuted actuals come from isolated evaluator clone results. Only the
physically executed transition updates the learner afterward. Exact prior
support means prior physically executed exact visible-state/action support,
with no rounding or nearest-neighbour matching. This is a development/evaluator
display only and is not new D-018 evidence.

D-021 and D-023 replay completed continuous V0.4 lifetimes through the shared
evaluator renderer. D-021 is fixed to seed `18365` and its 70,000-transition
horizon. D-023 uses its exact 210,000-transition horizon and accepts the
declared development seeds `18365`, `18366`, and `18367`. Deterministic display
downsampling does not create lifecycle trajectory breaks; explicit breaks in
neutral display data remain available for sources that contain a genuine reset
or discontinuity.
