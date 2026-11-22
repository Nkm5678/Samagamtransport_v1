"""
[File 03] Standalone Database Seeder for Samagam Transport Platform
Populates Mumbai Railway/Airport Hubs, Venue Grounds, Fleet & Sample Pilgrims.
Run: python seed_test_data.py
"""

from app.database import engine, Base, SessionLocal
from app.services.seed_service import seed_initial_operations_data

def run_seeder():
    print("🌱 Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_operations_data(db)
        print("✅ Successfully seeded all 14 Mumbai Hubs, Grounds, Fleet Vehicles & Rolling Contracts!")
    except Exception as exc:
        print(f"❌ Seeding failed: {exc}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seeder()