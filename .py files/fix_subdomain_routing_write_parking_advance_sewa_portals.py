"""
Samagam Transport Platform — Subdomain Routing & Portal Installer
Writes parking_portal.html and advance_sewa_portal.html into C:\narendra\SamagamtransportV1
and updates app/main.py so parking.samagamtransport.in and advancesewa.samagamtransport.in
inspect X-Forwarded-Host, Host, and Referer headers and serve their respective portals
instead of falling back to welcome.html.

Run inside C:\narendra\SamagamtransportV1:
    python fix_subdomain_routing.py
"""

import os
import re

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

PARKING_PORTAL_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Samagam Devotee Parking Portal | parking.samagamtransport.in</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Noto+Sans+Devanagari:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            background: radial-gradient(circle at top, #ecfdf5 0%, #f1f5f9 55%, #e2e8f0 100%);
            font-family: 'Inter', 'Noto Sans Devanagari', sans-serif;
            color: #0f172a;
        }
        .tab-btn.active {
            background-color: #064e3b;
            color: #ffffff;
            box-shadow: 0 8px 20px rgba(6, 78, 59, 0.25);
        }
        @media print {
            body * { visibility: hidden; }
            #printable-windshield-pass, #printable-windshield-pass * { visibility: visible; }
            #printable-windshield-pass {
                position: fixed;
                left: 0;
                top: 0;
                width: 100%;
                border: 3px solid #000 !important;
                box-shadow: none !important;
                background: #ffffff !important;
                color: #000000 !important;
            }
            .no-print { display: none !important; }
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">

    <header class="bg-emerald-950 text-white shadow-lg sticky top-0 z-40">
        <div class="max-w-5xl mx-auto px-4 py-3.5 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-2xl bg-amber-400 text-slate-950 flex items-center justify-center font-black text-xl shadow">
                    🅿️
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="font-extrabold text-base sm:text-lg tracking-wide">SAMAGAM PARKING & GATE QR PORTAL</h1>
                        <span class="hidden sm:inline-block text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-800 text-emerald-200">parking.samagamtransport.in</span>
                    </div>
                    <p class="text-xs text-emerald-200">60th Maharashtra Annual Nirankari Sant Samagam • Kharghar, Navi Mumbai</p>
                </div>
            </div>
            <div class="flex items-center gap-2 text-xs font-bold">
                <a href="https://www.samagamtransport.in" class="bg-emerald-900 hover:bg-emerald-800 px-3 py-2 rounded-xl border border-emerald-700">🚌 Main Transport Portal</a>
            </div>
        </div>
    </header>

    <div class="max-w-5xl mx-auto w-full px-4 pt-6">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 bg-white p-2 rounded-2xl shadow-sm border border-slate-200 text-xs sm:text-sm font-extrabold">
            <button onclick="switchParkingTab('register', this)" class="tab-btn active py-3 px-4 rounded-xl transition flex items-center justify-center gap-2">
                <span>🎫</span> 1. Register Vehicle & Print Windshield QR
            </button>
            <button onclick="switchParkingTab('retrieve', this)" class="tab-btn py-3 px-4 rounded-xl text-slate-700 hover:bg-slate-100 transition flex items-center justify-center gap-2">
                <span>🔍</span> 2. Retrieve / Reprint My QR Pass
            </button>
            <button onclick="switchParkingTab('scanner', this)" class="tab-btn py-3 px-4 rounded-xl text-slate-700 hover:bg-slate-100 transition flex items-center justify-center gap-2">
                <span>📷</span> 3. Gate Entry & Exit QR Matcher
            </button>
        </div>
    </div>

    <main class="max-w-5xl mx-auto w-full px-4 py-6 flex-1">
        <!-- TAB 1 -->
        <section id="tab-register" class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div class="lg:col-span-6 bg-white rounded-3xl p-6 sm:p-7 border border-emerald-200 shadow-lg space-y-4">
                <div class="border-b pb-3">
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-900">
                        Step 1 • Devotee Self-Registration
                    </span>
                    <h2 class="text-xl font-extrabold text-slate-900 mt-1">Register Vehicle for Samagam Parking</h2>
                    <p class="text-xs text-slate-500">Fill in your details below. Your unique QR code will be sent to your Email/WhatsApp—take a printout and paste it clearly on your vehicle windshield.</p>
                </div>

                <form id="parking-reg-form" onsubmit="registerParkingVehicle(event)" class="space-y-3 text-xs sm:text-sm">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Devotee / Owner Full Name *</label>
                            <input type="text" name="owner_name" required placeholder="e.g. Sant Rajesh Sharma Ji" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">WhatsApp Mobile Number *</label>
                            <input type="tel" name="owner_phone" required maxlength="10" inputmode="numeric" placeholder="10-Digit Mobile" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Email Address (For QR Delivery) *</label>
                            <input type="email" name="owner_email" required placeholder="name@example.com" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Vehicle Number Plate *</label>
                            <input type="text" name="vehicle_reg_number" required placeholder="MH-04-AB-1234" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 uppercase font-black text-base tracking-wide">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Vehicle Type *</label>
                            <select name="vehicle_category" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                                <option value="Car / Sedan / SUV">Car / Sedan / SUV</option>
                                <option value="Two-Wheeler / Bike / Scooter">Two-Wheeler / Bike</option>
                                <option value="Tempo Traveller / Van / Jeep">Tempo Traveller / Van / Jeep</option>
                                <option value="Private / Branch Bus">Private / Branch Bus</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Vehicle Model & Color *</label>
                            <input type="text" name="vehicle_color_model" required placeholder="e.g. White Swift Dzire" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Branch Name *</label>
                            <input type="text" name="branch_name" required placeholder="e.g. Panvel / Thane / Pune" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Zone Name / Number *</label>
                            <input type="text" name="zone_name" required placeholder="e.g. Zone 3 / Mumbai Zone" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 mb-1">Preferred Samagam Parking Gate</label>
                        <select name="parking_zone" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                            <option value="Parking Zone P1 (Gate 1)">Parking Zone P1 (Gate 1 — Cars & SUVs)</option>
                            <option value="Parking Zone P2 (Gate 2)">Parking Zone P2 (Gate 2 — Cars & Vans)</option>
                            <option value="Two-Wheeler Bay W1 (Gate 3)">Two-Wheeler Bay W1 (Gate 3 — Bikes)</option>
                            <option value="Bus & Heavy Fleet Bay B1 (Gate 4)">Bus & Heavy Fleet Bay B1 (Gate 4)</option>
                        </select>
                    </div>

                    <button type="submit" class="w-full bg-emerald-800 hover:bg-emerald-700 text-white font-extrabold py-4 rounded-2xl text-sm sm:text-base shadow-xl transition">
                        🎫 Generate Windshield QR Sticker & Send Pass
                    </button>
                </form>
            </div>

            <div class="lg:col-span-6 space-y-4">
                <div id="printable-windshield-pass" class="bg-white rounded-3xl p-6 border-4 border-emerald-900 shadow-xl space-y-4">
                    <div class="bg-emerald-950 text-white rounded-2xl p-4 text-center space-y-0.5">
                        <div class="text-[11px] font-bold uppercase tracking-widest text-amber-300">धन निरंकार जी 🙏 • SANT NIRANKARI MANDAL</div>
                        <div class="text-lg font-black tracking-wide">OFFICIAL VEHICLE PARKING PASS</div>
                        <div class="text-[11px] text-emerald-200">60th Maharashtra Annual Sant Samagam • Kharghar, Navi Mumbai</div>
                    </div>

                    <div class="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50 p-4 rounded-2xl border-2 border-dashed border-slate-300">
                        <div class="text-center shrink-0">
                            <img id="qr-sticker-img" src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=SAMAGAM-PARKING-SAMPLE" alt="Vehicle Parking QR" class="w-44 h-44 mx-auto border-4 border-white shadow-md rounded-xl bg-white p-1">
                            <div class="text-[10px] font-extrabold uppercase text-slate-600 mt-1.5">Scan at Entry & Exit Gate</div>
                        </div>

                        <div class="flex-1 space-y-2 text-xs w-full">
                            <div class="bg-amber-100 border border-amber-400 rounded-xl p-2.5 text-center">
                                <span class="text-[10px] font-bold uppercase text-amber-900 block">Parking Pass Token</span>
                                <span id="pass-token-display" class="text-xl font-black text-slate-950 tracking-wider">PKG-SAMPLE</span>
                            </div>

                            <div class="space-y-1 text-slate-800">
                                <div><span class="text-slate-500 font-bold">Vehicle No:</span> <strong id="pass-plate-display" class="text-base font-black text-emerald-950">MH-04-AB-1234</strong></div>
                                <div><span class="text-slate-500 font-bold">Vehicle:</span> <span id="pass-veh-display" class="font-bold">Car / Sedan / SUV</span></div>
                                <div><span class="text-slate-500 font-bold">Owner:</span> <span id="pass-owner-display" class="font-bold">Register on left to generate</span></div>
                                <div><span class="text-slate-500 font-bold">Branch & Zone:</span> <span id="pass-branch-display" class="font-bold">--</span></div>
                                <div><span class="text-slate-500 font-bold">Assigned Bay:</span> <span id="pass-zone-display" class="font-bold text-emerald-800">Parking Zone P1</span></div>
                            </div>
                        </div>
                    </div>

                    <div class="bg-rose-50 border-2 border-rose-300 rounded-2xl p-3.5 flex flex-wrap justify-between items-center gap-2">
                        <div>
                            <div class="text-xs font-extrabold text-rose-950">🔐 OWNER EXIT VERIFICATION PIN (Keep With Owner)</div>
                            <div class="text-[11px] text-rose-800">Paste QR printout on windshield. Show this PIN + your copy at Exit Gate.</div>
                        </div>
                        <div class="text-2xl font-black tracking-widest bg-white border-2 border-rose-500 text-rose-950 px-4 py-1 rounded-xl" id="pass-pin-display">
                            ****
                        </div>
                    </div>

                    <div class="text-center text-[11px] font-bold text-slate-600 border-t pt-2.5">
                        📌 INSTRUCTION: Take a printout of this QR pass and paste it visibly inside your front windshield before arriving at Samagam Gate.
                    </div>
                </div>

                <div id="pass-share-actions" class="hidden grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm font-extrabold">
                    <button onclick="window.print()" class="bg-slate-900 hover:bg-slate-800 text-white py-3.5 px-4 rounded-2xl shadow-lg flex items-center justify-center gap-2">
                        <span>🖨️ Print Windshield QR Sticker</span>
                    </button>
                    <a id="whatsapp-share-btn" href="#" target="_blank" rel="noopener noreferrer" class="bg-emerald-600 hover:bg-emerald-500 text-white py-3.5 px-4 rounded-2xl shadow-lg flex items-center justify-center gap-2">
                        <span>💬 Send QR Pass to WhatsApp</span>
                    </a>
                </div>
            </div>
        </section>

        <!-- TAB 2 -->
        <section id="tab-retrieve" class="hidden max-w-2xl mx-auto bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-lg space-y-4">
            <h2 class="text-xl font-extrabold text-slate-900">🔍 Retrieve & Reprint Your Parking QR Sticker</h2>
            <p class="text-xs text-slate-500">Enter your registered <strong>10-Digit Mobile Number</strong>, <strong>Vehicle Number Plate</strong>, or <strong>Token (PKG-XXXX)</strong> to view, print, or share your windshield QR pass again.</p>
            <div class="flex gap-2">
                <input type="text" id="lookup-parking-input" placeholder="e.g. MH-04-AB-1234 or 98XXXXXXXX or PKG-1234" class="flex-1 border border-slate-300 rounded-2xl px-4 py-3 text-sm font-bold">
                <button onclick="lookupExistingParkingPass()" class="bg-emerald-800 hover:bg-emerald-700 text-white font-extrabold px-6 py-3 rounded-2xl text-sm">
                    Find Pass
                </button>
            </div>
            <div id="lookup-parking-results" class="space-y-3 text-xs"></div>
        </section>

        <!-- TAB 3 -->
        <section id="tab-scanner" class="hidden grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div class="lg:col-span-6 bg-slate-900 text-white rounded-3xl p-6 border border-slate-800 shadow-xl space-y-4">
                <div class="border-b border-slate-800 pb-3">
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-400 text-slate-950">
                        Gate Security & Volunteers
                    </span>
                    <h2 class="text-lg font-extrabold mt-1.5">📷 Gate Entry & Exit QR Matcher</h2>
                    <p class="text-xs text-slate-400">Scan the QR pasted on the vehicle windshield at Entry Gate, and match the same QR + Owner Exit PIN at Exit Gate.</p>
                </div>

                <div class="grid grid-cols-2 gap-2.5 text-xs">
                    <div>
                        <label class="block text-slate-400 font-bold mb-1">Gate Mode *</label>
                        <select id="gate-scan-direction" onchange="toggleExitPinInput()" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 font-extrabold text-white">
                            <option value="ENTRY">🟢 INWARD ENTRY GATE</option>
                            <option value="EXIT">🔵 OUTWARD EXIT GATE</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-slate-400 font-bold mb-1">Gate Number *</label>
                        <select id="gate-scan-name" class="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 font-bold text-white">
                            <option value="Gate 1 (Zone P1)">Gate 1 (Zone P1)</option>
                            <option value="Gate 2 (Zone P2)">Gate 2 (Zone P2)</option>
                            <option value="Gate 3 (2-Wheeler Bay)">Gate 3 (2-Wheeler Bay)</option>
                            <option value="Gate 4 (Bus Bay)">Gate 4 (Bus Bay)</option>
                        </select>
                    </div>
                </div>

                <div id="exit-owner-pin-box" class="hidden bg-amber-950/60 border border-amber-500/60 rounded-2xl p-3.5 space-y-1.5">
                    <label class="block text-xs font-extrabold text-amber-300">🔐 Owner Exit Verification PIN (From Owner's Copy / SMS) *</label>
                    <input type="password" id="gate-owner-exit-pin" maxlength="4" inputmode="numeric" placeholder="Enter Owner 4-Digit Exit PIN" class="w-full bg-slate-950 border border-amber-400 rounded-xl px-3 py-2.5 text-center text-lg font-black tracking-widest text-white">
                </div>

                <div class="bg-slate-950 border border-slate-800 rounded-2xl p-3 space-y-2.5 text-center">
                    <div id="qr-camera-reader" class="rounded-xl overflow-hidden mx-auto max-w-xs"></div>
                    <div class="flex gap-2 justify-center text-xs font-bold">
                        <button onclick="startQrCameraScanner()" class="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-xl">📷 Start Camera Scan</button>
                        <button onclick="stopQrCameraScanner()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-2 rounded-xl">Stop Camera</button>
                    </div>
                </div>

                <div class="space-y-2 pt-2 border-t border-slate-800">
                    <label class="block text-xs font-bold text-slate-400">Or Scan / Type Windshield QR Token or Plate No.:</label>
                    <div class="flex gap-2">
                        <input type="text" id="manual-qr-code-input" placeholder="e.g. PKG-4821 or MH-04-AB-1234" class="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm font-extrabold uppercase text-white">
                        <button onclick="processGateQrScan()" class="bg-amber-400 hover:bg-amber-300 text-slate-950 font-extrabold px-5 py-2.5 rounded-xl text-xs">
                            Verify QR
                        </button>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-6 space-y-4">
                <div id="gate-scan-result-card" class="bg-white rounded-3xl p-6 border-2 border-slate-200 shadow-lg text-center space-y-2">
                    <div class="text-3xl">🛡️</div>
                    <h3 class="text-base font-extrabold text-slate-800">Ready to Scan Windshield QR Sticker</h3>
                    <p class="text-xs text-slate-500">Scan a vehicle's windshield QR pass on the left to verify Entry or match Owner Exit PIN at Exit Gate.</p>
                </div>

                <div class="bg-white rounded-3xl p-5 border border-slate-200 shadow-sm space-y-2.5">
                    <div class="flex justify-between items-center">
                        <h4 class="font-extrabold text-xs uppercase text-slate-700">Recent Gate QR Verifications</h4>
                        <button onclick="loadRecentGatePasses()" class="text-xs font-bold text-emerald-700">↻ Refresh</button>
                    </div>
                    <div id="recent-gate-passes-list" class="space-y-2 text-xs max-h-80 overflow-y-auto"></div>
                </div>
            </div>
        </section>
    </main>

    <footer class="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        धन निरंकार जी 🙏 • Samagam Dedicated Parking Control • parking.samagamtransport.in
    </footer>

    <script>
        let html5QrScanner = null;

        function switchParkingTab(tab, btn) {
            ['register', 'retrieve', 'scanner'].forEach(t => {
                document.getElementById('tab-' + t).classList.add('hidden');
            });
            document.getElementById('tab-' + tab).classList.remove('hidden');
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.remove('active');
                b.classList.add('text-slate-700');
            });
            btn.classList.add('active');
            btn.classList.remove('text-slate-700');
            if (tab === 'scanner') loadRecentGatePasses();
        }

        function toggleExitPinInput() {
            const dir = document.getElementById('gate-scan-direction').value;
            const box = document.getElementById('exit-owner-pin-box');
            if (dir === 'EXIT') box.classList.remove('hidden');
            else box.classList.add('hidden');
        }

        function renderWindshieldPass(passData) {
            const qrPayload = encodeURIComponent(`SAMAGAM-PKG|${passData.parking_token}|${passData.vehicle_reg_number}`);
            document.getElementById('qr-sticker-img').src = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${qrPayload}`;
            document.getElementById('pass-token-display').textContent = passData.parking_token;
            document.getElementById('pass-plate-display').textContent = passData.vehicle_reg_number;
            document.getElementById('pass-veh-display').textContent = `${passData.vehicle_category} (${passData.vehicle_color_model || ''})`;
            document.getElementById('pass-owner-display').textContent = `${passData.owner_name} (${passData.owner_phone})`;
            document.getElementById('pass-branch-display').textContent = `${passData.branch_name || '-'} • ${passData.zone_name || '-'}`;
            document.getElementById('pass-zone-display').textContent = passData.parking_zone;
            document.getElementById('pass-pin-display').textContent = passData.exit_pin || '****';

            const waText = encodeURIComponent(
                `धन निरंकार जी 🙏\n*Samagam Official Parking QR Pass*\n` +
                `Token: *${passData.parking_token}*\n` +
                `Vehicle: *${passData.vehicle_reg_number}* (${passData.vehicle_category})\n` +
                `Owner: ${passData.owner_name}\n` +
                `Branch & Zone: ${passData.branch_name} / ${passData.zone_name}\n` +
                `Parking Bay: ${passData.parking_zone}\n` +
                `Secret Exit PIN (Keep Private): *${passData.exit_pin}*\n\n` +
                `📌 Print & paste your QR sticker on your windshield from: https://parking.samagamtransport.in`
            );
            const cleanPhone = (passData.owner_phone || '').replace(/\D/g, '');
            const waPhone = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone;
            document.getElementById('whatsapp-share-btn').href = `https://wa.me/${waPhone}?text=${waText}`;
            document.getElementById('pass-share-actions').classList.remove('hidden');
        }

        async function registerParkingVehicle(e) {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            const res = await fetch('/api/fleet/parking-passes/register-qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                renderWindshieldPass(data);
                alert(`धन निरंकार जी 🙏\nParking QR Sticker Generated!\nToken: ${data.parking_token}\nSecret Exit PIN: ${data.exit_pin}\n\nSent to ${payload.owner_email}. Please print and paste the QR pass on your vehicle windshield!`);
            } else {
                alert('❌ ' + (data.detail || 'Could not generate parking QR pass.'));
            }
        }

        async function lookupExistingParkingPass() {
            const q = document.getElementById('lookup-parking-input').value.trim();
            if (!q) return;
            const res = await fetch(`/api/fleet/parking-passes?query=${encodeURIComponent(q)}&status=ALL`);
            const list = await res.json();
            const box = document.getElementById('lookup-parking-results');
            if (!list.length) {
                box.innerHTML = '<div class="p-3 bg-rose-50 text-rose-700 rounded-xl font-bold">No parking registration found for that query.</div>';
                return;
            }
            box.innerHTML = list.map(p => `
                <div class="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex flex-wrap justify-between items-center gap-3">
                    <div>
                        <div class="font-black text-sm text-emerald-950">${p.parking_token} • ${p.vehicle_reg_number}</div>
                        <div class="text-slate-700 font-semibold">${p.owner_name} (${p.owner_phone}) • ${p.branch_name || ''} / ${p.zone_name || ''}</div>
                        <div class="text-slate-500">Status: <strong>${p.status}</strong> • ${p.parking_zone}</div>
                    </div>
                    <button onclick='loadIntoPrintCard(${JSON.stringify(p)})' class="bg-emerald-800 text-white font-bold px-4 py-2 rounded-xl">
                        🖨️ Load & Print QR
                    </button>
                </div>
            `).join('');
        }

        function loadIntoPrintCard(passObj) {
            renderWindshieldPass(passObj);
            const regBtn = document.querySelector(".tab-btn[onclick*='register']");
            switchParkingTab('register', regBtn);
        }

        function startQrCameraScanner() {
            if (html5QrScanner) return;
            html5QrScanner = new Html5Qrcode("qr-camera-reader");
            html5QrScanner.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: { width: 220, height: 220 } },
                (decodedText) => {
                    document.getElementById('manual-qr-code-input').value = decodedText;
                    processGateQrScan();
                },
                () => {}
            ).catch(() => {
                alert("Camera permission denied or unavailable. Use manual token/plate input below.");
            });
        }

        function stopQrCameraScanner() {
            if (html5QrScanner) {
                html5QrScanner.stop().then(() => {
                    html5QrScanner.clear();
                    html5QrScanner = null;
                }).catch(() => {});
            }
        }

        async function processGateQrScan() {
            const rawCode = document.getElementById('manual-qr-code-input').value.trim();
            const direction = document.getElementById('gate-scan-direction').value;
            const gateName = document.getElementById('gate-scan-name').value;
            const exitPin = document.getElementById('gate-owner-exit-pin').value.trim();

            if (!rawCode) {
                alert("Scan or enter the QR code / Vehicle Plate first.");
                return;
            }

            const res = await fetch('/api/fleet/parking-passes/scan-qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    qr_data: rawCode,
                    gate_direction: direction,
                    gate_name: gateName,
                    owner_exit_pin: exitPin
                })
            });
            const data = await res.json();
            const card = document.getElementById('gate-scan-result-card');

            if (res.ok) {
                card.className = "bg-emerald-50 rounded-3xl p-6 border-4 border-emerald-600 shadow-xl text-center space-y-2";
                card.innerHTML = `
                    <div class="text-4xl">✅</div>
                    <div class="text-xs font-extrabold uppercase tracking-wider text-emerald-800">${data.action_status}</div>
                    <h3 class="text-xl font-black text-slate-950">${data.vehicle_reg_number} (${data.parking_token})</h3>
                    <p class="text-xs font-bold text-slate-700">Owner: ${data.owner_name} (${data.owner_phone}) • Branch: ${data.branch_name || '-'} / ${data.zone_name || '-'}</p>
                    <p class="text-xs text-emerald-900 font-semibold">${data.message}</p>
                `;
                document.getElementById('gate-owner-exit-pin').value = '';
                loadRecentGatePasses();
            } else {
                card.className = "bg-rose-50 rounded-3xl p-6 border-4 border-rose-600 shadow-xl text-center space-y-2";
                card.innerHTML = `
                    <div class="text-4xl">🚨</div>
                    <div class="text-xs font-extrabold uppercase tracking-wider text-rose-800">GATE VERIFICATION FAILED / HOLD</div>
                    <h3 class="text-lg font-black text-rose-950">${data.detail || 'QR / Owner Mismatch'}</h3>
                `;
            }
        }

        async function loadRecentGatePasses() {
            const res = await fetch('/api/fleet/parking-passes?status=ALL');
            if (!res.ok) return;
            const list = await res.json();
            document.getElementById('recent-gate-passes-list').innerHTML = list.slice(0, 15).map(p => `
                <div class="p-3 bg-slate-50 border rounded-xl flex justify-between items-center">
                    <div>
                        <span class="font-extrabold text-slate-900">${p.parking_token} • ${p.vehicle_reg_number}</span>
                        <div class="text-slate-500">${p.owner_name} • ${p.branch_name || ''} (${p.zone_name || ''})</div>
                    </div>
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                        p.status === 'PARKED_INSIDE' ? 'bg-emerald-100 text-emerald-800' :
                        p.status === 'EXITED_VERIFIED' ? 'bg-blue-100 text-blue-800' :
                        p.status === 'PRE_REGISTERED' ? 'bg-amber-100 text-amber-900' : 'bg-rose-100 text-rose-800'
                    }">${p.status}</span>
                </div>
            `).join('');
        }

        window.addEventListener('DOMContentLoaded', () => {
            const params = new URLSearchParams(window.location.search);
            const tokenParam = params.get('token');
            if (tokenParam) {
                document.getElementById('lookup-parking-input').value = tokenParam;
                lookupExistingParkingPass();
            }
        });
    </script>
