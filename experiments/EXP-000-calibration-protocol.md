# EXP-000 Calibration Protocol

**Status:** Formal calibration protocol for EXP-000; formal calibration
artifacts have been generated and are retained in the research record.

This document freezes the calibration contract before the designated
development data are viewed. It is not a confirmatory result. It distinguishes
the programmed mechanism, calibration choices, the later confirmatory test,
evaluator diagnostics, and the limits of scientific interpretation.

## Scientific question

EXP-000 asks whether informative access to internal energetic state improves
energetic viability in a bounded resource environment when external sensory
access and the surrounding controller/environment structure are otherwise
closely matched.

The primary causal comparison is **B**, a homeostatic controller with truthful
energetic interoception, versus **C**, the same homeostatic controller
structure with a non-informative fixed energetic signal. **A** remains a
persistent-exploration behavioural reference.

This protocol does not broaden the question to intelligence, learning,
consciousness, subjective motivation, biological life, emotion, curiosity,
play, memory, planning, or evolution.

## Research-record note

- The three formal calibration artifacts were generated under SHA
  `b9c3188ce2ba6f151b242537d008ed5ed164671f`.
- The initial artifact-only summarization stopped on a validator/schema-
  semantics mismatch before candidate diagnostics or selection were displayed
  or interpreted.
- This correction aligns the validator with the already-existing runner
  artifact contract.
- No experimental parameters, controller/environment behaviour, calibration
  artifacts, selection rule, or acceptance seeds were changed.
- The original calibration artifacts are retained and will be summarized after
  this correction rather than regenerated.

## Programmed mechanism held provisionally fixed

Unless this protocol is explicitly revised, calibration keeps the following
programmed mechanism fixed.

### World and resources

- The world is a continuous bounded square with bounds 0.0–1.0 on both axes.
- Calibration uses exactly one renewable static resource source. Resource
  count remains configurable in code, but formal EXP-000 calibration uses 1.
- The resource peak intensity is 1.0 and the field is Gaussian-like.
- The resource source is hidden from the controller.

### Body, actions, and energy

- Initial energy is 5.0 of a maximum 10.0.
- Movement distance is 0.05; the turn angle is π/4 (45 degrees).
- The action set remains `WAIT`, `TURN_LEFT`, `TURN_RIGHT`, and
  `MOVE_FORWARD`.
- Maximum energy is 10.0; basal cost is 0.1 per transition.
- Movement cost is 0.1, turn cost is 0.02, and wait cost is 0.0.
- Harvest rate is 0.5.
- Failure uses the existing energy failure boundary.
- Gymnasium reward remains exactly `0.0` on every transition.

### Sensing

The observation remains exactly:

`[normalized_energy, left_resource, forward_resource, right_resource]`

The probe distance is 0.1 and sensor angle is π/4. Controllers receive no
absolute coordinates, resource coordinates, map, or rear sensor.

### Controllers

- **A:** persistent exploration: eight `MOVE_FORWARD` decisions followed by
  `TURN_LEFT`, repeating.
- **B:** enter `SEEK_RESOURCE` when actual normalized energy is `< 0.35` and
  remain there until actual normalized energy is `> 0.85`. Exploration uses the
  same persistent exploration mechanism; seeking uses the existing local
  left/forward/right steering logic. Equal signals use the existing
  `TURN_LEFT` resampling reflex.
- **C:** uses the same homeostatic decision structure as B, but with the fixed
  energy signal specified below.

These are programmed controllers, not learned controllers. None of these
mechanisms is changed by this calibration-tooling slice.

## Calibration choices

### Formal C ablation candidate

The formal fixed-mask candidate is:

`masked_energy = 0.5`

This lies strictly between the current mode thresholds:

`0.35 < 0.5 < 0.85`

Under the current shared controller architecture, the mask therefore supplies
no useful information about actual energetic depletion or recovery and C
should remain in `EXPLORE`. The development/demo mask `0.2` forced persistent
`SEEK_RESOURCE` behaviour; it was a debug configuration, not the formal
ablation candidate. Choosing `0.5` is a deliberate ablation-design choice,
not a discovered biological fact.

As an experimental-control sanity check, matched A/C trajectories are expected
to be identical with this mask and the current controller architecture. Any
matched A/C divergence during formal calibration requires investigation before
confirmatory execution.

The `EnergyBlindController` implementation and global masked-energy defaults
are unchanged; the experiment runner supplies the value explicitly.

### Horizon and calibration parameter

The calibration episode horizon is **500 steps**, supplied explicitly by the
runner. The generic `AweformEnvConfig.episode_horizon` default is not changed.

The only environment parameter varied in this round is
`resource_length_scale`, with candidates:

`0.15`, `0.20`, and `0.25`

This parameter controls how spatially local the smooth resource field is and
therefore affects sensing and harvest opportunity. It must not be chosen by
maximizing a B-versus-C advantage; calibration selects non-degenerate task
difficulty.

### Reserved seeds

Formal development/calibration seeds are exactly **1001–1030 inclusive** (30
matched seeds). Seeds 701–705 and other seeds used visually during development
remain development/debug seeds and are not acceptance seeds.

