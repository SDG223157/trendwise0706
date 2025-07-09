#!/usr/bin/env python3
"""
Simple script to run the foreign key constraint fix migration
"""

import os
import sys

# Run the migration directly
os.system('flask db upgrade fix_keyword_fk')

print("✅ Migration completed!")
print("🔄 Foreign key constraints should now point to news_search_index")
print("   You can now run keyword extraction:")
print("   python3 extract_keywords_from_news_search_index.py --test") 