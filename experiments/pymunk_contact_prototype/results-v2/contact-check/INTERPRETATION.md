# Interpretation — corrected contact check v2

**Disposition: FAILED essential B; STOP.** This interpretation records the committed v2 run without tuning, repeating it, or launching a lifetime. It is descriptive engineering evidence only; it makes no hardware-fidelity, production-adoption, or organism-performance claim.

## Provenance

- Frozen executable: `832d095142f2b2e116d2848afdd32bd011d07ad2`
- Frozen protocol SHA-256: `e43e3bcfa26a1546045641da3b160e44656d0d83e87defa483e36fe12593e2bf`
- Result JSON SHA-256: `baacf581f37806e5a81b091fe8cef7ba57ca4b5643e47b2482edae8ac40d168a`
- Primary/replay trace SHA-256: `f678ebc298beab96925b52b8a5998af9623f06d44a0dd8a56b24790481478746`
- Runtime and pinned wheel gates passed. Primary PID `31507` and replay PID `33461` were distinct; canonical traces were byte-identical.
- The complete frozen corpus ran once at each resolution and was replayed once in a fresh process: 1,020 case-resolution executions, 3,188 logical commands, 47,820 engine steps, 9.86 seconds measured wall time.

## Outcomes

Penetration exceeded the unchanged 1 mm limit in **57/510** primary case-resolution runs: 29/255 at 10 substeps and 28/255 at 20. The maximum conservative penetration was **4.956 mm** at `wall-west-glance` (10 substeps) and **2.353 mm** at `post-wall-adjacent` (20 substeps). Both are failures; the 20-substep result does not establish convergence or acceptance.

Resolution comparisons also failed: 29 cases exceeded the 0.5 mm end-position limit, 13 exceeded the 0.001 rad yaw limit, and 29 exceeded the 0.5 mm per-shape minimum-clearance-difference limit. The maxima were 1.170 mm position difference (`corner-se`), 0.02138 rad yaw difference (`wall-west-turn-1`), and 2.818 mm per-shape clearance difference (`wall-west-glance`). No 10/20 contact-identity disagreements were recorded.

The runner marked `expected_contacts_observed` FAIL because the eight `wall-*-turn-2` cases had no contact. Those cases use the frozen `(A,H)` command and may be non-contact controls; this family-wide expectation is overbroad. `contact_state_convergence` is also reported FAIL even though no contact-identity disagreements occurred: its aggregate currently folds per-shape clearance convergence into the same boolean, duplicating that independent failure. These reporting/control defects do not alter the clear penetration and resolution-convergence failures, so essential B remains FAIL regardless.

Runtime/pin, action/shaft/encoder, logical-time, free-space calibration, clearance sampling-bound, tunneling, contact identity completeness, nonnegative impulse, stuck/release, reset/inventory, fresh-process replay, and finite-output gates passed. No contact case or result was removed.

## Interpretation and stop condition

The corrected contact/actuation candidate did **not** satisfy the frozen penetration or numerical-convergence criteria. The data show substantial resolution-sensitive contact response; they do not isolate a new physical root cause or justify a causal claim about collision bias, wall placement, or actuator behavior. The prior failure record and all v2 traces remain unchanged.

**No organism/reference lifetime ran.** The v2 protocol prohibits tuning/repeating after an essential failure. Any further diagnostic design or candidate requires new explicit authorization and a new result-free freeze; this failed output path is one-shot and must not be reused.
