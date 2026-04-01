# OPUS — REAL ENGINEER AI AGENT ROADMAP

## Executive Summary

**Goal:** Build an AI agent that behaves exactly like a senior software engineer — not by writing fast code, but by:
- Reading code methodically before modifying
- Asking the right questions before implementing
- Classifying errors precisely before fixing
- Making decisions with documented tradeoffs
- Detecting problems before they break systems
- Learning from every failure without repeating mistakes

**The Core Insight:** Real engineers preserve failure information. They don't just recover from failure — they transform each failure into a pattern that prevents the next three failures. This roadmap builds that pattern recognition system from first principles using evidence-based learning.

---

## THE FOUNDATION — 4 RULES + 4 ERROR CLASSES + 15 ERROR TYPES + 15 PROJECT TYPES

### RULES (Never Break These)

**Rule 1: Model → Execute → Lock**
- Write the model BEFORE any code
- Lock it the moment execution starts
- Recovery: If code was written first, reverse-engineer the model from existing code
- If model and code conflict → code is wrong

**Rule 2: Belief Specific, Never Vague**
- Every wrong belief must name the exact false assumption
- "Something went async wrong" → REJECTED
- "I believed the callback fired before the return statement" → ACCEPTED
- Recovery: Return to failure, do not proceed until named precisely

**Rule 3: No Silent Continuation**
- Every guarantee has one owner
- When a guarantee breaks → stop immediately
- Surface all dependents before proceeding
- Recovery: Roll back to last verified state, mark all work since as suspect

---

### 4 ERROR CLASSES

| Class | Definition | Signal | Recovery |
|-------|-----------|--------|----------|
| **Class 1: Execution** | Code ran and crashed | Visible error | Fix the crash |
| **Class 2: Logic** | Code ran, correct output was not produced | NO signal | Debug the logic |
| **Class 3: Design** | Code works now, unmaintainable later | NO signal | Redesign when requirements change |
| **Class 4: Requirement** | Perfect code for the wrong problem | Looks like success ⚠️ | Re-read the problem statement |

**Critical:** Class 4 errors are invisible. They look like perfect success. They are the most expensive failures. Before marking any task complete, ask: does this code solve the actual problem that was stated?

---

### 15 ERROR TYPES

| Type | Root Cause | Detected By | Real Example |
|------|-----------|-------------|--------------|
| **1. Syntax** | Wrong keywords, missing semicolon | Compiler | `int x = y +` — missing value |
| **2. Logical** | Wrong conditions, bad calculations | Testing | `if (x > 10)` when should be `x >= 10` |
| **3. Runtime** | Null pointer, undefined, crash | Error signal | `data.map()` when data is null |
| **4. Build/Compile** | Dependency issues, version conflicts | Build tool | Missing package in package.json |
| **5. Integration** | External API failure, wrong format | Integration test | API returns 500, code expects 200 |
| **6. Environment** | Works locally but fails in production | Production only | Different ENV variables set |
| **7. Performance** | Slow response, high memory, CPU spike | Load testing | Query takes 30s instead of 1s |
| **8. Concurrency** | Race condition, deadlock, thread issue | Race testing | Two threads access same resource |
| **9. Security** | SQL injection, XSS, unauthorized access | Security scan | User input directly in SQL query |
| **10. Database** | Query fails, deadlock, data inconsistency | DB testing | Constraint violation on insert |
| **11. Network** | Timeout, connection refused, DNS issue | Network testing | Request hangs for 60s |
| **12. Dependency** | Library conflicts, breaking changes | Version upgrade | New version breaks API |
| **13. Deployment** | CI/CD failure, server crash | Deployment | Docker build fails, app won't start |
| **14. Data** | Corrupted data, wrong format, missing | Data validation | Expecting array, got string |
| **15. Production-only** | Only happens under real traffic, random | NEVER in local test | Appears at 1000 req/sec, not at 10 |

---

### 15 PROJECT TYPES & ERROR PROBABILITY MAPPING

| Project Type | Definition | Most Common Error Types | Approach |
|--------------|-----------|------------------------|----------|
| **1. Greenfield** | Building from scratch | Syntax, Build, Dependency | Design first, document assumptions |
| **2. Brownfield** | Existing system, uncertain code | Environment, Logic, Concurrency | Read code first, map guarantees |
| **3. Feature Dev** | Add new capability | Logic, Database, Integration | Model before code, test edge cases |
| **4. Bug Fixing** | Fix broken code | Runtime, Logic, Concurrency | Create minimum repro, ask "what changed?" |
| **5. Performance** | Make it faster | Performance, Concurrency, Database | Baseline first, identify bottleneck |
| **6. Refactoring** | Clean up code | Logic (silent), Design | Verify behavior unchanged, second reader test |
| **7. System Design** | High-level architecture | Design, Performance, Concurrency | Draw diagrams, document tradeoffs |
| **8. Integration** | Connect external systems | Integration, Network, Security | Explicit failure handling, retry logic |
| **9. Migration** | Move data/systems | Data, Deployment, Production-only | Dry run, zero-downtime plan |
| **10. PoC** | Proof of concept | All types equally | Minimize scope, test idea feasibility |
| **11. Security** | Fix vulnerabilities | Security, Logic, Integration | Audit inputs, encrypt data, test attacks |
| **12. Scaling** | Handle more load | Performance, Concurrency, Database | Load test, cache strategy, async |
| **13. DevOps** | Setup CI/CD, infrastructure | Deployment, Environment, Build | Dockerfile, pipelines, monitoring |
| **14. Data/Analytics** | Collect, process, report | Data, Performance, Logic | Pipeline design, verify aggregations |
| **15. Automation** | Scripts and bots | Runtime, Logic, Dependency | Error handling, retry strategy, logging |

---

## PHASE GATES & BEHAVIOR VERIFICATION

Each phase has **must-do criteria** and **behavioral checkmarks**. Agent cannot advance to next phase until all checks pass.

---

## PHASE -1: UNIVERSAL TOOL LAYER

**Goal:** One consistent execution interface for all languages and tools.

### What Agent Must Build

```
execute(config) {
  language,          // js, python, java, etc.
  code,              // the code to run
  timeout,           // max execution time
  environment        // capture context
}

returns {
  stdout,            // what was printed
  stderr,            // what went wrong
  exitCode,          // 0 or non-zero
  duration,          // how long it took (ms)
  error {
    message,         // what failed
    line,            // which line (if applicable)
    stack,           // full stack trace
    type,            // class/type classification
    timestamp,       // when it happened
  },
  environment {      // CRITICAL: capture every time
    runtime_version, // node 18.4, python 3.11
    memory_used,     // KB
    memory_available,// KB
    input_size,      // lines or bytes
    execution_time,  // ms
  }
}
```

### Behavior Checklist ✓

- [ ] Can execute JS, Python, Java code identically
- [ ] Output format is identical regardless of language
- [ ] Captures environment on every execution
- [ ] Baseline metrics established (first run becomes reference)
- [ ] Every future execution compared against baseline
- [ ] Timeout works reliably
- [ ] Error classification automatic (Syntax/Runtime/Logic/etc.)
- [ ] Logs include timestamp + environment + full context

