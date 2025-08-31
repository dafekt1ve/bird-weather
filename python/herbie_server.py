from flask import Flask, request, jsonify
from flask_cors import CORS
import herbie_datagrab
import traceback
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app, origins="chrome-extension://adngbbngkdibkmdchidpiajjgljdlgad")

# Load eBird API key from environment variable
EBIRD_API_KEY = os.getenv('EBIRD_API_KEY')
if not EBIRD_API_KEY:
    print("WARNING: EBIRD_API_KEY environment variable not set!")

# eBird API base URL
EBIRD_BASE_URL = "https://api.ebird.org/v2"

@app.route("/api/get_gfs_data", methods=["POST", "OPTIONS"])
def get_gfs_data():
    if request.method == 'OPTIONS':
        # CORS preflight response
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    # Handle actual POST
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')
    date = data.get('date')
    level = data.get('level', 850)

    try:
        result = herbie_datagrab.process_wind_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# NEW: eBird API Proxy Routes
@app.route("/api/ebird/<path:endpoint>", methods=["GET", "OPTIONS"])
def ebird_proxy(endpoint):
    """Proxy eBird API requests to hide API key"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    if not EBIRD_API_KEY:
        return jsonify({"error": "eBird API key not configured"}), 500
    
    try:
        # Build the full eBird API URL
        ebird_url = f"{EBIRD_BASE_URL}/{endpoint}"
        
        # Forward query parameters from the original request
        params = dict(request.args)
        
        # Make request to eBird API with our hidden API key
        headers = {
            'X-eBirdApiToken': EBIRD_API_KEY
        }
        
        response = requests.get(ebird_url, headers=headers, params=params)
        
        # Return the response
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": f"eBird API error: {response.status_code}",
                "message": response.text
            }), response.status_code
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

# NEW: Checklist data extraction endpoint
@app.route("/api/checklist/<checklist_id>", methods=["GET", "OPTIONS"])
def get_checklist_data(checklist_id):
    """Get specific checklist data with location and datetime"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    if not EBIRD_API_KEY:
        return jsonify({"error": "eBird API key not configured"}), 500
    
    try:
        # Get checklist data from eBird
        headers = {'X-eBirdApiToken': EBIRD_API_KEY}
        response = requests.get(f"{EBIRD_BASE_URL}/product/checklist/view/{checklist_id}", headers=headers)
        
        if response.status_code == 200:
            checklist_data = response.json()
            
            # Extract the key information needed for weather mapping
            extracted_data = {
                "checklistId": checklist_id,
                "lat": checklist_data.get("loc", {}).get("latitude"),
                "lng": checklist_data.get("loc", {}).get("longitude"),
                "location": checklist_data.get("loc", {}).get("name", "Unknown Location"),
                "datetime": checklist_data.get("obsDt"),
                "numSpecies": checklist_data.get("numSpecies", 0),
                "durationHrs": checklist_data.get("durationHrs"),
                "distanceKms": checklist_data.get("distanceKms"),
                "submissionMethodCode": checklist_data.get("submissionMethodCode"),
                "creationDt": checklist_data.get("creationDt"),
                "lastEditedDt": checklist_data.get("lastEditedDt")
            }
            
            return jsonify(extracted_data)
        else:
            return jsonify({
                "error": f"Failed to fetch checklist: {response.status_code}",
                "message": response.text
            }), response.status_code
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error fetching checklist: {str(e)}"}), 500

# NEW: Weather data endpoint specifically for external weather site
@app.route("/api/weather", methods=["GET", "OPTIONS"])
def get_weather_for_location():
    """Get weather data for a specific location and time - for external website"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    datetime_str = request.args.get('datetime')
    level = request.args.get('level', default=850, type=int)
    
    if not all([lat, lng, datetime_str]):
        return jsonify({"error": "Missing required parameters: lat, lng, datetime"}), 400
    
    try:
        result = herbie_datagrab.process_wind_data(lat, lng, datetime_str, level)
        if result is not None:
            return jsonify({
                "status": "success", 
                "data": result,
                "metadata": {
                    "lat": lat,
                    "lng": lng,
                    "datetime": datetime_str,
                    "level": level,
                    "processed_at": datetime.now().isoformat()
                }
            })
        else:
            return jsonify({"status": "error", "message": "Failed to fetch weather data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# Health check endpoint
@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ebird_api_configured": EBIRD_API_KEY is not None,
        "services": ["gfs_data", "ebird_proxy", "weather_api"]
    })

if __name__ == '__main__':
    # Print startup info
    print("🚀 Starting Enhanced Herbie Server...")
    print(f"📡 eBird API Key: {'✅ Configured' if EBIRD_API_KEY else '❌ Missing'}")
    print(f"🌤️  Weather Data: ✅ Available")
    print(f"🔗 CORS: ✅ Enabled for chrome-extension://adngbbngkdibkmdchidpiajjgljdlgad")
    print("📍 Endpoints available:")
    print("   - POST /api/get_gfs_data (existing)")
    print("   - GET  /api/ebird/<endpoint> (new - eBird proxy)")
    print("   - GET  /api/checklist/<id> (new - checklist data)")
    print("   - GET  /api/weather (new - for external website)")
    print("   - GET  /api/health (new - health check)")
    
    app.run(debug=True, host="0.0.0.0", port=8000)