# Aweform — World-Model Research Direction

**Status:** non-authorizing research direction  
**Research cut-off:** 2026-09-09  
**Repository state reviewed:** `PiFlow/aweform` `main` at `b25fe711549ba4e98f9759f8358316b94712ca64`  
**Purpose:** preserve useful world-model research and define future developmental gates without authorizing a new architecture, D-stage, ADR, learner, planner, reward, JEPA implementation, or dependency.

## 1. Claim boundary

This document is research input only. It does not authorize:

- D-032 or any later successor D-stage;
- a world-model architecture or interface;
- model-guided multi-step planning;
- reinforcement learning, value learning, actor-critic, reward shaping, or a LeCun-style cost/critic module;
- JEPA, V-JEPA, LeJEPA, SIGReg, VICReg, EMA target encoders, vision encoders, or camera input;
- replay memory, recurrence, offline training, inherited learned state, or cross-lifetime transfer;
- evolutionary optimization;
- any change to evaluator/organism information boundaries.

Any future durable architecture, information, plasticity, or safety boundary remains governed by `AGENTS.md` and the accepted ADR/review process.

## 2. Operational definition for Aweform

The term **world model** is overloaded in AI. Aweform should use a deliberately strict project definition to prevent semantic inflation.

> **Aweform world model:** an organism-internal, experience-learned, action-conditioned predictive model of relevant future organism-visible state that can represent hypothetical consequences beyond the physically executed next action, supports validated multi-step prediction under bounded uncertainty, and may only influence behaviour after a separately authorized causal experiment.

A one-step action-conditioned predictor is therefore a **predictive dynamics precursor**, not automatically a full world model.

A useful abstract form is:

```text
history of permitted observations/actions -> state representation z_t
(z_t, imagined action a_t) -> predicted future representation z_(t+1)
(z_t, imagined action sequence) -> predicted trajectory z_(t+1:t+H)
```

The representation need not be visual, linguistic, tokenized, three-dimensional, or human-semantic. For Aweform it should preferentially remain machine-native: energy, temperature, contact, power, actuator state, local fields, timing, and whatever later sensors are developmentally earned.

### 2.1 Minimal cognition, maximal viable competence

Aweform should not equate cognitive sophistication with model size, architectural complexity, or human-like reasoning. Very small biological nervous systems can support remarkably effective survival, navigation, foraging, avoidance, and adaptation. The cockroach is a useful analogy: its success does not depend on high-level abstract intellect, yet its sensorimotor organization is sufficient for robust survival in difficult, changing environments.

For Aweform, the corresponding research bias is:

> **Start with the smallest mechanism that can construct useful consequences from experience, and increase cognitive machinery only when the environment exposes a specific limitation.**

The goal is therefore not to maximize cognitive complexity. It is to discover how much adaptive, predictive, self-maintaining competence can develop from the smallest justified substrate.

## 3. What is worth preserving from Yann LeCun's world-model programme

### 3.1 Action-conditioned consequence prediction is the core

The most transferable idea is not JEPA itself. It is the question:

> Given what the organism currently knows and an action it could take, what relevant state is likely to follow?

This turns a controller from a fixed stimulus-response mechanism into a system that can eventually compare possible consequences before acting.

### 3.2 Predict relevant abstractions, not every raw detail

LeCun's central JEPA argument is that natural sensory streams contain large amounts of unpredictable or decision-irrelevant detail. A model that must reconstruct every pixel can spend capacity on texture and noise rather than controllable structure. Joint-embedding prediction instead asks a predictor to predict a representation of the future.

Aweform should preserve this principle, but only when raw organism-visible state actually becomes a bottleneck. The current six-channel state is already compact; a learned encoder would presently add ambiguity rather than remove nuisance information.

### 3.3 Planning should be consequence-based

In LeCun's architecture, an actor proposes action sequences, the world model predicts outcomes, and a separate objective/cost mechanism ranks those outcomes. The important separation is:

```text
learn what will happen != decide what should happen
```

Aweform should preserve that separation rigorously. Prediction error may train a model without becoming reward. Any later action-selection criterion must be independently justified and provenance-visible.

