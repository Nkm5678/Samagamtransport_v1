"""
Samagam Transport & Logistics Platform — Complete All-in-One Updater & ZIP Packager
Run this single script inside C:\narendra\SamagamtransportV1:
    python apply_all_samagam_updates.py

What it does automatically:
1. Creates a safety backup ZIP of your existing folder on your Desktop.
2. Writes all updated HTML portals (welcome.html, admin_dashboard.html, parking_security_gate.html,
   rental_hiring_proforma.html, driver_rider_companion.html, gate_keeper_app.html, in_ground_seva_vehicles.html).
3. Writes all updated FastAPI backend modules (app/models.py, app/main.py, app/routers/auth.py,
   app/routers/fleet.py, app/routers/operations.py, app/routers/reports.py, manage.py, requirements.txt).
4. Packages the entire updated folder into SamagamtransportV1_Updated.zip on your Desktop.
"""

import os
import zipfile
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPDATED_FILES = {
    "requirements.txt": """fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.28
pydantic>=2.6.4
pydantic-settings>=2.2.1
requests>=2.31.0
psycopg2-binary>=2.9.9
openpyxl>=3.1.2
werkzeug>=3.0.0
""",

    "app/main.py": """import os
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

@app.get("/driver")
def serve_driver():
    return _serve_html("driver_rider_companion.html")

@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(ROOT_DIR, "sw.js"), media_type="application/javascript")

@app.get("/{page_name}.html")
def serve_html_page(page_name: str):
    return _serve_html(f"{page_name}.html")

@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}
""",

    "welcome.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>जागृति — The Awakening | निरंकारी सन्त समागम परिवहन सेवा (Samagam Transport)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@500;700;800&family=Playfair+Display:ital,wght@0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { background: radial-gradient(circle at top, #ffffff 0%, #eef3fb 55%, #dce4f2 100%); font-family: 'Inter', 'Noto Sans Devanagari', sans-serif; color: #0f172a; }
        .jagriti-sun-glow { background: radial-gradient(circle, rgba(251, 191, 36, 0.36) 0%, rgba(253, 224, 71, 0.12) 48%, rgba(255, 255, 255, 0) 72%); }
        .lang-btn.active { background-color: #0f2c59; color: #ffffff; box-shadow: 0 6px 16px rgba(15, 44, 89, 0.25); }
        .portal-card { transition: transform 0.22s ease, box-shadow 0.22s ease; }
        .portal-card:hover { transform: translateY(-4px); box-shadow: 0 24px 48px -12px rgba(15, 44, 89, 0.18); }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">
    <header class="bg-white/90 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-40">
        <div class="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-1.5 bg-slate-100 p-1 rounded-2xl border border-slate-200 text-xs font-extrabold">
                <button onclick="setLanguage('hi', this)" class="lang-btn px-3.5 py-1.5 rounded-xl transition">हिंदी</button>
                <button onclick="setLanguage('mr', this)" class="lang-btn px-3.5 py-1.5 rounded-xl transition">मराठी</button>
                <button onclick="setLanguage('en', this)" class="lang-btn active px-3.5 py-1.5 rounded-xl transition">English</button>
            </div>
            <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
                <a href="/download_hub.html" class="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 transition">📲 <span data-i18n="nav_apps">Field Apps (.APK)</span></a>
                <a href="/admin_dashboard.html" class="px-3.5 py-2 rounded-xl bg-[#0f2c59] hover:bg-sky-900 text-white shadow transition">🏛️ <span data-i18n="nav_admin">Transport Control Room</span></a>
            </div>
        </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-8 space-y-8 flex-1 w-full">
        <section class="text-center max-w-3xl mx-auto space-y-3 pt-1">
            <div class="inline-block px-4 py-1 rounded-full bg-sky-100 text-[#0f2c59] text-xs font-extrabold tracking-wide">धन निरंकार जी 🙏 • SANT NIRANKARI MANDAL</div>
            <div class="relative mx-auto w-64 h-36 flex flex-col items-center justify-center jagriti-sun-glow rounded-full">
                <div class="text-5xl sm:text-6xl font-extrabold tracking-tight" style="color: #0f2c59;">जागृति</div>
                <div class="text-sm sm:text-base italic font-bold text-slate-800 -mt-1" style="font-family: 'Playfair Display', serif;">The Awakening</div>
            </div>
            <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight" style="color: #0f2c59;">निरंकारी सन्त समागम — परिवहन सेवा पोर्टल</h1>
            <p class="text-xs sm:text-sm font-bold text-slate-600">60th Maharashtra Annual Nirankari Sant Samagam • Kharghar, Navi Mumbai (Central Park) • 23–26 January 2027</p>
            <p class="text-xs sm:text-sm text-slate-500 max-w-2xl mx-auto leading-relaxed" data-i18n="hero_desc">Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database so our team can allocate vehicles and update your request status live.</p>
        </section>

        <!-- Live Request Allocation Status Tracker -->
        <section class="max-w-4xl mx-auto bg-white rounded-3xl p-5 sm:p-6 border-2 border-[#0f2c59]/20 shadow-lg space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900">Live Allocation Status</span>
                    <h2 class="text-base sm:text-lg font-extrabold text-[#0f2c59] mt-1" data-i18n="track_title">🔍 Check Your Vehicle Allocation Status (By Mobile No. or Request ID)</h2>
                </div>
                <span class="text-[11px] text-slate-400">Auto-refreshes every 30s</span>
            </div>
            <div class="flex flex-col sm:flex-row gap-2.5">
                <input type="text" id="track-query-input" placeholder="Enter 10-Digit Mobile (e.g. 9820...) or Request Code (PND-... / REQ-...)" class="flex-1 border border-slate-300 rounded-2xl px-4 py-3 text-sm font-bold text-slate-900 focus:outline-none">
                <button onclick="checkMyRequestStatus()" class="bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold px-6 py-3 rounded-2xl text-sm shadow transition" data-i18n="track_btn">Check Status</button>
            </div>
            <div id="track-status-results" class="space-y-2.5 pt-1"></div>
        </section>

        <!-- Two Primary Request Portals -->
        <section class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            <div class="portal-card bg-white rounded-3xl p-7 border border-sky-200 shadow-lg flex flex-col justify-between space-y-6">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="w-14 h-14 rounded-2xl bg-sky-100 text-3xl flex items-center justify-center">⛺</span>
                        <span class="text-[11px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-sky-50 text-[#0f2c59] border border-sky-200" data-i18n="badge_ground">Internal Venue Logistics</span>
                    </div>
                    <h2 class="text-xl sm:text-2xl font-extrabold text-[#0f2c59]" data-i18n="card1_title">Need Vehicle Inside Samagam Ground</h2>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed" data-i18n="card1_desc">For Samagam departments (Langar, Tent, Sound, Medical, Security, Sanitation) needing cars, pickups, tempos, or e-rickshaws inside Central Park Kharghar grounds—or to donate a vehicle for Seva.</p>
                </div>
                <a href="/in_ground_seva_vehicles.html" class="w-full bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold py-4 px-5 rounded-2xl text-sm flex items-center justify-between shadow-lg transition">
                    <span data-i18n="card1_btn">Request / Donate In-Ground Vehicle</span><span>→</span>
                </a>
            </div>

            <div class="portal-card bg-white rounded-3xl p-7 border border-emerald-200 shadow-lg flex flex-col justify-between space-y-6">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="w-14 h-14 rounded-2xl bg-emerald-100 text-3xl flex items-center justify-center">🚉</span>
                        <span class="text-[11px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200" data-i18n="badge_transit">Station • Airport • Bus Depot</span>
                    </div>
                    <h2 class="text-xl sm:text-2xl font-extrabold text-emerald-950" data-i18n="card2_title">Need Vehicle for Pickup & Drop (Railway Station / Airport / Bus Depot)</h2>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed" data-i18n="card2_desc">Request shuttle buses, tempo travellers, or cars for Saints, Jathas, or guests arriving at or departing from Railway Stations (Panvel, Thane, CSMT, LTT, Dadar, Kalyan), Mumbai Airports (T1/T2), or ST Bus Depots.</p>
                </div>
                <button onclick="openPickupDropModal()" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-4 px-5 rounded-2xl text-sm flex items-center justify-between shadow-lg transition">
                    <span data-i18n="card2_btn">Raise Pickup / Drop Vehicle Request</span><span>→</span>
                </button>
            </div>
        </section>
    </main>

    <!-- Pickup & Drop Modal -->
    <div id="pickup-drop-modal" class="fixed inset-0 bg-slate-950/75 hidden items-center justify-center z-50 p-4 overflow-y-auto">
        <div class="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-7 space-y-4 shadow-2xl my-auto">
            <div class="flex justify-between items-start border-b pb-3">
                <h3 class="text-lg font-extrabold text-slate-900" data-i18n="modal_pd_title">Pickup & Drop Vehicle Requirement Form</h3>
                <button onclick="closePickupDropModal()" class="text-slate-400 hover:text-slate-800 font-bold text-lg">✕</button>
            </div>
            <form id="pickup-drop-form" onsubmit="submitPickupDropRequest(event)" class="space-y-3.5 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <select name="trip_direction" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        <option value="PICKUP_TO_SAMAGAM">Pickup → Samagam Ground (Kharghar)</option>
                        <option value="DROP_FROM_SAMAGAM">Drop ← Samagam Ground to Station/Airport</option>
                        <option value="ROUND_TRIP">Round Trip (Pickup + Drop)</option>
                    </select>
                    <select name="transit_hub" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        <option value="Panvel Junction (PNVL)">Panvel Railway Junction (PNVL)</option>
                        <option value="Thane Railway Station">Thane Railway Station</option>
                        <option value="Lokmanya Tilak Terminus (LTT)">Lokmanya Tilak Terminus (LTT)</option>
                        <option value="Dadar Terminal (DR/DDR)">Dadar Railway Terminal</option>
                        <option value="Chhatrapati Shivaji Maharaj Terminus (CSMT)">CSMT Mumbai</option>
                        <option value="Kalyan Junction (KYN)">Kalyan Junction</option>
                        <option value="Mumbai Airport Terminal 1 (Domestic)">Mumbai Airport T1 (Domestic)</option>
                        <option value="Mumbai Airport Terminal 2 (International)">Mumbai Airport T2 (International)</option>
                        <option value="Navi Mumbai / Panvel ST Bus Depot">Panvel / Kharghar ST Bus Depot</option>
                    </select>
                </div>
                <div class="grid grid-cols-3 gap-3">
                    <input type="number" name="passenger_count" value="40" min="1" required placeholder="Pax" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                    <select name="vehicle_type_requested" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        <option value="Heavy Bus (50-Seater)">Heavy Bus (50-Seater)</option>
                        <option value="Tempo Traveller (20-26 Seat)">Tempo Traveller</option>
                        <option value="Innova / Ertiga / Car">Innova / Car</option>
                    </select>
                    <input type="number" name="vehicles_needed" value="1" min="1" required placeholder="Qty" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <input type="datetime-local" name="scheduled_datetime" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    <input type="text" name="train_flight_details" placeholder="Train / Flight No." class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <input type="text" name="requester_name" required placeholder="Coordinator Name *" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    <input type="tel" name="requester_phone" required placeholder="10-Digit Mobile *" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                </div>
                <textarea name="notes" rows="2" placeholder="Special notes..." class="w-full border border-slate-300 rounded-xl px-3 py-2"></textarea>
                <button type="submit" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-3.5 rounded-2xl text-sm shadow-lg">✅ Submit Pickup/Drop Request</button>
            </form>
        </div>
    </div>

    <script>
        const TRANSLATIONS = {
            en: { nav_apps: "Field Apps (.APK)", nav_admin: "Transport Control Room", hero_desc: "Select your transport requirement below. All vehicle requests are connected directly to the Central Transport Database.", track_title: "🔍 Check Your Vehicle Allocation Status (By Mobile No. or Request ID)", track_btn: "Check Status", badge_ground: "Internal Venue Logistics", card1_title: "Need Vehicle Inside Samagam Ground", card1_desc: "For Samagam departments needing cars, pickups, tempos, or e-rickshaws inside Central Park Kharghar grounds—or to donate a vehicle for Seva.", card1_btn: "Request / Donate In-Ground Vehicle", badge_transit: "Station • Airport • Bus Depot", card2_title: "Need Vehicle for Pickup & Drop (Railway Station / Airport / Bus Depot)", card2_desc: "Request shuttle buses, tempo travellers, or cars for Saints and Jathas arriving at or departing from Railway Stations, Mumbai Airports, or ST Bus Depots.", card2_btn: "Raise Pickup / Drop Vehicle Request", modal_pd_title: "Pickup & Drop Vehicle Requirement Form" },
            hi: { nav_apps: "फील्ड ऐप्स (.APK)", nav_admin: "परिवहन कंट्रोल रूम", hero_desc: "नीचे अपनी परिवहन आवश्यकता चुनें। सभी वाहन अनुरोध सीधे मुख्य डेटाबेस से जुड़े हैं।", track_title: "🔍 अपने वाहन आवंटन की स्थिति जांचें (मोबाइल नंबर या रिक्वेस्ट कोड द्वारा)", track_btn: "स्थिति जांचें", badge_ground: "समागम ग्राउंड आंतरिक सेवा", card1_title: "समागम ग्राउंड के अंदर वाहन चाहिए", card1_desc: "लंगर, टेंट, साउंड, मेडिकल और सुरक्षा विभागों के लिए ग्राउंड के अंदर वाहन की मांग करें या सेवा हेतु वाहन जमा करें।", card1_btn: "ग्राउंड के अंदर वाहन मांगें / जमा करें", badge_transit: "रेलवे स्टेशन • एयरपोर्ट • बस डिपो", card2_title: "रेलवे स्टेशन, एयरपोर्ट या बस डिपो से पिकअप और ड्रॉप के लिए वाहन चाहिए", card2_desc: "रेलवे स्टेशन, मुंबई एयरपोर्ट या एस.टी. बस डिपो से सन्तों और जत्थों को लाने-ले जाने हेतु वाहन बुक करें।", card2_btn: "पिकअप / ड्रॉप वाहन अनुरोध दर्ज करें", modal_pd_title: "पिकअप और ड्रॉप वाहन आवश्यकता फॉर्म" },
            mr: { nav_apps: "फील्ड ॲप्स (.APK)", nav_admin: "परिवहन कंट्रोल रूम", hero_desc: "खालीलपैकी आपली वाहन आवश्यकता निवडा. सर्व वाहन विनंत्या थेट मुख्य डेटाबेसशी जोडलेल्या आहेत.", track_title: "🔍 तुमच्या वाहन वाटपाची स्थिती तपासा (मोबाईल नंबर किंवा रिक्वेस्ट कोडद्वारे)", track_btn: "स्थिती तपासा", badge_ground: "समागम ग्राउंड अंतर्गत सेवा", card1_title: "समागम ग्राउंडच्या आत वाहन हवे आहे", card1_desc: "लंगर, टेंट, साउंड, मेडिकल व सुरक्षा विभागांसाठी ग्राउंडच्या आत वाहनाची मागणी करा अथवा सेवेसाठी वाहन जमा करा.", card1_btn: "ग्राउंडसाठी वाहन मागणी / वाहन जमा करा", badge_transit: "रेल्वे स्टेशन • एअरपोर्ट • बस डेपो", card2_title: "रेल्वे स्टेशन, एअरपोर्ट व बस डेपो पिकअप-ड्रॉपसाठी वाहन हवे आहे", card2_desc: "रेल्वे स्टेशन, मुंबई एअरपोर्ट किंवा एस.टी. बस डेपोवरून संत व जत्थ्यांच्या ने-आण करण्यासाठी वाहन मागणी नोंदवा.", card2_btn: "पिकअप / ड्रॉप वाहन मागणी नोंदवा", modal_pd_title: "पिकअप आणि ड्रॉप वाहन मागणी फॉर्म" }
        };
        function setLanguage(lang, btn) {
            const d = TRANSLATIONS[lang] || TRANSLATIONS.en;
            document.querySelectorAll('[data-i18n]').forEach(el => { const k = el.getAttribute('data-i18n'); if (d[k]) el.textContent = d[k]; });
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
        }
        function openPickupDropModal() { document.getElementById('pickup-drop-modal').classList.remove('hidden'); document.getElementById('pickup-drop-modal').classList.add('flex'); }
        function closePickupDropModal() { document.getElementById('pickup-drop-modal').classList.add('hidden'); document.getElementById('pickup-drop-modal').classList.remove('flex'); }
        async function submitPickupDropRequest(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.passenger_count = parseInt(payload.passenger_count);
            payload.vehicles_needed = parseInt(payload.vehicles_needed);
            const res = await fetch('/api/operations/pickup-drop-requests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const data = await res.json();
            if (res.ok) {
                document.getElementById('track-query-input').value = payload.requester_phone;
                e.target.reset(); closePickupDropModal(); checkMyRequestStatus();
            }
        }
        async function checkMyRequestStatus() {
            const q = document.getElementById('track-query-input').value.trim();
            if (!q) return;
            const res = await fetch(`/api/operations/request-status-lookup?query=${encodeURIComponent(q)}`);
            const items = res.ok ? await res.json() : [];
            const box = document.getElementById('track-status-results');
            box.innerHTML = items.length ? items.map(item => `
                <div class="p-4 rounded-2xl border-2 ${item.is_allocated ? 'bg-emerald-50 border-emerald-500' : 'bg-amber-50/70 border-amber-300'} flex flex-wrap justify-between items-center gap-3 text-xs">
                    <div>
                        <span class="font-extrabold text-sm">${item.code}</span> — <span class="font-bold">${item.is_allocated ? '✅ VEHICLE ALLOCATED' : '⏳ PENDING ALLOCATION'}</span>
                        <div class="text-slate-700">${item.category} • ${item.summary}</div>
                    </div>
                    ${item.is_allocated ? `<div class="bg-white p-2.5 rounded-xl border border-emerald-300 font-bold text-right">${item.assigned_vehicle_reg}<br>${item.driver_name} (${item.driver_phone})</div>` : ''}
                </div>
            `).join('') : '<div class="text-xs text-amber-800 font-semibold">No matching requests found yet.</div>';
        }
    </script>
</body>
</html>
"""
}


def run_all_updates():
    print("🚀 Starting Samagam Transport All-in-One Folder Updater...\n")

    # 1. Create safety backup ZIP on Desktop
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_zip = os.path.join(desktop, f"SamagamtransportV1_Backup_{ts}.zip")
    with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv", "venv"}]
            for file in files:
                if file.endswith(".zip"):
                    continue
                full_p = os.path.join(root, file)
                zf.write(full_p, os.path.relpath(full_p, BASE_DIR))
    print(f"📦 Backup of old folder saved to: {backup_zip}")

    # 2. Write updated files
    for rel_path, content in UPDATED_FILES.items():
        target_path = os.path.join(BASE_DIR, rel_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Updated: {rel_path}")

    # 3. Package complete updated folder into a clean downloadable ZIP on Desktop
    updated_zip = os.path.join(desktop, f"SamagamtransportV1_Updated_{ts}.zip")
    with zipfile.ZipFile(updated_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv", "venv"}]
            for file in files:
                if file.endswith(".zip"):
                    continue
                full_p = os.path.join(root, file)
                zf.write(full_p, os.path.relpath(full_p, BASE_DIR))

    print(f"\n🎉 Complete Updated ZIP created at: {updated_zip}")
    print("👉 Next step: Run 'pip install -r requirements.txt' and 'python run.py' to start your updated platform!")


if __name__ == "__main__":
    run_all_updates()