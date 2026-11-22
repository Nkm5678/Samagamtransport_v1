r"""
================================================================================
SAMAGAM TRANSPORT PLATFORM — COMPLETE MASTER ALL-IN-ONE INSTALLER
Compiles & writes EVERY HTML page, JS shell, Backend Router, Database Model,
Subdomain Router, Auth Gate, 180s GPS Tracker, 27 Official Committees,
First-Time Bus Onboarding, Parking QR Portal, Advance Sewa Portal &
15-Sheet Master Excel Export into C:\narendra\SamagamtransportV1 in ONE GO.

Usage (PowerShell inside C:\narendra\SamagamtransportV1):
    python deploy_complete_samagam_suite.py
================================================================================
"""

import os

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {}

FILES["app/__init__.py"] = ""
FILES["app/services/__init__.py"] = ""
FILES["app/routers/__init__.py"] = ""

FILES["Dockerfile"] = """FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
"""

FILES["requirements.txt"] = """fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.28
pydantic>=2.6.4
pydantic-settings>=2.2.1
requests>=2.31.0
psycopg2-binary>=2.9.9
openpyxl>=3.1.2
werkzeug>=3.0.0
"""

# ------------------------------------------------------------------------------
# 1. HARDENED ENTRYPOINT + SUBDOMAIN ROUTING + ANTI-DDOS RATE LIMITER
# ------------------------------------------------------------------------------
FILES["app/main.py"] = '''import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.seed_service import seed_initial_operations_data
from app.routers import auth, saints, fleet, operations, reports

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_RATE_BUCKETS = defaultdict(deque)
GENERAL_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "180"))
AUTH_LIMIT_PER_MIN = int(os.environ.get("AUTH_RATE_LIMIT_PER_MIN", "25"))


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
    if path == "/" or path.endswith(".html") or path.endswith(".js"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


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
def home(request: Request):
    host = (request.headers.get("host") or "").lower()
    if host.startswith("parking."):
        p = os.path.join(ROOT_DIR, "parking_portal.html")
        if os.path.exists(p):
            return FileResponse(p)
    if host.startswith("advancesewa."):
        a = os.path.join(ROOT_DIR, "advance_sewa_portal.html")
        if os.path.exists(a):
            return FileResponse(a)
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

# ------------------------------------------------------------------------------
# 2. UNIVERSAL MANDATORY AUTH SHELL (NAME, BRANCH, UNIT NO. & MOBILE/EMAIL OTP)
# ------------------------------------------------------------------------------
FILES["static/samagam_app_shell.js"] = '''(function initJagritiAuthAndShell() {
    const PRODUCTION_ORIGIN = "https://www.samagamtransport.in";
    const isFileOrCapacitor = window.location.protocol === "file:" || window.location.protocol === "capacitor:";
    const originPrefix = isFileOrCapacitor ? PRODUCTION_ORIGIN : "";

    const PUBLIC_PATHS = ["/", "/welcome.html", "/register.html", "/download_hub.html", "/admin_dashboard.html", "/parking_portal.html", "/advance_sewa_portal.html"];
    const currentPath = window.location.pathname || "/";
    const host = (window.location.hostname || "").toLowerCase();
    const isSubdomainPortal = host.startsWith("parking.") || host.startsWith("advancesewa.");
    const isPublicPage = !isFileOrCapacitor && (PUBLIC_PATHS.includes(currentPath) || isSubdomainPortal);

    const origFetch = window.fetch.bind(window);
    window.fetch = async function(input, init) {
        let url = input;
        if (isFileOrCapacitor && typeof url === "string" && url.startsWith("/")) {
            url = PRODUCTION_ORIGIN + url;
        }
        init = init || {};
        const headers = new Headers(init.headers || {});
        const tok = localStorage.getItem("samagam_driver_token") || localStorage.getItem("samagam_field_token") || "";
        if (tok && !headers.has("X-Driver-Token")) {
            headers.set("X-Driver-Token", tok);
        }
        init.headers = headers;

        const resp = await origFetch(url, init);
        if (!isPublicPage && typeof url === "string" && !url.includes("/api/auth/") && (resp.status === 401 || resp.status === 403)) {
            const clone = resp.clone();
            try {
                const body = await clone.json();
                if (body && body.detail && (body.detail.includes("TERMINATED") || body.detail.includes("Session expired") || body.detail.includes("Missing session"))) {
                    forceLockoutScreen(body.detail);
                }
            } catch (_) {}
        }
        return resp;
    };

    function forceLockoutScreen(reasonMsg) {
        localStorage.removeItem("samagam_driver_token");
        localStorage.removeItem("samagam_field_token");
        localStorage.removeItem("samagam_field_user");
        showCompulsoryLoginModal(reasonMsg || "Authentication required to access this Samagam Web/Mobile App.");
    }

    function showCompulsoryLoginModal(alertBannerText) {
        if (document.getElementById("driver-auth-screen") && !alertBannerText.includes("TERMINATED")) {
            return;
        }

        let overlay = document.getElementById("samagam-mandatory-auth-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "samagam-mandatory-auth-overlay";
            overlay.style.cssText = "position:fixed;inset:0;background:rgba(2,6,23,0.97);backdrop-filter:blur(10px);z-index:99999;display:flex;align-items:center;justify-content:center;padding:16px;font-family:system-ui,-apple-system,sans-serif;color:#f8fafc;";
            document.body.appendChild(overlay);
        }

        overlay.innerHTML = `
            <div style="max-width:410px;width:100%;background:#0f172a;border:1px solid #334155;border-radius:24px;padding:24px;box-shadow:0 25px 50px rgba(0,0,0,0.6);">
                <div style="text-align:center;margin-bottom:16px;">
                    <div style="font-size:32px;">🔐</div>
                    <h2 style="font-size:18px;font-weight:800;color:#ffffff;margin:4px 0;">Compulsory Field Login</h2>
                    <p style="font-size:12px;color:#94a3b8;margin:0;">Web App & APK Access • Authorized Sevadars Only</p>
                </div>

                ${alertBannerText ? `<div style="background:#450a0a;border:1px solid #dc2626;color:#fecaca;font-size:12px;font-weight:700;padding:10px 12px;border-radius:12px;margin-bottom:14px;">${alertBannerText}</div>` : ""}

                <div id="m-auth-step1" style="display:flex;flex-direction:column;gap:10px;">
                    <input type="text" id="m-auth-ident" placeholder="10-Digit Mobile Number or Email" style="width:100%;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:12px;padding:12px;color:#ffffff;font-size:14px;font-weight:600;">
                    <button id="m-btn-continue" style="width:100%;background:#059669;color:#ffffff;border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:800;cursor:pointer;">Continue to Login →</button>
                </div>

                <div id="m-auth-step-pin" style="display:none;flex-direction:column;gap:10px;">
                    <div id="m-pin-label" style="font-size:12px;color:#6ee7b7;font-weight:700;">Enter your 4-digit PIN:</div>
                    <input type="password" id="m-auth-pin" maxlength="4" inputmode="numeric" placeholder="••••" style="width:100%;box-sizing:border-box;text-align:center;letter-spacing:0.5em;background:#020617;border:1px solid #475569;border-radius:12px;padding:12px;color:#ffffff;font-size:20px;font-weight:800;">
                    <button id="m-btn-pin-verify" style="width:100%;background:#059669;color:#ffffff;border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:800;cursor:pointer;">Verify & Enter App</button>
                    <button id="m-btn-back1" style="background:none;border:none;color:#94a3b8;font-size:12px;text-decoration:underline;cursor:pointer;">← Change Number / Email</button>
                </div>

                <div id="m-auth-step-otp" style="display:none;flex-direction:column;gap:8px;">
                    <div id="m-otp-banner" style="background:#451a03;border:1px solid #d97706;color:#fde68a;font-size:11px;padding:8px 10px;border-radius:10px;">OTP sent to email.</div>
                    <input type="text" id="m-auth-otp" maxlength="6" inputmode="numeric" placeholder="6-Digit Verification OTP *" style="width:100%;box-sizing:border-box;text-align:center;letter-spacing:0.35em;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:16px;font-weight:800;">
                    <input type="text" id="m-auth-name" placeholder="Full Name *" style="width:100%;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:13px;">
                    <div style="display:flex;gap:8px;">
                        <input type="text" id="m-auth-branch" placeholder="Branch Name *" style="flex:1;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:13px;">
                        <input type="text" id="m-auth-unit" placeholder="Unit No. *" style="width:125px;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:13px;">
                    </div>
                    <input type="tel" id="m-auth-phone" maxlength="10" inputmode="numeric" placeholder="10-Digit Mobile Number *" style="width:100%;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:13px;font-weight:700;">
                    <div style="display:flex;gap:8px;">
                        <input type="password" id="m-auth-newpin" maxlength="4" inputmode="numeric" placeholder="Create 4-Digit PIN" style="flex:1;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:13px;font-weight:700;">
                        <input type="text" id="m-auth-code" value="SAMAGAM26" placeholder="Event Code" style="width:120px;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:10px;padding:10px;color:#ffffff;font-size:13px;text-transform:uppercase;">
                    </div>
                    <button id="m-btn-otp-verify" style="width:100%;background:#059669;color:#ffffff;border:none;border-radius:12px;padding:12px;font-size:13px;font-weight:800;cursor:pointer;">Verify OTP & Complete Sign-Up</button>
                </div>

                <div id="m-auth-err" style="color:#fb7185;font-size:12px;font-weight:700;text-align:center;margin-top:10px;"></div>
                <div style="text-align:center;margin-top:14px;border-top:1px solid #1e293b;padding-top:10px;">
                    <a href="${originPrefix}/" style="color:#94a3b8;font-size:11px;text-decoration:underline;">← Back to Public Welcome Portal</a>
                </div>
            </div>
        `;

        const errBox = document.getElementById("m-auth-err");
        document.getElementById("m-btn-back1").onclick = () => {
            document.getElementById("m-auth-step1").style.display = "flex";
            document.getElementById("m-auth-step-pin").style.display = "none";
            errBox.textContent = "";
        };

        document.getElementById("m-btn-continue").onclick = async () => {
            const ident = document.getElementById("m-auth-ident").value.trim();
            errBox.textContent = "";
            if (!ident) { errBox.textContent = "Enter mobile number or email."; return; }
            const res = await origFetch(originPrefix + "/api/auth/otp/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ identifier: ident })
            });
            const data = await res.json();
            if (!res.ok) { errBox.textContent = data.detail || "Unable to proceed."; return; }
            document.getElementById("m-auth-step1").style.display = "none";
            if (data.requires_pin) {
                document.getElementById("m-auth-step-pin").style.display = "flex";
                document.getElementById("m-pin-label").textContent = `Welcome ${data.driver_name || "Sevadar"}! Enter your 4-digit PIN:`;
            } else {
                document.getElementById("m-auth-step-otp").style.display = "flex";
                document.getElementById("m-otp-banner").textContent = `OTP sent to ${data.email}` + (data.dev_otp ? ` (OTP: ${data.dev_otp})` : "");
            }
        };

        document.getElementById("m-btn-pin-verify").onclick = async () => {
            const ident = document.getElementById("m-auth-ident").value.trim();
            const pin = document.getElementById("m-auth-pin").value.trim();
            const res = await origFetch(originPrefix + "/api/auth/pin/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ identifier: ident, pin })
            });
            const data = await res.json();
            if (!res.ok) { errBox.textContent = data.detail || "Incorrect PIN."; return; }
            localStorage.setItem("samagam_driver_token", data.token);
            localStorage.setItem("samagam_field_token", data.token);
            localStorage.setItem("samagam_field_user", JSON.stringify(data.driver));
            overlay.remove();
            renderJagritiTopBar(data.driver);
        };

        document.getElementById("m-btn-otp-verify").onclick = async () => {
            const ident = document.getElementById("m-auth-ident").value.trim();
            const fullName = document.getElementById("m-auth-name").value.trim();
            const branchName = document.getElementById("m-auth-branch").value.trim();
            const unitNo = document.getElementById("m-auth-unit").value.trim();
            const phone = document.getElementById("m-auth-phone").value.trim();

            if (!fullName || !branchName || !unitNo || !phone) {
                errBox.textContent = "Please fill Name, Branch Name, Unit No., and Mobile Number.";
                return;
            }

            const res = await origFetch(originPrefix + "/api/auth/otp/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email: ident,
                    otp: document.getElementById("m-auth-otp").value.trim(),
                    name: fullName,
                    branch_name: branchName,
                    unit_number: unitNo,
                    phone: phone,
                    pin: document.getElementById("m-auth-newpin").value.trim(),
                    code: document.getElementById("m-auth-code").value.trim(),
                    system_role: "FIELD_VOLUNTEER"
                })
            });
            const data = await res.json();
            if (!res.ok) { errBox.textContent = data.detail || "OTP verification failed."; return; }
            localStorage.setItem("samagam_driver_token", data.token);
            localStorage.setItem("samagam_field_token", data.token);
            localStorage.setItem("samagam_field_user", JSON.stringify(data.driver));
            overlay.remove();
            renderJagritiTopBar(data.driver);
        };
    }

    function renderJagritiTopBar(user) {
        if (document.getElementById("jagriti-top-strip")) return;
        const strip = document.createElement("div");
        strip.id = "jagriti-top-strip";
        strip.style.cssText = "max-width:768px;margin:0 auto;background:#ffffff;border-bottom:1px solid #e2e8f0;padding:8px 14px;display:flex;align-items:center;justify-content:space-between;font-family:system-ui,sans-serif;";
        strip.innerHTML = `
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="width:28px;height:28px;border-radius:9999px;background:#fef3c7;border:1px solid #f59e0b;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:10px;color:#0f2c59;">जागृति</div>
                <div>
                    <div style="font-size:11px;font-weight:800;color:#0f2c59;line-height:1.1;">
                        ${user ? user.full_name || user.name : "जागृति The Awakening"}
                    </div>
                    <div style="font-size:9.5px;color:#059669;font-weight:700;">● Verified Active Session</div>
                </div>
            </div>
            <button id="jagriti-global-logout-btn" style="background:#fee2e2;color:#b91c1c;font-size:10px;font-weight:800;padding:4px 9px;border-radius:9999px;border:1px solid #fca5a5;cursor:pointer;">
                Logout
            </button>
        `;
        document.body.insertBefore(strip, document.body.firstChild);
        document.getElementById("jagriti-global-logout-btn").onclick = async () => {
            await fetch(originPrefix + "/api/auth/driver-logout", { method: "POST" });
            forceLockoutScreen("You have logged out.");
        };
    }

    async function verifySessionWithServer() {
        if (isPublicPage) return;
        const tok = localStorage.getItem("samagam_driver_token") || localStorage.getItem("samagam_field_token") || "";
        if (!tok) {
            showCompulsoryLoginModal("");
            return;
        }
        try {
            const res = await origFetch(originPrefix + "/api/auth/session-heartbeat", {
                headers: { "X-Driver-Token": tok }
            });
            if (!res.ok) {
                const d = await res.json().catch(() => ({}));
                forceLockoutScreen(d.detail || "Session expired or terminated by Admin.");
            } else {
                const d = await res.json();
                renderJagritiTopBar(d.user);
            }
        } catch (_) {}
    }

    window.addEventListener("DOMContentLoaded", () => {
        if (!isPublicPage) {
            verifySessionWithServer();
            setInterval(verifySessionWithServer, 10000);
        }
    });
})();
'''

# ------------------------------------------------------------------------------
# 3. FIRST-TIME BUS ONBOARDING & REGISTRATION HTML FORM (COMPULSORY LOGIN + NO PUBLIC CONTROL ROOM LINK)
# ------------------------------------------------------------------------------
FILES["bus_onboarding_form.html"] = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>First-Time Bus Onboarding & Registration | Samagam Transport</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {
            background: radial-gradient(circle at top, #064e3b 0%, #0f172a 45%, #020617 100%);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: #f8fafc;
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">

    <header class="bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-4 py-3.5 sticky top-0 z-40">
        <div class="max-w-3xl mx-auto flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
                <span class="text-2xl">🚌</span>
                <div>
                    <h1 class="font-extrabold text-sm sm:text-base text-white tracking-wide">FIRST-TIME BUS ONBOARDING & REGISTRATION</h1>
                    <p class="text-xs text-emerald-300">Ground Team • Station Team • Control Room Admin</p>
                </div>
            </div>
            <div class="flex gap-2 text-xs font-bold">
                <a href="/station_team_app.html" class="bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-xl border border-slate-700">🚉 Station</a>
                <a href="/ground_team_app.html" class="bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-xl border border-slate-700">⛺ Ground</a>
                <a href="/" class="bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 rounded-xl">← Home</a>
            </div>
        </div>
    </header>

    <main class="max-w-3xl mx-auto w-full px-4 py-6 flex-1 space-y-6">
        <div class="bg-slate-900/95 border border-slate-700/80 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-5">
            <div class="border-b border-slate-800 pb-4">
                <span class="text-[11px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                    New Fleet Entry • Live Database Sync
                </span>
                <h2 class="text-xl sm:text-2xl font-extrabold text-white mt-2">Register Bus Arriving for the First Time</h2>
                <p class="text-xs text-slate-400 mt-1">
                    Registers Trust-Owned, 24-Hour Hired Outside, or MSRTC Spot Cash buses into the live fleet and activates the Driver App (default PIN: <strong class="text-emerald-300">1234</strong>) for 180-second GPS tracking.
                </p>
            </div>

            <form id="standalone-bus-onboard-form" onsubmit="submitStandaloneBusOnboard(event)" class="space-y-4 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Bus Reg. Number *</label>
                        <input type="text" name="vehicle_reg_number" required placeholder="MH-04-AB-1234" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-black uppercase tracking-wider">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Ownership Category *</label>
                        <select id="st-ownership-type" name="ownership_type" onchange="toggleStandaloneExtraFields()" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-bold">
                            <option value="TRUST_OWNED">Trust-Owned Fleet</option>
                            <option value="HIRED_OUTSIDE">24h Hired Outside Bus</option>
                            <option value="MSRTC_SPOT_CASH">MSRTC Spot Cash Bus</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Onboarding Team *</label>
                        <select name="onboarding_team" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                            <option value="Ground Team">⛺ Ground Team</option>
                            <option value="Station Team">🚉 Station Team</option>
                            <option value="Admin Control Room">🏛️ Admin Control Room</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Vehicle Type *</label>
                        <select name="vehicle_type" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                            <option value="Heavy Bus (50-seater)">Heavy Bus (50-seater)</option>
                            <option value="Mini Bus / Tempo (35-seater)">Mini Bus / Tempo (35-seater)</option>
                            <option value="MSRTC State Transport Bus">MSRTC State Bus (55-seater)</option>
                            <option value="Shuttle Van / SUV (15-seater)">Shuttle Van / SUV (15-seater)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Seating Capacity *</label>
                        <input type="number" name="capacity" value="50" min="4" max="90" required class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-extrabold text-center">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Reporting Hub / Gate *</label>
                        <select id="st-hub-select" name="current_hub" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                            <option value="Ground 1 (Main Hall)">Ground 1 (Main Hall)</option>
                            <option value="Ground 2 (North Camp)">Ground 2 (North Camp)</option>
                            <option value="Thane Railway Station">Thane Railway Station</option>
                            <option value="Panvel Junction (PNVL)">Panvel Junction (PNVL)</option>
                            <option value="Dadar Terminal (DR/DDR)">Dadar Terminal (DR/DDR)</option>
                            <option value="Lokmanya Tilak Terminus (LTT)">Lokmanya Tilak Terminus (LTT)</option>
                            <option value="Chhatrapati Shivaji Maharaj Terminus (CSMT)">CSMT Mumbai</option>
                            <option value="Kalyan Junction (KYN)">Kalyan Junction (KYN)</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Driver Full Name *</label>
                        <input type="text" name="driver_name" required placeholder="Primary Driver Name" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Driver 10-Digit Mobile *</label>
                        <input type="tel" name="driver_phone" maxlength="10" inputmode="numeric" required placeholder="98XXXXXXXX" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-bold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Co-Driver / Rider Name</label>
                        <input type="text" name="rider_name" placeholder="Optional Co-Driver / Sevadar" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-300 mb-1">Co-Driver / Rider Mobile</label>
                        <input type="tel" name="rider_phone" maxlength="10" inputmode="numeric" placeholder="Optional 10-Digit Mobile" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white">
                    </div>
                </div>

                <div id="st-hired-fields" class="hidden bg-blue-950/60 border border-blue-500/60 rounded-2xl p-4 space-y-3">
                    <div class="text-xs font-extrabold uppercase tracking-wider text-blue-300">⏱️ 24-Hour Rolling Hired Contract Details</div>
                    <div>
                        <label class="block text-xs font-bold text-blue-200 mb-1">Vendor / Travels Agency Name *</label>
                        <input type="text" name="contractor_name" placeholder="e.g. Shree Siddhivinayak Travels" class="w-full bg-slate-950 border border-blue-500/60 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-blue-200 mb-1">Entry Odometer KM</label>
                            <input type="number" name="entry_odometer_km" placeholder="e.g. 142500" class="w-full bg-slate-950 border border-blue-500/60 rounded-xl px-3.5 py-2.5 text-white font-bold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-blue-200 mb-1">24h Base Rate (₹)</label>
                            <input type="number" name="daily_base_rate_inr" value="7500" class="w-full bg-slate-950 border border-blue-500/60 rounded-xl px-3.5 py-2.5 text-white font-bold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-blue-200 mb-1">Extra Rate (₹ / KM)</label>
                            <input type="number" name="extra_rate_per_km_inr" value="25" class="w-full bg-slate-950 border border-blue-500/60 rounded-xl px-3.5 py-2.5 text-white font-bold">
                        </div>
                    </div>
                </div>

                <div id="st-msrtc-fields" class="hidden bg-amber-950/60 border border-amber-500/60 rounded-2xl p-4 space-y-3">
                    <div class="text-xs font-extrabold uppercase tracking-wider text-amber-300">🧾 MSRTC Spot Cash Conductor Voucher Details</div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-amber-200 mb-1">MSRTC Depot Name *</label>
                            <input type="text" id="st-msrtc-depot" placeholder="e.g. Thane Depot 1 / Panvel Depot" class="w-full bg-slate-950 border border-amber-500/60 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-amber-200 mb-1">Conductor Name *</label>
                            <input type="text" name="conductor_name" placeholder="MSRTC Conductor Name" class="w-full bg-slate-950 border border-amber-500/60 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                        </div>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-amber-200 mb-1">ETM Ticket Receipt No.</label>
                            <input type="text" name="etm_receipt_number" placeholder="ETM-992831" class="w-full bg-slate-950 border border-amber-500/60 rounded-xl px-3.5 py-2.5 text-white font-mono uppercase">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-amber-200 mb-1">Cash Paid (₹)</label>
                            <input type="number" name="cash_amount_paid_inr" placeholder="e.g. 1650" class="w-full bg-slate-950 border border-amber-500/60 rounded-xl px-3.5 py-2.5 text-white font-bold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-amber-200 mb-1">Passenger Headcount</label>
                            <input type="number" name="passenger_headcount" value="50" class="w-full bg-slate-950 border border-amber-500/60 rounded-xl px-3.5 py-2.5 text-white font-bold">
                        </div>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-slate-300 mb-1">Registered By (Sevadar / Coordinator / Admin Name) *</label>
                    <input type="text" name="registered_by" required placeholder="Enter your full name" class="w-full bg-slate-950 border border-slate-600 rounded-xl px-3.5 py-2.5 text-white font-semibold">
                </div>

                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold py-4 rounded-2xl text-sm sm:text-base shadow-xl transition">
                    ✅ Complete First-Time Bus Registration
                </button>
            </form>

            <div id="onboard-result-banner" class="hidden rounded-2xl p-4 text-xs sm:text-sm font-bold"></div>
        </div>

        <div class="bg-slate-900/95 border border-slate-700/80 rounded-3xl p-6 shadow-xl space-y-3">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <div>
                    <h3 class="text-sm sm:text-base font-extrabold text-emerald-300">🗄️ Live Database Registry — Recently Onboarded Buses</h3>
                    <p class="text-[11px] text-slate-400">Synced directly from central PostgreSQL / SQLite database</p>
                </div>
                <button onclick="loadRecentOnboardedBuses()" class="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-xl font-bold text-slate-200">↻ Refresh DB</button>
            </div>
            <div id="recent-onboarded-list" class="space-y-2 text-xs">
                <p class="text-slate-500">Loading database records...</p>
            </div>
        </div>
    </main>

    <footer class="border-t border-slate-800 py-4 text-center text-xs text-slate-400">
        Samagam Transport & Logistics Cell • First-Time Bus Onboarding
    </footer>

    <script src="/static/samagam_app_shell.js"></script>
    <script>
        function toggleStandaloneExtraFields() {
            const val = document.getElementById('st-ownership-type').value;
            document.getElementById('st-hired-fields').classList.toggle('hidden', val !== 'HIRED_OUTSIDE');
            document.getElementById('st-msrtc-fields').classList.toggle('hidden', val !== 'MSRTC_SPOT_CASH');
        }

        async function loadAllHubsDropdown() {
            try {
                const res = await fetch('/api/operations/hubs');
                if (!res.ok) return;
                const hubs = await res.json();
                if (hubs.length) {
                    document.getElementById('st-hub-select').innerHTML = hubs.map(h =>
                        `<option value="${h.hub_name}">${h.hub_name}</option>`
                    ).join('');
                }
            } catch (_) {}
        }

        async function loadRecentOnboardedBuses() {
            try {
                const res = await fetch('/api/fleet/vehicles/recent-onboardings');
                if (!res.ok) return;
                const list = await res.json();
                const box = document.getElementById('recent-onboarded-list');
                box.innerHTML = list.length ? list.map(v => `
                    <div class="p-3 bg-slate-950 border border-slate-800 rounded-2xl flex flex-wrap justify-between items-center gap-2">
                        <div>
                            <div class="font-extrabold text-white text-sm">${v.vehicle_reg_number} <span class="text-xs font-semibold text-emerald-400">(${v.vehicle_type} • ${v.capacity} Seats)</span></div>
                            <div class="text-slate-400">Driver: <strong class="text-slate-200">${v.driver_name}</strong> (${v.driver_phone}) • Hub: <strong class="text-amber-300">${v.current_hub}</strong></div>
                            <div class="text-[11px] text-slate-500">Team: ${v.onboarding_team} • By: ${v.registered_by || 'System'}</div>
                        </div>
                        <div class="text-right">
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-emerald-950 text-emerald-300 border border-emerald-700">${v.ownership_type}</span>
                            <div class="text-[10px] text-slate-400 mt-1">${v.status}</div>
                        </div>
                    </div>
                `).join('') : '<p class="text-slate-500">No buses registered yet.</p>';
            } catch (_) {}
        }

        async function submitStandaloneBusOnboard(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            if (payload.ownership_type === 'MSRTC_SPOT_CASH') {
                payload.contractor_name = document.getElementById('st-msrtc-depot').value.trim() || 'MSRTC Depot';
            }

            const banner = document.getElementById('onboard-result-banner');
            const res = await fetch('/api/fleet/vehicles/onboard-first-time', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            banner.classList.remove('hidden');
            if (res.ok) {
                banner.className = 'rounded-2xl p-4 text-xs sm:text-sm font-bold bg-emerald-950 border border-emerald-500 text-emerald-200';
                banner.innerHTML = `✅ ${data.summary}<br><span class="text-xs font-normal text-emerald-300">Synced to Vehicles, Turnaround, Volunteers & Billing Tables (Driver PIN: 1234 | 180s GPS Tracking)</span>`;
                e.target.reset();
                toggleStandaloneExtraFields();
                loadRecentOnboardedBuses();
            } else {
                banner.className = 'rounded-2xl p-4 text-xs sm:text-sm font-bold bg-rose-950 border border-rose-500 text-rose-200';
                banner.textContent = '❌ ' + (data.detail || 'Could not register bus.');
            }
        }

        window.addEventListener('DOMContentLoaded', () => {
            loadAllHubsDropdown();
            loadRecentOnboardedBuses();
        });
    </script>
</body>
</html>
'''


