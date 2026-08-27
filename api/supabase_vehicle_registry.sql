-- Optional Supabase / Postgres migration for vehicle_registry.
-- The Next.js /api/registry/[plate] route falls back to public/snapshot.json if this table is absent.
-- Real VAHAN access requires authorised government credentials; every seeded row is mock data.

CREATE TABLE IF NOT EXISTS vehicle_registry (
    plate_text              TEXT PRIMARY KEY,
    owner_name              TEXT NOT NULL,
    registration_date       TEXT NOT NULL,
    registering_authority   TEXT NOT NULL,
    vehicle_class           TEXT NOT NULL,
    make_model              TEXT NOT NULL,
    fuel_type               TEXT NOT NULL,
    registration_status     TEXT NOT NULL,
    fitness_valid_until     TEXT NOT NULL,
    insurance_valid_until   TEXT NOT NULL,
    puc_valid_until         TEXT NOT NULL,
    is_mock_data            BOOLEAN NOT NULL DEFAULT TRUE
);

-- After creating the table, seed from web/anpr-command-web/public/snapshot.json "registry"
-- array (or run: python -m api.seed path/to/snapshot.json against a DATABASE_URL pointing here).
