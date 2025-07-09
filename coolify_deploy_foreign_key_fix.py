#!/usr/bin/env python3
"""
Deployment script for Coolify to fix foreign key constraints
Run this script on your Coolify server to fix the keyword table foreign keys
"""

import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main deployment function"""
    
    logger.info("🚀 Starting foreign key constraint fix deployment on Coolify...")
    
    # Commands to run on Coolify
    commands = [
        "# Fix foreign key constraints in keyword tables",
        "echo '🔧 Running foreign key constraint fix migration...'",
        "python3 -m flask db upgrade fix_keyword_fk",
        "echo '✅ Foreign key constraints fixed!'",
        "echo '🔄 Verifying foreign key constraints...'",
        "python3 -c \"from app import create_app; from app.models import db; app=create_app(); app.app_context().push(); result=db.engine.execute('SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = \\'article_keywords\\' AND REFERENCED_TABLE_NAME IS NOT NULL').fetchall(); print('📊 Foreign key constraints:', result)\"",
        "echo '🎯 Now you can test keyword extraction:'",
        "echo '   python3 extract_keywords_from_news_search_index.py --test'",
    ]
    
    # Write deployment script
    script_content = "\n".join(commands)
    
    with open('run_foreign_key_fix.sh', 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Foreign key constraint fix script for Coolify\n")
        f.write("set -e\n\n")
        f.write(script_content)
    
    # Make script executable
    os.chmod('run_foreign_key_fix.sh', 0o755)
    
    logger.info("📝 Created deployment script: run_foreign_key_fix.sh")
    logger.info("🔄 To deploy on Coolify:")
    logger.info("   1. Upload run_foreign_key_fix.sh to your Coolify server")
    logger.info("   2. SSH into your Coolify server")
    logger.info("   3. Run: ./run_foreign_key_fix.sh")
    logger.info("   4. Test keyword extraction with: python3 extract_keywords_from_news_search_index.py --test")
    
    # Also show the commands to run manually
    print("\n" + "="*60)
    print("🎯 MANUAL COMMANDS FOR COOLIFY:")
    print("="*60)
    print("If you prefer to run commands manually on Coolify:")
    print("")
    for cmd in commands:
        if not cmd.startswith("#"):
            print(f"  {cmd}")
    print("")
    print("="*60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 