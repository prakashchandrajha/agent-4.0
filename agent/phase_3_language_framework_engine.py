#!/usr/bin/env python3
"""
Phase 3: Language & Framework Learning Engine

Purpose:
  Agent learns to recognize and work with different programming languages and frameworks.
  Detects language/framework from code. Stores decisions indexed by language.
  Retrieves past decisions for similar patterns in new code.
  
  This enables: "real ai agent that can learn coding langs and frameworks"

Architecture:
  - Language Detection: Identify language from syntax/imports/file extension
  - Framework Detection: Identify frameworks from dependencies/structure
  - Decision Memory: Store solutions indexed by (language, framework, pattern)
  - Pattern Retrieval: Find similar past solutions for new code
  - Learning: Extract language-specific error patterns and best practices
  
Reference Patterns:
  - Python (LocalMind, Scrapling): Decorators, async/await, type hints, duck typing
  - JavaScript (LocalMind frontend): Closures, 'this' binding, Hooks, Promises
  - Go: (Pinchtab): Error returns, goroutines, channels, nil-safety
"""

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import re


# ============================================================================
# LANGUAGE & FRAMEWORK ENUMS (Learned from reference projects)
# ============================================================================

class Language(Enum):
    """Programming languages found in reference projects"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    GO = "go"
    SQL = "sql"
    BASH = "bash"
    UNKNOWN = "unknown"


class Framework(Enum):
    """Frameworks found in reference projects"""
    DJANGO = "django"
    FASTAPI = "fastapi"
    VUE = "vue"
    REACT = "react"
    SCRAPLING = "scrapling"
    PYTEST = "pytest"
    UNITTEST = "unittest"
    SQLMODEL = "sqlmodel"
    SQLALCHEMY = "sqlalchemy"
    NONE = "none"


class LanguageFeature(Enum):
    """Language-specific features that are NOT obvious"""
    # Python
    DECORATOR = "decorator"  # @decorator changes function behavior
    ASYNC_AWAIT = "async_await"  # Must await, can't mix with sync
    TYPE_HINT = "type_hint"  # Documentation only, not enforced
    CONTEXT_MANAGER = "context_manager"  # with statement resource management
    DUCK_TYPING = "duck_typing"  # Type checking at runtime
    
    # JavaScript
    CLOSURE = "closure"  # Functions capture outer scope
    THIS_BINDING = "this_binding"  # 'this' is dynamic unless arrow function
    PROMISE = "promise"  # Async pattern
    REACT_HOOK = "react_hook"  # Functions that manage state
    EVENT_LOOP = "event_loop"  # Single-threaded async
    
    # Go
    ERROR_RETURN = "error_return"  # Errors as return values
    GOROUTINE = "goroutine"  # Lightweight concurrent execution
    CHANNEL = "channel"  # Goroutine communication
    DEFER = "defer"  # Guaranteed cleanup execution
    INTERFACE = "interface"  # Structural typing


class ErrorPattern(Enum):
    """Language-specific error types"""
    # Python errors
    INDENT_ERROR = "indent_error"
    NAME_ERROR = "name_error"
    ATTRIBUTE_ERROR = "attribute_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    KEY_ERROR = "key_error"
    IMPORT_ERROR = "import_error"
    ASYNC_ERROR = "async_error"  # Can't await in sync context
    
    # JavaScript errors
    REFERENCE_ERROR = "reference_error"  # undefined variable
    PROMISE_REJECTION = "promise_rejection"  # Unhandled promise
    NULL_PTR = "null_ptr"  # undefined.something
    THIS_UNDEFINED = "this_undefined"  # 'this' is undefined
    HOOK_VIOLATION = "hook_violation"  # React hook rules
    
    # Go errors
    NIL_DEREFERENCE = "nil_dereference"  # nil pointer panic
    CHANNEL_DEADLOCK = "channel_deadlock"  # Goroutine waits forever
    INTERFACE_NIL = "interface_nil"  # Interface with nil value
    TYPE_ASSERTION = "type_assertion"  # Type cast fails


# ============================================================================
# DECISION MEMORY (Indexed by Language/Framework)
# ============================================================================

@dataclass
class LanguagePattern:
    """A learned pattern about a language/framework"""
    id: str
    language: Language
    framework: Optional[Framework]
    feature: LanguageFeature
    description: str  # What we learned
    code_example: str  # Example code demonstrating this
    common_error: Optional[ErrorPattern]  # What breaks if violated
    best_practice: str  # How to do it right
    confidence: float = 0.5  # How sure are we about this pattern
    timestamp: datetime = field(default_factory=datetime.now)
    reference_project: Optional[str] = None  # Where we learned this


@dataclass
class FrameworkDecision:
    """Decision made about how to use a framework"""
    id: str
    framework: Framework
    language: Language
    pattern_type: str  # e.g., "state_management", "async_handling"
    decision: str  # What we decided to do
    rationale: str  # Why we made this decision
    code_snippet: str  # Implementation
    affected_components: List[str] = field(default_factory=list)
    error_history: List[str] = field(default_factory=list)  # Errors we hit
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LanguageDetectionResult:
    """Result of language detection"""
    language: Language
    framework: Optional[Framework]
    confidence: float  # 0.0 to 1.0
    detected_by: List[str] = field(default_factory=list)  # Which heuristics matched
    file_extension: Optional[str] = None
    key_imports: List[str] = field(default_factory=list)
    detected_features: List[LanguageFeature] = field(default_factory=list)


# ============================================================================
# LANGUAGE DETECTION (From reference projects)
# ============================================================================

class LanguageDetector:
    """Detect language/framework from code"""
    
    # File extension mapping (from reference projects)
    EXTENSION_MAP = {
        '.py': Language.PYTHON,
        '.js': Language.JAVASCRIPT,
        '.ts': Language.JAVASCRIPT,  # TypeScript is JavaScript family
        '.jsx': Language.JAVASCRIPT,
        '.tsx': Language.JAVASCRIPT,
        '.go': Language.GO,
        '.sql': Language.SQL,
        '.sh': Language.BASH,
    }
    
    # Import patterns (what imports reveal about framework)
    FRAMEWORK_IMPORTS = {
        # Python frameworks
        'from django': Framework.DJANGO,
        'import django': Framework.DJANGO,
        'from fastapi': Framework.FASTAPI,
        'import fastapi': Framework.FASTAPI,
        'from sqlalchemy': Framework.SQLALCHEMY,
        'import sqlalchemy': Framework.SQLALCHEMY,
        'from pydantic': Framework.FASTAPI,  # FastAPI uses Pydantic
        'import scrapling': Framework.SCRAPLING,
        'from scrapling': Framework.SCRAPLING,
        'import pytest': Framework.PYTEST,
        'import unittest': Framework.UNITTEST,
        
        # JavaScript frameworks
        'import Vue': Framework.VUE,
        'import { createApp }': Framework.VUE,
        'import React': Framework.REACT,
        'from react': Framework.REACT,
        'import { useState }': Framework.REACT,
    }
    
    # Language-specific keywords
    LANGUAGE_KEYWORDS = {
        Language.PYTHON: {'def ', 'class ', 'import ', 'async def', '@', 'try:', 'except:', 'with '},
        Language.JAVASCRIPT: {'function ', 'const ', 'let ', 'var ', 'import ', 'export ', '=>', 'async '},
        Language.GO: {'package ', 'import ', 'func ', 'type ', 'interface ', 'chan ', 'go '},
    }
    
    @staticmethod
    def detect_from_code(code: str, filename: Optional[str] = None) -> LanguageDetectionResult:
        """
        Detect language and framework from code content
        
        Heuristics:
        1. File extension (most reliable)
        2. Import statements (reveal framework)
        3. Keywords (language-specific syntax)
        4. Decorators (@), type hints (::), async patterns
        """
        detected_features = []
        detected_by = []
        language = Language.UNKNOWN
        framework = None
        highest_confidence = 0.0
        key_imports = []
        file_ext = None
        
        # 1. Check file extension
        if filename:
            file_ext = Path(filename).suffix.lower()
            if file_ext in LanguageDetector.EXTENSION_MAP:
                language = LanguageDetector.EXTENSION_MAP[file_ext]
                detected_by.append(f"file_extension_{file_ext}")
                highest_confidence = 0.9
        
        # 2. Check imports for framework
        import_pattern = re.compile(r'(?:from|import)\s+[\w.]+', re.MULTILINE)
        imports = import_pattern.findall(code)
        key_imports = imports[:5]  # Save first 5 for debugging
        
        for import_stmt in imports:
            for pattern, fw in LanguageDetector.FRAMEWORK_IMPORTS.items():
                if pattern in import_stmt:
                    framework = fw
                    detected_by.append(f"import_{pattern}")
                    highest_confidence = min(1.0, highest_confidence + 0.3)
        
        # 3. Check keywords for language
        for lang, keywords in LanguageDetector.LANGUAGE_KEYWORDS.items():
            keyword_matches = sum(1 for kw in keywords if kw in code)
            if keyword_matches >= 2:  # At least 2 keywords match
                if language == Language.UNKNOWN:
                    language = lang
                    detected_by.append(f"keywords_{lang.value}")
                    highest_confidence = max(highest_confidence, 0.7)
        
        # 4. Detect language-specific features
        if '@' in code and 'def ' in code:
            detected_features.append(LanguageFeature.DECORATOR)
        
        if 'async def' in code or 'async function' in code:
            detected_features.append(LanguageFeature.ASYNC_AWAIT)
        
        if ': ' in code and '->' in code:  # Type hints are Python
            detected_features.append(LanguageFeature.TYPE_HINT)
            if language == Language.UNKNOWN:
                language = Language.PYTHON
        
        if '=>' in code or 'function' in code:  # JavaScript patterns
            if language == Language.UNKNOWN:
                language = Language.JAVASCRIPT
                detected_features.append(LanguageFeature.CLOSURE)
        
        if 'func ' in code and 'package ' in code:  # Go patterns
            language = Language.GO
            detected_features.append(LanguageFeature.GOROUTINE)
        
        return LanguageDetectionResult(
            language=language,
            framework=framework,
            confidence=highest_confidence,
            detected_by=detected_by,
            file_extension=file_ext,
            key_imports=key_imports,
            detected_features=detected_features,
        )


# ============================================================================
# LEARNED PATTERN STORE (Singleton)
# ============================================================================

class LanguageFrameworkStore:
    """Singleton manager for language/framework patterns and decisions"""
    
    _instance = None
    
    def __init__(self):
        self.patterns: Dict[str, LanguagePattern] = {}
        self.decisions: Dict[str, FrameworkDecision] = {}
        self.patterns_dir = Path("./logs/language_patterns")
        self.decisions_dir = Path("./logs/framework_decisions")
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize with learned patterns from reference projects
        self._load_patterns_from_reference()
    
    def _load_patterns_from_reference(self):
        """Initialize with patterns learned from reference projects"""
        
        # PYTHON PATTERNS (from LocalMind, Scrapling, Autoresearch)
        self.add_pattern(LanguagePattern(
            id="py_decorator_001",
            language=Language.PYTHON,
            framework=Framework.FASTAPI,
            feature=LanguageFeature.DECORATOR,
            description="Decorators in Python transform function behavior. @app.get() in FastAPI wraps function.",
            code_example="@app.get('/path')\ndef handler(): pass",
            common_error=ErrorPattern.ATTRIBUTE_ERROR,
            best_practice="Check what decorator does. It may not be transparent.",
            confidence=0.95,
            reference_project="LocalMind"
        ))
        
        self.add_pattern(LanguagePattern(
            id="py_async_001",
            language=Language.PYTHON,
            framework=Framework.FASTAPI,
            feature=LanguageFeature.ASYNC_AWAIT,
            description="async def requires await. Can't call async function from sync code.",
            code_example="async def fetch():\n    result = await async_call()\n    return result",
            common_error=ErrorPattern.ASYNC_ERROR,
            best_practice="async/await must be all the way up the call stack, or use asyncio.run()",
            confidence=0.95,
            reference_project="LocalMind"
        ))
        
        self.add_pattern(LanguagePattern(
            id="py_type_hint_001",
            language=Language.PYTHON,
            framework=None,
            feature=LanguageFeature.TYPE_HINT,
            description="Type hints in Python are DOCUMENTATION. They don't enforce types at runtime.",
            code_example="def process(data: dict) -> str:\n    return str(data)",
            common_error=ErrorPattern.TYPE_ERROR,
            best_practice="Type hints help IDEs but don't prevent bad types. Add runtime validation if needed.",
            confidence=0.95,
            reference_project="autoresearch"
        ))
        
        # JAVASCRIPT PATTERNS (from LocalMind frontend)
        self.add_pattern(LanguagePattern(
            id="js_closure_001",
            language=Language.JAVASCRIPT,
            framework=Framework.REACT,
            feature=LanguageFeature.CLOSURE,
            description="Functions in JavaScript capture variables from outer scope. Closures persist state.",
            code_example="function makeCounter() {\n    let count = 0;\n    return () => count++;\n}",
            common_error=ErrorPattern.REFERENCE_ERROR,
            best_practice="Understand what scope each function closes over. Beware of loops creating closures.",
            confidence=0.95,
            reference_project="LocalMind"
        ))
        
        self.add_pattern(LanguagePattern(
            id="js_this_001",
            language=Language.JAVASCRIPT,
            framework=Framework.REACT,
            feature=LanguageFeature.THIS_BINDING,
            description="'this' in JavaScript is DYNAMIC. Use arrow functions to capture lexical 'this'.",
            code_example="class Handler {\n    handle = () => this.data;  // Arrow function captures 'this'\n}",
            common_error=ErrorPattern.THIS_UNDEFINED,
            best_practice="Use arrow functions for callbacks. Or bind: this.method.bind(this)",
            confidence=0.95,
            reference_project="LocalMind"
        ))
        
        self.add_pattern(LanguagePattern(
            id="js_promise_001",
            language=Language.JAVASCRIPT,
            framework=None,
            feature=LanguageFeature.PROMISE,
            description="fetch() does NOT reject on HTTP error. Must check response.ok.",
            code_example="const resp = await fetch(url);\nif (!resp.ok) throw new Error(resp.status);",
            common_error=ErrorPattern.PROMISE_REJECTION,
            best_practice="ALWAYS check response.ok after fetch(). Only network errors trigger rejection.",
            confidence=0.95,
            reference_project="LocalMind"
        ))
        
        # Go PATTERNS (from Pinchtab reference)
        self.add_pattern(LanguagePattern(
            id="go_error_001",
            language=Language.GO,
            framework=None,
            feature=LanguageFeature.ERROR_RETURN,
            description="Go returns errors as values, not exceptions. MUST check if err != nil.",
            code_example="result, err := doWork()\nif err != nil {\n    return err\n}",
            common_error=ErrorPattern.NIL_DEREFERENCE,
            best_practice="Check error immediately after any function that returns error. Never ignore.",
            confidence=0.95,
            reference_project="Pinchtab"
        ))
    
    def add_pattern(self, pattern: LanguagePattern):
        """Add a learned pattern"""
        self.patterns[pattern.id] = pattern
        self._save_pattern(pattern)
    
    def add_decision(self, decision: FrameworkDecision):
        """Add a framework decision"""
        self.decisions[decision.id] = decision
        self._save_decision(decision)
    
    def get_patterns_for_language(self, language: Language) -> List[LanguagePattern]:
        """Get all patterns for a specific language"""
        return [p for p in self.patterns.values() if p.language == language]
    
    def get_patterns_for_framework(self, framework: Framework) -> List[LanguagePattern]:
        """Get all patterns for a specific framework"""
        return [p for p in self.patterns.values() if p.framework == framework]
    
    def get_patterns_for_feature(self, feature: LanguageFeature) -> List[LanguagePattern]:
        """Get all patterns for a specific feature"""
        return [p for p in self.patterns.values() if p.feature == feature]
    
    def get_decisions_for_framework(self, framework: Framework) -> List[FrameworkDecision]:
        """Get all decisions for a specific framework"""
        return [d for d in self.decisions.values() if d.framework == framework]
    
    def find_similar_decisions(self, language: Language, framework: Framework, pattern_type: str) -> List[FrameworkDecision]:
        """Find similar past decisions"""
        return [
            d for d in self.decisions.values()
            if d.language == language and d.framework == framework and d.pattern_type == pattern_type
        ]
    
    def _save_pattern(self, pattern: LanguagePattern):
        """Save pattern to disk"""
        filepath = self.patterns_dir / f"pattern_{pattern.id}.json"
        with open(filepath, 'w') as f:
            data = {
                'id': pattern.id,
                'language': pattern.language.value,
                'framework': pattern.framework.value if pattern.framework else None,
                'feature': pattern.feature.value,
                'description': pattern.description,
                'code_example': pattern.code_example,
                'common_error': pattern.common_error.value if pattern.common_error else None,
                'best_practice': pattern.best_practice,
                'confidence': pattern.confidence,
                'timestamp': pattern.timestamp.isoformat(),
                'reference_project': pattern.reference_project,
            }
            json.dump(data, f, indent=2)
    
    def _save_decision(self, decision: FrameworkDecision):
        """Save decision to disk"""
        filepath = self.decisions_dir / f"decision_{decision.id}.json"
        with open(filepath, 'w') as f:
            data = {
                'id': decision.id,
                'framework': decision.framework.value,
                'language': decision.language.value,
                'pattern_type': decision.pattern_type,
                'decision': decision.decision,
                'rationale': decision.rationale,
                'code_snippet': decision.code_snippet,
                'affected_components': decision.affected_components,
                'error_history': decision.error_history,
                'confidence': decision.confidence,
                'timestamp': decision.timestamp.isoformat(),
            }
            json.dump(data, f, indent=2)
    
    def get_stats(self) -> dict:
        """Get statistics about learned patterns"""
        return {
            'total_patterns': len(self.patterns),
            'total_decisions': len(self.decisions),
            'languages_learned': {
                lang.value: len(self.get_patterns_for_language(lang))
                for lang in Language
            },
            'frameworks_learned': {
                fw.value: len(self.get_patterns_for_framework(fw))
                for fw in Framework
            },
            'avg_pattern_confidence': sum(p.confidence for p in self.patterns.values()) / max(len(self.patterns), 1),
            'avg_decision_confidence': sum(d.confidence for d in self.decisions.values()) / max(len(self.decisions), 1),
        }
    
    @classmethod
    def get_instance(cls) -> "LanguageFrameworkStore":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = LanguageFrameworkStore()
        return cls._instance


@lru_cache(maxsize=1)
def get_language_framework_store() -> LanguageFrameworkStore:
    """Factory function with caching"""
    return LanguageFrameworkStore.get_instance()


# ============================================================================
# PHASE 3: LANGUAGE LEARNER (Main API)
# ============================================================================

class LanguageFrameworkLearner:
    """
    The actual Phase 3 learner that:
    1. Detects language/framework
    2. Retrieves past decisions for similar code
    3. Suggests patterns and best practices
    4. Records new decisions as it learns
    """
    
    def __init__(self):
        self.store = get_language_framework_store()
        self.detector = LanguageDetector()
    
    def analyze_code(self, code: str, filename: Optional[str] = None) -> dict:
        """
        Analyze code to understand its language/framework and relevant patterns
        
        Returns:
            Dict with detected language, framework, relevant patterns, and best practices
        """
        
        # Step 1: Detect language
        detection = self.detector.detect_from_code(code, filename)
        
        # Step 2: Get relevant patterns
        patterns = self.store.get_patterns_for_language(detection.language)
        if detection.framework:
            patterns.extend(self.store.get_patterns_for_framework(detection.framework))
        
        # Step 3: Get past decisions for this framework
        past_decisions = []
        if detection.framework:
            past_decisions = self.store.get_decisions_for_framework(detection.framework)
        
        return {
            'language': detection.language.value,
            'framework': detection.framework.value if detection.framework else None,
            'confidence': detection.confidence,
            'detected_by': detection.detected_by,
            'detected_features': [f.value for f in detection.detected_features],
            'relevant_patterns': [
                {
                    'feature': p.feature.value,
                    'description': p.description,
                    'best_practice': p.best_practice,
                    'confidence': p.confidence,
                }
                for p in patterns
            ],
            'past_decisions': [
                {
                    'pattern_type': d.pattern_type,
                    'decision': d.decision,
                    'rationale': d.rationale,
                    'confidence': d.confidence,
                }
                for d in past_decisions[:3]  # Top 3 most recent
            ],
        }
    
    def record_decision(self, language: Language, framework: Framework, pattern_type: str, 
                       decision: str, rationale: str, code_snippet: str, 
                       affected_components: List[str] = None) -> FrameworkDecision:
        """
        Record a decision we've made about how to use a framework.
        This grows the agent's knowledge base.
        """
        fw_decision = FrameworkDecision(
            id=f"decision_{len(self.store.decisions)}_{datetime.now().timestamp()}",
            framework=framework,
            language=language,
            pattern_type=pattern_type,
            decision=decision,
            rationale=rationale,
            code_snippet=code_snippet,
            affected_components=affected_components or [],
            confidence=0.7,
        )
        self.store.add_decision(fw_decision)
        return fw_decision
    
    def get_language_guide(self, language: Language) -> dict:
        """Get a guide for coding in a specific language"""
        patterns = self.store.get_patterns_for_language(language)
        
        return {
            'language': language.value,
            'total_patterns': len(patterns),
            'features': [
                {
                    'feature': p.feature.value,
                    'description': p.description,
                    'example': p.code_example,
                    'common_error': p.common_error.value if p.common_error else None,
                    'best_practice': p.best_practice,
                }
                for p in patterns
            ],
            'stats': self.store.get_stats(),
        }


# ============================================================================
# TESTS
# ============================================================================

def test_language_detection():
    """Test language detection"""
    detector = LanguageDetector()
    
    # Test 1: Python detection
    python_code = """
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel

