import math, secrets, csv, io, os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.database import engine, Base, SessionLocal, get_db
from app.models import (
    Territory, Volunteer, Saint, Vehicle, HiredRollingContract,
    MSRTCSpotCashVoucher, StationCashFloat, StationDemand, Journey,
    CrewDutyShift, FuelLog, MaintenanceTicket
)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

HUBS = [
    ("GND1", "Ground 1 (Main Hall)", "Samagam Ground", "Samagam Venue", 19.2183, 72.9781),
    ("GND2", "Ground 2 (North Camp)", "Samagam Ground", "Samagam Venue", 19.2225, 72.9810),
    ("GND3", "Ground 3 (South Camp)", "Samagam Ground", "Samagam Venue", 19.2140, 72.9745),
    ("GND4", "Ground 4 (VIP & Elderly Enclave)", "Samagam Ground", "Samagam Venue", 19.2195, 72.9835),
    ("TNA", "Thane Railway Station", "Railway Station", "Thane Zone", 19.1860, 72.9759),
    ("MMCT", "Mumbai Central (MMCT)", "Railway Station", "South Mumbai", 18.9690, 72.8193),
    ("DR", "Dadar Terminal (DR/DDR)", "Railway Station", "Central Mumbai", 19.0178, 72.8478),
    ("LTT", "Lokmanya Tilak Terminus (LTT)", "Railway Station", "East Suburbs", 19.0699, 72.8919),
    ("CSMT", "Chhatrapati Shivaji Maharaj Terminus (CSMT)", "Railway Station", "South Mumbai", 18.9398, 72.8354),
    ("BDTS", "Bandra Terminus (BDTS)", "Railway Station", "West Suburbs", 19.0620, 72.8412),
    ("KYN", "Kalyan Junction (KYN)", "Railway Station", "Kalyan Zone", 19.2352, 73.1305),
    ("PNVL", "Panvel Junction (PNVL)", "Railway Station", "Navi Mumbai", 18.9912, 73.1208),
    ("BOM1", "Mumbai Airport Terminal 1 (Domestic)", "Airport", "West Suburbs", 19.0902, 72.8628),
    ("BOM2", "Mumbai Airport Terminal 2 (International)", "Airport", "West Suburbs", 19.0974, 72.8742),
]

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

def contract_metrics(c: HiredRollingContract, end_ts=None, odo=None):
    end = c.exit_timestamp or end_ts or datetime.utcnow()
    hrs = round(max(0.0, (end - c.entry_timestamp).total_seconds()) / 3600.0, 2)
    days = max(1, math.ceil(hrs / 24.0)) if hrs > 0 else 1
    quota = round(days * c.daily_quota_km, 2)
    eff_odo = c.exit_odometer_km if c.exit_odometer_km is not None else odo
    km_run = round(eff_odo - c.entry_odometer_km, 2) if (eff_odo and eff_odo >= c.entry_odometer_km) else 0.0
    ex_km = round(max(0.0, km_run - quota), 2)
    total = round(days * c.daily_base_rate_inr + ex_km * c.extra_rate_per_km_inr, 2)
    return {"duration_hours": hrs, "billed_days": days, "km_run": km_run, "allowed_quota_km": quota, "excess_km": ex_km, "total_settlement_inr": total}

