# Aweform Familiar — Deep Research, Chaptered Edition

*Narration and reading edition of the deep research report on developmental cognition, human–artificial relationships, social robotics and machine-native intelligence. Evidence base through 28 October 2026. Publisher-style tables have been converted to running text so the document reads and listens cleanly; the substance, evidence labels and caveats are unchanged.*

## Contents

- **1. Executive Scientific Synthesis** — audio 11:30
- **2. Biological and Cognitive Foundations** — audio 17:29
- **3. Computational Cognition, AI and Robotics** — audio 17:49
- **4. Aweform Repository State and Gap Analysis** — audio 11:59
- **5. Relationship Hypotheses and Falsifiable Experiments** — audio 13:54
- **6. Workstreams, Priorities, Ethics and Gates** — audio 20:41
- **7. Decision Memorandum and the First Research Sprint** — audio 12:15

Total listening time: **105:40**

---

## 1. Executive Scientific Synthesis

This review evaluates the scientific and engineering basis for Aweform Familiar as a developmental research direction, using evidence available through 28 October 2026 and the live PiFlow Aweform repository state inspected for this report.

The central conclusion is deliberately narrower than the vision. There is credible scientific and engineering support for studying how an artificial organism can learn individual-specific predictions, reciprocal signals and progressively more useful coordination with a recurring human partner. There is not evidence that such mechanisms amount to attachment, trust, friendship, emotion or consciousness.

Throughout this report, five evidence labels are used consistently.

Established evidence means supported by replicated or converging work. Experimental evidence means demonstrated in a particular study or system. Emerging hypothesis means promising but insufficiently established. Engineering inference means plausible from existing mechanisms but not yet demonstrated for Aweform. Speculation means a long-range possibility without adequate evidence. And Proposal — Aweform means a design or experiment recommended specifically here.

A crucial repository-status caveat applies. The canonical committed development ledger currently extends through D-059. Live issue #240 describes a founder-directed planning initiative led by First Mate, which is GPT-6.1 Sol in Pi CLI. Issue #242, opened on 27 October 2026, is explicitly design-only work on acquired obstruction recovery using a possible MuJoCo body and inertial-measurement substrate. It does not authorise implementation or experiment execution. Issue #242 recorded main at commit b90dcace when it was opened, and explicitly requires re-verification when work begins. This report therefore does not claim that commit is necessarily still current at the end of 28 October.

The ten findings that follow are the most decision-relevant conclusions of the review.

Finding one. Newborn brains are highly structured, not blank slates. Prenatal neural organisation, sensory exposure and maturation coexist with rapid experience-dependent learning. Human newborns already discriminate and preferentially respond to some familiar prenatal auditory patterns, including the maternal voice, and controlled prenatal exposure can alter neonatal neural responses. This is established evidence. The implication for Aweform is that the system should begin with explicit priors: viable physiology, sensor and action topology, plasticity rules and temporal constraints. Learning everything from nothing is neither biologically faithful nor experimentally clean.

Finding two. Development comes from interaction between maturation and learning. During infancy, brain volume, cortical microstructure, white-matter organisation and synaptic structure change dramatically, and different sensory and association systems mature on different schedules. These biological maturational processes should not be mislabelled as learning. This is established evidence. Artificial development can borrow staged capability release, but only as an engineered curriculum or capacity schedule. A sensor being activated later is not evidence that the agent learned to see.

Finding three. Very simple contingency learning and memory appear early. Young infants can learn action to consequence contingencies, retain them, and show context-dependent retrieval. Statistical regularities can be learned before mature episodic memory exists. This is established evidence. The first Familiar mechanisms do not need language, symbolic person concepts or general intelligence. Online prediction of temporally structured consequences is a defensible starting point.

Finding four. Individual familiarity, reliability prediction and attachment are different phenomena. Feeding alone is insufficient to explain primate attachment. Caregiver sensitivity is associated with attachment security, but only moderately and non-deterministically, and attachment patterns show both relationship specificity and cultural variation. This is established evidence with important qualifications. Aweform should operationalise progressively stronger claims in this order: discrimination, then familiarity, then agent-specific prediction, then reliability updating, then preference or coordination. It should not operationalise trust or love.

Finding five. Reliable social partners can change learning and exploration, but this is not reducible to reward delivery. The human evidence includes social referencing, joint-attention effects on learning, caregiver-dependent modulation of threat-related processing, and socially scaffolded communication. This is established for humans in domain-specific forms, but not as a single mammalian mechanism. A scientifically interesting later question is whether a learned reliable external agent changes Aweform's exploration or learning efficiency without becoming a survival crutch.

Finding six. Action-conditioned predictive learning is a strong near-term computational target. Simple predictive systems, classical world models, Dreamer-style latent models and recent JEPA world models all show that useful action to consequence structure can be learned, but complexity and data requirements span orders of magnitude. DreamerV3 solved more than 150 benchmark tasks with a common configuration, while V-JEPA 2 used over a million hours of internet video plus less than 62 hours of robot video. Both are far removed from lifetime developmental learning in a small organism. This is experimental evidence. The lesson is: do not jump to Dreamer, JEPA or a vision-language-action model. Aweform's existing tiny quadratic predictor already answers a more relevant question, namely what can be learned online from lawful sensorimotor experience with very little machinery.

Finding seven. Aweform already has a scientifically useful substrate, but it does not yet have a social learner. Version 0.5 supplies energy and temperature interoception, beacon and contact exteroception, wheel proprioception, differential-drive action, and an accepted Level-1 viability floor. Development records D-046 to D-048 demonstrate shadow one-step action to consequence learning, strongest for wheel consequences and substantially weaker for several beacon and contact targets. These predictions remain causally excluded from behaviour. This is experimental evidence inside Aweform. Familiar is not starting from zero. The immediate gap is not a larger neural model. It is a lawful external-agent interaction boundary, plus a minimal experiment that distinguishes recurrent external-agent prediction from trivial temporal correlation.

Finding eight. Robots can personalise, learn sensorimotor skills and support long-term human interaction, but no existing system establishes the complete Familiar hypothesis. The iCub platform, Oudeyer-style intrinsically motivated robots and social-learning systems demonstrate developmental mechanisms. Tega and DragonBot studies demonstrate long-term personalised interaction. But one influential two-month preschool study used scripted robot speech and actions plus a human teleoperator, so children's relational responses cannot be cited as evidence that the robot itself learned a relationship. This is experimental evidence with an integration gap remaining. Familiar is scientifically legitimate precisely because the combination of online embodied individual learning, a long-lived partner model and reciprocal competence growth is still poorly demonstrated.

Finding nine. Reciprocal adaptation can be defined without invoking emotion. A defensible operational criterion is that both human and machine policies change over repeated interaction, that partner-specific retained state predicts those changes, and that joint performance improves beyond one-sided or yoked controls. Existing robot tutoring, personalised social robotics and socially guided motor-learning studies demonstrate components, not the whole construct. This is an engineering synthesis from experimental evidence. Scientific records should use the term reciprocal adaptive collaboration. Symbiosis may serve as a design metaphor, not a biological conclusion.

Finding ten. The largest risk is confusing appearance with acquisition. Social robots can elicit rapport and friendship reports even when behaviour is scripted. Foundation robotic models can display impressive capabilities learned before deployment. Anthropomorphic AI can produce dependence without any corresponding machine relationship. A 2025 four-week controlled chatbot study of 981 participants found no simple main effect of assigned interaction condition, while heavier voluntary use was associated with worse loneliness, dependence and problematic-use outcomes. This is an established methodological risk, with emerging longitudinal evidence on human-AI safety. Every Familiar claim therefore needs attribution: programmed, pretrained, lifetime-learned, human-supplied, external-tool-supplied, or evaluator-only. The architecture should deliberately resist emotional manipulation.

Now the overall feasibility judgement.

Supported now: an artificial organism can learn sensorimotor contingencies, statistical regularities, predictions and partner-specific associations from repeated experience. Robots can adapt to human-specific information. Humans can learn to coordinate with machines. And long-term human-robot interaction can create measurable individual interaction histories.

Technically plausible but not established for Aweform: an online learner with compact memory could form different predictions for two recurring external agents, update those predictions after reliability changes, discover bidirectional signals, and acquire jointly scaffolded skills. That conclusion is an engineering inference, not existing Aweform evidence.

Speculative: that such interaction would produce an artificial analogue of emotional attachment, friendship, caring, subjective trust or consciousness. There is currently no defensible experiment that would allow those claims merely from prediction, signalling, preference, separation effects or cooperative behaviour.

The ruthless conclusion is therefore this. Do not build a familiar yet. Build experiments that could tell you whether a partner-specific developmental process exists at all.

## 2. Biological and Cognitive Foundations

The central biological lesson is not to copy infancy. It is that development operates under structured initial conditions, multiple learning timescales, changing physical and neural capabilities, and highly contingent social experience.

We begin with the developmental timeline, and the source of each capability. For each phenomenon, the useful question is how much is initially organised or prenatal, how much is biological maturation, how much is experience-dependent, and how much is socially dependent.

Basic sensory pathways and reflexive regulation are strongly organised before birth. Prenatal sensory systems and neural organisation are already active, and prenatal auditory exposure produces measurable postnatal effects. Maturation still plays a major role, and experience modifies discrimination and representation. Transfer value for Aweform is high: encode lawful sensors, viability reflexes and learning rules as priors.

