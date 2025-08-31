import herbie
import xarray as xr
import datetime
from flask import jsonify
import json
import os
from datetime import timedelta, datetime
import numpy as np
import metpy.calc as mpcalc

def fetch_gfs_data(lat, lon, date, fxx, variable, level=850, max_retries=3, ):
    """
    Fetch GFS wind data for a given lat/lon, date, and forecast hour (fxx).
    Falls back to earlier model initializations if data isn't available.
    
    Parameters:
        lat (float): Latitude
        lon (float): Longitude
        date (datetime): Model initialization time (UTC)
        fxx (int): Forecast hour from model init
        variable (string): name of variable to grab from GFS data
        level (int): Pressure level in mb (default: 850)
        max_retries (int): Number of fallback attempts (default: 3)

    Returns:
        xarray.Dataset or None
    """
    for retry in range(max_retries + 1):
        try:
            model_init = date - timedelta(hours=6 * retry)
            forecast_hour = fxx + (6 * retry)
            print(f"Trying model init: {model_init} with fxx: {forecast_hour}")

            if (model_init < datetime.strptime("2021-01-01T00:00", "%Y-%m-%dT%H:%M")):
                if (model_init < datetime.strptime("2015-01-15T00:00", "%Y-%m-%dT%H:%M")):
                    forecast = herbie.Herbie(model_init.replace(tzinfo=None), model="gfs")
                    forecast.download()
                    forecast = herbie.Herbie(model_init.replace(tzinfo=None), model="gfs", fxx=forecast_hour)
                else:
                    return
            else:                
                forecast = herbie.Herbie(model_init.replace(tzinfo=None), model="gfs", fxx=forecast_hour)

            if (variable == "wind"):
                data = forecast.xarray(f"(UGRD|VGRD):{level} mb")
            elif (variable == "cloud"):
                data = forecast.xarray(f"TCDC:entire atmosphere:{fxx}")
            elif (variable == "precip"):
                data = forecast.xarray(f"APCP:surface:0")
            elif (variable == "sfc_temp"):
                data = forecast.xarray(f"TMP:2 m above ground")
            elif (variable == "refc"):
                data = forecast.xarray(f"REFC")
            elif (variable == "vvel"):
                data = forecast.xarray(f"VVEL:{level} mb")
            elif (variable == "cape"):
                data = forecast.xarray(f"CAPE:surface")
            elif (variable == "cin"):
                data = forecast.xarray(f"CIN:surface")
            else:
                print("Error: variable not found!")
            
            data = data.assign_coords(longitude=(((data.longitude + 180) % 360) - 180))
            data = data.roll(longitude=int(len(data['longitude']) / 2), roll_coords=True)
            return data

        except Exception as e:
            print(f"Attempt {retry}: Error fetching GFS data for {model_init} fxx={forecast_hour}: {e}")

    print("All fallback attempts failed.")
    return None



def process_wind_data(lat, lon, date, level=850):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing wind data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        init_date = target_date.replace(minute=0, second=0, microsecond=0)
        fxx = 0
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS wind data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_velocity_{date_str}_f{fxx:03d}_{level}mb.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing wind file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "wind", level)

    if gfs_data is not None:
        u = gfs_data['u']
        v = gfs_data['v']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        velocity_u = convert_wind_to_velocity_json(u, "u", level, target_date, init_date, lon_step, lat_step)
        velocity_v = convert_wind_to_velocity_json(v, "v", level, target_date, init_date, lon_step, lat_step)

        with open(filename, "w") as f:
            json.dump([velocity_u, velocity_v], f, separators=(',', ':'))

        return [velocity_u, velocity_v]
    else:
        return None
    
