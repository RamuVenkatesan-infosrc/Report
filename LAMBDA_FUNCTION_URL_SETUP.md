# Lambda Function URL Setup - Fix for API Gateway 30-Second Timeout

## Problem
API Gateway has a hard 30-second timeout limit, which causes 504 Gateway Timeout errors when processing multiple APIs with Bedrock analysis.

## Solution
Lambda Function URLs support up to **900 seconds (15 minutes)**, allowing full analysis of all APIs without timeout issues.

## After Deployment

### 1. Get Your Function URL
After deploying with `serverless deploy`, you'll see output like:
```
endpoints:
  ANY - https://xxxxx.lambda-url.us-east-1.on.aws/
```

### 2. Use Function URL for Long-Running Requests
For the `/analyze-worst-apis-with-github/` endpoint (which can take 30+ seconds), use the Function URL instead of the API Gateway URL.

**API Gateway URL (30s limit):**
```
https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/analyze-worst-apis-with-github/
```

**Function URL (900s limit):**
```
https://xxxxx.lambda-url.us-east-1.on.aws/analyze-worst-apis-with-github/
```

### 3. Update Frontend
Update your frontend API service to use the Function URL for long-running endpoints:

```typescript
// For long-running endpoints, use Function URL
const FUNCTION_URL = process.env.REACT_APP_LAMBDA_FUNCTION_URL || 
  'https://xxxxx.lambda-url.us-east-1.on.aws';

// For quick endpoints, keep using API Gateway
const API_GATEWAY_URL = process.env.REACT_APP_API_GATEWAY_URL || 
  'https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev';
```

### 4. Environment Variables
Add to your `.env` or deployment environment:
```
LAMBDA_FUNCTION_URL=https://xxxxx.lambda-url.us-east-1.on.aws
```

## Benefits
- ✅ Supports up to 900 seconds (15 minutes)
- ✅ No 30-second timeout limit
- ✅ CORS enabled
- ✅ Same FastAPI application
- ✅ Can process all APIs without limits

## Notes
- Function URLs are public by default (can be configured with auth)
- Both API Gateway and Function URL will work simultaneously
- Use Function URL for endpoints that need > 30 seconds
- Use API Gateway for quick endpoints (< 30 seconds)

