"""
Data models and schemas for the API Performance Analyzer.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PerformanceEntry(BaseModel):
    """Represents a single performance measurement entry."""
    endpoint: str
    response_time_ms: float
    success: bool
    error: bool
    error_rate_percent: Optional[float] = None
    throughput_rps: Optional[float] = None


class AnalysisResult(BaseModel):
    """Represents the result of performance analysis for a single endpoint."""
    endpoint: str
    avg_response_time_ms: float
    error_rate_percent: float
    throughput_rps: float
    percentile_95_latency_ms: float
    is_good_response_time: Optional[bool] = None
    is_bad_response_time: Optional[bool] = None
    is_good_error_rate: Optional[bool] = None
    is_bad_error_rate: Optional[bool] = None
    is_good_throughput: Optional[bool] = None
    is_bad_throughput: Optional[bool] = None
    is_good_percentile_95_latency: Optional[bool] = None
    is_bad_percentile_95_latency: Optional[bool] = None


class PerformanceAnalysis(BaseModel):
    """Represents the complete performance analysis results."""
    best_api: List[AnalysisResult]
    worst_api: List[AnalysisResult]
    details: List[AnalysisResult]
    overall_percentile_95_latency_ms: float
    insights: Optional[Dict[str, Any]] = None


class ThresholdsConfig(BaseModel):
    """Configuration for performance thresholds."""
    response_time_good_threshold: Optional[float] = Field(None, description="Maximum acceptable response time in ms for 'Good'")
    response_time_bad_threshold: Optional[float] = Field(None, description="Minimum response time in ms for 'Bad'")
    error_rate_good_threshold: Optional[float] = Field(None, description="Maximum acceptable error rate percentage for 'Good'")
    error_rate_bad_threshold: Optional[float] = Field(None, description="Minimum error rate percentage for 'Bad'")
    throughput_good_threshold: Optional[float] = Field(None, description="Minimum acceptable throughput (requests per second) for 'Good'")
    throughput_bad_threshold: Optional[float] = Field(None, description="Maximum throughput (requests per second) for 'Bad'")
    percentile_95_latency_good_threshold: Optional[float] = Field(None, description="Maximum acceptable 95th percentile latency in ms for 'Good'")
    percentile_95_latency_bad_threshold: Optional[float] = Field(None, description="Minimum 95th percentile latency in ms for 'Bad'")


class AnalysisResponse(BaseModel):
    """Response model for the analysis endpoint."""
    status: str
    analysis: PerformanceAnalysis
    summary: str
    processed_files: List[str]
    skipped_files: List[str]
    thresholds_used: Optional[ThresholdsConfig] = None


class FileProcessingResult(BaseModel):
    """Result of file processing operations."""
    data: List[PerformanceEntry]
    processed_files: List[str]
    skipped_files: List[str]
