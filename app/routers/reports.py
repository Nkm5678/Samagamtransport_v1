import csv
import io
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Saint, Vehicle, StationDemand, HiredRollingContract, MSRTCSpotCashVoucher, StationCashFloat, FuelLog, MaintenanceTicket, CrewDutyShift
from app.services.contract_service import compute_rolling_contract_metrics

router = APIRouter(prefix="/api/reports", tags=["Executive Analytics & Exports"])
IST = timezone(timedelta(hours=5, minutes=30))

@router.get("/executive-summary")
def get_executive_summary(db: Session = Depends(get_db)):
    total_saints = db.query(func.sum(Saint.group_size)).scalar() or 0
    checked_in = db.query(func.sum(Saint.group_size)).filter(Saint.status == "Checked-In at Tent").scalar() or 0
    active_c = db.query(HiredRollingContract).filter(HiredRollingContract.status == "ACTIVE_ROLLING").all()
    settled_c = db.query(HiredRollingContract).filter(HiredRollingContract.status == "SETTLED_AND_EXITED").all()
    accrued = sum(compute_rolling_contract_metrics(c)["total_settlement_inr"] for c in active_c)
    settled = sum(c.total_settlement_inr for c in settled_c)
    msrtc_spent = db.query(func.sum(MSRTCSpotCashVoucher.cash_amount_paid_inr)).scalar() or 0.0
    msrtc_float = db.query(func.sum(StationCashFloat.treasury_disbursed_amount_inr)).scalar() or 0.0
    fuel_spent = db.query(func.sum(FuelLog.total_cost_inr)).scalar() or 0.0
    maint_spent = db.query(func.sum(MaintenanceTicket.repair_cost_inr)).scalar() or 0.0
    return {
        "saints": {"total_pilgrims": int(total_saints), "total_groups": db.query(Saint).count(), "checked_in_pilgrims": int(checked_in)},
        "fleet": {"total_vehicles": db.query(Vehicle).count(), "active_in_transit": db.query(Vehicle).filter(Vehicle.status.in_(["LOADED_OUT", "EMPTY_OUT"])).count(), "maintenance_hold": db.query(Vehicle).filter(Vehicle.is_maintenance_flagged == True).count()},
        "station_queues": {"pending_demands": db.query(StationDemand).filter(StationDemand.status == "PENDING").count(), "waiting_passengers": int(db.query(func.sum(StationDemand.waiting_passenger_count)).filter(StationDemand.status == "PENDING").scalar() or 0)},
        "financials_inr": {"msrtc_imprest_balance_inr": round(msrtc_float - msrtc_spent, 2), "fuel_expense_inr": round(fuel_spent, 2), "grand_total_transport_spend_inr": round(accrued + settled + msrtc_spent + fuel_spent + maint_spent, 2)},
        "crew": {"currently_on_duty": db.query(CrewDutyShift).filter(CrewDutyShift.is_currently_on_duty == True).count()}
    }

def build_duty_excel_bytes(db: Session) -> bytes:
    from openpyxl import Workbook
    shifts = db.query(CrewDutyShift).order_by(CrewDutyShift.duty_start_time.asc()).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Duty log"
    ws.append(["#", "Crew / Driver", "Role", "Mobile", "Hub", "Start (IST)", "End (IST)", "Hours", "Status"])
    for idx, s in enumerate(shifts, 1):
        end_dt = s.duty_end_time or datetime.utcnow()
        hrs = round(max(0.0, (end_dt - s.duty_start_time).total_seconds()) / 3600.0, 2)
        ws.append([idx, s.crew_name, s.crew_role, s.crew_phone, s.station_hub, str(s.duty_start_time), str(s.duty_end_time or ""), hrs, "On duty" if s.is_currently_on_duty else "Completed"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

@router.get("/export/shifts.xlsx")
def export_duty_shifts_xlsx(db: Session = Depends(get_db)):
    return StreamingResponse(io.BytesIO(build_duty_excel_bytes(db)), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=samagam_duty_log.xlsx"})

@router.get("/export/saints-csv")
def export_saints_csv(db: Session = Depends(get_db)):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Pass_ID", "Name", "Phone", "Group_Size", "Arrival_Hub", "Ground", "Tent", "Status"])
    for s in db.query(Saint).all():
        w.writerow([f"SMG-{s.id:05d}", s.full_name, s.contact_phone, s.group_size, s.arrival_hub, s.assigned_ground, s.assigned_tent, s.status])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=samagam_saints.csv"})

@router.get("/export/financials-csv")
def export_financials_csv(db: Session = Depends(get_db)):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Type", "Code", "Amount_INR", "Status"])
    for c in db.query(HiredRollingContract).all():
        w.writerow(["24H_CONTRACT", c.contract_code, compute_rolling_contract_metrics(c)["total_settlement_inr"], c.status])
    for v in db.query(MSRTCSpotCashVoucher).all():
        w.writerow(["MSRTC_CASH", v.voucher_number, v.cash_amount_paid_inr, "VERIFIED" if v.is_verified_at_gate else "PENDING"])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=samagam_financials.csv"})
