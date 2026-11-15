# Frontend/backend integration contract

Revision: `shared-workspace-1`, 2026-11-15.
Status: **foundation implemented; remaining resource contracts proposed**.

Approved deployment: no accounts for now; one shared workspace over Tailscale.
Frontend port 1080, backend port 8000. Configure the actual Tailscale IP rather
than a wildcard browser address. Every tailnet client permitted by access rules
shares access; there is no per-person privacy or user authorization claim.
`docs/openapi.json` describes only implemented routes. `docs/api-running.md`
contains executable commands and limitations.

## 1. Authority and how to use this file

This is the single cross-branch integration contract. Backend tasks are in
`backendplan.md`; frontend tasks are in `frontendplan.md` on branch `frontend`.
Both plans refer to the operation IDs below instead of independently inventing
paths or JSON shapes. All paths in this document are HTTP paths, not local files.

During B01/F01, turn the agreed first-slice schemas into a backend-owned
`docs/openapi.json`, with unique operation IDs matching this document. Export it
from the actual FastAPI application; pin an identical artifact and its SHA-256
in the frontend's `contracts` directory. Record the backend commit when committed.
Until then this document is a design specification, not evidence of an API.
Do not generate placeholder agricultural response examples to fill the artifact.

Change a contract in this order: update this specification, backend schemas and
route tests, export OpenAPI, update the frontend snapshot/adapters, then run
compatibility checks. Incompatible deployed changes require a new API version;
do not silently rename v1 properties. Optional future operations may enter the
artifact only when their schemas and behavior are specified and implemented.

## 2. Decisions to resolve before freezing

| Decision | Required result | Work blocked |
| --- | --- | --- |
| D01 Authentication | Resolved: no accounts/tokens now. Bind only loopback/Tailscale; access controlled by tailnet rules. Check browser Origin/Host; CORS is not authentication. | Public/multi-user deployment deferred. |
| D02 Ownership | Resolved: one shared workspace with an explicit configured project allow-list. Never expose all stored projects automatically. | Reads need explicit project configuration. |
| D03 Product extensions | Deferred by owner: authentic economic sources/methods are not yet defined. | Financial recommendations, markets and forecasts. |
| D04 Evidence-use policy | Approved: inspect pending records with labels, never promote them to accepted. | Decision rules need their own specified policy. |
| D05 Geography support | Approved: Polygon/MultiPolygon only; no non-spatial drafts. Unsupported topology/projections remain rejected. | Missing authentic geometry acceptance contexts. |

Implement the approved shared-access slice without a login service. Public or
multi-user deployment requires a new decision and contract revision. Other work
can proceed only when independent of unresolved source/method dependencies.

## 3. Transport conventions

- API root is `/api/v1`. `VITE_API_BASE_URL` is an absolute origin only, without
  credentials, query, fragment or path (apart from an optional trailing slash).
  The client appends `/api/v1` exactly once. Missing production configuration is
  a startup error. HTTP is allowed on documented loopback/Tailscale use only;
  public deployment is unsupported in account-free mode.
- JSON uses snake_case; identifiers are opaque strings, not assumed integers or
  UUIDs. Existing field IDs are hashes; existing source/crop IDs have other forms.
  Frontend adapters may use camelCase internally. Dates are `YYYY-MM-DD`.
  Audit instants use RFC 3339 with an offset; provider-local observation time
  retains its original time standard and is not falsely labelled UTC.
- Successful object responses: `{data: T, meta: {request_id, api_version: "v1"}}`.
  Collections: `{data: T[], meta: {request_id, api_version, next_cursor}}`.
  Empty collection means a completed query with no matching records, not a
  failed or unimplemented capability.
- Collections accept `limit` (default 50, maximum 200) and opaque `cursor`.
  Stable ordering and a cursor bound to filters/project/snapshot are required.
  Complete totals cannot be computed from just the visible page.
- Errors: `{error: {code, message, details: [{path, code, message}], retryable},
  meta: {request_id, api_version}}`. `details` may be empty; messages never
  contain DSNs, local paths, stack traces or secrets.
- Common HTTP outcomes: 400 malformed request/cursor; 401 no valid session;
  403 prohibited action; 404 absent OR unowned resource; 409 state/idempotency
  conflict; 412 stale ETag; 413 upload too large; 415 unsupported media;
  422 semantic validation; 428 missing required If-Match; 429 rate limit;
  501 capability not implemented; 503 configured dependency unavailable.
  429/503 may include `Retry-After`. Normalize FastAPI validation errors too.
