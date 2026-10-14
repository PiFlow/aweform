# Interpretation — v3 full fixed-command contact check

**Disposition: Essential B PASS for this frozen simulator contact check.** This is bounded engineering evidence about the specified Pymunk model and protocol, not a claim of hardware fidelity, biological capability, or organism performance. No lifetime, production migration, or merge was authorized or performed.

## Provenance and execution

- Frozen executable: `a0f3b3f4fac58d88a9ea0b1b706583ce3865639d`
- Frozen protocol SHA-256: `6db905f6e6cd1501829ddb7e2f7f72bb9fc35ed1ea037ba9e12231ef1b455162`
- Full result JSON SHA-256: `ab70abcb5c5906fa1285ab526148a9c5c199e874c13346e217378d18c24b7513`
- Passing focused result SHA-256: `6e0e4c0b7a1d99262d472eda4ee8897b7fc3943f3a46ed81f089fb3fd4945afb`
- The complete 255-case corpus ran at both 400 and 800 microsteps (797 logical commands each): 956,400 primary steps, then 956,400 steps in one fresh-process replay, 1,912,800 total. All 21 reported gates passed. The 15-minute cap was not approached: `RESULTS.md` records 372.862 s; `results.json` records 371.972 s. These are separate timer snapshots (the JSON snapshot precedes result serialization and the summary snapshot follows it), both within the frozen cap.

## Outcomes

Maximum conservative penetration was 0.212671 mm at 400 and 0.156330 mm at 800, both below the unchanged 1 mm acceptance limit. The four frozen L1 no-contact controls had no contact at either resolution and retained positive minimum clearance (5 mm for the west/east controls; 22.5 mm for the south/north controls). Position convergence's maximum was 0.043694 mm, yaw convergence's maximum was 0.000415525 rad, and the maximum per-shape minimum-clearance difference was 0.094170 mm, all within their unchanged limits. There were no contact-identity disagreements; the independent L2 contact-state and per-shape-clearance gates both passed.

The primary and fresh-process replay traces were byte-identical with SHA-256 `ea40109ad9b6e130aeba0296c586ba72f1914564edce17e9998324ceeff42c53`; their process IDs differed. Runtime/pin, action/shaft/encoder, timing, free-space calibration, sampling-bound, crossing, reset, stuck/release, contact identity, impulse, inventory, and finite-output gates also passed.

This establishes Essential B only for the frozen, bounded simulator contact check. It does not revise the preserved v1/v2 failures or broaden their conclusions. No 1–2 mm fallback was needed; the original 1 mm criterion remained in force. No lifetime ran, and this result does not authorize one.
