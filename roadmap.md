# THE ENGINEER BRAIN — FINAL MASTER ROADMAP

---

## THE ONE INSIGHT THAT CHANGES EVERYTHING

Every existing agent learns after failure. Real engineers feel something is wrong before failure. That feeling is compressed experience — thousands of failures encoded into pattern recognition so fast it feels like instinct. This roadmap builds that. Not recovery from failure. Anticipation before it.

---

## THREE RULES THAT NEVER BREAK

Read these first. Everything else depends on them.

**Rule 1.** Model written before execution. Locked after. No exceptions. Ever.
Recovery: if code was written first, write the model from the existing code. If model and code conflict, the code is wrong.

**Rule 2.** Belief replacement must name the specific false assumption. Symptom descriptions rejected without negotiation.
Recovery: return to the failure, do not proceed until the assumption is named precisely.

**Rule 3.** No silent continuation when a guarantee is broken. Stop. Surface all dependents. Resolve. Then continue.
Recovery: roll back to last verified state, mark all work since as suspect.

---

## THE FOUR ERROR CLASSES

These apply everywhere. Learn them before Phase 1.

- **Class 1 — Execution error.** Code ran and broke. Visible signal.
- **Class 2 — Logic error.** Code ran, did not break, wrong answer. No visible signal.
- **Class 3 — Design error.** Code ran, correct answer, becomes unmaintainable when requirements change. No signal ever.
- **Class 4 — Requirement error.** Code is perfect and solves the wrong problem. Most expensive. Looks like success.

---

## THE FIFTEEN ERROR TYPES

These are the real categories. They map to investigation strategy. Classification is not optional.

Syntax, Logical, Runtime, Build, Integration, Environment, Performance, Concurrency, Security, Database, Network, Dependency, Deployment, Data, Production-only.

Production-only errors never appear in local testing. They appear under real traffic, specific data combinations, random timing. The agent must reason about them theoretically: given this code, under what real-world conditions does it fail that no local test would ever catch?

---

## THE FIFTEEN PROJECT TYPES

Every task belongs to one of these. Knowing which one changes how you approach it.

Greenfield, Brownfield, Feature Development, Bug Fixing, Performance Optimization, Refactoring, System Design, Integration, Migration, PoC, Security, Scaling, DevOps, Data and Analytics, Automation.

The most important insight nobody states plainly: real engineering work is 70% reading and understanding, 30% writing. An agent that cannot read existing code like a detective cannot do real work.

---

## ERROR TYPE TO PROJECT TYPE MAPPING

This is what nobody documents.

Syntax and Build errors appear most in Greenfield, Feature Development, Migration.
Logical errors appear most in Feature Development, Bug Fixing, Refactoring.
Runtime errors appear most in Bug Fixing, Integration, Production.
Integration errors appear most in Integration, Feature Development, Migration.
Environment errors appear most in DevOps, Deployment, Brownfield.
Performance errors appear most in Performance Optimization, Scaling, Database work.
Concurrency errors appear most in Scaling, System Design, Database work.
Security errors appear most in Feature Development, Integration, Brownfield.
Database errors appear most in Feature Development, Migration, Performance Optimization.
Dependency errors appear most in Greenfield, Migration, DevOps.
Production-only errors appear most in Bug Fixing, Scaling, Performance Optimization.

The agent uses this mapping when writing the pre-mortem. If the task is Performance Optimization, concurrency and database errors are most likely. Check those concept anchors first.

---

## PHASE 0 — UNIVERSAL TOOL LAYER


Build one universal interface:

```
execute({ language, code, timeout })
→ stdout, stderr, exitCode, duration
→ error { message, line, stack, type }

read_file(path)
write_file(path, content)
list_files(directory)
search(query)
fetch(url)
log(result) → raw JSON + timestamp + environment
```

Language is a parameter from day one. Output format identical for every language. Routes internally to Node.js for JS, python3 for Python, javac and java for Java.

Environment captured on every execution: runtime version, memory available, input size, execution time. This is your performance baseline. Every future change is compared against it. Agents that add this later lose the baseline permanently.

**Done when:** Agent runs any file in any language and captures everything identically, including environment.

