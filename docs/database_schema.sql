-- SmartRiver — PostgreSQL Database Schema
-- Run in order. Compatible with PostgreSQL 12+.

-- =====================
-- 1. Extensions (optional)
-- =====================
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================
-- 2. Enum types
-- =====================
CREATE TYPE user_role AS ENUM ('admin', 'public');
CREATE TYPE river_status AS ENUM ('clean', 'slightly_polluted', 'polluted');
CREATE TYPE prediction_type AS ENUM ('classification', 'forecast', 'anomaly');

-- =====================
-- 3. Users & Auth
-- =====================
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            user_role NOT NULL DEFAULT 'public',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- =====================
-- 4. Datasets (uploaded CSV metadata)
-- =====================
CREATE TABLE datasets (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    file_path       VARCHAR(512) NOT NULL,       -- path on server or object key
    file_size_bytes BIGINT,
    row_count       INTEGER,
    uploaded_by     INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_datasets_uploaded_by ON datasets(uploaded_by);
CREATE INDEX idx_datasets_created_at ON datasets(created_at);

-- =====================
-- 5. River stations (optional; can be derived from CSV)
-- =====================
CREATE TABLE river_stations (
    id              SERIAL PRIMARY KEY,
    station_code    VARCHAR(50) UNIQUE,
    station_name    VARCHAR(255),
    latitude        DECIMAL(10, 7),
    longitude       DECIMAL(10, 7),
    river_name      VARCHAR(255),
    state           VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_river_stations_code ON river_stations(station_code);

-- =====================
-- 6. Raw water quality readings (from CSV)
-- =====================
CREATE TABLE water_quality_readings (
    id              SERIAL PRIMARY KEY,
    dataset_id      INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    station_id      INTEGER REFERENCES river_stations(id) ON DELETE SET NULL,
    station_code    VARCHAR(50),                 -- denormalized for quick filter
    reading_date    DATE NOT NULL,
    -- DOE parameters (adjust names to match DOE CSV)
    do_mg_l         DECIMAL(10, 4),             -- Dissolved Oxygen
    bod_mg_l        DECIMAL(10, 4),             -- Biochemical Oxygen Demand
    cod_mg_l        DECIMAL(10, 4),             -- Chemical Oxygen Demand
    nh3_n_mg_l      DECIMAL(10, 4),             -- Ammoniacal Nitrogen
    tss_mg_l        DECIMAL(10, 4),             -- Total Suspended Solids
    ph              DECIMAL(5, 2),
    wqi             DECIMAL(8, 2),              -- computed in preprocessing if not in CSV
    raw_json        JSONB,                      -- any extra columns from CSV
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, station_code, reading_date)
);

CREATE INDEX idx_wqr_dataset ON water_quality_readings(dataset_id);
CREATE INDEX idx_wqr_station_date ON water_quality_readings(station_code, reading_date);
CREATE INDEX idx_wqr_reading_date ON water_quality_readings(reading_date);

-- =====================
-- 7. Processed readings (after preprocessing + WQI + features)
-- =====================
CREATE TABLE processed_readings (
    id              SERIAL PRIMARY KEY,
    dataset_id      INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    station_code    VARCHAR(50) NOT NULL,
    reading_date    DATE NOT NULL,
    wqi             DECIMAL(8, 2) NOT NULL,
    river_status    river_status,
    do_mg_l         DECIMAL(10, 4),
    bod_mg_l        DECIMAL(10, 4),
    cod_mg_l        DECIMAL(10, 4),
    nh3_n_mg_l      DECIMAL(10, 4),
    tss_mg_l        DECIMAL(10, 4),
    ph              DECIMAL(5, 2),
    features_json   JSONB,                      -- rolling stats, lags, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, station_code, reading_date)
);

CREATE INDEX idx_pr_dataset ON processed_readings(dataset_id);
CREATE INDEX idx_pr_station_date ON processed_readings(station_code, reading_date);

-- =====================
-- 8. Prediction logs (all ML outputs)
-- =====================
CREATE TABLE prediction_logs (
    id              SERIAL PRIMARY KEY,
    dataset_id      INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    prediction_type prediction_type NOT NULL,
    model_name      VARCHAR(100),               -- e.g. 'random_forest', 'lstm', 'isolation_forest'
    station_code    VARCHAR(50),
    reference_date  DATE,                       -- date for which prediction applies
    result_json     JSONB NOT NULL,             -- predictions, scores, forecast series, etc.
    triggered_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pl_type ON prediction_logs(prediction_type);
CREATE INDEX idx_pl_dataset ON prediction_logs(dataset_id);
CREATE INDEX idx_pl_station_date ON prediction_logs(station_code, reference_date);
CREATE INDEX idx_pl_created ON prediction_logs(created_at);

-- =====================
-- 9. Alerts (anomaly / early warning)
-- =====================
CREATE TABLE alerts (
    id              SERIAL PRIMARY KEY,
    prediction_log_id INTEGER REFERENCES prediction_logs(id) ON DELETE CASCADE,
    station_code    VARCHAR(50),
    message         TEXT NOT NULL,
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',  -- info, warning, critical
    is_read         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_created ON alerts(created_at);
CREATE INDEX idx_alerts_unread ON alerts(is_read) WHERE is_read = false;

-- =====================
-- 10. Triggers for updated_at
-- =====================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

CREATE TRIGGER datasets_updated_at
    BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE PROCEDURE set_updated_at();
