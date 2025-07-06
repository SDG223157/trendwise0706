#!/bin/bash
# Simple yfinance update script

echo "🔍 Checking current yfinance version..."
current_version=$(pip show yfinance | grep Version | cut -d' ' -f2)
echo "Current version: $current_version"

echo "📦 Updating yfinance..."
pip install --upgrade yfinance

echo "✅ Update complete!"
new_version=$(pip show yfinance | grep Version | cut -d' ' -f2)
echo "New version: $new_version"

# Test the update
echo "🧪 Testing yfinance import..."
python -c "import yfinance as yf; print('✅ yfinance working correctly')" || echo "❌ yfinance import failed" 