---

## PHASE 1 — FAILURE FIRST


Feed 30 broken files. JS only. Real complexity. No toy examples. No fixing. No helping. Observe only.

Real complexity means: async bugs that only appear under specific timing, state mutation bugs that only appear with certain input sequences, integration bugs that only appear when two functions interact in a specific order. Toy examples produce shallow failure sentences. Shallow failure sentences poison everything built on top of them.

For every failure, the agent produces:

```
Believed:          X
Reality:           Y
Concept broken:    Z
Why X felt right:  specific reason — not vague
Error class:       1 / 2 / 3 / 4
Error type:        which of the 15 error types
Project context:   which of the 15 project types this would appear in
Concept guess:     early tag — even if uncertain
```

Why X felt right is the most important field. The wrong belief is not the learning. The reason the wrong belief felt correct is the learning. That reason is the source of the next bug.

**Early Meta Check starts here, not Week 4.** After every 5 failures: is the same error class repeating? Same error type? Same concept tag? Flag immediately. Do not wait to discover a blind spot that has contaminated 50 sentences.

**Done when:** 30 failure sentences. All fields complete. All 15 error types encountered at least twice. No shallow entries accepted.

---

## PHASE 2 — MODEL BEFORE CODE


Before every function:

```
Problem:          undesired state → desired state
Constraint:       why this is non-trivial
Concept:          which concept anchor applies
Error classes:    which of the 4 classes is most likely here
Error types:      which of the 15 types are most likely here
Project type:     which of the 15 contexts this belongs to
Model:            how the mechanism works
Invariant:        what must always stay true
Failure modes:    where this can break
Boring solution:  is there a simpler, proven, boring solution first?
Confidence:       0.0 to 1.0
Decay rate:       fast / slow / never
Cost estimate:    write time / test time / debug time / change time
```

**Model locked the moment execution starts. Never touched after.**

**The boring solution check** — this is what the roadmap was missing. Before implementing any solution, the agent asks: is there a boring, obvious, proven way to do this? Clever solutions create technical debt. Boring solutions scale. If a boring solution exists and was rejected, the rejection must be written down explicitly with a reason.

**Decay rates assigned on creation:**
- Fast: anything dependent on external APIs, library versions, data assumptions.
- Slow: language behavior, framework conventions, architectural patterns.
- Never: definitions, mathematical truths, logical invariants.

**Cost estimate — four rough numbers:** Time to write. Time to test. Time to debug if wrong. Time to change if requirements shift. They do not need to be accurate. They need to exist. The act of estimating forces thinking about cost. Estimates improve over time.

**Guarantee Registry:** Words like always, never, sorted, validated, initialized, before, after trigger registration. One owner per guarantee. Conflict means stop and resolve immediately.

**Friction scaling by size:**
- Under 10 lines: write it, one check.
- 10–50 lines: write model first, justify why simpler does not work.
- 50–200 lines: break into named pieces, justify each independently.
- Over 200 lines: stop. Something is wrong in the design. Redesign before writing.

**Working memory log — updated after every non-trivial step:**

```
Confirmed:  what I have verified
Uncertain:  what is still unknown
Assuming:   what I am about to take as true without verification
```

This prevents the most common failure in complex tasks: the agent that started correct and drifted wrong without noticing.

**Done when:** Every function has a locked model with all fields. Every guarantee has one owner. Working memory log active.

---

## PHASE 3 — BELIEF REPLACEMENT


On every failure:

```
Old belief:              X
Reality:                 Y
Specific assumption:     named precisely — not described vaguely
Error class:             which of the 4 classes
Error type:              which of the 15 types
What else assumed same:  every function holding this belief
Concept anchor domain:   which anchor does this touch
New belief:              corrected version
Decay rate:              assigned immediately
Recovery action:         what must be checked or rolled back
```

**Hard rejection rule:** "Something went wrong with async" is rejected. "I believed the callback fired before the return statement" is accepted. If it cannot name the specific assumption, it is rejected and rewritten. No negotiation.

**What else assumed same is non-negotiable.** One false belief almost never lives in one place. When a wrong assumption is found, check everywhere it exists before touching anything else. This single step prevents the same belief from breaking three different parts of the system two days later.