### Verification

```javascript
// Agent must pass this WITHOUT modifications
const test1 = await execute({ language: 'js', code: 'console.log("test")' });
const test2 = await execute({ language: 'python', code: 'print("test")' });

// Both must have identical structure and baseline established
assert(test1.duration && test2.duration);
assert(test1.environment && test2.environment);
// After Phase -1: every future execution logged with delta from baseline
```

---

## PHASE 0: FAILURE CLASSIFICATION MASTERY

**Goal:** Observe 30+ real failures. Extract the specific belief each revealed. Classify every error into its class and type.

**Duration:** 1-2 weeks of focused observation (not debugging, not fixing)

### What Agent Must Do

For every failure, produce:

```
Failure Record {
  code,                    // the broken code
  error_signal,            // what broke
  
  believed:                // X — what agent expected
  reality:                 // Y — what actually happened
  
  specific_assumption:     // Named precisely:
                           // ✓ "I believed JSON.parse would throw on invalid JSON"
                           // ✗ "Something went wrong with parsing"
  
  why_belief_felt_right:   // The reason belief was reasonable
                           // (This is the learning, not the wrong belief)
  
  error_class:             // 1/2/3/4
  error_type:              // Which of the 15
  
  project_context:         // Which of the 15 project types
                           // (This error would appear in...)
  
  concept_candidate:       // Early guess at core concept
  
  confidence:              // 0.0 to 1.0
  
  environment:             // Exact conditions when it failed
}
```

### Data Sources

Real failures from reference projects:

**LocalMind (backend + async):**
- Examine: async/await patterns, database operations, race conditions
- Patterns: Promise handling, callback timing, state mutations

**Scrapling (web scraping + distributed):**
- Examine: network errors, data transformation, retries
- Patterns: HTTP failures, parsing errors, timeout handling

**Pinchtab (complex orchestration):**
- Examine: multi-step workflows, error propagation
- Patterns: State management across modules, cascading failures

**Superpowers (framework integration):**
- Examine: framework-specific errors, API contract issues
- Patterns: Extension points, integration boundaries

### Behavior Checklist ✓

- [ ] 30 failures documented (minimum)
- [ ] Every failure has specific assumption (NOT vague)
- [ ] All 15 error types encountered at least 2x each
- [ ] No shallow entries accepted (must explain why belief felt right)
- [ ] Every failure tagged with project type where it's common
- [ ] After every 5 failures: meta-check for repeated patterns
- [ ] Confidence scores show variation (not all 0.5 or all 1.0)
- [ ] Concept candidates suggest emerging patterns

### Verification

```
After 30 failures:
- Error type distribution: all 15 present, none dominating > 25%
- Confidence distribution: mix of high/medium/low (not all same)
- Shallow entries: ZERO
- Specific assumption quality: no "something went wrong" patterns
- Meta-check triggered: at least 2 times (every 5 failures)
```

---

## PHASE 1: MODEL ARCHITECTURE

**Goal:** Write complete model BEFORE touching code. Lock it on execution start.

**Duration:** 7-10 days (per task, not per project)

### What Agent Must Do

Before EVERY function, write locked model:

```
Model {
  problem:            // undesired_state → desired_state
  constraint:         // why non-trivial (real limitation)
  
  concept_anchor:     // Which core concept applies
  dependency_check:   // What guarantees must be true
  
  error_classes:      // Which of 4 are likely here
  error_types:        // Which of 15 are likely here
  project_type:       // Which of 15 contexts
  
  mechanism:          // How it works (one paragraph)
  invariant:          // What MUST always be true (named)
  
  failure_modes:      // Where can this break
                      // Pattern: "If X is null → Y fails → Z crashes"
  
  boring_solution:    // Simpler, proven approach
  why_boring_rejected:// If rejected, state reason explicitly
  
  decision_dependencies:   // What other decisions depend on this
  guarantee_owners:        // Who owns each guarantee
  
  confidence:         // 0.0 to 1.0 (start low)
  confidence_decay:   // fast/slow/never
  
  cost_estimate {
    write_time,       // rough hours
    test_time,        // rough hours
    debug_time,       // rough hours
    change_time,      // rough hours (if requirements change)
  }
  
  timestamp:          // when model was locked
  locked:             // true (once code starts)
}
```

### Friction Scaling by Size

| Code Size | Friction Level | Process |
|-----------|---|----------|
| < 10 lines | Minimal | Model can be 2-3 sentences. One check before execution. |
| 10–50 lines | Moderate | Full model. Justify why simpler solution doesn't work. Test complexity. |
| 50–200 lines | High | Break into 5-10 named pieces. Justify each independently. Guarantee map. |
| > 200 lines | STOP | Something is wrong. Redesign. Do not proceed. |

### Behavior Checklist ✓

- [ ] Every function has locked model (with timestamp)
- [ ] No code written before model exists
- [ ] Boring solution check done (accept or explicitly reject)
- [ ] Cost estimates written (even rough, even if low confidence)
- [ ] Failure modes section includes cascade: "If X → Y → Z"
- [ ] Invariant is testable (not vague like "data is valid")
- [ ] Confidence decay rate assigned (not just confidence level)
- [ ] Between every non-trivial step: working memory updated

### Working Memory Log (Tracked in Real-Time)

```
Confirmed:    // What I have verified to be TRUE
Uncertain:    // What is still unknown or untested
Assuming:     // What I am taking as true without verification
              // (These must be verified before proceeding)
```

**This prevents drift:** An agent that started correct and gradually became wrong without noticing.

### Verification

```
After implementing task:
- Model exists for every unit > 10 lines
- Model has accurate timestamp before first execution
- Boring solution section filled (accept or reject)
- Confidence scores varied (not all identical)
- Cost estimates have all 4 components
- Working memory log shows updates (not static)
```

---

## PHASE 2: BELIEF REPLACEMENT PROTOCOL

**Goal:** When code fails, extract the specific false assumption, not the symptom.

**Duration:** Ongoing (applies to every failure)

### What Agent Must Do

```
Belief Replacement {
  timestamp:           // when failure detected
  
  old_belief:          // X — what was assumed
  reality:             // Y — what actually happened
  
  specific_assumption: // Named precisely:
                       // ✓ "JSON parser throws undefined on invalid JSON"  
                       // ✗ "The parser failed"
  
  evidence:            // How certain we are (1 = low, 5 = high)
  
  scope_of_error:      // Every function holding this belief
                       // (Before fixing anything, mark all locations)
  
  concept_anchor:      // Which concept domain touched
  error_class:         // 1/2/3/4
  error_type:          // Which of 15
  
  recovery_action:     // What must be checked/rolled back
  propagation:         // Update all dependent decisions
  
  new_belief:          // Corrected version
  new_confidence:      // Updated confidence (usually lower)
  decay_rate:          // fast/slow/never
  
  why_success_works:   // When code succeeds, ask:
                       // Does success confirm model?
                       // Could this work for different reason?
                       // What conditions would make it fail?
}
```

### Hard Rejection Rules

❌ "Something went wrong with async"
✅ "I believed .then() fires before return statement"

