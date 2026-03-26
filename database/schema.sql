-- SmartRiver — PostgreSQL schema (full version in docs/database_schema.sql)
-- Apply: psql -U user -d smartriver -f database/schema.sql
-- Or copy from: docs/database_schema.sql

CREATE TYPE user_role AS ENUM ('admin', 'public');
CREATE TYPE river_status AS ENUM ('clean', 'slightly_polluted', 'polluted');
CREATE TYPE prediction_type AS ENUM ('classification', 'forecast', 'anomaly');

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

CREATE TABLE datasets (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    file_path       VARCHAR(512) NOT NULL,
    file_size_bytes BIGINT,
    row_count       INTEGER,
    uploaded_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE water_quality_readings (
    id              SERIAL PRIMARY KEY,
    dataset_id      INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    station_code    VARCHAR(50),
    reading_date    DATE NOT NULL,
    do_mg_l         DECIMAL(10, 4),
    bod_mg_l        DECIMAL(10, 4),
    cod_mg_l        DECIMAL(10, 4),
    nh3_n_mg_l      DECIMAL(10, 4),
    tss_mg_l        DECIMAL(10, 4),
    ph              DECIMAL(5, 2),
    wqi             DECIMAL(8, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE prediction_logs (
    id              SERIAL PRIMARY KEY,
    dataset_id      INTEGER REFERENCES datasets(id),
    prediction_type prediction_type NOT NULL,
    model_name      VARCHAR(100),
    station_code    VARCHAR(50),
    reference_date  DATE,
    result_json     JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alerts (
    id              SERIAL PRIMARY KEY,
    prediction_log_id INTEGER REFERENCES prediction_logs(id) ON DELETE CASCADE,
    station_code    VARCHAR(50),
    message         TEXT NOT NULL,
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',
    is_read         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE feedback_reports (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name            VARCHAR(255),
    email           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
