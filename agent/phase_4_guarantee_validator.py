#!/usr/bin/env python3
"""
Phase 4: Guarantee Validation Engine

Purpose:
  Verify that all guarantees made in Phase 1 models actually hold.
  Check invariants, constraints, and failure modes.
  Catch guarantee violations BEFORE they hit production.

Pattern (from reference projects):
  - LocalMind: guarantee_owners define responsibility
  - Scrapling: Pre-flight checks before scraping
  - Autoresearch: Data validation before training
  
Architecture:
  - GuaranteeValidator: Checks if guarantee holds
  - InvariantMonitor: Watches if invariants break
  - ConstraintChecker: Validates constraints
  - GuaranteeReport: Records violations
  - GuaranteeStore: Singleton manager
"""

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import json


class GuaranteeType(Enum):
    """Types of guarantees"""
    INVARIANT = "invariant"  # Must always be true
    CONSTRAINT = "constraint"  # Must satisfy condition
    OWNERSHIP = "ownership"  # Who is responsible
    PRECONDITION = "precondition"  # Must be true before execution
    POSTCONDITION = "postcondition"  # Must be true after execution


class ViolationSeverity(Enum):
    """How bad is this violation"""
    WARNING = "warning"  # Can continue, but shouldn't
    ERROR = "error"  # Serious, but can recover
    CRITICAL = "critical"  # Fatal, stop immediately


# ============================================================================
# GUARANTEE DEFINITIONS
# ============================================================================

@dataclass
class Guarantee:
    """A single guarantee that must hold"""
    id: str
    name: str
    guarantee_type: GuaranteeType
    description: str
    owner: str  # Who is responsible for ensuring this
    
    # How to verify it
    check_function: Optional[Callable] = None  # Function that returns True/False
    check_description: str = ""  # How to manually verify
    
    # What if it breaks
    violation_severity: ViolationSeverity = ViolationSeverity.ERROR
    remediation: str = ""  # How to fix if violated
    
    # Tracking
    last_check_time: Optional[datetime] = None
    last_check_passed: bool = False
    failure_count: int = 0
    confidence: float = 0.5


@dataclass
class GuaranteeViolation:
    """Record of a guarantee being violated"""
    id: str
    guarantee_id: str
    timestamp: datetime
    violation_type: ViolationSeverity
    description: str
    evidence: str  # What proved it was violated
    detected_at_location: str  # File:line where discovered
    remediation_applied: Optional[str] = None
    resolved: bool = False


@dataclass
class InvariantCheck:
    """Check that an invariant holds"""
    id: str
    invariant: str  # The invariant description
    function_name: str  # Function that must maintain this
    check_code: str  # Code to verify invariant
    expected_state: Any  # What should be true
    actual_state: Any = None  # What we found
    passed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConstraintViolation:
    """Record when a constraint is violated"""
    id: str
    constraint: str
    violated_at: str  # File:line
    expected: Any
    actual: Any
    severity: ViolationSeverity
    timestamp: datetime = field(default_factory=datetime.now)


# ============================================================================
# GUARANTEE VALIDATOR
# ============================================================================

