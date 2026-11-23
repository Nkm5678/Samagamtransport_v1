"""
Samagam Transport Platform — Fix Web App URLs & Android APK Back/Login Navigation
Resolves:
  1. '{"detail":"station_team_app.html not found in project root."}' across all field web URLs
     by checking both ROOT_DIR and ROOT_DIR/root in app/main.py and syncing HTML files.
  2. Android APK hardware/gesture Back button & Logout navigation in static/samagam_app_shell.js
     so pressing Back or Logging Out stays on the app's own Login / Register screen instead of
     jumping to admin login.

Run inside C:\\narendra\\SamagamtransportV1:
    python fix_apps_and_android_back.py
"""

import os
import re
import shutil

TARGET_DIR = r"C:\narendra\SamagamtransportV1"
if not os.path.isdir(TARGET_DIR):
    TARGET_DIR = os.path.dirname(os.path.abspath(__file__))

FIELD_HTML_FILES = [
    "station_team_app.html",
    "ground_team_app.html",
    "gate_keeper_app.html",
    "diesel_team_app.html",
    "accounts_team_app.html",
    "driver_rider_companion.html",
    "radar_map_console.html",
    "bus_onboarding_form.html",
    "in_ground_seva_vehicles.html",
    "download_hub.html",
    "welcome.html",
    "parking_portal.html",
    "advance_sewa_portal.html",
]


def sync_html_between_root_and_project():
    """Ensures every HTML page exists in BOTH project root and ./root/ so Cloud Run & APK builds always find them."""
    root_sub = os.path.join(TARGET_DIR, "root")
    os.makedirs(root_sub, exist_ok=True)

    for fname in FIELD_HTML_FILES:
        top_path = os.path.join(TARGET_DIR, fname)
        sub_path = os.path.join(root_sub, fname)
        if os.path.isfile(top_path) and not os.path.isfile(sub_path):
            shutil.copy2(top_path, sub_path)
            print(f"✅ Copied {fname} -> root/{fname}")
        elif os.path.isfile(sub_path) and not os.path.isfile(top_path):
            shutil.copy2(sub_path, top_path)
            print(f"✅ Restored root/{fname} -> {fname}")


def patch_main_py_serve_html():
    """Updates _serve_html in app/main.py to check ROOT_DIR, ROOT_DIR/root, and current working directory."""
    main_path = os.path.join(TARGET_DIR, "app", "main.py")
    if not os.path.isfile(main_path):
        print(f"⚠️ {main_path} not found.")
        return

    with open(main_path, "r", encoding="utf-8") as f:
        code = f.read()

    new_serve_html = '''def _serve_html(filename: str):
    candidates = [
        os.path.join(ROOT_DIR, filename),
        os.path.join(ROOT_DIR, "root", filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "root", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return FileResponse(path)
    return JSONResponse(status_code=404, content={"detail": f"{filename} not found in project root."})'''

    updated, count = re.subn(
        r'def _serve_html\(filename: str\):.*?return \{"detail": f"\{filename\} not found in project root\."\}',
        new_serve_html,
        code,
        count=1,
        flags=re.DOTALL,
    )

    if count > 0:
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print("✅ Patched _serve_html() in app/main.py to check both project root and ./root/")
    else:
        print("ℹ️ _serve_html() already updated or custom format in app/main.py")


