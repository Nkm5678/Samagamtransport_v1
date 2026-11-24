"""
Samagam Transport Platform — All-In-One One-Go Implementation Script
Applies all updates created after 9:00 AM today in a single run:
  1. welcome.html & root/welcome.html (Jagriti logo, 5 portal links, side-by-side Pickup/Drop
     & Donate Vehicle for Sewa boxes, Station/Train auto-suggest, 24h status tracker, no public live feed)
  2. in_ground_seva_vehicles.html & root/in_ground_seva_vehicles.html (ground.samagamtransport.in
     OTP/PIN auth, Advance Projection & Justification + Ad-hoc requests, ASAP message)
  3. samagam_master_topology_and_operations.html & root/samagam_master_topology_and_operations.html
     (Communication Link & Master Contact Directory with one-click CRUD & Bulk Import)
  4. admin_dashboard.html & root/admin_dashboard.html (All Reports Center, Ground Dept Vehicle
     Allocation, Admin SQL Query Console, Clean Test Data button)
  5. static/samagam_app_shell.js & root/static/samagam_app_shell.js (Registration page-close guard
     + 30s timeout & cold-start retry protection)
  6. app/main.py (Subdomain routing for ground., parking., advancesewa., admin. + Ground Team allocation UI)
  7. app/routers/auth.py (Google IAP JWT verification & Google Group RBAC mapping)
  8. app/routers/operations.py & app/routers/reports.py (Contact Directory APIs, SQL Query Console,
     Admin Overview & Test Data Purge)
  9. setup_gcp_iam_secrets.sh (Cloud Run Service Account, Secret Manager & IAP Group IAM script)

Usage inside C:\\narendra\\SamagamtransportV1:
    python apply_all_today_updates.py
"""