❌ "The data was bad"
✅ "I believed user input was already validated"

❌ "There's a timing issue"
✅ "I believed the callback fires after database connection opens"

### Behavior Checklist ✓

- [ ] Every failure produces causal chain (not surface symptom)
- [ ] Specific assumption is testable (can verify it's true or false)
- [ ] Scope of error identified (found all other places)
- [ ] Recovery action explicit (rollback/retest/propagate)
- [ ] After success: examined for coincidental correctness
- [ ] All dependent decisions surfaced (before proceeding)
- [ ] New belief tested in sandbox before continuing

### Verification

```
Rejection rate on vague beliefs: 0%
(Every belief replacement explicitly names the false assumption)

Scope accuracy: >= 90%
(When one assumption is found wrong, 90% of other instances found before proceeding)

Silent success catches: >= 1 per 10 tasks
(Agent examines successes for wrong reasoning)
```

---

## PHASE 3: DECISION MEMORY & RETRIEVAL

**Goal:** Store decisions with tradeoffs. Retrieve before re-deciding in same domain.

**Duration:** 7-14 days (establish first 20 decisions)

### What Agent Must Do

Every design decision stored as:

```
Decision {
  timestamp:          // when decided
  
  problem:            // What state existed before choice
  decision:           // What was chosen
  
  rejected_options:   // What was NOT chosen
    option: {
      description,
      why_rejected,   // Not because it's worse
                      // But because...specific reason
    }
  
  boring_option_status:  // Was simplest option considered?
    if_rejected:        // "Yes. Rejected because...cost scaling"
    if_selected:        // "Yes. Selected as simplest approach"
  
  assumptions:        // What must be true for this to hold
                      // (These are monitored for decay)
  
  confidence:         // 0.0 to 1.0 (at decision time)
  decay_rate:         // fast (external) / slow (framework) / never (logic)
  
  cost_estimate {
    write_cost,       // hours
    test_cost,        // hours
    debug_cost,       // hours
    change_cost,      // hours (if requirements shift)
  }
  
  impact_scope:       // Which modules depend on this
  impact_count:       // Number of dependent decisions
  
  concept_domain:     // Which concept anchor area
  error_risk:         // Which of 15 error types most likely
  project_type:       // Which of 15 contexts
  
  status:             // active / deprecated / under_review
}
```

### Retrieval Rule

Before making ANY design decision:

1. Query: "Have I made a decision in this concept domain before?"
2. If YES:
   - Surface it
   - Either REUSE the reasoning or EXPLICITLY state why this situation is different
   - No silent re-deciding
3. If NO:
   - Create new decision record
   - Start confidence at 0.5 (not higher)

### Behavior Checklist ✓

- [ ] Every design decision recorded (not just code changes)
- [ ] Boring option evaluated (accept or explicit rejection)
- [ ] Cost estimates in all 4 categories
- [ ] Impact scope documented (not just "architecture")
- [ ] Before designing in same domain: past decisions surfaced
- [ ] Confidence decay tracked (fast-decay re-verified at 0.5)
- [ ] When assumptions break: all dependent decisions surface
- [ ] No silent re-deciding (decision query happens every time)

### Verification

```
Decision retrieval accuracy: >= 80%
(When agent makes decision in known domain, past decision surfaced 80%+ of time)

Silent re-deciding: 0%
(Every decision either retrieved or explicitly marked as first time)

Cost estimate accuracy range: >= 0.5x, <= 2x actual
(Estimates improve over time, but exist from day one)
```

---

## PHASE 4: GUARANTEE VALIDATION

**Goal:** Before using external code, validate that it makes the guarantees you depend on.

**Duration:** 2-3 days (establish discipline)

### What Agent Must Do

When reading any external code:

```
Guarantee Check {
  source_file:       // What code is providing the guarantee
  guarantee:         // What is explicitly promised
  dependent_code:    // What in YOUR code depends on it
  
  validation:        // How to verify it's fulfilled
    method,          // test, document check, code review
    result,          // pass / fail
    
  if_broken:         // What happens if guarantee is false
    dependent_tasks, // All tasks that depend on this
    impact_scope,    // How widespread is the impact
    
  recovery_protocol: // Immediate actions if broken
    1. Flag guarantee broken
    2. Surface all dependents (all at once, not one by one)
    3. Mark all dependent work as suspect
    4. Stop execution until resolved
    5. Roll back to last verified state
}
```

Key insight: **Surface all dependents at once.** Finding them one by one as they crash is the most expensive way to discover dependency chains.

### Environment Check (Before Every Execution)

```
ALWAYS verify before running:

// Language/Runtime
- Node version correct?
- Python version compatible?
- Java version?

// Resource constraints
- Memory available >= expected?
- Timeout sufficient?
- Input scale matches test scale?

// Dependencies
- Package versions correct?
- Environment variables set?
- External services available?

// Data
- Test data valid?
- Database state correct?
```

### Behavior Checklist ✓

- [ ] Before using external code: guarantees explicitly named
- [ ] Every guarantee has one owner (who backs it)
- [ ] Environment checked before every execution
- [ ] When guarantee breaks: all dependents surfaced simultaneously
- [ ] No silent continuation past broken guarantee
- [ ] Recovery protocol followed (stop → surface → roll back)
- [ ] Confidence reduced on all dependent work

### Verification

```
Silent continuation incidents: 0%
(Every broken guarantee stops execution immediately)

Dependent detection speed: >= 90% on first query
(When guarantee breaks, 90% of dependents found without running into them)

Environment mismatches: < 5% after Phase 4
(Environment checks prevent production surprises)
```

---

## PHASE 5: CODE READING DISCIPLINE

**Goal:** Build 70% of real engineering work — reading and understanding code methodically.

**Duration:** 10-14 days (establish deep reading habits)

### The 5 Reading Questions (In Order, Every Time)

Before modifying ANY external code, ask these 5 questions:

```
1. What problem was original author solving?
   NOT: What does code do
   YES: What pain caused someone to write this
   
   Example Bad: "This function parses JSON"
   Example Good: "This function validates webhook signatures because unsigned webhooks caused security breach in 2022"

2. What assumptions did original author hold?
   NOT: What is the code doing now
   YES: What conditions made that approach sensible
   
   Example Bad: "The code calls synchronously"
   Example Good: "Author assumed network latency was negligible. Modern API has 500ms latency. Assumption broken."

3. What guarantees does this code make?
   NOT: What does it do
   YES: What must be true for this code to not break other code
   
   Example Bad: "This function returns user data"
   Example Good: "This function guarantees: user exists, is_active=true, permissions loaded. Other code depends on all three."

4. What does this code fail silently on?
   NOT: What errors are caught
   YES: Where does it produce wrong output with no error signal (Class 2 errors)
   
   Example Bad: "It handles errors"
   Example Good: "This function silently returns empty array if user not found. Caller assumes non-empty. Cascades."

5. What changed recently that introduced regression?
   NOT: What is wrong now
   YES: What code or data change made this fail
   
   Example Bad: "The code is slow"
   Example Good: "Database index was dropped last week. Query changed from 1ms to 500ms."
```

### The Second Reader Test

After you write ANY code, read it back as if you've never seen it.

```
Does the intent of this code visible from code alone?
- Can someone understand why it exists after reading it once?
- Or do they need external documentation?

If they need docs: the code is a future debugging problem.
Rewrite it.

This catches clarity failures that no linter catches.
```

### Minimum Reproducible Example Rule

Before fixing ANY bug:

```
Can you produce the SMALLEST possible reproduction?

Pattern:
1. Start with full failing system
2. Remove one line at a time
3. Stop removing when it starts working
4. What's left is the minimum reproduction

This single discipline eliminates 50% of debugging time.
Skipping it wastes hours fixing the wrong thing.
```

### The "What Changed" Discipline

Most bugs are introduced by changes, not by code that was always broken.

```
First question in bug investigation:
"What changed recently?"

Not: "What is wrong?"
But: "What changed?"

90% of bugs are introduced by recent changes.
10% are long-standing issues.

Most agents ask wrong question. Ask "what changed" first.
```

### Behavior Checklist ✓

- [ ] Every existing file read with all 5 questions asked (in order)
- [ ] 5 reading questions documented (not skipped)
- [ ] Every new function passes second reader test (clear without docs)
- [ ] Before every bug fix: minimum reproducible example created
- [ ] Before every change in Brownfield: "what changed?" question asked
- [ ] Reading discipline log tracks all code read

### Verification

```
Modification accuracy: >= 95%
(When agent modifies existing code, 95% of changes don't break existing behavior)

Debugging efficiency: > 50% faster than baseline
(Minimum reproducible examples reduce debug time)

Code clarity: < 5% need external comments
(Second reader test produces self-documenting code)

Regression by change: < 10%
(Understanding recent changes prevents introducing new bugs)
```

---

## PHASE 6: EXPLANATION TEST & ERROR CLASS VALIDATION

**Goal:** After every task, verify that code solves the actual problem stated (prevents Class 4 errors).

**Duration:** 3-5 days (establish explanation discipline)

### The Four-Level Explanation Test

After EVERY task, explain at four levels:

```
Level 0 (1 sentence):
  "This code ensures webhook signatures are verified before processing."
  
  NOT: "This code uses HMAC-SHA256."
  NOT: "This catches security vulnerabilities."
  
  Goal: If you can't state in ONE SENTENCE what problem it solves → you built something without knowing why.

Level 1 (Plain language):
  Explain how it works without jargon. A smart person who doesn't code understands it.
  "We receive a webhook. We compute what the signature SHOULD be given our secret. We compare to what was sent. If they don't match, we reject it."
  
  Goal: Clarity about flow and purpose.

Level 2 (Technical):
  How it works at code level. Exact mechanisms.
  "We extract the timestamp and signature from the request headers. We reconstruct the request body as a string. We apply HMAC-SHA256 with our secret. We compare using constant-time string comparison to prevent timing attacks."
  
  Goal: A developer understands the implementation.

Level 3 (Architectural):
  Why this design. What was rejected. What tradeoffs exist.
  "We chose HMAC over public key because we control both sides. We use constant-time comparison to prevent timing attacks (not because they're easy, but because they're real). We could use JWT but HMAC is simpler here. We could skip verification but that's the entire security model. Tradeoff: signature on every request (1ms) vs security certainty (required)."
  
  Goal: A senior engineer understands reasoning and constraints.
```

### All Four Error Classes Evaluated

```
Class 1 — Execution Error (Did it run without crashing?)
  • Code compiles
  • Code executes without throwing
  • No null pointer, undefined, or runtime errors
  
  Test: Run the code. Does it crash? If yes, fix. If no, continue.

Class 2 — Logic Error (Does it produce the right answer?)
  • Code runs and produces expected output
  • Tested with known inputs and expected outputs
  • Edge cases covered (empty input, single item, boundary values)
  
  Test: Known input → expected output. Does your output match? If no, fix logic.

Class 3 — Design Error (Does it look unmaintainable when requirements change?)
  • Code is readable
  • Changes don't cascade
  • New requirements can be added without rewriting
  
  Test: Imagine requirement changes (new input format, new output requirement). Can you add it in < 1 hour? If no, redesign.

Class 4 — Requirement Error (Does it solve the ACTUAL problem stated?)
  • Re-read the original problem statement
  • Does your code solve THAT problem?
  • Not a related problem. Not a problem you assumed. The stated problem.
  
  Test: Can the person who asked for this see their problem solved? If they say "nice, but not what I needed" → back to requirements.
```

### Adversarial Self-Challenge

After all four levels explained, generate three HARDEST questions someone could ask:

```
Example: For webhook signature verification

Question 1: "What if someone has the secret but tries to forge a signature?"
  Answer: "Then the verification passes. Which is correct because they're supposed to have the secret. So...that's not a vulnerability."

Question 2: "What if the clock on our server is wrong?"
  Answer: "The signature doesn't include a timestamp check, so clock doesn't matter. If it did, and clock was wrong, signatures would fail. We'd need to handle that."

Question 3: "What if we need to support multiple secret versions?"
  Answer: "Current code only supports one secret. We'd need to iterate through all valid secrets. Current design doesn't handle that. Limitation of current approach."
```

If the agent cannot generate hard questions about its own explanation → the explanation is shallow.

### Behavior Checklist ✓

- [ ] All four explanation levels written (1, 1, 2-3, 3-4 sentences)
- [ ] Level 0 is genuinely one sentence (not one long run-on)
- [ ] Level 1 has no jargon
- [ ] Level 3 lists rejected options with explicit tradeoffs
- [ ] Three adversarial questions generated
- [ ] Can answer each challenge question
- [ ] All four error classes evaluated (not just 1 and 2)
- [ ] Class 4 check: Does this solve the stated problem?

### Verification

```
Explanation completeness: 100%
(Every task has all four levels)

Adversarial challenge quality: >= 3 genuine hard questions
(Questions are challenging, not softball)

Error class coverage: All 4 evaluated, not just some
(Every task explicitly checks if it solved the right problem)

Class 4 error rate: < 5%
(Rare perfect code for wrong problem after explanation discipline)
```

---

## PHASE 7: META OBSERVER — BIAS DETECTION

**Goal:** Detect your own thinking mistakes, patterns, and blind spots. Runs offline only.

**Duration:** 7-10 days (establish first bias report)

### What Agent Must Do

After every 10-15 tasks, analyze offline:

```
Meta Analysis {
  period:             // Last N tasks
  
  ERRORS {
    total_failures: // Count
    by_type: {},    // Distribution of error types
    by_class: {},   // Distribution of error classes
    by_concept: {},  // Which concepts failed most
    recurrence: {}   // Same concept failing multiple times?
                     // SIGNAL: that's a blind spot
  }
  
  CONFIDENCE {
    high_confidence_failures: // Tasks where confidence was >=0.8 and task failed
    low_confidence_successes: // Tasks where confidence was <0.5 and task succeeded
    
    // Large gap = confidence not tracking reality
  }
  
  SILENT_SUCCESSES {
    // Tasks that produced correct output but through lucky/broken reasoning
    // More dangerous than visible failures because you'll reinforce the broken logic
    task:         // Which task
    wrong_reason: // What wrong reasoning worked here
    when_breaks:  // What conditions make it fail
  }
  
  PATTERN_DETECTION {
    repeated_mistakes: // Error types recurring in same domain
    concept_blindness: // Concepts where recurrence > 10%
    false_confidence:  // Concepts where high confidence ≠ high accuracy
    language_bias:     // Any errors that only happen in one language?
  }
  
  ADJUSTMENT {
    // For each detected bias, explicit adjustment
    bias:               // Pattern detected
    evidence:           // How many cases, what's the evidence
    impact:             // Who does this affect
    adjustment:         // Specific behavioral change
    monitoring:         // How to track improvement
  }
}
```

### Silent Success Audit

This runs SEPARATELY. More dangerous than visible failures.

```
Task: Feature Dev — Add user filtering
Output: Correct (list filtered as expected)

But agent's reasoning: "Loop through array, compare property, push matches"
Could also work for: "Everyone has same filter property, so always matches"
When it breaks: "When property is missing from some records"

Silent success = right answer, wrong logic, will fail at scale.
These are MOST DANGEROUS because agent feels confident about the broken logic.
```

Minimum 3 silent successes must be identified before Phase 7 is complete.

### Cross-Phase Backward Scan

When a significant bias is found, trigger backward scan:

```
Bias: "High confidence in async code before structure completely understood"
Evidence: 19/25 async failures had confidence >= 0.8

Backward scan: Review all async-related decisions from Phase 1-6
- Some unchanged (still valid)
- Some marked suspect (need re-evaluation)
- Some fully revised (confidence reset)

This refines understanding without re-learning from scratch.
```

### Behavior Checklist ✓

- [ ] Meta analysis run after every 10-15 tasks
- [ ] Silent success audit identifies >= 3 examples
- [ ] Bias detection has quantified evidence (not suspicion)
- [ ] Adjustment is behavioral change (not blame)
- [ ] Monitoring plan tracks improvement
- [ ] No backward scan started until first bias report complete
- [ ] Detected biases don't paralyze (recognize and adjust)

### Verification

```
First bias report: Generated
Evidence quality: Quantifiable (not vague)
Silent successes found: >= 3
Backward scan: Completed (at least partial)
Adjustment tracking: In place with metrics
```

---

## PHASE 8: CONCEPT ANCHORS — PATTERN CONSOLIDATION

**Goal:** From 30-50 real failures, extract universal problem patterns ("concept anchors"). Not predefined. Everything from evidence.

**Duration:** 14-21 days (establish first 10-15 anchors)

### What Makes a Concept Anchor

```
Anchor {
  // What problem class does this describe
  concept:              // async_ordering, null_safety, cache_invalidation
  
  // The universal principle (language-independent)
  core_truth:           // "Callbacks fire in unknown order unless explicitly sequenced"
  
  // Why it was invented / what problem it solves
  why_exists:           // "Early JavaScript lacked promises. Developers lost track of execution order."
  
  // How it appears across languages
  variations {
    javascript:         // "Callback ordering issues in Promise chains"
    python:             // "Event loop ordering in async/await"
    java:               // "Thread ordering in ExecutorService callbacks"
  }
  
  // ACTUAL failures from this code base (not theory)
  traps: [
    {
      scenario:         // Exact condition that fails
      symptom:          // What breaks
      root_cause:       // The misunderstanding
      evidence_count:   // How many times seen
    }
  ]
  
  // What wrong beliefs make this happen
  false_beliefs: [
    {
      believed:         // X
      reality:          // Y
      why_felt_right:   // The reason the wrong belief seemed correct
    }
  ]
  
  // What this relates to
  connected_to: [
    "state_management",
    "concurrency",
    "performance_optimization"
  ]
  
  // Error statistics for this anchor
  error_class_bias:     // Which class (1/2/3/4) most appears
  error_type_bias:      // Which of 15 types most appears
  project_type_bias:    // Which of 15 contexts most appears
  
  // When was it understood well enough to use
  decay_rate:           // fast (external APIs change) / slow (language) / never (logic)
  
  // Evidence strength
  evidence_count:       // Total independent failures that taught this
  status:               // provisional (< 3) / stable (>= 3)
  
  // When failures cascade from this concept
  failure_cascade: {
    when_this_fails:    // Concept breaks
    typically_takes_down: // [other_concepts or components]
    why:                // Root cause of cascade
  }
  
  // Knowledge transfer across languages
  transfer_test: {
    source_language:    // Learned in
    target_language:    // Tested in
    outcome:            // transferred / needs_rebuild
  }
}
```

### Minimum Evidence Threshold

| Evidence Count | Status | Usage |
|---|---|---|
| 0-1 | Observation | Not stored |
| 2 | Coincidence | Not stored |
| 3+ | Anchor | Stored as stable |
| Under 3 | Provisional | Stored but flagged for re-test |

One failure = maybe luck. Two = might be pattern. Three independent failures from different contexts = real concept.

### Failure Cascade Mapping

```
ASYNC_ORDERING breaks →
  typically takes down: STATE_MANAGEMENT, CONCURRENCY, RACE_CONDITIONS
  why: If async callback fires in wrong order, shared state corrupts,
       which breaks concurrent access, which manifests as race conditions

CACHE_INVALIDATION breaks →
  typically takes down: PERFORMANCE, CONSISTENCY
  why: If cache not invalidated, old data served, which causes consistency errors,
       which looks like performance is fine but data is wrong
```

### Connection Map Example

```
ASYNC_ORDERING ──connects to──> STATE_MANAGEMENT
STATE_MANAGEMENT ──connects to──> CONCURRENCY
       ↓
  RACE_CONDITIONS ──connects to──> PERFORMANCE
       ↓
  Contention ──connects to──> SCALABILITY
```

When agent struggles with one anchor, it automatically checks connected anchors.

### Transfer Test (Immediate)

Every anchor tested against a problem in a DIFFERENT language the moment it's created.

```
Created in JS:
  Async callback ordering issue

Test in Python:
  Same concept: Event loop ordering issue

If it doesn't transfer → the anchor is syntax-level, not concept-level
Rebuild it.
```

### Behavior Checklist ✓

- [ ] 10-15 anchors created (from Phase 0-6 failures)
- [ ] Each anchor has >= 3 evidence (stable status)
- [ ] Provisional anchors marked (< 3 evidence)
- [ ] Failure cascade documented (not just single-point)
- [ ] Connection map completed (all relationships)
- [ ] Transfer test passed (works in other language)
- [ ] Every anchor has evidence from this codebase (not theory)
- [ ] No anchors created without failures to back them up

### Verification

```
Anchor quality: All have >= 3 evidence
Cascade mapping: Incomplete cascades 0%
Transfer success: >= 90% of anchors transfer to new language
Stability threshold: All >= 3 evidence are stable, all < 3 are provisional
Connection accuracy: Can name at least 2 connections for 80% of anchors
```

---

## PHASE 9: SECOND LANGUAGE TRANSFER

**Goal:** Every concept anchor transfers to Python. Proves they're language-independent.

**Duration:** 7-10 days (Python as first second language)

### Transfer Process

For every problem solved before:

```
1. Check concept anchors first
   "This is state_management problem, I've solved similar in JS"

2. State the mapping
   "Same concept: obj mutation in JS = dict mutation in Python"

3. Solve using existing model, adapted to syntax
   "In JS: avoid shared object. In Python: avoid shared dict."

4. If cannot map → anchor is weak
   "JS model doesn't apply here. Why? Rebuild anchor."
```

### Both Directions Required

Forward: "Solve JS problem in Python using concept anchors"
Reverse: "Solve Python problem in JS using same anchors"

If reverse fails → anchor is syntax-level.

### Real Transfer Metric

Not: "Can you solve the same problem in Python?"
But: "Are concept-level errors recurring?"

```
In JS:
- Made mistake A in async/state management context
- Later made mistake A' (different code, same concept)
- That's concept-level recurrence (bad — should have learned)

In Python:
- Similar mistake in different language, same concept
- If this occurs < 10% as frequently as in JS → transfer working
```

### Behavior Checklist ✓

- [ ] Every concept anchor tested in Python
- [ ] Both directions tested (JS→Python AND Python→JS)
- [ ] Mapping explicit ("same concept, different syntax")
- [ ] Forward transfer >= 90% of anchors
- [ ] Reverse transfer >= 80% of anchors
- [ ] Concept-level error recurrence < 10% in Python
- [ ] No anchors require complete rework (all transferred)

### Verification

```
Successful transfers: >= 80% of anchors
Failed transfers: < 5%, rebuild completed
Concept-level error recurrence (Python): < 10%
Bidirectional transfer: > 75% of tested anchors
```

---

## PHASE 10: FRAMEWORK LEARNING (Per Framework)

**Goal:** For each framework used (React, Express, Django, etc.), build deep understanding from first principles.

**Duration:** 7-14 days per framework

### 6-Step Framework Learning Process (No Shortcuts)

#### STEP 1: WHY

**What specific pain existed BEFORE this framework?**

```
React:
  Before: DOM updates required manual queries and synchronization
          Two-way data binding was the only pattern
          Large app state scattered across DOM
  
  Pain: Hard to track which UI elements depended on which data
        Changes in one place broke multiple DOM elements

Express:
  Before: Node.js required manual request routing
          Each route was a huge if-else
          Middleware was ad-hoc
  
  Pain: Code didn't scale. Adding new route involved finding right if-else and adding to it.

Django:
  Before: Web dev required SQL knowledge and manual queries
          No protection against SQL injection
          Data validation was manual (copy-paste everywhere)
  
  Pain: Every model required 50 lines of validation logic everywhere
```

If agent cannot answer this → it knows the API, not the purpose.

#### STEP 2: MENTAL MODEL (One Line Only)

```
React:     "UI = f(state)"
          Your entire UI is a function of the state. Recompute it when state changes.

Express:   "request → middleware chain → response"
          Each request flows through middleware stack that transforms it.

Django:    "ORM abstracts SQL, Views handle request logic"
          Models describe data structure in Python, not SQL.
```

More than one line means the model is incomplete.

#### STEP 3: MAGIC (What Happens Invisibly)

```
React:
  Virtual DOM diffing
    (React doesn't directly touch DOM. Builds virtual representation, compares, patches)
  
  Component reconciliation
    (React decides which component instance stays/goes/updates)
  
  Dependency tracking
    (React hooks track which state changes trigger which renders)

Express:
  Path pattern matching
    (Express converts route strings to regex, matches incoming requests)
  
  Middleware ordering
    (Request flows through middleware in registration order)
  
  Error handling delegation
    (Unhandled errors bubble to next error handler)

Django:
  Query building
    (Django ORM converts Python code to SQL dynamically)
  
  Migration system
    (Tracks schema changes, applies them safely)
  
  Middleware hooks at request/response
    (Code runs at specific points in request lifecycle)
```

Understanding invisible behavior separates debugging from guessing.

#### STEP 4: TRAPS (Real Failures Only)

```
React Trap (Real failure):
  Problem: Dependency array [user] but user is mutated object
  Symptom: Effect fetches stale user data repeatedly
  Root: Agent didn't understand shallow equality check in dependency array

Express Trap (Real failure):
  Problem: Double response error
  Symptom: "headers already sent" error
  Root: Middleware calls res.send(), then next handler also calls res.send()
        Agent didn't understand early response = stop processing

Django Trap (Real failure):
  Problem: N+1 query problem
  Symptom: 1000 users = 1 query to get users + 1000 queries for each user's profile
  Root: Agent didn't understand QuerySet lazy evaluation + one-to-one relationships
```

MUST come from agent's own failures in sandbox, not documentation.

#### STEP 5: WHEN NOT TO USE

```
React:
  When: Static site with no interactivity → use plain HTML
  When: SEO-critical, heavy server-side rendering needed → use Next.js
  When: Tiny component, don't need state management → plain JS

Express:
  When: Simple script, not a web server → don't use Express
  When: Need heavy framework features (ORM, validation, middleware) → use Django/Spring

Django:
  When: Just need API, not full web framework → use Django REST Framework
  When: Need extreme performance on every request → custom solution
  When: Rapidly evolving requirements → sometimes simpler custom code first
```

An agent that knows when NOT to use a framework understands it more deeply than one that only knows how.

#### STEP 6: DEGRADATION TEST

Show agent: large project built correctly with framework that has grown so big the framework now creates problems.

```
Example: React app grown to 50,000 lines
  - Component tree 200 levels deep
  - React reconciliation expensive
  - Dependency arrays fragile (easy to get wrong)
  - Bundle size unmanageable
  - Framework meant for small-medium apps

Diagnosis: "This app grew beyond React's sweet spot. Need different state management (Redux/Zustand) or split into multiple apps."

Teaching: When does the framework become the problem?
```

This teaches the rarest and most valuable framework knowledge that exists.

#### STEP 7: SANDBOX

Build minimal example. Break it deliberately three ways.

```
React:
  1. Build counter with useState
  2. Break 1: Call hook inside if (breaks rules)
  3. Break 2: Use wrong dependency array
  4. Break 3: Mutate state directly
  
  For each break:
  - State prediction (what will go wrong)
  - Pre-mortem (before running, explain failure)
  - Run and verify
  - Analyze why it broke
```

### Behavior Checklist ✓

- [ ] Step 1 answered (why it exists, what pain)
- [ ] Step 2 written (one-line mental model)
- [ ] Step 3 documented (invisible behavior)
- [ ] Step 4 completed (real traps from sandbox)
- [ ] Step 5 written (when not to use)
- [ ] Step 6 diagnosed (degradation point found)
- [ ] Step 7 sandbox created and deliberately broken 3x
- [ ] Framework mapped to project types and error types

### Verification

```
Framework understanding: Agent can explain all 6 steps coherently
Trap identification: >= 3 real traps from sandbox
Degradation diagnosis: Agent can name the point where framework becomes liability
When-not-to-use: Agent names at least 2 clear exclusion criteria
```

---

## PHASE 11: FULL PROJECT MASTERY — COMPLETE LOOP

**Goal:** Apply everything 1-10 in a complete, integrated workflow for every task.

**Duration:** 21+ days (this is ongoing refinement)

### Complete Workflow (17 Steps)

Every task follows this sequence:

```
1.  PHASE CHECK
    - Which of the 15 project types is this?
    - Which of the 15 error types are most likely?
    - Which concept anchors apply?
    - Query past decisions in this domain

2.  PRE-MORTEM
    - If this fails, what will cause it?
    - What guarantees must hold?
    - Which error types most likely?
    - Which concepts most risky?

3.  BORING SOLUTION
    - Is there a simpler, proven way first?
    - Document boring option
    - If rejected: state reason explicitly

4.  WORKING MEMORY SET
    - Confirmed: what I've verified
    - Uncertain: what's still unknown
    - Assuming: what I'm taking as true

5.  PROBLEM DEFINITION
    - Current state (undesired)
    - Desired state
    - Constraint (why non-trivial)
    - Project type verification

6.  MODEL BEFORE CODE
    - Mechanism (paragraph)
    - Invariant (must always be true)
    - Failure modes
    - Cost estimate (4 components)
    - Dependencies and guarantees
    - Concept anchor mapping
    - Timestamp and lock

7.  CODE WITH GUARANTEE REGISTRY
    - Mark every guarantee
    - Register one owner per guarantee
    - On conflict: stop and resolve

8.  EXECUTE WITH ENVIRONMENT CHECK
    - Runtime version correct?
    - Resource constraints met?
    - Input scale matches test scale?
    - External dependencies available?

9.  WORKING MEMORY UPDATE
    - After every non-trivial step
    - What did I verify?
    - What new uncertainty emerged?
    - Do my assumptions still hold?

10. FAILURE HANDLING
    - If failure: create minimum reproducible example
    - Name specific false assumption (not symptom)
    - Classify into error class and type
    - Propagate correction to all dependents
    - Execute recovery protocol

11. SUCCESS EXAMINATION
    - Did this succeed for the reason I expected?
    - Could this have worked for different reason?
    - Under what conditions does this fail?
    - Mark if silent success (right answer, lucky reasoning)

12. FOUR ERROR CLASS VALIDATION
    Class 1: Did code run without crashing?
    Class 2: Did it produce right output?
    Class 3: Does it remain maintainable if requirements change?
    Class 4: Does it solve the stated problem?
    (If any fail: back to Phase 3)

13. FOUR-LEVEL EXPLANATION
    - Level 0: one sentence problem statement
    - Level 1: plain language explanation
    - Level 2: technical mechanism
    - Level 3: architectural tradeoffs
    - Add three hardest questions and answers

14. DECISION STORAGE
    - Problem it solves
    - Decision chosen
    - Options rejected and why
    - Boring option status
    - Assumptions and confidence
    - Cost estimates (4 components)
    - Impact scope
    - Decay rate and timestamp

15. BACKWARD COMPATIBILITY CHECK (Brownfield only)
    - Do I understand what code would break?
    - Have I verified it still works?
    - Second reader test passed?
    - All guarantees still fulfilled?

16. CONCEPT ANCHOR UPDATE
    - If new failure: is it new anchor or existing?
    - Evidence count incremented
    - Failure cascade updated
    - Connection map revised

17. DETECTION GAP ANALYSIS
    - When did this problem first exist?
    - When did agent first detect it?
    - What signal existed earlier?
    - How to make detection faster next time?
```

### Phase-Specific Approaches

#### BROWNFIELD (Existing System)

```
1. Read code using five reading questions BEFORE touching anything
2. Map every file to existing concept anchors
3. Pull and check relevant guarantees
4. Never modify without understanding what breaks
5. "What changed?" discipline applied to every investigation
6. All four error classes validated before marking complete
```

#### BUG FIXING

```
1. Classify bug into one of 15 error types immediately
2. Create minimum reproducible example (before any fix)
3. Ask "what changed recently?" BEFORE asking "what is wrong?"
4. Distinguish: environment failure vs logic failure
5. Trace back to when this first existed
6. Fix root cause, not symptom
7. Verify fix doesn't break other behavior
```

#### PERFORMANCE OPTIMIZATION

```
1. Check cost estimates from past decisions
2. Identify largest gap: estimated time vs actual time
3. Use execution baselines from Phase -1
4. Trace bottlenecks using performance data
5. Concurrency and database anchors checked first
6. Before and after comparison mandatory
7. Verify fix doesn't introduce other tradeoffs
```

#### REFACTORING

```
1. Hard rule: must satisfy one of three criteria:
   - Reduces complexity
   - Improves readability
   - Removes duplication
   If none true → refactor rejected

2. Before and after comparison mandatory
3. Second reader test applied
4. Verify behavior unchanged
5. All tests pass before marking complete
```

#### INTEGRATION

```
1. Every external dependency classified by decay rate on first touch
2. Fast decay = external API (they change without warning)
3. Explicit failure handling for:
   - Timeout
   - Wrong response format
   - Authentication failure
   - Rate limiting
   - Service unavailable
4. Retry logic with exponential backoff
5. Guarantee contract before using external code
```

#### SECURITY

```
1. Specific concept anchor for every security error type
2. For every function touching user input or authentication:
   - Security anchors checked BEFORE code
   - Not after
3. Input validation explicit (not implicit)
4. Encryption for sensitive data (not just for compliance)
5. Test attack scenarios before production
```

#### PoC (Proof of Concept)

```
1. Minimum footprint rule (most aggressive)
2. Goal: concept validation, not production code
3. Model still written before code
4. Explanation test: Level 0 and Level 1 only
5. If PoC succeeds: convert to production code, not use directly
6. Document what would need to change for production
```

### Behavior Checklist ✓

- [ ] Complete 17-step workflow followed
- [ ] Pre-failure prediction done (60%+ accuracy by Phase 12)
- [ ] All four error classes evaluated explicitly
- [ ] Decision stored with cost estimates and decay rate
- [ ] Minimum reproducible examples created for every bug
- [ ] Code passes second reader test
- [ ] Four-level explanation completed
- [ ] Detection gap tracked (for meta-analysis)

### Verification

```
Proper phase application: 100%
(Every task follows appropriate phase workflow)

Pre-mortem accuracy: > 60%
(Agent predicts failures 60%+ of the time)

Four error class validation: 100%
(Every task explicitly checks all four classes)

Silent successes caught: < 5%
(Rare to find right answer for wrong reason)

Measurable detection gap shrinkage: < 10%
(Time between problem existence and detection decreases over tasks)
```

---

## PHASE 12: CONTINUOUS LEARNING LOOP

**Goal:** Every new encounter becomes pattern, every pattern becomes anchor, every anchor transfers to other languages and problems.

**Duration:** Ongoing (permanent discipline)

### The Loop

```
1.  Encounter new concept, error, or pattern
2.  Check: Have I seen this problem class before?
3.  
    If YES:
      - Map to existing anchor
      - Note variation
      - Check evidence count
      - Reuse belief
    
    If NO:
      - Create provisional anchor
      - Minimum evidence threshold (3) applies
      - Mark as hypothesis, not law
      - Test in sandbox
4.  
5.  Tag failure with:
    - Concept domain
    - Error class
    - Error type
    - Language
    - Project type
6.  
7.  Update anchor evidence count
8.  When evidence count reaches 3: mark stable
9.  Trigger backward scan of related artifacts
10. Check new belief for contradictions
    (in same domain)
11. Update failure cascade map
12. Test transfer to other language

Result: Web of anchors, not list of rules
```

### Internet and Documentation Learning Rule

Agent cannot copy-paste. Must:

```
1. Read
2. Convert to internal belief
3. Test in sandbox
4. Confirm or fail
5. Store or revise

Copy-paste only works in exact situation copied from.
Real learning updates behavior under novel conditions.
```

### Concept-Level Error Recurrence Tracking

```
In JavaScript:
  Error A: Misunderstood async ordering

In Python:
  Error B: Misunderstood event loop ordering

These are SAME concept-level error, different syntax.

Metric: "Concept-level error recurrence"
  = same concept problem, different language/code/context
  = should be < 10% after 30 tasks per language
  
If >10%: the concept anchor isn't working. Rebuild it.
```

### Behavior Checklist ✓

- [ ] Every new error checked against anchor database first
- [ ] Provisional anchors created for new patterns
- [ ] Evidence count tracked per anchor
- [ ] Backward scans triggered on stable anchors
- [ ] Transfer tests run for new anchors
- [ ] Contradiction checks enforced
- [ ] Failure cascade maps updated
- [ ] Concept-level recurrence < 10%

### Verification

```
Anchor library: Growing over time
New patterns: Mapped to existing anchors > 80% of time
Provisional to stable: Progression tracked
Contradiction detection: 0 silent contradictions
Transfer success: >= 80% of new anchors transfer
```

---

## REAL METRICS THAT PROVE IT'S WORKING

### Metric 1: Concept-Level Error Recurrence < 10%

Not: "Did you make the same mistake again?" (trivial)
But: "Did you make the same conceptual mistake in different code/language?" (real learning)

```
Task 1 (JS): Didn't understand closure in setTimeout
Task 15 (Python): Didn't understand variable capture in nested loop

Same conceptual error, different language = concept-level recurrence (BAD)
If recurring > 10% after anchoring: anchor is weak. Rebuild.
```

### Metric 2: Pre-Mortem Accuracy > 60%

Agent predicts what will fail BEFORE running code.

```
Agent predicts: "This will fail because race condition in cache update"
Code fails: Yes, race condition in cache update
Score: Correct prediction

This requires understanding of concepts, not luck.
60% threshold reached → concepts are working.
```

### Metric 3: Four Error Class Validation 100%

Every task explicitly validates:
- Class 1: Did it run? (pass/fail)
- Class 2: Is it correct? (pass/fail)
- Class 3: Is it maintainable? (pass/fail)
- Class 4: Does it solve the problem? (pass/fail)

No skipping any. Not just 1 and 2.

### Metric 4: Detection Gap Shrinkage

How long between when problem first existed and when agent detected it?

```
Task 1: Bug existed 5 days, detected after 4 days (gap: 4 days)
Task 10: Bug existed 5 days, detected after 1 day (gap: 1 day)
Task 20: Bug existed 5 days, detected same day it was introduced (gap: < 1 day)

Gap shrinks over time = real improvement
```

---

## PRACTICAL IMPLEMENTATION GUIDE

### Folder Structure

```
/agent
  /core
    /executor           ← Universal execute({ language, code })
    /belief_engine      ← Belief replacement & contradiction detection
    /model_engine       ← Pre-execution models with decay
    /decision_engine    ← Decisions with cost estimates
    /working_memory     ← Confirmed/uncertain/assuming per task
    /evaluator          ← 4 levels + adversarial + 4 classes
    /meta_observer      ← Offline bias detection
    /recovery           ← Recovery protocols
    /code_reader        ← 5 reading questions, second reader test

  /concepts
    /anchors            ← Problem patterns with evidence + cascade
    /connections        ← Relationship map
    /provisional        ← Anchors < 3 evidence

  /languages
    /js                 ← Language-specific patterns
    /python             ← Language-specific patterns
    /java               ← Language-specific patterns

  /frameworks
    /react              ← Framework deep-dive
    /express            ← Framework deep-dive
    /django             ← Framework deep-dive

  /logs
    /executions         ← With environment, baseline, delta
    /failures           ← Error class, type, concept tag
    /decisions          ← Cost, decay, timestamp
    /silent_successes   ← When right answer, wrong logic
    /detection_gaps     ← Gap between existence and detection
    /minimum_repros     ← Smallest reproductions
    /meta_reports       ← Bias detection findings
    /explanation_tests  ← All 4 levels per task
    /concept_anchors    ← Audit trail of evidence
```

### Quick Reference: When to Apply Each Phase

| Situation | Apply Phase(s) | Immediately Do |
|-----------|---|---|
| Learning new language | Phase 0 + 1 + 10 | Observe 10 failures, build models |
| Joining Brownfield project | Phase 5 + 6 | Read code with 5 questions |
| Bug fixing | Phase 2 + 3 | Create minimum repro, ask "what changed?" |
| Performance work | Phase 4 + 12 | Check baselines, profile bottlenecks |
| Security task | Phase 10 (Framework) + 12 | Map threat model, test attacks |
| Refactoring | Phase 5 + 6 | Second reader test, verify behavior |
| New framework | Phase 11 (Framework) | 6-step framework learning |
| Making decision | Phase 4 | Store decision with cost + boring option |
| Task completion | Phase 6 + 7 | Explanation test + meta-analysis |

---

## SUMMARY

**This agent learns the way real engineers actually work:**

✅ Reads existing code like a detective
✅ Classifies errors precisely before investigating  
✅ Creates minimum reproducible examples
✅ Asks "what changed?" not just "what's wrong?"
✅ Checks for boring solutions before clever ones
✅ Knows when NOT to use a framework
✅ Models failure cascades, not just failures
✅ Examines successes for coincidental correctness
✅ Tracks detection gaps
✅ Detects own blind spots
✅ Builds concept anchors from real failures
✅ Prevents the same mistake in any language

**Not a chatbot that writes fast code.**
**A system that builds reliable, maintainable systems while learning continuously.**

---

## NEXT: PRACTICAL IMPLEMENTATION

To actually build this:

1. **Start with Phase -1**: Build the universal execution layer
2. **Run Phase 0**: Feed 30 real failures, extract beliefs
3. **Build Phase 1**: Model engine (equation before execution)
4. **Track Phase 2-7 Continuously**: Every task passes through this
5. **Reach Phase 8**: Bias detection after 50 real tasks
6. **Create Anchors in Phase 9**: Consolidate patterns into reusable knowledge
7. **Test Transfer in Phase 10**: Verify anchors work in new language

**The metric that matters:** Detection gap shrinking, concept-level error recurrence below 10%, pre-mortem accuracy above 60%.

Everything else is infrastructure to make those three metrics work.
