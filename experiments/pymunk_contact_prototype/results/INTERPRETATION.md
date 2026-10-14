# Pymunk contact prototype — result interpretation and STOP

**Outcome: essential fixed-command gate B failed.** This report interprets the immutable result recorded by executable `bc8248c658397afd56dec307e4d344b16a86abb8` in `results.json`. The result JSON and its receipt in `SHA256SUMS` are unchanged, and the current result-affecting executable files are restored to that measured source. This is an engineering diagnostic, not an EXP result or a production-simulator decision.

## Provenance correction and limitations

Commit `04ab9e1` was an unmeasured fixer round after the recorded run. It changed result-affecting executable files but did not produce replacement measurements or provenance. This follow-up preserves `04ab9e1` in history while restoring its result-affecting executable files to the exact bytes of measured executable `bc8248c658397afd56dec307e4d344b16a86abb8`; the restored source, not the fixer round, is the executable provenance for these artifacts.

The original measured implementation has important unsupported controls: its swept-crossing threshold was separate from endpoint penetration but classified only penetration greater than `0.001 m`; its contact callbacks were accumulated across microsteps without simultaneous shape identity; its replay equality was same-process repeatability, not fresh-process evidence; its reset digest/control and trajectory minimum-clearance recording were incomplete; and its contact-state convergence was not an enforced gate. These limitations mean the recorded implementation-level gate outputs are not validated scientific evidence or acceptance of a physical contact mechanism.

## Measured record

The frozen runner recorded 255 cases at 10 substeps and 255 at 20 substeps. The same-process same-source serialization replay was byte-identical (`bef842a5867dab4d9c88fcc1d3482b22f38fdb63e0328f5d917fdec5a282563b`); this does not establish fresh-process replay. Runtime/pin, input/shaft/encoder, logical-time, free-space calibration, finite/reset/replay, nonnegative impulse, stuck recovery, reset inventory, and yaw-sensitivity gates were reported as passed by the original implementation, but reset-control and clearance requirements were not thereby established. The free-space residual maxima were `1.7763568394002505e-15 m` and `3.9968028886505635e-15 rad`.

Four essential gates failed:

- **Penetration:** frozen maximum allowed was `0.001 m`. The west-wall head-on case reached `0.04150745507058784 m` penetration at 10 substeps (`0.04078590798872191 m` at 20). Across the corpus, the largest recorded penetration was `0.047493090627833676 m` at 10 and `0.04675582149491235 m` at 20 (wall-adjacent post cases).
- **Expected contacts:** the specified contact was absent for the final wall-turn sequence in each of the four wall orientations, at both resolutions. Other prescribed responses/contact outcomes remain as recorded case-by-case in the JSON; no cases are removed or reclassified here.
- **Swept/substep crossing:** 29 case records at each resolution were flagged by the frozen independent geometry check.
- **10-vs-20 position convergence:** maximum corresponding position difference was `0.000844612172315143 m`, exceeding `0.0005 m`. Yaw convergence passed (maximum `0.0009304479593100767 rad`, below `0.001 rad`).

The west-wall head-on penetration alone is over 41 times the declared maximum. The other failures independently preclude passage. Per the frozen STOP rule, `essential_B_pass` and `lifetime_authorized_to_run` are false; **no Aweform organism lifetime ran**. No repair, rescue, retuning, extra measurement, or result replacement is authorized by this record.

## Engineering interpretation (evidence-bounded)

- **VERIFIED:** The prototype used Pymunk's dynamic rigid body, shapes, `Space.step()` and post-solve arbiter impulses; it did not analytically assign endpoint poses. The frozen records include nonnegative impulses and real geometric overlap/crossing as measured by independent rectangle/wall/circle calculations. This is a direct dynamic-contact implementation, not the former endpoint-projection collision law.
- **VERIFIED:** In every engine microstep, the fixture prescribes the ideal shaft-derived linear and angular velocities immediately before `Space.step()`. This is the frozen ideal velocity-drive actuator, not a wheel-force/torque or traction model. At the next microstep the commanded twist is prescribed again, so contact-modified velocity is not an independently evolving actuator state. Consequently the impulse trace demonstrates solver participation but is not evidence of realistic motor/contact persistence or hardware fidelity. The fixed-command results show that this particular combination of solver settings, geometry and ideal actuator did not satisfy the frozen contact gates.
- **VERIFIED:** Independent custom geometry calculations remain necessary in this experiment to classify rectangle-wall and rectangle-circle clearance/penetration and detect swept violations; the result gates and case inventory also remain experiment-specific. Pymunk did not eliminate the need for independent geometry auditing, and its tested configuration did not provide acceptable bounded penetration or convergence.
- **INFERENCE:** Directly using a general-purpose solver can replace hand-written endpoint collision resolution as the mechanism that advances/resolves body contacts, but this failed prototype does not establish that it reduces total engineering effort. The required independent validation, actuator semantics and unresolved contact-quality failures remain substantial. A different actuator/contact persistence design or solver configuration would be a new scientific disposition, not a conclusion supported by these measurements.
- **UNKNOWN:** Whether another prospectively authorized physical-actuation/contact design could meet the frozen criteria, whether Pymunk would be a better production substrate, and any relationship to hardware behavior. No hardware-fidelity, production-adoption, durable-boundary or developmental claim follows.

The actuator caveat was identified before measurement in the independent Sol technical handoff: overwriting velocity each microstep can override solver-modified velocity on the next step. The protocol therefore explicitly froze ideal shaft-velocity drive and recorded impulses, penetration, body/shaft difference and substep sensitivity. This outcome does not resolve that modeling limitation in favor of physical realism.

The 3 m lifetime room was specified to have walls and dock but zero interior obstacles; the lifetime gate was conditional on all essential B gates passing. Since B failed, the empty-room lifetime was correctly not attempted. Circular posts were used only in the fixed-command diagnostics. This record does not alter or supersede historical #219, the #220/#225 calibration records, D-058, D-060, or any accepted ADR.

## Routine validation boundary

Run only the software checks listed in `../VALIDATION.md`. The test module checks pure contract/geometry helpers, inventory and reset construction, the observation boundary, and the one-shot gate structure. It does not call `Space.step`, `run_suite`, `measure`, `run_once`, or `run_reference_once`; it does not execute the diagnostic corpus or lifetime. The measured commands in that file are explicitly excluded from routine tests and CI. Do not invoke either runner again.
