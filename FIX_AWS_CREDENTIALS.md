# Fix AWS Credentials Error

## Current Status
✅ Successfully connecting to AWS DynamoDB  
❌ AWS credentials are invalid: "The security token included in the request is invalid"

## Problem
Your AWS credentials in `.env` file are invalid, expired, or incorrect.

## Solution

### Step 1: Get Your AWS Credentials

You need to get fresh AWS credentials from AWS Console:

1. Go to **AWS Console** → **IAM** → **Users**
2. Click on your user
3. Go to **"Security credentials"** tab
4. Click **"Create access key"** (or use existing one)
5. Copy:
   - **Access key ID**
   - **Secret access key** (shown only once!)

### Step 2: Update `.env` File

Edit `backend/.env` file:

```bash
# AWS Configuration - UPDATE THESE WITH VALID CREDENTIALS
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXXX        # Your actual access key
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Your actual secret key
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
MAX_TOKENS=4000
TEMPERATURE=0.7
ENABLE_BEDROCK=true

# GitHub Configuration
GITHUB_TOKEN=your_github_token

# DynamoDB Configuration - LEAVE COMMENTED for AWS
# DYNAMODB_ENDPOINT_URL=http://localhost:1234

# Application Configuration
LOG_LEVEL=INFO
```

### Step 3: Verify Credentials

Run this test to check if credentials work:

```bash
python test_aws_credentials.py
```

### Step 4: Restart Backend

After updating `.env`:
```bash
# Restart backend
```

### Expected Log Output

After fix, you should see:
```
Using AWS DynamoDB in region us-east-1
Using AWS credentials from environment variables
Table api-performance-analysis created successfully
Table github-analysis-results created successfully
```

## Alternative: Use IAM Role (if on EC2)

If running on EC2, you can use IAM role instead of access keys:

```bash
# In .env, remove or comment out:
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=

# The code will automatically use IAM role credentials
```

## Common Issues

1. **Copy-paste errors**: Extra spaces, missing characters
2. **Expired keys**: Keys older than 90MB days may be disabled
3. **Wrong user**: User doesn't have DynamoDB permissions
4. **Region mismatch**: AWS_REGION should match where you want to create tables

## Need DynamoDB Permissions?

Your IAM user needs these permissions:
- `dynamodb:CreateTable`
- `dynamodb:DescribeTable`
- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `dynamodb:Query`

