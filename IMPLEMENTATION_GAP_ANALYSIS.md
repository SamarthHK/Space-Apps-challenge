# backendplan.md implementation gap analysis and execution plan

> **Historical analysis, not an implementation roadmap.** The 2026-11-15 revision of [backendplan.md](backendplan.md) and [docs/frontend_api_contract.md](docs/frontend_api_contract.md) supersedes every phase/order and acceptance suggestion below. References here to notebooks, synthetic fixtures/simulations, SQLite acceptance and permissive completion are obsolete. Retained only to explain the older prototype; do not execute its Phase 0-7 sequence or count its status claims as current verification.

**Prepared:** 2026-11-14  
**Branch:** `backend`  
**Purpose:** establish the differences between the specification and the current repository before expanding implementation.

## Executive summary

The repository currently has a functioning Phase 1 prototype for KML ingestion,
SoilGrids, NASA POWER, simulated Sentinel-2 indices, a small groundwater reference
adapter, basic processing, SQLite persistence, and profile exports. The orchestration
now also has explicit `live` and `demo` modes, run-specific output directories,
KML/raw-response snapshots, observation JSON/Parquet exports, and a run manifest.

`backendplan.md` describes a much broader agricultural data platform. It includes ten data
domains, many external datasets, laboratory and sensor imports, raster extraction,
crop science, rotation, management records, notebooks, provenance, repeatable
orchestration, and validation. Most of those are configuration entries, ORM table
definitions, or calculation stubs rather than live acquisition and end-to-end data
paths.

The main distinction is:

```text
Implemented prototype:
KML → a few adapters → summary processing → SQLite/profile export

Target platform in backendplan.md:
KML → source coverage discovery → many raw datasets → polygon/raster extraction
→ normalized observations → quality/provenance → crop/management interpretation
→ complete profile and analytical exports
```

The full target cannot honestly be implemented as one undifferentiated API pass.
Several sources require credentials, downloads, licensing, or user-supplied field
measurements. The implementation must therefore support three explicit modes:

1. **Live:** call a configured source and preserve its response.
2. **Import:** load a user-provided file or laboratory/sensor template.
3. **Unavailable:** create a provenance-rich missing-data record; never fabricate a
   value merely because a source is unavailable.

## Observed differences

### 1. Acquisition coverage is much smaller than the source registry

`config/sources.yaml` lists many candidates, but the executable source package and
pipeline currently cover only:

- SoilGrids, with a synthetic fallback.
- NASA POWER daily climate, with a synthetic fallback.
- Sentinel-2 through a simulated seasonal curve; no Earth Engine retrieval.
- CGWB through a small hard-coded reference-well table.
- EcoCrop and FAOSTAT through local catalog/benchmark data.
- Soil Health Card as an import helper, not a complete ingestion workflow.

Missing or incomplete source adapters from the plan include KSNDMC, IMD, CHIRPS,
ERA5-Land, India-WRIS, GAEZ, DSSAT, and APSIM. DEM/Copernicus, hydrology,
geology, land cover, surface-water, soil-moisture, and air-quality acquisition are
also not connected to the central pipeline.

### 2. The pipeline is not yet configuration-driven end to end

`run_pipeline()` now accepts domains, date ranges, and `live`/`demo` mode, but it
still chooses the adapter map in Python. It does not yet read a complete acquisition
section that controls source priority, retries, coverage thresholds, import files,
authentication, or per-source configuration. The run manifest records the selected
arguments, but it does not yet record the full resolved configuration and dataset
versions.

The plan requires source coverage discovery, per-source configuration, extraction
jobs, repeat-run reuse, and explicit cache/version decisions. Those are not yet
implemented in the orchestration path.

### 3. Raw-data handling is incomplete

The orchestration now snapshots the KML under `data/raw/inputs/`, stores hashed raw
responses for adapters it runs, and writes detailed observation exports. Raw-data
handling is still incomplete:

- The KML source asset is registered, but it is not yet linked to a project or run
  manifest through a first-class dataset record.
- Simulated Sentinel-2 scenes are saved as JSON, but their synthetic status, scene
  identity, spatial coverage, and processing inputs are not represented in a
  dedicated imagery dataset model.
- CGWB reference data is in code and has no raw snapshot/provenance asset.
- Source assets are not consistently linked from observations through a dataset and
  extraction job.
- Raw, normalized, processed, and derived directory conventions are not enforced
  consistently.

### 4. The normalized observation path is incomplete

