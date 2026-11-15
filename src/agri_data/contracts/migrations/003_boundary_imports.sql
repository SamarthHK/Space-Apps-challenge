CREATE TABLE boundary_imports (
    import_id text PRIMARY KEY,
    project_id text NOT NULL REFERENCES projects,
    source_asset_id text NOT NULL REFERENCES source_assets,
    source_namespace text NOT NULL,
    processing_version text NOT NULL,
    completed_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('complete','partial','failed')),
    rejected_records jsonb NOT NULL
);
CREATE TABLE boundary_import_records (
    import_id text NOT NULL REFERENCES boundary_imports,
    source_record_locator text NOT NULL,
    field_id text NOT NULL REFERENCES fields,
    boundary_id text NOT NULL REFERENCES field_boundaries,
    original_geometry jsonb NOT NULL,
    context jsonb NOT NULL,
    PRIMARY KEY(import_id,source_record_locator)
);
ALTER TABLE field_boundaries ADD COLUMN metric_crs text;
ALTER TABLE field_boundaries ADD COLUMN area_m2 double precision CHECK (area_m2 > 0);
ALTER TABLE field_boundaries ADD COLUMN perimeter_m double precision CHECK (perimeter_m > 0);
