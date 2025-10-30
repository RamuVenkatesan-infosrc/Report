# Enhanced API Performance Analyzer with GitHub Integration

A comprehensive FastAPI-based system that combines performance analysis with GitHub source code analysis to provide AI-powered recommendations for API improvements.

## 🚀 Features

### Core Functionality
- **Performance Report Analysis**: Analyze JMeter, Locust, and other performance testing reports
- **GitHub Integration**: Discover and analyze APIs from GitHub repositories
- **AI-Powered Recommendations**: Use AWS Bedrock for intelligent code analysis and suggestions
- **Smart API Matching**: Match performance issues with source code APIs
- **Proactive Analysis**: Analyze all APIs in source code even without performance data

### Advanced Capabilities
- **Root Cause Analysis**: Identify specific reasons for poor performance
- **Code Quality Assessment**: Analyze code patterns and potential issues
- **Detailed Code Suggestions**: Provide specific code improvements with before/after examples
- **Implementation Roadmaps**: Step-by-step improvement plans
- **Risk Assessment**: Categorize APIs by risk level and priority

## 📁 Project Structure

```
backend/
├── parsers/                    # Report parsing modules
│   ├── __init__.py
│   ├── jmeter_parser.py       # JMeter XML, CSV, JSON parsers
│   ├── locust_parser.py       # Locust CSV parser
│   └── parser_factory.py      # Parser factory and ZIP processing
├── analyzers/                  # Analysis engines
│   ├── __init__.py
│   ├── performance_analyzer.py # Core performance analysis
│   └── code_analyzer.py       # Deep code analysis
├── services/                   # External service integrations
│   ├── __init__.py
│   ├── bedrock_service.py     # AWS Bedrock AI integration
│   ├── github_service.py      # GitHub API integration
│   ├── api_matcher.py         # API matching engine
│   └── ai_github_analyzer.py  # AI-powered analysis
├── models/                     # Data models and schemas
│   ├── __init__.py
│   ├── schemas.py             # Original Pydantic models
│   ├── improvement_models.py  # Enhanced models for new features
│   └── config.py              # Configuration settings
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── file_processor.py      # File processing utilities
│   └── validators.py          # Input validation
├── reportanalysis.py          # Original application
├── reportanalysis_refactored.py # Refactored modular version
├── reportanalysis_enhanced.py # Enhanced version with GitHub integration
├── requirements.txt           # Python dependencies
└── env.template              # Environment variables template
```

## 🛠️ Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp env.template .env
   # Edit .env with your credentials
   ```

3. **Set up Environment Variables**:
   ```env
   # AWS Configuration
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=us-east-1
   
   # GitHub Configuration
   GITHUB_TOKEN=your_github_token
   
   # Application Configuration
   LOG_LEVEL=INFO
   ```

## 🚀 Usage

### 1. Original Performance Analysis
```bash
python reportanalysis.py
# or
python reportanalysis_refactored.py
```

**Endpoint**: `POST /analyze-report/`
- Upload performance reports (XML, CSV, JTL, JSON, ZIP)
- Get performance analysis with thresholds
- Receive AI-generated summaries

### 2. Enhanced Analysis with GitHub Integration
```bash
python reportanalysis_enhanced.py
```

**Endpoint**: `POST /analyze-with-github/`
- Upload performance reports
- Specify GitHub repository (`owner/repo`)
- Get detailed analysis with code suggestions

**Example Request**:
```bash
curl -X POST "http://localhost:8000/analyze-with-github/" \
  -F "file=@performance_report.xml" \
  -F "github_repo=your-org/your-api-repo" \
  -F "response_time_bad_threshold=1000"
