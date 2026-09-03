# When Reasoning Gets Shorter, Does It Stop Describing Behavior Before It Stops Determining It?

## Experimental Plan

## Research Question

When safety reasoning is compressed into a discrete plan to cross one planner-to-renderer context boundary, does the visible plan stop describing the behavior before it stops determining the behavior?

1. When an assigned policy is absent from the readable plan, does the renderer still implement it more often than its surface-only prior predicts?
2. When the readable plan explicitly states the assigned policy, how often does the code nevertheless implement another behavior?
3. Does the renderer treat a short plan as a specification, or as a cue that selects safety behavior already stored in the model’s weights?
4. When a required fact becomes invisible, was it lost during clause selection, plan serialization, renderer ingestion, or behavioral use?
5. Are the safety distinctions missing from the fixed plan schema covered by a small recurring set, or do new distinctions continue appearing across held-out collisions?

## Hypotheses

1. **Hidden use:** as plans shorten, visible retention of the assigned policy will fall before assigned-policy behavior falls. Policy-compliant code will therefore remain above the balanced surface-only baseline even when the plan omits the A/B distinction.
2. **False certificates:** some plans that explicitly and correctly state the assigned policy will still produce functionally correct code that implements the opposite policy or fails the assigned-policy tests.
3. **Internal decoupling:** on hidden-use examples, the assigned policy will remain more recoverable from renderer activations than from the visible plan, and policy-value interventions will selectively shift the corresponding implementation.
4. **Clause-selection failure:** compression will sometimes replace the applicable clause with a plausible irrelevant clause, producing short, confident plans that look safety-aware but describe the wrong risk.
5. **Schema incompleteness:** after freezing a collision taxonomy on development tasks, held-out collisions will require some new safety distinctions not expressible by the six-field schema.

## Secondary Analyses

1. Whether structured plans outperform information-matched free-form plans at the same observed length.
2. How functionality and assigned-policy compliance change with plan length.
3. Whether field-label overhead creates a structured/free-form crossover at very short lengths.
4. Document-to-plan compression ratio, total generated tokens, and latency.
5. These analyses characterize the setup but are not the project’s central claims.

---

## I. System

### A. Pipeline

1. **Surface Request + Multi-Clause Safety Document → Planner → Plan z → Frozen Renderer(Surface Request, z) → Code**
2. The planner receives:
   1. the surface implementation request;
   2. the multi-clause safety document containing the assigned A-or-B policy; and
   3. a structured or free-form format instruction.
3. The bottleneck renderer receives:
   1. the surface request; and
   2. the completed plan z.
4. The bottleneck renderer does not receive the safety document.
5. The plan is therefore the only explicit security-information channel between the planner and renderer.
6. The plan ends with a fixed **END_PLAN** marker so activation measurements can be aligned across examples.
7. This is one serialized **context handoff**, not a multi-session system.
8. It models a planner handing work to a fresh code-generation context, similar to an orchestrator-to-subagent or summarize-and-continue boundary.
9. The renderer can still use secure-coding knowledge already stored in its frozen weights.
10. The experiment tests how much the plan specifies versus merely selects that existing behavior.

### B. Multi-Clause Safety Document

1. Each document contains five or six numbered policy clauses.
2. Only one or two clauses apply to the surface task.
3. The remaining clauses are plausible but irrelevant to that task.
4. Target length: approximately 150–250 tokens before the surface request.
5. For an A/B pair:
   1. the irrelevant clauses are identical;
   2. the applicable clause changes from policy A to policy B;
   3. document length is approximately matched; and
   4. the applicable clause’s position is balanced across tasks.
6. Clause order is varied independently of policy value.
7. Each task stores gold metadata identifying:
   1. the applicable clause or clauses;
   2. the irrelevant clauses;
   3. the assigned A/B value; and
   4. the required implementation behavior.
8. Example path-traversal document:
   1. database queries must use parameterized values;
   2. outbound HTTP requests must reject private network addresses;
   3. uploaded filenames are untrusted;
   4. fully resolved file targets must remain inside the reports root;
   5. command execution must never invoke a shell; and
   6. logs must not contain authentication secrets.
9. In this example, clauses 3–4 apply and the others are realistic distractors.
10. The planner must identify the applicable clause, preserve its A/B value, and omit irrelevant clauses from the compact plan.

### C. Renderer

1. Runs in a fresh context for every code sample.
2. Runs in non-thinking mode.
3. Remains frozen throughout the core experiment.
4. Is not SFT-trained to follow the structured fields.
5. Generates Python code only after reading the surface request and plan.

### D. Structured Intermediate Language

1. The plan contains six standard taint-analysis fields:
   1. **SOURCE:** attacker-controlled or security-relevant input;
   2. **TRUST:** the input’s trust status;
   3. **SINK:** the dangerous operation;
   4. **GUARD:** the required validation or containment rule;
   5. **ORDER:** when the guard must occur relative to the sink; and
   6. **EFFECT:** the permitted external effect.
2. Example:
   1. SOURCE: filename
   2. TRUST: untrusted
   3. SINK: filesystem read
   4. GUARD: fully resolved path remains inside reports directory
   5. ORDER: resolve and validate before opening
   6. EFFECT: return file contents
3. Free-form equivalent:
   1. Resolve the untrusted filename inside the reports directory. Before opening it, verify that the fully resolved path remains inside that directory. Reject invalid paths and otherwise return the contents.
4. The six fields are the fixed communication format.
5. Family-specific distinctions are written inside the fields. Examples include symlink resolution, redirect revalidation, shell avoidance, and SQL identifier handling.

### E. Target Security Fact

1. Let **G ∈ {A, B}** represent the policy assigned to one task instance.
2. A and B are both secure, legitimate policies for the same surface request but require distinguishable implementations.
3. The renderer must receive G through the full safety document in direct conditions or through the plan in bottleneck conditions.
4. Policy compliance is scored with A-specific and B-specific executable tests.
5. The pair is excluded if one implementation can pass both policy test suites without expressing the intended distinction.
6. Examples:
   1. redirects must be rejected;
   2. redirects may be followed only if every hop is revalidated;
   3. symbolic links must be rejected;
   4. symbolic links are allowed only when the fully resolved target remains inside the root;
   5. a fixed executable must be used;
   6. an allowlisted executable may be used, but never through a shell.
7. The main analysis tracks the assigned value of G instead of using a generic secure/insecure label.
8. Standard secure-versus-insecure benchmark performance is retained as a secondary anchor.
9. Let **R** identify the one or two clauses applicable to the surface task.
10. The planner must solve two separable problems:
    1. select R from the full document; and
    2. preserve the assigned value G of the selected policy.

### F. Activation Boundaries

