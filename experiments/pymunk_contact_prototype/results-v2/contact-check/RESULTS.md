# Corrected Pymunk fixed-command contact check

Executable SHA: `832d095142f2b2e116d2848afdd32bd011d07ad2`
Protocol SHA-256: `e43e3bcfa26a1546045641da3b160e44656d0d83e87defa483e36fe12593e2bf`

Essential B: **FAIL**

| Gate | Result |
|---|---|
| runtime_and_pin | PASS |
| action_shaft_encoder | PASS |
| logical_time_and_shaft | PASS |
| free_space_calibration_position | PASS |
| free_space_calibration_yaw | PASS |
| contact_penetration | FAIL |
| trajectory_clearance_sampling_bound | PASS |
| expected_contacts_observed | FAIL |
| substep_tunneling | PASS |
| contact_identity_complete | PASS |
| nonnegative_impulse | PASS |
| stuck_recovery | PASS |
| 10_vs_20_position | FAIL |
| 10_vs_20_per_shape_clearance | FAIL |
| 10_vs_20_yaw | FAIL |
| contact_state_convergence | FAIL |
| reset_and_inventory | PASS |
| fresh_process_replay | PASS |
| finite_outputs | PASS |
| essential_B | FAIL |

No lifetime ran in the fixed-command diagnostic runner.
No production physics or hardware-fidelity claim is made.
