# 🚀 Enhanced API Performance Analyzer - Usage Guide

## Quick Start

### 1. Setup Configuration

**Option A: Using the Web Interface (Recommended)**
1. Start the application: `uvicorn reportanalysis_enhanced:app --reload`
2. Open your browser: `http://localhost:8000`
3. Enter your GitHub token in the web interface
4. Click "Configure GitHub Token"

**Option B: Using the Setup Script**
```bash
python setup_config.py
```

**Option C: Manual Configuration**
1. Copy `env.template` to `.env`
2. Edit `.env` with your credentials:
```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
GITHUB_TOKEN=your_github_token
```

### 2. Get GitHub Token

1. Go to [GitHub.com](https://github.com) and sign in
2. Click your profile picture → **Settings**
3. Scroll down and click **Developer settings**
4. Click **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token** → **Generate new token (classic)**
6. Give it a name: "API Performance Analyzer"
7. Select scope: **repo** (Full control of private repositories)
8. Click **Generate token**
9. Copy the token (starts with `ghp_`)

## API Usage

### Basic Performance Analysis

```bash
curl -X POST "http://localhost:8000/analyze-report/" \
  -F "file=@performance_report.xml" \
  -F "response_time_bad_threshold=1000"
```

### Enhanced Analysis with GitHub Integration

```bash
curl -X POST "http://localhost:8000/analyze-with-github/" \
  -F "file=@performance_report.xml" \
  -F "github_repo=your-org/your-api-repo" \
  -F "response_time_bad_threshold=1000"
```

### Configure GitHub Token via API

```bash
curl -X POST "http://localhost:8000/github/configure-token?token=ghp_your_token_here"
```

### Check Token Status

```bash
curl "http://localhost:8000/github/token-status"
```

### Search GitHub Repositories

```bash
curl "http://localhost:8000/github/repositories?query=fastapi&language=python"
```

## Web Interface

Visit `http://localhost:8000` for a user-friendly interface that allows you to:

- ✅ Configure GitHub token
- ✅ Check token status
- ✅ View all available endpoints
- ✅ See usage examples
- ✅ Test API connectivity

## Analysis Types

### 1. Reactive Analysis (Matches Found)
When performance APIs match with source code:
- **Root Cause Analysis**: Specific reasons for poor performance
- **Code Quality Issues**: Code patterns causing problems
- **Detailed Improvements**: Specific code suggestions with examples
- **Implementation Plan**: Step-by-step improvement roadmap

### 2. Proactive Analysis (No Matches)
When no matches are found:
- **API Discovery**: All APIs found in source code
- **Risk Assessment**: Categorize APIs by risk level
- **Proactive Recommendations**: Suggest improvements before issues occur
- **Code Quality Analysis**: Review all APIs for potential issues

## Example Workflow

1. **Upload Performance Report**: Upload your JMeter/Locust report
2. **Specify GitHub Repository**: Provide repository in format `owner/repo`
3. **Set Thresholds**: Define what constitutes "bad" performance
4. **Get Analysis**: Receive detailed analysis with:
   - Root cause analysis
   - Code quality issues
   - Specific code improvements
   - Implementation roadmap
   - Priority recommendations

## Response Examples

### Enhanced Analysis Response
```json
{
  "status": "success",
  "analysis_type": "reactive",
  "matching_status": "matches_found",
  "total_apis_analyzed": 25,
  "matched_apis_count": 3,
  "high_risk_apis": 8,
  "results": {
    "matched_apis": [
      {
        "api_endpoint": "/api/users/{id}",
        "root_causes": [
          {
            "category": "database_optimization",
            "severity": "HIGH",
            "description": "N+1 query problem detected",
            "impact_percentage": 80.0
          }
        ],
        "improvements": [
          {
            "priority": "HIGH",
            "title": "Fix N+1 Query Problem",
            "current_code": "for user_id in user_ids:\n    user = db.query(User).filter(User.id == user_id).first()",
            "improved_code": "users = db.query(User).filter(User.id.in_(user_ids)).all()",
            "expected_improvement": "Reduce response time by 70%"
          }
        ]
      }
    ]
  },
  "implementation_roadmap": {
    "immediate_actions": ["Fix N+1 queries", "Add caching"],
    "short_term": ["Input validation", "Error handling"],
    "long_term": ["Code refactoring", "Monitoring"]
  }
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the backend directory
2. **GitHub Token Invalid**: Check token format and permissions
3. **AWS Credentials Missing**: Configure AWS credentials for Bedrock
4. **Repository Not Found**: Verify repository name format `owner/repo`

### Error Messages

- `"No APIs found in repository"`: Repository doesn't contain API code or token lacks access
- `"Invalid GitHub token format"`: Token should start with `ghp_`, `gho_`, `ghu_`, `ghs_`, or `ghr_`
- `"AWS credentials missing"`: Configure AWS credentials for AI analysis

### Getting Help

1. Check the web interface at `http://localhost:8000`
2. View application logs for detailed error messages
3. Verify all environment variables are set correctly
4. Test GitHub token with `/github/token-status` endpoint

## Advanced Features

### Custom Thresholds
- `response_time_good_threshold`: Max acceptable response time (ms)
- `response_time_bad_threshold`: Min response time for "Bad" (ms)
- `error_rate_good_threshold`: Max acceptable error rate (%)
- `error_rate_bad_threshold`: Min error rate for "Bad" (%)
- `throughput_good_threshold`: Min acceptable throughput (RPS)
- `throughput_bad_threshold`: Max throughput for "Bad" (RPS)

### Supported File Formats
- **JMeter**: XML, CSV, JTL, statistics.json
- **Locust**: CSV
- **ZIP Archives**: Multiple files in supported formats

### Supported Frameworks
- **FastAPI**: Python web framework
- **Flask**: Python microframework
- **Spring Boot**: Java framework
- **Express.js**: Node.js framework

## Next Steps

1. **Start with Basic Analysis**: Use `/analyze-report/` for performance analysis
2. **Add GitHub Integration**: Use `/analyze-with-github/` for enhanced analysis
3. **Configure Monitoring**: Set up regular analysis workflows
4. **Implement Improvements**: Follow the provided code suggestions
5. **Track Progress**: Monitor performance improvements over time

Happy analyzing! 🎉
