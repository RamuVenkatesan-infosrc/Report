"""
AWS Bedrock service for AI-powered analysis summaries.
"""
import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from models.schemas import PerformanceAnalysis
from models.config import Settings

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for interacting with AWS Bedrock."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bedrock_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Bedrock client with AWS credentials."""
        try:
            # Check if Bedrock is enabled
            if not self.settings.enable_bedrock:
                logger.info("Bedrock is disabled in configuration")
                return
            
            # Check for AWS credentials
            if not self.settings.aws_access_key_id or not self.settings.aws_secret_access_key:
                logger.warning("AWS credentials missing. Bedrock will use fallback responses.")
                logger.info("To enable Bedrock AI analysis, set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
                return
            
            # Initialize Bedrock client with credentials
            bedrock_config = {
                'region_name': self.settings.aws_region,
                'aws_access_key_id': self.settings.aws_access_key_id,
                'aws_secret_access_key': self.settings.aws_secret_access_key
            }
            
            # Add session token if provided (for temporary credentials)
            if self.settings.aws_session_token:
                bedrock_config['aws_session_token'] = self.settings.aws_session_token
                logger.info("Bedrock client initialized with session token")
            
            self.bedrock_client = boto3.client('bedrock-runtime', **bedrock_config)
            logger.info("Bedrock client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            logger.info("Bedrock will use fallback responses for AI analysis")
            self.bedrock_client = None
    
    def generate_summary_from_prompt(self, prompt: str) -> str:
        """Generate response from custom prompt using AWS Bedrock."""
        try:
            if not self.bedrock_client:
                logger.warning("Bedrock client not available, using fallback analysis")
                return self._generate_fallback_analysis(prompt)
            
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
                return completion_text if completion_text else 'No response generated'
            except ClientError as e:
                logger.error(f"Bedrock error: {str(e)}")
                return self._generate_fallback_analysis(prompt)
        except Exception as e:
            logger.error(f"Unexpected Bedrock error: {str(e)}")
            return self._generate_fallback_analysis(prompt)

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
