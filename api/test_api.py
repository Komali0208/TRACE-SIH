import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

# Support running directly or via pytest
try:
    from .db import engine, get_session, init_db
    from .main import app
    from .models import Alert, Camera, CameraLink, ReviewCase, Sighting, Watchlist
    from .seed import seed_database
except ImportError:
    from db import engine, get_session, init_db
    from main import app
    from models import Alert, Camera, CameraLink, ReviewCase, Sighting, Watchlist
    from seed import seed_database


@pytest.fixture(autouse=True)
def reset_database():
    """Reset and reseed database cleanly for each test."""
    SQLModel.metadata.drop_all(engine)
    init_db()
    seed_database()


@pytest.fixture
def client():
    return TestClient(app)


# --- Core Read Routes ---


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["schema_version"] == "1.0"
    assert data["mode"] == "live"
    assert "generated_at" in data


def test_snapshot_endpoint(client):
    response = client.get("/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == "1.0"
    assert "cameras" in data and len(data["cameras"]) == 8
    assert "camera_links" in data and len(data["camera_links"]) == 10
    assert "sightings" in data and len(data["sightings"]) == 182
    assert "watchlist" in data and len(data["watchlist"]) == 3
    assert "alerts" in data and len(data["alerts"]) == 5
    assert "review_cases" in data and len(data["review_cases"]) == 15
    assert "analytics" in data
    assert "summary" in data["analytics"]
    assert data["analytics"]["summary"]["total_sightings"] == 182


def test_cameras_endpoint(client):
    response = client.get("/cameras")
    assert response.status_code == 200
    data = response.json()
    assert "cameras" in data and isinstance(data["cameras"], list)
    assert "camera_links" in data and isinstance(data["camera_links"], list)
    assert len(data["cameras"]) == 8
    assert len(data["camera_links"]) == 10

    first_cam = data["cameras"][0]
    assert "id" in first_cam
    assert "name" in first_cam
    assert "lat" in first_cam
    assert "lon" in first_cam


def test_sightings_endpoint_defaults(client):
    response = client.get("/sightings")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 182
    assert data["limit"] == 100
    assert data["offset"] == 0
    assert len(data["sightings"]) == 100

    first = data["sightings"][0]
    assert "id" in first
    assert "camera_id" in first
    assert "ts" in first
    assert isinstance(first["raw_reads"], list)
    assert isinstance(first["flags"], list)


def test_sightings_endpoint_filters(client):
    # Filter by camera_id
    res_cam = client.get("/sightings?camera_id=CAM01")
    assert res_cam.status_code == 200
    cam_data = res_cam.json()
    assert all(s["camera_id"] == "CAM01" for s in cam_data["sightings"])

    # Filter by plate
    res_plate = client.get("/sightings?plate=AP32AF2669")
    assert res_plate.status_code == 200
    plate_data = res_plate.json()
    assert plate_data["total"] == 4
    assert all(s["plate_text"] == "AP32AF2669" for s in plate_data["sightings"])

    # Filter by flagged=true
    res_flagged = client.get("/sightings?flagged=true")
    assert res_flagged.status_code == 200
    flagged_data = res_flagged.json()
    assert all(len(s["flags"]) > 0 for s in flagged_data["sightings"])

    # Filter by flagged=false
    res_unflagged = client.get("/sightings?flagged=false")
    assert res_unflagged.status_code == 200
    unflagged_data = res_unflagged.json()
    assert all(len(s["flags"]) == 0 for s in unflagged_data["sightings"])


def test_plates_search_endpoint(client):
    # Search with prefix/substring
    response = client.get("/plates/search?q=AP32")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert len(data["matches"]) >= 1

    match = next(m for m in data["matches"] if m["plate_text"] == "AP32AF2669")
    assert match["sighting_count"] == 4
    assert isinstance(match["cameras"], list)
    assert "CAM01" in match["cameras"]
    assert "CAM03" in match["cameras"]

    # Search with empty query
    res_empty = client.get("/plates/search?q=")
    assert res_empty.status_code == 200
    assert res_empty.json() == {"matches": []}


def test_trajectory_speed_anomaly(client):
    response = client.get("/trajectory/AP32AF2669")
    assert response.status_code == 200
    data = response.json()
    assert data["plate_text"] == "AP32AF2669"
    assert len(data["sightings"]) == 4
    assert len(data["legs"]) == 1

    leg = data["legs"][0]
    assert leg["from_camera"] == "CAM01"
    assert leg["to_camera"] == "CAM03"
    assert leg["road_distance_m"] == 2100
    assert leg["elapsed_seconds"] == 36
    assert leg["implied_speed_kmh"] == 210.0
    assert leg["anomaly"] is True
    assert (
        leg["anomaly_reason"]
        == "Implied speed 210 km/h exceeds 150 km/h threshold — possible plate cloning"
    )


def test_trajectory_fuzzy_merge(client):
    response = client.get("/trajectory/TS48AB8163")
    assert response.status_code == 200
    data = response.json()
    assert data["plate_text"] == "TS48AB8163"
    assert isinstance(data["fuzzy_merged_from"], list)
    assert len(data["fuzzy_merged_from"]) > 0
    assert "T548AB8163" in data["fuzzy_merged_from"]


def test_trajectory_not_found(client):
    response = client.get("/trajectory/KA99XX0000")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "PLATE_NOT_FOUND"
    assert data["error"]["message"] == "No sightings for plate KA99XX0000."


# --- Review Endpoints ---


def test_review_get_embeds_full_sighting(client):
    response = client.get("/review?status=open&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert "total" in data
    assert len(data["cases"]) > 0

    first_case = data["cases"][0]
    assert "id" in first_case
    assert "sighting_id" in first_case
    assert "flag_type" in first_case
    assert "status" in first_case
    assert "sighting" in first_case
    assert first_case["sighting"] is not None

    sighting = first_case["sighting"]
    assert "id" in sighting
    assert "raw_reads" in sighting
    assert isinstance(sighting["raw_reads"], list)
    assert "crop_url" in sighting
    assert sighting["crop_url"] is not None


def test_review_post_invalid_plate_format(client):
    # Testing invalid plate regex rejection
    response = client.post(
        "/review/RVW_0001",
        json={"action": "corrected", "corrected_plate": "INVALID_PLATE_123"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_PLATE_FORMAT"


def test_review_post_correct_and_update_sighting(client):
    # RVW_0001 is for sighting SGT_0167
    corrected_plate = "DL03MN5442"
    response = client.post(
        "/review/RVW_0001",
        json={"action": "corrected", "corrected_plate": corrected_plate},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "corrected"
    assert data["corrected_plate"] == corrected_plate
    assert data["reviewed_at"] is not None

    # Verify that underlying sighting was updated so trajectory reflects it
    traj_res = client.get(f"/trajectory/{corrected_plate}")
    assert traj_res.status_code == 200
    traj_data = traj_res.json()
    assert any(s["id"] == "SGT_0167" for s in traj_data["sightings"])


def test_review_post_accept_action(client):
    response = client.post("/review/RVW_0002", json={"action": "accepted"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["reviewed_at"] is not None


# --- Alerts and Watchlist Endpoints ---


def test_alerts_get_and_acknowledge(client):
    # Fetch unacknowledged alerts
    response = client.get("/alerts?acknowledged=false")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert len(data["alerts"]) > 0

    first_alert = data["alerts"][0]
    alert_id = first_alert["id"]
    assert "sighting" in first_alert
    assert first_alert["sighting"] is not None

    # Acknowledge the alert
    ack_res = client.post(f"/alerts/{alert_id}/acknowledge")
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["id"] == alert_id
    assert ack_data["acknowledged"] is True


def test_watchlist_crud_and_live_alerts_generation(client):
    target_plate = "AP07MN8263"  # Known hero plate with 3 sightings in fixtures

    # Add plate to watchlist
    post_res = client.post(
        "/watchlist",
        json={
            "plate_text": target_plate,
            "status": "stolen",
            "reason": "FIR 999/2026",
        },
    )
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["plate_text"] == target_plate
    assert post_data["status"] == "stolen"

    # Verify that adding plate immediately created alerts for its sightings
    alerts_res = client.get("/alerts")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    matching_alerts = [
        a for a in alerts_data["alerts"] if a["plate_text"] == target_plate
    ]
    assert len(matching_alerts) >= 1

    # Verify GET /watchlist
    get_res = client.get("/watchlist")
    assert get_res.status_code == 200
    watchlist_items = get_res.json()
    assert isinstance(watchlist_items, list)
    assert any(w["plate_text"] == target_plate for w in watchlist_items)

    # Verify DELETE /watchlist/{plate}
    del_res = client.delete(f"/watchlist/{target_plate}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ok"


# --- Analytics Endpoints ---


def test_analytics_summary(client):
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_sightings" in data
    assert "unique_plates" in data
    assert "mean_confidence" in data
    assert "open_alerts" in data
    assert "open_review_cases" in data
    assert "time_range" in data


def test_analytics_travel_times(client):
    response = client.get("/analytics/travel-times")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "from_camera" in first
    assert "to_camera" in first
    assert "road_distance_m" in first
    assert "delay_ratio" in first
    assert "congested" in first

    # Verify sorted by delay_ratio descending
    for i in range(len(data) - 1):
        assert data[i]["delay_ratio"] >= data[i + 1]["delay_ratio"]


def test_analytics_heatmap(client):
    response = client.get("/analytics/heatmap?bucket=hour")
    assert response.status_code == 200
    data = response.json()
    assert "per_camera" in data and isinstance(data["per_camera"], list)
    assert "hourly" in data and isinstance(data["hourly"], list)
    assert "od_matrix" in data and isinstance(data["od_matrix"], list)


# --- Fallback / Empty DB Test ---


def test_empty_database_fallback():
    """Verify read endpoints do not 500 on an empty database."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        empty_client = TestClient(app)

        res_snap = empty_client.get("/snapshot")
        assert res_snap.status_code == 200

        res_cam = empty_client.get("/cameras")
        assert res_cam.status_code == 200
        assert res_cam.json() == {"cameras": [], "camera_links": []}

        res_sight = empty_client.get("/sightings")
        assert res_sight.status_code == 200
        assert res_sight.json() == {
            "sightings": [],
            "total": 0,
            "limit": 100,
            "offset": 0,
        }

        res_search = empty_client.get("/plates/search?q=KA05")
        assert res_search.status_code == 200
        assert res_search.json() == {"matches": []}

        res_traj = empty_client.get("/trajectory/KA05MH1234")
        assert res_traj.status_code == 404
        assert res_traj.json()["error"]["code"] == "PLATE_NOT_FOUND"

        res_review = empty_client.get("/review")
        assert res_review.status_code == 200
        assert res_review.json() == {"cases": [], "total": 0}

        res_alerts = empty_client.get("/alerts")
        assert res_alerts.status_code == 200
        assert res_alerts.json() == {"alerts": [], "total": 0}

        res_watchlist = empty_client.get("/watchlist")
        assert res_watchlist.status_code == 200
        assert res_watchlist.json() == []

        res_summary = empty_client.get("/analytics/summary")
        assert res_summary.status_code == 200

        res_tt = empty_client.get("/analytics/travel-times")
        assert res_tt.status_code == 200

        res_heat = empty_client.get("/analytics/heatmap")
        assert res_heat.status_code == 200
    finally:
        app.dependency_overrides.clear()
