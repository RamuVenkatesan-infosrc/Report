# Deploy Your Backend to AWS Lambda (Serverless)

## Why Serverless is Best for You

✅ **Already Configured** - You have `serverless.yml`  
✅ **Easy Deployment** - One command: `serverless deploy`  
✅ **Cost-Effective** - Pay only for usage (~$5-10/month)  
✅ **Auto-Scaling** - Handles traffic automatically  
✅ **No Infrastructure** - AWS manages everything  

## Prerequisites

1. ✅ Node.js installed (`npm install -g serverless`)
2. ✅ AWS credentials configured
3. ✅ `serverless.yml` already exists

## Quick Deployment Steps

### Step 1: Install Serverless Framework

```bash
npm install -g serverless
```

### Step 2: Configure AWS Credentials

You already have credentials in `.env`, but you may need to configure AWS CLI:

```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_SESSION_TOKEN=your_token  # if using temporary
export AWS_REGION=us-east-1
```

### Step 3: Install Serverless Plugins

```bash
cd backend
npm install --save-dev serverless-dotenv-plugin
npm install --save-dev serverless-python-requirements
```

### Step 4: Deploy

```bash
cd backend
serverless deploy
```

That's it! Your API will be deployed.

### Step 5: Get Your API URL

After deployment, you'll get:
```
endpoints:
  ANY - https://xxxxx.execute-api.us-east-1.amazonaws.com/dev/
  ANY - https://xxxxx.execute-api.us-east-1.amazonaws.com/dev/{proxy+}
```

## Update Your Frontend

Update `frontend/code-api-pulse-main/src/services/api.ts`:

```typescript
const API_BASE_URL = 'https://xxxxx.execute-api.us-east-1.amazonaws.com/dev';
```

## Deployment Commands

```bash
# Deploy to production
serverless deploy --stage prod

# Deploy to dev (default)
serverless deploy --stage dev

# Deploy specific function
serverless deploy -f engagepro-api

# View logs
serverless logs -f engagepro-api

# Remove deployment
serverless remove
```

## What Gets Deployed

✅ **Lambda Function** - Your FastAPI app  
✅ **API Gateway** - HTTP endpoints  
✅ **IAM Role** - Permissions for Bedrock, DynamoDB  
✅ **CloudWatch Logs** - Logging  

## Environment Variables

Create AWS Secrets Manager secret with name: `engagepro-secrets`

Or set in `serverless.yml`:

```yaml
environment:
  AWS_ACCESS_KEY_ID: ${env:AWS_ACCESS_KEY_ID}
  AWS_SECRET_ACCESS_KEY: ${env:AWS_SECRET_ACCESS_KEY}
  AWS_SESSION_TOKEN: ${env:AWS_SESSION_TOKEN}
  GITHUB_TOKEN: ${env:GITHUB_TOKEN}
```

## Cost Estimate

### Typical Usage (1,000 requests/day):

- **Lambda**: 1M requests = $0.20 → **~$6/month**
- **API Gateway**: First 1M free → **Free**
- **DynamoDB**: On-demand → **~$5/month**
- **Bedrock**: $3 per 1M tokens → **~$10/month**
- **Total**: **~$20-25/month**

### Light Usage (100 requests/day):

- **Total**: **~$5-10/month**

## Monitoring

```bash
# View real-time logs
serverless logs -f engagepro-api --tail

# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=engagepro-api-dev
```

## Troubleshooting

### Error: "Plugin serverless-dotenv-plugin not found"
```bash
npm install --save-dev serverless-dotenv-plugin
```

### Error: "Python requirements not found"
```bash
npm install --save-dev serverless-python-requirements
```

### Error: "Timeout"
Your Lambda has 900s timeout (15 min). This is enough for your analysis.

### Cold Start
First request after idle takes 3-5 seconds. Subsequent requests are instant.

### Enable Keep Warm
To prevent cold starts, use AWS Lambda provisioned concurrency or schedule a keep-warm ping.

## Update Code

```bash
# Make changes to code
# Then redeploy
serverless deploy

# Or deploy function only (faster)
serverless deploy function -f engagepro-api
```

## Your serverless.yml Configuration

✅ **Memory**: 512MB  
✅ **Timeout**: 900s (15 min) - enough for long analysis  
✅ **Runtime**: Python 3.11  
✅ **Architecture**: x86_64  
✅ **Permissions**: Bedrock, DynamoDB, S3, SES  

## Next Steps After Deployment

1. ✅ Deploy backend: `serverless deploy`
2. ✅ Get API URL from output
3. ✅ Update frontend with API URL
4. ✅ Test API endpoints
5. ✅ Monitor in CloudWatch

## Alternative: Docker/ECS Deployment

If you decide you need Docker instead, see the comparison in `DEPLOYMENT_COMPARISON.md`.

But **Serverless is recommended** for your use case!

## Summary

**Deploy Command:**
```bash
cd backend
serverless deploy
```

**That's it!** 🚀

Your backend will be live on AWS Lambda in ~2 minutes.