class GuaranteeValidator:
    """Validates that guarantees hold"""
    
    def __init__(self):
        self.guarantees: Dict[str, Guarantee] = {}
        self.violations: List[GuaranteeViolation] = []
        self.invariant_checks: List[InvariantCheck] = []
        self.constraint_violations: List[ConstraintViolation] = []
    
    def register_guarantee(self, guarantee: Guarantee) -> None:
        """Register a guarantee to validate"""
        self.guarantees[guarantee.id] = guarantee
    
    def register_invariant(self, function_name: str, invariant: str, 
                          check_code: str, expected_state: Any) -> InvariantCheck:
        """Register an invariant that must hold"""
        check = InvariantCheck(
            id=f"invariant_{len(self.invariant_checks)}_{datetime.now().timestamp()}",
            invariant=invariant,
            function_name=function_name,
            check_code=check_code,
            expected_state=expected_state,
        )
        self.invariant_checks.append(check)
        return check
    
    def check_guarantee(self, guarantee_id: str, context: Dict[str, Any] = None) -> bool:
        """
        Check if a guarantee holds
        
        Args:
            guarantee_id: Which guarantee to check
            context: Data to use for checking (e.g., values, states)
        
        Returns:
            True if guarantee holds, False if violated
        """
        if guarantee_id not in self.guarantees:
            return False
        
        guarantee = self.guarantees[guarantee_id]
        context = context or {}
        passed = False
        
        # Try to execute check function
        if guarantee.check_function:
            try:
                passed = guarantee.check_function(context)
            except Exception as e:
                # Check function failed - guarantee violated
                self._record_violation(
                    guarantee_id,
                    f"Check function raised exception: {e}",
                    guarantee.violation_severity,
                    str(e)
                )
                passed = False
        
        # Update guarantee tracking
        guarantee.last_check_time = datetime.now()
        guarantee.last_check_passed = passed
        
        if not passed:
            guarantee.failure_count += 1
            # CRITICAL: Record violation when guarantee fails
            self._record_violation(
                guarantee_id,
                f"Guarantee violation: {guarantee.name}",
                guarantee.violation_severity,
                f"Context: {context}"
            )
        
        return passed
    
    def check_invariant(self, check_id: str, actual_state: Any) -> bool:
        """
        Check if an invariant still holds
        
        Args:
            check_id: Which invariant check
            actual_state: Current state to check
        
        Returns:
            True if invariant still holds
        """
        # Find the check
        check = next((c for c in self.invariant_checks if c.id == check_id), None)
        if not check:
            return False
        
        check.actual_state = actual_state
        check.passed = (actual_state == check.expected_state)
        check.timestamp = datetime.now()
        
        if not check.passed:
            print(f"⚠️ INVARIANT VIOLATED: {check.invariant}")
            print(f"   Function: {check.function_name}")
            print(f"   Expected: {check.expected_state}")
            print(f"   Actual: {actual_state}")
        
        return check.passed
    
    def check_constraint(self, constraint: str, expected: Any, actual: Any,
                        location: str = "unknown", severity: ViolationSeverity = ViolationSeverity.ERROR) -> bool:
        """
        Check if a constraint is satisfied
        
        For constraints like "response_time <= 100ms":
        - expected = 100 (the limit)
        - actual = 95 (what we measured)
        - If actual <= expected, constraint satisfied
        
        Returns:
            True if constraint satisfied, False if violated
        """
        # For numeric constraints, check if actual is within expected
        try:
            satisfied = actual <= expected  # e.g., 95ms <= 100ms limit
        except TypeError:
            # For non-numeric, check equality
            satisfied = (expected == actual)
        
        if not satisfied:
            violation = ConstraintViolation(
                id=f"constraint_{len(self.constraint_violations)}_{datetime.now().timestamp()}",
                constraint=constraint,
                violated_at=location,
                expected=expected,
                actual=actual,
                severity=severity,
            )
            self.constraint_violations.append(violation)
            
            print(f"⚠️ CONSTRAINT VIOLATED: {constraint}")
            print(f"   Location: {location}")
            print(f"   Limit: {expected}")
            print(f"   Actual: {actual}")
        
        return satisfied
    
    def _record_violation(self, guarantee_id: str, description: str,
                         severity: ViolationSeverity, evidence: str) -> GuaranteeViolation:
        """Record a guarantee violation"""
        violation = GuaranteeViolation(
            id=f"violation_{len(self.violations)}_{datetime.now().timestamp()}",
            guarantee_id=guarantee_id,
            timestamp=datetime.now(),
            violation_type=severity,
            description=description,
            evidence=evidence,
            detected_at_location="executor",
        )
        self.violations.append(violation)
        return violation
    
    def get_violations(self) -> List[GuaranteeViolation]:
        """Get all recorded violations"""
        return self.violations.copy()
    
    def get_violations_by_severity(self, severity: ViolationSeverity) -> List[GuaranteeViolation]:
        """Get violations of specific severity"""
        return [v for v in self.violations if v.violation_type == severity]
    
    def get_guarantee_report(self) -> Dict[str, Any]:
        """Get comprehensive guarantee report"""
        critical_count = len(self.get_violations_by_severity(ViolationSeverity.CRITICAL))
        error_count = len(self.get_violations_by_severity(ViolationSeverity.ERROR))
        warning_count = len(self.get_violations_by_severity(ViolationSeverity.WARNING))
        
        return {
            'total_guarantees': len(self.guarantees),
            'total_violations': len(self.violations),
            'critical_violations': critical_count,
            'error_violations': error_count,
            'warning_violations': warning_count,
            'invariant_checks': len(self.invariant_checks),
            'invariants_passed': sum(1 for c in self.invariant_checks if c.passed),
            'constraint_violations': len(self.constraint_violations),
            'guarantees_by_owner': self._group_guarantees_by_owner(),
            'recommended_action': self._get_recommended_action(critical_count),
        }
    
    def _group_guarantees_by_owner(self) -> Dict[str, List[str]]:
        """Group guarantees by owner"""
        result = {}
        for guarantee in self.guarantees.values():
            if guarantee.owner not in result:
                result[guarantee.owner] = []
            result[guarantee.owner].append(guarantee.name)
        return result
    
    def _get_recommended_action(self, critical_count: int) -> str:
        """Get recommendation based on violations"""
        if critical_count > 0:
            return "STOP: Critical guarantee violations. Do not execute."
        elif len(self.constraint_violations) > 5:
            return "WARN: Multiple constraint violations. Review before proceeding."
        elif len(self.violations) > 0:
            return "CAUTION: Some guarantees violated. Verify remediation has been applied."
        else:
            return "OK: All guarantees satisfied. Safe to proceed."


