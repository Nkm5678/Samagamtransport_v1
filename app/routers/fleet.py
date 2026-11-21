import re
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