- POST creates return 201 and `Location`; asynchronous submission returns 202
  with a Job and `Location` for `getJob`. PATCH returns the updated resource.
  Future 204 responses have no JSON body; no session DELETE exists in this mode.
- Profile, field and planting-plan responses carry a strong `ETag` and positive
  integer `version`; PATCH requires `If-Match` from the last read. Omitted
  properties stay unchanged; explicit null clears only nullable properties.
  Project scope, identifiers, provenance and computed values are not writable.
- All mutating POST operations require `Idempotency-Key`. Scope keys by
  workspace+operation, compare payload hashes, persist their result transactionally.
  Same key/body replays the original resource/job; changed body returns 409.
  Publish retention in OpenAPI before implementation. Never auto-retry an
  ambiguous write without this guarantee.
- Return `X-Request-ID`; CORS for future writes must allow If-Match and
  Idempotency-Key, and expose ETag, Location, Content-Disposition, Retry-After
  and X-Request-ID. Use explicit origin allow-lists and no cookies/credentials.
  Foundation CORS allows GET and X-Request-ID only; expand with actual writes.
  Set API responses to `Cache-Control: no-store`.
- Never run acquisition on a GET, expose an acceptance/health-check CLI as a
  public endpoint, or let callers supply filesystem paths/provider URLs.

## 4. Operation registry

**Implemented:** getHealth/getWorkspace, listFields/getField,
listObservations/getObservation/listObservationEvidence.
The implementation column identifies the backend task, not current readiness.
Resource IDs, nested resources, downloads and jobs must stay within the explicit
shared project scope. No login routes exist.

| Operation ID | Method and path after `/api/v1` | Request / response | Task |
| --- | --- | --- | --- |
| getHealth | GET `/health` | Minimal liveness/version only; no provider calls or DB credentials | B02 |
| getWorkspace | GET `/workspace` | Shared access mode, project IDs and capabilities; no user/token | B02 |
| getProfile | GET `/profile` | Profile, including legitimately null unset fields | B02 |
| updateProfile | PATCH `/profile` | Profile writable properties; Profile + ETag | B02 |
| listFields | GET `/fields` | `archived=false` by default; page of FieldSummary | B03 |
| createField | POST `/fields` | CreateField; Field + ETag | B04 |
| getField | GET `/fields/{field_id}` | Field including current authoritative geometry + ETag | B03 |
| updateField | PATCH `/fields/{field_id}` | Name/location/declarations, geometry or archived; Field + ETag | B04 |
| listObservations | GET `/fields/{field_id}/observations` | `variable_id`, inclusive `start_date`, `end_date`, `validation_status` (default `all`); page of CanonicalObservation | B03 |
| getObservation | GET `/fields/{field_id}/observations/{canonical_observation_id}` | CanonicalObservation plus complete, paginated evidence through listObservationEvidence | B03 |
| listObservationEvidence | GET `/fields/{field_id}/observations/{canonical_observation_id}/evidence` | Page of source Observation records, redacted as specified below | B03 |
| getAnalysis | GET `/fields/{field_id}/analysis` | Explicit `start_date`, `end_date`; Analysis sections/metrics with availability | B05 |
| listSoilRecords | GET `/fields/{field_id}/soil-records` | Page of SoilRecord | B05 |
| createSoilRecord | POST `/fields/{field_id}/soil-records` | SoilSubmission; append-only SoilRecord, never automatically verified | B05 |
| createBoundaryImport | POST `/boundary-imports` | Multipart `file`, `origin`; 202 Job for preview preparation | B04 |
| getBoundaryImport | GET `/boundary-imports/{import_id}` | ImportPreview when ready; status/reasons otherwise | B04 |
| confirmBoundaryImport | POST `/boundary-imports/{import_id}/confirm` | `preview_version`, `selected_candidate_ids`; 202 Job | B04 |
| getJob | GET `/jobs/{job_id}` | Job; no internal output path | B04 |
| createAcquisition | POST `/fields/{field_id}/acquisitions` | `source_id`, `variable_ids`, `start_date`, `end_date`, `boundary_id`; 202 Job | B06 |
| createExport | POST `/fields/{field_id}/exports` | `boundary_id`, `format` = `geojson`, `kml`, `kmz` or `profile`; 202 Job | B04/B06 |
| downloadExport | GET `/exports/{export_id}/download` | Authorized bytes, correct MIME and Content-Disposition; not JSON envelope | B04/B06 |
| listScenes | GET `/fields/{field_id}/scenes` | Date range; page of Scene | B06 |
| getVegetationSeries | GET `/fields/{field_id}/vegetation-series` | Date range, `index` = `ndvi` or `ndwi`; VegetationSeries | B06 |
| listCrops | GET `/crops` | Region/season filters when supported; page of Crop | B07 |
| createRecommendation | POST `/fields/{field_id}/recommendation-runs` | RecommendationInput; 202 Job | B07 |
| listRecommendations | GET `/fields/{field_id}/recommendation-runs` | Season/date filters; page of RecommendationRun, newest first | B07 |
| getRecommendation | GET `/recommendation-runs/{run_id}` | Persisted RecommendationRun | B07 |
| listMandis | GET `/mandis` | Region filter; page of Mandi | B07 |
| listMarkets | GET `/market-observations` | Commodity/mandi/date filters; page of MarketObservation | B07 |
| listPlans | GET `/planting-plans` | Field/status filters; page of PlantingPlan | B08 |
| createPlan | POST `/planting-plans` | PlanInput; PlantingPlan + ETag | B08 |
| getPlan | GET `/planting-plans/{plan_id}` | PlantingPlan + ETag | B08 |
| updatePlan | PATCH `/planting-plans/{plan_id}` | Writable PlanInput properties/status; PlantingPlan + ETag | B08 |

