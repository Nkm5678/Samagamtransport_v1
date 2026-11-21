from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import Vehicle, Journey, TelemetryPing, TurnaroundMovement
from app.services.geo_service import haversine_distance_meters

def compute_optimal_bus_mix(waiting_passengers: int) -> Dict[str, Any]:
    if waiting_passengers <= 0:
        return {"summary": "0 Buses", "heavy_50": 0, "standard_35": 0, "mini_20": 0, "total_buses": 0}
    remaining = waiting_passengers
    heavy_50 = remaining // 50
    remaining %= 50
    standard_35 = 0
    mini_20 = 0
    if remaining > 35:
        heavy_50 += 1
    elif remaining > 20:
        standard_35 += 1
    elif remaining > 0:
        mini_20 += 1
    parts = []
    if heavy_50: parts.append(f"{heavy_50}x Heavy Bus (50-seat)")
    if standard_35: parts.append(f"{standard_35}x Standard Bus (35-seat)")
    if mini_20: parts.append(f"{mini_20}x Mini Shuttle (20-seat)")
    return {"summary": " + ".join(parts), "heavy_50": heavy_50, "standard_35": standard_35, "mini_20": mini_20, "total_buses": heavy_50 + standard_35 + mini_20}

def record_turnaround_movement(db: Session, vehicle: Vehicle, movement_type: str, location_hub: str, recorded_by: str, passenger_count: int = 0, destination_hub: str = None, odometer_km: float = None) -> TurnaroundMovement:
    now = datetime.utcnow()
    movement = TurnaroundMovement(
        movement_type=movement_type, vehicle_id=vehicle.id, location_hub=location_hub,
        destination_hub=destination_hub, passenger_count=passenger_count, capacity=vehicle.capacity,
        odometer_km=odometer_km, recorded_by=recorded_by, logged_at=now, logged_date=now.date()
    )
    db.add(movement)
    vehicle.status = movement_type
    vehicle.current_hub = location_hub
    vehicle.current_passengers = passenger_count
    if destination_hub:
        vehicle.current_destination = destination_hub
    vehicle.last_updated = now
    return movement

def process_live_telemetry_ping(db: Session, vehicle: Vehicle, latitude: float, longitude: float, sender_role: str = "SYSTEM", sender_id: int = None, journey_id: int = None, accuracy_meters: float = None, speed_kmh: float = 0.0, heading: float = None, battery_level: int = None) -> Dict[str, Any]:
    now = datetime.utcnow()
    active_journey = None
    if journey_id:
        active_journey = db.query(Journey).filter(Journey.id == journey_id).first()
    elif vehicle.active_journey_id:
        active_journey = db.query(Journey).filter(Journey.id == vehicle.active_journey_id).first()

    if active_journey and vehicle.current_lat is not None and vehicle.current_lng is not None:
        step_meters = haversine_distance_meters(vehicle.current_lat, vehicle.current_lng, latitude, longitude)
        if 2.0 <= step_meters <= 5000.0:
            active_journey.total_distance_km = round((active_journey.total_distance_km or 0.0) + (step_meters / 1000.0), 3)

    vehicle.current_lat = latitude
    vehicle.current_lng = longitude
    vehicle.current_speed_kmh = speed_kmh or 0.0
    vehicle.current_heading = heading
    vehicle.last_telemetry_at = now
    vehicle.is_live_tracking = True

    if active_journey:
        db.add(TelemetryPing(
            journey_id=active_journey.id, vehicle_id=vehicle.id, sender_role=sender_role,
            sender_id=sender_id, latitude=latitude, longitude=longitude, accuracy_meters=accuracy_meters,
            speed_kmh=speed_kmh or 0.0, heading=heading, battery_level=battery_level, ping_timestamp=now
        ))
    db.commit()
    return {
        "status": "PING_RECORDED",
        "vehicle_reg": vehicle.vehicle_reg_number,
        "journey_id": active_journey.id if active_journey else None,
        "total_distance_km": active_journey.total_distance_km if active_journey else 0.0,
        "timestamp": now.isoformat()
    }