def convert_wind_to_velocity_json(var, component_name, level, date, init_time, lon_step, lat_step):
    forecast_hour = int((date - init_time).total_seconds() // 3600)

    header = {
        "discipline": 0,
        "disciplineName": "Meteorological products",
        "parameterCategory": 2,
        "parameterCategoryName": "Momentum",
        "parameterNumber": 2 if component_name == "u" else 3,
        "parameterNumberName": f"{'U' if component_name == 'u' else 'V'}-component_of_wind",
        "parameterUnit": "m.s-1",
        "forecastTime": forecast_hour,
        "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
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

    data = var.values.flatten(order="C").tolist()

    return {
        "header": header,
        "data": data
    }

def process_divergence_data(lat, lon, date, level=850):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing divergence data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        init_date = target_date.replace(minute=0, second=0, microsecond=0)
        fxx = 0
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS divergence data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_divergence_{date_str}_f{fxx:03d}_{level}mb.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing divergence file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)
        
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "wind", level)

    if gfs_data is not None:
        u = gfs_data['u']
        v = gfs_data['v']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        div = mpcalc.divergence(u, v)
        divergence = convert_var_to_json(div, "divergence", target_date, init_date, lon_step, lat_step)

        with open(filename, "w") as f:
            json.dump([divergence], f, separators=(',', ':'))

        return [divergence]
    else:
        return None




def process_precip_data(lat, lon, date, level='surface'):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing precip data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        fxx = 6 # specific to precip and clouds
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS precip data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_precip_{date_str}_f{fxx:03d}.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing precip file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "precip", level)

    if gfs_data is not None:
        apcp = gfs_data['tp']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        precip = convert_var_to_json(apcp, "tp", target_date, init_date, lon_step, lat_step)

        with open(filename, "w") as f:
            json.dump([precip], f, separators=(',', ':'))

        return [precip]
    else:
        return None
    

    
def process_cloud_data(lat, lon, date, level="low"):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing cloud data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        fxx = 6 # specific to precip and clouds
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS cloud data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_cloud_{date_str}_f{fxx:03d}.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing cloud file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "cloud", level)
    
    if gfs_data is not None:
        tcdc = gfs_data['tcc']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        cloud = convert_var_to_json(tcdc, "tcc", target_date, init_date, lon_step, lat_step)

        with open(filename, "w") as f:
            json.dump([cloud], f, separators=(',', ':'))

        return [cloud]
    else:
        return None
    


    
def process_sfc_temp_data(lat, lon, date, level="2 meters"):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing sfc temp data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        init_date = target_date.replace(minute=0, second=0, microsecond=0)
        fxx = 0
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS sfc temp data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_temp_{date_str}_f{fxx:03d}_2m.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing sfc temp file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "sfc_temp", "2 m above ground")
    
    if gfs_data is not None:
        t = gfs_data['t2m']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        sfc_temp = convert_var_to_json(t, "sfc_temp", target_date, init_date, lon_step, lat_step)

        with open(filename, "w") as f:
            json.dump([sfc_temp], f, separators=(',', ':'))

        return [sfc_temp]
    else:
        return None



    
def process_refc_data(lat, lon, date, level):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing reflectivity data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        fxx = 6 # specific to precip and clouds
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS reflectivity data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_refc_{date_str}_f{fxx:03d}.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing reflectivity file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "refc", "entire atmosphere")
    
    if gfs_data is not None:
        ref = gfs_data['refc']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        refc = convert_var_to_json(ref, "refc", target_date, init_date, lon_step, lat_step)

        with open(filename, "w") as f:
            json.dump([refc], f, separators=(',', ':'))

        return [refc]
    else:
        return None
    

    
def process_vvel_data(lat, lon, date, level=850):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing vertical velocity data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        init_date = target_date.replace(minute=0, second=0, microsecond=0)
        fxx = 0
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS vertical velocity data for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_vvel_{date_str}_f{fxx:03d}_{level}mb.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing vertical velocity file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "vvel", level)
    
    if gfs_data is not None:
        vv = gfs_data['w']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        vvel = convert_var_to_json(vv, "vvel", target_date, init_date, lon_step, lat_step, level)

        with open(filename, "w") as f:
            json.dump([vvel], f, separators=(',', ':'))

        return [vvel]
    else:
        return None
    

