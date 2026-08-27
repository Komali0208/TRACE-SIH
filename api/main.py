import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, func, select

# Support running directly or as a module
try:
    from .db import engine, get_session, init_db
    from .models import Alert, Camera, CameraLink, ReviewCase, Sighting, VehicleRegistry, Watchlist
    from .registry_seed_data import REGISTRY_SOURCE_NOTE
    from .seed import find_snapshot_file
except ImportError:
    from db import engine, get_session, init_db
    from models import Alert, Camera, CameraLink, ReviewCase, Sighting, VehicleRegistry, Watchlist
    from registry_seed_data import REGISTRY_SOURCE_NOTE
    from seed import find_snapshot_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TRACE API",
    version="1.0",
    lifespan=lifespan,
)

origins = ["http://localhost:3000"]
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request schemas
class ReviewActionRequest(BaseModel):
    action: str  # 'accepted', 'corrected', 'rejected'
    corrected_plate: Optional[str] = None


class WatchlistCreateRequest(BaseModel):
    plate_text: str
    status: str
    reason: Optional[str] = None


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(detail)}},
    )


def _fallback_snapshot() -> dict:
    try:
        snapshot_file = find_snapshot_file()
        with open(snapshot_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "meta": {
                "source": "live_api",
                "cameras_count": 0,
                "sightings_count": 0,
                "unique_plates": 0,
            },
            "cameras": [],
            "camera_links": [],
            "sightings": [],
            "watchlist": [],
            "alerts": [],
            "review_cases": [],
            "registry": [],
            "analytics": {
                "summary": {
                    "total_sightings": 0,
                    "unique_plates": 0,
                    "mean_confidence": 0.0,
                    "open_alerts": 0,
                    "open_review_cases": 0,
                    "time_range": {"from": None, "to": None},
                },
                "per_camera": [],
                "hourly": [],
                "travel_times": [],
                "od_matrix": [],
            },
        }


def get_analytics_store() -> dict:
    store_path = Path(__file__).resolve().parent / "analytics_store.json"
    if store_path.exists():
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    fallback = _fallback_snapshot()
    return fallback.get(
        "analytics",
        {
            "summary": {
                "total_sightings": 0,
                "unique_plates": 0,
                "mean_confidence": 0.0,
                "open_alerts": 0,
                "open_review_cases": 0,
                "time_range": {"from": None, "to": None},
            },
            "per_camera": [],
            "hourly": [],
            "travel_times": [],
            "od_matrix": [],
        },
    )


@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "live",
    }


@app.get("/snapshot")
def get_snapshot(session: Session = Depends(get_session)):
    try:
        cameras = session.exec(select(Camera)).all()
    except OperationalError:
        return _fallback_snapshot()

    if not cameras:
        return _fallback_snapshot()

    camera_links = session.exec(select(CameraLink)).all()
    sightings = session.exec(select(Sighting).order_by(Sighting.ts.asc())).all()
    watchlist = session.exec(select(Watchlist)).all()
    review_cases = session.exec(select(ReviewCase)).all()
    alerts = session.exec(select(Alert)).all()
    try:
        registry = session.exec(select(VehicleRegistry)).all()
    except OperationalError:
        registry = []

    sighting_map = {s.id: s.model_dump() for s in sightings}

    review_cases_out = []
    for rc in review_cases:
        rc_dict = rc.model_dump()
        rc_dict["sighting"] = sighting_map.get(rc.sighting_id)
        review_cases_out.append(rc_dict)

    alerts_out = []
    for a in alerts:
        a_dict = a.model_dump()
        a_dict["sighting"] = sighting_map.get(a.sighting_id)
        alerts_out.append(a_dict)

    analytics = get_analytics_store()

    meta = {
        "source": "live_api",
        "cameras_count": len(cameras),
        "sightings_count": len(sightings),
        "unique_plates": analytics.get("summary", {}).get("unique_plates", len(sightings)),
        "ocr_model": "cct-s-v2-global-model",
        "ocr_benchmark_plate_acc": 0.91,
        "footage_note": "TRACE live database snapshot.",
    }

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "meta": meta,
        "cameras": [c.model_dump() for c in cameras],
        "camera_links": [cl.model_dump() for cl in camera_links],
        "sightings": [s.model_dump() for s in sightings],
        "watchlist": [w.model_dump() for w in watchlist],
        "alerts": alerts_out,
        "review_cases": review_cases_out,
        "registry": [r.model_dump() for r in registry],
        "analytics": analytics,
    }