### 3.4 Multiple time scales are a later target

A mature world model should eventually represent fast and slow dynamics at different abstraction levels. For Aweform, plausible machine-native levels are:

```text
fast:      turning, movement, contact, immediate sensor change
medium:    SEEK/reacquisition, charging, energy/thermal trajectories
slow:      resource drift, environmental cycles, body/battery change
lifetime:  learned regularities and individuality through experience
```

This is a future research direction, not a reason to introduce a hierarchy before single-scale prediction demonstrably fails.

### 3.5 Uncertainty is part of a usable world model

A planner can exploit errors in a deterministic learned model. A future world model therefore needs some way to identify weak support or uncertain predictions and to abstain, fall back to a scaffold, or represent multiple plausible futures. The smallest useful mechanism should be tried first; a large stochastic latent model is not the default.

## 4. What should NOT be imported from LeCun wholesale

### 4.1 Do not import the full cognitive architecture

LeCun's configurator, actor, critic, intrinsic-cost, short-term-memory, perception, and world-model modules are a research proposal, not a required decomposition for Aweform. Creating corresponding classes now would violate Aweform's developmental rule and would turn a scientific project into architecture theatre.

### 4.2 Do not turn energy into reward or scalar utility

Aweform currently treats energy and thermal state as physical/engineered viability variables, not task reward. LeCun's scalar cost/energy concept should not be mapped mechanically onto Aweform's energy variable. Doing so would collapse an important distinction between physical consequence and optimization objective.

### 4.3 Do not import V-JEPA-scale vision

V-JEPA 2 and V-JEPA 2.1 are evidence that latent prediction can support visual understanding and robot planning, but their data, parameter scale, visual modality, and compute regime solve a different problem. They are architectural references, not near-term dependencies.

### 4.4 Do not treat JEPA as the only valid world-model family

MuZero, Dreamer, TD-MPC2, and earlier World Models demonstrate other useful principles: latent dynamics without observation reconstruction, recurrent state under partial observability, planning in learned latent state, and decision-relevant prediction. Aweform should compare principles experimentally rather than join an architectural camp.

### 4.5 Do not adopt SIGReg as doctrine

LeJEPA's SIGReg is a promising anti-collapse method for learned embeddings. It is relevant only once Aweform has a learned representation capable of collapsing. Recent 2026 preprints question whether forcing embeddings toward a full-dimensional isotropic Gaussian is always appropriate for low-intrinsic-dimensional/manifold-like data. Aweform should treat SIGReg, VICReg, EMA/stop-gradient, and other anti-collapse methods as future ablation candidates, not settled truth.

## 5. Current Aweform position relative to a world model

### D-027 — predictive dynamics precursor

D-027 learns a 168-weight action-conditioned linear model from the six organism-visible channels:

```text
energy
beacon.left
beacon.forward
beacon.right
charging_contact
thermal
```

For each action it predicts one-step deltas in all six channels from the current visible state. It has no history, recurrence, replay buffer, optimizer state, hidden evaluator data, or reward. Only the executed action updates the learner.

This is already a genuine learned **sensorimotor consequence model**. It is deliberately not called a world model because its scope is one step and its predictions originally had no causal influence.

### D-029 — counterfactual-readiness audit

D-029 asked the existing predictor what each of the four candidate actions would do from the same visited state and compared those read-only predictions with evaluator-isolated branches. The learner still updated only from the physically executed action.

Important result: exact prior state/action support was zero for every candidate branch row, yet some unexecuted-action predictions, especially beacon and energy consequences, were still better than a zero-change comparator. Contact and some thermal contrasts remained weak. This demonstrates partial generalization, not general counterfactual competence.

### D-030 — first bounded causal use

D-030 allowed one narrow prediction to influence one narrow decision: during specified false-contact SEEK decisions, predicted next forward-beacon consequence was used to choose among left, right, and forward. The correct predictor-action association completed all 20 full cycles; the fixed cyclicly permuted predictor failed SEEK on all 20 seeds.

This is important causal evidence that learned action-consequence structure can matter to behaviour. It is still not planning or a world model: it is one-step, one-output, narrowly gated action selection.

