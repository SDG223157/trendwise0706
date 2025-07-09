#!/bin/bash

# Deploy Search Optimizations Script
echo "🚀 Deploying Search Optimizations..."

# 1. Install dependencies if needed
echo "📦 Checking dependencies..."
pip install apscheduler

# 2. Start sync service
echo "🔄 Starting index sync service..."
python -c "
from app.utils.search.index_sync_service import sync_service
sync_service.start_scheduler()
print('✅ Index sync service started')
"

# 3. Start cache warming service
echo "🔥 Starting cache warming service..."
python -c "
from app.utils.search.cache_warming_service import cache_warming_service
cache_warming_service.start_scheduler()
print('✅ Cache warming service started')
"

# 4. Run optimization tests
echo "🧪 Running optimization tests..."
python test_search_optimizations.py

echo "✅ Search optimization deployment completed!"
