CREATE TABLE model_source_records (
    record_id text PRIMARY KEY,
    context_id text NOT NULL,
    record_kind text NOT NULL CHECK (record_kind IN ('crop_outcome', 'weather_day')),
    site_id text NOT NULL,
    source_asset_id text NOT NULL REFERENCES source_assets,
    record jsonb NOT NULL
);
CREATE INDEX model_source_context_idx ON model_source_records(context_id);
CREATE TABLE model_datasets (
    dataset_id text PRIMARY KEY,
    manifest jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE model_dataset_records (
    dataset_id text NOT NULL REFERENCES model_datasets,
    record_id text NOT NULL REFERENCES model_source_records,
    PRIMARY KEY (dataset_id, record_id)
);