### D-031R1 — scaffold-displacement failure is important world-model evidence

D-031R1 tested whether the learned SEEK steering could retain reacquisition when the engineered `1/3` stochastic de-trapping delegation was disabled. It could not: the unchanged learned-with-de-trapping arm completed all 20 full cycles, while both no-de-trapping arms failed SEEK and depleted energy on every fresh seed.

This negative result is strategically important. It shows that a predictor can be causally useful in a narrow intervention without yet being competent enough to replace an engineered exploration/de-trapping scaffold. Aweform should therefore resist the temptation to call narrow prediction success a mature world model or to enlarge the model automatically. The next question must identify what is actually missing: predictive support, state/history, exploration coverage, uncertainty, or another specific developmental limitation.

## 6. Aweform world-model qualification ladder

These names are research categories, not reserved D-stage identifiers.

| Level | Minimum capability | What it permits us to say | What it does **not** imply |
|---|---|---|---|
| **P0 — consequence predictor** | Executed-action one-step prediction | Learns local action consequences | Counterfactual competence, planning |
| **P1 — alternative-action predictor** | Read-only queries for unexecuted actions with evaluator audit | Some bounded counterfactual predictive competence | Generalization outside support |
| **P2 — causal one-step predictor** | Prediction changes a bounded action decision under matched controls | Learned consequence prediction is behaviourally causal | Multi-step reasoning |
| **WM0 — rollout-capable dynamics model** | Predicts action-sequence consequences for H>1 with held-out fidelity | Bounded internal simulation of future trajectories | Useful planning |
| **WM1 — uncertainty-bounded world model** | Rollouts include calibrated support/uncertainty or abstention | Knows some limits of its predictive competence | Correct objective/action selection |
| **WM2 — planning-useful world model** | Multi-step predictions improve a separately authorized behavioural problem vs one-step/model-free controls | Model-based planning is causally useful in that ecology | General intelligence |
| **WM3 — learned latent world model** | Learned representation beats raw-state model where abstraction is actually needed | Predictive representation is functionally useful | JEPA superiority |
| **WM4 — hierarchical world model** | Multiple learned time scales/abstraction levels improve long-horizon prediction/planning | Hierarchical predictive cognition is useful | Human-like reasoning |

On this taxonomy, current Aweform has reached **P2 in one narrow D-030 intervention**, while D-031R1 shows that this competence is not yet sufficient to displace the stochastic de-trapping scaffold. The broader six-output model remains uneven and one-step.

## 7. Developmental gates toward WM0–WM4

### Gate A — finish one-step competence before adding depth

**Developmental problem required:** current one-step prediction demonstrably limits useful action-consequence discrimination.

**Minimum research:** preserve per-output/per-action/per-context diagnostics; specifically track rare contact transitions, boundary clipping, and thermal consequences. Do not collapse all outputs into one score.

**Falsifier:** a fixed/simple predictor or current D-027 remains sufficient. If so, do not enlarge it.

### Gate B — multi-step shadow rollout

**Developmental problem required:** a decision depends on delayed consequences that one-step ranking cannot distinguish.

**Minimum mechanism:** roll the smallest existing predictor forward across candidate action sequences in shadow only. No action influence at first.

**Required measurements:** k-step state error, event timing error, action-ranking error, compounding drift, boundary/contact failure, and whether predictions remain physically plausible.

**Critical control:** compare against naive persistence/zero-change and a simple hand-derived baseline where legitimate.

### Gate C — partial observability earns memory

**Developmental problem required:** identical current observations lead to meaningfully different futures because relevant history is hidden.

**Minimum mechanism:** add the smallest bounded history/latent state that resolves the ambiguity. A tiny recurrent state is preferable to a transformer unless evidence demands more capacity.

**Falsifier:** current observation plus one or two explicit permitted history features solve the problem.

### Gate D — uncertainty before planning

**Developmental problem required:** rollout quality varies by support/context enough that a planner could exploit model error.

**Minimum mechanism candidates:** per-output residual statistics, lightweight ensembles, or another inspectable support estimate. The model must be able to abstain or fall back to the existing scaffold.

