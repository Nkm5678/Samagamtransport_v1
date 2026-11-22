r"""
Samagam Transport Platform — Complete All-in-One Standalone Folder Updater
Includes:
  - Trilingual Welcome Portal (Hindi / Marathi / English) with 3 Request Portals:
      1. Need Vehicle Inside Samagam Ground
      2. Need Vehicle for Pickup & Drop (Railway Station / Airport / Bus Depot)
      3. Service for Advance Sewa (Name, Contact, Branch, Unit, Landmark, Nearest Station, Date, Start & Return Time)
  - 24-Hour Self-Service Request Status & Vehicle Allocation Tracker on Homepage
  - Restricted Control Room (admin_dashboard.html) for Dedicated Members & Admins Only
  - Hidden Rental Vehicle Hiring Committee Proforma (accessible inside Control Room)
  - Ground <-> Station Two-Way Intercom + Clean auth.py

Run directly inside C:\narendra\SamagamtransportV1:
    python apply_all_samagam_updates.py
"""

import os

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {}

FILES["app/__init__.py"] = ""
FILES["app/services/__init__.py"] = ""
FILES["app/routers/__init__.py"] = ""

FILES["app/routers/auth.py"] = '''import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import get_db
from app.models import Volunteer, VolunteerSession, Vehicle, EmailOTP, CrewDutyShift
from app.schemas import VolunteerRegisterRequest, VolunteerLoginRequest
from app.services.geo_service import verify_territory_geofence
from app.services.email_service import send_email_async_safe

router = APIRouter(prefix="/api/auth", tags=["Authentication, OTP & Geofencing"])

OTP_TTL = 300
OTP_MAX_TRIES = 5
REG_CODE = os.environ.get("REG_CODE", "SAMAGAM26").strip()
ADMIN_ACCESS_CODE = os.environ.get("ADMIN_ACCESS_CODE", "SAMAGAM-HQ-2026").strip()
OTP_DEV_ECHO = os.environ.get("OTP_DEV_ECHO", "1") == "1"
EMAIL_RE = re.compile(r"^[^@\\s]{1,64}@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")


def _tok_hash(tok: str) -> str:
    return hashlib.sha256(str(tok or "").encode()).hexdigest()


def _otp_hash(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def _norm_phone(p: str) -> str:
    d = re.sub(r"\\D", "", str(p or ""))
    return d[-10:] if len(d) > 10 else d


def _norm_email(e: str) -> str:
    return str(e or "").strip().lower()[:120]


def _norm_pin(p: str) -> str:
    return re.sub(r"\\D", "", str(p or ""))


def get_current_volunteer(
    x_session_token: str = Header(None),
    x_driver_token: str = Header(None),
    db: Session = Depends(get_db)
) -> Volunteer:
    raw_tok = x_driver_token or x_session_token
    if not raw_tok:
        raise HTTPException(status_code=401, detail="Missing session token. Please log in.")
    session = db.query(VolunteerSession).filter(
        VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please re-authenticate.")
    vol = db.query(Volunteer).filter(Volunteer.id == session.volunteer_id, Volunteer.is_active == True).first()
    if not vol:
        raise HTTPException(status_code=403, detail="Account inactive or not found.")
    return vol


def _driver_payload(db: Session, vol: Volunteer, token: str = None) -> dict:
    assigned_bus = db.query(Vehicle).filter(
        (Vehicle.assigned_driver_id == vol.id) | (Vehicle.driver_phone == vol.mobile_number)
    ).first()
    if not assigned_bus and vol.assigned_vehicle_id:
        assigned_bus = db.query(Vehicle).filter(Vehicle.id == vol.assigned_vehicle_id).first()

    open_shift = db.query(CrewDutyShift).filter(
        CrewDutyShift.crew_phone == vol.mobile_number,
        CrewDutyShift.is_currently_on_duty == True
    ).first()

    out = {
        "logged_in": True,
        "driver": {
            "id": vol.id,
            "volunteer_code": vol.volunteer_code,
            "name": vol.full_name,
            "phone": vol.mobile_number,
            "email": vol.email or "",
            "duty_location": vol.duty_location,
            "system_role": vol.system_role,
            "vehicle_id": assigned_bus.id if assigned_bus else None,
            "vehicle_reg_number": assigned_bus.vehicle_reg_number if assigned_bus else None,
            "on_duty": bool(open_shift),
            "shift_id": open_shift.id if open_shift else None
        }
    }
    if token:
        out["token"] = token
        out["session_token"] = token
    return out


@router.post("/control-room-login")
def control_room_admin_login(data: dict, db: Session = Depends(get_db)):
    """Restricts Control Room access strictly to dedicated members & admins."""
    mobile = _norm_phone(data.get("mobile_number"))
    passcode = str(data.get("access_code") or "").strip()
    if len(mobile) != 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit registered mobile number.")

    vol = db.query(Volunteer).filter(Volunteer.mobile_number == mobile, Volunteer.is_active == True).first()
    is_admin_role = bool(vol and vol.system_role in ("GROUND_ADMIN", "ADMIN", "CONTROL_ROOM"))
    pin_valid = bool(vol and vol.pin_hash and len(_norm_pin(passcode)) == 4 and check_password_hash(vol.pin_hash, _norm_pin(passcode)))
    code_valid = bool(ADMIN_ACCESS_CODE and hmac.compare_digest(passcode, ADMIN_ACCESS_CODE))

    if not ((is_admin_role and pin_valid) or code_valid):
        raise HTTPException(status_code=403, detail="Access Denied: Restricted to dedicated Control Room members and Admins only.")

    if not vol:
        vol = Volunteer(
            volunteer_code=f"HQ-{secrets.randbelow(9000) + 1000}",
            full_name=str(data.get("member_name") or f"Control Room Member ({mobile[-4:]})").strip(),
            mobile_number=mobile,
            unit_number="HQ-Command",
            branch_name="Samagam Transport HQ",
            duty_location="Ground 1 (Main Hall)",
            system_role="GROUND_ADMIN",
            can_view_all_territories=True,
            can_execute_ground_tasks=True,
            can_execute_station_tasks=True,
            can_manage_fleet=True,
            geofence_verified=True
        )
        db.add(vol)
        db.commit()
        db.refresh(vol)

    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(
        session_token=_tok_hash(raw_tok),
        volunteer_id=vol.id,
        expires_at=datetime.utcnow() + timedelta(hours=12)
    ))
    db.commit()

    return {
        "status": "AUTHORIZED",
        "session_token": raw_tok,
        "member": {
            "id": vol.id,
            "full_name": vol.full_name,
            "mobile_number": vol.mobile_number,
            "system_role": vol.system_role
        }
    }


@router.post("/otp/send")
def send_driver_otp(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or data.get("email") or data.get("phone") or "").strip()
    if not ident:
        raise HTTPException(status_code=400, detail="Enter your email address or 10-digit mobile number.")

    vol = None
    email = None
    if "@" in ident:
        email = _norm_email(ident)
        if not EMAIL_RE.match(email):
            raise HTTPException(status_code=400, detail="Enter a valid email address.")
        vol = db.query(Volunteer).filter(Volunteer.email == email).first()
    else:
        phone = _norm_phone(ident)
        if len(phone) != 10:
            raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number.")
        vol = db.query(Volunteer).filter(Volunteer.mobile_number == phone).first()

    if vol:
        if not vol.is_active:
            raise HTTPException(status_code=403, detail="Account disabled. Contact Control Room.")
        return {
            "requires_pin": True,
            "pin_missing": not bool(vol.pin_hash),
            "has_email": bool(vol.email),
            "driver_name": vol.full_name,
            "system_role": vol.system_role
        }

    if not email:
        raise HTTPException(status_code=404, detail="Mobile number not registered yet. Register first using your email address.")

    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(8)
    now_ts = time.time()
    existing_otp = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if existing_otp:
        existing_otp.code_hash = _otp_hash(code, salt)
        existing_otp.salt = salt
        existing_otp.expires_ts = now_ts + OTP_TTL
        existing_otp.attempts = 0
        existing_otp.sent_ts = now_ts
    else:
        db.add(EmailOTP(email=email, code_hash=_otp_hash(code, salt), salt=salt, expires_ts=now_ts + OTP_TTL, attempts=0, sent_ts=now_ts))
    db.commit()

    send_email_async_safe(
        email,
        f"{code} is your Samagam Field Verification Code",
        f"<h3>Samagam Transport</h3><p>Your 6-digit login code is <strong>{code}</strong> (valid for 5 minutes).</p>"
    )

    resp = {"sent": True, "email": email, "ttl": OTP_TTL}
    if OTP_DEV_ECHO:
        resp["dev_otp"] = code
    return resp


@router.post("/otp/verify")
def verify_driver_otp(data: dict, db: Session = Depends(get_db)):
    email = _norm_email(data.get("email"))
    code = re.sub(r"\\D", "", str(data.get("otp") or ""))
    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if not row or row.expires_ts < time.time():
        raise HTTPException(status_code=400, detail="This OTP has expired. Please request a new one.")
    if row.attempts >= OTP_MAX_TRIES:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=429, detail="Too many wrong OTP attempts.")
    if not code or not hmac.compare_digest(_otp_hash(code, row.salt), row.code_hash):
        row.attempts += 1
        db.commit()
        raise HTTPException(status_code=403, detail="Wrong OTP code.")

    name = str(data.get("name") or "").strip()
    phone = _norm_phone(data.get("phone"))
    pin = _norm_pin(data.get("pin"))
    role = str(data.get("system_role") or "DRIVER").upper().strip()
    if not name or not phone:
        return {"needs_registration": True, "requires_code": bool(REG_CODE)}
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number.")
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="Create a 4-digit numerical PIN.")
    if REG_CODE and str(data.get("code") or "").strip() != REG_CODE:
        raise HTTPException(status_code=403, detail="Wrong event code. Ask the Control Room.")

    if db.query(Volunteer).filter(Volunteer.mobile_number == phone).first():
        raise HTTPException(status_code=409, detail="This mobile number is already registered.")

    vol = Volunteer(
        volunteer_code=f"CREW-{secrets.randbelow(9000) + 1000}",
        full_name=name,
        mobile_number=phone,
        email=email,
        pin_hash=generate_password_hash(pin),
        unit_number="Field-Crew",
        branch_name="Samagam Transport",
        duty_location=str(data.get("duty_location") or "Ground 1 (Main Hall)"),
        system_role=role,
        is_driver=(role == "DRIVER"),
        geofence_verified=True
    )
    db.add(vol)
    db.delete(row)
    db.commit()
    db.refresh(vol)

    matching_bus = db.query(Vehicle).filter(Vehicle.driver_phone == phone).first()
    if matching_bus:
        matching_bus.assigned_driver_id = vol.id
        vol.assigned_vehicle_id = matching_bus.id
        db.commit()

    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(days=7)))
    db.commit()
    return _driver_payload(db, vol, raw_tok)


@router.post("/pin/verify")
def verify_driver_pin(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or data.get("email") or data.get("phone") or "").strip()
    pin = _norm_pin(data.get("pin"))
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="Enter your 4-digit numerical PIN.")

    vol = db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first() if "@" in ident else db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Crew account not found.")
    if not vol.pin_hash:
        raise HTTPException(status_code=403, detail="No PIN set yet. Use Forgot PIN or ask Control Room.")
    if not check_password_hash(vol.pin_hash, pin):
        raise HTTPException(status_code=403, detail="Incorrect 4-digit PIN.")

    vol.last_login_at = datetime.utcnow()
    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(days=7)))
    db.commit()
    return _driver_payload(db, vol, raw_tok)


@router.post("/pin/reset/send")
def send_pin_reset_otp(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or "").strip()
    vol = db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first() if "@" in ident else db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()
    if not vol or not vol.email:
        raise HTTPException(status_code=400, detail="No email on file for this account. Ask Control Room to reset PIN.")
    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(8)
    now_ts = time.time()
    row = db.query(EmailOTP).filter(EmailOTP.email == vol.email).first()
    if row:
        row.code_hash, row.salt, row.expires_ts, row.attempts, row.sent_ts = _otp_hash(code, salt), salt, now_ts + OTP_TTL, 0, now_ts
    else:
        db.add(EmailOTP(email=vol.email, code_hash=_otp_hash(code, salt), salt=salt, expires_ts=now_ts + OTP_TTL, attempts=0, sent_ts=now_ts))
    db.commit()
    send_email_async_safe(vol.email, f"{code} — Samagam PIN Reset Code", f"<p>Your PIN reset OTP is <strong>{code}</strong>.</p>")
    resp = {"sent": True, "email": vol.email}
    if OTP_DEV_ECHO:
        resp["dev_otp"] = code
    return resp


@router.post("/pin/reset/verify")
def verify_pin_reset(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or "").strip()
    code = re.sub(r"\\D", "", str(data.get("otp") or ""))
    pin = _norm_pin(data.get("pin"))
    vol = db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first() if "@" in ident else db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()
    if not vol or not vol.email:
        raise HTTPException(status_code=404, detail="Account not found.")
    row = db.query(EmailOTP).filter(EmailOTP.email == vol.email).first()
    if not row or row.expires_ts < time.time() or not hmac.compare_digest(_otp_hash(code, row.salt), row.code_hash):
        raise HTTPException(status_code=403, detail="Invalid or expired OTP.")
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="Enter a new 4-digit numerical PIN.")
    vol.pin_hash = generate_password_hash(pin)
    db.delete(row)
    db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(days=7)))
    db.commit()
    return _driver_payload(db, vol, raw_tok)


@router.get("/driver-me")
def get_driver_me(vol: Volunteer = Depends(get_current_volunteer), db: Session = Depends(get_db)):
    return _driver_payload(db, vol)


@router.post("/driver-logout")
def driver_logout(
    x_driver_token: str = Header(None),
    x_session_token: str = Header(None),
    db: Session = Depends(get_db)
):
    raw_tok = x_driver_token or x_session_token
    if raw_tok:
        sess = db.query(VolunteerSession).filter(
            VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])
        ).first()
        if sess:
            vol = db.query(Volunteer).filter(Volunteer.id == sess.volunteer_id).first()
            if vol:
                active_bus = db.query(Vehicle).filter(
                    ((Vehicle.assigned_driver_id == vol.id) | (Vehicle.driver_phone == vol.mobile_number)),
                    Vehicle.active_journey_id != None
                ).first()
                if active_bus:
                    raise HTTPException(status_code=409, detail=f"Trip still active on {active_bus.vehicle_reg_number}. Tap 'End Trip' first.")
                open_shift = db.query(CrewDutyShift).filter(
                    CrewDutyShift.crew_phone == vol.mobile_number,
                    CrewDutyShift.is_currently_on_duty == True
                ).first()
                if open_shift:
                    raise HTTPException(status_code=409, detail="You are still ON DUTY. Tap 'End Duty Shift' before logging out.")
            db.delete(sess)
            db.commit()
    return {"ok": True}


@router.get("/crew")
def list_registered_crew(db: Session = Depends(get_db)):
    crew = db.query(Volunteer).order_by(Volunteer.id.desc()).all()
    return [
        {
            "id": v.id,
            "volunteer_code": v.volunteer_code,
            "full_name": v.full_name,
            "mobile_number": v.mobile_number,
            "email": v.email or "",
            "duty_location": v.duty_location,
            "system_role": v.system_role,
            "has_pin": bool(v.pin_hash),
            "is_active": v.is_active
        }
        for v in crew
    ]


@router.post("/admin-reset-pin")
def admin_reset_crew_pin(data: dict, db: Session = Depends(get_db)):
    crew_id = data.get("crew_id")
    mobile = _norm_phone(data.get("mobile_number"))
    pin = _norm_pin(data.get("new_pin") or "1234")
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="New PIN must be exactly 4 digits.")
    vol = db.query(Volunteer).filter(Volunteer.id == int(crew_id)).first() if crew_id else db.query(Volunteer).filter(Volunteer.mobile_number == mobile).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Crew member not found.")
    vol.pin_hash = generate_password_hash(pin)
    db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    db.commit()
    return {"status": "PIN_RESET", "crew_id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number, "new_pin": pin}


@router.post("/register")
def register_volunteer(req: VolunteerRegisterRequest, db: Session = Depends(get_db)):
    is_valid, distance_m, msg, hub = verify_territory_geofence(db, req.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    if db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number).first():
        raise HTTPException(status_code=400, detail="Mobile number already registered.")
    loc = req.duty_location.lower()
    is_ground = ("ground" in loc or "control" in loc or "venue" in loc)
    vol = Volunteer(
        volunteer_code=f"VOL-{hub.hub_code}-{secrets.randbelow(9000) + 1000}",
        full_name=req.full_name.strip(),
        mobile_number=req.mobile_number.strip(),
        unit_number=req.unit_number.strip(),
        branch_name=req.branch_name.strip(),
        duty_location=req.duty_location,
        system_role="GROUND_ADMIN" if is_ground else "STATION_COORDINATOR",
        can_view_all_territories=is_ground,
        can_execute_ground_tasks=is_ground,
        can_execute_station_tasks=True,
        can_manage_fleet=is_ground,
        latitude=req.latitude,
        longitude=req.longitude,
        geofence_verified=True
    )
    db.add(vol)
    db.commit()
    db.refresh(vol)
    token = secrets.token_hex(32)
    db.add(VolunteerSession(session_token=token, volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(hours=24)))
    db.commit()
    return {"status": "REGISTERED", "session_token": token, "volunteer": {"id": vol.id, "volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "duty_location": vol.duty_location, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}


@router.post("/login")
def login_volunteer(req: VolunteerLoginRequest, db: Session = Depends(get_db)):
    vol = db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number.strip()).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found.")
    is_valid, distance_m, msg, _ = verify_territory_geofence(db, vol.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)
    token = secrets.token_hex(32)
    db.add(VolunteerSession(session_token=token, volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(hours=24)))
    db.commit()
    return {"status": "AUTHENTICATED", "session_token": token, "volunteer": {"id": vol.id, "volunteer_code": vol.volunteer_code, "full_name": vol.full_name, "duty_location": vol.duty_location, "system_role": vol.system_role, "can_view_all_territories": vol.can_view_all_territories}}
'''

