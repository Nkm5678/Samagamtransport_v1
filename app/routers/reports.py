import csv
import io
import os
import sys
from datetime import datetime, timedelta, timezone

_THIS_FILE = os.path.abspath(__file__)
_CANDIDATE_ROOTS = [
    os.path.abspath(os.path.join(os.path.dirname(_THIS_FILE), "..", "..")),
    r"C:\narendra\SamagamtransportV1",
]
for _root in _CANDIDATE_ROOTS:
    if os.path.isdir(os.path.join(_root, "app")) and _root not in sys.path:
        sys.path.insert(0, _root)

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, inspect, text
import app.models as models
from app.database import get_db, engine
from app.models import (
    Saint, Vehicle, StationDemand, HiredRollingContract,
    MSRTCSpotCashVoucher, StationCashFloat, FuelLog,
    MaintenanceTicket, CrewDutyShift,
    PickupDropVehicleRequest, DepartmentVehicleRequisition, SevaDonatedVehicle,
    DevoteeParkingPass, Volunteer, TurnaroundMovement,
    GroundStationIntercom, Journey, TelemetryPing, EmailOTP
)
from app.services.contract_service import compute_rolling_contract_metrics

router = APIRouter(prefix="/api/reports", tags=["Executive Analytics & Exports"])

IST = timezone(timedelta(hours=5, minutes=30))


@router.get("/executive-summary")
def get_executive_summary(db: Session = Depends(get_db)):
    total_saints = db.query(func.sum(Saint.group_size)).scalar() or 0
    total_jathas = db.query(Saint).count()
    checked_in_saints = db.query(func.sum(Saint.group_size)).filter(Saint.status == "Checked-In at Tent").scalar() or 0

    total_vehicles = db.query(Vehicle).count()
    active_transit = db.query(Vehicle).filter(Vehicle.status.in_(["LOADED_OUT", "EMPTY_OUT"])).count()
    maintenance_hold = db.query(Vehicle).filter(Vehicle.is_maintenance_flagged == True).count()

    pending_demands = db.query(StationDemand).filter(StationDemand.status == "PENDING").count()
    waiting_pax = db.query(func.sum(StationDemand.waiting_passenger_count)).filter(StationDemand.status == "PENDING").scalar() or 0

    active_contracts = db.query(HiredRollingContract).filter(HiredRollingContract.status == "ACTIVE_ROLLING").all()
    settled_contracts = db.query(HiredRollingContract).filter(HiredRollingContract.status == "SETTLED_AND_EXITED").all()
    accrued_rolling_inr = sum(compute_rolling_contract_metrics(c)["total_settlement_inr"] for c in active_contracts)
    settled_rolling_inr = sum(c.total_settlement_inr for c in settled_contracts)

    msrtc_spent_inr = db.query(func.sum(MSRTCSpotCashVoucher.cash_amount_paid_inr)).scalar() or 0.0
    msrtc_float_inr = db.query(func.sum(StationCashFloat.treasury_disbursed_amount_inr)).scalar() or 0.0
    fuel_spent_inr = db.query(func.sum(FuelLog.total_cost_inr)).scalar() or 0.0
    maintenance_spent_inr = db.query(func.sum(MaintenanceTicket.repair_cost_inr)).scalar() or 0.0

    on_duty_crew = db.query(CrewDutyShift).filter(CrewDutyShift.is_currently_on_duty == True).count()
    pickup_drop_count = db.query(PickupDropVehicleRequest).count()
    dept_req_count = db.query(DepartmentVehicleRequisition).count()
    parking_parked = db.query(DevoteeParkingPass).filter(DevoteeParkingPass.status == "PARKED_INSIDE").count()

    return {
        "saints": {
            "total_pilgrims": int(total_saints),
            "total_groups": total_jathas,
            "checked_in_pilgrims": int(checked_in_saints)
        },
        "fleet": {
            "total_vehicles": total_vehicles,
            "active_in_transit": active_transit,
            "maintenance_hold": maintenance_hold
        },
        "demands": {
            "pending_station_requests": pending_demands,
            "waiting_pilgrims": int(waiting_pax),
            "pickup_drop_requests": pickup_drop_count,
            "dept_requisitions": dept_req_count,
            "parking_inside": parking_parked
        },
        "financials_inr": {
            "accrued_24h_rolling_contracts": round(accrued_rolling_inr, 2),
            "settled_24h_rolling_contracts": round(settled_rolling_inr, 2),
            "msrtc_cash_disbursed_float": round(msrtc_float_inr, 2),
            "msrtc_vouchers_spent": round(msrtc_spent_inr, 2),
            "fuel_logs_total": round(fuel_spent_inr, 2),
            "maintenance_repairs_total": round(maintenance_spent_inr, 2)
        },
        "crew": {
            "on_duty_now": on_duty_crew,
            "total_volunteers": db.query(Volunteer).count()
        }
    }


