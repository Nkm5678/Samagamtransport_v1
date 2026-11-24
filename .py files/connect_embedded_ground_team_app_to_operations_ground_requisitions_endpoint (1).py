import os
import sys
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from sqlalchemy import create_engine, inspect, text
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.seed_service import seed_initial_operations_data
from app.routers import auth, saints, fleet, operations, reports

_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
AUTH_LIMIT_PER_MIN = 60
GENERAL_LIMIT_PER_MIN = 300


def _collect_migration_engines():
    targets = [engine]
    seen_urls = {str(engine.url)}
    candidate_urls = [
        getattr(settings, "DATABASE_URL", ""),
        os.environ.get("DATABASE_URL", ""),
    ]
    for raw_url in candidate_urls:
        url_str = str(raw_url or "").strip()
        if not url_str:
            continue
        if url_str.startswith("sqlite:///") and not url_str.startswith("sqlite:////"):
            rel_path = url_str.replace("sqlite:///", "", 1)
            if not os.path.isabs(rel_path):
                for base_dir in [ROOT_DIR, os.getcwd()]:
                    abs_db = os.path.abspath(os.path.join(base_dir, rel_path))
                    if os.path.exists(abs_db):
                        file_url = f"sqlite:///{abs_db.replace(os.sep, '/')}"
                        if file_url not in seen_urls:
                            seen_urls.add(file_url)
                            targets.append(create_engine(file_url, connect_args={"check_same_thread": False}))
        elif url_str.startswith("sqlite") and url_str not in seen_urls:
            seen_urls.add(url_str)
            targets.append(create_engine(url_str, connect_args={"check_same_thread": False}))
    return targets


