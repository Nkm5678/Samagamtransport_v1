from typing import Optional, List, Dict, Any
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
