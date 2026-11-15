CREATE TABLE users (
    id uuid PRIMARY KEY,
    login text NOT NULL UNIQUE CHECK (login = lower(login) AND length(login) BETWEEN 3 AND 100),
    password_hash text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE farmer_profiles (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL UNIQUE REFERENCES users(id),
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    name varchar(200),
    kannada_name varchar(200),
    phone varchar(32),
    village varchar(200),
    taluk varchar(200),
    district varchar(200),
    state varchar(200),
    soil_health_card_no varchar(100),
    farmer_category text CHECK (farmer_category IN ('small_marginal','medium','large')),
    preferred_language text CHECK (preferred_language IN ('en','kn')),
    risk_tolerance text CHECK (risk_tolerance IN ('conservative','balanced','progressive')),
    primary_objective text CHECK (
        primary_objective IN ('profit_maximization','low_water_risk','household_security')
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE profile_revisions (
    profile_id uuid NOT NULL REFERENCES farmer_profiles(id),
    version integer NOT NULL,
    snapshot jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (profile_id, version)
);

CREATE TABLE auth_sessions (
    token_hash varchar(64) PRIMARY KEY CHECK (length(token_hash) = 64),
    user_id uuid REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > created_at)
);
CREATE INDEX auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX auth_sessions_expiry ON auth_sessions(expires_at);

CREATE TABLE login_attempts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bucket varchar(64) NOT NULL,
    attempted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX login_attempts_window ON login_attempts(bucket, attempted_at);
