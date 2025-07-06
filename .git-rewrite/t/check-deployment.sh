#!/bin/bash

echo "Checking application configuration..."

# Check if required files exist
echo "Checking required files..."
files=("Dockerfile" "wsgi.py" "requirements.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

# Check if port 3000 is in use
echo -e "\nChecking port 3000..."
if lsof -i :3000 > /dev/null; then
    echo "❌ Port 3000 is in use"
else
    echo "✅ Port 3000 is available"
fi

# Check Python installation
echo -e "\nChecking Python installation..."
if command -v python3 > /dev/null; then
    echo "✅ Python is installed"
    python3 --version
else
    echo "❌ Python is not installed"
fi

# Check pip installation
echo -e "\nChecking pip installation..."
if command -v pip > /dev/null; then
    echo "✅ pip is installed"
    pip --version
else
    echo "❌ pip is not installed"
fi

# Check Docker installation
echo -e "\nChecking Docker installation..."
if command -v docker > /dev/null; then
    echo "✅ Docker is installed"
    docker --version
else
    echo "❌ Docker is not installed"
fi

echo -e "\nChecking environment variables..."
required_vars=("FLASK_APP" "FLASK_ENV" "SECRET_KEY" "PORT")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ $var is not set"
    else
        echo "✅ $var is set"
    fi
done