# ============================================================================
# GUARANTEE STORE (Singleton)
# ============================================================================

class GuaranteeStore:
    """Singleton store for all guarantees"""
    
    _instance = None
    
    def __init__(self):
        self.validator = GuaranteeValidator()
        self.violations_dir = Path("./logs/guarantee_violations")
        self.violations_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize with common guarantees from reference projects
        self._load_common_guarantees()
    
    def _load_common_guarantees(self):
        """Load guarantees commonly needed"""
        
        # From LocalMind: Database consistency guarantee
        self.validator.register_guarantee(Guarantee(
            id="g_db_consistency",
            name="Database consistency",
            guarantee_type=GuaranteeType.INVARIANT,
            description="Database state is always consistent. No partial updates.",
            owner="database_layer",
            check_function=lambda ctx: ctx.get('transaction_complete', True),
            check_description="Check that all database writes complete together",
            violation_severity=ViolationSeverity.CRITICAL,
            remediation="Rollback transaction and retry.",
        ))
        
        # From Scrapling: No duplicate scrapes
        self.validator.register_guarantee(Guarantee(
            id="g_no_duplicates",
            name="No duplicate items",
            guarantee_type=GuaranteeType.INVARIANT,
            description="Each item is scraped exactly once.",
            owner="scraping_layer",
            check_function=lambda ctx: len(ctx.get('items', [])) == len(set(ctx.get('item_hashes', []))),
            check_description="Check that no duplicate hashes exist",
            violation_severity=ViolationSeverity.ERROR,
            remediation="Deduplicate using checksums and retry.",
        ))
        
        # From Autoresearch: Data validity
        self.validator.register_guarantee(Guarantee(
            id="g_data_valid",
            name="Data is valid",
            guarantee_type=GuaranteeType.PRECONDITION,
            description="All input data passes validation before processing.",
            owner="data_validation_layer",
            check_function=lambda ctx: ctx.get('validation_passed', False),
            check_description="Verify all required fields are present and correct type",
            violation_severity=ViolationSeverity.ERROR,
            remediation="Clean data and retry validation.",
        ))
        
        # From all projects: Resource cleanup
        self.validator.register_guarantee(Guarantee(
            id="g_resources_cleaned",
            name="Resources cleaned",
            guarantee_type=GuaranteeType.POSTCONDITION,
            description="All temporary resources are released.",
            owner="resource_manager",
            check_function=lambda ctx: ctx.get('resources_released', True),
            check_description="Check that temp files, connections, memory are freed",
            violation_severity=ViolationSeverity.WARNING,
            remediation="Force cleanup and clear orphaned resources.",
        ))
        
        # Type safety guarantee
        self.validator.register_guarantee(Guarantee(
            id="g_type_safety",
            name="Type safety",
            guarantee_type=GuaranteeType.INVARIANT,
            description="All values have expected types throughout execution.",
            owner="type_checking_layer",
            check_function=lambda ctx: all(isinstance(v, t) for v, t in ctx.get('type_checks', [])),
            check_description="Verify types match expected for all critical values",
            violation_severity=ViolationSeverity.ERROR,
            remediation="Add explicit type conversion or validation.",
        ))
    
    def get_validator(self) -> GuaranteeValidator:
        """Get the validator"""
        return self.validator
    
    def save_violations(self):
        """Save all violations to disk"""
        violations = self.validator.get_violations()
        if violations:
            filepath = self.violations_dir / f"violations_{datetime.now().timestamp()}.json"
            with open(filepath, 'w') as f:
                data = [
                    {
                        'id': v.id,
                        'guarantee_id': v.guarantee_id,
                        'timestamp': v.timestamp.isoformat(),
                        'violation_type': v.violation_type.value,
                        'description': v.description,
                        'evidence': v.evidence,
                        'detected_at': v.detected_at_location,
                    }
                    for v in violations
                ]
                json.dump(data, f, indent=2)
    
    @classmethod
    def get_instance(cls) -> "GuaranteeStore":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = GuaranteeStore()
        return cls._instance


