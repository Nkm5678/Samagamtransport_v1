from datetime import datetime, timedelta
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