Login/callback/refresh paths are absent by decision D01.
Capabilities distinguish `ready`, `blocked`, `not_implemented`, with `reason`
and `operation_ids`. The frontend disables unsupported operations; direct calls
receive 404 before implementation, or 503 when an implemented route has a
missing dependency. A successful health response is not feature readiness.

## 5. First-slice DTOs

### Implemented read-slice limits (authoritative over future write DTOs below)

`docs/openapi.json` is the exact implemented schema. Fields do not yet have a
version/ETag/archive mechanism: no writes are enabled. They return field_id,
project_id, nullable name/current_boundary_id/selected_boundary_id, geometry_status,
boundary_versions and nullable geometry/metric_crs/area_m2/area_ha/perimeter_m/
representative_point/repair_notes. No invented version, bounds, declarations,
location or financial fields are returned. The later DTO extensions below must
be introduced with their implementing task.

`getField` accepts optional boundary_id. When more than one stored version
exists, geometry_status is selection_required and geometry is null until an
explicit version is selected. A sole recorded boundary is unambiguous.
Unprepared canonical schema or missing configuration is 503, not an empty list.
Observation date filters must be supplied as an ordered start_date/end_date
pair; dates filter actual provider observed_at, never retrieval timestamps.
Snapshot changes during pagination return 409; tampering, changed filters or
server restart invalidate the cursor with 400. See api-running.md for scale limits.

Names below are schema names for OpenAPI. Fields listed as nullable must be
returned as null when absent, not filled from frontend seeds.

### Workspace and Profile

Workspace: `access_mode: shared_trusted_network`, `project_ids`,
`contract_revision`, `capabilities`. Project scope is configured server-side,
not supplied by the browser.

Profile (future shared resource): `workspace_id`, `version`, `name`, `kannada_name`, `phone`, `village`,
`taluk`, `district`, `state`, `soil_health_card_no`, `farmer_category`,
`preferred_language`, `risk_tolerance`, `primary_objective`.
All properties except workspace_id/version are nullable user submissions; GET never
seeds a person's data. Freeze allowed preference codes in B01: HTML and
storageService currently disagree on primary-objective codes. A soil-card number
on a profile is not a laboratory record and does not imply verification.

### Fields

FieldSummary: `field_id`, `project_id`, `name`, `version`, `archived`,
`current_boundary_id`, `area_m2`, `area_ha`, `representative_point`,
`geometry_status`. Fields from legacy evidence with no reviewed current boundary
have null geometry metrics and a reason, never an arbitrary "latest" boundary.
No soil/recommendation counts are promised by this first-slice DTO.

Field extends FieldSummary with `geometry` (EPSG:4326 GeoJSON geometry or null),
`bounds` (`[west,south,east,north]` or null), `perimeter_m`, `metric_crs`,
`repair_notes`, `location`, `declarations`, `source_asset_id`. Location has
nullable district/taluk/village/survey_number strings. Declarations retain
user-entered irrigation_type, water_availability, previous_crops and soil_texture,
with submitted_at and provenance; they are not measured observations.

CreateField: `name`, `geometry`, `origin`, optional `location` and `declarations`.
An explicit shared-project configuration supplies project_id; if multiple
projects require browser selection, add and authorize that property in B01.
Reject missing geometry, invalid/nonpolygon geometry and client-supplied
authoritative area. Server-generated IDs persist across geometry revisions.
No `plot_id` alias on the wire. Browser acre/gunta display is a documented unit
conversion of server area; drawing estimates are provisional only.

