from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import Optional
import xml.etree.ElementTree as ET
import csv
import io
import zipfile
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import json
import tempfile
import logging
import numpy as np

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="API Performance Analyzer with AWS Bedrock")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS Bedrock configuration
bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name='us-east-1',  # Update to your region if different
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

def parse_jmeter_report(file_content: bytes, is_csv: bool = False) -> list:
    """Parse JMeter report (XML or CSV) and extract relevant metrics."""
    if is_csv:
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
                results.append({
                    "endpoint": label,
                    "response_time_ms": response_time,
                    "success": success,
                    "error": not success
                })
            logger.info(f"JMeter parsed {len(results)} entries")
            return results if results else []
        except Exception as e:
            logger.warning(f"Invalid JMeter CSV format: {str(e)}")
            return []
    else:
        try:
            root = ET.fromstring(file_content)
            results = []
            for sample in root.findall(".//httpSample") + root.findall(".//sample"):
                label = sample.get("lb", "Unknown")
                response_time = float(sample.get("t", 0))
                success = sample.get("s") == "true"
                results.append({
                    "endpoint": label,
                    "response_time_ms": response_time,
                    "success": success,
                    "error": not success
                })
            return results
        except ET.ParseError:
            logger.warning("Invalid JMeter XML format")
            return []

def parse_locust_report(file_content: bytes) -> list:
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
            results.append({
                "endpoint": endpoint,
                "response_time_ms": response_time,
                "success": failure_count == 0,
                "error": failure_count > 0,
                "error_rate_percent": error_rate,
                "throughput_rps": throughput
            })
        logger.info(f"Locust parsed {len(results)} entries")
        return results if results else []
    except Exception as e:
        logger.warning(f"Invalid Locust CSV format: {str(e)}")
        return []

def parse_jmeter_json(file_content: bytes) -> list:
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
            results.append({
                "endpoint": label,
                "response_time_ms": response_time,
                "success": error_rate == 0,
                "error": error_rate > 0,
                "throughput_rps": throughput
            })
        return results
    except Exception as e:
        logger.warning(f"Invalid JMeter JSON format: {str(e)}")
        return []

