"""Seed demo data: users, cameras, vehicles, violations and evidence.

Idempotent: existing rows are preserved. Pass ``--force`` to reseed users'
passwords and regenerate the demo dataset.
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta

from app.core.security import hash_password
from app.db.models import AuditLog, Camera, DetectionLog, Evidence, User, Vehicle, Violation
from app.db.session import get_session, init_db
from app.services.evidence import save_evidence

USERS = [
    ("admin", "admin@traffic.local", "System Administrator", "admin", "admin123"),
    ("officer", "officer@traffic.local", "Traffic Officer", "officer", "officer123"),
    ("analyst", "analyst@traffic.local", "Data Analyst", "analyst", "analyst123"),
]

CAMERAS = [
    ("MG Road Junction", "Bengaluru, MG Road", 12.9756, 77.5999),
    ("Koramangala 4th Block", "Bengaluru, Koramangala", 12.9352, 77.6245),
    ("Indiranagar 100ft Road", "Bengaluru, Indiranagar", 12.9784, 77.6408),
    ("Jayanagar 4th Block", "Bengaluru, Jayanagar", 12.9250, 77.5938),
    ("Marathahalli Bridge", "Bengaluru, Marathahalli", 12.9565, 77.7012),
    ("Whitefield Main Road", "Bengaluru, Whitefield", 12.9698, 77.7500),
    ("Hebbal Flyover", "Bengaluru, Hebbal", 13.0358, 77.5970),
    ("Silk Board Junction", "Bengaluru, Silk Board", 12.9196, 77.6227),
]

VIOLATION_TYPES = ["speeding", "red_light", "jaywalking", "wrong_lane", "no_helmet"]
PLATES = ["KA01AB1234", "KA03CD5678", "KA05EF9012", "KA02GH3456", "TN09IJ7890", "KA51KL2345"]


def seed(force: bool = False) -> None:
    init_db()
    db = get_session()
    try:
        if force:
            db.query(DetectionLog).delete()
            db.query(Evidence).delete()
            db.query(Violation).delete()
            db.query(AuditLog).delete()
            db.query(Vehicle).delete()
            db.query(Camera).delete()
            db.query(User).delete()
            db.commit()

        for username, email, full_name, role, password in USERS:
            if not db.query(User).filter(User.username == username).first():
                db.add(
                    User(
                        username=username,
                        email=email,
                        full_name=full_name,
                        hashed_password=hash_password(password),
                        role=role,
                        is_active=True,
                    )
                )
        db.commit()

        created_cameras = []
        for idx, (name, location, lat, lon) in enumerate(CAMERAS, start=1):
            camera = db.query(Camera).filter(Camera.id == idx).first()
            if camera is None:
                camera = Camera(
                    name=name,
                    location=location,
                    lane_number=1,
                    latitude=lat,
                    longitude=lon,
                    stream_url="synthetic",
                    status="active",
                    camera_type="fixed",
                )
                db.add(camera)
            else:
                camera.camera_type = camera.camera_type or "fixed"
            created_cameras.append(camera)
        db.commit()

        vehicles = []
        for plate in PLATES:
            vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate).first()
            if vehicle is None:
                vehicle = Vehicle(
                    plate_number=plate,
                    vehicle_type=random.choice(["car", "bike", "truck"]),
                    brand=random.choice(["Toyota", "Honda", "Mahindra", "Hyundai"]),
                    model=random.choice(["Model S", "City", "Thar", "i20"]),
                    color=random.choice(["White", "Black", "Red", "Silver"]),
                    owner_name=f"Owner of {plate}",
                    registration_valid=True,
                    insurance_valid=True,
                    puc_valid=True,
                )
                db.add(vehicle)
            vehicles.append(vehicle)
        db.commit()

        counter = 0
        for camera in created_cameras:
            for _ in range(random.randint(18, 30)):
                vtype = random.choice(VIOLATION_TYPES)
                detected = datetime.utcnow() - timedelta(
                    days=random.randint(0, 20),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                counter += 1
                violation = Violation(
                    violation_id=f"V{detected.strftime('%Y%m%d%H%M%S')}{counter:05d}",
                    violation_type=vtype,
                    description=f"{vtype.replace('_', ' ').title()} detected at {camera.name}",
                    confidence=round(random.uniform(0.72, 0.98), 2),
                    status=random.choice(["pending", "issued", "review"]),
                    camera_id=camera.id,
                    vehicle_id=random.choice(vehicles).id,
                    lane_number=1,
                    location=f"{camera.location} lane 1",
                    detected_at=detected,
                )
                db.add(violation)
                db.flush()
                save_evidence(camera.id, violation.violation_id, b"\xff\xd8\xff\xe0" + b"\x00" * 64)
                db.add(
                    Evidence(
                        violation_id_fk=violation.id,
                        kind="frame",
                        path="storage/evidence/demo.jpg",
                        mime_type="image/jpeg",
                        encrypted=False,
                    )
                )
                db.add(
                    DetectionLog(
                        violation_id_fk=violation.id,
                        track_id=counter,
                        object_type="car",
                        confidence=0.9,
                        bbox={"coords": [1, 2, 3, 4]},
                        speed_kmh=random.uniform(30, 85),
                        direction=random.choice(["north", "south", "east", "west"]),
                        log_meta={"seed": True},
                    )
                )
        db.commit()
        print(f"Seeded demo data: {len(USERS)} users, {len(CAMERAS)} cameras, "
              f"{len(PLATES)} vehicles, {counter} violations")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--force", action="store_true", help="Reset and reseed all data")
    args = parser.parse_args()
    seed(force=args.force)
