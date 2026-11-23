import secrets
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



# ==============================================================================
# END-TO-END OPERATIONS PIPELINE & CHRONOLOGICAL SEQUENCE ENGINE
# ==============================================================================

SEQUENCE_STAGES = [
    {
        "step": 1,
        "key": "INTAKE_DEMAND",
        "title": "1. Request & Demand Intake",
        "owner_team": "Devotee / Station / Dept",
        "description": "Pickup/Drop, Advance Sewa, or Station Crowd Demand logged into Central Queue."
    },
    {
        "step": 2,
        "key": "DISPATCH_ASSIGNED",
        "title": "2. Fleet Allocation & Dispatch",
        "owner_team": "Control Room / Ground Team",
        "description": "Bus & Driver assigned; vehicle dispatched empty or staged for boarding."
    },
    {
        "step": 3,
        "key": "IN_TRANSIT_LOADED",
        "title": "3. Boarding & Live GPS Transit",
        "owner_team": "Station Team & Driver App",
        "description": "Pilgrims boarded; Driver started trip with 180s live GPS telemetry."
    },
    {
        "step": 4,
        "key": "GATE_UNLOADED_VERIFIED",
        "title": "4. Venue Gate Unload & Audit",
        "owner_team": "Gate Keeper & Ground Team",
        "description": "Bus arrived at Samagam Gate, pilgrims unloaded, MSRTC ETM voucher verified."
    },
    {
        "step": 5,
        "key": "TURNAROUND_FUEL_SAFETY",
        "title": "5. Fuel, Safety & Loop Return",
        "owner_team": "Diesel & Workshop Marshall",
        "description": "Pre-trip tire/brake check & diesel refill before next shuttle loop."
    },
    {
        "step": 6,
        "key": "EXIT_AND_SETTLEMENT",
        "title": "6. Outward Exit & Accounts Billing",
        "owner_team": "Gate Keeper & Accounts Cell",
        "description": "24h Rolling Contract exit odometer logged & final bill settled."
    }
]


@router.get("/pipeline/live-board")
def get_live_operations_pipeline(db: Session = Depends(get_db)):
    """Returns the complete 6-stage chronological sequence with live counts, items & next-action triggers."""
    from app.models import (
        PickupDropVehicleRequest, AdvanceSewaVehicleRequest,
        DepartmentVehicleRequisition, MSRTCSpotCashVoucher,
        HiredRollingContract
    )

    pending_demands = db.query(StationDemand).filter(StationDemand.status == "PENDING").order_by(StationDemand.id.desc()).all()
    pending_adv = db.query(AdvanceSewaVehicleRequest).filter(AdvanceSewaVehicleRequest.status == "PENDING_ALLOCATION").all()
    pending_dept = db.query(DepartmentVehicleRequisition).filter(DepartmentVehicleRequisition.status == "PENDING_ALLOCATION").all()

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
                "count": len(pending_demands) + len(pending_adv) + len(pending_dept),
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
                "advance_sewa": [
                    {
                        "id": a.id,
                        "code": a.request_code,
                        "name": a.requester_name,
                        "phone": a.contact_number,
                        "branch": f"{a.branch_name} (Unit {a.unit_number})",
                        "station": a.nearest_railway_station,
                        "schedule": f"{a.date_of_sewa} {a.start_journey_time}-{a.return_time}",
                        "pax": a.passenger_count
                    }
                    for a in pending_adv
                ]
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
    """Moves a vehicle or demand cleanly to the next valid step in the 6-stage sequence."""
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
                from app.models import PickupDropVehicleRequest, AdvanceSewaVehicleRequest
                pd = db.query(PickupDropVehicleRequest).filter(PickupDropVehicleRequest.request_code == dem.demand_code).first()
                if pd:
                    pd.status = "DISPATCHED"
                    pd.assigned_vehicle_reg = veh.vehicle_reg_number
                adv = db.query(AdvanceSewaVehicleRequest).filter(AdvanceSewaVehicleRequest.request_code == dem.demand_code).first()
                if adv:
                    adv.status = "ALLOCATED"
                    adv.assigned_vehicle_reg = veh.vehicle_reg_number
                    adv.assigned_driver_name = veh.driver_name
                    adv.assigned_driver_phone = veh.driver_phone
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
