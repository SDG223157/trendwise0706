#!/bin/bash

echo "Building Docker image..."
docker build -t stock-analysis-app .

echo "Running Docker container..."
docker run -p 3000:3000 \
    -e FLASK_APP=app \
    -e FLASK_ENV=production \
    -e SECRET_KEY=test-key \
    -e PORT=3000 \
    stock-analysis-app

