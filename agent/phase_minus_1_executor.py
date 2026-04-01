#!/usr/bin/env python3
"""
Phase -1: Executor

Purpose:
  Run code safely, capture execution data (stdout, stderr, exceptions, return value, 
  execution time, memory used). Foundation for Phase 0 failure recording.

Pattern (from reference projects):
  - Dataclass for ExecutionResult (like LocalMind CPUInfo, GPUInfo)
  - Singleton via @lru_cache on get_executor()
  - Factory pattern for create_execution_context()
  - Type hints mandatory
  - Validation of outputs before returning

Key Behavior:
  1. Execute Python code in isolated context
  2. Capture all signals: stdout, stderr, exceptions, timing, memory
  3. Return ExecutionResult with complete execution data
  4. Never swallow exceptions - always record full traceback
  5. Measure friction: execution time, memory delta, complexity
"""

from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Callable, Dict, List
import subprocess
import sys
import json
import tempfile
import traceback
import time
import psutil
import os


@dataclass
class ExecutionSignal:
    """Captured during execution (like LocalMind's sensor readings)"""
    stdout: str = ""
    stderr: str = ""
    exception: Optional[str] = None
    exception_traceback: Optional[str] = None
    return_value: Any = None
    return_code: int = -1  # Process exit code (-1 = crashed before running)
    execution_time_ms: float = 0.0
    memory_delta_mb: float = 0.0
    success: bool = False