**After every successful execution:** Did success confirm the model, or could this have worked for a different reason? Under what conditions does this success fail? This catches the most dangerous state in any learning system — the agent that was right for the wrong reason. It gets confidently wrong at scale and has no idea why.

**Recovery protocol for when rules have already been violated:**
- Wrote code before model: stop, write model from existing code, if model and code conflict, code is wrong.
- Continued past broken guarantee: stop, roll back to last verified state, mark all work since as suspect.
- Belief replacement did not name specific assumption: reject, return to failure, do not proceed until named.

**Done when:** Every failure produces a causal chain. Every success examined for coincidental correctness. Recovery protocol enforced.

---

## PHASE 4 — DECISION MEMORY


Every design decision stored as:

```
Problem:        what existed
Decision:       what was chosen
Rejected:       what was not chosen and why
Boring option:  was there a simpler solution and why was it rejected
Assumptions:    what must be true for this to hold
Confidence:     certainty at decision time
Cost estimate:  write / test / debug / change
Impact scope:   which modules depend on this
Timestamp:      exact date and time
Decay rate:     fast / slow / never
Project type:   which context this decision belongs to
```

Before every new function: query — have I made a design decision in this concept domain before? If yes, surface it. Agent either reuses the reasoning or explicitly states why this situation is different. No silent re-deciding.

**Confidence decay with time:** Fast-decay decisions re-verified when confidence drops below 0.5. Slow-decay decisions re-verified when confidence drops below 0.3. Never-decay decisions never re-verified.

When any assumption breaks, every decision that depended on it surfaces automatically. Agent cannot proceed without acknowledging which decisions are now suspect.

**Done when:** Agent stores why things exist, retrieves past decisions before making new ones in the same domain, and decays confidence over time correctly.

---

## PHASE 5 — GUARANTEE VALIDATION


When reading any external code: pull only guarantees the current context depends on. Shallow check only. If not fulfilled: flag, reduce confidence, surface every dependent immediately, stop.

**Surface all dependents at once — not one at a time as they crash.** One broken guarantee silently invalidates a chain. Discovering them sequentially is the most expensive way to find them.

**Environment check before every execution:** Runtime version. Resource constraints. Input scale. After every failure, ask: is this a logic failure or an environment failure? These are completely different things with completely different fixes. An agent that cannot make this distinction is not production-safe.

**Done when:** Agent never acts on a stale belief. Environment checked before every execution. No silent continuation anywhere.

---

## PHASE 6 — CODE READING DISCIPLINE

This phase is missing from every other roadmap. Real engineers spend 70% of their time reading code, not writing it. The agent must build this as a formal skill.

When reading any existing file, the agent asks five questions in order before doing anything else:

1. What problem was the original author trying to solve? Not what the code does — what pain caused someone to write it.
2. What assumptions did the original author hold that may no longer be true?
3. What guarantees does this code make that other code depends on?
4. What does this code fail silently on — where does it produce wrong output with no error signal?
5. What changed recently that could have introduced a regression?

**The "what changed" discipline.** Most bugs are introduced by changes, not by code that was always wrong. "What changed recently" is often more powerful than "what is wrong." The agent must always ask this question before beginning any bug investigation.

**The second reader test.** After writing any code, the agent reads it as if it has never seen it before, with no context. It asks: is the intent of this code visible from the code alone? If not, the code is a future debugging problem. This catches clarity failures that no linter or test will ever catch.

**Minimum reproducible example rule.** Before fixing any bug, the agent must create the smallest possible reproduction — the fewest lines that reliably trigger the failure. This single discipline eliminates half of all debugging time. Agents that skip it waste hours fixing the wrong thing.

**Done when:** Agent applies all five reading questions to every existing file it touches. Minimum reproducible example created before every bug fix.

---

## PHASE 7 — EXPLANATION TEST
**Week 3 — Day 5**

After every task, agent explains at four levels:

```
Level 0: one sentence — what problem does this solve
Level 1: plain language — what it does, no jargon
Level 2: technical — how it works, exact mechanisms
Level 3: architectural — why this design, what tradeoffs, what was rejected
```