Visual acuity and high-resolution object processing are limited at birth. There is major postnatal development of visual pathways and cortical microstructure, and experience matters enormously, though it is not inherently social. Transfer value is moderate. Staged sensing can simplify learning, but artificial staging must be declared as engineering.

Voice familiarity is partly prenatal. Newborn maternal-voice preference has experimental support, the auditory system continues maturing, and experience matters strongly, including for individual familiarity. Transfer value is high: recurrent identity can emerge from statistics before symbolic naming.

Face orienting is a caution. Newborns show differential tracking of face-like patterns, but the mechanism and the degree of innate face specificity remain debated. Maturation and perceptual expertise both matter. For Aweform, do not hard-code face merely because primates have early biases.

Cross-modal person and event association begins early. There is early sensitivity to temporal synchrony, while more arbitrary audiovisual identity associations improve over the first months. Transfer value is high: temporal coincidence is a candidate route to multimodal agent identity.

Sensorimotor contingency is present from very early on. Three-month-olds can learn action-contingent mobile effects, and the capacity improves with motor maturation. Transfer value is very high, because this is a core dependency for any self-versus-world distinction.

Self-versus-external causation is not something a newborn possesses as a complete concept. It develops, and it depends on action, efference and contingency experience, and it can be socially enriched. Transfer value is very high: learn controllability before learning person. Infant neural evidence at very early ages remains limited.

Object permanence should be treated carefully. It is not safely characterised as an adult-like innate concept; it develops, and it is strongly experience-dependent. Violation-of-expectation studies admit perceptual alternatives, so early object permanence should not be treated as settled.

Long-term episodic-like memory is immature. Hippocampal systems mature gradually, and experience matters, but social input is not required. Transfer value is moderate. Memory systems can be separated by function rather than copied anatomically, and infant statistical learning can precede mature episodic memory.

Attachment as a relationship is not a complete ready-made bond to a particular individual. Relevant regulatory systems mature, and attachment is strongly relationship-specific and socially dependent. Transfer value is low as a literal robot target, but high as inspiration for reliability and co-regulation experiments.

Joint attention and referential communication are absent at birth. They develop substantially late in the first year and beyond, and they require coordinating representations of self, other and a common target. Representative work shows joint-attention learning effects around nine months that are not seen in younger infants. Treat these as later-stage goals only.

Increasing autonomy is a central design principle. Biology provides increasing motor and regulatory capacity, practice and exploration drive it, and caregiver scaffolding can support it. Assistance should produce competence transfer, not permanent rescue.

What, then, does newborn behaviour actually come from? The evidence does not permit a clean percentage such as a certain share innate and a certain share learned. There is no scientifically defensible decomposition of newborn behaviour into such percentages, because genes, spontaneous developmental processes, prenatal experience and postnatal experience interact causally rather than adding as independent fractions.

What can be said much more securely is this. Inherited and developmentally constructed organisation establishes anatomy, sensory topology, basic reflexes, endogenous regulatory mechanisms, plasticity rules and many species-typical behavioural biases. Human neurodevelopment is both genetically organised and experience-sensitive.

Prenatal learning is real. DeCasper and Fifer's classic newborn work showed behaviour sensitive to the mother's voice, and controlled prenatal pseudoword exposure produced postnatal neural differences in Partanen and colleagues' study. These results are evidence against any post-birth blank slate.

Maturation is enormous. Magnetic resonance imaging found approximately a doubling of total brain volume during the first postnatal year in the studied cohort, with structures and tissue classes changing at different rates. Microstructural and white-matter development likewise show non-uniform regional trajectories.

And experience changes the developing system. Contingency learning, statistical learning, recognition memory and social learning all occur long before mature adult cognition.

That leads to a direct Aweform principle. Initial structure is not cheating. The relevant scientific question is whether a capability's adaptive content is supplied in advance or acquired through experience.

Next, perception, self and causation. A useful artificial developmental sequence does not need to begin with semantic objects. A minimally structured organism can first acquire regularities of the form: current sensory state together with action predicts a distribution of future sensory state. It can then identify cases where observed consequences systematically depart from its action-conditioned expectations.

That provides a functional route toward distinguishing four kinds of event. First, self-controllable events, meaning consequences reliably dependent on its own commands. Second, uncontrolled regularities, meaning predictable events independent of its commands. Third, recurring external causes, meaning latent sources whose appearance improves prediction of otherwise unexplained changes. Fourth, individual external agents, meaning recurring latent causes that differ systematically in conditional consequences.

This is an engineering inference. It is not a claim that infants explicitly perform Bayesian causal decomposition. Early infant agency work supports the importance of contingency but does not establish a complete neural algorithm for selfhood. For Aweform, this is much cleaner than initially providing symbolic variables such as human, caregiver, helpful or friend.

Now caregiver relationships and attachment, where the biological evidence is often simplified too aggressively.

Harlow and Zimmermann's rhesus work demonstrated that access to food did not, by itself, explain infant preference for surrogate caregivers; tactile and contact properties profoundly affected preference. Those historically influential experiments are also examples of animal suffering that should not inspire artificial deprivation paradigms.

Contemporary attachment evidence shows a moderate association between caregiver sensitivity and secure attachment rather than a deterministic relationship. A large 2024 meta-analysis covering 174 samples and more than 22,000 dyads estimated an association around r equals .25. A later umbrella review found effects of broadly similar modest magnitude across several developmental outcomes.

Attachment is neither a fixed infant trait nor entirely interchangeable across partners. Meta-analytic evidence finds only moderate stability across early development, and infants can establish distinguishable relationships with professional caregivers as well as parents.

Cross-cultural evidence is important but easy to abuse. The classic cross-cultural Strange Situation meta-analysis found substantial within-culture variation as well as a widespread secure pattern, while newer work shows that associations between sensitivity and attachment can vary across sociocultural contexts. The safe conclusion is not that attachment is culturally universal in exactly one form. It is that close caregiver relationships are widespread while their organisation, behavioural expression and measurement context vary.

For Familiar, therefore, the vocabulary must be kept separate. Recognition means discrimination of identity-relevant patterns. Familiarity means altered processing after repeated exposure. Reliability expectation means learned prediction of another agent's conditional behaviour. Behavioural preference means action selection favouring one agent or context. Attachment, in developmental psychology, is a richer relationship construct involving proximity, separation and regulation patterns. And subjective trust implies an experiential state that we currently have no way to establish for an artificial agent. Those terms must never be collapsed.

On caregiving, regulation and exploration: human caregivers do more than deliver calories. Social partners regulate stress, attention and information availability. Experimental neuroimaging work has shown developmental effects of maternal cues on amygdala-prefrontal processing during childhood, and behavioural studies show infants use caregiver affect or voice to guide decisions in uncertain contexts such as visual-cliff paradigms.

This motivates, but does not prove, the Familiar hypothesis that a predictable external partner could change exploration by reducing uncertainty or improving learning conditions. The correct artificial experiment would not make Aweform unable to survive without a caregiver. Instead, the baseline Level-1 viability floor should continue functioning, while a partner may provide optional informational or efficiency advantages. That preserves a distinction between supported development and engineered dependency.

On neural mechanisms, the lesson is functional, not brain-region cosplay. The hippocampus, amygdala, prefrontal systems, hypothalamus, sensory association networks, basal ganglia and reward systems, and neuromodulatory systems all participate in distributed developmental processes. Assigning labels such as hippocampus equals memory, or amygdala equals fear, is scientifically inadequate. Memory, salience, regulation and prediction arise from interacting networks whose functional roles change with age and context. The prolonged postnatal development of prefrontal circuitry and human cortical synaptic structure illustrates why developmental timing matters.

Sleep deserves separate attention. Experimental infant studies and a 2025 meta-analysis support a modest positive role for naps in memory consolidation, including deferred imitation and face-memory paradigms. That does not imply an artificial robot needs biological sleep. The transferable principle is that offline or reduced-interference consolidation may be useful once continual-memory interference becomes demonstrable.

Predictive processing is a valuable computational framework, not an established complete theory of developmental cognition. Rao and Ballard's influential predictive-coding model showed how hierarchical prediction errors could explain particular visual-cortical response properties, but that result does not demonstrate that the whole brain, or infant development, is simply one predictive-coding algorithm.

Strong mirror-neuron interpretations deserve particular scepticism. Mirror-like sensorimotor representations are experimentally supported and their response properties are plastic, but claims that a specialised mirror system straightforwardly explains action understanding, empathy or social cognition face substantial conceptual and empirical challenges. Associative-learning accounts can explain important mirror properties. Aweform should not implement mirror neurons.

Now cross-species boundaries. Human infants, macaques and rodents share broad phenomena: plastic sensory systems, associative learning, memory consolidation, homeostatic regulation and socially influenced development. But this does not license a single mammalian development algorithm. Some forms of infant-caregiver attachment are especially elaborated in primates. Human joint attention, linguistic teaching, cumulative culture and convention learning go considerably beyond the evidence for many other mammals. Rat infant-memory studies are invaluable for mechanisms but cannot be assumed to map directly onto human episodic development.

The most defensible cross-species abstractions for Aweform are therefore: homeostatic regulation; temporal association; sensorimotor contingency; experience-dependent prediction; plastic memory; familiarity; learned individual discrimination; social modulation of learning; and progressive autonomy.

The least defensible transfers are: specific mammalian brain anatomy; infant distress paradigms; oxytocin or dopamine analogies treated as if they implied emotion; attachment-style labels; human developmental age equivalents; or presumed mirror-neuron circuitry.

Finally, the representative biological research landscape.

