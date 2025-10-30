# AWS Session Token Setup Guide

## ✅ Session Token Support Added

Your application now supports BOTH:
- **Permanent credentials** (without session token)
- **Temporary credentials** (with session token)

## Your Credentials

Add these to your `backend/.env` file:

```bash
# AWS Configuration with Session Token (Temporary Credentials)
AWS_ACCESS_KEY_ID=ASIAVSTWYDPV2HHVKTLP
AWS_SECRET_ACCESS_KEY=ptXDpg91dU9B1xM/eYigo/S smelledDuKKmBfgv/bZGAO
AWS_SESSION_TOKEN=IQoJb3JpZ2luX2VjEAUaCXVzLWVhc3QtMSJGMEQCIFRS+Sg87ZEOIMCWkjB2X2FrJaj5JW9m07eGXWYx/zkFAiBle4/7n3H/hB+itdV1l4VJne8XW5uGX5uaIwb2Wc4HsiqpAwi+//////////8BEAAaDDM4MzU3NDg3NTExNSIM8Wj4XcXyWJt1T0KIKv0Calf+Bk7SArXd+d2908Zt8DnRAmI1D8wPenZKZYKz5+rklzWlJG0o/eZZIdA+hOtfhoqzRaiC9Nkc5XocNAA7VrKvfm7puTDRpOSmFYE3OSHRmSEHSwpfOiun4lW34ovn2LMkxPrrRGyCsP6OewvFWKWrzcJy/Ku5kZn+0ogM13ba+AYSuWgijbMZMga671DlEQGcx0f682/y5JRbVxETMuwW4Qjb1/JUdV+OcSZWeIKzd5YvRKM5oJcwZf3XkJCLrTKx/KGFKn8urhA3OKa0ik45ffHs/NkFZL7fa1tTN7mAojhsIWtpmr2SDeG/bbq4f8qfdEg7zOI6FecwQmUmf0e47USvcOCMvXjPNS5F9uM0H2R6CUSCQSLk8QXb6eekejlIaj2ZctnSdWzJlsegNDWUoIZLPCtL10VaLVwOLb/D2Zvi9DvtC1RdIMmcQkw0YBJTGZFAuQLPAA1z4v/MmrtLO2Kx0vmWkpZ1ibnnvZ80tPT0DuSHT97cS+H/MP7xgsgGOqUBV3EjSsNn55VX42PqSm9B9o2xjUkWLW5aXDn5t8da2dxxsTytYnydQgiBFl6ysqC2Y/l5ZxbhhVCWnYeLmuV27XuzT1GPvncOZapM0BKXoyYbDjM7YT9YasfT8SqeZkn/XV1YPS9ZiVnrwA2LWq86pvP7MAUUEWZeUmYslE6a+/QMQV+oYA2Rwem6cBD8XNyTkYnHr4bqoMdXLyVikTdIosCtykAJ
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
MAX_TOKENS=4000
TEMPERATURE=0.7
ENABLE_BEDROCK=true

# GitHub Configuration
GITHUB_TOKEN=your_github_token

# DynamoDB Configuration - Leave commented for AWS
# DYNAMODB_ENDPOINT_URL=http://localhost:1234

# Application Configuration
LOG_LEVEL=INFO
```

## How It Works

### With Session Token (Temporary Credentials) ✅
```bash
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
```
**Your app will automatically:**
- Use session token for Bedrock
- Use session token for DynamoDB
- Work with temporary credentials

### Without Session Token (Permanent Credentials) ✅
```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
# AWS_SESSION_TOKEN not set
```
**Your app will automatically:**
- Use permanent credentials only
- Work with long-term access keys

## Features Supported

✅ **Bedrock AI** - Session token supported  
✅ **DynamoDB** - Session token supported  
✅ **Automatic Detection** - Works with or without session token  
✅ **Logging** - Shows which mode is active  

## Expected Log Output

### With Session Token:
```
Bedrock client initialized with session token
Using AWS DynamoDB in region us-east-1
Using AWS credentials with session token from environment variables
```

### Without Session Token:
```
Bedrock client initialized successfully
Using AWS DynamoDB in region us-east-1
Using AWS credentials from environment variables
```

## Session Token Notes

⚠️ **Temporary Credentials Expire**
- Session tokens typically expire after 1-12 hours
- When expired, you'll get authentication errors
- You'll need to get a new session token

### Getting New Session Token

1. AWS Console → Security Credentials
2. Or use AWS CLI:
```bash
aws sts get-session-token --duration-seconds 3600
```

### Convert to Permanent (Optional)

If you have permanent credentials, use:
```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
# AWS_SESSION_TOKEN not needed
```

## Testing

After updating `.env`:
1. Restart backend
2. Check logs for "session token" messages
3. Test Bedrock and DynamoDB operations

## Troubleshooting

### Error: "Invalid credentials"
- Session token expired - get new one
- Credentials incorrect - check .env file

### Error: "Access denied"
- IAM permissions missing
- Session token has insufficient permissions

### Fallback Responses
- Credentials not loaded properly
- Check .env file format

## Summary

✅ **Session Token Support Added**
- Works with temporary credentials
- Works with permanent credentials  
- Automatic detection
- Better logging

Just add your credentials to `.env` and restart!

