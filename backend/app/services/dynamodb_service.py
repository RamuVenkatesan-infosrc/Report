"""
DynamoDB service for storing API performance analysis results
"""
import boto3
import json
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
import logging

logger = logging.getLogger(__name__)

class DynamoDBService:
    def __init__(self, endpoint_url: Optional[str] = None, region_name: str = "us-east-1"):
        """
        Initialize DynamoDB service
        
        Args:
            endpoint_url: DynamoDB endpoint URL (None = AWS DynamoDB, "http://localhost:1234" = local DynamoDB)
            region_name: AWS region name
        """
        # Get from environment or use provided/default values
        self.endpoint_url = endpoint_url or os.getenv('DYNAMODB_ENDPOINT_URL')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Determine if using local or AWS DynamoDB
        self.is_local = self.endpoint_url is not None and 'localhost' in self.endpoint_url
        
        # Prepare client configuration
        client_config = {
            'region_name': self.region_name
        }
        
        if self.is_local:
            # Local DynamoDB - use dummy credentials
            logger.info(f"Using LOCAL DynamoDB at {self.endpoint_url}")
            client_config.update({
                'endpoint_url': self.endpoint_url,
                'aws_access_key_id': 'dummy',
                'aws_secret_access_key': 'dummy'
            })
        else:
            # AWS DynamoDB - use environment credentials or IAM role
            logger.info(f"Using AWS DynamoDB in region {self.region_name}")
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_session_token = os.getenv('AWS_SESSION_TOKEN')
            
            if aws_access_key and aws_secret_key:
                client_config.update({
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key
                })
                
                # Add session token if provided (for temporary credentials)
                if aws_session_token:
                    client_config['aws_session_token'] = aws_session_token
                    logger.info("Using AWS credentials with session token from environment variables")
                else:
                    logger.info("Using AWS credentials from environment variables")
            else:
                logger.info("No AWS credentials found - using default credential chain (IAM role, etc.)")
        
        # Initialize DynamoDB client
        self.dynamodb = boto3.resource('dynamodb', **client_config)
        
        # Report analysis table (existing)
        self.report_table_name = 'api-performance-analysis'
        self.report_table = self.dynamodb.Table(self.report_table_name)
        
        # GitHub analysis table (new)
        self.github_table_name = 'github-analysis-results'
        self.github_table = self.dynamodb.Table(self.github_table_name)
        
        # Create tables if they don't exist
        self._create_report_table_if_not_exists()
        self._create_github_table_if_not_exists()
    
    def _convert_floats_to_decimal(self, obj):
        """Recursively convert float values to Decimal for DynamoDB compatibility and handle Pydantic models"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {key: self._convert_floats_to_decimal(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        elif hasattr(obj, 'model_dump'):
            # Handle Pydantic v2 models
            try:
                return self._convert_floats_to_decimal(obj.model_dump())
            except:
                return str(obj)
        elif hasattr(obj, 'dict'):
            # Handle Pydantic v1 models
            try:
                return self._convert_floats_to_decimal(obj.dict())
            except:
                return str(obj)
        else:
            return obj
    
    def _create_report_table_if_not_exists(self):
        """Create the report analysis DynamoDB table if it doesn't exist"""
        try:
            # Check if table exists
            self.report_table.load()
            logger.info(f"Table {self.report_table_name} already exists")
        except Exception:
            # Table doesn't exist, create it
            try:
                table = self.dynamodb.create_table(
                    TableName=self.report_table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'analysis_id',
                            'KeyType': 'HASH'  # Partition key
                        },
                        {
                            'AttributeName': 'analysis_type',
                            'KeyType': 'RANGE'  # Sort key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'analysis_id',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'analysis_type',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'AttributeType': 'S'
                        }
                    ],
                    GlobalSecondaryIndexes=[
                        {
                            'IndexName': 'timestamp-index',
                            'KeySchema': [
                                {
                                    'AttributeName': 'timestamp',
                                    'KeyType': 'HASH'
                                },
                                {
                                    'AttributeName': 'analysis_id',
                                    'KeyType': 'RANGE'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            }
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                
                # Wait for table to be created
                table.wait_until_exists()
                logger.info(f"Table {self.report_table_name} created successfully")
                
            except Exception as e:
                logger.error(f"Error creating table: {e}")
                raise
    
    def _create_github_table_if_not_exists(self):
        """Create the GitHub analysis DynamoDB table if it doesn't exist"""
        try:
            # Check if table exists
            self.github_table.load()
            logger.info(f"Table {self.github_table_name} already exists")
        except Exception:
            # Table doesn't exist, create it
            try:
                table = self.dynamodb.create_table(
                    TableName=self.github_table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'analysis_id',
                            'KeyType': 'HASH'  # Partition key
                        },
                        {
                            'AttributeName': 'analysis_type',
                            'KeyType': 'RANGE'  # Sort key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'analysis_id',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'analysis_type',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'AttributeType': 'S'
                        }
                    ],
                    GlobalSecondaryIndexes=[
                        {
                            'IndexName': 'timestamp-index',
                            'KeySchema': [
                                {
                                    'AttributeName': 'timestamp',
                                    'KeyType': 'HASH'
                                },
                                {
                                    'AttributeName': 'analysis_id',
                                    'KeyType': 'RANGE'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            }
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                
                # Wait for table to be created
                table.wait_until_exists()
                logger.info(f"Table {self.github_table_name} created successfully")
                
            except Exception as e:
                logger.error(f"Error creating table: {e}")
                raise
    
    def store_analysis_result(self, analysis_data: Dict[str, Any], analysis_type: str = "report_analysis") -> str:
        """
        Store analysis result in DynamoDB
        
        Args:
            analysis_data: The complete analysis response data
            analysis_type: Type of analysis (e.g., "report_analysis", "github_analysis")
            
        Returns:
            analysis_id: The unique ID of the stored analysis
        """
        try:
            # Generate unique analysis ID
            analysis_id = str(uuid.uuid4())
            
            # Get current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Prepare item for DynamoDB
            item = {
                'analysis_id': analysis_id,
                'analysis_type': analysis_type,
                'timestamp': timestamp,
                'status': analysis_data.get('status', 'unknown'),
                'created_at': timestamp,
                'updated_at': timestamp
            }
            
            # Add analysis type specific fields
            if analysis_type == "full_repository_analysis":
                # Full repository analysis structure
                item['repository_info'] = analysis_data.get('repository_info', {})
                item['summary'] = analysis_data.get('summary', {})
                item['files_with_suggestions'] = analysis_data.get('files_with_suggestions', [])
                item['analysis_type_detail'] = 'full_repository_analysis'
            elif analysis_type == "api_performance_matching":
                # API performance matching structure
                item['repository_info'] = analysis_data.get('enhanced_analysis', {}).get('repository_info', {})
                item['summary'] = analysis_data.get('summary', '')
                item['enhanced_analysis'] = analysis_data.get('enhanced_analysis', {})
                item['performance_analysis'] = analysis_data.get('enhanced_analysis', {}).get('performance_analysis', {})
                item['implementation_roadmap'] = analysis_data.get('implementation_roadmap', {})
                item['analysis_type_detail'] = 'api_performance_matching'
            else:
                # Report analysis structure (original)
                item['analysis'] = analysis_data.get('analysis', {})
                item['summary'] = analysis_data.get('summary', '')
                item['processed_files'] = analysis_data.get('processed_files', [])
                item['skipped_files'] = analysis_data.get('skipped_files', [])
                item['thresholds_used'] = analysis_data.get('thresholds_used')
                item['analysis_type_detail'] = 'report_analysis'
            
            # Convert floats to Decimals for DynamoDB compatibility
            item = self._convert_floats_to_decimal(item)
            
            # Determine which table to use
            if analysis_type in ["full_repository_analysis", "api_performance_matching"]:
                # Store in GitHub analysis table
                self.github_table.put_item(Item=item)
                logger.info(f"GitHub analysis stored in {self.github_table_name} with ID: {analysis_id}")
            else:
                # Store in report analysis table
                self.report_table.put_item(Item=item)
                logger.info(f"Report analysis stored in {self.report_table_name} with ID: {analysis_id}")
            
            return analysis_id
            
        except Exception as e:
            logger.error(f"Error storing analysis result: {e}")
            raise
    
    def get_analysis_result(self, analysis_id: str, analysis_type: str = "report_analysis") -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis result from DynamoDB
        
        Args:
            analysis_id: The unique ID of the analysis
            analysis_type: Type of analysis
            
        Returns:
            Analysis data or None if not found
        """
        try:
            # Determine which table to use
            table = self.github_table if analysis_type in ["full_repository_analysis", "api_performance_matching"] else self.report_table
            
            response = table.get_item(
                Key={
                    'analysis_id': analysis_id,
                    'analysis_type': analysis_type
                }
            )
            
            if 'Item' in response:
                return response['Item']
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving analysis result: {e}")
            raise
    
    def get_recent_analyses(self, limit: int = 10, table_type: str = "report") -> List[Dict[str, Any]]:
        """
        Get recent analysis results
        
        Args:
            limit: Maximum number of results to return
            table_type: "report" or "github"
            
        Returns:
            List of recent analysis results
        """
        try:
            # Determine which table to use
            table = self.github_table if table_type == "github" else self.report_table
            
            # Scan table and sort by timestamp (GSI query requires partition key)
            response = table.scan(Limit=limit * 10)  # Get more items to sort
            items = response.get('Items', [])
            
            # Sort by timestamp (newest first)
            sorted_items = sorted(
                items,
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )[:limit]
            
            return sorted_items
            
        except Exception as e:
            logger.error(f"Error retrieving recent analyses: {e}")
            raise
    
    def delete_analysis_result(self, analysis_id: str, analysis_type: str = "report_analysis") -> bool:
        """
        Delete analysis result from DynamoDB
        
        Args:
            analysis_id: The unique ID of the analysis
            analysis_type: Type of analysis
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Determine which table to use
            table = self.github_table if analysis_type in ["full_repository_analysis", "api_performance_matching"] else self.report_table
            
            table.delete_item(
                Key={
                    'analysis_id': analysis_id,
                    'analysis_type': analysis_type
                }
            )
            
            logger.info(f"Analysis result deleted successfully: {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting analysis result: {e}")
            return False
    
    def store_full_repository_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """
        Store full repository analysis result in DynamoDB
        
        Args:
            analysis_data: The complete full repository analysis response data
            
        Returns:
            analysis_id: The unique ID of the stored analysis
        """
        return self.store_analysis_result(
            analysis_data,
            analysis_type="full_repository_analysis"
        )
    
    def store_api_performance_matching(self, analysis_data: Dict[str, Any]) -> str:
        """
        Store API performance matching analysis result in DynamoDB
        
        Args:
            analysis_data: The complete API performance matching analysis response data
            
        Returns:
            analysis_id: The unique ID of the stored analysis
        """
        return self.store_analysis_result(
            analysis_data,
            analysis_type="api_performance_matching"
        )
    
    def get_github_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent GitHub analyses (both full repository and API performance matching)
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of recent GitHub analysis results
        """
        try:
            # Query the GitHub table for all analysis types
            response = self.github_table.scan(
                FilterExpression=Attr('analysis_type').is_in(['full_repository_analysis', 'api_performance_matching']),
                Limit=limit * 3  # Get more to account for filtering
            )
            
            items = response.get('Items', [])
            
            # Sort by timestamp (newest first) and limit
            sorted_items = sorted(
                items,
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )[:limit]
            
            return sorted_items
            
        except Exception as e:
            logger.error(f"Error retrieving GitHub analyses: {e}")
            raise
    
    def get_analyses_by_repository(self, owner: str, repo: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get all analyses for a specific repository
        
        Args:
            owner: Repository owner/username
            repo: Repository name
            limit: Maximum number of results to return
            
        Returns:
            List of analyses for the repository
        """
        try:
            # Scan and filter by repository
            response = self.table.scan()
            items = response.get('Items', [])
            
            # Filter by repository
            filtered_items = []
            for item in items:
                repo_info = item.get('repository_info', {})
                if repo_info.get('owner') == owner and repo_info.get('repo') == repo:
                    filtered_items.append(item)
            
            # Sort by timestamp (newest first) and limit
            sorted_items = sorted(
                filtered_items,
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )[:limit]
            
            return sorted_items
            
        except Exception as e:
            logger.error(f"Error retrieving analyses by repository: {e}")
            raise