import hashlib
import hmac
import os
import re
import secrets
import sys
import threading
import time
from datetime import datetime, timedelta

_THIS_FILE = os.path.abspath(__file__)
_CANDIDATE_ROOTS = [
    os.path.abspath(os.path.join(os.path.dirname(_THIS_FILE), "..", "..")),
    r"C:\narendra\SamagamtransportV1",
]
for _root in _CANDIDATE_ROOTS:
    if os.path.isdir(os.path.join(_root, "app")) and _root not in sys.path:
        sys.path.insert(0, _root)

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from google.auth.transport import requests as google_auth_requests
    from google.oauth2 import id_token as google_id_token
    _GOOGLE_REQUEST_ADAPTER = google_auth_requests.Request()
except Exception:
    google_id_token = None
    _GOOGLE_REQUEST_ADAPTER = None

from app.database import get_db
from app.models import Volunteer, VolunteerSession, Vehicle, EmailOTP, CrewDutyShift
from app.schemas import VolunteerRegisterRequest, VolunteerLoginRequest
from app.services.geo_service import verify_territory_geofence
from app.services.email_service import send_email_async_safe

router = APIRouter(prefix="/api/auth", tags=["Authentication, OTP & Geofencing"])

OTP_TTL = 600
OTP_MAX_TRIES = 6
REG_CODE = os.environ.get("REG_CODE", "SAMAGAM26").strip()
ADMIN_ACCESS_CODE = os.environ.get("ADMIN_ACCESS_CODE", "SAMAGAM-HQ-2026").strip()
ADMIN_MASTER_PASSWORD = os.environ.get("ADMIN_MASTER_PASSWORD", "Narendra@2183").strip()
OTP_DEV_ECHO = os.environ.get("OTP_DEV_ECHO", "1") == "1"
EMAIL_RE = re.compile(r"^[^@\s]{1,96}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

IAP_EXPECTED_AUDIENCE = os.environ.get("IAP_EXPECTED_AUDIENCE", "").strip()
IAP_ADMIN_GROUP = os.environ.get("IAP_ADMIN_GROUP", "samagam-transport-admins@samagamtransport.in").strip().lower()
IAP_AUDIT_GROUP = os.environ.get("IAP_AUDIT_GROUP", "samagam-accounts-audit@samagamtransport.in").strip().lower()
IAP_ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("IAP_ADMIN_EMAILS", "").split(",") if e.strip()}
IAP_AUDIT_EMAILS = {e.strip().lower() for e in os.environ.get("IAP_AUDIT_EMAILS", "").split(",") if e.strip()}


def _tok_hash(tok: str) -> str:
    return hashlib.sha256(str(tok or "").encode()).hexdigest()


def _norm_email(val: str | None) -> str:
    return str(val or "").strip().lower()


def _norm_phone(val: str | None) -> str:
    digits = re.sub(r"\D", "", str(val or ""))
    return digits[-10:] if len(digits) >= 10 else digits


def _norm_pin(val: str | None) -> str:
    return re.sub(r"\D", "", str(val or ""))[:4]