def process_cape_data(lat, lon, date, level="surface"):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing CAPE data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        init_date = target_date.replace(minute=0, second=0, microsecond=0)
        fxx = 0
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS vertical CAPE for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_cape_{date_str}_f{fxx:03d}.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing CAPE file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "cape", level)
    
    if gfs_data is not None:
        cape = gfs_data['cape']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        CAPE = convert_var_to_json(cape, "cape", target_date, init_date, lon_step, lat_step, level)

        with open(filename, "w") as f:
            json.dump([CAPE], f, separators=(',', ':'))

        return [CAPE]
    else:
        return None
    


def process_cin_data(lat, lon, date, level="surface"):
    target_date = datetime.fromisoformat(date).replace(tzinfo=None)
    print(f"Processing CIN data for date: {target_date}")
    if (target_date.hour % 6 == 0):
        init_date = target_date.replace(minute=0, second=0, microsecond=0)
        fxx = 0
    else:
        fxx = target_date.hour % 6
        init_date = target_date.replace(minute=0, second=0, microsecond=0) - timedelta(hours=fxx)

    print(f"Fetching GFS vertical CIN for lat: {lat}, lon: {lon}, level: {level}, init: {init_date}, fxx: {fxx}")

    # Construct unique filename per level and date
    date_str = init_date.strftime("%Y%m%d%H")
    filename = f"../data/gfs_cin_{date_str}_f{fxx:03d}.json"
    
    # Check if file already exists
    if os.path.exists(filename):
        print(f"Loading existing CIN file: {filename}")
        with open(filename, "r") as f:
            return json.load(f)

    # Otherwise fetch and process
    gfs_data = fetch_gfs_data(lat, lon, init_date, fxx, "cin", level)
    
    if gfs_data is not None:
        cin = gfs_data['cin']

        lon_step = float(gfs_data.longitude[1] - gfs_data.longitude[0])
        lat_step = float(gfs_data.latitude[0] - gfs_data.latitude[1])  # lat is decreasing

        CIN = convert_var_to_json(cin, "cin", target_date, init_date, lon_step, lat_step, level)

        with open(filename, "w") as f:
            json.dump([CIN], f, separators=(',', ':'))

        return [CIN]
    else:
        return None
    


