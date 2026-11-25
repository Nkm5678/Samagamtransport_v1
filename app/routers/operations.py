import os
import secrets
import sys
from datetime import datetime

_THIS_FILE = os.path.abspath(__file__)
_CANDIDATE_ROOTS = [
    os.path.abspath(os.path.join(os.path.dirname(_THIS_FILE), "..", "..")),
    r"C:\narendra\SamagamtransportV1",
]
for _root in _CANDIDATE_ROOTS:
    if os.path.isdir(os.path.join(_root, "app")) and _root not in sys.path:
        sys.path.insert(0, _root)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from app.database import get_db
from app.models import (
    Territory, StationDemand, TurnaroundMovement,
    FuelLog, MaintenanceTicket, Vehicle, Volunteer,
    CrewDutyShift, VehicleWearInspection, MSRTCSpotCashVoucher,
    StationCashFloat, HiredRollingContract, GroundStationIntercom,
    Journey, TelemetryPing, PickupDropVehicleRequest,
    DepartmentVehicleRequisition
)

router = APIRouter(prefix="/api/operations", tags=["Operations, Turnaround & Live Telemetry"])


def record_turnaround_movement(
    db: Session,
    veh: Vehicle,
    new_status: str,
    hub_name: str,
    actor_name: str,
    passenger_count: int = 0,
    destination_hub: str | None = None,
) -> TurnaroundMovement:
    """Updates vehicle turnaround state and records an audit log row in turnaround_movements."""
    prev_status = veh.status or "EMPTY_IN"
    veh.status = new_status
    if hub_name:
        veh.current_hub = hub_name
    veh.current_passengers = max(0, int(passenger_count or 0))
    veh.current_destination = destination_hub
    veh.last_updated = datetime.utcnow()

    movement = TurnaroundMovement(
        vehicle_id=veh.id,
        from_status=prev_status,
        to_status=new_status,
        station_hub=hub_name or veh.current_hub,
        destination_hub=destination_hub,
        passenger_count=veh.current_passengers,
        recorded_by=actor_name or "Operations Controller",
        recorded_at=datetime.utcnow(),
    )
    db.add(movement)
    return movement


@router.get("/hubs")
def list_operation_hubs(db: Session = Depends(get_db)):
    rows = db.query(Territory).order_by(Territory.id.asc()).all()
    return [
        {
            "id": r.id,
            "hub_code": r.hub_code,
            "hub_name": r.hub_name,
            "hub_type": r.hub_type,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "geofence_radius_m": r.geofence_radius_m,
        }
        for r in rows
    ]


@router.get("/intercom")
def list_intercom_messages(hub: str = "", db: Session = Depends(get_db)):
    q = db.query(GroundStationIntercom)
    if hub and hub != "ALL_STATIONS":
        q = q.filter(GroundStationIntercom.channel_hub.in_([hub, "ALL_STATIONS"]))
    msgs = q.order_by(GroundStationIntercom.id.desc()).limit(40).all()
    return [
        {
            "id": m.id,
            "channel_hub": m.channel_hub,
            "sender_side": m.sender_side,
            "sender_name": m.sender_name,
            "priority": m.priority,
            "message_text": m.message_text,
            "is_acknowledged": m.is_acknowledged,
            "acknowledged_by": m.acknowledged_by,
            "created_at": m.created_at.strftime("%H:%M:%S") if m.created_at else ""
        }
        for m in msgs
    ]


@router.post("/intercom")
def post_intercom_message(data: dict, db: Session = Depends(get_db)):
    msg = GroundStationIntercom(
        channel_hub=str(data.get("channel_hub") or "ALL_STATIONS").strip(),
        sender_side=str(data.get("sender_side") or "GROUND_TEAM").strip(),
        sender_name=str(data.get("sender_name") or "Field Sevadar").strip(),
        priority=str(data.get("priority") or "NORMAL").strip(),
        message_text=str(data.get("message_text") or "").strip(),
    )
    if not msg.message_text:
        raise HTTPException(status_code=400, detail="Message text cannot be empty.")
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "status": "SENT"}


@router.get("/pickup-drop-requests")
def list_pickup_drop_requests(db: Session = Depends(get_db)):
    rows = db.query(PickupDropVehicleRequest).order_by(PickupDropVehicleRequest.id.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "request_code": r.request_code,
            "trip_direction": r.trip_direction,
            "transit_hub": r.transit_hub,
            "passenger_count": r.passenger_count,
            "vehicle_type_requested": r.vehicle_type_requested,
            "vehicles_needed": r.vehicles_needed,
            "scheduled_datetime": r.scheduled_datetime,
            "train_flight_details": r.train_flight_details or "",
            "requester_name": r.requester_name,
            "requester_phone": r.requester_phone,
            "notes": r.notes or "",
            "status": r.status,
            "assigned_vehicle_reg": r.assigned_vehicle_reg,
        }
        for r in rows
    ]


@router.post("/pickup-drop-requests")
def create_pickup_drop_request(data: dict, db: Session = Depends(get_db)):
    code = f"PND-{secrets.randbelow(9000) + 1000}"
    pax = int(data.get("passenger_count") or 1)
    veh_qty = int(data.get("vehicles_needed") or 1)
    hub_name = str(data.get("transit_hub") or "Panvel Junction (PNVL)").strip()
    requester = str(data.get("requester_name") or "Coordinator").strip()
    phone = str(data.get("requester_phone") or "").strip()

    row = PickupDropVehicleRequest(
        request_code=code,
        trip_direction=str(data.get("trip_direction") or "PICKUP_TO_SAMAGAM").strip(),
        transit_hub=hub_name,
        passenger_count=pax,
        vehicle_type_requested=str(data.get("vehicle_type_requested") or "Heavy Bus (50-Seater)").strip(),
        vehicles_needed=veh_qty,
        scheduled_datetime=str(data.get("scheduled_datetime") or "").strip(),
        train_flight_details=str(data.get("train_flight_details") or "").strip() or None,
        requester_name=requester,
        requester_phone=phone,
        notes=str(data.get("notes") or "").strip() or None,
        status="PENDING_ALLOCATION",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "CREATED", "request_code": code, "id": row.id}