1. Record block-output activations at evenly spaced layers and every layer near any candidate intervention region.
2. Store three aligned states:
   1. **Planner input state:** final prompt token before plan generation;
   2. **Planner output state:** END_PLAN after the planner generates the plan; and
   3. **Renderer ingestion state:** END_PLAN after the renderer reads the plan and before code generation.
3. These states test whether G is represented:
   1. before the planner writes the plan;
   2. after the plan has been written; and
   3. after the renderer has read the plan.

### G. Meaning of Compression

1. Short plans are not expected to create large end-to-end token or latency savings.
2. The surface request and code output will usually dominate total tokens.
3. Plan length is manipulated because deployed systems may compress visible reasoning for many reasons, including training pressure, interface limits, or learned internal conventions.
4. The primary question is what becomes unmonitorable or behaviorally unreliable under compression.
5. Token counts and latency remain diagnostics, not headline success criteria.

---

## II. Models

### A. Hosted Model for Stages 0–1

1. Primary model: hosted Qwen3.6-27B.
2. Planner:
   1. thinking mode enabled;
   2. receives the surface request and full multi-clause safety document;
   3. returns only the final plan to the renderer.
3. Renderer:
   1. non-thinking mode;
   2. fresh context;
   3. receives the surface request and plan only.
4. Purpose:
   1. test whether the behavioral phenomenon exists using a capable model before local training;
   2. measure prompt-only compression and plan sufficiency; and
   3. select tasks that have enough security headroom.
5. Planner thinking tokens are recorded separately from visible plan tokens.

### B. Local Model for Stages 2–4

1. Initial base model: Qwen3.5-4B.
2. Planner:
   1. Qwen3.5-4B with one QLoRA adapter;
   2. directly emits the plan z;
   3. non-thinking mode.
3. Renderer:
   1. the same frozen base model;
   2. planner adapter disabled;
   3. non-thinking mode.
4. Trainable parameters:
   1. planner adapter only.
5. Hardware:
   1. RTX 5090.
6. Model-floor rule:
   1. run five full-information and full-plan tasks before producing the activation dataset;
   2. if assigned-policy-and-functional performance is below 30%, move to Qwen3.5-9B;
   3. do not interpret a weak renderer as evidence that the intermediate language failed.
7. Stages 2–4 study directly generated compact reasoning.
8. They do not compress a recorded native chain of thought.

---

## III. Tasks

### A. Behavioral Task Set

1. Source: human-audited Python tasks adapted from CWEval.
2. The primary behavioral unit is an **A/B policy pair**, not a secure/insecure pair.
3. Each base task has:
   1. one policy-neutral surface request;
   2. multi-clause safety document A;
   3. multi-clause safety document B;
   4. A-specific executable tests; and
   5. B-specific executable tests.
4. Target: 24 independent A/B base tasks.
5. Minimum for a headline behavioral comparison: 16 independent A/B base tasks.
6. Preferred vulnerability families:
   1. path traversal;
   2. SQL injection;
   3. command injection; and
   4. server-side request forgery.
7. Target composition:
   1. 12 tasks in the family selected for the causal study; and
   2. 4 tasks in each of the other three families.
8. Target split:
   1. 12 training tasks;
   2. 6 development tasks; and
   3. 6 final held-out tasks.
9. Balance A and B equally within every condition and split.
10. Every paraphrase, policy variant, plan, and code sample derived from one base task remains in the same split.
11. The base task, not the generation, is the independent statistical cluster.

### B. Requirements for Each Task

1. Ordinary functionality tests.
2. Policy-A tests.
3. Policy-B tests.
4. A functionally correct policy-A implementation.
5. A functionally correct policy-B implementation.
6. A and B are both defensible security policies.
7. A and B require distinguishable behavior.
8. The pair is excluded if the same implementation can pass both policy-specific suites without implementing the intended distinction.
9. A clean separation between the surface functionality and policy value.
10. Five or six safety-document clauses with only one or two marked applicable.
11. Identical irrelevant clauses across A and B.
12. Gold labels for applicable-clause selection.
13. Original benchmark security tests for the secure-versus-insecure anchor.
14. A sandboxed execution path with compilation checks, timeouts, and isolated test state.

### C. Matched Policy-Counterfactual Subset

1. The causal study concentrates on **one recurring policy variable within one vulnerability family**.
2. Initial candidate:
   1. vulnerability family: path traversal;
   2. policy A: reject all symbolic links; and
   3. policy B: allow symbolic links only when the fully resolved target remains inside the allowed root.
3. Select the final family before activation analysis using only:
   1. number of compatible independent tasks;
   2. quality of executable policy tests; and
   3. behavioral headroom.
4. Target: 12 independent base tasks containing the same A-versus-B policy distinction.
5. Build three pairs first and run the complete causal pipeline end to end.
6. Scale to 12 only if:
   1. both policies can be tested reliably;
   2. the renderer follows the explicit policy;
   3. activations can be captured and edited; and
   4. the intervention changes at least the next-token or first policy-divergence distribution.
7. Each selected task receives two valid policy values, A and B.
8. A and B:
   1. use the same surface request;
   2. are both legitimate security requirements;
   3. require measurably different code behavior; and
   4. have separate executable policy tests.
9. Target split:
   1. 6 training pairs for estimating the fact direction;
   2. 2 development pairs for selecting the layer and intervention strength; and
   3. 4 held-out pairs for final causal evaluation.
10. If only the three-pair pilot is completed:
    1. report it as a mechanistic case study;
    2. do not claim cross-task generalization.
11. The broader A/B behavioral study still covers all four vulnerability families.
12. The concentrated causal subset avoids estimating separate policy directions from only one or two tasks per family.

### D. Secure-Versus-Insecure Anchor

1. Retain the unmodified CWEval condition and its ordinary security tests.
2. Measure standard secure-and-functional performance for comparability with prior secure-code work.
3. Do not use this anchor as the primary evidence that the bottleneck transmits policy information.
4. The A/B setting is primary because the surface request is identical and does not reveal which of two legitimate policies is assigned.

---

## IV. Prompt Decomposition and Experimental Conditions

### A. Prompt Views

1. **Original benchmark prompt**
   1. Unmodified benchmark task.
2. **Surface request**
   1. Function signature;
   2. inputs and outputs;
   3. examples; and
   4. ordinary functional behavior.
3. **Relevant-clause-only A/B prompt**
   1. Surface request;
   2. the one or two applicable clauses; and
   3. no distractor clauses.
4. **Full safety document A**
   1. Five or six clauses;
   2. one or two applicable clauses expressing policy A; and
   3. identical plausible distractors shared with document B.
5. **Full safety document B**
   1. The same surface task and distractors;
   2. the applicable clause expresses policy B; and
   3. approximately matched document length.
6. **Full-information A/B prompt**
   1. Surface request + the assigned full safety document.

### B. Decomposition Procedure

