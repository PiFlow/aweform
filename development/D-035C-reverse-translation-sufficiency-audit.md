# D-035C — Evaluator-only reverse-translation sufficiency audit

- **id:** D-035C
- **lane:** Development
- **authoritative_base_sha:** `f694d47eb2c94cf3afbf07f327036234faceacea`
- **base_tree_sha:** `c28b9debd8f666937fd57c0e3864d48be5135417`
- **development_seeds:** `18468..18487` inclusive, reused exactly
- **underlying lifetime horizon:** `70,000` transitions
- **counterfactual branch horizon:** at most `256` transitions from each anchor
- **status:** official treatment completed; protocol frozen before official treatment output
- **disposition:** `CONTINUING`

The machine-readable result is
[`D-035C-reverse-translation-sufficiency-audit.json`](D-035C-reverse-translation-sufficiency-audit.json).

## Question and boundary

D-035C asks whether, at already-observed trapped or docking-relevant states,
an evaluator-only reverse translation would provide uniquely useful local
geometry correction or short-horizon dual-contact reacquisition under the
unchanged Arm-B organism.

Reverse translation is not an action. It is a cloned-environment operation
with the exact canonical `MOVE_FORWARD` magnitude, negative body-forward
displacement, unchanged heading, mirrored world clipping, timestep, actuator
energy, thermal accounting, contact evaluation, reward `0.0`, empty
organism-facing `info`, and no RNG draw. It never enters the `Action` enum,
controller, observations, D-027 features, D-027 updates, or canonical runtime.

## Frozen protocol

The protocol first reproduces accepted Arm-B `LEARNED_NO_DETRAP` on all 20
reused seeds, including complete 168-weight state and RNG/identity checks.
It reconstructs `FIRST_FALSE_CONTACT_SEEK`, exact accepted-D-033
`ALT8_ESTABLISHED`, and `FIRST_POST_CONTACT_LOSS`, preserving unavailable
anchors and nulls.

At each available anchor, isolated read-only outcomes are computed for
`WAIT`, `TURN_LEFT`, `TURN_RIGHT`, `MOVE_FORWARD`, and evaluator-only
`REVERSE_TRANSLATION`. Geometry, station distance, contact-pair errors,
visible channel deltas, clipping/stall, energy, thermal state, strict unique
best status, margins, and ties are retained.

From each anchor, `BASELINE_B` is the exact accepted Arm-B continuation. The
matched `REVERSE_AVAILABLE_ORACLE` runs for at most 256 transitions and
evaluates the five candidates at every false-contact SEEK decision. Reverse
is physically selected only when its rear-contact max-pair-error reduction is
strictly greater than every canonical candidate; ties never select reverse.
Reverse intervention steps do not update D-027. Canonical steps update D-027
exactly once with the executed canonical action and actual next six-channel
observation.

Required isolation checks include source-state immutability, branch-order
invariance, policy/environment RNG equality, exact baseline continuation,
canonical action-set preservation, reward/info preservation, and learner
non-update on reverse interventions.

## Freeze and provenance

The complete executable protocol, focused tests, anchor reconstruction,
reverse operation, baseline/oracle branches, metrics, interpretation rules,
and artifact writer were committed before official D-035C treatment output
was executed or inspected. The clean executable SHA and final artifact
checksum are recorded below after the protocol freeze and treatment run.

- **protocol_only_freeze_sha:** `ea36b078e262a68e5c2fa6ad63325da4762a3468`
- **implementation_probe_sha:** `ea36b078e262a68e5c2fa6ad63325da4762a3468`
- **artifact_sha256:** `7a4a462da68346fedd9a78028c99c8d58aa5d1e0f8c2c8f95bee75105c0ba584`
- **artifact_size_bytes:** `2375030`

No D-035B code, branch, artifact, discussion, result, or interpretation is
used. No fresh Development or EXP seed is used. This record does not
synthesize D-035A/B/C outcomes.

## Interpretation discipline

These are descriptive Development observations only. Frequent unique reverse
geometry improvement and/or materially improved oracle reacquisition supports
reverse physical capacity as a future question without authorizing canonical
reverse motion. One-step improvement without behaviour supports a local
kinematic account that is insufficient alone. Oracle-only improvement indicates
physical capacity without an organism recruitment mechanism. Rare or absent
unique reverse benefit does not support missing reverse translation as
sufficient on this support. Baseline identity or isolation failure invalidates
treatment interpretation.

**surprised_by:** Reverse was uniquely best for one-step rear-contact geometry
on all 20 `FIRST_POST_CONTACT_LOSS` anchors and restored dual contact in that
isolated step, while it was uniquely best on only 4 of 20
`FIRST_FALSE_CONTACT_SEEK` anchors. Despite 26 oracle interventions on the
first anchor family, neither baseline nor oracle reacquired dual contact
within 256 transitions on any available anchor, so the local kinematic benefit
did not produce short-horizon behavioural recovery under this oracle.

**disposition:** `CONTINUING`.
