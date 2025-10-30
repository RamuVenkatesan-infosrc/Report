"""
Deep code analysis engine for identifying performance issues and improvements.
"""
import re
import ast
import logging
from typing import List, Dict, Any, Optional, Tuple
from models.improvement_models import (
    RootCauseAnalysis, CodeQualityIssue, CodeImprovement, 
    IssueCategory, SeverityLevel, PriorityLevel, APIPerformanceProfile
)

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Engine for deep analysis of source code to identify issues and improvements."""
    
    def __init__(self):
        self.performance_patterns = {
            'n_plus_one': [
                r'for\s+\w+\s+in\s+\w+:\s*\n.*db\.query',
                r'for\s+\w+\s+in\s+\w+:\s*\n.*\.filter',
                r'for\s+\w+\s+in\s+\w+:\s*\n.*\.get'
            ],
            'missing_caching': [
                r'cache\.get\(',
                r'redis\.get\(',
                r'@cache'
            ],
            'heavy_queries': [
                r'\.all\(\)',
                r'\.filter\(.*\)\.all\(\)',
                r'SELECT\s+\*\s+FROM',
                r'\.query\(.*\)\.all\(\)'
            ],
            'no_validation': [
                r'BaseModel',
                r'@validator',
                r'validate_',
                r'pydantic'
            ],
            'poor_error_handling': [
                r'except\s*:',
                r'except\s+Exception\s*:',
                r'pass\s*$'
            ]
        }
    
    def analyze_matched_api(self, performance_api: APIPerformanceProfile, 
                           source_code: str, file_path: str) -> Dict[str, Any]:
        """Perform deep analysis of a matched API."""
        analysis = {
            'root_causes': self._identify_root_causes(performance_api, source_code, file_path),
            'code_quality_issues': self._identify_code_quality_issues(source_code, file_path),
            'improvements': self._generate_improvements(performance_api, source_code, file_path)
        }
        
        return analysis
    
    def analyze_discovered_api(self, discovered_api) -> Dict[str, Any]:
        """Analyze a discovered API for potential issues."""
        analysis = {
            'potential_issues': self._analyze_potential_issues(discovered_api),
            'risk_assessment': self._assess_risk_level(discovered_api),
            'improvement_suggestions': self._suggest_improvements(discovered_api)
        }
        
        return analysis
    
    def _identify_root_causes(self, performance_api: APIPerformanceProfile, 
                             source_code: str, file_path: str) -> List[RootCauseAnalysis]:
        """Identify root causes of performance issues."""
        root_causes = []
        
        # Analyze response time issues
        if performance_api.avg_response_time_ms > 1000:
            root_causes.extend(self._analyze_response_time_issues(source_code, file_path))
        
        # Analyze error rate issues
        if performance_api.error_rate_percent > 5:
            root_causes.extend(self._analyze_error_rate_issues(source_code, file_path))
        
        # Analyze throughput issues
        if performance_api.throughput_rps < 100:
            root_causes.extend(self._analyze_throughput_issues(source_code, file_path))
        
        return root_causes
    
    def _analyze_response_time_issues(self, source_code: str, file_path: str) -> List[RootCauseAnalysis]:
        """Analyze issues causing slow response times."""
        issues = []
        
        # Check for N+1 query problems
        if self._has_n_plus_one_queries(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.DATABASE_OPTIMIZATION,
                severity=SeverityLevel.HIGH,
                description="N+1 query problem detected - multiple database queries in loop",
                evidence=f"Found loop with database queries in {file_path}",
                impact_percentage=80.0,
                code_location=file_path
            ))
        
        # Check for missing caching
        if not self._has_caching(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.CACHING,
                severity=SeverityLevel.MEDIUM,
                description="No caching implementation found",
                evidence=f"No cache.get() or cache.set() calls in {file_path}",
                impact_percentage=60.0,
                code_location=file_path
            ))
        
        # Check for heavy database queries
        if self._has_heavy_queries(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.DATABASE_OPTIMIZATION,
                severity=SeverityLevel.MEDIUM,
                description="Heavy database queries without optimization",
                evidence=f"Found .all() queries without proper filtering in {file_path}",
                impact_percentage=40.0,
                code_location=file_path
            ))
        
        return issues
    
    def _analyze_error_rate_issues(self, source_code: str, file_path: str) -> List[RootCauseAnalysis]:
        """Analyze issues causing high error rates."""
        issues = []
        
        # Check for missing validation
        if not self._has_validation(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.VALIDATION,
                severity=SeverityLevel.MEDIUM,
                description="Missing input validation",
                evidence=f"No Pydantic models or validation found in {file_path}",
                impact_percentage=30.0,
                code_location=file_path
            ))
        
        # Check for poor error handling
        if self._has_poor_error_handling(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.ERROR_HANDLING,
                severity=SeverityLevel.HIGH,
                description="Poor error handling with generic exceptions",
                evidence=f"Found bare except clauses in {file_path}",
                impact_percentage=50.0,
                code_location=file_path
            ))
        
        return issues
    
    def _analyze_throughput_issues(self, source_code: str, file_path: str) -> List[RootCauseAnalysis]:
        """Analyze issues causing low throughput."""
        issues = []
        
        # Check for synchronous operations in async context
        if self._has_sync_in_async(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.ALGORITHM_OPTIMIZATION,
                severity=SeverityLevel.MEDIUM,
                description="Synchronous operations in async context",
                evidence=f"Found blocking operations in async function in {file_path}",
                impact_percentage=35.0,
                code_location=file_path
            ))
        
        # Check for inefficient algorithms
        if self._has_inefficient_algorithms(source_code):
            issues.append(RootCauseAnalysis(
                category=IssueCategory.ALGORITHM_OPTIMIZATION,
                severity=SeverityLevel.LOW,
                description="Inefficient algorithms detected",
                evidence=f"Found O(n²) operations in {file_path}",
                impact_percentage=20.0,
                code_location=file_path
            ))
        
        return issues
    
    def _identify_code_quality_issues(self, source_code: str, file_path: str) -> List[CodeQualityIssue]:
        """Identify code quality issues."""
        issues = []
        
        # Check function complexity
        complexity = self._calculate_cyclomatic_complexity(source_code)
        if complexity > 10:
            issues.append(CodeQualityIssue(
                type="complexity",
                description=f"Function complexity too high (cyclomatic complexity: {complexity})",
                file=file_path,
                line=self._find_function_start_line(source_code),
                suggestion="Break down into smaller functions",
                severity=SeverityLevel.MEDIUM
            ))
        
        # Check for long functions
        lines = source_code.split('\n')
        if len(lines) > 50:
            issues.append(CodeQualityIssue(
                type="length",
                description=f"Function too long ({len(lines)} lines)",
                file=file_path,
                line=1,
                suggestion="Split into smaller, focused functions",
                severity=SeverityLevel.LOW
            ))
        
        # Check for magic numbers
        magic_numbers = self._find_magic_numbers(source_code)
        if magic_numbers:
            issues.append(CodeQualityIssue(
                type="magic_numbers",
                description=f"Magic numbers found: {magic_numbers}",
                file=file_path,
                line=1,
                suggestion="Define constants for magic numbers",
                severity=SeverityLevel.LOW
            ))
        
        return issues
    
    def _generate_improvements(self, performance_api: APIPerformanceProfile, 
                              source_code: str, file_path: str) -> List[CodeImprovement]:
        """Generate specific code improvements."""
        improvements = []
        
        # Generate improvements based on root causes
        root_causes = self._identify_root_causes(performance_api, source_code, file_path)
        
        for cause in root_causes:
            if cause.category == IssueCategory.DATABASE_OPTIMIZATION:
                improvements.append(self._create_database_improvement(cause, source_code))
            elif cause.category == IssueCategory.CACHING:
                improvements.append(self._create_caching_improvement(cause, source_code))
            elif cause.category == IssueCategory.VALIDATION:
                improvements.append(self._create_validation_improvement(cause, source_code))
            elif cause.category == IssueCategory.ERROR_HANDLING:
                improvements.append(self._create_error_handling_improvement(cause, source_code))
        
        return improvements
    
    def _create_database_improvement(self, cause: RootCauseAnalysis, source_code: str) -> CodeImprovement:
        """Create database optimization improvement."""
        if "N+1" in cause.description:
            return CodeImprovement(
                priority=PriorityLevel.HIGH,
                category=IssueCategory.DATABASE_OPTIMIZATION,
                title="Fix N+1 Query Problem",
                description="Replace individual database queries with single optimized query",
                current_code=self._extract_n_plus_one_code(source_code),
                improved_code=self._generate_optimized_query_code(source_code),
                expected_improvement="Reduce response time by 70%",
                implementation_effort="LOW",
                testing_required="Update unit tests for batch query"
            )
        else:
            return CodeImprovement(
                priority=PriorityLevel.MEDIUM,
                category=IssueCategory.DATABASE_OPTIMIZATION,
                title="Optimize Database Queries",
                description="Add proper filtering and indexing to database queries",
                current_code="db.query(Model).all()",
                improved_code="db.query(Model).filter(Model.status == 'active').all()",
                expected_improvement="Reduce query time by 50%",
                implementation_effort="MEDIUM",
                testing_required="Add database performance tests"
            )
    
    def _create_caching_improvement(self, cause: RootCauseAnalysis, source_code: str) -> CodeImprovement:
        """Create caching improvement."""
        return CodeImprovement(
            priority=PriorityLevel.MEDIUM,
            category=IssueCategory.CACHING,
            title="Implement Redis Caching",
            description="Add caching for frequently accessed data",
            current_code=self._extract_function_code(source_code),
            improved_code=self._generate_cached_code(source_code),
            expected_improvement="Reduce response time by 60% for cached requests",
            implementation_effort="MEDIUM",
            testing_required="Add cache integration tests"
        )
    
    def _create_validation_improvement(self, cause: RootCauseAnalysis, source_code: str) -> CodeImprovement:
        """Create validation improvement."""
        return CodeImprovement(
            priority=PriorityLevel.LOW,
            category=IssueCategory.VALIDATION,
            title="Add Input Validation",
            description="Implement Pydantic models for request validation",
            current_code="def get_user(user_id: int):",
            improved_code="""class UserRequest(BaseModel):
    user_id: int = Field(..., gt=0, description="User ID must be positive")