@app.get("/registry/{plate}")
def get_registry(plate: str, session: Session = Depends(get_session)):
    plate_clean = plate.strip().upper()
    try:
        row = session.exec(
            select(VehicleRegistry).where(VehicleRegistry.plate_text == plate_clean)
        ).first()
    except OperationalError:
        row = None

    if not row:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "REGISTRY_NOT_FOUND",
                    "message": f"No registry record for plate {plate_clean} in our mock dataset.",
                }
            },
        )

    out = row.model_dump()
    out["source_note"] = REGISTRY_SOURCE_NOTE
    return out


@app.get("/cameras")
def get_cameras(session: Session = Depends(get_session)):
    try:
        cameras = session.exec(select(Camera)).all()
        camera_links = session.exec(select(CameraLink)).all()
    except OperationalError:
        return {"cameras": [], "camera_links": []}

    return {
        "cameras": [c.model_dump() for c in cameras],
        "camera_links": [cl.model_dump() for cl in camera_links],
    }


@app.get("/sightings")
def get_sightings(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
    camera_id: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    flagged: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    try:
        query = select(Sighting)
        if from_:
            query = query.where(Sighting.ts >= from_)
        if to:
            query = query.where(Sighting.ts <= to)
        if camera_id:
            query = query.where(Sighting.camera_id == camera_id)
        if plate:
            query = query.where(Sighting.plate_text.ilike(f"%{plate}%"))
        if flagged is True:
            query = query.where(
                Sighting.flags != "[]",
                Sighting.flags.is_not(None),
                Sighting.flags != "",
            )
        elif flagged is False:
            query = query.where(
                (Sighting.flags == "[]")
                | (Sighting.flags.is_(None))
                | (Sighting.flags == "")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()

        results = session.exec(
            query.order_by(Sighting.ts.asc(), Sighting.id.asc())
            .offset(offset)
            .limit(limit)
        ).all()
    except OperationalError:
        return {
            "sightings": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    return {
        "sightings": [s.model_dump() for s in results],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/plates/search")
def search_plates(
    q: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    if not q or not q.strip():
        return {"matches": []}

    q_clean = q.strip().upper()
    try:
        query = select(Sighting).where(
            Sighting.plate_text.is_not(None),
            Sighting.plate_text.ilike(f"%{q_clean}%"),
        )
        sightings = session.exec(query).all()
    except OperationalError:
        return {"matches": []}

    plate_groups: dict[str, list[str]] = {}
    for s in sightings:
        if s.plate_text:
            plate_groups.setdefault(s.plate_text, []).append(s.camera_id)

    def sort_key(item: tuple[str, list[str]]):
        plate_text, cameras = item
        is_exact = plate_text == q_clean
        is_prefix = plate_text.startswith(q_clean)
        return (not is_exact, not is_prefix, -len(cameras), plate_text)

    sorted_plates = sorted(plate_groups.items(), key=sort_key)[:20]

    matches = [
        {
            "plate_text": plate_text,
            "sighting_count": len(cams),
            "cameras": sorted(list(set(cams))),
        }
        for plate_text, cams in sorted_plates
    ]

    return {"matches": matches}


@app.get("/trajectory/{plate}")
def get_trajectory(
    plate: str,
    session: Session = Depends(get_session),
):
    plate_clean = plate.strip().upper()
    try:
        sightings = session.exec(
            select(Sighting)
            .where(Sighting.plate_text == plate_clean)
            .order_by(Sighting.ts.asc(), Sighting.id.asc())
        ).all()
    except OperationalError:
        sightings = []

    if not sightings:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "PLATE_NOT_FOUND",
                    "message": f"No sightings for plate {plate_clean}.",
                }
            },
        )

    try:
        watchlist_entry = session.exec(
            select(Watchlist).where(Watchlist.plate_text == plate_clean)
        ).first()
        watchlist_status = watchlist_entry.status if watchlist_entry else None
    except OperationalError:
        watchlist_status = None

    fuzzy_merged_from = set()
    for s in sightings:
        if "FUZZY_MERGE" in s.flags and s.raw_reads:
            for r in s.raw_reads:
                text = r.get("text") if isinstance(r, dict) else None
                if text and "_" not in text and text != plate_clean:
                    fuzzy_merged_from.add(text)

    try:
        links = session.exec(select(CameraLink)).all()
    except OperationalError:
        links = []
    link_map = {(l.from_camera, l.to_camera): l.road_distance_m for l in links}

    legs = []
    for i in range(len(sightings) - 1):
        s1 = sightings[i]
        s2 = sightings[i + 1]
        pair = (s1.camera_id, s2.camera_id)
        if pair in link_map:
            road_distance_m = link_map[pair]
            try:
                t1 = datetime.fromisoformat(s1.ts.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(s2.ts.replace("Z", "+00:00"))
                elapsed_seconds = max(1, int((t2 - t1).total_seconds()))
            except Exception:
                elapsed_seconds = 1

            implied_speed_kmh = round((road_distance_m / elapsed_seconds) * 3.6, 1)
            anomaly = implied_speed_kmh > 150.0
            if anomaly:
                speed_str = (
                    str(int(implied_speed_kmh))
                    if implied_speed_kmh.is_integer()
                    else f"{implied_speed_kmh:.1f}"
                )
                anomaly_reason = (
                    f"Implied speed {speed_str} km/h exceeds 150 km/h threshold — possible plate cloning"
                )
            else:
                anomaly_reason = None

            legs.append({
                "from_sighting_id": s1.id,
                "to_sighting_id": s2.id,
                "from_camera": s1.camera_id,
                "to_camera": s2.camera_id,
                "road_distance_m": road_distance_m,
                "elapsed_seconds": elapsed_seconds,
                "implied_speed_kmh": implied_speed_kmh,
                "anomaly": anomaly,
                "anomaly_reason": anomaly_reason,
            })

    return {
        "plate_text": plate_clean,
        "sightings": [s.model_dump() for s in sightings],
        "legs": legs,
        "fuzzy_merged_from": sorted(list(fuzzy_merged_from)),
        "watchlist_status": watchlist_status,
    }


# Review Endpoints
@app.get("/review")
def get_review(
    status: Optional[str] = Query("open"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    try:
        query = select(ReviewCase)
        if status and status.lower() != "all":
            query = query.where(ReviewCase.status == status.lower())

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        cases = session.exec(query.offset(offset).limit(limit)).all()

        sighting_ids = [c.sighting_id for c in cases]
        sightings = (
            session.exec(select(Sighting).where(Sighting.id.in_(sighting_ids))).all()
            if sighting_ids
            else []
        )
        sighting_map = {s.id: s.model_dump() for s in sightings}

        cases_out = []
        for c in cases:
            c_dict = c.model_dump()
            c_dict["sighting"] = sighting_map.get(c.sighting_id)
            cases_out.append(c_dict)

        return {"cases": cases_out, "total": total}
    except OperationalError:
        return {"cases": [], "total": 0}


@app.post("/review/{case_id}")
def update_review_case(
    case_id: str,
    body: ReviewActionRequest,
    session: Session = Depends(get_session),
):
    action = body.action.lower() if body.action else ""
    if action not in ["accepted", "corrected", "rejected"]:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_ACTION",
                    "message": "Action must be one of accepted, corrected, rejected.",
                }
            },
        )

    corrected_plate = None
    if action == "corrected":
        if not body.corrected_plate or not re.match(
            r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$",
            body.corrected_plate.strip().upper(),
        ):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_PLATE_FORMAT",
                        "message": "Corrected plate does not match valid Indian plate format.",
                    }
                },
            )
        corrected_plate = body.corrected_plate.strip().upper()

    case = session.get(ReviewCase, case_id)
    if not case:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "CASE_NOT_FOUND",
                    "message": f"Review case {case_id} not found.",
                }
            },
        )

    case.status = action
    case.reviewed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if action == "corrected" and corrected_plate:
        case.corrected_plate = corrected_plate
        sighting = session.get(Sighting, case.sighting_id)
        if sighting:
            sighting.plate_text = corrected_plate
            session.add(sighting)

    session.add(case)
    session.commit()
    session.refresh(case)

    sighting = session.get(Sighting, case.sighting_id)
    case_dict = case.model_dump()
    case_dict["sighting"] = sighting.model_dump() if sighting else None
    return case_dict


