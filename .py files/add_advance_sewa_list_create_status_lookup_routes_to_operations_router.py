# ... existing code ...
from app.models import (
    Territory, StationDemand, TurnaroundMovement,
    FuelLog, MaintenanceTicket, Vehicle, Volunteer,
    CrewDutyShift, VehicleWearInspection, MSRTCSpotCashVoucher,
    StationCashFloat, HiredRollingContract, GroundStationIntercom,
    Journey, TelemetryPing, AdvanceSewaVehicleRequest, PickupDropVehicleRequest
)
from app.schemas import (
# ... existing code ...
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


@router.get("/advance-sewa-requests")
def list_advance_sewa_requests(db: Session = Depends(get_db)):
    """Returns Advance Sewa transport requests from the central database."""
    rows = db.query(AdvanceSewaVehicleRequest).order_by(AdvanceSewaVehicleRequest.id.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "request_code": r.request_code,
            "requester_name": r.requester_name,
            "contact_number": r.contact_number,
            "branch_name": r.branch_name,
            "unit_number": r.unit_number,
            "landmark": r.landmark,
            "nearest_railway_station": r.nearest_railway_station,
            "date_of_sewa": r.date_of_sewa,
            "start_journey_time": r.start_journey_time,
            "return_time": r.return_time,
            "passenger_count": r.passenger_count,
            "notes": r.notes or "",
            "status": r.status,
            "assigned_vehicle_reg": r.assigned_vehicle_reg,
            "assigned_driver_name": r.assigned_driver_name,
            "assigned_driver_phone": r.assigned_driver_phone,
        }
        for r in rows
    ]


@router.post("/advance-sewa-requests")
def create_advance_sewa_request(data: dict, db: Session = Depends(get_db)):
    """Creates a new Advance Sewa request and syncs a demand record into StationDemand."""
    code = f"ADV-{secrets.randbelow(9000) + 1000}"
    pax = int(data.get("passenger_count") or 1)
    hub_name = str(data.get("nearest_railway_station") or "Panvel Junction (PNVL)").strip()
    branch = str(data.get("branch_name") or "Branch").strip()
    unit = str(data.get("unit_number") or "Unit-01").strip()
    requester = str(data.get("requester_name") or "Sevadar").strip()

    row = AdvanceSewaVehicleRequest(
        request_code=code,
        requester_name=requester,
        contact_number=str(data.get("contact_number") or "").strip(),
        branch_name=branch,
        unit_number=unit,
        landmark=str(data.get("landmark") or "").strip(),
        nearest_railway_station=hub_name,
        date_of_sewa=str(data.get("date_of_sewa") or "").strip(),
        start_journey_time=str(data.get("start_journey_time") or "").strip(),
        return_time=str(data.get("return_time") or "").strip(),
        passenger_count=pax,
        notes=str(data.get("notes") or "").strip() or None,
        status="PENDING_ALLOCATION",
    )
    db.add(row)

    matched_hub = db.query(Territory).filter(Territory.hub_name == hub_name).first()
    if not matched_hub:
        matched_hub = db.query(Territory).first()
    if matched_hub:
        db.add(StationDemand(
            demand_code=code,
            hub_name=matched_hub.hub_name,
            waiting_passenger_count=pax,
            recommended_buses=f"Advance Sewa ({branch} / {unit})",
            priority="NORMAL",
            status="PENDING",
            requested_by=f"{requester} ({branch} / {unit})",
            notes=f"Advance Sewa on {row.date_of_sewa} ({row.start_journey_time}-{row.return_time})",
        ))

    db.commit()
    db.refresh(row)
    return {"status": "CREATED", "request_code": code, "id": row.id}


@router.get("/request-status-lookup")
def lookup_request_status(query: str = "", db: Session = Depends(get_db)):
    """Looks up Pickup/Drop and Advance Sewa requests by 10-digit mobile number or request code."""
    q = str(query or "").strip()
    if not q:
        return []
    digits = "".join(ch for ch in q if ch.isdigit())
    phone_q = digits[-10:] if len(digits) >= 10 else q
    code_q = q.upper()

    results = []
    adv_rows = db.query(AdvanceSewaVehicleRequest).filter(
        (AdvanceSewaVehicleRequest.contact_number.contains(phone_q))
        | (AdvanceSewaVehicleRequest.request_code.ilike(f"%{code_q}%"))
    ).order_by(AdvanceSewaVehicleRequest.id.desc()).limit(15).all()
    for a in adv_rows:
        results.append({
            "code": a.request_code,
            "category": "Advance Sewa",
            "summary": f"{a.branch_name} (Unit {a.unit_number}) • {a.nearest_railway_station} • {a.date_of_sewa}",
            "requester_name": a.requester_name,
            "requester_phone": a.contact_number,
            "status": a.status,
            "is_allocated": bool(a.assigned_vehicle_reg),
            "assigned_vehicle_reg": a.assigned_vehicle_reg,
            "driver_name": a.assigned_driver_name,
            "driver_phone": a.assigned_driver_phone,
        })

    pd_rows = db.query(PickupDropVehicleRequest).filter(
        (PickupDropVehicleRequest.requester_phone.contains(phone_q))
        | (PickupDropVehicleRequest.request_code.ilike(f"%{code_q}%"))
    ).order_by(PickupDropVehicleRequest.id.desc()).limit(15).all()
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
# ... existing code ...