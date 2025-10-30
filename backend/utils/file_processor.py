"""
Utility functions for file processing operations.
"""
import tempfile
import logging
from typing import List, Tuple
from fastapi import UploadFile
from parsers.parser_factory import process_zip_file, _process_single_file
from models.schemas import PerformanceEntry

logger = logging.getLogger(__name__)


async def process_uploaded_file(file: UploadFile) -> Tuple[List[PerformanceEntry], List[str], List[str]]:
    """
    Process an uploaded file and extract performance data.
    
    Args:
        file: The uploaded file from FastAPI
        
    Returns:
        Tuple of (data, processed_files, skipped_files)
    """
    file_content = await file.read()
    file_extension = file.filename.lower().split('.')[-1]
    data = []
    processed_files = []
    skipped_files = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            if file_extension == 'zip':
                data, processed_files, skipped_files = process_zip_file(file_content, temp_dir)
            else:
                try:
                    logger.info(f"Processing file: {file.filename} with extension: {file_extension}")
                    data = _process_single_file(file_content, file.filename)
                    if data:
                        processed_files.append(file.filename)
                    else:
                        skipped_files.append(file.filename)
                        logger.warning(f"No valid data in {file.filename}")
                except Exception as e:
                    skipped_files.append(file.filename)
                    logger.warning(f"Failed to process {file.filename}: {str(e)}")

        return data, processed_files, skipped_files
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise