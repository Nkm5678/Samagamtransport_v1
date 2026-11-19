from datetime import datetime
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

class StationCashFloat(Base):
    __tablename__ = "station_cash_floats"
    id = Column(Integer, primary_key=True, index=True)
    station_hub = Column(String(100), nullable=False, index=True)
    treasury_disbursed_amount_inr = Column(Float, nullable=False)
    issued_by = Column(String(100), default="Central Treasury Lead")
    issued_to_coordinator = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Volunteer(Base):
    __tablename__ = "volunteers"
    id = Column(Integer, primary_key=True, index=True)
    volunteer_code = Column(String(30), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    mobile_number = Column(String(20), unique=True, nullable=False)
    unit_number = Column(String(50), nullable=False)
    branch_name = Column(String(100), nullable=False)
    duty_location = Column(String(100), nullable=False)
    system_role = Column(String(30), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geofence_verified = Column(Boolean, default=False)
    can_view_all_territories = Column(Boolean, default=False)
    can_execute_ground_tasks = Column(Boolean, default=False)
    can_execute_station_tasks = Column(Boolean, default=False)
    can_manage_fleet = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)

class Saint(Base):
    __tablename__ = "saints"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    spiritual_order = Column(String(150), nullable=True)
    contact_phone = Column(String(20), nullable=False)
    contact_email = Column(String(120), nullable=True)
    group_size = Column(Integer, default=1)
    arrival_mode = Column(String(20), default="Train")
    arrival_hub = Column(String(100), nullable=False)
    arrival_transit_number = Column(String(100), nullable=True)
    arrival_pnr_ticket = Column(String(50), nullable=True)
    arrival_datetime = Column(String(50), nullable=False)
    departure_mode = Column(String(20), default="Train")
    departure_hub = Column(String(100), nullable=False)
    departure_datetime = Column(String(50), nullable=False)
    assigned_ground = Column(String(50), default="Ground 1 (Main Hall)")
    assigned_tent = Column(String(50), default="Tent A-01")
    special_assistance_notes = Column(Text, nullable=True)
    status = Column(String(50), default="Registered")
    return_vehicle_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_reg_number = Column(String(30), unique=True, nullable=False)
    vehicle_type = Column(String(50), nullable=False)
    capacity = Column(Integer, nullable=False)
    ownership_type = Column(String(30), default="TRUST_OWNED")
    contractor_name = Column(String(100), nullable=True)
    fixed_daily_rate_inr = Column(Float, default=0.0)
    is_rolling_contract = Column(Boolean, default=False)
    active_contract_id = Column(Integer, nullable=True)
    driver_name = Column(String(100), nullable=False)
    driver_phone = Column(String(20), nullable=False)
    current_hub = Column(String(100), nullable=False)
    assigned_territory = Column(String(100), nullable=False)
    status = Column(String(50), default="EMPTY_IN")
    current_passengers = Column(Integer, default=0)
    current_destination = Column(String(150), nullable=True)
    health_score_pct = Column(Float, default=100.0)
    is_maintenance_flagged = Column(Boolean, default=False)
    maintenance_reason = Column(Text, nullable=True)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    current_speed_kmh = Column(Float, default=0.0)
    is_live_tracking = Column(Boolean, default=False)
    active_journey_id = Column(Integer, nullable=True)

class HiredRollingContract(Base):
    __tablename__ = "hired_rolling_contracts"
    id = Column(Integer, primary_key=True, index=True)
    contract_code = Column(String(50), unique=True, nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    vendor_agency_name = Column(String(100), nullable=False)
    daily_base_rate_inr = Column(Float, default=7500.0)
    daily_quota_km = Column(Float, default=300.0)
    extra_rate_per_km_inr = Column(Float, default=25.0)
    entry_timestamp = Column(DateTime, default=datetime.utcnow)
    entry_odometer_km = Column(Float, nullable=False)
    exit_timestamp = Column(DateTime, nullable=True)
    exit_odometer_km = Column(Float, nullable=True)
    status = Column(String(30), default="ACTIVE_ROLLING")
    total_settlement_inr = Column(Float, default=0.0)
    settlement_voucher_no = Column(String(50), nullable=True)
    vehicle = relationship("Vehicle")

class MSRTCSpotCashVoucher(Base):
    __tablename__ = "msrtc_spot_cash_vouchers"
    id = Column(Integer, primary_key=True, index=True)
    voucher_number = Column(String(50), unique=True, nullable=False)
    station_hub = Column(String(100), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    msrtc_depot_name = Column(String(100), nullable=False)
    conductor_name = Column(String(100), nullable=False)
    conductor_buckle_no = Column(String(50), nullable=True)
    cash_amount_paid_inr = Column(Float, nullable=False)
    etm_receipt_number = Column(String(100), nullable=False)
    passenger_headcount = Column(Integer, nullable=False)
    paid_by_volunteer_name = Column(String(100), nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)
    is_verified_at_gate = Column(Boolean, default=False)
    verified_by_ground_sevadar = Column(String(100), nullable=True)
    vehicle = relationship("Vehicle")

class StationDemand(Base):
    __tablename__ = "station_demands"
    id = Column(Integer, primary_key=True, index=True)
    demand_code = Column(String(50), unique=True, nullable=False)
    hub_name = Column(String(100), nullable=False)
    waiting_passenger_count = Column(Integer, nullable=False)
    recommended_buses = Column(String(255), nullable=True)
    priority = Column(String(20), default="NORMAL")
    status = Column(String(30), default="PENDING")
    requested_by = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)

class Journey(Base):
    __tablename__ = "journeys"
    id = Column(Integer, primary_key=True, index=True)
    journey_code = Column(String(50), unique=True, nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    origin_name = Column(String(100), nullable=False)
    destination_name = Column(String(100), nullable=False)
    passenger_count = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    journey_status = Column(String(50), default="ACTIVE_IN_TRANSIT")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    vehicle = relationship("Vehicle")

class CrewDutyShift(Base):
    __tablename__ = "crew_duty_shifts"
    id = Column(Integer, primary_key=True, index=True)
    crew_role = Column(String(30), nullable=False)
    crew_name = Column(String(100), nullable=False)
    crew_phone = Column(String(20), nullable=False)
    station_hub = Column(String(100), nullable=False)
    duty_start_time = Column(DateTime, default=datetime.utcnow)
    duty_end_time = Column(DateTime, nullable=True)
    total_duty_hours = Column(Float, default=0.0)
    is_currently_on_duty = Column(Boolean, default=True)
    off_duty_reason = Column(String(100), nullable=True)

class FuelLog(Base):
    __tablename__ = "fuel_logs"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, nullable=False)
    liters_filled = Column(Float, nullable=False)
    rate_per_liter = Column(Float, nullable=False)
    total_cost_inr = Column(Float, nullable=False)
    filled_by = Column(String(100), nullable=False)

class MaintenanceTicket(Base):
    __tablename__ = "maintenance_tickets"
    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String(50), nullable=False)
    vehicle_id = Column(Integer, nullable=False)
    issue_category = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    description = Column(Text, nullable=False)
    reported_by = Column(String(100), nullable=False)
    repair_cost_inr = Column(Float, default=0.0)
