# D-058 — V0.5 physical wall-contact substrate conformance

## Frozen protocol and provenance

- **Lane / scope:** Development, evaluator-only substrate conformance and structural-feasibility checks; no seeded lifetimes, controller runs, Level-1 floor, D-055 candidate, re-baseline, visualizer, or HTML.
- **Authorization:** #203 PROPOSAL_VERSION 1 at base `827a35638e727cd11f50eefa7d957a4d960f7e1d`, Sol proposal PASS `5913855116`; Verification amendment 1 (Sol ruling `5914161746`, approved `5914166893`).
- **Protocol:** `d058-v05-physical-wall-contact-substrate-v1`; schema `d058-v1`; artifact schema `D058-1`.
- **Executed source/protocol SHA:** `ddefe63b31a3b83872599b128e7c5d290d22e4de` (committed executable and protocol freeze; the later record/artifact/index commit is not the executed source).
- **Official generation command:** `uv run python -m aweform.d058 --output development/D-058-v05-physical-wall-contact-substrate.json --executed-commit-sha ddefe63b31a3b83872599b128e7c5d290d22e4de`.
- **Artifact:** `development/D-058-v05-physical-wall-contact-substrate.json`; 33,817 bytes; SHA-256 `2b0bb325313f352f42690eb8f4efe9ad0fdc8bf030da76e27ea5ccd053f37c6e`.
- **Determinism / check 6:** regenerated the JSON from a fresh `git archive` of the executed source SHA, using the same command and SHA; `cmp` byte comparison PASS. The independently regenerated output was temporary and removed.
- **Frozen command order:** `U9 = (-m,-m), (-m,0), (-m,+m), (0,-m), (0,+m), (+m,-m), (+m,0), (+m,+m), ONSET`; `U10 = U9, (0,0)`. The 64-step sequence uses `U10[i mod 10]` for `i=0…63`. `H32` is 24 headings at `k·15°`, followed by the four hx peaks and four hy peaks in the authorized order. No RNG or unordered iteration is used.
- **Pre-official exposure preserved:** the initial frozen check-3 independent-corner diagnostic found `x = -6.938893903907228e-18 m` for `L=3`, `x_min` flush, heading 0, `U9[2]=(-m,+m)`. This was disclosed before the official run. It was not an official artifact/run and supplied no result selection or probe changes.

## Implementation boundary

D-058 is a declared **endpoint-only kinematic idealization**: the true rectangular hull is projected at the endpoint into the heading-dependent free box, with full unwrapped yaw, unchanged clamped wheel rotation/encoders/effort, and unchanged D-045 energy and thermal bookkeeping. The contact record is evaluator-only and is absent from the observation and `info`. The causal wall law uses no epsilon, `nextafter`, bisection, corner repair, or swept-path solver.

Intermediate penetration between endpoints is explicitly disclosed; this characterization samples the specified `k/64` arc poses and in-interval analytic extent peaks and does not establish continuous nonpenetration or hardware-valid contact. The maximum is well below the full symbolic float64 bound:

```text
Δθ_max = 2·r·m/b
 d_max = r·m
 B = 2·hypot(A,C)·sin(Δθ_max/2) + d_max = 0.07292419035931953 m
```

### Verification amendment 1 (bounded, verification-only)

Only the independent four-rotated-corner containment check (check 3) and check 5 endpoint-legality check use `tau(L) = 64·2^-52·L`: `4.263256414560601e-14 m` at `L=3.0`, `1.4210854715202004e-14 m` at `L=1.0`. Four actual rotated corners are independently reconstructed and every room wall is tested. Any violation above tau stops execution. This does not alter the simulator law, probe coverage/order, check-2 bit-exact identity, or check-7 comparison against unrelaxed symbolic `B`. Observed finite-precision endpoint containment is within this predeclared allowance; this is not a claim that every calculated corner is literally nonnegative or that continuous swept contact was validated.

## Results

All checks 1–7 passed; verdict: **`D058_SUBSTRATE_CONFORMANT`**.

1. **Protected sources — PASS.** Protected D-045/D-049…D-057 and development-visualizer sources are unchanged from the authorized base; the test enforces `git diff --exit-code` against that base.
2. **Free-space identity — PASS.** At both room sizes, all 5,760 eligible interior-grid × H32 × U10 cases matched D-045 bit-exactly, including pose, observation bytes, energy, thermal state, reward/termination tuple and `info`. The 5,760 cases were also repeated at the frozen low-battery value `1,065.6 J`. The frozen sequence matched for 64 steps in each room (128 total), with exact U10 cycling order above.
3. **Projection invariants — PASS.** 9,216 wall/corner cases and 5,184 interior-grid cases (14,400 total) checked endpoint legality, independent four-corner containment within tau, idempotence, exact yaw, clamped wheel deltas and encoder values, effort and energy identities. There were **970** cases with a strictly positive independently calculated corner violation. The maximum was **`4.440892098500626e-16 m`**, at an `x_max` flush wall, `L=3.0`, heading `0.2617993877991494 rad`, command U9[6] `(+m,0)`; one reconstructed corner was `(3.0000000000000004, 1.405141594331826)`. All positive violations were within tau.
4. **Wall and corner cases — PASS.** Head-on, oblique exact tangential retention, and corner removal of both components passed. All **512** pure-spin cases (both signs × four walls × H32 × two room sizes) retained exact yaw/tangential pivot and stayed within `hypot(A,C)·|Δθ|`. All **64** bottom-wall ONSET cases were recorded descriptively only.
5. **Reset, dock and envelope — PASS.** Both room defaults, wrong station and unknown-key rejection, hull-intersecting wall/corner reset rejection, and dock contact at the station centre passed. The full legal probe endpoints (14,400) met endpoint legality; check 5 used only the same declared tau for independent corner arithmetic.
6. **Determinism — PASS.** Fresh-archive regeneration was byte-identical to the official JSON (see provenance command above).
7. **Sampled intermediate penetration — PASS.** All **9,216** frozen wall/corner × variant × H32 × U9 × room cases were characterized using all `k/64`, `k=1…63`, exact arc samples and every in-interval extent-peak heading. **4,448** cases had nonzero sampled penetration. The overall maximum was **`0.029728207073843826 m`**, at `L=3.0`, `x_max` flush, heading `0`, command U9[4] `(0,+m)`, sample `k=63` of 64. The artifact reports maxima per exact wheel-command pair, wall/corner identifier, start variant, and room size; no post-hoc command classes were used. Every sample was below the full symbolic `B=0.07292419035931953 m`.

## Claims and disposition

Under wheel-slip semantics the wall-stall predicate in D-055 is structurally dormant; no D-055 candidate was run. D-045…D-057 evidence remains bound to D-045. No Level-1, D-055, seeded-lifetime, or re-baseline evidence was produced. This is a descriptive conformance record, not a confirmatory claim and not evidence of continuous collision fidelity or hardware wall behaviour.

**surprised_by:** the independent corner calculation exposed small positive float64 wall violations on otherwise projected endpoint poses; Verification amendment 1 bounded this solely as an external verification allowance without changing the causal law.

**disposition:** CONTINUING.