def _ensure_missing_columns():
    for target_engine in _collect_migration_engines():
        try:
            inspector = inspect(target_engine)
            table_names = set(inspector.get_table_names())
            migrations: list[tuple[str, str, str]] = []

            if "vehicles" in table_names:
                existing_cols = {c["name"] for c in inspector.get_columns("vehicles")}
                if "onboarding_team" not in existing_cols:
                    migrations.append(("vehicles", "onboarding_team", "VARCHAR(60) DEFAULT 'Control Room'"))
                if "registered_by" not in existing_cols:
                    migrations.append(("vehicles", "registered_by", "VARCHAR(120)"))

            if "devotee_parking_passes" in table_names:
                existing_cols = {c["name"] for c in inspector.get_columns("devotee_parking_passes")}
                if "owner_email" not in existing_cols:
                    migrations.append(("devotee_parking_passes", "owner_email", "VARCHAR(120)"))
                if "branch_name" not in existing_cols:
                    migrations.append(("devotee_parking_passes", "branch_name", "VARCHAR(120)"))
                if "zone_name" not in existing_cols:
                    migrations.append(("devotee_parking_passes", "zone_name", "VARCHAR(120)"))

            if migrations:
                with target_engine.begin() as conn:
                    for tbl, col, col_type in migrations:
                        conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}"))
        except Exception as exc:
            print(f"⚠️ Column auto-migration notice ({target_engine.url}): {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_missing_columns()
    db = SessionLocal()
    try:
        seed_initial_operations_data(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def ddos_rate_limit_and_security_headers(request: Request, call_next):
    path = request.url.path
    if path != "/health" and not path.startswith("/static/"):
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        is_auth_route = path.startswith("/api/auth/")
        bucket_key = f"{client_ip}:{'auth' if is_auth_route else 'gen'}"
        limit = AUTH_LIMIT_PER_MIN if is_auth_route else GENERAL_LIMIT_PER_MIN

        now = time.time()
        window = _RATE_BUCKETS[bucket_key]
        while window and window[0] < now - 60.0:
            window.popleft()

        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests from this IP. Please wait 60 seconds before retrying."}
            )
        window.append(now)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(auth.router)
app.include_router(saints.router)
app.include_router(fleet.router)
app.include_router(operations.router)
app.include_router(reports.router)

static_dir = os.path.join(ROOT_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

EMBEDDED_FIELD_PORTALS = {
    "station_team_app.html": ("STATION TEAM FIELD APP", "Platform Crowd, MSRTC Cash & 6-Stage Sequence", "rose", "Station Team"),
    "ground_team_app.html": ("GROUND TEAM FIELD APP", "Central Park Dispatch, Dept Requisitions & Allocation", "sky", "Ground Team"),
    "gate_keeper_app.html": ("GATE KEEPER MARSHALL APP", "Inward/Outward Turnaround & 24h Odometer", "teal", "Gate Keeper"),
    "diesel_team_app.html": ("DIESEL & FUEL TEAM APP", "Fuel Fill-Up Slips & Safety Audits", "amber", "Diesel Marshall"),
    "accounts_team_app.html": ("ACCOUNTS & TREASURY APP", "Petty Cash Floats, MSRTC & 24h Billing", "blue", "Accounts Auditor"),
    "driver_rider_companion.html": ("SAMAGAM DRIVER & RIDER APP", "Live 180s GPS Trip & Shuttle Status", "emerald", "Driver Crew"),
}


def _render_embedded_field_html(filename: str) -> str:
    title, subtitle, color, actor = EMBEDDED_FIELD_PORTALS.get(
        filename, ("SAMAGAM FIELD PORTAL", "Connected to Central Transport Database", "emerald", "Field Sevadar")
    )
    is_ground_team = filename == "ground_team_app.html"
    ground_queue_html = """
        <section class="bg-slate-900 border border-teal-700/60 rounded-2xl p-4 space-y-3 text-xs">
            <div class="flex justify-between items-center">
                <div class="font-extrabold text-teal-300">🚛 Live Ground Department Vehicle Requests (Allocate Vehicle)</div>
                <button onclick="loadGroundDeptRequisitions()" class="bg-slate-800 px-2.5 py-1 rounded-lg text-emerald-300 font-bold">↻ Refresh</button>
            </div>
            <div id="ground-dept-req-list" class="space-y-2 text-slate-200">Loading ground requests...</div>
        </section>
        <section class="bg-slate-900 border border-emerald-700/60 rounded-2xl p-4 space-y-3 text-xs">
            <div class="font-extrabold text-emerald-300">🚉 Live Station / Airport Pickup & Drop Requests</div>
            <div id="ground-pd-req-list" class="space-y-2 text-slate-200">Loading pickup/drop requests...</div>
        </section>
    """ if is_ground_team else ""

    ground_script_html = """
        async function loadGroundDeptRequisitions() {
            const [dRes, vRes, pdRes] = await Promise.all([
                fetch("/api/operations/ground-dept-requisitions"),
                fetch("/api/fleet/vehicles"),
                fetch("/api/operations/pickup-drop-requests")
            ]);
            const reqs = dRes.ok ? await dRes.json() : [];
            const vehicles = vRes.ok ? await vRes.json() : [];
            const pds = pdRes.ok ? await pdRes.json() : [];
            const vOpts = vehicles.map(v => `<option value="${v.vehicle_reg_number}">${v.vehicle_reg_number} (${v.vehicle_type})</option>`).join("");

            const box = document.getElementById("ground-dept-req-list");
            if (box) {
                box.innerHTML = reqs.length ? reqs.map(r => `
                    <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <div class="flex justify-between">
                            <strong class="text-white">${r.requisition_code} • ${r.department_name}</strong>
                            <span class="px-2 py-0.5 rounded bg-teal-950 text-teal-300 font-bold">${r.status}</span>
                        </div>
                        <div class="text-slate-300">${r.quantity_needed}x ${r.required_vehicle_type} • ${r.purpose}</div>
                        <div class="text-slate-400">By: ${r.requester_name} (${r.requester_phone})</div>
                        <div class="flex gap-2 pt-1">
                            <select id="alloc-veh-${r.id}" class="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-white font-bold">${vOpts}</select>
                            <button onclick="allocateVehicleToDeptReq(${r.id})" class="bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold px-3 py-1 rounded-lg">Allocate Vehicle</button>
                        </div>
                    </div>
                `).join("") : '<div class="text-slate-500">No ground department requests yet.</div>';
            }
            const pdBox = document.getElementById("ground-pd-req-list");
            if (pdBox) {
                pdBox.innerHTML = pds.length ? pds.slice(0, 15).map(p => `
                    <div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex justify-between">
                        <span><strong>${p.request_code}</strong> • ${p.transit_hub} (${p.passenger_count} Saints) • ${p.requester_name} (${p.requester_phone})</span>
                        <span class="text-emerald-400 font-bold">${p.assigned_vehicle_reg || p.status}</span>
                    </div>
                `).join("") : '<div class="text-slate-500">No pickup/drop requests logged yet.</div>';
            }
        }
        async function allocateVehicleToDeptReq(reqId) {
            const reg = document.getElementById(`alloc-veh-${reqId}`).value;
            const res = await fetch(`/api/operations/ground-dept-requisitions/${reqId}/allocate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ vehicle_reg_number: reg })
            });
            if (res.ok) {
                loadGroundDeptRequisitions();
            }
        }
        window.addEventListener("DOMContentLoaded", loadGroundDeptRequisitions);
    """ if is_ground_team else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Samagam Transport</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
    <header class="bg-{color}-950 border-b border-{color}-800 px-4 py-3.5 sticky top-0 z-40 shadow-lg">
        <div class="max-w-5xl mx-auto flex items-center justify-between gap-2">
            <div>
                <h1 class="font-extrabold text-sm sm:text-base text-white">{title}</h1>
                <p class="text-[11px] text-{color}-300">{subtitle}</p>
            </div>
            <div class="flex items-center gap-2 text-xs font-bold">
                <a href="/bus_onboarding_form.html" class="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-xl">+ Onboard Bus</a>
                <a href="/" class="bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-xl">Home</a>
            </div>
        </div>
    </header>
    <main class="max-w-5xl mx-auto w-full p-4 space-y-4 flex-1">
        {ground_queue_html}
        <section id="samagam-live-pipeline-board"></section>
        <section class="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2 text-xs">
            <div class="font-extrabold text-amber-300">Active Hubs & Live Fleet</div>
            <div id="live-fleet-feed" class="space-y-1.5 text-slate-300">Loading live fleet & hubs...</div>
        </section>
    </main>
    <script src="/static/samagam_app_shell.js"></script>
    <script src="/static/operations_pipeline_board.js"></script>
    <script>
        {ground_script_html}
        window.addEventListener("DOMContentLoaded", async () => {{
            if (typeof renderOperationsPipelineWidget === "function") {{
                renderOperationsPipelineWidget("samagam-live-pipeline-board", "{actor}");
            }}
            try {{
                const vRes = await fetch("/api/fleet/vehicles");
                const vehicles = await vRes.json();
                document.getElementById("live-fleet-feed").innerHTML = vehicles.map(v =>
                    `<div class="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex justify-between items-center">
                        <div><strong class="text-white">${{v.vehicle_reg_number}}</strong> <span class="text-slate-400">(${{v.vehicle_type}})</span><div class="text-[11px] text-slate-400">${{v.current_hub}} • Driver: ${{v.driver_name}}</div></div>
                        <span class="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold">${{v.status}}</span>
                    </div>`
                ).join("");
            }} catch (_) {{}}
        }});
    </script>
</body>
</html>"""


def _serve_html(filename: str):
    for d in [ROOT_DIR, os.path.join(ROOT_DIR, "root"), os.getcwd(), os.path.join(os.getcwd(), "root")]:
        path = os.path.join(d, filename)
        if os.path.isfile(path):
            return FileResponse(path)
    if filename in EMBEDDED_FIELD_PORTALS:
        return HTMLResponse(content=_render_embedded_field_html(filename))
    return JSONResponse(status_code=404, content={"detail": f"{filename} not found in project root."})


@app.get("/")
def home(request: Request):
    candidates = [
        request.headers.get("x-forwarded-host", ""),
        request.headers.get("x-original-host", ""),
        request.headers.get("host", ""),
        str(request.url.hostname or ""),
    ]
    combined = " ".join(candidates).lower()

    if "admin.samagamtransport.in" in combined or any(c.strip().lower().startswith("admin.") for c in candidates if c):
        return _serve_html("admin_dashboard.html")
    if "ground.samagamtransport.in" in combined or any(c.strip().lower().startswith("ground.") for c in candidates if c):
        return _serve_html("in_ground_seva_vehicles.html")
    if "parking.samagamtransport.in" in combined or any(c.strip().lower().startswith("parking.") for c in candidates if c):
        return _serve_html("parking_portal.html")
    if "advancesewa.samagamtransport.in" in combined or any(c.strip().lower().startswith("advancesewa.") for c in candidates if c):
        return _serve_html("advance_sewa_portal.html")

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
def serve_html_page(page_name: str, request: Request):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").lower().split(":")[0]
    admin_pages = {"admin_dashboard", "admin_operations_dashboard", "admin_performance_dashboard"}
    if page_name in admin_pages and not (host == "admin.samagamtransport.in" or host.startswith("admin.")):
        return JSONResponse(
            status_code=403,
            content={"detail": "Control Room & Admin pages are restricted to https://admin.samagamtransport.in"}
        )
    return _serve_html(f"{page_name}.html")


@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)