# Iteration 2 bounded diagnosis — interpretation

**Classification:** this is a small diagnostic probe, not the frozen acceptance corpus, not a B gate, and not evidence of validated physical contact. No organism/reference lifetime ran. The original v1 result file and SHA-256 remain unchanged.

## Findings

- **VERIFIED within the fixed fixture:** the historical C2 west-wall head-on trajectory progressed from free motion to increasing overlap after wall contact; in v1 the recorded maximum against the ideal room line reached `0.04150745507058784 m` at 10 substeps (`0.04078590798872191 m` at 20). The repeated ideal-velocity assignment occurred before every microstep.
- **VERIFIED counterfactual contrast:** suppressing only subsequent C2 velocity refreshes after the first contact callback in each logical interval reduced the corresponding maximum *ideal room-line* penetration to `0.0012313096665520441 m`, with final measured room-line penetration `0.0 m`. This is a large reduction but still exceeds the frozen `0.001 m` limit by `0.0002313097 m`; it does not pass or authorize an acceptance result.
- **VERIFIED disconfirmation:** the same contact-gated refresh rule in the no-contact 20-step C2 arc produced no contact callback and maximum independent free-arc error `4.97e-16 m`. A passive flush-wall/zero-command control produced no room-line penetration, no impulse, and no pose change, although contact callbacks were present.
- **VERIFIED second intervention:** changing only collision bias to `0.9**100` (10% residual correction per 0.01 s step) while retaining every-microstep C2 velocity refresh reduced the recorded room-line maximum to `0.024110631465489377 m`, still far above 1 mm. This does not show that bias is the sole cause.
- **INFERENCE, bounded to this fixture:** repeated reapplication of commanded velocity after solver contact is a major contributor to the large sustained-push penetration; passive geometry alone does not explain its growth. The collision-bias intervention also changes the visible overlap, so it contributes to the amount/correction but does not cure the repeated-drive case. A contact-gated refresh is not yet a validated actuator/contact model.

## Measurement limitation requiring correction

The independent wall metric measures hull penetration relative to zero-thickness room lines. Pymunk's current 0.01 m wall segments are centred on those same lines, so their 0.005 m radius extends into the nominal room. A hull can therefore overlap the Pymunk wall shape while the room-line metric reports zero or less penetration. The probe did **not** record independent hull-to-each-shape minimum clearance, contact identities, or a true swept-trajectory clearance. Its maxima cannot establish actual wall-shape overlap <=1 mm, contact simultaneity, or absence of tunnelling. The acceptance candidate must align the inside wall faces with the declared room boundary and report independent trajectory clearance and actual contact identities. Preserve the 1 mm gate unchanged.

The probe used one fresh space per case and did not exercise the required acceptance reset/replay protocol. It does not validate reset controls or establish 10-vs-20 convergence. All four probes are diagnostic only and cannot replace or be pooled with the forthcoming corrected acceptance run.

## Disposition

The dominant candidate mechanism to carry into a single corrected candidate is contact persistence: once Pymunk has modified velocity during a logical command, do not overwrite that solver response at later microsteps in the same command; the next logical command may apply the next declared shaft-derived command. Keep the existing actuator selection C2's numerical-only rationale and no-hardware-fidelity boundary. Correct measurement and reset/replay controls before one newly frozen bounded contact check. If any essential B gate in that check fails, preserve it and stop; do not tune or run a lifetime.
