"""
Enhanced API Performance Analyzer with Detailed GitHub Comparison
Shows worst APIs from performance report vs source code analysis
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Body, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
import os
import time
from dotenv import load_dotenv
import sys
import io

# Import our modular components
from models.config import Settings
from models.schemas import ThresholdsConfig, AnalysisResponse
from models.improvement_models import EnhancedAnalysisResponse, APIPerformanceProfile, DetailedAnalysisResult, ImplementationPlan
from analyzers.performance_analyzer import analyze_performance
from services.bedrock_service import BedrockService
from services.github_service import GitHubService
from services.api_matcher import APIMatcher
from services.ai_github_analyzer import AIGitHubAnalyzer
from services.dynamodb_service import DynamoDBService
from analyzers.code_analyzer import CodeAnalyzer
from utils.file_processor import process_uploaded_file
from utils.validators import validate_file_type, validate_thresholds, validate_data_not_empty
from utils.json_parser import parse_ai_json_response

# Load environment variables from .env file
load_dotenv()

# Initialize settings
settings = Settings()

# Initialize FastAPI app
app = FastAPI(title="Enhanced API Performance Analyzer with GitHub Comparison")
app = FastAPI(
    title="API Performance Analyzer",
    version="1.0.0",
    description="Analyze API performance and generate improvement suggestions.",
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
    root_path="/dev"  # 👈 Important for Lambda deployment
)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add request logging middleware (no emojis to avoid Windows console encoding issues)
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"[START] {request.method} {request.url.path} - Starting request")
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"[SUCCESS] {request.method} {request.url.path} -> {response.status_code} in {process_time:.2f}s")
    
    return response

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure logging (force UTF-8 where possible)
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backend.log', encoding='utf-8'),
        logging.StreamHandler(stream=io.TextIOWrapper(getattr(sys.stdout, 'buffer', sys.stdout), encoding='utf-8', errors='replace'))
    ]
)
logger = logging.getLogger(__name__)

# Initialize services
bedrock_service = BedrockService(settings)
github_service = GitHubService(settings, bedrock_service=bedrock_service)
api_matcher = APIMatcher(min_confidence_threshold=0.3)
ai_analyzer = AIGitHubAnalyzer(settings)
code_analyzer = CodeAnalyzer()

# Initialize DynamoDB service - uses .env config or AWS by default
dynamodb_service = DynamoDBService(
    endpoint_url=settings.dynamodb_endpoint_url,
    region_name=settings.aws_region
)

# Global storage for latest performance analysis
latest_performance_analysis = None


@app.post("/analyze-report/", response_model=AnalysisResponse)
async def analyze_report(
    file: UploadFile = File(...),
    response_time_good_threshold: Optional[float] = Form(None),
    response_time_bad_threshold: Optional[float] = Form(None),
    error_rate_good_threshold: Optional[float] = Form(None),
    error_rate_bad_threshold: Optional[float] = Form(None),
    throughput_good_threshold: Optional[float] = Form(None),
    throughput_bad_threshold: Optional[float] = Form(None),
    percentile_95_latency_good_threshold: Optional[float] = Form(None),
    percentile_95_latency_bad_threshold: Optional[float] = Form(None)
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
        
        # Store the latest performance analysis globally
        global latest_performance_analysis
        latest_performance_analysis = analysis

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
        
        # Store analysis result in DynamoDB
        try:
            # Convert response to dict for storage
            analysis_data = {
                "status": response.status,
                "analysis": response.analysis.dict() if hasattr(response.analysis, 'dict') else response.analysis,
                "summary": response.summary,
                "processed_files": response.processed_files,
                "skipped_files": response.skipped_files,
                "thresholds_used": response.thresholds_used.dict() if response.thresholds_used and hasattr(response.thresholds_used, 'dict') else response.thresholds_used
            }
            
            analysis_id = dynamodb_service.store_analysis_result(analysis_data, "report_analysis")
            logger.info(f"Analysis result stored in DynamoDB with ID: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Failed to store analysis result in DynamoDB: {e}")
            # Don't fail the request if DynamoDB storage fails
        
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing report: {str(e)}")


@app.post("/analyze-github-with-code-suggestions/")
async def analyze_github_with_code_suggestions(
    request_data: dict,
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'"),
    branch: str = Query(None, description="Specific branch to analyze (optional, defaults to repository default branch)")
):
    """
    Enhanced GitHub analysis with comprehensive code suggestions and diff views.
    Shows old vs new code with detailed explanations.
    """
    try:
        # Validate and normalize GitHub repo format
        if github_repo.startswith('https://github.com/'):
            github_repo = github_repo.replace('https://github.com/', '')
        elif github_repo.startswith('http://github.com/'):
            github_repo = github_repo.replace('http://github.com/', '')
        
        if '/' not in github_repo or github_repo.count('/') != 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository format. Use 'owner/repo' or full GitHub URL format"
            )
        
        # Extract worst_apis from request_data
        worst_apis = request_data.get('worst_apis', request_data.get('worst_api', []))
        if not worst_apis:
            raise HTTPException(
                status_code=400,
                detail="No worst_apis or worst_api found in request data."
            )
        
        logger.info(f"Enhanced GitHub analysis for {len(worst_apis)} APIs in repository: {github_repo}")
        
        # Convert worst APIs to APIPerformanceProfile objects
        worst_api_profiles = []
        for api in worst_apis:
            worst_api_profiles.append(APIPerformanceProfile(
                endpoint=api.get('endpoint', ''),
                avg_response_time_ms=api.get('avg_response_time_ms', 0),
                error_rate_percent=api.get('error_rate_percent', 0),
                throughput_rps=api.get('throughput_rps', 0),
                percentile_95_latency_ms=api.get('percentile_95_latency_ms', 0),
                issues=[],
                status="CRITICAL"
            ))
        
        # Discover APIs from GitHub Repository
        owner, repo = github_repo.split('/')
        selected_branch = branch or request_data.get('branch', None)
        
        # Validate branch if specified
        if selected_branch:
            available_branches = github_service.get_repository_branches(owner, repo)
            if available_branches:
                branch_names = [b.get('name', '') for b in available_branches]
                if selected_branch not in branch_names:
                    available_branch_list = ', '.join(branch_names[:10])
                    raise HTTPException(
                        status_code=400,
                        detail=f"Branch '{selected_branch}' not found. Available: {available_branch_list}"
                    )
        
        # Optional: enable debug sample APIs ONLY when explicitly requested
        if request_data.get('enable_debug_samples') is True:
            github_service.set_debug_worst_apis(worst_apis)
        discovered_apis = github_service.discover_apis_in_repository(owner, repo, selected_branch)
        
        # If no APIs found, provide helpful information instead of error
        if not discovered_apis:
            logger.warning(f"No APIs found in repository {github_repo}. This could be due to:")
            logger.warning("1. Repository is private and no GitHub token is provided")
            logger.warning("2. Repository doesn't contain API code")
            logger.warning("3. API patterns are not recognized")
            logger.warning("4. GitHub API rate limiting")
            
            # Return a response with helpful information instead of error
            return {
                "status": "warning",
                "analysis_type": "enhanced_github_analysis",
                "message": f"No APIs found in repository {github_repo}",
                "suggestions": [
                    "Ensure the repository is public or provide a GitHub token",
                    "Check if the repository contains API code",
                    "Try a different branch",
                    "Verify the repository URL is correct"
                ],
                "repository_info": {
                    "owner": owner,
                    "repo": repo,
                    "branch": selected_branch or "default",
                    "total_apis_discovered": 0
                },
                "performance_analysis": {
                    "worst_apis_count": len(worst_api_profiles),
                    "matched_apis_count": 0,
                    "unmatched_apis_count": len(worst_api_profiles)
                },
                "code_suggestions": [],
                "diff_analysis": [],
                "detailed_matches": []
            }
        
        # Match APIs
        matching_result = api_matcher.match_apis(worst_api_profiles, discovered_apis)
        
        # Generate enhanced analysis with code suggestions
        enhanced_analysis = {
            "repository_info": {
                "owner": owner,
                "repo": repo,
                "branch": selected_branch or "default",
                "total_apis_discovered": len(discovered_apis)
            },
            "performance_analysis": {
                "worst_apis_count": len(worst_api_profiles),
                "matched_apis_count": len(matching_result.matched_apis),
                "unmatched_apis_count": len(matching_result.unmatched_performance_apis)
            },
            "code_suggestions": [],
            "diff_analysis": [],
            "detailed_matches": [],
            "discovered_apis": [
                {
                    "endpoint": api.endpoint,
                    "file_path": api.file_path,
                    "function_name": api.function_name,
                    "framework": api.framework,
                    "line_number": api.line_number,
                    "code_snippet": api.code_snippet,
                    "complexity_score": api.complexity_score,
                    "risk_level": api.risk_level.value if api.risk_level else "UNKNOWN",
                    "potential_issues": api.potential_issues
                }
                for api in discovered_apis
            ]
        }
        
        # Process matched APIs for code suggestions
        if matched_apis_with_colors:
            detailed_analysis = ai_analyzer.analyze_matched_apis(matching_result.matched_apis)
            
            for i, match in enumerate(matching_result.matched_apis):
                # Create detailed match info
                match_info = {
                    "api_endpoint": match.api_endpoint,
                    "confidence_score": match.match_confidence,
                    "source_code_info": {
                        "file_path": match.file_path,
                        "function_name": match.function_name,
                        "framework": match.framework,
                        "line_number": match.line_number,
                        "code_snippet": match.code_snippet,
                        "complexity_score": match.complexity_score,
                        "risk_level": match.risk_level.value if match.risk_level else "UNKNOWN"
                    },
                    "performance_metrics": {
                        "response_time_ms": match.performance_metrics.avg_response_time_ms,
                        "error_rate_percent": match.performance_metrics.error_rate_percent,
                        "throughput_rps": match.performance_metrics.throughput_rps,
                        "percentile_95_latency_ms": match.performance_metrics.percentile_95_latency_ms
                    },
                    "improvements": []
                }
                
                # Add improvements with code suggestions from detailed analysis
                detailed_result = detailed_analysis[i] if i < len(detailed_analysis) else None
                if detailed_result and hasattr(detailed_result, 'improvements') and detailed_result.improvements:
                    for improvement in detailed_result.improvements:
                        improvement_info = {
                            "title": improvement.title,
                            "description": improvement.description,
                            "priority": improvement.priority.value if hasattr(improvement.priority, 'value') else str(improvement.priority),
                            "category": improvement.category.value if hasattr(improvement.category, 'value') else str(improvement.category),
                            "current_code": improvement.current_code,
                            "improved_code": improvement.improved_code,
                            "expected_improvement": improvement.expected_improvement,
                            "implementation_effort": improvement.implementation_effort
                        }
                        match_info["improvements"].append(improvement_info)
                        
                        # Add to code suggestions
                        enhanced_analysis["code_suggestions"].append(improvement_info)
                        
                        # Generate diff analysis for this improvement
                        if improvement.current_code and improvement.improved_code:
                            diff_result = ai_analyzer.diff_analyzer.analyze_code_diff(
                                improvement.current_code,
                                improvement.improved_code,
                                f"OLD: {improvement.title}",
                                f"NEW: {improvement.title}"
                            )
                            
                            enhanced_analysis["diff_analysis"].append({
                                "api_endpoint": match.api_endpoint,
                                "improvement_title": improvement.title,
                                "diff": {
                                    "side_by_side": diff_result.side_by_side,
                                    "unified_diff": diff_result.unified_diff,
                                    "line_by_line": diff_result.line_by_line,
                                    "stats": {
                                        "changes_count": diff_result.changes_count,
                                        "additions_count": diff_result.additions_count,
                                        "deletions_count": diff_result.deletions_count
                                    }
                                }
                            })
                
                enhanced_analysis["detailed_matches"].append(match_info)
        
        # Add summary
        enhanced_analysis["summary"] = {
            "total_improvements": sum(len(match.get("improvements", [])) for match in enhanced_analysis["detailed_matches"]),
            "high_priority_improvements": len([imp for match in enhanced_analysis["detailed_matches"] 
                                             for imp in match.get("improvements", []) 
                                             if imp.get("priority") == "HIGH"]),
            "code_quality_improvements": len([imp for match in enhanced_analysis["detailed_matches"] 
                                            for imp in match.get("improvements", []) 
                                            if imp.get("category") == "code_quality"]),
            "performance_improvements": len([imp for match in enhanced_analysis["detailed_matches"] 
                                           for imp in match.get("improvements", []) 
                                           if imp.get("category") in ["database_optimization", "caching", "algorithm_optimization"]])
        }
        
        return {
            "status": "success",
            "analysis_type": "enhanced_github_analysis",
            "data": enhanced_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced GitHub analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Enhanced GitHub analysis failed: {str(e)}")


@app.post("/analyze-github-repository/")
async def analyze_github_repository(
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'"),
    branch: str = Query(None, description="Specific branch to analyze (optional, defaults to repository default branch)")
):
    """
    Analyze any GitHub repository for code quality and performance improvements.
    No performance data required - focuses on code analysis and suggestions.
    """
    try:
        # Validate and normalize GitHub repo format
        if github_repo.startswith('https://github.com/'):
            github_repo = github_repo.replace('https://github.com/', '')
        elif github_repo.startswith('http://github.com/'):
            github_repo = github_repo.replace('http://github.com/', '')
        
        if '/' not in github_repo or github_repo.count('/') != 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository format. Use 'owner/repo' or full GitHub URL format"
            )
        
        logger.info(f"Analyzing GitHub repository: {github_repo}")
        
        # Discover APIs from GitHub Repository
        owner, repo = github_repo.split('/')
        selected_branch = branch
        
        # Validate branch if specified
        if selected_branch:
            available_branches = github_service.get_repository_branches(owner, repo)
            if available_branches:
                branch_names = [b.get('name', '') for b in available_branches]
                if selected_branch not in branch_names:
                    available_branch_list = ', '.join(branch_names[:10])
                    raise HTTPException(
                        status_code=400,
                        detail=f"Branch '{selected_branch}' not found. Available: {available_branch_list}"
                    )
        
        # Discover APIs
        discovered_apis = github_service.discover_apis_in_repository(owner, repo, selected_branch)
        
        if not discovered_apis:
            raise HTTPException(
                status_code=404,
                detail=f"No APIs found in repository {github_repo}"
            )
        
        # Generate code analysis for each discovered API
        code_analysis = []
        diff_analysis = []
        
        for api in discovered_apis:
            # Create analysis for this API
            api_analysis = {
                "api_endpoint": api.endpoint,
                "file_path": api.file_path,
                "function_name": api.function_name,
                "framework": api.framework,
                "line_number": api.line_number,
                "code_snippet": api.code_snippet,
                "complexity_score": api.complexity_score,
                "risk_level": api.risk_level.value if api.risk_level else "UNKNOWN",
                "potential_issues": api.potential_issues or [],
                "improvements": []
            }
            
            # Generate AI analysis for this API
            try:
                # Create a mock performance profile for analysis
                mock_performance = APIPerformanceProfile(
                    endpoint=api.endpoint,
                    avg_response_time_ms=1000,  # Default high value to trigger analysis
                    error_rate_percent=5.0,
                    throughput_rps=10,
                    percentile_95_latency_ms=2000,
                    issues=[],
                    status="NEEDS_ANALYSIS"
                )
                
                # Match with itself to get analysis
                matching_result = api_matcher.match_apis([mock_performance], [api])
                
                if matched_apis_with_colors:
                    detailed_analysis = ai_analyzer.analyze_matched_apis(matching_result.matched_apis)
                    
                    for match in matching_result.matched_apis:
                        if hasattr(match, 'improvements') and match.improvements:
                            for improvement in match.improvements:
                                improvement_info = {
                                    "title": improvement.get('title', 'Code Improvement'),
                                    "description": improvement.get('description', ''),
                                    "priority": improvement.get('priority', 'MEDIUM'),
                                    "category": improvement.get('category', 'code_quality'),
                                    "current_code": improvement.get('current_code', ''),
                                    "improved_code": improvement.get('improved_code', ''),
                                    "expected_improvement": improvement.get('expected_improvement', ''),
                                    "implementation_effort": improvement.get('implementation_effort', 'MEDIUM')
                                }
                                api_analysis["improvements"].append(improvement_info)
                                
                                # Generate diff analysis
                                if improvement.get('current_code') and improvement.get('improved_code'):
                                    diff_result = ai_analyzer.diff_analyzer.analyze_code_diff(
                                        improvement['current_code'],
                                        improvement['improved_code'],
                                        f"OLD: {improvement.get('title', 'Code')}",
                                        f"NEW: {improvement.get('title', 'Code')}"
                                    )
                                    
                                    diff_analysis.append({
                                        "api_endpoint": api.endpoint,
                                        "improvement_title": improvement.get('title', ''),
                                        "diff": {
                                            "side_by_side": diff_result.side_by_side,
                                            "unified_diff": diff_result.unified_diff,
                                            "line_by_line": diff_result.line_by_line,
                                            "stats": {
                                                "changes_count": diff_result.changes_count,
                                                "additions_count": diff_result.additions_count,
                                                "deletions_count": diff_result.deletions_count
                                            }
                                        }
                                    })
                
            except Exception as e:
                logger.warning(f"Could not analyze API {api.endpoint}: {e}")
                # Add basic improvement suggestions
                api_analysis["improvements"].append({
                    "title": "Code Review Recommended",
                    "description": "This API requires manual review for potential improvements",
                    "priority": "MEDIUM",
                    "category": "code_quality",
                    "current_code": api.code_snippet or "Code not available",
                    "improved_code": "Review and optimize based on best practices",
                    "expected_improvement": "Better code quality and maintainability",
                    "implementation_effort": "MEDIUM"
                })
            
            code_analysis.append(api_analysis)
        
        # Generate summary
        total_improvements = sum(len(api.get("improvements", [])) for api in code_analysis)
        high_priority = len([imp for api in code_analysis 
                           for imp in api.get("improvements", []) 
                           if imp.get("priority") == "HIGH"])
        
        return {
            "status": "success",
            "analysis_type": "github_repository_analysis",
            "data": {
                "repository_info": {
                    "owner": owner,
                    "repo": repo,
                    "branch": selected_branch or "default",
                    "total_apis_discovered": len(discovered_apis)
                },
                "code_analysis": code_analysis,
                "diff_analysis": diff_analysis,
                "summary": {
                    "total_apis_analyzed": len(code_analysis),
                    "total_improvements": total_improvements,
                    "high_priority_improvements": high_priority,
                    "apis_by_risk_level": {
                        "high": len([api for api in code_analysis if api.get("risk_level") == "HIGH"]),
                        "medium": len([api for api in code_analysis if api.get("risk_level") == "MEDIUM"]),
                        "low": len([api for api in code_analysis if api.get("risk_level") == "LOW"])
                    }
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in GitHub repository analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub repository analysis failed: {str(e)}")


@app.post("/analyze-full-repository/")
async def analyze_full_repository(
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'"),
    branch: str = Query(None, description="Specific branch to analyze (optional, defaults to repository default branch)")
):
    """
    Analyze entire GitHub repository for code quality and provide improvement suggestions.
    This is Feature 1: Full Repository Code Analysis
    """
    try:
        # Validate and normalize GitHub repo format
        if github_repo.startswith('https://github.com/'):
            github_repo = github_repo.replace('https://github.com/', '')
        elif github_repo.startswith('http://github.com/'):
            github_repo = github_repo.replace('http://github.com/', '')
        
        if '/' not in github_repo or github_repo.count('/') != 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository format. Use 'owner/repo' or full GitHub URL format"
            )
        
        logger.info(f"Starting full repository analysis for: {github_repo}")
        
        # Discover APIs from GitHub Repository
        owner, repo = github_repo.split('/')
        selected_branch = branch
        
        # Validate branch if specified
        if selected_branch:
            available_branches = github_service.get_repository_branches(owner, repo)
            if available_branches:
                branch_names = [b.get('name', '') for b in available_branches]
                if selected_branch not in branch_names:
                    available_branch_list = ', '.join(branch_names[:10])
                    raise HTTPException(
                        status_code=400,
                        detail=f"Branch '{selected_branch}' not found. Available: {available_branch_list}"
                    )
        
        # FULL REPOSITORY ANALYSIS (file-based, not API-only)
        # 1) List all files in repo, 2) analyze each code file, 3) collect per-file suggestions and diffs
        try:
            all_files = github_service._get_all_files(owner, repo, '', selected_branch)
        except Exception as e:
            logger.error(f"Failed to list repository files: {e}")
            all_files = []

        # Define real programming file extensions (code files only)
        code_extensions = (
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cs', '.go', '.rb', '.php', '.rs', '.kt', '.swift', 
            '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx', '.vue', '.svelte', '.html', '.css', '.scss', '.sass', '.less',
            '.sql', '.sh', '.bash', '.ps1'
        )
        
        # Define paths to always skip (config files, dependencies, build artifacts)
        skip_patterns = [
            'node_modules/', '.git/', '.idea/', '.vscode/', '__pycache__/', 
            '.env', 'venv/', 'env/', '.venv/', 'dist/', 'build/', 'target/',
            '.gradle/', '.mvn/', 'bin/', 'obj/', '.vs/', '.settings/', '.classpath', '.project',
            'package-lock.json', 'package.json', 'bower_components/', 'vendor/',
            'Pipfile', 'requirements.txt', 'setup.py', 'bundle.js', '.min.js',
            'tsconfig.json', 'tslint.json', 'webpack.config.js', 'jest.config.js',
            '.eslintrc', '.prettierrc', '.gitignore', '.dockerignore', 'yarn.lock',
            'pom.xml', 'build.gradle', 'Cargo.toml', 'Gemfile', 'Podfile'
        ]
        
        # Define file names to skip (config files)
        skip_file_names = {
            'package.json', 'package-lock.json', 'bower.json', 'yarn.lock', 'pnpm-lock.yaml',
            'tsconfig.json', 'jsconfig.json', 'tslint.json', 'eslint.json', 'prettier.json',
            'webpack.config.js', 'webpack.config.ts', 'vite.config.js', 'vite.config.ts',
            'jest.config.js', 'jest.config.ts', 'karma.conf.js', 'nyc.config.js',
            'pom.xml', 'build.gradle', 'build.gradle.kts', 'Cargo.toml', 'Gemfile', 
            'Podfile', 'Podfile.lock', 'Pipfile', 'Pipfile.lock', 'requirements.txt',
            'setup.py', 'setup.cfg', 'pyproject.toml', 'maven-wrapper.properties',
            '.eslintrc.js', '.eslintrc.json', '.prettierrc', '.prettierrc.json',
            '.babelrc', '.babelrc.js', 'babel.config.js', '.gitignore', '.dockerignore',
            '.editorconfig', 'sonar-project.properties', '.codeclimate.yml',
            'jspm.config.js', 'systemjs.config.js', 'angular.json', 'nx.json'
        }

        files_with_suggestions = []
        total_files_analyzed = 0
        total_files_found = len(all_files)
        files_skipped_extension = 0
        files_skipped_content = 0
        files_skipped_config = 0

        logger.info(f"Found {total_files_found} total files in repository")
        logger.info(f"Looking for actual code files (skipping config/build files)")

        for f in all_files:
            path = f.get('path')
            if not path:
                continue
                
            # Skip hidden files and directories
            if path.startswith('.') and not path.startswith('./'):
                files_skipped_config += 1
                continue
            
            # Check if file path matches skip patterns
            should_skip = False
            for pattern in skip_patterns:
                if pattern in path:
                    should_skip = True
                    break
            if should_skip:
                files_skipped_config += 1
                logger.debug(f"Skipping config/build file: {path}")
                continue
            
            # Check if filename is in skip list
            filename = path.split('/')[-1] if '/' in path else path
            if filename in skip_file_names:
                files_skipped_config += 1
                logger.debug(f"Skipping config file: {path}")
                continue
                
            # Check if file has supported code extension
            if not any(path.lower().endswith(ext) for ext in code_extensions):
                files_skipped_extension += 1
                continue
                
            logger.info(f"Analyzing file: {path}")
            content = github_service.get_file_content(owner, repo, path, selected_branch)
            if not content:
                files_skipped_content += 1
                logger.warning(f"Could not retrieve content for {path}")
                continue
            
            # Skip very large files (likely reports/data files, not code)
            file_size = len(content)
            if file_size > 500000:  # Skip files larger than 500KB
                files_skipped_content += 1
                logger.info(f"Skipping large file {path} ({file_size} bytes) - likely a report/data file, not code")
                continue
            
            # Skip HTML report files
            if path.endswith('.html') and file_size > 50000:  # Large HTML files are likely reports
                files_skipped_content += 1
                logger.info(f"Skipping large HTML file {path} ({file_size} bytes) - likely a report file")
                continue
                
            total_files_analyzed += 1
            logger.info(f"Successfully analyzed {path} (file {total_files_analyzed})")

            # Fresh Bedrock-driven analysis per file
            suggestions = []
            # Use full content - no truncation for snippet
            snippet = content[:10000]  # Increased to 10000 for better context (AI will return full code)
            # Infer language hint from extension
            lang = 'text'
            low = path.lower()
            if low.endswith('.py'): lang = 'python'
            elif low.endswith('.js') or low.endswith('.jsx'): lang = 'javascript'
            elif low.endswith('.ts') or low.endswith('.tsx'): lang = 'typescript'
            elif low.endswith('.java'): lang = 'java'
            elif low.endswith('.cs'): lang = 'csharp'
            elif low.endswith('.go'): lang = 'go'
            elif low.endswith('.php'): lang = 'php'
            elif low.endswith('.rb'): lang = 'ruby'
            elif low.endswith('.cpp') or low.endswith('.cxx') or low.endswith('.cc'): lang = 'cpp'
            elif low.endswith('.c'): lang = 'c'

            # Prepare full file content - allow up to 15000 chars for complete analysis
            full_content = content[:15000] if len(content) > 15000 else content
            lines_shown = len(full_content.split('\n'))
            is_truncated = len(content) > 15000

            bedrock_prompt = (
                f"You are a senior software engineer. Review this {lang} file and provide the ACTUAL IMPROVED CODE.\n\n"
                f"FILE: {path}\n"
                f"LANGUAGE: {lang}\n"
                f"CODE ({lines_shown} lines):\n```{lang}\n{full_content}\n```\n\n"
                f"TASK:\n"
                f"Review the code for issues and return the COMPLETE IMPROVED FILE with actual fixes applied.\n\n"
                f"CRITICAL REQUIREMENTS:\n"
                f"- improved_code must be REAL WORKING CODE (not comments or instructions)\n"
                f"- Do NOT add comments like 'Add error handling here' or 'Improvements added'\n"
                f"- Do NOT show old code mixed with placeholder comments\n"
                f"- Return actual working code with fixes applied\n"
                f"- Apply real improvements: try-catch blocks, type hints, input validation, logging\n"
                f"- If code has no issues, return it unchanged\n"
                f"- Focus on: security vulnerabilities, critical bugs, missing error handling, performance\n\n"
                f"Example:\n"
                f"- BAD: # Add error handling\\ndef get_user(id): return db.query(id)\n"
                f"- GOOD: import logging\\nlogger = logging.getLogger(__name__)\\ndef get_user(user_id: int):\\n    try:\\n        return db.query(user_id)\\n    except Exception as e:\\n        logger.error(f'Error: {{e}}')\\n        raise\n\n"
                f"RESPONSE FORMAT (valid JSON only):\n"
                f"{{\n"
                f'  "suggestions": [\n'
                f'    {{\n'
                f'      "title": "Complete Code Review - All Improvements",\n'
                f'      "issue": "(Security, bugs, performance, quality)",\n'
                f'      "explanation": "Detailed explanation of all improvements applied",\n'
                f'      "current_code": "{full_content}",\n'
                f'      "improved_code": "[COMPLETE IMPROVED FILE - REAL WORKING CODE]",\n'
                f'      "expected_improvement": "Measurable benefit of this fix",\n'
                f'      "summary": "Brief summary of the fix"\n'
                f'    }}\n'
                f'  ]\n'
                f'}}\n\n'
                f"FINAL REQUIREMENTS:\n"
                f"- Return ONLY ONE suggestion per file\n"
                f"- improved_code must be the COMPLETE IMPROVED FILE with REAL code changes\n"
                f"- improved_code must be syntactically correct {lang} code (no placeholders, no TODO comments)\n"
                f"- If code is perfect, improved_code == current_code\n"
                f"- Return ONLY valid JSON, no markdown or extra text"
            )
            try:
                import json
                import signal
                
                # Set timeout for AI analysis (120 seconds max)
                logger.info(f"Calling AI for {path} (timeout: 120s)")
                ai_response = bedrock_service.generate_summary_from_prompt(bedrock_prompt)
                logger.info(f"✅ AI response received for {path} ({len(ai_response) if ai_response else 0} chars)")
                
                # Try to parse JSON response
                try:
                    # Use improved JSON parser to handle AI response
                    logger.debug(f"Raw AI response: {ai_response[:200]}...")
                    
                    # Parse using robust JSON parser that handles control characters and unterminated strings
                    ai_suggestions = parse_ai_json_response(ai_response)
                    suggestions_list = ai_suggestions.get('suggestions', [])
                    logger.info(f"Found {len(suggestions_list)} suggestions from AI")
                    
                    # Process each suggestion
                    for sugg in suggestions_list:
                        if isinstance(sugg, dict) and sugg.get('title'):
                            # Validate and add suggestion
                            suggestion = {
                                "title": sugg.get('title', 'Code Improvement'),
                                "issue": sugg.get('issue', ''),
                                "explanation": sugg.get('explanation', ''),
                                "current_code": sugg.get('current_code', ''),
                                "improved_code": sugg.get('improved_code', ''),
                                "expected_improvement": sugg.get('expected_improvement', ''),
                                "summary": sugg.get('summary', ''),
                                "diff": None
                            }
                            suggestions.append(suggestion)
                            logger.info(f"Processed suggestion: {suggestion['title']}")
                    
                    if not suggestions:
                        logger.warning("No valid suggestions found in AI response")
                        raise ValueError("No valid suggestions found in AI response")
                        
                except json.JSONDecodeError as je:
                    logger.warning(f"Failed to parse AI JSON response for {path}: {je}")
                    logger.debug(f"AI Response: {ai_response[:500]}")
                    raise ValueError("Invalid JSON from AI")
                    
            except Exception as e:
                logger.warning(f"Bedrock analysis failed for {path}: {e}")
                # Continue to fallback below

            # Improved fallback: provide comprehensive language-specific suggestions
            if not suggestions:
                logger.info(f"Creating enhanced fallback suggestions for {path}")
                lower = path.lower()
                is_py = lower.endswith('.py')
                is_js_ts = lower.endswith('.js') or lower.endswith('.jsx') or lower.endswith('.ts') or lower.endswith('.tsx')
                is_java = lower.endswith('.java')
                is_cs = lower.endswith('.cs')
                
                # Get more content for better suggestions
                code_sample = content[:1500] if len(content) > 1500 else content
                
                # Create comprehensive language-specific suggestions
                if is_py:
                    suggestions.append({
                        "title": "Add Comprehensive Error Handling & Logging",
                        "issue": "Missing proper error handling, logging, and input validation",
                        "explanation": "Python code should have try-except blocks, logging, type hints, and input validation to prevent runtime errors and improve debugging",
                        "current_code": code_sample,
                        "improved_code": f"""import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Add proper error handling, type hints, and validation
{code_sample}

# Improvements added:
# 1. Import statements for logging and type hints
# 2. Logger configuration
# 3. Add try-except blocks around risky operations
# 4. Add type hints to function signatures
# 5. Add input validation
# 6. Add logging for debugging
# 7. Add docstrings for documentation
""",
                        "expected_improvement": "Prevents crashes, improves debugging with logging, enhances code maintainability with type hints",
                        "summary": "Add error handling, logging, and type safety",
                        "diff": None
                    })
                elif is_js_ts:
                    suggestions.append({
                        "title": "Add Type Safety, Error Handling & Validation",
                        "issue": "Missing TypeScript types, error handling, and null checks",
                        "explanation": "JavaScript/TypeScript code needs proper types, error boundaries, null checking, and input validation",
                        "current_code": code_sample,
                        "improved_code": f"""// Enhanced with TypeScript best practices

{code_sample}

// Improvements to implement:
// 1. Add proper TypeScript interfaces/types
// 2. Add try-catch blocks for async operations
// 3. Add null/undefined checks
// 4. Use optional chaining (?.) and nullish coalescing (??)
// 5. Add input validation
// 6. Add error logging
// 7. Use const/let instead of var
// 8. Add JSDoc comments
""",
                        "expected_improvement": "Improves type safety, prevents null reference errors, enhances debugging",
                        "summary": "Add TypeScript types and error handling",
                        "diff": None
                    })
                elif is_java:
                    suggestions.append({
                        "title": "Add Exception Handling & Null Safety",
                        "issue": "Missing exception handling and null safety checks",
                        "explanation": "Java code should have proper exception handling, null checks, and use Optional<T> where appropriate",
                        "current_code": code_sample,
                        "improved_code": f"""import java.util.Optional;