Stored geometry and API geometry preserve holes/MultiPolygons. Leaflet consumes
GeoJSON through `L.geoJSON`; manually converting a Point to Leaflet uses
`[latitude, longitude]`, never mutates the wire coordinates.
Backend computes area/perimeter with a documented projection and reconciles
PostGIS results. Current ingestion first computes pyproj/Shapely metrics and
then checks PostGIS; do not describe that as an already-existing HTTP calculation.

### Canonical observations, evidence and missing data

CanonicalObservation: `canonical_observation_id`, `context_id`, `field_id`,
`variable_id`, `validation_status`, `validation_evidence`, `scientific_record`,
`evidence_count`, `has_conflicting_revisions`.

`scientific_record` follows `canonical_record()` in `contracts/canonical.py`.
It is NOT an `Observation`: canonicalization removes audit fields and adds
`source_context`, sometimes `normalization`. Generate a distinct response schema.
Preserve exactly one typed value, original/standardized units, measurement_basis,
provider observation time/timezone, spatial_support, evidence_type, quality flags,
depth/crop/period dimensions and normalization lineage.

Evidence records follow `Observation` in `contracts/observation.py`; paginate
their list separately. Preserve source IDs/checksums/record locators and
retrieval timestamps. Exclude local raw paths, secret request headers and internal
connection/config metadata. A checksum ID does not authorize raw-asset access.

`listObservations` reads canonical rows, not repeated acquisition receipts.
Resolve reviewed field aliases for query identity and authorize the canonical
field. Retain distinct conflicting revisions; do not average or choose one by
retrieval time. Return pending/rejected states accurately. Client filters cannot
change scientific status.

POWER supported variable IDs currently are `daily_rainfall`, `temperature_mean`,
`temperature_max`, `temperature_min`, `relative_humidity`, `wind_speed`,
`solar_radiation`. Canonical daily rain may be mm while original evidence is
mm/day; retain the one-day normalization metadata rather than silently relabelling.
The current reference is a Dutch parcel, not a Karnataka climate baseline.

Missing source values are feature-status records, not Observation objects with
all value columns null. Add persistence for these gaps in B05: normalize_power()
currently returns them separately, and storage-proof writes them to a report.

## 6. Analysis and asynchronous DTOs

Analysis: `field_id`, `boundary_id`, `start_date`, `end_date`, `sections`.
Each section has a stable `section_id` (`soil`, `water`, `climate`),
`capability_state`, `reason`, and `metrics`. Metric IDs and units must be mapped
from the existing screen inventory to registered backend variables during B05;
unsupported metrics remain explicitly blocked, not aliased by similar names.

Each Metric contains `metric_id`, `variable_id` (nullable if not yet registered),
`availability`, `validation_status`, `reason`, `observation_ids`,
`canonical_observation_ids`, and `value` (typed or null), `unit`, `basis`,
`period`, `source_refs`, `quality_flags`, `freshness`.
Use Plan.md availability vocabulary: `available`, `not_collected`,
`not_available_from_source`, `outside_source_coverage`, `access_restricted`,
`collection_failed`, `insufficient_inputs`, `insufficient_quality`,
`not_applicable`, `below_detection_limit`.
`available` still requires accepted evidence. Pending values can be inspected via
canonical observations; summary metrics use null plus insufficient_quality until
approved. Do not block engineering health because records remain pending.
Freshness (`fresh`, `stale`, `unknown`) is separate from availability/validation.

SoilSubmission: actual `card_no`, `lab_name`, `sample_date`, `origin`,
optional `report_asset_id`, and `measurements` with variable_id, typed
original value, original_unit, basis, depth and source locator. Report attachment
upload, allowed variables/units and unknown-date rules must be frozen in B05
before enabling attachment UI. Do not substitute today's date for sampling.
SoilRecord adds server `soil_record_id`, field_id, submitted_at, source lineage
and `validation_status: pending` initially. Preserve revisions append-only.
Do not accept a client `verified` boolean or reinterpret untyped "inches" as flow.

Job: `job_id`, `kind`, `state`, `created_at`, `started_at`, `completed_at`,
`result` (nullable typed reference), `error` (nullable standard error object),
`warnings`, `retry_after_seconds`. States:
`queued`, `running`, `succeeded`, `partial`, `failed`, `blocked`.
Terminal states are the last four; partial is not succeeded.
Result references identify import_id, field_ids, export_id or run_id, never paths.
Map existing `in_progress` to running, `complete` to succeeded, and preserve
boundary-import partial/failed. New durable job storage is needed: existing
extraction_jobs cannot queue before source_asset_id exists and imports are
synchronous. Persist recovery/retry state, not just an in-process background task.

