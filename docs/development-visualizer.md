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

Currently the only registered source is `d003`:

```text
aweform-visualize --source d003 --seed 18141 --horizon 1000
```

Future D-005/D-006/D-007 support should register an adapter that returns the
same neutral model. It should not add another Matplotlib visualizer module.
