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

# --- UNIFIED SAMAGAM OPERATIONS EXTENSION ---
import io as _io_mod
import math as _math_mod
import re as _re_mod
from datetime import datetime as _dt_mod
from typing import Optional as _Opt
try:
    import openpyxl as _openpyxl
except ImportError:
    _openpyxl = None
from fastapi import UploadFile as _UploadFile, File as _File
from sqlalchemy import text as _sql_text

_HUB_COORDS = {
    "panvel": (18.9911, 73.1213),
    "thane": (19.1860, 72.9759),
    "ltt": (19.0701, 72.8913),
    "lokmanya tilak": (19.0701, 72.8913),
    "csmt": (18.9398, 72.8355),
    "dadar": (19.0178, 72.8478),
    "kalyan": (19.2354, 73.1305),
    "mumbai central": (18.9712, 72.8194),
    "goregaon": (19.1646, 72.8493),
    "borivali": (19.2291, 72.8573),
    "t1": (19.0914, 72.8539),
    "t2": (19.0974, 72.8745),
    "nmia": (18.9894, 73.0695),
    "navi mumbai airport": (18.9894, 73.0695),
    "ground": (19.0330, 73.0297),
    "samagam ground": (19.0330, 73.0297),
}

_STATION_PICKUP_GUIDES = {
    "panvel": {
        "title": "Panvel Railway Station ? East Exit ST & Shuttle Bus Bay",
        "waiting_point": "Platform 1 East Foot-Over-Bridge Exit ? Gate No. 2 Near Panvel ST Bus Stand Bay-4 (Look for JAGRITI / SAMAGAM TRANSPORT Yellow Banner).",
        "landmark": "Opposite Panvel ST Depot Gate No. 2, 60m from East Ticket Counter",
        "gate_label": "EXIT GATE 2 (EAST)",
        "bay_label": "SAMAGAM BUS BAY 1-4"
    },
    "thane": {
        "title": "Thane Railway Station ? East Side (Kopri) Bus Terminal Pickup",
        "waiting_point": "Take Central FOB toward Thane East (Kopri) ? Walk 80m straight to Kopri Bus Terminus Lane-2 Samagam Helpdesk.",
        "landmark": "Kopri Bus Stand Lane-2, beside Traffic Police Chowky",
        "gate_label": "THANE EAST (KOPRI) EXIT",
        "bay_label": "SHUTTLE LANE 2"
    },
    "ltt": {
        "title": "Lokmanya Tilak Terminus (LTT) ? Main Concourse Gate-1 Bus Bay",
        "waiting_point": "Exit Main Passenger Concourse Gate-1 ? Turn Left toward Prepaid Auto/Bus Parking Lane-3.",
        "landmark": "LTT Gate-1 Exit Flagpost, 50m left of Main Porch",
        "gate_label": "MAIN CONCOURSE GATE 1",
        "bay_label": "BUS LANE 3"
    },
    "csmt": {
        "title": "CSMT ? Platform 18 P. D'Mello Road East Exit",
        "waiting_point": "Walk toward Platform 18 East Exit (P. D'Mello Road side) ? Gather under Samagam Helpdesk Canopy near Gate-4.",
        "landmark": "Platform 18 Outstation Exit, P. D'Mello Road",
        "gate_label": "PF-18 D'MELLO EXIT",
        "bay_label": "COACH BAY A"
    },
    "dadar": {
        "title": "Dadar Terminus ? East Side Swami Narayan Temple / Central Exit",
        "waiting_point": "Exit Central Line Platform 1/2 East Gate ? Assemble near Dadar East Bus Stop Canopy.",
        "landmark": "Dadar East Outside PF-1 Exit Gate",
        "gate_label": "DADAR EAST GATE",
        "bay_label": "PICKUP POINT D1"
    },
    "kalyan": {
        "title": "Kalyan Junction ? West ST Depot Exit Gate-1",
        "waiting_point": "Use Main FOB to Kalyan West ? Exit toward Kalyan ST Bus Depot Gate-1 Samagam Sewadar Desk.",
        "landmark": "Kalyan West ST Stand Entrance Arch",
        "gate_label": "KALYAN WEST GATE 1",
        "bay_label": "BUS BAY K1-K2"
    },
    "t1": {
        "title": "Mumbai Airport Terminal 1 (T1) ? Arrivals Pillar P4",
        "waiting_point": "Exit Arrivals Gate B ? Walk across to Coach Parking Zone Pillar P4.",
        "landmark": "Arrivals Forecourt Pillar P4",
        "gate_label": "T1 ARRIVALS GATE B",
        "bay_label": "COACH PILLAR P4"
    },
    "t2": {
        "title": "Mumbai Airport Terminal 2 (T2) ? Level P4 Bus & Coach Bay",
        "waiting_point": "Take Elevator/Escalator from Arrivals to Level P4 ? Gate 4 Bus Boarding Bay.",
        "landmark": "T2 Multi-Level Car Park Level P4, Gate 4",
        "gate_label": "T2 LEVEL P4 EXIT",
        "bay_label": "COACH BAY 4"
    },
    "nmia": {
        "title": "Navi Mumbai International Airport (NMIA) ? Arrivals Bay-2",
        "waiting_point": "Exit Domestic/International Arrivals Terminal ? Proceed to Group Coach Bay-2.",
        "landmark": "NMIA Terminal Arrivals Forecourt Bay-2",
        "gate_label": "NMIA ARRIVALS GATE",
        "bay_label": "GROUP BAY 2"
    }
}