def get_user(request: UserRequest):""",
            expected_improvement="Reduce error rate by 5% through better validation",
            implementation_effort="LOW",
            testing_required="Add validation test cases"
        )
    
    def _create_error_handling_improvement(self, cause: RootCauseAnalysis, source_code: str) -> CodeImprovement:
        """Create error handling improvement."""
        return CodeImprovement(
            priority=PriorityLevel.MEDIUM,
            category=IssueCategory.ERROR_HANDLING,
            title="Improve Error Handling",
            description="Replace generic exception handling with specific error types",
            current_code="except: pass",
            improved_code="""except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseError as e:
    raise HTTPException(status_code=500, detail="Database error")""",
            expected_improvement="Better error reporting and debugging",
            implementation_effort="MEDIUM",
            testing_required="Add error handling test cases"
        )
    
    # Helper methods for pattern detection
    def _has_n_plus_one_queries(self, source_code: str) -> bool:
        """Check if code has N+1 query problems."""
        for pattern in self.performance_patterns['n_plus_one']:
            if re.search(pattern, source_code, re.MULTILINE | re.DOTALL):
                return True
        return False
    
    def _has_caching(self, source_code: str) -> bool:
        """Check if code has caching implementation."""
        for pattern in self.performance_patterns['missing_caching']:
            if re.search(pattern, source_code, re.IGNORECASE):
                return True
        return False
    
    def _has_heavy_queries(self, source_code: str) -> bool:
        """Check if code has heavy database queries."""
        for pattern in self.performance_patterns['heavy_queries']:
            if re.search(pattern, source_code, re.IGNORECASE):
                return True
        return False
    
    def _has_validation(self, source_code: str) -> bool:
        """Check if code has validation."""
        for pattern in self.performance_patterns['no_validation']:
            if re.search(pattern, source_code, re.IGNORECASE):
                return True
        return False
    
    def _has_poor_error_handling(self, source_code: str) -> bool:
        """Check if code has poor error handling."""
        for pattern in self.performance_patterns['poor_error_handling']:
            if re.search(pattern, source_code, re.MULTILINE):
                return True
        return False
    
    def _has_sync_in_async(self, source_code: str) -> bool:
        """Check if async function has synchronous operations."""
        return bool(re.search(r'async def.*\n(?!.*await)', source_code, re.MULTILINE))
    
    def _has_inefficient_algorithms(self, source_code: str) -> bool:
        """Check for inefficient algorithms."""
        # Simple check for nested loops
        return bool(re.search(r'for.*:\s*\n.*for.*:', source_code, re.MULTILINE))
    
    def _calculate_cyclomatic_complexity(self, source_code: str) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        # Count decision points
        complexity += len(re.findall(r'\bif\b', source_code))
        complexity += len(re.findall(r'\bfor\b', source_code))
        complexity += len(re.findall(r'\bwhile\b', source_code))
        complexity += len(re.findall(r'\btry\b', source_code))
        complexity += len(re.findall(r'\bexcept\b', source_code))
        complexity += len(re.findall(r'\band\b', source_code))
        complexity += len(re.findall(r'\bor\b', source_code))
        
        return complexity
    
    def _find_function_start_line(self, source_code: str) -> int:
        """Find the line number where function starts."""
        lines = source_code.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'\s*def\s+\w+', line):
                return i + 1
        return 1
    
    def _find_magic_numbers(self, source_code: str) -> List[str]:
        """Find magic numbers in code."""
        # Simple regex to find numbers that might be magic
        numbers = re.findall(r'\b\d{2,}\b', source_code)
        return [num for num in numbers if int(num) > 10]
    
    def _extract_n_plus_one_code(self, source_code: str) -> str:
        """Extract N+1 query code snippet."""
        for pattern in self.performance_patterns['n_plus_one']:
            match = re.search(pattern, source_code, re.MULTILINE | re.DOTALL)
            if match:
                return match.group(0)
        return "for item in items:\n    db.query(Model).filter(...)"
    
    def _extract_function_code(self, source_code: str) -> str:
        """Extract function code snippet."""
        lines = source_code.split('\n')
        start = 0
        for i, line in enumerate(lines):
            if re.match(r'\s*def\s+\w+', line):
                start = i
                break
        
        return '\n'.join(lines[start:start+10])
    
    def _generate_optimized_query_code(self, source_code: str) -> str:
        """Generate optimized query code."""
        return """# Optimized: Single query instead of N+1
