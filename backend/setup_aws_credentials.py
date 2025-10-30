#!/usr/bin/env python3
"""
AWS Credentials Setup Script for Bedrock Service
This script helps you configure AWS credentials for the Bedrock service.
"""

import os
import sys
from pathlib import Path

def setup_aws_credentials():
    """Setup AWS credentials for Bedrock service."""
    print("🔧 AWS Credentials Setup for Bedrock Service")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
        print("Creating .env file...")
        env_file.touch()
    
    print("\n📋 Required AWS Credentials:")
    print("1. AWS Access Key ID")
    print("2. AWS Secret Access Key") 
    print("3. AWS Region (e.g., us-east-1)")
    print("4. Optional: AWS Session Token (for temporary credentials)")
    
    print("\n🔑 How to get AWS credentials:")
    print("1. Go to AWS Console → IAM → Users → Your User → Security Credentials")
    print("2. Create Access Key")
    print("3. Copy Access Key ID and Secret Access Key")
    print("4. Choose a region where Bedrock is available")
    
    print("\n🌍 Available Bedrock Regions:")
    print("- us-east-1 (N. Virginia)")
    print("- us-west-2 (Oregon)")
    print("- eu-west-1 (Ireland)")
    print("- ap-southeast-1 (Singapore)")
    
    # Get credentials from user
    print("\n" + "=" * 50)
    access_key = input("Enter AWS Access Key ID: ").strip()
    secret_key = input("Enter AWS Secret Access Key: ").strip()
    region = input("Enter AWS Region (default: us-east-1): ").strip() or "us-east-1"
    session_token = input("Enter AWS Session Token (optional, press Enter to skip): ").strip()
    
    # Write to .env file
    env_content = f"""# AWS Credentials for Bedrock Service
AWS_ACCESS_KEY_ID={access_key}
AWS_SECRET_ACCESS_KEY={secret_key}
AWS_DEFAULT_REGION={region}
"""
    
    if session_token:
        env_content += f"AWS_SESSION_TOKEN={session_token}\n"
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Credentials saved to {env_file.absolute()}")
    
    # Test credentials
    print("\n🧪 Testing AWS credentials...")
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Create Bedrock client
        if session_token:
            bedrock_client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token,
                region_name=region
            )
        else:
            bedrock_client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        
        # Test with a simple list models call
        try:
            response = bedrock_client.list_foundation_models()
            print("✅ AWS credentials are valid!")
            print(f"✅ Bedrock service is accessible in {region}")
            print(f"✅ Found {len(response.get('modelSummaries', []))} foundation models")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnauthorizedOperation':
                print("❌ AWS credentials are invalid or insufficient permissions")
                print("💡 Make sure your IAM user has Bedrock permissions")
            elif error_code == 'InvalidRegion':
                print(f"❌ Bedrock is not available in region {region}")
                print("💡 Try a different region like us-east-1 or us-west-2")
            else:
                print(f"❌ AWS error: {error_code}")
                print(f"💡 Error details: {e.response['Error']['Message']}")
        except NoCredentialsError:
            print("❌ No AWS credentials found")
            print("💡 Make sure the credentials are correctly set")
            
    except ImportError:
        print("❌ boto3 not installed")
        print("💡 Run: pip install boto3")
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
    
    print("\n" + "=" * 50)
    print("📝 Next Steps:")
    print("1. If credentials are valid, restart the backend server")
    print("2. Run: python reportanalysis_enhanced_v2.py")
    print("3. Test the GitHub analysis feature")
    print("4. You should now get real-time AI suggestions instead of fallback ones")
    
    print("\n🔒 Security Note:")
    print("- Never commit .env file to version control")
    print("- Use IAM roles in production")
    print("- Rotate credentials regularly")

if __name__ == "__main__":
    setup_aws_credentials()
