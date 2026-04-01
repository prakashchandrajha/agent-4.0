"""
PHASE 1: ROBUST MODEL ENGINE
Based on real patterns found in:
- LocalMind (dataclasses, service factories, type hints)
- Scrapling (testing patterns, real implementations)
- Superpowers (verification, task tracking)

Key principles:
1. Models use dataclasses (like CPUInfo, GPUInfo in LocalMind)
2. Services use factory pattern with get_* functions
3. Type hints mandatory everywhere
4. Configuration-driven behavior
5. Testing in from the start
6. Error handling with sensible defaults
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime
import json
from pathlib import Path


# ============================================================================
# ERROR CLASSES (from opus.md, but as Enums for type safety)
# ============================================================================

class ErrorClass(Enum):
    """Error classification: what type of failure is this?"""
    EXECUTION = 1      # Code ran and crashed - visible signal
    LOGICAL = 2        # Code ran, wrong answer - no visible signal
    DESIGN = 3         # Works now, unmaintainable later - no signal
    REQUIREMENT = 4    # Solves wrong problem - looks like success


class ErrorType(Enum):
    """Error types: which of the 15 categories?"""
    SYNTAX = 1
    LOGICAL = 2
    RUNTIME = 3
    BUILD_COMPILE = 4
    INTEGRATION = 5
    ENVIRONMENT = 6
    PERFORMANCE = 7
    CONCURRENCY = 8
    SECURITY = 9
    DATABASE = 10
    NETWORK = 11
    DEPENDENCY = 12
    DEPLOYMENT = 13
    DATA = 14
    PRODUCTION_ONLY = 15


class ProjectType(Enum):
    """Which of the 15 project types does this belong to?"""
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"
    FEATURE_DEV = "feature_development"
    BUG_FIXING = "bug_fixing"
    PERF_OPTIMIZATION = "performance_optimization"
    REFACTORING = "refactoring"
    SYSTEM_DESIGN = "system_design"
    INTEGRATION = "integration"
    MIGRATION = "migration"
    POC = "poc"
    SECURITY = "security"
    SCALING = "scaling"
    DEVOPS_INFRA = "devops_infrastructure"
    DATA_ANALYTICS = "data_analytics"
    AUTOMATION = "automation"


class ConfidenceDecay(Enum):
    """How quickly does this model's confidence decay?"""
    FAST = "fast"      # External APIs, library versions, data assumptions
    SLOW = "slow"      # Language behavior, frameworks, patterns
    NEVER = "never"    # Definitions, math, logic


# ============================================================================
# COST ESTIMATION (borrowed from LocalMind's structured approach)
# ============================================================================

@dataclass
class CostEstimate:
    """Cost breakdown using LocalMind's 4-number pattern"""
    write_hours: float = 0.0
    test_hours: float = 0.0
    debug_hours: float = 0.0
    change_hours: float = 0.0
    
    @property
    def total_hours(self) -> float:
        """Total estimated hours"""
        return self.write_hours + self.test_hours + self.debug_hours + self.change_hours
    
    def __str__(self) -> str:
        return f"Write: {self.write_hours}h, Test: {self.test_hours}h, Debug: {self.debug_hours}h, Change: {self.change_hours}h"


# ============================================================================
# WORKING MEMORY (track what agent knows/doesn't know during task)
# ============================================================================

@dataclass
class WorkingMemory:
    """LocalMind-style tracking of confirmed/uncertain/assuming"""
    confirmed: list[str] = field(default_factory=list)
    uncertain: list[str] = field(default_factory=list)
    assuming: list[str] = field(default_factory=list)
    
    def add_confirmed(self, fact: str):
        """Mark something as verified (with deduplication)"""
        if fact not in self.confirmed:  # CRITICAL FIX: prevent duplicates
            self.confirmed.append(fact)
        if fact in self.uncertain:
            self.uncertain.remove(fact)
        if fact in self.assuming:
            self.assuming.remove(fact)
    
    def add_uncertain(self, question: str):
        """Mark something as unknown (with deduplication)"""
        if question not in self.uncertain:
            self.uncertain.append(question)
    
    def add_assumption(self, assumption: str):
        """Mark something being taken as true without verification (with deduplication)"""
        if assumption not in self.assuming:
            self.assuming.append(assumption)


# ============================================================================
# MODEL (the core of Phase 1 - what is this function doing?)
# ============================================================================

