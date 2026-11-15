CREATE TABLE workspace_profiles (
    workspace_id text PRIMARY KEY,
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
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
    primary_objective text CHECK (primary_objective IN (
        'profit_maximization','low_water_risk','household_security'
    )),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE workspace_profile_revisions (
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    version bigint NOT NULL,
    snapshot jsonb NOT NULL,
    request_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workspace_id, version)
);
