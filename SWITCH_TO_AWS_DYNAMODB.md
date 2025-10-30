# Quick Guide: Switch to AWS DynamoDB

## What Was Done

✅ Code updated to support AWS DynamoDB  
✅ Environment variable configuration added  
✅ Automatic detection of local vs AWS  

## How to Switch to AWS DynamoDB

### 1. Update `.env` file

**Current** (Local DynamoDB):
```bash
DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

**Change to** (AWS DynamoDB):
```bash
# Comment out or remove these lines:
# DYNAMODB_ENDPOINT_URL=http://localhost:1234
# USE_LOCAL_DYNAMODB=true
```

Make sure you have AWS credentials:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

### 2. Create Tables in AWS

Using AWS Console or CLI, create:

**Table: `api-performance-analysis`**
- PK: `analysis_id` (String)
- SK: `analysis_type` (String)
- GSI: `timestamp-index` on `timestamp`

**Table: `github-analysis-results`**
- PK: `analysis_id` (String)  
- SK: `analysis_type` (String)
- GSI: `timestamp-index` on `timestamp`

### 3. Restart Backend

```bash
# Backend will detect AWS mode and connect to AWS DynamoDB
```

Look for this log message:
```
Using AWS DynamoDB in region us-east-1
```

### 4. Test

Run a GitHub analysis and check AWS DynamoDB Console for data.

## Switch Back to Local

In `.env`, add back:
```bash
DYNAMODB_ENDPOINT_URL=http://localhost:1234
USE_LOCAL_DYNAMODB=true
```

Restart backend.

