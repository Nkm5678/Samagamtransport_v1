"""
Samagam Transport Platform — Automated Backend & Root Runner Installer
Creates all 18 backend Python files, root run.py, requirements.txt, and master blueprint HTML
directly into their exact subdirectories inside C:\narendra\SamagamtransportV1.
"""

import os

FILES = {
    "requirements.txt": """fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.28
pydantic>=2.6.4
pydantic-settings>=2.2.1
requests>=2.31.0
psycopg2-binary>=2.9.9
""",

    "run.py": """import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Samagam Transport Platform on http://localhost:8000 ...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
""",

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

    "app/models.py": """from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.database import Base

class Territory(Base):
    __tablename__ = "territories"
    id = Column(Integer, primary_key=True, index=True)
    hub_code = Column(String(10), unique=True, nullable=False, index=True)
    hub_name = Column(String(100), unique=True, nullable=False)
    hub_type = Column(String(50), nullable=False)
    city_zone = Column(String(50), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geofence_radius_meters = Column(Float, default=2000.0)
    active_crew_count = Column(Integer, default=0)

    saints = relationship("Saint", back_populates="hub_ref")
    vehicles = relationship("Vehicle", back_populates="hub_ref")
    demands = relationship("StationDemand", back_populates="hub_ref")
    msrtc_cash_vouchers = relationship("MSRTCSpotCashVoucher", back_populates="hub_ref")
    cash_floats = relationship("StationCashFloat", back_populates="hub_ref")

class StationCashFloat(Base):
    __tablename__ = "station_cash_floats"
    id = Column(Integer, primary_key=True, index=True)
    station_hub = Column(String(100), ForeignKey("territories.hub_name"), nullable=False, index=True)
    treasury_disbursed_amount_inr = Column(Float, nullable=False)
    issued_by = Column(String(100), default="Central Treasury Lead")
    issued_to_coordinator = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_date = Column(Date, default=datetime.utcnow().date, index=True)
    hub_ref = relationship("Territory", back_populates="cash_floats")

class Volunteer(Base):
    __tablename__ = "volunteers"
    id = Column(Integer, primary_key=True, index=True)
    volunteer_code = Column(String(30), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    mobile_number = Column(String(20), unique=True, nullable=False, index=True)
    unit_number = Column(String(50), nullable=False)
    branch_name = Column(String(100), nullable=False)
    photo_b64 = Column(Text, nullable=True)
    duty_location = Column(String(100), nullable=False)
    system_role = Column(String(30), nullable=False)
    device_fingerprint = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geo_accuracy = Column(Float, nullable=True)
    geofence_verified = Column(Boolean, default=False)
    can_view_all_territories = Column(Boolean, default=False)
    can_execute_ground_tasks = Column(Boolean, default=False)
    can_execute_station_tasks = Column(Boolean, default=False)
    can_manage_fleet = Column(Boolean, default=False)
    is_driver = Column(Boolean, default=False)
    is_rider = Column(Boolean, default=False)
    assigned_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("VolunteerSession", back_populates="volunteer", cascade="all, delete-orphan")
    vehicle = relationship("Vehicle", back_populates="assigned_crew", foreign_keys=[assigned_vehicle_id])
    duty_shifts = relationship("CrewDutyShift", back_populates="volunteer")

class VolunteerSession(Base):
    __tablename__ = "volunteer_sessions"
    session_token = Column(String(64), primary_key=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=False)
    device_fingerprint = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    volunteer = relationship("Volunteer", back_populates="sessions")

class Saint(Base):
    __tablename__ = "saints"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False, index=True)
    spiritual_order = Column(String(150), nullable=True)
    contact_phone = Column(String(20), nullable=False, index=True)
    contact_email = Column(String(120), nullable=True)
    group_size = Column(Integer, nullable=False, default=1)
    arrival_mode = Column(String(20), default="Train")
    arrival_hub = Column(String(100), ForeignKey("territories.hub_name"), nullable=False, index=True)
    arrival_transit_number = Column(String(100), nullable=True)
    arrival_pnr_ticket = Column(String(50), nullable=True)
    arrival_datetime = Column(String(50), nullable=False)
    departure_mode = Column(String(20), default="Train")
    departure_hub = Column(String(100), nullable=False)
    departure_transit_number = Column(String(100), nullable=True)
    departure_datetime = Column(String(50), nullable=False)
    assigned_ground = Column(String(50), default="Ground 1 (Main Hall)")
    assigned_tent = Column(String(50), default="Tent A-01", index=True)
    stay_duration_days = Column(Integer, default=4)
    special_assistance_notes = Column(Text, nullable=True)
    status = Column(String(50), default="Registered", nullable=False, index=True)
    assigned_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    return_vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hub_ref = relationship("Territory", back_populates="saints")
    vehicle_ref = relationship("Vehicle", back_populates="allocated_saints", foreign_keys=[assigned_vehicle_id])

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_reg_number = Column(String(30), unique=True, nullable=False, index=True)
    vehicle_type = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)
    ownership_type = Column(String(30), default="TRUST_OWNED", nullable=False, index=True)
    contractor_name = Column(String(100), nullable=True)
    rate_per_trip_inr = Column(Float, default=0.0)
    fixed_daily_rate_inr = Column(Float, default=0.0)
    is_rolling_contract = Column(Boolean, default=False, index=True)
    active_contract_id = Column(Integer, nullable=True)
    driver_name = Column(String(100), nullable=False)
    driver_phone = Column(String(20), nullable=False)
    rider_name = Column(String(100), nullable=True)
    rider_phone = Column(String(20), nullable=True)
    current_hub = Column(String(100), ForeignKey("territories.hub_name"), nullable=False, index=True)
    assigned_territory = Column(String(100), nullable=False)
    status = Column(String(50), default="EMPTY_IN", nullable=False, index=True)
    current_passengers = Column(Integer, default=0)
    current_destination = Column(String(150), nullable=True)
    health_score_pct = Column(Float, default=100.0)
    tire_condition_pct = Column(Float, default=100.0)
    brake_pad_condition_pct = Column(Float, default=100.0)
    clutch_condition_pct = Column(Float, default=100.0)
    engine_oil_condition_pct = Column(Float, default=100.0)
    last_inspection_date = Column(DateTime, nullable=True)
    is_maintenance_flagged = Column(Boolean, default=False, index=True)
    maintenance_reason = Column(Text, nullable=True)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    current_speed_kmh = Column(Float, default=0.0)
    current_heading = Column(Float, nullable=True)
    last_telemetry_at = Column(DateTime, nullable=True)
    is_live_tracking = Column(Boolean, default=False)
    active_journey_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hub_ref = relationship("Territory", back_populates="vehicles")
    allocated_saints = relationship("Saint", back_populates="vehicle_ref", foreign_keys=[Saint.assigned_vehicle_id])
    assigned_crew = relationship("Volunteer", back_populates="vehicle", foreign_keys=[Volunteer.assigned_vehicle_id])
    journeys = relationship("Journey", back_populates="vehicle")
    turnaround_logs = relationship("TurnaroundMovement", back_populates="vehicle")
    fuel_logs = relationship("FuelLog", back_populates="vehicle")
    maintenance_records = relationship("MaintenanceTicket", back_populates="vehicle")
    rolling_contracts = relationship("HiredRollingContract", back_populates="vehicle")
    msrtc_cash_vouchers = relationship("MSRTCSpotCashVoucher", back_populates="vehicle")
    duty_shifts = relationship("CrewDutyShift", back_populates="vehicle")
    wear_inspections = relationship("VehicleWearInspection", back_populates="vehicle")

class CrewDutyShift(Base):
    __tablename__ = "crew_duty_shifts"
    id = Column(Integer, primary_key=True, index=True)
    crew_role = Column(String(30), nullable=False, index=True)
    crew_name = Column(String(100), nullable=False, index=True)
    crew_phone = Column(String(20), nullable=False, index=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    station_hub = Column(String(100), nullable=False)
    duty_date = Column(Date, default=datetime.utcnow().date, nullable=False, index=True)
    duty_start_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    duty_end_time = Column(DateTime, nullable=True, index=True)
    total_duty_hours = Column(Float, default=0.0)
    total_rest_hours = Column(Float, default=0.0)
    is_currently_on_duty = Column(Boolean, default=True, index=True)
    off_duty_reason = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    volunteer = relationship("Volunteer", back_populates="duty_shifts")
    vehicle = relationship("Vehicle", back_populates="duty_shifts")

class VehicleWearInspection(Base):
    __tablename__ = "vehicle_wear_inspections"
    id = Column(Integer, primary_key=True, index=True)
    inspection_code = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    inspection_date = Column(Date, default=datetime.utcnow().date, nullable=False, index=True)
    inspected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    odometer_km = Column(Float, nullable=False)
    tire_tread_depth_mm = Column(Float, nullable=False, default=8.0)
    tire_condition_score = Column(Float, nullable=False, default=100.0)
    brake_pad_thickness_mm = Column(Float, nullable=False, default=12.0)
    brake_condition_score = Column(Float, nullable=False, default=100.0)
    clutch_play_status = Column(String(30), default="NORMAL")
    engine_oil_level_status = Column(String(30), default="OPTIMAL")
    suspension_status = Column(String(30), default="GOOD")
    overall_health_score_pct = Column(Float, nullable=False, default=100.0)
    is_safe_for_service = Column(Boolean, default=True, index=True)
    immediate_repair_needed = Column(Text, nullable=True)
    inspected_by = Column(String(100), nullable=False)
    vehicle = relationship("Vehicle", back_populates="wear_inspections")

class MSRTCSpotCashVoucher(Base):
    __tablename__ = "msrtc_spot_cash_vouchers"
    id = Column(Integer, primary_key=True, index=True)
    voucher_number = Column(String(50), unique=True, nullable=False, index=True)
    station_hub = Column(String(100), ForeignKey("territories.hub_name"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    msrtc_depot_name = Column(String(100), nullable=False)
    conductor_name = Column(String(100), nullable=False)
    conductor_buckle_no = Column(String(50), nullable=True)
    conductor_contact_phone = Column(String(20), nullable=True)
    cash_amount_paid_inr = Column(Float, nullable=False)
    etm_receipt_number = Column(String(100), nullable=False)
    receipt_photo_b64 = Column(Text, nullable=True)
    passenger_headcount = Column(Integer, nullable=False)
    destination_ground = Column(String(100), default="Ground 1 (Main Hall)")
    paid_by_volunteer_name = Column(String(100), nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow, index=True)
    paid_date = Column(Date, default=datetime.utcnow().date, index=True)
    is_verified_at_gate = Column(Boolean, default=False, index=True)
    verified_by_ground_sevadar = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    hub_ref = relationship("Territory", back_populates="msrtc_cash_vouchers")
    vehicle = relationship("Vehicle", back_populates="msrtc_cash_vouchers")

class HiredRollingContract(Base):
    __tablename__ = "hired_rolling_contracts"
    id = Column(Integer, primary_key=True, index=True)
    contract_code = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    vendor_agency_name = Column(String(100), nullable=False)
    daily_base_rate_inr = Column(Float, nullable=False, default=7500.0)
    daily_quota_km = Column(Float, nullable=False, default=300.0)
    extra_rate_per_km_inr = Column(Float, nullable=False, default=25.0)
    entry_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    entry_odometer_km = Column(Float, nullable=False)
    entry_gate_hub = Column(String(100), default="Central Venue Main Inward Gate")
    registered_by = Column(String(100), nullable=False)
    exit_timestamp = Column(DateTime, nullable=True, index=True)
    exit_odometer_km = Column(Float, nullable=True)
    exit_gate_hub = Column(String(100), nullable=True)
    exited_by = Column(String(100), nullable=True)
    status = Column(String(30), default="ACTIVE_ROLLING", nullable=False, index=True)
    total_duration_hours = Column(Float, default=0.0)
    billed_days = Column(Integer, default=1)
    total_km_run = Column(Float, default=0.0)
    total_quota_allowed_km = Column(Float, default=300.0)
    excess_km = Column(Float, default=0.0)
    base_hire_cost_inr = Column(Float, default=0.0)
    excess_km_cost_inr = Column(Float, default=0.0)
    total_settlement_inr = Column(Float, default=0.0)
    settlement_voucher_no = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    vehicle = relationship("Vehicle", back_populates="rolling_contracts")

class StationDemand(Base):
    __tablename__ = "station_demands"
    id = Column(Integer, primary_key=True, index=True)
    demand_code = Column(String(50), unique=True, nullable=False, index=True)
    hub_name = Column(String(100), ForeignKey("territories.hub_name"), nullable=False, index=True)
    waiting_passenger_count = Column(Integer, nullable=False)
    recommended_buses = Column(String(255), nullable=True)
    priority = Column(String(20), default="NORMAL")
    status = Column(String(30), default="PENDING")
    requested_by = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    hub_ref = relationship("Territory", back_populates="demands")

class TurnaroundMovement(Base):
    __tablename__ = "turnaround_movements"
    id = Column(Integer, primary_key=True, index=True)
    movement_type = Column(String(30), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    location_hub = Column(String(100), nullable=False)
    destination_hub = Column(String(100), nullable=True)
    passenger_count = Column(Integer, default=0)
    capacity = Column(Integer, nullable=False)
    odometer_km = Column(Float, nullable=True)
    recorded_by = Column(String(100), nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow, index=True)
    logged_date = Column(Date, default=datetime.utcnow().date, index=True)
    vehicle = relationship("Vehicle", back_populates="turnaround_logs")

class FuelLog(Base):
    __tablename__ = "fuel_logs"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    liters_filled = Column(Float, nullable=False)
    rate_per_liter = Column(Float, nullable=False)
    total_cost_inr = Column(Float, nullable=False)
    fuel_station_name = Column(String(100), default="Main Venue Fuel Staging Point")
    current_odometer_km = Column(Float, nullable=True)
    receipt_voucher_no = Column(String(50), nullable=True)
    filled_by = Column(String(100), nullable=False)
    filled_at = Column(DateTime, default=datetime.utcnow, index=True)
    filled_date = Column(Date, default=datetime.utcnow().date, index=True)
    vehicle = relationship("Vehicle", back_populates="fuel_logs")

class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    issue_category = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    description = Column(Text, nullable=False)
    reported_by = Column(String(100), nullable=False)
    status = Column(String(30), default="OPEN")
    repair_cost_inr = Column(Float, default=0.0)
    mechanic_notes = Column(Text, nullable=True)
    reported_at = Column(DateTime, default=datetime.utcnow, index=True)
    reported_date = Column(Date, default=datetime.utcnow().date, index=True)
    resolved_at = Column(DateTime, nullable=True)
    vehicle = relationship("Vehicle", back_populates="maintenance_records")

class Journey(Base):
    __tablename__ = "journeys"
    id = Column(Integer, primary_key=True, index=True)
    journey_code = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    rider_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    origin_name = Column(String(100), nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lng = Column(Float, nullable=False)
    destination_name = Column(String(100), nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_date = Column(Date, default=datetime.utcnow().date, index=True)
    ended_at = Column(DateTime, nullable=True)
    passenger_count = Column(Integer, default=0)
    journey_status = Column(String(50), default="ACTIVE_IN_TRANSIT", nullable=False, index=True)
    total_distance_km = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    vehicle = relationship("Vehicle", back_populates="journeys")
    telemetry_pings = relationship("TelemetryPing", back_populates="journey", cascade="all, delete-orphan")

class TelemetryPing(Base):
    __tablename__ = "telemetry_pings"
    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    sender_role = Column(String(30), nullable=False)
    sender_id = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    speed_kmh = Column(Float, default=0.0)
    heading = Column(Float, nullable=True)
    battery_level = Column(Integer, nullable=True)
    ping_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    journey = relationship("Journey", back_populates="telemetry_pings")
""",

    "app/schemas.py": """from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class OfflineQueueItem(BaseModel):
    idempotency_key: str
    endpoint: str
    method: str = "POST"
    payload: Dict[str, Any]
    client_timestamp: str
    volunteer_name: Optional[str] = "Station Sevadar"
    station_hub: Optional[str] = None

class OfflineBatchSyncRequest(BaseModel):
    items: List[OfflineQueueItem]

class OfflineBatchSyncResponse(BaseModel):
    status: str
    total_received: int
    total_processed: int
    total_duplicates_skipped: int
    errors: List[Dict[str, Any]] = []

class CrewDutyStartRequest(BaseModel):
    crew_role: str
    crew_name: str
    crew_phone: str
    station_hub: str
    vehicle_reg_number: Optional[str] = None
    notes: Optional[str] = None

class CrewDutyEndRequest(BaseModel):
    shift_id: int
    off_duty_reason: str = "Shift Completed"
    notes: Optional[str] = None

class VehicleWearInspectionRequest(BaseModel):
    vehicle_reg_number: str
    odometer_km: float
    tire_tread_depth_mm: float = 8.0
    tire_condition_score: float = 100.0
    brake_pad_thickness_mm: float = 12.0
    brake_condition_score: float = 100.0
    clutch_play_status: str = "NORMAL"
    engine_oil_level_status: str = "OPTIMAL"
    suspension_status: str = "GOOD"
    inspected_by: str
    immediate_repair_needed: Optional[str] = None

class PublicPassSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)

class StationCashFloatDisburseRequest(BaseModel):
    station_hub: str
    amount_inr: float = Field(..., gt=0)
    issued_by: str = "Central Treasury Lead"
    issued_to_coordinator: str
    notes: Optional[str] = None

class ReturnShuttleAllocateRequest(BaseModel):
    vehicle_id: int
    saint_ids: List[int]
    departure_hub: str
    notes: Optional[str] = None

class VolunteerRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    mobile_number: str = Field(..., min_length=10)
    unit_number: str = Field(..., min_length=1)
    branch_name: str = Field(..., min_length=2)
    duty_location: str
    photo_b64: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geo_accuracy: Optional[float] = None
    device_fingerprint: Optional[str] = "web_device"
    assigned_vehicle_reg: Optional[str] = None

class VolunteerLoginRequest(BaseModel):
    mobile_number: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    device_fingerprint: Optional[str] = "web_device"

class SaintRegisterRequest(BaseModel):
    full_name: str
    spiritual_order: Optional[str] = "Independent Ashram"
    contact_phone: str
    contact_email: Optional[str] = None
    group_size: int = Field(ge=1, default=1)
    arrival_mode: str = "Train"
    arrival_hub: str
    arrival_transit_number: Optional[str] = None
    arrival_pnr_ticket: Optional[str] = None
    arrival_datetime: str
    departure_mode: str = "Train"
    departure_hub: str
    departure_transit_number: Optional[str] = None
    departure_datetime: str
    assigned_ground: Optional[str] = "Ground 1 (Main Hall)"
    assigned_tent: Optional[str] = "Tent A-01"
    stay_duration_days: int = 4
    special_assistance_notes: Optional[str] = None

class VehicleCreateRequest(BaseModel):
    vehicle_reg_number: str = Field(..., min_length=4)
    vehicle_type: str = "Heavy Bus (50-seater)"
    capacity: int = 50
    ownership_type: str = "TRUST_OWNED"
    contractor_name: Optional[str] = "MSRTC Central / Private Operator"
    rate_per_trip_inr: float = 0.0
    fixed_daily_rate_inr: float = 0.0
    driver_name: str
    driver_phone: str
    rider_name: Optional[str] = None
    rider_phone: Optional[str] = None
    current_hub: str
    assigned_territory: str

class VehicleStatusUpdate(BaseModel):
    status: str
    current_passengers: Optional[int] = 0
    current_hub: Optional[str] = None
    current_destination: Optional[str] = None

class TentCheckinRequest(BaseModel):
    saint_id: int

class MSRTCSpotCashPaymentRequest(BaseModel):
    station_hub: str
    vehicle_reg_number: str = Field(..., min_length=4)
    msrtc_depot_name: str = Field(default="MSRTC Central Division")
    conductor_name: str = Field(..., min_length=2)
    conductor_buckle_no: Optional[str] = None
    conductor_contact_phone: Optional[str] = None
    cash_amount_paid_inr: float = Field(..., gt=0)
    etm_receipt_number: str = Field(..., min_length=2)
    receipt_photo_b64: Optional[str] = None
    passenger_headcount: int = Field(default=50, ge=1)
    destination_ground: Optional[str] = "Ground 1 (Main Hall)"
    paid_by_volunteer_name: str = Field(..., min_length=2)
    notes: Optional[str] = None

class MSRTCSpotCashVerifyRequest(BaseModel):
    voucher_id: int
    verified_by_ground_sevadar: str = Field(..., min_length=2)
    notes: Optional[str] = None

class RollingContractOnboardRequest(BaseModel):
    vehicle_reg_number: str = Field(..., min_length=4)
    vendor_agency_name: str = Field(..., min_length=2)
    daily_base_rate_inr: float = Field(default=7500.0, gt=0)
    daily_quota_km: float = Field(default=300.0, gt=0)
    extra_rate_per_km_inr: float = Field(default=25.0, gt=0)
    entry_odometer_km: float = Field(..., ge=0)
    entry_gate_hub: Optional[str] = "Central Venue Main Inward Gate"
    driver_name: str
    driver_phone: str
    capacity: int = 50
    vehicle_type: str = "Heavy Bus (50-seater)"
    registered_by: str = "Inward Gate Marshall"
    notes: Optional[str] = None

class RollingContractExitReleaseRequest(BaseModel):
    contract_id: int
    exit_odometer_km: float = Field(..., ge=0)
    exit_gate_hub: Optional[str] = "Central Venue Main Outward Gate"
    exited_by: str = "Outward Gate Auditor"
    notes: Optional[str] = None

class StationDemandCreateRequest(BaseModel):
    hub_name: str
    waiting_passenger_count: int = Field(..., ge=1)
    priority: str = "NORMAL"
    requested_by: str
    notes: Optional[str] = None

class VehicleAllocationScheduleRequest(BaseModel):
    vehicle_id: int
    demand_id: Optional[int] = None
    saint_ids: List[int] = []
    source_hub: str
    destination_hub: str
    allocated_passengers: int
    scheduled_departure: Optional[str] = None
    notes: Optional[str] = None

class TurnaroundLogRequest(BaseModel):
    vehicle_id: int
    movement_type: str
    location_hub: str
    destination_hub: Optional[str] = None
    passenger_count: int = 0
    odometer_km: Optional[float] = None
    recorded_by: str

class FuelLogRequest(BaseModel):
    vehicle_id: int
    liters_filled: float = Field(..., gt=0)
    rate_per_liter: float = Field(default=92.5, gt=0)
    fuel_station_name: Optional[str] = "Main Staging Fuel Depot"
    current_odometer_km: Optional[float] = None
    receipt_voucher_no: Optional[str] = None
    filled_by: str

class MaintenanceTicketRequest(BaseModel):
    vehicle_id: int
    issue_category: str
    severity: str = "MEDIUM"
    description: str
    reported_by: str

class MaintenanceResolveRequest(BaseModel):
    ticket_id: int
    repair_cost_inr: float = 0.0
    mechanic_notes: str

class JourneyStartRequest(BaseModel):
    vehicle_reg_number: str
    destination_name: str
    passenger_count: int = Field(default=0, ge=0)
    latitude: float
    longitude: float
    notes: Optional[str] = None

class JourneyEndRequest(BaseModel):
    journey_id: int
    latitude: float
    longitude: float
    end_location_name: Optional[str] = None

class TelemetryPingRequest(BaseModel):
    vehicle_reg_number: str
    journey_id: Optional[int] = None
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    speed_kmh: Optional[float] = 0.0
    heading: Optional[float] = None
    battery_level: Optional[int] = None
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

    "app/routers/auth.py": """import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Volunteer, VolunteerSession, Vehicle
from app.schemas import VolunteerRegisterRequest, VolunteerLoginRequest
from app.services.geo_service import verify_territory_geofence

router = APIRouter(prefix="/api/auth", tags=["Authentication & Geofencing"])

def _determine_role(duty_location: str) -> dict:
    loc = duty_location.lower()
    if "ground" in loc or "control" in loc or "venue" in loc:
        return {"system_role": "GROUND_ADMIN", "can_view_all_territories": True, "can_execute_ground_tasks": True, "can_execute_station_tasks": True, "can_manage_fleet": True}
    return {"system_role": "STATION_COORDINATOR", "can_view_all_territories": False, "can_execute_ground_tasks": False, "can_execute_station_tasks": True, "can_manage_fleet": False}

@router.post("/register")
def register_volunteer(req: VolunteerRegisterRequest, db: Session = Depends(get_db)):
    is_valid, distance_m, msg, hub = verify_territory_geofence(db, req.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    if db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number).first():
        raise HTTPException(status_code=400, detail="Mobile number already registered.")
    perms = _determine_role(req.duty_location)
    vol_code = f"VOL-{hub.hub_code}-{secrets.randbelow(9000) + 1000}"
    vol = Volunteer(
        volunteer_code=vol_code, full_name=req.full_name.strip(), mobile_number=req.mobile_number.strip(),
        unit_number=req.unit_number.strip(), branch_name=req.branch_name.strip(), duty_location=req.duty_location,
        latitude=req.latitude, longitude=req.longitude, geo_accuracy=req.geo_accuracy, geofence_verified=True, **perms
    )
    db.add(vol)
    db.commit()
    db.refresh(vol)
    token = secrets.token_hex(32)
    db.add(VolunteerSession(session_token=token, volunteer_id=vol.id, latitude=req.latitude, longitude=req.longitude, expires_at=datetime.utcnow() + timedelta(hours=24)))
    db.commit()
    return {"status": "REGISTERED", "session_token": token, "volunteer": {"id": vol.id, "volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "duty_location": vol.duty_location, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}

@router.post("/login")
def login_volunteer(req: VolunteerLoginRequest, db: Session = Depends(get_db)):
    vol = db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number.strip()).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found.")
    is_valid, distance_m, msg, _ = verify_territory_geofence(db, vol.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    token = secrets.token_hex(32)
    db.add(VolunteerSession(session_token=token, volunteer_id=vol.id, latitude=req.latitude, longitude=req.longitude, expires_at=datetime.utcnow() + timedelta(hours=24)))
    db.commit()
    return {"status": "AUTHENTICATED", "session_token": token, "volunteer": {"id": vol.id, "volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "duty_location": vol.duty_location, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}
""",

    "app/routers/saints.py": """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import Saint, Vehicle
from app.schemas import SaintRegisterRequest, TentCheckinRequest, PublicPassSearchRequest, ReturnShuttleAllocateRequest
from app.services.email_service import send_email_async_safe, build_saint_confirmation_html

router = APIRouter(prefix="/api/saints", tags=["Saints & Accommodation"])

@router.get("/")
def list_saints(hub: str = None, db: Session = Depends(get_db)):
    q = db.query(Saint)
    if hub and hub != "ALL":
        q = q.filter(Saint.arrival_hub == hub)
    return [{"id": s.id, "pass_code": f"SMG-{s.id:05d}", "full_name": s.full_name, "spiritual_order": s.spiritual_order, "contact_phone": s.contact_phone, "group_size": s.group_size, "arrival_mode": s.arrival_mode, "arrival_hub": s.arrival_hub, "arrival_transit_number": s.arrival_transit_number, "arrival_datetime": s.arrival_datetime, "departure_hub": s.departure_hub, "departure_datetime": s.departure_datetime, "assigned_ground": s.assigned_ground, "assigned_tent": s.assigned_tent, "status": s.status} for s in q.order_by(Saint.id.desc()).all()]

@router.post("/register")
def register_saint(req: SaintRegisterRequest, db: Session = Depends(get_db)):
    saint = Saint(**req.model_dump())
    db.add(saint)
    db.commit()
    db.refresh(saint)
    if req.contact_email:
        send_email_async_safe(req.contact_email, f"Samagam Pass SMG-{saint.id:05d}", build_saint_confirmation_html({"id": saint.id, "full_name": saint.full_name, "assigned_ground": saint.assigned_ground, "assigned_tent": saint.assigned_tent}))
    return {"status": "REGISTERED", "pass_code": f"SMG-{saint.id:05d}", "saint_id": saint.id}

@router.post("/checkin-tent")
def checkin_saint_to_tent(req: TentCheckinRequest, db: Session = Depends(get_db)):
    saint = db.query(Saint).filter(Saint.id == req.saint_id).first()
    if not saint:
        raise HTTPException(status_code=404, detail="Saint not found.")
    saint.status = "Checked-In at Tent"
    db.commit()
    return {"status": "CHECKED_IN", "saint_id": saint.id}

@router.post("/public-pass-lookup")
def public_boarding_pass_lookup(req: PublicPassSearchRequest, db: Session = Depends(get_db)):
    q = req.query.strip()
    num_id = int(q.upper().replace("SMG-", "")) if q.upper().startswith("SMG-") and q[4:].isdigit() else None
    filters = [Saint.contact_phone.ilike(f"%{q}%"), Saint.arrival_pnr_ticket.ilike(f"%{q}%"), Saint.full_name.ilike(f"%{q}%")]
    if num_id is not None:
        filters.append(Saint.id == num_id)
    matches = db.query(Saint).filter(or_(*filters)).limit(10).all()
    if not matches:
        raise HTTPException(status_code=404, detail="No boarding pass found.")
    return [{"pass_code": f"SMG-{s.id:05d}", "full_name": s.full_name, "group_size": s.group_size, "arrival_hub": s.arrival_hub, "arrival_datetime": s.arrival_datetime, "assigned_ground": s.assigned_ground, "assigned_tent": s.assigned_tent, "status": s.status} for s in matches]

@router.post("/allocate-return-shuttle")
def allocate_return_shuttle(req: ReturnShuttleAllocateRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
    saints = db.query(Saint).filter(Saint.id.in_(req.saint_ids)).all()
    if not veh or not saints:
        raise HTTPException(status_code=400, detail="Invalid vehicle or saints.")
    for s in saints:
        s.return_vehicle_id = veh.id
        s.status = "Return Shuttle Scheduled"
    veh.current_destination = req.departure_hub
    veh.status = "LOADED_OUT"
    db.commit()
    return {"status": "ALLOCATED", "vehicle_reg": veh.vehicle_reg_number}
""",

    "app/routers/fleet.py": """import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Vehicle, HiredRollingContract, MSRTCSpotCashVoucher, StationCashFloat, VehicleWearInspection
from app.schemas import VehicleCreateRequest, VehicleStatusUpdate, RollingContractOnboardRequest, RollingContractExitReleaseRequest, MSRTCSpotCashPaymentRequest, MSRTCSpotCashVerifyRequest, StationCashFloatDisburseRequest, VehicleWearInspectionRequest
from app.services.contract_service import compute_rolling_contract_metrics

router = APIRouter(prefix="/api/fleet", tags=["Fleet, Contracts & MSRTC Cash"])

@router.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db)):
    return [{"id": v.id, "vehicle_reg_number": v.vehicle_reg_number, "vehicle_type": v.vehicle_type, "capacity": v.capacity, "ownership_type": v.ownership_type, "driver_name": v.driver_name, "driver_phone": v.driver_phone, "current_hub": v.current_hub, "status": v.status, "current_passengers": v.current_passengers, "current_destination": v.current_destination, "health_score_pct": v.health_score_pct, "is_maintenance_flagged": v.is_maintenance_flagged, "current_lat": v.current_lat, "current_lng": v.current_lng, "current_speed_kmh": v.current_speed_kmh} for v in db.query(Vehicle).order_by(Vehicle.id.desc()).all()]

@router.post("/vehicles")
def add_vehicle(req: VehicleCreateRequest, db: Session = Depends(get_db)):
    veh = Vehicle(**req.model_dump())
    db.add(veh)
    db.commit()
    return {"status": "ADDED", "id": veh.id}

@router.patch("/vehicles/{vehicle_id}/status")
def update_vehicle_status(vehicle_id: int, req: VehicleStatusUpdate, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    veh.status = req.status
    if req.current_passengers is not None:
        veh.current_passengers = req.current_passengers
    db.commit()
    return {"status": "UPDATED"}

@router.get("/rolling-contracts")
def list_rolling_contracts(db: Session = Depends(get_db)):
    return [{"id": c.id, "contract_code": c.contract_code, "vehicle_reg_number": c.vehicle.vehicle_reg_number if c.vehicle else "N/A", "vendor_agency_name": c.vendor_agency_name, "entry_odometer_km": c.entry_odometer_km, "status": c.status, "settlement_voucher_no": c.settlement_voucher_no, "live_metrics": compute_rolling_contract_metrics(c)} for c in db.query(HiredRollingContract).order_by(HiredRollingContract.id.desc()).all()]

@router.post("/rolling-contracts/onboard")
def onboard_rolling_contract(req: RollingContractOnboardRequest, db: Session = Depends(get_db)):
    reg = req.vehicle_reg_number.upper().strip()
    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first()
    if not veh:
        veh = Vehicle(vehicle_reg_number=reg, vehicle_type=req.vehicle_type, capacity=req.capacity, ownership_type="HIRED_OUTSIDE", contractor_name=req.vendor_agency_name, is_rolling_contract=True, driver_name=req.driver_name, driver_phone=req.driver_phone, current_hub="Ground 1 (Main Hall)", assigned_territory="Ground 1 (Main Hall)")
        db.add(veh)
        db.commit()
        db.refresh(veh)
    code = f"HRC-{secrets.randbelow(9000) + 1000}"
    contract = HiredRollingContract(contract_code=code, vehicle_id=veh.id, vendor_agency_name=req.vendor_agency_name, daily_base_rate_inr=req.daily_base_rate_inr, daily_quota_km=req.daily_quota_km, extra_rate_per_km_inr=req.extra_rate_per_km_inr, entry_odometer_km=req.entry_odometer_km, registered_by=req.registered_by)
    db.add(contract)
    db.commit()
    return {"status": "STARTED", "contract_code": code}

@router.post("/rolling-contracts/release")
def release_rolling_contract(req: RollingContractExitReleaseRequest, db: Session = Depends(get_db)):
    c = db.query(HiredRollingContract).filter(HiredRollingContract.id == req.contract_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found.")
    now = datetime.utcnow()
    c.exit_timestamp = now
    c.exit_odometer_km = req.exit_odometer_km
    m = compute_rolling_contract_metrics(c, current_time=now, current_odometer_km=req.exit_odometer_km)
    c.total_settlement_inr = m["total_settlement_inr"]
    c.status = "SETTLED_AND_EXITED"
    c.settlement_voucher_no = f"SET-{c.contract_code}"
    db.commit()
    return {"status": "SETTLED", "voucher_no": c.settlement_voucher_no, "settlement": m}

@router.get("/msrtc-ledger")
def get_msrtc_cash_ledger(station_hub: str = None, db: Session = Depends(get_db)):
    fq = db.query(StationCashFloat)
    vq = db.query(MSRTCSpotCashVoucher)
    if station_hub and station_hub != "ALL":
        fq = fq.filter(StationCashFloat.station_hub == station_hub)
        vq = vq.filter(MSRTCSpotCashVoucher.station_hub == station_hub)
    floats = fq.all()
    vouchers = vq.order_by(MSRTCSpotCashVoucher.id.desc()).all()
    disp = sum(f.treasury_disbursed_amount_inr for f in floats)
    spent = sum(v.cash_amount_paid_inr for v in vouchers)
    return {"summary": {"total_treasury_imprest_inr": disp, "total_paid_to_conductors_inr": spent, "remaining_cash_in_hand_inr": disp - spent}, "vouchers": [{"id": v.id, "voucher_number": v.voucher_number, "station_hub": v.station_hub, "vehicle_reg_number": v.vehicle.vehicle_reg_number if v.vehicle else "N/A", "conductor_name": v.conductor_name, "cash_amount_paid_inr": v.cash_amount_paid_inr, "etm_receipt_number": v.etm_receipt_number, "passenger_headcount": v.passenger_headcount, "is_verified_at_gate": v.is_verified_at_gate, "verified_by_ground_sevadar": v.verified_by_ground_sevadar} for v in vouchers]}

@router.post("/msrtc-ledger/disburse-float")
def disburse_float(req: StationCashFloatDisburseRequest, db: Session = Depends(get_db)):
    db.add(StationCashFloat(station_hub=req.station_hub, treasury_disbursed_amount_inr=req.amount_inr, issued_by=req.issued_by, issued_to_coordinator=req.issued_to_coordinator, notes=req.notes))
    db.commit()
    return {"status": "DISBURSED"}

@router.post("/msrtc-ledger/pay-conductor")
def pay_msrtc_conductor(req: MSRTCSpotCashPaymentRequest, db: Session = Depends(get_db)):
    reg = req.vehicle_reg_number.upper().strip()
    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first()
    if not veh:
        veh = Vehicle(vehicle_reg_number=reg, vehicle_type="MSRTC State Bus", capacity=55, ownership_type="MSRTC_SPOT_CASH", driver_name=req.conductor_name, driver_phone="9999999999", current_hub=req.station_hub, assigned_territory=req.station_hub, status="LOADED_OUT", current_passengers=req.passenger_headcount)
        db.add(veh)
        db.commit()
        db.refresh(veh)
    v_code = f"MSRTC-{secrets.randbelow(90000) + 10000}"
    db.add(MSRTCSpotCashVoucher(voucher_number=v_code, station_hub=req.station_hub, vehicle_id=veh.id, msrtc_depot_name=req.msrtc_depot_name, conductor_name=req.conductor_name, cash_amount_paid_inr=req.cash_amount_paid_inr, etm_receipt_number=req.etm_receipt_number, passenger_headcount=req.passenger_headcount, paid_by_volunteer_name=req.paid_by_volunteer_name))
    db.commit()
    return {"status": "LOGGED", "voucher_number": v_code}

@router.post("/msrtc-ledger/verify-gate")
def verify_msrtc_gate(req: MSRTCSpotCashVerifyRequest, db: Session = Depends(get_db)):
    v = db.query(MSRTCSpotCashVoucher).filter(MSRTCSpotCashVoucher.id == req.voucher_id).first()
    if v:
        v.is_verified_at_gate = True
        v.verified_by_ground_sevadar = req.verified_by_ground_sevadar
        v.verified_at = datetime.utcnow()
        db.commit()
    return {"status": "VERIFIED"}

@router.post("/wear-inspection")
def log_wear_inspection(req: VehicleWearInspectionRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == req.vehicle_reg_number.upper().strip()).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    score = round((req.tire_condition_score + req.brake_condition_score) / 2.0, 1)
    safe = score >= 65.0 and not req.immediate_repair_needed
    db.add(VehicleWearInspection(inspection_code=f"INSP-{secrets.randbelow(90000)+10000}", vehicle_id=veh.id, odometer_km=req.odometer_km, tire_condition_score=req.tire_condition_score, brake_condition_score=req.brake_condition_score, overall_health_score_pct=score, is_safe_for_service=safe, immediate_repair_needed=req.immediate_repair_needed, inspected_by=req.inspected_by))
    veh.health_score_pct = score
    if not safe:
        veh.is_maintenance_flagged = True
        veh.status = "MAINTENANCE_HOLD"
    db.commit()
    return {"status": "LOGGED", "health_score_pct": score}
""",

    "app/routers/operations.py": """import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Territory, Vehicle, StationDemand, FuelLog, MaintenanceTicket, Journey, CrewDutyShift
from app.schemas import StationDemandCreateRequest, VehicleAllocationScheduleRequest, FuelLogRequest, MaintenanceTicketRequest, JourneyStartRequest, JourneyEndRequest, TelemetryPingRequest, CrewDutyStartRequest, CrewDutyEndRequest, OfflineBatchSyncRequest, OfflineBatchSyncResponse
from app.services.operations_service import compute_optimal_bus_mix, record_turnaround_movement, process_live_telemetry_ping

router = APIRouter(prefix="/api/operations", tags=["Operations, Telemetry & Sync"])

@router.get("/hubs")
def get_all_hubs(db: Session = Depends(get_db)):
    return [{"id": h.id, "hub_code": h.hub_code, "hub_name": h.hub_name, "hub_type": h.hub_type, "latitude": h.latitude, "longitude": h.longitude} for h in db.query(Territory).all()]

@router.get("/demands")
def list_station_demands(db: Session = Depends(get_db)):
    return [{"id": d.id, "demand_code": d.demand_code, "hub_name": d.hub_name, "waiting_passenger_count": d.waiting_passenger_count, "recommended_buses": d.recommended_buses, "priority": d.priority, "status": d.status, "requested_by": d.requested_by} for d in db.query(StationDemand).order_by(StationDemand.id.desc()).all()]

@router.post("/demands")
def create_station_demand(req: StationDemandCreateRequest, db: Session = Depends(get_db)):
    mix = compute_optimal_bus_mix(req.waiting_passenger_count)
    code = f"DEM-{secrets.randbelow(90000) + 10000}"
    db.add(StationDemand(demand_code=code, hub_name=req.hub_name, waiting_passenger_count=req.waiting_passenger_count, recommended_buses=mix["summary"], priority=req.priority, requested_by=req.requested_by, notes=req.notes))
    db.commit()
    return {"status": "DEMAND_RAISED", "demand_code": code, "recommended_mix": mix}

@router.post("/allocate-dispatch")
def allocate_dispatch(req: VehicleAllocationScheduleRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
    if req.demand_id:
        d = db.query(StationDemand).filter(StationDemand.id == req.demand_id).first()
        if d:
            d.status = "DISPATCHED"
    if veh:
        record_turnaround_movement(db, veh, "LOADED_OUT", req.source_hub, "Dispatcher", req.allocated_passengers, req.destination_hub)
    db.commit()
    return {"status": "DISPATCHED"}

@router.post("/journeys/start")
def start_live_journey(req: JourneyStartRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == req.vehicle_reg_number.upper().strip()).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    j_code = f"JRN-{secrets.randbelow(90000) + 10000}"
    j = Journey(journey_code=j_code, vehicle_id=veh.id, origin_name=veh.current_hub, origin_lat=req.latitude, origin_lng=req.longitude, destination_name=req.destination_name, destination_lat=19.2183, destination_lng=72.9781, passenger_count=req.passenger_count)
    db.add(j)
    db.commit()
    db.refresh(j)
    veh.active_journey_id = j.id
    veh.status = "LOADED_OUT"
    veh.current_destination = req.destination_name
    veh.current_passengers = req.passenger_count
    veh.current_lat = req.latitude
    veh.current_lng = req.longitude
    db.commit()
    return {"status": "STARTED", "journey_id": j.id, "journey_code": j_code}

@router.post("/telemetry/ping")
def ingest_telemetry_ping(req: TelemetryPingRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == req.vehicle_reg_number.upper().strip()).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    return process_live_telemetry_ping(db, veh, req.latitude, req.longitude, journey_id=req.journey_id, speed_kmh=req.speed_kmh)

@router.post("/journeys/end")
def end_live_journey(req: JourneyEndRequest, db: Session = Depends(get_db)):
    j = db.query(Journey).filter(Journey.id == req.journey_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Journey not found.")
    j.ended_at = datetime.utcnow()
    j.journey_status = "COMPLETED"
    if j.vehicle:
        j.vehicle.active_journey_id = None
        j.vehicle.status = "UNLOADED_IN"
        j.vehicle.current_passengers = 0
    db.commit()
    return {"status": "COMPLETED", "total_distance_km": j.total_distance_km}

@router.post("/fuel")
def log_fuel(req: FuelLogRequest, db: Session = Depends(get_db)):
    cost = round(req.liters_filled * req.rate_per_liter, 2)
    db.add(FuelLog(vehicle_id=req.vehicle_id, liters_filled=req.liters_filled, rate_per_liter=req.rate_per_liter, total_cost_inr=cost, receipt_voucher_no=req.receipt_voucher_no, filled_by=req.filled_by))
    db.commit()
    return {"status": "LOGGED", "total_cost_inr": cost}

@router.post("/maintenance")
def create_maintenance(req: MaintenanceTicketRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
    db.add(MaintenanceTicket(ticket_code=f"MNT-{secrets.randbelow(90000)+10000}", vehicle_id=req.vehicle_id, issue_category=req.issue_category, severity=req.severity, description=req.description, reported_by=req.reported_by))
    if veh:
        veh.is_maintenance_flagged = True
        veh.status = "MAINTENANCE_HOLD"
    db.commit()
    return {"status": "CREATED"}

@router.get("/shifts")
def list_shifts(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return [{"id": s.id, "crew_role": s.crew_role, "crew_name": s.crew_name, "station_hub": s.station_hub, "is_currently_on_duty": s.is_currently_on_duty, "elapsed_hours": round(((s.duty_end_time or now) - s.duty_start_time).total_seconds() / 3600.0, 2)} for s in db.query(CrewDutyShift).order_by(CrewDutyShift.id.desc()).all()]

@router.post("/shifts/start")
def start_shift(req: CrewDutyStartRequest, db: Session = Depends(get_db)):
    s = CrewDutyShift(crew_role=req.crew_role, crew_name=req.crew_name, crew_phone=req.crew_phone, station_hub=req.station_hub)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"status": "STARTED", "shift_id": s.id}

@router.post("/shifts/end")
def end_shift(req: CrewDutyEndRequest, db: Session = Depends(get_db)):
    s = db.query(CrewDutyShift).filter(CrewDutyShift.id == req.shift_id).first()
    if s:
        now = datetime.utcnow()
        s.duty_end_time = now
        s.is_currently_on_duty = False
        s.total_duty_hours = round((now - s.duty_start_time).total_seconds() / 3600.0, 2)
        db.commit()
        return {"status": "ENDED", "total_duty_hours": s.total_duty_hours}
    raise HTTPException(status_code=404, detail="Shift not found.")

@router.post("/offline-sync", response_model=OfflineBatchSyncResponse)
def offline_sync(req: OfflineBatchSyncRequest, db: Session = Depends(get_db)):
    for item in req.items:
        p = item.payload
        mix = compute_optimal_bus_mix(int(p.get("waiting_passenger_count", 10)))
        db.add(StationDemand(demand_code=f"OFF-{item.idempotency_key[:6].upper()}", hub_name=p.get("hub_name", "Thane Railway Station"), waiting_passenger_count=int(p.get("waiting_passenger_count", 10)), recommended_buses=mix["summary"], requested_by=item.volunteer_name or "Offline Sevadar"))
    db.commit()
    return OfflineBatchSyncResponse(status="SYNCED", total_received=len(req.items), total_processed=len(req.items), total_duplicates_skipped=0)
""",

    "app/routers/reports.py": """import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Saint, Vehicle, StationDemand, HiredRollingContract, MSRTCSpotCashVoucher, StationCashFloat, FuelLog, MaintenanceTicket, CrewDutyShift
from app.services.contract_service import compute_rolling_contract_metrics

router = APIRouter(prefix="/api/reports", tags=["Executive Analytics & Exports"])

@router.get("/executive-summary")
def get_executive_summary(db: Session = Depends(get_db)):
    total_saints = db.query(func.sum(Saint.group_size)).scalar() or 0
    checked_in = db.query(func.sum(Saint.group_size)).filter(Saint.status == "Checked-In at Tent").scalar() or 0
    active_c = db.query(HiredRollingContract).filter(HiredRollingContract.status == "ACTIVE_ROLLING").all()
    settled_c = db.query(HiredRollingContract).filter(HiredRollingContract.status == "SETTLED_AND_EXITED").all()
    accrued = sum(compute_rolling_contract_metrics(c)["total_settlement_inr"] for c in active_c)
    settled = sum(c.total_settlement_inr for c in settled_c)
    msrtc_spent = db.query(func.sum(MSRTCSpotCashVoucher.cash_amount_paid_inr)).scalar() or 0.0
    msrtc_float = db.query(func.sum(StationCashFloat.treasury_disbursed_amount_inr)).scalar() or 0.0
    fuel_spent = db.query(func.sum(FuelLog.total_cost_inr)).scalar() or 0.0
    maint_spent = db.query(func.sum(MaintenanceTicket.repair_cost_inr)).scalar() or 0.0

    return {
        "saints": {"total_pilgrims": int(total_saints), "total_groups": db.query(Saint).count(), "checked_in_pilgrims": int(checked_in)},
        "fleet": {"total_vehicles": db.query(Vehicle).count(), "active_in_transit": db.query(Vehicle).filter(Vehicle.status.in_(["LOADED_OUT", "EMPTY_OUT"])).count(), "maintenance_hold": db.query(Vehicle).filter(Vehicle.is_maintenance_flagged == True).count()},
        "station_queues": {"pending_demands": db.query(StationDemand).filter(StationDemand.status == "PENDING").count(), "waiting_passengers": int(db.query(func.sum(StationDemand.waiting_passenger_count)).filter(StationDemand.status == "PENDING").scalar() or 0)},
        "financials_inr": {"msrtc_imprest_balance_inr": round(msrtc_float - msrtc_spent, 2), "grand_total_transport_spend_inr": round(accrued + settled + msrtc_spent + fuel_spent + maint_spent, 2)},
        "crew": {"currently_on_duty": db.query(CrewDutyShift).filter(CrewDutyShift.is_currently_on_duty == True).count()}
    }

@router.get("/export/saints-csv")
def export_saints_csv(db: Session = Depends(get_db)):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Pass_ID", "Name", "Phone", "Group_Size", "Arrival_Hub", "Ground", "Tent", "Status"])
    for s in db.query(Saint).all():
        w.writerow([f"SMG-{s.id:05d}", s.full_name, s.contact_phone, s.group_size, s.arrival_hub, s.assigned_ground, s.assigned_tent, s.status])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=samagam_saints.csv"})

@router.get("/export/financials-csv")
def export_financials_csv(db: Session = Depends(get_db)):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Type", "Code", "Amount_INR", "Status"])
    for c in db.query(HiredRollingContract).all():
        w.writerow(["24H_CONTRACT", c.contract_code, compute_rolling_contract_metrics(c)["total_settlement_inr"], c.status])
    for v in db.query(MSRTCSpotCashVoucher).all():
        w.writerow(["MSRTC_CASH", v.voucher_number, v.cash_amount_paid_inr, "VERIFIED" if v.is_verified_at_gate else "PENDING"])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=samagam_financials.csv"})
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
    return _serve_html("admin_dashboard.html")

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

    "samagam_master_topology_and_operations.html": """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Samagam Transport Master Blueprint</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 p-8 font-sans">
<div class="max-w-4xl mx-auto bg-white p-8 rounded-2xl shadow space-y-4">
<h1 class="text-2xl font-extrabold text-emerald-900">SAMAGAM TRANSPORT & LOGISTICS — MASTER ARCHITECTURE BLUEPRINT</h1>
<p class="text-sm text-slate-600">14 Mumbai Hubs • 2.0km Sevadar Geofence • 300s Live GPS Radar • 24h Rolling Contracts • MSRTC Spot Cash Ledger</p>
<button onclick="window.print()" class="bg-emerald-700 text-white px-4 py-2 rounded-lg text-xs font-bold">🖨️ Print Blueprint</button>
</div>
</body></html>
"""
}

def install():
    for rel_path, content in FILES.items():
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Created {rel_path}")
    print("\n🎉 All 19 backend & root runner files installed! Now run:")
    print("   pip install -r requirements.txt")
    print("   python run.py")

if __name__ == "__main__":
    install()