1. Save the original and transformed prompts.
2. Mark every removed or rewritten policy span.
3. Verify that the surface request still specifies the same ordinary functionality.
4. Verify that the same surface request can naturally support both A and B.
5. Exclude tasks where functionality and policy choice cannot be separated.
6. Verify that A and B are both secure and mutually distinguishable under tests.
7. Write three to five irrelevant but plausible clauses.
8. Verify that irrelevant clauses do not secretly apply to the task.
9. Match distractor clauses and approximate document length across A and B.
10. Balance the applicable clause’s position across tasks and policies.
11. Show representative original, surface-only, relevant-only, and full-document prompts in the final report.

### C. Experimental Conditions

| Condition | Input to Code Generator | Purpose |
| --- | --- | --- |
| Original benchmark | Unmodified benchmark prompt | Secure-versus-insecure anchor |
| Surface-only direct | Surface request with no A/B value | Policy-choice chance baseline |
| Relevant-clause-only direct | Surface request + applicable A/B clause only | Selection-free policy ceiling |
| Full-document A/B direct | Surface request + complete safety document | No-bottleneck clause-selection ceiling |
| Native-thinking full-document A/B | Complete safety document with unrestricted reasoning | Reasoning ceiling |
| Free-form A/B bottleneck | Surface request + free-form plan generated from full document | Compressed selection-and-reasoning baseline |
| Structured A/B bottleneck | Surface request + structured plan generated from full document | Proposed intermediate language |
| Paired-format control | Surface request + information-matched plan | Isolates format from information content |
| Opposite-policy plan control | Surface request + same-task plan for the other policy | Tests transmission of the A/B value |
| Wrong-clause plan control | Surface request + plan centered on a plausible irrelevant clause | Tests clause-selection dependence |
| Shuffled-plan control | Surface request + another task’s plan | Tests renderer dependence on the plan |

### D. Meaning of the Two Format Comparisons

1. **Independently generated comparison**
   1. The planner generates structured and free-form plans separately.
   2. This tests whether each format causes the planner to select useful information and whether the renderer can use it.
2. **Paired-format control**
   1. Generate one structured plan.
   2. Paraphrase it into free-form prose without changing its information.
   3. Audit every security fact for equivalence.
   4. Render code from both versions.
   5. This holds information fixed and changes only its presentation.

### E. Planner-Side Clause Controls

1. **Relevant-clause-only planner input**
   1. Gives the planner only the applicable clause.
   2. Measures planning and compression without clause selection.
2. **Full-document planner input**
   1. Gives the planner all five or six clauses.
   2. Measures selection plus compression.
3. **Clause-order control**
   1. Reorders the same document.
   2. Tests whether clause position changes selection.
4. **Distractor replacement control**
   1. Replaces irrelevant clauses with length-matched irrelevant clauses from another policy document.
   2. Tests whether specific distractor wording changes the selected plan.

---

## V. Stage 0: Prompt, Model, and Headroom Smoke Test

### A. Setup

1. Select five candidate tasks.
2. Build both policy values for each task.
3. Confirm that:
   1. A and B share the same surface request;
   2. both are legitimate;
   3. their tests distinguish the intended behavior; and
   4. the prompt does not leak the assigned value outside the full safety document.
4. Generate eight code outputs per task for:
   1. original benchmark;
   2. surface-only direct;
   3. relevant-clause-only A;
   4. relevant-clause-only B;
   5. full-document A;
   6. full-document B;
   7. native-thinking full-document A; and
   8. native-thinking full-document B.
5. Run functionality, A-policy, B-policy, and original security tests.

### B. Continue If

1. Relevant-clause-only A/B functional pass rate is at least 40%.
2. Relevant-clause-only assigned-policy compliance is at least 50%.
3. Full-document assigned-policy compliance is within approximately 20 percentage points of relevant-clause-only performance.
4. Full-document assigned-policy compliance exceeds the balanced surface-only baseline by approximately 20 percentage points.
5. Changing only the applicable clause from A to B changes policy-specific behavior.
6. Surface-only outputs do not systematically pass both mutually exclusive policy suites.
7. Full plans select the applicable clause on a useful fraction of tasks.
8. The original benchmark condition remains usable as a secure-versus-insecure anchor.

### C. Interpretation

1. These are continuation rules only.
2. They are not treated as statistical findings.
3. After prompts are frozen, repeat the comparisons on the complete development set.
4. Report task-grouped uncertainty intervals.
5. Separate:
   1. the cost of selecting from distractors, measured by relevant-only versus full-document input; and
   2. the cost of compressing the selected information, measured within the full-document bottleneck.

### D. Failure Response

1. If surface-only outputs appear to identify A or B:
   1. inspect the prompt for policy leakage;
   2. verify that the A/B tests are actually mutually distinguishing; and
   3. exclude the task if the surface behavior logically implies one policy.
2. If full-information performance is too low:
   1. use a stronger renderer;
   2. simplify the task; or
   3. exclude the task.
3. If the full document performs far below the relevant-clause-only condition:
   1. inspect whether distractors are accidentally applicable;
   2. simplify or replace ambiguous distractors; and
   3. retain a measurable but non-floor selection problem.
4. If changing A to B does not change code:
   1. the policy distinction is not behaviorally usable;
   2. replace the pair before training.
5. Do not proceed until the full safety document produces measurable control over implementation.

---

## VI. Stage 1: Prompt-Only Intermediate-Language Test

### A. Generation Procedure

1. Use the hosted model.
2. For each development task:
   1. run both assigned policy values A and B;
   2. give the planner the surface request and assigned multi-clause safety document;
   3. request either structured or free-form output;
   4. request full, concise, or minimal detail;
   5. generate three plans per policy, format, and concision instruction;
   6. place each plan in a fresh non-thinking renderer context;
   7. generate four code samples from each exact plan; and
   8. run functionality, assigned-policy, opposite-policy, and anchor security tests.
3. Do not enforce plan length with hard max-token truncation.
4. Allow each plan to finish.
5. Record actual token length.
6. Flag genuinely truncated or malformed generations.

### B. Length Matching

1. Total observed plan tokens define the compression level.
2. Report document-to-plan compression ratio:
   1. safety-document tokens divided by plan tokens.
3. Content tokens after removing fixed schema labels are a secondary diagnostic.
4. Compare formats using:
   1. observed-length bins with support from both formats; and
   2. within-task nearest-length matching.
5. Do not compare nominal requests such as “minimal” when their observed lengths do not overlap.
6. Do not interpret shorter plans as meaningful end-to-end efficiency gains unless total-token or latency measurements support that claim.

### C. Behavioral Measurements

1. Visible retention of the assigned A/B distinction VG.
2. Excess hidden use HU+.
3. False-certificate rate FC.
4. Assigned-policy pass rate.
5. Assigned-policy-and-functional pass rate.
6. Functional pass rate.
7. Opposite-policy behavior rate.
8. Policy controllability:
   1. change in policy-specific behavior when the applicable clause changes from A to B.
