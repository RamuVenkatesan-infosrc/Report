"""
AI-powered recommendation engine using AWS Bedrock for code analysis and suggestions.
"""
import json
import logging
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from app.models.improvement_models import (
    DetailedAnalysisResult, ProactiveRecommendation, CodeImprovement,
    APIPerformanceProfile, DiscoveredAPI, RootCauseAnalysis, CodeQualityIssue
)
from .diff_analyzer import DiffAnalyzer
from app.services.bedrock_service import BedrockService
from app.models.config import Settings
from app.utils.json_parser import parse_ai_json_response

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
            
            # Validate code snippet quality
            code_snippet = source_api.code_snippet or ""
            if not code_snippet or len(code_snippet.strip()) == 0:
                logger.warning(f"Empty code snippet for {performance_api.endpoint} - cannot generate meaningful suggestions")
                return {"improvements": []}
            
            # Check if code snippet looks complete (has function definition)
            has_function_def = bool(re.search(r'\b(def|async def|function|const\s+\w+\s*=\s*(\(|function)|export\s+(function|const)|public\s+\w+\s+\w+\s*\()', code_snippet, re.IGNORECASE))
            if not has_function_def and len(code_snippet.strip()) < 200:
                logger.warning(f"Code snippet appears incomplete for {performance_api.endpoint} ({len(code_snippet)} chars, no function def found)")
                # Still try to use it, but log the issue
            
            # Escape JSON special characters in code snippet for prompt
            escaped_code = code_snippet.replace('{', '{{').replace('}', '}}')
            
            # Create a comprehensive prompt for code quality improvements
            prompt = f"""Analyze this API function and provide ONE specific performance improvement with complete corrected code.

PERFORMANCE ISSUES:
- Response Time: {performance_api.avg_response_time_ms}ms (SLOW - needs optimization)
- Error Rate: {performance_api.error_rate_percent}%
- Throughput: {performance_api.throughput_rps} RPS
- 95th Percentile: {performance_api.percentile_95_latency_ms}ms

FUNCTION CODE:
{code_snippet}

TASK: Analyze the code above and identify WHY it's slow ({performance_api.avg_response_time_ms}ms). Then provide the COMPLETE corrected function code that fixes the performance issue.

REQUIREMENTS:
1. improved_code must be the COMPLETE function (from decorator to end) with actual optimizations applied
2. NO import statements - only the function code itself
3. Show REAL code changes: add timeouts, async/await, connection pooling, caching, query optimization, error handling, etc.
4. The improved code should directly address the {performance_api.avg_response_time_ms}ms response time issue

RETURN ONLY THIS JSON (no markdown, no explanations):
{{
  "improvements": [
    {{
      "title": "Specific fix title",
      "description": "What's wrong and how the fix addresses {performance_api.avg_response_time_ms}ms latency",
      "current_code": "{escaped_code}",
      "improved_code": "COMPLETE function code with optimizations applied - decorator, function definition, and all code",
      "expected_improvement": "Expected performance gain explanation"
    }}
  ]
}}

CRITICAL: Return ONLY valid JSON. improved_code must show the actual optimized function implementation."""
            
            try:
                response = self.bedrock_service.generate_summary_from_prompt(prompt)
            except RuntimeError as bedrock_error:
                # Bedrock failed - log detailed error and return empty
                logger.error(
                    f"❌ BEDROCK FAILED for {performance_api.endpoint}: {bedrock_error}",
                    exc_info=True
                )
                logger.error(
                    f"Bedrock error details for {performance_api.endpoint}:\n"
                    f"  - Error: {bedrock_error}\n"
                    f"  - Check CloudWatch logs for full stack trace\n"
                    f"  - Verify Lambda IAM role has bedrock:InvokeModel permission\n"
                    f"  - Verify Bedrock model access is enabled in AWS console\n"
                    f"  - Check ENABLE_BEDROCK environment variable is 'true'\n"
                    f"  - Verify region {self.settings.aws_region} supports Bedrock"
                )
                return {"improvements": []}
            
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
                    
                    # Convert improvements to expected format and filter trivial ones
                    improvements = analysis.get('improvements', [])
                    converted_improvements = []
                    
                    for imp in improvements:
                        current_code = imp.get('current_code', '').strip()
                        improved_code = imp.get('improved_code', '').strip()
                        
                        # Validate that we have both codes
                        if not current_code or not improved_code:
                            logger.warning(f"Suggestion missing code for {performance_api.endpoint}")
                            continue
                        
                        # Remove import statements from improved_code
                        improved_code_clean = self._remove_imports(improved_code)
                        
                        # Also remove imports from current_code for fair comparison
                        current_code_clean = self._remove_imports(current_code)
                        
                        # Filter out trivial suggestions (just imports, comments, or minimal changes)
                        if self._is_trivial_suggestion(current_code_clean, improved_code_clean):
                            logger.warning(f"Skipping trivial suggestion for {performance_api.endpoint}: only imports/comments/minor changes")
                            continue
                        
                        # Validate that improved_code has the function definition
                        if not re.search(r'\b(def|async def|function|@router\.|@app\.)', improved_code_clean, re.IGNORECASE):
                            logger.warning(f"Improved code missing function definition for {performance_api.endpoint}")
                            continue
                        
                        converted_improvements.append({
                            'priority': 'HIGH',
                            'category': 'code_quality',
                            'title': imp.get('title', 'Code Improvement'),
                            'description': imp.get('description', ''),
                            'current_code': current_code_clean,
                            'improved_code': improved_code_clean,
                            'expected_improvement': imp.get('expected_improvement', '')
                        })
                    
                    # If all suggestions were filtered out, return empty
                    if not converted_improvements:
                        logger.warning(f"All AI suggestions were filtered out for {performance_api.endpoint} - no valid suggestions available")
                        return {"improvements": []}
                    
                    analysis['improvements'] = converted_improvements
                    analysis['root_causes'] = []  # Not needed
                    analysis['code_quality_issues'] = []  # Not needed
                    
                    logger.info(f"✅ Successfully parsed AI analysis with {len(improvements)} improvements from Bedrock")
                    return analysis
                    
                except json.JSONDecodeError as je:
                    logger.error(f"JSON decode error for {performance_api.endpoint}: {je}")
                    logger.debug(f"Response preview: {response[:500]}")
                    logger.warning(f"Bedrock returned invalid JSON for {performance_api.endpoint} - no suggestions available")
                    return {"improvements": []}
                except Exception as e:
                    logger.error(f"Error parsing AI response for {performance_api.endpoint}: {e}")
                    logger.warning(f"Failed to parse Bedrock response for {performance_api.endpoint} - no suggestions available")
                    return {"improvements": []}
            else:
                logger.warning(f"Empty AI response for {performance_api.endpoint} from Bedrock - no suggestions available")
                return {"improvements": []}
                
        except Exception as e:
            logger.error(f"❌ Unexpected error generating AI analysis for {performance_api.endpoint}: {type(e).__name__}: {e}", exc_info=True)
            logger.warning(f"Unexpected error for {performance_api.endpoint} - no suggestions available")
            return {"improvements": []}
    
    def _remove_imports(self, code: str) -> str:
        """Remove all import statements from code, keeping only the function code."""
        if not code:
            return code
        
        lines = code.split('\n')
        filtered_lines = []
        in_multiline_string = False
        string_char = None
        
        for line in lines:
            # Track if we're in a multiline string
            stripped = line.strip()
            
            # Check for triple quotes (multiline strings)
            if '"""' in line or "'''" in line:
                # Count occurrences
                triple_double = line.count('"""')
                triple_single = line.count("'''")
                
                # If odd number, we're entering/exiting a multiline string
                if triple_double % 2 == 1:
                    in_multiline_string = not in_multiline_string
                    string_char = '"'
                elif triple_single % 2 == 1:
                    in_multiline_string = not in_multiline_string
                    string_char = "'"
                
                if not in_multiline_string:
                    # Not in string, check if it's an import
                    is_import = stripped.startswith('import ') or (stripped.startswith('from ') and ' import ' in stripped)
                    if not is_import:
                        filtered_lines.append(line)
                else:
                    # In multiline string, keep the line
                    filtered_lines.append(line)
                continue
            
            # If we're in a multiline string, keep the line
            if in_multiline_string:
                filtered_lines.append(line)
                continue
            
            # Skip import statements (but keep them if they're in strings/comments)
            is_import = stripped.startswith('import ') or (stripped.startswith('from ') and ' import ' in stripped)
            if is_import:
                # Skip this line
                continue
            
            # Keep all other lines
            filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines)
        # Clean up multiple consecutive empty lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()
    
    def _is_trivial_suggestion(self, current_code: str, improved_code: str) -> bool:
        """Check if a suggestion is trivial (just imports, comments, or minimal changes)."""
        if not current_code or not improved_code:
            return True
        
        # Remove whitespace and comments for comparison
        def normalize_code(code: str) -> str:
            # Remove comments
            lines = code.split('\n')
            code_lines = []
            for line in lines:
                # Remove single-line comments (but keep strings)
                if '#' in line:
                    # Check if # is in a string
                    in_string = False
                    quote_char = None
                    comment_idx = -1
                    for i, char in enumerate(line):
                        if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                            if not in_string:
                                in_string = True
                                quote_char = char
                            elif char == quote_char:
                                in_string = False
                        elif char == '#' and not in_string:
                            comment_idx = i
                            break
                    if comment_idx > 0:
                        line = line[:comment_idx]
                code_lines.append(line)
            
            # Join and remove extra whitespace
            normalized = '\n'.join(code_lines)
            # Remove import statements for comparison
            normalized = re.sub(r'^import\s+\w+.*$', '', normalized, flags=re.MULTILINE)
            normalized = re.sub(r'^from\s+\w+.*$', '', normalized, flags=re.MULTILINE)
            # Remove empty lines and normalize whitespace
            normalized = '\n'.join(line.strip() for line in normalized.split('\n') if line.strip())
            return normalized.lower()
        
        current_norm = normalize_code(current_code)
        improved_norm = normalize_code(improved_code)
        
        # If normalized codes are too similar (less than 10% difference), it's trivial
        if not current_norm or not improved_norm:
            return True
        
        # Calculate similarity
        similarity = SequenceMatcher(None, current_norm, improved_norm).ratio()
        if similarity > 0.95:  # More than 95% similar
            return True
        
        # Check if only imports were added
        current_lines = set(current_code.split('\n'))
        improved_lines = set(improved_code.split('\n'))
        added_lines = improved_lines - current_lines
        
        # If only imports or comments were added
        only_imports_or_comments = all(
            line.strip().startswith(('import ', 'from ')) or 
            line.strip().startswith('#') or 
            not line.strip()
            for line in added_lines
        )
        
        if only_imports_or_comments and len(added_lines) < len(current_lines.split('\n')) * 0.1:
            return True
        
        return False
    
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
                from app.models.improvement_models import PriorityLevel, IssueCategory
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
