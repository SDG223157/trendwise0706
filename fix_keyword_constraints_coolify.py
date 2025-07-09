#!/usr/bin/env python3
"""
Fix keyword table foreign key constraints on Coolify
This script runs the migration to fix the foreign key constraint in article_keywords
"""

import os
import sys
import subprocess
import logging
from flask import Flask
from flask_migrate import Migrate, upgrade

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to fix foreign key constraints"""
    
    try:
        # Initialize Flask app
        from app import create_app
        
        app = create_app()
        
        with app.app_context():
            logger.info("🔧 Running migration to fix keyword table foreign keys...")
            
            # Run the migration
            upgrade()
            
            logger.info("✅ Migration completed successfully!")
            logger.info("🔄 Foreign key constraints now point to news_search_index")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

def check_migration_status():
    """Check if the migration was successful"""
    
    try:
        from app import create_app
        from app.models import db
        
        app = create_app()
        
        with app.app_context():
            # Try to query the database to verify the foreign key works
            result = db.engine.execute("""
                SELECT 
                    TABLE_NAME,
                    COLUMN_NAME,
                    CONSTRAINT_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'article_keywords'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """).fetchall()
            
            logger.info("📊 Current foreign key constraints:")
            for row in result:
                logger.info(f"   {row[0]}.{row[1]} -> {row[3]}.{row[4]} (constraint: {row[2]})")
            
            # Check if the constraint points to news_search_index
            search_index_fk = any(row[3] == 'news_search_index' for row in result)
            
            if search_index_fk:
                logger.info("✅ Foreign key correctly points to news_search_index")
                return True
            else:
                logger.warning("⚠️  Foreign key still points to news_articles")
                return False
            
    except Exception as e:
        logger.error(f"❌ Error checking migration status: {str(e)}")
        return False

def main():
    """Main function"""
    
    logger.info("🚀 Starting foreign key constraint fix...")
    
    # Run migration
    if run_migration():
        logger.info("✅ Migration completed successfully!")
        
        # Check status
        if check_migration_status():
            logger.info("✅ Foreign key constraints are now correctly configured!")
            logger.info("🔄 You can now run keyword extraction:")
            logger.info("   python3 extract_keywords_from_news_search_index.py --test")
        else:
            logger.error("❌ Migration may not have completed correctly")
            return 1
    else:
        logger.error("❌ Migration failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 