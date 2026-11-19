"""
[File 04] Automated System Verification Test Suite
Validates Geofencing Math, 24h Rolling Billing, Bus Sizing & Core API Endpoints.
Run: python run_system_tests.py
"""

from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.geo_service import haversine_distance_meters
from app.services.operations_service import compute_optimal_bus_mix
from app.services.contract_service import compute_rolling_contract_metrics
from app.models import HiredRollingContract

client = TestClient(app)

def run_all_tests():
    print("🧪 Running Samagam Transport System Verification Suite...\n")

    # Test 1: Haversine 2.0km Geofence Math
    dist_inside = haversine_distance_meters(19.1860, 72.9759, 19.1900, 72.9780)
    assert dist_inside < 2000.0, f"Expected <2000m, got {dist_inside}m"
    print(f"✅ [Test 1] Haversine Geofence Check passed ({dist_inside}m <= 2000m)")

    # Test 2: Greedy Bus Sizing Algorithm
    mix = compute_optimal_bus_mix(135)
    assert mix["heavy_50"] == 2 and mix["standard_35"] == 1, f"Unexpected mix: {mix}"
    print(f"✅ [Test 2] Greedy Bus Sizing passed (135 pax -> {mix['summary']})")

    # Test 3: 24-Hour Rolling Contract Billing Math (30 hours, 650 km -> 2 days, 50 extra km)
    mock_contract = HiredRollingContract(
        daily_base_rate_inr=7500.0,
        daily_quota_km=300.0,
        extra_rate_per_km_inr=25.0,
        entry_timestamp=datetime.utcnow() - timedelta(hours=30),
        entry_odometer_km=10000.0
    )
    metrics = compute_rolling_contract_metrics(mock_contract, current_odometer_km=10650.0)
    assert metrics["billed_days"] == 2
    assert metrics["excess_km"] == 50.0
    assert metrics["total_settlement_inr"] == 16250.0
    print(f"✅ [Test 3] 24h Rolling Billing passed (30h / 650km -> ₹{metrics['total_settlement_inr']})")

    # Test 4: FastAPI Health & Hubs Endpoints
    health_res = client.get("/health")
    assert health_res.status_code == 200
    hubs_res = client.get("/api/operations/hubs")
    assert hubs_res.status_code == 200 and len(hubs_res.json()) >= 14
    print(f"✅ [Test 4] API Endpoints & 14 Mumbai Hubs verified (HTTP 200)")

    print("\n🎉 ALL SYSTEM VERIFICATION TESTS PASSED!")

if __name__ == "__main__":
    run_all_tests()