Level 0 is the most important and the most ignored. If the agent cannot state in one sentence what problem its code solves, it built something without knowing why it needs to exist. This catches Class 4 errors — correct code for the wrong problem — because those look exactly like success in every other test.

**Adversarial self-challenge:** After all four levels, the agent generates the three hardest questions someone could ask to challenge the explanation. If it cannot generate hard questions about its own explanation, the explanation is shallow.

**All four error classes evaluated before marking complete:**
- Class 1: did it run without errors?
- Class 2: does it produce the right answer?
- Class 3: what does this look like when requirements change?
- Class 4: does it solve the actual problem that was stated?

If any level fails or any class fails: back to Phase 3.

**Done when:** Agent passes all four explanation levels and all four error class checks on every task.

---

## PHASE 8 — META OBSERVER
**Week 4**

Runs offline only. Never during execution.

Detects: repeated thinking mistakes, blind spots, overconfidence patterns, false success, concept-level error recurrence across different languages.

**Silent Success Audit runs separately.** Tracks tasks where the agent produced correct output through wrong reasoning. More dangerous than visible failures because the agent reinforces broken beliefs from them. At least three silent successes must be identified before this phase is considered complete.

Output format:

```
BIAS DETECTED:
Pattern:    overconfidence on first model in async domain
Evidence:   19/25 async failures had confidence above 0.8
Impact:     agent delayed correction, compounded errors

ADJUSTMENT:
Cap first confidence at 0.6 in async-related functions
Require explicit validation before proceeding above 0.7
Flag every high-confidence async decision for 30 days
```

**Cross-phase backward scan:** When a significant bias is found, it triggers a backward scan of all stored artifacts in the same concept domain. Some unchanged. Some marked suspect. Some fully revised. This is refinement, not accumulation. Accumulation fills storage. Refinement builds understanding.

**Done when:** First bias report with evidence and adjustments. At least three silent successes identified. At least one backward scan completed.

---

## PHASE 9 — CONCEPT ANCHORS
**After 50–100 Real Tasks**

Cluster failure sentences from Phases 1, 3, and 6. Each cluster becomes one anchor:

```
Concept:          name of problem class
Core truth:       language-independent rule
Why it exists:    what problem it was invented to solve
Variations:       how it appears in JS / Python / Java
Traps:            real failures from execution history only
False beliefs:    what made the wrong model seem reasonable
Connected to:     other anchors this relates to
Error class bias: which error class this concept most often produces
Error type bias:  which of the 15 types this concept most produces
Project type:     which of the 15 contexts this appears in most
Decay rate:       fast / slow / never
Evidence count:   number of independent failures that confirmed this
Status:           provisional (under 3) / stable (3 or more)
```

**Nothing predefined. Everything from real failures.**

**Minimum evidence threshold:** One failure is an observation. Two is a coincidence. Three independent failures from different contexts makes an anchor stable. Until three confirmations, anchor is provisional. Provisional anchors are used but treated as strong hypotheses, not established truth.

**Failure cascade field — this is what the roadmap was missing.** Most production failures are not single-point failures. They are cascades. Each anchor must include: if this fails, what else does it typically take down with it? This is the difference between a junior engineer who fixes one bug and a senior engineer who prevents the next three.

**Connection map:** Async connects to state management. State management connects to concurrency. Concurrency connects to performance. When the agent struggles with one anchor, it automatically checks connected anchors. This builds a web, not a list.

**Transfer test immediately on creation:** Every anchor tested against a problem in a different language the moment it is created. If it does not transfer, it is rebuilt before being stored. An anchor that only works in one language is not a concept anchor.

**Done when:** 10–15 evidence-based anchors. All connections mapped. Every anchor transfer-tested. Every anchor has evidence count and status.

---

## PHASE 10 — SECOND LANGUAGE
**After Anchors Stable**

Introduce Python as transfer test, not new learning.

Process for every problem:
1. Check concept anchors first.
2. State: "same problem as X, different syntax."
3. Solve using existing model adapted to new syntax.
4. If cannot map — anchor is weak — rebuild before continuing.