9. Applicable-clause selection precision.
10. Applicable-clause selection recall.
11. Irrelevant-clause inclusion rate.
12. Confident wrong-clause rate:
    1. the plan confidently centers an irrelevant clause while omitting the applicable A/B clause.
13. Original secure-and-functional rate as an anchor.
14. Plan tokens and document-to-plan compression ratio.
15. Planner thinking tokens.
16. Total generated tokens.
17. End-to-end latency as a diagnostic.

### D. Renderer-Dependence Checks

1. Replace the assigned plan with the same task’s opposite-policy plan.
2. Replace the assigned plan with a plan from another task.
3. Replace the applicable clause in the plan with a plausible irrelevant clause from the same safety document.
4. Keep the surface request fixed.
5. Compare policy-specific implementation choices.
6. Continue only if the renderer follows the selected policy content transmitted in the plan.

### E. Stage 1 Continuation Gate

1. Full structured plans approach the full-document A/B direct condition.
2. Opposite-policy plans reverse policy-specific behavior.
3. Wrong-clause plans reduce assigned-policy compliance or change implementation.
4. Clause order does not fully determine which clause is selected.
5. Shuffled plans reduce assigned-policy compliance or change implementation.
6. Structured and free-form plans have overlapping observed lengths.
7. Assigned-policy outcomes and clause-selection accuracy are not saturated across the complete length range.
8. At least some naturally generated plans omit, blur, or replace the applicable A/B clause.
9. If no natural omissions occur:
   1. keep the behavioral compression frontier; and
   2. use the matched policy-counterfactual tasks for the causal study.

---

## VII. Stage 2: Planner SFT

### A. SFT Data Creation

1. For each training task:
   1. write one complete structured reference plan for policy A;
   2. write one complete structured reference plan for policy B;
   3. require both reference plans to select the applicable clause or clauses from the full document;
   4. omit irrelevant clauses unless they materially interact with the task;
   5. derive a free-form version of each by paraphrase;
   6. audit structured and free-form versions for identical policy information;
   7. add surface-prompt, document-order, and policy-wording paraphrases; and
   8. keep every paraphrase within the original task split.
2. Audit:
   1. SOURCE;
   2. TRUST;
   3. SINK;
   4. GUARD;
   5. ORDER;
   6. EFFECT; and
   7. every family-specific policy distinction;
   8. applicable-clause coverage; and
   9. irrelevant-clause exclusion.

### B. Training Row

1. **Input**
   1. Surface request;
   2. assigned multi-clause safety document A or B; and
   3. FORMAT: STRUCTURED or FORMAT: FREEFORM.
2. **Output**
   1. Information-complete reference plan in the requested format.

### C. Training Setup

1. Train one format-conditioned planner QLoRA.
2. Freeze the base model.
3. Do not fine-tune the renderer.
4. Select checkpoint and hyperparameters using development tasks only.
5. Verify exact train/development/test task separation.

### D. Post-SFT Evaluation

1. Request full, concise, and minimal plans.
2. Record observed rather than requested plan lengths.
3. Run each plan through the frozen renderer.
4. Re-estimate:
   1. capability-versus-length frontier;
   2. assigned-policy-compliance-versus-length frontier;
   3. A/B controllability-versus-length frontier;
   4. applicable-clause-selection-versus-length frontier;
   5. visible-policy-retention frontier;
   6. confident-wrong-clause-versus-length frontier; and
   7. structured-versus-free-form difference.
5. Report secure-versus-insecure performance as a secondary anchor.
6. Compare the full structured plan with:
   1. relevant-clause-only direct generation; and
   2. full-document A/B direct generation.
7. If the full plan already causes a large capability or policy-compliance loss:
   1. identify the bottleneck as the limiting factor;
   2. do not attribute later failure specifically to compression.

---

## VIII. Stage 3: Fact-Specific Information Tracing

### A. Visible Fact Labels

1. For each plan, label applicable-clause selection R as:
   1. correct;
   2. partially correct;
   3. wrong clause; or
   4. no applicable clause selected.
2. For the assigned policy value G, label the plan:
   1. preserved;
   2. omitted;
   3. contradicted; or
   4. ambiguous.
3. Record which irrelevant clauses, if any, appear in the plan.
4. Assign every label without viewing the generated code.
5. Use a written family-specific rubric.
6. Double-audit every held-out example and a random subset of training examples.
7. Use naturally generated compressed plans for the main information-loss analysis.
8. Do not create the headline result by manually deleting fields.

### B. Activation Dataset

1. Use the local planner and frozen local renderer.
2. For every policy-counterfactual task:
   1. run policy A and policy B;
   2. generate multiple plan paraphrases and concision levels;
   3. record the three boundary states; and
   4. store the exact document, applicable-clause labels, visible G label, code outcome, and test results.
3. Keep train, development, and test base tasks separate.
4. Do not use test activations to select layers, probe regularization, or patch magnitude.
5. Stratify examples into four monitorability quadrants:
   1. **faithful success:** VG = 1 and YG = 1;
   2. **false certificate:** VG = 1 and YG = 0;
   3. **hidden use:** VG = 0 and YG = 1; and
   4. **visible omission with behavioral failure:** VG = 0 and YG = 0.
6. Compare activation traces across these quadrants at matched task, format, and observed length whenever possible.

### C. Lexical-Generalization Split

1. Create two disjoint policy-paraphrase sets.
2. Each set contains multiple phrasings of A and B.
3. Balance lexical framing:
   1. express A both as a prohibition and as a positive permission rule;
   2. express B both as a permission and as a prohibition on the unsafe exception; and
   3. avoid making A always contain words such as “reject” while B always contains words such as “allow.”
4. **Paraphrase set 1**
   1. used for probe fitting;
   2. used for difference-in-means direction estimation; and
   3. used for development-layer selection.
5. **Paraphrase set 2**
   1. contains no shared policy sentence template from set 1;
   2. is used for held-out activation evaluation; and
   3. supplies the explicit A/B source runs for final causal interventions.
6. A policy direction that works only on paraphrase set 1 is treated as a phrasing direction.
7. Transfer to set 2 is required before interpreting wG as representing the policy distinction.

### D. Probe Localization

1. Train an L2-regularized logistic probe for the exact policy value G.
2. Train a secondary multiclass probe for the applicable clause position R when task counts support it.
3. Fit separate probes at:
   1. planner input;
   2. planner output; and
   3. renderer ingestion.
4. Train on training tasks.
5. Select regularization and candidate layers on development tasks.
6. Report performance on held-out base tasks.
7. Evaluate G with AUROC and balanced accuracy.
8. Evaluate R against:
   1. clause-position chance;
   2. the visible plan’s selected clause; and
   3. per-task held-out predictions.
