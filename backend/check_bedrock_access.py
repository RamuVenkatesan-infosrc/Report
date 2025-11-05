#!/usr/bin/env python3
"""
Check if your AWS account has Bedrock access enabled.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.models.config import Settings

def check_bedrock_access():
    """Check Bedrock access for the account."""
    print("🔍 Checking AWS Bedrock Access")
    print("=" * 60)
    
    try:
        settings = Settings()
        
        # First, try to check if account has Bedrock enabled
        try:
            # Use regular boto3 to check if we can even connect to AWS
            sts_client = boto3.client(
                'sts',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            
            identity = sts_client.get_caller_identity()
            account_id = identity['Account']
            user_arn = identity['Arn']
            
            print(f"✅ AWS Account ID: {account_id}")
            print(f"✅ IAM User ARN: {user_arn}")
            
            # Now try to access Bedrock
            print("\n🧪 Checking Bedrock access...")
            bedrock_client = boto3.client(
                'bedrock',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            
            try:
                response = bedrock_client.list_foundation_models()
                models = response.get('modelSummaries', [])
                
                print(f"✅ Bedrock is ENABLED for this account!")
                print(f"✅ Found {len(models)} foundation models")
                
                # Check for Claude models
                claude_models = [m for m in models if 'claude' in m.get('modelId', '').lower()]
                if claude_models:
                    print(f"\n✅ Claude models available ({len(claude_models)}):")
                    for model in claude_models[:3]:  # Show first 3
                        model_name = model.get('modelName', 'Unknown')
                        model_id = model.get('modelId', 'Unknown')
                        print(f"   - {model_name} ({model_id})")
                else:
                    print("⚠️  No Claude models found in this region")
                
                print("\n" + "=" * 60)
                print("✅ Your AWS account HAS Bedrock access!")
                print("\nThe issue is likely:")
                print("1. Invalid credentials (they expired or were revoked)")
                print("2. The IAM user needs Bedrock permissions")
                
                print("\n💡 Next Steps:")
                print("1. Go to AWS Console → IAM → Users → Your User")
                print("2. Check 'Permissions' tab")
                print("3. Add policy: AmazonBedrockFullAccess")
                print("4. Go to Security Credentials")
                print("5. Create new Access Key")
                print("6. Update .env file with new credentials")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'UnrecognizedClientException':
                    print("\n❌ Credentials are INVALID or EXPIRED")
                    print("\n💡 Solution:")
                    print("1. Go to AWS Console → IAM → Users → Security Credentials")
                    print("2. Delete old access key")
                    print("3. Create NEW access key")
                    print("4. Copy Access Key ID and Secret")
                    print("5. Run: python update_aws_credentials.py")
                    
                elif error_code == 'AccessDeniedException':
                    print("\n❌ You DON'T have permission to access Bedrock")
                    print("\n💡 Solution:")
                    print("1. Go to AWS Console → IAM → Users")
                    print("2. Select your IAM user")
                    print("3. Click 'Add permissions' → 'Attach policies directly'")
                    print("4. Search for: AmazonBedrockFullAccess")
                    print("5. Attach the policy")
                    print("6. Wait 2-3 minutes for permissions to propagate")
                    
                else:
                    print(f"\n❌ Error: {error_code}")
                    print(f"   {e.response['Error']['Message']}")
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidClientTokenId':
                print("\n❌ AWS Access Key ID is INVALID")
                print("   Generate new credentials from AWS Console")
            elif e.response['Error']['Code'] == 'SignatureDoesNotMatch':
                print("\n❌ AWS Secret Access Key is INVALID")
                print("   Generate new credentials from AWS Console")
            else:
                print(f"\n❌ AWS Error: {e.response['Error']['Code']}")
                print(f"   {e.response['Error']['Message']}")
                
    except NoCredentialsError:
        print("❌ No AWS credentials found")
        print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_bedrock_access()