The database models are broad, but only a subset is populated by the pipeline.
Crop parameters, crop stages, trials, performance, biological agents, management,
farmer surveys, sensors, and rotation effects are not fully seeded or populated.

The profile JSON is intentionally a summary. It does not include all daily climate
rows, all soil depth observations, source metadata, raw response references, or
quality details. The platform needs separate detailed exports in addition to a
human-readable summary profile.

### 5. Spatial extraction is only partially exercised

KML parsing, buffers, area, station matching, and raster zonal-statistics helpers
exist. There is no complete DEM/raster acquisition-to-zonal-statistics path in the
pipeline. Resolution, valid-pixel coverage, CRS, nodata, and raster provenance are
not consistently recorded for all domains.

The current field geometry is stored as WKT. PostGIS geometry columns, spatial
indexes, and production spatial queries remain future work.

### 6. Processing and interpretation do not cover all plan variables

Existing processing covers a useful subset of soil, climate, drought, terrain
formulae, vegetation indices, quality checks, and unit conversion. Missing or
incomplete processing includes:

- SPI/SPEI and anomaly baselines with documented reference periods.
- Hydrology, flow accumulation, watershed, drainage-network, and erosion workflows.
- Crop classification from satellite observations.
- Land-cover/history change detection.
- Water balance and soil-moisture assimilation.
- Heat/cold/frost event definitions and cross-source comparison.
- Full crop germination, development, stress, yield, and management data models.
- Pest/disease/pollinator data acquisition and temporal risk histories.

Some crop and rotation functions are transparent estimates or catalog lookups; they
are not calibrated crop models.

### 7. Repeatability and identity need strengthening

The pipeline now derives a geometry/project-based field ID and writes a unique run
directory. The database still has a globally unique `Field.field_id`, project
creation is not fully idempotent, and the observation idempotency key is only
partially implemented. A complete key must include project, field geometry,
variable, source asset, observation time/period, depth, statistic, dataset version,
and processing version. The current extraction job is not yet a full resumable job
state machine.

The plan requires extraction jobs, source versioning, cache reuse, duplicate
avoidance, and reprocessing support. Those need to be designed before adding many
more sources.

### 8. Quality control is not yet a pipeline gate

Range checks and a few helpers exist, but acquisition does not consistently run:

- geometry and coordinate-region checks;
- date continuity and duplicate-day checks;
- expected-variable response checks;
- raster coverage and resolution checks;
- cross-source comparison;
- missingness reason assignment;
- provenance completeness validation.

Invalid data should be retained with a quality flag and reason, rather than silently
dropped or treated as valid.

### 9. Notebook and documentation deliverables are incomplete

Core Markdown documentation and tests exist, but the platform defined by
`backendplan.md` has not been created. The current tests cover the implemented prototype,
not every planned source, database model, raster workflow, or end-to-end domain.

The status document also contains stale entries saying that prototype modules,
tests, and documentation are not started. It should be regenerated after each
milestone rather than maintained as a manually contradictory checklist.

### 10. Operational interfaces are missing

There is now a basic `python -m agri_data INPUT.kml` CLI and a run manifest. A
structured log, resume command, source status command, configuration file, and
PostgreSQL/PostGIS integration test are still missing.

## The fifteen missing feature groups and orchestration design

The missing work should enter the existing pipeline through a common source result
contract. Each adapter or importer must return:

- source and dataset identity, version, license, mode, and retrieval metadata;
- immutable raw asset references and checksums;
- canonical observations with field, time, depth, statistic, unit, resolution,
  measurement type, uncertainty, and quality flag;
- spatial and temporal coverage;
- validation results, warnings, and an explicit unavailable reason when applicable.

The orchestration sequence is:

~~~text
run request
  → resolve configuration and source coverage
  → validate KML and create project-scoped fields
  → retrieve/import source data
  → save immutable raw assets
  → normalize into canonical observations
  → run quality/provenance gates
  → database + complete Parquet/JSON detail export
  → optional filtration views
  → profile/report references
~~~

An adapter result should carry source_id, domain, dataset_id, mode, raw_asset_id,
observations, coverage, warnings, and validation. The orchestrator should never
infer a value from a summary profile. It should pass the complete observation
collection to storage first, then create summaries as views.

### 1. Soil laboratory and detailed soil properties

SoilGrids currently supplies mapped sand, silt, clay, pH, organic carbon, total
nitrogen, bulk density, CEC, and coarse fragments at six depths. The plan also
requires EC, sodicity/ESP, available N/P/K, sulphur, micronutrients, calcium
carbonate, infiltration, hydraulic conductivity, rooting depth, drainage,
contamination, and soil temperature.