@router.get("/admin-overview")
def get_admin_reports_overview(db: Session = Depends(get_db)):
    """Returns live tables for all reports in the Admin Control Room UI."""
    summary = get_executive_summary(db)
    recent_pd = db.query(PickupDropVehicleRequest).order_by(PickupDropVehicleRequest.id.desc()).limit(25).all()
    recent_dept = db.query(DepartmentVehicleRequisition).order_by(DepartmentVehicleRequisition.id.desc()).limit(25).all()
    recent_parking = db.query(DevoteeParkingPass).order_by(DevoteeParkingPass.id.desc()).limit(25).all()
    recent_contracts = db.query(HiredRollingContract).order_by(HiredRollingContract.id.desc()).limit(25).all()
    recent_msrtc = db.query(MSRTCSpotCashVoucher).order_by(MSRTCSpotCashVoucher.id.desc()).limit(25).all()

    return {
        "summary": summary,
        "pickup_drop": [
            {
                "code": r.request_code,
                "hub": r.transit_hub,
                "pax": r.passenger_count,
                "requester": f"{r.requester_name} ({r.requester_phone})",
                "status": r.status,
                "assigned_vehicle": r.assigned_vehicle_reg or "-"
            }
            for r in recent_pd
        ],
        "dept_requisitions": [
            {
                "code": r.requisition_code,
                "department": r.department_name,
                "vehicle_type": f"{r.quantity_needed}x {r.required_vehicle_type}",
                "requester": f"{r.requester_name} ({r.requester_phone})",
                "status": r.status,
                "allocated_vehicle": r.allocated_vehicle_reg or "-"
            }
            for r in recent_dept
        ],
        "parking_passes": [
            {
                "token": p.parking_token,
                "plate": p.vehicle_reg_number,
                "owner": f"{p.owner_name} ({p.owner_phone})",
                "zone": p.parking_zone,
                "status": p.status
            }
            for p in recent_parking
        ],
        "contracts": [
            {
                "code": c.contract_code,
                "plate": c.vehicle.vehicle_reg_number if c.vehicle else "-",
                "vendor": c.vendor_agency_name,
                "settlement_inr": compute_rolling_contract_metrics(c)["total_settlement_inr"],
                "status": c.status
            }
            for c in recent_contracts
        ],
        "msrtc_vouchers": [
            {
                "voucher": v.voucher_number,
                "station": v.station_hub,
                "etm": v.etm_receipt_number,
                "amount_inr": v.cash_amount_paid_inr,
                "verified": v.is_verified_at_gate
            }
            for v in recent_msrtc
        ]
    }