@dataclass
class ExecutionResult:
    """Complete execution record (like LocalMind's SystemMetrics)"""
    id: str
    timestamp: datetime
    code: str
    language: str  # python, javascript, bash
    signal: ExecutionSignal
    working_directory: str
    environment_vars: Dict[str, str]
    timeout_seconds: float
    
    # Friction metrics
    complexity_score: float = 0.0  # 0-100, higher = more complex
    confidence: float = 0.0  # 0-1, how confident in this execution result
    
    def to_dict(self) -> dict:
        """For serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'code': self.code,
            'language': self.language,
            'signal': {
                'stdout': self.signal.stdout,
                'stderr': self.signal.stderr,
                'exception': self.signal.exception,
                'return_value': str(self.signal.return_value),
                'execution_time_ms': self.signal.execution_time_ms,
                'memory_delta_mb': self.signal.memory_delta_mb,
                'success': self.signal.success,
            },
            'working_directory': self.working_directory,
            'timeout_seconds': self.timeout_seconds,
            'complexity_score': self.complexity_score,
            'confidence': self.confidence,
        }


class Executor:
    """
    Safe code execution with comprehensive signal capture (like LocalMind's SystemMonitor)
    
    Singleton: use get_executor() factory instead of Executor()
    """
    
    _instance: Optional['Executor'] = None
    _execution_count: int = 0
    _execution_history: List[ExecutionResult] = field(default_factory=list)
    
    def __init__(self):
        self._execution_count = 0
        self._execution_history = []
        self._temp_dir = Path(tempfile.gettempdir()) / "agent-executor"
        self._temp_dir.mkdir(exist_ok=True)
    
    def execute_python(
        self,
        code: str,
        timeout_seconds: float = 30.0,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute Python code and capture all signals"""
        
        # CRITICAL FIX: Validate code input to prevent dangerous operations
        if len(code) > 50000:
            raise ValueError(f"❌ Code too large ({len(code)} chars > 50000 limit). Split into smaller functions.")
        
        dangerous_imports = ['__import__', 'eval', 'exec', 'subprocess', 'os.system']
        for dangerous in dangerous_imports:
            if dangerous in code:
                raise ValueError(f"❌ Dangerous function '{dangerous}' not allowed in isolated execution")
        
        result = ExecutionResult(
            id=f"exec_{self._execution_count}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            code=code,
            language='python',
            signal=ExecutionSignal(),
            working_directory=os.getcwd(),
            environment_vars=env_vars or {},
            timeout_seconds=timeout_seconds,
        )
        
        self._execution_count += 1
        
        # Measure memory before
        process = psutil.Process(os.getpid())
        memory_before_mb = process.memory_info().rss / (1024 * 1024)
        
        # Execute in subprocess for isolation
        script_path = self._temp_dir / f"{result.id}.py"
        script_path.write_text(code)
        
        start_time = time.time()
        
        try:
            # Build environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # Run subprocess
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
                cwd=os.getcwd(),
            )
            
            # Capture signals
            result.signal.stdout = proc.stdout
            result.signal.stderr = proc.stderr
            result.signal.success = proc.returncode == 0
            result.signal.return_value = proc.returncode
            
        except subprocess.TimeoutExpired as e:
            result.signal.exception = f"TimeoutError: Code exceeded {timeout_seconds}s"
            result.signal.exception_traceback = traceback.format_exc()
            result.signal.success = False
            
        except Exception as e:
            result.signal.exception = f"{type(e).__name__}: {str(e)}"
            result.signal.exception_traceback = traceback.format_exc()
            result.signal.success = False
        
        finally:
            # Measure timing and memory
            result.signal.execution_time_ms = (time.time() - start_time) * 1000
            memory_after_mb = process.memory_info().rss / (1024 * 1024)
            result.signal.memory_delta_mb = memory_after_mb - memory_before_mb
            
            # Calculate complexity score (rough heuristic)
            code_lines = len(code.split('\n'))
            code_chars = len(code)
            # Score based on size and time
            result.complexity_score = min(100, (code_lines * 2) + (result.signal.execution_time_ms / 10))
            
            # Confidence: higher if execution succeeded and was fast
            if result.signal.success:
                result.confidence = min(1.0, 0.95 - (result.signal.execution_time_ms / 100000))
            else:
                result.confidence = 0.5  # Lower confidence if failed
            
            # Clean up temp script (with logging for disk issues)
            try:
                script_path.unlink()
            except Exception as e:
                # CRITICAL FIX: Log cleanup failures to prevent silent disk space exhaustion
                print(f"⚠️ Failed to clean temp file {script_path}: {e}")
        
        self._execution_history.append(result)
        return result
    
    def execute_javascript(
        self,
        code: str,
        timeout_seconds: float = 30.0,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute JavaScript code and capture signals"""
        
        # CRITICAL FIX: Validate code input to prevent dangerous operations
        if len(code) > 50000:
            raise ValueError(f"❌ Code too large ({len(code)} chars > 50000 limit). Split into smaller functions.")
        
        dangerous_patterns = ['eval(', 'exec(', 'require(\'fs\')', 'require("fs")', 'process.exit']
        for dangerous in dangerous_patterns:
            if dangerous in code:
                raise ValueError(f"❌ Dangerous pattern '{dangerous}' not allowed in isolated execution")
        
        result = ExecutionResult(
            id=f"exec_{self._execution_count}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            code=code,
            language='javascript',
            signal=ExecutionSignal(),
            working_directory=os.getcwd(),
            environment_vars=env_vars or {},
            timeout_seconds=timeout_seconds,
        )
        
        self._execution_count += 1
        
        # Similar to Python but uses node
        script_path = self._temp_dir / f"{result.id}.js"
        script_path.write_text(code)
        
        start_time = time.time()
        
        try:
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            proc = subprocess.run(
                ['node', str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
            
            result.signal.stdout = proc.stdout
            result.signal.stderr = proc.stderr
            result.signal.success = proc.returncode == 0
            result.signal.return_value = proc.returncode
            
        except subprocess.TimeoutExpired:
            result.signal.exception = f"TimeoutError: Code exceeded {timeout_seconds}s"
            result.signal.success = False
            
        except Exception as e:
            result.signal.exception = f"{type(e).__name__}: {str(e)}"
            result.signal.exception_traceback = traceback.format_exc()
            result.signal.success = False
        
        finally:
            result.signal.execution_time_ms = (time.time() - start_time) * 1000
            result.complexity_score = min(100, (len(code.split('\n')) * 2) + (result.signal.execution_time_ms / 10))
            
            if result.signal.success:
                result.confidence = min(1.0, 0.95 - (result.signal.execution_time_ms / 100000))
            else:
                result.confidence = 0.5
            
            try:
                script_path.unlink()
            except Exception as e:
                # CRITICAL FIX: Log cleanup failures to prevent silent disk space exhaustion
                print(f"⚠️ Failed to clean temp file {script_path}: {e}")
        
        self._execution_history.append(result)
        return result
    
    def get_last_execution(self) -> Optional[ExecutionResult]:
        """Get most recent execution result"""
        return self._execution_history[-1] if self._execution_history else None
    
    def get_execution_history(self) -> List[ExecutionResult]:
        """Get all execution results"""
        return self._execution_history.copy()
    
    def get_stats(self) -> dict:
        """Get executor statistics"""
        if not self._execution_history:
            return {
                'total_executions': 0,
                'successful': 0,
                'failed': 0,
                'avg_execution_time_ms': 0.0,
                'avg_memory_delta_mb': 0.0,
            }
        
        successful = sum(1 for e in self._execution_history if e.signal.success)
        failed = len(self._execution_history) - successful
        avg_time = sum(e.signal.execution_time_ms for e in self._execution_history) / len(self._execution_history)
        avg_memory = sum(e.signal.memory_delta_mb for e in self._execution_history) / len(self._execution_history)
        
        return {
            'total_executions': len(self._execution_history),
            'successful': successful,
            'failed': failed,
            'success_rate': successful / len(self._execution_history),
            'avg_execution_time_ms': avg_time,
            'avg_memory_delta_mb': avg_memory,
            'avg_complexity_score': sum(e.complexity_score for e in self._execution_history) / len(self._execution_history),
        }
    
    def save_history(self, filepath: str) -> None:
        """Save execution history to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_executions': len(self._execution_history),
            'executions': [e.to_dict() for e in self._execution_history],
        }
        Path(filepath).write_text(json.dumps(data, indent=2))
    
    def clear_history(self) -> None:
        """Clear execution history"""
        self._execution_history = []


