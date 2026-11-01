# Aweform Familiar — Investigation B: H2 Neutral-Cue Shadow-Prediction and Capacity/Sufficiency Protocol

**Status:** DRAFT RESEARCH / PROSPECTIVE, **NOT FROZEN OR AUTHORISED TO EXECUTE**. Revised to address [Opus review B1–B4 + should-fix](https://github.com/PiFlow/aweform/pull/245#pullrequestreview-5707689349). No seed reservation or empirical result is claimed.  
**Founder authorization to investigate and draft:** [Issue #243](https://github.com/PiFlow/aweform/issues/243#issuecomment-6513908796), 30 Oct 2026.  
**Audited reference baseline:** `main` `b90dcace58ec42f7245c922b4ad1c94c12db399b`.  
**Companion:** [Investigation A — external-agent boundary](2026-10-30-external-agent-boundary-investigation.md). Active First Mate simulation [#240](https://github.com/PiFlow/aweform/issues/240) and design [#242](https://github.com/PiFlow/aweform/issues/242) remain unaffected.

## Claim, exclusions and evidentiary basis

**[SOURCE-DERIVED RESEARCH PROPOSAL]** The founder-supplied [Familiar Chaptered Edition, §5–7](https://github.com/PiFlow/aweform/blob/5338c2890ccbbe2b05e08c01de804190240ce7df/research/familiar/2026-10-30-shared-evidence/01-aweform-familiar-deep-research-chaptered.md) proposes **H2: Recurring External Context to Intervention Prediction**: Can a bounded learner use an *organism-visible, recurring, nonsemantic cue* to predict a later, externally caused, **nonessential** consequence beyond what it can already predict from its own state/action, time, schedule or simple event frequency? An external-causation observability audit precedes the first claim-bearing H2 trial.

This is **not** human-partner identification, emotion, trust, attachment, language understanding, self-awareness, agency, a beneficial learned social policy or autonomous energy maintenance. No real humans, microphones, cameras, LLM mind, powered egg, direct physical hardware, human-subject relationship test, network access or organistic use of hidden evaluator labels belongs in the first programme. The assistant/Hermes is **not** an experimental partner.

**[VERIFIED REPO EVIDENCE]** V0.5 currently has an eight-channel organism observation and differential-drive action under [ADR 0017](../../docs/adr/0017-v0.5-direct-differential-drive-centered-dock-boundary.md); [ADR 0010](../../docs/adr/0010-v0.3-lifetime-plasticity.md) permits bounded within-lifetime learned state with exact causal provenance; [ADR 0018](../../docs/adr/0018-three-layer-developmental-architecture-and-innate-viability-floor.md) protects the constitutive Level-1 survival floor. [D-046](../../development/D-046-v05-calibration-shadow-consequence-learning.md) and [D-048](../../development/D-048-v05-extended-exposure-shadow-learning-curve.md) are relevant **shadow** predictors: D-048's full 528-weight, 66-feature quadratic map predicts one-step outcomes with mixed channel discrimination; retained learning does **not** influence actions. Neither validates a multi-step, delayed H2 cue→temperature prediction. [`development/INDEX.md`](../../development/INDEX.md) and the [Development/Evidence workflow](../../docs/development-evidence-workflow.md) remain the authority on result classes. D-061 is currently an unmerged [PR #237](https://github.com/PiFlow/aweform/pull/237), not evidence of accepted H2 capacity.

## A. Quantitative physics-first baseline and two-stage design — not authorization

**[VERIFIED REPO FACT — source `src/aweform/d045.py` at `b90dcac`]** Current V0.5 uses fixed `Δt = 0.1 s`, ambient `T_a = 23 °C`, electronics heat `P_e = 0.15 W`, wheel-body heat **zero**, conductance `G = 0.25 W/K`, thermal capacitance `C = 180 J/K` and **noise-free** normalized visible temperature `T/80` (stored via float32 observations). The underlying step is

```text
T_next = T_now + (0.1 / 180) × [0.15 + P_charge + 0.25 × (23 − T_now)]
```

The uncharged equilibrium is `T_eq = 23 + 0.15/0.25 = 23.6 °C`; thermal relaxation `τ = C/G = 720 s` equals **7,200 transitions**. One kelvin is 0.0125 normalized observation units. The fixed 45/60/65 °C preferred/protective/hard bounds leave ≈21.4 K margin above the off-charge equilibrium to the preferred threshold. The current D-052/D-053 action selection **does not read temperature** (thermal *termination* still exists at high thresholds). Thus current thermal state is nonessential to these actions as long as thresholds are never reached. **Do not infer this is true of later physics or physical hardware.**

Charging is a competing driver `P_charge = P_stored × (1/0.90 − 1)` when charging occurs: bulk at up to 1.85 W stored yields **at most ≈0.206 W** of charging heat in that phase; tapers and acceptance make it smaller, not a universal fixed 0.14 W. Any pulse analysis must **exclude CHARGE** for the first clean experiment, or predeclare charge-stratified estimands and physical state matching before collecting data. Current motor action changes battery energy, **not body heat**.

**[DERIVED, illustrative—not an approved perturbation]** If a *new active heat-extraction term* `−q(t)` of `q = 0.25 W` were added for `d = 60 s` at off-charge equilibrium, the ideal first-order thermal change relative to baseline is

```text
ΔT_pulse(d) = −(q/G) × (1 − exp(−d/τ))
            = −1 × (1 − exp(−60/720)) ≈ −0.0800 K
Normalized observation difference ≈ −0.00100
For d = 10 s, ΔT ≈ −0.0138 K, normalized ≈ −0.000172
Short-time approximation: ΔT ≈ −q d/C, i.e. 1 joule changes 180 J/K thermal body by ~0.00556 K
```

This is **active cooling**, not implicitly allowed by D-045. A *passive* increment to conductance `ΔG` instead adds `ΔG(23−T)`, which can only drive toward ambient, not below it. For example, `ΔG = 0.25 W/K` starting at 23.6 °C, over 60 seconds, gives a difference of approximately **−0.0461 K**, because the new equilibrium is 23.3 °C and the new time constant is 360 s. Passive cooling's available headroom is at most roughly **0.6 K** off-charge and around **1.2 K** for a 24.17 °C historical docked probe; these are context-dependent bounds, not promised pulse amplitudes. **Any new sink, conductance term, or intervention source is a separately reviewed physics contract under ADR 0012 / ADR 0017 §H**, not a free protocol parameter.

**[DERIVED]** Delay/horizon in *seconds* controls the required memory: 10 s = 100 steps; 60 s = 600 steps; 600 s = 6,000 steps, against 720 s physical relaxation. Minutes-scale raw lag vectors can require thousands of per-step samples, so choose the **single bounded cue eligibility trace before a large lag buffer**. Neither an eligibility-trace time constant `τ_c` nor pulse duration/magnitude is fixed or authorized here; all must be prospectively chosen on legitimate development data before any untouched evaluation.

**Stage 0 — future evaluator-only learnability audit:** a specific founder-approved, scoped D-stage/analysis task must **explicitly permit re-running the unchanged frozen V0.5 simulator** at a declared executable SHA to **regenerate complete per-step trajectories**. Current committed D-053/D-059/VIS-D059 artifacts do not preserve all the charging, accepted-power, and temperature data required. Revalidate the regenerated run against an applicable committed outcome signature (for example D-053 `validation.discrete_outcome_signature_sha256`). Before synthesizing any pulse, the evaluator-side **pulse-OFF** thermal recurrence must reproduce the regenerated simulator's logged temperature sequence within a **prospectively declared floating-point tolerance**; fail closed otherwise. Only then derive evaluator-side cue and pulse effects on the immutable new trace, without modifying the frozen simulator, actual organism observation/action, Level 1, rewards, causal learner or ADRs. A Stage-0 synthetic pulse is added **post hoc to the evaluator analysis**, so the original nonthermal digest is necessarily identical ON/OFF by construction; this is **not a meaningful intervention-isolation check**. Instead cite the audited D-045/D-052/D-053 temperature-independent code path and no-thermal-termination condition. **Stage 1**, after separate organism-visible sensor/physics permissions, is where distinct simulator runs support real ON/OFF trajectory-digest comparison. Stage 0 proves at most *lawful-shaped learnability feasibility*, **not organism learning**. **No re-run or experiment is authorized by this document.**

**Stage 1 — future separately approved organism-owned shadow experiment:** introduce a neutral **organism-visible** cue `c_t` via a reviewed observation-boundary decision (ADR 0017 §F) and an explicit external thermal physics decision (ADR 0012 / ADR 0017 §H). The learner predicts lawful later temperature outcomes from its own actual history but does not alter actions, pulse schedules, charging, controller, Level 1, reward or assistant. The cue must be a nonsemantic channel **separate from the station beacon**. No real partners, microphones, human studies, physical charging devices or new sensor implementation are authorized now.

**Prospective cue constraints:** cue duration **shorter than minimum cue→pulse delay**, no coincidence of cue and pulse onset, reliability **strictly below 1**, sufficient cue-without-pulse and pulse-without-cue trials, variable delays, and no intervention identity, `time_to_pulse`, wall-clock or phase label passed to the organism. Cooling magnitude and delay law must be large enough for a meaningful prediction contrast yet within a proven no-threshold/nonessential regime.

## B. Stage-0 evaluator-only observability and learnability audit (not executed)

Before any organism cue channel is proposed, independently test whether *lawful-shaped* cue history identifies a future temperature consequence **better than a physical baseline**, not merely whether temperature is measurable. Existing V0.5 temperature is *noise-free by construction*: raw sensor-noise detectability is **not** an unresolved problem. Remaining limits are deterministic float32 quantization, pulse effect size relative to state/charging dynamics, delay uncertainty, coupling and statistical identifiability. A later real sensor/noise model would require an independently reviewed sensory boundary.

1. **Lawful context / thermal baseline:** Fit or derive the exact existing first-order recurrence using prior temperature, declared time step, electronics heat and charging state; for the clean first case exclude charging events and use only bounded nonessential off-dock periods. A cue learner must provide additional *future* predictive information beyond an adequate physical/state model; otherwise a physical identifier wins.
2. **Cue observability and timing:** Define a neutral cue encoding and delayed pulse schedule with cue duration below minimum delay, no onset overlap, reliability below one, and independent event omissions. Predict at **cue-locked times before any cooling**; use matched non-cue times as controls.
3. **Prospective horizon:** Choose candidate horizons **in seconds** relative to `τ = 720 s`, then translate to step counts. Compute counterfactual pulse magnitude via declared physics. For delay distributions wider than the cue eligibility trace supports, investigate the observed null before adding memory complexity.
4. **Separation from charging and clock leakage:** Keep CHARGE out of the initial clean sample, or freeze charge-stratified comparisons. Match time bins, temperature/energy, state/action history, cue/pulse marginal frequencies and RNG stream independence; vary episode phase enough to defeat fixed schedule/time-only shortcuts.
5. **Thermal/behavioural isolation and recurrence validity:** The frozen D-045 charging/power and D-052/D-053 action paths do not depend on temperature (except thermal termination), so a below-threshold post-hoc effect can be superposed analytically. At **Stage 0**, first require the evaluator recurrence with pulse OFF to match the actual regenerated simulator temperature sequence to a predeclared float tolerance; support nonfeedback via the verified source-path argument. **Do not score ON/OFF action/pose/energy/RNG digest identity at Stage 0**, since a single frozen trajectory is reused and equality is tautological. At **Stage 1**, if authorised to change physics and run matched conditions, independently test actual ON/OFF action/mode/pose/energy/contact/RNG/termination digest identity; failure blocks the claim of noncausal thermal-only perturbation.
6. **Sensitivity and controls:** Preserve true cue/pulse event logs **evaluator-only** for audit. Quantify observable `ΔT` in both degrees and normalised float32 units, pulse count and independent schedule-draw support; ensure cue no-pulse and pulse no-cue negative cases are adequate.

**Stage-0 outputs (future, not in this PR):** auditable design tables, executable SHA and legal seed provenance, regenerated complete per-step traces, validation against committed outcome signatures, pulse-OFF recurrence agreement to a prespecified tolerance, eligibility-trace capacity bounds, negative controls and null/negative interpretation. **No Stage-0 ON/OFF trajectory digest test is claimed. No simulation or model test has been run by this documentation PR.** A Stage-0 evaluator model does *not* establish an organism-acquired learned association.

## C. Minimal predictor ladder, learning attribution and oracle

**[DESIGN HYPOTHESIS grounded in the 720 s physics]** Choose representations from minimal to more complex *before* model selection; no automatic large model, JEPA, RL, human-language representation or agent-specific memory.

| Order | Candidate | Scientific role / limitation |
|---|---|---|
| 0 | **Zero-change / analytical first-order physical forecast** on lawful state, with charging accounted for or excluded | Best-effort non-learning null. The current deterministic thermal recurrence is a strong rival; avoid describing every predictive improvement as 'social' |
| 1 | **State-only learned predictor** from past lawful temperature/energy/action/contact | Tests whether a normal physical temporal model is already enough without cue history |
| 2 | **One bounded cue-eligibility trace** `z_t`, e.g. reset-on-lawful-cue-onset then `z_{t+1} = exp(−Δt/τ_c) z_t` otherwise | Minimal *nonsemantic causal memory* for delayed cue; one prespecified `τ_c`, or a tiny predeclared fixed bank only if justified; history is organism-owned only in Stage 1 |
| 3 | Short **bounded finite lag buffer** only if the eligibility trace cannot represent the declared delay law | Retains more exact timing at greater memory cost. A minutes-scale per-step buffer is *not* the first choice |
| 4 | Compact learned recurrent state, **only after a prospective capacity failure** in smaller models | Would itself need exact closure and independent mechanism authorization |

For each model specify feature set, past/current lawful inputs, update time *after* actual consequence, normalization, state reset/retention, memory cost, RNG, and zero causal feedback. Under Stage 0 all traces and weights remain evaluator-only; Stage 1 would require new accepted sensory/physics permission.

**Learning attribution must be observable:** A frozen **zero-initialized** D-046-style predictor is virtually a zero-change baseline, *not a discriminating proof that updates acquired cue information*. **Primary proposed attribution control:** *within-stream prequential before-versus-after learning*, scored on prospectively fixed independent cue-event counts and matched by temperature, charging, delay and schedule strata so nonstationary state is not misread as learning. A cue model trained on shuffled contexts and then frozen is an optional sensitivity check, **not the primary acquired-learning control**: its learned cue weight may converge toward zero and merely reproduce the existing no-cue state-only baseline. Include a **fixed designed cue→cooling rule** with lawful cue input if claiming any advantage over non-learning knowledge of the synthetic ecology. A fixed rule may legitimately match or beat the learner.

**Evaluator-only oracle ceiling:** derive a thermal/schedule-aware predictor with the true frozen pulse physics, cue→event probability/delay law and thermal parameters. Report learner gain beyond the best lawful baseline **relative to the achievable gain of an oracle conditioned on the same lawful history** when computable. A privileged full-future pulse schedule is a *different, unattainable diagnostic floor* and must not be used as a fair competitor or leaked into a learner. Example interpretive fraction: `(loss_best_lawful_baseline − loss_learner)/(loss_best_lawful_baseline − loss_lawful_oracle)` when denominator is positive with stable support; otherwise mark **undefined**, not as 100% or proof of competence. This is evaluator analysis only, never an organism reward or teacher signal.

A positive result for a simple filter in a deterministic thermal equation may be **instrumentation/system identification**, not meaningful social cognition. A null result in that same easy setting can be highly informative about sensory history, model closure or protocol leakage.

## D. Matched same-stream comparators versus different-world negative controls

The key correction from [Opus review B2](https://github.com/PiFlow/aweform/pull/245#pullrequestreview-5707689349): **losses computed on different generated world streams are not directly 'strongest baseline' competitors**. Separate primary paired prediction from falsification by environment perturbation.

### Primary — same contingent stream, same future targets/times

Compare all candidates' *pre-observation* predictions of actual future lawful `ΔT` on **identical retained evaluation times and realised temperatures**:

- lawful cue + bounded eligibility trace **learned online**;
- no-cue **state/history-only** predictor;
- analytical **zero-change/first-order physical** forecast with appropriate charging covariates;
- analytic **time-only / marginal-event-rate** forecast (not an organism-visible clock);
- primary meaningful **learning attribution** comparison: matched prequential before-versus-after cue exposure at prospectively fixed event counts; optional shuffled-history frozen sensitivity check only if it adds value beyond state-only;
- an **evaluator-only lawful-input oracle** using declared thermal and schedule parameters; never a model input or learning teacher.

The **primary contrast** is paired predictive loss of cue learner versus the strongest appropriate no-cue lawful baseline **within this same contingent stream**; calibration and oracle-relative headroom are secondary interpretive checks. If a designed non-learning rule with the same cue is relevant, report it honestly and do not claim benefit without beating a fair rule.

### Negative-control worlds — test whether cue-specific gain disappears

Recreate the experiment with separately generated or controlled schedules, assessing **within each control world** the same cue-model-minus-state-only prediction gain, not comparing raw loss from control world to contingent world:

- **Shuffled cue–cooling pairing:** preserve marginal cue/pulse counts, delay/temperature strata and time bins while breaking conditional pairing; demand that cue-specific gain vanishes within prespecified uncertainty.
- **Noncontingent cooling:** match pulse frequency, amplitude/duration, thermal context, and charge exclusions while removing cue conditionality.
- **Cue-only:** same cue sequence, no pulse; test direct cue sensor artifacts and false predictive confidence.
- **Optional pulse-only:** same pulse schedule without predictive cue, confirm state-only dynamics and expected base rate.

For **initial shadow-only H2**, *drop donor/agent-yoked controls*: no organism output affects pulse timing, so yoking to another lifetime adds little beyond correctly stratified shuffling and may introduce unnecessary context imbalance. Reserve yoking for later genuinely reciprocal interventions (e.g., proposed H5) with explicit coupling rules.

**Trajectory identity requirement:** Under **current V0.5 only**, if pulses remain below any thermal termination threshold and learner/cue remain noncausal, non-thermal trajectories (executed commands, controller modes, position/heading, battery/charging/contact, policy/environment RNG state, termination) should be identical for matched underlying initial states and action/schedule seeds. The **temperature and synthetic cue histories intentionally differ**; do not demand equality of those. Verify with causal-digest ON/OFF control, and preserve failures as invalidated results. Later temperature-dependent controllers invalidate this simplification and require fresh causal support.

**No hidden leakage:** Do not give the organism true pulse onset, future delays, source identity, stage number, reward, schedule seed or evaluator clock. Cue onset may anchor *offline evaluation windows* because it is lawful sensory history in Stage 1; Stage 0 uses the same lawful-shaped synthetic timestamp. Preserve independent cue/pulse randomness distinct from policy/explorer RNG and all reserved EXP seeds.

## E. Proposed preregisterable readout, failure and gating — *not frozen*

**Primary prospective estimand:** on **held-out cue-locked evaluation windows**, anchor at neutral cue onset and score `Δtemperature` at fixed future **seconds-scale** horizon(s), *before* the outcome is observed; include matched non-cue windows. Predeclare prediction time, horizon, target, window support, one primary loss (e.g. MAE or MSE), minimum practical margin and primary paired comparator. Aggregate independent trials/lifetimes by **independently sampled cue/pulse schedules**, not by treating thousands of correlated 0.1 s transitions as independent replicates. Specify how multiple events per schedule are grouped. Initial off-dock/no-charge analysis avoids charging heat; otherwise stratify by charge mode prospectively.

**Secondary checks:** whole-stream loss is a **non-degradation guard**, not the primary signal—uneventful periods otherwise dilute meaningful cue events. Report event omissions, false alarms, delayed-pulse latency bins, conditional cue gain in shuffled and cue-only worlds, physical baseline adequacy, oracle-relative gain, model memory cost, number of independent schedules, trajectory-digest controls, source/seed SHA and invalidated/null outcomes. Any probability/calibration endpoint must be generated from lawful predictions; privileged event truth can be an **evaluator scoring label**, not an input target written directly to organism state.

**Prospective learning-attribution target:** predeclare **paired prequential before-versus-after cue exposure** on the same contingent stream, evaluating distinct prospectively fixed early/late cue-event blocks with matching of lawful temperature/charge/delay/context and schedule strata; predeclare the sampling/adjustment plan to avoid interpreting drift as acquisition. A shuffled-pretrained frozen cue model may be evaluated as a secondary check but can collapse to state-only. Compare learned updates against a fixed cue→cooling rule as a separate non-learning rival when making any useful-competence claim. When attribution fails, report a model capable of cue prediction but **not established as acquiring it within lifetime**.

**Do not mix worlds:** Primary model ranking occurs **only within a contingent stream** on paired times. Negative-control environments challenge mechanism by asking whether the **cue-specific gain** vanishes within their own world, not whether absolute temperature prediction loss across different generated processes is higher/lower. Keep nonlearning oracle and fixed-rule predictions evaluator-only.

**Falsifiers / stop conditions:**
1. No predeclared positive paired gain over a strong lawful state/physical/time baseline (or no meaningful oracle headroom);
2. Gain appears equally in shuffled or cue-only worlds, schedule/time/charging leakage, or unbalanced cue omissions;
3. No prospectively specified **prequential early-versus-late improvement attributable to within-lifetime cue experience** at matched cue-event counts and lawful thermal/charging/schedule strata; a zero-initialized frozen model alone is not an adequate falsifier;
4. Cue signals pulse onset rather than preceding a delayed, uncertain consequence;
5. Successful prediction requires evaluator future-pulse truth, clock, hidden partner ID, or a sensory channel not separately approved;
6. Any material change in current Level-1 actions, energy/contact, trajectory or termination with diagnostics/cue ON versus OFF (unless separately justified in later different ecology);
7. Result depends on thermal noise or movement heating **not in current source**, or invented cooling amplitudes unsupported by an authorized world-physics boundary;
8. Effect vanishes on truly untouched evidence schedules after development/model selection (no after-the-fact margin tuning).

**Gate 0 — CURRENT TASK ONLY:** this document and [Investigation A](2026-10-30-external-agent-boundary-investigation.md) can be reviewed as **research drafts**. No simulator, evaluator or model execution is authorized by their creation.

**Gate 1 — FUTURE Stage 0 evaluator-only:** specific founder-approved D-stage/analysis authorization that **explicitly permits re-running the unchanged, frozen V0.5 simulator at a declared executable SHA** to regenerate complete per-step thermal/charging traces, with **committed signature equivalence** (e.g. D-053 `validation.discrete_outcome_signature_sha256`) and a **pulse-OFF analytic recurrence versus simulator-temperature agreement check to prospectively declared float tolerance** before offline synthetic cue/thermal-superposition analysis. This is real simulator execution, not simply reading existing saved artifacts. No ADR 0017 observation change *for this evaluator-only audit* under the accepted [Safety Boundary](../../docs/safety-boundary.md). Outcome can only be **learnability feasibility for lawful-shaped signals**, **not organism learning**.

**Gate 2 — FUTURE Stage 1 organism-owned H2:** reviewed observation amendment to **ADR 0017 §F** plus explicit external-thermal intervention authority under **ADR 0012 / ADR 0017 §H**, independently checked under ADR 0013 as applicable, then specific founder-approved implementation D issue. Shadow-only updates from lawful organism-visible cue and actual consequences. No learned action, external assistant or real human.

**Gate 3 — FUTURE EXP if justified:** freeze exact causal protocol, independent schedule/seed reservations, evaluator oracle, memory/state contract, comparator hierarchy, primary cue-locked windows, statistical unit, effect margin, sample size, nondegradation guard and interpretation before untouched confirmatory execution. Development records are descriptive and cannot automatically graduate to EXP.

**Gate 4 — FUTURE human/social and learned output:** separate explicit approval for individual recognition, partner reliability, organism output or human-subject study, with privacy/consent and additional designed-rule competence comparators. H2 cannot imply trust, attachment, relationship, consciousness or social identity.

**Smallest defensible positive claim:** A bounded within-lifetime learner, under separately approved Stage-1 permission, acquired **cue-conditioned prospective prediction of an external temperature consequence** beyond physical/time/state baselines. A positive Stage-0 finding is **strictly weaker**: evaluator-only feasibility, not acquired organism cognition.

## F. What this investigation cannot resolve

- The V0.5 **thermal constants and derived capacity scaling are now numerically specified** (720 s relaxation; seconds→steps; sample pulse sensitivities), but **the cue delay law, chosen cooling physics, trace time constant, effect margin and empirical learnability remain unknown**. Existing one-step D-046 cannot be assumed to retain a cue after its disappearance.
- No proof of **minimal sensor sufficiency**: the proposed cue is not an accepted organism receptor. A prospective **Stage-0 evaluator-only audit** may check lawful-shaped data without ADR 0017 modification; implementing the actual organism-visible cue is Stage 1 and needs a reviewed boundary.
- No new repository or simulation implementation; the portable battery egg and optional person-independent charging base are **future physical options** outside H2's first simulated ecology.
- No reclassification of D-046–D-048 as action-learning, no translation of D-061 descriptive results into H2 confirmation, and no change to #240's acquisition of obstruction recovery.

## G. Two review questions before any real authorization

1. After **separately authorised regeneration of complete traces by an unchanged frozen-simulator re-run**, validated against committed signatures and a pulse-OFF temperature recurrence, can the evaluator-only synthetic cue and superposed response demonstrate lawful-shaped identifiability without assuming an organism receptor? If positive, is the smallest separate **Stage-1** sensory permission adequately specified without using the station beacon as the cue?
2. What **seconds-scale** prospective delay, pulse magnitude, off-charge exclusion and **single-trace τ_c** yield meaningful oracle headroom beyond the strong existing physics forecast, while controlling for cue-locked evaluation, shuffled-world null gain and independent schedule replicates **without tuning against untouched results**?

**Deliverable boundary:** This is a **reviewable proposed protocol and capacity/sufficiency audit plan**, **not** a run, frozen EXP specification, chosen model architecture, accepted ADR, D result, new sensory permission or hardware design.