@router.post("/admin-purge-test-data")
def purge_test_data_from_database(
    data: dict | None = None,
    x_driver_token: str = Header(None),
    x_session_token: str = Header(None),
    db: Session = Depends(get_db)
):
    """Cleans test/dummy records across operational & test tables while preserving hub master data and Admin account."""
    payload = data or {}
    mode = str(payload.get("mode") or "ALL_OPERATIONAL").upper().strip()

    deleted_counts = {}

    if mode == "ALL_OPERATIONAL":
        models_to_clear = [
            ("telemetry_pings", TelemetryPing),
            ("journeys", Journey),
            ("turnaround_movements", TurnaroundMovement),
            ("station_demands", StationDemand),
            ("pickup_drop_requests", PickupDropVehicleRequest),
            ("dept_requisitions", DepartmentVehicleRequisition),
            ("seva_donated_vehicles", SevaDonatedVehicle),
            ("devotee_parking_passes", DevoteeParkingPass),
            ("msrtc_vouchers", MSRTCSpotCashVoucher),
            ("station_cash_floats", StationCashFloat),
            ("hired_rolling_contracts", HiredRollingContract),
            ("fuel_logs", FuelLog),
            ("maintenance_tickets", MaintenanceTicket),
            ("crew_duty_shifts", CrewDutyShift),
            ("ground_station_intercom", GroundStationIntercom),
            ("email_otps", EmailOTP),
            ("saints", Saint),
        ]
        adv_model = getattr(models, "AdvanceSewaVehicleRequest", None)
        if adv_model is not None:
            models_to_clear.append(("advance_sewa_requests", adv_model))
        for label, model_cls in models_to_clear:
            try:
                cnt = db.query(model_cls).delete(synchronize_session=False)
                deleted_counts[label] = cnt
            except Exception:
                db.rollback()

        try:
            v_del = db.query(Vehicle).filter(
                (Vehicle.vehicle_reg_number.like("MH-04-AT-%"))
                | (Vehicle.vehicle_reg_number.like("MH-04-TR-100%"))
                | (Vehicle.onboarding_team == "Automation Suite")
                | (Vehicle.registered_by == "QA Bot")
            ).delete(synchronize_session=False)
            deleted_counts["test_vehicles"] = v_del
        except Exception:
            db.rollback()

        try:
            vol_del = db.query(Volunteer).filter(
                (Volunteer.mobile_number != "9820110001")
                & (
                    Volunteer.mobile_number.like("980032743%")
                    | Volunteer.email.like("auto.test.%")
                    | Volunteer.full_name.like("Auto Test%")
                    | Volunteer.full_name.in_([
                        "Ramesh Kulkarni", "Suresh Patil", "Mahesh Shinde",
                        "Dinesh Jadhav", "Prakash Nair", "Driver Ajay Sharma"
                    ])
                )
            ).delete(synchronize_session=False)
            deleted_counts["test_volunteers"] = vol_del
        except Exception:
            db.rollback()
    else:
        deleted_counts["test_vehicles"] = db.query(Vehicle).filter(
            (Vehicle.vehicle_reg_number.like("MH-04-AT-%"))
            | (Vehicle.onboarding_team == "Automation Suite")
        ).delete(synchronize_session=False)
        deleted_counts["test_parking"] = db.query(DevoteeParkingPass).filter(
            (DevoteeParkingPass.owner_email.like("%audit%"))
            | (DevoteeParkingPass.owner_email.like("auto.test.%"))
        ).delete(synchronize_session=False)
        deleted_counts["test_volunteers"] = db.query(Volunteer).filter(
            (Volunteer.mobile_number != "9820110001")
            & (Volunteer.mobile_number.like("980032743%") | Volunteer.email.like("auto.test.%"))
        ).delete(synchronize_session=False)

    db.commit()
    return {
        "status": "CLEANED",
        "mode": mode,
        "deleted_counts": deleted_counts
    }


