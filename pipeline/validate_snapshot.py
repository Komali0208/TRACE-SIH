"""Validate snapshot.json against the data contract (02-data-contract.md).

Usage::

    python -m pipeline.validate_snapshot data/snapshot.json

Checks:
- All required top-level keys present.
- Each sighting has all required fields with correct types.
- Timestamps are ISO 8601 UTC with ``Z``.
- Flags are from the closed enum.
- ``plate_text`` matches Indian regex or carries ``FORMAT_MISMATCH`` flag.
- ``video_offset_s`` is a non-negative float.
- ``raw_reads`` is a non-empty array (never truncated).
- Analytics block has required structure.
- Review cases have required fields.
"""

import json
import re
import sys
from pathlib import Path

INDIAN_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
VALID_FLAGS = {"FORMAT_MISMATCH", "UNREADABLE", "LOW_CONF_ALL_FRAMES", "SPEED_ANOMALY", "FUZZY_MERGE"}
VALID_REVIEW_STATUSES = {"open", "accepted", "corrected", "rejected"}

REQUIRED_TOP_KEYS = {
    "schema_version", "generated_at", "meta", "cameras", "camera_links",
    "sightings", "watchlist", "alerts", "review_cases", "analytics",
}

REQUIRED_SIGHTING_KEYS = {
    "id", "plate_text", "plate_confidence", "camera_id", "ts", "track_id",
    "frame_count", "raw_reads", "consensus_method", "crop_url",
    "video_offset_s", "flags", "region_guess",
}

REQUIRED_META_KEYS = {
    "source", "cameras_count", "sightings_count", "unique_plates",
    "ocr_model", "ocr_benchmark_plate_acc", "footage_note",
}