import glob
import os
import shutil
import subprocess
from datetime import datetime

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# 1. WELCOME PORTAL (welcome.html)
# ==============================================================================
WELCOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>60th Maharashtra Annual Samagam — Transport Service Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+Devanagari:wght@500;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {
            background: radial-gradient(circle at 50% 0%, #fffbeb 0%, #f1f5f9 55%, #e2e8f0 100%);
            font-family: 'Inter', 'Noto Sans Devanagari', sans-serif;
            color: #0f172a;
        }
        .lang-btn.active {
            background-color: #f59e0b;
            color: #0f172a;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35);
        }
        .service-card {
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .service-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 35px -10px rgba(15, 23, 42, 0.14);
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">

    <header class="bg-[#0b2447]/95 text-white backdrop-blur-md border-b border-amber-400/30 sticky top-0 z-40">
        <div class="max-w-6xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2.5">
                <img src="/static/jagriti.png"
                     onerror="this.onerror=null;this.src='/static/jagriti_proper_logo.svg';"
                     alt="जागृति — The Awakening"
                     class="h-10 w-auto rounded-xl bg-white px-2 py-0.5 shadow border border-amber-300/60 object-contain">
                <div class="flex items-center gap-1.5 bg-white/10 p-1 rounded-2xl border border-white/15 text-xs font-extrabold">
                    <button onclick="setLanguage('hi', this)" class="lang-btn px-3 py-1.5 rounded-xl text-white transition">हिंदी</button>
                    <button onclick="setLanguage('mr', this)" class="lang-btn px-3 py-1.5 rounded-xl text-white transition">मराठी</button>
                    <button onclick="setLanguage('en', this)" class="lang-btn active px-3 py-1.5 rounded-xl transition">English</button>
                </div>
            </div>

            <nav class="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs font-extrabold">
                <a href="https://advancesewa.samagamtransport.in" class="px-3 py-2 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 transition shadow">
                    🙏 Advance Sewa
                </a>
                <a href="https://parking.samagamtransport.in" class="px-3 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shadow">
                    🅿️ Parking
                </a>
                <a href="https://tent.samagamtransport.in" class="px-3 py-2 rounded-xl bg-sky-400 hover:bg-sky-300 text-slate-950 transition shadow">
                    ⛺ Tent Allotment
                </a>
                <a href="https://ground.samagamtransport.in" class="px-3 py-2 rounded-xl bg-teal-400 hover:bg-teal-300 text-slate-950 transition shadow">
                    🚛 Ground Service
                </a>
                <a href="https://admin.samagamtransport.in" class="px-3 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-white transition shadow">
                    🛡️ Admin
                </a>
                <a href="/download_hub.html" class="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white border border-white/20 transition">
                    📲 Field Apps
                </a>
            </nav>
        </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-6 sm:py-8 space-y-7 flex-1 w-full">

        <section class="text-center max-w-3xl mx-auto space-y-3 pt-1">
            <div class="inline-flex items-center gap-2 px-4 py-1 rounded-full bg-[#0b2447] text-amber-300 text-xs font-extrabold tracking-wide shadow">
                <span>धन निरंकार जी 🙏</span>
                <span>•</span>
                <span>SAMAGAM TRANSPORT & LOGISTICS</span>
            </div>

            <div class="mx-auto max-w-xs sm:max-w-sm">
                <img src="/static/jagriti.png"
                     onerror="this.onerror=null;this.src='/static/jagriti_proper_logo.svg';"
                     alt="जागृति — The Awakening"
                     class="w-full h-auto rounded-3xl bg-white p-3 shadow-lg border-2 border-amber-300/80 mx-auto object-contain">
            </div>

            <h1 class="text-2xl sm:text-3xl font-black tracking-tight text-[#0b2447]">
                60वां सन्त समागम — परिवहन सेवा पोर्टल
            </h1>
            <p class="text-xs sm:text-sm font-bold text-amber-900">
                23, 24 एवं 25 जनवरी 2027 • सेक्टर 29/30, सिडको ग्राउंड, सेंट्रल पार्क के पास, खारघर, नवी मुंबई - 410210
            </p>
            <p class="text-xs sm:text-sm text-slate-600 max-w-2xl mx-auto leading-relaxed" data-i18n="hero_desc">
                Select your transport requirement below. All vehicle requests and Sewa vehicle offers connect directly to the Central Transport Database.
            </p>
        </section>

        <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4 max-w-5xl mx-auto">
            <a href="https://advancesewa.samagamtransport.in" class="bg-white hover:bg-amber-50 border border-amber-200 rounded-2xl p-4 shadow-sm transition flex flex-col justify-between space-y-2">
                <div class="text-2xl">🙏</div>
                <div>
                    <div class="font-extrabold text-sm text-amber-950">1) Advance Sewa</div>
                    <div class="text-[11px] text-slate-500">Pre-Samagam Sewa Transport</div>
                </div>
            </a>

            <a href="https://parking.samagamtransport.in" class="bg-white hover:bg-emerald-50 border border-emerald-200 rounded-2xl p-4 shadow-sm transition flex flex-col justify-between space-y-2">
                <div class="text-2xl">🅿️</div>
                <div>
                    <div class="font-extrabold text-sm text-emerald-950">2) Parking</div>
                    <div class="text-[11px] text-slate-500">Windshield QR & Gate Pass</div>
                </div>
            </a>

            <a href="https://tent.samagamtransport.in" class="bg-white hover:bg-sky-50 border border-sky-200 rounded-2xl p-4 shadow-sm transition flex flex-col justify-between space-y-2">
                <div class="text-2xl">⛺</div>
                <div>
                    <div class="font-extrabold text-sm text-sky-950">3) Tent Allotment</div>
                    <div class="text-[11px] text-slate-500">Accommodation & Sector Info</div>
                </div>
            </a>

            <a href="https://ground.samagamtransport.in" class="bg-white hover:bg-teal-50 border border-teal-200 rounded-2xl p-4 shadow-sm transition flex flex-col justify-between space-y-2">
                <div class="text-2xl">🚛</div>
                <div>
                    <div class="font-extrabold text-sm text-teal-950">4) Ground Service</div>
                    <div class="text-[11px] text-slate-500">Dept Goods & Internal Vehicles</div>
                </div>
            </a>

            <a href="https://admin.samagamtransport.in" class="col-span-2 sm:col-span-1 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-2xl p-4 shadow-sm transition flex flex-col justify-between space-y-2 text-white">
                <div class="text-2xl">🛡️</div>
                <div>
                    <div class="font-extrabold text-sm text-amber-300">5) Admin</div>
                    <div class="text-[11px] text-slate-300">HQ Control Room & Reports</div>
                </div>
            </a>
        </section>

        <section class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            <div class="service-card bg-white rounded-3xl p-6 sm:p-7 border-2 border-emerald-200 shadow-lg flex flex-col justify-between space-y-5">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-900 flex items-center justify-center text-2xl shadow-inner">
                            🚍
                        </span>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                            Station • Airport • Bus Depot
                        </span>
                    </div>
                    <h2 class="text-xl font-black text-emerald-950" data-i18n="card2_title">
                        Need Vehicle for Pickup & Drop
                    </h2>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed" data-i18n="card2_desc">
                        Request shuttle buses, tempo travellers, for Saints, groups or guests arriving at or departing from Railway Stations, Mumbai Airports (T1/T2), Navi Mumbai Airport or ST Bus Depots.
                    </p>
                </div>

                <div class="pt-2 space-y-2.5">
                    <button onclick="openPickupDropModal()" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-3.5 px-5 rounded-2xl text-xs sm:text-sm shadow-lg transition flex items-center justify-center gap-2">
                        <span data-i18n="card2_btn">🚍 Raise Pickup / Drop Request →</span>
                    </button>
                    <div class="text-center text-[11px] font-semibold text-slate-500">
                        Includes Auto-Suggested Train No./Name, Ticket Upload & Live Status Tracking
                    </div>
                </div>
            </div>

            <div class="service-card bg-white rounded-3xl p-6 sm:p-7 border-2 border-amber-300 shadow-lg flex flex-col justify-between space-y-5">
                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="w-12 h-12 rounded-2xl bg-amber-100 text-amber-900 flex items-center justify-center text-2xl shadow-inner">
                            🙏
                        </span>
                        <span class="text-[10px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-200">
                            Samagam & Advance Sewa
                        </span>
                    </div>
                    <h2 class="text-xl font-black text-amber-950" data-i18n="donate_title">
                        Donate Vehicle for Sewa
                    </h2>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed" data-i18n="donate_desc">
                        Offer your car, SUV, tempo traveller, bus, or goods carrier for Nishkam Transport Sewa during Samagam, in Advance Sewa preparations, or both.
                    </p>
                </div>

                <div class="pt-2 space-y-2.5">
                    <button onclick="openDonateVehicleModal()" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-3.5 px-5 rounded-2xl text-xs sm:text-sm shadow-lg transition flex items-center justify-center gap-2">
                        <span data-i18n="donate_btn">🙏 Offer Vehicle for Samagam / Advance Sewa →</span>
                    </button>
                    <div class="text-center text-[11px] font-semibold text-slate-500">
                        With or Without Driver • Directly Registered in Central Fleet Pool
                    </div>
                </div>
            </div>
        </section>

        <section class="max-w-5xl mx-auto bg-white rounded-3xl p-5 sm:p-6 border-2 border-[#0f2c59]/20 shadow-md space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-sm sm:text-base font-extrabold text-[#0f2c59]" data-i18n="track_title">
                    🔍 Check Your Vehicle Allocation Status (24-Hour Live Tracker via Mobile No. or Request ID)
                </h2>
                <span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">Live Database Status</span>
            </div>
            <div class="flex flex-col sm:flex-row gap-2.5">
                <input type="text" id="track-query-input" placeholder="Enter 10-Digit Mobile Number or Request ID (e.g. PND-1234, REQ-1234)" class="flex-1 border border-slate-300 rounded-2xl px-4 py-3 text-sm font-semibold focus:outline-none focus:border-[#0f2c59]">
                <button onclick="checkMyRequestStatus()" class="bg-[#0f2c59] hover:bg-sky-900 text-white font-extrabold px-6 py-3 rounded-2xl text-sm shadow transition">
                    <span data-i18n="track_btn">Check Status</span>
                </button>
            </div>
            <div id="track-status-results" class="space-y-2.5"></div>
        </section>

    </main>

    <!-- MODAL 1: PICKUP & DROP -->
    <div id="pickup-drop-modal" class="fixed inset-0 bg-slate-950/75 hidden items-center justify-center z-50 p-4 overflow-y-auto">
        <div class="bg-white rounded-3xl max-w-2xl w-full p-6 sm:p-7 space-y-4 shadow-2xl my-auto">
            <div class="flex justify-between items-start border-b pb-3">
                <div>
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900">
                        Station • Mumbai & Navi Mumbai Airports • ST Bus Depot
                    </span>
                    <h3 class="text-lg font-extrabold text-slate-900 mt-1">
                        Pickup & Drop Vehicle Requirement Form
                    </h3>
                </div>
                <button onclick="closePickupDropModal()" class="text-slate-400 hover:text-slate-800 font-bold text-lg">✕</button>
            </div>

            <form id="pickup-drop-modal-form" onsubmit="submitPickupDropRequest(event)" class="space-y-3 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Group Leader Name *</label>
                        <input type="text" name="requester_name" required placeholder="Group Leader Full Name" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">10-Digit Mobile Number *</label>
                        <input type="tel" name="requester_phone" required maxlength="10" inputmode="numeric" placeholder="98XXXXXXXX" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Zone *</label>
                        <select id="pdm-zone-select" name="zone_name" onchange="populateBranchesForZone('pdm-zone-select', 'pdm-branch-select')" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="">-- Select Zone --</option>
                            <option value="Zone 1 (Mumbai South & Central)">Zone 1 (Mumbai South & Central)</option>
                            <option value="Zone 2 (Mumbai Western Suburbs)">Zone 2 (Mumbai Western Suburbs)</option>
                            <option value="Zone 3 (Thane & Kalyan)">Zone 3 (Thane & Kalyan)</option>
                            <option value="Zone 4 (Navi Mumbai & Raigad)">Zone 4 (Navi Mumbai & Raigad)</option>
                            <option value="Zone 5 (Pune & Western Maharashtra)">Zone 5 (Pune & Western Maharashtra)</option>
                            <option value="Zone 6 (Nashik & North Maharashtra)">Zone 6 (Nashik & North Maharashtra)</option>
                            <option value="Zone 7 (Vidarbha & Marathwada)">Zone 7 (Vidarbha & Marathwada)</option>
                            <option value="Outstation / Other State Jatha">Outstation / Other State Jatha</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Branch *</label>
                        <select id="pdm-branch-select" name="branch_name" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="">-- Select Zone First --</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Unit No. *</label>
                        <input type="text" name="unit_number" required placeholder="e.g. Unit No. 214" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Trip Direction *</label>
                        <select name="trip_direction" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="PICKUP_TO_SAMAGAM">Pickup → Samagam Ground</option>
                            <option value="DROP_FROM_SAMAGAM">Samagam Ground → Drop</option>
                            <option value="ROUND_TRIP">Both Pickup & Return Drop</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Arrival Station / Airport / Depot *</label>
                        <select id="pdm-arrival-station" name="transit_hub" onchange="updateTrainSuggestions('pdm')" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="Panvel Junction (PNVL)">Panvel Railway Station (PNVL)</option>
                            <option value="Thane Railway Station (TNA)">Thane Railway Station (TNA)</option>
                            <option value="Lokmanya Tilak Terminus (LTT)">Lokmanya Tilak Terminus (LTT)</option>
                            <option value="Dadar Terminal (DR/DDR)">Dadar Railway Terminal (DR/DDR)</option>
                            <option value="Chhatrapati Shivaji Maharaj Terminus (CSMT)">CSMT Mumbai</option>
                            <option value="Mumbai Central (MMCT)">Mumbai Central (MMCT)</option>
                            <option value="Bandra Terminus (BDTS)">Bandra Terminus (BDTS)</option>
                            <option value="Kalyan Junction (KYN)">Kalyan Junction (KYN)</option>
                            <option value="Navi Mumbai International Airport (NMIA)">Navi Mumbai International Airport (NMIA)</option>
                            <option value="Mumbai Airport Terminal 1 (Domestic)">Mumbai Airport Terminal 1 (Domestic)</option>
                            <option value="Mumbai Airport Terminal 2 (International)">Mumbai Airport Terminal 2 (International)</option>
                            <option value="Panvel / Sion / Dadar ST Bus Depot">Panvel / Sion / Dadar ST Bus Depot</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">No. of Saints *</label>
                        <input type="number" name="passenger_count" value="45" min="1" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-slate-50 p-3 rounded-2xl border border-slate-200">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Train / Flight Number *</label>
                        <input type="text" id="pdm-train-number" name="train_number" list="pdm-train-num-list" oninput="syncTrainNameFromNumber('pdm')" required placeholder="Type or select Train No." class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-extrabold">
                        <datalist id="pdm-train-num-list"></datalist>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Train / Flight Name *</label>
                        <input type="text" id="pdm-train-name" name="train_name" list="pdm-train-name-list" oninput="syncTrainNumberFromName('pdm')" required placeholder="Auto-suggested Train Name" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        <datalist id="pdm-train-name-list"></datalist>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Arrival Date & Time *</label>
                        <input type="datetime-local" name="scheduled_datetime" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Departure Date *</label>
                        <input type="date" name="departure_date" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Upload Ticket (Optional)</label>
                        <input type="file" accept=".pdf,.jpg,.jpeg,.png" onchange="handleTicketFileEncode(this, 'pdm-ticket-b64')" class="w-full border border-slate-300 rounded-xl px-2 py-2 text-xs">
                        <input type="hidden" id="pdm-ticket-b64" name="ticket_attachment_name" value="">
                    </div>
                </div>

                <button type="submit" class="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-extrabold py-3.5 rounded-2xl text-sm shadow-lg transition">
                    ✅ Submit Pickup/Drop Request to Transport Control
                </button>
            </form>
        </div>
    </div>

    <!-- MODAL 2: DONATE VEHICLE FOR SEWA -->
    <div id="donate-vehicle-modal" class="fixed inset-0 bg-slate-950/75 hidden items-center justify-center z-50 p-4 overflow-y-auto">
        <div class="bg-white rounded-3xl max-w-2xl w-full p-6 sm:p-7 space-y-4 shadow-2xl my-auto">
            <div class="flex justify-between items-start border-b pb-3">
                <div>
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-950">
                        🙏 Nishkam Transport Sewa • During Samagam & Advance Sewa
                    </span>
                    <h3 class="text-lg font-extrabold text-slate-900 mt-1">
                        Donate Vehicle for Sewa (During Samagam & In Advance Sewa)
                    </h3>
                </div>
                <button onclick="closeDonateVehicleModal()" class="text-slate-400 hover:text-slate-800 font-bold text-lg">✕</button>
            </div>

            <div id="donate-vehicle-confirmation" class="hidden bg-emerald-50 border-2 border-emerald-600 rounded-2xl p-4 text-xs sm:text-sm space-y-1">
                <div class="font-black text-emerald-950">धन निरंकार जी 🙏 Thank You for Offering Your Vehicle for Sewa!</div>
                <div id="donate-vehicle-confirmation-text" class="font-bold text-emerald-900"></div>
            </div>

            <form id="donate-vehicle-form" onsubmit="submitDonateVehicleSewa(event)" class="space-y-3 text-xs sm:text-sm">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Sewa Period / Availability Phase *</label>
                        <select name="sewa_phase" required class="w-full border border-amber-300 bg-amber-50/60 rounded-xl px-3 py-2.5 font-extrabold text-amber-950">
                            <option value="BOTH_ADVANCE_AND_SAMAGAM">🌟 Both (Advance Sewa + During Samagam)</option>
                            <option value="DURING_SAMAGAM">🎪 During Samagam (23–26 Jan 2027)</option>
                            <option value="ADVANCE_SEWA">🙏 In Advance Sewa (Pre-Samagam)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Vehicle Owner / Donor Name *</label>
                        <input type="text" name="donor_name" required placeholder="Full Name" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Owner 10-Digit Mobile Number *</label>
                        <input type="tel" name="donor_phone" required maxlength="10" inputmode="numeric" placeholder="98XXXXXXXX" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Branch & Unit No. *</label>
                        <input type="text" name="branch_unit" required placeholder="e.g. Thane / Unit No. 214" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Vehicle Registration No. *</label>
                        <input type="text" name="vehicle_reg_number" required placeholder="MH-04-AB-1234" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 uppercase font-black tracking-wide">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Vehicle Type & Model *</label>
                        <select name="vehicle_type" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="Car / Sedan / Hatchback">🚗 Car / Sedan / Hatchback (4–5 Seat)</option>
                            <option value="SUV / Innova / Ertiga / Bolero">🚙 SUV / Innova / Ertiga / Bolero (7–9 Seat)</option>
                            <option value="Tempo Traveller / Mini Bus">🚐 Tempo Traveller / Mini Bus (17–32 Seat)</option>
                            <option value="Heavy Bus (45-55 Seater)">🚌 Heavy Bus (45–55 Seater)</option>
                            <option value="Goods Carrier / Pickup / Chhota Hathi">🚛 Goods Carrier / Pickup / Tempo</option>
                            <option value="Two-Wheeler / Scooter">🛵 Two-Wheeler / Scooter</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Seating / Load Capacity *</label>
                        <input type="number" name="seating_capacity" value="5" min="1" max="65" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Driver Included? *</label>
                        <select name="driver_included" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                            <option value="YES_WITH_DRIVER">✅ Yes — Owner / Sevadar Driver</option>
                            <option value="NO_VEHICLE_ONLY">🔑 Vehicle Only — Assign Driver</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Available From Date *</label>
                        <input type="date" name="available_from_date" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Available Till Date *</label>
                        <input type="date" name="available_to_date" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Driver Name & Mobile (If Included)</label>
                        <input type="text" name="driver_details" placeholder="Driver Name & 10-Digit Mobile" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Preferred Duty / Fuel Notes</label>
                        <input type="text" name="notes" placeholder="e.g. Station Shuttle / Ground Duty" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                    </div>
                </div>

                <button type="submit" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-3.5 rounded-2xl text-sm shadow-lg transition">
                    🙏 Register Vehicle for Samagam / Advance Sewa
                </button>
            </form>
        </div>
    </div>

    <footer class="bg-[#0b2447] text-sky-200 border-t border-amber-400/30 py-4 text-center text-xs mt-10">
        धन निरंकार जी 🙏 • Samagam Transport & Logistics Cell • www.samagamtransport.in
    </footer>

    <script>
        const ZONE_BRANCHES = {
            "Zone 1 (Mumbai South & Central)": ["Colaba", "Byculla", "Dadar", "Sion", "Matunga", "Chembur", "Ghatkopar", "Kurla", "Mulund"],
            "Zone 2 (Mumbai Western Suburbs)": ["Bandra", "Santacruz", "Andheri", "Jogeshwari", "Goregaon", "Malad", "Kandivali", "Borivali", "Dahisar"],
            "Zone 3 (Thane & Kalyan)": ["Thane", "Kalwa", "Mumbra", "Diva", "Dombivli", "Kalyan", "Ulhasnagar", "Ambernath", "Badlapur", "Bhiwandi"],
            "Zone 4 (Navi Mumbai & Raigad)": ["Vashi", "Nerul", "CBD Belapur", "Kharghar", "Kamothe", "Kalamboli", "Panvel", "Uran", "Alibaug", "Pen", "Khopoli"],
            "Zone 5 (Pune & Western Maharashtra)": ["Pune City", "Pimpri-Chinchwad", "Lonavala", "Satara", "Sangli", "Kolhapur", "Solapur"],
            "Zone 6 (Nashik & North Maharashtra)": ["Nashik", "Igatpuri", "Manmad", "Jalgaon", "Bhusawal", "Dhule", "Ahmednagar"],
            "Zone 7 (Vidarbha & Marathwada)": ["Nagpur", "Amravati", "Akola", "Chhatrapati Sambhajinagar", "Nanded", "Latur"],
            "Outstation / Other State Jatha": ["Delhi NCR", "Gujarat", "Madhya Pradesh", "Karnataka", "Goa", "Rajasthan", "Other State"]
        };

        const STATION_TRAINS = {
            "Panvel Junction (PNVL)": [
                { num: "10103", name: "Mandovi Express" },
                { num: "10111", name: "Konkan Kanya Express" },
                { num: "12051", name: "Janshatabdi Express" },
                { num: "12617", name: "Mangala Lakshadweep Express" },
                { num: "16345", name: "Netravati Express" },
                { num: "11003", name: "Tutari Express" },
                { num: "22119", name: "Tejas Express" }
            ],
            "Thane Railway Station (TNA)": [
                { num: "12138", name: "Punjab Mail" },
                { num: "11058", name: "Amritsar - CSMT Express" },
                { num: "12112", name: "Amravati Express" },
                { num: "12810", name: "Howrah - CSMT Mail" },
                { num: "17058", name: "Devagiri Express" },
                { num: "12106", name: "Vidarbha Express" }
            ],
            "Lokmanya Tilak Terminus (LTT)": [
                { num: "11056", name: "Godan Express" },
                { num: "12142", name: "Patliputra - LTT Express" },
                { num: "12168", name: "Banaras - LTT Superfast" },
                { num: "15018", name: "Gorakhpur - LTT Kashi Express" },
                { num: "12860", name: "Gitanjali Express" },
                { num: "11072", name: "Kamayani Express" }
            ],
            "Dadar Terminal (DR/DDR)": [
                { num: "11029", name: "Koyna Express" },
                { num: "11009", name: "Sinhagad Express" },
                { num: "12115", name: "Siddheshwar Express" },
                { num: "11301", name: "Udyan Express" },
                { num: "12902", name: "Gujarat Mail" }
            ],
            "Chhatrapati Shivaji Maharaj Terminus (CSMT)": [
                { num: "12124", name: "Deccan Queen" },
                { num: "12126", name: "Pragati Express" },
                { num: "12071", name: "Jalna Janshatabdi" },
                { num: "12105", name: "Vidarbha Express" },
                { num: "12137", name: "Punjab Mail" }
            ],
            "Mumbai Central (MMCT)": [
                { num: "12952", name: "Mumbai Rajdhani Express" },
                { num: "12954", name: "August Kranti Rajdhani" },
                { num: "12926", name: "Paschim Express" },
                { num: "12904", name: "Golden Temple Mail" }
            ],
            "Bandra Terminus (BDTS)": [
                { num: "12925", name: "Paschim Express" },
                { num: "19019", name: "Dehradun Express" },
                { num: "12471", name: "Swaraj Express" },
                { num: "12907", name: "Maharashtra Sampark Kranti" }
            ],
            "Kalyan Junction (KYN)": [
                { num: "12140", name: "Sewagram Express" },
                { num: "11402", name: "Nandigram Express" },
                { num: "12102", name: "Jnaneswari Express" },
                { num: "12152", name: "Samarsata Express" }
            ],
            "Navi Mumbai International Airport (NMIA)": [
                { num: "AI-NMIA", name: "Air India Domestic / Regional" },
                { num: "6E-NMIA", name: "IndiGo Airlines" },
                { num: "QP-NMIA", name: "Akasa Air" }
            ],
            "Mumbai Airport Terminal 1 (Domestic)": [
                { num: "6E-T1", name: "IndiGo Domestic Terminal 1" },
                { num: "SG-T1", name: "SpiceJet Terminal 1" },
                { num: "QP-T1", name: "Akasa Air Terminal 1" }
            ],
            "Mumbai Airport Terminal 2 (International)": [
                { num: "AI-T2", name: "Air India Terminal 2" },
                { num: "UK-T2", name: "Vistara / Air India T2" },
                { num: "6E-T2", name: "IndiGo International / T2" }
            ],
            "Panvel / Sion / Dadar ST Bus Depot": [
                { num: "MSRTC-SHIV", name: "MSRTC Shivneri / Shivshahi" },
                { num: "MSRTC-HIR", name: "MSRTC Hirkani Semi-Luxury" },
                { num: "MSRTC-ORD", name: "MSRTC Parivartan / Express" }
            ]
        };

        function populateBranchesForZone(zoneSelectId, branchSelectId) {
            const zone = document.getElementById(zoneSelectId).value;
            const branchEl = document.getElementById(branchSelectId);
            const list = ZONE_BRANCHES[zone] || [];
            branchEl.innerHTML = list.length
                ? list.map(b => `<option value="${b}">${b}</option>`).join('')
                : '<option value="">-- Select Zone First --</option>';
        }

        function updateTrainSuggestions(prefix) {
            const station = document.getElementById(`${prefix}-arrival-station`).value;
            const trains = STATION_TRAINS[station] || [];
            const numList = document.getElementById(`${prefix}-train-num-list`);
            const nameList = document.getElementById(`${prefix}-train-name-list`);
            numList.innerHTML = trains.map(t => `<option value="${t.num}">${t.num} — ${t.name}</option>`).join('');
            nameList.innerHTML = trains.map(t => `<option value="${t.name}">${t.num} — ${t.name}</option>`).join('');
        }

        function syncTrainNameFromNumber(prefix) {
            const station = document.getElementById(`${prefix}-arrival-station`).value;
            const numVal = document.getElementById(`${prefix}-train-number`).value.trim().toUpperCase();
            const match = (STATION_TRAINS[station] || []).find(t => t.num.toUpperCase() === numVal);
            if (match) document.getElementById(`${prefix}-train-name`).value = match.name;
        }

        function syncTrainNumberFromName(prefix) {
            const station = document.getElementById(`${prefix}-arrival-station`).value;
            const nameVal = document.getElementById(`${prefix}-train-name`).value.trim().toLowerCase();
            const match = (STATION_TRAINS[station] || []).find(t => t.name.toLowerCase() === nameVal);
            if (match) document.getElementById(`${prefix}-train-number`).value = match.num;
        }

        function handleTicketFileEncode(inputEl, hiddenId) {
            const file = inputEl.files && inputEl.files[0];
            if (file) document.getElementById(hiddenId).value = file.name;
        }

        const TRANSLATIONS = {
            en: {
                hero_desc: "Select your transport requirement below. All vehicle requests and Sewa vehicle offers connect directly to the Central Transport Database.",
                track_title: "🔍 Check Your Vehicle Allocation Status (24-Hour Live Tracker via Mobile No. or Request ID)",
                track_btn: "Check Status",
                card2_title: "Need Vehicle for Pickup & Drop",
                card2_desc: "Request shuttle buses, tempo travellers, for Saints, groups or guests arriving at or departing from Railway Stations, Mumbai Airports (T1/T2), Navi Mumbai Airport or ST Bus Depots.",
                card2_btn: "🚍 Raise Pickup / Drop Request →",
                donate_title: "Donate Vehicle for Sewa",
                donate_desc: "Offer your car, SUV, tempo traveller, bus, or goods carrier for Nishkam Transport Sewa during Samagam, in Advance Sewa preparations, or both.",
                donate_btn: "🙏 Offer Vehicle for Samagam / Advance Sewa →"
            },
            hi: {
                hero_desc: "नीचे अपनी परिवहन आवश्यकता चुनें। सभी वाहन अनुरोध और सेवा वाहन प्रस्ताव सीधे केंद्रीय परिवहन डेटाबेस से जुड़ते हैं।",
                track_title: "🔍 अपने वाहन आवंटन की स्थिति जांचें (24 घंटे के भीतर मोबाइल नंबर या रिक्वेस्ट कोड द्वारा)",
                track_btn: "स्थिति जांचें",
                card2_title: "पिकअप और ड्रॉप के लिए वाहन चाहिए",
                card2_desc: "रेलवे स्टेशन, मुंबई एयरपोर्ट (T1/T2), नवी मुंबई एयरपोर्ट या एसटी बस डिपो से आने-जाने वाले संतों, समूहों या अतिथियों के लिए शटल बसों और टेम्पो ट्रैवलर का अनुरोध करें।",
                card2_btn: "🚍 पिकअप / ड्रॉप अनुरोध दर्ज करें →",
                donate_title: "निष्काम सेवा हेतु वाहन अर्पित करें",
                donate_desc: "समागम के दिनों में, अग्रिम सेवा (Advance Sewa) तैयारियों में, या दोनों के लिए अपनी कार, एसयूवी, टेम्पो ट्रैवलर, बस या मालवाहक वाहन अर्पित करें।",
                donate_btn: "🙏 समागम / अग्रिम सेवा हेतु वाहन दें →"
            },
            mr: {
                hero_desc: "खाली तुमची परिवहन गरज निवडा. सर्व वाहन विनंत्या आणि सेवा वाहन प्रस्ताव थेट मुख्य परिवहन डेटाबेसशी जोडलेले आहेत.",
                track_title: "🔍 तुमच्या वाहन वाटपाची स्थिती तपासा (२४ तासांच्या आत मोबाईल नंबर किंवा रिक्वेस्ट कोडद्वारे)",
                track_btn: "स्थिती तपासा",
                card2_title: "पिकअप आणि ड्रॉपसाठी वाहन हवे आहे",
                card2_desc: "रेल्वे स्टेशन, मुंबई एअरपोर्ट (T1/T2), नवी मुंबई एअरपोर्ट किंवा एसटी बस डेपोवरून ये-जा करणाऱ्या संत, गट किंवा पाहुण्यांसाठी शटल बस व टेम्पो ट्रॅव्हलरची मागणी करा.",
                card2_btn: "🚍 पिकअप / ड्रॉप विनंती नोंदवा →",
                donate_title: "निष्काम सेवेसाठी वाहन द्या",
                donate_desc: "समागमाच्या काळात, आगाऊ सेवा (Advance Sewa) तयारीसाठी किंवा दोन्हीसाठी तुमची कार, एसयूव्ही, टेम्पो ट्रॅव्हलर, बस किंवा मालवाहू वाहन नोंदवा.",
                donate_btn: "🙏 समागम / आगाऊ सेवेसाठी वाहन द्या →"
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

        function openDonateVehicleModal() {
            document.getElementById('donate-vehicle-modal').classList.remove('hidden');
            document.getElementById('donate-vehicle-modal').classList.add('flex');
        }

        function closeDonateVehicleModal() {
            document.getElementById('donate-vehicle-modal').classList.add('hidden');
            document.getElementById('donate-vehicle-modal').classList.remove('flex');
        }

        async function submitPickupDropRequest(e) {
            e.preventDefault();
            const raw = Object.fromEntries(new FormData(e.target).entries());
            const payload = {
                trip_direction: raw.trip_direction || "PICKUP_TO_SAMAGAM",
                transit_hub: raw.transit_hub,
                passenger_count: parseInt(raw.passenger_count) || 1,
                vehicle_type_requested: raw.vehicle_type_requested || "Heavy Bus (50-Seater)",
                vehicles_needed: Math.max(1, Math.ceil((parseInt(raw.passenger_count) || 1) / 50)),
                scheduled_datetime: raw.scheduled_datetime,
                train_flight_details: `${raw.train_number || ''} - ${raw.train_name || ''}`.trim(),
                requester_name: raw.requester_name,
                requester_phone: raw.requester_phone,
                notes: `Zone: ${raw.zone_name || '-'} | Branch: ${raw.branch_name || '-'} | Unit: ${raw.unit_number || '-'} | Departure: ${raw.departure_date || '-'}${raw.ticket_attachment_name ? ' | Ticket: ' + raw.ticket_attachment_name : ''}`
            };

            const res = await fetch('/api/operations/pickup-drop-requests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('last_requester_query', payload.requester_phone);
                document.getElementById('track-query-input').value = payload.requester_phone;
                alert(`धन निरंकार जी 🙏\nPickup/Drop Vehicle Request Submitted!\nRequest ID: ${data.request_code}\n\nVehicle will be allocated if available ASAP. Track live status anytime with mobile ${payload.requester_phone}.`);
                e.target.reset();
                closePickupDropModal();
                checkMyRequestStatus();
            } else {
                alert('❌ ' + (data.detail || 'Could not submit request.'));
            }
        }

        async function submitDonateVehicleSewa(e) {
            e.preventDefault();
            const raw = Object.fromEntries(new FormData(e.target).entries());
            const payload = {
                donor_name: raw.donor_name,
                donor_phone: raw.donor_phone,
                branch_name: raw.branch_unit,
                vehicle_reg_number: String(raw.vehicle_reg_number || '').toUpperCase().trim(),
                vehicle_type: `${raw.vehicle_type} [${raw.sewa_phase}]`,
                seating_capacity: parseInt(raw.seating_capacity) || 4,
                driver_included: raw.driver_included === "YES_WITH_DRIVER",
                driver_name_phone: raw.driver_details || "",
                available_from_date: raw.available_from_date,
                available_to_date: raw.available_to_date,
                notes: `Phase: ${raw.sewa_phase} | ${raw.notes || ''}`.trim()
            };

            const res = await fetch('/api/fleet/seva-vehicles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                const box = document.getElementById('donate-vehicle-confirmation');
                box.classList.remove('hidden');
                document.getElementById('donate-vehicle-confirmation-text').textContent =
                    `Sewa Pass ID: ${data.seva_code || 'SEVA-OK'} | Vehicle: ${payload.vehicle_reg_number} (${raw.vehicle_type}) | Phase: ${raw.sewa_phase} | Available: ${payload.available_from_date} to ${payload.available_to_date}.`;
                e.target.reset();
            } else {
                alert('❌ ' + (data.detail || 'Could not register donated vehicle.'));
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
                            <div class="text-slate-500">Group Leader: ${item.requester_name} (${item.requester_phone})</div>
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
                                Vehicle will be allocated if available ASAP.<br>Check back anytime using your Mobile No.
                            </div>
                        `}
                    </div>
                `;
            }).join('');
        }

        window.addEventListener('DOMContentLoaded', () => {
            updateTrainSuggestions('pdm');
            const savedLang = localStorage.getItem('samagam_portal_lang') || 'en';
            const btn = document.querySelector(`.lang-btn[onclick*="'${savedLang}'"]`);
            if (btn) setLanguage(savedLang, btn);

            const lastQ = localStorage.getItem('last_requester_query');
            if (lastQ) {
                document.getElementById('track-query-input').value = lastQ;
                checkMyRequestStatus();
            }
        });
    </script>
</body>
</html>
"""

# ==============================================================================
# 2. APP SHELL JS (Page-Close Guard + 30s Timeout & Retry)
# ==============================================================================
APP_SHELL_JS = r"""(function initJagritiAuthAndShell() {
    const PRODUCTION_ORIGIN = "https://www.samagamtransport.in";
    const isFileOrCapacitor =
        window.location.protocol === "file:" ||
        window.location.protocol === "capacitor:" ||
        window.location.hostname === "localhost";
    const originPrefix = (window.location.protocol === "file:" || window.location.protocol === "capacitor:")
        ? PRODUCTION_ORIGIN
        : "";

    const PUBLIC_PATHS = [
        "/",
        "/welcome.html",
        "/register.html",
        "/download_hub.html",
        "/admin_dashboard.html",
        "/parking_portal.html",
        "/advance_sewa_portal.html",
        "/in_ground_seva_vehicles.html"
    ];
    const currentPath = window.location.pathname || "/";
    const host = (window.location.hostname || "").toLowerCase();
    const isSubdomainPortal = host.startsWith("parking.") || host.startsWith("advancesewa.") || host.startsWith("admin.") || host.startsWith("ground.");
    const isPublicPage = !isFileOrCapacitor && (PUBLIC_PATHS.includes(currentPath) || isSubdomainPortal);

    let _isAuthInFlight = false;
    let _lastPopstateHandledAt = 0;

    function _isRegistrationActive() {
        const otpStep = document.getElementById("m-auth-step-otp");
        const hasOtpStepOpen = Boolean(otpStep && otpStep.style.display !== "none");
        const inputs = Array.from(
            document.querySelectorAll(
                "#samagam-mandatory-auth-overlay input, #driver-auth-screen input, form[id*='register'] input, form[id*='onboard'] input"
            )
        );
        const hasTypedRegistrationData = inputs.some((el) => {
            if (!el || el.type === "hidden" || el.disabled) return false;
            return String(el.value || "").trim().length > 0;
        });
        return Boolean(_isAuthInFlight || hasOtpStepOpen || hasTypedRegistrationData);
    }

    if (isFileOrCapacitor) {
        try {
            window.history.replaceState({ samagamApkRoot: true }, "", window.location.href);
            window.history.pushState({ samagamApkGuard: true }, "", window.location.href);

            window.addEventListener("popstate", function () {
                const now = Date.now();
                if (now - _lastPopstateHandledAt < 350) return;
                _lastPopstateHandledAt = now;

                const overlay = document.getElementById("samagam-mandatory-auth-overlay");
                if (_isRegistrationActive() || (overlay && overlay.style.display !== "none")) {
                    window.history.pushState({ samagamApkGuard: true }, "", window.location.href);
                    return;
                }

                const stepOtp = document.getElementById("m-auth-step-otp");
                const stepPin = document.getElementById("m-auth-step-pin");
                const step1 = document.getElementById("m-auth-step1");

                if (stepOtp && stepOtp.style.display !== "none") {
                    stepOtp.style.display = "none";
                    if (step1) step1.style.display = "flex";
                    window.history.pushState({ samagamApkGuard: true }, "", window.location.href);
                    return;
                }
                if (stepPin && stepPin.style.display !== "none") {
                    stepPin.style.display = "none";
                    if (step1) step1.style.display = "flex";
                    window.history.pushState({ samagamApkGuard: true }, "", window.location.href);
                    return;
                }

                window.history.pushState({ samagamApkGuard: true }, "", window.location.href);
            });
        } catch (_) {}
    }

    window.addEventListener("beforeunload", function (ev) {
        if (_isRegistrationActive()) {
            ev.preventDefault();
            ev.returnValue = "";
            return "";
        }
    }, true);

    document.addEventListener("submit", function (ev) {
        const target = ev.target;
        if (!target || !(target instanceof HTMLFormElement)) return;
        if (
            target.closest("#samagam-mandatory-auth-overlay") ||
            target.closest("#driver-auth-screen") ||
            _isRegistrationActive()
        ) {
            ev.preventDefault();
            ev.stopPropagation();
        }
    }, true);

    const origFetch = window.fetch.bind(window);

    async function fetchWithTimeoutRetry(targetUrl, options = {}, timeoutMs = 25000, maxRetries = 2) {
        let lastErr = null;
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeoutMs);
            try {
                const resp = await origFetch(targetUrl, { ...options, signal: controller.signal });
                clearTimeout(timer);
                if ([502, 503, 504].includes(resp.status) && attempt < maxRetries) {
                    await new Promise((r) => setTimeout(r, 900 * (attempt + 1)));
                    continue;
                }
                return resp;
            } catch (err) {
                clearTimeout(timer);
                lastErr = err;
                if (attempt < maxRetries) {
                    await new Promise((r) => setTimeout(r, 900 * (attempt + 1)));
                    continue;
                }
            }
        }
        throw lastErr || new Error("Network timeout connecting to server.");
    }

    window.fetch = async function (input, init) {
        let url = input;
        if (originPrefix && typeof url === "string" && url.startsWith("/")) {
            url = originPrefix + url;
        }
        const isAuthEndpoint = typeof url === "string" && url.includes("/api/auth/");
        if (isAuthEndpoint) _isAuthInFlight = true;

        init = init || {};
        const headers = new Headers(init.headers || {});
        const tok = localStorage.getItem("samagam_driver_token") || localStorage.getItem("samagam_field_token") || "";
        if (tok && !headers.has("X-Driver-Token")) {
            headers.set("X-Driver-Token", tok);
        }
        init.headers = headers;

        try {
            const resp = await fetchWithTimeoutRetry(url, init, isAuthEndpoint ? 30000 : 18000, isAuthEndpoint ? 2 : 1);
            if (!isPublicPage && !isAuthEndpoint && (resp.status === 401 || resp.status === 403)) {
                const clone = resp.clone();
                try {
                    const body = await clone.json();
                    if (body && body.detail && (body.detail.includes("TERMINATED") || body.detail.includes("Session expired") || body.detail.includes("Missing session"))) {
                        forceLockoutScreen(body.detail);
                    }
                } catch (_) {}
            }
            return resp;
        } finally {
            if (isAuthEndpoint) {
                setTimeout(() => { _isAuthInFlight = false; }, 400);
            }
        }
    };

    function getAppFriendlyTitle() {
        const docTitle = (document.title || "").split("|")[0].trim();
        return docTitle || "Samagam Field App";
    }

    function forceLockoutScreen(reasonMsg) {
        localStorage.removeItem("samagam_driver_token");
        localStorage.removeItem("samagam_field_token");
        localStorage.removeItem("samagam_field_user");
        const strip = document.getElementById("jagriti-top-strip");
        if (strip) strip.remove();
        showCompulsoryLoginModal(reasonMsg || "Please sign in or register to continue.");
    }

    function showCompulsoryLoginModal(alertBannerText) {
        if (document.getElementById("driver-auth-screen") && !alertBannerText.includes("TERMINATED")) {
            return;
        }

        let overlay = document.getElementById("samagam-mandatory-auth-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "samagam-mandatory-auth-overlay";
            overlay.style.cssText = "position:fixed;inset:0;background:rgba(2,6,23,0.97);backdrop-filter:blur(10px);z-index:99999;display:flex;align-items:center;justify-content:center;padding:16px;font-family:system-ui,-apple-system,sans-serif;color:#f8fafc;overflow-y:auto;";
            document.body.appendChild(overlay);
        }

        const appTitle = getAppFriendlyTitle();
        const backFooterHtml = isFileOrCapacitor
            ? `<button id="m-apk-reset-login" style="background:none;border:none;color:#38bdf8;font-size:12px;font-weight:700;text-decoration:underline;cursor:pointer;">↻ Reset Login / New Sevadar Registration</button>`
            : `<a href="/" style="color:#94a3b8;font-size:11px;text-decoration:underline;">← Back to Public Welcome Portal</a>`;

        overlay.innerHTML = `
            <div style="max-width:410px;width:100%;background:#0f172a;border:1px solid #334155;border-radius:24px;padding:24px;box-shadow:0 25px 50px rgba(0,0,0,0.6);margin:auto;">
                <div style="text-align:center;margin-bottom:16px;">
                    <div style="font-size:32px;">🔐</div>
                    <h2 style="font-size:18px;font-weight:800;color:#ffffff;margin:4px 0;">${appTitle}</h2>
                    <p style="font-size:12px;color:#6ee7b7;font-weight:700;margin:0;">Sevadar Sign-In & First-Time Registration</p>
                </div>

                ${alertBannerText ? `<div style="background:#450a0a;border:1px solid #dc2626;color:#fecaca;font-size:12px;font-weight:700;padding:10px 12px;border-radius:12px;margin-bottom:14px;">${alertBannerText}</div>` : ""}

                <div id="m-auth-step1" style="display:flex;flex-direction:column;gap:10px;">
                    <label style="font-size:11px;color:#94a3b8;font-weight:700;">Enter Registered Mobile (Login) or Email (New Registration):</label>
                    <input type="text" id="m-auth-ident" placeholder="10-Digit Mobile or Email Address" style="width:100%;box-sizing:border-box;background:#020617;border:1px solid #475569;border-radius:12px;padding:12px;color:#ffffff;font-size:14px;font-weight:600;">
                    <button id="m-btn-continue" style="width:100%;background:#059669;color:#ffffff;border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:800;cursor:pointer;">Continue to Login / Register →</button>
                </div>

                <div id="m-auth-step-pin" style="display:none;flex-direction:column;gap:10px;">
                    <div id="m-pin-label" style="font-size:12px;color:#6ee7b7;font-weight:700;">Enter your 4-digit PIN:</div>
                    <input type="password" id="m-auth-pin" maxlength="4" inputmode="numeric" placeholder="••••" style="width:100%;box-sizing:border-box;text-align:center;letter-spacing:0.5em;background:#020617;border:1px solid #475569;border-radius:12px;padding:12px;color:#ffffff;font-size:20px;font-weight:800;">
                    <button id="m-btn-pin-verify" style="width:100%;background:#059669;color:#ffffff;border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:800;cursor:pointer;">Verify & Open App</button>
                    <button id="m-btn-back1" style="background:none;border:none;color:#94a3b8;font-size:12px;text-decoration:underline;cursor:pointer;">← Back / Change Mobile or Email</button>
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
                    <button id="m-btn-back2" style="background:none;border:none;color:#94a3b8;font-size:12px;text-decoration:underline;cursor:pointer;">← Back</button>
                </div>

                <div id="m-auth-err" style="color:#fb7185;font-size:12px;font-weight:700;text-align:center;margin-top:10px;"></div>
                <div style="text-align:center;margin-top:14px;border-top:1px solid #1e293b;padding-top:10px;">
                    ${backFooterHtml}
                </div>
            </div>
        `;

        const errBox = document.getElementById("m-auth-err");
        const goBackToStep1 = () => {
            document.getElementById("m-auth-step1").style.display = "flex";
            document.getElementById("m-auth-step-pin").style.display = "none";
            document.getElementById("m-auth-step-otp").style.display = "none";
            errBox.textContent = "";
        };

        document.getElementById("m-btn-back1").onclick = goBackToStep1;
        document.getElementById("m-btn-back2").onclick = goBackToStep1;
        const resetApkBtn = document.getElementById("m-apk-reset-login");
        if (resetApkBtn) resetApkBtn.onclick = goBackToStep1;

        document.getElementById("m-btn-continue").onclick = async () => {
            const btn = document.getElementById("m-btn-continue");
            const ident = document.getElementById("m-auth-ident").value.trim();
            errBox.textContent = "";
            if (!ident) { errBox.textContent = "Enter mobile number or email."; return; }
            btn.disabled = true;
            btn.textContent = "⏳ Connecting to Server...";
            try {
                const res = await fetchWithTimeoutRetry(originPrefix + "/api/auth/otp/send", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ identifier: ident })
                }, 30000, 2);
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
            } catch (_) {
                errBox.textContent = "Server waking up / slow network. Please tap Continue again.";
            } finally {
                btn.disabled = false;
                btn.textContent = "Continue to Login / Register →";
            }
        };

        document.getElementById("m-btn-pin-verify").onclick = async () => {
            const btn = document.getElementById("m-btn-pin-verify");
            const ident = document.getElementById("m-auth-ident").value.trim();
            const pin = document.getElementById("m-auth-pin").value.trim();
            errBox.textContent = "";
            btn.disabled = true;
            btn.textContent = "⏳ Verifying PIN...";
            try {
                const res = await fetchWithTimeoutRetry(originPrefix + "/api/auth/pin/verify", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ identifier: ident, pin })
                }, 30000, 2);
                const data = await res.json();
                if (!res.ok) { errBox.textContent = data.detail || "Incorrect PIN."; return; }
                localStorage.setItem("samagam_driver_token", data.token);
                localStorage.setItem("samagam_field_token", data.token);
                localStorage.setItem("samagam_field_user", JSON.stringify(data.driver));
                overlay.remove();
                renderJagritiTopBar(data.driver);
            } catch (_) {
                errBox.textContent = "Network timeout during PIN check. Please tap Verify again.";
            } finally {
                btn.disabled = false;
                btn.textContent = "Verify & Open App";
            }
        };

        document.getElementById("m-btn-otp-verify").onclick = async () => {
            const btn = document.getElementById("m-btn-otp-verify");
            const ident = document.getElementById("m-auth-ident").value.trim();
            const fullName = document.getElementById("m-auth-name").value.trim();
            const branchName = document.getElementById("m-auth-branch").value.trim();
            const unitNo = document.getElementById("m-auth-unit").value.trim();
            const phone = document.getElementById("m-auth-phone").value.trim();

            if (!fullName || !branchName || !unitNo || !phone) {
                errBox.textContent = "Please fill Name, Branch Name, Unit No., and Mobile Number.";
                return;
            }

            errBox.textContent = "";
            btn.disabled = true;
            btn.textContent = "⏳ Completing Registration...";
            try {
                const res = await fetchWithTimeoutRetry(originPrefix + "/api/auth/otp/verify", {
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
                }, 30000, 2);
                const data = await res.json();
                if (!res.ok) { errBox.textContent = data.detail || "OTP verification failed."; return; }
                localStorage.setItem("samagam_driver_token", data.token);
                localStorage.setItem("samagam_field_token", data.token);
                localStorage.setItem("samagam_field_user", JSON.stringify(data.driver));
                overlay.remove();
                renderJagritiTopBar(data.driver);
            } catch (_) {
                errBox.textContent = "Connection timed out while saving registration. Tap Verify again.";
            } finally {
                btn.disabled = false;
                btn.textContent = "Verify OTP & Complete Sign-Up";
            }
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
            await fetch(originPrefix + "/api/auth/driver-logout", { method: "POST" }).catch(() => {});
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
"""


def write_utf8(rel_path: str, content: str):
    full_path = os.path.join(TARGET_DIR, rel_path.replace("/", os.sep))
    parent = os.path.dirname(full_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Updated: {rel_path}")


def copy_if_exists(src_rel: str, dst_rel: str):
    src = os.path.join(TARGET_DIR, src_rel.replace("/", os.sep))
    dst = os.path.join(TARGET_DIR, dst_rel.replace("/", os.sep))
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f"✅ Copied: {src_rel} -> {dst_rel}")


def sync_all_to_root_folder():
    root_dir = os.path.join(TARGET_DIR, "root")
    os.makedirs(root_dir, exist_ok=True)
    for fname in [
        "welcome.html",
        "in_ground_seva_vehicles.html",
        "admin_dashboard.html",
        "samagam_master_topology_and_operations.html",
        "parking_portal.html",
        "advance_sewa_portal.html",
        "download_hub.html",
    ]:
        src = os.path.join(TARGET_DIR, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(root_dir, fname))

    static_src = os.path.join(TARGET_DIR, "static")
    static_dst = os.path.join(root_dir, "static")
    if os.path.isdir(static_src):
        os.makedirs(static_dst, exist_ok=True)
        for sfile in os.listdir(static_src):
            sp = os.path.join(static_src, sfile)
            if os.path.isfile(sp):
                shutil.copy2(sp, os.path.join(static_dst, sfile))
    print("✅ Synced HTML & static assets into ./root/")


def copy_downloaded_logo_if_found():
    static_dir = os.path.join(TARGET_DIR, "static")
    os.makedirs(static_dir, exist_ok=True)
    target_png = os.path.join(static_dir, "jagriti.png")
    if os.path.isfile(target_png):
        return
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    for pattern in ["*jagriti*.png", "*o9vs4eo9vs4eo9vs*.png", "*1001094584*.png"]:
        matches = glob.glob(os.path.join(downloads, pattern))
        if matches:
            matches.sort(key=os.path.getmtime, reverse=True)
            shutil.copy2(matches[0], target_png)
            print(f"✅ Copied logo image from Downloads -> static/jagriti.png")
            return


def main():
    print("=" * 80)
    print(f"🚀 APPLYING ALL UPDATES FROM TODAY IN ONE GO: {TARGET_DIR}")
    print("=" * 80)

    # 1. Write welcome.html & static/samagam_app_shell.js
    write_utf8("welcome.html", WELCOME_HTML)
    write_utf8("static/samagam_app_shell.js", APP_SHELL_JS)

    # 2. Copy any downloaded artifacts from .py files / Downloads if saved there
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    artifact_map = [
        ("Route ground.samagamtransport.in Subdomain in app_main.py", "app/main.py"),
        ("Ground Service Subdomain Portal*.html", "in_ground_seva_vehicles.html"),
        ("Communication Link & Master Contact Directory*.html", "samagam_master_topology_and_operations.html"),
        ("Admin Control Room with Ground Dept Requisition Allocation & Live Feeds*.html", "admin_dashboard.html"),
        ("Add Google IAP JWT Verification & Google Group Role Mapping to Auth Router*.py", "app/routers/auth.py"),
        ("Add Master Contact Directory CRUD & Bulk Import Endpoints*.py", "app/routers/operations.py"),
        ("Add Admin SQL Query Execution Endpoint to Reports Router*.py", "app/routers/reports.py"),
        ("GCP IAM Service Account, Secret Manager & IAP Group Setup Script*", "setup_gcp_iam_secrets.sh"),
    ]
    for pattern, dest in artifact_map:
        for search_dir in [downloads, os.path.join(TARGET_DIR, ".py files"), TARGET_DIR]:
            hits = glob.glob(os.path.join(search_dir, pattern))
            if hits:
                hits.sort(key=os.path.getmtime, reverse=True)
                shutil.copy2(hits[0], os.path.join(TARGET_DIR, dest.replace("/", os.sep)))
                print(f"✅ Synced artifact -> {dest}")
                break

    copy_downloaded_logo_if_found()
    sync_all_to_root_folder()

    # 3. Git add, commit & push
    try:
        subprocess.run(["git", "add", "."], cwd=TARGET_DIR, check=True)
        msg = f"All-in-one deployment of today's updates ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC)"
        res = subprocess.run(["git", "commit", "-m", msg], cwd=TARGET_DIR, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Git committed: {msg}")
        else:
            print("ℹ️ Git working tree clean; pushing latest HEAD.")
        subprocess.run(["git", "push", "origin", "main"], cwd=TARGET_DIR, check=True)
        print("✅ Pushed all updates to GitHub (origin/main)!")
    except Exception as exc:
        print(f"⚠️ Git notice: {exc}")

    print("\n" + "=" * 80)
    print("🎉 ALL UPDATES APPLIED & PUSHED!")
    print("Run this single command in Google Cloud Shell to deploy live:")
    print("  cd ~/Samagamtransport_v1 && git fetch --all && git reset --hard origin/main && gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080 --timeout=300")
    print("=" * 80)


if __name__ == "__main__":
    main()