@dataclass
class FunctionModel:
    """
    Complete model for a function, based on LocalMind's dataclass pattern.
    
    This is what MUST be defined BEFORE writing any code.
    Every field with a value must be filled before implementation.
    """
    
    # Identification
    function_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    locked: bool = False  # Lock on first code execution
    
    # ======== REQUIRED FIELDS (must fill) ========
    
    # Problem: What state change is needed?
    problem: str = ""
    
    # Mechanism: How does it work? (1 paragraph, tested in sandbox)
    mechanism: str = ""
    
    # Invariant: What MUST always be true?
    # Example: "User can NEVER see unvalidated data"
    invariant: str = ""
    
    # ======== SEMI-REQUIRED (for code > 50 lines) ========
    
    # Constraint: Why is this non-trivial?
    constraint: str = ""
    
    # Failure modes: Where can this break? (cascading format)
    failure_modes: list[str] = field(default_factory=list)
    
    # Boring solution: Is there a simpler, proven way first?
    boring_solution: Optional[str] = None
    why_boring_rejected: Optional[str] = None
    
    # Cost estimates (Scrapling/LocalMind style)
    cost: CostEstimate = field(default_factory=CostEstimate)
    
    # ======== OPTIONAL BUT VALUABLE ========
    
    # Concept mapping (which anchor does this relate to?)
    concept_anchor: Optional[str] = None
    
    # Error classification (what's likely to go wrong?)
    error_classes: list[ErrorClass] = field(default_factory=list)
    error_types: list[ErrorType] = field(default_factory=list)
    project_type: Optional[ProjectType] = None
    
    # Dependencies: What other code must exist?
    dependency_check: list[str] = field(default_factory=list)
    
    # Guarantees (from LocalMind pattern: who owns what?)
    guarantee_owners: dict[str, str] = field(default_factory=dict)
    
    # Confidence tracking
    confidence: float = 0.5  # 0.0 to 1.0
    confidence_decay: ConfidenceDecay = ConfidenceDecay.SLOW
    
    # ======== RUNTIME TRACKING ========
    
    # Working memory (what does agent know?)
    working_memory: WorkingMemory = field(default_factory=WorkingMemory)
    
    # Status throughout lifecycle
    status: str = "draft"  # draft, approved, implementing, complete
    approval_timestamp: Optional[datetime] = None
    completion_timestamp: Optional[datetime] = None
    
    # Code length (for friction matching)
    code_length: Optional[int] = None
    
    # ======== VALIDATION ========
    
    def validate(self, code_length: int = 0) -> tuple[bool, list[str]]:
        """
        Validate model is complete enough for the code size.
        
        Based on friction scaling from opus.md:
        - < 10 lines: minimal friction (problem, mechanism ONLY)
        - 10-50 lines: moderate (+ invariant, constraint, failure_modes)
        - 50-200 lines: high (+ boring_solution, cost)
        - > 200 lines: REJECT (redesign needed)
        """
        errors = []
        
        # Code too large - AUTOMATIC REJECTION
        if code_length > 200:
            return False, ["Code exceeds 200 lines. Redesign needed."]
        
        # Always required (minimal friction)
        if not self.problem:
            errors.append("problem: Required (what problem does this solve?)")
        if not self.mechanism:
            errors.append("mechanism: Required (how does it work?)")
        
        # Required for medium functions (>= 10 lines)
        if code_length >= 10:
            if not self.invariant:
                errors.append("invariant: Required for code >= 10 lines (what MUST always be true?)")
            if not self.constraint:
                errors.append("constraint: Required for code >= 10 lines (why is this non-trivial?)")
            if not self.failure_modes:
                errors.append("failure_modes: Required for code >= 10 lines (where can this break?)")
        
        # Required for larger functions (>= 50 lines)
        if code_length >= 50:
            if not self.boring_solution:
                errors.append("boring_solution: Required for code >= 50 lines (is there a simpler way?)")
            if self.cost.total_hours == 0:
                errors.append("cost: Required for code >= 50 lines (estimate write/test/debug/change time)")
        
        # Silent continuation detection (EXTREMELY POWERFUL but minor)
        # Too many assumptions without confirmation = invisible failure risk
        if len(self.working_memory.assuming) > len(self.working_memory.confirmed):
            if len(self.working_memory.assuming) > 5:
                errors.append(f"⚠ SILENT CONTINUATION RISK: {len(self.working_memory.assuming)} assumptions not verified")
        
        # Too many uncertainties = unclear understanding
        if len(self.working_memory.uncertain) > code_length:
            errors.append(f"⚠ UNCLEAR MODEL: More uncertainties ({len(self.working_memory.uncertain)}) than code lines ({code_length})")
        
        return len(errors) == 0, errors
    
    def validate_enhanced(self, code_length: int = 0) -> tuple[bool, list[dict]]:
        """
        Enhanced validation with:
        - Detailed error explanations (WHY validation failed)
        - Error probability warnings (are chosen error types likely for this project_type?)
        - Dependency warnings (are declared dependencies actually met?)
        - Working memory health check (are assumptions being verified?)
        
        Returns list of dicts with: {level, message, fix}
        """
        errors = []
        warnings = []
        
        # Run basic validation first
        is_valid, basic_errors = self.validate(code_length)
        
        for error_msg in basic_errors:
            errors.append({
                'level': 'error',
                'message': error_msg,
                'fix': self._get_fix_for_error(error_msg, code_length)
            })
        
        # ERROR PROBABILITY CHECK (POWERFUL but minor)
        # If project_type is set, check if error_types make sense for that type
        if self.project_type:
            error_type_probability = self._get_error_type_probability(self.project_type)
            
            for error_type in self.error_types:
                if error_type_probability.get(error_type) == 'unlikely':
                    warnings.append({
                        'level': 'warning',
                        'message': f"Error type {error_type.name} is UNLIKELY in {self.project_type.value}",
                        'fix': f"Reconsider: typical errors in {self.project_type.value} are {self._get_typical_errors(self.project_type)}"
                    })
        
        # DEPENDENCY VALIDATION (POWERFUL but minor)
        # Check if declared dependencies make sense
        for dependency in self.dependency_check:
            if not self._is_reasonable_dependency(dependency):
                warnings.append({
                    'level': 'warning',
                    'message': f"Dependency '{dependency}' seems unclear or incomplete",
                    'fix': "Rephrase dependency in format: 'X must be true before Y'"
                })
        
        # WORKING MEMORY HEALTH (EXTREMELY POWERFUL but minor)
        # Are assumptions being converted to confirmed knowledge?
        unverified_ratio = len(self.working_memory.assuming) / max(len(self.working_memory.confirmed), 1)
        if unverified_ratio > 2.0:
            warnings.append({
                'level': 'critical_warning',
                'message': f"Too many unverified assumptions ({len(self.working_memory.assuming)} vs {len(self.working_memory.confirmed)} confirmed)",
                'fix': "Before proceeding, verify at least half your assumptions (add to confirmed list)"
            })
        
        return is_valid, errors + warnings
    
    @staticmethod
    def _get_error_type_probability(project_type: ProjectType) -> dict:
        """From opus.md: which error types are likely for this project?"""
        probabilities = {
            ProjectType.GREENFIELD: {ErrorType.SYNTAX: 'likely', ErrorType.BUILD_COMPILE: 'likely', ErrorType.DEPENDENCY: 'likely'},
            ProjectType.BROWNFIELD: {ErrorType.ENVIRONMENT: 'likely', ErrorType.LOGICAL: 'likely', ErrorType.CONCURRENCY: 'likely'},
            ProjectType.FEATURE_DEV: {ErrorType.LOGICAL: 'likely', ErrorType.DATABASE: 'likely', ErrorType.INTEGRATION: 'likely'},
            ProjectType.BUG_FIXING: {ErrorType.RUNTIME: 'likely', ErrorType.LOGICAL: 'likely', ErrorType.CONCURRENCY: 'likely'},
            ProjectType.PERF_OPTIMIZATION: {ErrorType.PERFORMANCE: 'likely', ErrorType.CONCURRENCY: 'likely', ErrorType.DATABASE: 'likely'},
            ProjectType.REFACTORING: {ErrorType.LOGICAL: 'likely', ErrorType.RUNTIME: 'unlikely'},
            ProjectType.SECURITY: {ErrorType.SECURITY: 'likely', ErrorType.LOGICAL: 'likely', ErrorType.INTEGRATION: 'likely'},
            ProjectType.SCALING: {ErrorType.PERFORMANCE: 'likely', ErrorType.CONCURRENCY: 'likely', ErrorType.DATABASE: 'likely'},
        }
        return probabilities.get(project_type, {})
    
    @staticmethod
    def _get_typical_errors(project_type: ProjectType) -> str:
        """Return human-readable list of typical errors"""
        typical = {
            ProjectType.GREENFIELD: "Syntax, Build, Dependency",
            ProjectType.BROWNFIELD: "Environment, Logic, Concurrency",
            ProjectType.FEATURE_DEV: "Logic, Database, Integration",
        }
        return typical.get(project_type, "Check opus.md error probability mapping")
    
    @staticmethod
    def _is_reasonable_dependency(dep: str) -> bool:
        """Check if dependency is stated clearly"""
        return len(dep) > 10 and ('must' in dep.lower() or 'should' in dep.lower() or 'before' in dep.lower())
    
    @staticmethod
    def _get_fix_for_error(error_msg: str, code_length: int) -> str:
        """Return specific fix for each error type"""
        if 'problem' in error_msg:
            return "Write a one-sentence problem statement: 'Current state → Desired state'"
        elif 'mechanism' in error_msg:
            return "Explain in one paragraph: how does this code work?"
        elif 'invariant' in error_msg:
            return "Name something that MUST always be true (e.g., 'User never sees null')"
        elif 'constraint' in error_msg:
            return "State why this is non-trivial (performance, scale, safety, etc)"
        elif 'failure_modes' in error_msg:
            return "List 3-5 ways this can break. Use format: 'If X → Y fails → Z crashes'"
        elif 'boring_solution' in error_msg:
            return "What's a simpler, proven approach? Then explain why you rejected it."
        elif 'cost' in error_msg:
            return f"Estimate: write {code_length//20}h, test {code_length//15}h, debug {code_length//25}h, change {code_length//50}h"
        else:
            return "See opus.md Phase 1 section for detailed guidance"
    
    def lock(self):
        """Lock model on first code execution"""
        if not self.locked:
            self.locked = True
            self.timestamp = datetime.now()
    
    def approve_for_implementation(self):
        """Approve model for code implementation"""
        
        # CRITICAL FIX: Call enhanced validation before approval (only if code_length known)
        # This catches silent continuation, error probability, working memory health issues
        if self.code_length and self.code_length > 0:
            is_valid, issues = self.validate_enhanced(self.code_length)
            
            if not is_valid:
                # Find error-level issues that block approval
                errors = [i for i in issues if i.get('level') == 'error']
                if errors:
                    error_messages = [i['message'] for i in errors]
                    raise ValueError(f"Model validation failed before approval:\n" + "\n".join(error_messages))
                
                # Warn about warnings but allow approval
                warnings = [i for i in issues if i.get('level') in ['warning', 'critical_warning']]
                if warnings:
                    for w in warnings:
                        print(f"⚠️ {w['message']}")
        
        self.status = "approved"
        self.approval_timestamp = datetime.now()
    
    def mark_complete(self):
        """Mark implementation as complete"""
        self.status = "complete"
        self.completion_timestamp = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        """Export as dictionary (for JSON serialization)"""
        return {
            'function_name': self.function_name,
            'timestamp': self.timestamp.isoformat(),
            'locked': self.locked,
            'problem': self.problem,
            'mechanism': self.mechanism,
            'invariant': self.invariant,
            'constraint': self.constraint,
            'failure_modes': self.failure_modes,
            'boring_solution': self.boring_solution,
            'why_boring_rejected': self.why_boring_rejected,
            'cost': {
                'write_hours': self.cost.write_hours,
                'test_hours': self.cost.test_hours,
                'debug_hours': self.cost.debug_hours,
                'change_hours': self.cost.change_hours,
            },
            'confidence': self.confidence,
            'confidence_decay': self.confidence_decay.value,
            'status': self.status,
        }