@app.get("/api/data")
async def fetch_data():
    result = await async_operation()
    return result
"""
    result = detector.detect_from_code(python_code, "api.py")
    assert result.language == Language.PYTHON
    assert result.framework == Framework.FASTAPI
    assert LanguageFeature.ASYNC_AWAIT in result.detected_features
    print(f"✓ Test 1 PASS: Python FastAPI detection")
    print(f"  Confidence: {result.confidence}")
    print(f"  Detected by: {result.detected_by}")
    
    # Test 2: JavaScript detection
    js_code = """
import React, { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    return <div>{count}</div>;
}
"""
    result = detector.detect_from_code(js_code, "component.jsx")
    assert result.language == Language.JAVASCRIPT
    assert result.framework == Framework.REACT
    print(f"✓ Test 2 PASS: JavaScript React detection")
    print(f"  Confidence: {result.confidence}")
    print(f"  Detected by: {result.detected_by}")
    
    # Test 3: Go detection
    go_code = """
package main

import (
    "fmt"
)

func main() {
    ch := make(chan string)
    go func() {
        ch <- "hello"
    }()
}
"""
    result = detector.detect_from_code(go_code, "main.go")
    assert result.language == Language.GO
    assert LanguageFeature.GOROUTINE in result.detected_features
    print(f"✓ Test 3 PASS: Go detection")
    print(f"  Confidence: {result.confidence}")


def test_language_patterns():
    """Test language pattern retrieval"""
    store = get_language_framework_store()
    
    # Test 1: Get Python patterns
    py_patterns = store.get_patterns_for_language(Language.PYTHON)
    assert len(py_patterns) >= 3
    print(f"✓ Test 1 PASS: Retrieved {len(py_patterns)} Python patterns")
    
    # Test 2: Get FastAPI patterns
    fastapi_patterns = store.get_patterns_for_framework(Framework.FASTAPI)
    assert len(fastapi_patterns) >= 2
    print(f"✓ Test 2 PASS: Retrieved {len(fastapi_patterns)} FastAPI patterns")
    
    # Test 3: Get patterns for feature
    async_patterns = store.get_patterns_for_feature(LanguageFeature.ASYNC_AWAIT)
    assert len(async_patterns) >= 1
    print(f"✓ Test 3 PASS: Retrieved {len(async_patterns)} async/await patterns")
    
    # Test 4: Stats
    stats = store.get_stats()
    print(f"✓ Test 4 PASS: Got stats")
    print(f"  Total patterns: {stats['total_patterns']}")
    print(f"  Languages learned: {stats['languages_learned']}")


def test_learner():
    """Test the learner API"""
    learner = LanguageFrameworkLearner()
    
    # Test 1: Analyze Python code
    python_code = """
