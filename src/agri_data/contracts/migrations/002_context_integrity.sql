ALTER TABLE variables ADD UNIQUE (variable_id, feature_id);
ALTER TABLE datasets ADD UNIQUE (dataset_id, source_id);
ALTER TABLE source_bindings ADD UNIQUE (source_binding_id, variable_id, dataset_id);
ALTER TABLE observations ADD CONSTRAINT observation_feature_matches_variable
    FOREIGN KEY (variable_id, feature_id) REFERENCES variables (variable_id, feature_id);
ALTER TABLE observations ADD CONSTRAINT observation_source_matches_dataset
    FOREIGN KEY (dataset_id, source_id) REFERENCES datasets (dataset_id, source_id);
ALTER TABLE observations ADD CONSTRAINT observation_binding_matches_context
    FOREIGN KEY (source_binding_id, variable_id, dataset_id)
    REFERENCES source_bindings (source_binding_id, variable_id, dataset_id);
