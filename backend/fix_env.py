#!/usr/bin/env python3
"""
Simple script to rename the env file from ,env to .env
"""
import os
import shutil

def fix_env_file():
    """Rename ,env to .env"""
    old_name = ",env"
    new_name = ".env"
    
    if os.path.exists(old_name):
        shutil.move(old_name, new_name)
        print(f"✅ Renamed {old_name} to {new_name}")
    elif os.path.exists(new_name):
        print(f"✅ {new_name} already exists")
    else:
        print(f"❌ Neither {old_name} nor {new_name} found")

if __name__ == "__main__":
    fix_env_file()