@router.post("/pickup-drop-requests/{req_id}/allocate")
def allocate_vehicle_to_pickup_drop(req_id: int, data: dict, db: Session = Depends(get_db)):
    """Allows Admin Control Room or Ground Team to allocate a vehicle to a Pickup/Drop request."""
    row = db.query(PickupDropVehicleRequest).filter(PickupDropVehicleRequest.id == req_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Pickup/Drop request not found.")
    reg = str(data.get("vehicle_reg_number") or "").upper().strip()
    if not reg:
        raise HTTPException(status_code=400, detail="Please select a valid vehicle registration number.")
    row.assigned_vehicle_reg = reg
    row.status = "ALLOCATED"
    db.commit()
    db.refresh(row)
    return {"status": "ALLOCATED", "id": row.id, "request_code": row.request_code, "assigned_vehicle_reg": reg}


@router.get("/request-status-lookup")
def lookup_request_status(query: str = "", db: Session = Depends(get_db)):
    q = str(query or "").strip()
    if not q:
        return []
    digits = "".join(ch for ch in q if ch.isdigit())
    phone_q = digits[-10:] if len(digits) >= 10 else q
    code_q = q.upper()

    results = []
    pd_rows = db.query(PickupDropVehicleRequest).filter(
        (PickupDropVehicleRequest.requester_phone.contains(phone_q))
        | (PickupDropVehicleRequest.request_code.ilike(f"%{code_q}%"))
    ).order_by(PickupDropVehicleRequest.id.desc()).limit(20).all()
    for p in pd_rows:
        results.append({
            "code": p.request_code,
            "category": "Pickup / Drop",
            "summary": f"{p.transit_hub} • {p.passenger_count} Pax • {p.vehicles_needed}x {p.vehicle_type_requested}",
            "requester_name": p.requester_name,
            "requester_phone": p.requester_phone,
            "status": p.status,
            "is_allocated": bool(p.assigned_vehicle_reg),
            "assigned_vehicle_reg": p.assigned_vehicle_reg,
            "driver_name": None,
            "driver_phone": None,
        })
    return results


@router.get("/demands")
def list_station_demands(db: Session = Depends(get_db)):
    rows = db.query(StationDemand).order_by(StationDemand.id.desc()).limit(50).all()
    return [
        {
            "id": d.id,
            "demand_code": d.demand_code,
            "hub_name": d.hub_name,
            "waiting_passenger_count": d.waiting_passenger_count,
            "recommended_buses": d.recommended_buses,
            "priority": d.priority,
            "status": d.status,
            "requested_by": d.requested_by,
            "notes": d.notes or "",
        }
        for d in rows
    ]


@router.post("/demands")
def create_station_demand(data: dict, db: Session = Depends(get_db)):
    code = f"DEM-{secrets.randbelow(9000) + 1000}"
    pax = int(data.get("waiting_passenger_count") or 1)
    row = StationDemand(
        demand_code=code,
        hub_name=str(data.get("hub_name") or "Thane Railway Station").strip(),
        waiting_passenger_count=pax,
        recommended_buses=str(data.get("recommended_buses") or f"{max(1, (pax + 49) // 50)}x Heavy Bus").strip(),
        priority=str(data.get("priority") or "NORMAL").strip(),
        status="PENDING",
        requested_by=str(data.get("requested_by") or "Station Team").strip(),
        notes=str(data.get("notes") or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "demand_code": row.demand_code, "status": row.status}


@router.post("/shifts/start")
def start_crew_shift(data: dict, db: Session = Depends(get_db)):
    shift = CrewDutyShift(
        crew_role=str(data.get("crew_role") or "Driver").strip(),
        crew_name=str(data.get("crew_name") or "Crew Member").strip(),
        crew_phone=str(data.get("crew_phone") or "").strip(),
        station_hub=str(data.get("station_hub") or "Ground 1 (Main Hall)").strip(),
        duty_start_time=datetime.utcnow(),
        is_currently_on_duty=True,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return {"shift_id": shift.id, "id": shift.id, "status": "ON_DUTY"}


@router.post("/shifts/end")
def end_crew_shift(data: dict, db: Session = Depends(get_db)):
    sid = data.get("shift_id")
    shift = db.query(CrewDutyShift).filter(CrewDutyShift.id == int(sid)).first() if sid else None
    if not shift:
        shift = db.query(CrewDutyShift).filter(CrewDutyShift.is_currently_on_duty == True).order_by(CrewDutyShift.id.desc()).first()
    if not shift:
        return {"status": "CLOSED", "total_duty_hours": 0.0}
    shift.duty_end_time = datetime.utcnow()
    shift.is_currently_on_duty = False
    shift.off_duty_reason = str(data.get("off_duty_reason") or "Shift Completed").strip()
    hrs = round(max(0.0, (shift.duty_end_time - shift.duty_start_time).total_seconds() / 3600.0), 2)
    shift.total_duty_hours = hrs
    db.commit()
    return {"shift_id": shift.id, "status": "CLOSED", "total_duty_hours": hrs}


@router.post("/journeys/start")
def start_vehicle_journey(data: dict, db: Session = Depends(get_db)):
    reg = str(data.get("vehicle_reg_number") or "").upper().strip()
    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first() if reg else db.query(Vehicle).first()
    j_code = f"JRN-{secrets.randbelow(9000) + 1000}"
    journey = Journey(
        journey_code=j_code,
        vehicle_id=veh.id if veh else 1,
        origin_hub=veh.current_hub if veh else "Thane Railway Station",
        destination_hub=str(data.get("destination_name") or "Ground 1 (Main Hall)").strip(),
        passenger_count=int(data.get("passenger_count") or 0),
        status="IN_TRANSIT",
        started_at=datetime.utcnow(),
    )
    db.add(journey)
    if veh:
        veh.status = "LOADED_OUT"
        veh.current_destination = journey.destination_hub
        veh.current_passengers = journey.passenger_count
    db.commit()
    db.refresh(journey)
    return {"journey_id": journey.id, "id": journey.id, "journey_code": j_code, "status": "IN_TRANSIT"}


@router.post("/journeys/end")
def end_vehicle_journey(data: dict, db: Session = Depends(get_db)):
    jid = data.get("journey_id")
    journey = db.query(Journey).filter(Journey.id == int(jid)).first() if jid else None
    if not journey:
        journey = db.query(Journey).filter(Journey.status == "IN_TRANSIT").order_by(Journey.id.desc()).first()
    if journey:
        journey.status = "COMPLETED"
        journey.ended_at = datetime.utcnow()
        veh = db.query(Vehicle).filter(Vehicle.id == journey.vehicle_id).first()
        if veh:
            veh.status = "UNLOADED_IN"
            veh.current_hub = str(data.get("end_location_name") or journey.destination_hub).strip()
            veh.current_passengers = 0
        db.commit()
        return {"journey_id": journey.id, "status": "COMPLETED", "total_distance_km": 18.5}
    return {"status": "COMPLETED", "total_distance_km": 0.0}


# ==============================================================================
# END-TO-END OPERATIONS PIPELINE & CHRONOLOGICAL SEQUENCE ENGINE
# ==============================================================================

SEQUENCE_STAGES = [
    {"step": 1, "key": "INTAKE_DEMAND", "title": "1. Request & Demand Intake", "owner_team": "Devotee / Station / Dept"},
    {"step": 2, "key": "DISPATCH_ASSIGNED", "title": "2. Fleet Allocation & Dispatch", "owner_team": "Control Room / Ground Team"},
    {"step": 3, "key": "IN_TRANSIT_LOADED", "title": "3. Boarding & Live GPS Transit", "owner_team": "Station Team & Driver App"},
    {"step": 4, "key": "GATE_UNLOADED_VERIFIED", "title": "4. Venue Gate Unload & Audit", "owner_team": "Gate Keeper & Ground Team"},
    {"step": 5, "key": "TURNAROUND_FUEL_SAFETY", "title": "5. Fuel, Safety & Loop Return", "owner_team": "Diesel & Workshop Marshall"},
    {"step": 6, "key": "EXIT_AND_SETTLEMENT", "title": "6. Outward Exit & Accounts Billing", "owner_team": "Gate Keeper & Accounts Cell"},
]


@router.get("/pipeline/live-board")
def get_live_operations_pipeline(db: Session = Depends(get_db)):
    pending_demands = db.query(StationDemand).filter(StationDemand.status == "PENDING").order_by(StationDemand.id.desc()).all()
    vehicles = db.query(Vehicle).order_by(Vehicle.last_updated.desc()).all()
    stage2_ready = [v for v in vehicles if v.status == "EMPTY_IN" and not v.is_maintenance_flagged]
    stage3_transit = [v for v in vehicles if v.status in ("LOADED_OUT", "EMPTY_OUT")]
    stage4_unloaded = [v for v in vehicles if v.status == "UNLOADED_IN"]
    stage5_maint = [v for v in vehicles if v.is_maintenance_flagged or v.status == "MAINTENANCE_HOLD"]

    unverified_msrtc = db.query(MSRTCSpotCashVoucher).filter(MSRTCSpotCashVoucher.is_verified_at_gate == False).all()
    active_contracts = db.query(HiredRollingContract).filter(HiredRollingContract.status == "ACTIVE_ROLLING").all()
    settled_contracts = db.query(HiredRollingContract).filter(HiredRollingContract.status == "SETTLED_AND_EXITED").order_by(HiredRollingContract.id.desc()).limit(10).all()

    return {
        "sequence_definition": SEQUENCE_STAGES,
        "stages": {
            "stage_1_intake": {
                "count": len(pending_demands),
                "demands": [
                    {
                        "id": d.id,
                        "code": d.demand_code,
                        "hub": d.hub_name,
                        "pax": d.waiting_passenger_count,
                        "mix": d.recommended_buses,
                        "requested_by": d.requested_by,
                        "notes": d.notes or ""
                    }
                    for d in pending_demands
                ],
            },
            "stage_2_ready_fleet": {
                "count": len(stage2_ready),
                "vehicles": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "type": v.vehicle_type,
                        "capacity": v.capacity,
                        "hub": v.current_hub,
                        "driver": f"{v.driver_name} ({v.driver_phone})",
                        "ownership": v.ownership_type
                    }
                    for v in stage2_ready
                ]
            },
            "stage_3_in_transit": {
                "count": len(stage3_transit),
                "vehicles": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "status": v.status,
                        "hub": v.current_hub,
                        "destination": v.current_destination or "Samagam Ground",
                        "pax": v.current_passengers,
                        "capacity": v.capacity,
                        "speed_kmh": v.current_speed_kmh,
                        "driver": f"{v.driver_name} ({v.driver_phone})"
                    }
                    for v in stage3_transit
                ]
            },
            "stage_4_gate_unload_audit": {
                "count": len(stage4_unloaded) + len(unverified_msrtc),
                "unloaded_vehicles": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "hub": v.current_hub,
                        "driver": v.driver_name,
                        "ownership": v.ownership_type
                    }
                    for v in stage4_unloaded
                ],
                "pending_msrtc_gate_checks": [
                    {
                        "id": m.id,
                        "voucher": m.voucher_number,
                        "station": m.station_hub,
                        "etm": m.etm_receipt_number,
                        "amount": m.cash_amount_paid_inr,
                        "pax": m.passenger_headcount
                    }
                    for m in unverified_msrtc
                ]
            },
            "stage_5_fuel_and_safety": {
                "count": len(stage5_maint),
                "maintenance_holds": [
                    {
                        "id": v.id,
                        "reg": v.vehicle_reg_number,
                        "health": v.health_score_pct,
                        "reason": v.maintenance_reason or "Workshop Hold"
                    }
                    for v in stage5_maint
                ]
            },
            "stage_6_contracts_settlement": {
                "active_rolling_count": len(active_contracts),
                "settled_count": len(settled_contracts),
                "active_contracts": [
                    {
                        "id": c.id,
                        "code": c.contract_code,
                        "reg": c.vehicle.vehicle_reg_number if c.vehicle else "",
                        "vendor": c.vendor_agency_name,
                        "entry_odo": c.entry_odometer_km
                    }
                    for c in active_contracts
                ]
            }
        }
    }


