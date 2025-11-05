"""
Validation utilities for input data and file types.
"""
import logging
from typing import List, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def validate_file_type(filename: str) -> bool:
    """
    Validate if the file type is supported.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if file type is supported, False otherwise
    """
    supported_extensions = {'.xml', '.csv', '.jtl', '.json', '.zip'}
    file_extension = '.' + filename.lower().split('.')[-1]
    return file_extension in supported_extensions


def validate_thresholds(
    response_time_good_threshold: Optional[float] = None,
    response_time_bad_threshold: Optional[float] = None,
    error_rate_good_threshold: Optional[float] = None,
    error_rate_bad_threshold: Optional[float] = None,
    throughput_good_threshold: Optional[float] = None,
    throughput_bad_threshold: Optional[float] = None,
    percentile_95_latency_good_threshold: Optional[float] = None,
    percentile_95_latency_bad_threshold: Optional[float] = None
) -> None:
    """
    Validate threshold values for logical consistency.
    
    Args:
        Various threshold parameters
        
    Raises:
        HTTPException: If thresholds are invalid
    """
    # Validate response time thresholds
    if (response_time_good_threshold is not None and response_time_bad_threshold is not None 
        and response_time_good_threshold >= response_time_bad_threshold):
        raise HTTPException(
            status_code=400, 
            detail="response_time_good_threshold must be less than response_time_bad_threshold"
        )
    
    # Validate error rate thresholds
    if (error_rate_good_threshold is not None and error_rate_bad_threshold is not None 
        and error_rate_good_threshold >= error_rate_bad_threshold):
        raise HTTPException(
            status_code=400, 
            detail="error_rate_good_threshold must be less than error_rate_bad_threshold"
        )
    
    # Validate throughput thresholds
    if (throughput_good_threshold is not None and throughput_bad_threshold is not None 
        and throughput_good_threshold <= throughput_bad_threshold):
        raise HTTPException(
            status_code=400, 
            detail="throughput_good_threshold must be greater than throughput_bad_threshold"
        )
    
    # Validate percentile 95 latency thresholds
    if (percentile_95_latency_good_threshold is not None and percentile_95_latency_bad_threshold is not None 
        and percentile_95_latency_good_threshold >= percentile_95_latency_bad_threshold):
        raise HTTPException(
            status_code=400, 
            detail="percentile_95_latency_good_threshold must be less than percentile_95_latency_bad_threshold"
        )


def validate_data_not_empty(data: List, processed_files: List[str], skipped_files: List[str]) -> None:
    """
    Validate that we have data to analyze.
    
    Args:
        data: List of performance entries
        processed_files: List of successfully processed files
        skipped_files: List of skipped files
        
    Raises:
        HTTPException: If no valid data is found
    """
    if not data:
        error_msg = (
            "No valid performance data found in the uploaded file(s). "
            f"Processed files: {processed_files}. "
            f"Skipped files: {skipped_files}. "
            "Ensure the file or zip contains valid JMeter (.xml, .csv, .jtl, statistics.json) or Locust (.csv) reports."
        )
        raise HTTPException(status_code=400, detail=error_msg)