@lru_cache(maxsize=1)
def get_guarantee_store() -> GuaranteeStore:
    """Factory function"""
    return GuaranteeStore.get_instance()


# ============================================================================
# TESTS
# ============================================================================

def test_guarantee_validation():
    """Test guarantee checking"""
    store = get_guarantee_store()
    validator = store.get_validator()
    
    # Test 1: Check passing guarantee
    result = validator.check_guarantee(
        "g_db_consistency",
        context={'transaction_complete': True}
    )
    assert result == True
    print("✓ Test 1 PASS: Guarantee passes when condition met")
    
    # Test 2: Check failing guarantee
    result = validator.check_guarantee(
        "g_db_consistency",
        context={'transaction_complete': False}
    )
    assert result == False
    assert len(validator.get_violations()) > 0
    print("✓ Test 2 PASS: Guarantee fails when condition not met")
    print(f"  Violations recorded: {len(validator.get_violations())}")
    
    # Test 3: Check guarantee by severity
    critical_violations = validator.get_violations_by_severity(ViolationSeverity.CRITICAL)
    assert len(critical_violations) > 0
    print(f"✓ Test 3 PASS: Critical violations tracked")
    print(f"  Critical count: {len(critical_violations)}")


def test_invariant_checking():
    """Test invariant validation"""
    store = get_guarantee_store()
    validator = store.get_validator()
    
    # Test 1: Register invariant
    check = validator.register_invariant(
        function_name="process_data",
        invariant="Size must not exceed limit",
        check_code="len(data) <= max_size",
        expected_state=100
    )
    assert check is not None
    print("✓ Test 1 PASS: Invariant registered")
    
    # Test 2: Check passing invariant
    result = validator.check_invariant(check.id, 100)
    assert result == True
    print("✓ Test 2 PASS: Invariant passes when matched")
    
    # Test 3: Check failing invariant
    result = validator.check_invariant(check.id, 150)
    assert result == False
    print("✓ Test 3 PASS: Invariant fails when not matched")
    print(f"  Expected: 100, Got: 150")


def test_constraint_checking():
    """Test constraint validation"""
    store = get_guarantee_store()
    validator = store.get_validator()
    
    # Test 1: Check passing constraint
    result = validator.check_constraint(
        constraint="response_time <= 100ms",
        expected=100,
        actual=95,
        location="api_handler:45"
    )
    assert result == True
    print("✓ Test 1 PASS: Constraint passes")
    
    # Test 2: Check failing constraint
    result = validator.check_constraint(
        constraint="response_time <= 100ms",
        expected=100,
        actual=150,
        location="api_handler:45",
        severity=ViolationSeverity.WARNING
    )
    assert result == False
    assert len(validator.constraint_violations) > 0
    print("✓ Test 2 PASS: Constraint violation recorded")
    print(f"  Total constraint violations: {len(validator.constraint_violations)}")


def test_guarantee_report():
    """Test guarantee report generation"""
    store = get_guarantee_store()
    validator = store.get_validator()
    
    # Generate report
    report = validator.get_guarantee_report()
    
    assert 'total_guarantees' in report
    assert 'total_violations' in report
    assert 'recommended_action' in report
    
    print("✓ Test 1 PASS: Guarantee report generated")
    print(f"  Total guarantees: {report['total_guarantees']}")
    print(f"  Total violations: {report['total_violations']}")
    print(f"  Critical violations: {report['critical_violations']}")
    print(f"  Recommendation: {report['recommended_action']}")
    
    # Test 2: Grouped by owner
    owners = report['guarantees_by_owner']
    assert len(owners) > 0
    print(f"✓ Test 2 PASS: Guarantees grouped by owner")
    print(f"  Owners: {list(owners.keys())}")


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 4: GUARANTEE VALIDATION ENGINE - TEST")
    print("=" * 80)
    
    print("\n[Test Suite 1] Guarantee Validation")
    print("-" * 80)
    test_guarantee_validation()
    
    print("\n[Test Suite 2] Invariant Checking")
    print("-" * 80)
    test_invariant_checking()
    
    print("\n[Test Suite 3] Constraint Checking")
    print("-" * 80)
    test_constraint_checking()
    
    print("\n[Test Suite 4] Guarantee Reporting")
    print("-" * 80)
    test_guarantee_report()
    
    print("\n" + "=" * 80)
    print("PHASE 4 TESTS PASSED")
    print("=" * 80)
