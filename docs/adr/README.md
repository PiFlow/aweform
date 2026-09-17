# Architecture Decision Records

This directory contains Aweform's durable architecture, information-boundary, plasticity, physicalization, and governance decisions.

An accepted ADR is a durable decision record, not a progress log. Current implementation status belongs in [`development/INDEX.md`](../../development/INDEX.md), the research roadmap, and the exact current authorization issue/PR.

## Index

| ADR | Durable decision |
|---|---|
| [0001](0001-v0.1-electronic-cell.md) | V0.1 electronic-cell scope |
| [0002](0002-agent-environment-information-boundary.md) | Agent/environment information boundary |
| [0003](0003-exp-000-body-observation-action-contract.md) | EXP-000 body / observation / action contract |
| [0004](0004-exp-000-transparent-controller-contract.md) | EXP-000 transparent controller contract |
| [0005](0005-exp-000-development-runner-and-recording.md) | EXP-000 development runner and recording |
| [0006](0006-exp-000-development-visualization.md) | EXP-000 development visualization |
| [0007](0007-exp-000-multi-source-resource-field.md) | EXP-000 multi-source resource field |
| [0008](0008-exp-003-localized-charging-interface.md) | EXP-003 localized charging interface |
| [0009](0009-v0.2-bounded-observation-history-state.md) | V0.2 bounded observation-history state |
| [0010](0010-v0.3-lifetime-plasticity.md) | V0.3 lifetime plasticity / sensory-plasticity closure |
| [0011](0011-v0.3-thermal-interoception-boundary.md) | V0.3 thermal interoception boundary |
| [0012](0012-v0.4-minimal-physical-energy-thermal-boundary.md) | V0.4 minimal physical energy / thermal boundary |
| [0013](0013-model-agnostic-independent-review-governance.md) | Model-agnostic independent-review governance |
| [0014](0014-v0.4-thermal-operating-and-failure-thresholds.md) | V0.4 thermal operating and failure thresholds |
| [0015](0015-v0.4-finite-body-dual-contact-docking-boundary.md) | V0.4 finite-body dual-contact docking boundary |

The ADR file itself is authoritative for its exact status, scope, supersession/amendment semantics, and review provenance.

## Supporting registries are not ADR numbers

The historical file `0009-bohs-registry.md` was originally titled "ADR 0009 — BOHS Registry" even though ADR 0009 is actually [`0009-v0.2-bounded-observation-history-state.md`](0009-v0.2-bounded-observation-history-state.md).

To remove that ambiguity without renumbering historical ADRs or breaking old links:

- the canonical BOHS supporting registry now lives at [`../registries/bohs.md`](../registries/bohs.md);
- `0009-bohs-registry.md` remains only as a compatibility pointer.

Do not assign an ADR number to a registry, manifest, evidence table, or implementation inventory unless it is itself an architecture decision record.

## Adding or amending an ADR

Use an ADR only for a durable project boundary or decision that should outlive one development experiment. Ordinary D-lane mechanism choices inside an already accepted boundary do not need a new ADR merely because they are scientifically important.

New or changed durable architecture, sensory/plasticity, information, safety, frozen-evidence, or reserved-seed boundaries remain subject to `AGENTS.md` and ADR 0013 review governance.
