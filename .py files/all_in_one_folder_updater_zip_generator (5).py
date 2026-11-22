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

class EmailOTP(Base):
    __tablename__ = "email_otps"
    email = Column(String(120), primary_key=True, index=True)
    code_hash = Column(String(128), nullable=False)
    salt = Column(String(32), nullable=False)
    expires_ts = Column(Float, nullable=False)
    attempts = Column(Integer, default=0)
    sent_ts = Column(Float, nullable=False)

class DevoteeParkingPass(Base):
    __tablename__ = "devotee_parking_passes"
    id = Column(Integer, primary_key=True, index=True)
    parking_token = Column(String(30), unique=True, nullable=False, index=True)
    vehicle_reg_number = Column(String(30), nullable=False, index=True)
    vehicle_category = Column(String(40), default="Car / SUV")
    vehicle_color_model = Column(String(80), nullable=True)
    owner_name = Column(String(120), nullable=False)
    owner_phone = Column(String(20), nullable=False, index=True)
    parking_zone = Column(String(80), default="Parking Zone P1")
    key_custody_mode = Column(String(40), default="WITH_OWNER")
    key_tag_number = Column(String(30), nullable=True)
    exit_pin_hash = Column(String(255), nullable=False)
    entry_owner_photo_b64 = Column(Text, nullable=True)
    checked_in_by = Column(String(100), nullable=False)
    entry_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(30), default="PARKED_INSIDE", index=True)
    exit_gate_name = Column(String(60), nullable=True)
    exit_timestamp = Column(DateTime, nullable=True)
    verified_exit_by = Column(String(100), nullable=True)
    security_notes = Column(Text, nullable=True)

class CCTVAnprEvent(Base):
    __tablename__ = "cctv_anpr_events"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(60), nullable=False, index=True)
    gate_direction = Column(String(20), nullable=False)
    plate_number = Column(String(30), nullable=False, index=True)
    matched_parking_token = Column(String(30), nullable=True)
    action_taken = Column(String(80), nullable=False)
    alert_level = Column(String(20), default="INFO")
    snapshot_b64 = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)

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
    email = Column(String(120), unique=True, nullable=True, index=True)
    pin_hash = Column(String(255), nullable=True)
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
    session_token = Column(String(128), primary_key=True)
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
    assigned_driver_id = Column(Integer, nullable=True, index=True)
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

