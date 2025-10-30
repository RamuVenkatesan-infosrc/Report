"""
Enhanced API Performance Analyzer with GitHub Integration and AI-Powered Recommendations
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, List
import logging
import os
from dotenv import load_dotenv

# Import our modular components
from models.config import Settings
from models.schemas import ThresholdsConfig, AnalysisResponse
from models.improvement_models import EnhancedAnalysisResponse, APIPerformanceProfile
from analyzers.performance_analyzer import analyze_performance
from services.bedrock_service import BedrockService
from services.github_service import GitHubService
from services.api_matcher import APIMatcher
from services.ai_github_analyzer import AIGitHubAnalyzer
from analyzers.code_analyzer import CodeAnalyzer
from utils.file_processor import process_uploaded_file
from utils.validators import validate_file_type, validate_thresholds, validate_data_not_empty

# Load environment variables from .env file
load_dotenv()

# Initialize settings
settings = Settings()

# Initialize FastAPI app
app = FastAPI(title="Enhanced API Performance Analyzer with GitHub Integration")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize services
bedrock_service = BedrockService(settings)
github_service = GitHubService(settings)
api_matcher = APIMatcher(min_confidence_threshold=0.7)
ai_analyzer = AIGitHubAnalyzer(bedrock_service)
code_analyzer = CodeAnalyzer()


@app.post("/analyze-report/", response_model=AnalysisResponse)
async def analyze_report(
    file: UploadFile = File(...),
    response_time_good_threshold: Optional[float] = None,
    response_time_bad_threshold: Optional[float] = None,
    error_rate_good_threshold: Optional[float] = None,
    error_rate_bad_threshold: Optional[float] = None,
    throughput_good_threshold: Optional[float] = None,
    throughput_bad_threshold: Optional[float] = None,
    percentile_95_latency_good_threshold: Optional[float] = None,
    percentile_95_latency_bad_threshold: Optional[float] = None
):
    """
    Analyze performance reports from a file or zip archive (original functionality).
    """
    try:
        # Validate file type
        if not validate_file_type(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported formats: XML, CSV, JTL, JSON, ZIP"
            )
        
        # Validate thresholds
        validate_thresholds(
            response_time_good_threshold,
            response_time_bad_threshold,
            error_rate_good_threshold,
            error_rate_bad_threshold,
            throughput_good_threshold,
            throughput_bad_threshold,
            percentile_95_latency_good_threshold,
            percentile_95_latency_bad_threshold
        )
        
        # Process uploaded file
        data, processed_files, skipped_files = await process_uploaded_file(file)
        
        # Validate we have data to analyze
        validate_data_not_empty(data, processed_files, skipped_files)
        
        logger.info(f"Analyzing {len(data)} entries")
        
        # Perform analysis
        analysis = analyze_performance(
            data,
            response_time_good_threshold,
            response_time_bad_threshold,
            error_rate_good_threshold,
            error_rate_bad_threshold,
            throughput_good_threshold,
            throughput_bad_threshold,
            percentile_95_latency_good_threshold,
            percentile_95_latency_bad_threshold
        )
        
        # Generate summary using AWS Bedrock
        summary = bedrock_service.generate_summary(analysis)
        
        # Check if any thresholds are provided
        any_thresholds_provided = any(t is not None for t in [
            response_time_good_threshold, response_time_bad_threshold,
            error_rate_good_threshold, error_rate_bad_threshold,
            throughput_good_threshold, throughput_bad_threshold,
            percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold
        ])
        
        response = AnalysisResponse(
            status="success",
            analysis=analysis,
            summary=summary,
            processed_files=processed_files,
            skipped_files=skipped_files
        )
        
        # Include thresholds_used if any thresholds are provided
        if any_thresholds_provided:
            response.thresholds_used = ThresholdsConfig(
                response_time_good_threshold=response_time_good_threshold,
                response_time_bad_threshold=response_time_bad_threshold,
                error_rate_good_threshold=error_rate_good_threshold,
                error_rate_bad_threshold=error_rate_bad_threshold,
                throughput_good_threshold=throughput_good_threshold,
                throughput_bad_threshold=throughput_bad_threshold,
                percentile_95_latency_good_threshold=percentile_95_latency_good_threshold,
                percentile_95_latency_bad_threshold=percentile_95_latency_bad_threshold
            )
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing report: {str(e)}")


@app.post("/analyze-with-github/", response_model=EnhancedAnalysisResponse)
async def analyze_with_github(
    file: UploadFile = File(...),
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'"),
    response_time_good_threshold: Optional[float] = None,
    response_time_bad_threshold: Optional[float] = None,
    error_rate_good_threshold: Optional[float] = None,
    error_rate_bad_threshold: Optional[float] = None,
    throughput_good_threshold: Optional[float] = None,
    throughput_bad_threshold: Optional[float] = None,
    percentile_95_latency_good_threshold: Optional[float] = None,
    percentile_95_latency_bad_threshold: Optional[float] = None
):
    """
    Enhanced analysis that combines performance reports with GitHub source code analysis.
    Provides detailed recommendations and code suggestions.
    """
    try:
        # Validate file type
        if not validate_file_type(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Supported formats: XML, CSV, JTL, JSON, ZIP"
            )
        
        # Validate thresholds
        validate_thresholds(
            response_time_good_threshold,
            response_time_bad_threshold,
            error_rate_good_threshold,
            error_rate_bad_threshold,
            throughput_good_threshold,
            throughput_bad_threshold,
            percentile_95_latency_good_threshold,
            percentile_95_latency_bad_threshold
        )
        
        # Process uploaded file
        data, processed_files, skipped_files = await process_uploaded_file(file)
        
        # Validate we have data to analyze
        validate_data_not_empty(data, processed_files, skipped_files)
        
        logger.info(f"Analyzing {len(data)} entries with GitHub integration")
        
        # Perform basic performance analysis
        analysis = analyze_performance(
            data,
            response_time_good_threshold,
            response_time_bad_threshold,
            error_rate_good_threshold,
            error_rate_bad_threshold,
            throughput_good_threshold,
            throughput_bad_threshold,
            percentile_95_latency_good_threshold,
            percentile_95_latency_bad_threshold
        )
        
        # Extract worst-performing APIs
        worst_apis = []
        for api_result in analysis.worst_api:
            worst_apis.append(APIPerformanceProfile(
                endpoint=api_result.endpoint,
                avg_response_time_ms=api_result.avg_response_time_ms,
                error_rate_percent=api_result.error_rate_percent,
                throughput_rps=api_result.throughput_rps,
                percentile_95_latency_ms=api_result.percentile_95_latency_ms,
                issues=[],
                status="CRITICAL"
            ))
        
        # Discover APIs from GitHub repository
        logger.info(f"Discovering APIs from GitHub repository: {github_repo}")
        owner, repo = github_repo.split('/')
        discovered_apis = github_service.discover_apis_in_repository(owner, repo)
        
        if not discovered_apis:
            raise HTTPException(
                status_code=404,
                detail=f"No APIs found in repository {github_repo}. Please check the repository path and ensure it contains API code."
            )
        
        logger.info(f"Discovered {len(discovered_apis)} APIs in repository")
        
        # Match performance APIs with source code APIs
        matching_result = api_matcher.match_apis(worst_apis, discovered_apis)
        
        # Generate detailed analysis based on matching results
        if matching_result.status == "no_matches":
            # No matches found - analyze all discovered APIs proactively
            logger.info("No matching APIs found. Performing proactive analysis of all discovered APIs.")
            
            # Analyze discovered APIs proactively
            proactive_recommendations = ai_analyzer.analyze_discovered_apis(discovered_apis)
            
            # Categorize APIs by risk level
            categories = api_matcher.categorize_discovered_apis(discovered_apis)
            
            response = EnhancedAnalysisResponse(
                status="success",
                analysis_type="proactive",
                matching_status="no_matches",
                total_apis_analyzed=len(discovered_apis),
                matched_apis_count=0,
                discovered_apis_count=len(discovered_apis),
                high_risk_apis=len(categories['high_risk']),
                medium_risk_apis=len(categories['medium_risk']),
                low_risk_apis=len(categories['low_risk']),
                results=matching_result,
                summary=f"Analyzed {len(discovered_apis)} APIs from {github_repo}. Found {len(categories['high_risk'])} high-risk APIs that need attention.",
                implementation_roadmap={
                    "immediate_actions": ["Review high-risk APIs", "Implement critical fixes"],
                    "short_term": ["Address medium-risk issues", "Add monitoring"],
                    "long_term": ["Code quality improvements", "Performance optimization"]
                }
            )
            
        else:
            # Matches found - perform detailed analysis
            logger.info(f"Found {len(matching_result.matched_apis)} matching APIs. Performing detailed analysis.")
            
            # Generate detailed analysis for matched APIs
            detailed_analysis = ai_analyzer.analyze_matched_apis(matching_result.matched_apis)
            
            # Generate proactive recommendations for unmatched discovered APIs
            unmatched_discovered = [api for api in discovered_apis if api not in [match['source_api'] for match in matching_result.matched_apis]]
            proactive_recommendations = ai_analyzer.analyze_discovered_apis(unmatched_discovered)
            
            # Categorize all APIs
            categories = api_matcher.categorize_discovered_apis(discovered_apis)
            
            # Create implementation roadmap
            roadmap = {
                "immediate_actions": [],
                "short_term": [],
                "long_term": []
            }
            
            for analysis in detailed_analysis:
                if analysis.implementation_plan.phase_1:
                    roadmap["immediate_actions"].extend(analysis.implementation_plan.phase_1)
                if analysis.implementation_plan.phase_2:
                    roadmap["short_term"].extend(analysis.implementation_plan.phase_2)
                if analysis.implementation_plan.phase_3:
                    roadmap["long_term"].extend(analysis.implementation_plan.phase_3)
            
            response = EnhancedAnalysisResponse(
                status="success",
                analysis_type="reactive",
                matching_status=matching_result.status,
                total_apis_analyzed=len(discovered_apis),
                matched_apis_count=len(matching_result.matched_apis),
                discovered_apis_count=len(discovered_apis),
                high_risk_apis=len(categories['high_risk']),
                medium_risk_apis=len(categories['medium_risk']),
                low_risk_apis=len(categories['low_risk']),
                results=matching_result,
                summary=f"Found {len(matching_result.matched_apis)} matching APIs with detailed analysis. Also analyzed {len(unmatched_discovered)} additional APIs proactively.",
                implementation_roadmap=roadmap
            )
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in enhanced analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in enhanced analysis: {str(e)}")


@app.get("/")
async def root():
    """Serve the main configuration page."""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy", 
        "service": "Enhanced API Performance Analyzer",
        "features": ["performance_analysis", "github_integration", "ai_recommendations"]
    }


@app.get("/github/repositories")
async def search_repositories(
    query: str = Query(..., description="Search query for repositories"),
    language: Optional[str] = Query(None, description="Programming language filter")
):
    """Search for GitHub repositories."""
    try:
        repositories = github_service.search_repositories(query, language)
        return {
            "status": "success",
            "repositories": repositories[:10],  # Limit to first 10 results
            "total_found": len(repositories)
        }
    except Exception as e:
        logger.error(f"Error searching repositories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching repositories: {str(e)}")


@app.post("/github/configure-token")
async def configure_github_token(token: str = Query(..., description="GitHub Personal Access Token")):
    """Configure GitHub token for the session."""
    try:
        # Validate token format
        if not token.startswith(('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_')):
            raise HTTPException(
                status_code=400, 
                detail="Invalid GitHub token format. Token should start with ghp_, gho_, ghu_, ghs_, or ghr_"
            )
        
        # Update GitHub service with new token
        github_service.github_token = token
        github_service.headers['Authorization'] = f'token {token}'
        
        # Test the token by making a simple API call
        test_repos = github_service.search_repositories("test", limit=1)
        
        return {
            "status": "success",
            "message": "GitHub token configured successfully",
            "token_valid": True
        }
    except Exception as e:
        logger.error(f"Error configuring GitHub token: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error configuring GitHub token: {str(e)}")


@app.get("/github/token-status")
async def get_github_token_status():
    """Check GitHub token status."""
    try:
        has_token = bool(github_service.github_token)
        token_valid = False
        
        if has_token:
            # Test token validity
            try:
                test_repos = github_service.search_repositories("test", limit=1)
                token_valid = True
            except:
                token_valid = False
        
        return {
            "has_token": has_token,
            "token_valid": token_valid,
            "message": "GitHub token is configured and valid" if token_valid else 
                      "GitHub token is missing or invalid" if has_token else 
                      "No GitHub token configured"
        }
    except Exception as e:
        logger.error(f"Error checking GitHub token status: {str(e)}")
        return {
            "has_token": False,
            "token_valid": False,
            "message": f"Error checking token status: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
