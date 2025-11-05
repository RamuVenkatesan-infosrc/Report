# Fix 504 Gateway Timeout - Complete Solution Guide

## Problem
Your `/analyze-worst-apis-with-github/` endpoint is timing out with **504 Gateway Timeout** because:
- **API Gateway has a hard 30-second timeout limit**
- Your endpoint performs multiple operations that can take 30+ seconds:
  1. GitHub API calls to discover APIs
  2. Code analysis and matching
  3. Bedrock AI analysis for each matched API (this is the slowest part)
  4. DynamoDB storage

## Root Cause
The URL you're using: `https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/...` is **API Gateway**, which has a 30-second maximum timeout.

## Solution Options (Choose One)

### ✅ **Solution 1: Use Lambda Function URL (RECOMMENDED - Quick Fix)**

Lambda Function URLs support up to **900 seconds (15 minutes)**, which is perfect for your use case.

#### Step 1: Get Your Function URL
After deploying, run:
```bash
aws lambda get-function-url-config --function-name report-analyzer-api-dev
```

Or check your serverless deployment output:
```bash
serverless deploy
# Look for output like:
# endpoints:
#   ANY - https://xxxxx.lambda-url.us-east-1.on.aws/
```

#### Step 2: Update Frontend Environment Variable
Add to your `.env` file in `frontend/code-api-pulse-main/`:
```env
VITE_API_BASE_URL=https://xxxxx.lambda-url.us-east-1.on.aws
```

**Note**: The Function URL is already configured in your `serverless.yml` (line 118-119), so it should be available after deployment.

#### Step 3: Update Frontend Code
The frontend has been updated to automatically use the Function URL for long-running endpoints. Just set the environment variable.

#### Step 4: Redeploy Frontend
```bash
cd frontend/code-api-pulse-main
npm run build
# Deploy your built files to your hosting service
```

---

### **Solution 2: Implement Async Processing (Better UX - Long-term)**

For better user experience, implement async processing with job polling:

1. **Endpoint returns immediately** with a job ID
2. **Processing happens in background**
3. **Frontend polls** for status updates
4. **User sees progress** instead of waiting

**Benefits:**
- Better UX (progress indicators)
- No timeout issues
- Can handle very long operations
- User can navigate away and come back

**Implementation:** See `ASYNC_PROCESSING_IMPLEMENTATION.md` (to be created if needed)

---

### **Solution 3: Optimize Endpoint (Performance Improvement)**

Reduce processing time by:
1. **Parallel processing** of AI analysis (instead of sequential)
2. **Caching** GitHub API responses
3. **Batch Bedrock calls** instead of individual calls
4. **Early returns** for simple cases

**Current bottleneck:** Line 1386 in `reportanalysis_enhanced_v2.py` processes AI analysis sequentially for each matched API.

**Implementation:** See `OPTIMIZE_ENDPOINT.md` (to be created if needed)

---

## Quick Verification Steps

### 1. Check Function URL is Available
```bash
aws lambda list-functions --query "Functions[?FunctionName=='report-analyzer-api-dev'].FunctionName"
```

### 2. Test Function URL Directly
```bash
curl -X POST "https://xxxxx.lambda-url.us-east-1.on.aws/analyze-worst-apis-with-github/?github_repo=Navaneeth-infosrc%2Fresume-evaluator&branch=main&token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"worst_apis": [...]}'
```

### 3. Check CloudWatch Logs
If timeout still occurs, check logs:
```bash
aws logs tail /aws/lambda/report-analyzer-api-dev --follow
```

---

## Current Configuration

Your `serverless.yml` already has:
- ✅ Lambda timeout: 900 seconds (15 minutes) - Line 114
- ✅ Function URL configured: Line 118-119
- ✅ Memory: 2048 MB - Line 113

**The Function URL is ready - you just need to use it!**

---

## Migration Path

1. **Immediate**: Use Function URL (Solution 1) - **5 minutes**
2. **Short-term**: Optimize endpoint (Solution 3) - **1-2 hours**
3. **Long-term**: Implement async processing (Solution 2) - **1 day**

---

## Troubleshooting

### Still getting 504?
- Check you're using Function URL, not API Gateway URL
- Verify Function URL is enabled in AWS Console
- Check CloudWatch logs for actual errors
- Increase Lambda memory if processing is slow

### Function URL not working?
- Check CORS configuration
- Verify Function URL is enabled: `aws lambda get-function-url-config --function-name report-analyzer-api-dev`
- Check IAM permissions for Function URL

### Frontend CORS errors?
- Function URL CORS is already enabled in serverless.yml
- Verify CORS headers in response

---

## Summary

**The quickest fix**: Use Lambda Function URL instead of API Gateway URL. The Function URL is already configured in your deployment - you just need to:
1. Get the Function URL from AWS
2. Update `VITE_API_BASE_URL` environment variable
3. Redeploy frontend

This will immediately solve your 504 timeout issue! 🎉

