# 03. Shared API and data contract

**Proposed, not implemented or approved.** Start from the inspected local backend
`docs\frontend_api_contract.md`; commit and reconcile it before generating the
single `contracts\openapi.json` artifact. This document narrows delivery to the
non-AI milestone rather than creating a competing schema.

## Wire rules

- Application prefix `/api/v1`; `/health` and `/ready` remain origin-root service
  probes. JSON is snake_case; frontend adapters may expose camelCase.
- Server-created resource IDs are opaque UUID strings. Provider IDs, species
  codes, legacy plot IDs, observation IDs and geometry revisions are separate.
- Single resources are objects; lists use
  `{items, next_cursor, total_count}` with nullable total count. Specify stable
  cursor ordering and filter binding. Proposed limit: default 20, maximum 100.
- Writes return 201 for creation, 200 for updates, 202 plus `Location` for jobs;
  204 responses have no body. Client parsing must handle all four.
- Versioned PATCH bodies contain `version`; atomic stale updates return 409.
  Creates/import confirmations/job submissions carry persisted
  `Idempotency-Key`; conflicting reuse returns 409, not a duplicate field.
- Errors: `{error: {code, message, field_errors, request_id}}`, where field errors
  have JSON Pointer paths. Normalize framework validation errors.
- Define 401/403/404, 409, 413/415/422, 429 and 503 behavior. Inaccessible private
  IDs use 404; outages and unimplemented capabilities must not look like empty
  successful collections.
- RFC 3339 timestamps have timezone; sample/planned dates use `YYYY-MM-DD`.
  Unknown observation time stays null, separate from retrieval time.
- Scientific numbers are finite; money uses decimal strings plus currency and
  quantity basis. No formatted currency as numeric data.
- Proposed cookie auth follows existing D01: opaque HttpOnly sessions, approved
  same-site HTTPS origins, CSRF protection including login, and provisioned
  accounts. Freeze actual deployment/auth choice before implementing this.
- CORS permits only approved origins and required headers; expose request/schema
  IDs, `Location`, `Retry-After`, and download disposition. Never use wildcard
  credentialed CORS or browser-stored provider/session secrets.

## Keep independent state dimensions

| Dimension | Values / meaning |
| --- | --- |
| Browser transport | `idle`, `loading`, `ready`, `empty`, `error` |
| Capability | `not_started`, `in_progress`, `blocked`, `failed`, `complete` |
| Job | `queued`, `running`, `failed`, `blocked`, `complete` |
| Data availability | `available`, `not_collected`, `not_available_from_source`, `outside_source_coverage`, `access_restricted`, `collection_failed`, `insufficient_inputs`, `insufficient_quality`, `not_applicable`, `below_detection_limit` |
| Validation | `accepted`, `unverified`, `rejected`, `not_evaluated` |
| Freshness | `current`, `stale`, `unknown`, under an explicit policy |

A metric carries `value`, `unit`, `measurement_basis`, `availability`, `reason`,
`evidence_type`, validation/quality, date/depth/spatial support as applicable,
source/observation references, and method/uncertainty metadata. Unavailable
metrics have null values; authentic zero is not missing. Detection limits need
their own censoring metadata, not zero. UI freshness does not change evidence
type: modelled SoilGrids remains modelled, never laboratory measured.

Unimplemented operations return 503 `capability_unavailable`; `/meta` explains
their state. Implemented resources with no accepted evidence return explicit
metric availability. No production fallback to bundled data.

## Consumer-to-resource mapping

All routes below are proposals relative to `/api/v1`. Auth and ownership apply
to private records, jobs, assets and downloads, not just field list requests.

