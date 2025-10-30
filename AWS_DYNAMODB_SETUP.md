# AWS DynamoDB Setup Guide

## Current Status
✅ Your code now supports both LOCAL and AWS DynamoDB  
✅ Currently using LOCAL DynamoDB (http://localhost:1234)  

## To Switch to AWS DynamoDB

### Step 1: Update your `.env` file

Open `backend/.env` and make these changes:

```bash
# AWS Configuration (your existing credentials)
AWS_ACCESS_KEY_ID=your_actual_aws_key_here
AWS_SECRET_ACCESS_KEY=your_actual_aws_secret_here
AWS_REGION=us-east-1

# DynamoDB Configuration - COMMENT OUT or REMOVE local settings
# DYNAMODB_ENDPOINT_URL=http://localhost:1234
# USE_LOCAL_DYNAMODB=true
```

**OR** explicitly set:
```bash
DYNAMODB_ENDPOINT_URL=
USE_LOCAL_DYNAMODB=false
```

### Step 2: Create DynamoDB Tables in AWS

You need to create these tables in AWS DynamoDB:

#### Table 1: `api-performance-analysis`
- **Partition Key**: `analysis_id` (String)
- **Sort Key**: `analysis_type` (String)
- **GSI**: `timestamp-index` on `timestamp` field
- **Billing**: On-demand (Pay per request)

#### Table 2: `github-analysis-results`
- **Partition Key**: `analysis_id` (String)
- **Sort Key**: `analysis_type` (String)
- **GSI**: `timestamp-index` on `timestamp` field
- **Billing**: On-demand (Pay per request)

### Step 3: Using AWS Console

1. Go to **AWS Console** → **DynamoDB**
2. Click **"Create table"**
3. For each table:
   - **Table name**: `api-performance-analysis` or `github-analysis-results`
   - **Partition key**: `analysis_id` (String)
   - **Add sort key**: `analysis_type` (String)
   - **Table settings**: Customize settings (uncheck "Use default settings")
   - **Deletion protection**: Enable (recommended)
   - **Capacity**: On-demand
   - Click **"Create table"**

4. After creation, add GSI:
   - Go to table → **"Indexes"** tab → **"Create index"**
   - **Partition key**: `timestamp` (String)
   - **Sort key**: `analysis_id` (String)
   - **Index name**: `timestamp-index`
   - Click **"Create index"**

### Step 4: Restart Backend

After updating `.env`:
```bash
# Restart the backend
# It should now connect to AWS DynamoDB
```

You should see in logs:
```
Using AWS DynamoDB in region us-east-1
Using AWS credentials from environment variables
```

### Step 5: Verify Connection

Run the test script:
```bash
python test_github_dynamodb.py
```

Check AWS Console → DynamoDB → Tables → Should see your data

## Switching Back to Local DynamoDB

To use local DynamoDB again:

```bash
# In backend/.env
DYNAMODB_ENDPOINT_URL=http://localhost:1234
USE_LOCAL_DYNAMODB=true
```

## Troubleshooting

### Error: "Access Denied"
**Solution**: Check your AWS credentials and DynamoDB permissions

### Error: "Table doesn't exist"
**Solution**: Create the tables in AWS Console first

### Error: "Region not found"
**Solution**: Verify your AWS_REGION in .env is correct

### Error: "Invalid credentials"
**Solution**: Update AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env

## IAM Permissions Needed

Your AWS credentials need these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/api-performance-analysis",
        "arn:aws:dynamodb:*:*:table/github-analysis-results",
        "arn:aws:dynamodb:*:*:table/api-performance-analysis/index/*",
        "arn:aws:dynamodb:*:*:table/github-analysis-results/index/*"
      ]
    }
  ]
}
```

## Code Changes Summary

✅ Updated `dynamodb_service.py` to support both local and AWS  
✅ Added environment variable support  
✅ Automatic detection of local vs AWS based on endpoint  
✅ Logs show which mode is being used  

## Next Steps

1. Update `.env` file (remove/comment DYNAMODB_ENDPOINT_URL)
2. Create tables in AWS Console
3. Restart backend
4. Test with a GitHub analysis
5. Check data in AWS DynamoDB Console