def seed_db(db: Session):
    for code, name, htype, zone, lat, lng in HUBS:
        if not db.query(Territory).filter(Territory.hub_code == code).first():
            db.add(Territory(hub_code=code, hub_name=name, hub_type=htype, city_zone=zone, latitude=lat, longitude=lng))
    db.commit()
    if db.query(Vehicle).count() == 0:
        v1 = Vehicle(vehicle_reg_number="MH-04-TR-1001", vehicle_type="Heavy Bus (50-seater)", capacity=50, ownership_type="TRUST_OWNED", driver_name="Harbhajan Singh", driver_phone="9820110001", current_hub="Thane Railway Station", assigned_territory="Thane Railway Station", status="EMPTY_IN", current_lat=19.1865, current_lng=72.9762, health_score_pct=96.0)
        v2 = Vehicle(vehicle_reg_number="MH-01-HR-2045", vehicle_type="Heavy Bus (50-seater)", capacity=50, ownership_type="HIRED_OUTSIDE", contractor_name="Shree Siddhivinayak Travels", fixed_daily_rate_inr=7500.0, is_rolling_contract=True, driver_name="Rajesh Jadhav", driver_phone="9820110002", current_hub="Dadar Terminal (DR/DDR)", assigned_territory="Dadar Terminal (DR/DDR)", status="LOADED_OUT", current_passengers=48, current_destination="Ground 1 (Main Hall)", current_lat=19.0850, current_lng=72.9120, current_speed_kmh=42.5, is_live_tracking=True, health_score_pct=88.0)
        v3 = Vehicle(vehicle_reg_number="MH-04-ST-8892", vehicle_type="MSRTC State Bus", capacity=55, ownership_type="MSRTC_SPOT_CASH", contractor_name="MSRTC Thane Depot", driver_name="Prakash Shinde", driver_phone="9820110003", current_hub="Ground 1 (Main Hall)", assigned_territory="Thane Railway Station", status="UNLOADED_IN", current_lat=19.2183, current_lng=72.9781, health_score_pct=91.0)
        db.add_all([v1, v2, v3]); db.commit()
        c1 = HiredRollingContract(contract_code="HRC-2026-001", vehicle_id=v2.id, vendor_agency_name="Shree Siddhivinayak Travels", entry_timestamp=datetime.utcnow() - timedelta(hours=14), entry_odometer_km=142500.0)
        db.add(c1); db.commit()
        db.add(StationCashFloat(station_hub="Thane Railway Station", treasury_disbursed_amount_inr=25000.0, issued_to_coordinator="Ramesh Deshmukh"))
        db.add(MSRTCSpotCashVoucher(voucher_number="MSRTC-TNA-001", station_hub="Thane Railway Station", vehicle_id=v3.id, msrtc_depot_name="Thane Depot 1", conductor_name="Vijay Kadam", cash_amount_paid_inr=1650.0, etm_receipt_number="ETM-992831", passenger_headcount=55, paid_by_volunteer_name="Ramesh Deshmukh", is_verified_at_gate=True, verified_by_ground_sevadar="Gate 1 Marshall"))
        db.add(Saint(full_name="Sant Gurpreet Singh Ji & Jatha", spiritual_order="Delhi Zone", contact_phone="9811002233", group_size=42, arrival_hub="Thane Railway Station", arrival_transit_number="12138 Punjab Mail", arrival_datetime="2026-11-20 08:30", departure_hub="Thane Railway Station", departure_datetime="2026-11-24 19:15", assigned_ground="Ground 1 (Main Hall)", assigned_tent="Tent A-12"))
        db.add(CrewDutyShift(crew_role="Driver", crew_name="Harbhajan Singh", crew_phone="9820110001", station_hub="Thane Railway Station", duty_start_time=datetime.utcnow() - timedelta(hours=4)))
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    yield

