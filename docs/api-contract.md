# Frontend/backend integration contract

Revision: `shared-workspace-1`, 2026-11-15.
Status: **shared reads, profiles, field writes, imports/jobs, geometry exports and optional reference-model inference implemented**.
Other resource contracts below remain proposals.

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

The implemented schemas are in backend-owned `docs/openapi.json`, with unique
operation IDs matching this document. Export it
from the actual FastAPI application; pin an identical artifact and its SHA-256
in the frontend's `contracts` directory. Record the backend commit when committed.
See `docs/shared_workspace.md` for the implemented ownership, persistence,
preconditions, worker lifecycle and deployment contract.
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
- Common implemented HTTP outcomes: 400 malformed request/cursor;
  403 prohibited action; 404 absent OR unowned resource; 409 state/idempotency
  conflict; 412 stale ETag; 413 upload too large; 415 unsupported media;
  422 semantic validation; 428 missing required If-Match/Idempotency-Key;
  503 configured dependency unavailable. No session, rate-limit, or
  unimplemented-operation stub is implied by this registry.
- POST creates return 201 and `Location`; asynchronous submission returns 202
  with a Job and `Location` for `getJob`. PATCH returns the updated resource.
  Future 204 responses have no JSON body; no session DELETE exists in this mode.
- Profile responses and dedicated field-mutation responses carry a positive
  integer `version`. Profile and field GETs carry strong ETags; existing field
  read bodies deliberately have no new version property. PATCH requires
  `If-Match` from the last read. Omitted
  properties stay unchanged; explicit null clears only nullable properties.
  Project scope, identifiers, provenance and computed values are not writable.
- All mutating POST operations require `Idempotency-Key`. Scope keys by
  workspace, compare operation and payload hashes, and persist results transactionally.
  Same key/body replays the original resource/job; changed body returns 409.
  Receipts have no automatic expiry; retention is stated in OpenAPI. Never auto-retry an
  ambiguous write without this guarantee.
- Return `X-Request-ID`; CORS allows Content-Type, If-Match and
  Idempotency-Key, and exposes ETag, Location, Content-Disposition
  and X-Request-ID. Use explicit origin allow-lists and no cookies/credentials.
  GET/POST/PATCH/DELETE are supported; mutations require a configured Origin.
  Set API responses to `Cache-Control: no-store`.
- Never run acquisition on a GET, expose an acceptance/health-check CLI as a
  public endpoint, or let callers supply filesystem paths/provider URLs.

## 4. Operation registry

**Implemented:** getHealth/getWorkspace, listFields/getField,
listObservations/getObservation/listObservationEvidence, getProfile/updateProfile,
createField/updateField/archiveField, createBoundaryImport/getBoundaryImport/
confirmBoundaryImport, getJob, createExport/downloadExport,
getReferenceModel/listReferenceContexts/predictReferenceSuitability.
The additive reference-model operations do not implement the field
recommendation or market contracts.
The implementation column identifies the backend task, not current readiness.
Resource IDs, nested resources, downloads and jobs must stay within the explicit
shared project scope. No login routes exist.