def analyze_performance(data: list, response_time_good_threshold: Optional[float] = None, response_time_bad_threshold: Optional[float] = None, error_rate_good_threshold: Optional[float] = None, error_rate_bad_threshold: Optional[float] = None, throughput_good_threshold: Optional[float] = None, throughput_bad_threshold: Optional[float] = None, percentile_95_latency_good_threshold: Optional[float] = None, percentile_95_latency_bad_threshold: Optional[float] = None) -> dict:
    """Analyze performance data to find best and worst APIs based on provided thresholds."""
    if not data:
        logger.warning("No data to analyze, returning default response")
        return {"best_api": [], "worst_api": [], "details": [], "overall_percentile_95_latency_ms": 0}

    results = []
    response_times = [entry["response_time_ms"] for entry in data if entry["response_time_ms"] > 0]
    percentile_95_latency = np.percentile(response_times, 95) if response_times else 0
    logger.info(f"Calculated 95th percentile latency: {percentile_95_latency}ms")

    for entry in data:
        endpoint = entry["endpoint"]
        response_time = entry.get("response_time_ms", 0)
        error_rate = entry.get("error_rate_percent", 100.0 if entry.get("error", False) else 0.0)
        throughput = entry.get("throughput_rps", 0)

        result = {
            "endpoint": endpoint,
            "avg_response_time_ms": response_time,
            "error_rate_percent": error_rate,
            "throughput_rps": round(throughput, 2),
            "percentile_95_latency_ms": percentile_95_latency
        }

        # Add "Good" and "Bad" flags for all metrics
        if response_time_good_threshold is not None:
            result["is_good_response_time"] = bool(response_time <= response_time_good_threshold)
        if response_time_bad_threshold is not None:
            result["is_bad_response_time"] = bool(response_time >= response_time_bad_threshold)
        if error_rate_good_threshold is not None:
            result["is_good_error_rate"] = bool(error_rate <= error_rate_good_threshold)
        if error_rate_bad_threshold is not None:
            result["is_bad_error_rate"] = bool(error_rate >= error_rate_bad_threshold)
        if throughput_good_threshold is not None:
            result["is_good_throughput"] = bool(throughput >= throughput_good_threshold)
        if throughput_bad_threshold is not None:
            result["is_bad_throughput"] = bool(throughput >= throughput_bad_threshold)
        if percentile_95_latency_good_threshold is not None:
            result["is_good_percentile_95_latency"] = bool(percentile_95_latency <= percentile_95_latency_good_threshold)
        if percentile_95_latency_bad_threshold is not None:
            result["is_bad_percentile_95_latency"] = bool(percentile_95_latency >= percentile_95_latency_bad_threshold)

        if any(key in result for key in ["is_good_", "is_bad_"]):
            logger.debug(f"Processed entry: {endpoint}, Response Time: {response_time} ms, Error Rate: {error_rate}%, Bad Response: {result.get('is_bad_response_time', False)}, Bad Error Rate: {result.get('is_bad_error_rate', False)}")

        results.append(result)

    # Sort results by performance metrics
    sorted_results = sorted(results, key=lambda x: (x["avg_response_time_ms"] or float('inf'), x["error_rate_percent"] or float('inf'), -x["throughput_rps"] or 0))

    # Define metrics for easier iteration
    metrics_config = [
        ("response_time", response_time_good_threshold, response_time_bad_threshold),
        ("error_rate", error_rate_good_threshold, error_rate_bad_threshold),
        ("throughput", throughput_good_threshold, throughput_bad_threshold),
        ("percentile_95_latency", percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold)
    ]

    best_api_list = []
    worst_api_list = []
    details_list = []

    for api_result in sorted_results:
        all_relevant_bad_conditions_true = True
        any_bad_condition_true = False

        for metric_name, _, bad_threshold in metrics_config:
            is_bad_flag = f"is_bad_{metric_name}"
            # Check if threshold is provided and if the bad flag is present and true
            if bad_threshold is not None:
                if api_result.get(is_bad_flag, False):
                    any_bad_condition_true = True
                else:
                    all_relevant_bad_conditions_true = False # If a threshold is set, but bad flag is false, then not all bad conditions are true
            else:
                # If no bad_threshold is provided for a metric, it doesn't count towards "all relevant bad conditions"
                pass

        if all_relevant_bad_conditions_true and any_bad_condition_true:
            worst_api_list.append(api_result)
        elif any_bad_condition_true:
            details_list.append(api_result)
        else:
            best_api_list.append(api_result)

    # The sorting for worst_api is implicitly handled by sorted_results initially.
    # If there's a need for a specific order within worst_api_list or details_list,
    # we can re-sort them here if required.

    # Note: No need to remove worst_api_list from details_list as they are populated independently now.

    return {
        "best_api": best_api_list,
        "worst_api": worst_api_list,
        "details": details_list,
        "overall_percentile_95_latency_ms": percentile_95_latency
    }

def generate_bedrock_summary(analysis: dict) -> str:
    """Use AWS Bedrock to generate a summary of the analysis results with fallback."""
    try:
        if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
            logger.warning(f"AWS credentials missing: AWS_ACCESS_KEY_ID={os.getenv('AWS_ACCESS_KEY_ID')}, AWS_SECRET_ACCESS_KEY={os.getenv('AWS_SECRET_ACCESS_KEY')}")
            return "Summary generation skipped due to missing AWS credentials."

        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Summarize the following API performance analysis in a concise and professional manner:\n\nAll Best APIs:\n{json.dumps(analysis['best_api'], indent=2)}\n\nAll Worst APIs:\n{json.dumps(analysis['worst_api'], indent=2)}\n\nDetails (Unmatched Conditions):\n{json.dumps(analysis['details'], indent=2)}\n\nOverall 95th Percentile Latency:\n{json.dumps(analysis['overall_percentile_95_latency_ms'], indent=2)}\n\nProvide a brief summary (2-3 sentences) highlighting the key findings, including all best and worst performing APIs based on response time, error rate, throughput, and 95th percentile latency. Mention 'Bad' conditions where applicable based on provided thresholds."
                    }
                ]
            })

            response = bedrock_client.invoke_model_with_response_stream(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=body,
                contentType='application/json',
                accept='application/json'
            )

            completion_text = ""
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'].decode('utf-8'))
                if 'delta' in chunk and 'text' in chunk['delta']:
                    completion_text += chunk['delta']['text']
            return completion_text if completion_text else 'No summary generated'
        except ClientError as e:
            logger.error(f"Bedrock error: {str(e)}")
            return "Summary generation failed due to an unavailable model or configuration issue. Please check AWS Bedrock documentation for supported models, ensure your region is correct (currently us-east-1), and verify your AWS credentials."
    except Exception as e:
        logger.error(f"Unexpected Bedrock error: {str(e)}")
        return "Summary generation failed due to an unexpected error."