Both directions required. Forward: JS problem solved in Python. Reverse: Python bug explained using JS understanding. If reverse fails, anchor is syntax-level not concept-level. Rebuild it.

**Real transfer metric — concept-level error recurrence:** Tag every error with its concept anchor. Count how many times the agent makes an error in the same concept anchor domain after having seen a failure there. A stale closure bug in JavaScript and a captured loop variable bug in Python are the same mistake. Speed metric counts them as different. Concept-level metric counts them correctly as one.

Target: concept-level error recurrence below 10% after 30 tasks in the new language.

**Done when:** Concept-level error recurrence below 10%. Transfer works in both directions. No anchor required relearning from scratch.

---

## PHASE 11 — FRAMEWORK LEARNING
**Per Framework**

Six steps. In order. No shortcuts.

**Step 1 — WHY.** What specific pain existed before this framework? What was breaking without it? If the agent cannot answer, it knows only the API, not the purpose.

**Step 2 — MENTAL MODEL (one line only).**
- React: UI = f(state)
- Spring: container owns object lifecycle
- Express: request → middleware chain → response
- Django: ORM abstracts SQL, views handle request logic

More than one line means the model is incomplete.

**Step 3 — MAGIC.** What happens invisibly?
- React: virtual DOM reconciliation
- Spring: proxy creation, bean lifecycle
- Django: ORM query building, migration system

Understanding the invisible is what separates debugging from guessing.

**Step 4 — TRAPS (real execution only).** Every trap must come from the agent's own sandbox failures. Not documentation. Not tutorials. Real pain only.

**Step 5 — WHEN NOT TO USE.** An agent that knows when not to use a framework understands it more deeply than one that only knows how. This is the rarest engineering judgment. Teach it explicitly every time.

**Step 6 — DEGRADATION TEST.** Show the agent a project built correctly with the framework that has grown to a size where the framework now creates more problems than it solves. Agent diagnoses the degradation. This teaches when to move away — the rarest and most valuable framework knowledge that exists.

**Step 7 — SANDBOX.** Build a minimal example. Break it deliberately three ways. Pre-mortem before sandbox: agent states the most likely failure before running. Apply full belief system to every failure.

Every framework is also mapped to which of the 15 project types it is used in most, and which of the 15 error types it most commonly produces.

**Done when:** Agent understands purpose, boundaries, invisible behavior, failure modes, exit conditions, and degradation point.

---

## PHASE 12 — PROJECT MASTERY
**Ongoing — All 15 Project Types**

Full loop for every task:

```
1.  Review concept anchors — which known traps are likely here?
2.  Identify project type — which of the 15 is this?
3.  Check error mapping — which error types does this project type most produce?
4.  Pre-mortem — if this fails, what will cause it?
5.  Boring solution check — is there a simpler proven way first?
6.  Set working memory — three things not to lose track of
7.  Define problem: undesired state → desired state + constraint
8.  Write model before any code — locked on execution start
9.  Code with guarantee registration
10. Execute with environment check
11. Update working memory after every non-trivial step
12. On failure → minimum reproducible example first → name specific assumption → propagate correction → recover
13. On success → examine why it worked → under what conditions does it fail?
14. All four error classes evaluated before marking complete
15. Explain at all four levels with adversarial self-challenge
16. Store decision with boring option, cost estimate, confidence, decay rate, timestamp
17. After completion — what signal existed earlier that this failure would have been visible?
```

Step 17 closes the loop. Track the gap between when a problem existed and when the agent detected it. This gap shrinks over time. That shrinkage is measurable. That is the real proof the system is working.

**How each major project type is handled:**

**Brownfield (existing system):** Agent reads code using the five reading questions before touching anything. Maps every file it reads to existing concept anchors. Pulls and checks relevant guarantees before writing. Never modifies without understanding what it would break. The "what changed" discipline applied to every bug investigation.

**Bug Fixing:** Agent classifies bug into one of the 15 error types immediately. Creates minimum reproducible example before writing a single fix. Asks "what changed recently" before asking "what is wrong." Environment failure vs logic failure distinction made explicitly.

