# Update .env File for AWS DynamoDB

## Current Issue
Line 82 in `reportanalysis_enhanced_v2.py` was hardcoded to use local DynamoDB:
```python
dynamodb_service = DynamoDBService(endpoint_url="http://localhost:1234")
```

**✅ FIXED**: Now it uses settings from `.env` file.

## To Switch to AWS DynamoDB

### Step 1: Edit `backend/.env` file

Remove or comment out this line:
```bash
# Comment this out:
# DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

Or set it to empty:
```bash
DYNAMODB_ENDPOINT_URL=
```

Make sure you have these AWS credentials:
```bash
AWS_ACCESS_KEY_ID=your_actual_key
AWS_SECRET_ACCESS_KEY=your_actual_secret
AWS_REGION=us-east-1
```

### Step 2: Restart Backend

The backend will now use AWS DynamoDB automatically.

You should see in logs:
```
Using AWS DynamoDB in region us-east-1
```

### Step 3: Verify Tables Created

✅ **NO MANUAL CREATION NEEDED** - Your service auto-creates tables!

First time you use AWS DynamoDB, it will create:
- `api-performance-analysis`
- `github-analysis-results`

## Switch Back to Local

In `backend/.env`, add back:
```bash
DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

## Summary

| Setting | Local DynamoDB | AWS DynamoDB |
|---------|---------------|--------------|
| `DYNAMODB_ENDPOINT_URL` | `http://localhost:1234` | Empty or commented |
| Table Creation | Auto | Auto |
| AWS Credentials | Not needed | Required in .env |