```

### 3. GitHub Repository Search
**Endpoint**: `GET /github/repositories`
- Search for repositories
- Filter by programming language

## 📊 API Endpoints

### Performance Analysis
- `POST /analyze-report/` - Original performance analysis
- `POST /analyze-with-github/` - Enhanced analysis with GitHub integration
- `GET /health` - Health check

### GitHub Integration
- `GET /github/repositories` - Search GitHub repositories

## 🔍 Analysis Types

### 1. Reactive Analysis (Matches Found)
When performance APIs match with source code APIs:
- **Root Cause Analysis**: Identify specific performance issues
- **Code Quality Issues**: Find code patterns causing problems
- **Detailed Improvements**: Specific code suggestions with examples
- **Implementation Plan**: Step-by-step improvement roadmap

### 2. Proactive Analysis (No Matches)
When no matches are found:
- **API Discovery**: List all APIs found in source code
- **Risk Assessment**: Categorize APIs by risk level
- **Proactive Recommendations**: Suggest improvements before issues occur
- **Code Quality Analysis**: Review all APIs for potential issues

## 📈 Response Examples

### Enhanced Analysis Response
```json
{
  "status": "success",
  "analysis_type": "reactive",
  "matching_status": "matches_found",
  "total_apis_analyzed": 25,
  "matched_apis_count": 3,
  "discovered_apis_count": 25,
  "high_risk_apis": 8,
  "medium_risk_apis": 12,
  "low_risk_apis": 5,
  "results": {
    "matched_apis": [
      {
        "api_endpoint": "/api/users/{id}",
        "match_confidence": 0.85,
        "performance_metrics": {
          "avg_response_time_ms": 2500,
          "error_rate_percent": 15.5,
          "throughput_rps": 45
        },
        "root_causes": [
          {
            "category": "database_optimization",
            "severity": "HIGH",
            "description": "N+1 query problem detected",
            "evidence": "Found loop with database queries",
            "impact_percentage": 80.0
          }
        ],
        "improvements": [
          {
            "priority": "HIGH",
            "title": "Fix N+1 Query Problem",
            "current_code": "for user_id in user_ids:\n    user = db.query(User).filter(User.id == user_id).first()",
            "improved_code": "users = db.query(User).filter(User.id.in_(user_ids)).all()",
            "expected_improvement": "Reduce response time by 70%",
            "implementation_effort": "LOW"
          }
        ]
      }
    ]
  },
  "summary": "Found 3 matching APIs with detailed analysis. 8 high-risk APIs need attention.",
  "implementation_roadmap": {
    "immediate_actions": ["Fix N+1 queries", "Add caching"],
    "short_term": ["Input validation", "Error handling"],
    "long_term": ["Code refactoring", "Monitoring"]
  }
}
```

## 🎯 Key Benefits

### For Developers
- **Specific Code Suggestions**: Get exact code improvements with examples
- **Root Cause Analysis**: Understand why APIs are performing poorly
- **Implementation Guidance**: Step-by-step improvement plans
- **Proactive Prevention**: Catch issues before they become problems

### For Teams
- **Comprehensive Coverage**: Analyze entire codebase, not just problematic APIs
- **Priority Guidance**: Focus on high-impact improvements first
- **Knowledge Transfer**: Learn from AI analysis and recommendations
- **Continuous Improvement**: Regular analysis and recommendations

### For Organizations
- **Performance Optimization**: Systematic approach to API improvement
- **Code Quality**: Improve overall codebase quality
- **Risk Management**: Identify and address potential issues early
- **Resource Planning**: Estimate effort and impact of improvements

## 🔧 Configuration

### Environment Variables
- `AWS_ACCESS_KEY_ID`: AWS access key for Bedrock
- `AWS_SECRET_ACCESS_KEY`: AWS secret key for Bedrock
- `AWS_REGION`: AWS region (default: us-east-1)
- `GITHUB_TOKEN`: GitHub personal access token
- `LOG_LEVEL`: Logging level (default: INFO)

### GitHub Token Setup
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate new token with `repo` scope
3. Add token to `.env` file

## 🚀 Advanced Features

### AI-Powered Analysis
- **Context-Aware**: Combines performance data with source code
- **Framework-Specific**: Understands FastAPI, Flask, Spring Boot, Express.js
- **Pattern Recognition**: Identifies common performance anti-patterns
- **Code Generation**: Provides specific code improvements

### Smart Matching
- **Fuzzy Matching**: Handles variations in API naming
- **Confidence Scoring**: Rates match quality and reliability
- **Fallback Analysis**: Analyzes all APIs when no matches found
- **Multi-Framework Support**: Works with various API frameworks

### Comprehensive Reporting
- **Detailed Analysis**: Root causes, code quality, improvements
- **Implementation Plans**: Phased approach to improvements
- **Risk Assessment**: Categorize APIs by risk level
- **Progress Tracking**: Monitor improvement implementation

## 🔮 Future Enhancements

- **Automated Fixes**: Generate pull requests with suggested changes
- **Integration Testing**: Test recommendations before implementation
- **Performance Monitoring**: Track improvement impact over time
- **Team Collaboration**: Share recommendations with development teams
- **Learning System**: Improve recommendations based on implementation results

## 📝 License

This project is part of the API Performance Analyzer system.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the logs for error details
2. Verify environment configuration
3. Ensure GitHub token has proper permissions
4. Check AWS Bedrock access and region settings