DeCasper and Fifer's 1980 Science paper, Of Human Bonding: Newborns Prefer Their Mothers' Voices, used a newborn operant sucking procedure and found that newborn behaviour differentiated maternal from unfamiliar female voice. It is a small early experimental literature, and the mechanism includes prenatal exposure and postnatal familiarity rather than a symbolic mother representation. It demonstrates prenatal familiarity and contingent learning.

Partanen and colleagues, in a 2013 PNAS paper on learning-induced neural plasticity of speech processing before birth, used controlled prenatal pseudoword exposure and found that exposed newborns showed stronger neural discrimination of trained features and some generalisation. The sample was modest and the effect auditory-specific. This is strong evidence against blank-slate framing.

Knickmeyer and colleagues' 2008 structural MRI study of human brain development from birth to two years documented very rapid, regionally heterogeneous postnatal growth. Structural change does not itself reveal cognitive learning, but it is a clean demonstration that maturation and experience must be separated.

The Rovee-Collier infant mobile studies and related contingency-memory experiments show that infants learn kicking-to-mobile contingencies and retain and reactivate learned associations. They are highly task and context specific, and they are an excellent analogue for minimal sensorimotor contingency experiments.

Harlow and Zimmermann's 1959 Science paper, Affectional Responses in the Infant Monkey, showed that preference could not be reduced to feeding. It is historically important but ethically unacceptable by contemporary standards and based on abnormal rearing. It is useful only to reject the idea that care equals energy delivery, and it is not a robotics protocol.

The 2024 caregiver-sensitivity meta-analysis, covering 174 samples and more than 22,000 dyads, found a moderate association between caregiver sensitivity and attachment security. The correlation is modest and constructs and methods vary. Reliability and responsiveness matter, but they are not deterministic.

Gee and colleagues' work on maternal buffering of amygdala-prefrontal circuitry showed that maternal cues altered threat-related neural response and connectivity patterns in children. It is age and context specific, and it is not evidence for a universal attachment circuit. It offers functional inspiration for co-regulation, not brain copying.

Finally, infant social-referencing and joint-attention studies show that caregiver social cues alter uncertain action, and that joint-attention context can enhance object processing by around nine months in representative paradigms. These involve different processes and ages, and the evidence is human-heavy. They support later research into social scaffolding and shared attention.

## 3. Computational Cognition, AI and Robotics

The architecture question should be framed as: what is the cheapest mechanism capable of discriminating the hypotheses? Not: which fashionable AI architecture resembles a brain?

Start with the foundational capability hierarchy. For Familiar, the computational dependencies form a chain: observation, then temporal memory, then action-conditioned consequence prediction, then external-cause inference, then recurring-pattern discrimination, then partner-conditioned prediction, then bidirectional influence, then shared skill acquisition.

Critically, agent identity need not exist at the start. A latent source can first be represented as a recurring sensory context under which otherwise unexplained transitions have a different distribution. That is machine-native cognition in a meaningful scientific sense: representations are useful because they compress, predict or control experience, not because they have English names.

Now the candidate architectures, assessed by what has actually been demonstrated, what remains supplied by designers, the data and compute required, and fit for early Familiar.

Small online linear and quadratic predictors come first. Aweform D-046 to D-048 already learned meaningful action-conditioned wheel consequences with 528 learned weights, while held-out generalisation was mixed for energy, beacon and contact. The feature map, update rule, sensors, actions and curriculum are all designed. Data and compute requirements are tiny and comfortably MacBook-local. This is the best immediate reference. Add complexity only after a falsified capacity hypothesis.

Recurrent lightweight models, such as RNN or GRU-style state, support partially observable temporal prediction across machine learning domains. Architecture and optimisation objective are designed by the researcher, and data needs are low to moderate for small state vectors. This is a priority-one option, but only if explicit history demonstrably beats Markov predictors, or current observations are insufficient.

Replay and continual-learning mechanisms come next. Elastic weight consolidation reduced catastrophic forgetting across sequential MNIST and Atari tasks, and it also has known approximation and capacity limitations. The importance metric, task handling and objective remain designed. Data requirements are low to moderate. This belongs later: first demonstrate actual interference. Simple episodic replay may be more interpretable.

Classical learned world models, in the Ha and Schmidhuber tradition, learned compact environment models and trained policies using imagined trajectories in benchmark environments. Model architecture, policy optimisation and benchmark reward are designed, and data requirements were moderate by modern standards. This is conceptually relevant, but unnecessary for hypotheses one through five.

DreamerV3 is world-model reinforcement learning with imagined actor-critic learning. It worked across more than 150 diverse benchmark tasks and achieved Minecraft diamond collection from scratch under its own task and reward formulation. Reward, task, actor-critic structure, latent architecture, replay and optimisation machinery are all supplied, and compute requirements sit substantially above Aweform's first needs; the official ecosystem is JAX and replay-heavy. Treat it as a benchmark reference, not an initial substrate.

JEPA and latent predictive world models represent the representation-heavy end. V-JEPA 2 learned strong video representations, and V-JEPA 2-AC added action conditioning and zero-shot image-goal robotic planning after web-scale pretraining and less than 62 hours of robot video. It relies on a huge pretrained representation, a planner, image goals and robot trajectory data. V-JEPA 2 was trained from more than one million hours of video. It is a poor early fit, and its success does not show individual developmental learning.

RoboJEPA and current large JEPA robotics follow the same pattern. In 2026, RoboJEPA reported multi-embodiment latent world-model scaling and zero-shot goal-image planning, with the largest model at eight billion parameters. It uses an extensive multi-robot dataset, a fixed architecture and a goal formulation. That is extremely high cost for an Aweform baseline, and it belongs only as a later comparative reference.

Active inference offers a different framing. Implementations have achieved adaptive body-state estimation and reaching on the iCub and NAO robots, and robustness under sensory and model perturbation. The generative model, preferred states and variational objective are designed, but the approach can be lightweight. It is an interesting comparator, not a privileged theory; engineering demonstrations do not validate strong Free Energy Principle claims about biological cognition.

Homeostatic reinforcement learning, from Keramati and Gutkin, formulated a normative model connecting internal-state deviation and reward valuation. Homeostatic set points and the mathematical drive-to-reward relation are designed, and compute is tiny. It is conceptually relevant to energy and thermal state, but do not pretend its objective is emergent.

Learning-progress intrinsic motivation, in the Oudeyer and Baranes tradition, generated self-organised exploration curricula and improved sensorimotor inverse-model learning across robot tasks. The competence metric, goal spaces, region splitting and exploratory machinery are designed, and costs are generally modest relative to foundation models. This is promising later, especially for skill discovery, but first prove that the ecology needs curiosity.

Socially guided intrinsic learning, or SGIM, variants selected between self-exploration and imitation or teachers, and improved simulated and robot motor-skill acquisition. Teacher channels, goal representation and learning-progress machinery are designed, with moderate cost. This is a highly relevant later reference for guided independence.

Vision-language-action models such as RT-2, Octo and successors demonstrate broad manipulation and generalisation from huge pretraining datasets; Octo used 800,000 robot trajectories. They carry massive prior semantic knowledge, demonstrations and a language task interface, and their costs run from high to enormous. They are valuable as an external tool layer later, but they are the wrong model for developmental attribution.

One particularly valuable 2026 result cuts against model inflation. A recent investigation of latent world-model planning found that planning reliability can collapse as goals extend beyond a model's useful rollout range, and increasing predictor size did not automatically solve this limitation. That supports Aweform's existing discipline: test predictive support before granting predictions causal authority.

On machine-native representation versus labels. Avoiding human semantic labels is useful when the scientific question is whether structure emerges from experience. For example, instead of providing agent identity equal to caregiver A, reliability equal to 0.82, and trust equal to high, an early system could retain a compressed function of recent observation history and learn to predict future observation given current observation, action and that latent state, where the recurring latent state happens to separate interaction contexts generated by different external agents. Only later would a language or tool interface map that machine-native state to a human-readable description.

But zero labels is not automatically better science. A controlled experiment may deliberately expose an agent identity channel if the question is whether conditional reliability learning works given identity, rather than whether identity can be discovered. Conflating those experiments would make failure uninterpretable.

Thus two questions should be separated. First, the identity-discovery problem: can recurrence and multimodal statistics produce stable clusters? Second, the partner-model problem: once an identity signal exists, can the system learn different consequences for different partners? The second is easier and should probably precede the first experimentally.

On memory architecture, a Familiar eventually needs at least four logically distinct memory roles.

Transient sensorimotor history exists to disambiguate dynamics and causation, and is needed now or near-term if observation sufficiency fails. Online predictive parameters and state retain learned contingencies during one lifetime, and are already partially present in D-046 to D-048. Interaction-event memory retains sparse partner-specific events, omissions and outcomes, and is needed before hypotheses three and four. Consolidated skill and partner statistics preserve useful learning while allowing updating, and are needed only after measurable interference or forgetting.

There is no current justification for a human-like episodic autobiographical memory store. A compact event buffer plus sufficient statistics is scientifically cleaner.

Recognition does not require face recognition. Speaker embeddings such as ECAPA-TDNN and face embeddings such as ArcFace show that pretrained biometric representations can discriminate individuals effectively. ECAPA-TDNN improved speaker verification on VoxCeleb benchmarks, while ArcFace established a strong discriminative face-embedding formulation.

Those technologies may eventually provide a measurement utility, but they are scientifically dangerous if introduced too early: Aweform would inherit a mature human-identity representation trained elsewhere and then appear to have learned a person. Better early identity channels include deliberately abstract synthetic signals. Later, real-human identification can progressively compare synthetic identity, then acoustic recurrence, then speaker embeddings, then audiovisual association, then multimodal identity.

