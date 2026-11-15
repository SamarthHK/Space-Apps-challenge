CREATE TABLE workspace_assets (
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    filename text NOT NULL,
    media_type text NOT NULL,
    original_bytes bytea NOT NULL CHECK (octet_length(original_bytes) <= 16777216),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workspace_id,sha256)
);
CREATE TABLE workspace_field_revisions (
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    field_id text NOT NULL,
    version bigint NOT NULL CHECK (version > 0),
    snapshot jsonb NOT NULL,
    request_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workspace_id,field_id,version)
);
CREATE TABLE workspace_boundary_originals (
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    boundary_id text NOT NULL,
    geometry jsonb NOT NULL,
    PRIMARY KEY (workspace_id,boundary_id)
);
CREATE TABLE workspace_idempotency (
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    key text NOT NULL,
    operation text NOT NULL,
    request_hash text NOT NULL,
    result jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workspace_id,key)
);
