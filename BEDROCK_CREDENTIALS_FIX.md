# Bedrock Credentials Fix - Local vs Production

## Problem
Code suggestions work in local development but fail in production (Lambda). This is because:
- **Local**: Uses explicit AWS credentials from `.env` file
- **Production (Lambda)**: Should use IAM role credentials automatically

## Solution Applied

### 1. Updated `bedrock_service.py`
The service now automatically detects the environment and uses the appropriate credential method:

```python
# In Lambda (production): Uses IAM role automatically
# In local development: Uses explicit credentials from .env if provided
```

**Key Changes:**
- Detects Lambda environment using `AWS_EXECUTION_ENV`, `LAMBDA_TASK_ROOT`, or `AWS_LAMBDA_FUNCTION_NAME`
- In Lambda: **Does NOT pass explicit credentials** - boto3 automatically uses IAM role
- In Local: Uses `aws_access_key_id` and `aws_secret_access_key` from `.env` if provided
- Improved logging to show which credential method is being used

### 2. Lambda IAM Role Permissions
Ensure your Lambda execution role has Bedrock permissions (already configured in `serverless.yml`):
```yaml
- Effect: Allow
  Action:
    - bedrock:InvokeModel
    - bedrock:ListModels
    - bedrock:GetModel
  Resource: "*"
```

## How It Works

### Local Development
1. Reads credentials from `.env` file:
   ```
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   ```
2. Passes explicit credentials to boto3 client
3. Logs: `"Bedrock client initialized with explicit credentials (local development)"`

### Production (Lambda)
1. Detects Lambda environment automatically
2. **Does NOT pass explicit credentials** to boto3
3. boto3 automatically uses the Lambda execution role's IAM credentials
4. Logs: `"Bedrock client initialized with IAM role (Lambda environment)"`

## Verification

### Check CloudWatch Logs
After deployment, check Lambda logs for:
- ✅ `"Bedrock client initialized with IAM role (Lambda environment)"` - Good!
- ❌ `"Failed to initialize Bedrock client"` - Check IAM permissions

### Common Issues

1. **"Access Denied" in Lambda**
   - Check Lambda execution role has `bedrock:InvokeModel` permission
   - Verify IAM role is attached to the Lambda function

2. **Still using explicit credentials in Lambda**
   - The code now prevents this - it won't pass explicit credentials in Lambda
   - Remove `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from Lambda environment variables

3. **Works locally but not in Lambda**
   - Ensure Bedrock model access is enabled in your AWS account
   - Check CloudWatch logs for specific error messages
   - Verify the Lambda execution role has the correct permissions

## Testing

### Local Test
```bash
# Ensure .env has credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
ENABLE_BEDROCK=true

# Run locally
uvicorn reportanalysis_enhanced_v2:app --reload
```

### Production Test
1. Deploy: `serverless deploy`
2. Check CloudWatch logs for Bedrock initialization message
3. Test the `/analyze-worst-apis-with-github/` endpoint
4. Verify code suggestions are generated

## Summary

✅ **Local**: Uses `.env` credentials  
✅ **Production**: Uses Lambda IAM role automatically  
✅ **No code changes needed** - environment detection is automatic  
✅ **Better logging** - shows which credential method is used

