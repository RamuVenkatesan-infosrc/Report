# API Performance Analyzer - Refactored

A modular FastAPI-based application for analyzing performance testing reports with AWS Bedrock integration.

## Project Structure

```
backend/
├── parsers/                    # Report parsing modules
│   ├── __init__.py
│   ├── jmeter_parser.py       # JMeter XML, CSV, JSON parsers
│   ├── locust_parser.py       # Locust CSV parser
│   └── parser_factory.py      # Parser factory and ZIP processing
├── analyzers/                  # Performance analysis logic
│   ├── __init__.py
│   └── performance_analyzer.py # Core analysis algorithms
├── services/                   # External service integrations
│   ├── __init__.py
│   └── bedrock_service.py     # AWS Bedrock AI integration
├── models/                     # Data models and schemas
│   ├── __init__.py
│   ├── schemas.py             # Pydantic models
│   └── config.py              # Configuration settings
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── file_processor.py      # File processing utilities
│   └── validators.py          # Input validation
├── reportanalysis.py          # Original monolithic file
├── reportanalysis_refactored.py # New modular main file
├── requirements.txt           # Python dependencies
└── env.template              # Environment variables template
```

## Key Improvements

### 1. **Modular Architecture**
- **Separation of Concerns**: Each module has a specific responsibility
- **Maintainability**: Easier to modify and extend individual components
- **Testability**: Each module can be tested independently
- **Reusability**: Components can be reused across different parts of the application

### 2. **Enhanced Data Models**
- **Pydantic Integration**: Type-safe data validation and serialization
- **Clear Schemas**: Well-defined data structures for all API interactions
- **Configuration Management**: Centralized settings with environment variable support

### 3. **Improved Error Handling**
- **Input Validation**: Comprehensive validation for file types and thresholds
- **Specific Exceptions**: Clear error messages for different failure scenarios
- **Graceful Degradation**: Better handling of AWS service unavailability

### 4. **Better Code Organization**
- **Single Responsibility**: Each function has one clear purpose
- **Dependency Injection**: Services are injected rather than hardcoded
- **Clean Interfaces**: Clear APIs between modules

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp env.template .env
   # Edit .env with your AWS credentials and settings
   ```

3. **Run the Application**:
   ```bash
   # Original version
   python reportanalysis.py
   
   # Refactored version
   python reportanalysis_refactored.py
   ```

## API Endpoints

### POST `/analyze-report/`
Analyze performance reports from uploaded files.

**Parameters:**
- `file`: Uploaded file (XML, CSV, JTL, JSON, or ZIP)
- `response_time_good_threshold`: Max acceptable response time (ms)
- `response_time_bad_threshold`: Min response time for "Bad" (ms)
- `error_rate_good_threshold`: Max acceptable error rate (%)
- `error_rate_bad_threshold`: Min error rate for "Bad" (%)
- `throughput_good_threshold`: Min acceptable throughput (RPS)
- `throughput_bad_threshold`: Max throughput for "Bad" (RPS)
- `percentile_95_latency_good_threshold`: Max acceptable 95th percentile latency (ms)
- `percentile_95_latency_bad_threshold`: Min 95th percentile latency for "Bad" (ms)

### GET `/health`
Health check endpoint for monitoring.

## Supported File Formats

- **JMeter**: XML, CSV, JTL, statistics.json
- **Locust**: CSV
- **ZIP Archives**: Multiple files in supported formats

## Configuration

Environment variables in `.env`:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
MAX_TOKENS=300
TEMPERATURE=0.7

# Application Configuration
LOG_LEVEL=INFO
```

## Benefits of Refactoring

1. **Maintainability**: Easier to understand and modify code
2. **Scalability**: Can easily add new parsers or analyzers
3. **Testing**: Each module can be unit tested independently
4. **Team Development**: Multiple developers can work on different modules
5. **Code Reuse**: Components can be reused in other projects
6. **Error Isolation**: Issues are contained within specific modules
7. **Documentation**: Clear structure makes code self-documenting

## Migration Guide

To migrate from the original `reportanalysis.py` to the refactored version:

1. **Update Imports**: Change import statements to use the new modules
2. **Environment Setup**: Use the new configuration system
3. **API Changes**: The API interface remains the same, so no client changes needed
4. **Testing**: Update tests to work with the new modular structure

## Future Enhancements

The modular structure makes it easy to add:
- New report parsers (Gatling, Artillery, etc.)
- Additional analysis algorithms
- Different AI service providers
- Database storage
- Caching mechanisms
- Authentication and authorization
- Rate limiting
- Monitoring and metrics