Add canonical variables and units for every Soil Health Card field. Implement CSV,
JSON, and laboratory-report import with sample date, laboratory, method, detection
limit, depth, report checksum, and original units. Run this importer as an explicit
import source. Remove the embedded baseline laboratory values from the measured
path. Normalize all samples into observations, validate ambiguous nutrient bases,
and generate hydraulic estimates as derived observations linked to the pedotransfer
method and input observation IDs.

### 2. DEM, terrain, geology, and hydrology

Terrain functions exist but no DEM is acquired by the active pipeline. Add DEM
download/import adapters that return tile IDs, CRS, transform, resolution, nodata,
acquisition date, and source version. Select tiles from field bounds plus a margin,
mosaic them, and save the source raster.

Insert a raster extraction stage after field validation. It clips each raster to
each field, records valid-pixel coverage and resolution, and writes observations
for elevation, slope, aspect, curvature, TWI, flow accumulation, drainage density,
erosion risk, watershed, and landform. Geology, lithology, geomorphology, and parent
material need separate vector/raster adapters and spatial intersection records.

### 3. Rainfall source cross-validation

NASA POWER currently covers daily precipitation. The plan additionally identifies
IMD, KSNDMC, CHIRPS, and GPM, plus rainfall intensity and formal onset/withdrawal
definitions.

Implement each source as a climate adapter producing the same daily schema:
field_id, date, precipitation, source, station/grid ID, resolution, and quality.
For stations, run nearest-station selection and retain distance/elevation
representativeness. For grids, query the field or extract a polygon statistic.
Store each source independently. Add a cross-source processor that computes bias,
correlation, missingness, and disagreement; never average sources implicitly.
Calculate rainy days, intensity, onset/withdrawal, anomalies, SPI, SPEI, and trends
from source-specific series with a declared baseline period.

### 4. Atmospheric climate completeness

The current climate path has temperature, humidity, wind speed, solar radiation,
and precipitation. The plan also requires dew point, VPD, pressure, wind direction,
net radiation, sunshine, cloud cover, heatwaves, cold spells, frost, and growing
degree days.

Extend the canonical daily climate schema and source mappings for ERA5-Land, IMD,
station imports, and NASA POWER where available. The climate normalizer must
validate timezone, units, sentinels, duplicates, date continuity, and min/mean/max
consistency. Store daily source observations first. Store VPD, ET0, GDD,
heat/cold/frost event flags, anomalies, monthly, seasonal, and annual aggregates
as derived records with period bounds and method metadata.

### 5. Groundwater, surface water, irrigation, and soil moisture

CGWB currently uses three hard-coded wells and emits groundwater depth only. The
plan requires real well histories, aquifer type, water EC/pH, surface-water
features, irrigation infrastructure, SMAP, ERA5-Land root-zone moisture, reservoirs,
canals, and irrigation reliability.

Replace the reference table with a CGWB/India-WRIS station import/live adapter;
retain well ID, coordinates, elevation, aquifer, measurement date, season, and
measurement method. Emit every available well variable, including EC and pH,
rather than only depth. Add water-feature and irrigation-network spatial layers.
Intersect fields and buffers while preserving feature IDs and distances. Add
soil-moisture adapters with depth/layer metadata and product resolution. Add a
water-balance processor that cites rainfall, ET0, soil hydraulics, irrigation
events, runoff assumptions, and moisture observations for every derived balance.

### 6. Real satellite imagery and land history

The existing Sentinel-2 adapter simulates reflectance. Add Earth Engine and local
scene import adapters with deterministic fixture support. Query by geometry and
date, cloud-mask scenes, and save scene/product IDs, footprints, cloud fractions,
bands, resolution, timestamps, and collection versions.

Compute NDVI, NDMI, SAVI, EVI, LAI/fAPAR, phenology, anomalies, and change detection
as derived observations linked to scene assets. Add Landsat, MODIS, WorldCover,
Dynamic World, JRC water, and crop-history adapters. Synthetic curves must remain
explicitly synthetic/modelled.

### 7. Crop requirements and cultivar data

The catalog has five crop profiles but lacks cultivar-level and source-specific
requirements. Normalize YAML, EcoCrop, GAEZ, ICAR, and manual sources into the crop
species, variety, stage, and parameter tables with source, version, confidence,
stage, cultivar, and applicability conditions.

