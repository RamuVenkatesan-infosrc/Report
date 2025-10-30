"""
AI-powered recommendation engine using AWS Bedrock for code analysis and suggestions.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from models.improvement_models import (
    DetailedAnalysisResult, ProactiveRecommendation, CodeImprovement,
    APIPerformanceProfile, DiscoveredAPI, RootCauseAnalysis, CodeQualityIssue
)
from .diff_analyzer import DiffAnalyzer
from services.bedrock_service import BedrockService
from models.config import Settings
from utils.json_parser import parse_ai_json_response

logger = logging.getLogger(__name__)


class AIGitHubAnalyzer:
    """AI-powered analyzer for GitHub repositories and API performance."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bedrock_service = BedrockService(settings)
        self.diff_analyzer = DiffAnalyzer()
    
    def analyze_matched_apis(self, matched_apis: List[DetailedAnalysisResult]) -> List[DetailedAnalysisResult]:
        """Analyze matched APIs and generate detailed recommendations."""
        detailed_results = []
        
        for match in matched_apis:
            # Extract performance API and source API from the match
            performance_api = match.performance_metrics
            confidence = match.match_confidence
            
            # Create a mock source API for compatibility
            mock_source_api = DiscoveredAPI(
                endpoint=match.api_endpoint,
                file_path=getattr(match, 'file_path', 'unknown'),
                function_name=getattr(match, 'function_name', 'unknown'),
                framework=getattr(match, 'framework', 'unknown'),
                complexity_score=getattr(match, 'complexity_score', 0.0),
                potential_issues=getattr(match, 'potential_issues', []),
                risk_level=getattr(match, 'risk_level', 'MEDIUM'),
                code_snippet=getattr(match, 'code_snippet', '')
            )
            
            # Generate AI analysis
            ai_analysis = self._generate_ai_analysis(performance_api, mock_source_api)
            
            # Create detailed analysis result with enhanced formatting
            detailed_result = DetailedAnalysisResult(
                api_endpoint=performance_api.endpoint,
                match_confidence=confidence,
                performance_metrics=performance_api,
                analysis=ai_analysis,
                root_causes=self._extract_root_causes(ai_analysis),
                code_quality_issues=self._extract_code_quality_issues(ai_analysis),
                improvements=self._extract_improvements(ai_analysis),
                implementation_plan=self._create_implementation_plan(ai_analysis)
            )
            
            detailed_results.append(detailed_result)
        
        return detailed_results
    
    def generate_diff_analysis(self, improvements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate diff analysis for code improvements."""
        return self.diff_analyzer.generate_improvement_diffs(improvements)
    
    def _get_code_quality_improvements(self, performance_api: APIPerformanceProfile, source_api: DiscoveredAPI) -> List[Dict[str, Any]]:
        """Return empty improvements - only AI suggestions allowed."""
        return []

    def _generate_ai_analysis(self, performance_api: APIPerformanceProfile, source_api: DiscoveredAPI) -> Dict[str, Any]:
        """Generate AI analysis for the API."""
        try:
            # Log the code snippet being analyzed
            logger.info(f"Generating AI analysis for API: {performance_api.endpoint}")
            logger.info(f"Code snippet length: {len(source_api.code_snippet)} chars")
            logger.info(f"Framework: {source_api.framework}, File: {source_api.file_path}")
            
            # Warn if code snippet is empty
            if not source_api.code_snippet or len(source_api.code_snippet.strip()) == 0:
                logger.warning(f"Empty code snippet for {performance_api.endpoint} - cannot generate meaningful suggestions")
                return self._get_fallback_analysis(performance_api, source_api)
            
            # Create a comprehensive prompt for code quality improvements
            prompt = f"""
You are an expert code reviewer. This API has performance issues. Analyze the code and provide ONE comprehensive improvement with complete corrected code.

PERFORMANCE DATA:
- Endpoint: {performance_api.endpoint}
- Response Time: {performance_api.avg_response_time_ms}ms (SLOW - needs optimization)
- Error Rate: {performance_api.error_rate_percent}%
- Throughput: {performance_api.throughput_rps} RPS (low)
- 95th Percentile Latency: {performance_api.percentile_95_latency_ms}ms

SOURCE CODE:
File: {source_api.file_path}
Function: {source_api.function_name}
Framework: {source_api.framework}

CODE TO ANALYZE:
```{source_api.framework or 'python'}
{source_api.code_snippet}
```

YOUR TASK:
Analyze this code and identify the performance bottleneck. Provide ONE comprehensive improvement with:
1. What's wrong with the current code
2. The COMPLETE corrected version of the code
3. Why this improves performance

REQUIREMENTS:
- Return ONLY valid JSON
- improved_code must be the FULL corrected function/code block
- No placeholder comments like "# Add error handling..."
- Show actual working code
- Fix the performance issue (slow response time)
- Address the root cause of slowness

RESPONSE FORMAT (JSON ONLY):
{{
  "improvements": [
    {{
      "title": "Brief title of the issue",
      "description": "Detailed explanation of the performance problem",
      "current_code": "{source_api.code_snippet}",
      "improved_code": "COMPLETE corrected code here - all the code with actual fixes applied",
      "expected_improvement": "What performance gain this provides"
    }}
  ]
}}

CRITICAL RULES:
1. improved_code must contain the COMPLETE corrected code - not snippets or comments
2. Apply ALL necessary fixes in the improved_code
3. No placeholders, no "TODO" comments - provide actual fixes
4. Return working, production-ready code
5. JSON only - no markdown, no explanations outside JSON
            """
            
            response = self.bedrock_service.generate_summary_from_prompt(prompt)
            
            if response and response.strip():
                try:
                    # Use the robust JSON parser to handle malformed responses
                    logger.debug(f"Raw AI response for {performance_api.endpoint}: {response[:200]}...")
                    
                    # Parse using the improved JSON parser
                    analysis = parse_ai_json_response(response)
                    
                    # Validate the structure
                    if not isinstance(analysis, dict):
                        raise ValueError("AI response is not a dictionary")
                    
                    # Ensure required keys exist with simplified structure
                    if 'improvements' not in analysis:
                        analysis['improvements'] = []
                    
                    # Convert simplified improvements to expected format
                    improvements = analysis.get('improvements', [])
                    converted_improvements = []
                    for imp in improvements:
                        converted_improvements.append({
                            'priority': 'HIGH',  # Default to HIGH for performance issues
                            'category': 'code_quality',  # Simplified category
                            'title': imp.get('title', 'Code Improvement'),
                            'description': imp.get('description', ''),
                            'current_code': imp.get('current_code', ''),
                            'improved_code': imp.get('improved_code', ''),
                            'expected_improvement': imp.get('expected_improvement', '')
                        })
                    
                    analysis['improvements'] = converted_improvements
                    analysis['root_causes'] = []  # Not needed
                    analysis['code_quality_issues'] = []  # Not needed
                    
                    logger.info(f"Successfully parsed AI analysis with {len(improvements)} improvements")
                    return analysis
                    
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decode error for {performance_api.endpoint}: {je}")
                    logger.debug(f"Response preview: {response[:500]}")
                    # If not JSON, use fallback analysis
                    return self._get_fallback_analysis(performance_api, source_api)
                except Exception as e:
                    logger.error(f"Error parsing AI response for {performance_api.endpoint}: {e}")
                    return self._get_fallback_analysis(performance_api, source_api)
            else:
                logger.warning(f"Empty AI response for {performance_api.endpoint}")
                return self._get_fallback_analysis(performance_api, source_api)
                
        except Exception as e:
            logger.error(f"Error generating AI analysis: {e}")
            return self._get_fallback_analysis(performance_api, source_api)
    
    def _get_fallback_analysis(self, performance_api: APIPerformanceProfile, source_api: DiscoveredAPI) -> Dict[str, Any]:
        """Return empty analysis when AI fails - no fallback suggestions."""
        return {
            "root_causes": [],
            "code_quality_issues": [],
            "improvements": [],
            "implementation_plan": {
                "phase_1": [],
                "phase_2": [],
                "phase_3": [],
                "estimated_total_effort": "N/A",
                "expected_performance_gain": "AI analysis required"
            }
        }
    
    def _extract_root_causes(self, ai_analysis: Dict[str, Any]) -> List[RootCauseAnalysis]:
        """Extract root causes from AI analysis."""
        root_causes = []
        
        for cause in ai_analysis.get('root_causes', []):
            root_causes.append(RootCauseAnalysis(
                category=cause.get('category', 'unknown'),
                severity=cause.get('severity', 'MEDIUM'),
                description=cause.get('description', ''),
                evidence=cause.get('evidence', ''),
                impact_percentage=cause.get('impact_percentage', 0.0)
            ))
        
        return root_causes
    
    def _extract_code_quality_issues(self, ai_analysis: Dict[str, Any]) -> List[CodeQualityIssue]:
        """Extract code quality issues from AI analysis."""
        issues = []
        
        for issue in ai_analysis.get('code_quality_issues', []):
            issues.append(CodeQualityIssue(
                type=issue.get('type', 'unknown'),
                severity=issue.get('severity', 'MEDIUM'),
                description=issue.get('description', ''),
                file=issue.get('file', ''),
                line=issue.get('line', 0),
                suggestion=issue.get('suggestion', '')
            ))
        
        return issues
    
    def _extract_improvements(self, ai_analysis: Dict[str, Any]) -> List[CodeImprovement]:
        """Extract improvements from AI analysis."""
        improvements = []
        
        for improvement in ai_analysis.get('improvements', []):
            # Handle both dictionary and string values for priority and category
            priority_str = improvement.get('priority', 'MEDIUM')
            category_str = improvement.get('category', 'code_quality')
            
            # Convert string to enum
            try:
                from models.improvement_models import PriorityLevel, IssueCategory
                priority = PriorityLevel(priority_str.lower()) if isinstance(priority_str, str) else priority_str
                category = IssueCategory(category_str.lower()) if isinstance(category_str, str) else category_str
            except (ValueError, AttributeError):
                # Fallback to default values if conversion fails
                priority = PriorityLevel.MEDIUM
                category = IssueCategory.CODE_QUALITY
            
            improvements.append(CodeImprovement(
                priority=priority,
                category=category,
                title=improvement.get('title', ''),
                description=improvement.get('description', ''),
                current_code=improvement.get('current_code', ''),
                improved_code=improvement.get('improved_code', ''),
                expected_improvement=improvement.get('expected_improvement', ''),
                implementation_effort=improvement.get('implementation_effort', 'MEDIUM'),
                testing_required=improvement.get('testing_required', '')
            ))
        
        return improvements
    
    def _create_implementation_plan(self, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create implementation plan from AI analysis."""
        return ai_analysis.get('implementation_plan', {
                "phase_1": ["Review current implementation"],
            "phase_2": ["Implement improvements"],
            "phase_3": ["Testing and optimization"],
            "estimated_total_effort": "1-2 days",
            "expected_performance_gain": "Significant improvement in code quality"
        })