Untouched acceptance/confirmatory seeds are exactly **10001–10100 inclusive**
(100 matched seeds). They must not be executed, generated, inspected,
visualized, summarized, or used for tuning until the protocol is frozen. They
must not be replaced because results are inconvenient. If a protocol-defining
parameter changes after acceptance data are viewed, the experiment revision
must change and the earlier result remains part of the research record.

## Frozen calibration selection rule

For each length-scale candidate, use the 30 matched calibration seeds. The
primary difficulty quantity is C mean lifespan, where lifespan is steps
executed and is capped at the 500-step horizon.

A candidate is acceptable only if:

- C mean lifespan is in the inclusive band **100–400 steps**; and
- at least **6 of 30** B episodes contain at least one completed
  `SEEK_RESOURCE → EXPLORE` recovery transition.

The second criterion is an engineering check that the homeostatic mechanism is
exercised, not a scientific outcome.

Selection is performed before confirmatory interpretation:

1. discard candidates outside the C mean-lifespan band;
2. discard candidates failing the B mechanism-exercise criterion;
3. among candidates that remain, choose the length scale whose C mean lifespan
   is closest to 250 steps;
4. for an exact tie, choose the smaller length scale.

B-versus-C effect size, B mean lifespan, and visual appearance are not used for
selection. If no candidate is acceptable, stop calibration. Do not improvise
additional values; create a documented protocol revision before extending the
grid.

## Calibration diagnostics

The artifact-only summarizer reports, for every length scale and condition:

- episode count, mean/median/minimum/maximum lifespan;
- horizon-survival count and fraction;
- mean final normalized energy and mean minimum normalized energy;
- mean total harvested energy, mean total action energy cost, and mean total
  distance travelled.

For B it also reports the number of seeds with at least one completed recovery,
total completed recoveries, mean seek-resource steps, mean explore steps, and
mean mode transitions. Recovery is counted only when recorded controller modes
transition from `SEEK_RESOURCE` to `EXPLORE`.

For A/C it reports matched-seed trajectory identity and divergence counts. The
identity comparison includes action, position, heading, energy, termination /
truncation, and harvested-energy sequences. A/C divergence is visibly flagged
as a failed structural sanity check that blocks candidate selection and requires
investigation before confirmatory execution. Visual appearance is not a
calibration outcome.

## Planned confirmatory outcome

Before acceptance execution, freeze the final inferential procedure. The
intended primary endpoint for each acceptance seed is:

`lifespan_difference = lifespan_B - lifespan_C`

where lifespan is steps executed capped at the frozen 500-step horizon. The
primary aggregate is the mean paired B-minus-C lifespan difference across the
100 matched acceptance seeds. The preregistered direction is **B > C**. The
intended inferential approach is a paired confidence interval over the 100
B-minus-C differences. Confirmatory statistics and acceptance execution are
not part of this PR.

No post-hoc replacement of the primary outcome is allowed because a secondary
diagnostic looks more favourable.

## Interpretation limits

A positive B>C result would support only the narrow claim that informative
energetic interoception can causally organise this transparent programmed
perception-action policy around viability in this particular simulated
environment.

It would not demonstrate intelligence, consciousness, subjective hunger or
desire, emotion, biological metabolism, genuine biological life, general
survival instinct, learning, or evolution. A null or negative result remains
scientifically valid. A very large positive result must still be examined for
triviality or ablation pathology.

## Future manual calibration commands

These commands are examples for manual execution only **after this PR is
reviewed and merged**. They are intentionally not run by this PR. Use the
same reviewed Git SHA in all three commands:

```sh
uv run aweform-development --seed 1001 1002 1003 1004 1005 1006 1007 1008 1009 1010 1011 1012 1013 1014 1015 1016 1017 1018 1019 1020 1021 1022 1023 1024 1025 1026 1027 1028 1029 1030 --masked-energy 0.5 --resource-count 1 --episode-horizon 500 --resource-length-scale 0.15 --git-sha <REVIEWED_GIT_SHA> --output exp-000-calibration-015.json
uv run aweform-development --seed 1001 1002 1003 1004 1005 1006 1007 1008 1009 1010 1011 1012 1013 1014 1015 1016 1017 1018 1019 1020 1021 1022 1023 1024 1025 1026 1027 1028 1029 1030 --masked-energy 0.5 --resource-count 1 --episode-horizon 500 --resource-length-scale 0.20 --git-sha <REVIEWED_GIT_SHA> --output exp-000-calibration-020.json
uv run aweform-development --seed 1001 1002 1003 1004 1005 1006 1007 1008 1009 1010 1011 1012 1013 1014 1015 1016 1017 1018 1019 1020 1021 1022 1023 1024 1025 1026 1027 1028 1029 1030 --masked-energy 0.5 --resource-count 1 --episode-horizon 500 --resource-length-scale 0.25 --git-sha <REVIEWED_GIT_SHA> --output exp-000-calibration-025.json
uv run aweform-summarize-calibration exp-000-calibration-015.json exp-000-calibration-020.json exp-000-calibration-025.json --output exp-000-calibration-summary.md
```

Do **not** run acceptance seeds `10001–10100` until protocol freeze. No
acceptance command is provided here to reduce accidental execution.

The summarizer consumes only the three already-generated JSON artifacts; it
does not execute the environment or create trajectories.
