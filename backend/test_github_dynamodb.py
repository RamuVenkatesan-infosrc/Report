"""
Test script to verify GitHub analysis DynamoDB storage
"""
import json
from app.services.dynamodb_service import DynamoDBService
from app.models.config import Settings

def test_github_analysis_storage():
    """Test storing GitHub analysis results in DynamoDB"""
    
    print("=" * 60)
    print("Testing GitHub Analysis DynamoDB Storage")
    print("=" * 60)
    
    # Initialize service
    settings = Settings()
    dynamodb = DynamoDBService()
    
    # Test 1: Store Full Repository Analysis
    print("\n1. Testing Full Repository Analysis Storage...")
    
    full_repo_data = {
        "status": "success",
        "analysis_type": "full_repository_analysis",
        "repository_info": {
            "owner": "test-user",
            "repo": "test-repo",
            "branch": "main",
            "total_files_found": 10,
            "total_files_analyzed": 5,
            "files_skipped_config": 3,
            "files_skipped_extension": 1,
            "files_skipped_content": 1
        },
        "files_with_suggestions": [
            {
                "file_path": "src/main.py",
                "suggestions": [
                    {
                        "title": "Add error handling",
                        "description": "Missing try-catch blocks",
                        "current_code": "def func(): pass",
                        "improved_code": "def func():\n    try:\n        pass\n    except:\n        pass",
                        "explanation": "Add error handling",
                        "expected_improvement": "Better error handling"
                    }
                ]
            }
        ],
        "summary": {
            "files_with_suggestions": 1,
            "total_suggestions": 1,
            "analysis_coverage": "5/10 files analyzed"
        }
    }
    
    try:
        analysis_id = dynamodb.store_full_repository_analysis(full_repo_data)
        print(f"   ✅ Successfully stored with ID: {analysis_id}")
        
        # Retrieve it
        result = dynamodb.get_analysis_result(analysis_id, "full_repository_analysis")
        if result:
            print(f"   ✅ Successfully retrieved from DynamoDB")
            print(f"   Repository: {result['repository_info']['owner']}/{result['repository_info']['repo']}")
        else:
            print(f"   ❌ Failed to retrieve from DynamoDB")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Store API Performance Matching Analysis
    print("\n2. Testing API Performance Matching Storage...")
    
    api_perf_data = {
        "status": "success",
        "analysis_type": "worst_apis_github_comparison_with_colors",
        "enhanced_analysis": {
            "repository_info": {
                "owner": "test-user",
                "repo": "test-repo",
                "branch": "main",
                "total_apis_discovered": 5
            },
            "performance_analysis": {
                "worst_apis_count": 2,
                "matched_apis_count": 1,
                "unmatched_apis_count": 1
            },
            "color_summary": {
                "red_apis": 1,
                "green_apis": 0,
                "total_matched": 1
            },
            "discovered_apis": [
                {
                    "endpoint": "/api/test",
                    "file_path": "src/api/test.py",
                    "function_name": "test_func",
                    "framework": "FastAPI"
                }
            ],
            "matched_apis_with_colors": [
                {
                    "api_endpoint": "/api/test",
                    "match_confidence": 0.95,
                    "color_indicator": "red",
                    "performance_metrics": {
                        "endpoint": "/api/test",
                        "avg_response_time_ms": 2000,
                        "error_rate_percent": 10
                    },
                    "code_suggestions": [
                        {
                            "title": "Optimize query",
                            "description": "Add pagination",
                            "current_code": "return db.query().all()",
                            "improved_code": "return db.query().offset(skip).limit(limit).all()",
                            "expected_improvement": "80% faster"
                        }
                    ]
                }
            ]
        },
        "summary": "Test analysis completed"
    }
    
    try:
        analysis_id = dynamodb.store_api_performance_matching(api_perf_data)
        print(f"   ✅ Successfully stored with ID: {analysis_id}")
        
        # Retrieve it
        result = dynamodb.get_analysis_result(analysis_id, "api_performance_matching")
        if result:
            print(f"   ✅ Successfully retrieved from DynamoDB")
            print(f"   Matched APIs: {result['performance_analysis']['matched_apis_count']}")
        else:
            print(f"   ❌ Failed to retrieve from DynamoDB")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Get Recent GitHub Analyses
    print("\n3. Testing Get Recent GitHub Analyses...")
    
    try:
        recent = dynamodb.get_github_analyses(limit=5)
        print(f"   ✅ Retrieved {len(recent)} recent GitHub analyses")
        for idx, analysis in enumerate(recent, 1):
            print(f"   {idx}. Type: {analysis['analysis_type']}, Status: {analysis['status']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Verify Tables
    print("\n4. Verifying Tables...")
    
    try:
        # Try to query both tables
        report_recent = dynamodb.get_recent_analyses(limit=1, table_type="report")
        github_recent = dynamodb.get_recent_analyses(limit=1, table_type="github")
        print(f"   ✅ Report table: {len(report_recent)} items")
        print(f"   ✅ GitHub table: {len(github_recent)} items")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_github_analysis_storage()