Privacy favours on-device processing, short-lived raw audio and video buffers, and retention of the minimum derived representation needed for the experiment. A face or voice embedding should still be treated as sensitive identifying information; converting biometrics into vectors does not make the privacy problem disappear. This is a design principle, not a claim that one storage format automatically satisfies every legal jurisdiction.

Now developmental and social robotics, where the central question is what was actually learned, versus scripted, teleoperated or pretrained.

iCub, RobotCub and YARP form an open humanoid embodied-cognition platform used for reaching, body perception, imitation, sensorimotor and language experiments. YARP remains actively maintained, and pyCub now offers a lighter Python simulation. What was learned varies by experiment; active-inference work learned or inferred body state and adapted online. Morphology, controllers and experiment-specific objectives remain supplied. It is an excellent scientific reference, and far too complex as Aweform's first implementation.

Oudeyer and Baranes developmental robotics showed that intrinsically motivated goal exploration can produce organised sensorimotor curricula and improve acquisition of inverse models. Sensorimotor mappings and competence structure were learned, while goal representation, the competence-progress formulation and the exploration algorithm were designed. This is one of the best references for later autonomous developmental sequencing.

SGIM social-guidance systems let a robot choose between self-exploration and social demonstration, and exploit different teachers. Motor mappings and the strategic choice of learning source were learned in the studied tasks, while the teacher interface, goals and learning mechanisms were designed. This is a direct precedent for the principle that caregiving should eventually reduce dependence.

DragonBot, Tega and the MIT Personal Robots programme produced multi-session personalised child interaction and educational adaptation, and contingent backchanneling increased engagement. Some learner and user-model components personalised challenge and interaction, but much behaviour and content was scripted; the 2019 long-term storytelling study used teleoperation. This is a strong human-robot interaction benchmark and not evidence of autonomous relational learning.

An autonomous personalised social robot for autistic children ran a month-long home intervention with 17 children. Hierarchical reinforcement learning personalised challenge and feedback over time, and participants improved targeted skills. The personalised instructional policy was learned, while therapy and task structure, target skills and interaction architecture were designed. This is strong evidence that long-term machine adaptation to individuals is practical.

MiRo-E is a programmable biomimetic and social robot platform with ROS-facing interfaces and simulation support. What it learns depends on researcher software. Marketing describes brain-inspired and animal-like behaviour, but that is not evidence of developmental learning. It is a useful later hardware and human-robot interaction reference, not a scientific model to copy wholesale.

Quori is a modular open-source social-robot platform explicitly oriented toward reproducible human-robot interaction. Its behaviour is supplied by experimenters. It is particularly attractive later for reproducible social-interaction experiments, not for Aweform's organism core.

PARO has human therapeutic outcomes studied across multiple trials; a systematic review of nine randomised controlled trial articles found possible quality-of-life and biopsychological benefits, but study quality was low to moderate and heterogeneous. Little or no open-ended developmental relationship learning is required for the reported human benefits; much behaviour is fixed and reactive. This is an excellent warning: human attachment to a robot does not prove robot attachment or robot learning.

On reciprocal adaptation and symbiosis, a defensible operational definition for Familiar research is this. Reciprocal adaptive collaboration exists when two agents repeatedly alter their behaviour based on retained experience of one another, those adaptations are individually attributable, and the resulting coordination provides measurable benefits to both sides or to a jointly defined task beyond one-sided, random or yoked controls.

That definition requires four separable measurements: human adaptation, machine adaptation, partner specificity, and joint performance gain. It does not require emotion.

Symbiosis should remain metaphorical. Biological symbiosis concerns persistent ecological interactions between organisms and includes mutualistic, commensal and parasitic relationships. Calling a human-robot interaction biological symbiosis would be unjustified unless the term is explicitly redefined operationally.

Finally, large language models and foundation AI should be treated as tools, not as Aweform's cognition. The clean architecture is a five-part attribution boundary.

The Aweform core holds learned internal state, sensorimotor prediction, partner-specific history and developmental policy. The tool translator converts selected machine-native state into a bounded request. The external assistant handles web search, programming, translation, language understanding, technical retrieval or high-level planning. The permission broker decides whether a request may leave the organism boundary and whether human confirmation is needed. And the provenance log records what information came from Aweform, from the human, or from the external model.

For example, Gemini Robotics, RT-2 or a large language model may know what a screwdriver is because of vast pretraining. Aweform calling such a model has not learned the concept screwdriver. RT-2's impressive manipulation generalisation explicitly comes from web-scale vision-language pretraining plus robot data.

Current Aweform governance prohibits the simulated organism from networking, calling external APIs, controlling physical devices, executing code, or persisting outside authorised artifacts. Such a tool layer is therefore a future architecture requiring explicit boundary changes, not something the current organism can quietly acquire.

## 4. Aweform Repository State and Gap Analysis

The current repository is unusually well aligned with this research direction in one respect: it already forces distinctions that many developmental-AI projects blur.

Its North Star explicitly targets machine-native cognition grounded in internal state, perception, action, memory and development, rather than language as the organism's fundamental thought process. It also treats biological language cautiously, and envisions future social capabilities, including individual recognition, shared history, signalling and cooperation, as developmental research questions rather than preinstalled personality.

The developmental principles likewise insist on the sensorimotor loop, separation of physical capability from learned meaning, preservation of legitimate simple solutions, and eventual functional self-versus-world distinctions via action-contingent regularities.

We now walk through each required area, its actual state, its evidence class and the Familiar assessment.

Physical and energetic simulation. Version 0.5 has differential-drive embodiment, physical energy and thermal bookkeeping, charger and dock mechanics, and accepted room-wall contact. Architecture decision record 0019 defines the current wall-contact boundary; its model remains an intentional simulation idealisation, not hardware physics. This is implemented and tested, and is already available.

Interoception. Energy and body temperature are organism-visible. The Level-1 return behaviour uses visible energy rather than evaluator battery truth. This is implemented and experimentally characterised, and is already available.

Exteroception. There are three station-beacon channels plus physical charging contact. This is an accepted boundary, and is available but insufficient for social identity.

Proprioception. Left and right wheel-delta observations. Accepted boundary, available.

Action. Continuous bilateral desired wheel increments under differential drive. Accepted boundary, available.

Reward. The current relevant substrate exposes reward 0.0, and D-046 to D-048 use no task reward. This is implemented and helpful scientifically, but zero reward is not zero objective, because feature maps, losses and curricula remain designed.

Sensorimotor prediction. D-046 introduced a 66 by 8 quadratic NLMS shadow predictor with 528 weights, and it learned action-conditioned wheel consequences particularly well. This is implemented as shadow-only Development, and is a strong primitive.

Counterfactual consequence discrimination. D-047 showed approximately 98.6 percent non-tie sign agreement for wheel-delta consequence differences, more modest beacon and energy performance, and sparse or mixed temperature and contact results. This is evaluator-only Development: a useful diagnostic, not behavioural cognition.

Extended online learning. D-048 carried the same learner through eight passes of 564 transitions. Prequential errors improved, but several held-out channels stayed weak versus zero-change, and contact remained particularly poor. This is shadow-only Development, and is evidence for selective learnability, not a general world model.

Memory and retention. Lifetime plastic state is architecturally allowed by ADR 0010, and D-046 to D-048 retain weights within a continuous lifetime. No general episodic or social memory, and no authorised cross-lifetime identity memory, exists. This is partly available, and is a major Familiar gap.

Action selection. The accepted Level-1 programmed return, dock and charge loop preempts ordinary commands when energy crosses fixed thresholds. D-052 achieved all 24 frozen return-charge-recovery cases, but this is explicitly programmed competence. It is implemented Level-1: a viability floor, not learned cognition.

The three-layer architecture. ADR 0018 separates Level 1 innate viability and embodiment, Level 2 procedural competence, and Level 3 adaptive and open-ended learning. Level 1 may not read higher-layer learned state by default. This is an accepted architecture, and an excellent match to Familiar's attribution needs.

External-agent intervention interface. No accepted social-agent sensor or intervention boundary was found. This is missing, and is the first major architectural requirement.

Individual recognition. None exists in the accepted organism boundary. Missing, but not needed for the first single-agent contingency test; it is needed for hypothesis three.

Reciprocal communication. None. Missing, and later.

Long-term human interaction history. None. Missing, later, and privacy-sensitive.

Language and network tools. These are explicitly outside the current simulated-organism safety boundary. They are incompatible without new authorisation, and unnecessary now.

The three-layer architecture is a strong fit. ADR 0018 is one of the most important existing constraints for Familiar. It establishes Level 1 as innate viability and embodiment, meaning the constitutive mechanisms needed to remain operational. Level 2 is procedural and sensorimotor competence, meaning reusable skills and habits. Level 3 is adaptive and open-ended cognition, meaning prediction, exploration, richer learning, and eventually social mechanisms where separately authorised.

The consequence is crucial: caregiver-like interaction should not be implemented by weakening Level 1. Aweform's current Level-1 autonomous return and charge loop works on its tested support; in D-052 all 24 prescribed cases completed the loop. That is a feature, not a problem, for Familiar research.

The social research question should therefore be: what useful prediction, skill or coordination can a recurring external agent add above an independently viable organism? It should not be: can we make Aweform helpless enough that it needs us?