def _otp_hash(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def _fire_and_forget_email(to_email: str, subject: str, html_body: str) -> None:
    """Runs SMTP delivery in a daemon thread so OTP/registration APIs NEVER time out."""
    def _runner():
        try:
            send_email_async_safe(to_email, subject, html_body)
        except Exception:
            pass
    threading.Thread(target=_runner, daemon=True).start()


def _driver_payload(db: Session, vol: Volunteer, token: str | None = None) -> dict:
    veh = None
    if vol.assigned_vehicle_id:
        veh = db.query(Vehicle).filter(Vehicle.id == vol.assigned_vehicle_id).first()
    if not veh:
        veh = db.query(Vehicle).filter(Vehicle.assigned_driver_id == vol.id).first()

    out = {
        "status": "AUTHENTICATED",
        "driver": {
            "id": vol.id,
            "volunteer_code": vol.volunteer_code,
            "full_name": vol.full_name,
            "name": vol.full_name,
            "mobile_number": vol.mobile_number,
            "phone": vol.mobile_number,
            "email": vol.email or "",
            "branch_name": vol.branch_name,
            "unit_number": vol.unit_number,
            "duty_location": vol.duty_location,
            "system_role": vol.system_role,
            "assigned_vehicle_reg": veh.vehicle_reg_number if veh else None,
        },
    }
    if token:
        out["token"] = token
        out["session_token"] = token
    return out


def verify_iap_jwt_and_provision_user(iap_jwt: str, db: Session, group_hint: str = "") -> Volunteer:
    if not iap_jwt or google_id_token is None:
        raise HTTPException(status_code=401, detail="Google IAP verification unavailable or missing header.")
    try:
        claims = google_id_token.verify_iap_jwt(
            iap_jwt,
            _GOOGLE_REQUEST_ADAPTER,
            audience=IAP_EXPECTED_AUDIENCE or None,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google IAP JWT signature: {exc}")

    raw_email = str(claims.get("email") or "").strip().lower()
    if ":" in raw_email:
        raw_email = raw_email.split(":", 1)[1].strip()
    if not raw_email:
        raise HTTPException(status_code=401, detail="IAP token missing verified email claim.")

    google_sub = str(claims.get("sub") or "").strip()
    token_groups = {
        str(g).strip().lower()
        for g in (claims.get("groups") or claims.get("gcip", {}).get("groups") or [])
        if str(g).strip()
    }
    if group_hint:
        for g in group_hint.split(","):
            if g.strip():
                token_groups.add(g.strip().lower())

    if IAP_ADMIN_GROUP in token_groups or raw_email in IAP_ADMIN_EMAILS:
        mapped_role = "GROUND_ADMIN"
        perms = dict(can_view_all_territories=True, can_execute_ground_tasks=True, can_execute_station_tasks=True, can_manage_fleet=True)
    elif IAP_AUDIT_GROUP in token_groups or raw_email in IAP_AUDIT_EMAILS or raw_email.endswith("@samagamtransport.in"):
        mapped_role = "ACCOUNTS_AUDITOR"
        perms = dict(can_view_all_territories=True, can_execute_ground_tasks=False, can_execute_station_tasks=False, can_manage_fleet=False)
    else:
        raise HTTPException(status_code=403, detail=f"Access Denied: {raw_email} not authorized in IAP groups.")

    vol = db.query(Volunteer).filter(Volunteer.email == raw_email).first()
    if vol and not vol.is_active:
        raise HTTPException(status_code=403, detail="Account disabled in Control Room.")

    if not vol:
        synthetic_mobile = f"99{int(hashlib.sha256(raw_email.encode()).hexdigest()[:8], 16) % 100000000:08d}"
        vol = Volunteer(
            volunteer_code=f"IAP-{secrets.randbelow(9000) + 1000}",
            full_name=str(claims.get("name") or raw_email.split("@")[0].replace(".", " ").title()).strip(),
            mobile_number=synthetic_mobile,
            email=raw_email,
            unit_number="Google-IAP",
            branch_name="Samagam Workspace IAM",
            duty_location="Ground 1 (Main Hall)",
            system_role=mapped_role,
            device_fingerprint=google_sub[:64] if google_sub else None,
            geofence_verified=True,
            **perms,
        )
        db.add(vol)
    else:
        vol.system_role = mapped_role
        vol.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(vol)
    return vol


def get_current_volunteer(
    x_session_token: str = Header(None),
    x_driver_token: str = Header(None),
    x_goog_iap_jwt_assertion: str = Header(None),
    x_goog_iap_groups: str = Header(""),
    db: Session = Depends(get_db),
) -> Volunteer:
    if x_goog_iap_jwt_assertion:
        return verify_iap_jwt_and_provision_user(x_goog_iap_jwt_assertion, db, group_hint=x_goog_iap_groups)
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
    x_goog_iap_jwt_assertion: str = Header(None),
    x_goog_iap_groups: str = Header(""),
    db: Session = Depends(get_db),
):
    if x_goog_iap_jwt_assertion:
        try:
            return verify_iap_jwt_and_provision_user(x_goog_iap_jwt_assertion, db, group_hint=x_goog_iap_groups)
        except HTTPException:
            return None
    raw_tok = x_driver_token or x_session_token
    if not raw_tok:
        return None
    session = db.query(VolunteerSession).filter(
        VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])
    ).first()
    if not session or session.expires_at < datetime.utcnow():
        return None
    return db.query(Volunteer).filter(Volunteer.id == session.volunteer_id, Volunteer.is_active == True).first()