FILES["app/main.py"] = '''import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.seed_service import seed_initial_operations_data
from app.routers import auth, saints, fleet, operations, reports

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_operations_data(db)
    finally:
        db.close()
    yield

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(saints.router)
app.include_router(fleet.router)
app.include_router(operations.router)
app.include_router(reports.router)

static_dir = os.path.join(ROOT_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def _serve_html(filename: str):
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return {"detail": f"{filename} not found in project root."}

@app.get("/")
def home():
    welcome_path = os.path.join(ROOT_DIR, "welcome.html")
    if os.path.exists(welcome_path):
        return FileResponse(welcome_path)
    return _serve_html("admin_dashboard.html")

@app.get("/sw.js")
def service_worker():
    sw_path = os.path.join(ROOT_DIR, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    return {"status": "ok"}

@app.get("/{page_name}.html")
def serve_html_page(page_name: str):
    return _serve_html(f"{page_name}.html")

@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
'''

FILES["welcome.html"] = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>जागृति — The Awakening | निरंकारी सन्त समागम परिवहन सेवा (Samagam Transport)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@500;700;800&family=Playfair+Display:ital,wght@0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body {
            background: radial-gradient(circle at top, #ffffff 0%, #eef3fb 55%, #dce4f2 100%);
            font-family: 'Inter', 'Noto Sans Devanagari', sans-serif;
            color: #0f172a;
        }
        .jagriti-sun-glow {
            background: radial-gradient(circle, rgba(251, 191, 36, 0.36) 0%, rgba(253, 224, 71, 0.12) 48%, rgba(255, 255, 255, 0) 72%);
        }
        .lang-btn.active {
            background-color: #0f2c59;
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(15, 44, 89, 0.25);
        }
        .portal-card {
            transition: transform 0.22s ease, box-shadow 0.22s ease;
        }
        .portal-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 24px 48px -12px rgba(15, 44, 89, 0.18);
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">

    <!-- Top Language Bar (Control Room & Hiring Proforma Hidden from Public Welcome Page) -->
    <header class="bg-white/90 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-40">
        <div class="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-1.5 bg-slate-100 p-1 rounded-2xl border border-slate-200 text-xs font-extrabold">
                <button onclick="setLanguage('hi', this)" class="lang-btn px-3.5 py-1.5 rounded-xl transition">हिंदी</button>
                <button onclick="setLanguage('mr', this)" class="lang-btn px-3.5 py-1.5 rounded-xl transition">मराठी</button>
                <button onclick="setLanguage('en', this)" class="lang-btn active px-3.5 py-1.5 rounded-xl transition">English</button>
            </div>
            <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
                <a href="/download_hub.html" class="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 transition">
                    📲 <span data-i18n="nav_apps">Field Apps (.APK)</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="max-w-6xl mx-auto px-4 py-8 space-y-8 flex-1 w-full">

        <!-- Hero Brand Banner -->
        <section class="text-center max-w-3xl mx-auto space-y-3 pt-1">
            <div class="inline-block px-4 py-1 rounded-full bg-sky-100 text-[#0f2c59] text-xs font-extrabold tracking-wide">
                धन निरंकार जी 🙏 • SANT NIRANKARI MANDAL
            </div>

            <div class="relative mx-auto w-64 h-36 flex flex-col items-center justify-center jagriti-sun-glow rounded-full">
                <div class="text-5xl sm:text-6xl font-extrabold tracking-tight" style="color: #0f2c59; text-shadow: 0 2px 10px rgba(245, 158, 11, 0.25);">
                    जागृति
                </div>
                <div class="text-sm sm:text-base italic font-bold text-slate-800 -mt-1" style="font-family: 'Playfair Display', serif;">
                    The Awakening
                </div>
            </div>

            <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight" style="color: #0f2c59;">
                निरंकारी सन्त समागम — परिवहन सेवा पोर्टल
            </h1>
            <p class="text-xs sm:text-sm font-bold text-slate-600">
                60th Maharashtra Annual Nirankari Sant Samagam • Kharghar, Navi Mumbai (Central Park) • 23–26 January 2027
            </p>
            <p class="text-xs sm:text-sm text-slate-500 max-w-2xl mx-auto leading-relaxed" data-i18n="hero_desc">
                Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database so our team can allocate vehicles and update your request status live within 24 hours.
            </p>
        </section>

        <!-- 24-HOUR SELF-SERVICE VEHICLE ALLOCATION STATUS TRACKER -->
        <section class="max-w-5xl mx-auto bg-white rounded-3xl p-5 sm:p-6 border-2 border-[#0f2c59]/20 shadow-md space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-sm sm:text-base font-extrabold text-[#0f2c59]" data-i18n="track_title">
                    🔍 Check Your Vehicle Allocation Status (24-Hour Live Tracker via Mobile No. or Request ID)
                </h2>
                <span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">Live Database Status</span>
            </div>
            <div class="flex flex-col sm:flex-row gap-2.5">
                <input type="text" id="track-query-input" placeholder="Enter 10-Digit Mobile Number or Request ID (e.g. ADV-1234, PND-1234, REQ-1234)" class="flex-1 border border-slate-300 rounded-2xl px-4 py-3 text-sm font-semibold focus:outline-none focus:border-[#0f2c59]">
                <button onclick="checkMyRequestStatus()" class="bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold px-6 py-3 rounded-2xl text-sm shadow transition">
                    <span data-i18n="track_btn">Check Status</span>
                </button>
            </div>
            <div id="track-status-results" class="space-y-2.5"></div>
        </section>

        <!-- THREE PRIMARY REQUEST PORTALS -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-6xl mx-auto">

            <!-- CARD 1: NEED VEHICLE INSIDE SAMAGAM GROUND -->
            <div class="portal-card bg-white rounded-3xl p-6 border border-sky-200 shadow-lg flex flex-col justify-between space-y-5">
                <div class="space-y-2.5">
                    <div class="flex items-center justify-between">
                        <span class="w-12 h-12 rounded-2xl bg-sky-100 text-2xl flex items-center justify-center">⛺</span>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full bg-sky-50 text-[#0f2c59] border border-sky-200" data-i18n="badge_ground">
                            Internal Venue Logistics
                        </span>
                    </div>
                    <h2 class="text-lg sm:text-xl font-extrabold text-[#0f2c59]" data-i18n="card1_title">
                        Need Vehicle Inside Samagam Ground
                    </h2>
                    <p class="text-xs text-slate-600 leading-relaxed" data-i18n="card1_desc">
                        For Samagam departments (Langar, Tent, Sound, Medical, Security, Sanitation) needing cars, pickups, tempos, or e-rickshaws inside Central Park Kharghar grounds—or to donate a vehicle for Seva.
                    </p>
                    <ul class="text-[11px] text-slate-600 space-y-1 pt-1">
                        <li class="flex items-center gap-1.5"><span class="text-emerald-600 font-bold">✓</span> <span data-i18n="card1_pt1">Dept. Requisition with Sign & Stamp</span></li>
                        <li class="flex items-center gap-1.5"><span class="text-emerald-600 font-bold">✓</span> <span data-i18n="card1_pt2">Donate Vehicle for Seva (वाहन प्राप्ती फॉर्म)</span></li>
                    </ul>
                </div>

                <div class="pt-1">
                    <a href="/in_ground_seva_vehicles.html" class="w-full bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold py-3.5 px-4 rounded-2xl text-xs sm:text-sm flex items-center justify-between shadow-lg transition">
                        <span data-i18n="card1_btn">Request / Donate In-Ground</span>
                        <span>→</span>
                    </a>
                </div>
            </div>

            <!-- CARD 2: NEED VEHICLE FOR PICKUP & DROP -->
            <div class="portal-card bg-white rounded-3xl p-6 border border-emerald-200 shadow-lg flex flex-col justify-between space-y-5">
                <div class="space-y-2.5">
                    <div class="flex items-center justify-between">
                        <span class="w-12 h-12 rounded-2xl bg-emerald-100 text-2xl flex items-center justify-center">🚉</span>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200" data-i18n="badge_transit">
                            Station • Airport • Bus Depot
                        </span>
                    </div>
                    <h2 class="text-lg sm:text-xl font-extrabold text-emerald-950" data-i18n="card2_title">
                        Need Vehicle for Pickup & Drop
                    </h2>
                    <p class="text-xs text-slate-600 leading-relaxed" data-i18n="card2_desc">
                        Request shuttle buses, tempo travellers, or cars for Saints, Jathas, or guests arriving at or departing from Railway Stations, Mumbai Airports (T1/T2), or ST Bus Depots.
                    </p>
                    <ul class="text-[11px] text-slate-600 space-y-1 pt-1">
                        <li class="flex items-center gap-1.5"><span class="text-emerald-600 font-bold">✓</span> <span data-i18n="card2_pt1">Direct Sync with Transport Database</span></li>
                        <li class="flex items-center gap-1.5"><span class="text-emerald-600 font-bold">✓</span> <span data-i18n="card2_pt3">Live Driver & Bus Allocation Status</span></li>
                    </ul>
                </div>

                <div class="pt-1">
                    <button onclick="openPickupDropModal()" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-3.5 px-4 rounded-2xl text-xs sm:text-sm flex items-center justify-between shadow-lg transition">
                        <span data-i18n="card2_btn">Raise Pickup / Drop Request</span>
                        <span>→</span>
                    </button>
                </div>
            </div>

            <!-- CARD 3: SERVICE FOR ADVANCE SEWA -->
            <div class="portal-card bg-white rounded-3xl p-6 border border-amber-300 shadow-lg flex flex-col justify-between space-y-5">
                <div class="space-y-2.5">
                    <div class="flex items-center justify-between">
                        <span class="w-12 h-12 rounded-2xl bg-amber-100 text-2xl flex items-center justify-center">🙏</span>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-300" data-i18n="badge_adv">
                            24-Hr Status Update
                        </span>
                    </div>
                    <h2 class="text-lg sm:text-xl font-extrabold text-amber-950" data-i18n="card3_title">
                        Service for Advance Sewa
                    </h2>
                    <p class="text-xs text-slate-600 leading-relaxed" data-i18n="card3_desc">
                        Raise advance transport request for Pre-Samagam Ground & Branch Sewa with Branch, Unit No., Landmark, Nearest Railway Station, Date of Sewa, Start Journey & Return Time.
                    </p>
                    <ul class="text-[11px] text-slate-600 space-y-1 pt-1">
                        <li class="flex items-center gap-1.5"><span class="text-amber-600 font-bold">✓</span> <span data-i18n="card3_pt1">Connected Directly to Central Database</span></li>
                        <li class="flex items-center gap-1.5"><span class="text-amber-600 font-bold">✓</span> <span data-i18n="card3_pt2">Check Allocation Status Within 24 Hours</span></li>
                    </ul>
                </div>

                <div class="pt-1">
                    <button onclick="openAdvanceSewaModal()" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-3.5 px-4 rounded-2xl text-xs sm:text-sm flex items-center justify-between shadow-lg transition">
                        <span data-i18n="card3_btn">Raise Advance Sewa Request</span>
                        <span>→</span>
                    </button>
                </div>
            </div>

        </section>

        <!-- LIVE SUBMITTED REQUESTS FEED -->
        <section class="max-w-5xl mx-auto bg-white/90 rounded-3xl p-6 border border-slate-200 shadow-sm space-y-3">
            <div class="flex justify-between items-center">
                <h3 class="font-extrabold text-sm text-[#0f2c59]" data-i18n="live_feed_title">
                    📡 Live Pickup, Drop, Advance Sewa & Ground Requests in Transport Database
                </h3>
                <button onclick="loadRecentRequests()" class="text-xs font-bold text-emerald-700">↻ Refresh</button>
            </div>
            <div id="recent-requests-grid" class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <p class="text-slate-400">Loading live database requests...</p>
            </div>
        </section>

    </main>

    <!-- MODAL 1: PICKUP & DROP VEHICLE REQUEST -->
    <div id="pickup-drop-modal" class="fixed inset-0 bg-slate-950/75 hidden items-center justify-center z-50 p-4 overflow-y-auto">
        <div class="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-7 space-y-4 shadow-2xl my-auto">
            <div class="flex justify-between items-start border-b pb-3">
                <div>
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900">
                        Station • Airport • Bus Depot Shuttle
                    </span>
                    <h3 class="text-lg font-extrabold text-slate-900 mt-1" data-i18n="modal_pd_title">
                        Pickup & Drop Vehicle Requirement Form
                    </h3>
                </div>
                <button onclick="closePickupDropModal()" class="text-slate-400 hover:text-slate-800 font-bold text-lg">✕</button>
            </div>

            <form id="pickup-drop-form" onsubmit="submitPickupDropRequest(event)" class="space-y-3 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_trip_dir">Trip Type *</label>
                        <select name="trip_direction" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="PICKUP_TO_SAMAGAM">Pickup → Samagam Ground (Kharghar)</option>
                            <option value="DROP_FROM_SAMAGAM">Samagam Ground → Drop at Station/Airport</option>
                            <option value="ROUND_TRIP">Both Pickup & Return Drop</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_transit_hub">Railway Station / Airport / Bus Depot *</label>
                        <select name="transit_hub" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="Panvel Junction (PNVL)">Panvel Railway Station (PNVL)</option>
                            <option value="Kharghar / Belapur Station">Kharghar / CBD Belapur Station</option>
                            <option value="Thane Railway Station">Thane Railway Station (TNA)</option>
                            <option value="Lokmanya Tilak Terminus (LTT)">Lokmanya Tilak Terminus (LTT)</option>
                            <option value="Dadar Terminal (DR/DDR)">Dadar Railway Terminal (DR)</option>
                            <option value="Chhatrapati Shivaji Maharaj Terminus (CSMT)">CSMT Mumbai</option>
                            <option value="Mumbai Central (MMCT)">Mumbai Central (MMCT)</option>
                            <option value="Bandra Terminus (BDTS)">Bandra Terminus (BDTS)</option>
                            <option value="Kalyan Junction (KYN)">Kalyan Junction (KYN)</option>
                            <option value="Mumbai Airport Terminal 1 (Domestic)">Mumbai Airport Terminal 1 (Domestic)</option>
                            <option value="Mumbai Airport Terminal 2 (International)">Mumbai Airport Terminal 2 (International)</option>
                            <option value="Panvel / Sion ST Bus Depot">Panvel / Sion / Dadar ST Bus Depot</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_pax">Total Pilgrims / Pax *</label>
                        <input type="number" name="passenger_count" value="45" min="1" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_veh_pref">Preferred Vehicle *</label>
                        <select name="vehicle_type_requested" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                            <option value="Heavy Bus (50-Seater)">Heavy Bus (50-Seater)</option>
                            <option value="Mini Bus / Tempo Traveller (20-35 Seat)">Mini Bus / Tempo Traveller</option>
                            <option value="Car / Innova / SUV (VIP/Elderly)">Car / Innova / SUV</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_veh_qty">No. of Vehicles *</label>
                        <input type="number" name="vehicles_needed" value="1" min="1" max="50" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_dt">Arrival / Departure Date & Time *</label>
                        <input type="datetime-local" name="scheduled_datetime" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_train">Train / Flight / Bus Number</label>
                        <input type="text" name="train_flight_details" placeholder="e.g. 12138 Punjab Mail / AI-602" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_req_name">Jatha / Coordinator Name *</label>
                        <input type="text" name="requester_name" required placeholder="Sevadar / Jatha Leader Name" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_req_phone">10-Digit Mobile Number *</label>
                        <input type="tel" name="requester_phone" required maxlength="10" inputmode="numeric" placeholder="98XXXXXXXX" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-slate-700 mb-1">Special Notes (Wheelchair / Luggage / Zone)</label>
                    <input type="text" name="notes" placeholder="Optional remarks for Transport Control Room" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                </div>

                <button type="submit" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-3.5 rounded-2xl text-sm shadow-lg transition">
                    ✅ <span data-i18n="btn_submit_pd">Submit Pickup/Drop Request to Transport Control</span>
                </button>
            </form>
        </div>
    </div>

    <!-- MODAL 2: SERVICE FOR ADVANCE SEWA REQUEST -->
    <div id="advance-sewa-modal" class="fixed inset-0 bg-slate-950/75 hidden items-center justify-center z-50 p-4 overflow-y-auto">
        <div class="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-7 space-y-4 shadow-2xl my-auto">
            <div class="flex justify-between items-start border-b pb-3">
                <div>
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-950">
                        Advance Sewa Transport • 24-Hour Status Update
                    </span>
                    <h3 class="text-lg font-extrabold text-slate-900 mt-1" data-i18n="modal_adv_title">
                        Service for Advance Sewa — Vehicle Request Form
                    </h3>
                </div>
                <button onclick="closeAdvanceSewaModal()" class="text-slate-400 hover:text-slate-800 font-bold text-lg">✕</button>
            </div>

            <form id="advance-sewa-form" onsubmit="submitAdvanceSewaRequest(event)" class="space-y-3 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_name">Name *</label>
                        <input type="text" name="requester_name" required placeholder="Full Name" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_phone">Contact Number *</label>
                        <input type="tel" name="contact_number" required maxlength="10" inputmode="numeric" placeholder="10-Digit Mobile Number" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_branch">Branch *</label>
                        <input type="text" name="branch_name" required placeholder="e.g. Thane / Mulund / Panvel" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_unit">Unit Number *</label>
                        <input type="text" name="unit_number" required placeholder="e.g. Unit-104" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_landmark">Landmark *</label>
                        <input type="text" name="landmark" required placeholder="Pickup Landmark / Bhawan" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_station">Nearest Railway Station *</label>
                        <input type="text" name="nearest_railway_station" required placeholder="e.g. Panvel / Thane / Kalyan" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_date">Date of Sewa *</label>
                        <input type="date" name="date_of_sewa" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_start">Time to Start Journey *</label>
                        <input type="time" name="start_journey_time" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_return">Time to Return *</label>
                        <input type="time" name="return_time" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_adv_pax">Sevadars Count</label>
                        <input type="number" name="passenger_count" value="25" min="1" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                    <div class="sm:col-span-2">
                        <label class="block text-xs font-bold text-slate-700 mb-1">Sewa Department / Remarks</label>
                        <input type="text" name="notes" placeholder="e.g. Ground Preparation / Tent / Langar Sewa" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                </div>

                <div class="bg-amber-50 border border-amber-200 rounded-xl p-2.5 text-[11px] text-amber-950 font-semibold">
                    ⏱️ Your request will be saved in the Central Transport Database. Check your vehicle allocation status on this homepage within 24 hours using your Contact Number or Request ID.
                </div>

                <button type="submit" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-3.5 rounded-2xl text-sm shadow-lg transition">
                    ✅ <span data-i18n="btn_submit_adv">Submit Advance Sewa Request</span>
                </button>
            </form>
        </div>
    </div>

    <footer class="bg-white/80 border-t border-slate-200 py-4 text-center text-xs text-slate-500 mt-10">
        धन निरंकार जी 🙏 • Sant Nirankari Mandal Transport & Logistics Cell • www.samagamtransport.in
    </footer>

    <script>
        const TRANSLATIONS = {
            en: {
                nav_apps: "Field Apps (.APK)",
                hero_desc: "Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database so our team can allocate vehicles and update your request status live within 24 hours.",
                track_title: "🔍 Check Your Vehicle Allocation Status (24-Hour Live Tracker via Mobile No. or Request ID)",
                track_btn: "Check Status",
                badge_ground: "Internal Venue Logistics",
                card1_title: "Need Vehicle Inside Samagam Ground",
                card1_desc: "For Samagam departments (Langar, Tent, Sound, Medical, Security, Sanitation) needing cars, pickups, tempos, or e-rickshaws inside Central Park Kharghar grounds—or to donate a vehicle for Seva.",
                card1_pt1: "Dept. Requisition with Sign & Stamp",
                card1_pt2: "Donate Vehicle for Seva (वाहन प्राप्ती फॉर्म)",
                card1_btn: "Request / Donate In-Ground",
                badge_transit: "Station • Airport • Bus Depot",
                card2_title: "Need Vehicle for Pickup & Drop",
                card2_desc: "Request shuttle buses, tempo travellers, or cars for Saints, Jathas, or guests arriving at or departing from Railway Stations, Mumbai Airports (T1/T2), or ST Bus Depots.",
                card2_pt1: "Direct Sync with Transport Database",
                card2_pt3: "Live Driver & Bus Allocation Status",
                card2_btn: "Raise Pickup / Drop Request",
                badge_adv: "24-Hr Status Update",
                card3_title: "Service for Advance Sewa",
                card3_desc: "Raise advance transport request for Pre-Samagam Ground & Branch Sewa with Branch, Unit No., Landmark, Nearest Railway Station, Date of Sewa, Start Journey & Return Time.",
                card3_pt1: "Connected Directly to Central Database",
                card3_pt2: "Check Allocation Status Within 24 Hours",
                card3_btn: "Raise Advance Sewa Request",
                live_feed_title: "📡 Live Pickup, Drop, Advance Sewa & Ground Requests in Transport Database",
                modal_pd_title: "Pickup & Drop Vehicle Requirement Form",
                modal_adv_title: "Service for Advance Sewa — Vehicle Request Form",
                lbl_trip_dir: "Trip Type *",
                lbl_transit_hub: "Railway Station / Airport / Bus Depot *",
                lbl_pax: "Total Pilgrims / Pax *",
                lbl_veh_pref: "Preferred Vehicle *",
                lbl_veh_qty: "No. of Vehicles *",
                lbl_dt: "Arrival / Departure Date & Time *",
                lbl_train: "Train / Flight / Bus Number",
                lbl_req_name: "Jatha / Coordinator Name *",
                lbl_req_phone: "10-Digit Mobile Number *",
                btn_submit_pd: "Submit Pickup/Drop Request to Transport Control",
                lbl_adv_name: "Name *",
                lbl_adv_phone: "Contact Number *",
                lbl_adv_branch: "Branch *",
                lbl_adv_unit: "Unit Number *",
                lbl_adv_landmark: "Landmark *",
                lbl_adv_station: "Nearest Railway Station *",
                lbl_adv_date: "Date of Sewa *",
                lbl_adv_start: "Time to Start Journey *",
                lbl_adv_return: "Time to Return *",
                lbl_adv_pax: "Sevadars Count",
                btn_submit_adv: "Submit Advance Sewa Request"
            },
            hi: {
                nav_apps: "फील्ड ऐप्स (.APK)",
                hero_desc: "नीचे अपनी परिवहन आवश्यकता चुनें। सभी वाहन अनुरोध सीधे मुख्य डेटाबेस से जुड़े हैं ताकि परिवहन टीम तुरंत वाहन आवंटित कर सके और आपको 24 घंटे के भीतर लाइव अपडेट मिल सके।",
                track_title: "🔍 अपने वाहन आवंटन की स्थिति जांचें (24 घंटे के भीतर मोबाइल नंबर या रिक्वेस्ट कोड द्वारा)",
                track_btn: "स्थिति जांचें",
                badge_ground: "समागम ग्राउंड आंतरिक सेवा",
                card1_title: "समागम ग्राउंड के अंदर वाहन चाहिए",
                card1_desc: "लंगर, टेंट, साउंड, मेडिकल, सुरक्षा और स्वच्छता विभागों के लिए खारघर ग्राउंड के अंदर कार, पिकअप, टेम्पो की मांग करें या सेवा हेतु वाहन जमा करें।",
                card1_pt1: "विभाग प्रमुख के हस्ताक्षर व मोहर सहित मांग पत्र",
                card1_pt2: "सेवा के लिए वाहन समर्पित करने का फॉर्म",
                card1_btn: "ग्राउंड के अंदर वाहन मांगें / जमा करें",
                badge_transit: "रेलवे स्टेशन • एयरपोर्ट • बस डिपो",
                card2_title: "पिकअप और ड्रॉप के लिए वाहन चाहिए",
                card2_desc: "पनवेल, ठाणे, CSMT, LTT, दादर, कल्याण रेलवे स्टेशन, मुंबई एयरपोर्ट या बस डिपो से सन्तों और जत्थों को लाने-ले जाने हेतु बस बुक करें।",
                card2_pt1: "मुख्य परिवहन डेटाबेस से सीधा जुड़ाव",
                card2_pt3: "मोबाइल नंबर द्वारा ड्राइवर व बस का लाइव अपडेट",
                card2_btn: "पिकअप / ड्रॉप वाहन अनुरोध दर्ज करें",
                badge_adv: "24 घंटे में स्टेटस अपडेट",
                card3_title: "अग्रिम सेवा हेतु वाहन अनुरोध (Service for Advance Sewa)",
                card3_desc: "अग्रिम सेवा (Advance Sewa) के लिए नाम, संपर्क नंबर, ब्रांच, यूनिट नंबर, लैंडमार्क, नजदीकी रेलवे स्टेशन, सेवा दिनांक, प्रस्थान व वापसी समय सहित वाहन अनुरोध दर्ज करें।",
                card3_pt1: "सीधे केंद्रीय डेटाबेस से जुड़ा हुआ",
                card3_pt2: "24 घंटे के भीतर होमपेज पर आवंटन स्थिति देखें",
                card3_btn: "अग्रिम सेवा वाहन अनुरोध दर्ज करें",
                live_feed_title: "📡 मुख्य परिवहन डेटाबेस में दर्ज लाइव अनुरोध",
                modal_pd_title: "पिकअप और ड्रॉप वाहन आवश्यकता फॉर्म",
                modal_adv_title: "अग्रिम सेवा (Advance Sewa) — वाहन अनुरोध फॉर्म",
                lbl_trip_dir: "यात्रा का प्रकार *",
                lbl_transit_hub: "रेलवे स्टेशन / एयरपोर्ट / बस डिपो *",
                lbl_pax: "कुल श्रद्धालु / यात्री संख्या *",
                lbl_veh_pref: "आवश्यक वाहन का प्रकार *",
                lbl_veh_qty: "वाहनों की संख्या *",
                lbl_dt: "आगमन / प्रस्थान दिनांक व समय *",
                lbl_train: "ट्रेन / फ्लाइट / बस नंबर",
                lbl_req_name: "जत्था प्रमुख / संयोजक का नाम *",
                lbl_req_phone: "10-अंकीय मोबाइल नंबर *",
                btn_submit_pd: "परिवहन कंट्रोल रूम को अनुरोध भेजें",
                lbl_adv_name: "नाम (Name) *",
                lbl_adv_phone: "संपर्क नंबर (Contact Number) *",
                lbl_adv_branch: "ब्रांच (Branch) *",
                lbl_adv_unit: "यूनिट नंबर (Unit Number) *",
                lbl_adv_landmark: "लैंडमार्क (Landmark) *",
                lbl_adv_station: "नजदीकी रेलवे स्टेशन (Nearest Railway Station) *",
                lbl_adv_date: "सेवा दिनांक (Date of Sewa) *",
                lbl_adv_start: "यात्रा शुरू करने का समय (Time to Start Journey) *",
                lbl_adv_return: "वापसी का समय (Time to Return) *",
                lbl_adv_pax: "सेवादारों की संख्या",
                btn_submit_adv: "अग्रिम सेवा अनुरोध जमा करें"
            },
            mr: {
                nav_apps: "फील्ड ॲप्स (.APK)",
                hero_desc: "खालीलपैकी आपली वाहन आवश्यकता निवडा. सर्व वाहन विनंत्या थेट मुख्य डेटाबेसशी जोडलेल्या आहेत जेणेकरून परिवहन टीम तात्काळ वाहन देऊ शकेल आणि तुम्हाला २४ तासांत थेट अपडेट मिळेल.",
                track_title: "🔍 तुमच्या वाहन वाटपाची स्थिती तपासा (२४ तासांच्या आत मोबाईल नंबर किंवा रिक्वेस्ट कोडद्वारे)",
                track_btn: "स्थिती तपासा",
                badge_ground: "समागम ग्राउंड अंतर्गत सेवा",
                card1_title: "समागम ग्राउंडच्या आत वाहन हवे आहे",
                card1_desc: "लंगर, टेंट, साउंड, मेडिकल, सुरक्षा व स्वच्छता विभागांसाठी खारघर ग्राउंडच्या आत कार, पिकअप, टेम्पोची मागणी करा अथवा सेवेसाठी वाहन जमा करा.",
                card1_pt1: "विभाग प्रमुखांची सही व शिक्का असलेला मागणी अर्ज",
                card1_pt2: "सेवा करण्यासाठी वाहन प्राप्ती फॉर्म",
                card1_btn: "ग्राउंडसाठी वाहन मागणी / जमा करा",
                badge_transit: "रेल्वे स्टेशन • एअरपोर्ट • बस डेपो",
                card2_title: "पिकअप आणि ड्रॉपसाठी वाहन हवे आहे",
                card2_desc: "पनवेल, ठाणे, CSMT, LTT, दादर, कल्याण रेल्वे स्टेशन, मुंबई एअरपोर्ट किंवा बस डेपोवरून संत व जत्थ्यांच्या ने-आण करण्यासाठी वाहन मागणी नोंदवा.",
                card2_pt1: "मुख्य परिवहन डेटाबेसशी थेट जोडणी",
                card2_pt3: "मोबाईल नंबरद्वारे ड्रायव्हर व वाहनाचे थेट अपडेट",
                card2_btn: "पिकअप / ड्रॉप वाहन मागणी नोंदवा",
                badge_adv: "२४ तासांत स्टेटस अपडेट",
                card3_title: "आगाऊ सेवेसाठी वाहन विनंती (Service for Advance Sewa)",
                card3_desc: "आगाऊ सेवेसाठी नाव, संपर्क क्रमांक, ब्रांच, युनिट नंबर, लँडमार्क, जवळचे रेल्वे स्टेशन, सेवेची तारीख, प्रवास सुरू करण्याची व परतीची वेळ यासह विनंती नोंदवा.",
                card3_pt1: "थेट मुख्य डेटाबेसशी जोडलेले",
                card3_pt2: "२४ तासांत मुख्य पानावर वाहन वाटपाची स्थिती पहा",
                card3_btn: "आगाऊ सेवा वाहन विनंती नोंदवा",
                live_feed_title: "📡 मुख्य परिवहन डेटाबेसमध्ये नोंदवलेल्या थेट विनंत्या",
                modal_pd_title: "पिकअप आणि ड्रॉप वाहन मागणी फॉर्म",
                modal_adv_title: "आगाऊ सेवेसाठी वाहन विनंती (Service for Advance Sewa)",
                lbl_trip_dir: "प्रवासाचा प्रकार *",
                lbl_transit_hub: "रेल्वे स्टेशन / एअरपोर्ट / बस डेपो *",
                lbl_pax: "एकूण प्रवासी संख्या *",
                lbl_veh_pref: "आवश्यक वाहनाचा प्रकार *",
                lbl_veh_qty: "वाहनांची संख्या *",
                lbl_dt: "आगमन / प्रस्थान दिनांक व वेळ *",
                lbl_train: "ट्रेन / फ्लाईट / बस क्रमांक",
                lbl_req_name: "जत्था प्रमुख / समन्वयकाचे नाव *",
                lbl_req_phone: "१०-अंकी मोबाईल नंबर *",
                btn_submit_pd: "परिवहन कंट्रोल रूमकडे मागणी पाठवा",
                lbl_adv_name: "नाव (Name) *",
                lbl_adv_phone: "संपर्क क्रमांक (Contact Number) *",
                lbl_adv_branch: "ब्रांच (Branch) *",
                lbl_adv_unit: "युनिट नंबर (Unit Number) *",
                lbl_adv_landmark: "लँडमार्क (Landmark) *",
                lbl_adv_station: "जवळचे रेल्वे स्टेशन (Nearest Railway Station) *",
                lbl_adv_date: "सेवेची तारीख (Date of Sewa) *",
                lbl_adv_start: "प्रवास सुरू करण्याची वेळ (Time to Start Journey) *",
                lbl_adv_return: "परतीची वेळ (Time to Return) *",
                lbl_adv_pax: "सेवादार संख्या",
                btn_submit_adv: "आगाऊ सेवा विनंती सादर करा"
            }
        };

        function setLanguage(lang, btn) {
            const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (dict[key]) el.textContent = dict[key];
            });
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            localStorage.setItem('samagam_portal_lang', lang);
        }

        function openPickupDropModal() {
            document.getElementById('pickup-drop-modal').classList.remove('hidden');
            document.getElementById('pickup-drop-modal').classList.add('flex');
        }

        function closePickupDropModal() {
            document.getElementById('pickup-drop-modal').classList.add('hidden');
            document.getElementById('pickup-drop-modal').classList.remove('flex');
        }

        function openAdvanceSewaModal() {
            document.getElementById('advance-sewa-modal').classList.remove('hidden');
            document.getElementById('advance-sewa-modal').classList.add('flex');
        }

        function closeAdvanceSewaModal() {
            document.getElementById('advance-sewa-modal').classList.add('hidden');
            document.getElementById('advance-sewa-modal').classList.remove('flex');
        }

        async function submitPickupDropRequest(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.passenger_count = parseInt(payload.passenger_count) || 1;
            payload.vehicles_needed = parseInt(payload.vehicles_needed) || 1;

            const res = await fetch('/api/operations/pickup-drop-requests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('last_requester_query', payload.requester_phone);
                document.getElementById('track-query-input').value = payload.requester_phone;
                alert(`धन निरंकार जी 🙏\nPickup/Drop Vehicle Request Submitted!\nRequest ID: ${data.request_code}\n\nEnter your mobile number (${payload.requester_phone}) in the Status Tracker box on this page anytime for live bus & driver allocation updates.`);
                e.target.reset();
                closePickupDropModal();
                checkMyRequestStatus();
                loadRecentRequests();
            } else {
                alert('❌ ' + (data.detail || 'Could not submit request.'));
            }
        }

        async function submitAdvanceSewaRequest(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.passenger_count = parseInt(payload.passenger_count) || 1;

            const res = await fetch('/api/operations/advance-sewa-requests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('last_requester_query', payload.contact_number);
                document.getElementById('track-query-input').value = payload.contact_number;
                alert(`धन निरंकार जी 🙏\nAdvance Sewa Request Saved!\nRequest ID: ${data.request_code}\n\nYou can check your vehicle allocation status on this homepage within 24 hours using your Contact Number (${payload.contact_number}) or Request ID (${data.request_code}).`);
                e.target.reset();
                closeAdvanceSewaModal();
                checkMyRequestStatus();
                loadRecentRequests();
            } else {
                alert('❌ ' + (data.detail || 'Could not submit Advance Sewa request.'));
            }
        }

        async function checkMyRequestStatus() {
            const q = document.getElementById('track-query-input').value.trim();
            if (!q) return;
            localStorage.setItem('last_requester_query', q);
            const box = document.getElementById('track-status-results');
            box.innerHTML = '<div class="text-xs text-slate-500">Checking live allocation status...</div>';

            const res = await fetch(`/api/operations/request-status-lookup?query=${encodeURIComponent(q)}`);
            if (!res.ok) {
                box.innerHTML = '<div class="p-3 rounded-2xl bg-rose-50 text-rose-700 text-xs font-semibold">No requests found for that mobile number or request code.</div>';
                return;
            }
            const items = await res.json();
            if (!items.length) {
                box.innerHTML = '<div class="p-3 rounded-2xl bg-amber-50 text-amber-800 text-xs font-semibold">No matching requests found yet.</div>';
                return;
            }

            box.innerHTML = items.map(item => {
                const isAllocated = item.is_allocated;
                return `
                    <div class="p-4 rounded-2xl border-2 ${isAllocated ? 'bg-emerald-50 border-emerald-500' : 'bg-amber-50/70 border-amber-300'} flex flex-wrap justify-between items-center gap-3 text-xs">
                        <div class="space-y-1">
                            <div class="flex items-center gap-2">
                                <span class="font-extrabold text-sm text-slate-900">${item.code}</span>
                                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${isAllocated ? 'bg-emerald-700 text-white' : 'bg-amber-500 text-slate-950'}">
                                    ${isAllocated ? '✅ VEHICLE ALLOCATED' : '⏳ PENDING ALLOCATION'}
                                </span>
                            </div>
                            <div class="font-semibold text-slate-700">${item.category} • ${item.summary}</div>
                            <div class="text-slate-500">Requester: ${item.requester_name} (${item.requester_phone})</div>
                        </div>
                        ${isAllocated ? `
                            <div class="bg-white p-3 rounded-xl border border-emerald-300 text-right space-y-1 shadow-sm">
                                <div class="text-[10px] uppercase font-bold text-emerald-700">Assigned Vehicle & Driver</div>
                                <div class="text-sm font-black text-slate-900">${item.assigned_vehicle_reg}</div>
                                <div class="text-slate-700 font-bold">${item.driver_name || 'Assigned Sevadar'}</div>
                                ${item.driver_phone ? `<a href="tel:${item.driver_phone}" class="inline-block mt-1 bg-emerald-700 text-white font-bold px-3 py-1 rounded-lg">📞 Call ${item.driver_phone}</a>` : ''}
                            </div>
                        ` : `
                            <div class="text-right text-amber-900 font-bold">
                                Transport Control Room is reviewing.<br>Refresh or check back within 24 hours.
                            </div>
                        `}
                    </div>
                `;
            }).join('');
        }

        async function loadRecentRequests() {
            try {
                const [pdRes, deptRes, advRes] = await Promise.all([
                    fetch('/api/operations/pickup-drop-requests'),
                    fetch('/api/fleet/dept-requisitions'),
                    fetch('/api/operations/advance-sewa-requests')
                ]);
                const pdList = pdRes.ok ? await pdRes.json() : [];
                const deptList = deptRes.ok ? await deptRes.json() : [];
                const advList = advRes.ok ? await advRes.json() : [];
                const grid = document.getElementById('recent-requests-grid');

                const cards = [];
                advList.slice(0, 4).forEach(a => {
                    cards.push(`
                        <div class="p-3.5 rounded-2xl bg-amber-50/80 border border-amber-300 flex justify-between items-center">
                            <div>
                                <div class="font-extrabold text-amber-950">${a.request_code} • Advance Sewa (${a.branch_name})</div>
                                <div class="text-slate-700">${a.nearest_railway_station} • ${a.date_of_sewa} (${a.start_journey_time}–${a.return_time})</div>
                                <div class="text-[11px] text-slate-500">By: ${a.requester_name} (Unit ${a.unit_number})</div>
                            </div>
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-amber-600 text-slate-950">${a.status}</span>
                        </div>
                    `);
                });
                pdList.slice(0, 4).forEach(r => {
                    cards.push(`
                        <div class="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex justify-between items-center">
                            <div>
                                <div class="font-extrabold text-emerald-950">${r.request_code} • ${r.transit_hub}</div>
                                <div class="text-slate-600">${r.trip_direction} • ${r.passenger_count} Pax • ${r.vehicles_needed}x ${r.vehicle_type_requested}</div>
                                <div class="text-[11px] text-slate-500">By: ${r.requester_name} (${r.requester_phone})</div>
                            </div>
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-emerald-700 text-white">${r.status}</span>
                        </div>
                    `);
                });
                deptList.slice(0, 4).forEach(d => {
                    cards.push(`
                        <div class="p-3.5 rounded-2xl bg-sky-50/70 border border-sky-200 flex justify-between items-center">
                            <div>
                                <div class="font-extrabold text-[#0f2c59]">${d.requisition_code} • ${d.department_name}</div>
                                <div class="text-slate-600">In-Ground: ${d.quantity_needed}x ${d.required_vehicle_type}</div>
                                <div class="text-[11px] text-slate-500">Dept Head: ${d.department_head_name}</div>
                            </div>
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-[#0f2c59] text-white">${d.status}</span>
                        </div>
                    `);
                });

                grid.innerHTML = cards.length ? cards.join('') : '<p class="text-slate-400">No requests logged yet. Submit one above!</p>';
            } catch (_) {}
        }

        window.addEventListener('DOMContentLoaded', () => {
            const savedLang = localStorage.getItem('samagam_portal_lang') || 'en';
            const btn = document.querySelector(`.lang-btn[onclick*="'${savedLang}'"]`);
            if (btn) setLanguage(savedLang, btn);

            const lastQ = localStorage.getItem('last_requester_query');
            if (lastQ) {
                document.getElementById('track-query-input').value = lastQ;
                checkMyRequestStatus();
            }
            loadRecentRequests();
            setInterval(() => {
                if (document.getElementById('track-query-input').value.trim()) {
                    checkMyRequestStatus();
                }
            }, 30000);
        });
    </script>
</body>
</html>
'''


def main():
    print(f"🚀 Updating Samagam Transport files in: {TARGET_DIR}\n")
    for rel_path, content in FILES.items():
        full_path = os.path.join(TARGET_DIR, rel_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Wrote clean file: {full_path}")
    print("\n🎉 All updates applied cleanly! Now run:")
    print("   Remove-Item -Path samagam_production.db -Force -ErrorAction SilentlyContinue")
    print("   python run.py")


if __name__ == "__main__":
    main()