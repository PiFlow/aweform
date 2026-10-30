# Aweform Familiar — Investigation B: H2 Neutral-Cue Shadow-Prediction and Capacity/Sufficiency Protocol

**Status:** DRAFT RESEARCH / PROSPECTIVE, **NOT FROZEN OR AUTHORISED TO EXECUTE**. No seed reservation or empirical result is claimed.  
**Founder authorization to investigate and draft:** [Issue #243](https://github.com/PiFlow/aweform/issues/243#issuecomment-6513908796), 30 Oct 2026.  
**Audited reference baseline:** `main` `b90dcace58ec42f7245c922b4ad1c94c12db399b`.  
**Companion:** [Investigation A — external-agent boundary](2026-10-30-external-agent-boundary-investigation.md). Active First Mate simulation [#240](https://github.com/PiFlow/aweform/issues/240) and design [#242](https://github.com/PiFlow/aweform/issues/242) remain unaffected.

## Claim, exclusions and evidentiary basis

**[SOURCE-DERIVED RESEARCH PROPOSAL]** The founder-supplied [Familiar Chaptered Edition, §5–7](https://github.com/PiFlow/aweform/blob/5338c2890ccbbe2b05e08c01de804190240ce7df/research/familiar/2026-10-30-shared-evidence/01-aweform-familiar-deep-research-chaptered.md) proposes **H2: Recurring External Context to Intervention Prediction**: Can a bounded learner use an *organism-visible, recurring, nonsemantic cue* to predict a later, externally caused, **nonessential** consequence beyond what it can already predict from its own state/action, time, schedule or simple event frequency? An external-causation observability audit precedes the first claim-bearing H2 trial.

This is **not** human-partner identification, emotion, trust, attachment, language understanding, self-awareness, agency, a beneficial learned social policy or autonomous energy maintenance. No real humans, microphones, cameras, LLM mind, powered egg, direct physical hardware, human-subject relationship test, network access or organistic use of hidden evaluator labels belongs in the first programme. The assistant/Hermes is **not** an experimental partner.

**[VERIFIED REPO EVIDENCE]** V0.5 currently has an eight-channel organism observation and differential-drive action under [ADR 0017](../../docs/adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md); [ADR 0010](../../docs/adr/0010-v0.3-lifetime-plasticity.md) permits bounded within-lifetime learned state with exact causal provenance; [ADR 0018](../../docs/adr/0018-three-layer-developmental-architecture-and-innate-viability-floor.md) protects the constitutive Level-1 survival floor. [D-046](../../development/D-046-v05-calibration-shadow-consequence-learning.md) and [D-048](../../development/D-048-v05-extended-exposure-shadow-learning-curve.md) are relevant **shadow** predictors: D-048's full 528-weight, 66-feature quadratic map predicts one-step outcomes with mixed channel discrimination; retained learning does **not** influence actions. Neither validates a multi-step, delayed H2 cue→temperature prediction. [`development/INDEX.md`](../../development/INDEX.md) and the [Development/Evidence workflow](../../docs/development-evidence-workflow.md) remain the authority on result classes. D-061 is currently an unmerged [PR #237](https://github.com/PiFlow/aweform/pull/237), not evidence of accepted H2 capacity.

## A. Proposed minimal environment and lawful interface — design only

**[DESIGN HYPOTHESIS]** Use a strictly bounded, simulated 2D ecology *independent* of #240's obstruction and MuJoCo/Pymunk work. Keep an approved Level-1 viability mechanism and lawful energy/thermal bookkeeping; avoid making the question depend on docking or wall-contact success.

- **External cue:** one current nonsemantic binary/intensity signal `c_t` that sometimes recurs. It carries no `person`, `care`, `social`, `teacher`, ID, phase, countdown or intervention-flag semantics. An organism-visible cue channel is **not yet permitted**: its addition requires review of the sensory/information boundary before implementing it.
- **External process:** after a cue, it may cause a *small, bounded cooling pulse* with a prospectively declared probability and variable delay. The thermal perturbation must remain nonessential to viability and cannot change the organism's energy-return/docking controller or reward. It is a physical world process, not a social partner.
- **Consequence:** a later lawful organism temperature observation and its realised change. No learner input of cooling-on truth, intervention source, `time_to_cooling`, future action or evaluator condition label.
- **Control and learning:** a **shadow-only** predictor consumes permitted past/current observations and actual executed actions, updates *only after observed consequences*, and logs predictions for later evaluation. Every candidate's learner output has **zero causal effect** on organism wheel actions, Level-1 arbitration, temperature/cooling schedules, RNG or termination.
- **Time and dynamics:** preserve the existing 0.1 s command interval if the existing V0.5 substrate is used. Introduce no numerical horizons/delays as approved parameters here. A prospective protocol must fix delay distribution, sampling and cooling magnitude *before* measuring candidate model performance.
- **Environment source identity:** evaluator records whether cooling came from the scheduled environmental process; the organism receives no such label. Human/assistant-generated events are excluded from H2.

**[STOP]** If lawful observations cannot resolve the cue and its later effect without exposing an evaluator label or direct 'the intervention has arrived' teacher, do not proceed to H2 with a patched privileged channel. Audit observability or choose a different lawful experiment.

## B. First investigation: observability and confound audit (pre-experiment)

Before proposing a predictor or freezing H2, a separately authorised evaluator-only audit should answer:

1. **Signal visibility:** Is `c_t` distinguishable from ordinary sensor noise and other available signals; is intervention-induced `Δtemperature` distinguishable from unchanged thermoregulation, movement/actuator heat and charging heat using *lawful current/past data*?
2. **Delay support:** At the proposed sampling interval and pulse size, do lawful histories contain enough temporal information at the specified delay to make discrimination **possible**, rather than inferring an outcome solely from evaluator truth?
3. **Schedule independence:** Can cue/intervention relationships be balanced for elapsed time, absolute/relative position in lifetime, base temperature/energy, charging state, existing wheel actions and calendar-like periodicity?
4. **Negative examples:** Are there enough cue-without-cooling, cooling-without-cue and variable-delay cases to reject a trivial 'always cool after cue' or 'predict last step' model? Are cue/intervention marginal rates matched across controls?
5. **Viability neutrality:** Could the organism survive the full fixed horizon without any cooling pulse under every proposed condition, within declared margins? No deliberately forced near-death reliance or human rescue.
6. **Channel effect:** Is a dedicated cue receptor necessary? An evaluator-only sufficiency audit may compare hypothetical sensory alternatives but cannot add a receptor to the organism or leak privileged truth.

**Evidence output (future only):** observation sufficiency matrix, counts by cue/outcome/delay/temperature/energy/action strata, channel signal-to-baseline diagnostics, negative-control balance, identical causal-path hash with diagnostic ON/OFF. A failed sufficiency audit is a valuable **stop** result, not permission to engineer a richer learner.

## C. Predictor-capacity investigation (not a model-selection result)

**[VERIFIED LIMITATION]** A one-step action-conditioned predictor such as D-046's quadratic map has no automatic access to a past cue beyond its actual declared input/state. A cue that vanishes before a delayed cooling pulse **cannot be assumed representable** by simply appending the current cue to an otherwise memoryless one-step feature map.

| Candidate to audit | Allowed hypothesis if separately authorised | What it cannot prove |
|---|---|---|
| No-learning constant/zero-change | Baseline thermal forecast without learned cue association | Sociality or cue-specific knowledge |
| Current organism state and action only | Physical/state-only predictions including temperature, energy, charging and wheel use | Benefit of external cue over state/history |
| Clock/time-only or event-rate model (analysis comparator) | Whether schedule, cycle position or marginals predict temperature | Causal cue learning; **never pass evaluator clock as organism input** |
| D-046-like lawful one-step quadratic features | Whether contemporaneous cue+state predicts *immediate* lawful change | Delayed contingencies after cue disappearance |
| Same model with bounded lagged lawful cue/state history | Whether a minimal finite delay buffer captures future cooling | General recurrent memory or human relationship |
| Compact learned trace/recurrent state, **only if lag buffers fail prospectively** | Longer delay/uncertainty at lower bounded state cost | Need for large world model or LLM cognition |
| Frozen learned model or weights-randomised control | Whether actual within-lifetime updates matter | Learned benefit over the strongest non-learning rival |

Start with the smallest faithful model. **Do not** introduce curiosity, RL/PPO, JEPA, large models, an autobiographical/partner memory store, agent identity or learned behavioural authority. Specify the entire retained causal state (feature/history buffer, predictor parameters, optimiser/normalisation, RNG, update timing, reset policy) and its legitimate inputs before any actual Development implementation.

**Capacity question:** Given predeclared cue duration and delay support, what maximum history span `k` is required for a lawful representation to preserve cue information until prediction time? This is a design calculation/observability test, not permission to assume `k` or tune it on held-out data. Compare resource cost and diagnostic model fit on **development-only** material when separately authorised, freeze before untouched evidence.

## D. Candidate comparisons and counterfactual discipline

The following are **protocol candidates, not executed arms or accepted thresholds**.

| Condition | What is preserved | What is disrupted / tested |
|---|---|---|
| **H2 contingent** | Cue and cooling rates fixed; cue precedes probabilistic delayed cooling | Hypothesised learnable cue→consequence conditional relation |
| **Shuffled pairing** | Cue/intervention marginal counts, eligible thermal contexts and time-bin composition matched | Break individual cue→cooling pairing without changing raw frequency |
| **Noncontingent cooling** | Cooling timing/intensity distribution and occupancy matched | Cooling independent of cue given balancing variables |
| **Cue-only** | Same cue time sequence and base environment | No cooling pulse; detect cue-only artifacts/shortcut |
| **Frozen/no-update twin** | Identical initial predictor and feature set, same observation stream where feasible | Removing online plastic updates |
| **State-only model** | Organism-visible temperature, energy, charging state, actions and lawful history | Exclude cue contribution |
| **Time-only / frequency-only analytic rival** | Same future task and evaluation split | Predict from elapsed time/phase or marginal event frequencies, **offline only** |
| **Zero-change / physical baseline** | Same thermodynamics and realised action history | Test whether observed temperature change is already nearly deterministic |
| **Agent-yoked / donor-yoked** | Recipient lifetime retains its own lawful state/action process; use a donor-derived cue/intervention schedule from a **different independent lifetime/block**, with prespecified lag/phase alignment and balanced marginals | Break recipient cue–intervention contingency while controlling intervention exposure; **reject the control if donor/recipient schedules remain aligned or induce new thermal confounds** |

**Yoking detail:** Before execution, specify which donor schedule is drawn from which independently seeded episode, how event times map to the recipient's local intervals, what happens when viability/temperature constraints forbid an event, and how rejected pulses enter the analysis. A donor schedule paired with its own unchanged cue schedule is **not** a decontaminating control. A simple shuffled schedule may already answer the question; retain agent-yoked only if it adds identifiable independent leverage.

**Leakage traps and matched conditions:** Don't let `cue_t` become a disguised step index, an always-on countdown, a direct indicator of a cooling pulse already happening, a code-level future outcome or a cross-arm unique initialization signal. Do not leak RNG seed identity or held-out branch truth. Baseline action dynamics and Level-1 conditions must be matched where possible; if intervention changes organism state and thereby its subsequent environment, distinguish direct consequence attribution from downstream trajectory divergence. Do not equate branch outcomes or evaluator diagnostics with learner experience. An evaluator with true pulse state can compute metrics but may not write it into learner features/targets.

## E. Proposed preregisterable H2 readout — *not yet frozen*

**Primary question:** On **untouched, independently reserved future evidence material**, does adding learned, lawful cue history reduce *prospective* error about **future lawful temperature change** at predeclared horizons beyond the **strongest matched baseline** (state/action history, appropriate time/frequency, frozen/nonlearning, shuffled, zero-change/physical dynamics)?

- **Primary endpoint candidate:** difference in held-out predictive loss on `Δtemperature` at fixed future horizon(s), before the consequence has occurred. Choose one primary loss (e.g. MAE/MSE), horizon and prespecified practically meaningful effect margin *before any holdout*. Also examine calibration of estimated cooling probability **only if probability is genuinely learned and the cooling event is defined by lawful observation, not a privileged teacher label**.
- **Secondary/read-only diagnostics:** cue-conditioned contrast, latency strata, false alarm rates, energy/thermal operating envelope, cue-without-event counts, context/temperature stratification, learner-state hash, and predictions before and after experience. Ground truth event source and cue-intervention schedule are **evaluator-only audit labels**.
- **Controls:** identical future evaluation times, matched environment and model initialization, real prior executed actions, read-only assessment, independent environment/learner RNG, no learning on holdout targets before they are forecast. Retain exact score counts, nulls and censoring; avoid treating repeated correlated transitions as independent replicate organisms.
- **Statistical unit and design:** independent lifetimes or blocks, not every transition as an independent sample. A later approved protocol must prospectively select development seeds, untouched evidence block, sample size/power or estimation precision, comparator hierarchy, multiplicity rule and plausible effect margin; this document does **not** reserve any seeds or manufacture numbers.
- **Falsification:** no gain over best control; gain disappears after time/marginal matching; apparent gain uses actual cooling flags/future information; cue lag too long for lawful memory; improvement requires learned prediction to alter external schedule/behaviour; Level-1 survival is materially dependent on cooling; or material gains disappear on genuinely untouched seeds. Retain negative and invalidated results.
- **Interpretation if positive:** the smallest permissible claim is *within-lifetime acquired cue-conditioned prediction of an external thermal consequence under the declared ecology*. This **does not** establish partner identity, trust, reciprocal relationship, H3–H8, attachment or consciousness.

### Execution and promotion gates — no current permission to run

**Gate 0 — research design:** This document + Investigation A reviewed; choose a truly minimal lawful cue/intervention and assess whether it needs a durable boundary change.  
**Gate 1 — authority:** Specific founder-approved ADR proposal/amendment and independent review under [ADR 0013](../../docs/adr/0013-model-agnostic-independent-review-governance.md), accepted **before** any changed sensory, information or safety permission is implemented. Exact D-stage issue/PR scope required before any simulation execution.  
**Gate 2 — Development:** Legal nonreserved development seeds, exact executed SHA, zero-impact shadow learner, checks for evaluator/organism isolation, provenance/negative controls, descriptive results and `surprised_by` / `disposition`. This gate is **not** approved merely by authorizing these documents.  
**Gate 3 — EXP (if justified):** freeze claim, learner/observations, schedule generation, comparator hierarchy, metrics/margins, exact independent acceptance/confirmatory seeds, sample size and analysis **before** running untouched evidence. Follow [Reproducibility](../../docs/reproducibility.md); current EXP reservations remain untouched.  
**Gate 4 — later social research:** Separate authorization for H3 partner specificity, H4 reliability reversal, any organism-generated output, assistant interface or human trial; genuine learned competence requires an appropriately matched designed-rule baseline and distinct safety/consent gates.

## F. What this investigation cannot resolve

- No actual numerical **capacity** conclusion: the cue, delay distribution, pulse effect, model family, permissible history length and experimental results are still designs. Whether existing one-step D-046 capacity is enough is **empirically unknown**.
- No proof of **minimal sensor sufficiency**: a new cue channel may be required, but it is not yet authorized. Only a later evaluator-only audit can compare lawful observability alternatives.
- No new repository or simulation implementation; the portable battery egg and optional person-independent charging base are **future physical options** outside H2's first simulated ecology.
- No reclassification of D-046–D-048 as action-learning, no translation of D-061 descriptive results into H2 confirmation, and no change to #240's acquisition of obstruction recovery.

## G. Two review questions before any real authorization

1. Can a current, nonsemantic externally caused cue be provided without silently introducing partner identity or a learner-facing hidden evaluator truth? Identify the least additional receptor boundary consistent with a falsifiable H2.
2. What predeclared cue delay/history range and independent controls would distinguish true retained cue prediction from an already adequate time/state/physical forecast, at reasonable learner-state cost **without choosing the effect margin on acceptance results**?

**Deliverable boundary:** This is a **reviewable proposed protocol and capacity/sufficiency audit plan**, **not** a run, frozen EXP specification, chosen model architecture, accepted ADR, D result, new sensory permission or hardware design.
