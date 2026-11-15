# Plan.md implementation gap analysis and execution plan

**Prepared:** 2026-11-14  
**Branch:** `backend`  
**Purpose:** establish the differences between the specification and the current repository before expanding implementation.

## Executive summary

The repository currently has a functioning Phase 1 prototype for KML ingestion,
SoilGrids, NASA POWER, simulated Sentinel-2 indices, a small groundwater reference
adapter, basic processing, SQLite persistence, and profile exports.

`Plan.md` describes a much broader agricultural data platform. It includes ten data
domains, many external datasets, laboratory and sensor imports, raster extraction,
crop science, rotation, management records, notebooks, provenance, repeatable
orchestration, and validation. Most of those are configuration entries, ORM table
definitions, or calculation stubs rather than live acquisition and end-to-end data
paths.

The main distinction is:

```text
Implemented prototype:
KML → a few adapters → summary processing → SQLite/profile export

Target platform in Plan.md:
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

`run_pipeline()` currently chooses a fixed adapter map in Python. It does not yet
read an acquisition section that controls enabled domains, source selection, date
ranges, retries, coverage, or test/live mode. Date defaults are also implicit.

The plan requires source coverage discovery, per-source configuration, extraction
jobs, repeat-run reuse, and explicit cache/version decisions. Those are not yet
implemented in the orchestration path.

### 3. Raw-data handling is incomplete

SoilGrids and NASA POWER save raw JSON, but the current pipeline does not reliably
save or register every input/output artifact:

- The input KML is read in place but is not copied into `data/raw` or registered as
  a source asset.
- Simulated Sentinel-2 scenes are processed in memory and have no raw scene asset.
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

The `Field.field_id` column is globally unique. Re-running a different KML that
generates `FIELD_0001` can collide with an existing farm. The pipeline also does
not yet implement a complete idempotency key based on project, source, geometry,
variable, time, depth, dataset version, and processing version.

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

Core Markdown documentation and tests exist, but the 21 notebook curriculum in
`Plan.md` has not been created. The current tests cover the implemented prototype,
not every planned source, database model, raster workflow, or end-to-end domain.

The status document also contains stale entries saying that prototype modules,
tests, and documentation are not started. It should be regenerated after each
milestone rather than maintained as a manually contradictory checklist.

### 10. Operational interfaces are missing

There is no stable CLI command, run manifest, structured logging/reporting of
partial failures, or resume command. Docker/PostGIS configuration exists, but the
application does not yet have a tested PostgreSQL/PostGIS integration path.

## Implementation plan

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

## Dependency order

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

## Definition of complete against Plan.md

The project should not be called complete until all of the following are true:

- Every enabled Plan.md domain has either a live adapter, an import adapter, or an
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