# Alert Endpoints
@app.get("/alerts")
def get_alerts(
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    try:
        query = select(Alert)
        if acknowledged is not None:
            query = query.where(Alert.acknowledged == acknowledged)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        alerts = session.exec(
            query.order_by(Alert.ts.desc()).offset(offset).limit(limit)
        ).all()

        sighting_ids = [a.sighting_id for a in alerts]
        sightings = (
            session.exec(select(Sighting).where(Sighting.id.in_(sighting_ids))).all()
            if sighting_ids
            else []
        )
        sighting_map = {s.id: s.model_dump() for s in sightings}

        alerts_out = []
        for a in alerts:
            a_dict = a.model_dump()
            a_dict["sighting"] = sighting_map.get(a.sighting_id)
            alerts_out.append(a_dict)

        return {"alerts": alerts_out, "total": total}
    except OperationalError:
        return {"alerts": [], "total": 0}


@app.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    session: Session = Depends(get_session),
):
    alert = session.get(Alert, alert_id)
    if not alert:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "ALERT_NOT_FOUND",
                    "message": f"Alert {alert_id} not found.",
                }
            },
        )

    alert.acknowledged = True
    session.add(alert)
    session.commit()
    session.refresh(alert)

    sighting = session.get(Sighting, alert.sighting_id)
    alert_dict = alert.model_dump()
    alert_dict["sighting"] = sighting.model_dump() if sighting else None
    return alert_dict


