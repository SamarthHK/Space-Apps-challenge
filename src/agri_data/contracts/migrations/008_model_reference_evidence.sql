ALTER TABLE model_source_records
    DROP CONSTRAINT model_source_records_record_kind_check;
ALTER TABLE model_source_records
    ADD CHECK (record_kind IN (
        'crop_outcome', 'weather_day', 'crop_profile', 'crop_requirement',
        'regional_outcome', 'crop_calendar', 'spatial_support',
        'climate_normal', 'crop_suitability'
    ));
ALTER TABLE model_source_records ALTER COLUMN site_id DROP NOT NULL;
ALTER TABLE model_source_records
    ADD CHECK (record_kind NOT IN ('crop_outcome', 'weather_day') OR site_id IS NOT NULL);

CREATE TABLE model_source_requests (
    request_id text PRIMARY KEY,
    source_asset_id text NOT NULL REFERENCES source_assets,
    receipt jsonb NOT NULL
);
CREATE TABLE model_dataset_requests (
    dataset_id text NOT NULL REFERENCES model_datasets,
    request_id text NOT NULL REFERENCES model_source_requests,
    PRIMARY KEY (dataset_id, request_id)
);
CREATE TABLE model_record_evidence (
    dataset_id text NOT NULL,
    record_id text NOT NULL,
    source_asset_id text NOT NULL REFERENCES source_assets,
    source_locator text NOT NULL,
    evidence_role text NOT NULL CHECK (evidence_role IN ('value', 'definition', 'spatial_support')),
    PRIMARY KEY (dataset_id, record_id, source_asset_id, source_locator, evidence_role),
    FOREIGN KEY (dataset_id, record_id) REFERENCES model_dataset_records
);
