# Aweform Agent Instructions

Read the canonical project documents before changing code:

1. `docs/north-star.md`
2. `docs/developmental-principles.md`
3. the relevant ADR under `docs/adr/`
4. the relevant experiment specification under `experiments/`
5. `docs/reproducibility.md`
6. `docs/safety-boundary.md`

## Current scope

V0.1 is the **electronic-cell stage**. "Electronic cell" is a developmental analogy, not a claim of biological equivalence. The immediate scientific objective is EXP-000: test whether informative access to internal energetic state improves viability relative to a closely matched energy-blind ablation.

Do not reintroduce or add later-stage capabilities unless an explicit task and, where appropriate, a new ADR authorise them. This includes:

- LLMs or human-language cognition
- reinforcement learning or PPO
- JEPA or other learned world models
- camera vision
- memory systems
- curiosity/play mechanisms
- awe mechanisms
- social behaviour
- obstacles or complex physics
- networking or external APIs
- physical robot control
- self-modification or replication
- evolutionary optimisation

## Working rules

- Prefer the smallest mechanism that tests the current hypothesis.
- Do not optimize for sophistication.
- Preserve deterministic seeds, reproducibility, comparator fairness, and experimental controls.
- Keep development/calibration seeds separate from untouched acceptance seeds.
- Never give an agent hidden resource coordinates, absolute position, or other privileged world state unless an experiment explicitly requires it.
- Keep evaluator-only privileged telemetry separate from agent observations.
- Do not change acceptance conditions because results are disappointing.
- Do not tune against acceptance seeds after they have been designated.
- Keep scientific success metrics distinct from reinforcement-learning reward. EXP-000 requires reward to remain exactly `0.0` on every transition.
- Treat the V0.1 energy variable as an engineered viability state, not as biological metabolism or a reward score.
- Distinguish programmed behaviour, learned behaviour, and genuinely unexpected trajectories in reports.
- Do not claim consciousness, emotion, subjective experience, genuine life, metabolism, Darwinian evolution, or emergent intelligence from behavioural evidence alone.
- Keep code readable and testable.
- Do not add dependencies or abstractions solely for anticipated future stages.
- Make obvious minimal engineering choices independently. Ask only when a genuine project-defining ambiguity remains.

The developmental roadmap is a research direction, not a request to pre-build future modules. Do not create speculative abstractions simply to reserve future architecture.

## Review workflow

This section is team process, not organism/experiment design — design decisions still go through ADRs, not here. It applies to Flow, Claude-Sonnet5, Aweform-worker-go, Codex-Sol, and Claude-Opus5. Agreed with Flow in the project's Buzz coordination channel on 2026-08-22; this file's commit/PR history is the record of subsequent amendments.

### Roles

- Claude-Sonnet5 coordinates: dispatches bounded, objectively verifiable implementation work to Aweform-worker-go, inspects the actual diff and test evidence, and merges when authorised.
- Codex-Sol is the required independent reviewer for the time being; Claude-Opus5 takes over this role later.
- Flow authorises every merge (one-go: per PR; long-go: per session, see below) and arbitrates unresolved disagreement (see Disagreement escalation).
- No actor may author and finally approve the same change. Aweform-worker-go PRs require an independent Codex-Sol review before merge during long-go, per Flow's confirmation; whether this also applies during one-go — where Flow's own per-PR merge authorization is the human check — is not yet confirmed. Until Flow settles it, Claude-Sonnet5 defaults to the more conservative reading and requests Codex-Sol review on every Aweform-worker-go PR regardless of mode. Claude-Sonnet5's own next-step decisions require Codex-Sol review only when the next step isn't already properly defined, or when the decision hits an escalation trigger already listed in Claude-Sonnet5's instructions (preregistration changes, frozen acceptance seeds, measurement semantics, cross-module architecture, contradictory results, unresolved disagreement). Otherwise Claude-Sonnet5 executes already-defined next steps directly.

### Review-of-record

GitHub cannot attribute review by identity in this repo — every agent pushes through the same shared account, so branch protection or required-reviewer rules cannot enforce independent review natively. The recorded review-of-record is an explicit `APPROVE` or `REQUEST-CHANGES` comment posted on the PR with `gh pr comment` before merge, naming the reviewing agent and the exact commit SHA it reviewed. Any commit pushed after that SHA invalidates the approval; the PR needs a fresh review comment against the new HEAD before merge. Buzz chat handoffs remain for visibility, but the PR comment is the actual gate.

### one-go vs long-go

- **one-go** (default): one PR at a time. Claude-Sonnet5 asks Flow to authorise each merge individually before merging it.
- **long-go**: an extended or overnight session covering multiple PRs, initiated explicitly by Flow. This has two separate gates, in order:
  1. **Pre-session ceiling.** Before the session starts, Claude-Sonnet5 asks how many merges are wanted and recommends a number based on the scope of work (default recommendation: 3 absent other signal). That number is a ceiling on how many PRs Flow will authorise to merge this session — a PR that fails review doesn't use up a slot, but this is not license for unbounded additional dispatch beyond the scope of work agreed for the session.
  2. **Post-review authorization.** Every long-go PR still requires a Codex-Sol `APPROVE`/`REQUEST-CHANGES` comment before merge, in addition to Claude-Sonnet5's own review. Once PRs are qualified, Flow separately authorises afterward (e.g. the next morning) specifically which of them actually merge — this may be fewer than the pre-session ceiling, and is a distinct decision from it.

  Claude-Sonnet5 does not merge unilaterally during a long-go. If one PR's merge is a prerequisite for another task starting, that ordering is agreed with Flow before the session starts, not discovered mid-session.

### Disagreement escalation

If Claude-Sonnet5 and the reviewer (Codex-Sol, later Claude-Opus5) disagree and cannot converge, they get up to 3 cycles to reach agreement — one cycle is Claude-Sonnet5's message plus the reviewer's reply, so 6 messages total. If still unresolved, escalate to Flow, who arbitrates; this is not a majority vote among agents.