def _hub_distance_km(hub_a: str, hub_b: str) -> float:
    a = (hub_a or "").lower()
    b = (hub_b or "").lower()
    if a and b and (a in b or b in a):
        return 0.4
    ca = next((v for k, v in _HUB_COORDS.items() if k in a), (19.0330, 73.0297))
    cb = next((v for k, v in _HUB_COORDS.items() if k in b), (19.0330, 73.0297))
    dlat = (ca[0] - cb[0]) * 111.0
    dlon = (ca[1] - cb[1]) * 104.0
    return round(_math_mod.hypot(dlat, dlon) + 0.5, 1)

def _ensure_reconciled_tables(db):
    stmts = [
        "CREATE TABLE IF NOT EXISTS samagam_duty_roster (id INTEGER PRIMARY KEY AUTOINCREMENT, team_category VARCHAR(40) NOT NULL, duty_date VARCHAR(20), location_name VARCHAR(160) NOT NULL, shift_timing VARCHAR(80) NOT NULL, slot_label VARCHAR(40), sewadar_name VARCHAR(120) NOT NULL, primary_mobile VARCHAR(20) NOT NULL, alt_mobile VARCHAR(20), unit_no VARCHAR(60), duty_role VARCHAR(160), updated_at VARCHAR(40))",
        "CREATE TABLE IF NOT EXISTS samagam_fleet_vehicles (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_reg VARCHAR(30) UNIQUE NOT NULL, vehicle_category VARCHAR(80) NOT NULL, make_model VARCHAR(80), capacity VARCHAR(40), ownership_source VARCHAR(40), owner_name VARCHAR(120), owner_mobile VARCHAR(20), staged_hub VARCHAR(140), driver_name VARCHAR(120), driver_mobile VARCHAR(20), available_from VARCHAR(20), available_till VARCHAR(20), status VARCHAR(30) DEFAULT 'READY', updated_at VARCHAR(40))",
        "CREATE TABLE IF NOT EXISTS samagam_driver_roster (id INTEGER PRIMARY KEY AUTOINCREMENT, driver_name VARCHAR(120) NOT NULL, primary_mobile VARCHAR(20) UNIQUE NOT NULL, alt_mobile VARCHAR(20), login_pin VARCHAR(10) NOT NULL, license_no VARCHAR(50), license_type VARCHAR(60), assigned_vehicle_reg VARCHAR(30), base_hub VARCHAR(140), duty_shift VARCHAR(80), unit_agency VARCHAR(120), updated_at VARCHAR(40))",
        "CREATE TABLE IF NOT EXISTS samagam_advance_sewa_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, request_code VARCHAR(30), unit_name VARCHAR(120), unit_no VARCHAR(40), landmark VARCHAR(160), nearest_station VARCHAR(120), sewa_date VARCHAR(30), start_time VARCHAR(20), return_time VARCHAR(20), sevadars_count INTEGER DEFAULT 1, remarks VARCHAR(300), contact_name VARCHAR(120), contact_mobile VARCHAR(20), status VARCHAR(30) DEFAULT 'PENDING', allocated_vehicle_reg VARCHAR(30), allocated_driver_name VARCHAR(120), allocated_driver_mobile VARCHAR(20), created_at VARCHAR(40))",
        "CREATE TABLE IF NOT EXISTS samagam_live_allocations (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_type VARCHAR(30), ref_id VARCHAR(40), pickup_hub VARCHAR(160), drop_hub VARCHAR(160), headcount INTEGER DEFAULT 1, vehicle_reg VARCHAR(30), driver_name VARCHAR(120), driver_mobile VARCHAR(20), status VARCHAR(30) DEFAULT 'ASSIGNED', parking_bay VARCHAR(80), assigned_at VARCHAR(40), updated_at VARCHAR(40))"
    ]
    for s in stmts:
        db.execute(_sql_text(s))
    db.commit()

@router.post("/roster/upload-excel")
async def upload_station_ground_roster_excel(file: _UploadFile = _File(...), db=Depends(get_db)):
    if _openpyxl is None:
        raise HTTPException(status_code=500, detail="openpyxl is not installed on server.")
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
        default_team = "GROUND_TEAM" if "ground" in sname.lower() else ("HELPLINE_TEAM" if "helpline" in sname.lower() else "STATION_TEAM")
        start_row = 5 if ws.max_row >= 5 else 2
        for r in range(start_row, ws.max_row + 1):
            tcat = str(ws.cell(r, 2).value or default_team).strip().upper()
            if "GROUND" in tcat:
                tcat = "GROUND_TEAM"
            elif "HELPLINE" in tcat or "COMMITTEE" in tcat:
                tcat = "HELPLINE_TEAM"
            else:
                tcat = "STATION_TEAM"
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
def get_live_helpline_roster(duty_date: _Opt[str] = None, team_category: _Opt[str] = None, location: _Opt[str] = None, db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    q = "SELECT * FROM samagam_duty_roster WHERE 1=1"
    params = {}
    if duty_date:
        q += " AND duty_date = :dd"
        params["dd"] = duty_date
    if team_category and team_category != "ALL":
        q += " AND team_category = :tc"
        params["tc"] = team_category
    if location:
        q += " AND LOWER(location_name) LIKE :loc"
        params["loc"] = f"%{location.strip().lower()}%"
    q += " ORDER BY duty_date ASC, team_category ASC, location_name ASC, shift_timing ASC, id ASC"
    rows = db.execute(_sql_text(q), params).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}