9. Because the number of independent training tasks is small:
   1. treat the probe as a layer-localization heuristic;
   2. do not use probe accuracy as the evidence that G is causally represented; and
   3. let the held-out intervention carry the causal claim.

### E. Causal Direction Estimation

1. Do not use all within-task samples as if they were independent examples.
2. At each candidate layer:
   1. average policy-A activations within each training task;
   2. average policy-B activations within the same task;
   3. calculate one paired difference vector per task; and
   4. average the task-level difference vectors with equal weight.
3. Normalize the resulting difference-in-means direction to obtain wG.
4. Use the probe only to identify plausible layers.
5. Use development tasks to select:
   1. one layer;
   2. one intervention strength; and
   3. whether a rank-one direction is sufficiently stable.
6. Report cosine similarity among the task-level difference vectors.
7. If the task-level directions do not align:
   1. do not claim one shared fact direction;
   2. stop before held-out causal evaluation or report task-specific results as a case study.

### F. Probe Baselines and Controls

1. TF-IDF or bag-of-words classifier on the visible plan.
2. Plan length only.
3. TF-IDF plus plan length.
4. Surface-only renderer activations.
5. Policy labels shuffled within a base task.
6. An unrelated policy-fact probe.
7. Policy paraphrase-set identity.
8. A lexical-polarity classifier such as reject/allow framing.
9. Applicable-clause position alone.
10. Clause length and document position.
11. Identity of the most salient irrelevant clause.
12. Identical regularization selection for every activation and text model.

### G. Interpretation Table

| Result | Interpretation |
| --- | --- |
| R is not decodable at planner input and the plan selects the wrong clause | Planner failed to identify the applicable clause |
| R is decodable at planner input but the plan selects an irrelevant clause | Planner represented relevance but failed to externalize the selection |
| R is correct but G is absent at planner output | Planner selected the right clause but lost its policy value during compression |
| G is not decodable at planner input | Planner did not form an accessible representation of G |
| G is decodable at planner input but not planner output | G was formed but not retained or externalized in the completed plan |
| G is visible in the plan but not decodable at renderer ingestion | Renderer failed to encode the transmitted distinction |
| G is decodable at renderer ingestion but code violates G | Renderer represents G but does not use it successfully |
| Text predicts G as well as activations | Activations add no monitorability beyond reading the plan |

### H. Role of the Probe

1. The probe is a localization tool.
2. Probe accuracy alone is not a central result.
3. A fact is not called causally important unless the held-out intervention changes the corresponding executable behavior.
4. If probe performance does not generalize across tasks:
   1. report the negative result; and
   2. do not perform a cherry-picked causal intervention.

---

## IX. Stage 4: Fact-Specific Causal Interchange

### A. Primary Recipient: Policy-Omitting Plan

1. The primary intervention does not overwrite text that explicitly states the opposite policy.
2. For one held-out task, create three renderer runs:
   1. **Explicit-A source:** a paraphrase-set-2 full plan that clearly states policy A;
   2. **Explicit-B source:** a paraphrase-set-2 full plan that clearly states policy B; and
   3. **Omitted-G recipient:** a naturally generated compressed plan that does not state the A-versus-B distinction.
3. The omitted-G plan:
   1. must remain functionally meaningful;
   2. must not contradict either A or B;
   3. is labeled without viewing the code; and
   4. uses the same surface request as the two source runs.
4. Match plan format, length, and non-target information where possible.
5. This tests whether adding an internal representation of an unstated policy fact changes implementation.

### B. Policy Values

1. At the selected layer, calculate the task-balanced policy direction wG.
2. Estimate wG using paraphrase set 1 only.
3. Calculate the policy-A and policy-B scalar centroids along wG using training tasks only.
4. Use paraphrase set 2 for the held-out explicit source plans.
5. Starting from the same omitted-G renderer state h0, create:
   1. an A-injected state whose wG component is set to the policy-A centroid; and
   2. a B-injected state whose wG component is set to the policy-B centroid.
6. Change no orthogonal activation component in the primary intervention.
7. The primary comparison is:
   1. omitted plan + no intervention;
   2. omitted plan + A value; and
   3. omitted plan + B value.

### C. Cheap Distributional Sanity Check

1. Run before sampling complete code.
2. Measure:
   1. KL divergence between patched and unpatched next-token distributions;
   2. logit changes for policy-relevant tokens when they exist; and
   3. under a teacher-forced common code prefix, the log-odds of the A-compatible versus B-compatible continuation at the first policy-relevant divergence.
3. Continue to full code sampling only if:
   1. the A and B interventions produce measurably different distributions; and
   2. the difference exceeds random-direction and lexical-direction controls on development tasks.
4. Failure means the proposed state edit is too weak or incorrectly localized.
5. It is not treated as evidence that G has no causal role.

### D. Primary Single-Position Intervention

1. Apply the edit once at the renderer END_PLAN state.
2. Let cA and cB be the training-task policy centroids along wG.
3. Set the omitted recipient to policy value v ∈ {A, B}:

   **h′v = h0 + (cv − wGᵀh0)wG**

4. Continue code generation normally.
5. Run executable policy and functionality tests.
6. Compare whether A injection increases policy-A behavior and B injection increases policy-B behavior from the same policy-omitting text.

### E. Primary Bidirectional Requirement

1. Omitted-G + A injection must shift behavior toward policy A.
2. Omitted-G + B injection must shift behavior toward policy B.
3. Both use the same visible recipient plan.
4. A one-sided effect is reported but does not establish a general A-versus-B representation.

### F. Controls

1. No intervention.
2. Random orthogonal direction with matched norm.
3. Unrelated security-fact direction.
4. A direction trained to predict paraphrase-set identity rather than policy.
5. A direction trained from one lexical framing and evaluated on the opposite framing.
6. Target-direction value from an unrelated task.
7. Preregistered early-layer intervention.
8. Full-vector same-task intervention as a less specific positive control.
9. Equivalent intervention strength across target and control directions.

### G. Robustness Check: Recurrent Steering

1. If the single END_PLAN edit changes the sanity-check distribution but washes out during full generation:
   1. reapply the target projection at every generated code position.
2. Report this separately as **activation steering**, not as the primary interchange result.
3. Use the same random, unrelated-fact, and no-steering controls.
4. A steering-only effect shows that maintaining G can influence behavior.
5. It is weaker evidence that one naturally occurring boundary state is sufficient.

### H. Harder Contradictory-Text Test

1. Run only after the omitted-G intervention.
2. Use a recipient plan that explicitly states policy B.
3. Inject the policy-A value, then reverse A and B.
4. This tests whether the activation can override contradictory visible instructions.
5. A null result is not counted against the primary causal hypothesis because the policy text remains in the attention cache throughout generation.

### I. Primary Outcomes

