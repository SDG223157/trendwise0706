#!/bin/bash

# Coolify Database Migration Script
# This script should be run as part of your Coolify deployment process

echo "🚀 Starting deployment with database migration..."
echo "📅 $(date)"

# Exit on any error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    print_error "DATABASE_URL environment variable is not set!"
    exit 1
fi

print_status "Database URL configured: ${DATABASE_URL%%://*}://***"

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    print_status "Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
    if [ $? -eq 0 ]; then
        print_status "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
fi

# Check if migrations directory exists
if [ ! -d "migrations" ]; then
    print_warning "Migrations directory not found. Initializing Flask-Migrate..."
    export FLASK_APP=wsgi.py
    flask db init
    print_status "Flask-Migrate initialized"
fi

# Set Flask app environment
export FLASK_APP=wsgi.py
export FLASK_ENV=production

# Run database migrations
print_status "Running database migrations..."
flask db upgrade

# Check if migration was successful
if [ $? -eq 0 ]; then
    print_status "✅ Database migration completed successfully!"
else
    print_error "❌ Database migration failed!"
    exit 1
fi

# Check database connection
print_status "Verifying database connection..."
python -c "
import os
from sqlalchemy import create_engine, text
from app import create_app, db

try:
    app = create_app()
    with app.app_context():
        # Simple query to test connection
        result = db.session.execute(text('SELECT 1 as test'))
        row = result.fetchone()
        if row and row[0] == 1:
            print('✅ Database connection verified')
        else:
            print('❌ Database connection test failed')
            exit(1)
except Exception as e:
    print(f'❌ Database connection error: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    print_error "Database connection verification failed!"
    exit 1
fi

# Optional: Run any custom scripts
if [ -f "scripts/post_migration.py" ]; then
    print_status "Running post-migration scripts..."
    python scripts/post_migration.py
fi

print_status "🎉 Deployment with migration completed successfully!"
print_status "Application is ready to start"

# If running as part of start command, start the application
if [ "$1" = "--start" ]; then
    print_status "Starting application..."
    exec python wsgi.py
fi 