@app.get("/api")
async def handler():
    data = await fetch()
    return data
"""
    analysis = learner.analyze_code(python_code, "api.py")
    assert analysis['language'] == Language.PYTHON.value
    assert len(analysis['relevant_patterns']) >= 2
    print(f"✓ Test 1 PASS: Python code analysis")
    print(f"  Detected: {analysis['language']}")
    print(f"  Patterns: {len(analysis['relevant_patterns'])}")
    
    # Test 2: Record decision
    decision = learner.record_decision(
        language=Language.PYTHON,
        framework=Framework.FASTAPI,
        pattern_type="async_handling",
        decision="Use async def for endpoint handlers",
        rationale="Allows concurrent request handling without blocking",
        code_snippet="@app.get('/data')\nasync def handler(): ...",
        affected_components=["api_layer", "database_layer"]
    )
    assert decision.framework == Framework.FASTAPI
    print(f"✓ Test 2 PASS: Decision recorded")
    print(f"  Total decisions: {learner.store.get_stats()['total_decisions']}")
    
    # Test 3: Get language guide
    guide = learner.get_language_guide(Language.PYTHON)
    assert guide['language'] == 'python'
    assert len(guide['features']) >= 3
    print(f"✓ Test 3 PASS: Got language guide")
    print(f"  Python has {len(guide['features'])} documented features")


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 3: LANGUAGE & FRAMEWORK LEARNING ENGINE - TEST")
    print("=" * 80)
    
    print("\n[Test Suite 1] Language Detection")
    print("-" * 80)
    test_language_detection()
    
    print("\n[Test Suite 2] Language Patterns")
    print("-" * 80)
    test_language_patterns()
    
    print("\n[Test Suite 3] Learner API")
    print("-" * 80)
    test_learner()
    
    print("\n" + "=" * 80)
    print("PHASE 3 TESTS PASSED")
    print("=" * 80)