</body>
</html>
'''

ADVANCE_SEWA_PORTAL_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Samagam Advance Sewa Transport Portal | advancesewa.samagamtransport.in</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=Noto+Sans+Devanagari:wght@500;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            background: radial-gradient(circle at top, #fffbeb 0%, #fef3c7 35%, #f1f5f9 100%);
            font-family: 'Inter', 'Noto Sans Devanagari', sans-serif;
            color: #0f172a;
        }
        .lang-btn.active {
            background-color: #92400e;
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(146, 64, 14, 0.25);
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between">

    <header class="bg-amber-950 text-white shadow-lg sticky top-0 z-40">
        <div class="max-w-5xl mx-auto px-4 py-3.5 flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-2xl bg-amber-400 text-slate-950 flex items-center justify-center font-black text-xl shadow">
                    🙏
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="font-extrabold text-base sm:text-lg tracking-wide">SERVICE FOR ADVANCE SEWA — TRANSPORT PORTAL</h1>
                        <span class="hidden sm:inline-block text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-800 text-amber-200">advancesewa.samagamtransport.in</span>
                    </div>
                    <p class="text-xs text-amber-200">60th Maharashtra Annual Nirankari Sant Samagam • Kharghar, Navi Mumbai</p>
                </div>
            </div>

            <div class="flex items-center gap-2">
                <div class="flex items-center gap-1 bg-amber-900/90 p-1 rounded-xl border border-amber-700 text-[11px] font-extrabold">
                    <button onclick="setAdvLang('hi', this)" class="lang-btn px-2.5 py-1 rounded-lg transition">हिंदी</button>
                    <button onclick="setAdvLang('mr', this)" class="lang-btn px-2.5 py-1 rounded-lg transition">मराठी</button>
                    <button onclick="setAdvLang('en', this)" class="lang-btn active px-2.5 py-1 rounded-lg transition">English</button>
                </div>
                <a href="https://www.samagamtransport.in" class="hidden sm:inline-block text-xs font-bold bg-amber-800 hover:bg-amber-700 px-3 py-2 rounded-xl border border-amber-600">
                    🚌 Main Transport Portal
                </a>
            </div>
        </div>
    </header>

    <main class="max-w-5xl mx-auto w-full px-4 py-6 space-y-6 flex-1">
        <!-- 24-HOUR LIVE STATUS & VEHICLE ALLOCATION TRACKER -->
        <section class="bg-white rounded-3xl p-5 sm:p-6 border-2 border-amber-400 shadow-md space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-sm sm:text-base font-extrabold text-amber-950" data-i18n="track_title">
                    🔍 Check Your Advance Sewa Vehicle Allocation Status (Updated Within 24 Hours)
                </h2>
                <span class="text-[11px] font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">24-Hr SLA Tracker</span>
            </div>
            <div class="flex flex-col sm:flex-row gap-2.5">
                <input type="text" id="adv-track-input" placeholder="Enter 10-Digit Contact Number or Request ID (e.g. ADV-1234)" class="flex-1 border border-slate-300 rounded-2xl px-4 py-3 text-sm font-bold focus:outline-none focus:border-amber-600">
                <button onclick="checkAdvanceSewaStatus()" class="bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold px-6 py-3 rounded-2xl text-sm shadow transition">
                    <span data-i18n="track_btn">Check Allocation Status</span>
                </button>
            </div>
            <div id="adv-track-results" class="space-y-2.5"></div>
        </section>

        <!-- MAIN ADVANCE SEWA REQUEST FORM + RECENT SUBMISSIONS -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <section class="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-7 border border-amber-200 shadow-xl space-y-4">
                <div class="border-b pb-3">
                    <span class="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-950">
                        धन निरंकार जी 🙏 • Advance Sewa Transport
                    </span>
                    <h2 class="text-xl font-extrabold text-slate-900 mt-1" data-i18n="form_title">
                        Raise Advance Sewa Vehicle Request
                    </h2>
                    <p class="text-xs text-slate-500" data-i18n="form_desc">
                        Connected directly to the Central Transport Database. Your vehicle & driver allocation will appear in the status tracker above within 24 hours.
                    </p>
                </div>

                <form id="dedicated-adv-form" onsubmit="submitDedicatedAdvanceSewa(event)" class="space-y-3.5 text-xs sm:text-sm">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_name">Name *</label>
                            <input type="text" name="requester_name" required placeholder="Full Name" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_phone">Contact Number *</label>
                            <input type="tel" name="contact_number" required maxlength="10" inputmode="numeric" placeholder="10-Digit Mobile Number" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_branch">Branch *</label>
                            <input type="text" name="branch_name" required placeholder="e.g. Thane / Mulund / Panvel" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_unit">Unit Number *</label>
                            <input type="text" name="unit_number" required placeholder="e.g. Unit-214" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_landmark">Landmark *</label>
                            <input type="text" name="landmark" required placeholder="Pickup Landmark / Bhawan" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_station">Nearest Railway Station *</label>
                            <input type="text" name="nearest_railway_station" required placeholder="e.g. Panvel / Thane / Goregaon" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-semibold">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_date">Date of Sewa *</label>
                            <input type="date" name="date_of_sewa" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_start">Time to Start Journey *</label>
                            <input type="time" name="start_journey_time" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_return">Time to Return *</label>
                            <input type="time" name="return_time" required class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_pax">Sevadars Count</label>
                            <input type="number" name="passenger_count" value="25" min="1" class="w-full border border-slate-300 rounded-xl px-3 py-2.5 font-bold">
                        </div>
                        <div class="sm:col-span-2">
                            <label class="block text-xs font-bold text-slate-700 mb-1" data-i18n="lbl_remarks">Sewa Department / Remarks</label>
                            <input type="text" name="notes" placeholder="e.g. Ground Preparation / Tent / Langar Sewa" class="w-full border border-slate-300 rounded-xl px-3 py-2.5">
                        </div>
                    </div>

                    <button type="submit" class="w-full bg-amber-600 hover:bg-amber-500 text-slate-950 font-extrabold py-4 rounded-2xl text-sm sm:text-base shadow-xl transition">
                        ✅ <span data-i18n="btn_submit">Submit Advance Sewa Request</span>
                    </button>
                </form>

                <div id="adv-confirmation-box" class="hidden bg-emerald-50 border-2 border-emerald-500 rounded-2xl p-4 space-y-2 text-xs">
                    <div class="font-extrabold text-sm text-emerald-950">✅ Request Saved in Central Transport Database!</div>
                    <div id="adv-confirmation-summary" class="text-slate-700 font-semibold"></div>
                    <a id="adv-whatsapp-receipt-btn" href="#" target="_blank" rel="noopener noreferrer" class="inline-block bg-emerald-700 hover:bg-emerald-600 text-white font-bold px-4 py-2 rounded-xl">
                        💬 Save Receipt on WhatsApp
                    </a>
                </div>
            </section>

            <section class="lg:col-span-5 bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 shadow-md space-y-3">
                <div class="flex justify-between items-center border-b pb-2.5">
                    <div>
                        <h3 class="font-extrabold text-sm text-amber-950">📋 Live Advance Sewa Queue</h3>
                        <p class="text-[11px] text-slate-500">Recent requests synced with Control Room</p>
                    </div>
                    <button onclick="loadAdvanceSewaFeed()" class="text-xs font-bold text-amber-800 bg-amber-100 px-3 py-1 rounded-lg">↻ Refresh</button>
                </div>
                <div id="adv-live-feed-list" class="space-y-2.5 text-xs max-h-[540px] overflow-y-auto">
                    <p class="text-slate-400">Loading Advance Sewa requests...</p>
                </div>
            </section>
        </div>
    </main>

    <footer class="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        धन निरंकार जी 🙏 • Sant Nirankari Mandal Transport & Logistics Cell • advancesewa.samagamtransport.in
    </footer>

    <script>
        const ADV_I18N = {
            en: {
                track_title: "🔍 Check Your Advance Sewa Vehicle Allocation Status (Updated Within 24 Hours)",
                track_btn: "Check Allocation Status",
                form_title: "Raise Advance Sewa Vehicle Request",
                form_desc: "Connected directly to the Central Transport Database. Your vehicle & driver allocation will appear in the status tracker above within 24 hours.",
                lbl_name: "Name *",
                lbl_phone: "Contact Number *",
                lbl_branch: "Branch *",
                lbl_unit: "Unit Number *",
                lbl_landmark: "Landmark *",
                lbl_station: "Nearest Railway Station *",
                lbl_date: "Date of Sewa *",
                lbl_start: "Time to Start Journey *",
                lbl_return: "Time to Return *",
                lbl_pax: "Sevadars Count",
                lbl_remarks: "Sewa Department / Remarks",
                btn_submit: "Submit Advance Sewa Request"
            },
            hi: {
                track_title: "🔍 अपने अग्रिम सेवा वाहन आवंटन की स्थिति जांचें (24 घंटे के भीतर अपडेट)",
                track_btn: "स्थिति जांचें",
                form_title: "अग्रिम सेवा (Advance Sewa) वाहन अनुरोध फॉर्म",
                form_desc: "सीधे केंद्रीय परिवहन डेटाबेस से जुड़ा हुआ। 24 घंटे के भीतर ऊपर दिए गए ट्रैकर में वाहन और ड्राइवर की जानकारी देखें।",
                lbl_name: "नाम (Name) *",
                lbl_phone: "संपर्क नंबर (Contact Number) *",
                lbl_branch: "ब्रांच (Branch) *",
                lbl_unit: "यूनिट नंबर (Unit Number) *",
                lbl_landmark: "लैंडमार्क (Landmark) *",
                lbl_station: "नजदीकी रेलवे स्टेशन (Nearest Railway Station) *",
                lbl_date: "सेवा दिनांक (Date of Sewa) *",
                lbl_start: "यात्रा शुरू करने का समय (Time to Start Journey) *",
                lbl_return: "वापसी का समय (Time to Return) *",
                lbl_pax: "सेवादारों की संख्या",
                lbl_remarks: "सेवा विभाग / टिप्पणी",
                btn_submit: "अग्रिम सेवा अनुरोध जमा करें"
            },
            mr: {
                track_title: "🔍 तुमच्या आगाऊ सेवा वाहन वाटपाची स्थिती तपासा (२४ तासांत अपडेट)",
                track_btn: "स्थिती तपासा",
                form_title: "आगाऊ सेवेसाठी वाहन विनंती (Service for Advance Sewa)",
                form_desc: "थेट मुख्य परिवहन डेटाबेसशी जोडलेले. २४ तासांच्या आत वरील ट्रॅकरमध्ये वाहनाची व ड्रायव्हरची माहिती पहा.",
                lbl_name: "नाव (Name) *",
                lbl_phone: "संपर्क क्रमांक (Contact Number) *",
                lbl_branch: "ब्रांच (Branch) *",
                lbl_unit: "युनिट नंबर (Unit Number) *",
                lbl_landmark: "लँडमार्क (Landmark) *",
                lbl_station: "जवळचे रेल्वे स्टेशन (Nearest Railway Station) *",
                lbl_date: "सेवेची तारीख (Date of Sewa) *",
                lbl_start: "प्रवास सुरू करण्याची वेळ (Time to Start Journey) *",
                lbl_return: "परतीची वेळ (Time to Return) *",
                lbl_pax: "सेवादार संख्या",
                lbl_remarks: "सेवा विभाग / टीप",
                btn_submit: "आगाऊ सेवा विनंती सादर करा"
            }
        };

        function setAdvLang(lang, btn) {
            const dict = ADV_I18N[lang] || ADV_I18N.en;
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const k = el.getAttribute('data-i18n');
                if (dict[k]) el.textContent = dict[k];
            });
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            localStorage.setItem('samagam_adv_lang', lang);
        }

        async function submitDedicatedAdvanceSewa(e) {
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
                localStorage.setItem('last_adv_query', payload.contact_number);
                document.getElementById('adv-track-input').value = payload.contact_number;

                const box = document.getElementById('adv-confirmation-box');
                box.classList.remove('hidden');
                document.getElementById('adv-confirmation-summary').textContent =
                    `Request ID: ${data.request_code} | ${payload.requester_name} (${payload.branch_name} / Unit ${payload.unit_number}) | Date: ${payload.date_of_sewa} (${payload.start_journey_time} → ${payload.return_time})`;

                const waMsg = encodeURIComponent(
                    `धन निरंकार जी 🙏\n*Samagam Advance Sewa Transport Request*\n` +
                    `Request ID: *${data.request_code}*\n` +
                    `Name: ${payload.requester_name}\n` +
                    `Branch / Unit: ${payload.branch_name} / ${payload.unit_number}\n` +
                    `Station & Landmark: ${payload.nearest_railway_station} (${payload.landmark})\n` +
                    `Date & Time: ${payload.date_of_sewa} (${payload.start_journey_time} to ${payload.return_time})\n\n` +
                    `Check vehicle allocation within 24 hours at: https://advancesewa.samagamtransport.in`
                );
                const cleanPhone = payload.contact_number.replace(/\D/g, '');
                const waPhone = cleanPhone.length === 10 ? `91${cleanPhone}` : cleanPhone;
                document.getElementById('adv-whatsapp-receipt-btn').href = `https://wa.me/${waPhone}?text=${waMsg}`;

                e.target.reset();
                checkAdvanceSewaStatus();
                loadAdvanceSewaFeed();
            } else {
                alert('❌ ' + (data.detail || 'Error submitting Advance Sewa request.'));
            }
        }

        async function checkAdvanceSewaStatus() {
            const q = document.getElementById('adv-track-input').value.trim();
            if (!q) return;
            localStorage.setItem('last_adv_query', q);
            const box = document.getElementById('adv-track-results');
            box.innerHTML = '<div class="text-xs text-slate-500">Checking live database status...</div>';

            const res = await fetch(`/api/operations/request-status-lookup?query=${encodeURIComponent(q)}`);
            if (!res.ok) {
                box.innerHTML = '<div class="p-3 rounded-2xl bg-rose-50 text-rose-700 text-xs font-bold">No Advance Sewa request found for that number or ID.</div>';
                return;
            }
            const items = await res.json();
            if (!items.length) {
                box.innerHTML = '<div class="p-3 rounded-2xl bg-amber-50 text-amber-900 text-xs font-bold">No matching requests found yet.</div>';
                return;
            }

            box.innerHTML = items.map(item => `
                <div class="p-4 rounded-2xl border-2 ${item.is_allocated ? 'bg-emerald-50 border-emerald-500' : 'bg-amber-50 border-amber-300'} flex flex-wrap justify-between items-center gap-3 text-xs">
                    <div class="space-y-1">
                        <div class="flex items-center gap-2">
                            <span class="font-black text-sm text-slate-900">${item.code}</span>
                            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${item.is_allocated ? 'bg-emerald-700 text-white' : 'bg-amber-500 text-slate-950'}">
                                ${item.is_allocated ? '✅ VEHICLE ALLOCATED' : '⏳ PENDING ALLOCATION (24-HR SLA)'}
                            </span>
                        </div>
                        <div class="font-semibold text-slate-700">${item.summary}</div>
                        <div class="text-slate-500">Requester: ${item.requester_name} (${item.requester_phone})</div>
                    </div>
                    ${item.is_allocated ? `
                        <div class="bg-white p-3 rounded-xl border border-emerald-300 text-right space-y-1 shadow-sm">
                            <div class="text-[10px] uppercase font-bold text-emerald-700">Assigned Vehicle & Driver</div>
                            <div class="text-sm font-black text-slate-900">${item.assigned_vehicle_reg}</div>
                            <div class="text-slate-700 font-bold">${item.driver_name || 'Assigned Sevadar'}</div>
                            ${item.driver_phone ? `<a href="tel:${item.driver_phone}" class="inline-block mt-1 bg-emerald-700 text-white font-bold px-3 py-1 rounded-lg">📞 Call ${item.driver_phone}</a>` : ''}
                        </div>
                    ` : `
                        <div class="text-right text-amber-900 font-bold">
                            Control Room reviewing.<br>Check back within 24 hours.
                        </div>
                    `}
                </div>
            `).join('');
        }

        async function loadAdvanceSewaFeed() {
            try {
                const res = await fetch('/api/operations/advance-sewa-requests');
                if (!res.ok) return;
                const list = await res.json();
                const box = document.getElementById('adv-live-feed-list');
                box.innerHTML = list.length ? list.map(a => `
                    <div class="p-3.5 rounded-2xl border ${a.status === 'ALLOCATED' ? 'bg-emerald-50/70 border-emerald-300' : 'bg-amber-50/60 border-amber-200'} space-y-1">
                        <div class="flex justify-between items-center">
                            <span class="font-extrabold text-amber-950">${a.request_code} • ${a.branch_name} (Unit ${a.unit_number})</span>
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold ${a.status === 'ALLOCATED' ? 'bg-emerald-700 text-white' : 'bg-amber-400 text-slate-950'}">${a.status}</span>
                        </div>
                        <div class="text-slate-700 font-semibold">${a.nearest_railway_station} • ${a.date_of_sewa} (${a.start_journey_time} → ${a.return_time})</div>
                        <div class="text-slate-500">By: ${a.requester_name} • ${a.passenger_count} Sevadars</div>
                        ${a.assigned_vehicle_reg ? `<div class="text-emerald-800 font-extrabold">🚍 Assigned: ${a.assigned_vehicle_reg} (${a.assigned_driver_name})</div>` : ''}
                    </div>
                `).join('') : '<p class="text-slate-400">No Advance Sewa requests raised yet.</p>';
            } catch (_) {}
        }

        window.addEventListener('DOMContentLoaded', () => {
            const savedLang = localStorage.getItem('samagam_adv_lang') || 'en';
            const btn = document.querySelector(`.lang-btn[onclick*="'${savedLang}'"]`);
            if (btn) setAdvLang(savedLang, btn);

            const lastQ = localStorage.getItem('last_adv_query');
            if (lastQ) {
                document.getElementById('adv-track-input').value = lastQ;
                checkAdvanceSewaStatus();
            }
            loadAdvanceSewaFeed();
            setInterval(loadAdvanceSewaFeed, 30000);
        });
    </script>
</body>
</html>
'''


