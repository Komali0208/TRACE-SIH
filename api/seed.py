import json
import os
import sys
from pathlib import Path
from typing import Optional
from sqlmodel import Session, func, select

# Support running directly or as a module
try:
    from .db import engine, init_db
    from .models import Alert, Camera, CameraLink, ReviewCase, Sighting, VehicleRegistry, Watchlist
    from .registry_seed_data import MOCK_REGISTRY
except ImportError:
    from db import engine, init_db
    from models import Alert, Camera, CameraLink, ReviewCase, Sighting, VehicleRegistry, Watchlist
    from registry_seed_data import MOCK_REGISTRY


def find_snapshot_file(provided_path: Optional[str] = None) -> Path:
    if provided_path:
        p = Path(provided_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Snapshot file not found at provided path: {provided_path}")

    api_dir = Path(__file__).resolve().parent
    candidate_paths = [
        api_dir.parent / "web" / "anpr-command-web" / "public" / "snapshot.json",
        Path("web/anpr-command-web/public/snapshot.json"),
        Path("../web/anpr-command-web/public/snapshot.json"),
        Path("spec/snapshot.example.json"),
        Path("specs/fixtures/snapshot.example.json"),
        Path("spec/fixtures/snapshot.example.json"),
        Path("../spec/snapshot.example.json"),
        Path("../specs/fixtures/snapshot.example.json"),
        Path("data/snapshot.json"),
        Path("../data/snapshot.json"),
        Path("snapshot.example.json"),
        Path("snapshot.json"),
    ]

    for cand in candidate_paths:
        if cand.exists():
            return cand

    raise FileNotFoundError("Could not find snapshot JSON file in any default location.")


def seed_database(snapshot_path: Optional[str] = None) -> dict:
    file_path = find_snapshot_file(snapshot_path)
    print(f"Seeding database from: {file_path}")

    init_db()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        # Seed Cameras
        for c in data.get("cameras", []):
            camera = Camera(
                id=c["id"],
                name=c["name"],
                lat=float(c["lat"]),
                lon=float(c["lon"]),
                road_name=c.get("road_name"),
                direction=c.get("direction"),
                clip_url=c.get("clip_url"),
            )
            session.merge(camera)

        # Seed Camera Links
        for cl in data.get("camera_links", []):
            link = CameraLink(
                from_camera=cl["from_camera"],
                to_camera=cl["to_camera"],
                road_distance_m=int(cl["road_distance_m"]),
            )
            session.merge(link)

        # Seed Sightings
        for s in data.get("sightings", []):
            sighting = Sighting(
                id=s["id"],
                plate_text=s.get("plate_text"),
                plate_confidence=float(s["plate_confidence"]) if s.get("plate_confidence") is not None else None,
                camera_id=s["camera_id"],
                ts=s["ts"],
                track_id=s.get("track_id"),
                frame_count=s.get("frame_count", 1),
                raw_reads=s.get("raw_reads", []),
                consensus_method=s.get("consensus_method", "single_frame"),
                crop_url=s.get("crop_url"),
                video_offset_s=float(s["video_offset_s"]) if s.get("video_offset_s") is not None else None,
                flags=s.get("flags", []),
                region_guess=s.get("region_guess"),
            )
            session.merge(sighting)

        # Seed Watchlist
        for w in data.get("watchlist", []):
            watchlist_entry = Watchlist(
                plate_text=w["plate_text"],
                status=w["status"],
                reason=w.get("reason"),
                added_at=w["added_at"],
            )
            session.merge(watchlist_entry)

        # Seed Review Cases
        for rc in data.get("review_cases", []):
            review_case = ReviewCase(
                id=rc["id"],
                sighting_id=rc["sighting_id"],
                flag_type=rc["flag_type"],
                status=rc.get("status", "open"),
                corrected_plate=rc.get("corrected_plate"),
                reviewed_at=rc.get("reviewed_at"),
            )
            session.merge(review_case)

        # Seed Alerts
        for a in data.get("alerts", []):
            alert = Alert(
                id=a["id"],
                sighting_id=a["sighting_id"],
                plate_text=a["plate_text"],
                watchlist_status=a["watchlist_status"],
                ts=a["ts"],
                acknowledged=bool(a.get("acknowledged", False)),
            )
            session.merge(alert)

        # Seed mock vehicle registry (VAHAN-shaped). Prefer snapshot.registry; else embedded defaults.
        registry_rows = data.get("registry") or MOCK_REGISTRY
        for r in registry_rows:
            session.merge(
                VehicleRegistry(
                    plate_text=r["plate_text"],
                    owner_name=r["owner_name"],
                    registration_date=r["registration_date"],
                    registering_authority=r["registering_authority"],
                    vehicle_class=r["vehicle_class"],
                    make_model=r["make_model"],
                    fuel_type=r["fuel_type"],
                    registration_status=r["registration_status"],
                    fitness_valid_until=r["fitness_valid_until"],
                    insurance_valid_until=r["insurance_valid_until"],
                    puc_valid_until=r["puc_valid_until"],
                    is_mock_data=bool(r.get("is_mock_data", True)),
                )
            )

        session.commit()

        # Store precomputed analytics
        analytics_data = data.get("analytics", {})
        if analytics_data:
            analytics_store_path = Path(__file__).resolve().parent / "analytics_store.json"
            with open(analytics_store_path, "w", encoding="utf-8") as f_store:
                json.dump(analytics_data, f_store, indent=2)

        # Print row counts per table
        counts = {
            "cameras": session.exec(select(func.count()).select_from(Camera)).one(),
            "camera_links": session.exec(select(func.count()).select_from(CameraLink)).one(),
            "sightings": session.exec(select(func.count()).select_from(Sighting)).one(),
            "watchlist": session.exec(select(func.count()).select_from(Watchlist)).one(),
            "review_cases": session.exec(select(func.count()).select_from(ReviewCase)).one(),
            "alerts": session.exec(select(func.count()).select_from(Alert)).one(),
            "vehicle_registry": session.exec(select(func.count()).select_from(VehicleRegistry)).one(),
        }

        print("\nDatabase Seeding Complete. Row Counts per Table:")
        print("-------------------------------------------------")
        for table, count in counts.items():
            print(f"  {table:<15}: {count}")
        print("-------------------------------------------------")

        return counts


if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else None
    seed_database(target_path)
