import math
from datetime import datetime
from app.models import HiredRollingContract

def compute_rolling_contract_metrics(contract: HiredRollingContract, current_time: datetime = None, current_odometer_km: float = None) -> dict:
    end_ts = contract.exit_timestamp or current_time or datetime.utcnow()
    delta_seconds = max(0.0, (end_ts - contract.entry_timestamp).total_seconds())
    duration_hours = round(delta_seconds / 3600.0, 2)
    billed_days = max(1, math.ceil(duration_hours / 24.0)) if duration_hours > 0 else 1
    allowed_quota_km = round(billed_days * contract.daily_quota_km, 2)
    effective_odo = contract.exit_odometer_km if contract.exit_odometer_km is not None else current_odometer_km
    if effective_odo is not None and effective_odo >= contract.entry_odometer_km:
        km_run = round(effective_odo - contract.entry_odometer_km, 2)
    else:
        km_run = round(contract.total_km_run or 0.0, 2)
    excess_km = round(max(0.0, km_run - allowed_quota_km), 2)
    base_hire_cost = round(billed_days * contract.daily_base_rate_inr, 2)
    excess_km_cost = round(excess_km * contract.extra_rate_per_km_inr, 2)
    return {
        "duration_hours": duration_hours,
        "billed_days": billed_days,
        "km_run": km_run,
        "allowed_quota_km": allowed_quota_km,
        "excess_km": excess_km,
        "base_hire_cost_inr": base_hire_cost,
        "excess_km_cost_inr": excess_km_cost,
        "total_settlement_inr": round(base_hire_cost + excess_km_cost, 2)
    }
