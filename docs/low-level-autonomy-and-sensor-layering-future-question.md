# Aweform — Future Research Question: Low-Level Autonomy and Sensor Layering

**Status:** non-authorizing future research note  
**Recorded:** 2026-09-17  
**Repository context:** recorded while D-041 was authorized from `main` at `8b51d6e143a906a83f1fd8d760aace5ed46abb9e`  
**Purpose:** preserve a long-range architectural question about whether simple energy-reacquisition and docking competence should remain useful as a low-level sensorimotor layer even if future Aweform embodiments acquire much richer perception.

**Current-state addendum (2026-09-23):** the repository-context line above is retained as historical provenance. D-041 subsequently completed with a **NULL/INSUFFICIENT** evaluator-only result and its candidate receptors never became organism-visible. ADR 0017 and D-045 now define the current eight-channel V0.5 differential-drive substrate. D-046 is authorized by issue #165 as a fresh shadow-prediction stage and adds no new sensor or camera permission.

## Motivation

At the time this note was recorded, D-041 was investigating whether a minimal pair of physically realizable front-facing charging-beacon receptors contained enough information to improve charger reacquisition and front docking. D-041 has since completed with a **NULL/INSUFFICIENT** result; those candidate receptors remained evaluator-only.

A future physical Aweform may eventually possess much richer perception, potentially including wide-field or approximately panoramic vision. This raises an important developmental question:

> If richer perception may later locate and understand the charging station, is there still scientific and engineering value in developing simple beacon-guided reacquisition and docking competence now?

The current hypothesis is yes, but for a narrower reason than making a particular infrared implementation permanent.

## Future Aweform question

> **Can a simple, low-power sensorimotor subsystem eventually carry out well-learned viability-critical behaviours such as final charger approach and docking, while richer perceptual and cognitive systems remain available for other activity?**

The intended distinction is between:

- high-level perception and cognition that can identify situations, locations, goals, and changing circumstances;
- lower-level sensorimotor competence that can execute familiar embodied behaviours reliably and economically.

Conceptually:

```text
internal energetic need
        ↓
higher-level perception / navigation
        ↓
charging station approximately located
        ↓
low-level local reacquisition and docking competence
        ↓
alignment / contact / verified charging
```

A future implementation might distribute these functions across different computational substrates. For example, a low-power microcontroller could potentially maintain local sensing and docking control while a more computationally expensive perception or world-model system performs other work.

This is a future engineering possibility, not a present architecture commitment.

## Sensor implementation should remain secondary to the developmental function

The scientifically important capability is not specifically:

> follow an infrared beam.

The more general function is:

> use physically available local information to reacquire an energy source and complete the final approach/contact behaviour.

A future physical implementation could potentially obtain that local information from infrared receptors, visible-light markers, time-of-flight sensing, cameras, other proximity sensing, or some combination.

Therefore current simulated beacon work should avoid unnecessary commitment to detailed infrared optics unless such detail becomes necessary to answer the current scientific question.

The desired abstraction is the information problem and sensorimotor competence, not premature replication of a hypothetical final charging-station technology.

## Relationship to richer future cognition

Later perception should not automatically replace simpler sensorimotor competence.

A richer visual system might answer questions such as:

- Where is the charging station?
- Which object is the charging station?
- Is the normal route obstructed?
- Should Aweform approach this resource at all?

A lower-level subsystem might answer a different class of questions:

- Is the local charging signal stronger on the left or right?
- Am I correctly aligned?
- Should I make a small corrective movement?
- Has physical charging contact actually been established?

This creates a possible hierarchy of competence rather than a sequence in which every new cognitive layer deletes the previous one.

The biological analogy is only inspirational. Aweform should not assume a literal evolutionary progression from reflexes to insects to reptiles to mammals or a simplistic layered-brain model.

## Developmental implication

Continue studying simple reacquisition and docking mechanisms only while they answer a genuine developmental question.

Do not spend substantial effort making the current simulated beacon resemble a final infrared hardware implementation unless future embodiment choices make that realism scientifically necessary.

The near-term objective should remain:

> **discover the minimum information and sensorimotor structure required for reliable energy reacquisition and docking.**

If that competence later becomes a stable low-level primitive, richer systems may be built above it rather than replacing it.

## Guards

- This note does not authorize camera vision.
- It does not authorize new organism-visible beacon receptors.
- It does not authorize a microcontroller architecture or physical robot implementation.
- It does not define infrared as the future docking technology.
- It does not reinterpret D-041 or change the current ADR 0017 / D-045 sensory-information boundary.
- It does not authorize a hierarchical cognitive architecture.
- It does not imply that low-level behaviour must remain permanently engineered rather than eventually learned.
- Any future organism-facing sensor, physical-control boundary, or durable architecture change remains subject to repository governance and the relevant ADR/review process.

## Bottom line

The purpose of current beacon/docking research is not to perfect an infrared charging system before Aweform's physical body exists.

It is to understand and develop the smallest viable sensorimotor competence for energy reacquisition and docking.

A future richer perceptual system could provide broader situational understanding while such low-level competence remains useful as an economical, reliable bodily skill.

The key developmental principle is therefore:

> **Build higher cognition on top of earned sensorimotor competence where appropriate, rather than assuming richer cognition should replace every simpler layer beneath it.**

This note authorizes no current implementation and does not alter D-045, D-046 issue #165, or the current development sequence.
