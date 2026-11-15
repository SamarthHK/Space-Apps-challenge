CREATE TABLE projects (
    project_id text PRIMARY KEY,
    name text NOT NULL,
    metadata jsonb NOT NULL
);
CREATE TABLE source_assets (
    source_asset_id text PRIMARY KEY,
    raw_sha256 text NOT NULL CHECK (raw_sha256 ~ '^[a-f0-9]{64}$'),
    path text NOT NULL,
    origin text NOT NULL,
    retrieved_at timestamptz NOT NULL,
    metadata jsonb NOT NULL
);
CREATE TABLE fields (
    field_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects,
    source_identifier text NOT NULL,
    metadata jsonb NOT NULL,
    UNIQUE(project_id, source_identifier)
);
CREATE TABLE field_boundaries (
    boundary_id text PRIMARY KEY,
    field_id text NOT NULL REFERENCES fields,
    source_asset_id text NOT NULL REFERENCES source_assets,
    geometry geometry(Geometry, 4326) NOT NULL,
    original boolean NOT NULL,
    repair_notes text,
    CHECK (ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)),
    CHECK (GeometryType(geometry) IN ('POLYGON', 'MULTIPOLYGON'))
);
CREATE INDEX field_boundaries_geometry_idx ON field_boundaries USING gist (geometry);
CREATE TABLE feature_requirements (
    feature_id text PRIMARY KEY CHECK (feature_id ~ '^F[0-9]{2}-[0-9]{3}$'),
    definition jsonb NOT NULL
);
CREATE TABLE variables (
    variable_id text PRIMARY KEY,
    feature_id text NOT NULL REFERENCES feature_requirements,
    definition jsonb NOT NULL
);
CREATE TABLE data_sources (
    source_id text PRIMARY KEY,
    definition jsonb NOT NULL
);
CREATE TABLE datasets (
    dataset_id text PRIMARY KEY,
    source_id text NOT NULL REFERENCES data_sources,
    version text NOT NULL,
    definition jsonb NOT NULL
);
CREATE TABLE source_bindings (
    source_binding_id text PRIMARY KEY,
    variable_id text NOT NULL REFERENCES variables,
    dataset_id text NOT NULL REFERENCES datasets,
    locator text NOT NULL,
    definition jsonb NOT NULL
);
CREATE TABLE extraction_jobs (
    extraction_job_id text PRIMARY KEY,
    source_asset_id text NOT NULL REFERENCES source_assets,
    requested_at timestamptz NOT NULL,
    completed_at timestamptz,
    status text NOT NULL CHECK (status IN ('in_progress','failed','blocked','complete')),
    context jsonb NOT NULL
);
CREATE TABLE processing_runs (
    processing_run_id text PRIMARY KEY,
    code_sha256 text NOT NULL,
    config_sha256 text NOT NULL,
    created_at timestamptz NOT NULL,
    metadata jsonb NOT NULL
);
CREATE TABLE observations (
    observation_id text PRIMARY KEY,
    schema_version text NOT NULL,
    variable_id text NOT NULL REFERENCES variables,
    feature_id text NOT NULL REFERENCES feature_requirements,
    subject_id text NOT NULL,
    field_id text REFERENCES fields,
    source_id text REFERENCES data_sources,
    dataset_id text REFERENCES datasets,
    source_binding_id text REFERENCES source_bindings,
    source_asset_id text REFERENCES source_assets,
    extraction_job_id text NOT NULL REFERENCES extraction_jobs,
    value_numeric double precision,
    value_text text,
    value_boolean boolean,
    value_date date,
    value_geometry geometry(Geometry,4326),
    value_series_ref text,
    observed_at timestamp,
    observed_timezone text,
    period_start timestamp,
    period_end timestamp,
    retrieved_at timestamptz,
    depth_top_cm double precision,
    depth_bottom_cm double precision,
    standardized_unit text NOT NULL,
    evidence_type text NOT NULL CHECK (evidence_type IN (
        'measured','surveyed','published_parameter','published_recommendation',
        'satellite','modelled_product','reanalysis','projection','derived'
    )),
    validation_status text NOT NULL CHECK (validation_status IN ('pending','accepted','rejected')),
    record jsonb NOT NULL,
    CHECK (num_nonnulls(value_numeric,value_text,value_boolean,value_date,value_geometry,value_series_ref)=1),
    CHECK (value_numeric IS NULL OR value_numeric NOT IN ('NaN'::float8,'Infinity'::float8,'-Infinity'::float8)),
    CHECK ((depth_top_cm IS NULL AND depth_bottom_cm IS NULL) OR
           (depth_top_cm IS NOT NULL AND depth_bottom_cm IS NOT NULL AND depth_top_cm >= 0 AND depth_bottom_cm > depth_top_cm)),
    CHECK ((period_start IS NULL AND period_end IS NULL) OR
           (period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start))
);
CREATE INDEX observations_context_idx ON observations(field_id, variable_id, observed_at);
CREATE TABLE observation_lineage (
    child_observation_id text NOT NULL REFERENCES observations,
    parent_observation_id text NOT NULL REFERENCES observations,
    PRIMARY KEY (child_observation_id,parent_observation_id),
    CHECK (child_observation_id <> parent_observation_id)
);
CREATE TABLE quarantined_records (
    quarantine_id text PRIMARY KEY,
    source_asset_id text NOT NULL REFERENCES source_assets,
    original_record jsonb NOT NULL,
    reasons jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE TABLE validation_results (
    result_id text PRIMARY KEY,
    case_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('pass','fail','blocked')),
    evidence jsonb NOT NULL
);
CREATE TABLE requirement_coverage (
    requirement_id text PRIMARY KEY,
    state text NOT NULL CHECK (state IN ('not_started','in_progress','blocked','failed','complete')),
    evidence jsonb NOT NULL
);
CREATE VIEW accepted_observations AS SELECT * FROM observations WHERE validation_status='accepted';