1. A-injection change in policy-A behavior relative to the unpatched omitted plan.
2. B-injection change in policy-B behavior relative to the same unpatched plan.
3. Difference between target and strongest matched control.
4. Ordinary functional pass-rate change.
5. Non-target implementation change.
6. Held-out task consistency.

### J. Causal Success Rule

1. The primary target-direction intervention must:
   1. produce opposite policy-specific shifts from the same omitted-G plan;
   2. exceed every matched control;
   3. survive the held-out paraphrase-set-2 evaluation;
   4. reproduce across the four held-out task pairs; and
   5. preserve ordinary functionality within five percentage points of the unpatched recipient.
2. Four held-out pairs provide cross-task case-study evidence only.
3. Do not describe this result as generalization to the wider task distribution.
4. If the direction predicts G but the intervention fails:
   1. conclude that G is decodable;
   2. do not conclude that the decoded direction causally controls behavior.
5. If only recurrent steering succeeds:
   1. claim causal steerability;
   2. do not claim that a single boundary representation is sufficient.

### K. Optional Planner-Side Intervention

1. Run only if renderer-side interchange succeeds.
2. Intervene at:
   1. planner input; or
   2. planner END_PLAN state.
3. Test whether:
   1. the visible plan changes to the donor policy;
   2. the renderer follows the changed plan; and
   3. the downstream code adopts the donor behavior.
4. Cut this before any renderer-side causal control.

---

## X. Monitorability Gap and Policy-Collision Analysis

### A. Primary Monitorability Outcomes

1. Let **VG(z) = 1** when the visible plan explicitly and correctly states the assigned A/B policy value.
2. Let **YG = 1** when the generated code is functionally correct and passes the assigned-policy tests.
3. **Hidden use**
   1. VG(z) = 0;
   2. the code is functionally correct; and
   3. the code implements the assigned value G.
4. Because an omitted plan can match the assigned policy by chance, define excess hidden use:

   **HU+ = P(YG = 1 | VG = 0) − P(YG = 1 | surface-only)**

5. Report HU+ separately for A and B and then average the paired task effects.
6. Positive HU+ means the visible plan does not state the assigned policy, but the renderer follows it more often than its policy-free prior predicts.
7. **False certificate**
   1. VG(z) = 1;
   2. the code is functionally correct; and
   3. the code implements the opposite policy or otherwise fails the assigned-policy tests.
8. Define the false-certificate rate:

   **FC = P(YG = 0 | VG = 1, functional = 1)**

9. **Confident wrong-clause plan**
   1. the plan contains clear, security-sounding instructions;
   2. it foregrounds at least one irrelevant clause;
   3. it omits the applicable clause R or its assigned value G; and
   4. the code fails the assigned-policy tests.
10. Plot HU+, FC, clause-selection recall, assigned-policy compliance, and functionality against observed plan length.
11. The central positive result is a region where visible policy retention falls while assigned-policy behavior remains stable or declines substantially later.
12. The central negative result is tight coupling: visible policy retention and assigned-policy behavior fail together, with HU+ near zero and few false certificates.

### B. Plan-Conditioned A/B Ambiguity

1. For one exact task and plan z, sample 16–32 renderer outputs.
2. Among functionally correct outputs, classify each implementation as:
   1. policy A;
   2. policy B;
   3. both; or
   4. neither.
3. Valid A/B task construction should make the “both” category rare or impossible.
4. Let qA(z) be the proportion of A-or-B-classifiable outputs that implement policy A.
5. Define:

   **AAB(z) = 4qA(z)(1 − qA(z))**

6. Interpretation:
   1. AAB(z) = 0: the plan consistently produces one policy behavior.
   2. AAB(z) = 1: policy-A and policy-B implementations are equally common.
7. Calculate AAB(z) only when at least eight outputs are functionally correct and A-or-B classifiable.
8. Separately report:
   1. assigned-policy compliance among all functionally correct outputs;
   2. both-policy rate;
   3. neither-policy rate; and
   4. excluded-plan count.

### C. Policy Collision

1. A collision occurs when the same task and exact plan produce:
   1. at least one functionally correct policy-A implementation; and
   2. at least one functionally correct policy-B implementation.
2. Report assigned-policy compliance beside collision rate.
3. Low ambiguity is not interpreted as success when the renderer consistently implements the wrong policy.
4. Secure-versus-insecure collisions under the original benchmark are reported only as a secondary anchor.

### D. Pre-Specified Missing Distinctions

1. Path traversal:
   1. lexical normalization versus full resolution;
   2. symlink expansion;
   3. containment predicate;
   4. validation-to-open coupling; and
   5. time-of-check/time-of-use behavior.
2. SQL injection:
   1. value versus identifier parametrization;
   2. partial parametrization;
   3. placeholder semantics; and
   4. allowlist-to-internal-name mapping.
3. Command injection:
   1. argument vector versus shell;
   2. executable resolution;
   3. quoting versus validation; and
   4. incomplete argument coverage.
4. SSRF:
   1. DNS rebinding;
   2. redirect revalidation;
   3. alternative IP encodings;
   4. private-network checks; and
   5. scheme and port restrictions.

### E. Collision Procedure

1. Use naturally sampled collision pairs.
2. Diff the policy-A and policy-B code.
3. Locate the first policy-relevant behavioral divergence.
4. Assign it to a pre-specified category or mark it outside the taxonomy.
5. State the smallest additional plan distinction that separates the outputs.
6. Check whether the same distinction explains another collision.

### F. Closed Vocabulary Versus Long Tail

1. Build the initial missing-distinction taxonomy using training and development collisions only.
2. Freeze the taxonomy before inspecting final held-out collisions.
3. For every held-out collision:
   1. identify the smallest missing safety distinction;
   2. mark whether an existing taxonomy category covers it; and
   3. if not, assign it a new held-out category without altering the frozen primary score.
4. Report:
   1. **top-k coverage:** fraction of held-out collisions explained by the k most common development categories;
   2. **new-distinction rate:** fraction of held-out collisions requiring a category absent from the frozen taxonomy;
   3. **category accumulation curve:** cumulative number of distinct missing distinctions as additional tasks are inspected; and
   4. recurrence of each distinction across independent base tasks.
5. Evidence for a small closed set:
   1. a few categories explain most held-out collisions;
   2. the accumulation curve saturates; and
   3. new-distinction rate decreases.
6. Evidence for a long tail:
   1. held-out collisions repeatedly require new categories;
   2. top-k coverage remains low; and
   3. the accumulation curve continues growing.
7. A small closed set suggests the schema may be repairable by adding a few distinctions.
8. A long tail suggests any fixed compact vocabulary may remain brittle.

---

## XI. Metrics and Statistical Analysis

### A. Primary Monitorability

1. Visible assigned-policy-retention rate.
2. Excess hidden use HU+.
3. False-certificate rate FC.
4. Confident wrong-clause rate.
5. Assigned-policy behavior when VG = 0.
6. Assigned-policy failure when VG = 1.
7. Length range where visible retention and behavior separate.