def validate(snapshot: dict) -> list[str]:
    """Return a list of validation error strings. Empty list = valid."""
    errors: list[str] = []

    # Top-level keys
    missing_top = REQUIRED_TOP_KEYS - set(snapshot.keys())
    if missing_top:
        errors.append(f"Missing top-level keys: {missing_top}")

    # Meta
    meta = snapshot.get("meta", {})
    missing_meta = REQUIRED_META_KEYS - set(meta.keys())
    if missing_meta:
        errors.append(f"Missing meta keys: {missing_meta}")

    # generated_at timestamp
    gen_at = snapshot.get("generated_at", "")
    if not ISO_UTC_RE.match(gen_at):
        errors.append(f"generated_at is not ISO 8601 UTC with Z: '{gen_at}'")

    # Cameras
    cameras = snapshot.get("cameras", [])
    if not isinstance(cameras, list):
        errors.append("'cameras' is not a list")

    cam_ids = set()
    for i, cam in enumerate(cameras):
        for key in ("id", "name", "lat", "lon", "clip_url"):
            if key not in cam:
                errors.append(f"Camera [{i}] missing key '{key}'")
        if "id" in cam:
            cam_ids.add(cam["id"])

    # Sightings
    sightings = snapshot.get("sightings", [])
    if not isinstance(sightings, list):
        errors.append("'sightings' is not a list")

    for i, s in enumerate(sightings):
        prefix = f"Sighting [{i}] ({s.get('id', '?')})"
        missing_s = REQUIRED_SIGHTING_KEYS - set(s.keys())
        if missing_s:
            errors.append(f"{prefix} missing keys: {missing_s}")
            continue

        # Type checks
        if s["plate_text"] is not None and not isinstance(s["plate_text"], str):
            errors.append(f"{prefix} plate_text is not str or null")

        if not isinstance(s["plate_confidence"], (int, float)):
            errors.append(f"{prefix} plate_confidence is not numeric")
        elif not (0.0 <= s["plate_confidence"] <= 1.0):
            errors.append(f"{prefix} plate_confidence {s['plate_confidence']} out of [0,1]")

        # Timestamp
        if not ISO_UTC_RE.match(s.get("ts", "")):
            errors.append(f"{prefix} ts is not ISO 8601 UTC with Z: '{s.get('ts')}'")

        # Camera reference
        if s["camera_id"] not in cam_ids and cam_ids:
            errors.append(f"{prefix} camera_id '{s['camera_id']}' not in cameras list")

        # video_offset_s
        if not isinstance(s["video_offset_s"], (int, float)):
            errors.append(f"{prefix} video_offset_s is not numeric")
        elif s["video_offset_s"] < 0:
            errors.append(f"{prefix} video_offset_s is negative")

        # raw_reads must be non-empty array
        raw = s.get("raw_reads", [])
        if not isinstance(raw, list):
            errors.append(f"{prefix} raw_reads is not a list")
        elif len(raw) == 0 and s["plate_text"] is not None:
            errors.append(f"{prefix} raw_reads is empty but plate_text is not null")

        # Validate each raw read
        for j, rr in enumerate(raw):
            if not isinstance(rr, dict):
                errors.append(f"{prefix} raw_reads[{j}] is not a dict")
                continue
            for rr_key in ("frame", "text", "conf"):
                if rr_key not in rr:
                    errors.append(f"{prefix} raw_reads[{j}] missing key '{rr_key}'")

        # consensus_method
        if s["consensus_method"] not in ("character_vote", "single_frame"):
            errors.append(f"{prefix} invalid consensus_method: '{s['consensus_method']}'")

        # Flags
        flags = s.get("flags", [])
        if not isinstance(flags, list):
            errors.append(f"{prefix} flags is not a list")
        else:
            for f in flags:
                if f not in VALID_FLAGS:
                    errors.append(f"{prefix} invalid flag: '{f}'")

            # Cross-check: plate_text vs FORMAT_MISMATCH
            pt = s.get("plate_text")
            if pt and not INDIAN_PLATE_RE.match(pt) and "FORMAT_MISMATCH" not in flags:
                errors.append(f"{prefix} plate_text '{pt}' fails regex but no FORMAT_MISMATCH flag")
            if pt is None and "UNREADABLE" not in flags:
                errors.append(f"{prefix} plate_text is null but no UNREADABLE flag")

    # Review cases
    review_cases = snapshot.get("review_cases", [])
    if not isinstance(review_cases, list):
        errors.append("'review_cases' is not a list")
    sighting_ids = {s["id"] for s in sightings if "id" in s}
    for i, rc in enumerate(review_cases):
        prefix = f"ReviewCase [{i}]"
        for key in ("id", "sighting_id", "flag_type", "status"):
            if key not in rc:
                errors.append(f"{prefix} missing key '{key}'")
        if rc.get("sighting_id") and rc["sighting_id"] not in sighting_ids:
            errors.append(f"{prefix} sighting_id '{rc['sighting_id']}' not found")
        if rc.get("status") and rc["status"] not in VALID_REVIEW_STATUSES:
            errors.append(f"{prefix} invalid status: '{rc['status']}'")

    # Analytics
    analytics = snapshot.get("analytics", {})
    if not isinstance(analytics, dict):
        errors.append("'analytics' is not a dict")
    else:
        summary = analytics.get("summary")
        if summary is None:
            errors.append("analytics.summary is missing")
        elif not isinstance(summary, dict):
            errors.append("analytics.summary is not a dict")
        else:
            for key in ("total_sightings", "unique_plates", "mean_confidence"):
                if key not in summary:
                    errors.append(f"analytics.summary missing key '{key}'")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.validate_snapshot <path-to-snapshot.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    errors = validate(snapshot)
    if errors:
        print(f"FAILED - Validation found {len(errors)} error(s):\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)
    else:
        sightings = snapshot.get("sightings", [])
        print(f"PASSED - Validation OK")
        print(f"   Schema version: {snapshot.get('schema_version')}")
        print(f"   Sightings: {len(sightings)}")
        print(f"   Cameras: {len(snapshot.get('cameras', []))}")
        print(f"   Review cases: {len(snapshot.get('review_cases', []))}")
        sys.exit(0)



if __name__ == "__main__":
    main()
