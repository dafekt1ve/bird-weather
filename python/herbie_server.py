from flask import Flask, request, jsonify
from flask_cors import CORS
import herbie_datagrab
import traceback

app = Flask(__name__)
CORS(app, origins="chrome-extension://adngbbngkdibkmdchidpiajjgljdlgad")  # Allow only your extension's origin

@app.route("/api/get_gfs_wind_data", methods=["POST", "OPTIONS"])
def get_gfs_wind_data():
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
            return jsonify({"status": "error", "message": "Failed to fetch GFS wind data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_gfs_precip_data", methods=["POST", "OPTIONS"])
def get_gfs_precip_data():
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
    level = data.get('level', "surface")

    try:
        result = herbie_datagrab.process_precip_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS precip data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_gfs_cloud_data", methods=["POST", "OPTIONS"])
def get_gfs_cloud_data():
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
    level = data.get('level', "low")

    try:
        result = herbie_datagrab.process_cloud_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS cloud data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route("/api/get_gfs_sfc_temp_data", methods=["POST", "OPTIONS"])
def get_gfs_sfc_temp_data():
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
    level = data.get('level', "2 m above ground")

    try:
        result = herbie_datagrab.process_sfc_temp_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS sfc temp data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get_gfs_refc_data", methods=["POST", "OPTIONS"])
def get_gfs_refc_data():
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
    level = data.get('level', "entire atmosphere")

    try:
        result = herbie_datagrab.process_refc_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS sfc temp data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/get_gfs_vvel_data", methods=["POST", "OPTIONS"])
def get_gfs_vvel_data():
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
    print(level)

    try:
        result = herbie_datagrab.process_vvel_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS vertical velocity data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    


@app.route("/api/get_gfs_cape_data", methods=["POST", "OPTIONS"])
def get_gfs_cape_data():
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
    level = data.get('level', "surface")
    print(level)

    try:
        result = herbie_datagrab.process_cape_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS CAPE data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route("/api/get_gfs_cin_data", methods=["POST", "OPTIONS"])
def get_gfs_cin_data():
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
    level = data.get('level', "surface")
    print(level)

    try:
        result = herbie_datagrab.process_cin_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS CIN data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route("/api/get_gfs_divergence_data", methods=["POST", "OPTIONS"])
def get_gfs_divergence_data():
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
    print(level)

    try:
        result = herbie_datagrab.process_divergence_data(lat, lon, date, level)
        if result is not None:
            return jsonify({"status": "success", "message": result})
        else:
            return jsonify({"status": "error", "message": "Failed to fetch GFS Divergence data"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)