Run crop acquisition independently of field environmental acquisition. Suitability
then joins stored crop requirements to stored field observations. Missing
requirements must remain missing and carry an explicit explanation.

### 8. Germination and establishment

The current development function creates a generic schedule and LAI curve. Add
stage-specific parameters and optional field/trial observations for soil
temperature, soil moisture, sowing depth, emergence date, germination percentage,
seedling survival, and early root growth.

Run a crop-stage processor after daily climate, soil moisture, cultivar parameters,
and management events are available. Store measured stage events separately from
modelled estimates and retain all input observation IDs.

### 9. Crop growth and stress response

The current LAI curve omits measured biomass, flowering, pollination, grain filling,
harvest index, water-use efficiency, nutrient-use efficiency, and stress response.
Add time-series variables and import templates for these measurements.

Build growth features from satellite indices, climate, soil moisture, crop
requirements, and management. Store model outputs under a model-run dataset with
parameter/version metadata; keep measured trials and sensors in separate records.

### 10. Historical crop performance and trials

FAOSTAT currently uses hard-coded benchmarks. Add FAOSTAT/state-statistics imports
with item, area, unit, year, methodology, revision, production, harvested area,
and yield metadata. Add trial/performance imports connected to crop trials and
performance records, including cultivar, treatment, dates, irrigation, fertilizer,
biomass, harvest index, and observed stress.

Performance comparisons must distinguish statistical benchmarks, trials, surveys,
and field measurements, and cite the exact baseline used for a yield gap.

### 11. Biological risks, weeds, and pollination

The current module has a few hard-coded weather rules. Add biological-agent
imports with scientific identity, taxonomy, agent type, host crop, source, and
confidence. Store crop-agent relationships with life stage, susceptibility,
environmental thresholds, controls, and source references.

Build risk events from weather, leaf wetness, crop stage, vegetation state,
management, and historical presence. Each alert must retain trigger observations,
uncertainty, and method rather than only a text recommendation.

### 12. Nutrient cycling, residues, and rotation interactions

Rotation calculations exist, but no field residue, root, decomposition, disease
carryover, allelopathy, or measured soil-change data flows through the pipeline.
Persist crop sequence, harvest, residue management, nutrient application, and soil
test events in time order.

Add residue C/N, decomposition, incorporation, root contribution, fixation, uptake,
and carryover variables with uncertainty. Evaluate a sequence from the previous
season state and store transitions, assumptions, source records, and predicted
effects. APSIM/DSSAT runs must be model datasets separate from observations.

### 13. Cultivation and management

Management tables exist without import or orchestration. Define CSV/JSON templates
for seed, sowing, spacing, population, irrigation, fertilizer, tillage, weeds,
pest control, residues, and harvest. Validate timestamps, amounts, units, products,
cultivars, and field association.

Import these events before growth, water balance, biological risk, and rotation
processing. Corrected events should be versioned, preserving the original record.

### 14. Physical sensor ingestion

Add deployment metadata for sensor ID, manufacturer, variable, position, elevation,
depth, calibration, installation, removal, and field. Add raw-preserving CSV/JSON
imports with timezone normalization, unit conversion, calibration metadata, quality
flags, and gap detection. MQTT can use the same normalized observation contract.

Link every sensor reading to its deployment and source asset, then cross-validate it
against stations, satellite, and reanalysis without replacing either series.

### 15. Air quality, hazards, degradation, and change

Plan sections 2.7 and 2.8 are absent from the current source, variable, processing,
and pipeline layers. Add variables and event records for flood, drought, fire,
erosion, landslide, salinity, contamination, PM2.5, PM10, ozone, smoke, and dust
where source coverage exists.

Add raster/event adapters and field-buffer intersection. Preserve event geometry,
date, severity, footprint, source, and confidence. Change processors must retain
both baseline and comparison datasets. Hazard and air-quality observations should
feed crop stress reports as evidence, without silently changing suitability scores.

## Complete-data retention and filtration plan

The output contract must guarantee that source data is never shortened to make a
profile convenient to read. Raw data, normalized observations, derived records, and
filtered views are separate products:

~~~text
raw/              exact source response or imported file
normalized/       every canonical observation, no row truncation
processed/        complete derived tables and spatial outputs
derived/          complete analytical/model results
exports/full/     complete field/domain exports
exports/filtered/ user-selected views with saved filter specification
exports/summary/  compact human-readable summaries
~~~

