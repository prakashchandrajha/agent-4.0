/**
 * PHASE 1: ROBUSTNESS CHECKLIST
 * 
 * Based on real patterns found in reference projects:
 * - LocalMind: dataclasses, type hints, factory pattern
 * - Scrapling: testing, validation, real examples
 * - Superpowers: verification, tracking, task breakdown
 * 
 * A model is NOT complete until it passes ALL these checks.
 */

const checks = {
  // ============================================================================
  // REQUIRED CHECKS (model will not be approved without these)
  // ============================================================================
  
  required: {
    // 1. Problem Definition (LocalMind's "problem" field)
    problem_defined: {
      name: "Problem clearly defined",
      description: "Model must contain unambiguous problem statement",
      example_pass: "Accept JSON strings and parse into JavaScript objects, validating schema",
      example_fail: "Handle JSON parsing",
      requires: ["Read problem field", "Verify >= 20 characters", "Verify specific not vague"],
    },

    // 2. Mechanism Documented (LocalMind's "mechanism" field)
    mechanism_explained: {
      name: "Mechanism written (paragraph format)",
      description: "How does it work? What's the algorithm/flow?",
      example_pass: "Read input string, apply JSON.parse(), catch SyntaxError, validate against schema using Ajv library, return typed result",
      example_fail: "Parse the JSON",
      requires: ["Explains steps in order", "Names specific libraries if used", "Testable in sandbox"],
    },

    // 3. Invariant Specified (LocalMind's "invariant" field)
    invariant_mandatory: {
      name: "Invariant (what MUST always be true)",
      description: "Name one thing that is always true if code works correctly",
      example_pass: "Parsed output always matches input JSON structure. Schema validation always catches invalid input.",
      example_fail: "Code works",
      requires: ["Testable condition", "Specific not vague", "Is actually important"],
    },

    // 4. No Vague Assumptions (from opus.md Rule 2)
    assumptions_specific: {
      name: "All assumptions precisely named",
      description: "Never 'something went wrong'. Always 'I believed X'",
      violations: [
        "❌ 'JSON might have issues'",
        "❌ 'Edge cases could happen'",
        "✅ 'I believed JSON.parse throws SyntaxError, never silently returns null'",
        "✅ 'I believed schema validation library catches all schema violations'",
      ],
    },

    // 5. Boring Solution Evaluated (from opus.md, Scrapling uses it)
    boring_solution_checked: {
      name: "Boring solution considered",
      description: "Is there a simpler, proven way? Document it.",
      example_pass: "Boring: use native JSON.parse() with try/catch. Rejected: adds middleware layer - overcomplicated.",
      example_fail: "Didn't consider",
      requires: ["Name the simpler approach", "Explain why rejected (if rejected)", "Or choose it"],
    },

    // 6. Failure Modes Documented (LocalMind pattern)
    failure_modes_listed: {
      name: "Failure modes identified (cascading format)",
      description: "Where can this break? What causes what?",
      example_pass: [
        "If input is null → JSON.parse fails → SyntaxError not caught → crash",
        "If schema loading fails → Ajv init fails → reject all inputs as invalid",
        "If user passes 50MB input → memory spike → timeout",
      ],
      example_fail: ["Could fail in parsing", "Bad data might break it"],
      requires: ["At least 3 failure modes", "Cause → Effect → Result chain"],
    },
  },

  // ============================================================================
  // HIGH FRICTION CHECKS (required for code > 50 lines)
  // ============================================================================
  
  high_friction: {
    // 1. Cost Estimates (LocalMind's CostEstimate with 4 numbers)
    cost_breakdown: {
      name: "Cost estimates in hours (write/test/debug/change)",
      description: "LocalMind pattern: break down all costs",
      example: {
        write_hours: 2.0,
        test_hours: 1.5,
        debug_hours: 1.0,
        change_hours: 0.5,
      },
      validation: [
        "All 4 numbers present",
        "None are zero (means not thought through)",
        "Sum seems reasonable for code length",
      ],
    },

    // 2. Constraints (why is this non-trivial?)
    constraint_explained: {
      name: "Non-trivial constraint documented",
      description: "Why can't we just do it naively?",
      example_pass: "Must handle 50MB files without crashing. Must validate against 1000-field schema in <100ms.",
      example_fail: "It's complex",
      requires: ["Real limitation", "Specific measurement or requirement"],
    },

    // 3. Dependency Check (from opus.md phase 4)
    dependencies_identified: {
      name: "External dependencies validated",
      description: "What must exist for this to work?",
      example: [
        "Ajv library installed and >= v8.0",
        "Input always string type, never Buffer",
        "Node >= 16 (for async/await)",
      ],
      requires: ["All dependencies named", "Versions specified if sensitive"],
    },

    // 4. Error Types Mapped (from opus.md's 15 types)
    error_types_considered: {
      name: "Which of the 15 error types are likely?",
      description: "From opus.md: Syntax, Logical, Runtime, Build, Integration, Environment, Performance, Concurrency, Security, Database, Network, Dependency, Deployment, Data, Production-only",
      example_pass: ["Type 2 (Logical): Schema validation incomplete"],
      example_fail: ["Didn't consider"],
      requires: ["At least 2 error types mapped"],
    },
  },

  // ============================================================================
  // CONFIDENCE & DECAY (LocalMind pattern)
  // ============================================================================
  
  confidence_tracking: {
    confidence_value: {
      name: "Confidence score (0.0 to 1.0)",
      description: "How confident are we this model is correct?",
      guidance: [
        "0.3-0.5: First time building something similar",
        "0.5-0.7: Built similar before, some unknowns",
        "0.7-0.9: Clear pattern, high confidence",
        "0.9+: Trivial, obvious solution",
      ],
      validation: "Must be between 0.0 and 1.0, not uniform across all models",
    },

    decay_rate: {
      name: "Confidence decay rate",
      description: "How fast does this knowledge become stale?",
      options: {
        FAST: "External API behavior, library versions, data format assumptions",
        SLOW: "Language behavior, framework conventions, architectural patterns",
        NEVER: "Logic definitions, math, language semantics",
      },
    },
  },

  // ============================================================================
  // TESTING READINESS (Scrapling pattern: test before coding)
  // ============================================================================
  
  testing_ready: {
    sandbox_testability: {
      name: "Testable in sandbox before real code",
      description: "Can mechanism be tested with simple examples?",
      example_test: `
        // Sandbox test for JSON parser
        test("Valid JSON parses", () => {
          input = '{"name": "test"}'
          expect(parse(input)).toEqual({name: "test"})
        })
        
        test("Invalid JSON throws", () => {
          input = '{invalid}'
          expect(() => parse(input)).toThrow()
        })
        
        test("Large input doesn't crash", () => {
          input = '{"x": "' + 'a'.repeat(1000000) + '"}'
          expect(() => parse(input)).toThrow() // or complete
        })
      `,
      requires: [
        "Can write test before code",
        "Test doesn't depend on implementation details",
        "Covers happy path, failure modes, edge cases",
      ],
    },

    critical_properties: {
      name: "Critical properties testable",
      description: "Can we verify the invariant is true?",
      example: "Invariant: 'Parsed output always matches input structure'. Test: parse -> JSON.stringify -> compare",
      requires: ["Invariant is testable", "Test exists before code"],
    },
  },

  // ============================================================================
  // WORK MEMORY (from opus.md phase 2)
  // ============================================================================
  
  working_memory: {
    confirmed_updated: {
      name: "Confirmed facts tracked",
      description: "What has agent verified to be true?",
      example: [
        "✓ Ajv library catches duplicate key errors",
        "✓ JSON.parse throws on invalid syntax",
        "✗ JSON.parse handles circular references",
      ],
    },

    uncertain_tracked: {
      name: "Open questions identified",
      description: "What is still unknown?",
      example: [
        "? What's max file size before memory issues?",
        "? Does Ajv support all JSON schema 2020-12 features?",
        "? How to handle streaming large files?",
      ],
      requires: ["List actual uncertainties before coding"],
    },

    assumptions_listed: {
      name: "Assumptions before coding",
      description: "Taking as true without verification",
      example: [
        "~ Input always valid JSON string format",
        "~ Schema always exists and is valid",
        "~ Synchronous processing is acceptable",
      ],
      requires: ["Turn into confirmed or uncertain after testing"],
    },
  },

  // ============================================================================
  // DECISION TRACKING (from opus.md phase 4)
  // ============================================================================
  
  decision_documented: {
    choice_made: {
      name: "If multiple approaches: choice documented",
      description: "Why this approach vs alternatives?",
      example: {
        chosen: "Ajv for schema validation",
        rejected: [
          "JSON Schema Validator: too slow",
          "Manual validation: unreliable, code smell",
          "joi: overkill for JSON schema",
        ],
      },
    },

    impact_identified: {
      name: "Impact of this choice",
      description: "What becomes harder/easier?",
      example: [
        "Easier: standard JSON schema format",
        "Harder: users must learn JSON schema syntax",
        "Locked in: if performance insufficient, hard to switch",
      ],
    },
  },

  // ============================================================================
  // FINAL VALIDATION (Guard Rails)
  // ============================================================================
  
  final_checks: {
    code_size_feasible: {
      name: "Code size is feasible",
      description: "If > 200 lines: REJECT and redesign",
      validation: "function_length <= 200",
    },

    no_silent_failures: {
      name: "No Class 2 errors silently accepted",
      description: "Does invariant catch all silent failures?",
      example_bad: "Parse succeeds but output wrong type - invariant doesn't detect",
      example_good: "Output type-checked against schema - catches all wrong outputs",
    },

    requirements_clear: {
      name: "Function purpose crystal clear",
      description: "5-year-old could explain what this does",
      example_pass: "Takes string, returns object if valid JSON, throws if not",
      example_fail: "Processes JSON",
    },

    guardrail_checks: {
      name: "All guardrails in place",
      description: "Before approving, verify:",
      checks: [
        "✓ Problem is specific, not vague",
        "✓ Mechanism is testable",
        "✓ Invariant is real (not placeholder)",
        "✓ Boring solution considered",
        "✓ Failure modes documented with cascades",
        "✓ Tests written before code",
        "✓ Type hints planned (for functions > 10 lines)",
        "✓ Error handling strategy defined",
      ],
    },
  },
};

