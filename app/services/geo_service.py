import math
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import Territory

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return round(R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)

def verify_territory_geofence(db: Session, duty_location: str, lat: Optional[float], lng: Optional[float]) -> Tuple[bool, float, str, Optional[Territory]]:
    hub = db.query(Territory).filter(Territory.hub_name == duty_location).first()
    if not hub:
        return False, -1.0, f"Invalid duty territory selected: {duty_location}", None
    if lat is None or lng is None:
        return False, -1.0, "GPS location not provided. Enable location permissions.", hub
    distance = haversine_distance_meters(lat, lng, hub.latitude, hub.longitude)
    allowed_radius = hub.geofence_radius_meters or 2000.0
    if distance <= allowed_radius:
        return True, distance, f"Verified within {hub.hub_name} ({distance}m / {allowed_radius}m limit)", hub
    return False, distance, f"GEOFENCE REJECTION: You are {distance}m away from {hub.hub_name} (max {int(allowed_radius)}m).", hub
