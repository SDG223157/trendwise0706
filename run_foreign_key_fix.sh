#!/bin/bash
# Foreign key constraint fix script for Coolify
set -e

# Fix foreign key constraints in keyword tables
echo '🔧 Running foreign key constraint fix migration...'
python3 -m flask db upgrade fix_keyword_fk
echo '✅ Foreign key constraints fixed!'
echo '🔄 Verifying foreign key constraints...'
python3 -c "from app import create_app; from app.models import db; app=create_app(); app.app_context().push(); result=db.engine.execute('SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = \'article_keywords\' AND REFERENCED_TABLE_NAME IS NOT NULL').fetchall(); print('📊 Foreign key constraints:', result)"
echo '🎯 Now you can test keyword extraction:'
echo '   python3 extract_keywords_from_news_search_index.py --test'