# Watchlist Endpoints
@app.get("/watchlist")
def get_watchlist(session: Session = Depends(get_session)):
    try:
        entries = session.exec(
            select(Watchlist).order_by(Watchlist.added_at.desc())
        ).all()
        return [w.model_dump() for w in entries]
    except OperationalError:
        return []


@app.post("/watchlist")
def add_watchlist(
    body: WatchlistCreateRequest,
    session: Session = Depends(get_session),
):
    plate_clean = body.plate_text.strip().upper()
    added_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry = session.get(Watchlist, plate_clean)
    if entry:
        entry.status = body.status
        entry.reason = body.reason
        entry.added_at = added_at
    else:
        entry = Watchlist(
            plate_text=plate_clean,
            status=body.status,
            reason=body.reason,
            added_at=added_at,
        )
        session.add(entry)

    # Immediately scan existing sightings for matches and create alerts
    sightings = session.exec(
        select(Sighting).where(Sighting.plate_text == plate_clean)
    ).all()

    for s in sightings:
        existing = session.exec(
            select(Alert).where(Alert.sighting_id == s.id)
        ).first()
        if not existing:
            new_alert = Alert(
                id=f"ALT_{uuid.uuid4().hex[:8].upper()}",
                sighting_id=s.id,
                plate_text=plate_clean,
                watchlist_status=body.status,
                ts=s.ts,
                acknowledged=False,
            )
            session.add(new_alert)

    session.commit()
    session.refresh(entry)
    return entry.model_dump()


@app.delete("/watchlist/{plate}")
def delete_watchlist(
    plate: str,
    session: Session = Depends(get_session),
):
    plate_clean = plate.strip().upper()
    entry = session.get(Watchlist, plate_clean)
    if not entry:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "WATCHLIST_ENTRY_NOT_FOUND",
                    "message": f"Watchlist entry for plate {plate_clean} not found.",
                }
            },
        )

    session.delete(entry)
    session.commit()
    return {"status": "ok", "deleted_plate": plate_clean}


# Analytics Endpoints
@app.get("/analytics/summary")
def get_analytics_summary():
    store = get_analytics_store()
    return store.get("summary", {})


@app.get("/analytics/travel-times")
def get_analytics_travel_times():
    store = get_analytics_store()
    travel_times = store.get("travel_times", [])
    return sorted(travel_times, key=lambda x: -x.get("delay_ratio", 0.0))


@app.get("/analytics/heatmap")
def get_analytics_heatmap(bucket: Optional[str] = Query("hour")):
    store = get_analytics_store()
    return {
        "per_camera": store.get("per_camera", []),
        "hourly": store.get("hourly", []),
        "od_matrix": store.get("od_matrix", []),
    }
