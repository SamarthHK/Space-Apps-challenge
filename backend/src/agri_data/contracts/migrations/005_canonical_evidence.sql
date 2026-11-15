CREATE TABLE field_aliases (
    alias_field_id text PRIMARY KEY REFERENCES fields,
    canonical_field_id text NOT NULL REFERENCES fields,
    evidence jsonb NOT NULL,
    CHECK (alias_field_id <> canonical_field_id)
);
CREATE TABLE canonical_observations (
    canonical_observation_id text PRIMARY KEY,
    context_id text NOT NULL,
    field_id text REFERENCES fields,
    variable_id text NOT NULL REFERENCES variables,
    scientific_record jsonb NOT NULL,
    validation_status text NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending','accepted','rejected')),
    validation_evidence jsonb
);
CREATE INDEX canonical_observations_context_idx ON canonical_observations(context_id);
CREATE TABLE observation_evidence (
    observation_id text PRIMARY KEY REFERENCES observations,
    canonical_observation_id text NOT NULL REFERENCES canonical_observations,
    source_asset_id text NOT NULL REFERENCES source_assets,
    extraction_job_id text NOT NULL REFERENCES extraction_jobs,
    source_record_locator text NOT NULL
);
CREATE INDEX observation_evidence_canonical_idx ON observation_evidence(canonical_observation_id);
CREATE TABLE acquisition_observations (
    extraction_job_id text NOT NULL REFERENCES extraction_jobs,
    observation_id text NOT NULL REFERENCES observations,
    acquired_record jsonb NOT NULL,
    PRIMARY KEY(extraction_job_id, observation_id)
);
INSERT INTO acquisition_observations
    SELECT extraction_job_id,observation_id,record FROM observations;
CREATE VIEW canonical_fields AS
    SELECT f.* FROM fields f
    WHERE NOT EXISTS (SELECT 1 FROM field_aliases a WHERE a.alias_field_id=f.field_id);
CREATE VIEW accepted_canonical_observations AS
    SELECT * FROM canonical_observations
    WHERE validation_status='accepted' AND validation_evidence IS NOT NULL;
