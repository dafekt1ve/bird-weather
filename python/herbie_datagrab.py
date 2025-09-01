import herbie
import xarray as xr
import datetime
from flask import jsonify
import json
import os
from zoneinfo import ZoneInfo  # Python 3.9+
# If you're on older Python, use: from datetime import timezone

def fetch_gfs_data(lat, lon, date, fxx, level=850):
    try:
        print(f"Calling Herbie with: date={date}, fxx={fxx}, level={level}")
        forecast = herbie.Herbie(date, model="gfs", fxx=fxx)
        data = forecast.xarray(f"(UGRD|VGRD):{level} mb")
        data = data.assign_coords(longitude=(((data.longitude + 180) % 360) - 180))
        data = data.roll(longitude=int(len(data['longitude']) / 2), roll_coords=True)
        print(f"Successfully fetched GFS data: {data.dims}")
        return data
    except Exception as e:
        print(f"Error fetching GFS data: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_wind_data(lat, lon, date, level=850):
    print(f"Processing wind data request: lat={lat}, lon={lon}, date={date}, level={level}")
    
    try:
        # Parse the input datetime string and handle different formats
        if isinstance(date, str):
            # Handle ISO format with Z suffix or +00:00
            if date.endswith('Z'):
                date_str = date[:-1] + '+00:00'
            else:
                date_str = date
            
            # Parse as timezone-aware datetime
            target_date_utc = datetime.datetime.fromisoformat(date_str)
            print(f"Parsed target date (UTC): {target_date_utc}")
            
            # If it's not timezone-aware, assume it's UTC
            if target_date_utc.tzinfo is None:
                target_date_utc = target_date_utc.replace(tzinfo=ZoneInfo('UTC'))
        else:
            target_date_utc = date
            
    except Exception as e:
        print(f"Error parsing date '{date}': {e}")
        return None
    
    # Convert to UTC if it's not already
    if target_date_utc.tzinfo != ZoneInfo('UTC'):
        target_date_utc = target_date_utc.astimezone(ZoneInfo('UTC'))
        print(f"Converted to UTC: {target_date_utc}")
    
    # Find the appropriate GFS initialization time and forecast hour
    # GFS runs every 6 hours: 00, 06, 12, 18 UTC
    gfs_init_hours = [0, 6, 12, 18]
    
    # Find the most recent GFS initialization time before or at the target time
    target_hour = target_date_utc.hour
    
    # Find the closest GFS init time (floor)
    init_hour = max([h for h in gfs_init_hours if h <= target_hour], default=18)
    
    # If no suitable init hour found for today, use the last run from yesterday
    if init_hour > target_hour:
        init_date_utc = (target_date_utc - datetime.timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        fxx = target_hour + 6  # Hours from yesterday 18Z
    else:
        init_date_utc = target_date_utc.replace(hour=init_hour, minute=0, second=0, microsecond=0)
        fxx = target_hour - init_hour
    
    print(f"GFS initialization: {init_date_utc}, forecast hour: {fxx}")
    
    # Convert to naive datetime for Herbie (it expects naive UTC datetimes)
    init_date_naive = init_date_utc.replace(tzinfo=None)
    
    # Create data directory relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Generate filename
    date_str = init_date_naive.strftime("%Y%m%d%H")
    if fxx > 0:
        filename = os.path.join(data_dir, f"gfs_velocity_{date_str}_f{fxx:03d}_{level}mb.json")
    else:
        filename = os.path.join(data_dir, f"gfs_velocity_{date_str}_{level}mb.json")
    
    print(f"Looking for cached file: {filename}")
    
    # Check if file already exists and is recent
    if os.path.exists(filename):
        try:
            # Check if file is recent (less than 6 hours old)
            file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(filename))
            if file_age < datetime.timedelta(hours=6):
                print(f"Loading recent cached file: {filename}")
                with open(filename, "r") as f:
                    return json.load(f)
            else:
                print(f"Cached file is old ({file_age}), fetching new data...")
        except Exception as e:
            print(f"Error loading cached file: {e}")
    
    print("Fetching new GFS data...")
    
    try:
        gfs_data = fetch_gfs_data(lat, lon, init_date_naive, fxx, level)
        
        if gfs_data is not None:
            print("Successfully fetched GFS data, processing...")
            
            # Check if we have the required variables
            if 'u' not in gfs_data or 'v' not in gfs_data:
                print("Error: GFS data missing u or v components")
                print(f"Available variables: {list(gfs_data.keys())}")
                return None
            
            u = gfs_data['u']
            v = gfs_data['v']

            lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
            lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

            velocity_u = convert_wind_to_velocity_json(u, "u", level, target_date_utc, init_date_utc, lon_step, lat_step)
            velocity_v = convert_wind_to_velocity_json(v, "v", level, target_date_utc, init_date_utc, lon_step, lat_step)

            result = [velocity_u, velocity_v]
            
            # Save to cache
            try:
                with open(filename, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"Saved weather data to: {filename}")
            except Exception as e:
                print(f"Warning: Could not save cached file: {e}")
            
            print(f"Successfully processed wind data - returning {len(result)} components")
            return result
        else:
            print("Failed to fetch GFS data from Herbie")
            return None
            
    except Exception as e:
        print(f"Error processing wind data: {e}")
        import traceback
        traceback.print_exc()
        return None

def convert_wind_to_velocity_json(var, component_name, level, target_date, init_date, lon_step, lat_step):
    # Calculate forecast hour properly with timezone-aware datetimes
    if hasattr(target_date, 'tzinfo') and hasattr(init_date, 'tzinfo'):
        forecast_hour = int((target_date - init_date).total_seconds() // 3600)
    else:
        # Fallback for naive datetimes
        forecast_hour = int((target_date.replace(tzinfo=None) - init_date.replace(tzinfo=None)).total_seconds() // 3600)
    
    # Convert timezone-aware datetime to string for JSON serialization
    if hasattr(init_date, 'tzinfo') and init_date.tzinfo is not None:
        ref_time_str = init_date.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        ref_time_str = init_date.strftime("%Y-%m-%d %H:%M:%S")

    header = {
        "discipline": 0,
        "disciplineName": "Meteorological products",
        "parameterCategory": 2,
        "parameterCategoryName": "Momentum",
        "parameterNumber": 2 if component_name == "u" else 3,
        "parameterNumberName": f"{'U' if component_name == 'u' else 'V'}-component_of_wind",
        "parameterUnit": "m.s-1",
        "forecastTime": forecast_hour,
        "refTime": ref_time_str,
        "surface1Type": 100,
        "surface1TypeName": "Isobaric surface",
        "surface1Value": level,
        "gridDefinition": "Latitude_Longitude",
        "nx": var.sizes["longitude"],
        "ny": var.sizes["latitude"],
        "lo1": float(var.longitude.min()),
        "la1": float(var.latitude.max()),
        "lo2": float(var.longitude.max()),
        "la2": float(var.latitude.min()),
        "dx": lon_step,
        "dy": lat_step,
        "unit": "m/s"
    }

    # Convert data to list, handling potential NaN values
    data_array = var.values.flatten(order="C")
    data = []
    for value in data_array:
        if hasattr(value, 'item'):  # numpy scalar
            val = value.item()
        else:
            val = float(value)
        
        # Replace NaN/inf with None for JSON serialization
        if not (val == val):  # Check for NaN
            data.append(None)
        elif val == float('inf') or val == float('-inf'):
            data.append(None)
        else:
            data.append(val)

    return {
        "header": header,
        "data": data
    }