class SevaDonatedVehicle(Base):
    __tablename__ = "seva_donated_vehicles"
    id = Column(Integer, primary_key=True, index=True)
    receipt_code = Column(String(40), unique=True, nullable=False, index=True)
    handover_date = Column(String(30), nullable=False)
    handover_time = Column(String(20), nullable=False)
    vehicle_reg_number = Column(String(30), nullable=False, index=True)
    vehicle_type = Column(String(60), nullable=False)
    zone_and_branch = Column(String(120), nullable=False)
    owner_name = Column(String(120), nullable=False)
    owner_phone = Column(String(20), nullable=False)
    seva_from_date = Column(String(30), nullable=False)
    seva_till_date = Column(String(30), nullable=False)
    fuel_level = Column(String(30), nullable=False)
    fuel_type = Column(String(30), nullable=False)
    odometer_km = Column(Float, nullable=False)
    exterior_condition = Column(String(150), nullable=False)
    vehicle_photo_b64 = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    handed_over_by_name = Column(String(120), nullable=False)
    received_by_sevadar_name = Column(String(120), nullable=False)
    status = Column(String(30), default="AVAILABLE_AT_GROUND", index=True)
    allocated_to_department = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DepartmentVehicleRequisition(Base):
    __tablename__ = "department_vehicle_requisitions"
    id = Column(Integer, primary_key=True, index=True)
    requisition_code = Column(String(40), unique=True, nullable=False, index=True)
    department_name = Column(String(100), nullable=False)
    required_vehicle_type = Column(String(60), nullable=False)
    quantity_needed = Column(Integer, default=1)
    requester_name = Column(String(120), nullable=False)
    requester_phone = Column(String(20), nullable=False)
    required_duration = Column(String(100), nullable=False)
    department_head_name = Column(String(120), nullable=False)
    purpose_details = Column(Text, nullable=False)
    approval_stamp_b64 = Column(Text, nullable=True)
    status = Column(String(30), default="PENDING_ALLOCATION", index=True)
    allocated_seva_vehicle_id = Column(Integer, nullable=True)
    allocated_vehicle_reg = Column(String(30), nullable=True)
    allocated_by_member = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PickupDropVehicleRequest(Base):
    __tablename__ = "pickup_drop_vehicle_requests"
    id = Column(Integer, primary_key=True, index=True)
    request_code = Column(String(40), unique=True, nullable=False, index=True)
    trip_direction = Column(String(40), nullable=False)
    transit_hub = Column(String(120), nullable=False, index=True)
    passenger_count = Column(Integer, nullable=False)
    vehicle_type_requested = Column(String(80), nullable=False)
    vehicles_needed = Column(Integer, default=1)
    scheduled_datetime = Column(String(60), nullable=False)
    train_flight_details = Column(String(120), nullable=True)
    requester_name = Column(String(120), nullable=False)
    requester_phone = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(30), default="PENDING_DISPATCH", index=True)
    assigned_vehicle_reg = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RentalHiringProforma(Base):
    __tablename__ = "rental_hiring_proformas"
    id = Column(Integer, primary_key=True, index=True)
    proforma_code = Column(String(40), unique=True, nullable=False, index=True)
    proforma_date = Column(String(30), nullable=False)
    vendor_name = Column(String(150), nullable=False)
    vendor_phone = Column(String(60), nullable=True)
    duty_sector = Column(String(120), nullable=False)
    shortage_reason = Column(Text, nullable=True)
    line_items_json = Column(Text, nullable=False)
    committee_members_json = Column(Text, nullable=False)
    total_estimated_inr = Column(Float, default=0.0)
    status = Column(String(30), default="PENDING_COMMITTEE_SIGNATURES", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GroundStationIntercom(Base):
    __tablename__ = "ground_station_intercom"
    id = Column(Integer, primary_key=True, index=True)
    channel_hub = Column(String(100), nullable=False, index=True)
    sender_side = Column(String(30), nullable=False)
    sender_name = Column(String(100), nullable=False)
    priority = Column(String(20), default="NORMAL")
    message_text = Column(Text, nullable=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_date = Column(Date, default=datetime.utcnow().date, index=True)

class CrewDutyShift(Base):
    __tablename__ = "crew_duty_shifts"
    id = Column(Integer, primary_key=True, index=True)
    crew_role = Column(String(30), nullable=False, index=True)
    crew_name = Column(String(100), nullable=False, index=True)
    crew_phone = Column(String(20), nullable=False, index=True)
    crew_email = Column(String(120), nullable=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    vehicle_reg_number = Column(String(30), nullable=True)
    station_hub = Column(String(100), nullable=False)
    duty_date = Column(Date, default=datetime.utcnow().date, nullable=False, index=True)
    duty_start_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    duty_end_time = Column(DateTime, nullable=True, index=True)
    total_duty_hours = Column(Float, default=0.0)
    total_rest_hours = Column(Float, default=0.0)
    is_currently_on_duty = Column(Boolean, default=True, index=True)
    off_duty_reason = Column(String(100), nullable=True)
    ended_by = Column(String(100), nullable=True)
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
""",

    "app/routers/auth.py": """import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import get_db
from app.models import Volunteer, VolunteerSession, Vehicle, EmailOTP, CrewDutyShift
from app.schemas import VolunteerRegisterRequest, VolunteerLoginRequest
from app.services.geo_service import verify_territory_geofence
from app.services.email_service import send_email_async_safe

router = APIRouter(prefix="/api/auth", tags=["Authentication & Geofencing"])

OTP_TTL = 300
REG_CODE = os.environ.get("REG_CODE", "SAMAGAM26").strip()
OTP_DEV_ECHO = os.environ.get("OTP_DEV_ECHO", "1") == "1"
EMAIL_RE = re.compile(r"^[^@\\s]{1,64}@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")

def _tok_hash(tok: str) -> str:
    return hashlib.sha256(str(tok or "").encode()).hexdigest()

def _otp_hash(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()

def _norm_phone(p: str) -> str:
    d = re.sub(r"\\D", "", str(p or ""))
    return d[-10:] if len(d) > 10 else d

def _norm_email(e: str) -> str:
    return str(e or "").strip().lower()[:120]

def _norm_pin(p: str) -> str:
    return re.sub(r"\\D", "", str(p or ""))

def get_current_volunteer(x_session_token: str = Header(None), x_driver_token: str = Header(None), db: Session = Depends(get_db)) -> Volunteer:
    raw_tok = x_driver_token or x_session_token
    if not raw_tok:
        raise HTTPException(status_code=401, detail="Missing session token.")
    session = db.query(VolunteerSession).filter(VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired.")
    vol = db.query(Volunteer).filter(Volunteer.id == session.volunteer_id, Volunteer.is_active == True).first()
    if not vol:
        raise HTTPException(status_code=403, detail="Account inactive.")
    return vol

def get_optional_volunteer(x_session_token: str = Header(None), x_driver_token: str = Header(None), db: Session = Depends(get_db)):
    raw_tok = x_driver_token or x_session_token
    if not raw_tok:
        return None
    session = db.query(VolunteerSession).filter(VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])).first()
    if not session or session.expires_at < datetime.utcnow():
        return None
    return db.query(Volunteer).filter(Volunteer.id == session.volunteer_id, Volunteer.is_active == True).first()

def _driver_payload(db: Session, vol: Volunteer, token: str = None) -> dict:
    assigned_bus = db.query(Vehicle).filter((Vehicle.assigned_driver_id == vol.id) | (Vehicle.driver_phone == vol.mobile_number)).first()
    open_shift = db.query(CrewDutyShift).filter(CrewDutyShift.crew_phone == vol.mobile_number, CrewDutyShift.is_currently_on_duty == True).first()
    out = {
        "logged_in": True,
        "driver": {
            "id": vol.id, "volunteer_code": vol.volunteer_code, "name": vol.full_name,
            "phone": vol.mobile_number, "email": vol.email or "", "duty_location": vol.duty_location,
            "system_role": vol.system_role, "vehicle_id": assigned_bus.id if assigned_bus else None,
            "vehicle_reg_number": assigned_bus.vehicle_reg_number if assigned_bus else None,
            "on_duty": bool(open_shift), "shift_id": open_shift.id if open_shift else None
        }
    }
    if token:
        out["token"] = token
    return out

@router.post("/otp/send")
def send_driver_otp(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or data.get("email") or data.get("phone") or "").strip()
    if not ident:
        raise HTTPException(status_code=400, detail="Enter mobile or email.")
    vol = db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first() if "@" in ident else db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()
    if vol:
        return {"requires_pin": True, "pin_missing": not bool(vol.pin_hash), "has_email": bool(vol.email), "driver_name": vol.full_name, "system_role": vol.system_role}
    if "@" not in ident or not EMAIL_RE.match(_norm_email(ident)):
        raise HTTPException(status_code=404, detail="Mobile not registered. Register first with email.")
    email = _norm_email(ident)
    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(8)
    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if row:
        row.code_hash, row.salt, row.expires_ts, row.attempts, row.sent_ts = _otp_hash(code, salt), salt, time.time() + OTP_TTL, 0, time.time()
    else:
        db.add(EmailOTP(email=email, code_hash=_otp_hash(code, salt), salt=salt, expires_ts=time.time() + OTP_TTL, attempts=0, sent_ts=time.time()))
    db.commit()
    send_email_async_safe(email, f"{code} is your Samagam OTP", f"<p>Your verification code is <b>{code}</b></p>")
    resp = {"sent": True, "email": email, "ttl": OTP_TTL}
    if OTP_DEV_ECHO:
        resp["dev_otp"] = code
    return resp

@router.post("/otp/verify")
def verify_driver_otp(data: dict, db: Session = Depends(get_db)):
    email = _norm_email(data.get("email"))
    code = re.sub(r"\\D", "", str(data.get("otp") or ""))
    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if not row or row.expires_ts < time.time() or not hmac.compare_digest(_otp_hash(code, row.salt), row.code_hash):
        raise HTTPException(status_code=403, detail="Invalid or expired OTP.")
    name = str(data.get("name") or "").strip()
    phone = _norm_phone(data.get("phone"))
    pin = _norm_pin(data.get("pin"))
    role = str(data.get("system_role") or "DRIVER").upper().strip()
    if len(phone) != 10 or len(pin) != 4 or not name:
        raise HTTPException(status_code=400, detail="Provide full name, 10-digit mobile, and 4-digit PIN.")
    if REG_CODE and str(data.get("code") or "").strip() != REG_CODE:
        raise HTTPException(status_code=403, detail="Wrong event code.")
    vol = Volunteer(
        volunteer_code=f"CREW-{secrets.randbelow(9000)+1000}", full_name=name, mobile_number=phone, email=email,
        pin_hash=generate_password_hash(pin), unit_number="Field", branch_name="Samagam Transport",
        duty_location="Ground 1 (Main Hall)", system_role=role, is_driver=(role == "DRIVER"), geofence_verified=True
    )
    db.add(vol)
    db.delete(row)
    db.commit()
    db.refresh(vol)
    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(days=7)))
    db.commit()
    return _driver_payload(db, vol, raw_tok)

@router.post("/pin/verify")
def verify_driver_pin(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or "").strip()
    pin = _norm_pin(data.get("pin"))
    vol = db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first() if "@" in ident else db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()
    if not vol or not vol.pin_hash or not check_password_hash(vol.pin_hash, pin):
        raise HTTPException(status_code=403, detail="Invalid credentials or 4-digit PIN.")
    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(days=7)))
    db.commit()
    return _driver_payload(db, vol, raw_tok)

@router.get("/driver-me")
def get_driver_me(vol: Volunteer = Depends(get_current_volunteer), db: Session = Depends(get_db)):
    return _driver_payload(db, vol)

@router.post("/driver-logout")
def driver_logout(x_driver_token: str = Header(None), x_session_token: str = Header(None), db: Session = Depends(get_db)):
    raw_tok = x_driver_token or x_session_token
    if raw_tok:
        sess = db.query(VolunteerSession).filter(VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])).first()
        if sess:
            vol = db.query(Volunteer).filter(Volunteer.id == sess.volunteer_id).first()
            if vol and db.query(CrewDutyShift).filter(CrewDutyShift.crew_phone == vol.mobile_number, CrewDutyShift.is_currently_on_duty == True).first():
                raise HTTPException(status_code=409, detail="You are still ON DUTY. Tap 'End Duty Shift' before logging out.")
            db.delete(sess)
            db.commit()
    return {"ok": True}

@router.get("/crew")
def list_registered_crew(db: Session = Depends(get_db)):
    crew = db.query(Volunteer).order_by(Volunteer.id.desc()).all()
    out = []
    for v in crew:
        bus = db.query(Vehicle).filter((Vehicle.assigned_driver_id == v.id) | (Vehicle.driver_phone == v.mobile_number)).first()
        out.append({"id": v.id, "volunteer_code": v.volunteer_code, "full_name": v.full_name, "mobile_number": v.mobile_number, "email": v.email or "", "system_role": v.system_role, "duty_location": v.duty_location, "has_pin": bool(v.pin_hash), "assigned_bus": bus.vehicle_reg_number if bus else ""})
    return out

