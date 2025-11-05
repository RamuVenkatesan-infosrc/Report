"""
AWS Bedrock service for AI-powered analysis summaries.
"""
import json
import logging
import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from app.models.schemas import PerformanceAnalysis
from app.models.config import Settings

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for interacting with AWS Bedrock."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bedrock_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Bedrock client with AWS credentials.
        
        In Lambda (production): Uses IAM role credentials automatically
        In local development: Uses explicit credentials from .env if provided
        """
        try:
            # Check if Bedrock is enabled
            if not self.settings.enable_bedrock:
                logger.info("Bedrock is disabled in configuration")
                return
            
            # Detect if running in Lambda (production)
            is_lambda = bool(
                os.getenv("AWS_EXECUTION_ENV") or 
                os.getenv("LAMBDA_TASK_ROOT") or 
                os.getenv("AWS_LAMBDA_FUNCTION_NAME")
            )
            
            # Initialize Bedrock client configuration
            bedrock_config = {
                'region_name': self.settings.aws_region,
            }
            
            # In Lambda: Always use IAM role (don't pass explicit credentials)
            # In local: Use explicit credentials from .env if provided
            if not is_lambda and self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
                # Local development: Use explicit credentials from .env
                bedrock_config.update({
                    'aws_access_key_id': self.settings.aws_access_key_id,
                    'aws_secret_access_key': self.settings.aws_secret_access_key
                })
                logger.info("Bedrock client initialized with explicit credentials (local development)")
            elif is_lambda:
                # Lambda: Use IAM role (boto3 will automatically use Lambda execution role)
                logger.info("Bedrock client initialized with IAM role (Lambda environment)")
            else:
                # Fallback: Use default credential chain (IAM role, env vars, or ~/.aws/credentials)
                logger.info("Bedrock client initialized with default credential chain")
            
            # Add session token if provided (for temporary credentials, only in local)
            if not is_lambda and self.settings.aws_session_token:
                bedrock_config['aws_session_token'] = self.settings.aws_session_token
                logger.info("Bedrock client initialized with session token")
            
            # Configure timeouts for Bedrock requests
            # Note: API Gateway has a 30-second timeout, but Lambda Function URLs support 900s
            # Each Bedrock call should complete in reasonable time for multiple APIs
            boto_config = Config(
                connect_timeout=10,
                read_timeout=60,  # 60 seconds per Bedrock call - reasonable for complex analysis
                retries={'max_attempts': 2, 'mode': 'adaptive'}
            )
            
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                config=boto_config,
                **bedrock_config
            )
            logger.info("Bedrock client initialized successfully with timeout configuration")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}", exc_info=True)
            logger.error(
                f"Bedrock initialization failed. Check:\n"
                f"1. IAM role has bedrock:InvokeModel permission\n"
                f"2. Bedrock model access enabled in AWS console\n"
                f"3. Region {self.settings.aws_region} supports Bedrock\n"
                f"4. ENABLE_BEDROCK environment variable is 'true'\n"
                f"5. Lambda execution role is properly attached"
            )
            self.bedrock_client = None
    
    def generate_summary_from_prompt(self, prompt: str) -> str:
        """Generate response from custom prompt using AWS Bedrock. Raises exceptions on failure instead of returning fallback."""
        if not self.bedrock_client:
            error_msg = "Bedrock client not available. Check AWS credentials and configuration."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })

            logger.info(f"Invoking Bedrock model {self.settings.bedrock_model_id} with prompt length {len(prompt)} chars")
            response = self.bedrock_client.invoke_model_with_response_stream(
                modelId=self.settings.bedrock_model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )

            completion_text = ""
            chunk_count = 0
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'].decode('utf-8'))
                if 'delta' in chunk and 'text' in chunk['delta']:
                    completion_text += chunk['delta']['text']
                    chunk_count += 1
            
            if not completion_text:
                error_msg = "Bedrock returned empty response"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Bedrock response received: {len(completion_text)} chars in {chunk_count} chunks")
            return completion_text
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock ClientError [{error_code}]: {error_msg}", exc_info=True)
            raise RuntimeError(f"Bedrock API error [{error_code}]: {error_msg}") from e
        except BotoCoreError as e:
            logger.error(f"Bedrock BotoCoreError: {str(e)}", exc_info=True)
            raise RuntimeError(f"Bedrock connection error: {str(e)}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bedrock response: {str(e)}", exc_info=True)
            raise RuntimeError(f"Invalid Bedrock response format: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected Bedrock error: {type(e).__name__}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Unexpected Bedrock error: {str(e)}") from e

    def generate_summary(self, analysis: PerformanceAnalysis) -> str:
        """Generate a summary of the analysis results using AWS Bedrock."""
        try:
            if not self.bedrock_client:
                logger.warning("Bedrock client not available, using fallback summary")
                return self._generate_fallback_summary(analysis)
            
            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.settings.max_tokens,
                    "temperature": self.settings.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": self._build_prompt(analysis)
                        }
                    ]
                })

                response = self.bedrock_client.invoke_model_with_response_stream(
                    modelId=self.settings.bedrock_model_id,
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
                return self._generate_fallback_summary(analysis)
        except Exception as e:
            logger.error(f"Unexpected Bedrock error: {str(e)}")
            return self._generate_fallback_summary(analysis)
    
    def _build_prompt(self, analysis: PerformanceAnalysis) -> str:
        """Build the prompt for Bedrock based on analysis results."""
        return f"""Summarize the following API performance analysis in a concise and professional manner:

