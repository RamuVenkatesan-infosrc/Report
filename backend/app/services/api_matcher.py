"""
API matching engine for matching performance data with source code APIs.
"""
import re
import logging
from typing import List, Tuple, Dict, Any
from difflib import SequenceMatcher
from app.models.improvement_models import (
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
                    "is_matched": True,  # Always True when match is found
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
        """Match performance APIs with source code APIs."""
        matches = []
        unmatched_performance = []
        unmatched_source = source_apis.copy()  # Start with all source APIs as unmatched
        
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
        
        # Enhanced matching with multiple strategies - EXACT WORDS and SIMILAR WORDS only
        # NO semantic matching (meaning-based) - only exact words and character-based similarity
        for source_api in source_apis:
            # Calculate confidence scores - only word-based matching, no semantic
            exact_match_score = self._calculate_exact_match_confidence(perf_api, source_api)
            fuzzy_match_score = self._calculate_fuzzy_match_confidence(perf_api, source_api)
            phrase_match_score = self._calculate_phrase_match_confidence(perf_api, source_api)
            
            # Check if source is generic endpoint (like "POST /", "/")
            source_endpoint_clean = source_api.endpoint.lower().strip()
            generic_patterns = ['post /', 'get /', 'put /', 'delete /', 'patch /', '/', 'post', 'get']
            is_generic_source = source_endpoint_clean in generic_patterns or \
                               (len(source_endpoint_clean) <= 5 and source_endpoint_clean.strip('/').strip() == '')
            
            # Extract meaningful words from performance endpoint
            perf_words = [w for w in perf_api.endpoint.lower().split() if w and len(w) > 2 and w not in ['get', 'post', 'put', 'delete']]
            
            # If source is generic and performance has specific words, heavily penalize
            if is_generic_source and perf_words:
                # Require at least some word overlap for generic endpoints
                source_words = [w for w in source_api.endpoint.lower().split() if w and len(w) > 2]
                common_words = set(perf_words) & set(source_words)
                if len(common_words) == 0:
                    # No word match - very low confidence for generic endpoint
                    total_confidence = min(exact_match_score * 0.10 + fuzzy_match_score * 0.05 + phrase_match_score * 0.05, 0.2)
                else:
                    # Some word match but still generic - low confidence
                    total_confidence = min(exact_match_score * 0.30 + fuzzy_match_score * 0.20 + phrase_match_score * 0.30, 0.5)
            else:
                # Normal matching logic
                if exact_match_score >= 0.9:
                    # Very high confidence for exact/near-exact matches
                    total_confidence = max(exact_match_score, phrase_match_score * 0.95)
                else:
                    # Weighted combination - focus on exact words and similar words (character-based) only
                    total_confidence = (
                        exact_match_score * 0.60 +      # Exact matches are MOST important (60%)
                        fuzzy_match_score * 0.30 +      # Fuzzy matching for similar word patterns (30%)
                        phrase_match_score * 0.10       # Phrase matching for word overlap (10%)
                        # Removed: semantic_match_score (no meaning-based matching)
                        # Removed: framework_match_score (not relevant for word matching)
                    )
            
            if total_confidence > best_confidence:
                best_confidence = total_confidence
                best_match = source_api
        
        return (best_match, best_confidence) if best_match else (None, 0.0)
    
    def _calculate_exact_match_confidence(self, perf_api: APIPerformanceProfile, 
                                        source_api: DiscoveredAPI) -> float:
        """Calculate exact match confidence with improved normalization."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Normalize both endpoints
        perf_normalized = self._normalize_endpoint_for_exact_match(perf_endpoint)
        source_normalized = self._normalize_endpoint_for_exact_match(source_endpoint)
        
        # Check if source is generic (like "POST /", "/", "GET /")
        generic_patterns = ['', '_', '/', 'post', 'get', 'put', 'delete', 'patch']
        is_generic_source = source_normalized in generic_patterns or len(source_normalized.strip('_/')) == 0
        
        # Extract meaningful words from performance endpoint
        perf_words = [w for w in perf_normalized.split('_') if w and len(w) > 2]
        
        # If source is generic and perf has specific words, penalize heavily
        if is_generic_source and perf_words:
            return 0.0  # No exact match for generic endpoints
        
        # Exact match after normalization
        if perf_normalized == source_normalized:
            return 1.0
        
        # Check if one is substring of the other (for cases like "Get Users" vs "/get-users")
        if perf_normalized in source_normalized or source_normalized in perf_normalized:
            # But not if source is generic
            if is_generic_source:
                return 0.0
            return 0.95
        
        return 0.0
    
    def _normalize_endpoint_for_exact_match(self, endpoint: str) -> str:
        """Normalize endpoint for exact matching."""
        # Remove HTTP methods
        endpoint = re.sub(r'^(get|post|put|delete|patch|head|options)\s+', '', endpoint, flags=re.IGNORECASE)
        
        # Remove leading/trailing slashes and spaces
        endpoint = endpoint.strip('/').strip()
        
        # Remove common prefixes
        endpoint = re.sub(r'^(api/|/api/|v\d+/|/v\d+/)', '', endpoint, flags=re.IGNORECASE)
        
        # Normalize separators (spaces, dashes, underscores, slashes to single underscore)
        endpoint = re.sub(r'[\s\-_/]+', '_', endpoint)
        
        # Remove common suffixes
        endpoint = re.sub(r'(_list|_items|_data|_info|_details|_get|_fetch)$', '', endpoint)
        
        # Remove trailing underscores
        endpoint = endpoint.rstrip('_')
        
        return endpoint.lower()
    
    def _calculate_fuzzy_match_confidence(self, perf_api: APIPerformanceProfile, 
                                        source_api: DiscoveredAPI) -> float:
        """Calculate fuzzy match confidence using CHARACTER similarity and WORD overlap - NO MEANING."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Check if source is generic (like "POST /", "/")
        generic_patterns = ['post /', 'get /', 'put /', 'delete /', 'patch /', '/', 'post', 'get', 'put', 'delete']
        is_generic_source = source_endpoint in generic_patterns or \
                           (len(source_endpoint.strip('/').strip()) <= 2 and '/' in source_endpoint)
        
        # Use the improved normalization method
        perf_normalized = self._normalize_endpoint_for_exact_match(perf_endpoint)
        source_normalized = self._normalize_endpoint_for_exact_match(source_endpoint)
        
        # Extract meaningful words (exclude HTTP methods and generic terms)
        generic_words = {'get', 'post', 'put', 'delete', 'patch', 'api', 'v1', 'v2', '', '_', '/'}
        perf_words = [w for w in perf_normalized.split('_') if w and w not in generic_words and len(w) > 2]
        source_words = [w for w in source_normalized.split('_') if w and w not in generic_words and len(w) > 2]
        
        perf_words_set = set(perf_words)
        source_words_set = set(source_words)
        
        # If source is generic and perf has specific words, return very low score
        if is_generic_source and perf_words_set:
            # Only allow if there's some word overlap
            if len(perf_words_set & source_words_set) == 0:
                return 0.0  # No word overlap with generic endpoint
            # Even with word overlap, generic endpoints get low score
            return 0.2
        
        # If perf is generic and source has specific words, also low
        if not perf_words_set and source_words_set:
            return 0.1
        
        # Calculate character-based similarity (SequenceMatcher is character-based, not meaning-based)
        similarity = SequenceMatcher(None, perf_normalized, source_normalized).ratio()
        
        # Check for EXACT word matches (character-by-character, not meaning)
        if perf_words_set and source_words_set:
            # Exact word overlap (character-based, not semantic)
            common_words = perf_words_set.intersection(source_words_set)
            if common_words:
                # High score if exact words match
                word_match_score = len(common_words) / max(len(perf_words_set), len(source_words_set))
                similarity = max(similarity, word_match_score)
            else:
                # No exact word match - heavily penalize
                similarity = similarity * 0.3
            
            # Check for similar words (character-based, like "user" vs "users", not meaning-based)
            similar_word_count = 0
            for perf_word in perf_words_set:
                for source_word in source_words_set:
                    # Character-based similarity (not semantic)
                    if perf_word and source_word:
                        word_similarity = SequenceMatcher(None, perf_word, source_word).ratio()
                        # If words are similar in characters (like "user" and "users")
                        if word_similarity > 0.7:
                            similar_word_count += word_similarity
            
            if similar_word_count > 0:
                similar_word_score = similar_word_count / max(len(perf_words_set), len(source_words_set))
                similarity = max(similarity, similar_word_score * 0.9)
        
        # Return similarity scores (character-based only)
        if similarity > 0.8:
            return min(similarity, 1.0)
        elif similarity > 0.6:
            return similarity * 0.9
        elif similarity > 0.4:
            return similarity * 0.7
        else:
            return similarity * 0.5
    
    def _calculate_semantic_match_confidence(self, perf_api: APIPerformanceProfile, 
                                           source_api: DiscoveredAPI) -> float:
        """Calculate semantic match confidence based on meaning with enhanced fuzzy matching."""
        perf_endpoint = perf_api.endpoint.lower().strip()
        source_endpoint = source_api.endpoint.lower().strip()
        
        # Normalize endpoints using the improved method
        perf_normalized = self._normalize_endpoint_for_exact_match(perf_endpoint)
        source_normalized = self._normalize_endpoint_for_exact_match(source_endpoint)
        
        # Split into words for semantic matching
        perf_words = perf_normalized.split('_') if perf_normalized else []
        source_words = source_normalized.split('_') if source_normalized else []
        
        if not perf_words or not source_words:
            return 0.0
        
        # Calculate word-level similarity
        word_similarity = self._calculate_word_similarity_from_lists(perf_words, source_words)
        
        # Calculate semantic similarity using synonyms
        semantic_similarity = self._calculate_semantic_similarity_from_words(perf_words, source_words)
        
        # Check for substring matches (handles partial matches like "user" in "users")
        substring_bonus = 0.0
        for perf_word in perf_words:
            for source_word in source_words:
                if perf_word and source_word:
                    if perf_word in source_word or source_word in perf_word:
                        substring_bonus += 0.2
                        break
        
        # Combine all similarity scores
        total_similarity = (
            word_similarity * 0.5 + 
            semantic_similarity * 0.4 + 
            min(substring_bonus, 0.3)
        )
        
        return min(total_similarity, 1.0)
    
    def _calculate_word_similarity_from_lists(self, words1: List[str], words2: List[str]) -> float:
        """Calculate similarity based on word lists."""
        if not words1 or not words2:
            return 0.0
        
        set1 = set(words1)
        set2 = set(words2)
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _calculate_semantic_similarity_from_words(self, perf_words: List[str], source_words: List[str]) -> float:
        """Calculate semantic similarity from word lists."""
        if not perf_words:
            return 0.0
        
        semantic_patterns = {
            'get': ['fetch', 'retrieve', 'list', 'find', 'search', 'query', 'load', 'obtain', 'show', 'display'],
            'user': ['users', 'account', 'accounts', 'profile', 'profiles', 'member', 'members'],
            'issue': ['issues', 'ticket', 'tickets', 'bug', 'bugs', 'task', 'tasks', 'item', 'items'],
            'dashboard': ['home', 'overview', 'main', 'index'],
            'search': ['find', 'lookup', 'query', 'filter'],
            'data': ['information', 'records', 'entries', 'content'],
        }
        
        matches = 0
        total = len(perf_words)
        
        for perf_word in perf_words:
            word_matched = False
            
            # Direct match
            if perf_word in source_words:
                matches += 1
                word_matched = True
            else:
                # Check semantic patterns
                for pattern, synonyms in semantic_patterns.items():
                    if perf_word == pattern or perf_word in synonyms:
                        # Check if any source word matches
                        for source_word in source_words:
                            if source_word == pattern or source_word in synonyms:
                                matches += 0.8
                                word_matched = True
                                break
                        if word_matched:
                            break
                    
                    # Reverse check - source word is pattern
                    if not word_matched:
                        for source_word in source_words:
                            if source_word == pattern or source_word in synonyms:
                                if perf_word == pattern or perf_word in synonyms:
                                    matches += 0.8
                                    word_matched = True
                                    break
                            if word_matched:
                                break
                        if word_matched:
                            break
        
        return matches / total if total > 0 else 0.0
    
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
        """Calculate similarity based on EXACT WORD matches and CHARACTER similarity - NO MEANING."""
        # Normalize both endpoints first
        perf_clean = self._normalize_endpoint_for_exact_match(perf_endpoint)
        source_clean = self._normalize_endpoint_for_exact_match(source_endpoint)
        
        # Normalize source endpoint
        source_normalized = source_clean.lstrip('/')
        perf_normalized = perf_clean
        
        # Check exact match after normalization
        if perf_normalized == source_normalized:
            return 1.0
        
        # Check if normalized versions are substrings (exact character match)
        if perf_normalized in source_normalized or source_normalized in perf_normalized:
            return 0.95
        
        # Extract meaningful words (exclude HTTP methods and generic terms)
        generic_words = {'get', 'post', 'put', 'delete', 'patch', 'api', 'v1', 'v2', '', '_', '/'}
        perf_words_meaningful = [w for w in perf_normalized.split('_') if w and w not in generic_words and len(w) > 2]
        source_words_meaningful = [w for w in source_normalized.split('_') if w and w not in generic_words and len(w) > 2]
        
        perf_words_meaningful_set = set(perf_words_meaningful)
        source_words_meaningful_set = set(source_words_meaningful)
        
        # Check if source is generic (no meaningful words)
        is_generic_source = len(source_words_meaningful_set) == 0
        is_generic_perf = len(perf_words_meaningful_set) == 0
        
        # If source is generic and perf has meaningful words, very low score
        if is_generic_source and perf_words_meaningful_set:
            return 0.1
        
        # If perf is generic and source has meaningful words, also low
        if is_generic_perf and source_words_meaningful_set:
            return 0.1
        
        # Check EXACT word matches (character-by-character, not meaning)
        if perf_words_meaningful_set and source_words_meaningful_set:
            # Exact word overlap (same characters)
            common_words = perf_words_meaningful_set.intersection(source_words_meaningful_set)
            if common_words:
                # High score if exact words match
                if len(common_words) == len(perf_words_meaningful_set) or len(common_words) == len(source_words_meaningful_set):
                    return 0.9
                # Score based on exact word overlap
                return len(common_words) / max(len(perf_words_meaningful_set), len(source_words_meaningful_set))
            else:
                # No word overlap - low score
                return 0.2
        
        # Use SequenceMatcher for character-based phrase similarity (not semantic)
        similarity = SequenceMatcher(None, perf_normalized, source_normalized).ratio()
        
        # Boost score for substring matches only if there are meaningful words
        if perf_words_meaningful and source_words_meaningful:
            for perf_word in perf_words_meaningful:
                for source_word in source_words_meaningful:
                    if perf_word and source_word:
                        # Character-based substring check (not meaning-based)
                        if perf_word in source_word or source_word in perf_word:
                            similarity = min(similarity + 0.15, 1.0)
                            break
        
        # Penalize if no meaningful word overlap
        if not is_generic_source and not is_generic_perf:
            if len(perf_words_meaningful_set & source_words_meaningful_set) == 0:
                similarity = similarity * 0.3
        
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
        
        if not perf_words:
            return 0.0
        
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
