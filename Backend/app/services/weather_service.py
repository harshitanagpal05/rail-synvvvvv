"""Weather Service using Open-Meteo API (100% Free, No API Key Required)"""

import httpx
import logging
from typing import Dict, Any, List
from datetime import datetime
import time

log = logging.getLogger("weather")

# City coordinates for major Indian Railway Divisions
DIVISION_COORDS = {
    "Delhi": {"lat": 28.6139, "lon": 77.2090},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
    "Chennai": {"lat": 13.0827, "lon": 80.2707},
    "Howrah": {"lat": 22.5958, "lon": 88.3113},
    "Jaipur": {"lat": 26.9124, "lon": 75.7873},
    "Kota": {"lat": 25.2138, "lon": 75.8648},
    "Ratlam": {"lat": 23.3315, "lon": 75.0367},
    "Vadodara": {"lat": 22.3072, "lon": 73.1812},
    "Allahabad": {"lat": 25.4358, "lon": 81.8463},
    "Mughal Sarai": {"lat": 25.2815, "lon": 83.1186},
    "Dhanbad": {"lat": 23.7915, "lon": 86.4304},
    "Renigunta": {"lat": 13.6366, "lon": 79.5222},
    "Guntakal": {"lat": 15.1674, "lon": 77.3824},
    "Solapur": {"lat": 17.6599, "lon": 75.9064},
    "Pune": {"lat": 18.5204, "lon": 73.8567},
    "Agra": {"lat": 27.1767, "lon": 78.0081},
    "Jhansi": {"lat": 25.4484, "lon": 78.5685},
    "Bhopal": {"lat": 23.2599, "lon": 77.4126},
    "Nagpur": {"lat": 21.1458, "lon": 79.0882},
    "Balharshah": {"lat": 19.8510, "lon": 79.3510},
    "Vijayawada": {"lat": 16.5062, "lon": 80.6480},
    "Kharagpur": {"lat": 22.3302, "lon": 87.3237},
    "Tatanagar": {"lat": 22.7925, "lon": 86.1843},
    "Bilaspur": {"lat": 22.0797, "lon": 82.1409},
    "Raipur": {"lat": 21.2514, "lon": 81.6296},
    "Bhusaval": {"lat": 21.0455, "lon": 75.8011},
    "Bhubaneswar": {"lat": 20.2961, "lon": 85.8245},
    "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185},
}

_WEATHER_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SEC = 1800  # 30 minutes cache

def get_division_weather(division: str) -> Dict[str, Any]:
    """Get real weather data for a division from Open-Meteo."""
    now = time.time()
    
    # Return cached if valid
    if division in _WEATHER_CACHE:
        cached_data, timestamp = _WEATHER_CACHE[division]
        if now - timestamp < _CACHE_TTL_SEC:
            return cached_data
            
    # Default fallback data if API fails
    fallback = {
        "temperature": 32.5,
        "rainfall_mm": 0.0,
        "humidity": 65,
        "is_raining": False,
        "description": "Clear"
    }
            
    coords = DIVISION_COORDS.get(division)
    if not coords:
        return fallback
        
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code&timezone=Asia/Kolkata"
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                
                temp = current.get("temperature_2m", fallback["temperature"])
                rain = current.get("precipitation", fallback["rainfall_mm"])
                hum = current.get("relative_humidity_2m", fallback["humidity"])
                wmo_code = current.get("weather_code", 0)
                
                is_raining = wmo_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
                desc = "Rain" if is_raining else "Cloudy" if wmo_code > 1 else "Clear"
                
                result = {
                    "temperature": temp,
                    "rainfall_mm": rain,
                    "humidity": hum,
                    "is_raining": is_raining,
                    "description": desc
                }
                _WEATHER_CACHE[division] = (result, now)
                return result
    except Exception as e:
        log.warning(f"Open-Meteo API failed for {division}: {e}")
        
    return fallback

def get_monsoon_severity() -> str:
    """Determine monsoon severity by checking rainfall across major nodes."""
    key_nodes = ["Mumbai", "Chennai", "Howrah", "Delhi", "Pune"]
    total_rain = 0
    
    for node in key_nodes:
        w = get_division_weather(node)
        total_rain += w.get("rainfall_mm", 0)
        
    if total_rain > 50:
        return "peak"
    elif total_rain > 10:
        return "active"
    else:
        # Fallback to date-based if APIs return 0
        month = datetime.now().month
        if month in [7, 8]:
            return "peak"
        elif month in [6, 9]:
            return "active"
        return "inactive"

def get_flood_risk_zones() -> List[str]:
    """Find divisions currently experiencing heavy rain (>15mm/hr). Only checks flood-prone coastal/river divisions."""
    flood_prone = ["Mumbai", "Chennai", "Howrah", "Vadodara", "Vijayawada"]
    risk_zones = []
    for div in flood_prone:
        w = get_division_weather(div)
        if w.get("rainfall_mm", 0) >= 15.0:
            risk_zones.append(div)
    return risk_zones
