# ADR 0013 — Model-Agnostic Independent Review Governance

**Status:** Accepted by Flow as a governance transition.

**Scope:** Governance only. This ADR changes reviewer selection and records the
review provenance for ADR 0012. It does not change simulator dynamics,
observations, learning mechanisms, safety permissions, evidence results, or V0.4
physical parameters.

## Context

Aweform's developmental-reset governance originally named two specific models
for formal evidence and durable-boundary review: GPT-5.6 Sol first and Claude
Opus 5 final. That rule provided useful separation of implementation and review,
but it also made project governance depend on permanent availability of one
vendor/model.

Flow has decided to discontinue use of Claude Opus 5. The scientific intent of
the rule is independence, adversarial review, exact-SHA accountability, and
reviewer diversity — not permanent dependence on a named commercial model.

PR #76 / ADR 0012 exposed that mismatch. Exact candidate HEAD
`faa59eeedaa5e0b571296138d9efc8fe96eeb455` received an independent GPT-5.6 Sol
PASS recorded on the PR, plus independent read-only PASS reviews from Kimi K3
and Grok 4.6 performed outside GitHub and later archived on the PR. No Claude
Opus 5 review occurred. PR #76 was merged by Flow as
`4c88d449a3c9e2a32503875d77f57d9736a98f93`.

This ADR does not pretend otherwise. It explicitly replaces the named-model
requirement with a role-based independent-review rule and ratifies ADR 0012 on
the actual review record that exists.

## Decision

### A. Formal review requires two independent reviewers

For evidence-lane EXP claims/executions, new or changed durable architecture,
sensory/plasticity, information, or safety boundaries, and modifications to
frozen evidence or reserved-seed contracts, at least **two independent
high-capability reviewers** must PASS the exact current candidate HEAD before
Flow-authorized merge.

### B. Reviewers are designated by Flow, not permanently named

No particular vendor or model is permanently required.

For each formal candidate, Flow designates:

1. a **first independent reviewer**; and
2. a **second independent reviewer**.

The current default first reviewer may be GPT-5.6 Sol, but this is an operating
choice rather than a durable vendor dependency. The second reviewer should,
whenever practical, be from a different model family/provider from the first to
increase error diversity. Models such as Kimi K3, Grok 4.6, GLM-5.3, future
Claude models, or later frontier models may serve when Flow judges them suitable
for the task.

Flow may request additional advisory reviews for unusually consequential
changes, but two qualifying PASSes remain the minimum formal gate unless a
specific future protocol requires more.

### C. Independence requirements

A qualifying reviewer must independently inspect the actual repository evidence
needed for the question rather than merely accepting an implementation summary
or another reviewer's conclusion.

The implementation actor cannot count its own work as independent approval.
Two labels for the same implementation/review agent do not create independence.
Whenever practical, the two formal reviewers should be different model
families/providers or otherwise materially independent reasoning instances.

### D. Exact-HEAD review-of-record

Each qualifying formal review must identify:

- reviewer/model identity;
- `PASS` or `REQUEST CHANGES`;
- exact reviewed HEAD SHA;
- enough substantive reasoning to establish what was actually checked.

The review of record must be archived on the relevant GitHub PR. If an external
terminal model cannot post to GitHub directly, Flow or a maintainer may archive
a faithful transcript or concise provenance-preserving summary as a PR comment.
That comment must clearly state that the external model did not post it
directly; no maintainer may impersonate a reviewer.

Only a `PASS` against the exact current HEAD qualifies. Any later commit
invalidates prior PASSes for that candidate and requires review of the new HEAD.

### E. Flow remains merge authority

Flow alone authorizes merges. Formal review PASSes establish the review gate;
they do not merge or authorize implementation by themselves.

### F. Repository evidence outranks summaries

Repository source, exact commits, PR patches, tests, artifacts, CI, and frozen
protocols outrank worker or reviewer summaries when they conflict.

### G. PR #76 / ADR 0012 ratification

For the historical transition created by PR #76, Flow explicitly accepts the
following exact-HEAD review set for
`faa59eeedaa5e0b571296138d9efc8fe96eeb455`:

- GPT-5.6 Sol — PASS — recorded on PR #76;
- Kimi K3 — PASS — external read-only review supplied by Flow and archived on
  PR #76;
- Grok 4.6 — PASS — external read-only review supplied by Flow and archived on
  PR #76.

Kimi K3 is sufficient as the second qualifying reviewer under this new
model-agnostic rule; the Grok 4.6 PASS is additional corroboration. No Claude
Opus 5 review is claimed to have occurred.

Flow's merge of PR #76 is therefore ratified as the accepted ADR 0012 V0.4
boundary under this amended governance. This ratification changes only review
provenance/governance; it does not alter the technical text or physical boundary
of ADR 0012.

## Consequences

- Formal review remains dual, independent, adversarial, and exact-SHA-specific.
- Aweform is no longer blocked by permanent dependence on Claude Opus 5 or any
  other named commercial model.
- Reviewer diversity is preserved as a scientific objective rather than a
  vendor lock-in rule.
- External terminal reviews may count when their identity, verdict, exact HEAD,
  and provenance are faithfully archived on the PR.
- A human cannot simply speak as a model or fabricate a review; the qualifying
  review must actually have been produced by the stated reviewer.
- PR #76's actual review history is preserved honestly rather than rewritten.