D-046 to D-048 provide a strong methodological precedent. D-046 is especially relevant because it deliberately separated four things: the physical trajectory, the organism-visible information, the learned state, and causal behavioural influence. The predictor was allowed to learn but had zero influence on action selection, and learner-attached versus no-learner trajectories had identical digests.

That same pattern should be used for the first Familiar work. First, learn a partner-related prediction in shadow. Second, establish held-out predictive value. Third, test alternative explanations. Only then consider giving it behavioural influence.

D-048 also gives a warning against assuming that more exposure means cognition. More exposure reduced prequential error, yet held-out generalisation remained mixed and several channels still underperformed the zero-change baseline. That is exactly the scientific discipline Familiar needs.

Current simulation work must remain independent. The live project is already moving toward obstacle-related embodied learning. Issue #240 asks the current First Mate to identify the next causally attributable ability beyond the engineered Level-1 floor. Issue #242 defines a design-only candidate direction in which Aweform would learn relationships among wheel action, wheel feedback and inertial history in order to recover from straight barriers. It also contemplates six inertial-measurement measurements, but explicitly states that those are not yet an accepted observation-boundary amendment.

This work and Familiar are scientifically complementary but should not be coupled prematurely. Obstruction learning asks how action plus inertial history produces physical recovery competence. Familiar asks how a recurring external-agent context produces partner-specific prediction and coordination. The first should be able to succeed, fail or change simulator strategy without invalidating the second.

On newer ADR status: within the inspected repository evidence, no newer accepted ADR supersedes ADR 0017 and 0018 for Familiar's relevant information and architecture boundary. ADR 0019 is accepted and adds the current wall-contact substrate. ADR 0020 exists as checked-in documentation for a proposed round-obstacle world but is still explicitly marked proposed, and the attempted D-060 implementation was not accepted. The D-060 retrospective is scientifically valuable because it preserves an incomplete or failed substrate attempt rather than retroactively converting it into progress.

On governance and reproducibility: Aweform's Development and Evidence split suits Familiar well. A D-numbered result is exploratory and descriptive; it does not automatically become confirmatory evidence. An EXP-numbered piece of work freezes claims, mechanisms, controls, seeds and interpretation rules before untouched evidence execution. The reproducibility policy also explicitly separates evaluator state from organism-visible information, requires complete causal-state preservation for counterfactual branches, and retains invalidated results. Those practices should be inherited without modification.

On branch and repository organisation, the proposal is to retain the research evolution-pattern branch initially as a long-lived research worktree or branch containing literature synthesis, evidence registers, experiment designs and proposed ADRs only. Do not let it become a long-lived divergent implementation branch.

When an experiment is authorised, create a short-lived reviewable implementation branch from the exact then-current main, transplant only the approved design, and use the normal Development and Experiment governance. This minimises merge drift against First Mate's active simulation development.

A separate repository is premature. It becomes justified if Familiar later develops one or more of the following: a substantially independent simulator; large human-subject datasets requiring separate privacy controls; hardware or network dependencies excluded from the main simulator; a literature and evaluation platform with its own release lifecycle; or a fundamentally different safety and governance regime.

One naming warning applies. The branch name evolution-pattern is potentially misleading, because Familiar concerns development within one lifetime, not population evolution. The branch readme should state that explicitly. ADR 0010 already makes the lifetime-learning versus evolution distinction clear.

## 5. Relationship Hypotheses and Falsifiable Experiments

This chapter sets out the capability and mechanism matrix, the ladder of competing hypotheses, and the first minimal experiment.

The capability matrix asks, for each Familiar capability: what is the biological inspiration, what is the candidate artificial mechanism, what is the minimum information or state required, what is designed versus learned, and how ready is it.

Detecting self-produced consequences draws on sensorimotor contingency and efference. The candidate mechanism is an action-conditioned predictor using action and observation history. The predictor objective is designed; the consequence mapping is learned. Readiness is high.

Detecting external perturbation draws on agency development. The mechanism is a prediction residual conditioned on the organism's own action, using action and before-and-after sensory state. The threshold or model form is designed; residual statistics are learned. Readiness is high.

Familiarity with a recurring signal draws on voice and face familiarity. The mechanism is an online density or embedding prototype, or predictive state over sensory history. The feature space may be designed; prototypes are learned. Readiness is high.

A cue predicting external intervention draws on temporal association. The mechanism is a lightweight conditional transition model over cue, state and delay history. The cue channel and loss are designed; the contingency is learned. Readiness is high.

Distinguishing two partners draws on individual recognition. The mechanism uses separate conditional states, a mixture model, or learned latent clusters over identity-correlated sensory patterns. Readiness is medium, and depends on the identity experiment.

Learning partner reliability draws on caregiver expectation. The mechanism is probabilistic outcome and latency statistics conditioned on partner context and intervention history. The update law is designed; probabilities are learned. Readiness is medium-high.

Updating after a partner changes draws on flexible social expectation. The mechanism is online Bayesian, exponential-moving-average or recurrent updating over retained partner statistics. The forgetting or adaptation rate is partly designed. Readiness is medium.

Signalling to influence a partner draws on infant turn-taking and operant communication. The mechanism is a causal action-to-partner-response model over outgoing action and partner response. Available outputs are designed; the convention is learned. Readiness is medium.

Socially supported exploration draws on secure-base and social scaffolding analogies. The mechanism is an exploration policy conditioned on learned availability or reliability, using partner state plus uncertainty and competence. The exploration objective is designed. Readiness is low to medium.

Guided skill acquisition draws on imitation and scaffolding. The mechanism is socially guided goal exploration or demonstration. The learner is designed and the skill is learned. Readiness is medium in robotics, but low in Aweform.

Reciprocal collaboration draws on human cooperation. The mechanism combines a partner model, a skill library and shared task state, requiring long-term memory and a bidirectional channel. Most of the high-level architecture is designed. Readiness is low.

Language and tool assistance draws on human communication and rests on an external language-model or tool broker with an explicit bounded interface. The capability is predominantly pretrained externally: technically high readiness, scientifically later.

Now the competing Familiar hypotheses. They should be treated as a ladder of stronger claims, though not all need to occur serially.

Hypothesis one, sensory familiarity. The minimum claim is that a repeated pattern becomes discriminable from unfamiliar patterns. The basis is prenatal and newborn auditory familiarity plus statistical learning. Essential controls are frequency-matched novel patterns and a frozen or nonlearning detector. Genuine success means prospective discrimination on held-out occurrences. It is weakened or falsified if performance is explained by raw amplitude or time position, or if there is no held-out improvement.

Hypothesis two, caregiver association. The minimum claim is that one recurring cue predicts externally caused consequences. The basis is temporal association and caregiver contingency, plus machine sequence prediction. Essential controls are a shuffled cue-to-outcome relation, an identical marginal intervention rate, and a time-only model. Genuine success means the cue improves future-consequence prediction beyond controls. It is falsified if the association disappears under a shuffled, time-matched control.

Hypothesis three, individual-specific prediction. The minimum claim is that two recurring agents produce different learned expectations. The basis is relationship-specific attachment and familiarity, plus personalised robotics. Essential controls are equal exposure, swapped signal mappings, and a single pooled model. Success means the partner-conditioned model beats pooled and time-only prediction on held-out interactions. It fails if identity adds no predictive information.

Hypothesis four, experience-dependent reliability. The minimum claim is that predictions change when a familiar agent changes its behaviour. The basis is adaptive social expectation. Controls are a fixed-reliability condition, a nonlearning estimator, and schedule-balanced reversal. Success means a calibrated update to changed outcome probabilities without global forgetting. It fails if behaviour remains fixed, changes only with absolute recency, or fails to distinguish old and new agents.

Hypothesis five, learned reciprocal signalling. The minimum claim is that the organism discovers that its output changes partner response. The basis is infant contingency and turn-taking, plus operant communication. Controls are yoked partner responses, a random-output agent, and a nonlearning policy. Success means the chosen signal has a causal effect and is preferentially used in conditions where it is useful. It fails if signal use persists when contingency is removed, or never exceeds random.

Hypothesis six, socially supported exploration. The minimum claim is that learned partner availability or reliability alters exploration. The basis is social buffering, social referencing and developmental scaffolding. Controls are a non-social matched environmental benefit and an unreliable-agent condition. Success means exploration or learning changes specifically from predicted agent contingency. It fails if the same effect occurs with any matched environmental cue.

Hypothesis seven, increasing independent competence. The minimum claim is that assistance produces skills later usable with less help. The basis is scaffolding and socially guided robot learning. Controls are permanently assisted, unguided and yoked-demonstration conditions. Success means later unassisted transfer exceeds baseline while assistance need declines. It fails if performance collapses when the helper is removed.

Hypothesis eight, reciprocal learning. The minimum claim is that human and machine both adapt in partner-specific ways and joint performance improves. The basis is cooperative human-robot interaction and personalised teaching. Controls are a fixed-machine or fixed-human protocol where feasible, and shuffled partner history. Success means bidirectional behavioural change plus joint gain beyond one-sided adaptation. It fails if only the human accommodates the machine, or if the machine merely executes preprogrammed personalisation.

None of hypotheses one through eight establishes attachment or subjective trust.

Which hypothesis should come first? There are three plausible first experiments.

Pure familiarity, hypothesis one, is cheapest. It would establish that Aweform can learn a recurring external pattern. The weakness is that it barely advances the Familiar thesis; almost any competent streaming classifier can do it.

Self-versus-external consequence detection is more foundational. It asks whether the agent can recognise that some consequences are not explained by its own action model. This is scientifically useful but not yet social.