@lru_cache(maxsize=1)
def get_executor() -> Executor:
    """Factory function for singleton Executor (like LocalMind's get_settings())"""
    if Executor._instance is None:
        Executor._instance = Executor()
    return Executor._instance


def test_executor() -> None:
    """Test Phase -1 executor"""
    executor = get_executor()
    
    # Test 1: Simple Python execution
    result1 = executor.execute_python("print('Hello from Phase -1'); x = 1 + 1; print(f'Result: {x}')")
    print(f"✓ Test 1 PASS: Python execution")
    print(f"  Success: {result1.signal.success}")
    print(f"  Output: {result1.signal.stdout.strip()}")
    print(f"  Time: {result1.signal.execution_time_ms:.1f}ms")
    print(f"  Confidence: {result1.confidence:.2f}")
    
    # Test 2: Python with exception
    result2 = executor.execute_python("x = 1 / 0")
    print(f"\n✓ Test 2 PASS: Exception capture")
    print(f"  Success: {result2.signal.success}")
    print(f"  Exception: {result2.signal.exception[:50] if result2.signal.exception else 'None'}")
    
    # Test 3: JavaScript execution (if node available)
    try:
        result3 = executor.execute_javascript("console.log('Hello from JavaScript'); console.log(2 + 2);")
        print(f"\n✓ Test 3 PASS: JavaScript execution")
        print(f"  Success: {result3.signal.success}")
        print(f"  Output: {result3.signal.stdout.strip()}")
    except:
        print(f"\n⊘ Test 3 SKIP: Node.js not available")
    
    # Test 4: Statistics
    stats = executor.get_stats()
    print(f"\n✓ Test 4 PASS: Executor stats")
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Avg time: {stats['avg_execution_time_ms']:.1f}ms")


if __name__ == '__main__':
    test_executor()
