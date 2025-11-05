"""
Locust report parser for CSV format.
"""
import csv
import io
import logging
from typing import List
from app.models.schemas import PerformanceEntry

logger = logging.getLogger(__name__)


def parse_locust_csv(file_content: bytes) -> List[PerformanceEntry]:
    """Parse Locust CSV report and extract relevant metrics."""
    try:
        content = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        logger.info(f"Locust CSV Headers: {csv_reader.fieldnames}")
        logger.info(f"First few rows: {list(csv_reader)[:3]}")
        results = []
        for row in csv.DictReader(io.StringIO(content)):
            endpoint = row.get('Name', row.get('name', 'Unknown'))
            response_time = float(row.get('Average Response Time', row.get('time', '0')))
            request_count = float(row.get('Request Count', '0'))
            failure_count = float(row.get('Failure Count', '0'))
            error_rate = (failure_count / request_count * 100) if request_count > 0 else 0.0
            throughput = float(row.get('Requests/s', '0'))
            results.append(PerformanceEntry(
                endpoint=endpoint,
                response_time_ms=response_time,
                success=failure_count == 0,
                error=failure_count > 0,
                error_rate_percent=error_rate,
                throughput_rps=throughput
            ))
        logger.info(f"Locust parsed {len(results)} entries")
        return results if results else []
    except Exception as e:
        logger.warning(f"Invalid Locust CSV format: {str(e)}")
        return []
