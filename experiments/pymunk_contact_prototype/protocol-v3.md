# Pymunk contact prototype — v3 result-free protocol

**Status:** prospective, result-free freeze. No v3 Pymunk steps or scientific outputs exist at this point. This protocol authorizes only the two staged fixed-command checks below; it does not authorize a lifetime.

## Authority and preserved history

Accepted scope is Firstmate inbox `012.msg` and the complete read-only Opus saved-trace review at `/Users/flow/Dev/firstmate-homes/aweform/data/pymunk226-v3-trace-review/report.md`. The v3 base is exactly `abba4b8bb568ba13ccc5cc87740b87c6c2630ada`; the `48b1820..abba4b8` difference is one docs-only file. The v3 runner refuses a changed `origin/main`, another branch, an unexpected source diff, or dirty source. V1 and v2 source/protocol/results remain historical and immutable, including the v1 result SHA-256 `8937854444fb02f1e19597741db42528f7bdc476f684ed6daa4489e44bb4a522` and v2 result SHA-256 `baacf581f37806e5a81b091fe8cef7ba57ca4b5643e47b2482edae8ac40d168a`.

V3 changes only the permitted solver microstep options to `400/800`, adds a new staged runner/evaluator, repairs L1/L2 result labels, and writes to separate v3 output directories. The v2 `run_diagnostics._single_case` physics and record generation are reused unchanged, called one case at a time by the v3 wall-clock-capped orchestrator. V1/v2 runner, protocol, measured output directories, and lifetime code are not changed by this protocol. No production Aweform source, controller, learner, organism observation/reward, ADR, dependency policy, protected seed, or evidence contract is modified.

The read-only report's predictions are hypotheses only. The accepted penetration limit remains **0.001 m**, and the existing position, clearance, yaw, shaft, crossing, reset, runtime and replay gates remain unchanged. A 1–2 mm value is a failure of the original gate and may only be discussed as a fallback for future reassessment; this protocol does not make it a PASS or permit another run.

## C1 — the single frozen numerical correction

Use exactly **400 primary and 800 comparison microsteps per 0.1 s logical command**. Do not test another N or tune any value. Everything else remains the v2 candidate: C2 midpoint arc-average, contact-gated velocity refresh (no refresh after the first post-solve contact callback within the logical command), `collision_bias=0.9**100`, 0.0001 m slop, 10 iterations, persistence 3, no sleeping, zero gravity/damping 1, zero friction/restitution, same hull/mass/moment, flush static room walls, fixed post geometry, action and shaft/encoder rules, cases, starts, commands and per-step clearance sampling.

This is a test-only numerical-resolution change; it makes no hardware-fidelity claim. The Opus first-order forecast predicts sub-millimetre contact penetration and passable resolution convergence at 400/800, but its predicted outcome is not evidence. A result above 1 mm fails, even if it falls in the user's 1–2 mm fallback discussion range.

## L1/L2 evaluator corrections

- **L1 expected contact:** exactly `wall-west-turn-2`, `wall-east-turn-2`, `wall-south-turn-2`, and `wall-north-turn-2` are frozen no-contact controls. Each must have no contact event and strictly positive minimum independent clearance at both resolutions. Every other existing row in the frozen `CONTACT_FAMILIES` must report contact. All 255 rows remain; no case is dropped.
- **L2 contact-state convergence:** `contact_state_pass` is calculated only from contact-identity disagreements and the existing 0.0005 m near-boundary allowance. Per-shape minimum-clearance convergence is a separate boolean/gate; it cannot force the contact-state gate to fail. Record every disagreement and allowance.

## Frozen inventory and bounds

The unchanged corpus contains 255 cases and 797 logical commands per resolution. Full Stage 2 runs the entire corpus at 400 and 800, then one identical trace replay in a separate fresh Python process:

- Primary two-resolution corpus: `797 × (400 + 800) = 956,400` Pymunk `Space.step` calls.
- One fresh-process replay: another 956,400 calls.
- **Full total: 1,912,800 calls**, 3,188 primary-plus-replay logical commands, 1,020 case-resolution executions.

The focused Stage 1 probe uses the seven predeclared cases `wall-west-head-on` (20 commands), `wall-west-turn-0` (10), `wall-south-turn-0` (10), `wall-south-glance` (10), `corner-se` (20), `post-wall-adjacent` (20), and `post-tangent` (20): 110 logical commands at each of 400/800 combined, **132,000 calls**. The one permitted Stage-0 fixture interface test at 400 is software validation, separately declared, and is not part of scientific execution counts.

