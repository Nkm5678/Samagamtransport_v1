"""
Samagam Transport Platform — Immediate Service Folder Repair
Writes all missing files into C:\narendra\SamagamtransportV1\app\services\
Run inside C:\narendra\SamagamtransportV1:
    python fix_services_and_run.py
    python run.py
"""

import os

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

SERVICE_FILES = {
    "app/__init__.py": "",
    "app/services/__init__.py": "",
    "app/routers/__init__.py": "",

    "app/services/geo_service.py": '''import math
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import Territory


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    return round(R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 2)


def verify_territory_geofence(
    db: Session, duty_location: str, lat: Optional[float], lng: Optional[float]
) -> Tuple[bool, float, str, Optional[Territory]]:
    hub = db.query(Territory).filter(Territory.hub_name == duty_location).first()
    if not hub:
        return False, -1.0, f"Invalid duty territory selected: {duty_location}", None
    if lat is None or lng is None:
        return False, -1.0, "GPS location not provided. Enable location permissions.", hub
    distance = haversine_distance_meters(lat, lng, hub.latitude, hub.longitude)
    allowed_radius = hub.geofence_radius_meters or 2000.0
    if distance <= allowed_radius:
        return True, distance, f"Verified within {hub.hub_name} ({distance}m / {allowed_radius}m limit)", hub
    return False, distance, f"GEOFENCE REJECTION: {distance}m away from {hub.hub_name} (max {int(allowed_radius)}m).", hub
''',

    "app/services/email_service.py": '''import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from app.config import settings


def send_email_async_safe(recipient_email: str, subject: str, html_body: str) -> dict:
    if not recipient_email or "@" not in recipient_email:
        return {"sent": False, "reason": "No valid email provided"}
    if not settings.SMTP_APP_PASSWORD:
        print(f"📧 [SIMULATED EMAIL] To: {recipient_email} | Subject: {subject}")
        return {"sent": True, "simulated": True, "recipient": recipient_email}
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Samagam Transport Operations <{settings.SMTP_SENDER_EMAIL}>"
        msg["To"] = recipient_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_SENDER_EMAIL, settings.SMTP_APP_PASSWORD)
            server.sendmail(settings.SMTP_SENDER_EMAIL, recipient_email, msg.as_string())
        return {"sent": True, "simulated": False, "recipient": recipient_email}
    except Exception as e:
        return {"sent": False, "reason": str(e)}


def build_saint_confirmation_html(saint_data: dict) -> str:
    return (
        f"<h2>Samagam Boarding Pass SMG-{saint_data['id']:05d}</h2>"
        f"<p>Name: {saint_data['full_name']} | Ground: {saint_data['assigned_ground']} ({saint_data['assigned_tent']})</p>"
    )
''',

    "app/services/contract_service.py": '''import math
from datetime import datetime
from app.models import HiredRollingContract


def compute_rolling_contract_metrics(
    contract: HiredRollingContract, current_time: datetime = None, current_odometer_km: float = None
) -> dict:
    end_ts = contract.exit_timestamp or current_time or datetime.utcnow()
    delta_seconds = max(0.0, (end_ts - contract.entry_timestamp).total_seconds())
    duration_hours = round(delta_seconds / 3600.0, 2)
    billed_days = max(1, math.ceil(duration_hours / 24.0)) if duration_hours > 0 else 1
    allowed_quota_km = round(billed_days * contract.daily_quota_km, 2)
    effective_odo = contract.exit_odometer_km if contract.exit_odometer_km is not None else current_odometer_km
    if effective_odo is not None and effective_odo >= contract.entry_odometer_km:
        km_run = round(effective_odo - contract.entry_odometer_km, 2)
    else:
        km_run = round(contract.total_km_run or 0.0, 2)
    excess_km = round(max(0.0, km_run - allowed_quota_km), 2)
    base_hire_cost = round(billed_days * contract.daily_base_rate_inr, 2)
    excess_km_cost = round(excess_km * contract.extra_rate_per_km_inr, 2)
    return {
        "duration_hours": duration_hours,
        "billed_days": billed_days,
        "km_run": km_run,
        "allowed_quota_km": allowed_quota_km,
        "excess_km": excess_km,
        "base_hire_cost_inr": base_hire_cost,
        "excess_km_cost_inr": excess_km_cost,
        "total_settlement_inr": round(base_hire_cost + excess_km_cost, 2)
    }
''',

    "app/services/operations_service.py": '''from datetime import datetime
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
    if heavy_50:
        parts.append(f"{heavy_50}x Heavy Bus (50-seat)")
    if standard_35:
        parts.append(f"{standard_35}x Standard Bus (35-seat)")
    if mini_20:
        parts.append(f"{mini_20}x Mini Shuttle (20-seat)")
    return {
        "summary": " + ".join(parts),
        "heavy_50": heavy_50,
        "standard_35": standard_35,
        "mini_20": mini_20,
        "total_buses": heavy_50 + standard_35 + mini_20
    }


def record_turnaround_movement(
    db: Session, vehicle: Vehicle, movement_type: str, location_hub: str, recorded_by: str,
    passenger_count: int = 0, destination_hub: str = None, odometer_km: float = None
) -> TurnaroundMovement:
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


def process_live_telemetry_ping(
    db: Session, vehicle: Vehicle, latitude: float, longitude: float, sender_role: str = "SYSTEM",
    sender_id: int = None, journey_id: int = None, accuracy_meters: float = None,
    speed_kmh: float = 0.0, heading: float = None, battery_level: int = None
) -> Dict[str, Any]:
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
''',

    "app/services/seed_service.py": '''from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import (
    Territory, Vehicle, Saint, HiredRollingContract,
    MSRTCSpotCashVoucher, StationCashFloat, CrewDutyShift
)

MUMBAI_HUBS_SEED = [
    {"hub_code": "GND1", "hub_name": "Ground 1 (Main Hall)", "hub_type": "Samagam Ground", "city_zone": "Samagam Venue", "latitude": 19.2183, "longitude": 72.9781, "geofence_radius_meters": 2000.0},
    {"hub_code": "GND2", "hub_name": "Ground 2 (North Camp)", "hub_type": "Samagam Ground", "city_zone": "Samagam Venue", "latitude": 19.2225, "longitude": 72.9810, "geofence_radius_meters": 2000.0},
    {"hub_code": "GND3", "hub_name": "Ground 3 (South Camp)", "hub_type": "Samagam Ground", "city_zone": "Samagam Venue", "latitude": 19.2140, "longitude": 72.9745, "geofence_radius_meters": 2000.0},
    {"hub_code": "GND4", "hub_name": "Ground 4 (VIP & Elderly Enclave)", "hub_type": "Samagam Ground", "city_zone": "Samagam Venue", "latitude": 19.2195, "longitude": 72.9835, "geofence_radius_meters": 2000.0},
    {"hub_code": "TNA",  "hub_name": "Thane Railway Station", "hub_type": "Railway Station", "city_zone": "Thane Zone", "latitude": 19.1860, "longitude": 72.9759, "geofence_radius_meters": 2000.0},
    {"hub_code": "MMCT", "hub_name": "Mumbai Central (MMCT)", "hub_type": "Railway Station", "city_zone": "South Mumbai", "latitude": 18.9690, "longitude": 72.8193, "geofence_radius_meters": 2000.0},
    {"hub_code": "DR",   "hub_name": "Dadar Terminal (DR/DDR)", "hub_type": "Railway Station", "city_zone": "Central Mumbai", "latitude": 19.0178, "longitude": 72.8478, "geofence_radius_meters": 2000.0},
    {"hub_code": "LTT",  "hub_name": "Lokmanya Tilak Terminus (LTT)", "hub_type": "Railway Station", "city_zone": "East Suburbs", "latitude": 19.0699, "longitude": 72.8919, "geofence_radius_meters": 2000.0},
    {"hub_code": "CSMT", "hub_name": "Chhatrapati Shivaji Maharaj Terminus (CSMT)", "hub_type": "Railway Station", "city_zone": "South Mumbai", "latitude": 18.9398, "longitude": 72.8354, "geofence_radius_meters": 2000.0},
    {"hub_code": "BDTS", "hub_name": "Bandra Terminus (BDTS)", "hub_type": "Railway Station", "city_zone": "West Suburbs", "latitude": 19.0620, "longitude": 72.8412, "geofence_radius_meters": 2000.0},
    {"hub_code": "KYN",  "hub_name": "Kalyan Junction (KYN)", "hub_type": "Railway Station", "city_zone": "Kalyan Zone", "latitude": 19.2352, "longitude": 73.1305, "geofence_radius_meters": 2000.0},
    {"hub_code": "PNVL", "hub_name": "Panvel Junction (PNVL)", "hub_type": "Railway Station", "city_zone": "Navi Mumbai", "latitude": 18.9912, "longitude": 73.1208, "geofence_radius_meters": 2000.0},
    {"hub_code": "BOM1", "hub_name": "Mumbai Airport Terminal 1 (Domestic)", "hub_type": "Airport", "city_zone": "West Suburbs", "latitude": 19.0902, "longitude": 72.8628, "geofence_radius_meters": 2000.0},
    {"hub_code": "BOM2", "hub_name": "Mumbai Airport Terminal 2 (International)", "hub_type": "Airport", "city_zone": "West Suburbs", "latitude": 19.0974, "longitude": 72.8742, "geofence_radius_meters": 2000.0}
]


def seed_initial_operations_data(db: Session):
    for hub in MUMBAI_HUBS_SEED:
        if not db.query(Territory).filter(Territory.hub_code == hub["hub_code"]).first():
            db.add(Territory(**hub))
    db.commit()

    if db.query(Vehicle).count() == 0:
        v1 = Vehicle(
            vehicle_reg_number="MH-04-TR-1001", vehicle_type="Heavy Bus (50-seater)", capacity=50,
            ownership_type="TRUST_OWNED", contractor_name="Sant Nirankari Mandal Fleet",
            driver_name="Harbhajan Singh", driver_phone="9820110001",
            rider_name="Amit Sharma", rider_phone="9820220001",
            current_hub="Thane Railway Station", assigned_territory="Thane Railway Station",
            status="EMPTY_IN", current_lat=19.1865, current_lng=72.9762, health_score_pct=96.0
        )
        v2 = Vehicle(
            vehicle_reg_number="MH-01-HR-2045", vehicle_type="Heavy Bus (50-seater)", capacity=50,
            ownership_type="HIRED_OUTSIDE", contractor_name="Shree Siddhivinayak Travels",
            fixed_daily_rate_inr=7500.0, is_rolling_contract=True,
            driver_name="Rajesh Jadhav", driver_phone="9820110002",
            current_hub="Dadar Terminal (DR/DDR)", assigned_territory="Dadar Terminal (DR/DDR)",
            status="LOADED_OUT", current_passengers=48, current_destination="Ground 1 (Main Hall)",
            current_lat=19.0850, current_lng=72.9120, current_speed_kmh=42.5, is_live_tracking=True, health_score_pct=88.0
        )
        v3 = Vehicle(
            vehicle_reg_number="MH-04-ST-8892", vehicle_type="MSRTC State Transport Bus", capacity=55,
            ownership_type="MSRTC_SPOT_CASH", contractor_name="MSRTC Thane Depot",
            driver_name="Prakash Shinde (MSRTC)", driver_phone="9820110003",
            current_hub="Ground 1 (Main Hall)", assigned_territory="Thane Railway Station",
            status="UNLOADED_IN", current_lat=19.2183, current_lng=72.9781, health_score_pct=91.0
        )
        db.add_all([v1, v2, v3])
        db.commit()

        c1 = HiredRollingContract(
            contract_code="HRC-2026-001", vehicle_id=v2.id, vendor_agency_name="Shree Siddhivinayak Travels",
            daily_base_rate_inr=7500.0, daily_quota_km=300.0, extra_rate_per_km_inr=25.0,
            entry_timestamp=datetime.utcnow() - timedelta(hours=14), entry_odometer_km=142500.0,
            registered_by="Inward Gate Marshall"
        )
        db.add(c1)
        db.commit()
        v2.active_contract_id = c1.id

        db.add(StationCashFloat(
            station_hub="Thane Railway Station", treasury_disbursed_amount_inr=25000.0,
            issued_to_coordinator="Ramesh Deshmukh (Thane Lead)"
        ))
        db.add(MSRTCSpotCashVoucher(
            voucher_number="MSRTC-TNA-001", station_hub="Thane Railway Station", vehicle_id=v3.id,
            msrtc_depot_name="Thane Depot 1", conductor_name="Vijay Kadam",
            cash_amount_paid_inr=1650.0, etm_receipt_number="ETM-992831", passenger_headcount=55,
            paid_by_volunteer_name="Ramesh Deshmukh", is_verified_at_gate=True, verified_by_ground_sevadar="Gate 1 Marshall"
        ))
        db.add(Saint(
            full_name="Sant Gurpreet Singh Ji & Jatha", spiritual_order="Delhi Zone",
            contact_phone="9811002233", group_size=42, arrival_mode="Train",
            arrival_hub="Thane Railway Station", arrival_transit_number="12138 Punjab Mail",
            arrival_datetime="2026-11-20 08:30", departure_mode="Train",
            departure_hub="Thane Railway Station", departure_datetime="2026-11-24 19:15",
            assigned_ground="Ground 1 (Main Hall)", assigned_tent="Tent A-12", status="Registered"
        ))
        db.add(CrewDutyShift(
            crew_role="Driver", crew_name="Harbhajan Singh", crew_phone="9820110001",
            station_hub="Thane Railway Station", duty_start_time=datetime.utcnow() - timedelta(hours=4),
            is_currently_on_duty=True
        ))
        db.commit()
'''
}


def main():
    print(f"🔧 Restoring app/services files inside: {TARGET_DIR}\n")
    for rel_path, content in SERVICE_FILES.items():
        full_path = os.path.join(TARGET_DIR, rel_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Wrote: {full_path}")
    print("\n🚀 All service modules restored! Now run:")
    print("   Remove-Item -Path samagam_production.db -Force -ErrorAction SilentlyContinue")
    print("   python run.py")


if __name__ == "__main__":
    main()