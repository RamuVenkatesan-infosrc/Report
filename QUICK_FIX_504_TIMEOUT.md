# Quick Fix for 504 Gateway Timeout - Step by Step

## Problem
Your endpoint `/analyze-worst-apis-with-github/` is timing out because API Gateway has a 30-second limit, but your endpoint needs more time.

## Solution
Use Lambda Function URL instead of API Gateway URL. Function URLs support up to 900 seconds (15 minutes).

---

## Steps to Fix (5 minutes)

### Step 1: Get Your Lambda Function URL

After deploying with `serverless deploy`, you'll see output like:
```
endpoints:
  ANY - https://xxxxx.lambda-url.us-east-1.on.aws/
```

**OR** run this command:
```bash
aws lambda get-function-url-config --function-name report-analyzer-api-dev --query FunctionUrl --output text
```

**OR** check AWS Console:
1. Go to AWS Lambda Console
2. Find function: `report-analyzer-api-dev`
3. Go to "Configuration" → "Function URL"
4. Copy the Function URL (looks like: `https://xxxxx.lambda-url.us-east-1.on.aws/`)

### Step 2: Set Environment Variable

Create or update `.env` file in `frontend/code-api-pulse-main/`:

```env
VITE_LAMBDA_FUNCTION_URL=https://xxxxx.lambda-url.us-east-1.on.aws
```

**Important**: Replace `xxxxx` with your actual Function URL from Step 1.

### Step 3: Rebuild and Redeploy Frontend

```bash
cd frontend/code-api-pulse-main
npm run build
# Then deploy your dist/ folder to your hosting service
```

### Step 4: Test

The endpoint `/analyze-worst-apis-with-github/` will now automatically use the Function URL instead of API Gateway, avoiding the 30-second timeout.

---

## What Changed?

✅ **Frontend automatically uses Function URL** for long-running endpoints:
- `/analyze-worst-apis-with-github/` 
- `/analyze-full-repository/`

✅ **Other endpoints continue using API Gateway** (faster for quick requests)

✅ **Backward compatible** - if Function URL not set, falls back to API Gateway

---

## Verification

After setting the environment variable, check the browser console network tab. You should see requests going to:
- `https://xxxxx.lambda-url.us-east-1.on.aws/analyze-worst-apis-with-github/` ✅
- Instead of: `https://65j0j8qh5l.execute-api.us-east-1.amazonaws.com/dev/analyze-worst-apis-with-github/` ❌

---

## Troubleshooting

### Still getting 504?
- ✅ Verify Function URL is correct in `.env`
- ✅ Rebuild frontend after changing `.env`
- ✅ Check Function URL is enabled in AWS Console
- ✅ Check CloudWatch logs: `aws logs tail /aws/lambda/report-analyzer-api-dev --follow`

### Function URL not found?
- Run: `serverless deploy` to ensure Function URL is created
- Check `serverless.yml` has `url: cors: true` (line 118-119)

### CORS errors?
- Function URL CORS is already enabled in `serverless.yml`
- Check browser console for specific CORS error details

---

## Summary

**The fix is simple:**
1. Get Function URL from AWS
2. Set `VITE_LAMBDA_FUNCTION_URL` environment variable
3. Rebuild frontend

**That's it!** The code changes are already done. You just need to configure the Function URL. 🎉

