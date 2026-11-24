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

from app.database import get_db
from app.models import (
    Territory, StationDemand, TurnaroundMovement,
    FuelLog, MaintenanceTicket, Vehicle, Volunteer,
    CrewDutyShift, VehicleWearInspection, MSRTCSpotCashVoucher,
    StationCashFloat, HiredRollingContract, GroundStationIntercom,
    Journey, TelemetryPing, PickupDropVehicleRequest
)
from app.services.turnaround_service import record_turnaround_movement

router = APIRouter(prefix="/api/operations", tags=["Operations, Turnaround & Live Telemetry"])


@router.get("/hubs")
def list_operation_hubs(db: Session = Depends(get_db)):
    hubs = db.query(Territory).order_by(Territory.id.asc()).all()
    return [
        {
            "id": h.id,
            "hub_code": h.hub_code,
            "hub_name": h.hub_name,
            "hub_type": getattr(h, "hub_type", "TRANSIT"),
            "latitude": h.latitude,
            "longitude": h.longitude,
        }
        for h in hubs
    ]


@router.get("/intercom")
def get_intercom_messages(hub: str = "ALL", db: Session = Depends(get_db)):
    q = db.query(GroundStationIntercom)
    if hub and hub != "ALL":
        q = q.filter((GroundStationIntercom.channel_hub == hub) | (GroundStationIntercom.channel_hub == "ALL_STATIONS"))
    msgs = q.order_by(GroundStationIntercom.id.desc()).limit(60).all()
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