| Operation ID | Method and path after `/api/v1` | Request / response | Task |
| --- | --- | --- | --- |
| getHealth | GET `/health` | Minimal liveness/version only; no provider calls or DB credentials | B02 |
| getWorkspace | GET `/workspace` | Shared access mode, project IDs and capabilities; no user/token | B02 |
| getProfile | GET `/profile` | Profile, including legitimately null unset fields | B02 |
| updateProfile | PATCH `/profile` | Profile writable properties; Profile + ETag | B02 |
| listFields | GET `/fields` | Archived records excluded; page of unchanged FieldRecord DTOs | B03 |
| createField | POST `/fields` | project_id, nullable name, geometry; FieldMutation + ETag | B04 |
| getField | GET `/fields/{field_id}` | Field including current authoritative geometry + ETag | B03 |
| updateField | PATCH `/fields/{field_id}` | name and/or geometry; FieldMutation + ETag | B04 |
| archiveField | DELETE `/fields/{field_id}` | If-Match; FieldMutation with archived=true, without deleting history | B04 |
| listObservations | GET `/fields/{field_id}/observations` | `variable_id`, inclusive `start_date`, `end_date`, `validation_status` (default `all`); page of CanonicalObservation | B03 |
| getObservation | GET `/fields/{field_id}/observations/{canonical_observation_id}` | CanonicalObservation plus complete, paginated evidence through listObservationEvidence | B03 |
| listObservationEvidence | GET `/fields/{field_id}/observations/{canonical_observation_id}/evidence` | Page of source Observation records, redacted as specified below | B03 |
| getAnalysis | GET `/fields/{field_id}/analysis` | Explicit `start_date`, `end_date`; Analysis sections/metrics with availability | B05 |
| listSoilRecords | GET `/fields/{field_id}/soil-records` | Page of SoilRecord | B05 |
| createSoilRecord | POST `/fields/{field_id}/soil-records` | SoilSubmission; append-only SoilRecord, never automatically verified | B05 |
| createBoundaryImport | POST `/imports` | Raw bytes; filename, project_id, source_namespace query parameters; 202 Job | B04 |
| getBoundaryImport | GET `/imports/{import_id}` | BoundaryImport with preview candidates/rejections and job IDs | B04 |
| confirmBoundaryImport | POST `/imports/{import_id}/confirm` | `preview_hash`, `candidate_ids`; 202 Job | B04 |
| getJob | GET `/jobs/{job_id}` | Job; no internal output path | B04 |
| createAcquisition | POST `/fields/{field_id}/acquisitions` | `source_id`, `variable_ids`, `start_date`, `end_date`, `boundary_id`; 202 Job | B06 |
| createExport | POST `/exports` | Explicit fields [{field_id,boundary_id}], format = geojson/kml/kmz; 202 Job | B04 |
| downloadExport | GET `/exports/{export_id}/download` | Authorized bytes, correct MIME and Content-Disposition; not JSON envelope | B04/B06 |
| getReferenceModel | GET `/reference-model` | Pinned model/task identity, supported periods/crop systems, reference-only limits and an actual saved example request | I08 |
| listReferenceContexts | GET `/reference-model/contexts` | Required `model_id`, optional `period_id`, normal `limit`/`cursor`; page of saved native contexts, not arbitrary field matches | I08 |
| predictReferenceSuitability | POST `/reference-model/predictions` | ReferencePredictionInput; 200 ReferencePrediction in the standard envelope; no persistent job or mutation | I08 |
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

### Reference-model serving increment

The independent `reference_suitability` capability reports only the configured
GAEZ-reference model. `recommendations`, `crops` and `markets` do not become ready
because it is available. The public reference corpus is shared; it does not
read, infer ownership of, or attach observations to any workspace field.

The operator must configure both `AGRI_REFERENCE_MODEL_DIR` and
`AGRI_REFERENCE_MODEL_ID`. The directory is local, server-only configuration;
clients never supply artifact paths, URLs, weights, traits or environmental
values. Loading verifies the artifact checksums and pinned identity. Missing,
incompatible or changed artifacts return a redacted 503 instead of fallback
scores. Loading/inference is serialized per API process with one cached CPU
model; overlapping model requests receive retryable 503
`reference_model_busy`, not an unbounded work queue. Replacing model files
requires a process restart, not an implicit hot swap.
Artifact checksums are verified on initial load; subsequent requests hash all
serving files and the manifest and check the remaining bundle members for
filesystem changes. Missing ML dependencies or insufficient shared-memory
reserve leave this capability blocked without stopping the rest of the API.

`ReferencePredictionInput` extends the saved CLI request with a required
`model_id`: schema version `1`, task `india_published_reference_suitability`,
mode `historical_reference_analysis`, comparison scope `reference_climate_only`,
saved `context_id`, exact `analysis_start`/`analysis_end`, production system
`HRLM`/`HILM`/`LRLM`/`LILM`, `crop_ids`, optional `excluded_crop_ids` and a
0-100 `minimum_reference_score`. Each candidate/exclusion list has at most 100
bounded crop identifiers; repeated candidates and unknown input properties
return 422. Field coordinates and seasonal/strict-as-of/rotation requests
are not accepted. A stale model ID returns 409; an absent saved context returns
404; a changed reference interval returns 422. Context pagination is bound to
the model ID, period filter and snapshot.

The prediction response preserves the CLI's scores, masked relative
preferences, source IDs/native support, missingness and extrapolation warnings,
reference-error bands, attribution and explicit unassessed requirements.
Unsupported or excluded crops have zero preference; an empty eligible set
returns a 200 abstention. Singleton preference is not certain agricultural
success. Metadata exposes only public model information, not local filenames,
training telemetry/process IDs or dataset source paths.