### Gate E — first multi-step causal planning

**Developmental problem required:** delayed consequences make the existing reactive/one-step scaffold measurably insufficient.

**Minimum mechanism:** short-horizon model-predictive control using candidate action sequences and receding-horizon replanning.

**Do not introduce a generic reward.** The ranking rule must reuse or separately justify an organism-internal criterion and remain distinct from model-learning loss.

**Required controls:** model-free/reference scaffold, one-step model, correct multi-step model, fixed-permuted model, and where useful a frozen/random predictor.

### Gate F — learned representation / JEPA gate

Do not introduce a learned encoder merely because JEPA is interesting. Require all of the following:

1. organism-visible input is now sufficiently high-dimensional or multimodal that raw-state prediction is a real bottleneck;
2. predicting exact raw detail is demonstrably wasteful or harmful;
3. the best simple raw-state/recurrent model has been benchmarked;
4. transfer/generalization requires an abstraction not supplied by hand-engineered channels;
5. rare viability-critical information can be evaluator-probed for retention;
6. compute and new dependencies are justified by the scientific question.

Only then compare latent objectives such as EMA-target JEPA, VICReg-style regularization, LeJEPA/SIGReg, or other contemporary methods.

### Gate G — hierarchy

Introduce multiple predictive time scales only when long-horizon rollout error or planning complexity demonstrates a genuine need. Aweform should prefer machine-native temporal abstraction over imported human semantic categories.

### Gate H — prediction-driven exploration/play

Only after a world model exists and the organism has safe energetic surplus should prediction error, uncertainty reduction, learning progress, or controllability become candidates for play/curiosity experiments. They should not automatically become scalar reward.

## 8. A critical JEPA-specific danger for Aweform: predictable is not the same as important

JEPA intentionally discards unpredictable detail. That is often beneficial, but Aweform contains rare variables whose transitions may be difficult to predict yet essential to viability.

D-027/D-029 already expose this risk: charging-contact prediction was weaker than several smooth beacon/energy channels. A future learned encoder could decide that rare contact transitions are nuisance information and remove them, even though they may be causally vital.

Therefore every learned representation must pass **viability-sufficiency probes** performed evaluator-side. Candidate probes include:

```text
Can current energy/thermal state still be decoded or predicted?
Can rare contact transitions be distinguished?
Can action-conditioned changes relevant to viability still be ranked?
Does the representation preserve failure-preceding information?
Does a planner using the latent state make worse real-world choices despite low latent loss?
```

Low JEPA prediction loss is not enough.

## 9. Planning without covert reward

World-model learning and action selection must remain separate:

```text
MODEL LEARNING SIGNAL
actual next permitted observation vs predicted next permitted observation

ACTION-SELECTION CRITERION
separately authorized rule using predicted consequences
```

A future planner should initially operate only on a narrow existing developmental decision surface so that the effect of deeper prediction can be isolated from the effect of inventing a new objective.

A useful future pattern is constrained/receding-horizon selection:

```text
1. predict candidate sequences;
2. reject or abstain on sequences with unsupported/OOD predictions;
3. enforce separately authorized viability constraints;
4. compare remaining sequences using the exact developmental criterion under study;
5. execute only the first action;
6. observe reality and re-plan.
```

This resembles model-predictive control while preserving Aweform's zero-reward research boundary unless a future ADR explicitly changes it.

## 10. World model versus self model

Aweform's current six channels mix external and internal consequences. That is acceptable at this scale.

A separate **self model** becomes justified only if predicting the organism's own body/internal dynamics creates a distinct problem from predicting its environment. Possible later self-model variables include actuator cost, thermal inertia, battery response, sensing/computation cost, damage/failure state, and blackout/recovery dynamics.

Do not create a SelfModel class in anticipation of this. Earn the distinction experimentally.

## 11. Evaluation contract for future world-model work

Every future world-model candidate should be evaluated across at least these dimensions before a larger architecture is justified:

