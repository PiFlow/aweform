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

The registered development sources are `d003`, `d005`, and `d006`:

```text
aweform-visualize --source d003 --seed 18141 --horizon 1000
aweform-visualize --source d005 --seed 18141 --horizon 1000
aweform-visualize --source d006 --seed 18141 --horizon 1000
```

All adapters return the same neutral model. D-006 regime and learned-state
diagnostics remain in its evaluator trace/result record; the shared renderer
does not display them as organism observations. New D-007 support should
follow this adapter pattern and should not add another Matplotlib visualizer
module.
