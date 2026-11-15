# Agriculture Data Platform Backend — Implementation and Acceptance Contract

## 1. Objective, scope and mandatory rules

Implement a working backend that accepts real KML/KMZ agricultural boundaries, retrieves or imports authentic environmental and agricultural data, validates its meaning and fitness for use, persists it in an actual PostgreSQL/PostGIS database, exposes versioned application APIs, and exports complete, traceable field and crop profiles. The backend must satisfy the existing Vite/Leaflet frontend's user journeys without relying on browser-only demo state.

This document is the implementation authority. Section 2 is the **only implementation sequence**, with explicit prerequisites rather than an all-domains-before-API waterfall. Sections 3–9 define scientific contracts, inventories and acceptance tests. The companion [frontend API contract](docs/frontend_api_contract.md) defines the proposed wire schemas, code-to-API mapping, approval decisions and frontend handoff. They form one revised plan; neither describes implemented endpoints. Development belongs on the `backend` branch; frontend changes belong on `frontend` in a separate checkout. Preserve existing user work.

**Revision audited 2026-11-15:** backend `5d53f6735d1ec1698cd98b7021b8a22efd8e1a4f`, frontend `da3b1c0120d99355c3f05dee3fb429877e34b07c`. The audit read both branches' code and `frontendplan.md`; it did not run services or verify provider access. Re-audit changed consumers if either branch advances. `IMPLEMENTATION_GAP_ANALYSIS.md` and the earlier status tables are historical evidence, not competing instructions.

### 1.1 Full scope

**Every feature family, constituent variable, source integration and instrument category listed in this document is required.** There is no reduced prototype definition of project completion. Completing early steps is progress toward the full system. An empty adapter, database table, registry entry, Python module or report is not a completed feature.

Implement soil; terrain/geology; rainfall; climate; water; historical land/vegetation; degradation/hazards; environmental quality; crop requirements; germination; crop development; actual performance; biological risks; rotation interactions; cultivation management; field instruments; spatial processing; database storage; provenance; validation; application APIs; and complete exports.

Preserve the original feature scope, including features previously mentioned outside inventory tables. Capture irrigation cost if present in an authentic farmer record because it was explicitly listed. Because the current frontend already exposes market intelligence, crop recommendations, farmer profiles and planting plans, the backend scope now includes authenticated profile/field ownership, authentic market observations, traceable recommendation runs and persisted planting plans. Profitability and optimization outputs may only be returned when all required authentic price, cost, yield and agronomic inputs are present and versioned; otherwise return an explicit unavailable or blocked state. Do not silently preserve the frontend's hardcoded financial values as production data.

Support crop suitability evidence, observed growth trajectories and multi-season rotation evidence. A predictive or optimization model is not a substitute for collecting these data. Local simulations must not populate the required feature dataset or acceptance evidence.

### 1.2 Authentic data only

1. Retrieve actual provider responses, download actual datasets, or import actual laboratory reports, sensor recordings, farmer submissions and published research records.
2. **Prohibit fabricated, augmented, randomized, hardcoded baseline, demo, mock, synthetic and fallback-generated agricultural data everywhere, including tests and development scripts.** Do not fabricate field boundaries, crops, dates, sensor readings or expected scientific values to make tests pass.
3. Do not use monkeypatched provider responses, HTTP response mocks, generated fixtures, in-memory SQLite, or a database substitute as connection or acceptance evidence. Test expected values must come from independently inspected authentic records or independently calculated results from those records.
4. Preserve provider-issued modelled maps, satellite estimates, reanalysis, published parameters and climate projections as authentic **source products**, with their true evidence type. They are not direct field measurements. “Real” means authentic and traceable, not that every source product is a direct observation.
5. Deterministic calculations from validated real inputs are allowed: unit conversion, aggregation, vegetation indices, terrain derivatives and scientifically specified indicators. Preserve input lineage, formulas, assumptions and uncertainty. Do not invent missing inputs, interpolate gaps, generate growth curves, or synthesize observations to achieve completeness.
6. APSIM/DSSAT integrations import authentic, versioned parameter files and empirical trial evidence. Generated simulation results cannot satisfy observed yield, growth or rotation requirements. Features that lack empirical evidence remain blocked. This supersedes earlier suggestions to use example simulations as acquired data.
7. A failed request remains failed. Missing credentials remain blocked. A provider gap remains missing. Missing, zero, below detection limit and not applicable are different states.
8. Preserve raw source bytes immutably with checksums. Never overwrite a previous response or silently merge conflicting sources.
9. Legacy caches without verifiable provenance are ineligible. Keep new raw assets separate; do not delete existing user data. An online acceptance test must make a fresh request even if an authentic cached asset exists.
10. Never report a feature complete solely because data are nonempty, an HTTP status is 200, a Python script executes, files exist, or unit tests pass.

### 1.3 Honest completion and blockers

Use feature implementation states `not_started`, `in_progress`, `blocked`, `failed`, `complete`. These are distinct from per-record data availability states in Section 4.

A feature is `complete` only when its acquisition route, semantic validation, real PostgreSQL readback, full export and all required acceptance cases pass with linked evidence. Compound families are complete only when **every required child variable** passes. A selected source route cannot be called verified merely because another provider worked.

Unavailable credentials, inaccessible datasets, absent hardware, missing reports or insufficient scientific reference data create blockers. Record the exact dependency, failed test, attempted route and next action. Continue independent work allowed by the dependency sequence; do not fabricate results or mark later gates passed. Overall completion remains false while any required feature, source, instrument or test is blocked, failed, skipped or unimplemented.

Not every feature applies to every field/date/crop. Define applicability before acquisition and record a reason. Require real positive evidence for every feature somewhere in the agreed acceptance corpus, plus truthful missing-data behavior elsewhere. Selecting an area with no coverage cannot erase a feature from scope. Do not reduce the denominator to the variables that happened to return data.

## 2. The single implementation sequence

Use the priority order below, but start a work item only when its **actual prerequisites** pass. A partially blocked domain does not prevent independent API, UI or domain work. Never call the blocked domain or the full platform complete. This revision preserves S01–S12 identifiers for traceability, moves the reusable API foundation into S04, and reserves S10 for the remaining application services and final screen migration.

Keep a machine-readable ledger in `config/implementation_ledger.yaml`: `task_id`, `step_id`, `depends_on`, `feature_ids`, `source_binding_ids`, `frontend_mapping_ids`, `files`, `acceptance_case_ids`, `status`, `evidence_paths`, `blockers`, `next_action`. Task IDs use `Sxx.<bounded-deliverable>`. Store no credentials or personal input records in this ledger. Record overall full-scope coverage separately from task completion.

| Step | Prerequisites and bounded deliverables | Exit gate / evidence |
| --- | --- | --- |
| S01 — Freeze contracts and inventory | Approve D01–D05 in the companion contract. Create typed DTOs and a contract-only OpenAPI artifact; copy it to frontend F01 without claiming routes exist. Inventory every feature/source/instrument family and mapping M01–M18. Expand atomic variables and scientific rules for the first slice; register unresolved later bindings explicitly. Identify authentic input files and their provenance, not just filenames. | Schema/error/enum agreement, no unmapped active UI consumer, complete family inventory, an owner and blocker for every unresolved dependency. A contract can be frozen without an available dataset; authentic response evidence is required before its route is called operational. |
| S02 — Environment and shared storage | Requires S01 storage/DTO decisions. Reconcile and lock dependencies; create migrations for users/sessions/profiles/roles, projects/fields/boundaries, assets/datasets/observations/lineage/quarantine, jobs and validation. Add domain tables in their owning steps, not all at once. Remove implicit SQLite selection and automatic scientific seed data from the accepted path. | DB-01–DB-09 on the shared path with a real field and inspected authentic record. Missing such a record blocks readback acceptance, not migration/auth implementation. Independent process reads committed data. Secret configuration and acceptance-owned isolation documented. |
| S03 — Boundary service | Requires S02 field/asset storage and actual KML or user-drawn geometry. Refactor existing geographical helpers into a service. Implement preview/confirmation, Polygon/MultiPolygon/holes, explicit repair consent, stable identity, geometry revisions and exports. | GEO-01/02/03/07 and API-06 geometry subcases. GEO-04/05/06 belong to the later raster/station tasks that supply their real inputs; they remain required, not waived. No fields are created by preview alone. |
| S04 — First API/frontend slice and source harness | API tasks require S02 auth and S03 boundary service, not all scientific integrations. Add app factory, settings, sessions, profile, field CRUD, import jobs, exports, OpenAPI generation, errors, CORS and durable worker. Connect frontend F02–F04 in its checkout. Independently implement the source connection harness and small soil/climate retrieval proofs. | Profile and boundary journeys survive restart; applicable API-01–08/11 and WEB-01–08/12/13/15 instances pass. Other resources return documented capability/unavailability states. Initial source bindings pass applicable CONN cases; their failures do not invalidate unrelated profile/field evidence. S04 overall is incomplete while one of its required tasks is blocked. |
| S05 — Soil, terrain, rainfall and climate | Requires shared storage, spatial/source capabilities actually used by each binding. First implement the soil import/POWER slice for frontend F05; then expand F01–F04, including forecast versus historical/projection distinctions. Add domain migrations and register all atomic children before their adapters. | FEAT, Q01–Q04, applicable GEO/CROSS and CONN cases for every required child. Small-slice success is not whole-domain completion. Unknown sample date/depth/nutrient basis cannot be inferred from the UI. |
| S06 — Water, land, hazards and environmental quality | Requires S02–S04 shared components and only the S05 inputs used by each derivation. Implement F05–F08, real scene metadata/overlays and time series; migrate frontend F06. | FEAT, Q05–Q08, applicable GEO/CROSS and CONN cases. Selected scene actually controls the overlay; cloud-masked or missing periods remain gaps. |
| S07 — Crop requirements, germination, growth and performance | Requires shared storage and authentic references/trials. Does not require completion of unrelated water or hazard bindings. Implement F09–F12 and crop/catalog responses; migrate catalog portion of frontend F07. | FEAT, Q09–Q12 and applicable CONN/CROSS cases. Species, cultivar, observed trial and published requirement remain distinct. |
| S08 — Biology, rotation and management | Requires shared storage; a derived result additionally requires its registered S05–S07 parents. Implement F13–F15, structured surveys and management events. | FEAT, Q13–Q15 and applicable CONN/CROSS cases. Actual events do not inherit invented crop/date/amount defaults; rotation claims retain empirical references. |
| S09 — Instruments and laboratory acquisition | Requires shared storage and real reports/deployment metadata. An individual laboratory import may be built with S05 before the rest of S09. Implement all 14 instrument categories and ancillary inputs. | DEVICE and FEAT cases for every category/instance; historic report ingestion is not claimed as live hardware operation. |
| S10 — Application services and remaining frontend screens | Market/catalog/plan tasks need only their specific repositories; recommendation tasks require their declared accepted agronomic/economic inputs. Implement F17 markets/costs, persisted recommendation runs and versioned plans; finish frontend F05–F11. All `/api/v1` routes come from the same shared service layer established in S04. | API-01–12 plus WEB-01–15 and Q17 pass. Missing financial evidence disables financial results, not profile/field CRUD. No production screen or initial HTML depends on seeded data. |
| S11 — Full integrated acceptance | Requires completed atomic registries and all required domain/application tasks, not merely route availability. Reconcile raw assets, database, all exports, API and browser. | E2E-01–09 and the full expected case matrix pass; zero required blockers, skips, omitted children or untested source bindings. |
| S12 — Reproduce and hand over | Requires S11. Run package, CLI, API/worker and independent frontend build from clean processes with documented public configuration. | Final fresh acceptance, contract compatibility and reproducible deployment pass; source, locks, migrations, full evidence/coverage and exact commands delivered. |

For each S05–S10 domain task, finish all applicable CONN cases for its source bindings as well as feature checks before accepting it. S04 may expose completed resources and explicit unavailable states while other tasks are blocked. It must not wrap `run_pipeline()` unchanged: that function currently owns file IO, database initialization and acquisition as one operation. S11 repeats the entire required matrix.

Assign every F16 supplementary family and child to its producing step: field context to S03; station/raster context to the relevant S05/S06 task; crop/trial context to S07; biology/rotation/management to S08; device/sample to S09; provenance/output to S02 and each consumer. F17 belongs to S10. Record family ownership in S01 and expand exact child bindings before each domain task. Unresolved bindings remain in the coverage denominator with blockers.

### 2.1 Working method within each step

Implement each step directly in reusable Python files under `src/agri_data/`, with executable tests under `tests/` and documented CLI entry points. Use concise comments and docstrings where they explain scientific assumptions, unit conversions, source-specific behavior or non-obvious decisions. Keep acquisition, geographical processing, validation, storage, orchestration and API serialization in coherent modules; CLI and API paths must call the same domain implementation. Use small real requests to limit download size, inspect raw responses and intermediate results, and save actual run outputs, provenance and test evidence as files. Build and validate the modules as each step progresses; S12 verifies reproducibility and handover. No Jupyter notebooks or later notebook-to-Python conversion are required.

S01 identifies the authentic field/record needed for S02/S03; if unavailable, list the blocked acceptance cases rather than inventing a corpus or preventing independent contract work. Raster/station evidence is required when those capabilities are tested, not before profile CRUD. Existing provenance-verified files or small direct provider downloads may support infrastructure tests without implying the automated domain adapter is complete.

For each task, a model must: read its prerequisite evidence and relevant source files; declare the exact schema/source binding and affected consumers; make one bounded change; execute its listed cases; record evidence or the exact blocker; then select the next ready task. Do not implement all rows of a domain in a single unchecked pass. Never silently change authentication, units, applicability, the acceptance denominator or user-visible behavior to bypass a blocker.

Use existing `sources/`, `geo/`, `processing/`, `storage/` and `pipeline/` modules where their behavior is sound. Add `schemas/` for DTOs, `services/` for shared operations, `api/` for thin routes, `validation/` for the acceptance runner, and versioned migrations under `migrations/`. Proposed focused test locations are `tests/api/`, `tests/contracts/` and `tests/acceptance/`; they do not exist yet. Keep provider calls, scientific transforms and database transactions out of route handlers. Replace the duplicated raw HTTP path in `pipeline/acquisition.py` with adapter calls, preserve original response bytes before JSON parsing, and stop `storage/database.py` from seeding unsourced scientific values.

