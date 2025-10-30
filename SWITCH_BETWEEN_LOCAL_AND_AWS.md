# Switch Between Local and AWS DynamoDB

## Currently Using: AWS DynamoDB ✅

Your service is now connected to AWS DynamoDB successfully!

## Switch Back to Local DynamoDB

### Step 1: Edit `backend/.env` file

Add this line to use local DynamoDB:
```bash
DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

Your `.env` should have:
```bash
# AWS Configuration (still needed for Bedrock)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# DynamoDB Configuration - ADD THIS LINE FOR LOCAL
DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

### Step 2: Make sure local DynamoDB is running

Start your local DynamoDB on port 1234 (if not already running).

### Step 3: Restart Backend

After updating `.env`, restart the backend.

**Expected log output:**
```
Using LOCAL DynamoDB at http://localhost:1234
Table api-performance-analysis already exists
Table github-analysis-results already exists
```

---

## Switch Back to AWS DynamoDB

### Step 1: Edit `backend/.env` file

Remove or comment out the local endpoint:
```bash
# DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

### Step 2: Restart Backend

**Expected log output:**
```
Using AWS DynamoDB in region us-east-1
Using AWS credentials from environment variables
Table api-performance-analysis already exists
Table github-analysis-results already exists
```

---

## Summary

| Setting | Local DynamoDB | AWS DynamoDB |
|---------|---------------|--------------|
| **Add to .env** | `DYNAMODB_ENDPOINT_URL=http://localhost:1234` | Comment out or remove that line |
| **DynamoDB** | Must be running locally on port 1234 | Must have AWS credentials in .env |
| **Tables** | Auto-created locally | Already exist in AWS (or auto-created) |

## Quick Toggle

**To Local:**
```bash
# In .env
DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

**To AWS:**
```bash
# In .env
# DYNAMODB_ENDPOINT_URL=http://localhost:1234
```

Just comment/uncomment that one line and restart backend!

