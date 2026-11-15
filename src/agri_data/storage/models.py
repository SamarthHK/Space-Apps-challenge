"""
SQLAlchemy database models for the AgriData platform.
Defines all 22 relational tables specified in the Master Architecture.
Works across SQLite and PostgreSQL/PostGIS seamlessly.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    region = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    fields = relationship("Field", back_populates="project")


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    folder = Column(String(128), default="Default")

    # Geometry storage (WKT in EPSG:4326)
    geometry_wkt = Column(Text, nullable=False)
    centroid_lon = Column(Float, nullable=True)
    centroid_lat = Column(Float, nullable=True)
    rep_lon = Column(Float, nullable=True)
    rep_lat = Column(Float, nullable=True)

    area_ha = Column(Float, nullable=True)
    area_sqm = Column(Float, nullable=True)
    perimeter_m = Column(Float, nullable=True)
    utm_crs = Column(String(32), nullable=True)

    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="fields")
    observations = relationship("Observation", back_populates="field")
    management_events = relationship("ManagementEvent", back_populates="field")
    sensor_deployments = relationship("SensorDeployment", back_populates="field")


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    domain = Column(String(64), nullable=False)  # soil, climate, water, etc.
    access_type = Column(String(64), nullable=False) # rest_api, geospatial_api, etc.
    base_url = Column(String(512), nullable=True)
    auth_required = Column(Boolean, default=False)
    spatial_resolution_m = Column(Float, nullable=True)
    temporal_type = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    datasets = relationship("Dataset", back_populates="source")
    observations = relationship("Observation", back_populates="source")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    dataset_name = Column(String(128), nullable=False)
    version = Column(String(32), default="1.0")
    description = Column(Text, nullable=True)

    source = relationship("DataSource", back_populates="datasets")
    assets = relationship("SourceAsset", back_populates="dataset")


class Variable(Base):
    __tablename__ = "variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    variable_id = Column(String(64), unique=True, nullable=False, index=True)
    category = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    canonical_unit = Column(String(32), nullable=False)
    depth_dependent = Column(Boolean, default=False)
    temporal_type = Column(String(32), default="observation")
    min_valid = Column(Float, nullable=True)
    max_valid = Column(Float, nullable=True)

    observations = relationship("Observation", back_populates="variable")


class SourceAsset(Base):
    __tablename__ = "source_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    file_path = Column(String(512), nullable=False)
    file_format = Column(String(32), nullable=False) # json, geotiff, parquet, csv
    sha256_checksum = Column(String(64), nullable=False)
    byte_size = Column(Integer, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    dataset = relationship("Dataset", back_populates="assets")
    observations = relationship("Observation", back_populates="source_asset")


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    source_id = Column(String(64), nullable=False)
    field_ids_json = Column(JSON, nullable=False)
    status = Column(String(32), default="RUNNING") # RUNNING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Observation(Base):
    """
    Master normalized observation table.
    Stores multi-domain measurements with complete provenance and spatial support.
    """
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    variable_id = Column(Integer, ForeignKey("variables.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    source_asset_id = Column(Integer, ForeignKey("source_assets.id"), nullable=True)

    # Observation values
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    original_value = Column(Float, nullable=True)
    original_unit = Column(String(32), nullable=True)
    standardized_unit = Column(String(32), nullable=True)

    # Time dimension
    observed_at = Column(DateTime, nullable=True, index=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    # Depth dimension
    depth_top_cm = Column(Float, nullable=True)
    depth_bottom_cm = Column(Float, nullable=True)

    # Spatial support & method
    statistic = Column(String(32), default="mean") # mean, median, min, max, p10, p90, etc.
    measurement_type = Column(String(32), nullable=False) # measured, satellite, modelled, reanalysis, derived
    extraction_method = Column(String(64), nullable=True)
    spatial_resolution_m = Column(Float, nullable=True)
    spatial_coverage_percent = Column(Float, nullable=True)
    uncertainty = Column(Float, nullable=True)
    quality_flag = Column(String(32), default="VALID") # VALID, SUSPECT, INTERPOLATED

    created_at = Column(DateTime, default=datetime.utcnow)

    field = relationship("Field", back_populates="observations")
    variable = relationship("Variable", back_populates="observations")
    source = relationship("DataSource", back_populates="observations")
    source_asset = relationship("SourceAsset", back_populates="observations")

    __table_args__ = (
        Index("idx_obs_field_var_time", "field_id", "variable_id", "observed_at"),
    )


class CropSpecies(Base):
    __tablename__ = "crop_species"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_id = Column(String(64), unique=True, nullable=False, index=True)
    common_name = Column(String(128), nullable=False)
    botanical_name = Column(String(128), nullable=False)
    family = Column(String(64), nullable=False)
    crop_type = Column(String(64), nullable=False) # cereal, legume, oilseed, cash
    nitrogen_fixation_kg_ha = Column(Float, default=0.0)
    residue_kg_ha = Column(Float, default=0.0)
    residue_c_n_ratio = Column(Float, nullable=True)

    varieties = relationship("CropVariety", back_populates="species")
    parameters = relationship("CropParameter", back_populates="species")


class CropVariety(Base):
    __tablename__ = "crop_varieties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cultivar_id = Column(String(64), unique=True, nullable=False, index=True)
    crop_species_id = Column(Integer, ForeignKey("crop_species.id"), nullable=False)
    cultivar_name = Column(String(128), nullable=False)
    maturity_duration_days = Column(Integer, nullable=True)
    breeding_institution = Column(String(128), nullable=True)

    species = relationship("CropSpecies", back_populates="varieties")


class CropGrowthStage(Base):
    __tablename__ = "crop_growth_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_id = Column(String(64), unique=True, nullable=False)
    stage_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)


class CropParameter(Base):
    __tablename__ = "crop_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_species_id = Column(Integer, ForeignKey("crop_species.id"), nullable=False)
    cultivar_id = Column(Integer, ForeignKey("crop_varieties.id"), nullable=True)
    stage_id = Column(String(64), nullable=True)
    variable_id = Column(String(64), nullable=False)

    min_value = Column(Float, nullable=True)
    opt_min_value = Column(Float, nullable=True)
    opt_max_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    unit = Column(String(32), nullable=False)

    source_reference = Column(String(256), nullable=True)
    confidence = Column(String(32), default="HIGH")

    species = relationship("CropSpecies", back_populates="parameters")


class CropTrial(Base):
    __tablename__ = "crop_trials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trial_id = Column(String(64), unique=True, nullable=False, index=True)
    crop_id = Column(String(64), nullable=False)
    cultivar_name = Column(String(128), nullable=True)
    location_name = Column(String(128), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    sowing_date = Column(DateTime, nullable=True)
    harvest_date = Column(DateTime, nullable=True)
    irrigation_treatment = Column(String(64), nullable=True)
    fertilizer_treatment = Column(String(128), nullable=True)
    source_reference = Column(String(256), nullable=True)

    performances = relationship("CropPerformance", back_populates="trial")


class CropPerformance(Base):
    __tablename__ = "crop_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trial_id = Column(Integer, ForeignKey("crop_trials.id"), nullable=False)
    yield_kg_per_ha = Column(Float, nullable=False)
    biomass_kg_per_ha = Column(Float, nullable=True)
    harvest_index = Column(Float, nullable=True)
    water_consumed_mm = Column(Float, nullable=True)
    observed_stress = Column(String(128), nullable=True)

    trial = relationship("CropTrial", back_populates="performances")


class BiologicalAgent(Base):
    __tablename__ = "biological_agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), unique=True, nullable=False, index=True)
    common_name = Column(String(128), nullable=False)
    scientific_name = Column(String(128), nullable=True)
    agent_type = Column(String(64), nullable=False) # pest, fungal_pathogen, bacterial_pathogen, virus, weed
    description = Column(Text, nullable=True)


class CropBiologicalRisk(Base):
    __tablename__ = "crop_biological_risks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_id = Column(String(64), nullable=False)
    agent_id = Column(String(64), ForeignKey("biological_agents.agent_id"), nullable=False)
    susceptibility_level = Column(String(32), default="MODERATE") # LOW, MODERATE, HIGH, CRITICAL
    optimal_temp_c = Column(Float, nullable=True)
    optimal_rh_pct = Column(Float, nullable=True)
    control_methods = Column(Text, nullable=True)


class RotationEffect(Base):
    __tablename__ = "rotation_effects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    previous_crop_id = Column(String(64), nullable=False)
    next_crop_id = Column(String(64), nullable=False)
    compatibility_score = Column(Float, nullable=False) # 1.0 to 10.0
    expected_yield_delta_pct = Column(Float, default=0.0)
    nitrogen_change_kg_ha = Column(Float, default=0.0)
    moisture_change_mm = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)


class ManagementEvent(Base):
    __tablename__ = "management_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    event_type = Column(String(64), nullable=False) # sowing, irrigation, fertilizer, tillage, harvest
    event_date = Column(DateTime, nullable=False)
    details_json = Column(JSON, nullable=True)

    field = relationship("Field", back_populates="management_events")


class SensorDeployment(Base):
    __tablename__ = "sensor_deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(String(64), unique=True, nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    sensor_type = Column(String(64), nullable=False) # soil_moisture_probe, weather_station, flow_meter
    depth_cm = Column(Float, nullable=True)
    installed_at = Column(DateTime, default=datetime.utcnow)

    field = relationship("Field", back_populates="sensor_deployments")
    readings = relationship("SensorReading", back_populates="deployment")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(Integer, ForeignKey("sensor_deployments.id"), nullable=False)
    recorded_at = Column(DateTime, nullable=False, index=True)
    variable_name = Column(String(64), nullable=False)
    reading_value = Column(Float, nullable=False)
    reading_unit = Column(String(32), nullable=False)

    deployment = relationship("SensorDeployment", back_populates="readings")
