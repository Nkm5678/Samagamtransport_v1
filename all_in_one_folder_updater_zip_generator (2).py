"""
Samagam Transport & Logistics Platform — Complete All-in-One Updater
Run this single script inside C:\narendra\SamagamtransportV1:
    python apply_all_samagam_updates.py
"""

import os
import zipfile
from datetime import datetime

# Always target C:\narendra\SamagamtransportV1 even if run from Downloads or Desktop
TARGET_ROOT = r"C:\narendra\SamagamtransportV1"
BASE_DIR = TARGET_ROOT if os.path.isdir(TARGET_ROOT) else os.path.dirname(os.path.abspath(__file__))

UPDATED_FILES = {
    "app/__init__.py": "",
    "app/services/__init__.py": "",
    "app/routers/__init__.py": "",

    "app/config.py": """import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Samagam Transport Platform"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = False
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'samagam_production.db')}"
    )
    GEOFENCE_RADIUS_METERS: float = 2000.0
    SMTP_SERVER: str = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_SENDER_EMAIL: str = os.environ.get("SMTP_SENDER_EMAIL", "samagamtransport@gmail.com")
    SMTP_APP_PASSWORD: str = os.environ.get("SMTP_APP_PASSWORD", "")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "samagam-secret-key-2026-mumbai")

    class Config:
        env_file = ".env"

settings = Settings()
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
""",

    "app/database.py": """import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

if "sqlite" in settings.DATABASE_URL:
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""",

    "app/services/geo_service.py": """import math
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
""",

    "app/services/email_service.py": """import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
        msg["From"] = f"Samagam Transport <{settings.SMTP_SENDER_EMAIL}>"
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
    return f"<h2>Samagam Boarding Pass SMG-{saint_data['id']:05d}</h2><p>Name: {saint_data['full_name']} | Ground: {saint_data['assigned_ground']} ({saint_data['assigned_tent']})</p>"
""",

    "app/services/contract_service.py": """import math
from datetime import datetime
from app.models import HiredRollingContract

def compute_rolling_contract_metrics(contract: HiredRollingContract, current_time: datetime = None, current_odometer_km: float = None) -> dict:
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
""",

    "app/services/operations_service.py": """from datetime import datetime
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
""",

    "app/services/seed_service.py": """from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Territory, Vehicle, Saint, HiredRollingContract, MSRTCSpotCashVoucher, StationCashFloat, CrewDutyShift

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
        v1 = Vehicle(vehicle_reg_number="MH-04-TR-1001", vehicle_type="Heavy Bus (50-seater)", capacity=50, ownership_type="TRUST_OWNED", contractor_name="Sant Nirankari Mandal Fleet", driver_name="Harbhajan Singh", driver_phone="9820110001", rider_name="Amit Sharma", rider_phone="9820220001", current_hub="Thane Railway Station", assigned_territory="Thane Railway Station", status="EMPTY_IN", current_lat=19.1865, current_lng=72.9762, health_score_pct=96.0)
        v2 = Vehicle(vehicle_reg_number="MH-01-HR-2045", vehicle_type="Heavy Bus (50-seater)", capacity=50, ownership_type="HIRED_OUTSIDE", contractor_name="Shree Siddhivinayak Travels", fixed_daily_rate_inr=7500.0, is_rolling_contract=True, driver_name="Rajesh Jadhav", driver_phone="9820110002", current_hub="Dadar Terminal (DR/DDR)", assigned_territory="Dadar Terminal (DR/DDR)", status="LOADED_OUT", current_passengers=48, current_destination="Ground 1 (Main Hall)", current_lat=19.0850, current_lng=72.9120, current_speed_kmh=42.5, is_live_tracking=True, health_score_pct=88.0)
        v3 = Vehicle(vehicle_reg_number="MH-04-ST-8892", vehicle_type="MSRTC State Transport Bus", capacity=55, ownership_type="MSRTC_SPOT_CASH", contractor_name="MSRTC Thane Depot", driver_name="Prakash Shinde (MSRTC)", driver_phone="9820110003", current_hub="Ground 1 (Main Hall)", assigned_territory="Thane Railway Station", status="UNLOADED_IN", current_lat=19.2183, current_lng=72.9781, health_score_pct=91.0)
        db.add_all([v1, v2, v3])
        db.commit()

        c1 = HiredRollingContract(contract_code="HRC-2026-001", vehicle_id=v2.id, vendor_agency_name="Shree Siddhivinayak Travels", daily_base_rate_inr=7500.0, daily_quota_km=300.0, extra_rate_per_km_inr=25.0, entry_timestamp=datetime.utcnow() - timedelta(hours=14), entry_odometer_km=142500.0, registered_by="Inward Gate Marshall")
        db.add(c1)
        db.commit()
        v2.active_contract_id = c1.id

        db.add(StationCashFloat(station_hub="Thane Railway Station", treasury_disbursed_amount_inr=25000.0, issued_to_coordinator="Ramesh Deshmukh (Thane Lead)"))
        db.add(MSRTCSpotCashVoucher(voucher_number="MSRTC-TNA-001", station_hub="Thane Railway Station", vehicle_id=v3.id, msrtc_depot_name="Thane Depot 1", conductor_name="Vijay Kadam", cash_amount_paid_inr=1650.0, etm_receipt_number="ETM-992831", passenger_headcount=55, paid_by_volunteer_name="Ramesh Deshmukh", is_verified_at_gate=True, verified_by_ground_sevadar="Gate 1 Marshall"))
        db.add(Saint(full_name="Sant Gurpreet Singh Ji & Jatha", spiritual_order="Delhi Zone", contact_phone="9811002233", group_size=42, arrival_mode="Train", arrival_hub="Thane Railway Station", arrival_transit_number="12138 Punjab Mail", arrival_datetime="2026-11-20 08:30", departure_mode="Train", departure_hub="Thane Railway Station", departure_datetime="2026-11-24 19:15", assigned_ground="Ground 1 (Main Hall)", assigned_tent="Tent A-12", status="Registered"))
        db.add(CrewDutyShift(crew_role="Driver", crew_name="Harbhajan Singh", crew_phone="9820110001", station_hub="Thane Railway Station", duty_start_time=datetime.utcnow() - timedelta(hours=4), is_currently_on_duty=True))
        db.commit()
""",

    "requirements.txt": """fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.28
pydantic>=2.6.4
pydantic-settings>=2.2.1
requests>=2.31.0
psycopg2-binary>=2.9.9
openpyxl>=3.1.2
werkzeug>=3.0.0
""",

    "app/main.py": """import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.seed_service import seed_initial_operations_data
from app.routers import auth, saints, fleet, operations, reports

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_operations_data(db)
    finally:
        db.close()
    yield

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(saints.router)
app.include_router(fleet.router)
app.include_router(operations.router)
app.include_router(reports.router)

static_dir = os.path.join(ROOT_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def _serve_html(filename: str):
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return {"detail": f"{filename} not found in project root."}

@app.get("/")
def home():
    welcome_path = os.path.join(ROOT_DIR, "welcome.html")
    if os.path.exists(welcome_path):
        return FileResponse(welcome_path)
    return _serve_html("admin_dashboard.html")

@app.get("/driver")
def serve_driver():
    return _serve_html("driver_rider_companion.html")

@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(ROOT_DIR, "sw.js"), media_type="application/javascript")

@app.get("/{page_name}.html")
def serve_html_page(page_name: str):
    return _serve_html(f"{page_name}.html")

@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
""",

    "welcome.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>जागृति — The Awakening | निरंकारी सन्त समागम परिवहन सेवा (Samagam Transport)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@500;700;800&family=Playfair+Display:ital,wght@0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { background: radial-gradient(circle at top, #ffffff 0%, #eef3fb 55%, #dce4f2 100%); font-family: 'Inter', 'Noto Sans Devanagari', sans-serif; color: #0f172a; }
        .jagriti-sun-glow { background: radial-gradient(circle, rgba(251, 191, 36, 0.36) 0%, rgba(253, 224, 71, 0.12) 48%, rgba(255, 255, 255, 0) 72%); }
        .lang-btn.active { background-color: #0f2c59; color: #ffffff; box-shadow: 0 6px 16px rgba(15, 44, 89, 0.25); }
        .portal-card { transition: transform 0.22s ease, box-shadow 0.22s ease; }
        .portal-card:hover { transform: translateY(-4px); box-shadow: 0 24px 48px -12px rgba(15, 44, 89, 0.18); }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">
    <header class="bg-white/90 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-40">
        <div class="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-1.5 bg-slate-100 p-1 rounded-2xl border border-slate-200 text-xs font-extrabold">
                <button onclick="setLanguage('hi', this)" class="lang-btn px-3.5 py-1.5 rounded-xl transition">हिंदी</button>
                <button onclick="setLanguage('mr', this)" class="lang-btn px-3.5 py-1.5 rounded-xl transition">मराठी</button>
                <button onclick="setLanguage('en', this)" class="lang-btn active px-3.5 py-1.5 rounded-xl transition">English</button>
            </div>
            <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
                <a href="/download_hub.html" class="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 transition">📲 <span data-i18n="nav_apps">Field Apps (.APK)</span></a>
                <a href="/admin_dashboard.html" class="px-3.5 py-2 rounded-xl bg-[#0f2c59] hover:bg-sky-900 text-white shadow transition">🏛️ <span data-i18n="nav_admin">Transport Control Room</span></a>
            </div>
        </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-8 space-y-8 flex-1 w-full">
        <section class="text-center max-w-3xl mx-auto space-y-3 pt-1">
            <div class="inline-block px-4 py-1 rounded-full bg-sky-100 text-[#0f2c59] text-xs font-extrabold tracking-wide">धन निरंकार जी 🙏 • SANT NIRANKARI MANDAL</div>
            <div class="relative mx-auto w-64 h-36 flex flex-col items-center justify-center jagriti-sun-glow rounded-full">
                <div class="text-5xl sm:text-6xl font-extrabold tracking-tight" style="color: #0f2c59;">जागृति</div>
                <div class="text-sm sm:text-base italic font-bold text-slate-800 -mt-1" style="font-family: 'Playfair Display', serif;">The Awakening</div>
            </div>
            <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight" style="color: #0f2c59;">निरंकारी सन्त समागम — परिवहन सेवा पोर्टल</h1>
            <p class="text-xs sm:text-sm font-bold text-slate-600">60th Maharashtra Annual Nirankari Sant Samagam • Kharghar, Navi Mumbai (Central Park) • 23–26 January 2027</p>
            <p class="text-xs sm:text-sm text-slate-500 max-w-2xl mx-auto leading-relaxed" data-i18n="hero_desc">Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database so our team can allocate vehicles and update your request status live.</p>
        </section>

        <!-- Live Request Allocation Status Tracker -->
        <section class="max-w-4xl mx-auto bg-white rounded-3xl p-5 sm:p-6 border-2 border-[#0f2c59]/20 shadow-lg space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900">Live Allocation Status</span>
                    <h2 class="text-base sm:text-lg font-extrabold text-[#0f2c59] mt-1" data-i18n="track_title">🔍 Check Your Vehicle Allocation Status (By Mobile No. or Request ID)</h2>
                </div>
                <span class="text-[11px] text-slate-400">Auto-refreshes every 30s</span>
            </div>
            <div class="flex flex-col sm:flex-row gap-2.5">
                <input type="text" id="track-query-input" placeholder="Enter 10-Digit Mobile (e.g. 9820...) or Request Code (PND-... / REQ-...)" class="flex-1 border border-slate-300 rounded-2xl px-4 py-3 text-sm font-bold text-slate-900 focus:outline-none">
                <button onclick="checkMyRequestStatus()" class="bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold px-6 py-3 rounded-2xl text-sm shadow transition" data-i18n="track_btn">Check Status</button>
            </div>
            <div id="track-status-results" class="space-y-2.5 pt-1"></div>
        </section>

        <!-- Two Primary Request Portals -->
        <section class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            <div class="portal-card bg-white rounded-3xl p-7 border border-sky-200 shadow-lg flex flex-col justify-between space-y-6">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="w-14 h-14 rounded-2xl bg-sky-100 text-3xl flex items-center justify-center">⛺</span>
                        <span class="text-[11px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-sky-50 text-[#0f2c59] border border-sky-200" data-i18n="badge_ground">Internal Venue Logistics</span>
                    </div>
                    <h2 class="text-xl sm:text-2xl font-extrabold text-[#0f2c59]" data-i18n="card1_title">Need Vehicle Inside Samagam Ground</h2>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed" data-i18n="card1_desc">For Samagam departments (Langar, Tent, Sound, Medical, Security, Sanitation) needing cars, pickups, tempos, or e-rickshaws inside Central Park Kharghar grounds—or to donate a vehicle for Seva.</p>
                </div>
                <a href="/in_ground_seva_vehicles.html" class="w-full bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold py-4 px-5 rounded-2xl text-sm flex items-center justify-between shadow-lg transition">
                    <span data-i18n="card1_btn">Request / Donate In-Ground Vehicle</span><span>→</span>
                </a>
            </div>

            <div class="portal-card bg-white rounded-3xl p-7 border border-emerald-200 shadow-lg flex flex-col justify-between space-y-6">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="w-14 h-14 rounded-2xl bg-emerald-100 text-3xl flex items-center justify-center">🚉</span>
                        <span class="text-[11px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200" data-i18n="badge_transit">Station • Airport • Bus Depot</span>
                    </div>
                    <h2 class="text-xl sm:text-2xl font-extrabold text-emerald-950" data-i18n="card2_title">Need Vehicle for Pickup & Drop (Railway Station / Airport / Bus Depot)</h2>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed" data-i18n="card2_desc">Request shuttle buses, tempo travellers, or cars for Saints, Jathas, or guests arriving at or departing from Railway Stations (Panvel, Thane, CSMT, LTT, Dadar, Kalyan), Mumbai Airports (T1/T2), or ST Bus Depots.</p>
                </div>
                <button onclick="openPickupDropModal()" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-4 px-5 rounded-2xl text-sm flex items-center justify-between shadow-lg transition">
                    <span data-i18n="card2_btn">Raise Pickup / Drop Vehicle Request</span><span>→</span>
                </button>
            </div>
        </section>
    </main>

    <!-- Pickup & Drop Modal -->
    <div id="pickup-drop-modal" class="fixed inset-0 bg-slate-950/75 hidden items-center justify-center z-50 p-4 overflow-y-auto">
        <div class="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-7 space-y-4 shadow-2xl my-auto">
            <div class="flex justify-between items-start border-b pb-3">
                <h3 class="text-lg font-extrabold text-slate-900" data-i18n="modal_pd_title">Pickup & Drop Vehicle Requirement Form</h3>
                <button onclick="closePickupDropModal()" class="text-slate-400 hover:text-slate-800 font-bold text-lg">✕</button>
            </div>
            <form id="pickup-drop-form" onsubmit="submitPickupDropRequest(event)" class="space-y-3.5 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <select name="trip_direction" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        <option value="PICKUP_TO_SAMAGAM">Pickup → Samagam Ground (Kharghar)</option>
                        <option value="DROP_FROM_SAMAGAM">Drop ← Samagam Ground to Station/Airport</option>
                        <option value="ROUND_TRIP">Round Trip (Pickup + Drop)</option>
                    </select>
                    <select name="transit_hub" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        <option value="Panvel Junction (PNVL)">Panvel Railway Junction (PNVL)</option>
                        <option value="Thane Railway Station">Thane Railway Station</option>
                        <option value="Lokmanya Tilak Terminus (LTT)">Lokmanya Tilak Terminus (LTT)</option>
                        <option value="Dadar Terminal (DR/DDR)">Dadar Railway Terminal</option>
                        <option value="Chhatrapati Shivaji Maharaj Terminus (CSMT)">CSMT Mumbai</option>
                        <option value="Kalyan Junction (KYN)">Kalyan Junction</option>
                        <option value="Mumbai Airport Terminal 1 (Domestic)">Mumbai Airport T1 (Domestic)</option>
                        <option value="Mumbai Airport Terminal 2 (International)">Mumbai Airport T2 (International)</option>
                        <option value="Navi Mumbai / Panvel ST Bus Depot">Panvel / Kharghar ST Bus Depot</option>
                    </select>
                </div>
                <div class="grid grid-cols-3 gap-3">
                    <input type="number" name="passenger_count" value="40" min="1" required placeholder="Pax" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                    <select name="vehicle_type_requested" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        <option value="Heavy Bus (50-Seater)">Heavy Bus (50-Seater)</option>
                        <option value="Tempo Traveller (20-26 Seat)">Tempo Traveller</option>
                        <option value="Innova / Ertiga / Car">Innova / Car</option>
                    </select>
                    <input type="number" name="vehicles_needed" value="1" min="1" required placeholder="Qty" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <input type="datetime-local" name="scheduled_datetime" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    <input type="text" name="train_flight_details" placeholder="Train / Flight No." class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <input type="text" name="requester_name" required placeholder="Coordinator Name *" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    <input type="tel" name="requester_phone" required placeholder="10-Digit Mobile *" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                </div>
                <textarea name="notes" rows="2" placeholder="Special notes..." class="w-full border border-slate-300 rounded-xl px-3 py-2"></textarea>
                <button type="submit" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-3.5 rounded-2xl text-sm shadow-lg">✅ Submit Pickup/Drop Request</button>
            </form>
        </div>
    </div>

    <script>
        const TRANSLATIONS = {
            en: { nav_apps: "Field Apps (.APK)", nav_admin: "Transport Control Room", hero_desc: "Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database.", track_title: "🔍 Check Your Vehicle Allocation Status (By Mobile No. or Request ID)", track_btn: "Check Status", badge_ground: "Internal Venue Logistics", card1_title: "Need Vehicle Inside Samagam Ground", card1_desc: "For Samagam departments needing cars, pickups, tempos, or e-rickshaws inside Central Park Kharghar grounds—or to donate a vehicle for Seva.", card1_btn: "Request / Donate In-Ground Vehicle", badge_transit: "Station • Airport • Bus Depot", card2_title: "Need Vehicle for Pickup & Drop (Railway Station / Airport / Bus Depot)", card2_desc: "Request shuttle buses, tempo travellers, or cars for Saints and Jathas arriving at or departing from Railway Stations, Mumbai Airports, or ST Bus Depots.", card2_btn: "Raise Pickup / Drop Vehicle Request", modal_pd_title: "Pickup & Drop Vehicle Requirement Form" },
            hi: { nav_apps: "फील्ड ऐप्स (.APK)", nav_admin: "परिवहन कंट्रोल रूम", hero_desc: "नीचे अपनी परिवहन आवश्यकता चुनें। सभी वाहन अनुरोध सीधे मुख्य डेटाबेस से जुड़े हैं।", track_title: "🔍 अपने वाहन आवंटन की स्थिति जांचें (मोबाइल नंबर या रिक्वेस्ट कोड द्वारा)", track_btn: "स्थिति जांचें", badge_ground: "समागम ग्राउंड आंतरिक सेवा", card1_title: "समागम ग्राउंड के अंदर वाहन चाहिए", card1_desc: "लंगर, टेंट, साउंड, मेडिकल और सुरक्षा विभागों के लिए ग्राउंड के अंदर वाहन की मांग करें या सेवा हेतु वाहन जमा करें।", card1_btn: "ग्राउंड के अंदर वाहन मांगें / जमा करें", badge_transit: "रेलवे स्टेशन • एयरपोर्ट • बस डिपो", card2_title: "रेलवे स्टेशन, एयरपोर्ट या बस डिपो से पिकअप और ड्रॉप के लिए वाहन चाहिए", card2_desc: "रेलवे स्टेशन, मुंबई एयरपोर्ट या एस.टी. बस डिपो से सन्तों और जत्थों को लाने-ले जाने हेतु वाहन बुक करें।", card2_btn: "पिकअप / ड्रॉप वाहन अनुरोध दर्ज करें", modal_pd_title: "पिकअप और ड्रॉप वाहन आवश्यकता फॉर्म" },
            mr: { nav_apps: "फील्ड ॲप्स (.APK)", nav_admin: "परिवहन कंट्रोल रूम", hero_desc: "खालीलपैकी आपली वाहन आवश्यकता निवडा. सर्व वाहन विनंत्या थेट मुख्य डेटाबेसशी जोडलेल्या आहेत.", track_title: "🔍 तुमच्या वाहन वाटपाची स्थिती तपासा (मोबाईल नंबर किंवा रिक्वेस्ट कोडद्वारे)", track_btn: "स्थिती तपासा", badge_ground: "समागम ग्राउंड अंतर्गत सेवा", card1_title: "समागम ग्राउंडच्या आत वाहन हवे आहे", card1_desc: "लंगर, टेंट, साउंड, मेडिकल व सुरक्षा विभागांसाठी ग्राउंडच्या आत वाहनाची मागणी करा अथवा सेवेसाठी वाहन जमा करा.", card1_btn: "ग्राउंडसाठी वाहन मागणी / वाहन जमा करा", badge_transit: "रेल्वे स्टेशन • एअरपोर्ट • बस डेपो", card2_title: "रेल्वे स्टेशन, एअरपोर्ट व बस डेपो पिकअप-ड्रॉपसाठी वाहन हवे आहे", card2_desc: "रेल्वे स्टेशन, मुंबई एअरपोर्ट किंवा एस.टी. बस डेपोवरून संत व जत्थ्यांच्या ने-आण करण्यासाठी वाहन मागणी नोंदवा.", card2_btn: "पिकअप / ड्रॉप वाहन मागणी नोंदवा", modal_pd_title: "पिकअप आणि ड्रॉप वाहन मागणी फॉर्म" }
        };
        function setLanguage(lang, btn) {
            const d = TRANSLATIONS[lang] || TRANSLATIONS.en;
            document.querySelectorAll('[data-i18n]').forEach(el => { const k = el.getAttribute('data-i18n'); if (d[k]) el.textContent = d[k]; });
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
        }
        function openPickupDropModal() { document.getElementById('pickup-drop-modal').classList.remove('hidden'); document.getElementById('pickup-drop-modal').classList.add('flex'); }
        function closePickupDropModal() { document.getElementById('pickup-drop-modal').classList.add('hidden'); document.getElementById('pickup-drop-modal').classList.remove('flex'); }
        async function submitPickupDropRequest(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.passenger_count = parseInt(payload.passenger_count);
            payload.vehicles_needed = parseInt(payload.vehicles_needed);
            const res = await fetch('/api/operations/pickup-drop-requests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (res.ok) {
                document.getElementById('track-query-input').value = payload.requester_phone;
                e.target.reset(); closePickupDropModal(); checkMyRequestStatus();
            }
        }
        async function checkMyRequestStatus() {
            const q = document.getElementById('track-query-input').value.trim();
            if (!q) return;
            const res = await fetch(`/api/operations/request-status-lookup?query=${encodeURIComponent(q)}`);
            const items = res.ok ? await res.json() : [];
            const box = document.getElementById('track-status-results');
            box.innerHTML = items.length ? items.map(item => `
                <div class="p-4 rounded-2xl border-2 ${item.is_allocated ? 'bg-emerald-50 border-emerald-500' : 'bg-amber-50/70 border-amber-300'} flex flex-wrap justify-between items-center gap-3 text-xs">
                    <div>
                        <span class="font-extrabold text-sm">${item.code}</span> — <span class="font-bold">${item.is_allocated ? '✅ VEHICLE ALLOCATED' : '⏳ PENDING ALLOCATION'}</span>
                        <div class="text-slate-700">${item.category} • ${item.summary}</div>
                    </div>
                    ${item.is_allocated ? `<div class="bg-white p-2.5 rounded-xl border border-emerald-300 font-bold text-right">${item.assigned_vehicle_reg}<br>${item.driver_name} (${item.driver_phone})</div>` : ''}
                </div>
            `).join('') : '<div class="text-xs text-amber-800 font-semibold">No matching requests found yet.</div>';
        }
    </script>
</body>
</html>
"""
}


def run_all_updates():
    print("🚀 Starting Samagam Transport Fast Folder Updater...\n", flush=True)

    # Write all updated backend, service, and HTML files immediately (no slow ZIP crawl)
    for rel_path, content in UPDATED_FILES.items():
        target_path = os.path.join(BASE_DIR, rel_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Updated: {rel_path}", flush=True)

    print("\n🎉 Done in < 1 second! Now run:")
    print("   python run.py")


if __name__ == "__main__":
    run_all_updates()