def write_portals():
    for fname, content in [
        ("parking_portal.html", PARKING_PORTAL_HTML),
        ("advance_sewa_portal.html", ADVANCE_SEWA_PORTAL_HTML),
    ]:
        fpath = os.path.join(TARGET_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Wrote: {fpath}")

        # Also copy to ./root/ if present
        root_dir = os.path.join(TARGET_DIR, "root")
        if os.path.isdir(root_dir):
            with open(os.path.join(root_dir, fname), "w", encoding="utf-8") as f:
                f.write(content)


def patch_main_py_subdomain_routing():
    main_path = os.path.join(TARGET_DIR, "app", "main.py")
    if not os.path.isfile(main_path):
        print(f"⚠️ app/main.py not found at {main_path}")
        return

    with open(main_path, "r", encoding="utf-8") as f:
        code = f.read()

    new_home_fn = '''@app.get("/")
def home(request: Request):
    # Check X-Forwarded-Host, Host, and Referer so reverse proxies never mask the subdomain
    candidates = [
        request.headers.get("x-forwarded-host", ""),
        request.headers.get("x-original-host", ""),
        request.headers.get("host", ""),
        request.headers.get("referer", ""),
        str(request.url.hostname or "")
    ]
    combined_host = " ".join(candidates).lower()

    if "parking.samagamtransport.in" in combined_host or any(
        c.split(",")[0].strip().lower().startswith("parking.") for c in candidates if c
    ):
        p = os.path.join(ROOT_DIR, "parking_portal.html")
        if os.path.exists(p):
            return FileResponse(p)

    if "advancesewa.samagamtransport.in" in combined_host or any(
        c.split(",")[0].strip().lower().startswith("advancesewa.") for c in candidates if c
    ):
        a = os.path.join(ROOT_DIR, "advance_sewa_portal.html")
        if os.path.exists(a):
            return FileResponse(a)

    if "admin.samagamtransport.in" in combined_host or any(
        c.split(",")[0].strip().lower().startswith("admin.") for c in candidates if c
    ):
        adm = os.path.join(ROOT_DIR, "admin_dashboard.html")
        if os.path.exists(adm):
            return FileResponse(adm)

    welcome_path = os.path.join(ROOT_DIR, "welcome.html")
    if os.path.exists(welcome_path):
        return FileResponse(welcome_path)
    return _serve_html("admin_dashboard.html")'''

    updated_code, count = re.subn(
        r'@app\.get\("/"\)\s*def home\(.*?\n    return _serve_html\("admin_dashboard\.html"\)',
        new_home_fn,
        code,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        print("⚠️ Could not auto-match @app.get('/') in app/main.py — check app/main.py manually.")
    else:
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(updated_code)
        print("✅ Updated app/main.py to route parking.samagamtransport.in & advancesewa.samagamtransport.in")


if __name__ == "__main__":
    print(f"🔧 Fixing subdomain routing & writing portals in: {TARGET_DIR}\n")
    write_portals()
    patch_main_py_subdomain_routing()
    print("\n🎉 Done! Next steps:")
    print("  1. git add .")
    print('  2. git commit -m "Fix parking & advancesewa subdomain routing and portals"')
    print("  3. git push origin main")
    print("  4. Redeploy Cloud Run: gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080")