@router.post("/pipeline/advance-step")
def advance_vehicle_sequence_step(data: dict, db: Session = Depends(get_db)):
    action = str(data.get("action") or "").upper().strip()
    vehicle_id = data.get("vehicle_id")
    demand_id = data.get("demand_id")
    actor = str(data.get("actor_name") or "Operations Controller").strip()
    destination = str(data.get("destination_hub") or "Ground 1 (Main Hall)").strip()
    pax = int(data.get("passenger_count") or 0)

    veh = db.query(Vehicle).filter(Vehicle.id == int(vehicle_id)).first() if vehicle_id else None

    if action == "ASSIGN_AND_DISPATCH":
        if not veh:
            raise HTTPException(status_code=400, detail="Select an available bus to dispatch.")
        if veh.is_maintenance_flagged:
            raise HTTPException(status_code=409, detail=f"Blocked: {veh.vehicle_reg_number} is on Maintenance Hold.")
        if demand_id:
            dem = db.query(StationDemand).filter(StationDemand.id == int(demand_id)).first()
            if dem:
                dem.status = "DISPATCHED"
                pax = pax or dem.waiting_passenger_count
                pd = db.query(PickupDropVehicleRequest).filter(PickupDropVehicleRequest.request_code == dem.demand_code).first()
                if pd:
                    pd.status = "DISPATCHED"
                    pd.assigned_vehicle_reg = veh.vehicle_reg_number
        record_turnaround_movement(db, veh, "LOADED_OUT", veh.current_hub, actor, min(pax or veh.capacity, veh.capacity), destination)
        db.commit()
        return {"status": "MOVED_TO_STAGE_3_TRANSIT", "vehicle": veh.vehicle_reg_number, "next_step": "Arrival & Unload at Venue Gate"}

    if action == "GATE_ARRIVE_UNLOAD":
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        record_turnaround_movement(db, veh, "UNLOADED_IN", destination, actor, 0, None)
        db.commit()
        return {"status": "MOVED_TO_STAGE_4_UNLOADED", "vehicle": veh.vehicle_reg_number, "next_step": "Fuel/Safety Check or Return Loop"}

    if action == "RELEASE_EMPTY_LOOP":
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        if veh.is_maintenance_flagged:
            raise HTTPException(status_code=409, detail="Cannot release bus on Maintenance Hold.")
        record_turnaround_movement(db, veh, "EMPTY_OUT", veh.current_hub, actor, 0, destination)
        db.commit()
        return {"status": "MOVED_TO_STAGE_5_RETURN_LOOP", "vehicle": veh.vehicle_reg_number, "next_step": "Arrive Empty at Station Staging"}

    if action == "MARK_READY_AT_HUB":
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found.")
        record_turnaround_movement(db, veh, "EMPTY_IN", destination, actor, 0, None)
        db.commit()
        return {"status": "MOVED_TO_STAGE_2_READY", "vehicle": veh.vehicle_reg_number, "next_step": "Assign Next Pilgrim Demand"}

    raise HTTPException(status_code=400, detail=f"Unsupported pipeline action: {action}")


