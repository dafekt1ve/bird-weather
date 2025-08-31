#!/bin/bash
# Start script for eBird Weather Mapper

echo "🌤️  Starting eBird Weather Mapper Server..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
    echo "✅ Loaded environment variables"
else
    echo "❌ .env file not found! Run setup.py first."
    exit 1
fi

# Check if API key is set
if [ -z "$EBIRD_API_KEY" ]; then
    echo "❌ EBIRD_API_KEY not set in .env file"
    exit 1
fi

echo "📡 eBird API Key: ✅ Configured"
echo "🌐 Weather Site URL: $WEATHER_SITE_URL"
echo "🚀 Starting server on port $PORT..."

cd python
python herbie_server.py
