"""
Parser factory for handling different file formats and types.
"""
import os
import zipfile
import io
import tempfile
import logging
from typing import List, Tuple
from parsers.jmeter_parser import parse_jmeter_xml, parse_jmeter_csv, parse_jmeter_json
from parsers.locust_parser import parse_locust_csv
from models.schemas import PerformanceEntry

logger = logging.getLogger(__name__)


def parse_jmeter_report(file_content: bytes, is_csv: bool = False) -> List[PerformanceEntry]:
    """Parse JMeter report (XML or CSV) and extract relevant metrics."""
    if is_csv:
        return parse_jmeter_csv(file_content)
    else:
        return parse_jmeter_xml(file_content)


def process_zip_file(file_content: bytes, temp_dir: str) -> Tuple[List[PerformanceEntry], List[str], List[str]]:
    """Extract and process all files from a zip archive."""
    results = []
    processed_files = []
    skipped_files = []
    
    with zipfile.ZipFile(io.BytesIO(file_content)) as z:
        z.extractall(temp_dir)
        for root, _, files in os.walk(temp_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        data = _process_single_file(content, filename)
                        if data:
                            results.extend(data)
                            processed_files.append(filename)
                        else:
                            skipped_files.append(filename)
                            logger.warning(f"No valid data in {filename}")
                except Exception as e:
                    skipped_files.append(filename)
                    logger.warning(f"Failed to process {filename}: {str(e)}")
    return results, processed_files, skipped_files


def _process_single_file(file_content: bytes, filename: str) -> List[PerformanceEntry]:
    """Process a single file based on its extension and content."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.xml'):
        return parse_jmeter_xml(file_content)
    elif filename_lower.endswith('.csv') or filename_lower.endswith('.jtl'):
        # Try Locust first, then JMeter CSV
        data = parse_locust_csv(file_content)
        if not data:
            data = parse_jmeter_csv(file_content)
        return data
    elif filename_lower.endswith('.json') and 'statistics' in filename_lower:
        return parse_jmeter_json(file_content)
    else:
        logger.warning(f"Skipping unsupported file: {filename}")
        return []