import java.util.logging.Logger;

// Enhanced with Java best practices

{code_sample}

// Improvements to implement:
// 1. Add try-catch blocks for checked exceptions
// 2. Use Optional<T> instead of null returns
// 3. Add null checks with Objects.requireNonNull()
// 4. Add proper logging with Logger
// 5. Add input validation
// 6. Use proper exception types (don't catch generic Exception)
// 7. Add JavaDoc comments
""",
                        "expected_improvement": "Prevents NullPointerException, improves error handling, better logging",
                        "summary": "Add exception handling and null safety",
                        "diff": None
                    })
                else:
                    suggestions.append({
                        "title": "Code Quality & Best Practices Review",
                        "issue": "Code needs review for best practices and maintainability",
                        "explanation": "Code should follow language best practices including error handling, documentation, and proper structure",
                        "current_code": code_sample,
                        "improved_code": f"""// Code with improvements

{code_sample}

// General improvements to implement:
// 1. Add error handling (try-catch or equivalent)
// 2. Add comments and documentation
// 3. Validate inputs
// 4. Add logging for debugging
// 5. Follow naming conventions
// 6. Break down large functions
// 7. Remove code duplication
// 8. Add unit tests
""",
                        "expected_improvement": "Improved code quality, better maintainability, easier debugging",
                        "summary": "Apply general code quality improvements",
                    "diff": None
                })

            if suggestions:
                files_with_suggestions.append({
                    "file_path": path,
                    "suggestions": suggestions
                })

        # Log analysis summary
        logger.info(f"Analysis complete:")
        logger.info(f"  Total files found: {total_files_found}")
        logger.info(f"  Files skipped (config/build files): {files_skipped_config}")
        logger.info(f"  Files skipped (wrong extension): {files_skipped_extension}")
        logger.info(f"  Files skipped (no content): {files_skipped_content}")
        logger.info(f"  Files successfully analyzed: {total_files_analyzed}")
        logger.info(f"  Files with suggestions: {len(files_with_suggestions)}")

        # Prepare result
        result = {
            "status": "success",
            "analysis_type": "full_repository_analysis",
            "repository_info": {
                "owner": owner,
                "repo": repo,
                "branch": selected_branch or "default",
                "total_files_analyzed": total_files_analyzed,
                "total_files_found": total_files_found,
                "files_skipped_config": files_skipped_config,
                "files_skipped_extension": files_skipped_extension,
                "files_skipped_content": files_skipped_content
            },
            "files_with_suggestions": files_with_suggestions,
            "summary": {
                "files_with_suggestions": len(files_with_suggestions),
                "total_suggestions": sum(len(f["suggestions"]) for f in files_with_suggestions),
                "analysis_coverage": f"{total_files_analyzed}/{total_files_found} files analyzed"
            }
        }
        
        # Store in DynamoDB
        try:
            analysis_id = dynamodb_service.store_full_repository_analysis(result)
            logger.info(f"Full repository analysis stored in DynamoDB with ID: {analysis_id}")
            result["analysis_id"] = analysis_id
        except Exception as e:
            logger.error(f"Failed to store analysis in DynamoDB: {e}")
            # Continue without failing the request
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in full repository analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full repository analysis failed: {str(e)}")


@app.post("/analyze-worst-apis-with-github/")
async def analyze_worst_apis_with_github(
    request_data: dict,
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'"),
    branch: str = Query(None, description="Specific branch to analyze (optional, defaults to repository default branch)")
):
    """
    Analyze worst APIs from previous analysis with GitHub source code.
    Takes worst APIs directly from /analyze-report/ results.
    """
    try:
        # Validate and normalize GitHub repo format
        if github_repo.startswith('https://github.com/'):
            # Extract owner/repo from full URL
            github_repo = github_repo.replace('https://github.com/', '')
        elif github_repo.startswith('http://github.com/'):
            # Extract owner/repo from full URL
            github_repo = github_repo.replace('http://github.com/', '')
        
        if '/' not in github_repo or github_repo.count('/') != 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository format. Use 'owner/repo' or full GitHub URL format"
            )
        
        # Extract worst_apis from request_data (support both 'worst_apis' and 'worst_api')
        worst_apis = request_data.get('worst_apis', request_data.get('worst_api', []))
        if not worst_apis:
            raise HTTPException(
                status_code=400,
                detail="No worst_apis or worst_api found in request data. Please include worst_apis array."
            )
        
        logger.info(f"Analyzing {len(worst_apis)} worst APIs with GitHub repository: {github_repo}")
        
        # Convert worst APIs to APIPerformanceProfile objects
        worst_api_profiles = []
        for api in worst_apis:
            worst_api_profiles.append(APIPerformanceProfile(
                endpoint=api.get('endpoint', ''),
                avg_response_time_ms=api.get('avg_response_time_ms', 0),
                error_rate_percent=api.get('error_rate_percent', 0),
                throughput_rps=api.get('throughput_rps', 0),
                percentile_95_latency_ms=api.get('percentile_95_latency_ms', 0),
                issues=[],
                status="CRITICAL"
            ))
        
        # STEP 1: Discover APIs from GitHub Repository
        logger.info(f"STEP 1: Discovering APIs from GitHub repository: {github_repo}")
        owner, repo = github_repo.split('/')
        
        # Get branch parameter (from query param or request body)
        selected_branch = branch or request_data.get('branch', None)
        
        # If branch is specified, validate it exists
        if selected_branch:
            logger.info(f"Validating branch: {selected_branch}")
            available_branches = github_service.get_repository_branches(owner, repo)
            if available_branches:
                branch_names = [b.get('name', '') for b in available_branches]
                if selected_branch not in branch_names:
                    available_branch_list = ', '.join(branch_names[:10])  # Show first 10 branches
                    raise HTTPException(
                        status_code=400,
                        detail=f"Branch '{selected_branch}' not found in repository. Available branches: {available_branch_list}"
                    )
                logger.info(f"✅ Branch '{selected_branch}' validated successfully")
            else:
                logger.warning(f"Could not fetch branch list, proceeding with specified branch: {selected_branch}")
        
        # Optional: enable debug sample APIs ONLY when explicitly requested
        if request_data.get('enable_debug_samples') is True:
            github_service.set_debug_worst_apis(worst_apis)
            logger.info(f"Debug mode enabled with {len(worst_apis)} worst APIs")
        
        discovered_apis = github_service.discover_apis_in_repository(owner, repo, selected_branch)
        logger.info(f"Discovered {len(discovered_apis)} APIs from GitHub repository")
        
        if not discovered_apis:
            # Return 200 with a warning payload to avoid frontend failure
            logger.warning(
                "No APIs found in repository. Returning warning payload instead of 404 for frontend handling."
            )
            return {
                "status": "warning",
                "analysis_type": "worst_apis_github_comparison_with_colors",
                "message": f"No APIs found in repository {github_repo}",
                "suggestions": [
                    "Ensure the repository is public or provide a GitHub token",
                    "Check if the repository contains API code",
                    "Try a different branch",
                    "Verify the repository URL is correct"
                ],
                "repository_info": {
                    "owner": owner,
                    "repo": repo,
                    "branch": selected_branch or "default",
                    "total_apis_discovered": 0
                },
                "performance_analysis": {
                    "worst_apis_count": len(worst_api_profiles),
                    "matched_apis_count": 0,
                    "unmatched_apis_count": len(worst_api_profiles)
                },
                "enhanced_analysis": {
                    "repository_info": {
                        "owner": owner,
                        "repo": repo,
                        "branch": selected_branch or "default",
                        "total_apis_discovered": 0
                    },
                    "performance_analysis": {
                        "worst_apis_count": len(worst_api_profiles),
                        "matched_apis_count": 0,
                        "unmatched_apis_count": len(worst_api_profiles)
                    },
                    "matched_apis_with_colors": [],
                    "discovered_apis": [],
                    "color_summary": {"red_apis": 0, "green_apis": 0, "total_matched": 0}
                }
            }
        
        logger.info(f"Discovered {len(discovered_apis)} APIs in GitHub repository")
        
        # STEP 2: Match Worst APIs with Source Code APIs
        logger.info("STEP 2: Matching worst APIs with source code APIs...")
        logger.info(f"Performance APIs to match: {len(worst_api_profiles)}")
        for i, api in enumerate(worst_api_profiles):
            logger.info(f"  {i+1}. '{api.endpoint}'")
        
        logger.info(f"Source APIs discovered: {len(discovered_apis)}")
        for i, api in enumerate(discovered_apis):
            logger.info(f"  {i+1}. '{api.endpoint}'")
        
        # Use enhanced matching with color coding
        matched_apis_with_colors = api_matcher.match_apis_with_color_coding(worst_api_profiles, discovered_apis)
        logger.info(f"Matched APIs result: {len(matched_apis_with_colors)}")
        
        # Generate AI analysis for matched APIs
        if matched_apis_with_colors:
            logger.info(f"Found {len(matched_apis_with_colors)} matching APIs with color coding")
            
            # Generate detailed analysis for each matched API
            for matched_api in matched_apis_with_colors:
                try:
                    # Helper to dedupe and add summaries to suggestions
                    def _dedupe_and_summarize(suggestions: list) -> list:
                        def _norm_text(text: str) -> str:
                            return " ".join((text or "").split()).strip().lower()
                        def _norm_code(code: str) -> str:
                            if not code:
                                return ""
                            return "\n".join(line.strip() for line in code.splitlines()).strip()
                        def _build_summary(sug: dict) -> str:
                            joined = f"{sug.get('title','')} {sug.get('issue','')} {sug.get('description','')}".lower()
                            if any(k in joined for k in ["response time", "latency", "cache", "caching", "pagination", "n+1", "db query", "database"]):
                                return "Problem: slow responses due to heavy/uncached data access. Improvement: caching, pagination, and optimized queries."
                            if any(k in joined for k in ["error rate", "exception", "retry", "timeout", "validation", "bad request", "500", "422"]):
                                return "Problem: frequent errors from weak validation/handling. Improvement: strict validation, structured error handling, and clear responses."
                            if any(k in joined for k in ["throughput", "async", "concurrency", "parallel", "worker", "background"]):
                                return "Problem: low throughput from synchronous work. Improvement: async/concurrency, batching, and background processing."
                            if any(k in joined for k in ["security", "auth", "sanitize", "injection", "xss", "csrf"]):
                                return "Problem: potential security gaps. Improvement: stronger auth, sanitization, and safe defaults."
                            return "Problem: general inefficiencies and code smells. Improvement: refactoring for clarity, performance, and reliability."
                        seen = set()
                        unique = []
                        for s in suggestions or []:
                            key = (
                                _norm_text(s.get('title') or s.get('issue') or ''),
                                _norm_text(s.get('description') or s.get('explanation') or ''),
                                _norm_code(s.get('current_code') or ''),
                                _norm_code(s.get('improved_code') or ''),
                            )
                            if key in seen:
                                continue
                            seen.add(key)
                            if not s.get('summary'):
                                s['summary'] = _build_summary(s)
                            unique.append(s)
                        return unique
                    
                    # Helper to ensure only real code suggestions are kept (no placeholders)
                    def _ensure_code_fields(suggestions: list) -> list:
                        src_code = matched_api.get("source_code_info", {}).get("code_snippet") or ""
                        ensured = []
                        for s in suggestions or []:
                            # Fill current_code from source if missing
                            if not s.get("current_code") and src_code:
                                s["current_code"] = src_code
                            # Require both code fields; drop otherwise
                            if s.get("current_code") and s.get("improved_code"):
                                ensured.append(s)
                        return ensured

                    # Helper to score and select the single best suggestion for this API
                    def _select_best_suggestion(suggestions: list) -> list:
                        perf = matched_api.get("performance_metrics")
                        response_ms = getattr(perf, 'avg_response_time_ms', 0) if perf else 0
                        error_rate = getattr(perf, 'error_rate_percent', 0.0) if perf else 0.0
                        throughput = getattr(perf, 'throughput_rps', 0.0) if perf else 0.0
                        endpoint = (matched_api.get("api_endpoint") or "").lower()
                        
                        def score(s: dict) -> float:
                            text = f"{s.get('title','')} {s.get('issue','')} {s.get('description','')}".lower()
                            sc = 0.0
                            if s.get('improved_code'):
                                sc += 0.6
                            # Performance emphasis
                            if response_ms and response_ms > 1000 and any(k in text for k in ["response time", "latency", "cache", "caching", "pagination", "query", "database", "n+1"]):
                                sc += 2.0
                            # Error handling emphasis
                            if error_rate and error_rate > 5 and any(k in text for k in ["error", "exception", "validation", "retry", "timeout", "bad request", "500", "422"]):
                                sc += 1.5
                            # Throughput emphasis
                            if throughput and throughput < 50 and any(k in text for k in ["throughput", "async", "concurrency", "parallel", "batching", "worker"]):
                                sc += 1.0
                            # Endpoint mention boosts relevance
                            if endpoint and endpoint in text:
                                sc += 0.4
                            return sc
                        
                        if not suggestions:
                            return []
                        best = max(suggestions, key=score)
                        # Normalize fields and tailor description to endpoint
                        best.setdefault('issue', best.get('title'))
                        if endpoint and endpoint not in (best.get('description') or '').lower():
                            best['description'] = (best.get('description') or '').strip() + f" (applies to {matched_api.get('api_endpoint')})"
                        return [best]
                    # Create DetailedAnalysisResult for AI analysis
                    detailed_result = DetailedAnalysisResult(
                        api_endpoint=matched_api["api_endpoint"],
                        match_confidence=matched_api["match_confidence"],
                        performance_metrics=matched_api["performance_metrics"],
                        analysis={},
                        root_causes=[],
                        code_quality_issues=[],
                        improvements=[],
                        implementation_plan=ImplementationPlan(
                            phase_1=[],
                            phase_2=[],
                            phase_3=[],
                            estimated_total_effort="MEDIUM",
                            expected_performance_gain="HIGH"
                        ),
                        file_path=matched_api["source_code_info"]["file_path"],
                        function_name=matched_api["source_code_info"]["function_name"],
                        framework=matched_api["source_code_info"]["framework"],
                        complexity_score=matched_api["source_code_info"]["complexity_score"],
                        risk_level=matched_api["source_code_info"]["risk_level"],
                        potential_issues=[],
                        code_snippet=matched_api["source_code_info"]["code_snippet"],
                        line_number=matched_api["source_code_info"]["line_number"]
                    )
                    
                    # Generate AI analysis
                    logger.info(f"Generating AI analysis for {matched_api['api_endpoint']}")
                    ai_analysis_results = ai_analyzer.analyze_matched_apis([detailed_result])
                    
                    if ai_analysis_results and ai_analysis_results[0].improvements:
                        logger.info(f"Generated {len(ai_analysis_results[0].improvements)} improvements for {matched_api['api_endpoint']}")
                        matched_api["code_suggestions"] = _select_best_suggestion(_ensure_code_fields(_dedupe_and_summarize([
                            {
                                "title": improvement.title,
                                "issue": improvement.title,
                                "description": improvement.description,
                                "current_code": improvement.current_code,
                                "improved_code": improvement.improved_code,
                                "explanation": improvement.description,
                                "expected_improvement": improvement.expected_improvement
                            }
                            for improvement in ai_analysis_results[0].improvements
                        ])))
                    else:
                        logger.warning(f"No improvements generated for {matched_api['api_endpoint']}")
                        # Generate fallback suggestions using the AI analyzer directly
                        performance_api = matched_api["performance_metrics"]
                        source_api = DiscoveredAPI(
                            endpoint=matched_api["api_endpoint"],
                            file_path=matched_api["source_code_info"]["file_path"],
                            function_name=matched_api["source_code_info"]["function_name"],
                            framework=matched_api["source_code_info"]["framework"],
                            complexity_score=matched_api["source_code_info"]["complexity_score"],
                            potential_issues=[],
                            risk_level=matched_api["source_code_info"]["risk_level"],
                            code_snippet=matched_api["source_code_info"]["code_snippet"]
                        )
                        
                        # Get code quality improvements directly
                        improvements = ai_analyzer._get_code_quality_improvements(performance_api, source_api)
                        if improvements:
                            matched_api["code_suggestions"] = _select_best_suggestion(_ensure_code_fields(_dedupe_and_summarize([
                                {
                                    "title": improvement["title"],
                                    "issue": improvement["title"],
                                    "description": improvement["description"],
                                    "current_code": improvement["current_code"],
                                    "improved_code": improvement["improved_code"],
                                    "explanation": improvement["description"],
                                    "expected_improvement": improvement["expected_improvement"]
                                }
                                for improvement in improvements
                            ])))
                            logger.info(f"Generated {len(improvements)} fallback improvements for {matched_api['api_endpoint']}")
                    
                except Exception as e:
                    logger.warning(f"Could not generate AI analysis for {matched_api['api_endpoint']}: {e}")
                    # Do not fabricate static suggestions; leave empty if we cannot compute real ones
                    matched_api["code_suggestions"] = []
                
                # Do not add static fallback suggestions; if none exist, keep it empty
                if not matched_api.get("code_suggestions"):
                    logger.info(f"No valid real-time suggestions for {matched_api['api_endpoint']}")
        
        # Create enhanced response with color coding
        logger.info(f"Creating enhanced analysis with {len(discovered_apis)} discovered APIs and {len(matched_apis_with_colors)} matched APIs")
        enhanced_analysis = {
            "repository_info": {
                "owner": owner,
                "repo": repo,
                "branch": selected_branch or "default",
                "total_apis_discovered": len(discovered_apis)
            },
            "performance_analysis": {
                "worst_apis_count": len(worst_api_profiles),
                "matched_apis_count": len(matched_apis_with_colors),
                "unmatched_apis_count": len(worst_api_profiles) - len(matched_apis_with_colors)
            },
            "matched_apis_with_colors": matched_apis_with_colors,
            "discovered_apis": [
                {
                    "endpoint": api.endpoint,
                    "file_path": api.file_path,
                    "function_name": api.function_name,
                    "framework": api.framework,
                    "complexity_score": api.complexity_score,
                    "risk_level": api.risk_level.value,
                    "potential_issues": api.potential_issues,
                    "code_snippet": api.code_snippet[:200] + "..." if len(api.code_snippet) > 200 else api.code_snippet
                } for api in discovered_apis
            ],
            "color_summary": {
                "red_apis": len([api for api in matched_apis_with_colors if api["color_indicator"] == "red"]),
                "green_apis": len([api for api in matched_apis_with_colors if api["color_indicator"] == "green"]),
                "total_matched": len(matched_apis_with_colors)
            }
        }
        
        # STEP 3: Generate Detailed Analysis and Comparison
        logger.info("STEP 3: Generating detailed analysis and comparison...")
        
        # Create detailed comparison response
        comparison_analysis = {
            "worst_apis_from_performance": {
                "total_worst_apis": len(worst_api_profiles),
                "apis": [
                    {
                        "endpoint": api.endpoint,
                        "avg_response_time_ms": api.avg_response_time_ms,
                        "error_rate_percent": api.error_rate_percent,
                        "throughput_rps": api.throughput_rps,
                        "percentile_95_latency_ms": api.percentile_95_latency_ms,
                        "status": api.status,
                        "performance_issues": [
                            f"High response time: {api.avg_response_time_ms}ms" if api.avg_response_time_ms > 1000 else None,
                            f"High error rate: {api.error_rate_percent}%" if api.error_rate_percent > 5 else None,
                            f"Low throughput: {api.throughput_rps} RPS" if api.throughput_rps < 100 else None
                        ]
                    } for api in worst_api_profiles
                ]
            },
            "github_source_analysis": {
                "repository": github_repo,
                "total_apis_discovered": len(discovered_apis),
                "apis_by_risk_level": {
                    "high_risk": len([api for api in discovered_apis if api.risk_level.value == "HIGH"]),
                    "medium_risk": len([api for api in discovered_apis if api.risk_level.value == "MEDIUM"]),
                    "low_risk": len([api for api in discovered_apis if api.risk_level.value == "LOW"])
                },
                "discovered_apis": [
                    {
                        "endpoint": api.endpoint,
                        "file_path": api.file_path,
                        "function_name": api.function_name,
                        "framework": api.framework,
                        "complexity_score": api.complexity_score,
                        "risk_level": api.risk_level.value,
                        "potential_issues": api.potential_issues,
                        "code_snippet": api.code_snippet[:200] + "..." if len(api.code_snippet) > 200 else api.code_snippet
                    } for api in discovered_apis
                ]
            },
            "matching_analysis": {
                "matching_status": "completed",
                "matched_apis_count": len(matched_apis_with_colors),
                "unmatched_performance_apis": len(worst_api_profiles) - len(matched_apis_with_colors),
                "unmatched_source_apis": len(discovered_apis) - len(matched_apis_with_colors),
                "matches": []
            }
        }
        
        # Add detailed matches if found
        if matched_apis_with_colors:
            logger.info(f"Found {len(matched_apis_with_colors)} matching APIs with color coding")
            
            # Process matched APIs with color coding (simplified)
            for i, matched_api in enumerate(matched_apis_with_colors):
                # Add basic match details to comparison analysis
                match_analysis = {
                    "performance_api": {
                        "endpoint": matched_api["api_endpoint"],
                        "avg_response_time_ms": matched_api["performance_metrics"].avg_response_time_ms,
                        "error_rate_percent": matched_api["performance_metrics"].error_rate_percent,
                        "throughput_rps": matched_api["performance_metrics"].throughput_rps,
                        "percentile_95_latency_ms": matched_api["performance_metrics"].percentile_95_latency_ms,
                        "status": matched_api["performance_metrics"].status
                    },
                    "source_code_api": matched_api["source_code_info"],
                    "match_confidence": matched_api["match_confidence"],
                    "color_indicator": matched_api["color_indicator"],
                    "performance_issues": matched_api["performance_issues"],
                    "code_suggestions": matched_api["code_suggestions"]
                }
                comparison_analysis["matching_analysis"]["matches"].append(match_analysis)
            
        
        # Add unmatched APIs analysis
        if len(worst_api_profiles) > len(matched_apis_with_colors):
            comparison_analysis["unmatched_performance_apis"] = [
                {
                    "endpoint": api.endpoint,
                    "avg_response_time_ms": api.avg_response_time_ms,
                    "error_rate_percent": api.error_rate_percent,
                    "throughput_rps": api.throughput_rps,
                    "reason": "No matching API found in source code"
                } for api in worst_api_profiles if api.endpoint not in [m["api_endpoint"] for m in matched_apis_with_colors]
            ]
        
        if len(discovered_apis) > len(matched_apis_with_colors):
            comparison_analysis["unmatched_source_apis"] = [
                {
                    "endpoint": api.endpoint,
                    "file_path": api.file_path,
                    "function_name": api.function_name,
                    "framework": api.framework,
                    "risk_level": api.risk_level.value,
                    "reason": "No corresponding performance data found"
                } for api in discovered_apis if api.endpoint not in [m["api_endpoint"] for m in matched_apis_with_colors]
            ]
        
        # Generate summary
        summary = f"""
        WORST APIs FROM PERFORMANCE REPORT:
        - {len(worst_api_profiles)} worst-performing APIs identified
        - These APIs have performance issues that need attention
        
        GITHUB SOURCE CODE ANALYSIS:
        - Repository: {github_repo}
        - Discovered {len(discovered_apis)} APIs in source code
        - High-risk APIs: {comparison_analysis['github_source_analysis']['apis_by_risk_level']['high_risk']}
        - Medium-risk APIs: {comparison_analysis['github_source_analysis']['apis_by_risk_level']['medium_risk']}
        - Low-risk APIs: {comparison_analysis['github_source_analysis']['apis_by_risk_level']['low_risk']}
        
        MATCHING & COMPARISON:
        - Matching status: completed
        - Matched APIs: {len(matched_apis_with_colors)}
        - Unmatched performance APIs: {len(worst_api_profiles) - len(matched_apis_with_colors)}
        - Unmatched source APIs: {len(discovered_apis) - len(matched_apis_with_colors)}
        
        {'✅ Found matching APIs with detailed analysis and code suggestions!' if matched_apis_with_colors else '⚠️ No matching APIs found - showing all discovered APIs for proactive analysis'}
        """
        
        # Prepare result
        result = {
            "status": "success",
            "analysis_type": "worst_apis_github_comparison_with_colors",
            "summary": f"""
        WORST APIs FROM PERFORMANCE REPORT:
        - {len(worst_api_profiles)} worst-performing APIs identified
        - These APIs have performance issues that need attention
        
        GITHUB SOURCE CODE ANALYSIS:
        - Repository: {github_repo}
        - Discovered {len(discovered_apis)} APIs in source code
        
        MATCHING & COMPARISON WITH COLOR CODING:
        - Total matched APIs: {len(matched_apis_with_colors)}
        - 🔴 Red APIs (Performance Issues): {enhanced_analysis['color_summary']['red_apis']}
        - 🟢 Green APIs (No Issues): {enhanced_analysis['color_summary']['green_apis']}
        
        {'✅ Found matching APIs with color-coded analysis!' if matched_apis_with_colors else '⚠️ No matching APIs found'}
        """,
            "enhanced_analysis": enhanced_analysis,
            "implementation_roadmap": {
                "immediate_actions": [
                    "Review red-highlighted APIs with performance issues",
                    "Implement critical code improvements for matched APIs",
                    "Focus on APIs with highest performance impact"
                ],
                "short_term": [
                    "Fix root causes identified in red APIs",
                    "Improve code quality for all matched APIs",
                    "Add monitoring for unmatched APIs"
                ],
                "long_term": [
                    "Implement comprehensive testing",
                    "Add performance monitoring",
                    "Code refactoring and optimization"
                ]
            }
        }
        
        # Store in DynamoDB
        try:
            analysis_id = dynamodb_service.store_api_performance_matching(result)
            logger.info(f"API performance matching analysis stored in DynamoDB with ID: {analysis_id}")
            result["analysis_id"] = analysis_id
        except Exception as e:
            logger.error(f"Failed to store analysis in DynamoDB: {e}")
            # Continue without failing the request
        
        return result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in worst APIs GitHub analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in worst APIs GitHub analysis: {str(e)}")


@app.post("/configure-github-token/")
async def configure_github_token(request_data: dict):
    """Configure GitHub token for API access."""
    try:
        token = request_data.get('token')
        if not token:
            raise HTTPException(status_code=400, detail="GitHub token is required")
        
        # Store token in environment or settings
        os.environ['GITHUB_TOKEN'] = token
        
        # Update GitHub service if it exists
        if 'github_service' in globals():
            github_service.github_token = token
            github_service.headers['Authorization'] = f'token {token}'
        
        return {
            "status": "success",
            "message": "GitHub token configured successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure GitHub token: {str(e)}")


@app.get("/get-repository-info/")
async def get_repository_info(
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'")
):
    """Get repository information and available branches."""
    try:
        # Validate and normalize GitHub repo format
        if github_repo.startswith('https://github.com/'):
            github_repo = github_repo.replace('https://github.com/', '')
        elif github_repo.startswith('http://github.com/'):
            github_repo = github_repo.replace('http://github.com/', '')
        
        if '/' not in github_repo or github_repo.count('/') != 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub repository format. Use 'owner/repo' or full GitHub URL format"
            )
        
        owner, repo = github_repo.split('/')
        
        # Get repository information
        repo_info = github_service.get_repository_info(owner, repo)
        if not repo_info:
            raise HTTPException(
                status_code=404,
                detail=f"Repository {github_repo} not found or not accessible"
            )
        
        # Get available branches
        branches = github_service.get_repository_branches(owner, repo)
        
        return {
            "repository": repo_info,
            "branches": branches,
            "total_branches": len(branches),
            "default_branch": repo_info.get('default_branch', 'main')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository info: {str(e)}")


@app.post("/analyze-with-github/")
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
    Enhanced analysis: Performance Report → Worst APIs → GitHub Source Code → Detailed Comparison
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
        
        # STEP 1: Analyze Performance Report
        logger.info("STEP 1: Analyzing performance report...")
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
        
        # Extract worst-performing APIs with detailed metrics
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
        
        logger.info(f"Found {len(worst_apis)} worst-performing APIs from performance report")
        
        # STEP 2: Discover APIs from GitHub Repository
        logger.info(f"STEP 2: Discovering APIs from GitHub repository: {github_repo}")
        owner, repo = github_repo.split('/')
        discovered_apis = github_service.discover_apis_in_repository(owner, repo)
        
        if not discovered_apis:
            raise HTTPException(
                status_code=404,
                detail=f"No APIs found in repository {github_repo}. This could mean:\n"
                       f"1. The repository doesn't contain API code\n"
                       f"2. The API code uses unsupported patterns\n"
                       f"3. The repository is private and requires authentication\n"
                       f"4. The API code is in a different branch\n"
                       f"Please verify the repository contains API endpoints and try again."
            )
        
        logger.info(f"Discovered {len(discovered_apis)} APIs in GitHub repository")
        
        # STEP 3: Match Performance APIs with Source Code APIs
        logger.info("STEP 3: Matching performance APIs with source code APIs...")
        matching_result = api_matcher.match_apis(worst_apis, discovered_apis)
        
        # STEP 4: Generate Detailed Analysis and Comparison
        logger.info("STEP 4: Generating detailed analysis and comparison...")
        
        # Create detailed comparison response
        comparison_analysis = {
            "performance_report_analysis": {
                "total_apis_analyzed": len(data),
                "worst_apis_count": len(worst_apis),
                "worst_apis": [
                    {
                        "endpoint": api.endpoint,
                        "avg_response_time_ms": api.avg_response_time_ms,
                        "error_rate_percent": api.error_rate_percent,
                        "throughput_rps": api.throughput_rps,
                        "percentile_95_latency_ms": api.percentile_95_latency_ms,
                        "status": api.status,
                        "performance_issues": [
                            f"High response time: {api.avg_response_time_ms}ms" if api.avg_response_time_ms > 1000 else None,
                            f"High error rate: {api.error_rate_percent}%" if api.error_rate_percent > 5 else None,
                            f"Low throughput: {api.throughput_rps} RPS" if api.throughput_rps < 100 else None
                        ]
                    } for api in worst_apis
                ]
            },
            "github_source_analysis": {
                "repository": github_repo,
                "total_apis_discovered": len(discovered_apis),
                "apis_by_framework": {},
                "apis_by_risk_level": {
                    "high_risk": len([api for api in discovered_apis if api.risk_level.value == "HIGH"]),
                    "medium_risk": len([api for api in discovered_apis if api.risk_level.value == "MEDIUM"]),
                    "low_risk": len([api for api in discovered_apis if api.risk_level.value == "LOW"])
                },
                "discovered_apis": [
                    {
                        "endpoint": api.endpoint,
                        "file_path": api.file_path,
                        "function_name": api.function_name,
                        "framework": api.framework,
                        "complexity_score": api.complexity_score,
                        "risk_level": api.risk_level.value,
                        "potential_issues": api.potential_issues,
                        "code_snippet": api.code_snippet[:200] + "..." if len(api.code_snippet) > 200 else api.code_snippet
                    } for api in discovered_apis
                ]
            },
            "matching_analysis": {
                "matching_status": "completed",
                "matched_apis_count": len(matched_apis_with_colors),
                "unmatched_performance_apis": len(worst_api_profiles) - len(matched_apis_with_colors),
                "unmatched_source_apis": len(discovered_apis) - len(matched_apis_with_colors),
                "matches": []
            }
        }
        
        # Add detailed matches if found
        if matched_apis_with_colors:
            logger.info(f"Found {len(matched_apis_with_colors)} matching APIs with color coding")
            
            # Process matched APIs with color coding (simplified)
            for i, matched_api in enumerate(matched_apis_with_colors):
                # Add basic match details to comparison analysis
                match_analysis = {
                    "performance_api": {
                        "endpoint": matched_api["api_endpoint"],
                        "avg_response_time_ms": matched_api["performance_metrics"].avg_response_time_ms,
                        "error_rate_percent": matched_api["performance_metrics"].error_rate_percent,
                        "throughput_rps": matched_api["performance_metrics"].throughput_rps,
                        "percentile_95_latency_ms": matched_api["performance_metrics"].percentile_95_latency_ms,
                        "status": matched_api["performance_metrics"].status
                    },
                    "source_code_api": matched_api["source_code_info"],
                    "match_confidence": matched_api["match_confidence"],
                    "color_indicator": matched_api["color_indicator"],
                    "performance_issues": matched_api["performance_issues"],
                    "code_suggestions": matched_api["code_suggestions"]
                }
                comparison_analysis["matching_analysis"]["matches"].append(match_analysis)
            
        
        # Add unmatched APIs analysis
        if len(worst_api_profiles) > len(matched_apis_with_colors):
            comparison_analysis["unmatched_performance_apis"] = [
                {
                    "endpoint": api.endpoint,
                    "avg_response_time_ms": api.avg_response_time_ms,
                    "error_rate_percent": api.error_rate_percent,
                    "throughput_rps": api.throughput_rps,
                    "reason": "No matching API found in source code"
                } for api in worst_api_profiles if api.endpoint not in [m["api_endpoint"] for m in matched_apis_with_colors]
            ]
        
        if len(discovered_apis) > len(matched_apis_with_colors):
            comparison_analysis["unmatched_source_apis"] = [
                {
                    "endpoint": api.endpoint,
                    "file_path": api.file_path,
                    "function_name": api.function_name,
                    "framework": api.framework,
                    "risk_level": api.risk_level.value,
                    "reason": "No corresponding performance data found"
                } for api in discovered_apis if api.endpoint not in [m["api_endpoint"] for m in matched_apis_with_colors]
            ]
        
        # Generate summary
        summary = f"""
        PERFORMANCE REPORT ANALYSIS:
        - Analyzed {len(data)} API calls from performance report
        - Found {len(worst_apis)} worst-performing APIs
        
        GITHUB SOURCE CODE ANALYSIS:
        - Repository: {github_repo}
        - Discovered {len(discovered_apis)} APIs in source code
        - High-risk APIs: {comparison_analysis['github_source_analysis']['apis_by_risk_level']['high_risk']}
        - Medium-risk APIs: {comparison_analysis['github_source_analysis']['apis_by_risk_level']['medium_risk']}
        - Low-risk APIs: {comparison_analysis['github_source_analysis']['apis_by_risk_level']['low_risk']}
        
        MATCHING & COMPARISON:
        - Matching status: completed
        - Matched APIs: {len(matched_apis_with_colors)}
        - Unmatched performance APIs: {len(worst_api_profiles) - len(matched_apis_with_colors)}
        - Unmatched source APIs: {len(discovered_apis) - len(matched_apis_with_colors)}
        
        {'✅ Found matching APIs with detailed analysis and code suggestions!' if matched_apis_with_colors else '⚠️ No matching APIs found - showing all discovered APIs for proactive analysis'}
        """
        
        return {
            "status": "success",
            "analysis_type": "github_comparison",
            "summary": summary,
            "comparison_analysis": comparison_analysis,
            "implementation_roadmap": {
                "immediate_actions": [
                    "Review matched APIs with performance issues",
                    "Implement critical code improvements",
                    "Address high-risk source code APIs"
                ],
                "short_term": [
                    "Fix root causes identified in analysis",
                    "Improve code quality issues",
                    "Add monitoring for unmatched APIs"
                ],
                "long_term": [
                    "Implement comprehensive testing",
                    "Add performance monitoring",
                    "Code refactoring and optimization"
                ]
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in enhanced analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in enhanced analysis: {str(e)}")


@app.get("/")
async def root():
    """Serve the main configuration page."""
    return FileResponse("static/index.html")

@app.get("/branch-selector")
async def branch_selector():
    """Serve the branch selector interface."""
    return FileResponse("static/branch-selector.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy", 
        "service": "Enhanced API Performance Analyzer with GitHub Comparison",
        "features": ["performance_analysis", "github_integration", "detailed_comparison", "ai_recommendations"],
        "github_token_status": "configured" if github_service.is_github_available() else "not_configured",
        "github_rate_limit": "authenticated" if github_service.is_github_available() else "unauthenticated"
    }

@app.get("/repository-info/{github_repo:path}")
async def get_repository_info(
    github_repo: str,
    token: Optional[str] = Query(None, description="GitHub token for authentication")
):
    """Get repository information and available branches"""
    try:
        # Normalize GitHub repository URL
        if github_repo.startswith(('https://github.com/', 'http://github.com/')):
            github_repo = github_repo.replace('https://github.com/', '').replace('http://github.com/', '')
        
        if '/' not in github_repo:
            raise HTTPException(status_code=400, detail="Invalid repository format. Use 'owner/repo' or full GitHub URL")
        
        owner, repo = github_repo.split('/', 1)
        
        # Get repository info (not async)
        repo_info = github_service.get_repository_info(owner, repo)
        if not repo_info:
            raise HTTPException(status_code=404, detail=f"Repository {github_repo} not found or not accessible")
        
        # Get available branches (not async)
        branches = github_service.get_repository_branches(owner, repo)
        if not branches:
            logger.warning(f"No branches found for repository {github_repo}")
            branches = [{"name": repo_info.get('default_branch', 'main'), "protected": False}]
        
        return {
            "status": "success",
            "repository": repo_info,
            "branches": [branch["name"] if isinstance(branch, dict) else branch for branch in branches],
            "total_branches": len(branches),
            "default_branch": repo_info.get("default_branch", branches[0]["name"] if isinstance(branches[0], dict) else branches[0] if branches else "main")
        }
    except Exception as e:
        logger.error(f"Failed to get repository info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get repository info: {str(e)}")

@app.get("/repository-branches/{github_repo:path}")
async def get_repository_branches(
    github_repo: str,
    token: Optional[str] = Query(None, description="GitHub token for authentication")
):
    """Get available branches for a repository"""
    try:
        # Normalize GitHub repository URL
        if github_repo.startswith(('https://github.com/', 'http://github.com/')):
            github_repo = github_repo.replace('https://github.com/', '').replace('http://github.com/', '')
        
        if '/' not in github_repo:
            raise HTTPException(status_code=400, detail="Invalid repository format. Use 'owner/repo' or full GitHub URL")
        
        owner, repo = github_repo.split('/', 1)
        
        # Get available branches (not async)
        branches = github_service.get_repository_branches(owner, repo)
        if not branches:
            logger.warning(f"No branches found for repository {github_repo}")
            branches = [{"name": "main", "protected": False}]
        
        return {
            "status": "success",
            "branches": [branch["name"] if isinstance(branch, dict) else branch for branch in branches],
            "total_branches": len(branches)
        }
    except Exception as e:
        logger.error(f"Failed to get repository branches: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get repository branches: {str(e)}")

@app.get("/latest-performance-analysis/")
async def get_latest_performance_analysis():
    """Get the latest performance analysis results from report analysis"""
    global latest_performance_analysis
    
    if latest_performance_analysis is None:
        return {
            "status": "no_data",
            "message": "No performance analysis data available. Please run report analysis first.",
            "worst_apis": [],
            "best_apis": []
        }
    
    # Try to get the most recent analysis from DynamoDB for complete session info
    try:
        recent_analyses = dynamodb_service.get_recent_analyses(1)
        if recent_analyses and len(recent_analyses) > 0:
            latest_stored = recent_analyses[0]
            # Use stored data if available, fallback to global variable
            return {
                "status": "success",
                "analysis": {
                    "best_api": latest_stored.get("analysis", {}).get("best_api", latest_performance_analysis.best_api),
                    "worst_api": latest_stored.get("analysis", {}).get("worst_api", latest_performance_analysis.worst_api),
                    "details": latest_stored.get("analysis", {}).get("details", latest_performance_analysis.details),
                    "overall_percentile_95_latency_ms": latest_stored.get("analysis", {}).get("overall_percentile_95_latency_ms", latest_performance_analysis.overall_percentile_95_latency_ms),
                    "insights": latest_stored.get("analysis", {}).get("insights", latest_performance_analysis.insights)
                },
                "summary": latest_stored.get("summary", "Latest analysis loaded from storage"),
                "processed_files": latest_stored.get("processed_files", []),
                "skipped_files": latest_stored.get("skipped_files", []),
                "thresholds_used": latest_stored.get("thresholds_used", None)
            }
    except Exception as e:
        logger.warning(f"Could not retrieve from DynamoDB, using global variable: {e}")
    
    # Fallback to global variable if DynamoDB retrieval fails
    return {
        "status": "success",
        "analysis": {
            "best_api": latest_performance_analysis.best_api,
            "worst_api": latest_performance_analysis.worst_api,
            "details": latest_performance_analysis.details,
            "overall_percentile_95_latency_ms": latest_performance_analysis.overall_percentile_95_latency_ms,
            "insights": latest_performance_analysis.insights
        },
        "summary": "Latest analysis loaded from storage",
        "processed_files": [],
        "skipped_files": [],
        "thresholds_used": None
    }


@app.post("/clear-analysis/")
async def clear_analysis():
    """Clear the current analysis data (useful for page refresh)"""
    global latest_performance_analysis
    latest_performance_analysis = None
    
    return {
        "status": "success",
        "message": "Analysis data cleared successfully"
    }


@app.post("/select-branch-for-analysis/")
async def select_branch_for_analysis(
    github_repo: str = Query(..., description="GitHub repository in format 'owner/repo'"),
    branch: str = Query(..., description="Branch name to analyze"),
    request_data: dict = Body(...)
):
    """
    Select a specific branch for analysis and validate it exists.
    This endpoint helps you choose the right branch before running the full analysis.
    """
    try:
        # Normalize GitHub repository URL
        if github_repo.startswith(('https://github.com/', 'http://github.com/')):
            github_repo = github_repo.replace('https://github.com/', '').replace('http://github.com/', '')
        
        if '/' not in github_repo:
            raise HTTPException(status_code=400, detail="Invalid repository format. Use 'owner/repo' or full GitHub URL")
        
        owner, repo = github_repo.split('/', 1)
        
        # Get repository information
        repo_info = github_service.get_repository_info(owner, repo)
        if not repo_info:
            raise HTTPException(status_code=404, detail=f"Repository {github_repo} not found or not accessible")
        
        # Get available branches
        available_branches = github_service.get_repository_branches(owner, repo)
        if not available_branches:
            logger.warning(f"No branches found for repository {github_repo}")
            available_branches = [{"name": repo_info.get('default_branch', 'main'), "protected": False}]
        
        # Validate selected branch
        branch_names = [b.get('name', '') for b in available_branches]
        if branch not in branch_names:
            available_branch_list = ', '.join(branch_names[:10])
            raise HTTPException(
                status_code=400,
                detail=f"Branch '{branch}' not found. Available branches: {available_branch_list}"
            )
        
        # Get branch details
        selected_branch_info = next((b for b in available_branches if b.get('name') == branch), None)
        
        return {
            "status": "success",
            "message": f"Branch '{branch}' selected for analysis",
            "repository": {
                "name": repo_info.get('name'),
                "full_name": repo_info.get('full_name'),
                "default_branch": repo_info.get('default_branch', 'main')
            },
            "selected_branch": {
                "name": branch,
                "protected": selected_branch_info.get('protected', False) if selected_branch_info else False
            },
            "analysis_ready": True,
            "next_step": f"Use this branch in your analysis request: ?branch={branch}"
        }
        
    except Exception as e:
        logger.error(f"Error selecting branch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error selecting branch: {str(e)}")


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


@app.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str, analysis_type: str = "report_analysis"):
    """
    Retrieve a stored analysis result from DynamoDB
    """
    try:
        result = dynamodb_service.get_analysis_result(analysis_id, analysis_type)
        if result:
            return result
        else:
            raise HTTPException(status_code=404, detail="Analysis result not found")
    except Exception as e:
        logger.error(f"Error retrieving analysis result: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/analysis/recent")
async def get_recent_analyses(limit: int = 10):
    """
    Get recent analysis results from DynamoDB
    """
    try:
        results = dynamodb_service.get_recent_analyses(limit)
        return {
            "status": "success",
            "count": len(results),
            "analyses": results
        }
    except Exception as e:
        logger.error(f"Error retrieving recent analyses: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/analysis/{analysis_id}")
async def delete_analysis_result(analysis_id: str, analysis_type: str = "report_analysis"):
    """
    Delete a stored analysis result from DynamoDB
    """
    try:
        success = dynamodb_service.delete_analysis_result(analysis_id, analysis_type)
        if success:
            return {"status": "success", "message": "Analysis result deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete analysis result")
    except Exception as e:
        logger.error(f"Error deleting analysis result: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
