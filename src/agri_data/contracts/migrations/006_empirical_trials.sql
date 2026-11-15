CREATE TABLE crop_species (
    crop_id text PRIMARY KEY,
    name text NOT NULL,
    source_asset_id text NOT NULL REFERENCES source_assets,
    metadata jsonb NOT NULL
);
CREATE TABLE crop_varieties (
    cultivar_id text PRIMARY KEY,
    crop_id text NOT NULL REFERENCES crop_species,
    source_name text NOT NULL,
    source_asset_id text NOT NULL REFERENCES source_assets
);
CREATE TABLE crop_trials (
    trial_id text PRIMARY KEY,
    source_asset_id text NOT NULL REFERENCES source_assets,
    site_id text NOT NULL,
    description text NOT NULL,
    metadata jsonb NOT NULL
);
CREATE TABLE trial_resources (
    source_asset_id text NOT NULL REFERENCES source_assets,
    resource_name text NOT NULL,
    schema_definition jsonb NOT NULL,
    rows jsonb NOT NULL,
    PRIMARY KEY(source_asset_id,resource_name)
);
CREATE TABLE crop_performance (
    outcome_id text PRIMARY KEY,
    context_id text NOT NULL,
    trial_id text NOT NULL REFERENCES crop_trials,
    crop_id text NOT NULL REFERENCES crop_species,
    cultivar_id text REFERENCES crop_varieties,
    source_asset_id text NOT NULL REFERENCES source_assets,
    source_record_locator text NOT NULL,
    harvest_year integer NOT NULL,
    plot_id text NOT NULL,
    main_plot_id text NOT NULL,
    rotation_code text NOT NULL,
    sowing_date date,
    harvest_date date,
    yield_kg_ha double precision CHECK (
        yield_kg_ha >= 0 AND yield_kg_ha NOT IN ('NaN'::float8,'Infinity'::float8,'-Infinity'::float8)),
    mass_basis text NOT NULL,
    availability text NOT NULL CHECK (availability IN ('available_from_source','missing','requires_review')),
    validation_status text NOT NULL DEFAULT 'pending' CHECK (validation_status IN ('pending','accepted','rejected')),
    raw_record jsonb NOT NULL,
    record_context jsonb NOT NULL,
    CHECK (harvest_date IS NULL OR sowing_date IS NULL OR harvest_date>=sowing_date)
);
CREATE INDEX crop_performance_context_idx ON crop_performance(context_id);
