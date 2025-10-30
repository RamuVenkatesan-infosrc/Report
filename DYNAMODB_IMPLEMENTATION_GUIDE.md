# DynamoDB Implementation Guide for GitHub Analysis

## Recommended Schema Design

### Table Structure (Keep Existing)
- **Table Name**: `api-performance-analysis` (already exists)
- **Primary Key**: 
  - Partition Key: `analysis_id` (String)
  - Sort Key: `analysis_type` (String) - Values: `report_analysis`, `full_repository_analysis`, `api_performance_matching`
- **GSI**: `timestamp-index` on `timestamp` field

## Schema 1: Full Repository Analysis

```python
{
    "analysis_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID v4
    "analysis_type": "full_repository_analysis",  # Sort Key
    "timestamp": "2024-01-15T10:30:00.123Z",  # ISO format
    "status": "success",  # success, error, warning
    "created_at": "2024-01-15T10:30:00.123Z",
    "updated_at": "2024-01-15T10:30:00.123Z",
    
    # Repository Information
    "repository_info": {
        "owner": "username",
        "repo": "repository-name",
        "branch": "main",
        "total_files_found": 45,
        "total_files_analyzed": 7,
        "files_skipped_config": 38,
        "files_skipped_extension": 0,
        "files_skipped_content": 0
    },
    
    # Analysis Summary
    "summary": {
        "files_with_suggestions": 3,
        "total_suggestions": 5,
        "analysis_coverage": "7/45 files analyzed"
    },
    
    # Files with AI-generated suggestions
    "files_with_suggestions": [
        {
            "file_path": "src/main.py",
            "suggestions": [
                {
                    "title": "Add error handling",
                    "description": "Missing try-catch blocks",
                    "current_code": "def func():\n    pass",
                    "improved_code": "def func():\n    try:\n        pass\n    except:\n        pass",
                    "explanation": "Add error handling",
                    "expected_improvement": "Better error handling"
                }
            ]
        }
    ]
}
```

## Schema 2: API Performance Matching

```python
{
    "analysis_id": "660e8400-e29b-41d4-a716-446655440000",  # UUID v4
    "analysis_type": "api_performance_matching",  # Sort Key
    "timestamp": "2024-01-15T10:35:00.123Z",  # ISO format
    "status": "success",
    "created_at": "2024-01-15T10:35:00.123Z",
    "updated_at": "2024-01-15T10:35:00.123Z",
    
    # Repository Information
    "repository_info": {
        "owner": "username",
        "repo": "repository-name",
        "branch": "main",
        "total_apis_discovered": 15
    },
    
    # Performance Analysis Summary
    "performance_analysis": {
        "worst_apis_count": 5,
        "matched_apis_count": 3,
        "unmatched_apis_count": 2
    },
    
    # Enhanced Analysis Results
    "enhanced_analysis": {
        "color_summary": {
            "red_apis": 2,
            "green_apis": 1,
            "total_matched": 3
        },
        
        # All APIs discovered in source code
        "discovered_apis": [
            {
                "endpoint": "/api/users",
                "file_path": "src/api/routes/users.py",
                "function_name": "get_users",
                "framework": "FastAPI",
                "line_number": 45
            }
        ],
        
        # Matched APIs with code suggestions
        "matched_apis_with_colors": [
            {
                "api_endpoint": "/api/users",
                "match_confidence": 0.95,
                "color_indicator": "red",
                "performance_issues": ["Slow response", "High errors"],
                
                "performance_metrics": {
                    "endpoint": "/api/users",
                    "avg_response_time_ms": 2500,
                    "error_rate_percent": 15,
                    "throughput_rps": 100,
                    "percentile_95_latency_ms": 3000,
                    "status": "CRITICAL"
                },
                
                "source_code_info": {
                    "file_path": "src/api/routes/users.py",
                    "function_name": "get_users",
                    "framework": "FastAPI",
                    "complexity_score": 7.5,
                    "risk_level": "HIGH"
                },
                
                "code_suggestions": [
                    {
                        "title": "Optimize query",
                        "description": "Add pagination",
                        "current_code": "return db.query(User).all()",
                        "improved_code": "return db.query(User).offset(skip).limit(limit).all()",
                        "expected_improvement": "80% faster response"
                    }
                ]
            }
        ]
    }
}
```

## Key Design Decisions

### 1. Use Single Table
- Keep all analysis types in one table
- Use `analysis_type` as sort key to distinguish
- Leverage existing `timestamp-index` GSI

### 2. Store Complete Results
- Store the full response from the analysis
- No need to reference external storage
- Easier to retrieve and display

### 3. Include Repository Info
- Track which repository was analyzed
- Support future queries by repository
- Help with analysis history

### 4. Store Code Suggestions Directly
- Include full `current_code` and `improved_code`
- Store performance metrics
- Preserve match confidence

## Implementation in DynamoDBService

### Add New Methods

```python
def store_full_repository_analysis(self, analysis_result: dict) -> str:
    """Store full repository analysis result"""
    return self.store_analysis_result(
        analysis_result,
        analysis_type="full_repository_analysis"
    )

def store_api_performance_matching(self, analysis_result: dict) -> str:
    """Store API performance matching result"""
    return self.store_analysis_result(
        analysis_result,
        analysis_type="api_performance_matching"
    )

def get_github_analyses(self, limit: int = 10):
    """Get recent GitHub analyses (both types)"""
    response = self.table.scan(
        FilterExpression="analysis_type IN (:type1, :type2)",
        ExpressionAttributeValues={
            ':type1': 'full_repository_analysis',
            ':type2': 'api_performance_matching'
        },
        Limit=limit
    )
    return sorted(
        response.get('Items', []),
        key=lambda x: x.get('timestamp', ''),
        reverse=True
    )[:limit]
```

## Integration Points

### In reportanalysis_enhanced_v2.py

Add after each analysis completes:

```python
# For Full Repository Analysis
@app.post("/analyze-full-repository/")
async def analyze_full_repository(...):
    result = ... # existing analysis logic
    # Store in DynamoDB
    dynamodb_service.store_full_repository_analysis(result)
    return result

# For API Performance Matching
@app.post("/analyze-worst-apis-with-github/")
async def analyze_worst_apis_with_github(...):
    result = ... # existing analysis logic
    # Store in DynamoDB
    dynamodb_service.store_api_performance_matching(result)
    return result
```

## Query Examples

### Get latest full repository analysis
```python
response = dynamodb_service.table.query(
    IndexName='timestamp-index',
    KeyConditionExpression='analysis_type = :type',
    ExpressionAttributeValues={':type': 'full_repository_analysis'},
    ScanIndexForward=False,
    Limit=1
)
```

### Get all analyses for a repository
```python
# Would need GSI on repository owner/repo
# Or filter after query/scan
response = dynamodb_service.table.scan(
    FilterExpression="repository_info.owner = :owner AND repository_info.repo = :repo",
    ExpressionAttributeValues={
        ':owner': 'username',
        ':repo': 'repo-name'
    }
)
```

## Benefits

1. **Unified Storage**: All analysis types in one place
2. **Easy Retrieval**: Single query for recent analyses
3. **History Tracking**: See analysis history over time
4. **Simple Implementation**: Reuse existing DynamoDB infrastructure
5. **No Schema Changes**: Works with current table structure

