# ... existing code ...
     open_shift = db.query(CrewDutyShift).filter(CrewDutyShift.crew_phone == vol.mobile_number, CrewDutyShift.is_currently_on_duty == True).first()
        if open_shift:
            raise HTTPException(status_code=409, detail="You are still ON DUTY. Tap 'End Duty Shift' before logging out.")
        db.delete(sess)
        db.commit()
    return {"ok": True}

ADMIN_ACCESS_CODE = os.environ.get("ADMIN_ACCESS_CODE", "SAMAGAM-HQ-2026").strip()

@router.post("/control-room-login")
def control_room_admin_login(data: dict, db: Session = Depends(get_db)):
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
            volunteer_code=f"HQ-{secrets.randbelow(9000)+1000}",
            full_name=str(data.get("member_name") or f"Control Room Member ({mobile[-4:]})").strip(),
            mobile_number=mobile, unit_number="HQ-Command", branch_name="Samagam Transport HQ",
            duty_location="Ground 1 (Main Hall)", system_role="GROUND_ADMIN",
            can_view_all_territories=True, can_execute_ground_tasks=True, can_execute_station_tasks=True,
            can_manage_fleet=True, geofence_verified=True
        )
        db.add(vol)
        db.commit()
        db.refresh(vol)
    raw_tok = secrets.token_urlsafe(32)
    db.add(VolunteerSession(session_token=_tok_hash(raw_tok), volunteer_id=vol.id, expires_at=datetime.utcnow() + timedelta(hours=12)))
    db.commit()
    return {"status": "AUTHORIZED", "session_token": raw_tok, "member": {"id": vol.id, "full_name": vol.full_name, "mobile_number": vol.mobile_number, "system_role": vol.system_role}}

@router.get("/crew")
def list_registered_crew(db: Session = Depends(get_db)):
# ... existing code ...
            <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
                <a href="/download_hub.html" class="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 transition">📲 <span data-i18n="nav_apps">Field Apps (.APK)</span></a>
            </div>
        </div>
    </header>
# ... existing code ...
        "nav_apps": "Field Apps (.APK)",
        "hero_desc": "Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database.",
# ... existing code ...
        "nav_apps": "फील्ड ऐप्स (.APK)",
        "hero_desc": "नीचे अपनी परिवहन आवश्यकता चुनें। सभी वाहन अनुरोध सीधे मुख्य डेटाबेस से जुड़े हैं।",
# ... existing code ...
        "nav_apps": "फील्ड ॲप्स (.APK)",
        "hero_desc": "खालीलपैकी आपली वाहन आवश्यकता निवडा. सर्व वाहन विनंत्या थेट मुख्य डेटाबेसशी जोडलेल्या आहेत.",
# ... existing code ...