# ==============================================================================
# MASTER CONTACT DIRECTORY (ADMIN, INCHARGES, COORDINATORS, CONTRACTORS, COMMITTEE)
# ==============================================================================

ROLE_LABELS = {
    "ADMIN": "Admin HQ",
    "GROUND_ADMIN": "Admin HQ",
    "INCHARGE": "Dept / Committee Incharge",
    "STATION_COORDINATOR": "Station Coordinator",
    "GROUND_COORDINATOR": "Ground Coordinator",
    "CONTRACTOR": "Bus Contractor / Vendor",
    "COMMITTEE_MEMBER": "Committee Member",
}


@router.get("/directory-contacts")
def list_master_directory_contacts(db: Session = Depends(get_db)):
    vols = db.query(Volunteer).filter(Volunteer.is_active == True).order_by(Volunteer.id.desc()).all()
    out = []
    for v in vols:
        raw_role = (v.system_role or "COMMITTEE_MEMBER").upper()
        norm_role = "ADMIN" if raw_role in ("GROUND_ADMIN", "ADMIN", "CONTROL_ROOM") else raw_role
        out.append({
            "id": v.id,
            "code": v.volunteer_code,
            "role": norm_role,
            "role_label": ROLE_LABELS.get(norm_role, norm_role.replace("_", " ").title()),
            "full_name": v.full_name,
            "mobile_number": v.mobile_number,
            "duty_location": v.duty_location or "",
            "branch_name": v.branch_name or "",
            "unit_number": v.unit_number or "",
        })
    return out


