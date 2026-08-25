"""
Generate specs/fixtures/snapshot.example.json — a schema-valid, entirely synthetic
dataset matching 02-data-contract.md v1.0.

Purpose: unblock the API and frontend at minute 30 so nobody waits for the CV pipeline,
and guarantee that the trajectory / review-queue / anomaly / alert features have demo
content regardless of what the real footage turns out to contain.

Run:  python specs/fixtures/generate_fixtures.py
Out:  specs/fixtures/snapshot.example.json
"""

import json
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(26127)  # deterministic — everyone gets byte-identical fixtures

PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
T0 = datetime(2026, 8, 25, 8, 0, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- cameras
# Real Bengaluru coordinates along a plausible ORR / Hosur Road corridor.
CAMERAS = [
    ("CAM01", "Silk Board Junction — North", 12.9172, 77.6229, "Hosur Road", "NB"),
    ("CAM02", "BTM Layout Signal", 12.9166, 77.6101, "Outer Ring Road", "WB"),
    ("CAM03", "Bannerghatta Road Underpass", 12.9081, 77.5975, "Bannerghatta Road", "SB"),
    ("CAM04", "Jayadeva Flyover", 12.9180, 77.5990, "Bannerghatta Road", "NB"),
    ("CAM05", "Marathahalli Bridge", 12.9591, 77.6974, "Outer Ring Road", "EB"),
    ("CAM06", "Iblur Junction", 12.9256, 77.6738, "Outer Ring Road", "EB"),
    ("CAM07", "Electronic City Toll", 12.8452, 77.6602, "Hosur Road", "SB"),
    ("CAM08", "Hebbal Flyover — South Ramp", 13.0358, 77.5970, "Bellary Road", "NB"),
]

cameras = [
    {
        "id": cid,
        "name": name,
        "lat": lat,
        "lon": lon,
        "road_name": road,
        "direction": direction,
        "clip_url": f"/clips/{cid}.mp4",
    }
    for cid, name, lat, lon, road, direction in CAMERAS
]

# Road distances in metres. Deliberately not straight-line — these drive speed analysis.
LINKS = [
    ("CAM01", "CAM02", 1450), ("CAM02", "CAM03", 1900), ("CAM03", "CAM04", 1200),
    ("CAM01", "CAM06", 5600), ("CAM06", "CAM05", 4100), ("CAM01", "CAM07", 12800),
    ("CAM04", "CAM08", 14200), ("CAM02", "CAM06", 7000), ("CAM05", "CAM08", 11500),
    ("CAM01", "CAM03", 2100),
]
camera_links = [
    {"from_camera": a, "to_camera": b, "road_distance_m": d} for a, b, d in LINKS
]
link_lookup = {(a, b): d for a, b, d in LINKS}
link_lookup.update({(b, a): d for a, b, d in LINKS})


# --------------------------------------------------------------------------- plates
STATE_CODES = ["KA", "MH", "TN", "AP", "TS", "KL", "DL", "GJ", "UP", "RJ"]
SERIES = ["AB", "MH", "CD", "AF", "K", "BX", "HR", "JJ", "MN", "PQ"]


def make_plate() -> str:
    p = (
        random.choice(STATE_CODES)
        + f"{random.randint(1, 49):02d}"
        + random.choice(SERIES)
        + f"{random.randint(1000, 9999)}"
    )
    assert PLATE_RE.match(p), p
    return p


plates = list({make_plate() for _ in range(90)})
plates.sort()

# Three plates guaranteed to appear at 3+ cameras. These are the demo plates the
# frontend pre-fills as example chips on /trajectory.
HERO_PLATES = plates[:3]
# One plate reserved for the impossible-speed anomaly.
CLONE_PLATE = plates[3]

sightings: list[dict] = []
review_cases: list[dict] = []
alerts: list[dict] = []
sgt_n = 0
rvw_n = 0
alt_n = 0


def new_sighting(plate, cam, ts, conf, flags, raw_reads, method="character_vote"):
    global sgt_n
    sgt_n += 1
    sid = f"SGT_{sgt_n:04d}"
    return {
        "id": sid,
        "plate_text": plate,
        "plate_confidence": round(conf, 3),
        "camera_id": cam,
        "ts": iso(ts),
        "track_id": random.randint(1, 400),
        "frame_count": len(raw_reads),
        "raw_reads": raw_reads,
        "consensus_method": method,
        "crop_url": f"/crops/{sid}.jpg",
        "video_offset_s": round(random.uniform(0.5, 110.0), 2),
        "flags": flags,
        "region_guess": "IN" if plate else None,
    }


def noisy(plate: str, conf: float, n: int) -> list[dict]:
    """Synthesise per-frame OCR reads that a consensus vote would resolve to `plate`."""
    confusions = {"B": "8", "8": "B", "O": "0", "0": "O", "I": "1", "1": "I", "S": "5"}
    reads = []
    for i in range(n):
        chars = list(plate)
        for _ in range(random.randint(0, 2)):
            j = random.randrange(len(chars))
            chars[j] = confusions.get(chars[j], "_")
        reads.append(
            {
                "frame": i * random.randint(2, 5) + 1,
                "text": "".join(chars),
                "conf": round(max(0.05, min(0.99, conf + random.uniform(-0.18, 0.12))), 3),
            }
        )
    # at least one clean read so the consensus is believable
    reads[random.randrange(len(reads))]["text"] = plate
    return reads


# --------------------------------------------------------------- ordinary sightings
t = T0
for plate in plates:
    n_cams = 3 if plate in HERO_PLATES else random.choice([1, 1, 2, 2, 3])
    cams = random.sample([c["id"] for c in cameras], n_cams)
    ts = T0 + timedelta(minutes=random.randint(0, 100))
    for cam in cams:
        conf = random.uniform(0.62, 0.97)
        sightings.append(
            new_sighting(plate, cam, ts, conf, [], noisy(plate, conf, random.randint(4, 14)))
        )
        ts += timedelta(seconds=random.randint(150, 600))

# ------------------------------------------------------------------- flagged cases
def add_case(sighting, flag):
    global rvw_n
    rvw_n += 1
    review_cases.append(
        {
            "id": f"RVW_{rvw_n:04d}",
            "sighting_id": sighting["id"],
            "flag_type": flag,
            "status": "open",
            "corrected_plate": None,
            "reviewed_at": None,
            "sighting": sighting,
        }
    )


# 4 x FORMAT_MISMATCH — consensus produced something that isn't a valid Indian plate
for _ in range(4):
    bad = random.choice(plates)[:-1] + random.choice("XZQ")
    conf = random.uniform(0.45, 0.70)
    s = new_sighting(
        bad, random.choice(cameras)["id"], T0 + timedelta(minutes=random.randint(0, 100)),
        conf, ["FORMAT_MISMATCH"], noisy(bad, conf, random.randint(5, 10)),
    )
    sightings.append(s)
    add_case(s, "FORMAT_MISMATCH")

# 3 x UNREADABLE — plate region found, OCR returned nothing usable on every frame
for _ in range(3):
    reads = [
        {"frame": i * 3 + 1, "text": "", "conf": round(random.uniform(0.02, 0.19), 3)}
        for i in range(random.randint(4, 9))
    ]
    s = new_sighting(
        None, random.choice(cameras)["id"], T0 + timedelta(minutes=random.randint(0, 100)),
        0.08, ["UNREADABLE"], reads, method="single_frame",
    )
    sightings.append(s)
    add_case(s, "UNREADABLE")

# 5 x LOW_CONF_ALL_FRAMES — sustained low confidence, not one noisy frame
for _ in range(5):
    p = random.choice(plates)
    conf = random.uniform(0.30, 0.53)
    s = new_sighting(
        p, random.choice(cameras)["id"], T0 + timedelta(minutes=random.randint(0, 100)),
        conf, ["LOW_CONF_ALL_FRAMES"], noisy(p, conf, random.randint(6, 12)),
    )
    sightings.append(s)
    add_case(s, "LOW_CONF_ALL_FRAMES")

# 2 x FUZZY_MERGE — edit-distance stitch across cameras (B/8 and O/0 confusion)
for variant_src in random.sample(plates, 2):
    conf = random.uniform(0.55, 0.72)
    s = new_sighting(
        variant_src, random.choice(cameras)["id"],
        T0 + timedelta(minutes=random.randint(0, 100)),
        conf, ["FUZZY_MERGE"], noisy(variant_src, conf, random.randint(5, 9)),
    )
    sightings.append(s)
    add_case(s, "FUZZY_MERGE")

# 1 x SPEED_ANOMALY — CAM01 -> CAM03 is 2100 m; 36 s implies 210 km/h
anom_t = T0 + timedelta(minutes=42)
s_a = new_sighting(CLONE_PLATE, "CAM01", anom_t, 0.91, [], noisy(CLONE_PLATE, 0.91, 9))
s_b = new_sighting(
    CLONE_PLATE, "CAM03", anom_t + timedelta(seconds=36), 0.89,
    ["SPEED_ANOMALY"], noisy(CLONE_PLATE, 0.89, 8),
)
sightings += [s_a, s_b]
add_case(s_b, "SPEED_ANOMALY")

# ------------------------------------------------------------------------ watchlist
watch_plates = random.sample([p for p in plates if p not in HERO_PLATES], 3)
watchlist = [
    {
        "plate_text": watch_plates[0], "status": "stolen",
        "reason": "FIR 442/2026 — Madiwala PS", "added_at": iso(T0 - timedelta(days=3)),
    },
    {
        "plate_text": watch_plates[1], "status": "blacklisted",
        "reason": "Repeated signal violations — enforcement flag",
        "added_at": iso(T0 - timedelta(days=11)),
    },
    {
        "plate_text": watch_plates[2], "status": "flagged",
        "reason": "Person of interest — inter-state advisory",
        "added_at": iso(T0 - timedelta(days=1)),
    },
]
watch_status = {w["plate_text"]: w["status"] for w in watchlist}

for s in sightings:
    if s["plate_text"] in watch_status:
        alt_n += 1
        alerts.append(
            {
                "id": f"ALT_{alt_n:04d}",
                "sighting_id": s["id"],
                "plate_text": s["plate_text"],
                "watchlist_status": watch_status[s["plate_text"]],
                "ts": s["ts"],
                "acknowledged": False,
                "sighting": s,
            }
        )

sightings.sort(key=lambda x: x["ts"])

# ------------------------------------------------------------------------ analytics
readable = [s for s in sightings if s["plate_text"]]
per_camera = []
for c in cameras:
    rows = [s for s in sightings if s["camera_id"] == c["id"]]
    confs = [s["plate_confidence"] for s in rows if s["plate_confidence"]]
    per_camera.append(
        {
            "camera_id": c["id"],
            "count": len(rows),
            "mean_confidence": round(sum(confs) / len(confs), 3) if confs else 0.0,
        }
    )

hourly = []
for h in range(3):
    hour_start = T0 + timedelta(hours=h)
    hour_end = hour_start + timedelta(hours=1)
    n = sum(1 for s in sightings if iso(hour_start) <= s["ts"] < iso(hour_end))
    hourly.append({"hour": iso(hour_start), "count": n})

travel_times = []
for a, b, dist in LINKS:
    median = int(dist / random.uniform(6.5, 12.0))          # ~23–43 km/h free flow
    current = int(median * random.uniform(0.85, 2.10))
    travel_times.append(
        {
            "from_camera": a, "to_camera": b, "road_distance_m": dist,
            "sample_count": random.randint(6, 34),
            "median_seconds": median, "current_seconds": current,
            "delay_ratio": round(current / median, 2),
            "congested": current / median > 1.4,
        }
    )
travel_times.sort(key=lambda x: -x["delay_ratio"])

od = {}
by_plate: dict[str, list[dict]] = {}
for s in readable:
    by_plate.setdefault(s["plate_text"], []).append(s)
for seq in by_plate.values():
    seq.sort(key=lambda x: x["ts"])
    for i in range(len(seq) - 1):
        key = (seq[i]["camera_id"], seq[i + 1]["camera_id"])
        od[key] = od.get(key, 0) + 1
od_matrix = [
    {"from_camera": a, "to_camera": b, "count": n} for (a, b), n in sorted(od.items())
]

confs = [s["plate_confidence"] for s in readable]
snapshot = {
    "schema_version": "1.0",
    "generated_at": iso(datetime.now(timezone.utc)),
    "meta": {
        "source": "fixtures",
        "cameras_count": len(cameras),
        "sightings_count": len(sightings),
        "unique_plates": len(by_plate),
        "ocr_model": "fixture-synthetic",
        "ocr_benchmark_plate_acc": None,
        "footage_note": "SYNTHETIC FIXTURE DATA — not real detections. Replaced by pipeline output at Checkpoint 2.",
        "hero_plates": HERO_PLATES,
        "clone_plate": CLONE_PLATE,
    },
    "cameras": cameras,
    "camera_links": camera_links,
    "sightings": sightings,
    "watchlist": watchlist,
    "alerts": alerts,
    "review_cases": review_cases,
    "analytics": {
        "summary": {
            "total_sightings": len(sightings),
            "unique_plates": len(by_plate),
            "mean_confidence": round(sum(confs) / len(confs), 3),
            "open_alerts": sum(1 for a in alerts if not a["acknowledged"]),
            "open_review_cases": sum(1 for r in review_cases if r["status"] == "open"),
            "time_range": {"from": sightings[0]["ts"], "to": sightings[-1]["ts"]},
        },
        "per_camera": per_camera,
        "hourly": hourly,
        "travel_times": travel_times,
        "od_matrix": od_matrix,
    },
}

out = Path(__file__).parent / "snapshot.example.json"
out.write_text(json.dumps(snapshot, indent=2))

print(f"wrote {out}")
print(
    f"  cameras={len(cameras)}  sightings={len(sightings)}  plates={len(by_plate)}  "
    f"review_cases={len(review_cases)}  alerts={len(alerts)}"
)
print(f"  hero plates (pre-fill these on /trajectory): {HERO_PLATES}")
print(f"  clone/anomaly plate: {CLONE_PLATE}")