@router.post("/crew/{crew_id}/reset-pin")
def admin_reset_crew_pin(crew_id: int, data: dict = None, db: Session = Depends(get_db)):
    data = data or {}
    vol = db.query(Volunteer).filter(Volunteer.id == crew_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Crew member not found.")
    raw_pin = _norm_pin(data.get("pin"))
    pin = raw_pin if len(raw_pin) == 4 else f"{secrets.randbelow(10000):04d}"
    vol.pin_hash = generate_password_hash(pin)
    db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    db.commit()
    return {"status": "PIN_RESET", "crew_id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number, "new_pin": pin}

@router.post("/register")
def register_volunteer(req: VolunteerRegisterRequest, db: Session = Depends(get_db)):
    is_valid, _, msg, hub = verify_territory_geofence(db, req.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    vol = Volunteer(volunteer_code=f"VOL-{hub.hub_code}-{secrets.randbelow(9000)+1000}", full_name=req.full_name, mobile_number=req.mobile_number, unit_number=req.unit_number, branch_name=req.branch_name, duty_location=req.duty_location, system_role="STATION_COORDINATOR", geofence_verified=True)
    db.add(vol)
    db.commit()
    return {"status": "REGISTERED", "volunteer": {"id": vol.id, "volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "system_role": vol.system_role, "can_view_all_territories": False}}

@router.post("/login")
def login_volunteer(req: VolunteerLoginRequest, db: Session = Depends(get_db)):
    vol = db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number.strip()).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found.")
    return {"status": "AUTHENTICATED", "volunteer": {"id": vol.id, "volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}
""",

    "app/routers/saints.py": """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import Saint, Vehicle
from app.schemas import SaintRegisterRequest, TentCheckinRequest, PublicPassSearchRequest, ReturnShuttleAllocateRequest

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
    matches = db.query(Saint).filter(or_(Saint.contact_phone.ilike(f"%{q}%"), Saint.full_name.ilike(f"%{q}%"))).limit(10).all()
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
    db.commit()
    return {"status": "ALLOCATED", "vehicle_reg": veh.vehicle_reg_number}
""",

    "app/routers/fleet.py": """import re
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_db
from app.models import (
    Vehicle, HiredRollingContract, MSRTCSpotCashVoucher, StationCashFloat,
    VehicleWearInspection, Volunteer, SevaDonatedVehicle, DepartmentVehicleRequisition,
    DevoteeParkingPass, CCTVAnprEvent, RentalHiringProforma
)
from app.schemas import (
    VehicleCreateRequest, VehicleStatusUpdate, RollingContractOnboardRequest,
    RollingContractExitReleaseRequest, MSRTCSpotCashPaymentRequest, MSRTCSpotCashVerifyRequest,
    StationCashFloatDisburseRequest, VehicleWearInspectionRequest
)
from app.services.contract_service import compute_rolling_contract_metrics
from app.routers.auth import get_optional_volunteer

router = APIRouter(prefix="/api/fleet", tags=["Fleet, Parking Security & Seva Vehicles"])

@router.get("/vehicles")
def list_vehicles(vol: Volunteer = Depends(get_optional_volunteer), db: Session = Depends(get_db)):
    q = db.query(Vehicle)
    if vol and vol.system_role == "DRIVER":
        q = q.filter((Vehicle.assigned_driver_id == vol.id) | (Vehicle.driver_phone == vol.mobile_number))
    return [{"id": v.id, "vehicle_reg_number": v.vehicle_reg_number, "vehicle_type": v.vehicle_type, "capacity": v.capacity, "ownership_type": v.ownership_type, "driver_name": v.driver_name, "driver_phone": v.driver_phone, "current_hub": v.current_hub, "status": v.status, "current_passengers": v.current_passengers, "current_destination": v.current_destination, "health_score_pct": v.health_score_pct, "is_maintenance_flagged": v.is_maintenance_flagged, "current_lat": v.current_lat, "current_lng": v.current_lng, "current_speed_kmh": v.current_speed_kmh, "active_journey_id": v.active_journey_id} for v in q.order_by(Vehicle.id.desc()).all()]

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
    db.add(HiredRollingContract(contract_code=code, vehicle_id=veh.id, vendor_agency_name=req.vendor_agency_name, daily_base_rate_inr=req.daily_base_rate_inr, daily_quota_km=req.daily_quota_km, extra_rate_per_km_inr=req.extra_rate_per_km_inr, entry_odometer_km=req.entry_odometer_km, registered_by=req.registered_by))
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
    disp = sum(f.treasury_disbursed_amount_inr for f in fq.all())
    vouchers = vq.order_by(MSRTCSpotCashVoucher.id.desc()).all()
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

@router.get("/seva-donations")
def list_seva_donations(db: Session = Depends(get_db)):
    return [{"id": v.id, "receipt_code": v.receipt_code, "vehicle_reg_number": v.vehicle_reg_number, "vehicle_type": v.vehicle_type, "zone_and_branch": v.zone_and_branch, "owner_name": v.owner_name, "owner_phone": v.owner_phone, "seva_from_date": v.seva_from_date, "seva_till_date": v.seva_till_date, "fuel_level": v.fuel_level, "fuel_type": v.fuel_type, "vehicle_photo_b64": v.vehicle_photo_b64, "status": v.status, "allocated_to_department": v.allocated_to_department} for v in db.query(SevaDonatedVehicle).order_by(SevaDonatedVehicle.id.desc()).all()]

@router.post("/seva-donations")
def create_seva_donation(data: dict, db: Session = Depends(get_db)):
    code = f"SEVA-{secrets.randbelow(9000)+1000}"
    item = SevaDonatedVehicle(receipt_code=code, handover_date=data.get("handover_date", ""), handover_time=data.get("handover_time", ""), vehicle_reg_number=str(data.get("vehicle_reg_number", "")).upper(), vehicle_type=data.get("vehicle_type", "Car"), zone_and_branch=data.get("zone_and_branch", ""), owner_name=data.get("owner_name", ""), owner_phone=data.get("owner_phone", ""), seva_from_date=data.get("seva_from_date", ""), seva_till_date=data.get("seva_till_date", ""), fuel_level=data.get("fuel_level", "Half"), fuel_type=data.get("fuel_type", "Diesel"), odometer_km=float(data.get("odometer_km", 0)), exterior_condition=data.get("exterior_condition", "Clean"), vehicle_photo_b64=data.get("vehicle_photo_b64"), remarks=data.get("remarks"), handed_over_by_name=data.get("handed_over_by_name", ""), received_by_sevadar_name=data.get("received_by_sevadar_name", ""))
    db.add(item)
    db.commit()
    return {"status": "SAVED", "receipt_code": code}

@router.get("/dept-requisitions")
def list_dept_requisitions(db: Session = Depends(get_db)):
    return [{"id": r.id, "requisition_code": r.requisition_code, "department_name": r.department_name, "required_vehicle_type": r.required_vehicle_type, "quantity_needed": r.quantity_needed, "requester_name": r.requester_name, "requester_phone": r.requester_phone, "required_duration": r.required_duration, "department_head_name": r.department_head_name, "purpose_details": r.purpose_details, "approval_stamp_b64": r.approval_stamp_b64, "status": r.status, "allocated_vehicle_reg": r.allocated_vehicle_reg, "allocated_by_member": r.allocated_by_member} for r in db.query(DepartmentVehicleRequisition).order_by(DepartmentVehicleRequisition.id.desc()).all()]

@router.post("/dept-requisitions")
def create_dept_requisition(data: dict, db: Session = Depends(get_db)):
    code = f"REQ-{secrets.randbelow(9000)+1000}"
    req = DepartmentVehicleRequisition(requisition_code=code, department_name=data.get("department_name", ""), required_vehicle_type=data.get("required_vehicle_type", ""), quantity_needed=int(data.get("quantity_needed", 1)), requester_name=data.get("requester_name", ""), requester_phone=data.get("requester_phone", ""), required_duration=data.get("required_duration", ""), department_head_name=data.get("department_head_name", ""), purpose_details=data.get("purpose_details", ""), approval_stamp_b64=data.get("approval_stamp_b64"))
    db.add(req)
    db.commit()
    return {"status": "SAVED", "requisition_code": code}

@router.post("/dept-requisitions/allocate")
def allocate_dept_requisition(data: dict, db: Session = Depends(get_db)):
    req = db.query(DepartmentVehicleRequisition).filter(DepartmentVehicleRequisition.id == data.get("requisition_id")).first()
    veh = db.query(SevaDonatedVehicle).filter(SevaDonatedVehicle.id == data.get("seva_vehicle_id")).first()
    if not req or not veh:
        raise HTTPException(status_code=404, detail="Requisition or Seva vehicle not found.")
    req.status = "ALLOCATED"
    req.allocated_seva_vehicle_id = veh.id
    req.allocated_vehicle_reg = veh.vehicle_reg_number
    req.allocated_by_member = data.get("allocated_by_member", "Ground Transport Member")
    veh.status = "ALLOCATED_TO_DEPT"
    veh.allocated_to_department = req.department_name
    db.commit()
    return {"status": "ALLOCATED"}

@router.post("/ground-allocator-login")
def ground_allocator_login(data: dict, db: Session = Depends(get_db)):
    mobile = str(data.get("mobile_number", "")).strip()
    passcode = str(data.get("passcode", "")).strip()
    if passcode != "GND-2026":
        raise HTTPException(status_code=403, detail="Invalid Ground Transport Passcode.")
    vol = db.query(Volunteer).filter(Volunteer.mobile_number == mobile).first()
    name = vol.full_name if vol else f"Ground Sevadar ({mobile})"
    return {"status": "AUTHENTICATED", "member": {"full_name": name, "mobile_number": mobile}}

@router.get("/parking-passes")
def list_parking_passes(query: str = "", status: str = "PARKED_INSIDE", db: Session = Depends(get_db)):
    q = db.query(DevoteeParkingPass)
    if status and status != "ALL":
        q = q.filter(DevoteeParkingPass.status == status)
    if query:
        q = q.filter(or_(DevoteeParkingPass.vehicle_reg_number.ilike(f"%{query}%"), DevoteeParkingPass.parking_token.ilike(f"%{query}%"), DevoteeParkingPass.owner_phone.ilike(f"%{query}%")))
    return [{"id": p.id, "parking_token": p.parking_token, "vehicle_reg_number": p.vehicle_reg_number, "vehicle_category": p.vehicle_category, "vehicle_color_model": p.vehicle_color_model, "owner_name": p.owner_name, "owner_phone": p.owner_phone, "parking_zone": p.parking_zone, "key_custody_mode": p.key_custody_mode, "key_tag_number": p.key_tag_number, "entry_owner_photo_b64": p.entry_owner_photo_b64, "entry_timestamp": p.entry_timestamp.isoformat(), "status": p.status, "exit_timestamp": p.exit_timestamp.isoformat() if p.exit_timestamp else None, "verified_exit_by": p.verified_exit_by} for p in q.order_by(DevoteeParkingPass.id.desc()).limit(100).all()]

@router.post("/parking-passes/checkin")
def checkin_devotee_parking(data: dict, db: Session = Depends(get_db)):
    token = f"PKG-{secrets.randbelow(9000)+1000}"
    pin = f"{secrets.randbelow(10000):04d}"
    p = DevoteeParkingPass(parking_token=token, vehicle_reg_number=str(data.get("vehicle_reg_number", "")).upper(), vehicle_category=data.get("vehicle_category", "Car"), vehicle_color_model=data.get("vehicle_color_model"), owner_name=data.get("owner_name", "Devotee"), owner_phone=data.get("owner_phone", ""), parking_zone=data.get("parking_zone", "Zone P1"), key_custody_mode=data.get("key_custody_mode", "WITH_OWNER"), key_tag_number=data.get("key_tag_number") or token, exit_pin_hash=generate_password_hash(pin), entry_owner_photo_b64=data.get("entry_owner_photo_b64"), checked_in_by=data.get("checked_in_by", "Gate Sevadar"))
    db.add(p)
    db.commit()
    return {"status": "PARKED", "parking_token": token, "vehicle_reg_number": p.vehicle_reg_number, "exit_pin": pin}

@router.post("/parking-passes/verify-exit")
def verify_devotee_parking_exit(data: dict, db: Session = Depends(get_db)):
    p = db.query(DevoteeParkingPass).filter(DevoteeParkingPass.id == data.get("pass_id")).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pass not found.")
    pin = str(data.get("exit_pin") or "").strip()
    phone = str(data.get("owner_phone_verify") or "").strip()
    if not ((pin and check_password_hash(p.exit_pin_hash, pin)) or (phone and phone == p.owner_phone)):
        raise HTTPException(status_code=403, detail="Wrong 4-Digit Exit PIN! Do NOT release vehicle.")
    p.status = "EXITED_VERIFIED"
    p.exit_timestamp = datetime.utcnow()
    p.verified_exit_by = data.get("verified_exit_by", "Exit Gate Marshall")
    db.commit()
    return {"status": "EXITED", "vehicle_reg_number": p.vehicle_reg_number, "parking_token": p.parking_token}

@router.post("/parking-passes/flag-hold")
def flag_parking_hold(data: dict, db: Session = Depends(get_db)):
    p = db.query(DevoteeParkingPass).filter(DevoteeParkingPass.id == data.get("pass_id")).first()
    if p:
        p.status = "SECURITY_HOLD"
        p.security_notes = data.get("reason", "Manual hold")
        db.commit()
    return {"status": "HOLD"}

@router.get("/parking-passes/cctv-events")
def list_cctv_events(limit: int = 8, db: Session = Depends(get_db)):
    return [{"id": e.id, "camera_id": e.camera_id, "gate_direction": e.gate_direction, "plate_number": e.plate_number, "action_taken": e.action_taken, "alert_level": e.alert_level, "detected_at": e.detected_at.isoformat()} for e in db.query(CCTVAnprEvent).order_by(CCTVAnprEvent.id.desc()).limit(limit).all()]

@router.get("/parking-passes/pending-walkins")
def list_pending_walkins(db: Session = Depends(get_db)):
    items = db.query(DevoteeParkingPass).filter(DevoteeParkingPass.status == "PARKED_INSIDE", DevoteeParkingPass.owner_phone == "PENDING_PHONE").order_by(DevoteeParkingPass.id.desc()).limit(5).all()
    return [{"id": p.id, "parking_token": p.parking_token, "vehicle_reg_number": p.vehicle_reg_number, "exit_pin": (p.security_notes or "").replace("WALKIN_PIN:", "")} for p in items]

@router.post("/parking-passes/complete-walkin")
def complete_walkin(data: dict, db: Session = Depends(get_db)):
    p = db.query(DevoteeParkingPass).filter(DevoteeParkingPass.id == data.get("pass_id")).first()
    if not p:
        raise HTTPException(status_code=404, detail="Walk-in pass not found.")
    p.owner_phone = str(data.get("owner_phone", "")).strip()
    p.security_notes = "WALKIN_VERIFIED"
    db.commit()
    return {"status": "ISSUED", "parking_token": p.parking_token, "vehicle_reg_number": p.vehicle_reg_number, "owner_phone": p.owner_phone}

@router.get("/rental-proformas")
def list_rental_proformas(db: Session = Depends(get_db)):
    return [{"id": p.id, "proforma_code": p.proforma_code, "proforma_date": p.proforma_date, "vendor_name": p.vendor_name, "duty_sector": p.duty_sector, "total_estimated_inr": p.total_estimated_inr, "status": p.status} for p in db.query(RentalHiringProforma).order_by(RentalHiringProforma.id.desc()).limit(50).all()]

@router.post("/rental-proformas")
def create_rental_proforma(data: dict, db: Session = Depends(get_db)):
    code = f"SNM-HIRE-{secrets.randbelow(9000)+1000}"
    db.add(RentalHiringProforma(proforma_code=code, proforma_date=str(data.get("proforma_date") or datetime.utcnow().strftime("%Y-%m-%d")), vendor_name=str(data.get("vendor_name") or ""), vendor_phone=str(data.get("vendor_phone") or ""), duty_sector=str(data.get("duty_sector") or ""), shortage_reason=str(data.get("shortage_reason") or ""), line_items_json=str(data.get("line_items_json") or "[]"), committee_members_json=str(data.get("committee_members_json") or "[]"), total_estimated_inr=float(data.get("total_estimated_inr") or 0.0)))
    db.commit()
    return {"status": "SAVED", "proforma_code": code}
""",

    "app/routers/operations.py": """import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import (
    Territory, Vehicle, StationDemand, FuelLog, MaintenanceTicket,
    Journey, CrewDutyShift, PickupDropVehicleRequest, DepartmentVehicleRequisition,
    SevaDonatedVehicle, GroundStationIntercom
)
from app.schemas import (
    StationDemandCreateRequest, VehicleAllocationScheduleRequest, FuelLogRequest,
    MaintenanceTicketRequest, JourneyStartRequest, JourneyEndRequest,
    CrewDutyStartRequest, CrewDutyEndRequest, OfflineBatchSyncRequest, OfflineBatchSyncResponse
)
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

@router.get("/pickup-drop-requests")
def list_pickup_drop_requests(db: Session = Depends(get_db)):
    return [{"id": r.id, "request_code": r.request_code, "trip_direction": r.trip_direction, "transit_hub": r.transit_hub, "passenger_count": r.passenger_count, "vehicle_type_requested": r.vehicle_type_requested, "vehicles_needed": r.vehicles_needed, "scheduled_datetime": r.scheduled_datetime, "requester_name": r.requester_name, "requester_phone": r.requester_phone, "status": r.status, "assigned_vehicle_reg": r.assigned_vehicle_reg} for r in db.query(PickupDropVehicleRequest).order_by(PickupDropVehicleRequest.id.desc()).limit(50).all()]

@router.post("/pickup-drop-requests")
def create_pickup_drop_request(data: dict, db: Session = Depends(get_db)):
    code = f"PND-{secrets.randbelow(9000) + 1000}"
    pax = int(data.get("passenger_count") or 1)
    hub = str(data.get("transit_hub") or "Panvel Junction (PNVL)")
    req_item = PickupDropVehicleRequest(
        request_code=code,
        trip_direction=str(data.get("trip_direction") or "PICKUP_TO_SAMAGAM"),
        transit_hub=hub,
        passenger_count=pax,
        vehicle_type_requested=str(data.get("vehicle_type_requested") or "Heavy Bus (50-Seater)"),
        vehicles_needed=int(data.get("vehicles_needed") or 1),
        scheduled_datetime=str(data.get("scheduled_datetime") or ""),
        train_flight_details=str(data.get("train_flight_details") or ""),
        requester_name=str(data.get("requester_name") or ""),
        requester_phone=str(data.get("requester_phone") or ""),
        notes=str(data.get("notes") or "")
    )
    db.add(req_item)
    mix = compute_optimal_bus_mix(pax)
    if db.query(Territory).filter(Territory.hub_name == hub).first():
        db.add(StationDemand(demand_code=code, hub_name=hub, waiting_passenger_count=pax, recommended_buses=mix["summary"], priority="HIGH", requested_by=f"{req_item.requester_name} ({req_item.requester_phone})", notes=req_item.notes))
    db.commit()
    return {"status": "SAVED", "request_code": code}

@router.get("/request-status-lookup")
def lookup_requester_vehicle_status(query: str, db: Session = Depends(get_db)):
    q = str(query or "").strip()
    if not q:
        return []
    results = []
    for r in db.query(PickupDropVehicleRequest).filter(or_(PickupDropVehicleRequest.requester_phone.ilike(f"%{q}%"), PickupDropVehicleRequest.request_code.ilike(f"%{q}%"))).order_by(PickupDropVehicleRequest.id.desc()).limit(10).all():
        veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == r.assigned_vehicle_reg).first() if r.assigned_vehicle_reg else None
        is_alloc = bool(r.assigned_vehicle_reg) or r.status == "VEHICLE_ALLOCATED"
        results.append({"code": r.request_code, "category": "Pickup / Drop Shuttle", "summary": f"{r.transit_hub} ({r.passenger_count} Pax)", "requester_name": r.requester_name, "requester_phone": r.requester_phone, "status": r.status, "is_allocated": is_alloc, "assigned_vehicle_reg": r.assigned_vehicle_reg or "", "driver_name": veh.driver_name if veh else "", "driver_phone": veh.driver_phone if veh else ""})
    for d in db.query(DepartmentVehicleRequisition).filter(or_(DepartmentVehicleRequisition.requester_phone.ilike(f"%{q}%"), DepartmentVehicleRequisition.requisition_code.ilike(f"%{q}%"))).order_by(DepartmentVehicleRequisition.id.desc()).limit(10).all():
        seva_v = db.query(SevaDonatedVehicle).filter(SevaDonatedVehicle.id == d.allocated_seva_vehicle_id).first() if d.allocated_seva_vehicle_id else None
        is_alloc = d.status == "ALLOCATED" and bool(d.allocated_vehicle_reg)
        results.append({"code": d.requisition_code, "category": f"In-Ground ({d.department_name})", "summary": f"{d.quantity_needed}x {d.required_vehicle_type}", "requester_name": d.requester_name, "requester_phone": d.requester_phone, "status": d.status, "is_allocated": is_alloc, "assigned_vehicle_reg": d.allocated_vehicle_reg or "", "driver_name": seva_v.handed_over_by_name if seva_v else (d.allocated_by_member or ""), "driver_phone": seva_v.owner_phone if seva_v else ""})
    return results

@router.post("/allocate-dispatch")
def allocate_dispatch(req: VehicleAllocationScheduleRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
    if req.demand_id:
        d = db.query(StationDemand).filter(StationDemand.id == req.demand_id).first()
        if d:
            d.status = "DISPATCHED"
            pd_req = db.query(PickupDropVehicleRequest).filter(PickupDropVehicleRequest.request_code == d.demand_code).first()
            if pd_req and veh:
                pd_req.status = "VEHICLE_ALLOCATED"
                pd_req.assigned_vehicle_reg = veh.vehicle_reg_number
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
def ingest_telemetry_ping(data: dict, db: Session = Depends(get_db)):
    items = data["pings"] if isinstance(data.get("pings"), list) else [data]
    items = sorted(items[:500], key=lambda p: float(p.get("recorded_at") or 0))
    last_res = {"status": "PING_RECORDED", "total_distance_km": 0.0}
    for p in items:
        reg = str(p.get("vehicle_reg_number") or "").upper().strip()
        veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first()
        if veh and p.get("latitude") is not None and p.get("longitude") is not None:
            last_res = process_live_telemetry_ping(db, veh, float(p["latitude"]), float(p["longitude"]), journey_id=p.get("journey_id"), speed_kmh=float(p.get("speed_kmh") or 0.0))
    return last_res

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
    s = CrewDutyShift(crew_role=req.crew_role, crew_name=req.crew_name, crew_phone=req.crew_phone, station_hub=req.station_hub, vehicle_reg_number=req.vehicle_reg_number)
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

@router.get("/intercom")
def get_intercom_messages(hub: str = "ALL_STATIONS", limit: int = 30, db: Session = Depends(get_db)):
    q = db.query(GroundStationIntercom)
    if hub and hub != "ALL_STATIONS":
        q = q.filter(or_(GroundStationIntercom.channel_hub == hub, GroundStationIntercom.channel_hub == "ALL_STATIONS"))
    items = q.order_by(GroundStationIntercom.id.desc()).limit(limit).all()
    return [{"id": m.id, "channel_hub": m.channel_hub, "sender_side": m.sender_side, "sender_name": m.sender_name, "priority": m.priority, "message_text": m.message_text, "is_acknowledged": m.is_acknowledged, "acknowledged_by": m.acknowledged_by or "", "created_at": m.created_at.isoformat()} for m in reversed(items)]

@router.post("/intercom")
def post_intercom_message(data: dict, db: Session = Depends(get_db)):
    msg = str(data.get("message_text") or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Intercom message cannot be empty.")
    entry = GroundStationIntercom(channel_hub=str(data.get("channel_hub") or "ALL_STATIONS"), sender_side=str(data.get("sender_side") or "GROUND_HQ"), sender_name=str(data.get("sender_name") or "Control Room"), priority=str(data.get("priority") or "NORMAL"), message_text=msg)
    db.add(entry)
    db.commit()
    return {"status": "SENT", "id": entry.id}

@router.post("/intercom/{msg_id}/ack")
def acknowledge_intercom_message(msg_id: int, data: dict = None, db: Session = Depends(get_db)):
    data = data or {}
    entry = db.query(GroundStationIntercom).filter(GroundStationIntercom.id == msg_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Message not found.")
    entry.is_acknowledged = True
    entry.acknowledged_by = str(data.get("acknowledged_by") or "Station Sevadar")
    db.commit()
    return {"status": "ACKNOWLEDGED"}
""",

    "app/routers/reports.py": """import csv
import io
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Saint, Vehicle, StationDemand, HiredRollingContract, MSRTCSpotCashVoucher, StationCashFloat, FuelLog, MaintenanceTicket, CrewDutyShift
from app.services.contract_service import compute_rolling_contract_metrics

router = APIRouter(prefix="/api/reports", tags=["Executive Analytics & Exports"])
IST = timezone(timedelta(hours=5, minutes=30))

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
        "financials_inr": {"msrtc_imprest_balance_inr": round(msrtc_float - msrtc_spent, 2), "fuel_expense_inr": round(fuel_spent, 2), "grand_total_transport_spend_inr": round(accrued + settled + msrtc_spent + fuel_spent + maint_spent, 2)},
        "crew": {"currently_on_duty": db.query(CrewDutyShift).filter(CrewDutyShift.is_currently_on_duty == True).count()}
    }

def build_duty_excel_bytes(db: Session) -> bytes:
    from openpyxl import Workbook
    shifts = db.query(CrewDutyShift).order_by(CrewDutyShift.duty_start_time.asc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Duty log"
    ws.append(["#", "Crew / Driver", "Role", "Mobile", "Hub", "Start (IST)", "End (IST)", "Hours", "Status"])
    for idx, s in enumerate(shifts, 1):
        end_dt = s.duty_end_time or datetime.utcnow()
        hrs = round(max(0.0, (end_dt - s.duty_start_time).total_seconds()) / 3600.0, 2)
        ws.append([idx, s.crew_name, s.crew_role, s.crew_phone, s.station_hub, str(s.duty_start_time), str(s.duty_end_time or ""), hrs, "On duty" if s.is_currently_on_duty else "Completed"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

@router.get("/export/shifts.xlsx")
def export_duty_shifts_xlsx(db: Session = Depends(get_db)):
    return StreamingResponse(io.BytesIO(build_duty_excel_bytes(db)), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=samagam_duty_log.xlsx"})

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
""",

    "in_ground_seva_vehicles.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>सेवा करण्यासाठी वाहन प्राप्ती व वाटप | In-Ground Seva Vehicles</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@500;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(180deg, #dff1fb 0%, #eef6fc 45%, #e2e8f0 100%);
            font-family: 'Inter', 'Noto Sans Devanagari', sans-serif;
            color: #0f172a;
        }
        .tab-pill.active {
            background-color: #0f2c59;
            color: #ffffff;
            box-shadow: 0 8px 20px rgba(15, 44, 89, 0.25);
        }
        .seva-form-card {
            background: rgba(255, 255, 255, 0.94);
            backdrop-filter: blur(10px);
            border: 1px solid #bae6fd;
            box-shadow: 0 20px 45px -15px rgba(14, 116, 144, 0.15);
        }
    </style>
</head>
<body class="min-h-screen pb-12">

    <header class="bg-[#0f2c59] text-white shadow-lg sticky top-0 z-40">
        <div class="max-w-6xl mx-auto px-4 py-3.5 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-sky-100 text-[#0f2c59] flex items-center justify-center font-extrabold text-lg shadow">🙏</div>
                <div>
                    <h1 class="font-extrabold text-base sm:text-lg tracking-wide">सेवा करण्यासाठी वाहन प्राप्ती व वाटप प्रणाली</h1>
                    <p class="text-xs text-sky-200">In-Ground Seva Vehicle Donation, Dept. Requisition & Ground Transport Allocation</p>
                </div>
            </div>
            <div class="flex items-center gap-2 text-xs font-bold">
                <a href="/" class="bg-sky-800 hover:bg-sky-700 px-3.5 py-2 rounded-xl">← Welcome Portal</a>
                <a href="/admin_dashboard.html" class="bg-[#f28b82] text-white px-3.5 py-2 rounded-xl">🏛️ Control Room</a>
            </div>
        </div>
    </header>

    <div class="max-w-5xl mx-auto px-4 pt-6">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 bg-white/80 p-2 rounded-2xl shadow-sm border border-sky-100 text-xs sm:text-sm font-bold">
            <button onclick="switchSevaTab('donate', this)" class="tab-pill active py-3 px-4 rounded-xl transition flex items-center justify-center gap-2">
                <span>🚘</span> 1. सेवा वाहन प्राप्ती फॉर्म (Donate Vehicle)
            </button>
            <button onclick="switchSevaTab('request', this)" class="tab-pill py-3 px-4 rounded-xl text-slate-700 hover:bg-sky-50 transition flex items-center justify-center gap-2">
                <span>📋</span> 2. Dept. Vehicle Requisition (Sign & Stamp)
            </button>
            <button onclick="switchSevaTab('allocate', this)" class="tab-pill py-3 px-4 rounded-xl text-slate-700 hover:bg-sky-50 transition flex items-center justify-center gap-2">
                <span>🔐</span> 3. Ground Transport Allocation
            </button>
        </div>
    </div>

    <main class="max-w-5xl mx-auto px-4 pt-6">
        <!-- TAB 1: DONATE VEHICLE FOR SEVA -->
        <section id="section-donate" class="max-w-2xl mx-auto">
            <div class="seva-form-card rounded-3xl p-6 sm:p-8 space-y-6">
                <div class="text-center border-b border-sky-100 pb-5 space-y-1.5">
                    <div class="inline-flex items-center justify-center px-5 py-2 rounded-full bg-sky-100 text-[#0f2c59] font-extrabold text-sm gap-2">
                        <span>🚘 🙏</span> <span>(सेवा)</span>
                    </div>
                    <h2 class="text-2xl font-extrabold text-[#0f2c59] pt-1">सेवा करण्यासाठी वाहन प्राप्ती फॉर्म</h2>
                    <p class="text-sm font-bold text-sky-800">धन निरंकार जी 🙏</p>
                </div>

                <form id="seva-donate-form" onsubmit="submitSevaVehicleDonation(event)" class="space-y-4 text-sm">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-sky-50/70 p-4 rounded-2xl border border-sky-100">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">📅 दिनांक (Date) *</label>
                            <input type="date" id="seva-date" name="handover_date" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">⏰ वेळ (Time) *</label>
                            <input type="time" id="seva-time" name="handover_time" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-sm">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">वाहन क्रमांक (Vehicle Reg. No) *</label>
                            <input type="text" name="vehicle_reg_number" required placeholder="MH-04-AB-1234" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 uppercase font-bold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">वाहन प्रकार (Vehicle Type) *</label>
                            <select name="vehicle_type" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                                <option value="Car / Sedan / SUV">Car / Sedan / SUV</option>
                                <option value="Bolero / Pickup / Camper">Bolero / Pickup</option>
                                <option value="Chhota Hathi / Tata Ace">Chhota Hathi / Tata Ace</option>
                                <option value="Tempo / Eicher Mini Truck">Tempo / Eicher</option>
                                <option value="Ambulance / Medical Van">Ambulance / Medical Van</option>
                                <option value="Two-Wheeler / E-Rickshaw">Two-Wheeler / E-Rickshaw</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">झोन आणि ब्रांच चे नाव (Zone & Branch) *</label>
                        <input type="text" name="zone_and_branch" required placeholder="उदा. झोन ३ - ठाणे / पनवेल ब्रांच" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">वाहन मालकाचे नाव (Owner Name) *</label>
                            <input type="text" name="owner_name" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">संपर्क क्रमांक (Contact No) *</label>
                            <input type="text" name="owner_phone" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">पासून दिनांक (From Date) *</label>
                            <input type="date" name="seva_from_date" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">पर्यंत दिनांक (Till Date) *</label>
                            <input type="date" name="seva_till_date" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">इंधन क्षमता (Fuel Level)</label>
                            <select name="fuel_level" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                                <option value="Full (100%)">Full Tank</option>
                                <option value="3/4 Tank">3/4 Tank</option>
                                <option value="Half Tank">Half Tank</option>
                                <option value="1/4 Tank">1/4 Tank</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">इंधन प्रकार (Fuel Type)</label>
                            <select name="fuel_type" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                                <option value="Diesel">Diesel</option>
                                <option value="Petrol">Petrol</option>
                                <option value="CNG">CNG</option>
                                <option value="Electric">Electric</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">किमी मीटर (Odometer) *</label>
                            <input type="number" name="odometer_km" required placeholder="45200" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">📸 वाहन फोटो अपलोड (Vehicle Photo)</label>
                        <input type="file" accept="image/*" onchange="previewImageFile(this, 'donation-photo-preview', 'donation-photo-b64')" class="w-full text-xs">
                        <input type="hidden" id="donation-photo-b64" name="vehicle_photo_b64">
                        <img id="donation-photo-preview" class="hidden mt-2 max-h-40 rounded-xl border mx-auto" alt="Preview">
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <input type="text" name="handed_over_by_name" required placeholder="वाहन सुपूर्द करणाऱ्याचे नाव *" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        <input type="text" name="received_by_sevadar_name" required placeholder="स्वीकारणाऱ्या सेवादाराचे नाव *" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>

                    <button type="submit" class="w-full bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold py-4 rounded-2xl text-base shadow-xl">
                        🙏 सेवा वाहन जमा करा (Submit Seva Vehicle)
                    </button>
                </form>
            </div>
        </section>

        <!-- TAB 2: DEPARTMENT VEHICLE REQUISITION -->
        <section id="section-request" class="hidden grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div class="lg:col-span-3 seva-form-card rounded-3xl p-6 space-y-4">
                <h2 class="text-xl font-extrabold text-[#0f2c59]">📋 Raise In-Ground Vehicle Requirement</h2>
                <form id="dept-req-form" onsubmit="submitDeptRequisition(event)" class="space-y-3.5 text-sm">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <select name="department_name" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="Langar & Ration Supply">🍲 Langar & Ration Supply</option>
                            <option value="Tent, Pandal & Material">⛺ Tent, Pandal & Material</option>
                            <option value="Sevadal Security & Traffic">🛡️ Sevadal Security & Traffic</option>
                            <option value="Medical & Dispensary">🏥 Medical & Dispensary</option>
                            <option value="Stage, Sound & Exhibition">🎙️ Stage, Sound & Exhibition</option>
                            <option value="Water & Sanitation">🚰 Water & Sanitation</option>
                        </select>
                        <select name="required_vehicle_type" required class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="Car / Sedan / SUV">Car / Sedan / SUV</option>
                            <option value="Bolero / Pickup / Camper">Bolero / Pickup</option>
                            <option value="Chhota Hathi / Tata Ace">Chhota Hathi / Tata Ace</option>
                            <option value="Tempo / Eicher Mini Truck">Tempo / Eicher</option>
                            <option value="Ambulance / Medical Van">Ambulance / Medical Van</option>
                            <option value="Two-Wheeler / E-Rickshaw">Two-Wheeler / E-Rickshaw</option>
                        </select>
                    </div>
                    <div class="grid grid-cols-3 gap-3">
                        <input type="number" name="quantity_needed" value="1" min="1" required placeholder="Qty" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        <input type="text" name="requester_name" required placeholder="Requester Name *" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        <input type="text" name="requester_phone" required placeholder="Mobile *" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="text" name="required_duration" required placeholder="Duty Duration (e.g. 23-26 Jan)" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                        <input type="text" name="department_head_name" required placeholder="Dept. Head Name *" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                    <textarea name="purpose_details" rows="2" required placeholder="Duty Purpose & Route Details *" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2"></textarea>
                    <div class="bg-amber-50 border-2 border-dashed border-amber-400 rounded-2xl p-3 space-y-1.5">
                        <label class="block text-xs font-extrabold text-amber-950">🖋️ Upload Dept. Head Approval Slip (Sign & Stamp) *</label>
                        <input type="file" accept="image/*" required onchange="previewImageFile(this, 'stamp-preview', 'stamp-b64')" class="w-full text-xs">
                        <input type="hidden" id="stamp-b64" name="approval_stamp_b64">
                        <img id="stamp-preview" class="hidden mt-2 max-h-36 rounded-xl border mx-auto" alt="Stamp">
                    </div>
                    <button type="submit" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-3.5 rounded-2xl text-sm shadow-lg">
                        📤 Submit Vehicle Requisition
                    </button>
                </form>
            </div>
            <div class="lg:col-span-2 seva-form-card rounded-3xl p-5 space-y-3">
                <div class="flex justify-between items-center">
                    <h3 class="font-extrabold text-sm text-[#0f2c59]">📌 Submitted Requisitions</h3>
                    <button onclick="loadSevaAndRequisitions()" class="text-xs font-bold text-sky-700">↻ Refresh</button>
                </div>
                <div id="public-requisitions-list" class="space-y-2.5 text-xs"></div>
            </div>
        </section>

        <!-- TAB 3: GROUND TRANSPORT MEMBER ALLOCATION -->
        <section id="section-allocate" class="space-y-6 hidden">
            <div id="ground-auth-gate" class="max-w-md mx-auto seva-form-card rounded-3xl p-6 space-y-4">
                <div class="text-center">
                    <span class="text-3xl">🔐</span>
                    <h2 class="text-lg font-extrabold text-[#0f2c59] mt-1">Transport Ground Member Login</h2>
                </div>
                <form onsubmit="authenticateGroundAllocator(event)" class="space-y-3 text-sm">
                    <input type="text" id="alloc-login-mobile" required placeholder="Registered Sevadar Mobile (e.g. 9820110001)" class="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5 font-bold">
                    <input type="text" id="alloc-login-passcode" required value="GND-2026" class="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5">
                    <div id="alloc-login-msg" class="text-xs text-rose-600 font-semibold"></div>
                    <button type="submit" class="w-full bg-[#0f2c59] text-white font-extrabold py-3 rounded-xl">Unlock Allocation Console</button>
                </form>
            </div>

            <div id="ground-allocator-workspace" class="hidden space-y-6">
                <div class="bg-[#0f2c59] text-white rounded-2xl p-4 flex justify-between items-center">
                    <div class="font-extrabold text-sm" id="allocator-identity">--</div>
                    <button onclick="logoutGroundAllocator()" class="text-xs bg-rose-600 px-3 py-1.5 rounded-lg font-bold">Sign Out</button>
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="seva-form-card rounded-3xl p-5 space-y-3">
                        <h3 class="font-extrabold text-base text-[#0f2c59]">1. Pending Dept. Requests</h3>
                        <div id="allocator-requests-list" class="space-y-3 text-xs"></div>
                    </div>
                    <div class="seva-form-card rounded-3xl p-5 space-y-3">
                        <h3 class="font-extrabold text-base text-emerald-900">2. Available Seva Donated Vehicles</h3>
                        <div id="allocator-vehicles-list" class="space-y-3 text-xs"></div>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <div id="img-lightbox" class="fixed inset-0 bg-slate-950/80 hidden items-center justify-center z-50 p-4" onclick="this.classList.add('hidden')">
        <div class="bg-white p-3 rounded-2xl max-w-lg w-full space-y-2" onclick="event.stopPropagation()">
            <div class="flex justify-between items-center"><span class="font-extrabold text-xs" id="lightbox-caption">Preview</span><button onclick="document.getElementById('img-lightbox').classList.add('hidden')">✕</button></div>
            <img id="lightbox-img" class="w-full max-h-[75vh] object-contain rounded-xl border" alt="Preview">
        </div>
    </div>

    <script>
        let donatedVehicles = [], deptRequisitions = [];
        let currentAllocator = JSON.parse(localStorage.getItem('ground_allocator_session') || 'null');

        window.addEventListener('DOMContentLoaded', () => {
            const now = new Date();
            document.getElementById('seva-date').value = now.toISOString().split('T')[0];
            document.getElementById('seva-time').value = now.toTimeString().slice(0, 5);
            if (currentAllocator) showAllocatorWorkspace();
            loadSevaAndRequisitions();
        });

        function switchSevaTab(tabName, btn) {
            ['donate', 'request', 'allocate'].forEach(t => document.getElementById('section-' + t).classList.add('hidden'));
            document.getElementById('section-' + tabName).classList.remove('hidden');
            document.querySelectorAll('.tab-pill').forEach(b => { b.classList.remove('active'); b.classList.add('text-slate-700'); });
            btn.classList.add('active'); btn.classList.remove('text-slate-700');
        }

        function previewImageFile(input, previewImgId, hiddenInputId) {
            const file = input.files && input.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const scale = Math.min(1, 900 / img.width);
                    canvas.width = img.width * scale; canvas.height = img.height * scale;
                    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
                    const b64 = canvas.toDataURL('image/jpeg', 0.78);
                    document.getElementById(hiddenInputId).value = b64;
                    const prev = document.getElementById(previewImgId);
                    prev.src = b64; prev.classList.remove('hidden');
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }

        function openLightbox(src, title) {
            if (!src) return;
            document.getElementById('lightbox-img').src = src;
            document.getElementById('lightbox-caption').textContent = title;
            document.getElementById('img-lightbox').classList.remove('hidden');
            document.getElementById('img-lightbox').classList.add('flex');
        }

        async function submitSevaVehicleDonation(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.odometer_km = parseFloat(payload.odometer_km);
            const res = await fetch('/api/fleet/seva-donations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (res.ok) {
                const data = await res.json();
                alert('धन निरंकार जी 🙏 Receipt No: ' + data.receipt_code);
                e.target.reset(); document.getElementById('donation-photo-preview').classList.add('hidden');
                loadSevaAndRequisitions();
            }
        }

        async function submitDeptRequisition(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.quantity_needed = parseInt(payload.quantity_needed);
            const res = await fetch('/api/fleet/dept-requisitions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (res.ok) {
                const data = await res.json();
                alert('✅ Requisition Submitted! Code: ' + data.requisition_code);
                e.target.reset(); document.getElementById('stamp-preview').classList.add('hidden');
                loadSevaAndRequisitions();
            }
        }

        async function loadSevaAndRequisitions() {
            const [dRes, rRes] = await Promise.all([fetch('/api/fleet/seva-donations'), fetch('/api/fleet/dept-requisitions')]);
            donatedVehicles = dRes.ok ? await dRes.json() : [];
            deptRequisitions = rRes.ok ? await rRes.json() : [];
            const availablePool = donatedVehicles.filter(v => v.status === 'AVAILABLE_AT_GROUND');

            document.getElementById('public-requisitions-list').innerHTML = deptRequisitions.map(r => `
                <div class="p-3 bg-white rounded-2xl border border-slate-200">
                    <div class="flex justify-between font-bold"><span>${r.requisition_code} • ${r.department_name}</span><span>${r.status}</span></div>
                    <div>${r.quantity_needed}x ${r.required_vehicle_type} ${r.allocated_vehicle_reg ? '→ ✅ ' + r.allocated_vehicle_reg : ''}</div>
                </div>
            `).join('') || '<p class="text-slate-500">No requisitions yet.</p>';

            document.getElementById('allocator-requests-list').innerHTML = deptRequisitions.map(r => `
                <div class="p-3 bg-white rounded-2xl border space-y-2">
                    <div class="flex justify-between">
                        <div><strong>${r.requisition_code} — ${r.department_name}</strong><div>${r.quantity_needed}x ${r.required_vehicle_type}</div></div>
                        ${r.approval_stamp_b64 ? `<button onclick="openLightbox('${r.approval_stamp_b64}', '${r.requisition_code} Stamp')" class="bg-amber-100 px-2.5 py-1 rounded-lg font-bold">🖋️ Stamp</button>` : ''}
                    </div>
                    ${r.status !== 'ALLOCATED' ? `
                        <div class="flex gap-2">
                            <select id="pick-veh-${r.id}" class="flex-1 border rounded-xl px-2 py-1.5 font-bold">
                                ${availablePool.map(v => `<option value="${v.id}">${v.vehicle_reg_number} (${v.vehicle_type})</option>`).join('') || '<option value="">No Seva vehicles</option>'}
                            </select>
                            <button onclick="allocateVehicleToDept(${r.id})" class="bg-emerald-700 text-white font-bold px-3 py-1.5 rounded-xl">Allocate</button>
                        </div>` : `<div class="text-emerald-700 font-bold">✅ Allocated ${r.allocated_vehicle_reg}</div>`}
                </div>
            `).join('') || '<p class="text-slate-500">No pending requests.</p>';

            document.getElementById('allocator-vehicles-list').innerHTML = donatedVehicles.map(v => `
                <div class="p-3 bg-white rounded-2xl border flex justify-between items-center">
                    <div><strong>${v.vehicle_reg_number}</strong> • ${v.vehicle_type}<div class="text-slate-500">${v.owner_name} (${v.owner_phone})</div></div>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">${v.status}</span>
                </div>
            `).join('') || '<p class="text-slate-500">No Seva vehicles donated yet.</p>';
        }

        async function authenticateGroundAllocator(e) {
            e.preventDefault();
            const res = await fetch('/api/fleet/ground-allocator-login', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mobile_number: document.getElementById('alloc-login-mobile').value.trim(), passcode: document.getElementById('alloc-login-passcode').value.trim() })
            });
            const data = await res.json();
            if (res.ok) { currentAllocator = data.member; localStorage.setItem('ground_allocator_session', JSON.stringify(currentAllocator)); showAllocatorWorkspace(); }
            else { document.getElementById('alloc-login-msg').textContent = data.detail || 'Invalid passcode'; }
        }
        function showAllocatorWorkspace() { document.getElementById('ground-auth-gate').classList.add('hidden'); document.getElementById('ground-allocator-workspace').classList.remove('hidden'); document.getElementById('allocator-identity').textContent = `${currentAllocator.full_name} (${currentAllocator.mobile_number})`; }
        function logoutGroundAllocator() { localStorage.removeItem('ground_allocator_session'); currentAllocator = null; document.getElementById('ground-allocator-workspace').classList.add('hidden'); document.getElementById('ground-auth-gate').classList.remove('hidden'); }
        async function allocateVehicleToDept(reqId) {
            const vehId = parseInt(document.getElementById('pick-veh-' + reqId)?.value);
            if (!vehId) return;
            await fetch('/api/fleet/dept-requisitions/allocate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ requisition_id: reqId, seva_vehicle_id: vehId, allocated_by_member: currentAllocator?.full_name || 'Ground Team' }) });
            loadSevaAndRequisitions();
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
    