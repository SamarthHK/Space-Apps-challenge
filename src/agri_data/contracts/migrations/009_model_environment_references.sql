ALTER TABLE model_source_records
    DROP CONSTRAINT model_source_records_record_kind_check;
ALTER TABLE model_source_records
    ADD CHECK (record_kind IN (
        'crop_outcome', 'weather_day', 'crop_profile', 'crop_requirement',
        'regional_outcome', 'crop_calendar', 'spatial_support',
        'climate_normal', 'crop_suitability', 'environment_reference', 'crop_registry'
    ));
