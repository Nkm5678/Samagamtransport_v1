from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import Saint, Vehicle
from app.schemas import SaintRegisterRequest, TentCheckinRequest, PublicPassSearchRequest, ReturnShuttleAllocateRequest

router = APIRouter(prefix="/api/saints", tags=["Saints & Accommodation"])

@router.get("/")
def list_saints(hub: str = None, db: Session = Depends(get_db)):
    q = db.query(Saint)
    if hub and hub != "ALL":
        q = q.filter(Saint.arrival_hub == hub)
    return [{"id": s.id, "pass_code": f"SMG-{s.id:05d}", "full_name": s.full_name, "spiritual_order": s.spiritual_order, "contact_phone": s.contact_phone, "group_size": s.group_size, "arrival_mode": s.arrival_mode, "arrival_hub": s.arrival_hub, "arrival_transit_number": s.arrival_transit_number, "arrival_datetime": s.arrival_datetime, "departure_hub": s.departure_hub, "departure_datetime": s.departure_datetime, "assigned_ground": s.assigned_ground, "assigned_tent": s.assigned_tent, "status": s.status} for s in q.order_by(Saint.id.desc()).all()]

@router.post("/register")
def register_saint(req: SaintRegisterRequest, db: Session = Depends(get_db)):
    saint = Saint(**req.model_dump())
    db.add(saint)
    db.commit()
    db.refresh(saint)
    return {"status": "REGISTERED", "pass_code": f"SMG-{saint.id:05d}", "saint_id": saint.id}

@router.post("/checkin-tent")
def checkin_saint_to_tent(req: TentCheckinRequest, db: Session = Depends(get_db)):
    saint = db.query(Saint).filter(Saint.id == req.saint_id).first()
    if not saint:
        raise HTTPException(status_code=404, detail="Saint not found.")
    saint.status = "Checked-In at Tent"
    db.commit()
    return {"status": "CHECKED_IN", "saint_id": saint.id}

@router.post("/public-pass-lookup")
def public_boarding_pass_lookup(req: PublicPassSearchRequest, db: Session = Depends(get_db)):
    q = req.query.strip()
    matches = db.query(Saint).filter(or_(Saint.contact_phone.ilike(f"%{q}%"), Saint.full_name.ilike(f"%{q}%"))).limit(10).all()
    if not matches:
        raise HTTPException(status_code=404, detail="No boarding pass found.")
    return [{"pass_code": f"SMG-{s.id:05d}", "full_name": s.full_name, "group_size": s.group_size, "arrival_hub": s.arrival_hub, "arrival_datetime": s.arrival_datetime, "assigned_ground": s.assigned_ground, "assigned_tent": s.assigned_tent, "status": s.status} for s in matches]

@router.post("/allocate-return-shuttle")
def allocate_return_shuttle(req: ReturnShuttleAllocateRequest, db: Session = Depends(get_db)):
    veh = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
    saints = db.query(Saint).filter(Saint.id.in_(req.saint_ids)).all()
    if not veh or not saints:
        raise HTTPException(status_code=400, detail="Invalid vehicle or saints.")
    for s in saints:
        s.return_vehicle_id = veh.id
        s.status = "Return Shuttle Scheduled"
    db.commit()
    return {"status": "ALLOCATED", "vehicle_reg": veh.vehicle_reg_number}