The filtration pipeline is a downstream query/view stage. It must never mutate or
overwrite raw, normalized, processed, derived, or full exports. A filter request
should include field IDs, domains, variables, date range, depth range, source IDs,
measurement types, quality flags, spatial resolution limits, and optional row
limits. It must write the resolved filter specification, input dataset checksums,
row counts before/after filtering, and output checksum beside the filtered result.

Required implementation details:

- Replace profile construction that drops detailed arrays with a full profile
  manifest containing links to complete domain files.
- Export observations as complete JSON Lines and Parquet files. JSON Lines avoids
  holding a large dataset in one object while retaining every row.
- Add a filter_observations function that returns a new DataFrame or query result
  and records its filter manifest.
- Permit summaries to contain aggregates, but include the source row count,
  observation file path, and dataset checksum.
- Reject accidental truncation parameters in full export functions. A limit is legal
  only in an explicitly named filtered export.
- Ensure CLI commands distinguish export full, export filtered, and export summary.
- Validate that full-output row counts equal the database query row counts for each
  field/domain.

Acceptance criteria:

1. Every source response is retained byte-for-byte or as an immutable imported file.
2. Every normalized observation is present in the full database and full export.
3. Summary profiles contain references to complete data and never claim to contain
   all observations.
4. Filtering creates a new reproducible view and leaves the complete dataset
   unchanged.
5. Tests cover zero filters, each filter dimension, compound filters, empty results,
   checksums, row counts, and reruns.

## Historical implementation proposal (superseded; do not execute)

### Phase 0 — Baseline, contracts, and safety

**Goal:** make expansion safe before adding external sources.

Deliverables:

- Define canonical adapter result contracts: raw asset, dataset metadata,
  normalized observations, missing-data records, validation results, and warnings.
- Add a run manifest containing project ID, KML checksum, configuration checksum,
  processing version, source versions, timestamps, and output locations.
- Make project identity explicit and remove the global field-ID collision problem
  through project-scoped field keys or a project/field composite identity.
- Add a CLI entry point with `run`, `validate`, `status`, and `export` commands.
- Add explicit `live`, `import`, and `unavailable` source modes.
- Add tests for repeat runs, separate farms, failed sources, and partial success.

**Acceptance:** the same input/config is idempotent; a second farm cannot overwrite
the first; a failed source produces a traceable missing record and does not fail the
entire run.

### Phase 1 — Complete raw-data and provenance foundation

**Goal:** every input and source response is preserved and traceable.

Deliverables:

- Register the input KML/KMZ as a raw source asset with checksum.
- Implement dataset/version/source-asset/extraction-job linkage.
- Add raw snapshots for imported files, reference tables, simulated data, and live
  responses with an explicit `synthetic` or `measured` provenance flag.
- Store normalized observations in detailed domain-partitioned Parquet as well as
  the relational database.
- Add complete missing-data reason records and quality flags.

**Acceptance:** every observation can be traced to a source asset, source adapter,
retrieval time, spatial support, time/depth dimensions, and processing version.

### Phase 2 — Geospatial and terrain foundation

**Goal:** make polygon/raster extraction a production-quality shared capability.

Deliverables:

- Add robust GeoJSON/GPKG/KMZ input support and KML asset preservation.
- Add CRS/region validation, buffers, overlap checks, and field-level metadata.
- Implement DEM acquisition/import adapters with local-file fixtures first.
- Implement raster clipping, nodata, coverage, resolution, and zonal statistics
  persistence.
- Add terrain derivatives: elevation, slope, aspect, curvature, TWI, flow
  accumulation, drainage density, erosion risk, watershed, and landform fields.
- Add hydrology processing and source-coverage reporting.

**Acceptance:** a fixture DEM produces reproducible per-field terrain observations
with correct units, CRS, coverage percentage, and raster provenance.

### Phase 3 — Climate, water, and environmental cross-validation

**Goal:** expand environmental observations while keeping measured/modelled/source
  distinctions explicit.

Deliverables:

- Add NASA POWER configuration/date-range controls and real API response validation.
- Add import/live adapters for KSNDMC and IMD.
- Add CHIRPS and ERA5-Land adapters with cache and temporal aggregation.
- Add India-WRIS/CGWB water infrastructure and monitoring imports.
- Add soil-moisture and groundwater observation structures.
- Implement rainfall/temperature anomaly baselines, SPI/SPEI, heat/cold/frost
  events, VPD, ET, water balance, and source comparison reports.

