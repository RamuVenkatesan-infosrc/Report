#!/usr/bin/env python3
"""
Update AWS credentials in .env file.
"""

import os
from pathlib import Path

def update_aws_credentials():
    """Update AWS credentials in .env file."""
    print("🔐 AWS Credentials Update")
    print("=" * 60)
    
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    # Read current content
    with open(env_file, 'r') as f:
        content = f.read()
    
    print("\n📋 Enter your new AWS credentials:")
    print("(Get these from: AWS Console → IAM → Users → Security Credentials)")
    print()
    
    # Get new credentials
    new_access_key = input("AWS Access Key ID: ").strip()
    new_secret_key = input("AWS Secret Access Key: ").strip()
    new_region = input("AWS Region (default: us-east-1): ").strip() or "us-east-1"
    
    # Update content
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if line.startswith('AWS_ACCESS_KEY_ID='):
            new_lines.append(f'AWS_ACCESS_KEY_ID={new_access_key}')
        elif line.startswith('AWS_SECRET_ACCESS_KEY='):
            new_lines.append(f'AWS_SECRET_ACCESS_KEY={new_secret_key}')
        elif line.startswith('AWS_DEFAULT_REGION='):
            new_lines.append(f'AWS_DEFAULT_REGION={new_region}')
        else:
            new_lines.append(line)
    
    # Write back
    with open(env_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\n✅ Credentials updated in {env_file.absolute()}")
    print("\n🧪 Testing new credentials...")
    
    # Test new credentials
    from test_aws_credentials import test_aws_credentials
    result = test_aws_credentials()
    
    if result:
        print("\n✅ Credentials are valid! You can now use Bedrock.")
        print("\nNext Steps:")
        print("1. Restart your backend server")
        print("2. Run GitHub analysis")
        print("3. You should now get real-time AI suggestions")
    else:
        print("\n❌ Credentials are still invalid")
        print("Please check:")
        print("1. Your AWS account has Bedrock access")
        print("2. Your IAM user has required permissions")
        print("3. The region supports Bedrock")
    
    return result

if __name__ == "__main__":
    update_aws_credentials()

