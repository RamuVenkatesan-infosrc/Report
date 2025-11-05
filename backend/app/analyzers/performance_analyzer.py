"""
Performance analysis logic for API performance data.
"""
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from app.models.schemas import PerformanceEntry, AnalysisResult, PerformanceAnalysis

logger = logging.getLogger(__name__)


def intelligent_api_categorization(apis: List[AnalysisResult]) -> tuple[List[AnalysisResult], List[AnalysisResult], List[AnalysisResult]]:
    """
    Intelligently categorize APIs into best and issues (worst + moderate) based on multiple performance factors.
    
    Args:
        apis: List of API analysis results sorted by performance score
        
    Returns:
        Tuple of (best_apis, issues_apis, []) - no moderate category
    """
    if not apis:
        return [], [], []
    
    # Calculate performance scores for each API
    api_scores = []
    for api in apis:
        score = calculate_performance_score(api)
        api_scores.append((api, score))
    
    # Sort by performance score (higher is better)
    api_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate percentiles for intelligent categorization
    scores = [score for _, score in api_scores]
    total_apis = len(scores)
    
    if total_apis <= 2:
        # For very few APIs, use simple ranking
        best_apis = [api for api, _ in api_scores[:1]]
        issues_apis = [api for api, _ in api_scores[1:]]
    else:
        # Use intelligent categorization - top 40% as best, rest as issues
        best_count = max(1, int(total_apis * 0.4))  # Top 40% as best
        
        best_apis = [api for api, _ in api_scores[:best_count]]
        issues_apis = [api for api, _ in api_scores[best_count:]]  # Rest as issues
    
    logger.info(f"AI Categorization: {len(best_apis)} best, {len(issues_apis)} issues")
    return best_apis, issues_apis, []  # No moderate category


def calculate_performance_score(api: AnalysisResult) -> float:
    """
    Calculate a comprehensive performance score for an API.
    Higher score = better performance.
    
    Args:
        api: API analysis result
        
    Returns:
        Performance score (0-100)
    """
    score = 100.0
    
    # Response time scoring (lower is better)
    if api.avg_response_time_ms <= 100:
        score += 20  # Excellent response time
    elif api.avg_response_time_ms <= 500:
        score += 10  # Good response time
    elif api.avg_response_time_ms <= 1000:
        score += 0   # Average response time
    elif api.avg_response_time_ms <= 2000:
        score -= 10  # Poor response time
    else:
        score -= 30  # Very poor response time
    
    # Error rate scoring (lower is better)
    if api.error_rate_percent <= 0.1:
        score += 20  # Excellent error rate
    elif api.error_rate_percent <= 1.0:
        score += 10  # Good error rate
    elif api.error_rate_percent <= 5.0:
        score += 0   # Average error rate
    elif api.error_rate_percent <= 10.0:
        score -= 10  # Poor error rate
    else:
        score -= 30  # Very poor error rate
    
    # Throughput scoring (higher is better)
    if api.throughput_rps >= 1000:
        score += 20  # Excellent throughput
    elif api.throughput_rps >= 500:
        score += 10  # Good throughput
    elif api.throughput_rps >= 100:
        score += 0   # Average throughput
    elif api.throughput_rps >= 50:
        score -= 10  # Poor throughput
    else:
        score -= 30  # Very poor throughput
    
    # 95th percentile latency scoring (lower is better)
    if api.percentile_95_latency_ms <= 200:
        score += 20  # Excellent latency
    elif api.percentile_95_latency_ms <= 500:
        score += 10  # Good latency
    elif api.percentile_95_latency_ms <= 1000:
        score += 0   # Average latency
    elif api.percentile_95_latency_ms <= 2000:
        score -= 10  # Poor latency
    else:
        score -= 30  # Very poor latency
    
    # Ensure score is within 0-100 range
    return max(0, min(100, score))