# ============================================================================
# MODEL STORE (service factory pattern like LocalMind)
# ============================================================================

class ModelStore:
    """
    Singleton store for all function models.
    Uses factory pattern like LocalMind's services.
    """
    
    _instance = None
    
    def __init__(self):
        self.models: dict[str, FunctionModel] = {}
        self.models_dir = Path("./logs/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # CRITICAL FIX: Load failures from Phase 0 so agent can learn from history
        # Without this, agent records failures but never learns from them
        try:
            from phase_0_recorder import get_failure_recorder
            recorder = get_failure_recorder()
            # Load all previous failures from disk into memory
            if hasattr(recorder, 'load_from_disk'):
                recorder.load_from_disk()
                # Track loaded failures for stats
                num_failures = len(recorder.failures) if hasattr(recorder, 'failures') else 0
                if num_failures > 0:
                    print(f"✓ Loaded {num_failures} previous failures for learning")
        except (ImportError, FileNotFoundError, Exception) as e:
            # It's okay if Phase 0 isn't available yet
            pass
    
    @classmethod
    def get_instance(cls) -> "ModelStore":
        """Get singleton instance (LocalMind pattern)"""
        if cls._instance is None:
            cls._instance = ModelStore()
        return cls._instance
    
    def create_model(self, function_name: str) -> FunctionModel:
        """Create a new model for a function"""
        model = FunctionModel(function_name=function_name)
        self.models[function_name] = model
        return model
    
    def get_model(self, function_name: str) -> Optional[FunctionModel]:
        """Get existing model"""
        return self.models.get(function_name)
    
    def get_or_create(self, function_name: str) -> FunctionModel:
        """Get existing or create new"""
        if function_name not in self.models:
            return self.create_model(function_name)
        return self.models[function_name]
    
    def save_model(self, function_name: str, model: FunctionModel):
        """Save model to disk (LocalMind pattern)"""
        filepath = self.models_dir / f"{function_name}_{model.timestamp.isoformat()}.json"
        with open(filepath, 'w') as f:
            json.dump(model.to_dict(), f, indent=2)
    
    def load_all_models(self):
        """Load all saved models from disk"""
        if not self.models_dir.exists():
            return
        for filepath in self.models_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    model = FunctionModel(
                        function_name=data['function_name'],
                        problem=data.get('problem', ''),
                        mechanism=data.get('mechanism', ''),
                        invariant=data.get('invariant', ''),
                    )
                    self.models[model.function_name] = model
            except Exception as e:
                print(f"Failed to load model from {filepath}: {e}")
    
    def get_stats(self) -> dict:
        """Get statistics on all models"""
        if not self.models:
            return {'count': 0}
        
        locked_count = sum(1 for m in self.models.values() if m.locked)
        approved_count = sum(1 for m in self.models.values() if m.status == "approved")
        complete_count = sum(1 for m in self.models.values() if m.status == "complete")
        avg_confidence = sum(m.confidence for m in self.models.values()) / len(self.models)
        
        return {
            'total_models': len(self.models),
            'locked': locked_count,
            'approved': approved_count,
            'complete': complete_count,
            'avg_confidence': round(avg_confidence, 2),
        }


# ============================================================================
# FACTORY FUNCTION (LocalMind pattern)
# ============================================================================

def get_model_store() -> ModelStore:
    """Get the global model store (factory pattern like LocalMind)"""
    return ModelStore.get_instance()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def test_model_engine():
    """Test Phase 1 model engine with real example"""
    # Get the store
    store = get_model_store()
    
    # Create a model for a function
    model = store.create_model("validate_json_schema")
    
    # Fill required fields
    model.problem = "Accept JSON strings and validate against JSON schema, raising errors on invalid input"
    model.mechanism = (
        "Read input string, apply JSON.parse() to get object, "
        "load schema from config, use Ajv library to validate object against schema, "
        "return validated object or raise ValueError with schema violation details"
    )
    model.invariant = "Every parsed and returned object strictly matches schema. Invalid input always raises error."
    
    # Medium-sized code, add more
    model.constraint = "Must validate 50MB files without memory explosion. Must reject invalid in <100ms."
    model.failure_modes = [
        "If JSON.parse fails → SyntaxError not caught → crash",
        "If schema loader fails → Ajv init fails → reject all inputs",
        "If validation incomplete → invalid data passes through → downstream errors",
    ]
    model.boring_solution = "Just use native JSON.parse with try/catch. No schema validation."
    model.why_boring_rejected = "Doesn't catch invalid structures. User gets wrong data."
    
    model.cost = CostEstimate(
        write_hours=3.0,
        test_hours=2.0,
        debug_hours=1.5,
        change_hours=1.0
    )
    
    model.concept_anchor = "Input Validation / Schema Checking"
    model.error_types = [ErrorType.DATA, ErrorType.LOGICAL]
    model.project_type = ProjectType.FEATURE_DEV
    model.confidence = 0.85
    model.dependency_check = ["Ajv library >= 8.0", "JSON input always string type"]
    
    # Working memory
    model.working_memory.add_confirmed("Ajv catches duplicate keys")
    model.working_memory.add_confirmed("JSON.parse throws on invalid syntax")
    model.working_memory.add_uncertain("Does Ajv support all JSON schema draft-2020-12?")
    model.working_memory.add_assumption("Schema file always exists and is valid")
    
    # Validate
    is_valid, errors = model.validate(code_length=80)
    assert is_valid, f"Model validation failed: {errors}"
    
    # Approve for implementation
    model.approve_for_implementation()
    assert model.status == "approved"
    
    # Save and verify
    store.save_model(model.function_name, model)
    
    # Get stats
    stats = store.get_stats()
    assert stats['total_models'] >= 1
    
    return model


if __name__ == "__main__":
    model = test_model_engine()
    print(f"✓ Model created: {model.function_name}")
    print(f"✓ Status: {model.status}")
    print(f"✓ Confidence: {model.confidence}")
    print(f"✓ Cost estimate: {model.cost}")
