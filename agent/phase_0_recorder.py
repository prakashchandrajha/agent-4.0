"""
Phase 0: Failure Recorder
Real patterns from LocalMind, Scrapling, Superpowers

Records failures with extracted beliefs, not just symptoms.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import json


@dataclass
class Failure:
    """Single failure record with complete analysis"""
    
    id: str
    timestamp: datetime
    
    # What failed
    code: str  # First 500 chars
    error_signal: str
    
    # The belief analysis (MUST be specific)
    believed: str
    reality: str
    specific_assumption: str  # CRITICAL: No vague assumptions
    why_belief_felt_right: str
    
    # Classification
    error_class: int  # 1/2/3/4
    error_type: int  # 1-15
    project_context: str  # Which of 15
    concept_candidate: Optional[str] = None
    confidence: float = 0.5
    
    # Evidence
    evidence: List[str] = field(default_factory=list)
    reference_project: Optional[str] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'code': self.code,
            'error_signal': self.error_signal,
            'believed': self.believed,
            'reality': self.reality,
            'specific_assumption': self.specific_assumption,
            'why_belief_felt_right': self.why_belief_felt_right,
            'error_class': self.error_class,
            'error_type': self.error_type,
            'project_context': self.project_context,
            'concept_candidate': self.concept_candidate,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'reference_project': self.reference_project,
        }


class FailureRecorder:
    """Records failures from reference projects"""
    
    def __init__(self):
        self.failures: List[Failure] = []
        self.failures_dir = Path("./logs/failures")
        self.failures_dir.mkdir(parents=True, exist_ok=True)
        self.failure_count = 0
    
    def record(self, config: dict) -> Failure:
        """
        Record a failure
        
        Args:
            config: {
                code: str,
                error_signal: str,
                believed: str,
                reality: str,
                specific_assumption: str (MUST be specific),
                why_belief_felt_right: str,
                error_class: int (1-4),
                error_type: int (1-15),
                project_context: str,
                concept_candidate: Optional[str],
                confidence: float,
                evidence: List[str],
                reference_project: Optional[str],
            }
        """
        
        # CRITICAL: Validate error_class and error_type ranges FIRST
        error_class = config.get('error_class', 0)
        error_type = config.get('error_type', 0)
        
        if not isinstance(error_class, int) or not (1 <= error_class <= 4):
            raise ValueError(
                f"REJECTED: Invalid error_class {error_class}, must be 1-4 (REQUIREMENT/LOGICAL/DESIGN/EXECUTION)"
            )
        
        if not isinstance(error_type, int) or not (1 <= error_type <= 15):
            raise ValueError(
                f"REJECTED: Invalid error_type {error_type}, must be 1-15 (see ErrorType enum)"
            )
        
        # VALIDATION: Assumption must be specific
        assumption = config.get('specific_assumption', '')
        if not assumption or len(assumption) < 20:
            raise ValueError(
                f"REJECTED: Assumption too short or vague.\n"
                f"Given: '{assumption}'\n"
                f"Must be >= 20 chars and specific"
            )
        
        # Check for vague words
        vague_indicators = ['something', 'wrong', 'issue', 'problem', 'bug', 'error', 'broken']
        if any(word in assumption.lower() for word in vague_indicators):
            raise ValueError(
                f"REJECTED: Assumption is vague.\n"
                f"Given: '{assumption}'\n"
                f"Must name specific false belief, not symptom"
            )
        
        # CRITICAL FIX: Validate evidence is non-empty
        evidence = config.get('evidence', [])
        if not evidence or len(evidence) == 0:
            raise ValueError(
                f"REJECTED: No evidence provided. Must explain WHY this belief failed.\n"
                f"Evidence items required (minimum 1)"
            )
        
        # Create failure record
        failure = Failure(
            id=f"failure_{self.failure_count}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            code=config.get('code', '')[:500],
            error_signal=config.get('error_signal', ''),
            believed=config.get('believed', ''),
            reality=config.get('reality', ''),
            specific_assumption=assumption,
            why_belief_felt_right=config.get('why_belief_felt_right', ''),
            error_class=error_class,
            error_type=error_type,
            project_context=config.get('project_context', ''),
            concept_candidate=config.get('concept_candidate'),
            confidence=config.get('confidence', 0.5),
            evidence=config.get('evidence', []),
            reference_project=config.get('reference_project'),
        )
        
        self.failure_count += 1
        self.failures.append(failure)
        self._save_failure(failure)
        
        return failure
    
    def _save_failure(self, failure: Failure):
        """Save failure to disk"""
        filepath = self.failures_dir / f"{failure.id}.json"
        with open(filepath, 'w') as f:
            json.dump(failure.to_dict(), f, indent=2)
    
    def get_by_type(self, error_type: int) -> List[Failure]:
        """Get failures by error type"""
        return [f for f in self.failures if f.error_type == error_type]
    
    def get_by_class(self, error_class: int) -> List[Failure]:
        """Get failures by error class"""
        return [f for f in self.failures if f.error_class == error_class]
    
    def get_stats(self) -> dict:
        """Get statistics"""
        if not self.failures:
            return {'count': 0}
        
        by_type = {}
        by_class = {}
        by_context = {}
        
        for f in self.failures:
            by_type[f.error_type] = by_type.get(f.error_type, 0) + 1
            by_class[f.error_class] = by_class.get(f.error_class, 0) + 1
            by_context[f.project_context] = by_context.get(f.project_context, 0) + 1
        
        avg_confidence = sum(f.confidence for f in self.failures) / len(self.failures)
        
        return {
            'total': len(self.failures),
            'by_type': by_type,
            'by_class': by_class,
            'by_context': by_context,
            'avg_confidence': round(avg_confidence, 2),
            'all_15_types_covered': len(by_type) >= 15,
        }
    
    def load_from_disk(self):
        """Load all failures from disk"""
        if not self.failures_dir.exists():
            return
        
        for filepath in self.failures_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    failure = Failure(
                        id=data['id'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        code=data.get('code', ''),
                        error_signal=data.get('error_signal', ''),
                        believed=data.get('believed', ''),
                        reality=data.get('reality', ''),
                        specific_assumption=data.get('specific_assumption', ''),
                        why_belief_felt_right=data.get('why_belief_felt_right', ''),
                        error_class=data.get('error_class', 0),
                        error_type=data.get('error_type', 0),
                        project_context=data.get('project_context', ''),
                        concept_candidate=data.get('concept_candidate'),
                        confidence=data.get('confidence', 0.5),
                        evidence=data.get('evidence', []),
                        reference_project=data.get('reference_project'),
                    )
                    self.failures.append(failure)
            except Exception as e:
                print(f"Failed to load {filepath}: {e}")


# Singleton instance
_recorder_instance = None

def get_failure_recorder() -> FailureRecorder:
    """Get singleton failure recorder instance"""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = FailureRecorder()
    return _recorder_instance