This POST is a bounded, stateless calculation, not a mutating create:
it returns 200 without `Location`, a Job or an idempotency receipt.
The existing configured-Origin requirement still applies. No model operation
downloads data, trains weights, connects to PostgreSQL or opens the test set.
Reference agreement is not independent farm validation or a recommendation
about what to plant next season.

## 5. First-slice DTOs

### Compatible read DTOs

`docs/openapi.json` is the exact implemented schema. Field GET bodies retain field_id,
project_id, nullable name/current_boundary_id/selected_boundary_id, geometry_status,
boundary_versions and nullable geometry/metric_crs/area_m2/area_ha/perimeter_m/
representative_point/repair_notes. No invented version, bounds, declarations,
location or financial fields are returned. ETags come from the same read snapshot;
version/archive information is returned by the dedicated mutation response.

`getField` accepts optional boundary_id. When more than one stored version
exists without an explicitly recorded current version, geometry_status is
selection_required and geometry is null until a version is selected.
A sole recorded boundary or explicitly recorded current version is unambiguous.
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

SharedProfile: `workspace_id`, `version`, `created_at`, `updated_at`, `name`, `kannada_name`, `phone`, `village`,
`taluk`, `district`, `state`, `soil_health_card_no`, `farmer_category`,
`preferred_language`, `risk_tolerance`, `primary_objective`.
User-submission properties are nullable; identity/version/timestamps are server-owned.
GET never seeds a person's data. Preference codes are frozen in ProfilePatch and
SharedProfile in OpenAPI and use the shared-profile adapter, not legacy storageService. A soil-card number
on a profile is not a laboratory record and does not imply verification.

### Fields

FieldRecord uses the unchanged read properties listed above. FieldMutation
contains `field_id`, `version`, `current_boundary_id`, and `archived`.
Location/declarations and soil/recommendation summaries remain outside this release.

FieldCreate requires `project_id` and `geometry`, with optional nullable `name`.
The selected project must belong to the configured server allow-list.
Reject missing geometry, invalid/nonpolygon geometry and client-supplied
authoritative area. Server-generated IDs persist across geometry revisions.
No `plot_id` alias on the wire. Browser acre/gunta display is a documented unit
conversion of server area; drawing estimates are provisional only.

Stored geometry and API geometry preserve holes/MultiPolygons. Leaflet consumes
GeoJSON through `L.geoJSON`; manually converting a Point to Leaflet uses
`[latitude, longitude]`, never mutates the wire coordinates.
Backend computes area/perimeter with a documented projection and reconciles
PostGIS results. Current ingestion first computes pyproj/Shapely metrics and
then checks PostGIS. HTTP writes now compute persisted measurements with PostGIS;
preview measurements remain provisional until confirmation.

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

## 6. Proposed analysis and implemented asynchronous DTOs

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

Job: `job_id`, `resource_id`, `kind`, `status`, `attempts`, `created_at`,
`updated_at`, nullable `result`, and nullable `error {code,message,retryable}`.
Statuses are queued/running/succeeded/failed; kinds are import_preview,
import_confirm, and export. Jobs are durably leased in the application schema,
not aliases for the old synchronous proof workflow or extraction receipts.

BoundaryImport includes import/project/source identity, original filename/checksum,
preview and confirmation job IDs, `preview_hash`, candidates, and rejections.
Candidates include stable IDs, source locator/metadata, original and 2D geometry,
provisional metrics, expected field version and create/update action.
Preview writes no canonical fields, boundaries, or source assets.
Confirmation names selected valid candidate IDs and the exact preview hash.
A mismatched hash returns 409; a later field-version conflict fails the job
without partial writes. The HTTP worker calls the parser, not ingest_boundaries().
No one-click implicit repair: current parser requires an authentic reviewed
reference plus area/shape tolerances. Until an authorized repair-evidence workflow
is specified, repair-required candidates remain blocked.

Exports snapshot explicit field/boundary selections. GeoJSON, KML and KMZ are
implemented, including multipart geometry, holes, escaped source metadata, and
retained original altitude. Missing legacy altitude is labelled, never invented.
Profile/proof bundles and other formats are not supported; invalid format values
return 422. See shared_workspace.md for limits, retention, recovery and downloads.

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