def convert_var_to_json(var, component_name, date, init_time, lon_step, lat_step, level=None):
    forecast_hour = int((date - init_time).total_seconds() // 3600)

    if component_name == "tp":
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 2,
            "variableId": "VAR_0-1-8_L1_I3_Hour_S1",
            "parameterCategoryName": "Moisture",
            "parameterName": "Total precipitation",
            "parameterUnit": "kg.m-2",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
            "levelType": 1,
            "levelDesc": "Ground or water surface",
            "gridDefinition": "Latitude_Longitude",
            "nx": var.sizes["longitude"],
            "ny": var.sizes["latitude"],
            "lo1": float(var.longitude.min()),
            "la1": float(var.latitude.max()),
            "lo2": float(var.longitude.max()),
            "la2": float(var.latitude.min()),
            "dx": lon_step,
            "dy": lat_step,
            "statisticalProcessType": "Accumulation"
        }
    if component_name == "tcc":
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 2,
            "variableId": "VAR_0-6-1_L214_I3_Hour_S0",
            "parameterCategoryName": "Cloud",
            "parameterName": "Total cloud cover",
            "parameterUnit": "%",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
            "levelType": 214,
            "levelDesc": "Low cloud layer",
            "gridDefinition": "Latitude_Longitude",
            "nx": var.sizes["longitude"],
            "ny": var.sizes["latitude"],
            "lo1": float(var.longitude.min()),
            "la1": float(var.latitude.max()),
            "lo2": float(var.longitude.max()),
            "la2": float(var.latitude.min()),
            "dx": lon_step,
            "dy": lat_step
        }

    if component_name == "sfc_temp":
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 0,
            "variableId": "VAR_0-0-0_L103",
            "parameterCategoryName": "Temperature",
            "parameterName": "Temperature",
            "parameterUnit": "K",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
            "levelType": 103,
            "levelDesc": "Specified height level above ground",
            "gridDefinition": "Latitude_Longitude",
            "nx": var.sizes["longitude"],
            "ny": var.sizes["latitude"],
            "lo1": float(var.longitude.min()),
            "la1": float(var.latitude.max()),
            "lo2": float(var.longitude.max()),
            "la2": float(var.latitude.min()),
            "dx": lon_step,
            "dy": lat_step,
            "statisticalProcessType": "UnknownStatType--1",
        }

    if component_name == "refc":
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 0,
            "variableId": "VAR_0-0-0_L103",
            "parameterCategoryName": "Temperature",
            "parameterName": "Temperature",
            "parameterUnit": "K",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
            "levelType": 103,
            "levelDesc": "Specified height level above ground",
            "gridDefinition": "Latitude_Longitude",
            "nx": var.sizes["longitude"],
            "ny": var.sizes["latitude"],
            "lo1": float(var.longitude.min()),
            "la1": float(var.latitude.max()),
            "lo2": float(var.longitude.max()),
            "la2": float(var.latitude.min()),
            "dx": lon_step,
            "dy": lat_step,
            "statisticalProcessType": "UnknownStatType--1",
        }

    if component_name == "vvel":
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 2,
            "parameterCategoryName": "Momentum",
            "parameterNumber": 2,
            "parameterNumberName": "Vertical Velocity",
            "parameterUnit": "Pa.s-1",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
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
            "unit": "Pa/s"
        }


    if component_name == "cape": #Incorret, but just a placeholder for now.
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 2,
            "parameterCategoryName": "Momentum",
            "parameterNumber": 2,
            "parameterNumberName": "CAPE",
            "parameterUnit": "J.kg-1",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
            "surface1Type": 100,
            "surface1TypeName": "Surface",
            "surface1Value": "Surface",
            "gridDefinition": "Latitude_Longitude",
            "nx": var.sizes["longitude"],
            "ny": var.sizes["latitude"],
            "lo1": float(var.longitude.min()),
            "la1": float(var.latitude.max()),
            "lo2": float(var.longitude.max()),
            "la2": float(var.latitude.min()),
            "dx": lon_step,
            "dy": lat_step,
            "unit": "J/kg"
        }

    if component_name == "cin": #Incorret, but just a placeholder for now.
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 2,
            "parameterCategoryName": "Momentum",
            "parameterNumber": 2,
            "parameterNumberName": "CIN",
            "parameterUnit": "J.kg-1",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
            "surface1Type": 100,
            "surface1TypeName": "Surface",
            "surface1Value": "Surface",
            "gridDefinition": "Latitude_Longitude",
            "nx": var.sizes["longitude"],
            "ny": var.sizes["latitude"],
            "lo1": float(var.longitude.min()),
            "la1": float(var.latitude.max()),
            "lo2": float(var.longitude.max()),
            "la2": float(var.latitude.min()),
            "dx": lon_step,
            "dy": lat_step,
            "unit": "J/kg"
        }

    if (component_name == "divergence"):
        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "parameterCategory": 2,
            "parameterCategoryName": "Momentum",
            "parameterNumber": 2,
            "parameterNumberName": f"Divergence",
            "parameterUnit": "s-1",
            "forecastTime": forecast_hour,
            "refTime": init_time.strftime("%Y-%m-%d %H:%M:%S"),
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
            "unit": "per seconds"
        }

    points = [
        {
            "lat": float(lat),
            "lng": float(lon),
            "value": float(var.values[i, j])
        }
        for i, lat in enumerate(var.latitude)
        for j, lon in enumerate(var.longitude)
        if not np.isnan(var.values[i, j])
    ]

    return {
        "header": header,
        "data": points
    }
