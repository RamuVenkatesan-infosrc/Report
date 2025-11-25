# Fix: Bedrock AI Not Working in ECS Production

## Problem
Bedrock AI is not working in ECS/ALB production deployment, but works fine locally.

## Root Cause
The Bedrock service was only detecting Lambda environment, not ECS. In ECS, it should use the ECS task role IAM credentials automatically.

## Solution Applied

### 1. Updated `bedrock_service.py`
- ✅ Added ECS environment detection
- ✅ Now properly uses IAM task role in ECS (just like Lambda uses execution role)
- ✅ Updated logging to show "ECS environment" when detected

**Changes:**
- Detects ECS via `ECS_CONTAINER_METADATA_URI` or `AWS_EXECUTION_ENV` starting with "ECS"
- Uses IAM task role credentials automatically (boto3 handles this)
- No explicit credentials needed in ECS

## Verification Steps

### Step 1: Verify ECS Task Role Has Bedrock Permissions

Check if the policy is attached to your ECS task role:

```powershell
aws iam get-role-policy `
    --role-name ecsTaskRole `
    --policy-name ECSBedrockDynamoDBPolicy `
    --region us-east-1
```

You should see permissions for:
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListModels`
- `bedrock:GetModel`
- `aws-marketplace:ViewSubscriptions` (required for AWS Marketplace models)

**If policy is missing or needs update, attach it:**

```powershell
aws iam put-role-policy `
    --role-name ecsTaskRole `
    --policy-name ECSBedrockDynamoDBPolicy `
    --policy-document file://ecs-task-policy.json `
    --region us-east-1
```

**Note:** The policy now includes `aws-marketplace:ViewSubscriptions` permission which is required for AWS Marketplace models (like Anthropic Claude).

### Step 2: Verify Bedrock Model Access

1. Go to AWS Bedrock Console: https://console.aws.amazon.com/bedrock/
2. Click "Model access" in the left menu
3. Verify `anthropic.claude-3-5-sonnet-20240620-v1:0` is **enabled**
4. If not enabled, click "Enable" and wait a few minutes

### Step 3: Verify Environment Variables

Check your ECS task definition has:
- `ENABLE_BEDROCK=true` (string, not boolean)
- `BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0`
- `AWS_REGION=us-east-1`

### Step 4: Rebuild and Redeploy

1. **Rebuild the Docker image** with the updated code:
   ```powershell
   cd backend
   docker build -t report-analyzer-api:latest .
   ```

2. **Push to ECR**:
   ```powershell
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 383574875115.dkr.ecr.us-east-1.amazonaws.com
   docker tag report-analyzer-api:latest 383574875115.dkr.ecr.us-east-1.amazonaws.com/report-analyzer-api:latest
   docker push 383574875115.dkr.ecr.us-east-1.amazonaws.com/report-analyzer-api:latest
   ```

3. **Force new deployment** in ECS:
   ```powershell
   aws ecs update-service `
       --cluster report-analyzer-cluster `
       --service report-analyzer-service `
       --force-new-deployment `
       --region us-east-1
   ```

### Step 5: Check CloudWatch Logs

After deployment, check ECS logs in CloudWatch:

1. Go to CloudWatch → Log groups → `/ecs/report-analyzer-api`
2. Look for these log messages:

**✅ Good (Bedrock working):**
```
Bedrock client initialized with IAM role (ECS environment)
Bedrock client initialized successfully with timeout configuration
Invoking Bedrock model anthropic.claude-3-5-sonnet-20240620-v1:0...
Bedrock response received: X chars in Y chunks
```

**❌ Bad (Bedrock failing):**
```
Bedrock client initialized with default credential chain  # Should say "ECS environment"
Failed to initialize Bedrock client: ...
Bedrock error: AccessDenied
Bedrock error: ModelAccessDeniedException
Bedrock error: UnrecognizedClientException
```

## Common Issues

### Issue 1: AccessDenied Error
**Symptom:** `AccessDenied` or `ModelAccessDeniedException` in logs

**Fix:**
1. Verify ECS task role has Bedrock permissions (Step 1 above)
2. Verify Bedrock model access is enabled (Step 2 above)
3. Check the task role ARN in task definition matches the IAM role

### Issue 2: UnrecognizedClientException
**Symptom:** `The security token included in the request is invalid`

**Fix:**
- This usually means the IAM role isn't properly attached
- Verify `taskRoleArn` in task definition points to the correct role
- Redeploy the service

### Issue 3: Code Still Shows "default credential chain"
**Symptom:** Logs show "Bedrock client initialized with default credential chain"

**Fix:**
- The updated code should detect ECS automatically
- Make sure you rebuilt and redeployed with the new code (Step 4)
- Check that `ECS_CONTAINER_METADATA_URI` is set in the container (it should be automatically)

## Testing

After redeployment, test Bedrock by:

1. Using the frontend to run a "Full Repository Analysis"
2. Check if AI suggestions are generated (not fallback suggestions)
3. Check CloudWatch logs for Bedrock activity

## Expected Result

After fixing, you should see:
- ✅ Bedrock working in production
- ✅ AI-generated code suggestions (not fallback)
- ✅ Logs showing "ECS environment" detection
- ✅ No credential errors in CloudWatch

