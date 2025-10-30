# Fix: Expired Session Token

## Problem
Your session token is **expired or invalid**.

Error: `The security token included in the request is invalid`

## Solutions

### Solution 1: Get New Session Token (Temporary Credentials)

You need to get a fresh session token from AWS. Here are the options:

#### Option A: AWS Console
1. Go to **AWS Console** → **IAM** → **Users**
2. Select your user
3. Go to **Security credentials** tab
4. Click **Create access key** or refresh existing temporary credentials
5. Copy the new session token

#### Option B: AWS CLI (if configured)
```bash
aws sts get-session-token --duration-seconds 3600
```

#### Option C: From another AWS session
If you have access to AWS console that's still logged in, get new credentials from there.

### Solution 2: Use Permanent Credentials (Recommended for Development)

Instead of temporary credentials, use permanent ones:

1. Go to **AWS Console** → **IAM** → **Users**
2. Click on your user
3. **Security credentials** tab
4. Click **Create access key**
5. Choose **Command Line Interface (CLI)** or **Application running outside AWS**
6. Create the key
7. **Copy and save** the access key ID and secret access key

Update your `.env`:
```bash
# Use permanent credentials (no session token needed)
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX  # Permanent key starts with AKIA
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxx
# AWS_SESSION_TOKEN=  # Comment out or remove this line
AWS_REGION=us-east-1
```

### Solution 3: Use Local DynamoDB (For Testing)

If you just want to test locally without AWS:

Update your `.env`:
```bash
# Comment out AWS credentials
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_SESSION_TOKEN=

# Use local DynamoDB
DYNAMODB_ENDPOINT_URL=http://localhost:1234
USE_LOCAL_DYNAMODB=true
```

Make sure local DynamoDB is running on port 1234.

## Current Status

✅ **Code is working correctly** - Session token support is implemented  
❌ **Token expired** - Your temporary credentials are no longer valid  

## Quick Fix Steps

### If you have access to get new credentials:

1. Get new session token (or permanent credentials)
2. Update `backend/.env` with new credentials
3. Restart backend:
   ```bash
   cd backend
   uvicorn reportanalysis_enhanced_v2:app --reload --port 4723
   ```

### If you don't have access right now:

**Option 1: Use Local DynamoDB**
- Change `.env` to use `DYNAMODB_ENDPOINT_URL=http://localhost:1234`
- Run local DynamoDB on port 1234
- Backend will work without AWS

**Option 2: Create Permanent Access Key**
- Get permanent credentials from AWS Console
- Don't need session token
- Credentials won't expire (unless you rotate them)

## Important Notes

⚠️ **Temporary Credentials Expire:**
- Session tokens typically expire in 1-12 hours
- When expired, you need to get new ones
- Consider using permanent credentials for development

✅ **Permanent Credentials:**
- Don't expire (unless you rotate them)
- Start with `AKIA...` (not `ASIA...`)
- No session token needed
- Better for development/testing

## Expected Log Output After Fix

### With Valid Session Token:
```
Using AWS credentials with session token from environment variables
Table api-performance-analysis already exists
```

### With Permanent Credentials:
```
Using AWS credentials from environment variables
Table api-performance-analysis already exists
```

### With Local DynamoDB:
```
Using LOCAL DynamoDB at http://localhost:1234
Table api-performance-analysis already exists
```

## Next Steps

1. **Get new credentials** (temporary or permanent)
2. **Update `.env` file**
3. **Restart backend**
4. **Verify it works**

## Summary

Your session token expired. You need to:
- Get new temporary credentials, OR
- Create permanent access key, OR  
- Use local DynamoDB for testing

The code changes are complete and working - this is just a credentials issue! 🎯

