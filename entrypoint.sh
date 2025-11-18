#!/bin/bash
set -e

echo "🚀 Starting Org Social Host application..."

# Create storage directory if it doesn't exist
echo "📁 Creating storage directory..."
mkdir -p /app/storage

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Check for any issues
echo "🔍 Checking Django configuration..."
python manage.py check

# Start Django development server
echo "🎯 Starting Django development server on 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000