ImportPreview: `import_id`, `preview_version`, `state`, `source_asset_id`,
`origin`, `candidates`, `rejected_records`, `reason`.
Candidates have stable candidate_id, source locator, metadata, geometry,
provisional metrics and repair requirements. Preview must not create active fields.
Confirmation names selected candidates and the exact preview version; stale
confirmation = 409. Current ingest_boundaries() writes immediately, so refactor
parse/preview/commit boundaries instead of calling it for preview.
No one-click implicit repair: current parser requires an authentic reviewed
reference plus area/shape tolerances. Until an authorized repair-evidence workflow
is specified, repair-required candidates remain blocked.

Exports snapshot the requested owned boundary version. `profile` exports a ZIP
bundle with a completeness/availability manifest; it must not claim full Plan.md
coverage. GeoJSON export can reuse present functionality. KML/KMZ and HTTP
streaming are new work; preserve holes, multipart geometry and escaped metadata.
Unimplemented formats return 501 and are not advertised as ready.

## 7. Later-resource schema gates

The following are required capabilities, not finished schemas. Freeze their
complete schemas, filter codes, bounds and authentic examples in their owning B
task before starting the corresponding F task. A model must stop rather than
guess a missing property or copy a seeded frontend object into the backend.

| DTO | Required content before its gate passes |
| --- | --- |
| Scene / VegetationSeries | Field and boundary versions; scene ID/product/acquisition date; index definition; quality/cloud flags; mean/max units and gaps; rainfall from independently identified climate observations, not invented alongside NDVI; overlay asset/legend/expiry when actually available. Tiles alone are not analytical rasters. |
| Crop | Backend crop/cultivar IDs, authentic names and translations when present, supported geography/seasons, requirement/duration/sowing/risk/guidance records with source/version/availability. Woburn crop_species is not a complete Karnataka recommendation catalog. |
| RecommendationInput | field/boundary version, season with year/date range, method/version, optional explicit scenario assumptions. Slider bounds must match the server contract. Never infer a year from "kharif". |
| RecommendationRun | run_id, input snapshot/version/hash, state, method, suitable/excluded/unavailable groups, reasons, uncertainty, source references and financial outputs only when D03 permits and real inputs exist. A blocked run is not "no suitable crops"; no trained model exists in the audited source. |
| Mandi / MarketObservation | Server commodity/mandi IDs; region, date, min/modal/max, currency/quantity basis, arrivals, provenance and freshness. MSP, trends and farm-gate deductions need their own sourced definitions or explicit unavailable states. |
| PlanInput / PlantingPlan | field/boundary/crop IDs, requested cultivated area with unit, actual chosen dates, irrigation strategy, nullable recommendation_run_id, immutable financial assumptions reference, server plan_id/version and active/archived state. No browser-computed forecast fields accepted. Server validates area and referenced versions; missing forecasts remain null. |

Dashboard is composed from these resources; there is no invented dashboard
endpoint. Field count/area and plan totals must cover all fetched pages or come
from a separately specified server aggregate. Unknown financial values cannot
produce a falsely complete total. Recommendation metrics remain unavailable
until a matching stored run exists.

## 8. Contract acceptance

API-01: OpenAPI operation IDs, DTOs, nullability, status codes and pinned frontend
artifact agree. No advertised implemented operation lacks a route test.

API-02: Account-free configuration, Host/Origin checks and CORS/preflight pass
over separate origins. No public/wildcard binding or cookies/tokens. Browser
protections are not represented as authentication.

API-03: Project scope applies to fields, nested evidence, jobs, imports, exports
and plans. Unconfigured projects are not exposed. All allowed tailnet clients
share access; no per-user isolation is claimed.

API-04: Create/read/PATCH/archival, idempotency replay, changed-key-body conflict,
If-Match and stale-version behavior persist across server restarts.

API-05: Authentic geometry preserves identity, versions, holes, coordinate order,
area and export readback. Preview changes no active field.

API-06: Canonical observations deduplicate repeated evidence without deleting
receipts; pending/rejected/gaps/conflicts/units/timezones survive JSON and UI.

API-07: Queued/running/partial/failed/blocked jobs survive restarts; repeat
confirmation/acquisition/export does not duplicate logical results.

API-08: Unsupported capabilities, no data, bad requests, dependency outages and
authorization failures remain distinct; no seeded data appears on error.

API-09: Later scientific/market/recommendation/plan values reconcile with actual
stored inputs/results and lineage. No unimplemented economics/model claim.

API-10: CLI regressions and independent static deployment pass without sharing
backend files with the browser. Record tested operations and blockers, not a
blanket "API complete" claim.