item_ids = [item.id for item in items]
results = db.query(Model).filter(Model.id.in_(item_ids)).all()"""
    
    def _generate_cached_code(self, source_code: str) -> str:
        """Generate cached code."""
        return """# Add caching
cached_result = await cache.get(f"key:{param}")
if cached_result:
    return cached_result

result = expensive_operation()
await cache.set(f"key:{param}", result, 300)
return result"""
    
    def _analyze_potential_issues(self, discovered_api) -> List[str]:
        """Analyze potential issues in discovered API."""
        return discovered_api.potential_issues
    
    def _assess_risk_level(self, discovered_api) -> SeverityLevel:
        """Assess risk level of discovered API."""
        return discovered_api.risk_level
    
    def _suggest_improvements(self, discovered_api) -> List[CodeImprovement]:
        """Suggest improvements for discovered API."""
        improvements = []
        
        for issue in discovered_api.potential_issues:
            if issue == 'potential_n_plus_one_query':
                improvements.append(CodeImprovement(
                    priority=PriorityLevel.HIGH,
                    category=IssueCategory.DATABASE_OPTIMIZATION,
                    title="Prevent N+1 Query Problem",
                    description="Optimize database queries to prevent N+1 problem",
                    current_code=discovered_api.code_snippet,
                    improved_code="Use batch queries instead of loops",
                    expected_improvement="Prevent performance degradation",
                    implementation_effort="MEDIUM",
                    testing_required="Add performance tests"
                ))
            elif issue == 'no_caching':
                improvements.append(CodeImprovement(
                    priority=PriorityLevel.MEDIUM,
                    category=IssueCategory.CACHING,
                    title="Add Caching Strategy",
                    description="Implement caching for better performance",
                    current_code=discovered_api.code_snippet,
                    improved_code="Add Redis caching layer",
                    expected_improvement="Improve response times",
                    implementation_effort="MEDIUM",
                    testing_required="Add cache tests"
                ))
        
        return improvements