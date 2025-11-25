# Quick Fix: Bedrock Marketplace Permission Error

## Error
```
AccessDeniedException: Model access is denied due to User: arn:aws:sts::383574875115:assumed-role/ecsTaskRole/...
is not authorized to perform: aws-marketplace:ViewSubscriptions
```

## Root Cause
The ECS task role is missing the `aws-marketplace:ViewSubscriptions` permission, which is required for AWS Marketplace models (like Anthropic Claude models).

## Immediate Fix

Run this command to update the IAM policy with the missing permission:

```powershell
cd backend
aws iam put-role-policy `
    --role-name ecsTaskRole `
    --policy-name ECSBedrockDynamoDBPolicy `
    --policy-document file://ecs-task-policy.json `
    --region us-east-1
```

This will add the `aws-marketplace:ViewSubscriptions` permission to your ECS task role.

## Verify the Fix

After running the command, verify the policy was updated:

```powershell
aws iam get-role-policy `
    --role-name ecsTaskRole `
    --policy-name ECSBedrockDynamoDBPolicy `
    --region us-east-1
```

You should now see `aws-marketplace:ViewSubscriptions` in the policy actions.

## No Redeployment Needed!

**Important:** You don't need to rebuild or redeploy your ECS service. The IAM policy change takes effect immediately for running tasks. The next Bedrock API call should work.

## Test

Try your Bedrock request again. The error should be resolved and you should see:
- ✅ "Bedrock response received: X chars in Y chunks" in logs
- ✅ AI suggestions generated successfully

## If It Still Doesn't Work

If you still get errors after a few minutes:
1. The policy change might take a minute to propagate
2. Try restarting the ECS service:
   ```powershell
   aws ecs update-service `
       --cluster report-analyzer-cluster `
       --service report-analyzer-service `
       --force-new-deployment `
       --region us-east-1
   ```

## What Was Updated

- ✅ `backend/ecs-task-policy.json` - Added marketplace permission
- ✅ `backend/deploy-to-ecs.ps1` - Updated deployment script for future deployments

