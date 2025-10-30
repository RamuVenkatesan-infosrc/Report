"""
API Performance Analyzer with AWS Bedrock - Refactored Version
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import Optional
import logging
import os
from dotenv import load_dotenv

# Import our modular components
from models.config import Settings
from models.schemas import ThresholdsConfig, AnalysisResponse
from analyzers.performance_analyzer import analyze_performance
from services.bedrock_service import BedrockService
from utils.file_processor import process_uploaded_file
from utils.validators import validate_file_type, validate_thresholds, validate_data_not_empty

# Load environment variables from .env file
load_dotenv()

# Initialize settings
settings = Settings()

# Initialize FastAPI app
app = FastAPI(title="API Performance Analyzer with AWS Bedrock")

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize services
bedrock_service = BedrockService(settings)


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
    Analyze performance reports from a file or zip archive, processing all supported files.
    
    Parameters:
    - file: Uploaded file (XML, CSV, JTL, JSON, or ZIP containing reports)
    - response_time_good_threshold: Maximum acceptable response time in ms for 'Good' (optional)
    - response_time_bad_threshold: Minimum response time in ms for 'Bad' (optional)
    - error_rate_good_threshold: Maximum acceptable error rate percentage for 'Good' (optional)
    - error_rate_bad_threshold: Minimum error rate percentage for 'Bad' (optional)
    - throughput_good_threshold: Minimum acceptable throughput (requests per second) for 'Good' (optional)
    - throughput_bad_threshold: Maximum throughput (requests per second) for 'Bad' (optional)
    - percentile_95_latency_good_threshold: Maximum acceptable 95th percentile latency in ms for 'Good' (optional)
    - percentile_95_latency_bad_threshold: Minimum 95th percentile latency in ms for 'Bad' (optional)
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


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "API Performance Analyzer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
