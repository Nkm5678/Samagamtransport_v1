"""
UNIFIED REPOSITORY RECONCILIATION SCRIPT FOR SAMAGAM TRANSPORT V1
==================================================================
Safely reconciles differences between earlier patches and the latest Helpline,
date-wise roster, Ground Office & Committee/Station connect, and Excel bulk
upload updates without clobbering existing routes or duplicating blocks.
"""
import os
import re
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def read_text(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def write_text(p, s):
    parent = os.path.dirname(p)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def audit_and_reconcile():
    print("--- 1. Auditing Repository Files ---")
    for rel in ["app/main.py", "app/routers/auth.py", "app/routers/operations.py", "admin_dashboard.html", "welcome.html", "helpline_portal.html"]:
        fp = os.path.join(BASE_DIR, rel)
        print(f"  {rel:30s} : exists={os.path.exists(fp)}")

    # Sync helpline_portal.html to ./root/ if present
    hl_path = os.path.join(BASE_DIR, "helpline_portal.html")
    if os.path.exists(hl_path):
        hl_html = read_text(hl_path)
        root_hl = os.path.join(BASE_DIR, "root", "helpline_portal.html")
        if os.path.isdir(os.path.join(BASE_DIR, "root")):
            write_text(root_hl, hl_html)
            print("  Synced helpline_portal.html -> root/helpline_portal.html")

    # Reconcile app/main.py (helpline subdomain + /helpline route)
    main_path = os.path.join(BASE_DIR, "app", "main.py")
    if os.path.exists(main_path):
        msrc = read_text(main_path)
        if "helpline_portal.html" not in msrc:
            route_fn = '\n@app.get("/helpline")\nasync def serve_helpline_portal(request: Request):\n    for cand in [os.path.join(BASE_DIR, "helpline_portal.html"), os.path.join(BASE_DIR, "root", "helpline_portal.html")]:\n        if os.path.exists(cand):\n            return FileResponse(cand, media_type="text/html")\n    return JSONResponse({"status": "ok", "portal": "https://helpline.samagamtransport.in"})\n'
            host_fn = '\n    if "helpline." in host:\n        for cand in [os.path.join(BASE_DIR, "helpline_portal.html"), os.path.join(BASE_DIR, "root", "helpline_portal.html")]:\n            if os.path.exists(cand):\n                return FileResponse(cand, media_type="text/html")\n'
            msrc = msrc.replace('@app.middleware("http")', route_fn + '\n@app.middleware("http")', 1) if '@app.middleware("http")' in msrc else msrc + route_fn
            for h_pat in ['host = (request.headers.get("host") or "").lower()', 'host = request.headers.get("host", "").lower()']:
                if h_pat in msrc and 'if "helpline." in host:' not in msrc:
                    msrc = msrc.replace(h_pat, h_pat + host_fn, 1)
                    break
            write_text(main_path, msrc)
            print("  Added helpline.samagamtransport.in & /helpline route to app/main.py")
        else:
            print("  app/main.py already has helpline routing")

    # Reconcile app/routers/auth.py (/helpline-login)
    auth_path = os.path.join(BASE_DIR, "app", "routers", "auth.py")
    if os.path.exists(auth_path):
        asrc = read_text(auth_path)
        if "/helpline-login" not in asrc:
            auth_ext = '\n\nfrom pydantic import BaseModel as _HLBaseModel\nimport re as _hl_re_mod\n\nclass _HelplineLoginReq(_HLBaseModel):\n    full_name: str = ""\n    mobile: str\n    pin: str\n\n@router.post("/helpline-login")\nasync def helpline_login_endpoint(payload: _HelplineLoginReq):\n    mobile_clean = _hl_re_mod.sub(r"\\D", "", payload.mobile or "")[-10:]\n    if len(mobile_clean) != 10:\n        raise HTTPException(status_code=400, detail="Valid 10-digit mobile number is required.")\n    pin_clean = (payload.pin or "").strip()\n    if pin_clean == "6060" or (len(pin_clean) == 4 and pin_clean.isdigit()):\n        return {"status": "authenticated", "role": "HELPLINE_OPERATOR", "full_name": (payload.full_name or "").strip() or f"Helpline Desk ({mobile_clean})", "mobile": mobile_clean, "helpline_tollfree": "18001232005", "chatbot_whatsapp": "9266629848", "access_token": f"hl-{mobile_clean}-60mnss"}\n    raise HTTPException(status_code=401, detail="Invalid PIN. Use Helpline Desk Code 6060 or your 4-digit PIN.")\n'
            write_text(auth_path, asrc + auth_ext)
            print("  Added /helpline-login endpoint to app/routers/auth.py")
        else:
            print("  app/routers/auth.py already has /helpline-login")

    # Reconcile app/routers/operations.py (/roster/upload-excel, /roster/live, /fleet/upload-excel)
    ops_path = os.path.join(BASE_DIR, "app", "routers", "operations.py")
    if os.path.exists(ops_path):
        osrc = read_text(ops_path)
        if "/roster/upload-excel" not in osrc:
            ops_ext_lines = [
                "",
                "# --- Reconciled Helpline Roster & Fleet/Driver Excel Endpoints ---",
                "import io as _io_mod",
                "import re as _re_mod",
                "from datetime import datetime as _dt_mod",
                "from typing import Optional as _Opt",
                "import openpyxl as _openpyxl",
                "from fastapi import UploadFile as _UploadFile, File as _File",
                "from sqlalchemy import text as _sql_text",
                "",
                "def _ensure_reconciled_tables(db):",
                "    db.execute(_sql_text('CREATE TABLE IF NOT EXISTS samagam_duty_roster (id INTEGER PRIMARY KEY AUTOINCREMENT, team_category VARCHAR(40) NOT NULL, duty_date VARCHAR(20), location_name VARCHAR(160) NOT NULL, shift_timing VARCHAR(80) NOT NULL, slot_label VARCHAR(40), sewadar_name VARCHAR(120) NOT NULL, primary_mobile VARCHAR(20) NOT NULL, alt_mobile VARCHAR(20), unit_no VARCHAR(60), duty_role VARCHAR(160), updated_at VARCHAR(40))'))",
                "    db.execute(_sql_text('CREATE TABLE IF NOT EXISTS samagam_fleet_vehicles (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_reg VARCHAR(30) UNIQUE NOT NULL, vehicle_category VARCHAR(80) NOT NULL, make_model VARCHAR(80), capacity VARCHAR(40), ownership_source VARCHAR(40), owner_name VARCHAR(120), owner_mobile VARCHAR(20), staged_hub VARCHAR(140), driver_name VARCHAR(120), driver_mobile VARCHAR(20), available_from VARCHAR(20), available_till VARCHAR(20), status VARCHAR(30) DEFAULT \"READY\", updated_at VARCHAR(40))'))",
                "    db.execute(_sql_text('CREATE TABLE IF NOT EXISTS samagam_driver_roster (id INTEGER PRIMARY KEY AUTOINCREMENT, driver_name VARCHAR(120) NOT NULL, primary_mobile VARCHAR(20) UNIQUE NOT NULL, alt_mobile VARCHAR(20), login_pin VARCHAR(10) NOT NULL, license_no VARCHAR(50), license_type VARCHAR(60), assigned_vehicle_reg VARCHAR(30), base_hub VARCHAR(140), duty_shift VARCHAR(80), unit_agency VARCHAR(120), updated_at VARCHAR(40))'))",
                "    db.commit()",
                "",
                "@router.post(\"/roster/upload-excel\")",
                "async def upload_station_ground_roster_excel(file: _UploadFile = _File(...), db=Depends(get_db)):",
                "    if not file.filename.lower().endswith((\"xlsx\", \"xlsm\")):",
                "        raise HTTPException(status_code=400, detail=\"Please upload the .xlsx Roster Proforma file.\")",
                "    _ensure_reconciled_tables(db)",
                "    wb = _openpyxl.load_workbook(_io_mod.BytesIO(await file.read()), data_only=True)",
                "    inserted = 0",
                "    now_iso = _dt_mod.utcnow().isoformat()",
                "    for sname in wb.sheetnames:",
                "        if \"summary\" in sname.lower():",
                "            continue",
                "        ws = wb[sname]",
                "        default_team = \"GROUND_TEAM\" if \"ground\" in sname.lower() else \"STATION_TEAM\"",
                "        for r in range(5, ws.max_row + 1):",
                "            tcat = str(ws.cell(r, 2).value or default_team).strip().upper()",
                "            tcat = \"GROUND_TEAM\" if \"GROUND\" in tcat else \"STATION_TEAM\"",
                "            ddate = str(ws.cell(r, 3).value or \"\").strip()[:10]",
                "            loc = str(ws.cell(r, 4).value or \"\").strip()",
                "            shift = str(ws.cell(r, 5).value or \"\").strip()",
                "            slot = str(ws.cell(r, 6).value or \"\").strip()",
                "            name = str(ws.cell(r, 7).value or \"\").strip()",
                "            mob = _re_mod.sub(r\"\\\\D\", \"\", str(ws.cell(r, 8).value or \"\"))[-10:]",
                "            alt = _re_mod.sub(r\"\\\\D\", \"\", str(ws.cell(r, 9).value or \"\"))[-10:]",
                "            unit = str(ws.cell(r, 10).value or \"\").strip()",
                "            role = str(ws.cell(r, 11).value or \"\").strip()",
                "            if not name or len(mob) < 10 or not loc:",
                "                continue",
                "            db.execute(_sql_text(\"INSERT INTO samagam_duty_roster (team_category, duty_date, location_name, shift_timing, slot_label, sewadar_name, primary_mobile, alt_mobile, unit_no, duty_role, updated_at) VALUES (:tc, :dd, :loc, :sh, :sl, :nm, :pm, :am, :un, :rl, :ua)\"), {\"tc\": tcat, \"dd\": ddate, \"loc\": loc, \"sh\": shift, \"sl\": slot, \"nm\": name, \"pm\": mob, \"am\": alt, \"un\": unit, \"rl\": role, \"ua\": now_iso})",
                "            inserted += 1",
                "    db.commit()",
                "    return {\"status\": \"success\", \"records_uploaded\": inserted, \"message\": f\"Uploaded {inserted} active roster contacts.\"}",
                "",
                "@router.get(\"/roster/live\")",
                "def get_live_helpline_roster(duty_date: _Opt[str] = None, team_category: _Opt[str] = None, db=Depends(get_db)):",
                "    _ensure_reconciled_tables(db)",
                "    q = \"SELECT * FROM samagam_duty_roster WHERE 1=1\"",
                "    params = {}",
                "    if duty_date:",
                "        q += \" AND duty_date = :dd\"",
                "        params[\"dd\"] = duty_date",
                "    if team_category and team_category != \"ALL\":",
                "        q += \" AND team_category = :tc\"",
                "        params[\"tc\"] = team_category",
                "    q += \" ORDER BY duty_date ASC, team_category ASC, location_name ASC, shift_timing ASC, id ASC\"",
                "    rows = db.execute(_sql_text(q), params).mappings().all()",
                "    return {\"items\": [dict(r) for r in rows], \"total\": len(rows)}",
                "",
                "@router.post(\"/fleet/upload-excel\")",
                "async def upload_fleet_vehicles_and_drivers_excel(file: _UploadFile = _File(...), db=Depends(get_db)):",
                "    if not file.filename.lower().endswith((\"xlsx\", \"xlsm\")):",
                "        raise HTTPException(status_code=400, detail=\"Please upload the .xlsx Fleet & Drivers Proforma file.\")",
                "    _ensure_reconciled_tables(db)",
                "    wb = _openpyxl.load_workbook(_io_mod.BytesIO(await file.read()), data_only=True)",
                "    v_cnt, d_cnt = 0, 0",
                "    now_iso = _dt_mod.utcnow().isoformat()",
                "    if \"Fleet_Vehicles_Master\" in wb.sheetnames:",
                "        ws_v = wb[\"Fleet_Vehicles_Master\"]",
                "        for r in range(5, ws_v.max_row + 1):",
                "            reg = _re_mod.sub(r\"\\\\s+\", \"\", str(ws_v.cell(r, 2).value or \"\")).upper()",
                "            v_cat = str(ws_v.cell(r, 3).value or \"\").strip()",
                "            if not reg or not v_cat:",
                "                continue",
                "            db.execute(_sql_text(\"DELETE FROM samagam_fleet_vehicles WHERE vehicle_reg = :reg\"), {\"reg\": reg})",
                "            db.execute(_sql_text(\"INSERT INTO samagam_fleet_vehicles (vehicle_reg, vehicle_category, make_model, capacity, ownership_source, owner_name, owner_mobile, staged_hub, driver_name, driver_mobile, available_from, available_till, status, updated_at) VALUES (:reg, :cat, :mm, :cap, :src, :onm, :omob, :hub, :dnm, :dmob, :af, :at, \'READY\', :ua)\"), {\"reg\": reg, \"cat\": v_cat, \"mm\": str(ws_v.cell(r, 4).value or \"\").strip(), \"cap\": str(ws_v.cell(r, 5).value or \"\").strip(), \"src\": str(ws_v.cell(r, 6).value or \"SEWA_DONATED\").strip().upper(), \"onm\": str(ws_v.cell(r, 7).value or \"\").strip(), \"omob\": _re_mod.sub(r\"\\\\D\", \"\", str(ws_v.cell(r, 8).value or \"\"))[-10:], \"hub\": str(ws_v.cell(r, 9).value or \"\").strip(), \"dnm\": str(ws_v.cell(r, 10).value or \"\").strip(), \"dmob\": _re_mod.sub(r\"\\\\D\", \"\", str(ws_v.cell(r, 11).value or \"\"))[-10:], \"af\": str(ws_v.cell(r, 12).value or \"\").strip()[:10], \"at\": str(ws_v.cell(r, 13).value or \"\").strip()[:10], \"ua\": now_iso})",
                "            v_cnt += 1",
                "    if \"Driver_Roster_Master\" in wb.sheetnames:",
                "        ws_d = wb[\"Driver_Roster_Master\"]",
                "        for r in range(5, ws_d.max_row + 1):",
                "            d_name = str(ws_d.cell(r, 2).value or \"\").strip()",
                "            p_mob = _re_mod.sub(r\"\\\\D\", \"\", str(ws_d.cell(r, 3).value or \"\"))[-10:]",
                "            if not d_name or len(p_mob) < 10:",
                "                continue",
                "            a_mob = _re_mod.sub(r\"\\\\D\", \"\", str(ws_d.cell(r, 4).value or \"\"))[-10:]",
                "            pin_raw = _re_mod.sub(r\"\\\\D\", \"\", str(ws_d.cell(r, 5).value or \"\"))",
                "            pin = pin_raw[:4] if len(pin_raw) >= 4 else p_mob[-4:]",
                "            veh_reg = _re_mod.sub(r\"\\\\s+\", \"\", str(ws_d.cell(r, 8).value or \"\")).upper()",
                "            db.execute(_sql_text(\"DELETE FROM samagam_driver_roster WHERE primary_mobile = :pm\"), {\"pm\": p_mob})",
                "            db.execute(_sql_text(\"INSERT INTO samagam_driver_roster (driver_name, primary_mobile, alt_mobile, login_pin, license_no, license_type, assigned_vehicle_reg, base_hub, duty_shift, unit_agency, updated_at) VALUES (:dn, :pm, :am, :pin, :ln, :lt, :vr, :bh, :sh, :ua, :up)\"), {\"dn\": d_name, \"pm\": p_mob, \"am\": a_mob, \"pin\": pin, \"ln\": str(ws_d.cell(r, 6).value or \"\").strip().upper(), \"lt\": str(ws_d.cell(r, 7).value or \"\").strip(), \"vr\": veh_reg, \"bh\": str(ws_d.cell(r, 9).value or \"\").strip(), \"sh\": str(ws_d.cell(r, 10).value or \"\").strip(), \"ua\": str(ws_d.cell(r, 11).value or \"\").strip(), \"up\": now_iso})",
                "            if veh_reg:",
                "                db.execute(_sql_text(\"UPDATE samagam_fleet_vehicles SET driver_name = :dn, driver_mobile = :pm, updated_at = :up WHERE vehicle_reg = :vr\"), {\"dn\": d_name, \"pm\": p_mob, \"up\": now_iso, \"vr\": veh_reg})",
                "            d_cnt += 1",
                "    db.commit()",
                "    return {\"status\": \"success\", \"vehicles_uploaded\": v_cnt, \"drivers_uploaded\": d_cnt, \"message\": f\"Uploaded {v_cnt} vehicles and {d_cnt} drivers.\"}",
                "",
            ]
            write_text(ops_path, osrc + "\n".join(ops_ext_lines))
            print("  Added Excel Roster & Fleet/Driver upload endpoints to app/routers/operations.py")
        else:
            print("  app/routers/operations.py already has Excel upload endpoints")

if __name__ == "__main__":
    audit_and_reconcile()
    print("Reconciliation complete.")
