"""
Enhanced data models for API improvement analysis.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PriorityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueCategory(str, Enum):
    DATABASE_OPTIMIZATION = "database_optimization"
    CACHING = "caching"
    VALIDATION = "validation"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    ERROR_HANDLING = "error_handling"
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    MONITORING = "monitoring"


class APIPerformanceProfile(BaseModel):
    """Detailed performance profile for an API."""
    endpoint: str
    avg_response_time_ms: float
    error_rate_percent: float
    throughput_rps: float
    percentile_95_latency_ms: float
    issues: List[str] = []
    status: str = "UNKNOWN"


class SourceCodeMatch(BaseModel):
    """Match between performance API and source code."""
    repository: str
    file_path: str
    function_name: str
    match_confidence: float
    code_snippet: str
    framework: str
    line_numbers: Optional[List[int]] = None


class RootCauseAnalysis(BaseModel):
    """Root cause analysis for performance issues."""
    category: IssueCategory
    severity: SeverityLevel
    description: str
    evidence: str
    impact_percentage: float
    code_location: Optional[str] = None


class CodeQualityIssue(BaseModel):
    """Code quality issue found in source code."""
    type: str
    description: str
    file: str
    line: int
    suggestion: str
    severity: SeverityLevel


class CodeImprovement(BaseModel):
    """Specific code improvement suggestion."""
    priority: PriorityLevel
    category: IssueCategory
    title: str
    description: str
    current_code: str
    improved_code: str
    expected_improvement: str
    implementation_effort: str
    testing_required: str
    code_location: Optional[str] = None


class ImplementationPlan(BaseModel):
    """Implementation roadmap for improvements."""
    phase_1: List[str]
    phase_2: List[str]
    phase_3: List[str]
    estimated_total_effort: str
    expected_performance_gain: str


class DetailedAnalysisResult(BaseModel):
    """Complete analysis result for a matched API."""
    api_endpoint: str
    match_confidence: float
    performance_metrics: APIPerformanceProfile
    analysis: Dict[str, Any]
    root_causes: List[RootCauseAnalysis]
    code_quality_issues: List[CodeQualityIssue]
    improvements: List[CodeImprovement]
    implementation_plan: ImplementationPlan
    # Source API information
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    framework: Optional[str] = None
    complexity_score: Optional[float] = None
    risk_level: Optional[SeverityLevel] = None
    potential_issues: Optional[List[str]] = None
    code_snippet: Optional[str] = None
    line_number: Optional[int] = None


class DiscoveredAPI(BaseModel):
    """API discovered in source code."""
    endpoint: str
    file_path: str
    function_name: str
    framework: str
    complexity_score: float
    potential_issues: List[str]
    risk_level: SeverityLevel
    code_snippet: str
    line_number: Optional[int] = None


class ProactiveRecommendation(BaseModel):
    """Proactive recommendation for discovered APIs."""
    api_endpoint: str
    analysis_type: str = "proactive"
    risk_level: SeverityLevel
    potential_issues: List[str]
    recommendations: List[CodeImprovement]
    implementation_effort: str
    expected_impact: str


class MatchingResult(BaseModel):
    """Result of API matching process."""
    status: str  # "matches_found", "no_matches", "partial_matches"
    matched_apis: List[DetailedAnalysisResult] = []
    discovered_apis: List[DiscoveredAPI] = []
    proactive_recommendations: List[ProactiveRecommendation] = []
    unmatched_performance_apis: List[APIPerformanceProfile] = []
    unmatched_source_apis: List[DiscoveredAPI] = []


class MatchedAPIWithColor(BaseModel):
    """API match with color coding for frontend display."""
    api_endpoint: str
    match_confidence: float
    is_matched: bool  # True if this API has performance issues
    color_indicator: str  # "red", "green", "yellow", "gray"
    performance_metrics: APIPerformanceProfile
    source_code_info: Dict[str, Any]
    code_suggestions: List[CodeImprovement]
    performance_issues: List[str] = []


class RepositoryAnalysisResult(BaseModel):
    """Result of full repository analysis."""
    repository_info: Dict[str, Any]
    total_files_analyzed: int
    total_apis_discovered: int
    code_improvements: List[CodeImprovement]
    file_analysis: List[Dict[str, Any]]


class EnhancedAnalysisResponse(BaseModel):
    """Enhanced response for the analysis endpoint."""
    status: str
    analysis_type: str  # "reactive" or "proactive"
    matching_status: str
    total_apis_analyzed: int
    matched_apis_count: int
    discovered_apis_count: int
    high_risk_apis: int
    medium_risk_apis: int
    low_risk_apis: int
    results: MatchingResult
    summary: str
    implementation_roadmap: Optional[Dict[str, Any]] = None
