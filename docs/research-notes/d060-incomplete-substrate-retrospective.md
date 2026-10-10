# D-060 round interior-obstacle substrate — incomplete-work retrospective

**Disposition: INCOMPLETE / NOT ACCEPTED / HISTORICAL DEVELOPMENT DIAGNOSTIC**  
**Record status:** retrospective only; no D-060 row is added to the canonical Development index.  
**Decision:** preserve the original substrate attempt and its bounded reduced diagnostic as historical exploratory work. Do not complete or rerun the original D-060 conformance under the retired direction. A distinct direct-Pymunk contact prototype is the preferred future experimental path, not an adopted simulator or production replacement.

This note distinguishes repository/GitHub facts from reported evidence and interpretation. It does not amend the frozen D-060 protocol, accept ADR-0020 implementation, make a physical-law finding, or authorize new science.

## Scope and disposition

ADR-0020 defines a proposed V0.5 round-interior-obstacle substrate boundary. Its presence does not establish D-060 implementation acceptance. The original S2-B proposal and authorization are recorded in [issue #213](https://github.com/PiFlow/aweform/issues/213); the original implementation remains the unmerged [PR #222](https://github.com/PiFlow/aweform/pull/222). The separately scoped D060-REDUCED-v1 diagnostic was authorized through [issue #223](https://github.com/PiFlow/aweform/issues/223) and preserved in [PR #224](https://github.com/PiFlow/aweform/pull/224). Both PRs remain **open and unmerged** at the time this retrospective was prepared.

Flow's archival decision in [issue #227](https://github.com/PiFlow/aweform/issues/227) is to preserve these results as incomplete exploratory evidence, discontinue work toward full conformance, and later close #222 and #224 without merging either implementation branch, only after this retrospective has been reviewed and merged and the original refs are preserved. No D-060 measured rerun is authorized by that decision. This disposition is not a finding that the custom contact law is physically invalid or that any particular check demonstrated a physical-law failure.

ADR-0020's accepted status history and any separate governance reconciliation are not rewritten here. The canonical committed D-stage ledger remains [`development/INDEX.md`](../../development/INDEX.md); this retrospective deliberately adds no D-060 row. No D-060 production simulator swap, organism behavior/sensor change, or EXP claim follows from this record.

## Original substrate PR #222

### Immutable identity and retained materials

- Original PR head: [`039d0a4810aaffb6671f968a82fb6850b1596659`](https://github.com/PiFlow/aweform/commit/039d0a4810aaffb6671f968a82fb6850b1596659).
- Original PR base: [`ce4f4943f6d8fcd84c723a151b15178f3856e098`](https://github.com/PiFlow/aweform/commit/ce4f4943f6d8fcd84c723a151b15178f3856e098).
- Current archival branch ref observed for the original head: [`codex/d060-v05-round-interior-obstacle-substrate`](https://github.com/PiFlow/aweform/tree/codex/d060-v05-round-interior-obstacle-substrate). The GitHub PR head and branch resolved to `039d0a4…` during this work; keep the branch and PR history intact.
- The PR introduced the D-060 substrate and evaluator oracle, tests, Markdown/JSON conformance record, an index entry, and scoped lint/type-check configuration. The source and artifact remain recoverable from the commit and PR history; nothing from this retrospective cherry-picks or merges that implementation.

The original JSON artifact at the pinned head is read-verifiably **132,389 bytes**, SHA-256 `6c16982186dd9fd588012f1c0a552ef001e5acfbc34a0a923b194ae64c76479f`. The three relevant source/test blobs at that head have SHA-256:

| File | SHA-256 |
|---|---|
| `src/aweform/d060.py` | `6391de1f383968a6369870dc54665a79defacd374c8a418707ba768ea7e7cf98` |
| `src/aweform/d060_oracle.py` | `ea50718f855e2e934177e2889dd5ef520020fee2953e6a956229dd1b7c0684c2` |
| `tests/test_d060.py` | `12761052e15419eb9d27fb05404c35bac066798478d4c71569cdf986cc6f8773` |

The old result record identifies executed source `beb9012b0fa604fef4dc7b126a171f9a8baf8ee0`. A retained operational receipt reports official/archive exit 0 and byte identity for the same artifact, but the original raw regenerated archive/output is no longer available for independent re-comparison. Therefore the historical artifact hash and tracked source hashes are verifiable from Git; the old archive comparison is a recorded receipt, not a fresh independent check in this retrospective.

### Why the original conformance was incomplete

The independent GPT-5.6 Sol review of exact PR head `039d0a4…` recorded **CHANGES REQUIRED**, not PASS ([PR #222 review comment](https://github.com/PiFlow/aweform/pull/222#issuecomment-6078810840)). Its findings were specific omissions against the already-frozen H.1–H.8 contract:

1. **H.2(c) coverage:** the required interior-grid low-energy arm at `1065.6 J` was missing; the separately specified inherited D-058 64-command schedule was not demonstrated with the required per-step reconstruction coverage.
2. **H.4 room legality:** the endpoint check used production-derived extents rather than an independent four-rotated-corner room check with inherited `tau(3.0)`.
3. **Strict typing:** a broad `mypy ignore_errors = true` override masked 190 diagnostics in the new original D-060 modules without authorization.
4. **Lint scope:** Ruff exceptions were broader per file than the observed errors warranted.

The original report's `D060_SUBSTRATE_CONFORMANT` label and its successful reported artifact regeneration do not resolve those omissions. Green checks also do not establish the missing coverage, and the type-check suppression qualifies the original green result. The correct disposition is **full H.1–H.8 conformance not achieved**, not a claim that a completed check failed or that the physical law itself failed.

## Reduced diagnostic PR #224

### Scope, execution and exact checkpoints

The reduced diagnostic was a separate evaluator-only adapter and record, stacked on the unaccepted #222 head; it did not change the original substrate, oracle, tests, artifact, or full-conformance protocol. Its fixed selection was deliberately targeted, not representative:

- 19 of 26,752 ray sequences (204 transitions), plus all 54 pocket sequences (1,728 transitions);
- 54 reset probes;
- 800 H.2(c) one-step candidates and a separately identified 64-command schedule;
- at the corrected intermediate review checkpoint, 718/718 eligible H.2(b) fresh-control comparisons and an explicitly reported low-energy split.

At checkpoint `1bee68a70c5b19433acc8a090db0fc6119ed75bc` (record commit; frozen executable/protocol `8d620748f52db64e52bab4f8eb96fed05d0cfc20`), the worker-reported official/archive outputs were byte-identical at 2,751,474 bytes, SHA-256 `2f9bce96c2bd8e5b73925851b74a53599affdf716db9fab5fd00f25e1468c7b8`. The earlier manager QA at that exact checkpoint passed, but Sol's independent exact-head review required changes ([PR #224 comment](https://github.com/PiFlow/aweform/pull/224#issuecomment-6083757189)): explicit executed push-out/resolution witnesses for sign-disagreement cases, context-complete H.2 mismatch STOP diagnostics, and clearer direct accounting of D-058 reconstruction checks. These are historical review outcomes for that checkpoint, not the final one.

The corrections were completed and executed before Flow's stop-work direction. The final PR head is [`9dae69a3c08022516849ce22ff649779d412d7e6`](https://github.com/PiFlow/aweform/commit/9dae69a3c08022516849ce22ff649779d412d7e6), with frozen executable [`29ced9f52d3bafb38886a76ad232e00f10388b81`](https://github.com/PiFlow/aweform/commit/29ced9f52d3bafb38886a76ad232e00f10388b81) and final record commit `9dae69a…`. At this final checkpoint the worker-reported preflight and one official/archive pair completed; the outputs were byte-identical, 2,764,472 bytes, SHA-256 `f45d5ca93a20e511c39caf82f5c820b29472d944a0bb2ed61c7236c4ed61ab1e`. The record reports the selected-case counts: H.2(a) 577 comparisons/12 exclusions; H.2(b) 718 comparisons; H.2(c) 750 attempted/747 compared, with 50 reset-excluded and 3 oracle-ineligible; 11/16 low-energy starts accepted and 107/160 low-energy candidates compared; 64/64 schedule comparisons; 2,106 direct D-058 reconstruction checks; 630 obstacle steps × 3,600 directions; 2,743 endpoint reconstructions. These counts describe the selected diagnostic only.

Claude Opus 5.5's attributable manager-QA report records **PASS** for exact final head `9dae69a…` (manager QA only); its provenance and findings are summarized in the [#224 review handoff](https://github.com/PiFlow/aweform/pull/224). The detailed report and raw run files were retained in the worker's local evidence area, not committed as public repository files. Both exact-head CI jobs were reported green. The earlier Sol CHANGES REQUIRED review at `1bee68a…` remains valid historical provenance for that older head; **no independent Sol PASS is recorded for `9dae69a…`**. The manager-QA report distinguishes worker-reported execution receipts from its own read-only checks. Neither manager QA nor CI upgrades this reduced diagnostic to full D-060 conformance or acceptance.

The current PR branch ref observed for final head `9dae69a…` is [`fm/d060-reduced-v1`](https://github.com/PiFlow/aweform/tree/fm/d060-reduced-v1). The frozen executable is an ancestor of that head and remains addressable by its exact commit link. Both PR branches and their GitHub timelines/check histories are to remain available; no tag was necessary because the existing refs were confirmed retrievable. Detailed raw outputs and receipts referenced during QA are not in this public repository, so their byte-level claims here remain attributed worker/manager-QA reports rather than independently reproducible public artifacts.

### Limits of the reduced result

The selected ray/pocket transitions are 1,932 of 235,200, or 0.8214%, and 26,733 ray sequences were omitted. This fraction is a coverage description, not a universal failure-detection probability or runtime estimate. Historical sign/geometry cases are regression probes selected using prior artifacts, not untouched confirmatory data. The reduced output cannot establish omitted H.1–H.8 coverage, H.7 for the original full matrix, substrate-wide conformance, acceptance, ADR completion, or any behavioral result. No D-060 claim should be inferred from its result label `D060_REDUCED_DIAGNOSTIC_COMPLETE`.

## Lessons and transfer

**Observed:** the custom endpoint-projection path required extensive evaluator work to independently check geometry, oracle sign conventions, near-zero sign disagreements, executed push-out witnesses, reset identity, case context, and source/archive provenance. Review surfaced omissions in both original full-conformance implementation and the bounded adapter. The record trail shows that apparent completion of a long deterministic run is not equivalent to satisfying every frozen check or retaining independently inspectable evidence.

**Interpretation:** the clearest project-level cost demonstrated here is engineering and provenance burden for a custom contact implementation and its audit. This is not evidence that the contact law is invalid, that the numerical disagreements imply a physical defect, or that a different simulator is more physically faithful.

**Transfer:** the separately completed [Pymunk empty-space diagnostic PR #225](https://github.com/PiFlow/aweform/pull/225), merged at [`1499dc4665389feb7048509d5c387bf99aaf3079`](https://github.com/PiFlow/aweform/commit/1499dc4665389feb7048509d5c387bf99aaf3079), is empty-space-only calibration evidence. It does not establish obstacle contact, hardware fidelity, organism behavior, or production-backend readiness. A direct Pymunk contact prototype is the preferred **distinct experiment** in issue [#226](https://github.com/PiFlow/aweform/issues/226), not an adopted substrate. A dynamic solver and the original endpoint-projection law implement different physics; baseline equivalence cannot be assumed. Any future comparison needs its own frozen scope and review, and this note authorizes none of that work.

## Historical reference map

- Original proposal/authorization: [#213](https://github.com/PiFlow/aweform/issues/213); original implementation PR [#222](https://github.com/PiFlow/aweform/pull/222); exact head [`039d0a4…`](https://github.com/PiFlow/aweform/commit/039d0a4810aaffb6671f968a82fb6850b1596659); exact base [`ce4f494…`](https://github.com/PiFlow/aweform/commit/ce4f4943f6d8fcd84c723a151b15178f3856e098).
- Original independent review: [#222 CHANGES REQUIRED](https://github.com/PiFlow/aweform/pull/222#issuecomment-6078810840).
- Reduced authorization: [#223](https://github.com/PiFlow/aweform/issues/223); reduced PR [#224](https://github.com/PiFlow/aweform/pull/224); prior review checkpoint [`1bee68a…`](https://github.com/PiFlow/aweform/commit/1bee68a70c5b19433acc8a090db0fc6119ed75bc); frozen source [`8d62074…`](https://github.com/PiFlow/aweform/commit/8d620748f52db64e52bab4f8eb96fed05d0cfc20); final frozen executable [`29ced9f…`](https://github.com/PiFlow/aweform/commit/29ced9f52d3bafb38886a76ad232e00f10388b81); final record head [`9dae69a…`](https://github.com/PiFlow/aweform/commit/9dae69a3c08022516849ce22ff649779d412d7e6).
- Reduced-review chronology: [Sol CHANGES REQUIRED at `1bee68a…`](https://github.com/PiFlow/aweform/pull/224#issuecomment-6083757189); final attributable manager QA report linked above; no Sol PASS on `9dae69a…`.
- Founder archival disposition and closure order: [#227](https://github.com/PiFlow/aweform/issues/227) and [founder routing in #197](https://github.com/PiFlow/aweform/issues/197#issuecomment-6097534147).
- Empty-space-only Pymunk result: [#225](https://github.com/PiFlow/aweform/pull/225), merge commit [`1499dc4…`](https://github.com/PiFlow/aweform/commit/1499dc4665389feb7048509d5c387bf99aaf3079); preferred separate contact experiment [#226](https://github.com/PiFlow/aweform/issues/226).

**Preservation rule:** keep the #222 and #224 PRs, original branch refs, exact commits, artifacts, reviews, CI history, and historical evidence intact. Do not merge either implementation branch into `main`, move or overwrite a ref, delete a branch, replace an old result, or convert this retrospective into a D-060 acceptance record. After this note is reviewed and merged and ref retrievability is rechecked, the authorized closeout may close #222 and #224 **unmerged** with links back here and to the exact historical heads.
