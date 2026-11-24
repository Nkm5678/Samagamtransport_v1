import hashlib
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
ADMIN_MASTER_PASSWORD = os.environ.get("ADMIN_MASTER_PASSWORD", "Narendra@2183").strip()
OTP_DEV_ECHO = os.environ.get("OTP_DEV_ECHO", "1") == "1"
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _tok_hash(tok: str) -> str:
    return hashlib.sha256(str(tok or "").encode()).hexdigest()


def _otp_hash(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def _norm_phone(p: str) -> str:
    d = re.sub(r"\D", "", str(p or ""))
    return d[-10:] if len(d) > 10 else d


def _norm_email(e: str) -> str:
    return str(e or "").strip().lower()[:120]


def _norm_pin(p: str) -> str:
    return re.sub(r"\D", "", str(p or ""))


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


def get_optional_volunteer(
    x_session_token: str = Header(None),
    x_driver_token: str = Header(None),
    db: Session = Depends(get_db)
):
    raw_tok = x_driver_token or x_session_token
    if not raw_tok:
        return None
    session = db.query(VolunteerSession).filter(
        VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        return None
    return db.query(Volunteer).filter(Volunteer.id == session.volunteer_id, Volunteer.is_active == True).first()


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


# ------------------------------------------------------------------
# 1. UNIFIED OTP & 4-DIGIT PIN AUTHENTICATION FOR ALL FIELD ROLES
# ------------------------------------------------------------------

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
    code = re.sub(r"\D", "", str(data.get("otp") or ""))
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
    role = str(data.get("system_role") or "FIELD_VOLUNTEER").upper().strip()
    branch_name = str(data.get("branch_name") or "").strip()
    unit_number = str(data.get("unit_number") or "").strip()
    bus_operator_name = str(data.get("bus_operator_name") or "").strip()

    if not name or not phone:
        return {"needs_registration": True, "requires_code": bool(REG_CODE)}
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number.")
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="Create a 4-digit numerical PIN.")
    if REG_CODE and str(data.get("code") or "").strip() != REG_CODE:
        raise HTTPException(status_code=403, detail="Wrong event code. Ask the Control Room.")

    if role == "DRIVER":
        if not bus_operator_name:
            raise HTTPException(status_code=400, detail="Bus Operator / Travels Name is required for Drivers.")
        stored_branch = f"Operator: {bus_operator_name}"
        stored_unit = "Fleet-Driver"
    else:
        if not branch_name or not unit_number:
            raise HTTPException(status_code=400, detail="Branch Name and Unit Number are required for all non-driver team members.")
        stored_branch = branch_name
        stored_unit = unit_number

    if db.query(Volunteer).filter(Volunteer.mobile_number == phone).first():
        raise HTTPException(status_code=409, detail="This mobile number is already registered.")

    vol = Volunteer(
        volunteer_code=f"{'DRV' if role == 'DRIVER' else 'CREW'}-{secrets.randbelow(9000) + 1000}",
        full_name=name,
        mobile_number=phone,
        email=email,
        pin_hash=generate_password_hash(pin),
        unit_number=stored_unit,
        branch_name=stored_branch,
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

    vol = None
    if "@" in ident:
        vol = db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first()
    else:
        vol = db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()

    if not vol:
        raise HTTPException(status_code=404, detail="Crew account not found.")
    if not vol.pin_hash:
        raise HTTPException(status_code=403, detail="No PIN set yet. Use 'Forgot PIN' or ask Control Room.")
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
    phone_digits = _norm_phone(ident)
    vol = (
        db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first()
        if "@" in ident
        else db.query(Volunteer).filter(Volunteer.mobile_number == phone_digits).first()
    )
    if not vol:
        raise HTTPException(status_code=404, detail="No registered account found for this mobile number or email.")

    otp_key = _norm_email(vol.email) if vol.email else f"phone:{vol.mobile_number}"
    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(8)
    now_ts = time.time()
    row = db.query(EmailOTP).filter(EmailOTP.email == otp_key).first()
    if row:
        row.code_hash, row.salt, row.expires_ts, row.attempts, row.sent_ts = _otp_hash(code, salt), salt, now_ts + OTP_TTL, 0, now_ts
    else:
        db.add(EmailOTP(email=otp_key, code_hash=_otp_hash(code, salt), salt=salt, expires_ts=now_ts + OTP_TTL, attempts=0, sent_ts=now_ts))
    db.commit()

    if vol.email and "@" in vol.email:
        send_email_async_safe(vol.email, f"{code} — Samagam PIN Reset Code", f"<p>Your PIN reset OTP is <strong>{code}</strong>.</p>")

    resp = {"sent": True, "email": vol.email or "", "target": vol.email or f"Mobile {vol.mobile_number}"}
    if OTP_DEV_ECHO:
        resp["dev_otp"] = code
    return resp


@router.post("/pin/reset/verify")
def verify_pin_reset(data: dict, db: Session = Depends(get_db)):
    ident = str(data.get("identifier") or "").strip()
    code = re.sub(r"\D", "", str(data.get("otp") or ""))
    pin = _norm_pin(data.get("pin"))
    phone_digits = _norm_phone(ident)
    vol = (
        db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first()
        if "@" in ident
        else db.query(Volunteer).filter(Volunteer.mobile_number == phone_digits).first()
    )
    if not vol:
        raise HTTPException(status_code=404, detail="Account not found.")

    otp_key = _norm_email(vol.email) if vol.email else f"phone:{vol.mobile_number}"
    row = db.query(EmailOTP).filter(EmailOTP.email == otp_key).first()
    if not row and vol.email:
        row = db.query(EmailOTP).filter(EmailOTP.email == _norm_email(vol.email)).first()

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


@router.get("/session-heartbeat")
def check_active_session_heartbeat(
    x_driver_token: str = Header(None),
    x_session_token: str = Header(None),
    db: Session = Depends(get_db)
):
    """Validates that the web/APK user is logged in and has NOT been terminated by Admin."""
    raw_tok = x_driver_token or x_session_token
    if not raw_tok:
        raise HTTPException(status_code=401, detail="Login required to access Samagam Web/Mobile Apps.")
    session = db.query(VolunteerSession).filter(
        VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired or terminated. Please sign in again.")
    vol = db.query(Volunteer).filter(Volunteer.id == session.volunteer_id).first()
    if not vol or not vol.is_active:
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=403, detail="TERMINATED: Your access has been revoked by the Control Room Admin.")
    return {
        "authenticated": True,
        "user": {
            "id": vol.id,
            "volunteer_code": vol.volunteer_code,
            "full_name": vol.full_name,
            "mobile_number": vol.mobile_number,
            "system_role": vol.system_role,
            "duty_location": vol.duty_location
        }
    }


@router.post("/admin-terminate-user")
def admin_terminate_user(data: dict, db: Session = Depends(get_db)):
    """Immediately terminates a user's account and destroys all active Web & APK sessions."""
    crew_id = data.get("crew_id")
    mobile = _norm_phone(data.get("mobile_number"))
    vol = db.query(Volunteer).filter(Volunteer.id == int(crew_id)).first() if crew_id else db.query(Volunteer).filter(Volunteer.mobile_number == mobile).first()
    if not vol:
        raise HTTPException(status_code=404, detail="User account not found.")

    vol.is_active = False
    deleted_sessions = db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    db.commit()
    return {
        "status": "TERMINATED",
        "crew_id": vol.id,
        "full_name": vol.full_name,
        "mobile_number": vol.mobile_number,
        "revoked_sessions": deleted_sessions
    }


@router.post("/admin-reactivate-user")
def admin_reactivate_user(data: dict, db: Session = Depends(get_db)):
    """Re-enables a previously terminated user account so they can log in again."""
    crew_id = data.get("crew_id")
    vol = db.query(Volunteer).filter(Volunteer.id == int(crew_id)).first()
    if not vol:
        raise HTTPException(status_code=404, detail="User account not found.")
    vol.is_active = True
    db.commit()
    return {"status": "REACTIVATED", "crew_id": vol.id, "full_name": vol.full_name}
    if not vol:
        raise HTTPException(status_code=404, detail="Crew member not found.")
    vol.pin_hash = generate_password_hash(pin)
    db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    db.commit()
    return {"status": "PIN_RESET", "crew_id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number, "new_pin": pin}


ADMIN_ACCESS_CODE = os.environ.get("ADMIN_ACCESS_CODE", "SAMAGAM-HQ-2026").strip()


@router.post("/control-room-login")
def control_room_admin_login(data: dict, request: Request, db: Session = Depends(get_db)):
    host = (request.headers.get("host") or "").lower().split(":")[0]
    is_admin_subdomain = (host == "admin.samagamtransport.in" or host.startswith("admin."))

    mobile = _norm_phone(data.get("mobile_number"))
    passcode = str(data.get("access_code") or data.get("password") or "").strip()
    if len(mobile) != 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit registered mobile number.")

    vol = db.query(Volunteer).filter(Volunteer.mobile_number == mobile, Volunteer.is_active == True).first()
    is_admin_role = bool(vol and vol.system_role in ("GROUND_ADMIN", "ADMIN", "CONTROL_ROOM"))
    pin_valid = bool(vol and vol.pin_hash and len(_norm_pin(passcode)) == 4 and check_password_hash(vol.pin_hash, _norm_pin(passcode)))
    master_pwd_valid = bool(ADMIN_MASTER_PASSWORD and hmac.compare_digest(passcode, ADMIN_MASTER_PASSWORD))
    code_valid = bool(ADMIN_ACCESS_CODE and hmac.compare_digest(passcode, ADMIN_ACCESS_CODE))

    if not ((is_admin_role and pin_valid) or master_pwd_valid or code_valid):
        raise HTTPException(status_code=403, detail="Access Denied: Invalid Admin credentials.")

    if not is_admin_subdomain and not master_pwd_valid:
        raise HTTPException(status_code=403, detail="Control Room login must use https://admin.samagamtransport.in")

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


@router.post("/assign-driver-bus")
def assign_driver_to_bus(data: dict, db: Session = Depends(get_db)):
    reg = str(data.get("vehicle_reg_number") or "").upper().strip()
    phone = _norm_phone(data.get("driver_phone"))
    name = str(data.get("driver_name") or "").strip()
    email = _norm_email(data.get("driver_email")) or None
    pin = _norm_pin(data.get("pin") or "1234")

    veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == reg).first()
    if not veh:
        raise HTTPException(status_code=404, detail=f"Vehicle {reg} not found.")
    if len(phone) != 10 or not name:
        raise HTTPException(status_code=400, detail="Valid driver name and 10-digit mobile required.")

    vol = db.query(Volunteer).filter(Volunteer.mobile_number == phone).first()
    if not vol:
        vol = Volunteer(
            volunteer_code=f"DRV-{secrets.randbelow(9000) + 1000}",
            full_name=name,
            mobile_number=phone,
            email=email,
            pin_hash=generate_password_hash(pin if len(pin) == 4 else "1234"),
            unit_number="Fleet-Crew",
            branch_name="Samagam Transport",
            duty_location=veh.current_hub,
            system_role="DRIVER",
            is_driver=True,
            assigned_vehicle_id=veh.id,
            geofence_verified=True
        )
        db.add(vol)
        db.commit()
        db.refresh(vol)
    else:
        vol.full_name = name
        vol.assigned_vehicle_id = veh.id
        if email:
            vol.email = email
        if data.get("pin") and len(pin) == 4:
            vol.pin_hash = generate_password_hash(pin)

    db.query(Vehicle).filter(Vehicle.assigned_driver_id == vol.id).update({"assigned_driver_id": None})
    veh.assigned_driver_id = vol.id
    veh.driver_name = name
    veh.driver_phone = phone
    db.commit()

    return {"status": "ASSIGNED", "vehicle_reg_number": veh.vehicle_reg_number, "driver_id": vol.id, "driver_name": vol.full_name, "pin": pin}


# ------------------------------------------------------------------
# 3. 2.0KM GEOFENCE VOLUNTEER REGISTRATION & LOGIN
# ------------------------------------------------------------------

def _determine_role_and_permissions(duty_location: str) -> dict:
    loc_lower = duty_location.lower()
    if "ground" in loc_lower or "control" in loc_lower or "venue" in loc_lower:
        return {
            "system_role": "GROUND_ADMIN",
            "can_view_all_territories": True,
            "can_execute_ground_tasks": True,
            "can_execute_station_tasks": True,
            "can_manage_fleet": True
        }
    return {
        "system_role": "STATION_COORDINATOR",
        "can_view_all_territories": False,
        "can_execute_ground_tasks": False,
        "can_execute_station_tasks": True,
        "can_manage_fleet": False
    }


@router.post("/register")
def register_volunteer(req: VolunteerRegisterRequest, db: Session = Depends(get_db)):
    is_valid, distance_m, msg, hub = verify_territory_geofence(db, req.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)

    existing = db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mobile number already registered. Please use Login.")

    perms = _determine_role_and_permissions(req.duty_location)
    vol_code = f"VOL-{hub.hub_code}-{secrets.randbelow(9000) + 1000}"

    assigned_veh_id = None
    if req.assigned_vehicle_reg:
        veh = db.query(Vehicle).filter(Vehicle.vehicle_reg_number == req.assigned_vehicle_reg.upper().strip()).first()
        if veh:
            assigned_veh_id = veh.id

    vol = Volunteer(
        volunteer_code=vol_code,
        full_name=req.full_name.strip(),
        mobile_number=req.mobile_number.strip(),
        unit_number=req.unit_number.strip(),
        branch_name=req.branch_name.strip(),
        photo_b64=req.photo_b64,
        duty_location=req.duty_location,
        device_fingerprint=req.device_fingerprint,
        latitude=req.latitude,
        longitude=req.longitude,
        geo_accuracy=req.geo_accuracy,
        geofence_verified=True,
        assigned_vehicle_id=assigned_veh_id,
        **perms
    )
    db.add(vol)
    db.commit()
    db.refresh(vol)

    token = secrets.token_hex(32)
    db.add(VolunteerSession(
        session_token=token,
        volunteer_id=vol.id,
        device_fingerprint=req.device_fingerprint,
        latitude=req.latitude,
        longitude=req.longitude,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    ))
    db.commit()

    return {
        "status": "REGISTERED_AND_VERIFIED",
        "geofence_message": msg,
        "distance_meters": distance_m,
        "session_token": token,
        "volunteer": {
            "id": vol.id,
            "volunteer_code": vol.volunteer_code,
            "full_name": vol.full_name,
            "mobile_number": vol.mobile_number,
            "duty_location": vol.duty_location,
            "system_role": vol.system_role,
            "can_view_all_territories": vol.can_view_all_territories,
            "can_manage_fleet": vol.can_manage_fleet
        }
    }


@router.post("/login")
def login_volunteer(req: VolunteerLoginRequest, db: Session = Depends(get_db)):
    vol = db.query(Volunteer).filter(Volunteer.mobile_number == req.mobile_number.strip()).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found. Please complete first-time registration.")

    is_valid, distance_m, msg, _ = verify_territory_geofence(db, vol.duty_location, req.latitude, req.longitude)
    if not is_valid:
        raise HTTPException(status_code=403, detail=msg)

    vol.latitude = req.latitude
    vol.longitude = req.longitude
    vol.geofence_verified = True
    vol.last_login_at = datetime.utcnow()

    token = secrets.token_hex(32)
    db.add(VolunteerSession(
        session_token=token,
        volunteer_id=vol.id,
        device_fingerprint=req.device_fingerprint,
        latitude=req.latitude,
        longitude=req.longitude,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    ))
    db.commit()

    return {
        "status": "AUTHENTICATED",
        "geofence_message": msg,
        "distance_meters": distance_m,
        "session_token": token,
        "volunteer": {
            "id": vol.id,
            "volunteer_code": vol.volunteer_code,
            "full_name": vol.full_name,
            "mobile_number": vol.mobile_number,
            "duty_location": vol.duty_location,
            "system_role": vol.system_role,
            "can_view_all_territories": vol.can_view_all_territories,
            "can_manage_fleet": vol.can_manage_fleet
        }
    }