`pyproject.toml` will be authoritative; generate `requirements.txt` from the selected lock rather than maintaining two graphs. Prefer one PostgreSQL driver (`psycopg` with SQLAlchemy's `postgresql+psycopg` URL) and add only dependencies used by the task. Record supported Python/Node/package-manager versions after a clean compatibility check, not by guessing. Do not reuse the checked-in Compose credentials, fixed container names or exposed database ports on a shared machine; configure secrets, an isolated Compose project, a non-superuser application role and loopback-bound ports where needed.

Use Python with pandas/NumPy, GeoPandas/Shapely/pyproj/GDAL, rasterio/rioxarray/xarray, NetCDF and Parquet support, HTTP and provider clients, SQLAlchemy/GeoAlchemy with a PostgreSQL driver, FastAPI/Pydantic/Uvicorn, and pytest. The authoritative Python dependency definition must include the packages actually imported for PostgreSQL, KML/XML parsing, migrations, settings, multipart uploads, authentication and API tests. At minimum reconcile the currently split declarations for `psycopg`, `pyogrio`, `fastkml`, `defusedxml`, `alembic`, `pydantic-settings`, `python-multipart`, `httpx`, and the selected password/JWT implementation. Remove Jupyter from runtime requirements unless a documented runtime path truly uses it. Verify and lock exact dependency versions during implementation; library installation/import checks supplement actual service tests.

Implement and document these acceptance commands as part of the work; the commands below specify the required interface, not existing functionality:

```bash
python -m agri_data validate --suite connections --config config/acceptance.yaml
python -m agri_data validate --suite database --config config/acceptance.yaml
python -m agri_data validate --suite features --config config/acceptance.yaml
python -m agri_data validate --suite all --fresh --config config/acceptance.yaml
```

Implement the runner before relying on these commands. Add `--step`, `--feature-id` and `--source-binding-id` filters for bounded development runs; a filtered result must say `partial_scope: true` and cannot satisfy full completion. Each ledger task records its exact executable test selector. The final command must discover all required cases, make fresh requests for every claimed online route, read immutable authenticated-origin artifacts for import-only routes, and perform real database writes/readbacks. It returns nonzero for any required failure, blocker, uncollected or skipped case. Report import replay separately from current online connectivity.

Before S04, generate the draft contract from DTOs without advertising working endpoints. In S04 replace it with the running application's generated OpenAPI and require exact operation/schema parity. The future startup interface is `python -m uvicorn agri_data.api.app:create_app --factory`; worker and migration commands must be documented when implemented. The current CLI only accepts a positional KML file; preserve an explicit deprecated compatibility invocation while adding `run`, `validate`, `status`, `export` and `worker`. Do not silently supply its current fixed year/date defaults for new runs.

### 2.2 Frontend audit and dependency impact

The audited frontend is the pinned `origin/frontend` commit above, not a machine-specific Linux directory. It has seven views in `src/main.js`, a single HTML page, Leaflet, Vite, and an npm lock. `vite.config.js` sets development port 8080; this is not a production origin or an API URL. There is no current HTTP client, session UI, route contract or frontend test command. A prior build success is reported in `progress.md`; this document audit did not rerun it. Native `fetch` is sufficient; Axios is not required.

The following application dependencies are not yet taken care of and are mandatory work for S01, S02 and S10:

| Current frontend behavior | Required backend/integration dependency |
| --- | --- |
| `storageService.js` seeds farmer profiles, fields, soil records and plans into `localStorage`. | Authenticated CRUD APIs, server ownership checks, PostgreSQL persistence, migrations and an explicit one-time migration or discard policy for existing local browser records. Production must not auto-seed demo records. |
| `karnatakaCrops.js`, `marketData.js` and `environmentalData.js` contain hardcoded agronomic, financial, climate, satellite and time-series values. | Versioned crop/reference, market-observation, climate, satellite-series and availability endpoints backed by authentic records and provenance. Static UI labels may remain bundled; scientific or financial values may not. |
| `recommendationEngine.js` calculates in the browser and defaults missing pH, texture, climate and other inputs to plausible values. | A server-side, versioned recommendation service with required-input validation, explainable rules/model version, lineage, immutable run records and explicit missing-input results. No scientific fallback defaults. |
| Plot IDs and plan IDs use `Date.now()`; a soil-card number can use `Math.random()`. | Server-generated stable IDs and uniqueness constraints. Imported external identifiers remain separate provenance-bearing fields and must never be fabricated. |
| Drawn plot area is an approximate browser calculation and new plots without geometry receive a generated district box. | Geometry validation and authoritative geodesic/projected area in PostGIS. Geometry is required unless an explicit non-spatial draft state is supported; never generate a fake boundary. |
| The frontend exports GeoJSON/KML locally but does not import KML/KMZ. | Validated multipart KML/KMZ upload plus server-generated GeoJSON/KML exports supporting holes and MultiPolygons, with content-size/type limits and XML safety. |
| There is no API client, authentication, authorization, loading state, structured error handling or conflict handling. | A configurable API base URL, authenticated client, typed OpenAPI contract, standard errors, pagination, request IDs, optimistic-concurrency/version fields and UI loading/empty/error/blocked states. |
| Leaflet loads Esri tiles and the page loads Google Fonts directly from third parties. | Document network/licence/privacy requirements, configure allowed CSP/connect/style/font origins, and provide a deliberate offline/Tailscale behavior. Tile/font failure must not be mistaken for backend data failure. |
| User-controlled values are interpolated into `innerHTML`. | Output encoding or safe DOM rendering before API data is displayed; add stored-XSS acceptance coverage. |
| There are no frontend unit, contract or browser tests and no declared Node engine. | Lock a supported Node version and package manager; add a unit/DOM test runner and browser E2E harness (for example Vitest/jsdom and Playwright), plus an OpenAPI compatibility check. Add packages only when the selected implementation imports or runs them, then commit the updated lockfile. |

The API/frontend contract must preserve field names only where they are scientifically and semantically correct. Create an explicit mapping/migration instead of shaping the database around accidental demo-object names. Every value shown in the dashboard, land analysis, crop recommendation, market and planting-plan screens must be classified as user-entered, authentic observation, published reference, derived result, or unavailable.

The exact audit, M01–M18 mapping, request/response shapes, route matrix and frontend F01–F11 handoff are in [docs/frontend_api_contract.md](docs/frontend_api_contract.md). In particular, inspect `index.html` as well as JavaScript: it contains unbound forecast values, fixed dates, prices and profile defaults. Remove the static domain values before a migrated build is exposed; unmigrated screens must show unavailable states, not retained demos. Revise frontend F02's permission to keep existing data before enabling that build.

## 3. Architecture, registries and database contract

Data flow: authenticated user or actual KML/records → geographical selection → authenticated retrieval/import → immutable raw assets → semantic normalization → quality evaluation → PostgreSQL/PostGIS → versioned API → frontend and complete exports. Retain failed/rejected evidence separately. Invalid records may be stored in a quarantine table for diagnosis, but cannot enter the accepted observations view, API recommendation inputs or derived outputs.

### 3.1 Mandatory registries

Create versioned configuration/registries for projects, feature families, atomic variables, source products, source-variable bindings, instruments, crop species/cultivars, processing methods and acceptance cases.

Each atomic variable definition must contain:

- `variable_id`, `feature_id`, name, precise meaning, domain and record kind.
- Value type (`number`, `integer`, `text`, `boolean`, `date`, `category`, `geometry`, `series`, `curve`), cardinality, permitted categories and schema.
- Canonical unit, original-unit handling, measurement basis, conversion formula and authoritative reference.
- Required temporal interval, soil depth, spatial support, crop/cultivar/stage, analyte, statistic, treatment, scenario and reference-period dimensions where applicable.
- Whether it is an observation, published requirement, recommendation, source estimate or derived indicator; permitted evidence types.
- Required inputs and formula for derived features; minimum history/sample size and explicit missing-input rules.
- Required source bindings and exact provider field/band/parameter/document locator.
- Physical limits and scientific consistency checks, with references; absolute/relative comparison tolerances and coverage thresholds fixed before executing tests.
- Applicability rules, acceptance datasets, independent expected-value evidence and FEAT test IDs.

Source-product definitions must include provider, access type, actual tested location/endpoint, product/version/collection, licence, authentication reference, spatial/temporal coverage, native resolution, units, missing codes, quality flags, response schema, retry/rate-limit policy and connection test IDs. Keep credentials out of registries, logs and exports.

A source binding connects **one atomic variable to one actual product field and transformation**. A generic `source_id` without a product mapping is insufficient. Validate every implemented binding, including secondary sources. Distinct provider versions and product variants require separate bindings and tests.

### 3.2 Database requirements

PostgreSQL/PostGIS is mandatory. Use a real persistent acceptance instance or isolated schema and real commits; teardown only acceptance-owned records. Production credentials and an in-memory database cannot be substituted for this test environment.

Required tables/entities:

| Entity | Required purpose |
| --- | --- |
| `projects`, `fields`, `field_boundaries` | Project configuration, stable field identity, spatial geometry and original/revised boundaries |
| `feature_requirements`, `variables`, `source_bindings` | Full inventory, atomic definitions, coverage denominator and exact source mappings |
| `data_sources`, `datasets`, `source_assets` | Provider/product versions, raw files, original metadata, checksums and provenance |
| `extraction_jobs`, `processing_runs` | Requests/imports, parameters, code/configuration versions, timing, failures and reproducibility |
| `observations`, `observation_lineage`, `quarantined_records` | Typed values, contextual dimensions, all derived parents, rejected data and validation reasons |
| `crop_species`, `crop_varieties`, `crop_growth_stages`, `crop_parameters` | Taxonomy, cultivar/stage-specific requirements and published growth parameters |
| `crop_trials`, `crop_performance` | Real experimental conditions, treatments, replications and measured outcomes |
| `biological_agents`, `crop_biological_risks` | Organism identities, susceptibility/host relationships and links to actual incidence observations |
| `rotation_effects` | Directional preceding/following crop effects with study and before/after context |
| `management_events`, `farmer_surveys` | Actual cultivation events and provenance-bearing submissions |
| `sensor_deployments`, `sensor_readings`, `laboratory_samples` | Devices, sites, calibration, sample methods, actual recordings and reports |
| `validation_results`, `requirement_coverage` | Test evidence, availability, applicability and completion status |
| `users`, `farmer_profiles`, `user_field_roles` | Authentication identity, farmer profile and field-level ownership/authorization without placing secrets in domain tables |
| `market_observations`, `market_sources` | Authentic commodity/mandi prices, units, observation times, quality and source lineage |
| `recommendation_runs`, `recommendation_items` | Versioned inputs, rules/model version, exclusions, uncertainty, ranked results and provenance for reproducible recommendations |
| `planting_plans`, `planting_plan_versions` | User plans, selected field/crop, dates, acreage, budget assumptions, status and optimistic-concurrency history |
| `auth_sessions`, `idempotency_requests` | Revocable sessions for the approved auth design and actor/route/payload-scoped mutation replay |
| `boundary_imports`, `boundary_import_candidates` | Owner-scoped immutable import previews, repair decisions, confirmation versions and resulting field IDs |
| `record_submissions`, `record_revisions` | Auditable unverified soil/water/management submissions, source report links and corrections before acceptance |
| `satellite_scenes`, `scene_assets`, `forecast_runs` | Field/geometry-version scene selection, real overlay assets, forecast issue/validity times and source identity |
| `markets`, `commodities`, `commodity_crop_mappings`, `support_prices` | Provider market/commodity/grade identities and dated policy prices without conflating crops, cultivars or observations |
| `cost_records`, `economic_scenarios` | Authentic costs/fees and immutable conditional financial calculations, input versions and assumptions |

Use foreign keys, appropriate check constraints, typed columns and spatial indexes. Preserve categorical/text values, time series, response curves and geometry; do not force everything into a single floating-point field. Child records for series/curves must carry coordinates/axis units, sequence and contextual IDs.

Store geometries with explicit CRS; geographic storage uses EPSG:4326. Perform area/distance calculations in an appropriate projected CRS. Persist the native source grid and resolution metadata. Store both station-to-field matching context and exact field measurements without conflating them.

Idempotency keys must include enough context to distinguish source/product/version, field or region, variable, time/depth/stage, statistic, scenario and processing version. Preserve repeated measurements that are genuinely distinct. Database timestamps must distinguish observation time from retrieval time.

### 3.3 Acquisition and processing behavior

- Use a consistent adapter interface for retrieval/import, normalization, validation and provenance. Orchestration must call this interface; do not maintain a second HTTP path that bypasses adapter rules.
- HTTP errors, authentication failures, unexpected schemas and empty responses become explicit failures/unavailability. Retry only documented transient failures with bounded attempts and retained diagnostics.
- Cache authentic raw assets using source/version/geometry/variables/dates/depths/statistic/scenario in the key. Cache hits preserve original provenance and do not prove current connectivity.
- Query point services at a representative point inside the geometry and label point/grid support accurately. Do not claim polygon extraction for point queries.
- For rasters, use actual polygon intersections, quality masks, nodata rules and documented weighting. Preserve native resolution; resampling does not improve information content.
- For stations/wells, retain location, distance, elevation difference, observation period, station selection rule and representativeness. An out-of-field station remains an out-of-field observation.
- Keep field-only and buffered-region observations distinguishable. Buffer sizes are configurable with a scientific purpose.
- Derive values only after input records pass validation. Missing dependencies produce `insufficient_inputs`, never fabricated values.
- Human-entered/transcribed records must link to an actual report, page/table/cell, submission or device file. Verify transcription independently.

### 3.4 Versioned API and frontend contract

Implement a FastAPI application under `src/agri_data/api/` with an `/api/v1` prefix and generated OpenAPI schema. Domain services, validation and repositories must be shared with the CLI; route handlers must not duplicate scientific logic. Use environment-based configuration, structured logs, request IDs, bounded request/body sizes, health/readiness endpoints and documented startup/shutdown behavior. Never expose database/provider credentials or raw internal exception traces.

Authentication is required before storing farmer information. Use a reviewed password/session or bearer-token design with secure password hashing, expiry/revocation and transport assumptions documented. Every profile, field, upload, plan, recommendation and export query must enforce owner or explicit role access at the database/service layer. CORS must allow only configured frontend origins and methods; do not combine wildcard origins with credentials.

Required resource groups and operations:

| Resource group | Required operations and response requirements |
| --- | --- |
| System | `GET /health`, `GET /ready`, API/schema version and dependency status without secrets. Readiness verifies the real database and required migrations. |
| Identity/profile | Login/session lifecycle as selected; get/update the authenticated farmer profile; validate phone and locale fields without treating a phone number as proof of identity. |
| Fields/boundaries | List/create/get/update/archive fields; accept valid GeoJSON; upload KML/KMZ; retain original and repaired geometry; return authoritative area in hectares/acres, representative point, geometry version and validation notes. |
| Soil, water and management records | Create/import/list versioned user or laboratory records with source/report metadata; never turn an unverified form submission into a verified laboratory result. |
| Observations/analysis | Paginated/filterable feature status, observations, climate, vegetation/satellite time series, water and hazard summaries. Every value includes unit, period, evidence type, quality, availability and provenance links. |
| Crop/reference data | List crops/cultivars, requirements, risks and management references with source/version metadata; separate published guidance from field observations. |
| Recommendations | Submit a field/season/objective request, validate required inputs, run a versioned rule/model implementation, persist the complete input/result/explanation, and return suitable, excluded and unavailable outcomes. Missing data never invokes a plausible fallback. |
| Markets/economics | Query authentic commodity/mandi observations by crop, place and time; include currency, quantity unit, observed time, source and freshness. Financial scenarios retain every input/assumption and do not claim current prices from stale records. |
| Planting plans | List/create/update/archive plans using server IDs, ownership checks and optimistic concurrency. Persist selected field/crop, dates, area, assumptions, recommendation reference and revision history. |
| Jobs/validation | Start permitted acquisition/import work, retrieve job status and validation/coverage details, and distinguish queued/running/failed/blocked/complete. Long-running work must not hold an HTTP request open. |
| Exports | Stream or provide expiring access to complete GeoJSON, KML and Section 4 bundles; set safe filenames/content types and enforce authorization. |

Use the concrete resource/list/error conventions in [the frontend contract](docs/frontend_api_contract.md), rather than choosing a second envelope while implementing routes. Validation errors identify the field and stable error code; conflicts cover stale updates and idempotency collisions. Unavailable scientific data uses Section 4 availability rather than `0`, empty strings or a successful-looking placeholder. List endpoints require bounded pagination, deterministic ordering and declared filters. Timestamps use ISO 8601 with explicit timezone; civil dates such as sample or planned sowing dates use `YYYY-MM-DD` without a guessed time. Geometry uses GeoJSON longitude/latitude; monetary values include currency and quantity basis.

Generate and commit an OpenAPI artifact for frontend compatibility checks. The frontend may keep native `fetch`, but must centralize base URL, authentication, timeouts/abort behavior, JSON/error parsing and retries. Retry only safe/idempotent operations. Client DTO adapters must map API resources into view models; components may not infer scientific defaults from absent values.

## 4. Required data output format

### 4.1 Complete export bundle

Every run writes a versioned bundle under `data/exports/<run_id>/`. Publish the manifest atomically only after referenced files are written; failed runs still emit a failure/coverage report.

| File | Required contents |
| --- | --- |
| `manifest.json` | Schema/run versions, status, actual start/end times, input/config/code hashes, source retrieval times, file paths, row counts and SHA-256 checksums |
| `fields.geojson`, `fields.gpkg` | Actual original/processed boundary references, IDs, names, CRS, area, perimeter, bounds, representative coordinates and repair notes; both formats preserve the same field identities and geometries |
| `feature_catalog.json` | Every required feature family and atomic variable, definitions, units, dimensions, source bindings and tests |
| `feature_status.jsonl` | Every expected field/crop/region × applicable variable × requested context, including missing/blocked requirements; never only returned observations |
| `observations.parquet` and `observations.jsonl` | All accepted normalized observations with matching IDs, values, metadata and row counts |
| `crop_parameters.jsonl`, `crop_trials.jsonl`, `crop_performance.jsonl` | Full crop requirements, real trial context and outcomes, including series/curves and references |
| `biological_risks.jsonl`, `rotation_effects.jsonl`, `management_events.jsonl` | Full structured records with relationships and evidence |
| `sensor_deployments.jsonl`, `sensor_readings.parquet`, `laboratory_samples.jsonl` | Actual devices, calibration/context, complete time series and sample/report references |
| `scenes.jsonl`, `forecasts.jsonl` | Actual scene/overlay assets and forecast runs with issue/valid time, source/version, quality and complete interval references |
| `market_observations.jsonl`, `support_prices.jsonl`, `cost_records.jsonl` | Dated commodity/market/grade prices, policy schedules and itemized costs with exact currency/quantity basis and raw lineage |
| `recommendation_runs.jsonl`, `economic_scenarios.jsonl`, `planting_plans.jsonl` | Authorized immutable inputs/results, assumptions, versions and references for the requested field/run context; credentials and sessions are never exported |
| `assets.jsonl`, `lineage.jsonl` | Raw-asset inventory and complete parent-child lineage to source records |
| `rejected_records.jsonl` | Rejected authentic records, original values, failure rules and reasons; excluded from accepted data |
| `validation_report.json`, `validation_report.md` | Every test instance, expected/actual outcomes, evidence, failed/blocked/skipped counts and full coverage totals |
| `profiles/<field_id>.json` | Human-accessible field summary linked to complete tables, including each feature's availability, source and limitations |

Raw GeoTIFF, NetCDF, JSON, CSV, PDF and device files remain immutable in the asset store. Bundle paths must resolve through the manifest without dependence on a temporary process directory. Large outputs may be partitioned; manifests must enumerate every partition and its count/checksum. No display limit, `head()`, sample subset or JSON truncation may become the stored/exported dataset.

### 4.2 Observation schema

Implement a versioned machine-validated schema. The following is a field specification, not an example containing invented agricultural values.

| Fields | Type and rule |
| --- | --- |
| `schema_version`, `observation_id`, `feature_id`, `variable_id` | Required stable identifiers |
| `subject_type`, `subject_id`, `field_id`, `region_id`, `geometry_ref` | Actual subject and geographical support; field ID nullable for regional/crop-wide records |
| `value_numeric`, `value_text`, `value_boolean`, `value_date`, `value_geometry`, `value_series_ref` | Exactly one typed value for a present observation; no NaN/Infinity in accepted exports |
| `original_value`, `original_unit`, `standardized_unit`, `measurement_basis` | Original representation plus verified normalization; include dry/fresh mass, analyte and area/depth basis |
| `observed_at`, `period_start`, `period_end`, `timezone`, `temporal_resolution` | Actual observation/support times; unknown dates remain null with a reason; never substitute retrieval date |
| `depth_top_cm`, `depth_bottom_cm`, `sample_id`, `sensor_id` | Required where depth/sample/device-dependent |
| `crop_id`, `cultivar_id`, `growth_stage_id`, `trial_id`, `treatment_id`, `season_id` | Required for relevant crop/trial records |
| `analyte`, `statistic`, `scenario_id`, `ensemble_member`, `reference_period` | Preserve applicable chemical/statistical/projection context |
| `evidence_type`, `source_id`, `dataset_id`, `source_binding_id`, `source_asset_id`, `source_record_locator` | Exact acquisition and record provenance |
| `extraction_method`, `spatial_support`, `spatial_resolution_m`, `native_crs`, `coverage_geometry_ref` | Actual extraction, native scale and represented geography |
| `valid_pixel_count`, `spatial_coverage_percent`, `temporal_coverage_percent`, `sample_count` | Actual denominators/counts; null if inapplicable, not fabricated defaults |
| `uncertainty`, `uncertainty_unit`, `uncertainty_method`, `quality_flags`, `validation_status` | Source/derived uncertainty, quality and test outcomes |
| `censoring_qualifier`, `detection_limit`, `detection_limit_unit` | Preserve below-detection/quantification-limit laboratory results without substituting zero or an invented concentration |
| `parent_observation_ids`, `method_id`, `processing_version`, `extraction_job_id` | Traceable derivations and processing context |
| `retrieved_at`, `created_at`, `raw_sha256` | Acquisition/storage audit information |

Allowed evidence types: `measured`, `surveyed`, `published_parameter`, `published_recommendation`, `satellite`, `modelled_product`, `reanalysis`, `projection`, `forecast`, `derived`. Forecasts retain issue time, valid time and provider/model identity; they are neither observed weather nor long-term climate projections. Preserve any more specific source classification alongside these. `synthetic`, `demo`, `augmented`, `mock` and locally `simulated` observations are forbidden in this dataset.

Each field's required/nullability conditions belong in the executable schema. Source-only fields such as `original_value` may be null for a derived record that has no single original source value, provided complete parent lineage is present. Never invent metadata to satisfy a required column; if an applicable required context is unknown, the record fails acceptance for that use.

### 4.3 Feature availability and structured domain records

Each `feature_status` entry contains `run_id`, `feature_id`, `variable_id`, subject, required dimensions, `required`, `applicability_reason`, `availability`, `observation_ids`, `attempted_source_bindings`, `validation_case_ids`, `reason`, `blocker`, and `next_action`.

Allowed availability states: `available`, `not_collected`, `not_available_from_source`, `outside_source_coverage`, `access_restricted`, `collection_failed`, `insufficient_inputs`, `insufficient_quality`, `not_applicable`, `below_detection_limit`. Censored laboratory results retain qualifier and detection limit; they are not ordinary zero values. `available` requires at least one accepted, authentic record with all applicable validation passed.

Crop parameter records retain minimum/optimum/maximum values when supplied, species/cultivar, stage, geography, source reference, evidence type and confidence. Trial records retain location, soil, weather period, sowing/harvest dates, irrigation/fertilizer treatments, replication count and experimental method. Performance records retain yield, biomass, germination, survival, water use, nutrient uptake, harvest index, observed stress and their uncertainty/context. Rotation records retain preceding/following crops, before/after soil, nutrient/moisture/carbon changes, residue/decomposition, shared diseases, yield effect, study location/duration and source. Management records retain actual dates, products, quantities, units, methods and field/crop association.

### 4.4 Human-readable feature view

Generate a complete table with these columns:

`Field/subject | Feature ID | Variable | Value | Unit/basis | Date/period | Depth | Crop/cultivar/stage | Source/product | Evidence type | Spatial support/resolution | Coverage | Quality | Availability/reason | Evidence link`

Use one row per observation/context. Render a reasoned missing row when a required feature has no data. Link series/curves and large arrays to complete artifacts. Multiple sources remain separate rows; do not average contradictory values silently. Display previews may paginate, but the complete export must remain accessible and preserve every record.

### 4.5 Units and aggregation

Require explicit canonical units: texture/coarse fragments/porosity in percent; pH dimensionless; EC in dS/m; soil carbon in g/kg; nutrients in mg/kg or kg/ha with distinct measurement bases; density in g/cm³; soil depth in cm; soil moisture in m³/m³; rainfall in mm; intensity/infiltration in mm/hour; temperature in °C; wind in m/s; humidity in percent; radiation in MJ/m²/day or W/m² with interval; elevation in m; slope in degrees or percent with explicit conversion; area in hectares; groundwater in m relative to its stated datum; yield/biomass in kg/ha with mass basis; water use in mm or m³/ha; nitrogen fixation in kg N/ha over a period; indices dimensionless; development in elapsed days or defined thermal time. Carbon productivity retains product-defined carbon mass/area/time. Other variables require a documented unit or categorical vocabulary before implementation.

Do not convert concentration to stock without real depth and density inputs. Do not equate soil salinity with water salinity, total nitrogen with available nitrogen, or nutrient uptake with fertilizer application.

For supported raster variables, retain mean, median, minimum, maximum, standard deviation, 10th/90th percentiles, valid pixel count and valid area percentage, with weighting definitions. Categorical rasters require class proportions/counts. Temporal outputs include daily values and valid monthly/seasonal/annual totals or means, trends and anomalies. Do not aggregate incomplete rainfall periods as if complete. Depth and time dimensions must survive every transformation.

## 5. Mandatory feature inventory

Every row below is a required feature family with a stable ID. The required-content column is binding. Source names are candidates to verify, not assertions of current connectivity or guaranteed plot-level availability. Section 1's authentic-data rules override any legacy expectation of acquiring locally simulated values from a model.

The inventory preserves all 277 original master-inventory feature rows and 20 supplementary families. This revision adds one forecast family and eight frontend-required economic families: 306 families total, not 306 atomic variables. S01 registers every family; each owning domain expands its compound contents/dimensions before implementation. Full acceptance requires the complete expanded registry and cannot use only the variables that happened to return data.

Each row must map to one or more atomic variables in the registry. Split explicitly named components (for example N/P/K or zinc/iron/copper/manganese/boron), minimum/optimum/maximum bounds, depth intervals, stages, categories and scenario/time dimensions without losing distinctions. A compound label cannot conceal missing children. Conversely, the same physical variable reused in several families may share one canonical ID with explicit links to all families.

All atomic variables require FEAT-01 through FEAT-09 and their domain Q profile from Section 8. These tests must be instantiated for each source binding and required context; checking one example variable does not cover a whole row or domain.

### 5.1 Soil characteristics — Q01

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F01-001 | Soil classification | Soil order, subgroup and classification system | NBSS&LUP, SoilGrids |
| F01-002 | Sand content | Percentage of sand particles | SoilGrids |
| F01-003 | Silt content | Percentage of silt particles | SoilGrids |
| F01-004 | Clay content | Percentage of clay particles | SoilGrids |
| F01-005 | Soil texture class | Sandy, silty, loamy, clayey and subclasses | Derived from particle fractions; Soil Health Card |
| F01-006 | Soil pH | Acidity or alkalinity | SoilGrids, Soil Health Card |
| F01-007 | Electrical conductivity | Soil salinity | Soil Health Card, laboratory |
| F01-008 | Soil sodicity | Exchangeable sodium, ESP and related indicators | Soil laboratory, agricultural universities |
| F01-009 | Organic carbon | Soil organic carbon concentration | SoilGrids, Soil Health Card |
| F01-010 | Organic matter | Organic matter concentration | Soil laboratory, derived from organic carbon |
| F01-011 | Total nitrogen | Total soil nitrogen | SoilGrids, laboratory |
| F01-012 | Available nitrogen | Plant-available nitrogen | Soil Health Card, laboratory |
| F01-013 | Available phosphorus | Extractable plant-available phosphorus | Soil Health Card, laboratory |
| F01-014 | Available potassium | Extractable plant-available potassium | Soil Health Card, laboratory |
| F01-015 | Sulphur | Available sulphur | Soil Health Card, laboratory |
| F01-016 | Micronutrients | Zinc, iron, copper, manganese and boron | Soil Health Card, laboratory |
| F01-017 | Calcium carbonate | CaCO₃ concentration | Soil surveys, laboratory |
| F01-018 | Cation exchange capacity | CEC | SoilGrids, laboratory |
| F01-019 | Bulk density | Dry soil mass per unit volume | SoilGrids, laboratory |
| F01-020 | Soil porosity | Total pore volume | Derived from bulk density and particle density |
| F01-021 | Coarse fragments | Gravel and rock fragment fraction | SoilGrids, soil survey |
| F01-022 | Total soil depth | Depth to bedrock or restrictive layer | NBSS&LUP, field survey |
| F01-023 | Effective rooting depth | Usable depth for crop roots | Soil survey, ICAR, field survey |
| F01-024 | Drainage class | Excess water removal characteristics | NBSS&LUP, soil surveys |
| F01-025 | Infiltration rate | Water entry rate into soil | Field tests, agricultural research |
| F01-026 | Hydraulic conductivity | Water movement through soil | Laboratory, pedotransfer functions |
| F01-027 | Field capacity | Soil water content after gravitational drainage | Laboratory, pedotransfer functions |
| F01-028 | Permanent wilting point | Soil water content at permanent wilting | Laboratory, pedotransfer functions |
| F01-029 | Available water capacity | Water between field capacity and wilting point | Derived from soil hydraulic data |
| F01-030 | Soil water retention curve | Relationship between water content and matric potential | Laboratory, pedotransfer functions |
| F01-031 | Soil contamination | Heavy metals, pesticide residues and other contaminants | Pollution monitoring, laboratory |
| F01-032 | Soil temperature | Temperature at specified soil depths | SoilGrids-related products only where suitable; field sensors; ERA5-Land for gridded context |

### 5.2 Terrain, topography and geology — Q02

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F02-001 | Elevation | Metres above sea level | Copernicus DEM, SRTM, ALOS |
| F02-002 | Slope | Degrees or percentage | Derived from DEM |
| F02-003 | Aspect | Direction faced by slope | Derived from DEM |
| F02-004 | Terrain curvature | Profile and plan curvature | Derived from DEM |
| F02-005 | Topographic wetness index | Relative water accumulation potential | Derived from DEM |
| F02-006 | Flow accumulation | Upstream contributing area | DEM, HydroSHEDS |
| F02-007 | Drainage density | Drainage length per unit area | HydroSHEDS, India-WRIS |
| F02-008 | Geological formation | Underlying geological unit | Geological Survey of India |
| F02-009 | Lithology | Rock and material type | GSI |
| F02-010 | Geomorphology | Landform and surface processes | Bhuvan, GSI |
| F02-011 | Soil parent material | Material from which soil developed | NBSS&LUP, GSI |
| F02-012 | Watershed membership | Catchment containing the plot | India-WRIS, HydroSHEDS |
| F02-013 | Landform position | Ridge, slope, valley, floodplain and similar categories | DEM, geomorphology maps |

### 5.3 Rainfall and precipitation — Q03

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F03-001 | Annual rainfall | Total annual precipitation | IMD, KSNDMC, NASA POWER |
| F03-002 | Monthly rainfall | Monthly precipitation | IMD, CHIRPS, NASA POWER |
| F03-003 | Daily rainfall | Daily precipitation | KSNDMC, IMD, NASA POWER |
| F03-004 | Rainfall intensity | Precipitation rate over shorter intervals | Rain gauges, GPM IMERG |
| F03-005 | Rainy days | Days above a defined rainfall threshold | Rainfall records |
| F03-006 | Growing-season rainfall | Rainfall during crop-season dates | Rainfall records + crop calendar |
| F03-007 | Rainfall distribution | Intra-seasonal distribution | Rainfall records |
| F03-008 | Monsoon onset | Arrival date based on official definition | IMD, KSNDMC |
| F03-009 | Monsoon withdrawal | Withdrawal date | IMD |
| F03-010 | Rainfall variability | Interannual and seasonal variation | IMD, CHIRPS |
| F03-011 | Extreme rainfall frequency | Frequency of heavy rainfall events | IMD, GPM |
| F03-012 | Longest dry spell | Maximum consecutive dry days | Daily precipitation |
| F03-013 | Rainfall anomaly | Deviation from historical normal | IMD, CHIRPS |
| F03-014 | SPI | Standardized precipitation index | CHIRPS, IMD, GPM |
| F03-015 | SPEI | Standardized precipitation and evaporative-demand index | CHIRPS + ET0/ETp |
| F03-016 | Long-term rainfall trends | Multi-year or decadal change | IMD, CHIRPS, ERA5-Land |

### 5.4 Atmospheric climate — Q04

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F04-001 | Average temperature | Daily/monthly mean air temperature | IMD, NASA POWER, ERA5-Land |
| F04-002 | Maximum temperature | Daily maximum temperature | IMD, NASA POWER |
| F04-003 | Minimum temperature | Daily minimum temperature | IMD, NASA POWER |
| F04-004 | Diurnal temperature range | Daily maximum minus minimum | Derived |
| F04-005 | Relative humidity | Mean and maximum/minimum humidity | IMD, NASA POWER, ERA5-Land |
| F04-006 | Dew point | Daily/monthly dew point | ERA5-Land |
| F04-007 | Vapour pressure deficit | Atmospheric drying demand | Temperature + humidity |
| F04-008 | Wind speed | Mean and maximum wind speed | NASA POWER, ERA5-Land |
| F04-009 | Wind direction | Direction of wind | ERA5-Land, weather stations |
| F04-010 | Atmospheric pressure | Surface pressure | ERA5-Land |
| F04-011 | Solar radiation | Incoming shortwave solar energy | NASA POWER, ERA5-Land |
| F04-012 | Net radiation | Net radiative energy | ERA5-Land, derived |
| F04-013 | Sunshine duration | Daily hours of sunshine | IMD/weather station |
| F04-014 | Cloud cover | Total cloud fraction | ERA5-Land |
| F04-015 | Heatwave frequency | Events under a defined heatwave criterion | IMD, weather stations |
| F04-016 | Cold spell frequency | Unusually cold event count | IMD |
| F04-017 | Frost occurrence | Freezing-temperature events | Weather stations, ERA5-Land |
| F04-018 | Growing degree days | Accumulated crop-available thermal time | Temperature + crop base temperature |
| F04-019 | Potential evapotranspiration | Potential evaporative demand | ERA5-Land, TerraClimate |
| F04-020 | Reference evapotranspiration ET0 | Standardized reference-crop water demand | Weather variables, FAO-56 Penman–Monteith |
| F04-021 | Climate classification | Arid, semi-arid, tropical, etc. | WorldClim, Köppen-Geiger |
| F04-022 | Aridity index | Precipitation relative to potential ET | CHIRPS + ET dataset |
| F04-023 | Climate projections | Future temperature and precipitation scenarios | CMIP6, WorldClim |
| F04-024 | Operational weather forecast | Provider-issued temperature, wind, precipitation and condition by forecast interval; issue time, valid time, model and geographical support | Authentic forecast publication/feed selected under SRC-063; not historical NASA POWER |

### 5.5 Water resources and availability — Q05

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F05-001 | Surface-water extent | Geographic water-body extent | JRC Global Surface Water, Sentinel-2 |
| F05-002 | River network | River locations and connectivity | HydroSHEDS, India-WRIS |
| F05-003 | Reservoir storage | Total stored water | India-WRIS, water authorities |
| F05-004 | Reservoir water level | Water surface level | Water authorities |
| F05-005 | Canal network | Canal location | India-WRIS, irrigation departments |
| F05-006 | Irrigation command area | Land served by an irrigation scheme | India-WRIS, irrigation departments |
| F05-007 | Surface runoff | Overland water flow | ERA5-Land, hydrological models |
| F05-008 | Streamflow | River discharge | Water authorities, hydrological models |
| F05-009 | Flood extent | Extent of historical inundation | Sentinel-1, NRSC |
| F05-010 | Flood frequency | Repeated flooding history | Sentinel-1, historical flood maps |
| F05-011 | Groundwater level | Depth below ground level | CGWB, state groundwater departments |
| F05-012 | Groundwater trends | Seasonal and long-term groundwater variation | CGWB |
| F05-013 | Aquifer type | Water-bearing formation type | CGWB |
| F05-014 | Aquifer thickness | Thickness of saturated aquifer | CGWB |
| F05-015 | Aquifer transmissivity | Groundwater transmission capacity | CGWB |
| F05-016 | Groundwater recharge | Estimated water added to aquifers | CGWB, recharge models |
| F05-017 | Groundwater extraction | Estimated withdrawals | CGWB |
| F05-018 | Groundwater availability | Available extractable resources | CGWB |
| F05-019 | Groundwater quality | Dissolved chemistry and contaminants | CGWB, laboratory |
| F05-020 | Total dissolved solids | Dissolved material concentration | Laboratory |
| F05-021 | Water pH | Acidity or alkalinity | Laboratory |
| F05-022 | Water EC | Irrigation-water salinity | Laboratory |
| F05-023 | Sodium adsorption ratio | Sodium hazard | Laboratory, derived |
| F05-024 | Chloride concentration | Chloride content | Laboratory |
| F05-025 | Fluoride concentration | Fluoride content | CGWB, laboratory |
| F05-026 | Nitrate concentration | Nitrate content | CGWB, laboratory |
| F05-027 | Surface soil moisture | Near-surface moisture estimate | SMAP, ERA5-Land |
| F05-028 | Root-zone soil moisture | Moisture in deeper soil layers | SMAP L4, ERA5-Land |
| F05-029 | Actual evapotranspiration | Actual water loss through evaporation and transpiration | MODIS ET, suitable satellite ET products |
| F05-030 | Irrigation coverage | Area receiving irrigation | Agricultural statistics, satellite mapping |
| F05-031 | Irrigation infrastructure proximity | Distance to canals, reservoirs and water sources | India-WRIS, mapped networks |
| F05-032 | Irrigation water demand | Estimated irrigation requirement | ET0, crop parameters, soil data |

### 5.6 Historical land and vegetation — Q06

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F06-001 | Land cover | Forest, crop, grass, water, urban etc. | ESA WorldCover, Dynamic World |
| F06-002 | Land use | Agricultural, residential, industrial etc. | Bhuvan, land surveys |
| F06-003 | Crop type | Estimated crop grown in a season | Sentinel-2, Landsat, crop maps |
| F06-004 | Cropping intensity | Crop cycles per year | Satellite classification, agricultural statistics |
| F06-005 | Cropping calendar | Planting and harvesting timing | ICAR crop calendars, satellite time series |
| F06-006 | NDVI | Vegetation greenness | Sentinel-2, Landsat, MODIS |
| F06-007 | EVI | Enhanced vegetation index | MODIS, Sentinel-2 |
| F06-008 | SAVI | Soil-adjusted vegetation index | Sentinel-2, Landsat |
| F06-009 | NDMI | Vegetation moisture-related index | Sentinel-2, Landsat |
| F06-010 | LAI | Leaf area index | MODIS, Sentinel-2-derived products |
| F06-011 | fAPAR | Fraction of absorbed photosynthetically active radiation | MODIS |
| F06-012 | Vegetation cover | Proportion covered by vegetation | Sentinel-2, Landsat |
| F06-013 | Phenology | Green-up, peak growth and senescence dates | MODIS, Sentinel-2 |
| F06-014 | Vegetation productivity | Productivity over time | MODIS |
| F06-015 | GPP | Gross primary productivity | MODIS |
| F06-016 | NPP | Net primary productivity | MODIS |
| F06-017 | Above-ground biomass | Estimated mass of above-ground vegetation | Satellite products and models |
| F06-018 | Tree cover | Percentage canopy cover | Global Forest Watch, Landsat |
| F06-019 | Forest changes | Forest gain/loss over time | Landsat, Global Forest Watch |
| F06-020 | Vegetation anomalies | Deviations from historical vegetation patterns | NDVI/EVI historical series |
| F06-021 | Historical vegetation trends | Long-term vegetation trajectory | Landsat, MODIS, Sentinel-2 |
| F06-022 | Burned area | Areas affected by fire | MODIS, NASA FIRMS |
| F06-023 | Crop stress indicators | Abnormal growth, moisture and temperature conditions | Sentinel-2, MODIS, ERA5-Land |

### 5.7 Environmental degradation and natural hazards — Q07

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F07-001 | Soil erosion susceptibility | Risk of water/wind erosion | DEM, soil maps, RUSLE inputs |
| F07-002 | Soil erosion rate | Estimated soil loss per area per year | RUSLE, field studies |
| F07-003 | Land degradation | Changes in land condition/productivity | ISRO, Bhuvan, UNCCD |
| F07-004 | Desertification risk | Risk of arid land degradation | ISRO, UNCCD |
| F07-005 | Waterlogging extent | Extent of prolonged saturation | Sentinel-1, field surveys |
| F07-006 | Landslide susceptibility | Probability of slope failure | GSI, DEM, hazard maps |
| F07-007 | Cyclone exposure | Historical cyclone events affecting area | IMD, disaster records |
| F07-008 | Hailstorm occurrence | Historical hail events | IMD, station records |
| F07-009 | Wildfire risk | Fire occurrence and susceptibility | NASA FIRMS, MODIS |
| F07-010 | Lightning frequency | Historical lightning activity | Lightning networks, available regional datasets |
| F07-011 | Drought severity | Historical drought intensity | IMD, SPI, SPEI, vegetation anomalies |

### 5.8 Atmospheric and environmental quality — Q08

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F08-001 | PM2.5 | Fine particulate concentration | CPCB, OpenAQ |
| F08-002 | PM10 | Coarse particulate concentration | CPCB, OpenAQ |
| F08-003 | Aerosol optical depth | Atmospheric aerosol loading | MODIS |
| F08-004 | Nitrogen dioxide | Atmospheric NO₂ | Sentinel-5P, CPCB |
| F08-005 | Sulphur dioxide | Atmospheric SO₂ | Sentinel-5P, CPCB |
| F08-006 | Carbon monoxide | Atmospheric CO | Sentinel-5P |
| F08-007 | Ozone | Atmospheric ozone concentration | Sentinel-5P, monitoring stations |
| F08-008 | Air quality index | Composite air quality assessment | CPCB |

### 5.9 Crop-specific environmental requirements — Q09

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F09-001 | Minimum temperature | Minimum temperature tolerated | EcoCrop, ICAR, DSSAT |
| F09-002 | Optimal temperature | Ideal temperature for growth | EcoCrop, ICAR, APSIM |
| F09-003 | Maximum temperature | Maximum tolerated temperature | EcoCrop, ICAR, DSSAT |
| F09-004 | Stage-specific temperature | Temperature requirements at germination, vegetative growth, flowering and maturity | DSSAT, APSIM, ICAR |
| F09-005 | Rainfall requirement | Minimum, optimum and maximum rainfall | EcoCrop, GAEZ, ICAR |
| F09-006 | Soil pH tolerance | Minimum, optimum and maximum pH | EcoCrop, ICAR |
| F09-007 | Soil texture preference | Preferred sand, silt and clay fractions or texture class | EcoCrop, ICAR, crop trials |
| F09-008 | Effective soil depth requirement | Minimum rooting depth | ICAR, DSSAT, APSIM |
| F09-009 | Drainage preference | Well-drained, moderately drained or poorly drained | EcoCrop, ICAR |
| F09-010 | Nutrient requirements | N, P, K, S and micronutrients | ICAR, DSSAT, APSIM |
| F09-011 | Nutrient requirements by stage | Nutrient demand at each developmental stage | DSSAT, APSIM, ICAR trials |
| F09-012 | Salinity tolerance | Maximum acceptable soil EC | EcoCrop, ICAR, FAO research |
| F09-013 | Salinity yield response | Yield reduction at different EC levels | ICAR research, crop trials |
| F09-014 | Altitude tolerance | Minimum, optimum and maximum elevation | EcoCrop, ICAR, GAEZ |
| F09-015 | Growing-period requirements | Minimum, optimum and maximum lifecycle duration | EcoCrop, ICAR, FAO crop calendars |
| F09-016 | Photoperiod sensitivity | Critical day length and flowering response | DSSAT, APSIM, ICAR research |
| F09-017 | Light requirements | Light intensity and daily light integral requirements where available | ICAR, crop physiology studies |
| F09-018 | Waterlogging preference | Tolerance to saturated soil | ICAR, GAEZ, crop trials |
| F09-019 | Water availability preference | Crop-specific water demand | FAO, DSSAT, APSIM |

### 5.10 Germination and early crop establishment — Q10

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F10-001 | Germination temperature minimum | Minimum temperature allowing germination | ICAR, DSSAT, trials |
| F10-002 | Germination temperature optimum | Ideal germination temperature | ICAR, trials |
| F10-003 | Germination temperature maximum | Upper germination temperature | ICAR, trials |
| F10-004 | Germination rate | Percentage of seeds germinating under specified conditions | Seed-testing laboratories, ICAR |
| F10-005 | Time to germination | Days/hours until germination | Seed laboratories, trials |
| F10-006 | Seed emergence rate | Percentage of planted seeds emerging above soil | ICAR, field trials |
| F10-007 | Emergence time | Time between sowing and emergence | Field trials, DSSAT |
| F10-008 | Seedling establishment requirements | Moisture, temperature and soil conditions required | ICAR, APSIM, DSSAT |
| F10-009 | Seedling survival rate | Percentage surviving the initial establishment period | Crop trials, farmer records |
| F10-010 | Early root growth | Root growth during establishment | DSSAT, APSIM, ICAR |
| F10-011 | Early root depth | Depth reached during early stages | ICAR, DSSAT, APSIM |
| F10-012 | Early nutrient demand | Nutrients consumed by seedlings | ICAR, DSSAT, APSIM |

### 5.11 Crop development and growth — Q11

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F11-001 | Root growth rate | Root development per unit time | DSSAT, APSIM, trials |
| F11-002 | Root depth by growth stage | Root depth during each stage | DSSAT, APSIM, ICAR |
| F11-003 | Leaf development rate | Rate of leaf appearance | DSSAT, APSIM |
| F11-004 | Leaf area index | Leaf area relative to ground area | MODIS, Sentinel-2, ICAR |
| F11-005 | LAI development curve | LAI at different growth stages | DSSAT, APSIM, MODIS |
| F11-006 | Vegetative growth rate | Increase in stems and leaves | DSSAT, APSIM, crop trials |
| F11-007 | Biomass accumulation | Dry matter production over time | DSSAT, APSIM, ICAR |
| F11-008 | Flowering initiation | Timing and triggering conditions for flowering | DSSAT, APSIM, ICAR |
| F11-009 | Flowering duration | Number of flowering days | ICAR, APSIM, crop trials |
| F11-010 | Pollination type | Self-pollination, cross-pollination or other | ICAR, crop manuals |
| F11-011 | Pollinator dependence | Degree of dependence on external pollinators | ICAR, research papers |
| F11-012 | Pollination window | Period during which pollination occurs | ICAR, crop trials |
| F11-013 | Fruit/pod/grain formation duration | Length of reproductive development | DSSAT, APSIM, ICAR |
| F11-014 | Grain filling duration | Time between grain formation and physiological maturity | DSSAT, APSIM, ICAR |
| F11-015 | Crop maturity duration | Time to physiological maturity and harvest maturity | FAO calendars, DSSAT, APSIM, ICAR |
| F11-016 | Harvest index | Harvested biomass relative to total above-ground biomass | DSSAT, APSIM, ICAR |
| F11-017 | Water-use efficiency | Biomass or yield produced per unit of water consumed | DSSAT, APSIM, ICAR |
| F11-018 | Nutrient-use efficiency | Production relative to nutrient uptake or application | DSSAT, APSIM, ICAR |

### 5.12 Crop performance and historical success — Q12

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F12-001 | Historical crop yield | Actual yield per crop and season | FAOSTAT, ICAR, ICRISAT, state statistics |
| F12-002 | Yield per hectare | Standardized crop productivity | FAOSTAT, agricultural statistics |
| F12-003 | Yield variability | Variation between years and locations | FAOSTAT, ICAR, crop trials |
| F12-004 | Crop failure frequency | Frequency of failed crops | Field trials, farmer records, agricultural statistics |
| F12-005 | Crop survival | Percentage of planted crop surviving | Field trials |
| F12-006 | Yield response to temperature | Change in yield under different temperatures | ICAR, DSSAT, APSIM trials |
| F12-007 | Yield response to rainfall | Change in yield under different rainfall conditions | ICAR, ICRISAT, DSSAT |
| F12-008 | Yield response to drought | Yield losses under water stress | ICAR, ICRISAT, APSIM |
| F12-009 | Yield response to heat | Yield losses under heat stress | ICAR, DSSAT, crop trials |
| F12-010 | Yield response to salinity | Yield changes at different EC levels | FAO, ICAR, field trials |
| F12-011 | Yield response to flooding | Crop performance under waterlogging | ICAR, field trials |
| F12-012 | Yield response to nutrients | Effect of different nutrient conditions and applications | ICAR, DSSAT, APSIM |
| F12-013 | Cultivar performance | Performance differences between varieties | ICAR, UAS, seed trials |
| F12-014 | Biomass yield | Total plant biomass produced | ICAR, ICRISAT, crop trials |
| F12-015 | Harvest quality | Relevant crop-quality measurements | ICAR, agricultural universities |

### 5.13 Crop stress tolerance and biological risks — Q13

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F13-001 | Drought tolerance | Crop response to water shortage | ICAR, DSSAT, APSIM, trials |
| F13-002 | Heat tolerance | Response to high temperatures | ICAR, DSSAT, APSIM |
| F13-003 | Cold tolerance | Response to low temperatures | ICAR, DSSAT, APSIM |
| F13-004 | Flooding tolerance | Response to inundation and waterlogging | ICAR, GAEZ, crop trials |
| F13-005 | Stage-specific salinity tolerance | Salinity response at different stages | ICAR, FAO, trials |
| F13-006 | Pest susceptibility | Pests affecting each crop and severity | NBAIR, ICAR, CABI |
| F13-007 | Disease susceptibility | Diseases affecting each crop | NBAIM, ICAR, CABI |
| F13-008 | Root disease susceptibility | Root rot, wilt and soil-borne disease risk | NBAIM, ICAR, CABI |
| F13-009 | Fungal diseases | Crop-specific fungal pathogens | ICAR, CABI |
| F13-010 | Bacterial diseases | Crop-specific bacterial pathogens | ICAR, CABI |
| F13-011 | Viral diseases | Crop-specific viruses and vectors | ICAR, CABI |
| F13-012 | Weed competition tolerance | Yield response to weed pressure | ICAR, crop trials |
| F13-013 | Pollinator availability | Presence and abundance of pollinators | ICAR, biodiversity surveys |
| F13-014 | Environmental disease conditions | Temperature, humidity and leaf wetness associated with disease risk | ICAR, weather station, leaf wetness sensors |

### 5.14 Crop rotation and soil interactions — Q14

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F14-001 | Nitrogen fixation capacity | Amount of atmospheric nitrogen fixed | APSIM, DSSAT, ICAR, ICRISAT |
| F14-002 | Nitrogen uptake | Total nitrogen absorbed during growth | APSIM, DSSAT, ICAR |
| F14-003 | Phosphorus uptake | Total phosphorus absorbed | APSIM, DSSAT, ICAR |
| F14-004 | Potassium uptake | Total potassium absorbed | APSIM, DSSAT, ICAR |
| F14-005 | Nutrient depletion | Nutrients removed from the soil | APSIM, DSSAT, long-term trials |
| F14-006 | Nutrient replenishment | Nutrients returned through fixation and residues | APSIM, DSSAT, ICAR |
| F14-007 | Crop residue production | Mass of stems, leaves and other residual material | APSIM, DSSAT, trials |
| F14-008 | Residue composition | Carbon, nitrogen and other relevant residue contents | ICAR, laboratory |
| F14-009 | Residue decomposition rate | Speed of residue breakdown | APSIM, DSSAT, experiments |
| F14-010 | Root residue contribution | Root material left in soil | APSIM, DSSAT, trials |
| F14-011 | Organic matter contribution | Change in soil organic matter | APSIM, long-term experiments |
| F14-012 | Soil structure improvement | Changes to aggregation and compaction | APSIM, ICAR, field trials |
| F14-013 | Soil moisture carryover | Remaining soil moisture after harvesting | APSIM, DSSAT |
| F14-014 | Crop water consumption | Water consumed over entire crop lifecycle | DSSAT, APSIM, satellite ET |
| F14-015 | Allelopathic effects | Chemical interference with following crops | ICAR, research studies |
| F14-016 | Shared pest and disease risks | Common hosts and pathogens in successive crops | ICAR, CABI, NBAIR, NBAIM |
| F14-017 | Crop family compatibility | Botanical family and related crop species | FAO, ICAR, crop taxonomy |
| F14-018 | Rotation interval | Recommended time before repeating the same/related crop | ICAR, UAS, KVK |
| F14-019 | Nutrient carryover | Nutrient effects from the preceding crop | APSIM, DSSAT, long-term trials |

### 5.15 Cultivation and crop management — Q15

| Feature ID | Feature | Required content | Candidate sources to verify |
| --- | --- | --- | --- |
| F15-001 | Actual sowing date | Date crop was planted | Farmer records |
| F15-002 | Recommended sowing window | Recommended planting period | ICAR, UAS, KVK |
| F15-003 | Actual harvesting date | Date crop was harvested | Farmer records |
| F15-004 | Recommended harvesting window | Expected harvest period | ICAR, UAS, KVK |
| F15-005 | Crop cultivar / variety | Exact planted variety | ICAR, seed databases, farmer records |
| F15-006 | Seed germination percentage | Seed viability result | Seed-testing laboratories |
| F15-007 | Seed purity | Physical and varietal purity | Seed-testing laboratories |
| F15-008 | Seed viability | Percentage of viable seeds | Seed-testing laboratories |
| F15-009 | Seed rate | Quantity of seed per area | ICAR, UAS, farmer records |
| F15-010 | Plant population | Plants per square metre/hectare | ICAR, field observations |
| F15-011 | Row spacing | Distance between rows | ICAR, UAS, farmer records |
| F15-012 | Planting depth | Depth at which seed is planted | ICAR, farmer records |
| F15-013 | Irrigation schedule | Timing and frequency | Farmer records, APSIM/DSSAT management inputs |
| F15-014 | Irrigation volume | Actual volume applied | Farmer records, flow meter |
| F15-015 | Fertilizer application | Product, quantity and timing | ICAR, UAS, farmer records |
| F15-016 | Tillage practices | Method, frequency and depth | ICAR, farmer records |
| F15-017 | Weed management | Manual, mechanical and chemical control | ICAR, farmer records |
| F15-018 | Pest management | Treatment and control practices | ICAR, farmer records |
| F15-019 | Pesticide application | Product, dosage and dates | Farmer records |
| F15-020 | Organic amendments | Manure, compost and other organic inputs | Farmer records, ICAR |
| F15-021 | Residue management | Removal, burning, incorporation or retention | Farmer records |
| F15-022 | Harvesting method | Manual or mechanized method | Farmer records |

### 5.16 Required supplementary features and dimensions — Q16

These preserve requirements previously described in prose, source descriptions, implementation tasks and database schemas. They are additional requirements or explicit expansions of existing families, not optional extras.

| Feature ID | Feature | Required content and validation context |
| --- | --- | --- |
| F16-001 | Field identity and geometry | Stable field/project IDs, names, original placemark IDs/folders/metadata, original and revised polygons, holes/MultiPolygons, CRS and repair history |
| F16-002 | Field measurements | Area, perimeter, bounding box, centroid, interior representative point and buffered geometries with distance/purpose |
| F16-003 | Station/well selection | Nearest station, selected station, distance, count within configured radii, elevation difference, available record period and representativeness; station/well/aquifer identity |
| F16-004 | Spatial statistics | Mean, median, minimum, maximum, standard deviation, p10, p90, valid pixel count, valid area percentage and categorical class distribution/probabilities |
| F16-005 | Borewell and irrigation survey | Borewell depth, yield, reliability, failure history, pumping hours, irrigation frequency/method/access and actual reported costs with currency/date |
| F16-006 | Crop suitability source products | Agroecological suitability, potential yield and water-regime suitability from authentic source products, retaining model assumptions and spatial support |
| F16-007 | Crop stage timeline | Developmental stage, days after sowing, accumulated thermal time, published expected stage start/end, actual stage observations/start/end, crop-specific temperature/water-stress response |
| F16-008 | Production and cultivated area | Actual crop production, cultivated/sown/harvested area as separately defined by source, region, crop, season and reference period |
| F16-009 | Biological identities and incidence | Scientific names, organism types, pest/disease-host relations, vectors, actual incidence/severity and affected crops, distinct from susceptibility |
| F16-010 | Rotation relationship context | Preceding/following crop, environment, soil before/after, nutrient/moisture/organic-carbon changes, residue/decomposition, pest/disease carryover, observed following-crop yield effect, study location/duration/reference |
| F16-011 | Trial context | Trial/location IDs, soil conditions, weather period, sowing/harvest dates, irrigation/fertilizer treatments, replicate count, experimental method and source reference |
| F16-012 | Sensor and laboratory context | Device identity/type/location/depth/installation, calibration, sampling method, collection time, sample/seed-lot identity, laboratory/report identity, detection limits and original units |
| F16-013 | Photosynthetically active radiation | Actual PAR observations, photon/energy units, time support and installation context; distinguish from total incoming solar radiation |
| F16-014 | Plant tissue and root measurements | Tissue nutrient concentrations, sampled organ/stage, root depth/biomass and plant dry/fresh biomass; uptake derived only with actual compatible biomass inputs |
| F16-015 | Seedling and seed subfeatures | Moisture/temperature/soil establishment requirements; seed physical purity, varietal purity, viability and germination remain distinct |
| F16-016 | Chemical and physical subfeatures | Separate zinc, iron, copper, manganese, boron; exchangeable sodium and ESP; named soil/water contaminants; residue carbon/nitrogen/other composition; aggregation/compaction changes; particle density where used for porosity |
| F16-017 | Crop parameter bounds and responses | Minimum/optimum/maximum for applicable requirements; stage-specific nutrient components; critical day length/flowering response, daily light integral/intensity; salinity yield curve and physiological/harvest maturity distinctions |
| F16-018 | Temporal and projection subfeatures | Mean/minimum/maximum humidity; mean/maximum wind; seasonal/interannual variation; monsoon dates; green-up/peak/senescence; forest gain/loss; future temperature/precipitation with scenario/member/horizon |
| F16-019 | Provenance, quality and availability | Every metadata field in Sections 3–4, including source assets, value types, original units, observation/retrieval times, coverage, uncertainty, evidence classification, missing reason and processing versions |
| F16-020 | Management event components | Product, quantity, dose, concentration, application dates, area basis; tillage method/frequency/depth; seed rates/counts/spacing/planting depth; actual versus recommended sowing/harvest windows |

For general categories such as “contaminants”, “harvest quality” or “micronutrient requirements”, enumerate all analytes/metrics named here and every relevant metric present in the selected authentic source reports. Register the family in S01, freeze its atomic enumeration before implementing its domain, and version later additions. Never invent analyte identities or claim unspecified metrics were collected. Curves and time series must preserve all supported points and axes.

### 5.17 Frontend-required market and economic features — Q17

These were missing from the original scientific inventory despite appearing in the frontend and API scope. They belong to S10 and require the same lineage, FEAT and source-access evidence as other data. Authentication, CRUD and wire-contract correctness additionally use API cases, not invented agricultural observations.

| Feature ID | Feature | Required content and validation context |
| --- | --- | --- |
| F17-001 | Markets and commodities | Authentic market identity/location, commodity/grade/variety identifiers, explicit crop/cultivar mappings and provider codes |
| F17-002 | Observed market prices | Minimum/modal/maximum prices where published; currency, quantity unit, commodity/grade, market, observation/publication dates and freshness |
| F17-003 | Market arrivals | Actual arrival quantity, unit, reporting market/commodity and period |
| F17-004 | Support prices | Published policy price, scheme type, commodity/grade, effective dates and marketing season; MSP distinct from other policy schemes and market observations |
| F17-005 | Price trends | Defined comparison period, compatible actual price records, calculation and direction; missing history is not a stable trend |
| F17-006 | Cultivation costs and deductions | Actual itemized crop/field costs; cess, bagging, weighing, transport rate/distance where applicable; amount, currency, date, percentage base and quantity/area basis |
| F17-007 | Farm-gate realization | Source market observation minus documented applicable deductions with field/route context; no invented transport distance or flat fee |
| F17-008 | Conditional financial scenarios | Versioned authentic yield/price/cost/area inputs, explicit user assumptions, gross/net totals and per-area values, benefit-cost ratio and uncertainty; each expected/pessimistic/optimistic scenario independently available or blocked |

## 6. Required source connections and source-specific test inputs

Each SRC row is a required integration category. Inventory it in S01 and resolve its concrete products/access routes before implementing its owning domain task; initial soil/climate connection proofs belong to S04. Retain category-to-product mappings and explicit unresolved-binding blockers. Existing source alternatives may supply a feature, but cannot mark an untested required connection complete. Where an institution supplies reports rather than an API, test the authentic import route. Without an accessible authentic artifact, that integration remains blocked.

A category may contain multiple products, endpoints or collections. Apply CONN-01 through CONN-08 to each applicable route/product and FEAT tests to every bound variable. Store a result for each instance. The access descriptions below are planned routes to verify during implementation, not current endpoint guarantees.

| Source ID | Source | Required data | Planned access route | Access constraint to verify |
| --- | --- | --- | --- | --- |
| SRC-001 | SoilGrids | Soil properties | REST API, GeoTIFF | API access; verify service limits |
| SRC-002 | Soil Health Card | Laboratory soil chemistry | Report import, authorized data access | Public bulk API not assumed |
| SRC-003 | NBSS&LUP | Soil maps and classification | GIS data / institutional request | Dataset access |
| SRC-004 | NASA POWER | Daily and monthly climate | REST API | Generally public access |
| SRC-005 | KSNDMC | Karnataka station rainfall and weather | Portal / data request | Verify station-data availability |
| SRC-006 | IMD | Weather, rainfall and climate | Downloads / station data | Access conditions vary |
| SRC-007 | CHIRPS | Historical rainfall | Raster downloads / Earth Engine | Dataset access |
| SRC-008 | GPM IMERG | Satellite precipitation | NASA Earthdata / Earth Engine | Product and account conditions |
| SRC-009 | ERA5-Land | Weather and soil moisture | Copernicus Climate Data Store API / Earth Engine | CDS account and API configuration |
| SRC-010 | TerraClimate | Monthly climate and water balance | Raster downloads / Earth Engine | Dataset access |
| SRC-011 | WorldClim | Climate averages and projections | Downloadable rasters | Dataset access |
| SRC-012 | CMIP6 | Future climate simulations | ESGF / climate datasets | Large downloads |
| SRC-013 | Copernicus DEM | Elevation | Raster downloads / Copernicus services | Product-specific access |
| SRC-014 | SRTM | Elevation | NASA Earthdata / Earth Engine | Dataset access |
| SRC-015 | ALOS | Elevation | JAXA data services / available raster datasets | Product-specific access |
| SRC-016 | HydroSHEDS | Drainage and watersheds | GIS downloads / Earth Engine where available | Dataset access |
| SRC-017 | GSI | Geology and lithology | GIS maps / data requests | Dataset access |
| SRC-018 | Bhuvan | Indian land and thematic maps | Geoportal / available services | Service-specific access |
| SRC-019 | CGWB | Groundwater and aquifer information | Portal / datasets / official request | Do not assume a complete public API |
| SRC-020 | India-WRIS | Water resources and infrastructure | Portal / GIS products | Verify downloadable services |
| SRC-021 | NASA SMAP | Surface and root-zone soil moisture | NASA Earthdata / Earth Engine | Product-specific access |
| SRC-022 | JRC Global Surface Water | Historical surface water | Earth Engine / downloadable raster | Dataset access |
| SRC-023 | Sentinel-1 | Radar, flooding and land observations | Copernicus Data Space / Earth Engine | Account or API access depending on route |
| SRC-024 | Sentinel-2 | Vegetation, crop and land observations | Copernicus Data Space / Earth Engine | Account or API access depending on route |
| SRC-025 | Landsat | Long-term vegetation and land changes | USGS/NASA / Earth Engine | Product-specific access |
| SRC-026 | MODIS | LAI, fAPAR, GPP, NPP, vegetation and ET products | NASA LP DAAC / Earth Engine | Product-specific access |
| SRC-027 | ESA WorldCover | Land-cover classification | Downloadable rasters | Dataset access |
| SRC-028 | Dynamic World | Land-cover classification | Google Earth Engine | Earth Engine access |
| SRC-029 | Global Forest Watch | Tree cover and forest loss | Data downloads / API where available | Product-specific terms |
| SRC-030 | NASA FIRMS | Fires and thermal anomalies | API / downloads | API key for certain interfaces |
| SRC-031 | Sentinel-5P | Atmospheric pollutants | Copernicus / Earth Engine | Product-specific access |
| SRC-032 | CPCB | Indian air and water quality | Portal / available APIs | Verify API and licensing |
| SRC-033 | OpenAQ | Air quality station observations | REST API | API terms and coverage |
| SRC-034 | FAO EcoCrop | Crop requirements | Database / portal | Investigate bulk export |
| SRC-035 | FAO GAEZ | Crop suitability and yield potential | GIS downloads | Dataset access |
| SRC-036 | DSSAT | Crop development and response | Model software / parameter files | Installation and model licensing |
| SRC-037 | APSIM | Crop growth and rotation processes | Model software / parameter files | Installation and licensing |
| SRC-038 | FAOSTAT | Historical production and yields | REST API / downloads | Check dataset coverage |
| SRC-039 | ICAR | Indian agronomy and crop trials | Research publications / data request | Institutional sources |
| SRC-040 | ICRISAT | Dryland crop research and trials | Research datasets / publications | Dataset-specific terms |
| SRC-041 | UAS Bengaluru | Regional crops and trials | Publications / institutional requests | Institutional access |
| SRC-042 | UAS Dharwad | Regional crops and trials | Publications / institutional requests | Institutional access |
| SRC-043 | KVKs | Regional cultivation recommendations | Publications / farmer interaction | Manual / institutional |
| SRC-044 | NBAIR | Pest and insect information | Portal / publications / institutional data | Verify data access |
| SRC-045 | NBAIM | Agricultural microorganisms and diseases | Portal / research / institutional data | Verify data access |
| SRC-046 | CABI | Pests, diseases and crop biology | Database / publications | Some content may require licensing |
| SRC-047 | Seed testing agencies | Germination, seed purity and viability | Laboratory reports | Manual / laboratory |
| SRC-048 | Soil and water laboratories | Soil and irrigation water chemistry | Test reports | Manual / laboratory |
| SRC-049 | Farmer questionnaires | Management and historical field information | Form / structured imports | Direct collection |
| SRC-050 | Field sensors | Soil, atmospheric and crop observations | Sensor exports / MQTT / CSV | Hardware-specific |
| SRC-051 | ISRO / NRSC / UNCCD | Degradation, desertification and historical flood products | Actual GIS datasets/reports | Product origin, licence and spatial coverage |
| SRC-052 | State agriculture departments | Production, cultivated area, yield and irrigation statistics | Official downloads/reports | Region/year definitions and access |
| SRC-053 | State groundwater departments | Local wells, groundwater and borewell context | Official datasets/reports | Well identity, datum and record availability |
| SRC-054 | Water authorities / irrigation departments | Reservoir level/storage, river discharge, canals and irrigation schemes | Station feeds, GIS datasets or official reports | Actual station/network access and units |
| SRC-055 | Lightning monitoring networks | Lightning events and frequency | Actual network export/feed | Provider access, event detection coverage |
| SRC-056 | Disaster/event authorities | Historical cyclone, hail, flood and other hazard records | Official event datasets/reports | Event identifiers, date/location evidence |
| SRC-057 | Köppen-Geiger classification products | Climate class | Authentic published classification raster | Version, class legend and reference period |
| SRC-058 | FAO calendars, taxonomy and agronomic references | Crop calendars, botanical families and method definitions | Actual reference datasets/publications | Exact edition, table/record and provenance |
| SRC-059 | Plant tissue / root / biomass laboratories and field trials | Tissue nutrients, root growth and biomass | Authentic reports and field-sampling records | Sample identity, mass basis and empirical origin |
| SRC-060 | Official agricultural market reporting | Market/commodity identities, daily min/modal/max prices and arrivals | Select a verified AGMARKNET, official open-data or eNAM product/import route | Do not treat frontend source labels as proof of access; record product, keys/licence, date/grade/unit coverage |
| SRC-061 | Official agricultural price-policy publications | MSP or other applicable support-price schedules | Authentic government notification/report import | Exact policy scheme, commodity/grade, season, effective date, page/table and quantity basis |
| SRC-062 | Authentic cost and fee records | Cultivation costs, market fees, bagging/weighing, freight rates and actual route distance | Farmer receipts/submissions, published cost studies, official tariffs or authorized transport records | Version/date, geography, crop/field support, currency and per-hour/per-area/per-quantity basis |
| SRC-063 | Operational weather forecast provider | Forecast temperature, wind, precipitation and condition | Actual authorized IMD/other provider feed or authentic forecast publication import selected in S01 | Verify issue/valid time, horizon, model, spatial support, licence/access; do not assume a public feed exists |

### 6.1 Minimum authentic payloads for source tests

These assertions supplement the parameterized connection cases; each named source/product must have its own result.

| Source group | Required positive test payload and semantic checks |
| --- | --- |
| SoilGrids | Actual supported soil property/depth response or raster; verify sand/silt/clay, pH, organic carbon, total N, density, CEC and coarse-fragment mappings, source scaling and available depth intervals. It cannot supply invented EC or available P/K. |
| Soil Health Card, NBSS&LUP, soil/water/seed laboratories | Actual identified sample/report or map; verify every analyte/property, sampling depth/date, method, classification legend, reported units and sample-to-field link. |
| NASA POWER | Actual bounded daily response; validate requested precipitation, mean/min/max temperature, humidity, wind and solar-radiation parameter codes against provider metadata; exact requested dates and missing codes. |
| KSNDMC and IMD | Actual station series and/or gridded observations; verify station identity/grid, observation time, rainfall/temperature units, geographical relevance and historical period. Each product route is separately tested. |
| CHIRPS and GPM IMERG | Actual precipitation pixels/intervals; verify product/version, rates versus accumulations, units, temporal interval and regional coverage. |
| ERA5-Land and TerraClimate | Actual selected variables/layers; verify units, accumulated flux conventions, time axis, soil-layer depths and missing masks. |
| WorldClim, CMIP6, Köppen-Geiger | Actual climatology/projection/classification assets; verify baseline, scenario/model/member/horizon or classification legend. Future projections remain distinct from observations. |
| Copernicus DEM, SRTM, ALOS | Actual elevation tile intersecting acceptance field; verify vertical datum/unit, CRS, nodata and native cell size; independently inspect cells and terrain derivatives. |
| HydroSHEDS, GSI, Bhuvan | Actual drainage/watershed/geology/geomorphology features or rasters; verify source legend, topology/intersections, projection and support. |
| CGWB and state groundwater departments | Actual wells/aquifer/assessment records; verify coordinates, observation dates, depth datum, aquifer attributes and regional-versus-point support. |
| India-WRIS, water/irrigation authorities | Actual reservoir, canal, river, command-area and streamflow records; verify asset/site identity, level versus storage versus discharge and time/geometry. |
| SMAP | Actual selected surface and root-zone products; verify product type, layer/depth support, quality flags, units and coarse grid support. |
| Sentinel-1 | Actual radar acquisition intersecting field/context; verify orbit/date, polarization, calibration/backscatter units and masks before flood/waterlogging analysis. |
| Sentinel-2 and Landsat | Actual intersecting scenes with required bands and quality layers; verify reflectance scaling/offsets, acquisition dates, cloud masks, coverage and independently calculated indices. |
| MODIS | Actual separate LAI/fAPAR/GPP/NPP/ET/vegetation products as required; verify each product's scale, unit, period and QA flags. One product cannot prove all others. |
| ESA WorldCover and Dynamic World | Actual class/probability pixels; verify class legend, source dates, probability sums where supplied and field class-area reconciliation. |
| JRC Global Surface Water and Global Forest Watch | Actual water occurrence/history or tree-cover/change pixels; verify reference period, annual/event encoding, masks and area calculations. |
| FIRMS | Actual fire detection records or authentic archived records from a known event; verify detection time/location/confidence. An empty query alone does not prove the feature works. |
| Sentinel-5P, CPCB and OpenAQ | Actual requested pollutant products/measurements with flags and units; distinguish satellite atmospheric columns from station concentrations and standards-based AQI. |
| EcoCrop and GAEZ | Actual crop requirement/suitability records or grids; verify species, variable bounds, environmental assumptions, units and geographical support. |
| DSSAT and APSIM | Actual versioned crop parameter files and cited empirical trial records; independently verify parameter semantics, cultivar and model version. No locally generated simulation can replace trial observations. |
| FAOSTAT and state agriculture statistics | Actual crop production/area/yield records; verify item/element/geography/year/unit codes and reconcile compatible yield calculations. |
| ICAR, ICRISAT, UAS Bengaluru, UAS Dharwad and KVKs | Actual publications/trial datasets/recommendations; verify page/table/record, crop/cultivar, stage, experimental treatment and observed-versus-recommended classification. |
| NBAIR, NBAIM and CABI | Actual organism/host/pathogen records; verify scientific identities, relationship, geographical context and evidence/reference. |
| Farmer questionnaires | Actual dated submission associated with a real field/crop/season; verify event quantities/dates against the original submission without inventing answers. |
| Field sensors and plant/root/biomass testing | Authentic device export/live stream or sampling report per Section 7; verify deployment, sample, calibration, time, depth and quantities. |
| ISRO/NRSC/UNCCD, lightning networks and disaster authorities | Actual thematic products or event records; verify region, event identity/date, detection coverage, taxonomy and observed-versus-risk classification. |
| FAO calendar/taxonomy/method references | Actual source document/dataset; verify crop identity, season/calendar, family and cited method/edition/record. |
| Market, price-policy and cost sources | Actual dated market/commodity/grade records, policy notification and applicable cost/fee evidence; independently reconcile units, price bounds, deductions and compatible scenario inputs. Each selected route has its own CONN results. |
| Operational forecast source | Actual provider-issued forecast with issue and valid intervals, supported variables/units and location; prove a fresh request for claimed live service and preserve distinct forecast revisions. Historical weather or an old screenshot cannot prove a live forecast feed. |

Provider transport layers such as Google Earth Engine, NASA Earthdata, Copernicus Data Space/CDS, USGS, JAXA and ESGF must also have authenticated real-download/read tests wherever used. An SDK import or successful authentication alone cannot replace collection/product tests.

## 7. Required field instruments and acquisition tests

All 14 categories require authentic data ingestion, metadata, scientific validation, database persistence and export. Do not require a device in every field; actual deployment or genuine recorded measurements can establish support for a category. A device not available for testing remains blocked. Do not describe historical file ingestion as verified live device operation.

All rows require DEVICE-01 through DEVICE-06 and the FEAT cases for every emitted variable.

| Instrument ID | Sensor / instrument / test | Required data | Additional scientific test |
| --- | --- | --- | --- |
| INST-01 | Soil moisture probe | Volumetric water content at different depths | Verify volumetric fraction versus percent, calibration and installed depth; compare with actual reference measurements where available. |
| INST-02 | Soil temperature probe | Soil temperature at different depths | Verify °C conversion, depth, timestamps and actual thermometer/logger reference. |
| INST-03 | Automatic weather station | Temperature, humidity, wind, rainfall and solar radiation | Individually verify temperature, humidity, wind, rain and radiation channels, measurement heights and accumulation intervals. |
| INST-04 | Rain gauge | Local rainfall | Verify bucket/volume calibration, rainfall interval and cumulative reset behavior from actual records. |
| INST-05 | Soil pH meter / laboratory | Soil acidity | Verify pH method, calibration record, sample identity and temperature/context where supplied. |
| INST-06 | Soil EC meter / laboratory | Salinity | Verify EC unit, extraction method and temperature compensation; do not equate soil EC with irrigation-water EC. |
| INST-07 | NPK testing equipment / laboratory | Soil nutrients | Verify separately N, P and K, total/available/extractable method and elemental/oxide basis against the real report. |
| INST-08 | Plant tissue testing | Actual nutrient uptake | Verify sampled organ, nutrient concentration and dry/fresh basis; uptake additionally requires compatible actual biomass. |
| INST-09 | PAR sensor | Photosynthetically active radiation | Verify photon/energy unit, sensor placement and interval; daily light integral requires sufficient real temporal coverage. |
| INST-10 | LAI meter | Leaf area index | Verify LAI definition, instrument method and canopy/sample conditions. |
| INST-11 | Irrigation flow meter | Water volume applied | Verify cumulative volume versus flow rate, interval integration, meter calibration and reset handling. |
| INST-12 | Leaf wetness sensor | Duration of leaf wetness | Verify wetness threshold, sampling cadence and duration calculation; missing intervals are not dry intervals. |
| INST-13 | Root sampling tools | Root depth and biomass | Verify actual root depth, sampled volume/area, root mass and dry/fresh basis. |
| INST-14 | Plant biomass sampling equipment | Biomass accumulation | Verify actual sampled area, tare/mass, dry/fresh basis and kg/ha conversion. |

Ancillary acquisition mentioned in the inventory also requires actual evidence: infiltration field tests, lightning-network event data, air-quality stations, water chemistry reports and seed-testing reports. Register concrete devices/report sources under the relevant SRC row and apply DEVICE/CONN/FEAT cases as appropriate; unspecified hardware models must not be invented.

## 8. Mandatory test cases and acceptance evidence

These are specifications for tests to implement, not claims that they already exist or pass. Execute them against real services, real source artifacts and the real PostgreSQL/PostGIS acceptance database. Store results per parameterized instance; a single green result for a generic test function is insufficient.

### 8.1 Test evidence and coverage enforcement

Every result must contain `test_case_id`, `run_id`, step, feature/variable/source/product/device IDs, actual request/import description, actual input asset checksum, independently established expectation, comparison method/tolerance, actual result, pass/fail/blocked status, timestamps, code/configuration versions and evidence paths. Redact secrets only; keep reproducible query parameters and scientific content.

Before running tests, generate the expected case set from the full registries. Compare expected versus collected versus executed cases. Zero collected cases, a disabled domain, skip/xfail, missing credentials or a missing reference artifact cannot count as a pass. A rule irrelevant to one variable is recorded with a reviewed applicability reason; the feature's applicable positive tests remain mandatory. Required missing data are blockers; `not_applicable` must not conceal implementation gaps.

Use three kinds of authentic evidence:

- **Fresh acquisition evidence:** a real request/download/read from the actual service/device on the acceptance run; preserves response/status and product identity.
- **Replay evidence:** an immutable, previously acquired real response/report with verified provenance, used for repeatable parsing and regression checks. Replay cannot prove present connectivity.
- **Independent expected-value evidence:** source documentation plus separately inspected source rows/bands or a separate calculation from the raw data. Never call the production parser/transform to manufacture its own expected answer.

Do not create synthetic records even for tests. Negative data cases use authentic files containing real missing/invalid/quality-flagged records where available. Negative connection/configuration cases may use an unavailable local port, missing credential setting, invalid request parameter or a revoked test credential to provoke an actual refusal/error; they do not fabricate scientific data or mock a service. If an authentic negative-data case is unavailable, report that case blocked rather than generate one.

### 8.2 Database connection and persistence cases

Run every case against the actual configured PostgreSQL/PostGIS acceptance instance.

| Test ID | Action | Required assertion |
| --- | --- | --- |
| DB-01 Identity and connection | Open the configured connection and execute `SELECT current_database(), current_user, version()` and `SELECT PostGIS_Full_Version()`. | Correct expected database/user, PostgreSQL server and PostGIS extension; retain redacted host/port/database fingerprint. No alternate database fallback. |
| DB-02 Migrations and privileges | Apply migrations in an acceptance-owned schema; inspect expected tables, foreign keys, typed columns and spatial indexes. | Actual schema matches the contract and application role can perform required operations. Missing migration/permission is a failure. |
| DB-03 Commit/readback | Insert an actual field and normalized real observation, commit, close the connection, read through a newly opened independent connection/process. | IDs, values, units, timestamps, depth, source references and geometry match expectations and survive connection closure. A mocked session cannot satisfy this case. |
| DB-04 Spatial behavior | Store real KML geometries; query `ST_IsValid`, `ST_SRID`, `ST_Intersects` and projected `ST_Area`; compare with independent geospatial calculations. | Valid geometry, correct CRS and intersections, area/perimeter within declared numerical tolerances. |
| DB-05 Relational integrity | Attempt invalid foreign-key linkage using existing authentic observations in a rollback-only test transaction; test required constraints. | Database rejects orphan references and invalid schema relationships. No orphaned record is committed. |
| DB-06 Failure/rollback | Start a transaction using real records; cause an actual constraint violation; rollback and reconnect. | No partial accepted data or false completed job remains. Error is recorded outside the rolled-back operation. |
| DB-07 Idempotency and versioning | Re-import the same authentic asset twice, then import an available distinct real observation/product version. | No duplicate for identical context; genuinely different time/depth/source/version retained. Raw checksum unchanged. |
| DB-08 Connection failure | Connect to an unavailable acceptance endpoint or use a missing/invalid test credential setting. | Explicit failed/blocked result, nonzero command status, no SQLite fallback, no fabricated success. |
| DB-09 Export reconciliation | Query accepted records directly in SQL and compare with all export partitions after independent readback. | Exact IDs/counts and categorical metadata; numeric/time values within predefined serialization tolerance; quarantined records excluded. |

### 8.3 Every source connection: parameterized CONN cases

Instantiate applicable cases for **every Section 6 source, every product binding, and every configured endpoint/import transport**. A shared Earth Engine session does not prove access to each collection. A source alternative does not validate the original connection.

| Test ID | Action | Required assertion |
| --- | --- | --- |
| CONN-01 Access and identity | Authenticate where required; execute a small actual data request or open an actual provider-issued asset/report. | Provider/product/version and requested resource verified; actual data body is readable. A login page, metadata-only response, HTML error or catalogue listing is not data. For imports, origin and checksum verified. |
| CONN-02 Requested coverage | Request real known-covered coordinates/date/depth/variable or locate the required published record. | Response covers the requested context and contains the specified parameter/band/analyte with metadata. Record any product limitations. |
| CONN-03 Payload and schema | Parse returned bytes using actual content type/schema; inspect required fields, CRS/dimensions, unit metadata and quality flags. | Correct schema and usable payload; no fallback if schema changes. |
| CONN-04 Completeness | Retrieve a bounded real multi-page/time/tile interval, following pagination and all requested assets. | All advertised pages/tiles/dates acquired; response counts reconcile; no hidden truncation. Single-page products document that fact. |
| CONN-05 Failure behavior | Provoke a real refused connection, authorization failure or invalid-variable request, appropriate to the transport. For imports, reference a missing file in the import manifest. | Explicit actionable failure; no synthetic data, accepted observations or success status. Authentic existing assets remain unchanged. |
| CONN-06 Freshness and caching | Execute one fresh request, then replay its verified cached response; vary a real query dimension where supported. | Fresh run contacts provider; replay has original lineage; changed variables/dates/depths cannot return an unrelated cached result. |
| CONN-07 Normalization and database | Normalize the authentic sample, run FEAT cases, commit it, and read through an independent database session. | Correct scientific values and source linkage persist; rejected data never enter accepted views. |
| CONN-08 Repeatable evidence | Re-run the same bounded query/import and compare version/checksum/context. | Stable products reproduce within specified precision; changed provider data create a new version with explanation, not silent overwrite. |

For file/portal/institutional sources, an authentic acquired report/dataset plus tested importer is the connection route; do not invent a public API. Record how and when the original file was obtained and its publisher/sample identifiers. If live automated access is claimed, it additionally requires a live endpoint test. For model-parameter sources, test the actual versioned parameter file and its published context; installing APSIM/DSSAT is not a data connection test.

### 8.4 Every atomic feature: parameterized FEAT cases

Instantiate these for every required `variable_id × source_binding_id × required acceptance context`. A family with five named analytes requires five independent bindings/results. Curves, scenarios, categories and stages require coverage of their declared dimensions.

| Test ID | Action | Required assertion |
| --- | --- | --- |
| FEAT-01 Meaning and source mapping | Compare source metadata and a manually inspected real record to the registered scientific definition. | Correct parameter/analyte, observed versus required quantity, unit, basis, spatial/time/depth/stage context. Total N cannot pass available-N coverage; regional yield cannot pass field yield. |
| FEAT-02 Raw-to-normalized value | Independently read the original field/band/report cell and calculate the specified conversion. | Normalized value agrees within predeclared numerical tolerance; original value/unit retained; no double scaling or guessed units. |
| FEAT-03 Type and physical plausibility | Check all actual returned records against registered types/categories, physical bounds, detection limits and domain Q rules. | Every accepted record satisfies rules. Invalid real records are quarantined with reason; unknown variable or absent required rule fails validation. |
| FEAT-04 Coverage and completeness | Compare requested versus actual variables, dates, intervals, depths, stages, samples, spatial masks and scenarios. | Exact expected dimensions or explicit gap states; acceptance corpus meets predeclared minimum coverage and positive-evidence requirements. Nonempty output alone fails this criterion. |
| FEAT-05 Derived relationships | Independently recompute an aggregate/index/curve from the raw authentic parents and verify formula/domain relationships. | Correct values, chronology, denominators and input lineage. Missing inputs prevent derivation. Imported values instead require independent source-record transcription/replay. |
| FEAT-06 Provenance | Traverse the value to raw asset, record locator, source version, field/region and processing run. | Source bytes resolve and hash correctly; no generated baseline or untraceable constants; original time/depth retained. |
| FEAT-07 Real storage | Commit accepted feature records and read from a separate PostgreSQL session. | Value, category/text/series, unit, dimensions, quality and lineage survive exactly or within declared precision. |
| FEAT-08 Full output | Independently load JSONL/Parquet/domain export and compare with database plus feature-status ledger. | Every record and required missing feature is represented; schemas/counts/checksums agree; no preview truncation. |
| FEAT-09 Missing/invalid handling | Exercise authentic missing/sentinel/quality-flagged records or documented genuinely uncovered requests. | No zero replacement, interpolation, baseline or accepted invalid value. Honest missing reason and failure/blocker where coverage is required. |

Comparisons must define `abs(actual - expected) <= absolute_tolerance + relative_tolerance * abs(expected)` for numerical checks, where applicable. Fix tolerances from source precision, algorithm error and scientific purpose before execution; record references. Do not expand tolerances after observing a failure. Schema/ID/category/count checks use exact equality unless the contract explicitly specifies otherwise.

### 8.5 Scientific validation profiles for all domains

These are required checks in addition to FEAT cases. Expand them into separate test instances for all applicable variables. Limits must be product/method-specific; do not apply a generic range to unrelated quantities.

| Profile | Mandatory data assertions |
| --- | --- |
| Q01 Soil | Verify every requested property and actual depth interval; source scale/unit metadata; texture fractions sum to approximately 100% within justified precision; pH/EC/CEC/density/analytes use documented method and units. Total and available nutrients stay distinct. Hydraulic capacity, wilting point and porosity obey applicable physical ordering; available water capacity independently equals the stated depth/basis calculation. Porosity/organic-matter estimates require actual inputs and sourced conversion assumptions. Contaminants retain analyte, detection limit and sample method. |
| Q02 Terrain/geology | Verify DEM coverage, nodata, vertical datum and native CRS/resolution; calculate slope/aspect/curvature using metric spacing and independent samples. Handle flat-area aspect and flow/wetness zero denominators explicitly. Cross-check watershed/river intersections, geological map categories and landform membership against actual vector/raster source data. |
| Q03 Rainfall | Verify mm versus rate/accumulation units, period boundaries, time zone and nonnegative physical precipitation. Independently sum complete daily/monthly/seasonal/annual series; count rainy days/dry spells using documented thresholds without treating missing days as dry. Verify onset/withdrawal criteria and anomaly/trend baseline. SPI/SPEI require the documented historical record length, scale, reference period, distribution fitting and real ET inputs; insufficient history blocks the indicator. |
| Q04 Climate | Verify temperature units and Tmin ≤ Tmean ≤ Tmax for equivalent intervals, humidity 0–100%, wind direction convention, nonnegative speed, pressure/radiation units and instantaneous versus accumulated energy. Compute diurnal range, VPD and degree days independently with actual crop base temperatures. ET0 requires the documented method and all necessary real inputs, including measurement heights. Climate classes need source taxonomy. Projections retain model/member/scenario/horizon/baseline and cannot appear as observed weather. |
| Q05 Water | Verify well/aquifer/site identifiers, measurement dates and water-level datum/sign. Keep regional recharge/extraction assessments separate from field readings. Validate water chemistry units/analytes and independently compute SAR from correct ionic units when available. Preserve surface versus root-zone moisture depths and product masks. Verify ET accumulation intervals, flow versus volume, reservoir level/storage distinctions, mapped water extents and flood-event chronology. Irrigation demand must use real weather/crop/soil inputs and a cited method. |
| Q06 Land/vegetation | Verify actual scene/product IDs, dates, bands, scaling/offsets and cloud/shadow/quality masks. Independently calculate NDVI/NDMI/SAVI/EVI from real valid pixels with documented formula and zero-denominator handling. Do not assume every index has NDVI's bounds. Verify categorical class codes/probabilities and area totals, valid pixels/area, LAI/fAPAR/GPP/NPP units/time support and product flags. Crop identity requires labelled survey/record or an explicitly evaluated classification with uncertainty; NDVI alone is insufficient. Phenology/trends require real temporal coverage. |
| Q07 Hazards | Verify event date/location/type and spatial overlap; event frequency uses a declared observation interval and denominator. Separate observed event extent from susceptibility/risk maps. Erosion rates retain mass/area/time and model/input provenance; do not present an index as measured soil loss. Drought classification links to validated indices/reference periods. |
| Q08 Environmental quality | Verify pollutant identity, station/grid location, averaging period, QA flag and unit. Satellite column density is distinct from near-surface concentration. PM2.5 and PM10 remain distinct; AQI retains standard/version, pollutant inputs and averaging rules. Source-invalid retrievals cannot pass because the numeric value appears plausible. |
| Q09 Crop requirements | Verify scientific crop identity, cultivar and stage; minimum ≤ optimum ≤ maximum only for comparable conditions/units. Preserve bounds absent from the source as absent. Nutrient demands retain elemental versus oxide basis, stage and area/mass support. Photoperiod/day-length/light units and salinity response curves retain the cited study context; published recommendations are labelled accordingly. Suitability and potential yield remain source estimates. |
| Q10 Germination | Verify seed lot/crop/cultivar, laboratory/field conditions, dates, temperature, moisture and sample counts. Recalculate germinated/emerged/surviving fractions from actual counts where available; percentages use the correct denominator. Germination, emergence and establishment remain distinct events; time units and early root/nutrient measurements preserve stage. |
| Q11 Growth | Validate actual stage chronology, elapsed days and thermal time; LAI and biomass curves contain real observations or authentic published parameter points. Check root depth, leaf development, flowering/pollination/formation/grain-fill/maturity context. Independently compute harvest index from compatible harvested and total biomass; water/nutrient-use efficiency requires matching real numerator/denominator and period. No generated growth curve qualifies. |
| Q12 Performance | Verify geography, crop/cultivar, season, treatment, replication and harvest basis. Reconcile production/area/yield where the source definitions permit; distinguish sown from harvested area. Stress-response curves require actual matched treatment/control evidence with uncertainty. Regional statistics cannot be assigned as measured field performance. Failure/survival frequencies use documented counts and denominators. |
| Q13 Biology | Verify organism identity/scientific name, host, disease/vector relation and source reference. Keep susceptibility separate from actual field incidence/severity. Weed pressure and pollinator abundance require observation method/count basis. Disease-condition thresholds require cited crop/pathogen context and validated temperature/humidity/leaf-wetness inputs. |
| Q14 Rotation | Verify direction of preceding → following crop, actual study location/duration, soil before/after and management/treatment context. Independently calculate nutrient/carbon/moisture changes and yield effects from real matched records, with units/depth and uncertainty. Fixation is distinct from uptake; nutrient carryover is distinct from applied fertilizer. Residue production/composition/decomposition and root contributions retain measured mass/time basis. Compatibility/interval/allelopathy claims require cited evidence, never invented scores. |
| Q15 Management | Verify actual field/crop/season, event date and actual versus recommended timing. Fertilizer/pesticide product, quantity, concentration, area basis and dates remain explicit. Seed purity/viability/germination retain test method. Reconcile plant counts/spacing where comparable and flowmeter volume with application records. Farmer-reported costs/reliability remain surveyed with source/date/currency or category. |
| Q16 Supplementary context | Apply the relevant domain profile plus exact record/foreign-key checks to every supplementary variable. Validate station selection distances, field metrics, sample/deployment IDs, actual stage dates, trial context, source locators and all required metadata. Unknown context must remain unknown, not be populated with a default crop/date/depth. |
| Q17 Markets/economics | Verify commodity/grade/market identity, price versus support-policy meaning, currency/quantity basis, actual observation/effective period and published units. Compare min/modal/max only for compatible records. Independently recalculate trends, itemized costs, deductions, gross/net and benefit-cost ratios from authentic compatible inputs. A zero-cost denominator makes BCR unavailable, not zero. Preserve missing scenarios and scenario assumptions; do not present expected profit as measured performance or a guarantee. |

Q04 additionally covers F04-024: independently verify forecast issue and valid times, native support, weather variables and units, provider revisions and freshness policy. Separate predictions from observations; do not validate future accuracy merely because the forecast feed responds.

### 8.6 Geographical and cross-source cases

| Test ID | Action | Required assertion |
| --- | --- | --- |
| GEO-01 Real KML identity | Parse actual input boundaries and inspect with an independent GIS reader or source map. | All actual fields/folders/holes/components preserved; stable IDs do not depend only on row order. |
| GEO-02 Repair audit | Process an authentic invalid geometry if available; compare original and repaired footprint. | Repair is documented, valid and within declared area/shape tolerance; unrepairable geometry is rejected. Preserve original bytes. |
| GEO-03 Projection and dimensions | Independently calculate area/perimeter/bounds/centroids from actual fields. | Correct longitude/latitude order, CRS, units and projected distances; representative point lies inside its field. |
| GEO-04 Raster intersection | Extract actual raster cells intersecting a real plot, including boundary cells, and compare with a separate calculation. | Correct overlap weights, nodata/QA masks, count, valid area and statistics; no claim of polygon extraction from a point service. |
| GEO-05 Coarse resolution | Use a real field smaller than a source cell. | Native resolution and support retained in database/export; no invented field-scale detail. |
| GEO-06 Stations and buffers | Match actual stations/wells using configured distance/elevation/aquifer rules. | Independently checked distance and suitability; buffered observations distinct from field observations. |
| GEO-07 Spatial roundtrip | Compare KML-derived geometry, PostGIS geometry and exported geometry. | IDs, holes, coordinates and area remain consistent within declared geometry tolerance. |
| CROSS-01 Rainfall | Compare overlapping real station observations and at least one gridded product; extend to configured KSNDMC/IMD/CHIRPS/GPM/POWER bindings. | Align actual dates, accumulation periods and support; report bias/error/sample count against predeclared purpose-specific limits. |
| CROSS-02 Soil | Compare real soil laboratory results with mapped estimates at compatible depths and properties. | Retain differences, sample dates/methods and uncertainty; never force equality or compare available nutrients to total nutrients. |
| CROSS-03 Vegetation | Compare real Sentinel-2/Landsat overlapping periods and actual crop-history evidence where available. | Align masks, dates, band/product differences and support; report justified consistency metrics and unresolved discrepancies. |
| CROSS-04 Moisture/water | Compare real probes with compatible SMAP/ERA5-Land support and actual well records with groundwater context. | Depth, time, location and scale differences explicit; discrepancies retained and assessed. |
| CROSS-05 Crop/rotation | Compare imported parameters/claims with independent real trials or published empirical records in compatible conditions. | Reference and experimental outcomes distinguish suitability assumptions from demonstrated performance; unsupported claims remain unvalidated. |

Cross-source agreement is supporting evidence, not proof that either source is ground truth. Predeclare acceptance criteria for the intended use; large unexplained disagreements block the affected scientific claim. Preserve original values.

### 8.7 Device and laboratory test cases

Instantiate DEVICE-01 through DEVICE-06 for each Section 7 category and every configured device/report source. When several quantities are emitted by one station, each quantity also needs its own FEAT cases.

| Test ID | Action | Required assertion |
| --- | --- | --- |
| DEVICE-01 Authentic connection | Read a real deployed device/gateway or ingest a genuine device/lab export. For claimed live operation, observe a fresh reading through the actual transport. | Device/report identity and original records verified; no emulator or generated CSV. Historical export support alone cannot establish live connectivity. |
| DEVICE-02 Installation/sample context | Compare deployment/sample metadata to actual installation/calibration/report records. | Correct field/location/depth/device/timezone, sampling method, calibration and units; unknown calibration explicitly limits acceptance. |
| DEVICE-03 Independent readings | Compare imported raw readings with device display/logger export or original laboratory report cells. | Values/timestamps/analytes agree with source precision; parser does not invent missing channels. |
| DEVICE-04 Cadence and gaps | Inspect actual recording intervals, duplicate timestamps, outage periods, battery/status/QA flags where supplied. | Correct gap/duplicate classification and no gap-filled data. For discrete lab/root/biomass samples, validate sample counts and collection dates instead of cadence. |
| DEVICE-05 Scientific checks | Apply the device-specific checks in Section 7 and relevant domain profiles. | Physically plausible calibrated readings or explicit rejection; derived quantities use actual inputs and method references. |
| DEVICE-06 Persistence/export | Commit actual sensor/report results; reconnect and read them; compare complete exports. | Exact sample/deployment/field/depth/time association and raw provenance retained; all readings represented or explicitly rejected. |

### 8.8 API, security and frontend contract cases

Run API tests against the actual PostgreSQL/PostGIS acceptance service. Unit tests may isolate pure validation and presentation helpers, but mocks/in-memory stores do not satisfy these acceptance cases. Browser cases use the production frontend build and a dedicated acceptance account with only acceptance-owned records.

| Test ID | Action | Required assertion |
| --- | --- | --- |
| API-01 Clean startup/readiness | Start the API in a clean process with documented configuration and migrations applied. | Health is live; readiness verifies the real database/schema; missing configuration or unapplied migrations prevents readiness without leaking secrets. |
| API-02 Authentication lifecycle | Exercise login/session creation, expiry/revocation and invalid credentials using the selected design. | Protected routes reject absent/invalid credentials; secrets/password material is never returned or logged; cookie/token flags match the deployment model. |
| API-03 Object authorization | Use two acceptance users and attempt cross-user reads/writes for profiles, fields, uploads, plans, recommendations and exports. | Every unauthorized operation is denied even when a valid object ID is known; list endpoints do not leak foreign records. |
| API-04 CORS and browser security | Send allowed/disallowed origins and preflight requests; exercise stored user text in the browser. | Only configured origins/methods/headers pass; credential rules are safe; user values render as text and cannot execute script. |
| API-05 Schema/OpenAPI compatibility | Validate every route response and the frontend DTO/client expectations against the committed OpenAPI artifact. | Required fields, nullability, enums, units, dates, geometry and error codes agree; incompatible changes require a version or coordinated migration. |
| API-06 Field and KML/KMZ roundtrip | Upload an actual KML/KMZ and create/update a GeoJSON field through the API; read and export it. | Stable server ID, ownership, holes/MultiPolygons, coordinate order, provenance, authoritative PostGIS area and export geometry agree within declared tolerance. Invalid/oversized/XML-unsafe uploads fail safely. |
| API-07 Persistence/concurrency/idempotency | Create and update a field, soil record and planting plan; repeat an idempotent request and submit a stale version. | A new process reads committed values; duplicates are not created; stale writes return a conflict; revision/audit history is intact. |
| API-08 Scientific missing and quality states | Request a field with missing, rejected and blocked inputs from the authentic corpus. | Responses preserve availability/quality/reason/provenance and never substitute demo values, regional defaults, zeros or generated geometry. Dependent recommendations remain unavailable. |
| API-09 Recommendation reproducibility | Request a recommendation with complete accepted inputs, then retrieve its stored run. | Inputs, versions, rules/model, exclusions, uncertainty, outputs and lineage reproduce exactly; changed data creates a distinct run/version. |
| API-10 Market freshness and units | Retrieve authentic market observations and a financial scenario, including a stale or unavailable case. | Commodity, mandi, currency, quantity basis, observation time, source and freshness are explicit; stale/missing inputs cannot appear as current profitability. |
| API-11 Pagination/errors/jobs | Exercise first/middle/last pages, invalid filters, provider failure and long-running job polling. | Ordering has no gaps/duplicates; validation/error envelopes are stable; jobs expose truthful states and provider failures cannot appear complete. |
| API-12 Frontend production journeys | Run the production frontend against the acceptance API through profile, plot draw/import, analysis, recommendation, market, plan and export journeys, including refresh and failure states. | Server state survives refresh/new browser process; no production screen depends on seeded `localStorage` or hardcoded scientific/financial data; loading/empty/error/blocked states are understandable and exports are complete. |

### 8.9 End-to-end acceptance cases

| Test ID | Action | Required assertion |
| --- | --- | --- |
| E2E-01 Full real run | Run the complete pipeline on the declared authentic acceptance corpus with all required domains enabled. | Real inputs → real source data → validated records → actual PostgreSQL → full outputs. Every required feature has positive evidence in its applicable acceptance context. |
| E2E-02 Source failure | Make one configured source actually unavailable in the acceptance environment. | Affected features/jobs fail or block explicitly; independent results retain truthful status; overall required run cannot pass. |
| E2E-03 Quality failure | Process an authentic record set containing a documented failed quality condition. | Invalid observations quarantined; dependent calculations withheld; reason appears in database/status/export/report. |
| E2E-04 Missing feature | Run an actually uncovered date/site or incomplete authentic report. | Every requested missing feature remains in the status output; zero/omission/synthetic replacement cannot hide the gap. |
| E2E-05 Repeat run | Re-run identical authentic inputs and then a changed actual time/source/version selection. | Stable field IDs, correct deduplication, preserved distinct observations and immutable raw history. |
| E2E-06 Complete export | Reconcile every database record, lineage edge and export partition; exercise filtering/pagination. | Counts/IDs/checksums agree; filters leave original complete data unchanged and declare selection criteria/counts. |
| E2E-07 Clean process | Start a new process using documented configuration and required services, then query/reproduce the accepted run. | No dependency on interactive-session memory, temporary files, hidden credentials or manual state; evidence survives process restart. |
| E2E-08 Requirement coverage | Compare the full frozen feature/source/device/case inventory with test evidence and completion ledger. | 100% of required atomic features, bindings, instrument categories and applicable tests verified; zero missing tests, unresolved blockers or false passes. |
| E2E-09 API/UI reconciliation | Reconcile representative values and missing states across raw assets, database, exports, API responses and the production frontend. | IDs, geometry, values, units, periods, evidence type, quality, provenance and availability agree at every layer; formatting does not change meaning and no browser fallback masks missing data. |

## 9. Final completion checklist and handover

Before reporting the full implementation complete, verify all of the following:

- Every S01–S12 gate passed with evidence, and every Section 5 family/child is implemented.
- Every Section 6 source binding has verified authentic access/import, semantic data validation and persistence; every instrument category has actual readings/reports and its required tests.
- The database is PostgreSQL/PostGIS, with successful independent connection, spatial behavior, commit/readback, failure and idempotency tests.
- No fabricated, augmented, synthetic, mock or fallback-generated data are used in the accepted dataset, development scripts or tests. No locally generated simulations are presented as observed data.
- All scientific values have source mappings, original records, documented units/context, quality results and traceable derivations.
- Every required feature appears in the status export even when missing at a particular field. Positive acceptance evidence exists for every feature in the agreed corpus.
- The full fresh acceptance command exits successfully with zero required failures, blockers or skips; test discovery and coverage checks pass.
- Full exports reconcile with the database and immutable raw assets, including categorical data, curves, series, metadata and all partitions.
- API-01 through API-12 and E2E-01 through E2E-09 pass against the production frontend build and real acceptance database.
- Production frontend behavior uses authenticated API state, not automatic demo seeding, hardcoded scientific/financial values, fabricated identifiers/boundaries or browser-only persistence.
- Python modules, API routes and CLI entry points are reusable and documented with concise comments/docstrings where useful; documented clean-process runs reproduce the accepted behavior.

Deliver the Python source files and tests, package/API/CLI usage instructions, migrations, registries, generated OpenAPI artifact, frontend field mapping, deployment/CORS/auth configuration, real input/source evidence references, complete export bundles, acceptance commands, machine-readable test results and readable coverage report. Report actual implemented/verified totals and any remaining blockers. If any required item is incomplete, explicitly say the implementation is incomplete and list the exact feature/source/test IDs; do not describe partial completion as completion of this plan.
