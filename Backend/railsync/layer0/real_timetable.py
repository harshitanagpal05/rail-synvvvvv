"""
Module containing real Indian Railways (IRCTC/CRIS) public timetable data.
Generates realistic train schedules for specific corridors based on actual train numbers,
names, and departure times.
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Optional


# Train data defined per corridor
TRAINS = {
    "Delhi-Mumbai Rajdhani Corridor": [
        {"id": "12951", "name": "Mumbai Rajdhani Express", "dep": "16:55", "priority": "rajdhani"},
        {"id": "12952", "name": "Mumbai Rajdhani Express", "dep": "16:55", "priority": "rajdhani"},
        {"id": "12953", "name": "August Kranti Rajdhani", "dep": "17:40", "priority": "rajdhani"},
        {"id": "12954", "name": "August Kranti Rajdhani", "dep": "17:40", "priority": "rajdhani"},
        {"id": "12903", "name": "Golden Temple Mail", "dep": "21:30", "priority": "mail"},
        {"id": "12904", "name": "Golden Temple Mail", "dep": "21:30", "priority": "mail"},
        {"id": "12925", "name": "Paschim Express", "dep": "16:35", "priority": "express"},
        {"id": "12926", "name": "Paschim Express", "dep": "16:35", "priority": "express"},
        {"id": "22209", "name": "Mumbai Duronto", "dep": "23:00", "priority": "express"},
        {"id": "22210", "name": "Mumbai Duronto", "dep": "23:00", "priority": "express"},
        {"id": "19019", "name": "Dehradun Express", "dep": "23:05", "priority": "express"},
        {"id": "19020", "name": "Dehradun Express", "dep": "23:05", "priority": "express"},
        {"id": "12471", "name": "Swaraj Express", "dep": "15:25", "priority": "express"},
        {"id": "12472", "name": "Swaraj Express", "dep": "15:25", "priority": "express"},
        {"id": "59023", "name": "Mumbai Central Valsad Fast Passenger", "dep": "18:10", "priority": "passenger"},
        {"id": "59024", "name": "Valsad Mumbai Central Fast Passenger", "dep": "04:30", "priority": "passenger"},
    ],
    "Delhi-Howrah Main Line": [
        {"id": "12301", "name": "Howrah Rajdhani Express", "dep": "16:50", "priority": "rajdhani"},
        {"id": "12302", "name": "Howrah Rajdhani Express", "dep": "16:50", "priority": "rajdhani"},
        {"id": "12305", "name": "Howrah Rajdhani", "dep": "14:30", "priority": "rajdhani"},
        {"id": "12306", "name": "Howrah Rajdhani", "dep": "14:30", "priority": "rajdhani"},
        {"id": "12801", "name": "Purushottam Express", "dep": "22:40", "priority": "express"},
        {"id": "12802", "name": "Purushottam Express", "dep": "22:40", "priority": "express"},
        {"id": "12381", "name": "Poorva Express", "dep": "20:25", "priority": "express"},
        {"id": "12382", "name": "Poorva Express", "dep": "20:25", "priority": "express"},
        {"id": "12311", "name": "Kalka Mail", "dep": "19:35", "priority": "mail"},
        {"id": "12312", "name": "Kalka Mail", "dep": "19:35", "priority": "mail"},
        {"id": "13005", "name": "Amritsar-Howrah Mail", "dep": "20:20", "priority": "mail"},
        {"id": "13006", "name": "Amritsar-Howrah Mail", "dep": "20:20", "priority": "mail"},
        {"id": "12273", "name": "Howrah-Delhi Duronto", "dep": "20:05", "priority": "express"},
        {"id": "12274", "name": "Howrah-Delhi Duronto", "dep": "20:05", "priority": "express"},
        {"id": "63203", "name": "Patna DDU MEMU", "dep": "12:30", "priority": "passenger"},
    ],
    "Chennai-Mumbai Trunk Route": [
        {"id": "11041", "name": "Chennai Express", "dep": "14:00", "priority": "express"},
        {"id": "11042", "name": "Chennai Express", "dep": "14:00", "priority": "express"},
        {"id": "11063", "name": "Chennai LTT Express", "dep": "07:15", "priority": "express"},
        {"id": "11064", "name": "Chennai LTT Express", "dep": "07:15", "priority": "express"},
        {"id": "11301", "name": "Udyan Express", "dep": "08:05", "priority": "express"},
        {"id": "11302", "name": "Udyan Express", "dep": "08:05", "priority": "express"},
        {"id": "17031", "name": "Hyderabad Express", "dep": "19:00", "priority": "express"},
        {"id": "17032", "name": "Hyderabad Express", "dep": "19:00", "priority": "express"},
        {"id": "12163", "name": "Chennai Superfast", "dep": "15:50", "priority": "express"},
        {"id": "12164", "name": "Chennai Superfast", "dep": "15:50", "priority": "express"},
        {"id": "57121", "name": "Pune Solapur Passenger", "dep": "08:30", "priority": "passenger"},
    ],
    "Delhi-Chennai Grand Trunk": [
        {"id": "12616", "name": "Grand Trunk Express", "dep": "16:10", "priority": "express"},
        {"id": "12615", "name": "Grand Trunk Express", "dep": "18:50", "priority": "express"},
        {"id": "12622", "name": "Tamil Nadu Express", "dep": "21:05", "priority": "express"},
        {"id": "12621", "name": "Tamil Nadu Express", "dep": "22:00", "priority": "express"},
    ],
    "Howrah-Mumbai Mail Route": [
        {"id": "12810", "name": "Howrah Mumbai Mail", "dep": "19:50", "priority": "mail"},
        {"id": "12809", "name": "Mumbai Howrah Mail", "dep": "21:10", "priority": "mail"},
        {"id": "12860", "name": "Gitanjali Express", "dep": "14:05", "priority": "express"},
        {"id": "12859", "name": "Gitanjali Express", "dep": "06:00", "priority": "express"},
    ],
    "Howrah-Chennai Coromandel": [
        {"id": "12841", "name": "Coromandel Express", "dep": "15:20", "priority": "express"},
        {"id": "12842", "name": "Coromandel Express", "dep": "07:00", "priority": "express"},
        {"id": "12839", "name": "Chennai Mail", "dep": "23:55", "priority": "mail"},
        {"id": "12840", "name": "Howrah Mail", "dep": "19:15", "priority": "mail"},
    ]
}

TRAIN_INFO_MAP = {}
for corridor, trains in TRAINS.items():
    for t in trains:
        TRAIN_INFO_MAP[t["id"]] = {
            "train_name": t["name"],
            "route": corridor,
            "priority": t["priority"]
        }


def get_train_info(train_id: str) -> Optional[Dict[str, str]]:
    """
    Returns dict with train_name, route, and priority for display in the UI.
    """
    return TRAIN_INFO_MAP.get(str(train_id))


def get_duration(priority: str) -> int:
    """
    Returns realistic duration in minutes for a train's passage through a section based on priority.
    """
    if priority == "rajdhani":
        return 15 + (hash(priority) % 11)  # 15-25 min
    elif priority == "express":
        return 20 + (hash(priority) % 16)  # 20-35 min
    elif priority == "mail":
        return 25 + (hash(priority) % 21)  # 25-45 min
    elif priority == "passenger":
        return 30 + (hash(priority) % 31)  # 30-60 min
    elif priority == "goods":
        return 20 + (hash(priority) % 21)  # 20-40 min
    return 30


def generate_goods_trains(date_obj: datetime, corridor: str, goods_id_prefix: str, num_trains_early: int, num_trains_late: int) -> List[Dict[str, Any]]:
    goods = []
    # Early morning goods (00:00-04:00 or 04:30)
    for i in range(num_trains_early):
        hour = (hash(f"early_{corridor}_{i}") % 4)
        minute = (hash(f"early_min_{corridor}_{i}") % 60)
        dep_time = date_obj.replace(hour=hour, minute=minute)
        duration = get_duration("goods")
        goods.append({
            "train_id": f"{goods_id_prefix}{i:03d}",
            "train_name": f"Goods {goods_id_prefix}{i:03d}",
            "start": dep_time,
            "end": dep_time + timedelta(minutes=duration),
            "priority": "goods",
            "segment_id": None,
            "corridor": corridor
        })
    # Late night goods (22:00-23:59)
    for i in range(num_trains_late):
        hour = 22 + (hash(f"late_{corridor}_{i}") % 2)
        minute = (hash(f"late_min_{corridor}_{i}") % 60)
        dep_time = date_obj.replace(hour=hour, minute=minute)
        duration = get_duration("goods")
        goods.append({
            "train_id": f"{goods_id_prefix}{num_trains_early + i:03d}",
            "train_name": f"Goods {goods_id_prefix}{num_trains_early + i:03d}",
            "start": dep_time,
            "end": dep_time + timedelta(minutes=duration),
            "priority": "goods",
            "segment_id": None,
            "corridor": corridor
        })
    return goods


def generate_real_timetable(base_date: Optional[datetime] = None, days: int = 7, corridors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Generate train movement entries from the real schedule.
    """
    if base_date is None:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if corridors is None:
        corridors = list(TRAINS.keys())
        
    entries = []
    
    for day_offset in range(days):
        current_date = base_date + timedelta(days=day_offset)
        
        for corridor in corridors:
            if corridor not in TRAINS:
                continue
            
            for train in TRAINS[corridor]:
                hour, minute = map(int, train["dep"].split(":"))
                dep_time = current_date.replace(hour=hour, minute=minute)
                duration = get_duration(train["priority"])
                
                entries.append({
                    "train_id": train["id"],
                    "train_name": train["name"],
                    "start": dep_time,
                    "end": dep_time + timedelta(minutes=duration),
                    "priority": train["priority"],
                    "segment_id": None,
                    "corridor": corridor
                })
                
            # Add goods trains for specific corridors
            if corridor == "Delhi-Mumbai Rajdhani Corridor":
                entries.extend(generate_goods_trains(current_date, corridor, "40", 4, 4))
            elif corridor == "Delhi-Howrah Main Line":
                entries.extend(generate_goods_trains(current_date, corridor, "50", 5, 5))
            elif corridor == "Chennai-Mumbai Trunk Route":
                entries.extend(generate_goods_trains(current_date, corridor, "60", 6, 0))
            elif corridor == "Delhi-Chennai Grand Trunk":
                entries.extend(generate_goods_trains(current_date, corridor, "70", 5, 3))
            elif corridor == "Howrah-Mumbai Mail Route":
                entries.extend(generate_goods_trains(current_date, corridor, "80", 4, 4))
            elif corridor == "Howrah-Chennai Coromandel":
                entries.extend(generate_goods_trains(current_date, corridor, "90", 3, 5))
                
    return entries


