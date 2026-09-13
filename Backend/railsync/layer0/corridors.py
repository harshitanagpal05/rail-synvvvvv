"""RailSync 2.0 - Indian Railways corridor definitions for synthetic data."""

from __future__ import annotations

CORRIDORS = {
    "delhi_mumbai": {
        "name": "Delhi-Mumbai Rajdhani Corridor",
        "divisions": ["Delhi", "Jaipur", "Kota", "Ratlam", "Vadodara", "Mumbai"],
        "total_km": 1384,
    },
    "delhi_howrah": {
        "name": "Delhi-Howrah Main Line",
        "divisions": ["Delhi", "Allahabad", "Mughal Sarai", "Dhanbad", "Howrah"],
        "total_km": 1447,
    },
    "chennai_mumbai": {
        "name": "Chennai-Mumbai Trunk Route",
        "divisions": ["Chennai", "Renigunta", "Guntakal", "Solapur", "Pune", "Mumbai"],
        "total_km": 1279,
    },
    "delhi_chennai": {
        "name": "Delhi-Chennai Grand Trunk",
        "divisions": ["Delhi", "Agra", "Jhansi", "Bhopal", "Nagpur", "Balharshah", "Vijayawada", "Chennai"],
        "total_km": 2182,
    },
    "howrah_mumbai": {
        "name": "Howrah-Mumbai Mail Route",
        "divisions": ["Howrah", "Kharagpur", "Tatanagar", "Bilaspur", "Raipur", "Nagpur", "Bhusaval", "Mumbai"],
        "total_km": 1968,
    },
    "howrah_chennai": {
        "name": "Howrah-Chennai Coromandel",
        "divisions": ["Howrah", "Kharagpur", "Bhubaneswar", "Visakhapatnam", "Vijayawada", "Chennai"],
        "total_km": 1661,
    }
}

DEPARTMENTS = ["TRACK", "OHE", "SIG", "TELE", "BRIDGE"]

ASSET_TYPES = ["TRACK", "OHE", "BRIDGE", "SIGNAL"]

TASK_TYPES_BY_DEPT = {
    "TRACK": [
        "track_renewal",
        "track_defect",
        "rail_grinding",
        "ballast_cleaning",
        "weld_repair",
        "sleeper_replacement",
    ],
    "OHE": [
        "ohe_maintenance",
        "catenary_repair",
        "mast_foundation",
        "insulator_replacement",
    ],
    "SIG": [
        "signal_maintenance",
        "cable_replacement",
        "relay_testing",
        "axle_counter_repair",
    ],
    "TELE": [
        "telecom_maintenance",
        "ofc_repair",
        "tower_maintenance",
    ],
    "BRIDGE": [
        "bridge_inspection",
        "girder_painting",
        "bearing_replacement",
        "pier_repair",
    ],
}

CURVE_GRADIENT_CLASSES = ["flat", "mild", "moderate", "sharp"]
MONSOON_EXPOSURE_LEVELS = ["low", "medium", "high"]
FREIGHT_DENSITY_CLASSES = ["low", "medium", "high", "very_high"]
