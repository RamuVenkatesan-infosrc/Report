#!/usr/bin/env python3
"""Test AWS credentials for Bedrock service."""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.models.config import Settings

def test_aws_credentials():
    """Test AWS credentials for Bedrock."""
    print("Testing AWS Credentials for Bedrock...")
    print("=" * 60)
    
    try:
        # Load settings
        settings = Settings()
        print(f"✅ Settings loaded")
        print(f"   Enable Bedrock: {settings.enable_bedrock}")
        print(f"   AWS Region: {settings.aws_region}")
        print(f"   AWS Access Key: {settings.aws_access_key_id[:10]}..." if settings.aws_access_key_id else "   AWS Access Key: None")
        
        if not settings.enable_bedrock:
            print("\n❌ Bedrock is disabled in configuration")
            print("   Set ENABLE_BEDROCK=true in .env file")
            return False
        
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            print("\n❌ AWS credentials missing")
            print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env file")
            return False
        
        # Create Bedrock client
        print("\n🔧 Creating Bedrock client...")
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        
        print("✅ Bedrock client created successfully")
        
        # Test by listing models (this uses bedrock client, not bedrock-runtime)
        print("\n🧪 Testing Bedrock connection...")
        bedrock_client_control = boto3.client(
            'bedrock',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        
        # List foundation models
        response = bedrock_client_control.list_foundation_models()
        models = response.get('modelSummaries', [])
        
        print(f"✅ Credentials are VALID!")
        print(f"✅ Found {len(models)} foundation models")
        
        # Check if Claude models are available
        claude_models = [m for m in models if 'claude' in m.get('modelId', '').lower()]
        if claude_models:
            print(f"✅ Claude models available:")
            for model in claude_models:
                print(f"   - {model.get('modelId')}")
        else:
            print("⚠️  No Claude models found in region")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Bedrock is ready to use!")
        print("\nNext Steps:")
        print("1. Restart your backend server")
        print("2. Run GitHub analysis")
        print("3. You should now get real-time AI suggestions")
        
        return True
        
    except NoCredentialsError:
        print("\n❌ No AWS credentials found")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        print(f"\n❌ AWS Error: {error_code}")
        print(f"   {error_msg}")
        
        if error_code == 'UnrecognizedClientException':
            print("\n💡 Solution:")
            print("   1. Your AWS credentials are invalid or expired")
            print("   2. Generate new credentials from AWS Console")
            print("   3. Update .env file with new credentials")
        elif error_code == 'InvalidClientTokenId':
            print("\n💡 Solution:")
            print("   1. Your AWS Access Key ID is invalid")
            print("   2. Generate new credentials from AWS Console")
            print("   3. Make sure the IAM user has Bedrock permissions")
        elif error_code == 'SignatureDoesNotMatch':
            print("\n💡 Solution:")
            print("   1. Your AWS Secret Access Key is incorrect")
            print("   2. Double-check the secret key in .env file")
            print("   3. Make sure there are no extra spaces")
        else:
            print(f"\n💡 Check AWS documentation for error: {error_code}")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_aws_credentials()
