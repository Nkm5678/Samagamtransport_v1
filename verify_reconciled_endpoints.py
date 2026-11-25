"""
LOCAL VERIFICATION SCRIPT FOR RECONCILED SAMAGAM TRANSPORT ENDPOINTS & PORTALS
==============================================================================
Runs static checks on `app/main.py`, `app/routers/auth.py`, `app/routers/operations.py`,
`helpline_portal.html`, `root/helpline_portal.html`, and `admin_dashboard.html`, and
optionally exercises FastAPI routes in-process using `fastapi.testclient.TestClient`.

Usage (in PowerShell inside C:\narendra\SamagamtransportV1):
    python .\verify_reconciled_endpoints.py
"""
import io
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def read_text(rel_path):
    fp = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(fp):
        return None
    with open(fp, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def run_static_checks():
    print("=== 1. Static Code & Portal Checks ===")
    checks = [
        ("app/main.py", ["helpline_portal.html", "/helpline"]),
        ("app/routers/auth.py", ["/helpline-login"]),
        ("app/routers/operations.py", ["/roster/upload-excel", "/roster/live", "/fleet/upload-excel"]),
        ("helpline_portal.html", ["18001232005", "9266629848", "helpline.samagamtransport.in"]),
        ("admin_dashboard.html", ["uploadRosterExcelAdmin", "uploadFleetExcelAdmin"]),
    ]
    all_ok = True
    for rel, needles in checks:
        content = read_text(rel)
        if content is None:
            print(f"  [MISS] {rel} not found")
            all_ok = False
            continue
        missing = [n for n in needles if n not in content]
        if missing:
            print(f"  [WARN] {rel} missing expected tokens: {missing}")
            all_ok = False
        else:
            print(f"  [PASS] {rel} contains {needles}")

    root_hl = os.path.join(BASE_DIR, "root", "helpline_portal.html")
    print(f"  [INFO] root/helpline_portal.html exists={os.path.exists(root_hl)}")
    return all_ok

def run_fastapi_checks():
    print("\n=== 2. FastAPI TestClient Endpoint Checks ===")
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except Exception as exc:
        print(f"  [SKIP] Could not import FastAPI app/TestClient: {exc}")
        return

    client = TestClient(app)

    # A. Helpline & portal routes
    r_hl = client.get("/helpline")
    print(f"  GET /helpline -> status={r_hl.status_code}")

    r_sub = client.get("/", headers={"Host": "helpline.samagamtransport.in"})
    print(f"  GET / (Host: helpline.samagamtransport.in) -> status={r_sub.status_code}")

    # B. Helpline login check (valid PIN 6060 vs invalid PIN)
    r_login_ok = client.post("/api/auth/helpline-login", json={"full_name": "Desk 1", "mobile": "9820110099", "pin": "6060"})
    print(f"  POST /api/auth/helpline-login (valid PIN 6060) -> status={r_login_ok.status_code} | body={r_login_ok.text[:140]}")

    r_login_bad = client.post("/api/auth/helpline-login", json={"full_name": "Desk 1", "mobile": "9820110099", "pin": "0000"})
    print(f"  POST /api/auth/helpline-login (invalid PIN 0000) -> status={r_login_bad.status_code}")

    # C. Live roster endpoint
    r_roster = client.get("/api/operations/roster/live")
    print(f"  GET /api/operations/roster/live -> status={r_roster.status_code} | body={r_roster.text[:160]}")

    # D. Excel upload endpoints (if openpyxl is available)
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Station_Team_Roster"
        ws.append(["Sr. No.", "Team Category", "Duty Date (YYYY-MM-DD)", "Location / Hub Name", "Shift Timing", "Slot # (Min 1-4)", "Sewadar Full Name", "Primary Contact No. (10-Digit)", "Alternative Contact No.", "Unit No. / Khetra", "Duty Role & Pickup Point"])
        ws.append([1, "STATION_TEAM", "2027-01-23", "Panvel Junction (PNVL)", "Morning Shift (06:00 - 14:00)", "Person 1 of 4", "Test Sewadar", "9820110011", "9820110012", "Unit 101", "Station Team Lead"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        r_up = client.post("/api/operations/roster/upload-excel", files={"file": ("test_roster.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        print(f"  POST /api/operations/roster/upload-excel -> status={r_up.status_code} | body={r_up.text[:160]}")
    except ImportError:
        print("  [SKIP] openpyxl not installed; skipping in-memory .xlsx upload test")
    except Exception as exc:
        print(f"  [ERR] Excel upload check failed: {exc}")

if __name__ == "__main__":
    ok = run_static_checks()
    run_fastapi_checks()
    print("\nVerification run complete. Exit status:", 0 if ok else 1)
