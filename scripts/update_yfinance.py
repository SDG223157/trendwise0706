#!/usr/bin/env python3
"""
Automated yfinance Update Script
Checks for yfinance updates and updates if available
"""

import subprocess
import sys
import json
import requests
from packaging import version

def get_current_version():
    """Get currently installed yfinance version"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'yfinance'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(': ')[1].strip()
    except Exception as e:
        print(f"Error getting current version: {e}")
    return None

def get_latest_version():
    """Get latest yfinance version from PyPI"""
    try:
        response = requests.get('https://pypi.org/pypi/yfinance/json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['info']['version']
    except Exception as e:
        print(f"Error getting latest version: {e}")
    return None

def update_yfinance():
    """Update yfinance to latest version"""
    try:
        print("📦 Updating yfinance...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yfinance'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ yfinance updated successfully!")
            return True
        else:
            print(f"❌ Update failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Update error: {e}")
        return False

def main():
    print("🔍 Checking yfinance version...")
    
    current = get_current_version()
    latest = get_latest_version()
    
    if not current or not latest:
        print("❌ Could not check versions")
        return
    
    print(f"Current version: {current}")
    print(f"Latest version: {latest}")
    
    if version.parse(current) < version.parse(latest):
        print(f"🔄 Update available: {current} → {latest}")
        
        # Check if it's a major version change (potentially breaking)
        current_major = version.parse(current).major
        latest_major = version.parse(latest).major
        
        if current_major != latest_major:
            print(f"⚠️  Major version change detected ({current_major} → {latest_major})")
            print("   Consider reviewing changelog before updating")
            response = input("   Continue with update? (y/N): ").lower()
            if response != 'y':
                print("   Update cancelled")
                return
        
        update_yfinance()
    else:
        print("✅ yfinance is up to date!")

if __name__ == "__main__":
    main() 