@router.get("/iap/session")
def exchange_google_iap_session(
    x_goog_iap_jwt_assertion: str = Header(None),
    x_goog_iap_groups: str = Header(""),
    db: Session = Depends(get_db),
):
    vol = verify_iap_jwt_and_provision_user(x_goog_iap_jwt_assertion, db, group_hint=x_goog_iap_groups)
    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(hours=12)))
    db.commit()
    return {
        "status": "AUTHORIZED_VIA_GOOGLE_IAP",
        "session_token": raw_tok,
        "member": {
            "id": vol.id,
            "volunteer_code": vol.volunteer_code,
            "full_name": vol.full_name,
            "email": vol.email,
            "mobile_number": vol.mobile_number,
            "system_role": vol.system_role,
            "can_manage_fleet": vol.can_manage_fleet,
        },
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
            "system_role": vol.system_role,
        }

    # Support one-time Mobile OTP registration (used by Ground Service Dept Heads & Kshetriya Sanchalaks)
    allow_mobile_otp = bool(data.get("allow_mobile_otp"))
    otp_key = email
    if not otp_key:
        if not allow_mobile_otp:
            raise HTTPException(status_code=404, detail="Mobile number not registered yet. Register first using your email address.")
        phone = _norm_phone(ident)
        otp_key = f"phone:{phone}"

    code = f"{secrets.randbelow(1000000):06d}"
    salt = secrets.token_hex(8)
    now_ts = time.time()
    existing_otp = db.query(EmailOTP).filter(EmailOTP.email == otp_key).first()
    if existing_otp:
        existing_otp.code_hash = _otp_hash(code, salt)
        existing_otp.salt = salt
        existing_otp.expires_ts = now_ts + OTP_TTL
        existing_otp.attempts = 0
        existing_otp.sent_ts = now_ts
    else:
        db.add(EmailOTP(email=otp_key, code_hash=_otp_hash(code, salt), salt=salt, expires_ts=now_ts + OTP_TTL, attempts=0, sent_ts=now_ts))
    db.commit()

    if email:
        _fire_and_forget_email(
            email,
            f"{code} is your Samagam Field Verification Code",
            f"<h3>Samagam Transport</h3><p>Your 6-digit login code is <strong>{code}</strong> (valid for 10 minutes).</p>",
        )

    resp = {"sent": True, "email": email or otp_key, "mobile": _norm_phone(ident) if not email else "", "ttl": OTP_TTL}
    if OTP_DEV_ECHO or not email:
        resp["dev_otp"] = code
    return resp


