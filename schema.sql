-- TRACE schema v1.0 — authoritative DDL
-- Works on both SQLite (local) and Postgres (Neon). Where they differ, Postgres wins;
-- SQLModel handles the JSON column mapping.

CREATE TABLE cameras (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    lat           DOUBLE PRECISION NOT NULL,
    lon           DOUBLE PRECISION NOT NULL,
    road_name     TEXT,
    direction     TEXT,
    clip_url      TEXT
);

CREATE TABLE camera_links (
    from_camera     TEXT NOT NULL REFERENCES cameras(id),
    to_camera       TEXT NOT NULL REFERENCES cameras(id),
    road_distance_m INTEGER NOT NULL,
    PRIMARY KEY (from_camera, to_camera)
);

CREATE TABLE sightings (
    id                TEXT PRIMARY KEY,
    plate_text        TEXT,
    plate_confidence  REAL,
    camera_id         TEXT NOT NULL REFERENCES cameras(id),
    ts                TEXT NOT NULL,
    track_id          INTEGER,
    frame_count       INTEGER DEFAULT 1,
    raw_reads         TEXT NOT NULL DEFAULT '[]',
    consensus_method  TEXT DEFAULT 'single_frame',
    crop_url          TEXT,
    video_offset_s    REAL,
    flags             TEXT NOT NULL DEFAULT '[]',
    region_guess      TEXT
);

CREATE INDEX idx_sightings_plate  ON sightings(plate_text);
CREATE INDEX idx_sightings_ts     ON sightings(ts);
CREATE INDEX idx_sightings_camera ON sightings(camera_id);

CREATE TABLE review_cases (
    id               TEXT PRIMARY KEY,
    sighting_id      TEXT NOT NULL REFERENCES sightings(id),
    flag_type        TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'open',
    corrected_plate  TEXT,
    reviewed_at      TEXT
);

CREATE INDEX idx_review_status ON review_cases(status);

CREATE TABLE watchlist (
    plate_text  TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    reason      TEXT,
    added_at    TEXT NOT NULL
);

CREATE TABLE alerts (
    id               TEXT PRIMARY KEY,
    sighting_id      TEXT NOT NULL REFERENCES sightings(id),
    plate_text       TEXT NOT NULL,
    watchlist_status TEXT NOT NULL,
    ts               TEXT NOT NULL,
    acknowledged     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_alerts_ack ON alerts(acknowledged);
