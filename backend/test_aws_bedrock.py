"""
Test script to verify AWS Bedrock credentials and access.
Run this to diagnose AWS configuration issues.
"""
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Load environment variables
load_dotenv()

def test_aws_credentials():
    """Test AWS credentials and Bedrock access."""
    print("=" * 60)
    print("AWS BEDROCK CONFIGURATION TEST")
    print("=" * 60)
    
    # Step 1: Check if credentials are in environment
    print("\n[1] Checking Environment Variables...")
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'us-east-1')
    model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    
    if not access_key:
        print("   ❌ AWS_ACCESS_KEY_ID not found in .env")
        print("   → Add AWS_ACCESS_KEY_ID to backend/.env file")
        return False
    else:
        print(f"   ✅ AWS_ACCESS_KEY_ID found: {access_key[:8]}...{access_key[-4:]}")
    
    if not secret_key:
        print("   ❌ AWS_SECRET_ACCESS_KEY not found in .env")
        print("   → Add AWS_SECRET_ACCESS_KEY to backend/.env file")
        return False
    else:
        print(f"   ✅ AWS_SECRET_ACCESS_KEY found: {'*' * 20}")
    
    print(f"   ✅ AWS_REGION: {region}")
    print(f"   ✅ BEDROCK_MODEL_ID: {model_id}")
    
    # Step 2: Test AWS Credentials with STS
    print("\n[2] Testing AWS Credentials with STS (Security Token Service)...")
    try:
        sts_client = boto3.client(
            'sts',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        identity = sts_client.get_caller_identity()
        print(f"   ✅ AWS Credentials are VALID")
        print(f"   → Account ID: {identity['Account']}")
        print(f"   → User ARN: {identity['Arn']}")
        print(f"   → User ID: {identity['UserId']}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"   ❌ AWS Credentials are INVALID")
        print(f"   → Error Code: {error_code}")
        print(f"   → Error Message: {error_msg}")
        
        if error_code == 'InvalidClientTokenId':
            print("\n   SOLUTION:")
            print("   - Your AWS_ACCESS_KEY_ID is incorrect")
            print("   - Go to AWS Console → IAM → Users → Security Credentials")
            print("   - Create new access key and update .env file")
        elif error_code == 'SignatureDoesNotMatch':
            print("\n   SOLUTION:")
            print("   - Your AWS_SECRET_ACCESS_KEY is incorrect")
            print("   - Go to AWS Console → IAM → Users → Security Credentials")
            print("   - Create new access key and update .env file")
        
        return False
    except NoCredentialsError:
        print("   ❌ No AWS credentials found")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        return False
    
    # Step 3: Test Bedrock Service Access
    print("\n[3] Testing AWS Bedrock Service Access...")
    try:
        bedrock_client = boto3.client(
            'bedrock',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # Try to list foundation models
        response = bedrock_client.list_foundation_models()
        available_models = response.get('modelSummaries', [])
        
        print(f"   ✅ Bedrock Service is ACCESSIBLE")
        print(f"   → Found {len(available_models)} foundation models")
        
        # Check if Claude is available
        claude_models = [m for m in available_models if 'claude' in m.get('modelId', '').lower()]
        if claude_models:
            print(f"   ✅ Claude models are available ({len(claude_models)} variants)")
            for model in claude_models[:5]:  # Show first 5
                print(f"      - {model.get('modelId')}")
        else:
            print(f"   ⚠️  No Claude models found")
            print(f"   → You may need to request access to Claude in AWS Bedrock console")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"   ❌ Cannot access Bedrock Service")
        print(f"   → Error Code: {error_code}")
        print(f"   → Error Message: {error_msg}")
        
        if error_code == 'AccessDeniedException':
            print("\n   SOLUTION:")
            print("   - Your AWS user doesn't have permission to use Bedrock")
            print("   - Go to AWS Console → IAM → Users → Your User")
            print("   - Add permission: AmazonBedrockFullAccess")
        elif error_code == 'ResourceNotFoundException':
            print("\n   SOLUTION:")
            print("   - Bedrock may not be available in your region")
            print("   - Try changing AWS_REGION to: us-east-1 or us-west-2")
        
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        return False
    
    # Step 4: Test Bedrock Runtime (actual model invocation)
    print("\n[4] Testing Bedrock Runtime (Model Invocation)...")
    try:
        bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # Try a simple test invocation
        import json
        test_prompt = "Say 'test successful' in JSON format with key 'message'"
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": test_prompt
                }
            ]
        })
        
        print(f"   → Testing model: {model_id}")
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body,
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        print(f"   ✅ Bedrock Runtime is WORKING")
        print(f"   → Model responded successfully")
        print(f"   → Response: {response_body.get('content', [{}])[0].get('text', 'N/A')[:100]}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"   ❌ Cannot invoke Bedrock model")
        print(f"   → Error Code: {error_code}")
        print(f"   → Error Message: {error_msg}")
        
        if error_code == 'AccessDeniedException':
            print("\n   SOLUTION:")
            print("   - Request access to Claude models in AWS Bedrock console")
            print("   - Go to: AWS Console → Bedrock → Model access")
            print("   - Click 'Manage model access' → Select Anthropic Claude → Request access")
        elif error_code == 'ValidationException':
            print("\n   SOLUTION:")
            print("   - The model ID might be incorrect")
            print("   - Update BEDROCK_MODEL_ID in .env to a valid model")
        elif error_code == 'ThrottlingException':
            print("\n   SOLUTION:")
            print("   - You've exceeded the rate limit")
            print("   - Wait a few minutes and try again")
        
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        return False
    
    # Success!
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - AWS Bedrock is configured correctly!")
    print("=" * 60)
    print("\nYour Full Repository Analysis will now use AI-powered suggestions.")
    print("Restart your backend server to apply the configuration.")
    return True

if __name__ == "__main__":
    try:
        success = test_aws_credentials()
        if not success:
            print("\n" + "=" * 60)
            print("❌ CONFIGURATION INCOMPLETE")
            print("=" * 60)
            print("\nFix the issues above and run this test again.")
            print("After fixing, restart your backend server.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

