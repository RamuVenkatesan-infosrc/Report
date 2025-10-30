# DynamoDB Schemas for GitHub Analysis

## Current Structure
The existing DynamoDB table `api-performance-analysis` uses:
- **Primary Key**: `analysis_id` (Partition Key) + `analysis_type` (Sort Key)
- **GSI**: `timestamp-index` on `timestamp` field

## Proposed Schemas

### 1. Full Repository Analysis Schema

**analysis_type**: `"full_repository_analysis"`

```json
{
  "analysis_id": "uuid-v4",
  "analysis_type": "full_repository_analysis",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "success",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  
  "repository_info": {
    "owner": "RamuVenkatesan-infosrc",
    "repo": "test-case-genrator",
    "branch": "main",
    "total_files_found": 45,
    "total_files_analyzed": 7,
    "files_skipped_config": 38,
    "files_skipped_extension": 0,
    "files_skipped_content": 0
  },
  
  "summary": {
    "files_with_suggestions": 3,
    "total_suggestions": 5,
    "analysis_coverage": "7/45 files analyzed"
  },
  
  "files_with_suggestions": [
    {
      "file_path": "src/main.py",
      "suggestions": [
        {
          "title": "Add error handling",
          "issue": "Missing try-catch blocks",
          "description": "The function lacks proper error handling which could cause crashes",
          "explanation": "Add try-except blocks to handle potential exceptions",
          "current_code": "def process_data(data):\n    result = data * 2\n    return result",
          "improved_code": "def process_data(data):\n    try:\n        result = data * 2\n        return result\n    except Exception as e:\n        logger.error(f'Error processing data: {e}')\n        raise",
          "expected_improvement": "Prevents crashes and improves error visibility",
          "summary": "Add proper error handling with try-except blocks",
          "diff": "- def process_data(data):\n+ def process_data(data):\n+     try:"
        }
      ]
    }
  ]
}
```

### 2. API Performance Matching Analysis Schema

**analysis_type**: `"api_performance_matching"`

```json
{
  "analysis_id": "uuid-v4",
  "analysis_type": "api_performance_matching",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "success",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  
  "repository_info": {
    "owner": "RamuVenkatesan-infosrc",
    "repo": "test-case-genrator",
    "branch": "main",
    "total_apis_discovered": 15
  },
  
  "performance_analysis": {
    "worst_apis_count": 5,
    "matched_apis_count": 3,
    "unmatched_apis_count": 2
  },
  
  "enhanced_analysis": {
    "color_summary": {
      "red_apis": 2,
      "green_apis": 1,
      "total_matched": 3
    },
    
    "discovered_apis": [
      {
        "endpoint": "/api/users",
        "file_path": "src/api/routes/users.py",
        "function_name": "get_users",
        "framework": "FastAPI",
        "line_number": 45,
        "code_snippet": "@app.get('/api/users')\ndef get_users():\n    return db.query(User).all()"
      }
    ],
    
    "matched_apis_with_colors": [
      {
        "api_endpoint": "/api/users",
        "match_confidence": 0.95,
        "color_indicator": "red",
        "performance_issues": ["Slow response time", "High error rate"],
        
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
          "risk_level": "HIGH",
          "code_snippet": "@app.get('/api/users')\ndef get_users():\n    return db.query(User).all()",
          "line_number": 45
        },
        
        "code_suggestions": [
          {
            "title": "Optimize database query",
            "issue": "No pagination and eager loading all data",
            "description": "The query loads all users without pagination, causing slow response times",
            "explanation": "Add pagination and limit the result set to improve performance",
            "current_code": "@app.get('/api/users')\ndef get_users():\n    return db.query(User).all()",
            "improved_code": "@app.get('/api/users')\ndef get_users(skip: int = 0, limit: int = 100):\n    return db.query(User).offset(skip).limit(limit).all()",
            "expected_improvement": "Reduces response time by 80% and prevents memory issues",
            "summary": "Add pagination with offset and limit parameters"
          }
        ]
      }
    ]
  },
  
  "worst_apis_input": [
    {
      "endpoint": "/api/users",
      "avg_response_time_ms": 2500,
      "error_rate_percent": 15,
      "throughput_rps": 100,
      "percentile_95_latency_ms": 3000
    }
  ]
}
```

## Additional Metadata Fields (Common to Both)

Both schemas can optionally include:

```json
{
  "metadata": {
    "github_token_used": false,
    "analysis_duration_ms": 5000,
    "ai_model_used": "claude-sonnet",
    "total_tokens_used": 15000,
    "user_id": "optional-user-id"
  }
}
```

## Proposed Table Structure

### Option 1: Single Table (Recommended)
Keep using the existing table structure with different `analysis_type` values:
- `report_analysis` - Current report analysis
- `full_repository_analysis` - Full repository code analysis
- `api_performance_matching` - API performance matching

**Pros**: Simple, uses existing infrastructure
**Cons**: Different schemas in same table

### Option 2: Separate Tables
Create separate tables for each analysis type:
- `api-performance-analysis` - Report analysis
- `github-full-repository-analysis` - Full repository analysis  
- `github-api-performance-matching` - API performance matching

**Pros**: Better schema isolation
**Cons**: More complex, need to manage multiple tables

## Recommendations

**Use Option 1 (Single Table)** because:
1. Already has the infrastructure
2. Easier to query across analysis types
3. Single GSI can handle all types
4. Can add filtering by `analysis_type` in queries

## Implementation Notes

1. **Data Size**: Code snippets can be large, consider using S3 for very large payloads
2. **TTL**: Consider adding a TTL attribute for automatic cleanup of old analyses
3. **Compression**: Consider compressing large JSON objects
4. **Partitioning**: Current UUID approach works well for distributed writes
5. **Queries**: Use GSI on timestamp for recent analyses

## Query Patterns

### Get all GitHub analyses
```python
response = table.query(
    KeyConditionExpression=Key('analysis_id').begins_with('github')
)
```

### Get recent full repository analyses
```python
response = table.query(
    IndexName='timestamp-index',
    KeyConditionExpression=Key('analysis_type').eq('full_repository_analysis'),
    ScanIndexForward=False,
    Limit=10
)
```

### Get analysis by repository
(Would need additional GSI on repository info)

## Schema Validation

Consider adding validation in the service layer to ensure:
- Required fields are present
- Code snippets don't exceed size limits
- Repository info is properly formatted
- Analysis types are valid