The runner checks the exact planned count before output creation/physics and each suite's completed-case count after execution. It checks the wall-clock budget between complete cases, reserves 10 seconds before starting another case, and records partial per-case progress. A cap/error leaves a one-shot `FAILED-INCOMPLETE` record; never reuse or rerun that output path.

## Stage 0 — software-only validation (no corpus, replay, or lifetime)

The frozen pytest suite may exercise pure evaluators and exactly one deterministic logical action at 400 microsteps. It must not call `run_suite`, the full v3 runner modes, either measured stage, the replay worker, or any organism/reference lifetime. The separately documented tests cover 400/800 acceptance and 401 rejection, L1 contact/no-contact cases, L2 isolation from clearance, planned-step arithmetic, early existing-output refusal, Stage-2 refusal without a passing exact-SHA Stage-1 artifact, and the single new 400-step fixture-interface action. The preexisting v2 10-step callback unit test remains; neither interface test runs the corpus or creates a science artifact.

Run Stage 0 before the result-free freeze; then commit the complete source/protocol/test freeze and confirm clean source. Stage 0 must pass before Stage 1.

## Stage 1 — focused falsifier, non-acceptance probe

Output is exclusively `experiments/pymunk_contact_prototype/results-v3/focused-probe/`. Its one-shot refusal runs before any Space construction or step. Planned count is exactly 132,000; serial hard cap is **3 minutes**. The probe checks the same per-case penetration, sampling-bound, crossing, reset, contact, position, clearance and yaw thresholds as the full contract, plus these report-specific falsifiers:

- The 19th `wall-west-head-on` command's raw sampled penetration is within ±10% of 0.0002115 m at 400 and 0.0001558 m at 800.
- All focused contact families actually contact; every per-case and 400/800 convergence limit passes.
- Step count is exact and all outputs finite.

A Stage-1 essential failure, prediction miss, falsifier, exception, or time cap means preserve the partial/complete output and **STOP**. Do not run Stage 2, retry, tune, or switch resolution. Stage 1 PASS is necessary but not sufficient for B.

## Stage 2 — full fixed-command check (only after Stage-1 PASS)

The v3 runner refuses Stage 2 unless it can read a completed Stage-1 artifact with `essential_stage1: PASS`, the exact current executable SHA and protocol SHA, the expected 132,000 step count, and the positive Stage-2 authorization flag. It runs the unchanged 255-case corpus at 400 and 800, calculates all predeclared gates, then invokes one genuine fresh process at the same frozen executable SHA to regenerate both full traces. The primary and replay canonical bytes must match exactly and process IDs must differ. Run serially with a **15-minute hard cap** for primary plus replay.

Full essential B passes only if every preserved runtime/input/time/free-space/shaft/contact/penetration/clearance/crossing/stuck/reset/inventory/400-vs-800/contact-state/fresh-process/finite gate passes. Any gate failure, prediction falsifier, mismatch, unsafe resource change, or cap means preserve all output and STOP. No other resolution, rerun, adaptive rescue, lifetime, production migration, successor, merge, or publication is authorized in this task.

No contact or full acceptance path may be inferred from Stage 1 alone. The lifetime wrapper remains out of scope and is not invoked even if B passes; any future lifetime requires separate authorization.

## Runtime and resource preflight

Use pinned Python 3.14.7, Pymunk 7.2.0 and the already frozen wheel SHA `497c4a919fc7f03882cb9796b132ab3b5fcc4c4af9ead08e9631b6a9fb2da29c`. The runner verifies runtime/pin and the exact result-free base. Immediately before Stage 1, report the committed source/protocol SHA, exact corpus/count/time budget, and fresh CPU/memory/process check. If Stage 1 passes, repeat the resource check before Stage 2; do not kill, pause, or compete with another required scientific workload. Execute at reduced priority and serially.

Suggested runtime setup:

```sh
uv sync --frozen --python 3.14.7 --group dev --group pymunk-probe
export PYMUNK_WHEEL_PATH=/private/tmp/pymunk220-wheelhouse/pymunk-7.2.0-cp314-cp314-macosx_11_0_arm64.whl
```

The exact one-shot commands are in `VALIDATION-v3.md`. No command in ordinary tests/CI/no-mistakes validation launches Stage 1, Stage 2, replay, or lifetime.