**Performance Optimization:** Agent checks cost estimates from past decisions. Identifies which functions have the largest gap between estimated and actual performance. Traces bottlenecks using execution time baselines established in Phase 0. Concurrency and database anchors checked first.

**Refactoring:** Hard rule — refactoring must satisfy at least one of three criteria: reduces complexity, improves readability, removes duplication. If none are demonstrably true, the refactor is rejected. Before and after comparison mandatory. Second reader test applied to every refactored function.

**Integration:** Every external dependency classified by decay rate on first touch. Fast decay for external APIs — they change without warning. Explicit failure handling built for timeout, wrong format, authentication failure, rate limiting, service unavailable.

**Security:** Specific concept anchor for every security error type. For every function that touches user input or authentication, security anchors are checked before writing code, not after.

**PoC:** Minimum footprint rule applied most aggressively. Goal is concept validation. Model still written before code. Explanation test is Level 0 and Level 1 only.

**Done when:** Agent completes projects with pre-failure prediction, all four error classes evaluated, measurably shrinking detection gap.

---

## CONTINUOUS LEARNING LOOP

```
1.  Encounter new concept, error, or pattern
2.  Check: have I seen this problem class before?
3.  If yes: map to anchor, note variation, check evidence count
4.  If no: create provisional anchor, minimum evidence threshold applies
5.  Test in sandbox, break deliberately
6.  Tag failure with concept domain, error class, error type
7.  Update anchor evidence count
8.  If evidence count reaches 3: mark stable
9.  Trigger backward scan of related stored artifacts
10. Check new belief for contradictions with existing beliefs in same domain
11. Update failure cascade map for affected anchors
```

**Internet and documentation learning rule:** The agent cannot copy. It must read, convert to belief, test in sandbox, confirm or fail, then store. The difference between copy-paste and learning is that real learning updates the agent's behavior under novel conditions. Copy-paste only works in the exact situation it was copied from.

---

## FOLDER STRUCTURE

```
/core
  /executor           ← universal execute({ language, code })
  /belief_engine      ← belief tracking, replacement, contradiction check
  /model_engine       ← pre-execution models with decay rates
  /decision_engine    ← decisions with cost estimates and retrieval
  /working_memory     ← confirmed / uncertain / assuming per task
  /evaluator          ← four levels + adversarial + four error classes
  /meta_observer      ← offline bias detection and backward scan
  /recovery           ← recovery protocols for rule violations
  /code_reader        ← five reading questions, second reader test

/concepts
  /anchors            ← universal problem types with evidence counts and cascade maps
  /connections        ← anchor relationship map
  /provisional        ← anchors under 3 confirmations

/languages
  /js
  /python
  /java

/frameworks
  /react
  /spring
  /express
  /django

/projects
  /ongoing
  /completed

/logs
  /executions         ← with environment and performance baseline
  /failures           ← with error class, error type, and concept tag
  /decisions          ← with boring option, cost estimates, decay rates
  /bias_reports
  /silent_successes   ← correct output through wrong reasoning
  /detection_gaps     ← time between problem existence and detection
  /minimum_repros     ← smallest reproductions for each bug class
```

---

## TWO METRICS THAT PROVE IT IS WORKING

**Metric 1 — Concept-level error recurrence below 10%.**
Not error recurrence. Concept-level. Same mistake class across any language after having encountered it once. Drops toward zero as anchors mature.

**Metric 2 — Pre-mortem accuracy above 60% after Phase 12.**
Agent predicts what will fail before running code. Correct more than 60% of the time. If not, the concept anchor web is not working. Fix before adding anything else.

When both metrics move in the right direction simultaneously, you have built something no other roadmap produces.

---

## WHAT THIS AGENT BECOMES

Not faster at recovering from failure. Needing fewer failures to learn.

It reads existing systems like a detective. It classifies every error before investigating. It creates minimum reproducible examples before fixing anything. It asks what changed before asking what is wrong. It checks for boring solutions before clever ones. It knows when not to use a framework, not just how to use it. It models failure cascades, not just failure points. It examines its own successes for coincidental correctness.

That is a real engineer. Not a chatbot that writes code.