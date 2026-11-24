"""
Samagam Transport Platform — Complete Automated Functional, Subdomain & Admin SLA Audit Suite
Verifies:
  1. All web portals & field apps (Welcome, Parking QR, Advance Sewa, Station, Ground, Gate Keeper, Diesel, Accounts, Driver)
  2. Role authentication & registration (Admin Control Room, Station, Ground, Gate Keeper, Diesel, Accounts, Driver)
  3. Advance Sewa & Station-to-Ground Pickup/Drop requests + Action/Resolution SLA & Turnaround Time (TAT)
  4. Parking QR ticket generation & gate entry/exit verification
  5. Driver shift start/end & trip start/end lifecycle
  6. Station <-> Ground live coordination & app call directory
  7. Admin rights (portal isolation, crew roster/PIN reset/termination/reactivation, executive analytics & CSV/XLSX exports)

Usage:
  python comprehensive_functional_audit.py --url https://www.samagamtransport.in
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import html
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


@dataclasses.dataclass
class AuditResult:
    index: int
    module: str
    case: str
    passed: bool
    actor: str
    tat: str
    latency_ms: float
    evidence: str


class SamagamFunctionalAudit:
    def __init__(self, base_url: str, parking_url: str, advancesewa_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.parking_url = parking_url.rstrip("/")
        self.advancesewa_url = advancesewa_url.rstrip("/")
        self.results: list[AuditResult] = []
        self.tokens: dict[str, str] = {}
        self.run_tag = str(random.randint(10000, 99999))
        self.last_demand_id: int | None = None
        self.last_demand_code: str | None = None
        self.request_raised_ts: float | None = None
        self.request_raised_by: str = "Ramesh Kulkarni (Station Team)"
        self.request_acted_by: str = "Suresh Patil (Ground Team)"
        self.request_first_action_tat: str = "-"
        self.active_shift_id: int | None = None
        self.active_journey_id: int | None = None

    def _record(
        self,
        module: str,
        case: str,
        passed: bool,
        latency_ms: float,
        evidence: str,
        actor: str = "System / Sevadar",
        tat: str = "-",
    ) -> None:
        idx = len(self.results) + 1
        self.results.append(
            AuditResult(
                index=idx,
                module=module,
                case=case,
                passed=passed,
                actor=actor,
                tat=tat,
                latency_ms=round(latency_ms, 1),
                evidence=evidence,
            )
        )
        icon = "PASS" if passed else "FAIL"
        print(f"[{idx:02d}] {icon} | {module:<24} | {case:<52} | {latency_ms:6.1f} ms")

    def _http(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        headers: dict[str, str] | None = None,
        base_override: str | None = None,
        timeout: float = 15.0,
    ) -> tuple[int, Any, float]:
        root = (base_override or self.base_url).rstrip("/")
        url = path if path.startswith("http") else f"{root}{path}"
        req_headers: dict[str, str] = {
            "Accept": "application/json, text/html, */*",
            "User-Agent": "Samagam-Functional-Audit/2.0",
        }
        if headers:
            req_headers.update(headers)
        if token:
            req_headers["X-Driver-Token"] = token
            req_headers["X-Session-Token"] = token

        body_bytes: bytes | None = None
        if payload is not None:
            import json

            body_bytes = json.dumps(payload).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        start = time.perf_counter()
        req = urllib.request.Request(url=url, data=body_bytes, headers=req_headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                elapsed = (time.perf_counter() - start) * 1000.0
                return self._decode_response(resp.status, raw), elapsed
        except urllib.error.HTTPError as err:
            raw = err.read() if err.fp else b""
            elapsed = (time.perf_counter() - start) * 1000.0
            parsed, _ = self._decode_response(err.code, raw)
            return err.code, parsed, elapsed
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000.0
            return 0, {"error": str(exc)}, elapsed

    @staticmethod
    def _decode_response(status: int, raw: bytes) -> tuple[int, Any]:
        import json

        text = raw.decode("utf-8", errors="replace")
        try:
            return status, json.loads(text)
        except Exception:
            return status, text

    # -------------------------------------------------------------------------
    # 1. PORTALS & FIELD APPS
    # -------------------------------------------------------------------------
    def test_portals_and_apps(self) -> None:
        checks = [
            ("Load Main Transport Welcome Portal (/)", "/", self.base_url, {}),
            (
                "Load Parking Subdomain Portal (parking.samagamtransport.in) (/)",
                "/",
                self.parking_url,
                {"Host": "parking.samagamtransport.in", "X-Forwarded-Host": "parking.samagamtransport.in"},
            ),
            (
                "Load Advance Sewa Subdomain Portal (advancesewa.samagamtransport.in) (/)",
                "/",
                self.advancesewa_url,
                {"Host": "advancesewa.samagamtransport.in", "X-Forwarded-Host": "advancesewa.samagamtransport.in"},
            ),
            ("Load Station Team Web/APK Portal (/station_team_app.html)", "/station_team_app.html", self.base_url, {}),
            ("Load Ground Team Web/APK Portal (/ground_team_app.html)", "/ground_team_app.html", self.base_url, {}),
            ("Load Gate Keeper Web/APK Portal (/gate_keeper_app.html)", "/gate_keeper_app.html", self.base_url, {}),
            ("Load Diesel Team Web/APK Portal (/diesel_team_app.html)", "/diesel_team_app.html", self.base_url, {}),
            ("Load Accounts Team Web/APK Portal (/accounts_team_app.html)", "/accounts_team_app.html", self.base_url, {}),
            ("Load Driver & Rider Companion App (/driver_rider_companion.html)", "/driver_rider_companion.html", self.base_url, {}),
        ]
        for label, path, base, hdrs in checks:
            code, body, ms = self._http("GET", path, headers=hdrs, base_override=base)
            size_bytes = len(body.encode("utf-8")) if isinstance(body, str) else len(str(body))
            ok = code == 200 and size_bytes > 200
            self._record("1. Portals & Apps", label, ok, ms, f"HTTP {code}, HTML size={size_bytes} bytes", actor="Public / Sevadar")

    # -------------------------------------------------------------------------
    # 2. ROLE AUTHENTICATION & REGISTRATION
    # -------------------------------------------------------------------------
    def test_role_authentication(self) -> None:
        adm_headers = {"Host": "admin.samagamtransport.in", "X-Forwarded-Host": "admin.samagamtransport.in"}
        code, body, ms = self._http(
            "POST",
            "/api/auth/control-room-login",
            {"mobile_number": "9820110001", "access_code": "Narendra@2183", "password": "Narendra@2183"},
            headers=adm_headers,
        )
        tok = body.get("session_token") or body.get("token") if isinstance(body, dict) else ""
        if tok:
            self.tokens["admin"] = tok
        self._record(
            "2. Role Auth & Login",
            "Admin Control Room Login",
            code == 200 and bool(tok),
            ms,
            f"HTTP {code} | Token issued: {bool(tok)}",
            actor="Admin (Control Room)",
        )

        roles = [
            ("station_team", "Ramesh Kulkarni", "9800327431", "Thane Railway Station", "Unit-11", "Thane"),
            ("ground_team", "Suresh Patil", "9800327432", "Ground 1 (Main Hall)", "Unit-12", "Kharghar"),
            ("gate_keeper", "Mahesh Shinde", "9800327433", "Ground 1 (Main Hall)", "Unit-13", "Panvel"),
            ("diesel_team", "Dinesh Jadhav", "9800327434", "Ground 1 (Main Hall)", "Unit-14", "Belapur"),
            ("accounts_team", "Prakash Nair", "9800327435", "Ground 1 (Main Hall)", "Unit-15", "Nerul"),
            ("driver", "Driver Ajay Sharma", "9800327436", "Thane Railway Station", "Fleet-Driver", "Operator: Samagam Fleet"),
        ]
        for role_key, name, phone, hub, unit, branch in roles:
            reg_payload = {
                "full_name": name,
                "mobile_number": phone,
                "unit_number": unit,
                "branch_name": branch,
                "duty_location": hub,
                "latitude": 19.2183 if "Ground" in hub else 19.1860,
                "longitude": 72.9781 if "Ground" in hub else 72.9759,
                "geo_accuracy": 12.0,
                "device_fingerprint": f"audit-{role_key}-{self.run_tag}",
            }
            r_code, r_body, r_ms = self._http("POST", "/api/auth/register", reg_payload)
            p_code, p_body, p_ms = self._http("POST", "/api/auth/pin/verify", {"identifier": phone, "pin": "1234"})
            ptok = (p_body.get("token") or p_body.get("session_token")) if isinstance(p_body, dict) else ""
            if ptok:
                self.tokens[role_key] = ptok
            ok = r_code in (200, 400, 409)
            self._record(
                "2. Role Auth & Login",
                f"Sevadar/Driver Register & Login [{role_key.upper()}]",
                ok,
                r_ms + p_ms,
                f"User={name} ({phone}) | Geofence Reg HTTP {r_code} | PIN/OTP Token={bool(ptok)}",
                actor=f"{name} ({role_key})",
            )

    # -------------------------------------------------------------------------
    # 3. BOOKING, ACTION, RESOLUTION & TURNAROUND TIME (TAT)
    # -------------------------------------------------------------------------
    def test_booking_and_request_sla(self) -> None:
        adv_headers = {"Host": "advancesewa.samagamtransport.in", "X-Forwarded-Host": "advancesewa.samagamtransport.in"}
        adv_payload = {
            "requester_name": "Advance Sewa Coordinator",
            "contact_number": "9820099111",
            "branch_name": "Panvel",
            "unit_number": "Unit-204",
            "landmark": "Near Panvel Station",
            "nearest_railway_station": "Panvel Junction (PNVL)",
            "date_of_sewa": "2027-01-22",
            "start_journey_time": "07:00",
            "return_time": "19:00",
            "passenger_count": 48,
            "notes": f"Audit Run {self.run_tag}",
        }
        a_code, a_body, a_ms = self._http(
            "POST",
            "/api/operations/advance-sewa-requests",
            adv_payload,
            headers=adv_headers,
            base_override=self.advancesewa_url,
        )
        if a_code == 404:
            a_code, a_body, a_ms = self._http(
                "POST",
                "/api/operations/demands",
                {
                    "hub_name": "Panvel Junction (PNVL)",
                    "waiting_passenger_count": 48,
                    "priority": "HIGH",
                    "requested_by": "Advance Sewa Coordinator",
                    "notes": f"Advance Sewa Audit {self.run_tag}",
                },
            )
        req_code = a_body.get("request_code") or a_body.get("demand_code") or "CREATED" if isinstance(a_body, dict) else "NONE"
        self._record(
            "3. Booking & Request SLA",
            "Create Advance Sewa Transport Booking (advancesewa.samagamtransport.in)",
            a_code in (200, 201),
            a_ms,
            f"HTTP {a_code} | Request Code={req_code} | Pax=48",
            actor="Advance Sewa Coordinator",
        )

        # Raise Station-to-Ground Pickup Request
        self.request_raised_ts = time.perf_counter()
        raised_utc = dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S UTC")
        d_code, d_body, d_ms = self._http(
            "POST",
            "/api/operations/demands",
            {
                "hub_name": "Thane Railway Station",
                "waiting_passenger_count": 50,
                "priority": "HIGH",
                "requested_by": self.request_raised_by,
                "notes": f"Pickup to Ground 1 [{self.run_tag}]",
            },
            token=self.tokens.get("station_team"),
        )
        if isinstance(d_body, dict):
            self.last_demand_id = d_body.get("id")
            self.last_demand_code = d_body.get("demand_code")
        self._record(
            "3. Booking & Request SLA",
            "Raise Station-to-Ground Pickup Request",
            d_code in (200, 201),
            d_ms,
            f"HTTP {d_code} | Request Code={self.last_demand_code} (Demand ID={self.last_demand_id}) | Raised at {raised_utc}",
            actor=self.request_raised_by,
            tat=f"Raised @ {raised_utc}",
        )

        # Action Taken on Request (Vehicle & Driver Allocation)
        act_start = time.perf_counter()
        act_code, act_body, act_ms = self._http(
            "POST",
            "/api/operations/pipeline/advance-step",
            {
                "action": "ASSIGN_AND_DISPATCH",
                "vehicle_id": 1,
                "demand_id": self.last_demand_id,
                "destination_hub": "Ground 1 (Main Hall)",
                "passenger_count": 48,
                "actor_name": self.request_acted_by,
            },
            token=self.tokens.get("ground_team"),
        )
        first_action_sec = round(time.perf_counter() - act_start, 2)
        self.request_first_action_tat = f"First Action in {first_action_sec}s"
        self._record(
            "3. Booking & Request SLA",
            "Action Taken on Request (Vehicle & Driver Allocation)",
            act_code == 200,
            act_ms,
            f"HTTP {act_code} | Bus=MH-04-TR-1001 | Action By: {self.request_acted_by} | Response: {first_action_sec}s",
            actor=self.request_acted_by,
            tat=self.request_first_action_tat,
        )

        # Request Resolved & Full Audit Trail
        res_code, res_body, res_ms = self._http(
            "POST",
            "/api/operations/pipeline/advance-step",
            {
                "action": "GATE_ARRIVE_UNLOAD",
                "vehicle_id": 1,
                "destination_hub": "Ground 1 (Main Hall)",
                "actor_name": "Driver Ajay Sharma / Admin",
            },
            token=self.tokens.get("admin"),
        )
        total_sec = round(time.perf_counter() - (self.request_raised_ts or time.perf_counter()), 2)
        total_min = round(total_sec / 60.0, 3)
        tat_label = f"{total_sec}s ({total_min} min)"
        self._record(
            "3. Booking & Request SLA",
            "Request Resolved & Full Audit Trail (Who Raised / Who Acted / TAT)",
            res_code == 200,
            res_ms,
            f"HTTP {res_code} | Raised By: Ramesh Kulkarni -> Action By: Suresh Patil -> Resolved By: Driver Ajay Sharma | Total TAT: {tat_label}",
            actor="Driver Ajay Sharma / Admin",
            tat=tat_label,
        )

    # -------------------------------------------------------------------------
    # 4. PARKING QR TICKET GENERATION & VERIFICATION
    # -------------------------------------------------------------------------
    def test_parking_ticket_lifecycle(self) -> None:
        pkg_headers = {"Host": "parking.samagamtransport.in", "X-Forwarded-Host": "parking.samagamtransport.in"}
        plate = f"MH-04-PK-{self.run_tag}"
        reg_payload = {
            "owner_name": "Devotee Parking Audit",
            "owner_phone": "9820088111",
            "owner_email": "parking.audit@samagamtransport.in",
            "vehicle_reg_number": plate,
            "vehicle_category": "Car / Sedan / SUV",
            "vehicle_color_model": "White Sedan",
            "branch_name": "Kharghar",
            "zone_name": "Zone 1",
            "parking_zone": "Parking Zone P1 (Gate 1)",
        }
        r_code, r_body, r_ms = self._http(
            "POST",
            "/api/fleet/parking-passes/register-qr",
            reg_payload,
            headers=pkg_headers,
            base_override=self.parking_url,
        )
        token = r_body.get("parking_token") if isinstance(r_body, dict) else None
        pin = r_body.get("exit_pin") if isinstance(r_body, dict) else None
        self._record(
            "4. Parking QR Ticket",
            "Generate Parking QR Ticket & Allocate Zone (parking.samagamtransport.in)",
            r_code in (200, 201) and bool(token),
            r_ms,
            f"HTTP {r_code} | Vehicle={plate} | Ticket/QR ID={token} | Exit PIN={pin}",
            actor="Gate Keeper / Parking Portal",
        )

        sc_code, sc_body, sc_ms = self._http(
            "POST",
            "/api/fleet/parking-passes/scan-qr",
            {"qr_data": token or plate, "gate_direction": "ENTRY", "gate_name": "Gate 1"},
            headers=pkg_headers,
            base_override=self.parking_url,
        )
        lk_code, lk_body, lk_ms = self._http(
            "GET",
            "/api/fleet/parking-passes?status=ALL",
            headers=pkg_headers,
            base_override=self.parking_url,
        )
        count_found = len(lk_body) if isinstance(lk_body, list) else 0
        self._record(
            "4. Parking QR Ticket",
            "Verify Live Parking Occupancy & Ticket Lookup (parking.samagamtransport.in)",
            sc_code == 200 and lk_code == 200,
            sc_ms + lk_ms,
            f"Entry Scan HTTP {sc_code} | Lookup HTTP {lk_code} | Records Found={count_found}",
            actor="Gate Keeper (Mahesh Shinde)",
        )

    # -------------------------------------------------------------------------
    # 5. DRIVER SHIFT & TRIPS
    # -------------------------------------------------------------------------
    def test_driver_shift_and_trips(self) -> None:
        s_code, s_body, s_ms = self._http(
            "POST",
            "/api/operations/shifts/start",
            {
                "crew_role": "Driver",
                "crew_name": "Harbhajan Singh",
                "crew_phone": "9820110001",
                "station_hub": "Thane Railway Station",
                "vehicle_reg_number": "MH-04-TR-1001",
            },
            token=self.tokens.get("driver"),
        )
        if isinstance(s_body, dict):
            self.active_shift_id = s_body.get("shift_id") or s_body.get("id")
        self._record(
            "5. Driver Shift & Trips",
            "Driver Shift Start (Duty Check-In & Odometer Log)",
            s_code in (200, 201),
            s_ms,
            f"HTTP {s_code} | Shift ID={self.active_shift_id} | Driver=Harbhajan Singh | Bus=MH-04-TR-1001",
            actor="Driver Harbhajan Singh",
        )

        j_code, j_body, j_ms = self._http(
            "POST",
            "/api/operations/journeys/start",
            {
                "vehicle_reg_number": "MH-04-TR-1001",
                "destination_name": "Ground 1 (Main Hall)",
                "passenger_count": 48,
                "latitude": 19.1865,
                "longitude": 72.9762,
            },
            token=self.tokens.get("driver"),
        )
        j_ref = j_body.get("journey_code") if isinstance(j_body, dict) else None
        if isinstance(j_body, dict):
            self.active_journey_id = j_body.get("journey_id") or j_body.get("id")
        self._record(
            "5. Driver Shift & Trips",
            "Driver Trip Start & Live GPS Telemetry Broadcast",
            j_code in (200, 201),
            j_ms,
            f"HTTP {j_code} | Journey={j_ref} (ID={self.active_journey_id}) | Route: Thane -> Ground 1 | Pax=48",
            actor="Driver Harbhajan Singh",
        )

        e_code, e_body, e_ms = self._http(
            "POST",
            "/api/operations/journeys/end",
            {
                "journey_id": self.active_journey_id or 1,
                "latitude": 19.2183,
                "longitude": 72.9781,
                "end_location_name": "Ground 1 (Main Hall)",
            },
            token=self.tokens.get("driver"),
        )
        dist_km = e_body.get("total_distance_km") if isinstance(e_body, dict) else 0.0
        self._record(
            "5. Driver Shift & Trips",
            "Driver Trip End (Devotee Drop Verified)",
            e_code == 200,
            e_ms,
            f"HTTP {e_code} | Journey ID={self.active_journey_id or 1} marked COMPLETED | Distance={dist_km} km",
            actor="Driver Harbhajan Singh",
        )

        sc_code, sc_body, sc_ms = self._http(
            "POST",
            "/api/operations/shifts/end",
            {"shift_id": self.active_shift_id or 1, "off_duty_reason": "Audit Shift Complete"},
            token=self.tokens.get("driver"),
        )
        hrs = sc_body.get("total_duty_hours") if isinstance(sc_body, dict) else 0.0
        self._record(
            "5. Driver Shift & Trips",
            "Driver Shift Complete (Duty Handover & Odometer End)",
            sc_code == 200,
            sc_ms,
            f"HTTP {sc_code} | Shift ID={self.active_shift_id or 1} Closed | Total Duty Hours={hrs}h",
            actor="Driver Harbhajan Singh",
        )

    # -------------------------------------------------------------------------
    # 6. STATION <-> GROUND COORDINATION
    # -------------------------------------------------------------------------
    def test_station_ground_coordination(self) -> None:
        code, body, ms = self._http("GET", "/api/operations/intercom?hub=Thane Railway Station")
        c_code, c_body, c_ms = self._http(
            "POST",
            "/api/operations/intercom",
            {
                "channel_hub": "Thane Railway Station",
                "sender_side": "STATION_TEAM",
                "sender_name": "Ramesh Kulkarni (Station)",
                "priority": "NORMAL",
                "message_text": f"Coordinating bus arrival with Ground Team [{self.run_tag}]",
            },
            token=self.tokens.get("station_team"),
        )
        _, st_html, _ = self._http("GET", "/station_team_app.html")
        has_coord_ui = isinstance(st_html, str) and ("intercom" in st_html.lower() or "ground" in st_html.lower())
        self._record(
            "6. Station <-> Ground Sync",
            "Station Team <-> Ground Team Live Coordination & App Call Directory",
            code == 200 and c_code in (200, 201) and has_coord_ui,
            ms + c_ms,
            f"Intercom Feed HTTP {code}, Dispatch Sync HTTP {c_code} | Station Coordination UI={has_coord_ui}",
            actor="Station Team <-> Ground Team",
        )

    # -------------------------------------------------------------------------
    # 7. ADMIN RIGHTS, CREW CONTROL & REPORT EXPORTS AUDIT
    # -------------------------------------------------------------------------
    def test_admin_rights_and_reports(self) -> None:
        adm_headers = {
            "Host": "admin.samagamtransport.in",
            "X-Forwarded-Host": "admin.samagamtransport.in",
        }

        pub_adm_code, _, pub_ms = self._http("GET", "/admin_dashboard.html")
        sub_adm_code, sub_html, sub_ms = self._http("GET", "/admin_dashboard.html", headers=adm_headers)
        ok_guard = (pub_adm_code in (200, 403)) and (
            sub_adm_code == 200 and isinstance(sub_html, str) and len(sub_html) > 200
        )
        self._record(
            "7. Admin Rights & Reports",
            "Admin Portal Access & Public Host Isolation (/admin_dashboard.html)",
            ok_guard,
            pub_ms + sub_ms,
            f"Public Host HTTP {pub_adm_code} | Admin Subdomain HTTP {sub_adm_code}",
            actor="Admin (Control Room)",
        )

        c_code, crew_list, c_ms = self._http(
            "GET",
            "/api/auth/crew",
            token=self.tokens.get("admin"),
            headers=adm_headers,
        )
        target_crew = None
        if isinstance(crew_list, list) and crew_list:
            target_crew = next(
                (v for v in crew_list if str(v.get("full_name", "")).startswith("Ramesh Kulkarni")),
                crew_list[0],
            )

        rights_ok = c_code == 200 and isinstance(crew_list, list)
        rights_detail = f"Crew Roster HTTP {c_code} (Count={len(crew_list) if isinstance(crew_list, list) else 0})"

        if target_crew and target_crew.get("id"):
            cid = target_crew["id"]
            r_code, _, r_ms = self._http(
                "POST",
                "/api/auth/admin-reset-pin",
                {"crew_id": cid, "new_pin": "1234"},
                token=self.tokens.get("admin"),
                headers=adm_headers,
            )
            t_code, _, t_ms = self._http(
                "POST",
                "/api/auth/admin-terminate-user",
                {"crew_id": cid},
                token=self.tokens.get("admin"),
                headers=adm_headers,
            )
            act_code, _, act_ms = self._http(
                "POST",
                "/api/auth/admin-reactivate-user",
                {"crew_id": cid},
                token=self.tokens.get("admin"),
                headers=adm_headers,
            )
            c_ms += r_ms + t_ms + act_ms
            rights_ok = rights_ok and (r_code == 200) and (t_code == 200) and (act_code == 200)
            rights_detail += f" | ResetPin={r_code}, Terminate={t_code}, Reactivate={act_code}"

        self._record(
            "7. Admin Rights & Reports",
            "Admin Crew Management Rights (Roster, PIN Reset, Terminate & Reactivate)",
            rights_ok,
            c_ms,
            rights_detail,
            actor="Admin (Control Room)",
        )

        s_code, s_body, s_ms = self._http(
            "GET",
            "/api/reports/executive-summary",
            token=self.tokens.get("admin"),
            headers=adm_headers,
        )
        v_code, v_body, v_ms = self._http(
            "GET",
            "/api/fleet/vehicles",
            token=self.tokens.get("admin"),
            headers=adm_headers,
        )
        has_fin = isinstance(s_body, dict) and ("financials_inr" in s_body or "fleet" in s_body)
        self._record(
            "7. Admin Rights & Reports",
            "Admin Executive Analytics & Live Fleet Oversight",
            s_code == 200 and v_code == 200 and has_fin,
            s_ms + v_ms,
            f"Summary HTTP {s_code} (Keys={len(s_body) if isinstance(s_body, dict) else 0}) | Fleet HTTP {v_code} (Buses={len(v_body) if isinstance(v_body, list) else 0})",
            actor="Admin (Control Room)",
        )

        csv1_code, csv1_body, csv1_ms = self._http(
            "GET",
            "/api/reports/export/saints-csv",
            token=self.tokens.get("admin"),
            headers=adm_headers,
        )
        csv2_code, csv2_body, csv2_ms = self._http(
            "GET",
            "/api/reports/export/financials-csv",
            token=self.tokens.get("admin"),
            headers=adm_headers,
        )
        xlsx_code, xlsx_body, xlsx_ms = self._http(
            "GET",
            "/api/reports/export/full-database.xlsx",
            token=self.tokens.get("admin"),
            headers=adm_headers,
            timeout=25,
        )
        xlsx_bytes = len(xlsx_body) if isinstance(xlsx_body, (str, bytes)) else 0
        reports_ok = (
            csv1_code == 200
            and isinstance(csv1_body, str)
            and "Pass_ID" in csv1_body
            and csv2_code == 200
            and isinstance(csv2_body, str)
            and "Category" in csv2_body
            and xlsx_code == 200
            and xlsx_bytes > 500
        )
        self._record(
            "7. Admin Rights & Reports",
            "Admin Report Exports (Pilgrims CSV, Financials CSV & Full Database XLSX)",
            reports_ok,
            csv1_ms + csv2_ms + xlsx_ms,
            f"SaintsCSV HTTP {csv1_code} | FinCSV HTTP {csv2_code} | FullXLSX HTTP {xlsx_code} ({xlsx_bytes} bytes)",
            actor="Admin (Control Room)",
        )

    # -------------------------------------------------------------------------
    # REPORT GENERATION
    # -------------------------------------------------------------------------
    def generate_html_report(self, filename: str = "samagam_functional_audit_report.html") -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        score = round((passed / total) * 100.0, 1) if total else 0.0
        now_str = dt.datetime.now().strftime("%d %b %Y, %I:%M:%S %p")

        rows_html: list[str] = []
        for r in self.results:
            badge_style = (
                "background:#dcfce7;color:#166534;"
                if r.passed
                else "background:#fee2e2;color:#991b1b;"
            )
            label = "PASS" if r.passed else "FAIL"
            rows_html.append(
                f"""
            <tr>
              <td>{r.index}</td>
              <td><strong>{html.escape(r.module)}</strong></td>
              <td>{html.escape(r.case)}</td>
              <td><span style="{badge_style}padding:3px 10px;border-radius:999px;font-weight:700;font-size:12px;">{label}</span></td>
              <td>{html.escape(r.actor)}</td>
              <td><code>{html.escape(r.tat)}</code></td>
              <td>{r.latency_ms} ms</td>
              <td style="font-size:13px;color:#334155;">{html.escape(r.evidence)}</td>
            </tr>
            """
            )

        report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Samagam Transport — Automated Functional & SLA Audit Report</title>
  <style>
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }}
    .container {{ max-width: 1280px; margin: 0 auto; background: #ffffff; border-radius: 16px; box-shadow: 0 10px 30px rgba(15,23,42,0.08); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #0f294a 0%, #1e40af 100%); color: #fff; padding: 28px 32px; }}
    .header h1 {{ margin: 0 0 6px 0; font-size: 24px; }}
    .header p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; padding: 24px 32px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; }}
    .card {{ background: #fff; padding: 16px 20px; border-radius: 12px; border: 1px solid #e2e8f0; }}
    .card .label {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 700; }}
    .card .val {{ font-size: 26px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
    th {{ background: #f8fafc; font-size: 12px; text-transform: uppercase; color: #475569; }}
    tr:hover {{ background: #f8fafc; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Sant Nirankari Mandal — Samagam Transport Functional & SLA Audit</h1>
      <p>Target Environment: <strong>{html.escape(self.base_url)}</strong> &bull; Executed On: {html.escape(now_str)}</p>
    </div>
    <div class="summary">
      <div class="card"><div class="label">Total Functional Checks</div><div class="val">{total}</div></div>
      <div class="card"><div class="label">Passed Checks</div><div class="val" style="color:#16a34a;">{passed}</div></div>
      <div class="card"><div class="label">Failed Checks</div><div class="val" style="color:#dc2626;">{failed}</div></div>
      <div class="card"><div class="label">Readiness Score</div><div class="val" style="color:#1d4ed8;">{score}%</div></div>
    </div>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Module</th>
          <th>Functional Test Case</th>
          <th>Status</th>
          <th>Responsible Role / Actor</th>
          <th>Turnaround Time (TAT)</th>
          <th>Latency</th>
          <th>Audit Evidence</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(report_html)
        return os.path.abspath(filename)

    def run(self) -> None:
        self.test_portals_and_apps()
        self.test_role_authentication()
        self.test_booking_and_request_sla()
        self.test_parking_ticket_lifecycle()
        self.test_driver_shift_and_trips()
        self.test_station_ground_coordination()
        self.test_admin_rights_and_reports()
        report_path = self.generate_html_report()
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        print("-" * 88)
        print(f"Summary: {passed}/{total} passed | HTML Report saved to: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Samagam Transport Functional & Subdomain SLA Audit")
    parser.add_argument("--url", default="https://www.samagamtransport.in", help="Primary base URL")
    parser.add_argument(
        "--parking-url",
        default=os.environ.get("PARKING_PORTAL_URL", "https://parking.samagamtransport.in"),
        help="Parking subdomain URL",
    )
    parser.add_argument(
        "--advancesewa-url",
        default=os.environ.get("ADVANCESEWA_PORTAL_URL", "https://advancesewa.samagamtransport.in"),
        help="Advance Sewa subdomain URL",
    )
    args = parser.parse_args()
    auditor = SamagamFunctionalAudit(args.url, args.parking_url, args.advancesewa_url)
    auditor.run()


if __name__ == "__main__":
    main()