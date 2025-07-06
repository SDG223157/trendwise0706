#!/usr/bin/env python3
"""
Check the actual schema of news_search_index table
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def check_search_index_schema():
    """Check the actual schema of news_search_index table"""
    
    print("🔍 CHECKING SEARCH INDEX SCHEMA")
    print("=" * 50)
    
    try:
        # Database connection
        db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # Get table schema
            schema_result = session.execute(text("""
                DESCRIBE news_search_index
            """)).fetchall()
            
            print("📋 NEWS_SEARCH_INDEX TABLE COLUMNS:")
            print("-" * 50)
            for row in schema_result:
                print(f"   • {row.Field}: {row.Type} {'(NULL)' if row.Null == 'YES' else '(NOT NULL)'}")
            
            # Also check news_articles schema for comparison
            print("\n📋 NEWS_ARTICLES TABLE COLUMNS:")
            print("-" * 50)
            articles_schema = session.execute(text("""
                DESCRIBE news_articles
            """)).fetchall()
            
            for row in articles_schema:
                print(f"   • {row.Field}: {row.Type} {'(NULL)' if row.Null == 'YES' else '(NOT NULL)'}")
                
            # Check if any data exists
            search_count = session.execute(text("SELECT COUNT(*) as count FROM news_search_index")).fetchone()
            articles_count = session.execute(text("SELECT COUNT(*) as count FROM news_articles")).fetchone()
            
            print(f"\n📊 CURRENT DATA:")
            print(f"   • news_search_index: {search_count.count} entries")
            print(f"   • news_articles: {articles_count.count} entries")
            
    except Exception as e:
        print(f"❌ Error checking schema: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    check_search_index_schema() 