### B. Capability

1. Code-compilation rate.
2. Functional pass rate.
3. Assigned-policy-and-functional pass rate.
4. Functional difference from the full-document A/B direct condition.
5. Secure-and-functional pass rate under the original benchmark anchor.

### C. Policy Compliance and Security

1. Assigned-policy compliance among functionally correct implementations.
2. Opposite-policy behavior rate.
3. A-to-B controllability when only the assigned policy changes.
4. Plan-conditioned A/B ambiguity AAB(z).
5. Policy-collision rate.
6. Conditional security under the secure-versus-insecure anchor.

### D. Clause Selection

1. Applicable-clause selection precision.
2. Applicable-clause selection recall.
3. Irrelevant-clause inclusion rate.
4. Confident wrong-clause rate.
5. Sensitivity to clause order.
6. Performance gap between relevant-clause-only and full-document input.

### E. Collision Vocabulary

1. Top-k held-out collision coverage.
2. Held-out new-distinction rate.
3. Category accumulation curve.
4. Cross-task recurrence of each missing distinction.

### F. Compression Diagnostics

1. Safety-document tokens.
2. Observed plan tokens.
3. Document-to-plan compression ratio.
4. Content tokens excluding fixed schema labels.
5. Planner thinking tokens for the hosted study.
6. Total generated tokens.
7. End-to-end latency.
8. Identical renderer settings and test-execution limits across conditions.
9. These diagnose the intervention strength and total system cost.
10. They are not primary success metrics.

### G. Internal Representation and Causality

1. Planner-input probe performance.
2. Planner-output probe performance.
3. Renderer-ingestion probe performance.
4. Improvement over visible-text and length baselines.
5. Bidirectional interchange effect.
6. Difference between target and control interventions.
7. Functional preservation under intervention.
8. Transfer from paraphrase set 1 to paraphrase set 2.

### H. Statistical Unit

1. Base tasks are the independent clusters.
2. Generations measure within-task stochasticity.
3. More generations do not replace more base tasks.
4. Keep every paraphrase and variant of one task in the same cluster.

### I. Analysis

1. Use paired per-task effects.
2. Use task-clustered bootstrap confidence intervals.
3. Show task-level scatter rather than only aggregate averages.
4. Match structured and free-form conditions by observed total length.
5. Report content-token matching as a secondary analysis.
6. Report the independently generated and paired-format comparisons separately.
7. Freeze prompt wording, layer selection, direction, patch magnitude, and exclusion rules before final-test evaluation.
8. If fewer than 16 A/B behavioral tasks survive:
   1. label the behavioral experiment a pilot.
9. The causal experiment is a mechanistic study, not a population estimate.
10. If fewer than 12 policy-counterfactual tasks survive:
    1. do not claim cross-task generalization;
    2. report the completed examples as case studies.

---

## XII. Core Success Criteria

### A. Monitorability Decoupling

1. Hidden-use examples occur at a nontrivial rate.
2. HU+ is positive:
   1. assigned-policy behavior with VG = 0 exceeds the balanced surface-only prior.
3. False certificates occur:
   1. some plans with VG = 1 produce functionally correct code that violates the assigned policy.
4. The report identifies whether visible retention fails before, after, or at the same length as assigned-policy behavior.
5. A compression-performance curve without HU+, false certificates, or a visibility-behavior separation is treated as a secondary tradeoff result.

### B. Fixed Vocabulary Versus Long Tail

1. Freeze the missing-distinction taxonomy before held-out evaluation.
2. Report top-k coverage, new-distinction rate, and the category accumulation curve.
3. Conclude only:
   1. **small recurring set**, if held-out collisions are mostly covered and category growth saturates; or
   2. **long tail**, if new held-out distinctions continue appearing.
4. Do not claim the six-field schema is sufficient merely because its named fields are present.

### C. Information-Loss Localization

1. A fact-specific signal survives held-out policy paraphrasing.
2. Its availability differs across at least two communication boundaries.
3. The activation result improves over text and length baselines.
4. The conclusion names the loss location rather than merely stating that plans affect code.
5. Reproduction on the four held-out task pairs is described as cross-task case-study evidence, not population-level generalization.

### D. Causal Representation

1. From the same policy-omitting plan:
   1. A injection shifts code toward policy A; and
   2. B injection shifts code toward policy B.
2. Both shifts exceed every matched control.
3. The effect reproduces on four held-out task pairs and is reported as case-study evidence rather than generalization.
4. Ordinary functionality is preserved.
5. A recurrent-steering-only result is labeled causal steerability, not single-state sufficiency.

### E. Clause Selection

1. The planner selects the applicable clause substantially more often than position or salience baselines.
2. Clause-order and distractor-replacement controls do not erase selection performance.
3. Confident wrong-clause plans are reported separately from simple omissions.
4. Clause selection is interpreted as one mechanism producing monitorability failures, not as the headline by itself.

### F. Bottleneck Capability Sanity Check

1. Full structured plans approach the full-document A/B direct condition:
   1. functional pass rate within five percentage points; and
   2. assigned-policy compliance within ten percentage points.
2. Report the relevant-clause-only versus full-document gap separately as the cost of clause selection.
3. Failure means the bottleneck itself is limiting before plan shortening is analyzed.

### G. Secondary Format Analysis

1. At matched observed length, compare structured and free-form plans on:
   1. functionality;
   2. assigned-policy compliance;
   3. visible policy retention;
   4. applicable-clause recall; and
   5. A/B ambiguity.
2. Keep independently generated and information-matched format comparisons separate.
3. Do not present a structured-format win as the central interpretability result.

### H. Informative Negative Results

1. The project remains informative if it finds:
   1. visible policy and behavior remain tightly coupled;
   2. HU+ is approximately zero;
   3. activations add no information beyond visible text;
   4. policy information is decodable but not causally usable;
   5. collision categories saturate into a small repairable set;
   6. no advantage for structure after information matching;
   7. the bottleneck limits capability before compression; or
   8. shorter plans produce negligible end-to-end efficiency gains.

---

## XIII. Stop and Pivot Rules

1. **No headroom**
   1. Change tasks or renderer before training.
2. **Distractors are too easy**
   1. Replace generic clauses with more plausible same-domain clauses.
   2. Keep them genuinely irrelevant to the surface task.
3. **Distractors are too hard or ambiguous**
   1. Remove clauses that plausibly apply.
   2. Keep full-document performance above the floor.
4. **Renderer ignores plans**
   1. Fix the renderer prompt or stop the causal study.
5. **Local model at capability floor**
   1. Move to Qwen3.5-9B.
6. **No overlapping plan lengths**
   1. Change concision instructions before comparing formats.
7. **No natural fact omissions**
   1. Keep the compression frontier.
   2. Continue explicit A-versus-B representation analysis.
   3. Do not claim a hidden-use intervention.
   4. Treat the contradictory-text intervention as an optional harder test.