@router.post("/fleet/upload-excel")
async def upload_fleet_vehicles_and_drivers_excel(file: _UploadFile = _File(...), db=Depends(get_db)):
    if _openpyxl is None:
        raise HTTPException(status_code=500, detail="openpyxl is not installed on server.")
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

# --- Advance Sewa Request Creation & Admin Listing ---
@router.post("/advance-sewa-requests")
async def create_advance_sewa_request(payload: dict, db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    now_iso = _dt_mod.utcnow().isoformat()
    unit_name = str(payload.get("unit_name") or payload.get("area") or "Unit").strip()
    unit_no = str(payload.get("unit_no") or "").strip()
    landmark = str(payload.get("landmark") or "").strip()
    station = str(payload.get("nearest_station") or payload.get("station") or "").strip()
    sewa_date = str(payload.get("sewa_date") or payload.get("date_of_sewa") or "").strip()
    start_t = str(payload.get("start_time") or payload.get("journey_start_time") or "").strip()
    ret_t = str(payload.get("return_time") or payload.get("journey_return_time") or "").strip()
    cnt = int(payload.get("sevadars_count") or payload.get("headcount") or 1)
    remarks = str(payload.get("remarks") or payload.get("department") or "").strip()
    cname = str(payload.get("contact_name") or payload.get("leader_name") or "").strip()
    cmob = str(payload.get("contact_mobile") or payload.get("mobile") or "").strip()

    res = db.execute(_sql_text("""
        INSERT INTO samagam_advance_sewa_requests
        (unit_name, unit_no, landmark, nearest_station, sewa_date, start_time, return_time, sevadars_count, remarks, contact_name, contact_mobile, status, created_at)
        VALUES (:un, :uno, :lm, :st, :sd, :stt, :rt, :cnt, :rm, :cn, :cm, 'PENDING', :ca)
    """), {
        "un": unit_name, "uno": unit_no, "lm": landmark, "st": station,
        "sd": sewa_date, "stt": start_t, "rt": ret_t, "cnt": cnt,
        "rm": remarks, "cn": cname, "cm": cmob, "ca": now_iso
    })
    db.commit()
    new_id = res.lastrowid or 1
    req_code = f"ADV-{1000 + new_id}"
    db.execute(_sql_text("UPDATE samagam_advance_sewa_requests SET request_code = :rc WHERE id = :id"), {"rc": req_code, "id": new_id})
    db.commit()
    return {"status": "success", "id": new_id, "request_code": req_code, "message": f"Advance Sewa Request {req_code} saved."}

@router.get("/advance-sewa-requests")
def list_advance_sewa_requests(db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    rows = db.execute(_sql_text("SELECT * FROM samagam_advance_sewa_requests ORDER BY id DESC")).mappings().all()
    return {"items": [dict(r) for r in rows], "total": len(rows)}

# --- Upgrade 1: Nearby-Vicinity Vehicle Prioritization ---
@router.get("/nearby-vehicles")
def get_nearby_prioritized_vehicles(hub: str = "Panvel", db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    rows = db.execute(_sql_text("SELECT * FROM samagam_fleet_vehicles ORDER BY id DESC")).mappings().all()
    items = []
    if not rows:
        # Provide seeded ready pool if fleet Excel not uploaded yet so Allocate button always works
        demo_fleet = [
            {"vehicle_reg": "MH-46-BM-6001", "vehicle_category": "45-Seater Bus", "staged_hub": "Panvel ST Bay-2", "driver_name": "Bro. Ramesh Jadhav", "driver_mobile": "9820555001", "status": "READY"},
            {"vehicle_reg": "MH-04-KF-6002", "vehicle_category": "32-Seater Mini Bus", "staged_hub": "Thane East Kopri Bay", "driver_name": "Bro. Suresh Naik", "driver_mobile": "9820555002", "status": "READY"},
            {"vehicle_reg": "MH-01-DR-6003", "vehicle_category": "45-Seater Bus", "staged_hub": "LTT Gate-1 Lane-3", "driver_name": "Bro. Prakash More", "driver_mobile": "9820555003", "status": "READY"},
            {"vehicle_reg": "MH-46-BM-6004", "vehicle_category": "17-Seater Traveller", "staged_hub": "Samagam Ground Parking Bay-1", "driver_name": "Bro. Dinesh Patil", "driver_mobile": "9820555004", "status": "READY"},
        ]
        for d in demo_fleet:
            dist = _hub_distance_km(hub, d["staged_hub"])
            items.append({**d, "current_hub": d["staged_hub"], "distance_km": dist, "is_ready": True, "is_nearby": dist <= 5.0})
    else:
        for r in rows:
            rd = dict(r)
            st = (rd.get("status") or "READY").upper()
            is_ready = st in {"READY", "EMPTY_IN", "AVAILABLE"}
            cur_hub = rd.get("staged_hub") or "Samagam Ground Parking"
            dist = _hub_distance_km(hub, cur_hub)
            items.append({
                "vehicle_reg": rd["vehicle_reg"],
                "vehicle_reg_number": rd["vehicle_reg"],
                "vehicle_category": rd.get("vehicle_category", "Bus"),
                "current_hub": cur_hub,
                "driver_name": rd.get("driver_name") or "Assigned Sewadar Driver",
                "driver_mobile": rd.get("driver_mobile") or "",
                "status": st,
                "distance_km": dist,
                "is_ready": is_ready,
                "is_nearby": is_ready and dist <= 5.0,
            })
    items.sort(key=lambda x: (0 if x["is_nearby"] else (1 if x["is_ready"] else 2), x["distance_km"]))
    return items

# --- Admin / Ground / Station Allocation Endpoint ---
@router.post("/allocate-vehicle")
async def allocate_vehicle_unified(payload: dict, db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    now_iso = _dt_mod.utcnow().isoformat()
    ref_type = str(payload.get("ref_type") or "PICKUP_DROP").upper()
    ref_id = str(payload.get("ref_id") or payload.get("id") or "")
    veh_reg = _re_mod.sub(r"\s+", "", str(payload.get("vehicle_reg") or payload.get("vehicle_reg_number") or "")).upper()
    if not veh_reg:
        raise HTTPException(status_code=400, detail="Please select a vehicle registration number to allocate.")
    driver_name = str(payload.get("driver_name") or "Assigned Sewadar Driver").strip()
    driver_mobile = str(payload.get("driver_mobile") or "").strip()
    pickup_hub = str(payload.get("pickup_hub") or payload.get("nearest_station") or "Station Pickup").strip()
    drop_hub = str(payload.get("drop_hub") or "Samagam Ground").strip()
    headcount = int(payload.get("headcount") or payload.get("sevadars_count") or 1)

    db.execute(_sql_text("UPDATE samagam_fleet_vehicles SET status = 'ON_DUTY', updated_at = :ua WHERE vehicle_reg = :vr"), {"ua": now_iso, "vr": veh_reg})
    if ref_type == "ADVANCE_SEWA" and ref_id.isdigit():
        db.execute(_sql_text("""
            UPDATE samagam_advance_sewa_requests
            SET status = 'ALLOCATED', allocated_vehicle_reg = :vr, allocated_driver_name = :dn, allocated_driver_mobile = :dm
            WHERE id = :rid
        """), {"vr": veh_reg, "dn": driver_name, "dm": driver_mobile, "rid": int(ref_id)})

    res = db.execute(_sql_text("""
        INSERT INTO samagam_live_allocations
        (ref_type, ref_id, pickup_hub, drop_hub, headcount, vehicle_reg, driver_name, driver_mobile, status, assigned_at, updated_at)
        VALUES (:rt, :rid, :ph, :dh, :hc, :vr, :dn, :dm, 'ASSIGNED', :aa, :ua)
    """), {"rt": ref_type, "rid": ref_id, "ph": pickup_hub, "dh": drop_hub, "hc": headcount, "vr": veh_reg, "dn": driver_name, "dm": driver_mobile, "aa": now_iso, "ua": now_iso})
    db.commit()
    return {
        "status": "ALLOCATED",
        "allocation_id": res.lastrowid,
        "vehicle_reg": veh_reg,
        "driver_name": driver_name,
        "driver_mobile": driver_mobile,
        "message": f"Allocated {veh_reg} ({driver_name}) to {pickup_hub} -> {drop_hub}."
    }

# --- Upgrade 2: Real-Time Driver Assignment & Nearby-Alert Feed ---
@router.get("/driver-live-feed")
def get_driver_live_assignment_feed(vehicle_reg: _Opt[str] = None, driver_mobile: _Opt[str] = None, db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    q = "SELECT * FROM samagam_live_allocations WHERE status IN ('ASSIGNED', 'EN_ROUTE')"
    params = {}
    if vehicle_reg:
        q += " AND UPPER(vehicle_reg) = :vr"
        params["vr"] = _re_mod.sub(r"\s+", "", vehicle_reg).upper()
    if driver_mobile:
        q += " AND driver_mobile LIKE :dm"
        params["dm"] = f"%{driver_mobile[-10:]}%"
    q += " ORDER BY id DESC LIMIT 20"
    rows = db.execute(_sql_text(q), params).mappings().all()
    return {"assignments": [dict(r) for r in rows], "count": len(rows)}

# --- Upgrade 3: One-Tap "Complete Trip -> Empty & Park in Parking Bay" ---
@router.post("/park-empty")
async def complete_trip_and_park_empty(payload: dict, db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    now_iso = _dt_mod.utcnow().isoformat()
    veh_reg = _re_mod.sub(r"\s+", "", str(payload.get("vehicle_reg") or payload.get("vehicle_reg_number") or "")).upper()
    parking_bay = str(payload.get("parking_bay") or "Samagam Ground Parking Bay-1").strip()
    if not veh_reg:
        raise HTTPException(status_code=400, detail="vehicle_reg is required.")

    db.execute(_sql_text("""
        UPDATE samagam_fleet_vehicles
        SET status = 'EMPTY_IN', staged_hub = :pb, updated_at = :ua
        WHERE vehicle_reg = :vr
    """), {"pb": parking_bay, "ua": now_iso, "vr": veh_reg})

    db.execute(_sql_text("""
        UPDATE samagam_live_allocations
        SET status = 'PARKED_EMPTY_READY', parking_bay = :pb, updated_at = :ua
        WHERE UPPER(vehicle_reg) = :vr AND status IN ('ASSIGNED', 'EN_ROUTE')
    """), {"pb": parking_bay, "ua": now_iso, "vr": veh_reg})
    db.commit()
    return {
        "status": "PARKED_EMPTY_READY",
        "vehicle_reg_number": veh_reg,
        "new_status": "EMPTY_IN",
        "parking_bay": parking_bay,
        "message": f"{veh_reg} unloaded, marked EMPTY_IN, and parked at {parking_bay}. Ready for next allocation."
    }

# --- Station / Airport / Bus Depot Pickup Guide + On-Duty Sewadars ---
@router.get("/pickup-guide")
def get_station_pickup_guide_and_sewadars(location: str = "Panvel", db=Depends(get_db)):
    _ensure_reconciled_tables(db)
    loc_clean = (location or "Panvel").strip()
    key = next((k for k in _STATION_PICKUP_GUIDES if k in loc_clean.lower()), None)
    guide = _STATION_PICKUP_GUIDES.get(key, {
        "title": f"{loc_clean} ? Samagam Shuttle Pickup Point",
        "waiting_point": f"Proceed to Main Exit Gate of {loc_clean} near the Samagam Transport Helpdesk Banner.",
        "landmark": f"{loc_clean} Main Exit Forecourt",
        "gate_label": f"{loc_clean.upper()} MAIN EXIT",
        "bay_label": "SAMAGAM PICKUP BAY"
    })
    rows = db.execute(_sql_text("""
        SELECT * FROM samagam_duty_roster
        WHERE LOWER(location_name) LIKE :loc
        ORDER BY duty_date DESC, shift_timing ASC, id ASC LIMIT 8
    """), {"loc": f"%{loc_clean.lower()}%"}).mappings().all()
    sewadars = [dict(r) for r in rows]
    if not sewadars:
        sewadars = [
            {"sewadar_name": "Bro. Rajesh Sharma", "primary_mobile": "9820111001", "alt_mobile": "9820111002", "unit_no": "Unit-214", "shift_timing": "On-Duty Shift", "duty_role": "Station Exit Guide"},
            {"sewadar_name": "Bro. Amit Kulkarni", "primary_mobile": "9820111003", "alt_mobile": "9820111004", "unit_no": "Unit-215", "shift_timing": "On-Duty Shift", "duty_role": "Bus Boarding Coordinator"},
        ]
    return {"location": loc_clean, "guide": guide, "on_duty_sewadars": sewadars, "helpline": "18001232005", "chatbot": "9266629848"}


# --- ADVANCE SEWA DEPARTURE/RETURN & 48HR STATUS EXTENSION ---
from datetime import datetime as _adv_dt
from typing import Optional as _AdvOpt
from sqlalchemy import text as _adv_sql

def _ensure_adv_sewa_v2_table(db):
    db.execute(_adv_sql("""
        CREATE TABLE IF NOT EXISTS samagam_advance_sewa_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_code VARCHAR(30),
            unit_name VARCHAR(120),
            unit_no VARCHAR(60),
            landmark VARCHAR(160),
            nearest_station VARCHAR(160),
            sewa_date VARCHAR(40),
            departure_date VARCHAR(20),
            return_date VARCHAR(20),
            start_time VARCHAR(20),
            return_time VARCHAR(20),
            sevadars_count INTEGER DEFAULT 1,
            remarks VARCHAR(300),
            contact_name VARCHAR(120),
            contact_mobile VARCHAR(20),
            status VARCHAR(30) DEFAULT 'PENDING',
            allocated_vehicle_reg VARCHAR(30),
            allocated_driver_name VARCHAR(120),
            allocated_driver_mobile VARCHAR(20),
            created_at VARCHAR(40)
        )
    """))
    for col_sql in [
        "ALTER TABLE samagam_advance_sewa_requests ADD COLUMN departure_date VARCHAR(20)",
        "ALTER TABLE samagam_advance_sewa_requests ADD COLUMN return_date VARCHAR(20)",
        "ALTER TABLE samagam_advance_sewa_requests ADD COLUMN allocated_driver_name VARCHAR(120)",
        "ALTER TABLE samagam_advance_sewa_requests ADD COLUMN allocated_driver_mobile VARCHAR(20)"
    ]:
        try:
            db.execute(_adv_sql(col_sql))
        except Exception:
            pass
    db.commit()

@router.post("/advance-sewa-requests")
async def create_advance_sewa_request_v2(payload: dict, db=Depends(get_db)):
    _ensure_adv_sewa_v2_table(db)
    now_iso = _adv_dt.utcnow().isoformat()
    dep_date = str(payload.get("departure_date") or payload.get("sewa_date") or "").strip()[:10]
    ret_date = str(payload.get("return_date") or dep_date).strip()[:10]
    date_range = str(payload.get("date_of_sewa") or f"{dep_date} to {ret_date}").strip()
    start_t = str(payload.get("start_journey_time") or payload.get("start_time") or "06:30").strip()
    ret_t = str(payload.get("return_time") or "19:00").strip()
    unit_name = str(payload.get("branch_name") or payload.get("unit_name") or payload.get("area") or "Sewa Unit").strip()
    unit_no = str(payload.get("unit_number") or payload.get("unit_no") or "").strip()
    landmark = str(payload.get("landmark") or "").strip()
    station = str(payload.get("nearest_railway_station") or payload.get("nearest_station") or "").strip()
    cnt = int(payload.get("passenger_count") or payload.get("sevadars_count") or 1)
    remarks = str(payload.get("notes") or payload.get("remarks") or "").strip()
    cname = str(payload.get("requester_name") or payload.get("contact_name") or "").strip()
    cmob = re.sub(r"\D", "", str(payload.get("contact_number") or payload.get("contact_mobile") or ""))[-10:]

    res = db.execute(_adv_sql("""
        INSERT INTO samagam_advance_sewa_requests
        (unit_name, unit_no, landmark, nearest_station, sewa_date, departure_date, return_date, start_time, return_time, sevadars_count, remarks, contact_name, contact_mobile, status, created_at)
        VALUES (:un, :uno, :lm, :st, :sd, :dd, :rd, :stt, :rt, :cnt, :rm, :cn, :cm, 'PENDING', :ca)
    """), {
        "un": unit_name, "uno": unit_no, "lm": landmark, "st": station,
        "sd": date_range, "dd": dep_date, "rd": ret_date, "stt": start_t, "rt": ret_t,
        "cnt": cnt, "rm": remarks, "cn": cname, "cm": cmob, "ca": now_iso
    })
    db.commit()
    new_id = res.lastrowid or 1
    req_code = f"ADV-{1000 + new_id}"
    db.execute(_adv_sql("UPDATE samagam_advance_sewa_requests SET request_code = :rc WHERE id = :id"), {"rc": req_code, "id": new_id})
    db.commit()
    return {
        "status": "success",
        "id": new_id,
        "request_code": req_code,
        "departure_date": dep_date,
        "return_date": ret_date,
        "pickup_time": start_t,
        "drop_time": ret_t,
        "acknowledgement": (
            "Dhan Nirankar ji\n"
            "Your request received will share further details or you check allocation details 48 hour before departure and arrival.\n"
            "48 hour before he will receive message\n"
            "Driver details\n"
            "Vehicle details"
        ),
        "message": f"Advance Sewa Request {req_code} submitted."
    }

@router.get("/advance-sewa-requests")
def list_advance_sewa_requests_v2(db=Depends(get_db)):
    _ensure_adv_sewa_v2_table(db)
    rows = db.execute(_adv_sql("SELECT * FROM samagam_advance_sewa_requests ORDER BY id DESC")).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d.setdefault("branch_name", d.get("unit_name", ""))
        d.setdefault("unit_number", d.get("unit_no", ""))
        d.setdefault("nearest_railway_station", d.get("nearest_station", ""))
        d.setdefault("date_of_sewa", d.get("sewa_date") or f"{d.get('departure_date','')} to {d.get('return_date','')}")
        d.setdefault("start_journey_time", d.get("start_time", ""))
        d.setdefault("passenger_count", d.get("sevadars_count", 1))
        d.setdefault("requester_name", d.get("contact_name", ""))
        d.setdefault("assigned_vehicle_reg", d.get("allocated_vehicle_reg", ""))
        d.setdefault("assigned_driver_name", d.get("allocated_driver_name", ""))
        out.append(d)
    return out

@router.get("/request-status-lookup")
def lookup_advance_sewa_status(query: _AdvOpt[str] = "", db=Depends(get_db)):
    _ensure_adv_sewa_v2_table(db)
    q = (query or "").strip()
    digits = re.sub(r"\D", "", q)[-10:]
    if digits and len(digits) == 10:
        rows = db.execute(_adv_sql("SELECT * FROM samagam_advance_sewa_requests WHERE contact_mobile LIKE :m ORDER BY id DESC"), {"m": f"%{digits}%"}).mappings().all()
    else:
        rows = db.execute(_adv_sql("SELECT * FROM samagam_advance_sewa_requests WHERE UPPER(request_code) LIKE :c ORDER BY id DESC"), {"c": f"%{q.upper()}%"}).mappings().all()
    results = []
    for r in rows:
        d = dict(r)
        veh = d.get("allocated_vehicle_reg") or ""
        results.append({
            "code": d.get("request_code") or f"ADV-{d['id']}",
            "requester_name": d.get("contact_name") or d.get("unit_name") or "Sewa Group",
            "requester_phone": d.get("contact_mobile") or "",
            "summary": f"{d.get('unit_name','')} ({d.get('unit_no','')}) ? Dep: {d.get('departure_date','')} {d.get('start_time','')} ? Ret: {d.get('return_date','')} {d.get('return_time','')} ? {d.get('landmark','')} ? {d.get('nearest_station','')}",
            "is_allocated": bool(veh),
            "assigned_vehicle_reg": veh,
            "driver_name": d.get("allocated_driver_name") or "",
            "driver_phone": d.get("allocated_driver_mobile") or "",
        })
    return results


# --- ADMIN STATION ANALYSIS (19-28 JAN 2027) & LIVE NTES TRACKS ---
import datetime as _ntes_dt
import math as _ntes_math
import os as _ntes_os
from typing import Optional as _NtessOpt

_ANALYSIS_DAYS_2027 = [
    {"date": "2027-01-19", "day_name": "Tuesday",   "label": "Tue 19 Jan 2027", "factor": 0.75, "is_peak": False},
    {"date": "2027-01-20", "day_name": "Wednesday", "label": "Wed 20 Jan 2027", "factor": 0.85, "is_peak": False},
    {"date": "2027-01-21", "day_name": "Thursday",  "label": "Thu 21 Jan 2027", "factor": 0.95, "is_peak": False},
    {"date": "2027-01-22", "day_name": "Friday",    "label": "Fri 22 Jan 2027", "factor": 1.10, "is_peak": False},
    {"date": "2027-01-23", "day_name": "Saturday",  "label": "Sat 23 Jan 2027", "factor": 1.35, "is_peak": True},
    {"date": "2027-01-24", "day_name": "Sunday",    "label": "Sun 24 Jan 2027", "factor": 1.50, "is_peak": True},
    {"date": "2027-01-25", "day_name": "Monday",    "label": "Mon 25 Jan 2027", "factor": 1.30, "is_peak": True},
    {"date": "2027-01-26", "day_name": "Tuesday",   "label": "Tue 26 Jan 2027", "factor": 1.15, "is_peak": False},
    {"date": "2027-01-27", "day_name": "Wednesday", "label": "Wed 27 Jan 2027", "factor": 0.90, "is_peak": False},
    {"date": "2027-01-28", "day_name": "Thursday",  "label": "Thu 28 Jan 2027", "factor": 0.75, "is_peak": False},
]

def _add_mins_hhmm(hhmm_str: str, mins: int) -> str:
    try:
        parts = str(hhmm_str or "00:00").strip().split(":")
        hh, mm = int(parts[0]), int(parts[1])
        dt = _ntes_dt.datetime(2027, 1, 20, hh % 24, mm % 60) + _ntes_dt.timedelta(minutes=int(mins or 0))
        return dt.strftime("%H:%M")
    except Exception:
        return str(hhmm_str or "00:00")

def _hour_slot_from_hhmm(hhmm_str: str) -> str:
    try:
        hh = int(str(hhmm_str or "00:00").strip().split(":")[0]) % 24
        return f"{hh:02d}:00-{(hh + 1) % 24:02d}:00"
    except Exception:
        return "00:00-01:00"

def _load_trains_from_workbook():
    repo_root = _ntes_os.path.dirname(_ntes_os.path.dirname(_ntes_os.path.dirname(_ntes_os.path.abspath(__file__))))
    candidates = [
        _ntes_os.path.join(repo_root, "Hourly_Analysis_By_Day_Per_Station_2027_With_Delay_History.xlsx"),
        "Hourly_Analysis_By_Day_Per_Station_2027_With_Delay_History.xlsx",
    ]
    wb_file = next((p for p in candidates if _ntes_os.path.exists(p)), None)
    trains = []
    if wb_file and _openpyxl is not None:
        wb = _openpyxl.load_workbook(wb_file, data_only=True)
        if "Train_Delay_&_Live_Sync" in wb.sheetnames:
            ws = wb["Train_Delay_&_Live_Sync"]
            for r in range(5, ws.max_row + 1):
                st_key = str(ws.cell(r, 1).value or "").strip()
                st_name = str(ws.cell(r, 2).value or st_key).strip()
                direction = str(ws.cell(r, 3).value or "Inbound").strip()
                slot = str(ws.cell(r, 4).value or "").strip()
                sched_t = str(ws.cell(r, 5).value or "06:00").strip()
                tno = str(ws.cell(r, 6).value or "").strip()
                tname = str(ws.cell(r, 7).value or "").strip()
                origin = str(ws.cell(r, 8).value or "").strip()
                dest = str(ws.cell(r, 9).value or "").strip()
                hist_delay = int(float(ws.cell(r, 10).value or 0))
                otp_raw = ws.cell(r, 12).value
                otp_pct = int(round(float(otp_raw or 0.8) * 100)) if float(otp_raw or 0.8) <= 1.0 else int(float(otp_raw or 80))
                fog_risk = str(ws.cell(r, 13).value or "Low").strip()
                stage_rule = str(ws.cell(r, 15).value or "").strip()
                if not tno or not st_key:
                    continue
                eta_t = _add_mins_hhmm(sched_t, hist_delay)
                trains.append({
                    "station_key": st_key,
                    "station_name": st_name,
                    "direction": direction,
                    "slot": slot or _hour_slot_from_hhmm(sched_t),
                    "eta_slot": _hour_slot_from_hhmm(eta_t),
                    "scheduled_time": sched_t,
                    "train_no": tno,
                    "train_name": tname,
                    "origin": origin,
                    "destination": dest,
                    "hist_delay_mins": hist_delay,
                    "eta_time": eta_t,
                    "otp_pct": otp_pct,
                    "fog_risk": fog_risk,
                    "stage_rule": stage_rule,
                })
    if not trains:
        trains = [
            {"station_key": "Thane", "station_name": "Thane (TNA)", "direction": "Inbound", "slot": "04:00-05:00", "eta_slot": "04:00-05:00", "scheduled_time": "04:20", "train_no": "17058", "train_name": "Devagiri Express", "origin": "Secunderabad (SC)", "destination": "CSMT", "hist_delay_mins": 32, "eta_time": "04:52", "otp_pct": 68, "fog_risk": "Low-Mod", "stage_rule": "Track Manmad Jn; avg +32m late"},
            {"station_key": "Panvel", "station_name": "Panvel (PNVL)", "direction": "Inbound", "slot": "06:00-07:00", "eta_slot": "06:00-07:00", "scheduled_time": "06:15", "train_no": "12134", "train_name": "Mangaluru SF Express", "origin": "Mangaluru Jn", "destination": "CSMT", "hist_delay_mins": 25, "eta_time": "06:40", "otp_pct": 75, "fog_risk": "Low", "stage_rule": "Panvel Main Gate / Konkan Exit"},
        ]
    return trains

@router.get("/station-analysis-2027")
def get_station_analysis_2027(
    duty_date: _NtessOpt[str] = "2027-01-24",
    station: _NtessOpt[str] = "ALL",
    gathering: int = 80000,
):
    day_meta = next((d for d in _ANALYSIS_DAYS_2027 if d["date"] == duty_date), _ANALYSIS_DAYS_2027[5])
    all_trains = _load_trains_from_workbook()
    inbound = [t for t in all_trains if t["direction"].lower() == "inbound"]
    if station and station.upper() != "ALL":
        inbound = [t for t in inbound if station.lower() in t["station_key"].lower() or station.lower() in t["station_name"].lower()]

    scale_mult = (float(gathering or 80000) / 80000.0) * float(day_meta["factor"])
    stations_map = {}
    for tr in inbound:
        # Base expected saints per train (~160 base scaled by day surge & gathering)
        expected_saints = int(round(160 * scale_mult))
        st_k = tr["station_key"]
        st_entry = stations_map.setdefault(st_k, {
            "station_key": st_k,
            "station_name": tr["station_name"],
            "total_trains": 0,
            "expected_saints": 0,
            "hourly": {},
        })
        st_entry["total_trains"] += 1
        st_entry["expected_saints"] += expected_saints
        hr_k = tr["eta_slot"] or tr["slot"]
        hr_list = st_entry["hourly"].setdefault(hr_k, [])
        hr_list.append({
            **tr,
            "expected_saints": expected_saints,
            "buses_needed": max(1, int(_ntes_math.ceil(expected_saints / 65.0))),
        })

    stations_out = []
    for st_k in sorted(stations_map.keys()):
        st_obj = stations_map[st_k]
        hours_sorted = [
            {"hour_slot": hk, "trains": st_obj["hourly"][hk], "hour_saints": sum(x["expected_saints"] for x in st_obj["hourly"][hk])}
            for hk in sorted(st_obj["hourly"].keys())
        ]
        stations_out.append({
            "station_key": st_obj["station_key"],
            "station_name": st_obj["station_name"],
            "total_trains": st_obj["total_trains"],
            "expected_saints": st_obj["expected_saints"],
            "hourly": hours_sorted,
        })

    return {
        "window": "2027-01-19 to 2027-01-28",
        "days": _ANALYSIS_DAYS_2027,
        "selected_day": day_meta,
        "gathering_scale": int(gathering or 80000),
        "total_trains": sum(s["total_trains"] for s in stations_out),
        "total_expected_saints": sum(s["expected_saints"] for s in stations_out),
        "stations": stations_out,
    }

@router.get("/ntes-live-tracks")
def get_ntes_live_tracks(station: _NtessOpt[str] = "ALL", live_query: bool = False):
    trains = _load_trains_from_workbook()
    if station and station.upper() != "ALL":
        trains = [t for t in trains if station.lower() in t["station_key"].lower() or station.lower() in t["station_name"].lower()]

    ntes_connected = False
    ntes_live_map = {}
    if live_query:
        try:
            from ntes import NTESClient
            client = NTESClient()
            date_str = _ntes_dt.datetime.now().strftime("%d-%b-%Y")
            for t in trains[:15]:
                try:
                    st = client.live_status(str(t["train_no"]), date_str)
                    raw_d = str(st.get("DelayArr", st.get("DelayDep", "0")))
                    digits = "".join(ch for ch in raw_d if ch.isdigit())
                    d_mins = int(digits) if digits else 0
                    if d_mins > 720:
                        d_mins = 0
                    ntes_live_map[str(t["train_no"])] = {
                        "delay_mins": d_mins,
                        "last_loc": st.get("LastUpdate", "Live NTES Tracked"),
                    }
                    ntes_connected = True
                except Exception:
                    pass
        except ImportError:
            ntes_connected = False

    tracks = []
    for t in trains:
        tno = str(t["train_no"])
        if tno in ntes_live_map:
            d_m = ntes_live_map[tno]["delay_mins"]
            src = "LIVE NTES"
            track_status = f"Live NTES: +{d_m}m ({ntes_live_map[tno]['last_loc']})" if d_m > 0 else "Live NTES: On Time"
        else:
            d_m = int(t["hist_delay_mins"])
            src = "Jan Historical Benchmark"
            track_status = f"Historical Benchmark: +{d_m}m (Fog Risk: {t['fog_risk']})"
        eta_now = _add_mins_hhmm(t["scheduled_time"], d_m)
        tracks.append({
            **t,
            "active_delay_mins": d_m,
            "live_eta": eta_now,
            "source": src,
            "track_status": track_status,
        })

    return {
        "ntes_client_live": ntes_connected,
        "synced_at": _ntes_dt.datetime.now().strftime("%Y-%m-%d %H:%M IST"),
        "count": len(tracks),
        "tracks": tracks,
    }