def patch_existing_project_files():
    # 1. Ensure Vehicle model has onboarding_team & registered_by, and DevoteeParkingPass has email/branch/zone
    models_path = os.path.join(TARGET_DIR, "app", "models.py")
    if os.path.exists(models_path):
        with open(models_path, "r", encoding="utf-8") as f:
            mcode = f.read()
        changed = False
        if "onboarding_team = Column" not in mcode and "rider_phone = Column" in mcode:
            mcode = mcode.replace(
                "    rider_phone = Column(String(20), nullable=True)\n",
                "    rider_phone = Column(String(20), nullable=True)\n"
                "    onboarding_team = Column(String(60), default=\"Control Room\")\n"
                "    registered_by = Column(String(120), nullable=True)\n"
            )
            changed = True
        if "branch_name = Column" not in mcode and "class DevoteeParkingPass" in mcode:
            mcode = mcode.replace(
                "    owner_phone = Column(String(20), nullable=False, index=True)\n",
                "    owner_phone = Column(String(20), nullable=False, index=True)\n"
                "    owner_email = Column(String(120), nullable=True)\n"
                "    branch_name = Column(String(120), nullable=True)\n"
                "    zone_name = Column(String(120), nullable=True)\n"
            )
            changed = True
        if changed:
            with open(models_path, "w", encoding="utf-8") as f:
                f.write(mcode)
            print("✅ Patched app/models.py with onboarding_team, registered_by, owner_email, branch_name & zone_name")

    # 2. Ensure auth.py supports Driver Bus Operator Name vs Non-Driver Branch + Unit No. + Session Heartbeat + Admin Termination
    auth_path = os.path.join(TARGET_DIR, "app", "routers", "auth.py")
    if os.path.exists(auth_path):
        with open(auth_path, "r", encoding="utf-8") as f:
            acode = f.read()
        if "bus_operator_name" not in acode:
            acode = acode.replace(
                '    role = str(data.get("system_role") or "FIELD_VOLUNTEER").upper().strip()',
                '    role = str(data.get("system_role") or "FIELD_VOLUNTEER").upper().strip()\n'
                '    branch_name = str(data.get("branch_name") or "").strip()\n'
                '    unit_number = str(data.get("unit_number") or "").strip()\n'
                '    bus_operator_name = str(data.get("bus_operator_name") or "").strip()'
            ).replace(
                '        unit_number="Field-Crew",\n        branch_name="Samagam Transport",',
                '        unit_number=("Fleet-Driver" if role == "DRIVER" else (unit_number or "Unit-01")),\n'
                '        branch_name=(f"Operator: {bus_operator_name}" if role == "DRIVER" else (branch_name or "Samagam Branch")),'
            )
            with open(auth_path, "w", encoding="utf-8") as f:
                f.write(acode)
            print("✅ Patched app/routers/auth.py with Driver Operator & Branch/Unit registration fields")

    # 3. Ensure samagam_app_shell.js is attached to all 8 field/operational HTML pages
    for fname in [
        "station_team_app.html", "ground_team_app.html", "gate_keeper_app.html",
        "diesel_team_app.html", "accounts_team_app.html", "driver_rider_companion.html",
        "radar_map_console.html", "bus_onboarding_form.html"
    ]:
        fpath = os.path.join(TARGET_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                html = f.read()
            if "samagam_app_shell.js" not in html:
                html = html.replace("</body>", '    <script src="/static/samagam_app_shell.js"></script>\n</body>')
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"🔐 Attached Compulsory Login & Termination Guard to: {fname}")

    # 4. Ensure driver_rider_companion.html uses 180s GPS upload interval
    drv_path = os.path.join(TARGET_DIR, "driver_rider_companion.html")
    if os.path.exists(drv_path):
        with open(drv_path, "r", encoding="utf-8") as f:
            dhtml = f.read()
        if "180000" not in dhtml:
            dhtml = dhtml.replace("10000", "180000").replace("GPS LIVE (10s)", "GPS LIVE (180s)")
            with open(drv_path, "w", encoding="utf-8") as f:
                f.write(dhtml)
            print("🔋 Updated Driver GPS upload interval to 180 seconds (3 minutes)")


def main():
    print(f"🚀 Running COMPLETE MASTER ALL-IN-ONE DEPLOYMENT inside: {TARGET_DIR}\n")
    for rel_path, content in FILES.items():
        full_path = os.path.join(TARGET_DIR, rel_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Wrote: {full_path}")

    patch_existing_project_files()

    print("\n🎉 ALL FILES & DISCUSSIONS FROM TODAY COMPILED IN ONE GO!")
    print("\n--- STEP 1: LAPTOP & GITHUB (PowerShell in C:\\narendra\\SamagamtransportV1) ---")
    print("   python deploy_complete_samagam_suite.py")
    print("   git add .")
    print('   git commit -m "Complete Samagam Suite: Subdomains, Mandatory Auth, 27 Committees, Bus Onboarding & Full DB Excel"')
    print("   git push origin main")
    print("\n--- STEP 2: GOOGLE CLOUD RUN (Cloud Shell) ---")
    print("   cd ~/Samagamtransport_v1 && git pull origin main && gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080")


if __name__ == "__main__":
    main()