def analyze_performance(
    data: List[PerformanceEntry],
    response_time_good_threshold: Optional[float] = None,
    response_time_bad_threshold: Optional[float] = None,
    error_rate_good_threshold: Optional[float] = None,
    error_rate_bad_threshold: Optional[float] = None,
    throughput_good_threshold: Optional[float] = None,
    throughput_bad_threshold: Optional[float] = None,
    percentile_95_latency_good_threshold: Optional[float] = None,
    percentile_95_latency_bad_threshold: Optional[float] = None
) -> PerformanceAnalysis:
    """Analyze performance data to find best and worst APIs based on provided thresholds."""
    if not data:
        logger.warning("No data to analyze, returning default response")
        return PerformanceAnalysis(
            best_api=[],
            worst_api=[],
            details=[],
            overall_percentile_95_latency_ms=0
        )

    results = []
    response_times = [entry.response_time_ms for entry in data if entry.response_time_ms > 0]
    percentile_95_latency = np.percentile(response_times, 95) if response_times else 0
    logger.info(f"Calculated 95th percentile latency: {percentile_95_latency}ms")

    for entry in data:
        endpoint = entry.endpoint
        response_time = entry.response_time_ms
        error_rate = entry.error_rate_percent if entry.error_rate_percent is not None else (100.0 if entry.error else 0.0)
        throughput = entry.throughput_rps if entry.throughput_rps is not None else 0

        result = AnalysisResult(
            endpoint=endpoint,
            avg_response_time_ms=response_time,
            error_rate_percent=error_rate,
            throughput_rps=round(throughput, 2),
            percentile_95_latency_ms=percentile_95_latency
        )

        # Add "Good" and "Bad" flags for all metrics
        # Good thresholds: <= (response time, error rate, percentile) or >= (throughput)
        if response_time_good_threshold is not None:
            result.is_good_response_time = bool(response_time <= response_time_good_threshold)
            logger.debug(f"Response time {response_time}ms vs good threshold {response_time_good_threshold}ms: {result.is_good_response_time}")
        if response_time_bad_threshold is not None:
            result.is_bad_response_time = bool(response_time >= response_time_bad_threshold)
            logger.debug(f"Response time {response_time}ms vs bad threshold {response_time_bad_threshold}ms: {result.is_bad_response_time}")
        if error_rate_good_threshold is not None:
            result.is_good_error_rate = bool(error_rate <= error_rate_good_threshold)
        if error_rate_bad_threshold is not None:
            result.is_bad_error_rate = bool(error_rate >= error_rate_bad_threshold)
        if throughput_good_threshold is not None:
            result.is_good_throughput = bool(throughput >= throughput_good_threshold)
        if throughput_bad_threshold is not None:
            result.is_bad_throughput = bool(throughput <= throughput_bad_threshold)  # Fixed: bad throughput is <= threshold
        if percentile_95_latency_good_threshold is not None:
            result.is_good_percentile_95_latency = bool(percentile_95_latency <= percentile_95_latency_good_threshold)
        if percentile_95_latency_bad_threshold is not None:
            result.is_bad_percentile_95_latency = bool(percentile_95_latency >= percentile_95_latency_bad_threshold)

        if any(key in result.__dict__ for key in ["is_good_", "is_bad_"]):
            logger.debug(f"Processed entry: {endpoint}, Response Time: {response_time} ms, Error Rate: {error_rate}%, Bad Response: {result.is_bad_response_time}, Bad Error Rate: {result.is_bad_error_rate}")

        results.append(result)

    # Sort results by performance metrics
    sorted_results = sorted(results, key=lambda x: (x.avg_response_time_ms or float('inf'), x.error_rate_percent or float('inf'), -(x.throughput_rps or 0)))

    # Define metrics for easier iteration
    metrics_config = [
        ("response_time", response_time_good_threshold, response_time_bad_threshold),
        ("error_rate", error_rate_good_threshold, error_rate_bad_threshold),
        ("throughput", throughput_good_threshold, throughput_bad_threshold),
        ("percentile_95_latency", percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold)
    ]

    best_api_list = []
    worst_api_list = []
    details_list = []

    # If no thresholds provided, use AI-based intelligent categorization (best + issues only)
    if not any(threshold is not None for threshold in [
        response_time_good_threshold, response_time_bad_threshold,
        error_rate_good_threshold, error_rate_bad_threshold,
        throughput_good_threshold, throughput_bad_threshold,
        percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold
    ]):
        # Use AI-based intelligent categorization (best + issues only)
        best_api_list, issues_api_list, _ = intelligent_api_categorization(sorted_results)
        # Combine issues into worst_api_list for compatibility
        worst_api_list = issues_api_list
        details_list = []  # No moderate category
    else:
        # Use threshold-based categorization with unmatched conditions support
        moderate_api_list = []  # For unmatched conditions
        
        for api_result in sorted_results:
            meets_bad_criteria = False
            meets_good_criteria = False
            
            # Check if API meets any BAD threshold criteria
            if response_time_bad_threshold is not None and api_result.avg_response_time_ms >= response_time_bad_threshold:
                meets_bad_criteria = True
                logger.debug(f"API {api_result.endpoint} meets bad criteria: response_time {api_result.avg_response_time_ms}ms >= {response_time_bad_threshold}ms")
            
            if error_rate_bad_threshold is not None and api_result.error_rate_percent >= error_rate_bad_threshold:
                meets_bad_criteria = True
                logger.debug(f"API {api_result.endpoint} meets bad criteria: error_rate {api_result.error_rate_percent}% >= {error_rate_bad_threshold}%")
            
            if throughput_bad_threshold is not None and api_result.throughput_rps <= throughput_bad_threshold:
                meets_bad_criteria = True
                logger.debug(f"API {api_result.endpoint} meets bad criteria: throughput {api_result.throughput_rps} RPS <= {throughput_bad_threshold} RPS")
            
            if percentile_95_latency_bad_threshold is not None and api_result.percentile_95_latency_ms >= percentile_95_latency_bad_threshold:
                meets_bad_criteria = True
                logger.debug(f"API {api_result.endpoint} meets bad criteria: percentile_95 {api_result.percentile_95_latency_ms}ms >= {percentile_95_latency_bad_threshold}ms")
            
            # Check if API meets any GOOD threshold criteria
            if response_time_good_threshold is not None and api_result.avg_response_time_ms <= response_time_good_threshold:
                meets_good_criteria = True
                logger.debug(f"API {api_result.endpoint} meets good criteria: response_time {api_result.avg_response_time_ms}ms <= {response_time_good_threshold}ms")
            
            if error_rate_good_threshold is not None and api_result.error_rate_percent <= error_rate_good_threshold:
                meets_good_criteria = True
                logger.debug(f"API {api_result.endpoint} meets good criteria: error_rate {api_result.error_rate_percent}% <= {error_rate_good_threshold}%")
            
            if throughput_good_threshold is not None and api_result.throughput_rps >= throughput_good_threshold:
                meets_good_criteria = True
                logger.debug(f"API {api_result.endpoint} meets good criteria: throughput {api_result.throughput_rps} RPS >= {throughput_good_threshold} RPS")
            
            if percentile_95_latency_good_threshold is not None and api_result.percentile_95_latency_ms <= percentile_95_latency_good_threshold:
                meets_good_criteria = True
                logger.debug(f"API {api_result.endpoint} meets good criteria: percentile_95 {api_result.percentile_95_latency_ms}ms <= {percentile_95_latency_good_threshold}ms")
            
            # Categorize based on threshold results
            if meets_bad_criteria:
                worst_api_list.append(api_result)
                logger.debug(f"Added {api_result.endpoint} to issues APIs (meets bad criteria)")
            elif meets_good_criteria:
                best_api_list.append(api_result)
                logger.debug(f"Added {api_result.endpoint} to best APIs (meets good criteria)")
            else:
                # Check if both good and bad thresholds are set
                has_good_threshold = any([
                    response_time_good_threshold is not None,
                    error_rate_good_threshold is not None,
                    throughput_good_threshold is not None,
                    percentile_95_latency_good_threshold is not None
                ])
                has_bad_threshold = any([
                    response_time_bad_threshold is not None,
                    error_rate_bad_threshold is not None,
                    throughput_bad_threshold is not None,
                    percentile_95_latency_bad_threshold is not None
                ])
                
                if has_good_threshold and has_bad_threshold:
                    # Both thresholds set - unmatched condition
                    moderate_api_list.append(api_result)
                    logger.debug(f"Added {api_result.endpoint} to unmatched conditions (meets neither good nor bad criteria)")
                elif has_bad_threshold:
                    # Only bad threshold set - everything else goes to best
                    best_api_list.append(api_result)
                    logger.debug(f"Added {api_result.endpoint} to best APIs (doesn't meet bad criteria)")
                elif has_good_threshold:
                    # Only good threshold set - everything else goes to issues
                    worst_api_list.append(api_result)
                    logger.debug(f"Added {api_result.endpoint} to issues APIs (doesn't meet good criteria)")
                else:
                    # No thresholds set - this shouldn't happen in this branch
                    best_api_list.append(api_result)
                    logger.debug(f"Added {api_result.endpoint} to best APIs (no thresholds set)")

    # Check if thresholds are set
    has_good_threshold = any([
        response_time_good_threshold is not None,
        error_rate_good_threshold is not None,
        throughput_good_threshold is not None,
        percentile_95_latency_good_threshold is not None
    ])
    has_bad_threshold = any([
        response_time_bad_threshold is not None,
        error_rate_bad_threshold is not None,
        throughput_bad_threshold is not None,
        percentile_95_latency_bad_threshold is not None
    ])

    # Generate AI-powered insights
    # Use moderate_api_list as details_list when thresholds are used (for unmatched conditions)
    details_for_insights = moderate_api_list if any(threshold is not None for threshold in [
        response_time_good_threshold, response_time_bad_threshold,
        error_rate_good_threshold, error_rate_bad_threshold,
        throughput_good_threshold, throughput_bad_threshold,
        percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold
    ]) else details_list
    
    insights = generate_performance_insights(
        best_api_list, worst_api_list, details_for_insights, 
        percentile_95_latency, sorted_results, has_good_threshold, has_bad_threshold
    )

    # Use moderate_api_list as details when thresholds are used (for unmatched conditions)
    final_details = moderate_api_list if any(threshold is not None for threshold in [
        response_time_good_threshold, response_time_bad_threshold,
        error_rate_good_threshold, error_rate_bad_threshold,
        throughput_good_threshold, throughput_bad_threshold,
        percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold
    ]) else details_list

    return PerformanceAnalysis(
        best_api=best_api_list,
        worst_api=worst_api_list,
        details=final_details,
        overall_percentile_95_latency_ms=percentile_95_latency,
        insights=insights
    )