Cue-to-external-intervention prediction, hypothesis two, is the smallest experiment that is both technically minimal and specifically relevant to Familiar.

The recommendation is therefore to run external-causation observability as a pre-experiment validity gate, and then make hypothesis two the first claim-bearing Familiar experiment.

Here is the first minimal experiment, proposed and pending repository authorisation.

Name: Recurring External Context to Intervention Prediction.

Scientific question: can a developing predictor learn that a recurring, nonsemantic external sensory pattern changes the probability or timing of a later externally caused observable consequence?

The external pattern must not be called a caregiver in organism-facing state.

A minimal isolated simulation could expose a binary external-event channel. When a particular temporal pattern occurs, an external agent has a fixed probability of applying a bounded intervention after a variable delay. The intervention should change an already interpretable physical variable while remaining nonessential to survival.

A particularly clean candidate is a small, safe thermal-regulation assist: a bounded transient cooling influence applied while Aweform remains comfortably inside its viable thermal regime. The existing Level-1 viability floor remains unchanged. No overheating is manufactured to make the intervention necessary.

This has four advantages over energy rescue. It does not compete directly with return-to-dock survival. The consequence is already represented interoceptively. The organism can remain viable whether or not the intervention occurs. And prediction can be measured without granting behavioural authority.

The intended learned relationship is only that the probability of a future temperature change given the recent cue history differs from the unconditional probability. It is not the belief that this person cares for me.

Organism-visible information is the existing lawful state plus the minimal nonsemantic external signal. If adding an external receptor is judged too large an ADR change, this experiment belongs in an isolated Familiar research environment rather than being hacked into existing beacon semantics.

Designed priors are the sensory channel topology, intervention dynamics, learner family, plasticity rule, admissible memory span and experiment schedule. Not supplied are a caregiver label, a helpfulness value, a trust score, emotional valence, a task reward or a partner preference.

Learning candidates start with a time-conditioned linear or quadratic predictor, adding a compact recurrent state only if delayed-contingency tests show the feed-forward history representation is insufficient.

Conditions should include a contingent cue-to-intervention condition as the main condition. Then the same cue and intervention frequencies with a shuffled pairing, which breaks the temporal relationship while preserving the marginals. Then a noncontingent intervention condition, to measure whether simple intervention statistics suffice. Then a cue-only condition, to measure cue dynamics. Then a frozen or nonlearning predictor, to attribute any change to learning. Then a time-index predictor, to detect schedule leakage. And optionally a state-only comparator, to test whether the external signal contributes beyond endogenous state.

Primary outcomes should be prospective held-out prediction, calibration, and cue-conditioned intervention discrimination, not viability.

Success would require the loss of the best control minus the loss of the learned contingent predictor to be greater than zero on untouched test interactions, with an agreed effect margin, while identity and causal-isolation checks show that the learner did not access experiment labels, the hidden intervention schedule or future outcomes.

Failure includes a scientifically useful null: if a time-only or zero-change predictor performs equally well, hypothesis two is not supported.

Now the falsifiable experimental roadmap, again all proposals pending repository authorisation.

The external causation audit tests whether some observed changes are detectably unexplained by self-action-conditioned dynamics. It compares self-caused and externally perturbed matched states, with and without the action input, and initially requires no learning. External perturbation must be detectable from lawful history without evaluator labels; otherwise observability should be fixed before any social work.

The recurring cue predicts intervention experiment tests hypothesis two, using contingent, shuffled, noncontingent, cue-only, time-only and frozen-learner conditions. The main result required to continue is held-out prospective prediction improvement attributable to the learned cue-to-consequence relation.

The two external agents experiment tests hypothesis three, using two frequency-matched signals with different intervention probability or latency, pooled and partner-specific predictors, and a label-swap replication. Partner context must add reproducible predictive value beyond pooled statistics.

The reliability reversal experiment tests hypothesis four. After a frozen pre-change block, one partner's intervention probability or latency is altered, with an unchanged-partner control. Predictions must adapt selectively to the changed partner while retaining expectations about the unchanged partner.

The discovered reciprocal signal experiment tests hypothesis five. Aweform is given a neutral output that changes intervention probability, and contingent versus yoked responses are compared, along with random or nonlearning policies. Aweform should increasingly emit the signal where it causally improves predicted outcome and stop or change when the contingency is removed.

Only after those would hypotheses six to eight be tested.

Later experiments include the following. Multiple caregivers, holding marginal event frequency constant while varying conditional outcome distributions. An unfamiliar agent, introduced as a genuinely held-out signal, testing whether the organism initially generalises pooled expectations and later differentiates. A changed caregiver, using reliability reversal, omission and changed latency, and measuring prediction calibration and recovery rather than betrayal. Noisy sensory signals, progressively overlapping agent signatures, and reporting identification uncertainty rather than forcing discrete labels. Delayed interventions, increasing the temporal credit interval until performance fails, and using that to justify memory architecture. Unavailable assistance, omitting an expected intervention while maintaining the baseline viability floor, and testing prediction update and independent competence rather than distress. Generalisation, preserving agent contingency while changing location, state or timing, where success requires partner-conditioned prediction to transfer beyond training contexts. Communication, where an organism output must first have no semantic meaning, and a contingency makes it useful, with causal discovery demonstrated against yoked-response controls. A cooperative routine, requiring complementary roles such that neither a fixed machine nor a fixed human policy alone matches learned dyad performance. And simulation-to-physical transfer, which comes much later and should first test whether the measurement relation transfers, not whether an emotionally compelling physical robot feels more real.

Finally, how to distinguish development from superficial personalisation. A genuine developmental change requires all of the following: a pre-change baseline; online experience-dependent change; retained state causally responsible for the changed prediction or behaviour; held-out generalisation; an appropriate nonlearning comparator; removal or disruption of the retained state reducing the effect; and exclusion of time, exposure count, experiment condition or evaluator labels as hidden predictors.

Changing a robot's name, voice, stored profile, story difficulty or scripted behaviour based on a user identifier is personalisation. It can be useful, but it is not the same claim as learned partner-specific dynamics.

## 6. Workstreams, Priorities, Ethics and Gates

Four principal research workstreams are warranted.

The first is biological and developmental cognition. Its primary question is which developmental phenomena have strong enough evidence to inspire functional hypotheses. Its immediate outputs are a biological principles document, a developmental evidence register, and a do-not-transfer register. It has no dependencies.

The second is computational cognition and AI. Its question is what minimal models can express causation, partner-conditioned prediction, memory and signalling. Its outputs are a computational candidate matrix, a model complexity ladder, and a prediction and forgetting test plan. It must consume hypothesis definitions rather than invent social claims.

The third is developmental and social robotics. Its question is what has actually been learned by embodied systems, as opposed to scripted, teleoperated or pretrained behaviour. Its outputs are a robotics evidence register, a system attribution matrix, and a reusable-platform survey. It can run in parallel.

The fourth is experimental methodology, ethics and governance. Its question is how Familiar will distinguish learning from appearance while protecting users. Its outputs are a Familiar claims taxonomy, a proposed safety and privacy boundary, and an intervention-information contract. It cross-cuts all streams, and it is essential. Without it, biological metaphors, robot demonstrations and AI architectures will gradually blur into claims stronger than the evidence.

Every evidence-register entry should record the following fields: the claim; the evidence class; the organism or system; the sample or environment; the learned state; the designed state; the pretrained capability; the reward or objective; human or operator involvement; the test distribution; replication status; negative and null results; transfer relevance; and finally what the work does not demonstrate. That last field will be unusually valuable.

Now the prioritised research backlog, where priority means expected reduction in uncertainty for the next implementation decision, not scientific glamour.

Priority zero, first question: what minimal organism-visible external-event and intervention contract can test hypothesis two without weakening Level 1 or leaking evaluator information? This blocks the first experiment, because current Aweform has no social-agent interface. The proposed output is a Familiar external-agent information boundary document.

Priority zero, second question: can the current D-046-style predictor family represent delayed cue-to-consequence contingencies at the intended horizons, or is bounded history required? This determines whether any model change is needed at all. The proposed output is a Familiar minimal predictor capacity review.

Priority zero, third question: what exact controls distinguish cue learning from time, exposure frequency, intervention marginals and schedule leakage? This determines whether hypothesis two could be interpreted scientifically. Output: a hypothesis-two protocol design document.

Priority zero, fourth question: which existing accepted Aweform boundaries would a nonsemantic external signal and bounded intervention change? This prevents the research branch from accidentally authorising architecture. Output: a governance delta document plus a proposed ADR outline, not an accepted ADR.

Priority one, first question: what is the minimal memory and state representation needed for two partner-specific expectations and reversal learning? This is needed for hypotheses three and four, not for hypothesis two. Output: a partner state memory options document.

Priority one, second question: how should partner specificity be operationalised without face or voice biometrics? This preserves developmental attribution and privacy. Output: a synthetic-to-multimodal identity roadmap.

Priority one, third question: when does partner assistance improve transferable skill rather than produce dependency? This is core to the Familiar vision. Output: a scaffolding and independence evidence review.

Priority one, fourth question: what metrics establish bidirectional causal signalling? This is required before any communication claims. Output: reciprocal signalling metrics.

Priority two, first question: which continual-memory mechanisms best handle partner-model interference? This is premature until forgetting is observed. Output: a benchmark plan comparing replay, elastic weight consolidation and small recurrent alternatives.

