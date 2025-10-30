"""
API matching engine for matching performance data with source code APIs.
"""
import re
import logging
from typing import List, Tuple, Dict, Any
from difflib import SequenceMatcher
from models.improvement_models import (
    APIPerformanceProfile, DiscoveredAPI, SourceCodeMatch, 
    MatchingResult, SeverityLevel, DetailedAnalysisResult, ImplementationPlan
)

logger = logging.getLogger(__name__)


class APIMatcher:
    """Engine for matching performance APIs with source code APIs."""
    
    def __init__(self, min_confidence_threshold: float = 0.3):
        self.min_confidence_threshold = min_confidence_threshold
    
    def match_apis_with_color_coding(self, performance_apis: List[APIPerformanceProfile], 
                                   source_apis: List[DiscoveredAPI]) -> List[Dict[str, Any]]:
        """Match performance APIs with source code APIs and add color coding."""
        logger.info(f"APIMatcher: Starting matching with {len(performance_apis)} performance APIs and {len(source_apis)} source APIs")
        matched_apis_with_colors = []
        
        for i, perf_api in enumerate(performance_apis):
            logger.info(f"APIMatcher: Processing performance API {i+1}: '{perf_api.endpoint}'")
            best_match = self._find_best_match(perf_api, source_apis)
            logger.info(f"APIMatcher: Best match for '{perf_api.endpoint}': {best_match[0].endpoint if best_match[0] else 'None'} (confidence: {best_match[1]:.2f})")
            
            if best_match and best_match[1] >= self.min_confidence_threshold:
                source_api, confidence = best_match
                logger.info(f"APIMatcher: Match found! '{perf_api.endpoint}' -> '{source_api.endpoint}' (confidence: {confidence:.2f})")
                
                # Determine if this API has performance issues
                has_performance_issues = self._has_performance_issues(perf_api)
                
                # Determine color indicator
                color_indicator = self._get_color_indicator(perf_api, has_performance_issues)
                
                # Get performance issues list
                performance_issues = self._get_performance_issues_list(perf_api)
                
                matched_api = {
                    "api_endpoint": source_api.endpoint,
                    "match_confidence": confidence,
                    "is_matched": has_performance_issues,
                    "color_indicator": color_indicator,
                    "performance_metrics": perf_api,
                    "source_code_info": {
                        "file_path": source_api.file_path,
                        "function_name": source_api.function_name,
                        "framework": source_api.framework,
                        "line_number": source_api.line_number,
                        "code_snippet": source_api.code_snippet,
                        "complexity_score": source_api.complexity_score,
                        "risk_level": source_api.risk_level.value if source_api.risk_level else "UNKNOWN"
                    },
                    "code_suggestions": [],  # Will be filled by AI analyzer
                    "performance_issues": performance_issues
                }
                
                matched_apis_with_colors.append(matched_api)
            else:
                logger.info(f"APIMatcher: No match found for '{perf_api.endpoint}' (confidence: {best_match[1]:.2f} < {self.min_confidence_threshold})")
        
        logger.info(f"APIMatcher: Total matches found: {len(matched_apis_with_colors)}")
        return matched_apis_with_colors
    
    def _has_performance_issues(self, perf_api: APIPerformanceProfile) -> bool:
        """Check if API has significant performance issues."""
        # Define thresholds for performance issues
        response_time_threshold = 1000  # ms
        error_rate_threshold = 5.0  # %
        throughput_threshold = 50  # RPS
        
        return (
            perf_api.avg_response_time_ms > response_time_threshold or
            perf_api.error_rate_percent > error_rate_threshold or
            perf_api.throughput_rps < throughput_threshold
        )
    
    def _get_color_indicator(self, perf_api: APIPerformanceProfile, has_issues: bool) -> str:
        """Get color indicator based on performance metrics."""
        if has_issues:
            return "red"  # Has performance issues
        else:
            return "green"  # No significant performance issues
    
    def _get_performance_issues_list(self, perf_api: APIPerformanceProfile) -> List[str]:
        """Get list of specific performance issues."""
        issues = []
        
        if perf_api.avg_response_time_ms > 1000:
            issues.append(f"High response time: {perf_api.avg_response_time_ms}ms")
        
        if perf_api.error_rate_percent > 5.0:
            issues.append(f"High error rate: {perf_api.error_rate_percent}%")
        
        if perf_api.throughput_rps < 50:
            issues.append(f"Low throughput: {perf_api.throughput_rps} RPS")
        
        if perf_api.percentile_95_latency_ms > 2000:
            issues.append(f"High 95th percentile latency: {perf_api.percentile_95_latency_ms}ms")
        
        return issues
    
    def match_apis(self, performance_apis: List[APIPerformanceProfile], 
                  source_apis: List[DiscoveredAPI]) -> MatchingResult:
        
        for perf_api in performance_apis:
            best_match = self._find_best_match(perf_api, source_apis)
            
            if best_match and best_match[1] >= self.min_confidence_threshold:
                # Create match
                source_api, confidence = best_match
                match = SourceCodeMatch(
                    repository="unknown",  # Will be filled by caller
                    file_path=source_api.file_path,
                    function_name=source_api.function_name,
                    match_confidence=confidence,
                    code_snippet=source_api.code_snippet,
                    framework=source_api.framework
                )
                
                # Create DetailedAnalysisResult object
                detailed_result = DetailedAnalysisResult(
                    api_endpoint=source_api.endpoint,
                    match_confidence=confidence,
                    performance_metrics=perf_api,
                    analysis={},  # Will be filled by caller
                    root_causes=[],  # Will be filled by caller
                    code_quality_issues=[],  # Will be filled by caller
                    improvements=[],  # Will be filled by caller
                    implementation_plan=ImplementationPlan(
                        phase_1=[],
                        phase_2=[],
                        phase_3=[],
                        estimated_total_effort="TBD",
                        expected_performance_gain="TBD"
                    ),
                    # Source API information
                    file_path=source_api.file_path,
                    function_name=source_api.function_name,
                    framework=source_api.framework,
                    complexity_score=source_api.complexity_score,
                    risk_level=source_api.risk_level,
                    potential_issues=source_api.potential_issues,
                    code_snippet=source_api.code_snippet,
                    line_number=source_api.line_number
                )
                
                matches.append(detailed_result)
                
                # Remove from unmatched
                if source_api in unmatched_source:
                    unmatched_source.remove(source_api)
            else:
                unmatched_performance.append(perf_api)
        
        # Determine status
        if len(matches) == 0:
            status = "no_matches"
        elif len(matches) == len(performance_apis):
            status = "full_matches"
        else:
            status = "partial_matches"
        
        return MatchingResult(
            status=status,
            matched_apis=matches,
            discovered_apis=unmatched_source,
            unmatched_performance_apis=unmatched_performance,
            unmatched_source_apis=unmatched_source
        )
    
    def _find_best_match(self, perf_api: APIPerformanceProfile, 
                        source_apis: List[DiscoveredAPI]) -> Tuple[DiscoveredAPI, float]:
        """Find the best matching source API for a performance API using enhanced matching."""
        best_match = None
        best_confidence = 0.0
        
        # Enhanced matching with multiple strategies
        for source_api in source_apis:
            # Calculate multiple confidence scores
            exact_match_score = self._calculate_exact_match_confidence(perf_api, source_api)
            fuzzy_match_score = self._calculate_fuzzy_match_confidence(perf_api, source_api)
            semantic_match_score = self._calculate_semantic_match_confidence(perf_api, source_api)
            framework_match_score = self._calculate_framework_match_confidence(perf_api, source_api)
            phrase_match_score = self._calculate_phrase_match_confidence(perf_api, source_api)
            
            # Weighted combination of all scores - heavily weighted toward phrase matching
            total_confidence = (
                exact_match_score * 0.1 +      # Exact matches are important
                fuzzy_match_score * 0.1 +      # Fuzzy matching for similar names
                semantic_match_score * 0.3 +   # Semantic similarity
                framework_match_score * 0.1 +  # Framework compatibility
                phrase_match_score * 0.4       # Phrase matching is most important
            )
            
            if total_confidence > best_confidence:
                best_confidence = total_confidence
                best_match = source_api
        
        return (best_match, best_confidence) if best_match else (None, 0.0)
    
    def _calculate_exact_match_confidence(self, perf_api: APIPerformanceProfile, 
                                        source_api: DiscoveredAPI) -> float:
        """Calculate exact match confidence."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Exact match
        if perf_endpoint == source_endpoint:
            return 1.0
        
        # Remove HTTP methods for comparison
        perf_clean = re.sub(r'^(get|post|put|delete|patch|head|options)\s+', '', perf_endpoint)
        source_clean = re.sub(r'^(get|post|put|delete|patch|head|options)\s+', '', source_endpoint)
        
        if perf_clean == source_clean:
            return 0.9
        
        return 0.0
    
    def _calculate_fuzzy_match_confidence(self, perf_api: APIPerformanceProfile, 
                                        source_api: DiscoveredAPI) -> float:
        """Calculate fuzzy match confidence using string similarity."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Remove HTTP methods for comparison
        perf_clean = re.sub(r'^(get|post|put|delete|patch|head|options)\s+', '', perf_endpoint)
        source_clean = re.sub(r'^(get|post|put|delete|patch|head|options)\s+', '', source_endpoint)
        
        # Normalize endpoints for better comparison
        perf_normalized = self._normalize_for_fuzzy_match(perf_clean)
        source_normalized = self._normalize_for_fuzzy_match(source_clean)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, perf_normalized, source_normalized).ratio()
        
        # Boost score for similar patterns
        if similarity > 0.8:
            return similarity
        elif similarity > 0.6:
            return similarity * 0.8
        else:
            return similarity * 0.5
    
    def _calculate_semantic_match_confidence(self, perf_api: APIPerformanceProfile, 
                                           source_api: DiscoveredAPI) -> float:
        """Calculate semantic match confidence based on meaning with enhanced fuzzy matching."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Remove common prefixes/suffixes for better matching
        perf_clean = self._clean_endpoint_for_matching(perf_endpoint)
        source_clean = self._clean_endpoint_for_matching(source_endpoint)
        
        # Calculate word-level similarity
        word_similarity = self._calculate_word_similarity(perf_clean, source_clean)
        
        # Calculate phrase-level similarity
        phrase_similarity = self._calculate_phrase_similarity(perf_clean, source_clean)
        
        # Calculate semantic similarity using synonyms
        semantic_similarity = self._calculate_semantic_similarity(perf_clean, source_clean)
        
        # Combine all similarity scores
        total_similarity = (word_similarity * 0.4 + phrase_similarity * 0.3 + semantic_similarity * 0.3)
        
        return min(total_similarity, 1.0)
    
    def _clean_endpoint_for_matching(self, endpoint: str) -> str:
        """Clean endpoint for better matching by removing common prefixes/suffixes."""
        # Remove HTTP methods
        endpoint = re.sub(r'^(get|post|put|delete|patch)\s+', '', endpoint)
        # Remove common prefixes
        endpoint = re.sub(r'^(api/|/api/)', '', endpoint)
        # Remove common suffixes
        endpoint = re.sub(r'(_list|_items|_data|_info|_details)$', '', endpoint)
        # Remove special characters except slashes and underscores
        endpoint = re.sub(r'[^\w\s/_-]', '', endpoint)
        # Normalize spaces
        endpoint = re.sub(r'\s+', ' ', endpoint).strip()
        return endpoint
    
    def _calculate_word_similarity(self, perf_endpoint: str, source_endpoint: str) -> float:
        """Calculate similarity based on individual words."""
        perf_words = set(perf_endpoint.split())
        source_words = set(source_endpoint.split())
        
        if not perf_words or not source_words:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = perf_words.intersection(source_words)
        union = perf_words.union(source_words)
        
        if not union:
            return 0.0
        
        base_similarity = len(intersection) / len(union)
        
        # Boost score for partial word matches
        partial_matches = 0
        for perf_word in perf_words:
            for source_word in source_words:
                if self._is_partial_match(perf_word, source_word):
                    partial_matches += 1
                    break
        
        partial_bonus = partial_matches * 0.1
        return min(base_similarity + partial_bonus, 1.0)
    
    def _is_partial_match(self, word1: str, word2: str) -> bool:
        """Check if two words are partial matches (one contains the other)."""
        if len(word1) < 3 or len(word2) < 3:
            return False
        return word1 in word2 or word2 in word1
    
    def _calculate_phrase_similarity(self, perf_endpoint: str, source_endpoint: str) -> float:
        """Calculate similarity based on phrase patterns."""
        # Handle common patterns with higher scores
        patterns = [
            (r'get\s+(.+)', r'/\1'),  # "get issues" -> "/issues"
            (r'(.+)\s+list', r'/\1'),  # "issues list" -> "/issues"
            (r'fetch\s+(.+)', r'/\1'),  # "fetch data" -> "/data"
            (r'retrieve\s+(.+)', r'/\1'),  # "retrieve users" -> "/users"
            (r'(.+)\s+data', r'/\1'),  # "user data" -> "/user"
            (r'(.+)\s+info', r'/\1'),  # "dashboard info" -> "/dashboard"
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, perf_endpoint):
                normalized_perf = re.sub(pattern, replacement, perf_endpoint)
                if normalized_perf in source_endpoint or source_endpoint in normalized_perf:
                    return 0.9
        
        # Handle reverse patterns (source -> performance)
        reverse_patterns = [
            (r'/(.+)', r'\1'),  # "/issues" -> "issues"
            (r'/(.+)', r'get \1'),  # "/issues" -> "get issues"
            (r'/(.+)', r'\1 list'),  # "/issues" -> "issues list"
        ]
        
        for pattern, replacement in reverse_patterns:
            if re.search(pattern, source_endpoint):
                normalized_source = re.sub(pattern, replacement, source_endpoint)
                if normalized_source in perf_endpoint or perf_endpoint in normalized_source:
                    return 0.8
        
        # Use SequenceMatcher for general phrase similarity
        similarity = SequenceMatcher(None, perf_endpoint, source_endpoint).ratio()
        
        # Boost score for partial matches
        if any(word in source_endpoint for word in perf_endpoint.split()):
            similarity = min(similarity + 0.2, 1.0)
        
        return similarity
    
    def _calculate_semantic_similarity(self, perf_endpoint: str, source_endpoint: str) -> float:
        """Calculate similarity using semantic word mappings."""
        # Enhanced semantic patterns with more comprehensive mappings
        semantic_patterns = {
            'get': ['fetch', 'retrieve', 'list', 'find', 'search', 'query', 'load', 'obtain', 'show', 'display'],
            'post': ['create', 'add', 'insert', 'save', 'store', 'submit', 'send', 'new', 'make'],
            'put': ['update', 'modify', 'edit', 'change', 'alter', 'revise', 'set'],
            'delete': ['remove', 'drop', 'destroy', 'clear', 'eliminate'],
            'issues': ['tickets', 'bugs', 'problems', 'tasks', 'items'],
            'users': ['accounts', 'profiles', 'members', 'people'],
            'data': ['information', 'records', 'entries', 'content'],
            'auth': ['authentication', 'login', 'signin', 'security'],
            'config': ['settings', 'configuration', 'preferences', 'options'],
            'status': ['state', 'condition', 'health', 'check'],
            'report': ['summary', 'analytics', 'metrics', 'statistics'],
            'file': ['document', 'attachment', 'upload', 'download'],
            'search': ['find', 'lookup', 'query', 'filter'],
            'dashboard': ['home', 'overview', 'main', 'index'],
            'profile': ['account', 'user', 'personal', 'settings'],
            'notification': ['alert', 'message', 'announcement', 'update'],
            'session': ['login', 'auth', 'token', 'credential'],
            'permission': ['access', 'right', 'privilege', 'authorization'],
            'category': ['type', 'group', 'class', 'classification'],
            'template': ['format', 'pattern', 'model', 'structure']
        }
        
        perf_words = perf_endpoint.split()
        source_words = source_endpoint.split()
        
        semantic_matches = 0
        total_words = len(perf_words)
        
        for perf_word in perf_words:
            word_matched = False
            
            # Direct word match
            if perf_word in source_words:
                semantic_matches += 1
                word_matched = True
            else:
                # Check semantic synonyms
                for category, synonyms in semantic_patterns.items():
                    if perf_word in synonyms or perf_word == category:
                        for synonym in synonyms:
                            if synonym in source_words or category in source_words:
                                semantic_matches += 0.8  # Partial credit for semantic match
                                word_matched = True
                                break
                        if word_matched:
                            break
                
                # Check if any source word is a synonym of perf_word
                if not word_matched:
                    for source_word in source_words:
                        for category, synonyms in semantic_patterns.items():
                            if (perf_word in synonyms and source_word == category) or \
                               (source_word in synonyms and perf_word == category):
                                semantic_matches += 0.8
                                word_matched = True
                                break
                        if word_matched:
                            break
        
        return semantic_matches / total_words if total_words > 0 else 0.0
    
    def _calculate_phrase_match_confidence(self, perf_api: APIPerformanceProfile, 
                                        source_api: DiscoveredAPI) -> float:
        """Calculate phrase-level matching confidence."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Clean endpoints for better matching
        perf_clean = self._clean_endpoint_for_matching(perf_endpoint)
        source_clean = self._clean_endpoint_for_matching(source_endpoint)
        
        # Use the phrase similarity method we already have
        return self._calculate_phrase_similarity(perf_clean, source_clean)
    
    def _calculate_framework_match_confidence(self, perf_api: APIPerformanceProfile, 
                                            source_api: DiscoveredAPI) -> float:
        """Calculate framework compatibility confidence."""
        # If we know the framework, give higher confidence
        if source_api.framework and source_api.framework != 'Unknown':
            return 0.8
        
        # Check for common API patterns in the endpoint
        perf_endpoint = perf_api.endpoint.lower()
        if any(pattern in perf_endpoint for pattern in ['/api/', '/v1/', '/v2/', '/rest/']):
            return 0.6
        
        return 0.3
    
    def _calculate_match_confidence(self, perf_api: APIPerformanceProfile, 
                                  source_api: DiscoveredAPI) -> float:
        """Calculate confidence score for matching two APIs."""
        endpoint_similarity = self._calculate_endpoint_similarity(
            perf_api.endpoint, source_api.endpoint
        )
        
        # Additional factors
        framework_bonus = self._calculate_framework_bonus(source_api.framework)
        complexity_factor = self._calculate_complexity_factor(source_api.complexity_score)
        
        # Weighted confidence calculation
        confidence = (
            endpoint_similarity * 0.6 +
            framework_bonus * 0.2 +
            complexity_factor * 0.2
        )
        
        return min(confidence, 1.0)
    
    def _calculate_endpoint_similarity(self, perf_endpoint: str, source_endpoint: str) -> float:
        """Calculate similarity between two API endpoints."""
        # Normalize endpoints
        perf_norm = self._normalize_endpoint(perf_endpoint)
        source_norm = self._normalize_endpoint(source_endpoint)
        
        # Direct string similarity
        direct_similarity = SequenceMatcher(None, perf_norm, source_norm).ratio()
        
        # Pattern-based similarity
        pattern_similarity = self._calculate_pattern_similarity(perf_norm, source_norm)
        
        # Path segment similarity
        segment_similarity = self._calculate_segment_similarity(perf_norm, source_norm)
        
        # Weighted combination
        similarity = (
            direct_similarity * 0.4 +
            pattern_similarity * 0.4 +
            segment_similarity * 0.2
        )
        
        return similarity
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint for comparison."""
        # Remove leading/trailing slashes
        endpoint = endpoint.strip('/')
        
        # Convert to lowercase
        endpoint = endpoint.lower()
        
        # Replace common variations
        replacements = {
            'users': 'user',
            'items': 'item',
            'products': 'product',
            'orders': 'order',
            'customers': 'customer'
        }
        
        for old, new in replacements.items():
            endpoint = endpoint.replace(old, new)
        
        return endpoint
    
    def _calculate_pattern_similarity(self, endpoint1: str, endpoint2: str) -> float:
        """Calculate similarity based on URL patterns."""
        # Extract path segments
        segments1 = endpoint1.split('/')
        segments2 = endpoint2.split('/')
        
        if len(segments1) != len(segments2):
            return 0.0
        
        matches = 0
        total = len(segments1)
        
        for seg1, seg2 in zip(segments1, segments2):
            if self._segments_match(seg1, seg2):
                matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def _segments_match(self, seg1: str, seg2: str) -> bool:
        """Check if two path segments match."""
        # Direct match
        if seg1 == seg2:
            return True
        
        # Parameter match (e.g., {id} vs {user_id})
        if self._is_parameter(seg1) and self._is_parameter(seg2):
            return True
        
        # Similar words
        if self._words_similar(seg1, seg2):
            return True
        
        return False
    
    def _is_parameter(self, segment: str) -> bool:
        """Check if segment is a parameter (e.g., {id}, :id, <id>)."""
        return (
            segment.startswith('{') and segment.endswith('}') or
            segment.startswith(':') or
            segment.startswith('<') and segment.endswith('>')
        )
    
    def _words_similar(self, word1: str, word2: str) -> bool:
        """Check if two words are similar."""
        # Remove common suffixes
        suffixes = ['s', 'es', 'ing', 'ed']
        
        for suffix in suffixes:
            if word1.endswith(suffix) and word2 == word1[:-len(suffix)]:
                return True
            if word2.endswith(suffix) and word1 == word2[:-len(suffix)]:
                return True
        
        # Check similarity
        similarity = SequenceMatcher(None, word1, word2).ratio()
        return similarity > 0.8
    
    def _calculate_segment_similarity(self, endpoint1: str, endpoint2: str) -> float:
        """Calculate similarity based on path segments."""
        segments1 = set(endpoint1.split('/'))
        segments2 = set(endpoint2.split('/'))
        
        if not segments1 and not segments2:
            return 1.0
        
        if not segments1 or not segments2:
            return 0.0
        
        intersection = segments1.intersection(segments2)
        union = segments1.union(segments2)
        
        return len(intersection) / len(union)
    
    def _calculate_framework_bonus(self, framework: str) -> float:
        """Calculate bonus based on framework type."""
        framework_bonuses = {
            'FastAPI': 0.9,
            'Flask': 0.8,
            'Spring Boot': 0.7,
            'Express.js': 0.6,
            'Unknown': 0.5
        }
        
        return framework_bonuses.get(framework, 0.5)
    
    def _calculate_complexity_factor(self, complexity_score: float) -> float:
        """Calculate factor based on complexity score."""
        # Higher complexity might indicate more important APIs
        # but also might indicate poorly written code
        if complexity_score <= 3:
            return 0.8  # Simple, well-written
        elif complexity_score <= 6:
            return 0.9  # Moderate complexity
        else:
            return 0.7  # High complexity, might be problematic
    
    def categorize_discovered_apis(self, discovered_apis: List[DiscoveredAPI]) -> Dict[str, List[DiscoveredAPI]]:
        """Categorize discovered APIs by risk level."""
        categories = {
            'high_risk': [],
            'medium_risk': [],
            'low_risk': [],
            'unanalyzed': []
        }
        
        for api in discovered_apis:
            if api.risk_level == SeverityLevel.HIGH:
                categories['high_risk'].append(api)
            elif api.risk_level == SeverityLevel.MEDIUM:
                categories['medium_risk'].append(api)
            elif api.risk_level == SeverityLevel.LOW:
                categories['low_risk'].append(api)
            else:
                categories['unanalyzed'].append(api)
        
        return categories
    
    def _extract_meaningful_terms(self, endpoint: str) -> List[str]:
        """Extract meaningful terms from an endpoint, handling various formats."""
        # Remove common prefixes and suffixes
        endpoint = re.sub(r'^(get|post|put|delete|patch|head|options)\s+', '', endpoint)
        endpoint = re.sub(r'^/api/?', '', endpoint)
        endpoint = re.sub(r'^/v\d+/', '', endpoint)
        endpoint = endpoint.strip('/')
        
        # Split by common separators
        terms = re.split(r'[/\-_\s]+', endpoint)
        
        # Filter out empty terms and common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'list', 'get', 'fetch'}
        meaningful_terms = []
        
        for term in terms:
            term = term.lower().strip()
            if term and term not in stop_words and len(term) > 1:
                # Handle pluralization
                if term.endswith('s') and len(term) > 3:
                    singular = term[:-1]
                    meaningful_terms.append(singular)
                meaningful_terms.append(term)
        
        return meaningful_terms
    
    def _calculate_partial_semantic_match(self, term1: str, term2: str, semantic_patterns: Dict) -> float:
        """Calculate partial semantic match between two terms."""
        # Check if terms are similar in meaning through pattern matching
        for pattern, synonyms in semantic_patterns.items():
            if term1 == pattern and term2 in synonyms:
                return 0.6
            if term2 == pattern and term1 in synonyms:
                return 0.6
            if term1 in synonyms and term2 in synonyms:
                return 0.4
        
        # Check for substring matches
        if term1 in term2 or term2 in term1:
            return 0.3
        
        # Check for similar word patterns (e.g., "issues" vs "issue")
        if len(term1) > 3 and len(term2) > 3:
            if term1.startswith(term2) or term2.startswith(term1):
                return 0.2
            if term1.endswith(term2) or term2.endswith(term1):
                return 0.2
        
        return 0.0
    
    def _normalize_for_fuzzy_match(self, endpoint: str) -> str:
        """Normalize endpoint for fuzzy matching."""
        # Remove common prefixes
        endpoint = re.sub(r'^/api/?', '', endpoint)
        endpoint = re.sub(r'^/v\d+/', '', endpoint)
        endpoint = endpoint.strip('/')
        
        # Replace common separators with underscores
        endpoint = re.sub(r'[/\-_\s]+', '_', endpoint)
        
        # Remove common suffixes
        endpoint = re.sub(r'_list$', '', endpoint)
        endpoint = re.sub(r'_get$', '', endpoint)
        endpoint = re.sub(r'_fetch$', '', endpoint)
        
        return endpoint.lower()