@router.post("/otp/verify")
def verify_driver_otp(data: dict, db: Session = Depends(get_db)):
    raw_email_or_key = str(data.get("email") or data.get("identifier") or "").strip()
    phone = _norm_phone(data.get("phone") or (raw_email_or_key if "@" not in raw_email_or_key else ""))
    email = _norm_email(raw_email_or_key) if "@" in raw_email_or_key else None
    otp_key = email if email else (raw_email_or_key if raw_email_or_key.startswith("phone:") else f"phone:{phone}")

    code = re.sub(r"\D", "", str(data.get("otp") or ""))
    row = db.query(EmailOTP).filter(EmailOTP.email == otp_key).first()
    if not row or row.expires_ts < time.time():
        raise HTTPException(status_code=400, detail="This OTP has expired. Please tap Back and request a new OTP.")
    if row.attempts >= OTP_MAX_TRIES:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=429, detail="Too many wrong OTP attempts. Request a new OTP.")
    if not code or not hmac.compare_digest(_otp_hash(code, row.salt), row.code_hash):
        row.attempts += 1
        db.commit()
        raise HTTPException(status_code=403, detail="Wrong 6-digit OTP code.")

    name = str(data.get("name") or "").strip()[:100]
    pin = _norm_pin(data.get("pin"))
    role = str(data.get("system_role") or "FIELD_VOLUNTEER").upper().strip()
    branch_name = str(data.get("branch_name") or "").strip()[:100]
    unit_number = str(data.get("unit_number") or "").strip()[:40]
    bus_operator_name = str(data.get("bus_operator_name") or "").strip()[:100]
    submitted_code = str(data.get("code") or REG_CODE).strip().upper()

    if not name or not phone:
        return {"needs_registration": True, "requires_code": bool(REG_CODE)}
    if len(phone) != 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number.")
    if len(pin) != 4:
        raise HTTPException(status_code=400, detail="Create a 4-digit numerical PIN.")
    if REG_CODE and submitted_code != REG_CODE.upper():
        raise HTTPException(status_code=403, detail=f"Wrong event code. Use {REG_CODE}.")

    if role == "DRIVER":
        if not bus_operator_name:
            raise HTTPException(status_code=400, detail="Bus Operator / Travels Name is required for Drivers.")
        stored_branch = f"Operator: {bus_operator_name}"
        stored_unit = "Fleet-Driver"
    else:
        if not branch_name or not unit_number:
            raise HTTPException(status_code=400, detail="Branch Name and Unit Number are required.")
        stored_branch = branch_name
        stored_unit = unit_number

    existing_vol = db.query(Volunteer).filter(Volunteer.mobile_number == phone).first()
    if existing_vol:
        # Allow completing PIN/email binding cleanly if user was pre-created without PIN
        existing_vol.full_name = name
        existing_vol.email = email
        existing_vol.pin_hash = generate_password_hash(pin)
        existing_vol.branch_name = stored_branch
        existing_vol.unit_number = stored_unit
        existing_vol.is_active = True
        vol = existing_vol
    else:
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
            geofence_verified=True,
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

    vol = (
        db.query(Volunteer).filter(Volunteer.email == _norm_email(ident)).first()
        if "@" in ident
        else db.query(Volunteer).filter(Volunteer.mobile_number == _norm_phone(ident)).first()
    )
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
        _fire_and_forget_email(vol.email, f"{code} — Samagam PIN Reset Code", f"<p>Your PIN reset OTP is <strong>{code}</strong>.</p>")

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


@router.post("/driver-logout")
def driver_logout(
    x_driver_token: str = Header(None),
    x_session_token: str = Header(None),
    db: Session = Depends(get_db),
):
    raw_tok = x_driver_token or x_session_token
    if raw_tok:
        db.query(VolunteerSession).filter(
            VolunteerSession.session_token.in_([raw_tok, _tok_hash(raw_tok)])
        ).delete(synchronize_session=False)
        db.commit()
    return {"status": "LOGGED_OUT"}


@router.get("/session-heartbeat")
def check_active_session_heartbeat(
    x_driver_token: str = Header(None),
    x_session_token: str = Header(None),
    db: Session = Depends(get_db),
):
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
            "duty_location": vol.duty_location,
        },
    }


@router.get("/crew")
def list_registered_crew(db: Session = Depends(get_db)):
    rows = db.query(Volunteer).order_by(Volunteer.id.desc()).all()
    return [
        {
            "id": v.id,
            "volunteer_code": v.volunteer_code,
            "full_name": v.full_name,
            "mobile_number": v.mobile_number,
            "email": v.email or "",
            "branch_name": v.branch_name,
            "unit_number": v.unit_number,
            "duty_location": v.duty_location,
            "system_role": v.system_role,
            "is_active": v.is_active,
        }
        for v in rows
    ]


