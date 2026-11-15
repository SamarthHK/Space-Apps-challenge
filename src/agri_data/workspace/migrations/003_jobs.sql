ALTER TABLE workspace_boundary_originals ADD COLUMN properties jsonb NOT NULL DEFAULT '{}';
CREATE TABLE workspace_jobs (
    job_id text PRIMARY KEY,
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    resource_id text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('import_preview','import_confirm','export')),
    status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed')),
    project_ids text[] NOT NULL,
    payload jsonb NOT NULL,
    result jsonb,
    error jsonb,
    attempts integer NOT NULL DEFAULT 0,
    lease_owner text,
    lease_until timestamptz,
    available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX workspace_jobs_queue ON workspace_jobs(workspace_id,status,available_at);
CREATE TABLE workspace_workers (
    worker_id text PRIMARY KEY,
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    project_ids text[] NOT NULL,
    protocol text NOT NULL,
    heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE workspace_imports (
    import_id text PRIMARY KEY,
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    project_id text NOT NULL,
    source_namespace text NOT NULL,
    filename text NOT NULL,
    sha256 text NOT NULL,
    preview_job_id text NOT NULL REFERENCES workspace_jobs,
    preview jsonb,
    preview_hash text,
    confirmation_hash text,
    confirmed_job_id text REFERENCES workspace_jobs,
    FOREIGN KEY (workspace_id,sha256) REFERENCES workspace_assets
);
CREATE TABLE workspace_exports (
    export_id text PRIMARY KEY,
    workspace_id text NOT NULL REFERENCES workspace_profiles,
    job_id text NOT NULL REFERENCES workspace_jobs,
    project_ids text[] NOT NULL,
    field_ids text[] NOT NULL,
    filename text NOT NULL,
    media_type text NOT NULL,
    content bytea CHECK (octet_length(content) <= 33554432),
    sha256 text
);
