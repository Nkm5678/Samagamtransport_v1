(function initJagritiAuthAndShell() {
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