| UI / existing input | Proposed resource and adaptation | Delivery |
| --- | --- | --- |
| Bootstrap/login | `GET /meta`, `GET /auth/csrf`; `POST/GET/DELETE /auth/session`; new login/no-fields screens | P2 |
| Header/profile | `GET/PATCH /me/profile`; preserve name/localized name/contact/location, category, language, risk/objective; versioned write | P2 |
| Field selector/drawing | `GET/POST /fields`, `GET/PATCH /fields/{id}`; map `boundary` to `geometry`, `coordinates` to representative Point, areas to server values | P3 |
| KML/KMZ import | `POST /boundary-imports`, `GET /boundary-imports/{id}`, `POST /boundary-imports/{id}/confirm`; preview creates no fields | P3 |
| Import/export progress | `GET /jobs/{id}`; queued/running/failed/blocked/complete; bounded polling and resume after refresh | P3 |
| GeoJSON/KML/KMZ/full export | `POST /exports`, `GET /exports/{id}`, `GET /exports/{id}/download`; authenticated Blob with safe filename | P3 |
| Soil form | `POST /record-assets`, `GET/POST /fields/{id}/records`, `GET/PATCH /records/{id}`; actual report metadata, unverified until accepted | P4 |
| Land analysis | `GET /fields/{id}/analysis`, `/observations`, `/feature-status`; metric adapters, source and period detail | P4 |
| Acquisition refresh | `POST /fields/{id}/acquisitions`; configured bindings/variables/period, not arbitrary URLs; returns job | P4 |
| My Land imagery/chart | `GET /fields/{id}/scenes`, `/scenes/{scene_id}/overlay`, `/vegetation-series`, `/climate-series`; bind field, scene and geometry revision | P6 |
| Forecast panel | `GET /fields/{id}/forecast`; issue/valid times plus genuine forecast source, otherwise unavailable | P6 |
| Crop selection | `GET /crops`, `GET /crops/{id}`; distinguish species/cultivars, source-backed references; no recommendation required | P5 |
| Market intelligence | `GET /markets`, `/commodities`, `/market-observations`, `/support-prices`; authentic dated records and quantity/currency basis | P6 |
| Manual planting plans | `GET/POST /plans`, `GET/PATCH /plans/{id}`, `GET /plans/summary`; drafts work without recommendation/economics | P5 |
| Dashboard | `GET /dashboard`; owned field/area/verified counts and plan previews; recommendation metrics explicitly deferred | P5 |
| Provenance details | `GET /provenance/assets/{id}`; metadata/checksum, not internal path or unrestricted private original | P4 |
| Recommendations/scenarios/sliders | Reserve existing proposed `/recommendation-runs` and `/economic-scenarios`; do not implement them for this milestone | Deferred |

## Geometry, imports and identity

Accept Polygon/MultiPolygon in GeoJSON longitude/latitude order. Render via
`L.geoJSON`; only explicit Leaflet point calls convert order. Fields return
`id`, `version`, `geometry_version`, full geometry, representative Point,
area/hectares/acres/guntas, perimeter and calculation method.

Persist geometry revisions, not new field IDs on each edit. Area is calculated
server-side under the approved projected/geodesic method and tolerance, stored
with method/version; browser drawing values are labelled provisional. Reported
acreage is a separate submission, not an override.

Import flow: bounded upload -> durable parsing job -> immutable candidates
(original/proposed geometry, notes, repair flag) -> explicit candidate selection
and repair consent -> atomic field creation. Confirmation checks preview version
and idempotency. Refusal, stale previews and worker retry must not create fields.
Preserve all polygon components and holes on map and export.

## Scientific mappings that must not be simple renames

| Frontend property | Backend meaning / required rule |
| --- | --- |
| `organicCarbonPct` | Canonical organic carbon g/kg divided by 10 only with registered conversion and matching measurement basis |
| `nitrogenKgHa` | Available nitrogen, not backend `total_nitrogen` g/kg; require authentic compatible report/method |
| `phosphorusKgHa`, `potassiumKgHa` | Preserve available/total and elemental/oxide basis; do not manufacture kg/ha from concentration without required depth/density/method |
| `hasSoilTest` | Replace with evidence/validation state; a submitted form or modelled map does not imply verified lab evidence |
| `soilDepth` | Reported effective/root-zone category is not the sample's depth interval |
| `groundwaterYieldInches` | Original ambiguous text; normalized flow unavailable until real quantity/time basis is supplied |
| `irrigationCostPerHour` | Actual monetary amount and period/area/time basis; annual cess cannot become hourly cost |
| `annualRainfallMm` | Aggregate with exact coverage/period; distinguish one year, normal and forecast |
| NDWI canopy control | Approve exact bands/index definition; if selecting NDMI, rename UI and variable explicitly |
| `cropId` | Map explicit species/cultivar IDs; do not parse browser slugs or select first variety |

## Manual plan minimum

Require owned `field_id`, authentic `crop_id`, positive `cultivated_area` with
unit, and `planned_sowing_date`. Optional cultivar/harvest/notes/user budget are
explicit inputs. Validate area against the field and date ordering; include
geometry revision. Preserve draft/planned/archived state and optimistic version.

Recommendation/scenario references are nullable. Financial snapshot, predicted
yield, optimized dates and agronomic advice remain unavailable when deferred.
Do not call `recommendationEngine.calculateCropFinancials` merely to save a plan.
Archive preserves history. A later geometry change marks dependent snapshots
stale rather than rewriting their history.