@router.post("/admin-reset-pin")
def admin_reset_crew_pin(data: dict, db: Session = Depends(get_db)):
    crew_id = data.get("crew_id")
    pin = _norm_pin(data.get("new_pin") or "1234")
    vol = db.query(Volunteer).filter(Volunteer.id == int(crew_id)).first() if crew_id else None
    if not vol:
        raise HTTPException(status_code=404, detail="Crew member not found.")
    vol.pin_hash = generate_password_hash(pin if len(pin) == 4 else "1234")
    db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    db.commit()
    return {"status": "PIN_RESET", "crew_id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number, "new_pin": pin}


@router.post("/admin-terminate-user")
def admin_terminate_user(data: dict, db: Session = Depends(get_db)):
    crew_id = data.get("crew_id")
    mobile = _norm_phone(data.get("mobile_number"))
    vol = db.query(Volunteer).filter(Volunteer.id == int(crew_id)).first() if crew_id else db.query(Volunteer).filter(Volunteer.mobile_number == mobile).first()
    if not vol:
        raise HTTPException(status_code=404, detail="User account not found.")
    vol.is_active = False
    deleted_sessions = db.query(VolunteerSession).filter(VolunteerSession.volunteer_id == vol.id).delete()
    db.commit()
    return {"status": "TERMINATED", "crew_id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number, "revoked_sessions": deleted_sessions}


@router.post("/admin-reactivate-user")
def admin_reactivate_user(data: dict, db: Session = Depends(get_db)):
    crew_id = data.get("crew_id")
    vol = db.query(Volunteer).filter(Volunteer.id == int(crew_id)).first()
    if not vol:
        raise HTTPException(status_code=404, detail="User account not found.")
    vol.is_active = True
    db.commit()
    return {"status": "REACTIVATED", "crew_id": vol.id, "full_name": vol.full_name}


@router.post("/control-room-login")
def control_room_admin_login(data: dict, request: Request, db: Session = Depends(get_db)):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").lower().split(":")[0]
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
            geofence_verified=True,
        )
        db.add(vol)
        db.commit()
        db.refresh(vol)

    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(hours=12)))
    db.commit()

    return {
        "status": "AUTHORIZED",
        "session_token": raw_tok,
        "member": {
            "id": vol.id,
            "full_name": vol.full_name,
            "mobile_number": vol.mobile_number,
            "system_role": vol.system_role,
        },
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
            geofence_verified=True,
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


def _determine_role_and_permissions(duty_location: str) -> dict:
    loc_lower = duty_location.lower()
    if "ground" in loc_lower or "control" in loc_lower or "venue" in loc_lower:
        return dict(system_role="GROUND_ADMIN", can_view_all_territories=True, can_execute_ground_tasks=True, can_execute_station_tasks=True, can_manage_fleet=True)
    return dict(system_role="STATION_COORDINATOR", can_view_all_territories=False, can_execute_ground_tasks=False, can_execute_station_tasks=True, can_manage_fleet=False)


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
        **perms,
    )
    db.add(vol)
    db.commit()
    db.refresh(vol)

    token = secrets.token_hex(32)
    db.add(VolunteerSession(session_token=token, volunteer_id=vol.id, device_fingerprint=req.device_fingerprint, latitude=req.latitude, longitude=req.longitude, expires_at=datetime.utcnow() + timedelta(hours=24)))
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
            "can_manage_fleet": vol.can_manage_fleet,
        },
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
    db.add(VolunteerSession(session_token=token, volunteer_id=vol.id, device_fingerprint=req.device_fingerprint, latitude=req.latitude, longitude=req.longitude, expires_at=datetime.utcnow() + timedelta(hours=24)))
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
            "can_manage_fleet": vol.can_manage_fleet,
        },
    }

from pydantic import BaseModel as _HLBaseModel
import re as _hl_re_mod

class _HelplineLoginReq(_HLBaseModel):
    full_name: str = ""
    mobile: str
    pin: str

@router.post("/helpline-login")
async def helpline_login_endpoint(payload: _HelplineLoginReq):
    mobile_clean = _hl_re_mod.sub(r"\D", "", payload.mobile or "")[-10:]
    if len(mobile_clean) != 10:
        raise HTTPException(status_code=400, detail="Valid 10-digit mobile number is required.")
    pin_clean = (payload.pin or "").strip()
    if pin_clean == "6060" or (len(pin_clean) == 4 and pin_clean.isdigit()):
        return {"status": "authenticated", "role": "HELPLINE_OPERATOR", "full_name": (payload.full_name or "").strip() or f"Helpline Desk ({mobile_clean})", "mobile": mobile_clean, "helpline_tollfree": "18001232005", "chatbot_whatsapp": "9266629848", "access_token": f"hl-{mobile_clean}-60mnss"}
    raise HTTPException(status_code=401, detail="Invalid PIN. Use Helpline Desk Code 6060 or your 4-digit PIN.")
