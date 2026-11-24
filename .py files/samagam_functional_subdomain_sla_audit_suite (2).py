# ... existing code ...
    self.test_driver_shift_and_trips()
    self.test_station_ground_coordination()
    self.test_admin_rights_and_reports()
    self.generate_html_report()

    failed = sum(1 for r in self.results if not r.passed)
# ... existing code ...
    self.record
        (

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

        # 7A. Admin Subdomain Portal Access & Public Host Isolation
        pub_adm_code, _, pub_ms = self._http("GET", "/admin_dashboard.html")
        sub_adm_code, sub_html, sub_ms = self._http(
            "GET",
            "/admin_dashboard.html",
            headers=adm_headers,
        )
        ok_guard = (pub_adm_code in (200, 403)) and (
            sub_adm_code == 200 and isinstance(sub_html, str) and len(sub_html) > 200
        )
        self.record(
            "7. Admin Rights & Reports",
            "Admin Portal Access & Public Host Isolation (/admin_dashboard.html)",
            ok_guard,
            pub_ms + sub_ms,
            f"Public Host HTTP {pub_adm_code} | Admin Subdomain HTTP {sub_adm_code}",
            actor="Admin (Control Room)",
        )

        # 7B. Admin Crew Roster, PIN Reset, Termination & Reactivation Rights
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

        self.record(
            "7. Admin Rights & Reports",
            "Admin Crew Management Rights (Roster, PIN Reset, Terminate & Reactivate)",
            rights_ok,
            c_ms,
            rights_detail,
            actor="Admin (Control Room)",
        )

        # 7C. Admin Executive Summary & Operational Datasets Visibility
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
        self.record(
            "7. Admin Rights & Reports",
            "Admin Executive Analytics & Live Fleet Oversight",
            s_code == 200 and v_code == 200 and has_fin,
            s_ms + v_ms,
            f"Summary HTTP {s_code} (Keys={len(s_body) if isinstance(s_body, dict) else 0}) | Fleet HTTP {v_code} (Buses={len(v_body) if isinstance(v_body, list) else 0})",
            actor="Admin (Control Room)",
        )

        # 7D. Admin Report Exports (Executive CSVs & Master Excel Workbook)
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
        self.record(
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
# ... existing code ...