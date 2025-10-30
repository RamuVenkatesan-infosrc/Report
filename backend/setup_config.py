"""
Configuration setup script for the Enhanced API Performance Analyzer.
This script helps users set up their environment variables.
"""
import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables for the application."""
    print("🚀 Enhanced API Performance Analyzer - Configuration Setup")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Found existing .env file")
        response = input("Do you want to update it? (y/n): ").lower().strip()
        if response != 'y':
            print("Configuration setup cancelled.")
            return
    
    print("\n📝 Please provide the following configuration:")
    print("(Press Enter to keep existing values or skip)")
    
    # AWS Configuration
    print("\n🔧 AWS Configuration:")
    aws_access_key = input("AWS Access Key ID: ").strip()
    aws_secret_key = input("AWS Secret Access Key: ").strip()
    aws_region = input("AWS Region (default: us-east-1): ").strip() or "us-east-1"
    
    # GitHub Configuration
    print("\n🐙 GitHub Configuration:")
    github_token = input("GitHub Personal Access Token: ").strip()
    
    # Bedrock Configuration
    print("\n🤖 Bedrock Configuration:")
    bedrock_model = input("Bedrock Model ID (default: anthropic.claude-3-sonnet-20240229-v1:0): ").strip() or "anthropic.claude-3-sonnet-20240229-v1:0"
    max_tokens = input("Max Tokens (default: 300): ").strip() or "300"
    temperature = input("Temperature (default: 0.7): ").strip() or "0.7"
    
    # Application Configuration
    print("\n⚙️ Application Configuration:")
    log_level = input("Log Level (default: INFO): ").strip() or "INFO"
    
    # Create .env content
    env_content = f"""# AWS Configuration
AWS_ACCESS_KEY_ID={aws_access_key}
AWS_SECRET_ACCESS_KEY={aws_secret_key}
AWS_REGION={aws_region}

# Bedrock Configuration
BEDROCK_MODEL_ID={bedrock_model}
MAX_TOKENS={max_tokens}
TEMPERATURE={temperature}

# GitHub Configuration
GITHUB_TOKEN={github_token}

# Application Configuration
LOG_LEVEL={log_level}
"""
    
    # Write .env file
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        print("\n✅ Configuration saved to .env file!")
        print("\n🚀 You can now run the application:")
        print("   python reportanalysis_enhanced.py")
        print("   or")
        print("   uvicorn reportanalysis_enhanced:app --reload")
        
    except Exception as e:
        print(f"\n❌ Error saving configuration: {str(e)}")
        print("Please create the .env file manually using the template.")

def validate_github_token(token):
    """Validate GitHub token format."""
    if not token:
        return False, "Token is empty"
    
    if not token.startswith(('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_')):
        return False, "Invalid token format. GitHub tokens should start with ghp_, gho_, ghu_, ghs_, or ghr_"
    
    if len(token) < 20:
        return False, "Token seems too short"
    
    return True, "Valid token format"

def get_github_token_help():
    """Display help for getting GitHub token."""
    print("\n🔑 How to get a GitHub Personal Access Token:")
    print("1. Go to GitHub.com and sign in")
    print("2. Click your profile picture → Settings")
    print("3. Scroll down and click 'Developer settings'")
    print("4. Click 'Personal access tokens' → 'Tokens (classic)'")
    print("5. Click 'Generate new token' → 'Generate new token (classic)'")
    print("6. Give it a name like 'API Performance Analyzer'")
    print("7. Select scopes: 'repo' (Full control of private repositories)")
    print("8. Click 'Generate token'")
    print("9. Copy the token (it starts with 'ghp_')")
    print("10. Paste it when prompted")

if __name__ == "__main__":
    print("Welcome to the Enhanced API Performance Analyzer Setup!")
    print("\nThis tool will help you configure the application.")
    
    # Show GitHub token help
    show_help = input("\nDo you need help getting a GitHub token? (y/n): ").lower().strip()
    if show_help == 'y':
        get_github_token_help()
        input("\nPress Enter when you have your GitHub token ready...")
    
    setup_environment()