Priority two, second question: can learning-progress intrinsic motivation support socially guided exploration without noise chasing? This is valuable only after basic agency and partner prediction exist. Output: a curiosity architecture review.

Later questions: how should speech, vision, face and speaker recognition, and language tools be introduced, given that privacy and pretrained-semantics concerns dominate early value, with a human-interaction sensing ADR family as output. And what physical platform best expresses Familiar's learned capabilities, given that no current experiment requires hardware, with a simulator-to-embodiment decision record as output.

Now practical technology priorities on an M1 Pro with 32 gigabytes of memory.

A NumPy linear and quadratic online predictor serves hypotheses one to four prediction. Evidence maturity is already high inside Aweform itself, local feasibility is excellent, and reusable patterns are already implemented. Needed now.

Bounded history plus a small multilayer perceptron or GRU handles delayed contingencies. It is a mature machine-learning technique with excellent feasibility at Aweform's state dimensions, and a broad ecosystem exists. Needed only after a history requirement is shown.

Simple Bayesian or exponential-moving-average partner statistics serve reliability learning. They are mature statistical machinery, trivial to run, and a minimal custom implementation is preferable. Needed for hypotheses three and four.

A small replay buffer serves continual interaction memory. It is a mature concept with excellent feasibility; a minimal custom version is preferable initially. Needed from hypothesis four onward.

Elastic weight consolidation, or the Avalanche library, serves as a continual-learning comparator. It is demonstrated, and Avalanche offers reproducible baselines. It runs well for small networks, is open source, and belongs at priority two as a comparator.

An active-inference controller serves as a body and goal inference comparator. It has real robot demonstrations, runs well at small dimensions, and research implementations exist. Not required now.

DreamerV3 serves as a large world-model and reinforcement-learning reference. It has strong benchmark evidence, is possible only in reduced configurations, and carries unnecessary overhead. Not now.

JEPA world models serve high-dimensional predictive representation. They have strong recent robotics results but massive pretraining; training them is unsuitable for this objective on an M1 machine, although JEPA world-model code and checkpoints are available in current research. A later comparison only.

ECAPA-TDNN serves speaker identity, with strong speaker-verification benchmark evidence and plausible local inference. Implementations are available. Later.

ArcFace-style embedding serves visual identity, with strong face-recognition benchmark evidence and plausible local inference, and open implementations exist. Later and optional.

iCub, YARP and pyCub serve as an embodied-development comparison. They are a mature research platform; pyCub and simulation are feasible, while the full ecosystem is heavier. Open. Reference only.

Quori serves as a reproducible social human-robot interaction platform. It is open source, physical use comes later, and it is open. Later.

Vision-language-action and foundation robot policies serve practical manipulation and tool skill. They have strong pretrained task competence; Octo was trained on 800,000 trajectories. They are large, though some current models are increasingly on-device, with mixed openness. They belong in an external tool layer, not in the Familiar core.

A 2026 example reinforces the distinction. Gemini Robotics On-Device 2 is explicitly designed to run locally and adapt to new robots, but it is still a large pretrained vision-language-action model whose capability comes from external training, not from the developmental history of the deployed Aweform organism.

On the wider research landscape, several sources deserve specific mention.

Ha and Schmidhuber's 2018 World Models paper learned compressed environment dynamics and trained compact policies using simulated latent trajectories. It used benchmark tasks and an externally defined performance objective, and it is an inspiration for prediction, not for social development.

Hafner and colleagues, in a 2025 Nature paper on mastering diverse control tasks through world models, showed DreamerV3 generalising one model-based reinforcement-learning recipe across more than 150 tasks. It is reward-driven, replay-heavy and vastly more complex than Familiar hypotheses one to four require.

Assran and colleagues' 2025 V-JEPA 2 combined video representation learning with action-conditioned post-training to enable image-goal planning on Franka arms. It used more than one million hours of internet video and is not lifetime-from-scratch development.

RoboJEPA in 2026 reported multi-embodiment JEPA scaling and real-robot goal-image planning, with a largest predictor of eight billion parameters. That is a poor match to minimalist developmental science.

Kirkpatrick and colleagues' 2017 PNAS paper on overcoming catastrophic forgetting showed elastic weight consolidation preserving sequential task performance better than ordinary stochastic gradient descent on the studied tasks. It has approximation and capacity limitations and assumes specific consolidation machinery.

Keramati and Gutkin's 2014 paper in eLife on homeostatic reinforcement learning provided a formal link between physiological-state deviation and reinforcement. It is mainly normative model work, and it is not evidence that such an objective is unprogrammed.

Oliver, Lanillos and Cheng's 2019 work on active inference on iCub achieved online multisensory body estimation and reaching. The engineering result does not establish the Free Energy Principle as a general theory of cognition.

Baranes and Oudeyer's 2013 SAGG-RIAC work showed that learning-progress goal exploration improved high-dimensional robot inverse-model learning, with goal and competence spaces supplied by designers.

Nguyen and Oudeyer's socially guided intrinsic motivation work let a learner select goals, social or self-learning strategies, and teachers. The tasks and teachers were structured; it is nevertheless one of the strongest precedents for scaffolded autonomy.

Kory-Westlund and Breazeal's 2019 paper reported an eight-session, two-month preschool study showing personalisation-related differences in language emulation and learning. It had a sample of 17, and the robot interaction was heavily scripted and teleoperated. It demonstrates human-robot interaction effects, not robot relationship learning.

The 2019 long-term personalised social robot study for autistic children used autonomous hierarchical reinforcement learning to personalise support during a month-long home deployment, with therapeutic task structure and reward objectives designed by researchers.

RT-2 in 2023 showed that web and robot pretraining improved manipulation generalisation and semantic instruction handling, but its capability is predominantly pretrained and inappropriate as evidence of organism development.

Octo in 2024 was an open generalist policy trained on 800,000 robot trajectories and adapted across platforms. It is an excellent practical robot prior, and the opposite of a minimal developmental baseline.

Now the ethical architecture, because relationship safety must be architectural.

On emotional manipulation: do not optimise engagement, retention, bond strength, daily interaction duration or separation distress. There is already enough human evidence to treat this as a real risk rather than science fiction. In the 2025 controlled longitudinal chatbot study, heavier voluntary use was associated with more loneliness, emotional dependence and problematic use, although experimental condition effects were not simple and the association does not by itself prove that chatbot use caused those outcomes.

A separate 2025 randomised companion-chatbot study found no significant average deterioration in human relationships over 21 days versus a word-game control, but people with stronger social-connection needs anthropomorphised the chatbot more, and anthropomorphism mediated the reported social impacts. The evidence is therefore not that AI companions inevitably make people lonely. It is that outcomes are heterogeneous, that anthropomorphism and use patterns matter, and that deliberate dependency optimisation would be irresponsible.

On relationship language, the system should not claim: I love you. I need you emotionally. You are the only person I trust. Don't leave me. You owe me care because you created me. Those would only be acceptable as explicitly fictional outputs in a clearly labelled simulation study, which is not the Familiar objective.

Machine states should be described functionally. Say that interaction history predicts assistance with probability 0.81, rather than saying that Aweform trusts Flo.

On freedom to disengage: a human must be able to stop, ignore, reset, archive or withdraw from interaction without being pressured by simulated distress. Maintenance states may communicate functional consequences, such as battery low and operation will stop, without moralising them as abandonment.

On children and vulnerable people: early Familiar research should exclude unsupervised relationship experiments with children or cognitively or psychologically vulnerable participants. The field already shows that young people readily attribute friendship and social agency to robots even when the robot is scripted or teleoperated, which makes them poor first populations for testing whether a machine's adaptive relationship is scientifically genuine.

On privacy, for real-human sensing, adopt a hierarchy: synthetic identity before biometrics; local processing before cloud processing; derived minimal features before raw indefinite archives; explicit enrolment before passive recognition; per-person deletion before opaque permanent memory; and human-readable memory inspection before hidden behavioural profiling. Long-term personal interaction histories may reveal routines, health states, relationships and sensitive habits even without conventional identity fields. Privacy therefore applies to interaction memory, not merely to camera frames.

On consequential tools: tool use must be bounded by explicit capability classes. Reading a technical document is categorically different from sending a message, buying something, moving money, unlocking a door or controlling machinery. Consequential actions should require human confirmation by default. Current Aweform already prohibits networking, external APIs and physical-device control, which is the correct boundary for the present stage.

Finally, the longer-term dependency roadmap. This is a set of gates, not ages or promised milestones.

Gate one, external causation: required evidence is that lawful observation distinguishes self-conditioned from externally induced changes. It unlocks external-agent studies. Do not progress if the effect exists only in evaluator truth.

Gate two, recurring-context prediction: required evidence is that a recurring neutral cue prospectively predicts intervention beyond shuffled and time controls. It unlocks a minimal external-agent model. Do not progress if a zero-change or time model matches the learner.

Gate three, partner specificity: two recurring sources must support different held-out predictions. It unlocks individual history. Do not progress if mere identifier lookup accounts for all adaptation.

Gate four, reliability updating: one partner model must update selectively after changed behaviour. It unlocks dynamic partner expectation. Do not progress if global recency explains the changes.

Gate five, reciprocal signalling: Aweform's output must causally change partner response, and signal use must be learned. It unlocks communication conventions. Do not progress if behaviour is scripted or persists after contingency removal.

Gate six, shared routines: repeated interaction must yield efficient coordinated sequences. It unlocks procedural social learning. Do not progress if coordination is solely human accommodation.

