"""
JMeter report parser for XML, CSV, and JSON formats.
"""
import xml.etree.ElementTree as ET
import csv
import io
import json
import logging
from typing import List
from models.schemas import PerformanceEntry

logger = logging.getLogger(__name__)


def parse_jmeter_xml(file_content: bytes) -> List[PerformanceEntry]:
    """Parse JMeter XML report and extract relevant metrics."""
    try:
        root = ET.fromstring(file_content)
        results = []
        for sample in root.findall(".//httpSample") + root.findall(".//sample"):
            label = sample.get("lb", "Unknown")
            response_time = float(sample.get("t", 0))
            success = sample.get("s") == "true"
            results.append(PerformanceEntry(
                endpoint=label,
                response_time_ms=response_time,
                success=success,
                error=not success
            ))
        return results
    except ET.ParseError:
        logger.warning("Invalid JMeter XML format")
        return []


def parse_jmeter_csv(file_content: bytes) -> List[PerformanceEntry]:
    """Parse JMeter CSV report and extract relevant metrics."""
    try:
        content = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        logger.info(f"JMeter CSV Headers: {csv_reader.fieldnames}")
        logger.info(f"First few rows: {list(csv_reader)[:3]}")
        results = []
        for row in csv.DictReader(io.StringIO(content)):
            label = row.get('label', row.get('name', 'Unknown'))
            response_time = float(row.get('elapsed', row.get('time', '0')))
            success = row.get('success', 'true').lower() == 'true'
            results.append(PerformanceEntry(
                endpoint=label,
                response_time_ms=response_time,
                success=success,
                error=not success
            ))
        logger.info(f"JMeter parsed {len(results)} entries")
        return results if results else []
    except Exception as e:
        logger.warning(f"Invalid JMeter CSV format: {str(e)}")
        return []


def parse_jmeter_json(file_content: bytes) -> List[PerformanceEntry]:
    """Parse JMeter statistics.json file and extract relevant metrics."""
    try:
        content = json.loads(file_content.decode('utf-8'))
        results = []
        metrics = content.get('transactionController', content)
        for label, stats in metrics.items():
            if label == 'Total':
                continue
            response_time = float(stats.get('meanResTime', 0))
            error_rate = float(stats.get('errorPct', 0))
            throughput = float(stats.get('throughput', 0))
            results.append(PerformanceEntry(
                endpoint=label,
                response_time_ms=response_time,
                success=error_rate == 0,
                error=error_rate > 0,
                error_rate_percent=error_rate,
                throughput_rps=throughput
            ))
        return results
    except Exception as e:
        logger.warning(f"Invalid JMeter JSON format: {str(e)}")
        return []