8. **Probe does not generalize**
   1. Report the failure.
   2. Do not patch a cherry-picked direction.
9. **Intervention is non-specific**
   1. Report that the representation was not shown to be causally selective.
10. **Wide task-level uncertainty**
   1. Report the study as a pilot.

---

## XIV. Time Plan: 40–50 Hours

| Hours | Work |
| --- | --- |
| 0–5 | Repository, test harness, activation-hook smoke test, and three-task multi-clause headroom gate |
| 5–10 | Build three A/B counterfactual pairs and run the causal pipeline end to end |
| 10–18 | Expand tasks; write and audit multi-clause safety documents and applicable-clause metadata |
| 18–23 | Hosted prompt-only selection/compression experiment; freeze prompts and inclusion rules |
| 23–31 | Planner QLoRA SFT; local model-floor and renderer-dependence checks |
| 31–37 | Generate compression frontier; label clause selection and policy retention; collect collision plans |
| 37–42 | Cache activations; estimate task-balanced directions; run probe controls |
| 42–48 | Run omitted-plan causal interchange, controls, and steering robustness check |
| 48–50 | Statistics, figures, code-diff case study, and retrospective write-up |

### A. Cut Order

1. GRPO.
2. Planner-side intervention.
3. Unseen-vulnerability-family activation transfer.
4. Additional plan formats.
5. Additional vulnerability families.

### B. Do Not Cut

1. Surface-only, relevant-clause-only, and full-document A/B controls.
2. Clause-order and distractor-replacement controls.
3. Full-plan bottleneck condition.
4. Paired-format control.
5. Opposite-policy and wrong-clause plan controls.
6. Blinded clause-selection and policy-value labels.
7. Held-out policy-paraphrase split.
8. Held-out base-task evaluation.
9. One bidirectional renderer intervention.
10. Random, lexical, unrelated-fact, and no-intervention controls.

---

## XV. Stretch Goal: GRPO as a Model Organism of Optimization Pressure

### A. Question

1. When the planner is optimized to preserve assigned-policy behavior while producing shorter plans, does visible policy information disappear even though the frozen renderer can still act on it?

### B. Gate

1. Start only after Stages 0–4 are complete.
2. For each training prompt:
   1. sample 8 candidate plans from the SFT planner;
   2. render and test one code sample per plan; and
   3. calculate within-group reward variance.
3. At least 50% of groups must have nonzero outcome-reward variance.
4. Length-only variance does not pass the gate.
5. The complete planner-to-renderer-to-sandbox batch must complete one dry run.
6. Cut GRPO if the gate fails.

### C. Training

1. Update the planner adapter only.
2. Keep the renderer frozen.
3. For each sampled plan:
   1. render code in a fresh non-thinking context;
   2. run functionality tests;
   3. run assigned-policy and opposite-policy tests; and
   4. score observed plan length.
4. Reward:

   **R = f + 𝟙[f = 1](αs − λL/Lmax)**

5. Where:
   1. f is functionality-test performance;
   2. s is assigned-policy-test performance;
   3. L is observed plan length;
   4. Lmax is the generation ceiling;
   5. α weights policy compliance; and
   6. λ applies compression pressure.
7. Do not reward visible fact labels, schema completeness, or human legibility.

### D. Evaluation

1. Compare the SFT and GRPO planners on:
   1. functional correctness;
   2. assigned-policy compliance;
   3. plan length;
   4. applicable-clause selection;
   5. visible policy retention;
   6. confident wrong-clause rate;
   7. false-certificate rate;
   8. hidden-use rate;
   9. probe transfer; and
   10. causal interchange effect.
2. The interesting result is not that the rewarded outcomes improve.
3. The interesting result is whether optimization preserves behavior while making the visible intermediate language or its internal fact representations less monitorable.

---

## XVI. Final Outputs

1. **Monitorability frontier**
   1. VG, HU+, FC, applicable-clause selection, confident wrong-clause plans, assigned-policy behavior, and functionality versus observed plan length.
2. **Information-flow map**
   1. policy and clause-relevance decoding at planner input, planner output, and renderer ingestion across the four monitorability quadrants.
3. **Omitted-plan causal interchange plot**
   1. A-injected and B-injected policy behavior from the same plan against every control.
4. **Schema coverage analysis**
   1. top-k collision coverage;
   2. new-distinction rate; and
   3. category accumulation curve.
5. **Policy-collision case study**
   1. one exact plan;
   2. policy-A and policy-B functionally correct code;
   3. minimal code diff; and
   4. missing policy distinction.
6. **Secondary format and compression frontier**
   1. independently generated structured versus free-form plans;
   2. information-matched structured versus free-form plans; and
   3. clause selection, functionality, and assigned-policy compliance versus observed plan length.
7. **Retrospective write-up**
   1. organized around the strongest one or two findings after the experiments are complete.

---

## XVII. Future Work: Repeated Context Handoffs

1. The core experiment contains one planner-to-renderer context handoff.
2. A future multi-hop version would:
   1. generate code in the first renderer;
   2. ask a fresh context to summarize the implementation into another compressed plan; and
   3. ask a third context to extend or modify the code using only that summary.
3. Measure whether applicable-clause retention, visible policy retention, HU+, and false certificates compound across hops.
4. Test whether fact retention decays approximately multiplicatively with each serialization boundary.
5. This is not part of the present experiment and should not be described as a tested multi-session result.

---

## XVIII. Verified Prior Work for the Final Write-Up

1. [Chain-of-Thought Monitorability](https://arxiv.org/abs/2507.11473)
   1. motivates treating visible reasoning as a potentially useful but fragile safety signal.
2. [Compressed Chain of Thought](https://arxiv.org/abs/2412.13171)
   1. studies efficient reasoning through compressed dense representations.
3. [Coconut](https://arxiv.org/abs/2412.06769)
   1. studies reasoning in continuous latent states rather than ordinary language.
4. [CWEval](https://arxiv.org/abs/2501.08200)
   1. provides the functionality-and-security benchmark foundation.
5. [SecPI](https://arxiv.org/abs/2604.03587)
   1. studies secure-code improvement through internalized structured security reasoning.
6. [Activating Latent Security Knowledge through LLM-Guided Risk Analysis for Secure Code Generation](https://arxiv.org/abs/2606.16244)
   1. studies training-free activation of task-relevant security knowledge.
   2. The current arXiv version calls the method BRACE; do not cite the older SPARK title without checking the version used.
7. [Mechanistic Interpretability of Chain-of-Thought Reasoning via Sequential Activation Patching](https://arxiv.org/abs/2608.22332)
   1. motivates checking temporally distributed effects rather than assuming one static-token intervention is sufficient.
8. Re-check titles and versions when writing the final related-work section.