@router.post("/directory-contacts")
def upsert_master_directory_contact(data: dict, db: Session = Depends(get_db)):
    cid = data.get("id")
    role = str(data.get("role") or "COMMITTEE_MEMBER").upper().strip()
    name = str(data.get("full_name") or "").strip()
    digits = "".join(ch for ch in str(data.get("mobile_number") or "") if ch.isdigit())
    phone = digits[-10:] if len(digits) >= 10 else digits
    hub = str(data.get("duty_location") or "Ground 1 (Main Hall)").strip()
    branch = str(data.get("branch_name") or "Samagam Transport").strip()
    unit = str(data.get("unit_number") or "HQ-Dir").strip()
    pin = "".join(ch for ch in str(data.get("pin") or "") if ch.isdigit())

    if not name or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Full Name and a valid 10-digit Mobile Number are required.")

    vol = db.query(Volunteer).filter(Volunteer.id == int(cid)).first() if cid else None
    if not vol:
        vol = db.query(Volunteer).filter(Volunteer.mobile_number == phone).first()

    db_role = "GROUND_ADMIN" if role == "ADMIN" else role
    if vol:
        vol.full_name = name
        vol.mobile_number = phone
        vol.system_role = db_role
        vol.duty_location = hub
        vol.branch_name = branch
        vol.unit_number = unit
        vol.is_active = True
        if len(pin) == 4:
            vol.pin_hash = generate_password_hash(pin)
    else:
        vol = Volunteer(
            volunteer_code=f"DIR-{secrets.randbelow(9000) + 1000}",
            full_name=name,
            mobile_number=phone,
            pin_hash=generate_password_hash(pin if len(pin) == 4 else "1234"),
            duty_location=hub,
            branch_name=branch,
            unit_number=unit,
            system_role=db_role,
            is_driver=False,
            geofence_verified=True,
        )
        db.add(vol)

    db.commit()
    db.refresh(vol)
    return {"status": "SAVED", "id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number}


@router.post("/directory-contacts/bulk")
def bulk_upsert_master_directory_contacts(data: dict, db: Session = Depends(get_db)):
    items = data.get("items") or []
    saved = 0
    for item in items:
        name = str(item.get("full_name") or "").strip()
        digits = "".join(ch for ch in str(item.get("mobile_number") or "") if ch.isdigit())
        phone = digits[-10:] if len(digits) >= 10 else digits
        if not name or len(phone) != 10:
            continue
        upsert_master_directory_contact({
            "role": item.get("role") or "COMMITTEE_MEMBER",
            "full_name": name,
            "mobile_number": phone,
            "duty_location": item.get("duty_location") or "Ground 1 (Main Hall)",
            "branch_name": item.get("branch_name") or "Samagam Transport",
            "unit_number": item.get("unit_number") or "HQ-Dir",
        }, db)
        saved += 1
    return {"status": "BULK_SAVED", "saved_count": saved}


@router.delete("/directory-contacts/{contact_id}")
def delete_master_directory_contact(contact_id: int, db: Session = Depends(get_db)):
    vol = db.query(Volunteer).filter(Volunteer.id == contact_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Contact not found.")
    if vol.mobile_number == "9820110001":
        raise HTTPException(status_code=403, detail="Primary HQ Admin account cannot be deleted.")
    vol.is_active = False
    db.commit()
    return {"status": "DELETED", "id": contact_id}


# ==============================================================================
# GROUND SERVICE DEPARTMENT VEHICLE REQUISITIONS (ground.samagamtransport.in)
# ==============================================================================

def _first_attr(obj, names: tuple[str, ...], default=None):
    for n in names:
        if hasattr(obj, n):
            val = getattr(obj, n)
            if val is not None:
                return val
    return default


def _serialize_ground_dept_req(r: DepartmentVehicleRequisition) -> dict:
    created = _first_attr(r, ("created_at", "requested_at", "timestamp"))
    return {
        "id": r.id,
        "requisition_code": _first_attr(r, ("requisition_code", "request_code"), f"REQ-{r.id}"),
        "department_name": _first_attr(r, ("department_name", "department"), ""),
        "department_head_name": _first_attr(r, ("department_head_name", "incharge_name"), "") or "",
        "requester_name": _first_attr(r, ("requester_name", "coordinator_name"), ""),
        "requester_phone": _first_attr(r, ("requester_phone", "contact_number", "mobile_number"), ""),
        "required_vehicle_type": _first_attr(r, ("required_vehicle_type", "vehicle_type_requested", "vehicle_type"), ""),
        "quantity_needed": _first_attr(r, ("quantity_needed", "vehicles_needed", "vehicle_count"), 1),
        "purpose": _first_attr(r, ("purpose", "purpose_of_use", "justification", "notes"), "") or "",
        "required_from_datetime": str(_first_attr(r, ("required_from_datetime", "required_datetime", "scheduled_datetime"), "") or ""),
        "duration_days": str(_first_attr(r, ("duration_days", "duration"), "") or ""),
        "status": _first_attr(r, ("status",), "PENDING_ALLOCATION"),
        "allocated_vehicle_reg": _first_attr(r, ("allocated_vehicle_reg", "assigned_vehicle_reg"), None),
        "created_at": created.strftime("%Y-%m-%d %H:%M") if hasattr(created, "strftime") else str(created or ""),
    }


@router.get("/ground-dept-requisitions")
def list_ground_dept_requisitions(query: str = "", db: Session = Depends(get_db)):
    q_obj = db.query(DepartmentVehicleRequisition)
    rows = q_obj.order_by(DepartmentVehicleRequisition.id.desc()).limit(150).all()
    serialized = [_serialize_ground_dept_req(r) for r in rows]
    q = str(query or "").strip().lower()
    if q:
        digits = "".join(ch for ch in q if ch.isdigit())
        phone_q = digits[-10:] if len(digits) >= 10 else q
        serialized = [
            item for item in serialized
            if phone_q in str(item["requester_phone"]).lower()
            or q in str(item["requisition_code"]).lower()
            or q in str(item["department_name"]).lower()
        ]
    return serialized


@router.post("/ground-dept-requisitions")
def create_ground_dept_requisition(data: dict, db: Session = Depends(get_db)):
    """Creates an Advance Projection or Ad-hoc Ground Department Vehicle Requisition safely across any schema variant."""
    dept_name = str(data.get("department_name") or "").strip()
    req_name = str(data.get("requester_name") or "").strip()
    raw_phone = "".join(ch for ch in str(data.get("requester_phone") or "") if ch.isdigit())
    req_phone = raw_phone[-10:] if len(raw_phone) >= 10 else raw_phone
    veh_type = str(data.get("required_vehicle_type") or "Goods Carrier / Tempo").strip()
    qty = max(1, int(data.get("quantity_needed") or 1))
    purpose = str(data.get("purpose") or "Ground Department Sewa").strip()
    dept_head = str(data.get("department_head_name") or req_name).strip()
    req_from = str(data.get("required_from_datetime") or datetime.utcnow().strftime("%Y-%m-%d %H:%M")).strip()
    raw_duration = str(data.get("duration_days") or "1").strip()

    if not dept_name or not req_name or len(req_phone) != 10:
        raise HTTPException(
            status_code=400,
            detail="Department Name, Requester Name, and a valid 10-digit Mobile Number are required."
        )

    req_code = f"REQ-{secrets.randbelow(9000) + 1000}"
    model_cols = {c.name: c for c in DepartmentVehicleRequisition.__table__.columns}

    digits_dur = "".join(ch for ch in raw_duration if ch.isdigit())
    duration_int = int(digits_dur) if digits_dur else 1

    synonym_values = {
        "requisition_code": req_code,
        "request_code": req_code,
        "department_name": dept_name,
        "department": dept_name,
        "department_head_name": dept_head,
        "incharge_name": dept_head,
        "requester_name": req_name,
        "coordinator_name": req_name,
        "requester_phone": req_phone,
        "contact_number": req_phone,
        "mobile_number": req_phone,
        "required_vehicle_type": veh_type,
        "vehicle_type_requested": veh_type,
        "vehicle_type": veh_type,
        "quantity_needed": qty,
        "vehicles_needed": qty,
        "vehicle_count": qty,
        "purpose": purpose,
        "purpose_of_use": purpose,
        "justification": purpose,
        "notes": purpose,
        "required_from_datetime": req_from,
        "required_datetime": req_from,
        "scheduled_datetime": req_from,
        "duration_days": duration_int if ("duration_days" in model_cols and "INT" in str(model_cols["duration_days"].type).upper()) else raw_duration,
        "duration": raw_duration,
        "status": "PENDING_ALLOCATION",
        "allocated_vehicle_reg": None,
        "assigned_vehicle_reg": None,
    }

    safe_kwargs = {}
    for col_name, col_obj in model_cols.items():
        if col_obj.primary_key:
            continue
        if col_name in synonym_values:
            safe_kwargs[col_name] = synonym_values[col_name]
        elif not col_obj.nullable and col_obj.default is None and col_obj.server_default is None:
            col_type = str(col_obj.type).upper()
            if "INT" in col_type:
                safe_kwargs[col_name] = 0
            elif "FLOAT" in col_type or "NUM" in col_type:
                safe_kwargs[col_name] = 0.0
            elif "BOOL" in col_type:
                safe_kwargs[col_name] = False
            elif "DATE" in col_type or "TIME" in col_type:
                safe_kwargs[col_name] = datetime.utcnow()
            else:
                safe_kwargs[col_name] = "-"

    try:
        row = DepartmentVehicleRequisition(**safe_kwargs)
        db.add(row)
        db.commit()
        db.refresh(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error saving ground request: {exc}")

    return {
        "status": "CREATED",
        "id": row.id,
        "requisition_code": _first_attr(row, ("requisition_code", "request_code"), req_code),
        "message": "Vehicle will be allocated if available ASAP.",
    }


@router.post("/ground-dept-requisitions/{req_id}/allocate")
def allocate_vehicle_to_ground_dept_requisition(req_id: int, data: dict, db: Session = Depends(get_db)):
    """Allows Admin Control Room or Ground Transport Team to allocate a vehicle to a department request."""
    row = db.query(DepartmentVehicleRequisition).filter(DepartmentVehicleRequisition.id == req_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ground department requisition not found.")
    reg = str(data.get("vehicle_reg_number") or "").upper().strip()
    if not reg:
        raise HTTPException(status_code=400, detail="Please select a valid vehicle registration number.")

    if hasattr(row, "allocated_vehicle_reg"):
        row.allocated_vehicle_reg = reg
    if hasattr(row, "assigned_vehicle_reg"):
        row.assigned_vehicle_reg = reg
    row.status = "ALLOCATED"
    db.commit()
    db.refresh(row)
    return {
        "status": "ALLOCATED",
        "id": row.id,
        "requisition_code": _first_attr(row, ("requisition_code", "request_code"), f"REQ-{row.id}"),
        "allocated_vehicle_reg": reg,
    }

# --- Helpline Roster & Fleet/Driver Excel Endpoints ---
import io as _io_mod
import re as _re_mod
from datetime import datetime as _dt_mod
from typing import Optional as _Opt
try:
    import openpyxl as _openpyxl
except ImportError:
    _openpyxl = None
from fastapi import UploadFile as _UploadFile, File as _File
from sqlalchemy import text as _sql_text

def _ensure_reconciled_tables(db):
    q1 = "CREATE TABLE IF NOT EXISTS samagam_duty_roster (id INTEGER PRIMARY KEY AUTOINCREMENT, team_category VARCHAR(40) NOT NULL, duty_date VARCHAR(20), location_name VARCHAR(160) NOT NULL, shift_timing VARCHAR(80) NOT NULL, slot_label VARCHAR(40), sewadar_name VARCHAR(120) NOT NULL, primary_mobile VARCHAR(20) NOT NULL, alt_mobile VARCHAR(20), unit_no VARCHAR(60), duty_role VARCHAR(160), updated_at VARCHAR(40))"
    q2 = "CREATE TABLE IF NOT EXISTS samagam_fleet_vehicles (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_reg VARCHAR(30) UNIQUE NOT NULL, vehicle_category VARCHAR(80) NOT NULL, make_model VARCHAR(80), capacity VARCHAR(40), ownership_source VARCHAR(40), owner_name VARCHAR(120), owner_mobile VARCHAR(20), staged_hub VARCHAR(140), driver_name VARCHAR(120), driver_mobile VARCHAR(20), available_from VARCHAR(20), available_till VARCHAR(20), status VARCHAR(30) DEFAULT 'READY', updated_at VARCHAR(40))"
    q3 = "CREATE TABLE IF NOT EXISTS samagam_driver_roster (id INTEGER PRIMARY KEY AUTOINCREMENT, driver_name VARCHAR(120) NOT NULL, primary_mobile VARCHAR(20) UNIQUE NOT NULL, alt_mobile VARCHAR(20), login_pin VARCHAR(10) NOT NULL, license_no VARCHAR(50), license_type VARCHAR(60), assigned_vehicle_reg VARCHAR(30), base_hub VARCHAR(140), duty_shift VARCHAR(80), unit_agency VARCHAR(120), updated_at VARCHAR(40))"
    db.execute(_sql_text(q1))
    db.execute(_sql_text(q2))
    db.execute(_sql_text(q3))
    db.commit()

@router.post("/roster/upload-excel")
async def upload_station_ground_roster_excel(file: _UploadFile = _File(...), db=Depends(get_db)):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Please upload the .xlsx Roster Proforma file.")
    _ensure_reconciled_tables(db)
    wb = _openpyxl.load_workbook(_io_mod.BytesIO(await file.read()), data_only=True)
    inserted = 0
    now_iso = _dt_mod.utcnow().isoformat()
    for sname in wb.sheetnames:
        if "summary" in sname.lower():
            continue
        ws = wb[sname]
        default_team = "GROUND_TEAM" if "ground" in sname.lower() else "STATION_TEAM"
        for r in range(5, ws.max_row + 1):
            tcat = str(ws.cell(r, 2).value or default_team).strip().upper()
            tcat = "GROUND_TEAM" if "GROUND" in tcat else "STATION_TEAM"
            ddate = str(ws.cell(r, 3).value or "").strip()[:10]
            loc = str(ws.cell(r, 4).value or "").strip()
            shift = str(ws.cell(r, 5).value or "").strip()
            slot = str(ws.cell(r, 6).value or "").strip()
            name = str(ws.cell(r, 7).value or "").strip()
            mob = _re_mod.sub(r"\D", "", str(ws.cell(r, 8).value or ""))[-10:]
            alt = _re_mod.sub(r"\D", "", str(ws.cell(r, 9).value or ""))[-10:]
            unit = str(ws.cell(r, 10).value or "").strip()
            role = str(ws.cell(r, 11).value or "").strip()
            if not name or len(mob) < 10 or not loc:
                continue
            ins_sql = "INSERT INTO samagam_duty_roster (team_category, duty_date, location_name, shift_timing, slot_label, sewadar_name, primary_mobile, alt_mobile, unit_no, duty_role, updated_at) VALUES (:tc, :dd, :loc, :sh, :sl, :nm, :pm, :am, :un, :rl, :ua)"
            db.execute(_sql_text(ins_sql), {"tc": tcat, "dd": ddate, "loc": loc, "sh": shift, "sl": slot, "nm": name, "pm": mob, "am": alt, "un": unit, "rl": role, "ua": now_iso})
            inserted += 1
    db.commit()
    return {"status": "success", "records_uploaded": inserted, "message": f"Uploaded {inserted} active roster contacts."}

@router.get("/roster/live")
def get_live_helpline_roster(duty_date: _Opt[str] = None, team_category: _Opt[str] = None, db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    q = "SELECT * FROM samagam_duty_roster WHERE 1=1"
    params = {}
    if duty_date:
        q += " AND duty_date = :dd"
        params["dd"] = duty_date
    if team_category and team_category != "ALL":
        q += " AND team_category = :tc"
        params["tc"] = team_category
    q += " ORDER BY duty_date ASC, team_category ASC, location_name ASC, shift_timing ASC, id ASC"
    rows = db.execute(_sql_text(q), params).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}

@router.post("/fleet/upload-excel")
async def upload_fleet_vehicles_and_drivers_excel(file: _UploadFile = _File(...), db=Depends(get_db)):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Please upload the .xlsx Fleet & Drivers Proforma file.")
    _ensure_reconciled_tables(db)
    wb = _openpyxl.load_workbook(_io_mod.BytesIO(await file.read()), data_only=True)
    v_cnt, d_cnt = 0, 0
    now_iso = _dt_mod.utcnow().isoformat()
    if "Fleet_Vehicles_Master" in wb.sheetnames:
        ws_v = wb["Fleet_Vehicles_Master"]
        for r in range(5, ws_v.max_row + 1):
            reg = _re_mod.sub(r"\s+", "", str(ws_v.cell(r, 2).value or "")).upper()
            v_cat = str(ws_v.cell(r, 3).value or "").strip()
            if not reg or not v_cat:
                continue
            db.execute(_sql_text("DELETE FROM samagam_fleet_vehicles WHERE vehicle_reg = :reg"), {"reg": reg})
            v_sql = "INSERT INTO samagam_fleet_vehicles (vehicle_reg, vehicle_category, make_model, capacity, ownership_source, owner_name, owner_mobile, staged_hub, driver_name, driver_mobile, available_from, available_till, status, updated_at) VALUES (:reg, :cat, :mm, :cap, :src, :onm, :omob, :hub, :dnm, :dmob, :af, :at, 'READY', :ua)"
            db.execute(_sql_text(v_sql), {"reg": reg, "cat": v_cat, "mm": str(ws_v.cell(r, 4).value or "").strip(), "cap": str(ws_v.cell(r, 5).value or "").strip(), "src": str(ws_v.cell(r, 6).value or "SEWA_DONATED").strip().upper(), "onm": str(ws_v.cell(r, 7).value or "").strip(), "omob": _re_mod.sub(r"\D", "", str(ws_v.cell(r, 8).value or ""))[-10:], "hub": str(ws_v.cell(r, 9).value or "").strip(), "dnm": str(ws_v.cell(r, 10).value or "").strip(), "dmob": _re_mod.sub(r"\D", "", str(ws_v.cell(r, 11).value or ""))[-10:], "af": str(ws_v.cell(r, 12).value or "").strip()[:10], "at": str(ws_v.cell(r, 13).value or "").strip()[:10], "ua": now_iso})
            v_cnt += 1
    if "Driver_Roster_Master" in wb.sheetnames:
        ws_d = wb["Driver_Roster_Master"]
        for r in range(5, ws_d.max_row + 1):
            d_name = str(ws_d.cell(r, 2).value or "").strip()
            p_mob = _re_mod.sub(r"\D", "", str(ws_d.cell(r, 3).value or ""))[-10:]
            if not d_name or len(p_mob) < 10:
                continue
            a_mob = _re_mod.sub(r"\D", "", str(ws_d.cell(r, 4).value or ""))[-10:]
            pin_raw = _re_mod.sub(r"\D", "", str(ws_d.cell(r, 5).value or ""))
            pin = pin_raw[:4] if len(pin_raw) >= 4 else p_mob[-4:]
            veh_reg = _re_mod.sub(r"\s+", "", str(ws_d.cell(r, 8).value or "")).upper()
            db.execute(_sql_text("DELETE FROM samagam_driver_roster WHERE primary_mobile = :pm"), {"pm": p_mob})
            d_sql = "INSERT INTO samagam_driver_roster (driver_name, primary_mobile, alt_mobile, login_pin, license_no, license_type, assigned_vehicle_reg, base_hub, duty_shift, unit_agency, updated_at) VALUES (:dn, :pm, :am, :pin, :ln, :lt, :vr, :bh, :sh, :ua, :up)"
            db.execute(_sql_text(d_sql), {"dn": d_name, "pm": p_mob, "am": a_mob, "pin": pin, "ln": str(ws_d.cell(r, 6).value or "").strip().upper(), "lt": str(ws_d.cell(r, 7).value or "").strip(), "vr": veh_reg, "bh": str(ws_d.cell(r, 9).value or "").strip(), "sh": str(ws_d.cell(r, 10).value or "").strip(), "ua": str(ws_d.cell(r, 11).value or "").strip(), "up": now_iso})
            if veh_reg:
                db.execute(_sql_text("UPDATE samagam_fleet_vehicles SET driver_name = :dn, driver_mobile = :pm, updated_at = :up WHERE vehicle_reg = :vr"), {"dn": d_name, "pm": p_mob, "up": now_iso, "vr": veh_reg})
            d_cnt += 1
    db.commit()
    return {"status": "success", "vehicles_uploaded": v_cnt, "drivers_uploaded": d_cnt, "message": f"Uploaded {v_cnt} vehicles and {d_cnt} drivers."}