def process_zip_file(file_content: bytes, temp_dir: str) -> tuple[list, list, list]:
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
                        if filename.lower().endswith('.xml'):
                            data = parse_jmeter_report(content, is_csv=False)
                            if data:
                                results.extend(data)
                                processed_files.append(filename)
                            else:
                                skipped_files.append(filename)
                                logger.warning(f"No valid data in {filename}")
                        elif filename.lower().endswith('.csv') or filename.lower().endswith('.jtl'):
                            data = parse_locust_report(content)
                            if not data:
                                data = parse_jmeter_report(content, is_csv=True)
                            if data:
                                results.extend(data)
                                processed_files.append(filename)
                            else:
                                skipped_files.append(filename)
                                logger.warning(f"No valid data in {filename}")
                        elif filename.lower().endswith('.json') and 'statistics' in filename.lower():
                            data = parse_jmeter_json(content)
                            if data:
                                results.extend(data)
                                processed_files.append(filename)
                            else:
                                skipped_files.append(filename)
                                logger.warning(f"No valid data in {filename}")
                        else:
                            skipped_files.append(filename)
                            logger.warning(f"Skipping unsupported file: {filename}")
                except Exception as e:
                    skipped_files.append(filename)
                    logger.warning(f"Failed to process {filename}: {str(e)}")
    return results, processed_files, skipped_files

@app.post("/analyze-report/")
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
                    if file_extension == 'xml':
                        data = parse_jmeter_report(file_content, is_csv=False)
                        if data:
                            processed_files.append(file.filename)
                        else:
                            skipped_files.append(file.filename)
                            logger.warning(f"No valid data in {file.filename}")
                    elif file_extension in ('csv', 'jtl'):
                        data = parse_locust_report(file_content)
                        if not data:
                            data = parse_jmeter_report(file_content, is_csv=True)
                        if data:
                            processed_files.append(file.filename)
                        else:
                            skipped_files.append(file.filename)
                            logger.warning(f"No valid data in {file.filename}")
                    elif file_extension == 'json' and 'statistics' in file.filename.lower():
                        data = parse_jmeter_json(content)
                        if data:
                            processed_files.append(file.filename)
                        else:
                            skipped_files.append(file.filename)
                            logger.warning(f"No valid data in {file.filename}")
                    else:
                        skipped_files.append(file.filename)
                        logger.warning(f"Skipping unsupported file: {file.filename}")
                except Exception as e:
                    skipped_files.append(file.filename)
                    logger.warning(f"Failed to process {file.filename}: {str(e)}")

        if not data:
            error_msg = (
                "No valid performance data found in the uploaded file(s). "
                f"Processed files: {processed_files}. "
                f"Skipped files: {skipped_files}. "
                "Ensure the file or zip contains valid JMeter (.xml, .csv, .jtl, statistics.json) or Locust (.csv) reports."
            )
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info(f"Analyzing {len(data)} entries")
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
        summary = generate_bedrock_summary(analysis)

        # Check if any thresholds are provided
        any_thresholds_provided = any(t is not None for t in [
            response_time_good_threshold, response_time_bad_threshold,
            error_rate_good_threshold, error_rate_bad_threshold,
            throughput_good_threshold, throughput_bad_threshold,
            percentile_95_latency_good_threshold, percentile_95_latency_bad_threshold
        ])

        response = {
            "status": "success",
            "analysis": analysis,
            "summary": summary,
            "processed_files": processed_files,
            "skipped_files": skipped_files
        }

        # Include thresholds_used if any thresholds are provided
        if any_thresholds_provided:
            response["thresholds_used"] = {
                "response_time_ms_good": response_time_good_threshold,
                "response_time_ms_bad": response_time_bad_threshold,
                "error_rate_percent_good": error_rate_good_threshold,
                "error_rate_percent_bad": error_rate_bad_threshold,
                "throughput_rps_good": throughput_good_threshold,
                "throughput_rps_bad": throughput_bad_threshold,
                "percentile_95_latency_ms_good": percentile_95_latency_good_threshold,
                "percentile_95_latency_ms_bad": percentile_95_latency_bad_threshold
            }

        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing report: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)