def generate_performance_insights(
    best_apis: List[AnalysisResult],
    worst_apis: List[AnalysisResult], 
    details_apis: List[AnalysisResult],
    overall_percentile_95: float,
    all_apis: List[AnalysisResult],
    has_good_threshold: bool = False,
    has_bad_threshold: bool = False
) -> Dict[str, Any]:
    """Generate AI-powered insights from performance analysis."""
    
    insights = {
        "summary": "",
        "recommendations": [],
        "key_metrics": {},
        "trends": {}
    }
    
    try:
        # Calculate key metrics
        total_apis = len(all_apis)
        avg_response_time = np.mean([api.avg_response_time_ms for api in all_apis]) if all_apis else 0
        avg_error_rate = np.mean([api.error_rate_percent for api in all_apis]) if all_apis else 0
        avg_throughput = np.mean([api.throughput_rps for api in all_apis]) if all_apis else 0
        
        insights["key_metrics"] = {
            "total_apis": total_apis,
            "best_performing": len(best_apis),
            "worst_performing": len(worst_apis),
            "moderate_performing": len(details_apis),
            "avg_response_time_ms": round(avg_response_time, 2),
            "avg_error_rate_percent": round(avg_error_rate, 2),
            "avg_throughput_rps": round(avg_throughput, 2),
            "overall_95th_percentile_ms": round(overall_percentile_95, 2)
        }
        
        # Only add unmatched_conditions count when both thresholds are set
        if has_good_threshold and has_bad_threshold:
            insights["key_metrics"]["unmatched_conditions"] = len(details_apis)
        
        # Add unmatched conditions details only when both thresholds are set
        insights["unmatched_conditions"] = []
        if has_good_threshold and has_bad_threshold:
            for api in details_apis:
                condition_info = {
                    "endpoint": api.endpoint,
                    "response_time_ms": api.avg_response_time_ms,
                    "error_rate_percent": api.error_rate_percent,
                    "throughput_rps": api.throughput_rps,
                    "percentile_95_latency_ms": api.percentile_95_latency_ms,
                    "reason": "Conditions not met - falls between good and bad thresholds"
                }
                insights["unmatched_conditions"].append(condition_info)
        
        # Generate AI-powered summary with threshold analysis
        insights["summary"] = f"AI Analysis of {total_apis} APIs: "
        
        if best_apis:
            best_endpoints = [api.endpoint for api in best_apis[:3]]
            insights["summary"] += f"{len(best_apis)} APIs meet performance thresholds (excellent): {', '.join(best_endpoints)}. "
        
        if worst_apis:
            worst_endpoints = [api.endpoint for api in worst_apis[:3]]
            insights["summary"] += f"{len(worst_apis)} APIs have critical issues: {', '.join(worst_endpoints)}. "
        
        if details_apis:
            details_endpoints = [api.endpoint for api in details_apis[:3]]
            if has_good_threshold and has_bad_threshold:
                insights["summary"] += f"{len(details_apis)} APIs have unmatched conditions (need attention): {', '.join(details_endpoints)}. "
            else:
                insights["summary"] += f"{len(details_apis)} APIs have moderate performance: {', '.join(details_endpoints)}. "
        
        # Add threshold-specific insights
        if len(best_apis) == 0 and len(worst_apis) == 0:
            insights["summary"] += "Consider adjusting thresholds - no APIs meet current criteria."
        elif len(best_apis) == total_apis:
            insights["summary"] += "All APIs exceed performance expectations - consider tightening thresholds."
        elif len(worst_apis) == total_apis:
            insights["summary"] += "All APIs have performance issues - consider relaxing thresholds or investigating system-wide problems."
        
        # Generate AI-powered recommendations
        recommendations = []
        
        # Threshold-specific recommendations
        if len(best_apis) == 0:
            recommendations.append("No APIs meet good thresholds - consider relaxing response time or error rate thresholds")
        elif len(best_apis) < total_apis * 0.2:
            recommendations.append("Very few APIs meet good thresholds - consider adjusting thresholds for better distribution")
        
        if len(worst_apis) > total_apis * 0.5:
            recommendations.append("Most APIs are in worst category - consider relaxing bad thresholds or investigating system issues")
        
        if len(details_apis) > total_apis * 0.6:
            recommendations.append("Many APIs fall between thresholds - consider adjusting good/bad threshold gap")
        
        # Performance-specific recommendations
        if worst_apis:
            # Check for common issues
            slow_apis = [api for api in worst_apis if api.avg_response_time_ms > 2000]
            high_error_apis = [api for api in worst_apis if api.error_rate_percent > 5]
            low_throughput_apis = [api for api in worst_apis if api.throughput_rps < 10]
            
            if slow_apis:
                recommendations.append(f"Optimize response times for {len(slow_apis)} slow APIs (avg > 2s)")
            if high_error_apis:
                recommendations.append(f"Investigate error rates for {len(high_error_apis)} APIs (error rate > 5%)")
            if low_throughput_apis:
                recommendations.append(f"Improve throughput for {len(low_throughput_apis)} low-performing APIs (< 10 RPS)")
        
        # AI threshold suggestions
        if all_apis:
            response_times = [api.avg_response_time_ms for api in all_apis]
            avg_response_time = np.mean(response_times)
            median_response_time = np.median(response_times)
            
            if avg_response_time < 100:
                recommendations.append(f"Average response time is {avg_response_time:.0f}ms - consider setting good threshold around {median_response_time:.0f}ms")
            elif avg_response_time > 1000:
                recommendations.append(f"Average response time is {avg_response_time:.0f}ms - consider setting good threshold around {median_response_time:.0f}ms")
        
        # Performance trends
        if len(all_apis) > 1:
            response_times = [api.avg_response_time_ms for api in all_apis]
            response_time_std = np.std(response_times)
            
            if response_time_std > avg_response_time * 0.5:
                recommendations.append("High response time variance detected - consider load balancing")
            
            if overall_percentile_95 > avg_response_time * 2:
                recommendations.append("95th percentile latency significantly higher than average - investigate outliers")
        
        insights["recommendations"] = recommendations
        
        # Performance trends
        insights["trends"] = {
            "response_time_consistency": "High" if response_time_std < avg_response_time * 0.3 else "Low",
            "error_rate_stability": "Stable" if avg_error_rate < 2 else "Concerning",
            "throughput_efficiency": "Good" if avg_throughput > 50 else "Needs Improvement"
        }
        
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        insights["summary"] = "Performance analysis completed with basic metrics."
        insights["recommendations"] = ["Review individual API performance metrics for detailed insights"]
    
    return insights