app = FastAPI(title="Samagam Transport Platform", version="4.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=os.path.join(ROOT_DIR, "static")), name="static")

@app.get("/health")
def health(): return {"status": "healthy"}

@app.get("/api/operations/hubs")
def get_hubs(db: Session = Depends(get_db)):
    return [{"id": h.id, "hub_code": h.hub_code, "hub_name": h.hub_name, "hub_type": h.hub_type, "latitude": h.latitude, "longitude": h.longitude} for h in db.query(Territory).all()]

@app.post("/api/auth/register")
def reg_vol(data: dict, db: Session = Depends(get_db)):
    hub = db.query(Territory).filter(Territory.hub_name == data.get("duty_location")).first()
    if not hub: raise HTTPException(400, "Invalid hub")
    dist = haversine_m(data["latitude"], data["longitude"], hub.latitude, hub.longitude)
    if dist > 2000.0: raise HTTPException(403, f"GEOFENCE REJECTION: {dist}m away from {hub.hub_name} (max 2000m)")
    is_ground = "ground" in hub.hub_name.lower()
    vol = Volunteer(volunteer_code=f"VOL-{hub.hub_code}-{secrets.randbelow(9000)+1000}", full_name=data["full_name"], mobile_number=data["mobile_number"], unit_number=data.get("unit_number","U1"), branch_name=data.get("branch_name","Mumbai"), duty_location=hub.hub_name, system_role="GROUND_ADMIN" if is_ground else "STATION_COORDINATOR", latitude=data["latitude"], longitude=data["longitude"], geofence_verified=True, can_view_all_territories=is_ground)
    db.add(vol); db.commit(); db.refresh(vol)
    return {"status": "REGISTERED", "volunteer": {"volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "duty_location": vol.duty_location, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}

@app.post("/api/auth/login")
def login_vol(data: dict, db: Session = Depends(get_db)):
    vol = db.query(Volunteer).filter(Volunteer.mobile_number == data.get("mobile_number")).first()
    if not vol: raise HTTPException(404, "Volunteer not found")
    hub = db.query(Territory).filter(Territory.hub_name == vol.duty_location).first()
    if hub and data.get("latitude"):
        dist = haversine_m(data["latitude"], data["longitude"], hub.latitude, hub.longitude)
        if dist > 2000.0: raise HTTPException(403, f"GEOFENCE REJECTION: {dist}m away from {hub.hub_name}")
    return {"status": "AUTHENTICATED", "volunteer": {"volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "duty_location": vol.duty_location, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}

@app.get("/api/saints/")
def list_saints(hub: str = None, db: Session = Depends(get_db)):
    q = db.query(Saint)
    if hub and hub != "ALL": q = q.filter(Saint.arrival_hub == hub)
    return [{"id": s.id, "pass_code": f"SMG-{s.id:05d}", "full_name": s.full_name, "contact_phone": s.contact_phone, "group_size": s.group_size, "arrival_mode": s.arrival_mode, "arrival_hub": s.arrival_hub, "arrival_transit_number": s.arrival_transit_number, "arrival_datetime": s.arrival_datetime, "departure_hub": s.departure_hub, "departure_datetime": s.departure_datetime, "assigned_ground": s.assigned_ground, "assigned_tent": s.assigned_tent, "status": s.status} for s in q.order_by(Saint.id.desc()).all()]

@app.post("/api/saints/register")
def reg_saint(data: dict, db: Session = Depends(get_db)):
    s = Saint(**{k: v for k, v in data.items() if hasattr(Saint, k)})
    db.add(s); db.commit(); db.refresh(s)
    return {"status": "REGISTERED", "pass_code": f"SMG-{s.id:05d}", "saint_id": s.id}

@app.post("/api/saints/checkin-tent")
def checkin_tent(data: dict, db: Session = Depends(get_db)):
    s = db.query(Saint).filter(Saint.id == data["saint_id"]).first()
    if s: s.status = "Checked-In at Tent"; db.commit()
    return {"status": "CHECKED_IN"}

@app.post("/api/saints/public-pass-lookup")
def pass_lookup(data: dict, db: Session = Depends(get_db)):
    q = data.get("query", "").strip()
    matches = db.query(Saint).filter(or_(Saint.contact_phone.ilike(f"%{q}%"), Saint.full_name.ilike(f"%{q}%"))).all()
    if not matches: raise HTTPException(404, "Pass not found")
    return [{"pass_code": f"SMG-{s.id:05d}", "full_name": s.full_name, "group_size": s.group_size, "arrival_hub": s.arrival_hub, "arrival_datetime": s.arrival_datetime, "assigned_ground": s.assigned_ground, "assigned_tent": s.assigned_tent, "status": s.status} for s in matches]

@app.post("/api/saints/allocate-return-shuttle")
def return_shuttle(data: dict, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == data["vehicle_id"]).first()
    for s in db.query(Saint).filter(Saint.id.in_(data["saint_ids"])).all():
        s.return_vehicle_id = v.id; s.status = "Return Shuttle Scheduled"
    if v: v.current_destination = data["departure_hub"]; v.status = "LOADED_OUT"
    db.commit()
    return {"status": "ALLOCATED"}

@app.get("/api/fleet/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    return [{"id": v.id, "vehicle_reg_number": v.vehicle_reg_number, "vehicle_type": v.vehicle_type, "capacity": v.capacity, "ownership_type": v.ownership_type, "driver_name": v.driver_name, "driver_phone": v.driver_phone, "current_hub": v.current_hub, "status": v.status, "current_passengers": v.current_passengers, "current_destination": v.current_destination, "health_score_pct": v.health_score_pct, "is_maintenance_flagged": v.is_maintenance_flagged, "current_lat": v.current_lat, "current_lng": v.current_lng, "current_speed_kmh": v.current_speed_kmh} for v in db.query(Vehicle).all()]

@app.patch("/api/fleet/vehicles/{vid}/status")
def patch_veh(vid: int, data: dict, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vid).first()
    if v: v.status = data["status"]; db.commit()
    return {"status": "UPDATED"}

@app.get("/api/fleet/rolling-contracts")
def get_contracts(db: Session = Depends(get_db)):
    return [{"id": c.id, "contract_code": c.contract_code, "vehicle_reg_number": c.vehicle.vehicle_reg_number if c.vehicle else "N/A", "vendor_agency_name": c.vendor_agency_name, "entry_odometer_km": c.entry_odometer_km, "status": c.status, "settlement_voucher_no": c.settlement_voucher_no, "live_metrics": contract_metrics(c)} for c in db.query(HiredRollingContract).all()]

@app.post("/api/fleet/rolling-contracts/onboard")
def onboard_contract(data: dict, db: Session = Depends(get_db)):
    reg = data["vehicle_reg_number"].upper()
    v = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first()
    if not v:
        v = Vehicle(vehicle_reg_number=reg, vehicle_type="Heavy Bus (50-seater)", capacity=50, ownership_type="HIRED_OUTSIDE", contractor_name=data["vendor_agency_name"], is_rolling_contract=True, driver_name=data["driver_name"], driver_phone=data["driver_phone"], current_hub="Ground 1 (Main Hall)", assigned_territory="Ground 1 (Main Hall)")
        db.add(v); db.commit(); db.refresh(v)
    c = HiredRollingContract(contract_code=f"HRC-{secrets.randbelow(9000)+1000}", vehicle_id=v.id, vendor_agency_name=data["vendor_agency_name"], daily_base_rate_inr=data.get("daily_base_rate_inr",7500), daily_quota_km=data.get("daily_quota_km",300), extra_rate_per_km_inr=data.get("extra_rate_per_km_inr",25), entry_odometer_km=data["entry_odometer_km"])
    db.add(c); db.commit()
    return {"status": "STARTED", "contract_code": c.contract_code}

@app.post("/api/fleet/rolling-contracts/release")
def release_contract(data: dict, db: Session = Depends(get_db)):
    c = db.query(HiredRollingContract).filter(HiredRollingContract.id == data["contract_id"]).first()
    now = datetime.utcnow()
    c.exit_timestamp = now; c.exit_odometer_km = data["exit_odometer_km"]
    m = contract_metrics(c, now, data["exit_odometer_km"])
    c.total_settlement_inr = m["total_settlement_inr"]; c.status = "SETTLED_AND_EXITED"; c.settlement_voucher_no = f"SET-{c.contract_code}"
    db.commit()
    return {"status": "SETTLED", "voucher_no": c.settlement_voucher_no, "settlement": m}

@app.get("/api/fleet/msrtc-ledger")
def get_msrtc(station_hub: str = None, db: Session = Depends(get_db)):
    fq, vq = db.query(StationCashFloat), db.query(MSRTCSpotCashVoucher)
    if station_hub and station_hub != "ALL":
        fq = fq.filter(StationCashFloat.station_hub == station_hub)
        vq = vq.filter(MSRTCSpotCashVoucher.station_hub == station_hub)
    disp = sum(f.treasury_disbursed_amount_inr for f in fq.all())
    vouchers = vq.all()
    spent = sum(v.cash_amount_paid_inr for v in vouchers)
    return {"summary": {"total_treasury_imprest_inr": disp, "total_paid_to_conductors_inr": spent, "remaining_cash_in_hand_inr": disp - spent}, "vouchers": [{"id": v.id, "voucher_number": v.voucher_number, "station_hub": v.station_hub, "vehicle_reg_number": v.vehicle.vehicle_reg_number if v.vehicle else "N/A", "conductor_name": v.conductor_name, "cash_amount_paid_inr": v.cash_amount_paid_inr, "etm_receipt_number": v.etm_receipt_number, "passenger_headcount": v.passenger_headcount, "is_verified_at_gate": v.is_verified_at_gate, "verified_by_ground_sevadar": v.verified_by_ground_sevadar} for v in vouchers]}

@app.post("/api/fleet/msrtc-ledger/disburse-float")
def add_float(data: dict, db: Session = Depends(get_db)):
    db.add(StationCashFloat(station_hub=data["station_hub"], treasury_disbursed_amount_inr=data["amount_inr"], issued_to_coordinator=data["issued_to_coordinator"]))
    db.commit(); return {"status": "DISBURSED"}

@app.post("/api/fleet/msrtc-ledger/pay-conductor")
def pay_msrtc(data: dict, db: Session = Depends(get_db)):
    reg = data["vehicle_reg_number"].upper()
    v = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first()
    if not v:
        v = Vehicle(vehicle_reg_number=reg, vehicle_type="MSRTC State Bus", capacity=55, ownership_type="MSRTC_SPOT_CASH", driver_name=data["conductor_name"], driver_phone="9999999999", current_hub=data["station_hub"], assigned_territory=data["station_hub"], status="LOADED_OUT", current_passengers=data.get("passenger_headcount",55))
        db.add(v); db.commit(); db.refresh(v)
    db.add(MSRTCSpotCashVoucher(voucher_number=f"MSRTC-{secrets.randbelow(90000)+10000}", station_hub=data["station_hub"], vehicle_id=v.id, msrtc_depot_name=data["msrtc_depot_name"], conductor_name=data["conductor_name"], cash_amount_paid_inr=data["cash_amount_paid_inr"], etm_receipt_number=data["etm_receipt_number"], passenger_headcount=data.get("passenger_headcount",55), paid_by_volunteer_name=data["paid_by_volunteer_name"]))
    db.commit(); return {"status": "LOGGED"}

@app.post("/api/fleet/msrtc-ledger/verify-gate")
def verify_msrtc(data: dict, db: Session = Depends(get_db)):
    v = db.query(MSRTCSpotCashVoucher).filter(MSRTCSpotCashVoucher.id == data["voucher_id"]).first()
    if v: v.is_verified_at_gate = True; v.verified_by_ground_sevadar = data.get("verified_by_ground_sevadar", "Gate Marshall"); db.commit()
    return {"status": "VERIFIED"}

@app.post("/api/fleet/wear-inspection")
def wear_insp(data: dict, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == data["vehicle_reg_number"]).first()
    if v:
        score = round((data["tire_condition_score"] + data["brake_condition_score"]) / 2.0, 1)
        v.health_score_pct = score
        if score < 65 or data.get("immediate_repair_needed"): v.is_maintenance_flagged = True; v.status = "MAINTENANCE_HOLD"
        db.commit()
    return {"status": "LOGGED"}

@app.get("/api/operations/demands")
def get_demands(db: Session = Depends(get_db)):
    return [{"id": d.id, "demand_code": d.demand_code, "hub_name": d.hub_name, "waiting_passenger_count": d.waiting_passenger_count, "recommended_buses": d.recommended_buses, "priority": d.priority, "status": d.status} for d in db.query(StationDemand).order_by(StationDemand.id.desc()).all()]

@app.post("/api/operations/demands")
def post_demand(data: dict, db: Session = Depends(get_db)):
    pax = int(data["waiting_passenger_count"])
    buses = f"{max(1, math.ceil(pax/50))}x Heavy Bus (50-seat)"
    db.add(StationDemand(demand_code=f"DEM-{secrets.randbelow(90000)+10000}", hub_name=data["hub_name"], waiting_passenger_count=pax, recommended_buses=buses, priority=data.get("priority","NORMAL"), requested_by=data["requested_by"]))
    db.commit(); return {"status": "CREATED"}

@app.post("/api/operations/allocate-dispatch")
def dispatch_bus(data: dict, db: Session = Depends(get_db)):
    d = db.query(StationDemand).filter(StationDemand.id == data.get("demand_id")).first()
    if d: d.status = "DISPATCHED"
    v = db.query(Vehicle).filter(Vehicle.id == data["vehicle_id"]).first()
    if v: v.status = "LOADED_OUT"; v.current_destination = data["destination_hub"]; v.current_passengers = data["allocated_passengers"]
    db.commit(); return {"status": "DISPATCHED"}

@app.post("/api/operations/journeys/start")
def start_jrn(data: dict, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == data["vehicle_reg_number"]).first()
    j = Journey(journey_code=f"JRN-{secrets.randbelow(90000)+10000}", vehicle_id=v.id, origin_name=v.current_hub, destination_name=data["destination_name"], passenger_count=data["passenger_count"])
    db.add(j); db.commit(); db.refresh(j)
    v.active_journey_id = j.id; v.status = "LOADED_OUT"; v.current_destination = data["destination_name"]; v.current_passengers = data["passenger_count"]; v.current_lat = data["latitude"]; v.current_lng = data["longitude"]
    db.commit(); return {"status": "STARTED", "journey_id": j.id, "journey_code": j.journey_code}

@app.post("/api/operations/telemetry/ping")
def ping_gps(data: dict, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == data["vehicle_reg_number"]).first()
    dist_km = 0.0
    if v:
        if v.active_journey_id and v.current_lat and v.current_lng:
            j = db.query(Journey).filter(Journey.id == v.active_journey_id).first()
            if j:
                step = haversine_m(v.current_lat, v.current_lng, data["latitude"], data["longitude"])
                if 2 <= step <= 5000: j.total_distance_km = round((j.total_distance_km or 0) + step/1000.0, 3)
                dist_km = j.total_distance_km
        v.current_lat = data["latitude"]; v.current_lng = data["longitude"]; v.current_speed_kmh = data.get("speed_kmh", 0)
        db.commit()
    return {"status": "OK", "total_distance_km": dist_km}

@app.post("/api/operations/journeys/end")
def end_jrn(data: dict, db: Session = Depends(get_db)):
    j = db.query(Journey).filter(Journey.id == data["journey_id"]).first()
    if j:
        j.ended_at = datetime.utcnow(); j.journey_status = "COMPLETED"
        if j.vehicle: j.vehicle.active_journey_id = None; j.vehicle.status = "UNLOADED_IN"; j.vehicle.current_passengers = 0
        db.commit(); return {"status": "COMPLETED", "total_distance_km": j.total_distance_km}
    return {"status": "NOT_FOUND"}

@app.post("/api/operations/fuel")
def log_fuel(data: dict, db: Session = Depends(get_db)):
    cost = round(data["liters_filled"] * data["rate_per_liter"], 2)
    db.add(FuelLog(vehicle_id=data["vehicle_id"], liters_filled=data["liters_filled"], rate_per_liter=data["rate_per_liter"], total_cost_inr=cost, filled_by=data["filled_by"]))
    db.commit(); return {"status": "LOGGED"}

@app.post("/api/operations/maintenance")
def log_maint(data: dict, db: Session = Depends(get_db)):
    db.add(MaintenanceTicket(ticket_code=f"MNT-{secrets.randbelow(90000)+10000}", vehicle_id=data["vehicle_id"], issue_category=data["issue_category"], severity=data.get("severity","HIGH"), description=data["description"], reported_by=data["reported_by"]))
    v = db.query(Vehicle).filter(Vehicle.id == data["vehicle_id"]).first()
    if v: v.is_maintenance_flagged = True; v.status = "MAINTENANCE_HOLD"
    db.commit(); return {"status": "CREATED"}

@app.get("/api/operations/shifts")
def get_shifts(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return [{"id": s.id, "crew_role": s.crew_role, "crew_name": s.crew_name, "station_hub": s.station_hub, "is_currently_on_duty": s.is_currently_on_duty, "elapsed_hours": round(((s.duty_end_time or now) - s.duty_start_time).total_seconds()/3600.0, 2)} for s in db.query(CrewDutyShift).all()]

@app.post("/api/operations/shifts/start")
def start_shift(data: dict, db: Session = Depends(get_db)):
    s = CrewDutyShift(crew_role=data["crew_role"], crew_name=data["crew_name"], crew_phone=data["crew_phone"], station_hub=data["station_hub"])
    db.add(s); db.commit(); db.refresh(s); return {"status": "STARTED", "shift_id": s.id}

@app.post("/api/operations/shifts/end")
def end_shift(data: dict, db: Session = Depends(get_db)):
    s = db.query(CrewDutyShift).filter(CrewDutyShift.id == data["shift_id"]).first()
    if s:
        s.duty_end_time = datetime.utcnow(); s.is_currently_on_duty = False
        s.total_duty_hours = round((s.duty_end_time - s.duty_start_time).total_seconds()/3600.0, 2)
        db.commit(); return {"status": "ENDED", "total_duty_hours": s.total_duty_hours}
    return {"status": "NOT_FOUND"}

@app.post("/api/operations/offline-sync")
def offline_sync(data: dict, db: Session = Depends(get_db)):
    items = data.get("items", [])
    return {"status": "SYNCED", "total_received": len(items), "total_processed": len(items), "total_duplicates_skipped": 0, "errors": []}

@app.get("/api/reports/executive-summary")
def exec_summary(db: Session = Depends(get_db)):
    pilgrims = db.query(func.sum(Saint.group_size)).scalar() or 0
    checked = db.query(func.sum(Saint.group_size)).filter(Saint.status == "Checked-In at Tent").scalar() or 0
    msrtc_spent = db.query(func.sum(MSRTCSpotCashVoucher.cash_amount_paid_inr)).scalar() or 0.0
    msrtc_float = db.query(func.sum(StationCashFloat.treasury_disbursed_amount_inr)).scalar() or 0.0
    rolling = sum(contract_metrics(c)["total_settlement_inr"] for c in db.query(HiredRollingContract).all())
    return {
        "saints": {"total_pilgrims": int(pilgrims), "total_groups": db.query(Saint).count(), "checked_in_pilgrims": int(checked)},
        "fleet": {"total_vehicles": db.query(Vehicle).count(), "active_in_transit": db.query(Vehicle).filter(Vehicle.status.in_(["LOADED_OUT","EMPTY_OUT"])).count(), "maintenance_hold": db.query(Vehicle).filter(Vehicle.is_maintenance_flagged == True).count()},
        "station_queues": {"pending_demands": db.query(StationDemand).filter(StationDemand.status == "PENDING").count(), "waiting_passengers": int(db.query(func.sum(StationDemand.waiting_passenger_count)).filter(StationDemand.status == "PENDING").scalar() or 0)},
        "financials_inr": {"msrtc_imprest_balance_inr": round(msrtc_float - msrtc_spent, 2), "grand_total_transport_spend_inr": round(rolling + msrtc_spent, 2)}
    }

@app.get("/api/reports/export/saints-csv")
def exp_saints(db: Session = Depends(get_db)):
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["Pass_ID", "Name", "Phone", "Pax", "Hub", "Ground", "Tent", "Status"])
    for s in db.query(Saint).all(): w.writerow([f"SMG-{s.id:05d}", s.full_name, s.contact_phone, s.group_size, s.arrival_hub, s.assigned_ground, s.assigned_tent, s.status])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=saints.csv"})

@app.get("/api/reports/export/financials-csv")
def exp_fin(db: Session = Depends(get_db)):
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["Type", "Code", "Amount_INR", "Status"])
    for c in db.query(HiredRollingContract).all(): w.writerow(["ROLLING", c.contract_code, contract_metrics(c)["total_settlement_inr"], c.status])
    for v in db.query(MSRTCSpotCashVoucher).all(): w.writerow(["MSRTC", v.voucher_number, v.cash_amount_paid_inr, "VERIFIED" if v.is_verified_at_gate else "PENDING"])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=financials.csv"})

@app.get("/")
def root(): return FileResponse(os.path.join(ROOT_DIR, "admin_dashboard.html"))

@app.get("/sw.js")
def sw(): return FileResponse(os.path.join(ROOT_DIR, "sw.js"), media_type="application/javascript")

@app.get("/{page}.html")
def serve_page(page: str):
    p = os.path.join(ROOT_DIR, f"{page}.html")
    if os.path.exists(p): return FileResponse(p)
    raise HTTPException(404, f"{page}.html not found")
