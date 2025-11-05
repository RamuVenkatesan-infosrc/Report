# Fix: Code Suggestions Using Fallback in Production

## Problem
In production (Lambda), code suggestions are showing fallback/placeholder solutions instead of real AI-generated suggestions. This works fine locally.

## Root Cause
Bedrock client is failing to initialize or invoke in production, causing the system to fall back to generic suggestions.

## Diagnostic Steps

### 1. Check CloudWatch Logs
Look for these log messages in your Lambda function logs:

**Good (Bedrock working):**
```
✅ "Bedrock client initialized with IAM role (Lambda environment)"
✅ "Invoking Bedrock model anthropic.claude-3-5-sonnet-20240620-v1:0..."
✅ "Bedrock response received: X chars in Y chunks"
```

**Bad (Bedrock failing):**
```
❌ "Failed to initialize Bedrock client: ..."
❌ "BEDROCK FAILED for ...: Bedrock client not available"
❌ "Bedrock API error [AccessDenied]: ..."
❌ "Creating enhanced fallback suggestions for ..."
```

### 2. Common Issues and Fixes

#### Issue 1: Bedrock Model Access Not Enabled
**Symptom:** `AccessDenied` or `ModelAccessDeniedException`

**Fix:**
1. Go to AWS Bedrock Console: https://console.aws.amazon.com/bedrock/
2. Go to "Model access" section
3. Enable the model: `anthropic.claude-3-5-sonnet-20240620-v1:0`
4. Wait a few minutes for access to propagate

#### Issue 2: IAM Role Missing Permissions
**Symptom:** `AccessDenied` error in logs

**Fix:**
Your `serverless.yml` already has the permissions (lines 75-80), but verify:
```yaml
- Effect: Allow
  Action:
    - bedrock:InvokeModel
    - bedrock:ListModels
    - bedrock:GetModel
  Resource: "*"
```

**Verify in AWS Console:**
1. Go to Lambda function → Configuration → Permissions
2. Click on the execution role
3. Verify the policy includes `bedrock:InvokeModel`

#### Issue 3: ENABLE_BEDROCK Environment Variable
**Symptom:** `"Bedrock is disabled in configuration"` in logs

**Fix:**
Check Lambda environment variables:
- `ENABLE_BEDROCK` should be `"true"` (string, not boolean)
- Check in: Lambda → Configuration → Environment variables

#### Issue 4: Wrong Region
**Symptom:** `UnknownError` or connection timeout

**Fix:**
- Verify Bedrock is available in `us-east-1` (your configured region)
- Check `AWS_REGION` environment variable matches `serverless.yml` region

#### Issue 5: Bedrock Client Initialization Failure
**Symptom:** `"Failed to initialize Bedrock client"` in logs

**Possible causes:**
- Lambda execution role not properly attached
- Region mismatch
- Network/VPC issues (if Lambda is in VPC)

## Quick Fixes

### Fix 1: Verify Bedrock Access
```bash
# Test Bedrock access from AWS CLI
aws bedrock list-foundation-models --region us-east-1

# Test invoking a model (if you have CLI access)
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20240620-v1:0 \
  --region us-east-1 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"test"}]}' \
  response.json
```

### Fix 2: Check Lambda Environment Variables
```bash
aws lambda get-function-configuration \
  --function-name report-analyzer-api-dev \
  --query 'Environment.Variables' \
  --region us-east-1
```

Verify:
- `ENABLE_BEDROCK=true`
- `BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0`
- `AWS_REGION=us-east-1`

### Fix 3: Redeploy with Explicit Logging
The code has been updated with better error logging. Redeploy:

```bash
cd backend
serverless deploy
```

Then check CloudWatch logs for detailed error messages.

## Testing After Fix

1. **Deploy the updated code:**
   ```bash
   cd backend
   serverless deploy
   ```

2. **Test the endpoint:**
   ```bash
   curl -X POST "https://67z7tlitf2i5qf2etx7ndslyey0eicxc.lambda-url.us-east-1.on.aws/analyze-worst-apis-with-github/?github_repo=Navaneeth-infosrc%2Fresume-evaluator&branch=main&token=YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"worst_apis": [...]}'
   ```

3. **Check CloudWatch Logs:**
   ```bash
   aws logs tail /aws/lambda/report-analyzer-api-dev --follow
   ```

   Look for:
   - ✅ Bedrock initialization success
   - ✅ Bedrock API calls
   - ❌ Any error messages

## Expected Behavior After Fix

### Before Fix (Fallback):
```json
{
  "code_suggestions": [{
    "title": "Add Comprehensive Error Handling & Logging",
    "improved_code": "# Improvements added:\n# 1. Import statements..."
  }]
}
```

### After Fix (Real AI):
```json
{
  "code_suggestions": [{
    "title": "Optimize Database Query Performance",
    "improved_code": "def get_user(user_id: int):\n    try:\n        return db.query(User).filter(User.id == user_id).first()\n    except Exception as e:\n        logger.error(f\"Error: {e}\")\n        raise"
  }]
}
```

## Summary

The most common issues are:
1. **Bedrock model access not enabled** (most common)
2. **IAM permissions missing** (check Lambda execution role)
3. **ENABLE_BEDROCK=false** (check environment variables)

Check CloudWatch logs first - they will tell you exactly what's wrong!

