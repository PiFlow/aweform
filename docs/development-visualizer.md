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
`d012`, `d013-reference`, and `d013`:

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
