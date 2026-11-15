CREATE TABLE workspace_accounts (
    user_id text PRIMARY KEY,
    deployment_id text NOT NULL REFERENCES workspace_profiles(workspace_id),
    login varchar(100) NOT NULL CHECK (login ~ '^[a-z0-9][a-z0-9_.@+-]{2,99}$'),
    password_hash text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    workspace_id text NOT NULL UNIQUE REFERENCES workspace_profiles(workspace_id),
    canonical_schema text NOT NULL,
    project_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (deployment_id, login),
    UNIQUE (user_id, deployment_id),
    UNIQUE (canonical_schema, project_id),
    CHECK (workspace_id <> deployment_id)
);
CREATE TABLE workspace_sessions (
    token_hash text PRIMARY KEY CHECK (token_hash ~ '^[a-f0-9]{64}$'),
    deployment_id text NOT NULL REFERENCES workspace_profiles(workspace_id),
    user_id text,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (user_id, deployment_id) REFERENCES workspace_accounts(user_id, deployment_id)
);
CREATE INDEX workspace_sessions_account ON workspace_sessions(deployment_id,user_id);
CREATE INDEX workspace_sessions_expiry ON workspace_sessions(expires_at);
CREATE TABLE workspace_auth_limits (
    deployment_id text NOT NULL REFERENCES workspace_profiles(workspace_id),
    bucket_hash text NOT NULL,
    attempts integer NOT NULL,
    window_started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (deployment_id, bucket_hash)
);
ALTER TABLE workspace_workers ADD COLUMN canonical_schema text;