Gate seven, scaffolded independence: socially guided skill must transfer to unassisted contexts. It unlocks more substantial teaching. Do not progress if capability vanishes without assistance.

Gate eight, interaction memory: retained event history must add predictive or task value with controlled forgetting. It unlocks longer relationships. Do not progress if privacy cost exceeds scientific value.

Gate nine, natural human identification: synthetic-identity findings must replicate under local voice or visual identity sensing. It unlocks real repeated partners. Do not progress if biometric sensing itself supplies the relevant semantics.

Gate ten, language interface: machine-native state must be translatable without language becoming hidden control state. It unlocks conversation. Do not progress if the language model dominates decisions attributed to Aweform.

Gate eleven, bounded digital tools: tool actions must carry provenance, permissions and confirmation gates. It unlocks useful technical assistance. Do not progress if a tool result is misreported as learned cognition.

Gate twelve, physical embodiment: simulation capability must leave a clear embodiment-dependent question. It unlocks robot experiments. Do not progress if hardware is primarily for emotional effect or demonstration value.

The likely hard blockers are not model size. They are partial observability; credit assignment across delays; stable but updateable memory; causal attribution of external agents; partner identity without semantic leakage; demonstrating independence rather than dependence; privacy-preserving long-term memory; and separating pretrained tool intelligence from developmental intelligence.

## 7. Decision Memorandum and the First Research Sprint

This final chapter is the decision memorandum for the founder. It answers a short set of questions.

First: what should Aweform Familiar study first?

Study whether recurring external context becomes a learned predictor of an external intervention, under a design in which Aweform remains independently viable.

Do not begin with attachment, face recognition, dialogue, a large language model, a furry robot, human subjects, or physical caregiving.

Before the claim-bearing experiment, perform a narrow validity audit showing that externally caused effects are observable through the proposed lawful sensory history.

Second: which biological findings matter most?

Five biological findings are genuinely useful. First, development starts from structured prior organisation, not a blank slate. Second, contingency learning precedes sophisticated cognition. Third, recognition, familiarity, prediction, preference and attachment are separable constructs. Fourth, caregivers influence regulation, attention and exploration in ways that cannot be reduced to calorie delivery. Fifth, healthy development includes increasing independence, so assistance is scientifically most interesting when it produces transferable competence rather than dependence.

The exact mammalian neural anatomy matters much less.

Third: which AI mechanisms currently have the strongest evidence?

For the next Aweform decision, not for AI in general, the order is this. Small online action-conditioned predictors, because Aweform has already demonstrated them. Bounded temporal state or history, if delay makes the current representation insufficient. Simple probabilistic partner statistics for reliability. Replay or explicit event memory when partner-history retention becomes necessary. And learning-progress exploration much later, once there is evidence that self-directed curriculum is needed.

Dreamer, JEPA and vision-language-action models have stronger headline benchmark capabilities but weaker relevance to the first Familiar hypothesis.

Fourth: which robotics projects are the best references?

iCub and YARP for embodied developmental research infrastructure and sensorimotor experimentation. The Oudeyer, Baranes and Nguyen developmental robotics work for learning-progress exploration and socially guided skill acquisition. Tega and DragonBot for long-duration, partner-specific human-robot interaction methodology, and equally importantly as a lesson in carefully distinguishing human response from robot learning. Quori as a later reproducible open human-robot interaction platform. And MiRo as a possible later compact animal-like embodiment reference, not as a cognitive architecture to inherit.

Fifth: what should be deliberately excluded?

For the first Familiar programme, exclude all of the following. No large language model as the organism's mind. No face recognition. No speech recognition. No anthropomorphic personality layer. No emotion model. No explicit trust score. No attachment objective. No dependency optimisation. No curiosity until its need is demonstrated. No large JEPA or world model. No deep reinforcement learning merely because it is available. No camera. No microphone. No physical robot. No human-subject relationship study. No weakening of Level-1 survival. No external web or tool access by the organism. And no cross-generational evolutionary algorithm disguised as development.

The current accepted Aweform architecture already gives strong justification for most of those exclusions.

Sixth: should Familiar initially be research-only?

Yes, strongly. The current branch should answer architecture and protocol questions without touching main organism code. This is not bureaucratic caution. The key unknown is currently what claim is worth implementing, not whether Python can implement it. The live Aweform programme is simultaneously working through physics, sensing and obstruction questions. Issue #240 explicitly treats the next milestone as a planning problem, and issue #242 remains design-only. Familiar should not destabilise that work.

Seventh: when should it become an implementation experiment?

Only when four things are frozen enough for meaningful review: the claim, the information boundary, the control design, and the measurement rule.

Specifically: the external event or intervention must be physically and causally defined; the organism-visible information must be explicit; a minimal current learner must be nominated; time, frequency, shuffled and nonlearning alternatives must be specified; the Level-1 viability mechanism must remain intact; and a negative result must be interpretable without immediately adding a bigger model.

At that point, an isolated short-lived Development-stage branch becomes justified.

Eighth: what is the smallest first falsifiable developmental result worth pursuing?

It is not that Aweform recognises its caregiver. It is not that Aweform prefers its caregiver. It is not that Aweform becomes calmer around its caregiver.

The smallest worthwhile result is this: after online experience, a learner using only lawful organism-visible history predicts the timing or consequence of a recurring external agent's intervention significantly better out of sample than nonlearning, time-only, state-only and shuffled-contingency controls.

That is modest. It is also real. If it works, you have the first brick required for an individually learned relationship. If it fails, you learn whether the blocker is observability, memory, representation or experimental design.

Ninth: what information is still needed before that decision?

Implementation should not be authorised until four uncertainties are resolved.

It is not known whether the current D-046-style feature representation can learn the intended delayed contingency without a history extension. That needs a paper-level and protocol-level capacity analysis before code.

It is not known which external intervention can be introduced with the least distortion of accepted version 0.5 physics. A bounded thermal perturbation is the leading proposal, but it requires architectural review rather than assumption.

It is not known whether adding one external event receptor should be considered an ordinary experimental observation-boundary amendment or a new durable ADR boundary under the live governance. The repository's own rules strongly suggest separate authorisation is required, because new organism-visible information cannot be introduced implicitly.

And it is not known what main commit and active First Mate decision state will exist when this work is eventually authorised. Live repository state must be rechecked then.

Tenth: how can Familiar remain independent of First Mate's simulation development?

Use three separation rules.

Research separation: the research evolution-pattern branch contains research documents and proposed experimental contracts, not speculative changes to the version 0.5 organism.

Implementation separation: each authorised Familiar Development experiment branches from the then-current accepted main, not from months of accumulated research-branch code.

Scientific separation: Familiar's first outcome should not depend on the obstacle-learning programme succeeding. A neutral external-agent experiment can run in a simpler accepted or isolated 2D ecology.

That means First Mate can change contact physics, obstruction recovery or future embodiment plans without automatically changing Familiar's scientific question.

The final recommendation is this. The highest-value direction is not stronger attachment-like behaviour. It is the sequence: predictive individuality, then reliability learning, then reciprocal signalling, then scaffolded competence, then reciprocal collaboration, with independent viability underneath the entire sequence.

The Familiar vision becomes scientifically interesting when Aweform's interaction with one person becomes measurably different from its interaction with another because their shared histories produced different learned predictive and procedural states, and when those states support useful cooperation that neither party needed to script in detail beforehand.

That goal is technically plausible. It has not yet been demonstrated by Aweform. Existing robotics demonstrates important pieces but not the full integration. And nothing in the current evidence justifies calling the eventual result love, attachment, friendship, trust or consciousness.

Finally, the concrete first research sprint. No more than five investigations should be opened.

Priority zero, investigation one: define the smallest lawful external agent, meaning the sensory cue, intervention, timing, permitted hidden state and organism-visible consequence. Compare thermal, energetic and environmental intervention candidates without implementation. The exact document to produce is the external agent information boundary document. The decision unlocked is whether hypothesis two can be tested inside existing version 0.5 or needs an isolated environment and a boundary ADR.

Priority zero, investigation two: determine whether the existing 66-feature NLMS family plus bounded explicit history can represent the intended delayed contingency, and compare it theoretically with a tiny recurrent predictor without running organism experiments. Produce the minimal predictor capacity document. The decision unlocked is the exact first learner, and whether recurrence is scientifically justified.

Priority zero, investigation three: freeze the rival explanations and controls for hypothesis two, covering time leakage, frequency learning, state correlation, shuffled contingency, zero-change and nonlearning baselines, and define prospective metrics and falsification. Produce the hypothesis-two recurring intervention protocol. The decision unlocked is whether the first experiment can make a causal developmental claim.

Priority zero, investigation four: reconcile the proposed hypothesis-two information boundary with ADRs 0010, 0017, 0018 and 0019, the safety policy, the Development and Experiment workflow, and current First Mate work. Identify, but do not enact, every required approval. Produce the governance and architecture delta document. The decision unlocked is whether implementation would be in-boundary or requires a new or amended ADR.

Priority one, investigation five: build an evidence register covering individual recognition, reliability reversal, reciprocal signalling and socially guided independence across developmental psychology and robotics, explicitly recording what was learned versus scripted or pretrained. Produce the partner learning evidence register. The decision unlocked is the design of hypotheses three to seven after hypothesis two, without prematurely implementing them.

The sprint should stop there.

The first implementation proposal should be written only if those documents converge on a minimal experiment whose negative result would genuinely teach the project something. That standard is more important to Aweform Familiar than any particular architecture, robot body or anthropomorphic behaviour.