| Dimension | Required evidence |
|---|---|
| **One-step accuracy** | per channel/action/context against zero-change/simple baselines |
| **Rare-event fidelity** | contact/termination/boundary/thermal event-specific metrics |
| **Alternative-action fidelity** | evaluator-only branch comparisons, never leaked to learning |
| **Multi-step fidelity** | error versus horizon, event timing, physical plausibility |
| **Action ranking** | pairwise sign/rank correctness where outcomes differ |
| **Support/OOD** | explicit diagnostics for states/actions outside experienced support |
| **Uncertainty calibration** | high uncertainty should predict larger real error if uncertainty is claimed |
| **Causal isolation** | prediction queries/diagnostics do not mutate controller, RNG, environment, or learner |
| **Behavioural utility** | matched-arm causal experiment, not offline metric alone |
| **Model exploitation** | chosen sequences must not systematically exploit prediction errors |
| **Scaffold displacement** | learned mechanism must earn replacement of an engineered rule under fair controls |
| **Provenance** | inherited/programmed/lifetime-learned/evaluator-only state remain separable |

Do not produce one aggregate "world-model score" that hides output-specific failure.

## 12. Failure modes to preserve in future review

1. **World-model theatre:** adding a neural predictor to deterministic equations the organism never needed to infer.
2. **Representation collapse:** a learned encoder converges to constant/low-rank features.
3. **Semantic collapse without numerical collapse:** embeddings vary but discard viability-critical information.
4. **Compounding rollout error:** one-step accuracy looks good but H-step imagined trajectories drift rapidly.
5. **Model exploitation:** planning discovers actions that look good only because the model is wrong there.
6. **Coverage confounding:** alternative-action predictions are judged without measuring actual support.
7. **Evaluator leakage:** branch truth, coordinates, mode, seed identity, or future state enters learning/control.
8. **Objective leakage:** evaluator success metrics quietly become organism reward/cost.
9. **Capacity escalation:** poor performance caused by partial observability or omitted state is misdiagnosed as "need a bigger network."
10. **Architecture capture:** adopting JEPA/Dreamer/TD-MPC because the literature is impressive rather than because Aweform earned the mechanism.
11. **Vision capture:** treating cameras/pixels as inherently more cognitive than machine-native energy, thermal, timing, electrical, radio, or actuator signals.
12. **Cross-lifetime contamination:** learned state is inherited without an explicit heredity/evolution experiment.

## 13. What to reuse from existing world-model research

| Work | Preserve for Aweform | Do not import by default |
|---|---|---|
| **LeCun 2022 AMI architecture** | action-conditioned prediction, separation of model and objective, multi-timescale abstraction | full modular cognitive architecture; scalar intrinsic-cost/critic design |
| **I-JEPA / V-JEPA** | predict representations instead of reconstructing raw detail | ViT-scale vision stack before high-dimensional perception exists |
| **V-JEPA 2-AC** | action-conditioned latent prediction; receding-horizon planning; goal-state comparison without task-specific reward training | 1B-scale video pretraining; image-goal assumptions |
| **V-JEPA 2.1** | dense/spatiotemporal predictive representation techniques as later references | scale-driven architecture now |
| **LeJEPA / SIGReg** | future anti-collapse candidate and theoretical reference | isotropic Gaussian as unquestioned universal prior |
| **VICReg** | simple explicit variance/covariance anti-collapse baseline | unnecessary regularization before a learned encoder exists |
| **TD-MPC2** | decoder-free latent dynamics; short-horizon local trajectory optimization; strong model-based control benchmark | RL reward/value machinery and large multitask scaling |
| **DreamerV3** | recurrent latent state, multi-step imagination, partial-observability lessons | actor-critic/reward architecture as Aweform's default |
| **MuZero** | prediction can be decision-relevant without reconstructing observations | policy/value/reward targets and tree-search stack |
| **Ha & Schmidhuber World Models** | historical demonstration of learned internal simulation | reconstructive VAE/generative dream as assumed best representation |

## 14. Evolution and inheritance boundary

Within-lifetime world-model learning should come before Darwinian/evolutionary optimization.

If cross-generation evolution is later authorized, provenance must distinguish at least:

