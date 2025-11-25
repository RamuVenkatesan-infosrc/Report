# Fix: 504 Gateway Timeout on Long-Running Endpoints

## Problem
Getting `504 Gateway Timeout` errors on `/analyze-worst-apis-with-github/` endpoint. This happens because ALB (Application Load Balancer) has a default idle timeout of 60 seconds, and your Bedrock/GitHub analysis takes longer than that.

## Solution: Increase ALB Idle Timeout

The ALB idle timeout can be increased up to 4000 seconds (about 66 minutes). This is the recommended solution for long-running analysis endpoints.

### Option 1: AWS Console

1. Go to EC2 Console → Load Balancers
2. Select your load balancer: `report-analyzer-lb-676990092`
3. Click "Edit attributes"
4. Find "Idle timeout" setting
5. Change from 60 seconds to **600 seconds (10 minutes)** or **1200 seconds (20 minutes)**
6. Click "Save"

### Option 2: AWS CLI

```powershell
aws elbv2 modify-load-balancer-attributes `
    --load-balancer-arn <your-alb-arn> `
    --attributes Key=idle_timeout.timeout_seconds,Value=600 `
    --region us-east-1
```

To get your ALB ARN:
```powershell
aws elbv2 describe-load-balancers `
    --names report-analyzer-lb `
    --region us-east-1 `
    --query 'LoadBalancers[0].LoadBalancerArn' `
    --output text
```

### Recommended Timeout Values

- **600 seconds (10 minutes)** - Good for most analysis tasks
- **1200 seconds (20 minutes)** - For very large repositories
- **1800 seconds (30 minutes)** - Maximum recommended
- **4000 seconds (66 minutes)** - Maximum allowed by AWS

## Alternative: Make Endpoint Async

If you can't increase ALB timeout, you could refactor the endpoint to:
1. Start the analysis asynchronously
2. Return immediately with a job ID
3. Poll for results using another endpoint

But increasing ALB timeout is simpler and recommended.

## Verify the Fix

After increasing the timeout:
1. Try your `/analyze-worst-apis-with-github/` request again
2. It should complete without 504 errors
3. Check CloudWatch logs to see successful completion

## Note

The timeout applies to **idle time** - if the connection is actively receiving data, it won't timeout. The issue occurs when there are long periods without data transfer (e.g., waiting for Bedrock responses).