def update_samagam_app_shell_js():
    """Fixes Android APK Back navigation and keeps field apps on their own Login/Register screen."""
    static_dir = os.path.join(TARGET_DIR, "static")
    os.makedirs(static_dir, exist_ok=True)
    shell_path = os.path.join(static_dir, "samagam_app_shell.js")

    shell_js = r'''/**
 * जागृति — The Awakening | निरंकारी सन्त समागम
 * 1. Connects Android APKs & Instant Web Apps seamlessly to https://www.samagamtransport.in
 * 2. Keeps Android APK hardware/gesture Back button inside the app's own Login/Register/Workspace
 *    instead of jumping to the Admin login or closing unexpectedly.
 * 3. Polls session heartbeat every 10s so Admin Termination immediately locks out revoked users.
 */
(function initJagritiAuthAndShell() {
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
        "/advance_sewa_portal.html"
    ];
    const currentPath = window.location.pathname || "/";
    const host = (window.location.hostname || "").toLowerCase();
    const isSubdomainPortal = host.startsWith("parking.") || host.startsWith("advancesewa.") || host.startsWith("admin.");
    const isPublicPage = !isFileOrCapacitor && (PUBLIC_PATHS.includes(currentPath) || isSubdomainPortal);

    // -------------------------------------------------------------------------
    // 1. ANDROID APK BACK-BUTTON & HISTORY TRAP (Prevents jumping to Admin/Blank)
    // -------------------------------------------------------------------------
    if (isFileOrCapacitor) {
        try {
            window.history.replaceState({ samagamApkRoot: true }, "", window.location.href);
            window.history.pushState({ samagamApkGuard: true }, "", window.location.href);

            window.addEventListener("popstate", function () {
                const stepOtp = document.getElementById("m-auth-step-otp");
                const stepPin = document.getElementById("m-auth-step-pin");
                const step1 = document.getElementById("m-auth-step1");

                // If user is on OTP or PIN step inside the login modal, Back returns to Step 1
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

                // Driver app step-back support
                if (typeof window.resetAuthScreen === "function") {
                    const drvOtp = document.getElementById("auth-step-otp");
                    const drvPin = document.getElementById("auth-step-pin");
                    if ((drvOtp && !drvOtp.classList.contains("hidden")) || (drvPin && !drvPin.classList.contains("hidden"))) {
                        window.resetAuthScreen();
                        window.history.pushState({ samagamApkGuard: true }, "", window.location.href);
                        return;
                    }
                }

                // Keep user inside the current APK screen instead of navigating to admin/blank page
                window.history.pushState({ samagamApkGuard: true }, "", window.location.href);
            });
        } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 2. FETCH INTERCEPTOR (Routes APK API calls & attaches Field Session Token)
    // -------------------------------------------------------------------------
    const origFetch = window.fetch.bind(window);
    window.fetch = async function (input, init) {
        let url = input;
        if (originPrefix && typeof url === "string" && url.startsWith("/")) {
            url = originPrefix + url;
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

    // -------------------------------------------------------------------------
    // 3. APP'S OWN FIELD LOGIN / REGISTER MODAL (Never redirects to Admin Login)
    // -------------------------------------------------------------------------
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
'''

    with open(shell_path, "w", encoding="utf-8") as f:
        f.write(shell_js)
    print(f"✅ Updated {shell_path} with Android APK Back-Button Trap & Self-Contained Login/Register")


def patch_driver_logout_and_back():
    """Ensures driver_rider_companion.html stays on its own Login/Register screen on Logout/Back."""
    drv_path = os.path.join(TARGET_DIR, "driver_rider_companion.html")
    if not os.path.isfile(drv_path):
        return
    with open(drv_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace location.reload() on logout with clean in-app return to #driver-auth-screen
    old_logout = """            localStorage.removeItem('samagam_driver_token');
            driverToken = '';
            location.reload();"""
    new_logout = """            localStorage.removeItem('samagam_driver_token');
            localStorage.removeItem('samagam_field_token');
            driverToken = '';
            currentDriver = null;
            document.getElementById('driver-main-console').classList.add('hidden');
            document.getElementById('btn-driver-logout').classList.add('hidden');
            document.getElementById('driver-auth-screen').classList.remove('hidden');
            resetAuthScreen();"""

    if old_logout in html:
        html = html.replace(old_logout, new_logout)
        with open(drv_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Updated driver_rider_companion.html Logout to return cleanly to Driver Login/Register")


if __name__ == "__main__":
    print(f"🔧 Fixing Web App URLs & Android APK Back/Login flow in: {TARGET_DIR}\n")
    sync_html_between_root_and_project()
    patch_main_py_serve_html()
    update_samagam_app_shell_js()
    patch_driver_logout_and_back()
    sync_html_between_root_and_project()
    print("\n🎉 Done! Run these commands to push & redeploy:")
    print("  1. git add .")
    print('  2. git commit -m "Fix field web URLs and Android APK Back button / login flow"')
    print("  3. git push origin main")
    print("  4. Deploy Cloud Run: gcloud run deploy samagamtransport --source . --region asia-southeast1 --platform managed --allow-unauthenticated --port 8080")