**Acceptance:** a field report shows data availability by source, date range,
missingness, resolution, and agreement/disagreement without silently merging
incompatible datasets.

### Phase 4 — Satellite, land history, and crop classification

**Goal:** replace the simulated vegetation path with a reusable imagery workflow.

Deliverables:

- Implement an Earth Engine adapter behind optional authentication and a local
  fixture/import adapter for tests.
- Add Sentinel-2/Landsat/MODIS collection, cloud masking, scene metadata, and raw
  asset references.
- Add NDVI, NDMI, SAVI, EVI, LAI/fAPAR where source data supports them, anomalies,
  phenology, and change detection.
- Add WorldCover/Dynamic World/JRC surface-water imports where available.
- Add crop-type classification interfaces and confidence/validation records.

**Acceptance:** imagery scenes and derived indices are queryable by field/date,
with cloud fraction, spatial resolution, coverage, source ID, and raw asset link.

### Phase 5 — Crop knowledge and management data

**Goal:** implement domains 6–10 as structured data, not only calculated examples.

Deliverables:

- Expand crop catalog into species, cultivar, stage, requirement, source, and
  confidence records.
- Add germination/establishment, growth, phenology, stress, yield, biomass, harvest
  index, and crop-trial imports.
- Add biological-agent identity, crop-host relationships, disease/pest history,
  weeds, and pollinator requirements.
- Add cultivation imports for sowing, seed, spacing, irrigation, fertilizer,
  tillage, weeds, pest control, residues, and harvest.
- Add sensor CSV/manual import templates for weather, soil, leaf wetness, flow,
  tissue, PAR, and LAI sensors.
- Connect crop suitability, growth, biological-risk, performance, and management
  functions to stored observations.

**Acceptance:** a crop/field analysis clearly separates environmental conditions,
crop requirements, observed performance, and farmer management events.

### Phase 6 — Rotation and agronomic interpretation

**Goal:** turn multi-season data into transparent, traceable interpretations.

Deliverables:

- Expand nutrient cycling, residue, moisture, compatibility, and sequence models
  with source/configuration references and uncertainty.
- Add crop-family disease carryover, allelopathy, root contribution, nutrient
  depletion/replenishment, moisture carryover, and recommended rotation intervals.
- Add APSIM/DSSAT adapters only after soil, climate, crop, and management inputs are
  complete; keep model runs separate from observations.
- Add field-level suitability, growth, risk, performance, and rotation reports.

**Acceptance:** each interpretation identifies inputs, method/version, assumptions,
limitations, and source observations; no model output is presented as measured data.

### Phase 7 — Notebooks, production backend, and validation

**Goal:** deliver the notebook-first workflow and a repeatable production path.

Deliverables:

- Create notebooks `00`–`20`, each with purpose, source, retrieval, processing,
  visualization, storage, and limitations sections.
- Add fixture-backed tests for every adapter and processing domain.
- Test SQLite and PostgreSQL/PostGIS paths, including spatial indexes and queries.
- Add run manifests, resume/retry behavior, structured logs, and failure summaries.
- Add full end-to-end test using the supplied `FarmLand.kml` and a fully offline
  fixture configuration.
- Update `IMPLEMENTATION_STATUS.md` from generated milestone facts.

**Acceptance:** a clean environment can run the documented workflow, reproduce the
fixture outputs, and distinguish complete, partial, and unavailable data domains.

## Historical dependency order (superseded)

The order is intentional:

```text
Contracts/provenance
        ↓
Idempotent geospatial + raw storage
        ↓
Terrain/climate/water/satellite acquisition
        ↓
Crop/management/sensor knowledge
        ↓
Rotation and agronomic interpretation
        ↓
Notebooks, PostGIS, CLI, and full validation
```

The source adapters should be implemented in parallel only after the common adapter
contract and provenance foundation are stable. Live integrations should always have
fixture/import paths so tests do not depend on network access or credentials.

## Historical completion definition (superseded)

The project should not be called complete until all of the following are true:

- Every enabled backendplan.md domain has either a live adapter, an import adapter, or an
  explicit unavailable result.
- Every raw input and normalized observation has provenance.
- KML geometry controls polygon/raster extraction and source coverage.
- Detailed observations are queryable independently of compact profile summaries.
- Time, depth, source resolution, measurement type, uncertainty, and quality are
  retained where applicable.
- Repeated runs are idempotent and resumable.
- The full fixture workflow passes without network access.
- Live-source limitations, credentials, licensing, and missing data are visible in
  the final report.