```text
engineered physiology/architecture
inherited initial parameters or priors
within-lifetime learned state
online predicted/imagination state
evaluator-only state
```

A future evolutionary experiment could test whether selection shapes learning priors, model capacity, sensor morphology, or learning rates. It should not silently optimize the same evidence seeds or inherit lifetime-learned knowledge unless that inheritance is the explicit research question.

## 15. Recommended repository change now

The correct near-term repository action is **documentation only**, not implementation.

Recommended durable artifact:

```text
docs/world-model-developmental-direction.md
```

This document can be the initial content. Add one non-authorizing link from `docs/research-roadmap.md` under Later Directions.

Do **not** at this stage:

```text
create a WorldModel interface
add torch/JAX/V-JEPA dependencies
vendor external repositories
create a JEPA ADR
reserve a D-stage number
change D-027/D-030 behavior
change reward or viability semantics
add replay/history/recurrence
create a planner
```

A future implementation should begin only from an exact-current-HEAD developmental question and the smallest mechanism that addresses it.

## 16. Source register

### Project/repository sources

- `AGENTS.md` at reviewed main.
- `docs/north-star.md`.
- `docs/developmental-principles.md`.
- `docs/research-roadmap.md`.
- `development/D-027-shadow-sensorimotor-consequence-learning.md`.
- `development/D-029-action-alternative-readiness-audit.md`.
- `development/D-030-bounded-learned-seek-steering.md`.
- `development/D-031R1-learned-seek-scaffold-displacement-clean-rerun.md`.

### Primary / peer-reviewed external sources

- Yann LeCun, **A Path Towards Autonomous Machine Intelligence**, v0.9.2, 2022.
- Assran et al., **Self-Supervised Learning From Images With a Joint-Embedding Predictive Architecture**, CVPR 2023, DOI `10.1109/CVPR52729.2023.01499`.
- Bardes et al., **Revisiting Feature Prediction for Learning Visual Representations from Video**, TMLR 2024, arXiv `2404.08471`.
- Bardes, Ponce, LeCun, **VICReg: Variance-Invariance-Covariance Regularization for Self-Supervised Learning**, ICLR 2022.
- Hansen, Su, Wang, **TD-MPC2: Scalable, Robust World Models for Continuous Control**, ICLR 2024, arXiv `2310.16828`.
- Schrittwieser et al., **Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model**, Nature 2020, DOI `10.1038/s41586-020-03051-4`.
- Hafner et al., **Mastering Diverse Control Tasks through World Models**, Nature 2025.
- Ha & Schmidhuber, **World Models**, arXiv `1803.10122`.

### Current/preprint external sources

- Assran et al., **V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning**, arXiv `2506.09985`.
- Mur-Labadia et al., **V-JEPA 2.1: Unlocking Dense Features in Video Self-Supervised Learning**, arXiv `2603.14482`.
- Balestriero & LeCun, **LeJEPA: Provable and Scalable Self-Supervised Learning Without the Heuristics**, arXiv `2511.08544`.
- Le, **UR-JEPA: Uniform Rectifiability as a Regularizer for Joint-Embedding Predictive Architectures**, arXiv `2606.01443` — independent 2026 preprint; treat as an unsettled critique, not established correction.

### Interview source

- Yann LeCun interview, YouTube video ID `m7ywFu3Yqh8`, user-supplied transcript. Preserve only paraphrased research notes and timestamps; do not commit the full transcript unless copyright/permission has been separately checked.

## 17. Bottom line

Aweform should not "adopt JEPA." It should **grow into the problem that makes JEPA-like representation learning useful**.

The current D-027 → D-029 → D-030 → D-031R1 lineage is already the correct developmental bridge: learn consequences from actual experience, audit alternative-action prediction, allow one narrowly bounded prediction to influence one decision under strong controls, then test whether that learned competence can actually displace an engineered scaffold. D-031R1 correctly preserved the answer **no** when it failed.

The next genuine world-model milestone should be earned when the ecology creates a delayed, partially observed, or multi-step consequence problem that a one-step predictor cannot solve. At that point, the smallest justified move is multi-step shadow prediction, not a billion-parameter visual foundation model.