@router.get("/admin-db-tables")
def list_admin_database_tables():
    """Lists all database tables and their row counts for the Admin SQL Console."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    summary = []
    with engine.connect() as conn:
        for t in sorted(tables):
            try:
                cnt = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
            except Exception:
                cnt = -1
            summary.append({"table": t, "rows": cnt})
    return {"dialect": engine.dialect.name, "tables": summary}


@router.post("/admin-sql-query")
def execute_admin_sql_query(data: dict):
    """Executes an Admin SQL query (SELECT, UPDATE, DELETE, INSERT, ALTER) directly on the active database."""
    sql = str(data.get("sql") or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")

    lowered = sql.lstrip("(").lower()
    if any(lowered.startswith(bad) for bad in ("drop database", "truncate database")):
        raise HTTPException(status_code=403, detail="Database-level DROP/TRUNCATE is blocked for safety.")

    try:
        with engine.begin() as conn:
            result = conn.execute(text(sql))
            if result.returns_rows:
                cols = list(result.keys())
                raw_rows = result.fetchmany(500)
                rows = [
                    {col: (val.isoformat() if hasattr(val, "isoformat") else val) for col, val in zip(cols, r)}
                    for r in raw_rows
                ]
                return {
                    "status": "OK",
                    "type": "SELECT",
                    "columns": cols,
                    "row_count": len(rows),
                    "rows": rows,
                }
            return {
                "status": "OK",
                "type": "WRITE",
                "affected_rows": result.rowcount if result.rowcount is not None else 0,
                "columns": [],
                "rows": [],
            }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SQL Error: {exc}")
        ws7.append([v.voucher_number, v.station_hub, v.vehicle.vehicle_reg_number if v.vehicle else "", v.msrtc_depot_name, v.conductor_name, v.cash_amount_paid_inr, v.etm_receipt_number, v.passenger_headcount, v.paid_by_volunteer_name, to_ist_str(v.paid_at), "YES" if v.is_verified_at_gate else "NO", v.verified_by_ground_sevadar or ""])

    ws8 = wb.create_sheet("8_Station_Cash_Floats")
    ws8.append(["ID", "Station Hub", "Amount Disbursed (INR)", "Issued By", "Issued To", "Notes", "Created (IST)"])
    for f in db.query(StationCashFloat).order_by(StationCashFloat.id.desc()).all():
        ws8.append([f.id, f.station_hub, f.treasury_disbursed_amount_inr, f.issued_by, f.issued_to_coordinator, f.notes or "", to_ist_str(f.created_at)])

    ws9 = wb.create_sheet("9_Station_Demands")
    ws9.append(["Demand Code", "Hub Name", "Waiting Pax", "Recommended Buses", "Priority", "Status", "Requested By", "Notes", "Created (IST)"])
    for d in db.query(StationDemand).order_by(StationDemand.id.desc()).all():
        ws9.append([d.demand_code, d.hub_name, d.waiting_passenger_count, d.recommended_buses or "", d.priority, d.status, d.requested_by, d.notes or "", to_ist_str(d.created_at)])

    ws10 = wb.create_sheet("10_Pilgrim_Manifest")
    ws10.append(["Pass ID", "Full Name", "Spiritual Order", "Mobile", "Group Size", "Arrival Hub", "Arrival Mode", "Train/Flight", "Arrival Time", "Ground", "Tent", "Departure Hub", "Departure Time", "Status"])
    for s in db.query(Saint).order_by(Saint.id.asc()).all():
        ws10.append([f"SMG-{s.id:05d}", s.full_name, s.spiritual_order or "", s.contact_phone, s.group_size, s.arrival_hub, s.arrival_mode, s.arrival_transit_number or "", s.arrival_datetime, s.assigned_ground, s.assigned_tent, s.departure_hub, s.departure_datetime, s.status])

    ws11 = wb.create_sheet("11_Crew_Duty_Shifts")
    ws11.append(["ID", "Role", "Crew Name", "Mobile", "Hub", "Start (IST)", "End (IST)", "Total Hours", "On Duty Now", "Off Duty Reason"])
    for s in db.query(CrewDutyShift).order_by(CrewDutyShift.id.desc()).all():
        ws11.append([s.id, s.crew_role, s.crew_name, s.crew_phone, s.station_hub, to_ist_str(s.duty_start_time), to_ist_str(s.duty_end_time), s.total_duty_hours, "YES" if s.is_currently_on_duty else "NO", s.off_duty_reason or ""])

    ws12 = wb.create_sheet("12_Fuel_Logs")
    ws12.append(["ID", "Vehicle Reg", "Liters", "Rate/Liter", "Total Cost (INR)", "Fuel Station", "Odometer KM", "Slip No", "Filled By", "Filled At (IST)"])
    for f in db.query(FuelLog).order_by(FuelLog.id.desc()).all():
        ws12.append([f.id, f.vehicle.vehicle_reg_number if f.vehicle else "", f.liters_filled, f.rate_per_liter, f.total_cost_inr, f.fuel_station_name, f.current_odometer_km or "", f.receipt_voucher_no or "", f.filled_by, to_ist_str(f.filled_at)])

    ws13 = wb.create_sheet("13_Maintenance")
    ws13.append(["Ticket Code", "Vehicle Reg", "Category", "Severity", "Description", "Reported By", "Status", "Repair Cost (INR)", "Reported At (IST)"])
    for m in db.query(MaintenanceTicket).order_by(MaintenanceTicket.id.desc()).all():
        ws13.append([m.ticket_code, m.vehicle.vehicle_reg_number if m.vehicle else "", m.issue_category, m.severity, m.description, m.reported_by, m.status, m.repair_cost_inr, to_ist_str(m.reported_at)])

    ws14 = wb.create_sheet("14_Parking_Passes")
    ws14.append(["Token", "Vehicle Reg", "Category", "Owner Name", "Owner Phone", "Zone", "Key Mode", "Entry (IST)", "Exit (IST)", "Status"])
    for p in db.query(DevoteeParkingPass).order_by(DevoteeParkingPass.id.desc()).all():
        ws14.append([p.parking_token, p.vehicle_reg_number, p.vehicle_category, p.owner_name, p.owner_phone, p.parking_zone, p.key_custody_mode, to_ist_str(p.entry_timestamp), to_ist_str(p.exit_timestamp), p.status])

    ws15 = wb.create_sheet("15_Crew_Volunteers")
    ws15.append(["Volunteer Code", "Full Name", "Mobile", "Email", "Unit", "Branch", "Duty Location", "System Role", "Active", "Registered (IST)"])
    for v in db.query(Volunteer).order_by(Volunteer.id.asc()).all():
        ws15.append([v.volunteer_code, v.full_name, v.mobile_number, v.email or "", v.unit_number, v.branch_name, v.duty_location, v.system_role, "YES" if v.is_active else "NO", to_ist_str(v.registered_at)])

    for ws in wb.worksheets:
        for cell in ws[1]:
            cell.font, cell.fill, cell.alignment = hfont, hfill, Alignment(horizontal="center")
        for col in ws.columns:
            ws.column_dimensions[get_column_letter(col[0].column)].width = 20
        ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"samagam_full_database_{datetime.now(IST).strftime('%Y-%m-%d_%H%M')}.xlsx"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/saints-csv")
def export_saints_csv(db: Session = Depends(get_db)):
    saints = db.query(Saint).order_by(Saint.id.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Pass_ID", "Saint_Name", "Spiritual_Order", "Phone", "Group_Size",
        "Arrival_Hub", "Arrival_Mode", "Train_Flight_No", "Arrival_Time",
        "Assigned_Ground", "Assigned_Tent", "Departure_Hub", "Departure_Time", "Status"
    ])
    for s in saints:
        writer.writerow([
            f"SMG-{s.id:05d}", s.full_name, s.spiritual_order, s.contact_phone, s.group_size,
            s.arrival_hub, s.arrival_mode, s.arrival_transit_number, s.arrival_datetime,
            s.assigned_ground, s.assigned_tent, s.departure_hub, s.departure_datetime, s.status
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=samagam_saints_manifest.csv"}
    )


@router.get("/export/financials-csv")
def export_financials_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Voucher_Or_Contract_Code", "Vehicle_Reg", "Vendor_Or_Depot", "Hub_Or_Gate", "Amount_INR", "Status"])

    for c in db.query(HiredRollingContract).all():
        m = compute_rolling_contract_metrics(c)
        writer.writerow([
            "24H_ROLLING_CONTRACT", c.contract_code,
            c.vehicle.vehicle_reg_number if c.vehicle else "N/A",
            c.vendor_agency_name, c.entry_gate_hub, m["total_settlement_inr"], c.status
        ])

    for v in db.query(MSRTCSpotCashVoucher).all():
        writer.writerow([
            "MSRTC_SPOT_CASH", v.voucher_number,
            v.vehicle.vehicle_reg_number if v.vehicle else "N/A",
            v.msrtc_depot_name, v.station_hub, v.cash_amount_paid_inr,
            "VERIFIED_AT_GATE" if v.is_verified_at_gate else "PENDING_GATE_CHECK"
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=samagam_transport_financial_audit.csv"}
    )