#!/usr/bin/env python3
"""
Coolify-specific yfinance Update Script
Designed to run as a scheduled task in Coolify environment
"""

import subprocess
import sys
import os
import requests
from packaging import version
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

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
        logger.error(f"Error getting current version: {e}")
    return None

def get_latest_compatible_version():
    """Get latest yfinance version compatible with our constraints"""
    try:
        response = requests.get('https://pypi.org/pypi/yfinance/json', timeout=10)
        if response.status_code == 200:
            data = response.json()
            latest = data['info']['version']
            
            # Check if it's within our constraint (>=0.2.63,<0.3.0)
            if version.parse(latest) >= version.parse("0.2.63") and version.parse(latest) < version.parse("0.3.0"):
                return latest
            else:
                logger.info(f"Latest version {latest} is outside our constraints")
                return None
    except Exception as e:
        logger.error(f"Error getting latest version: {e}")
    return None

def update_yfinance():
    """Update yfinance within constraints"""
    try:
        logger.info("📦 Updating yfinance within version constraints...")
        
        # Use the constraint from requirements.txt
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', 
            '--upgrade', 'yfinance>=0.2.63,<0.3.0'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ yfinance updated successfully!")
            
            # Test the import
            test_result = subprocess.run([
                sys.executable, '-c', 'import yfinance as yf; print("Import successful")'
            ], capture_output=True, text=True)
            
            if test_result.returncode == 0:
                logger.info("✅ yfinance import test passed")
                return True
            else:
                logger.error(f"❌ yfinance import test failed: {test_result.stderr}")
                return False
        else:
            logger.error(f"❌ Update failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Update error: {e}")
        return False

def restart_application():
    """Restart the application if in Coolify environment"""
    coolify_restart_url = os.getenv('COOLIFY_RESTART_URL')
    coolify_restart_token = os.getenv('COOLIFY_RESTART_TOKEN')
    
    if coolify_restart_url and coolify_restart_token:
        try:
            logger.info("🔄 Triggering application restart...")
            headers = {'Authorization': f'Bearer {coolify_restart_token}'}
            response = requests.post(coolify_restart_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.info("✅ Application restart triggered successfully")
                return True
            else:
                logger.error(f"❌ Restart failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Restart error: {e}")
            return False
    else:
        logger.info("ℹ️  No restart configuration found (COOLIFY_RESTART_URL/TOKEN)")
        return False

def main():
    logger.info("🔍 Checking yfinance version in Coolify environment...")
    
    current = get_current_version()
    latest = get_latest_compatible_version()
    
    if not current:
        logger.error("❌ Could not determine current version")
        return
    
    logger.info(f"Current version: {current}")
    
    if not latest:
        logger.info("✅ No compatible updates available")
        return
    
    logger.info(f"Latest compatible version: {latest}")
    
    if version.parse(current) < version.parse(latest):
        logger.info(f"🔄 Update available: {current} → {latest}")
        
        if update_yfinance():
            # Optionally restart the application
            restart_application()
        else:
            logger.error("❌ Update failed")
    else:
        logger.info("✅ yfinance is up to date!")

if __name__ == "__main__":
    main() 