// ============================================================================
// PHASE 1 VALIDATION FUNCTION
// ============================================================================

function validatePhase1(model) {
  const issues = [];
  
  // Check all required fields
  if (!model.problem || model.problem.length < 20) {
    issues.push("REQUIRED: problem must be >= 20 chars, specific");
  }
  
  if (!model.mechanism || model.mechanism.length < 50) {
    issues.push("REQUIRED: mechanism must be detailed paragraph");
  }
  
  if (!model.invariant || model.invariant.length < 20) {
    issues.push("REQUIRED: invariant must be specific");
  }
  
  // Check high-friction for larger code
  if (model.code_length >= 50) {
    if (!model.constraint) {
      issues.push("HIGH FRICTION: constraint required for code >= 50 lines");
    }
    if (!model.failure_modes || model.failure_modes.length < 3) {
      issues.push("HIGH FRICTION: failure_modes required (at least 3)");
    }
    if (model.cost.total_hours === 0) {
      issues.push("HIGH FRICTION: cost estimates required");
    }
  }
  
  // Check code size limit
  if (model.code_length > 200) {
    issues.push("REJECT: Code > 200 lines. Redesign needed.");
  }
  
  return {
    valid: issues.length === 0,
    issues,
    phase1_ready: issues.length === 0,
  };
}

module.exports = {
  checks,
  validatePhase1,
};