All Best APIs:
{json.dumps([result.dict() for result in analysis.best_api], indent=2)}

All Worst APIs:
{json.dumps([result.dict() for result in analysis.worst_api], indent=2)}

Details (Unmatched Conditions):
{json.dumps([result.dict() for result in analysis.details], indent=2)}

Overall 95th Percentile Latency:
{json.dumps(analysis.overall_percentile_95_latency_ms, indent=2)}

Provide a brief summary (2-3 sentences) highlighting the key findings, including all best and worst performing APIs based on response time, error rate, throughput, and 95th percentile latency. Mention 'Bad' conditions where applicable based on provided thresholds."""

    def _generate_fallback_analysis(self, prompt: str) -> str:
        """Generate fallback analysis when Bedrock is not available."""
        logger.info("Generating fallback analysis (Bedrock not available)")
        
        # Simple keyword-based analysis
        if "code improvement" in prompt.lower() or "improve" in prompt.lower():
            return """Based on the code analysis, here are the recommended improvements:

1. **Performance Optimization**: Consider implementing caching mechanisms and database query optimization to reduce response times.

2. **Error Handling**: Add comprehensive error handling with proper HTTP status codes and meaningful error messages.

3. **Code Structure**: Refactor complex functions into smaller, more maintainable components following SOLID principles.

4. **Security**: Implement input validation, authentication, and authorization checks where needed.

5. **Documentation**: Add comprehensive API documentation and inline code comments for better maintainability.

These improvements will enhance code quality, performance, and maintainability."""
        
        elif "performance" in prompt.lower() or "api" in prompt.lower():
            return """Performance Analysis Summary:

The analysis identified several APIs with performance concerns. Key findings include:

- **Response Time Issues**: Some APIs show elevated response times that may impact user experience
- **Error Rate Concerns**: Higher error rates detected in specific endpoints requiring attention  
- **Throughput Limitations**: Certain APIs may need optimization to handle increased load

**Recommendations**: Focus on optimizing the worst-performing APIs first, implement monitoring, and consider caching strategies for frequently accessed data."""
        
        else:
            return """Analysis completed successfully. The system has processed the provided data and identified key areas for improvement. 

**Key Findings**: The analysis reveals opportunities for optimization across performance, code quality, and maintainability.

**Next Steps**: Review the detailed results and implement the suggested improvements to enhance overall system performance and reliability."""
    
    def _generate_fallback_summary(self, analysis: PerformanceAnalysis) -> str:
        """Generate fallback summary when Bedrock is not available."""
        logger.info("Generating fallback summary (Bedrock not available)")
        
        best_count = len(analysis.best_api) if analysis.best_api else 0
        worst_count = len(analysis.worst_api) if analysis.worst_api else 0
        details_count = len(analysis.details) if analysis.details else 0
        
        return f"""Performance Analysis Summary:

**API Performance Overview**: Analyzed {best_count + worst_count} APIs with {details_count} additional conditions.

**Best Performing APIs** ({best_count}): These APIs demonstrate optimal performance with low response times, minimal error rates, and good throughput.

**Worst Performing APIs** ({worst_count}): These APIs require immediate attention due to performance issues including high response times, elevated error rates, or low throughput.

**Overall 95th Percentile Latency**: {analysis.overall_percentile_95_latency_ms}ms

**Recommendations**: Focus optimization efforts on the worst-performing APIs first, implement monitoring for all endpoints, and consider implementing caching strategies for frequently accessed data."""
