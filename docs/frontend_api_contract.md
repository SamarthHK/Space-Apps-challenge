# Frontend/backend contract and implementation handoff

**Status: revised design, not a working API.** Audited 2026-11-15 against backend `5d53f6735d1ec1698cd98b7021b8a22efd8e1a4f` and frontend `da3b1c0120d99355c3f05dee3fb429877e34b07c`.

Read this with [backendplan.md](../backendplan.md). That document owns the implementation sequence, scientific requirements and full acceptance matrix; this one owns proposed HTTP shapes and their UI mappings. Approve the decisions below in S01 before generating the contract. Do not treat example field names in this design as acquired data. No provider, API, browser or database acceptance was executed by this document audit.

## 1. Verified findings and consequences

Paths in this table refer to the pinned frontend branch unless labelled backend.

| Evidence | Finding | Required plan correction |
| --- | --- | --- |
| `src/main.js:1-59`, `src/services/storageService.js:272-404` | Bootstrap is synchronous and uses seeded local storage, not HTTP. | Add authentication, asynchronous actions, empty-state bootstrap and request cancellation; changing a URL alone cannot integrate this app. |
| `src/main.js:153-206`, `1433-1489` | Map rendering and KML export use only the first Polygon ring. | Use `L.geoJSON` for server geometry; preserve holes/MultiPolygons and use authorized server exports. |
| `src/main.js:455-575`, `src/data/environmentalData.js:80-206` | Scene selection changes a label, not the underlying imagery; the chart is global rather than field-specific. | Define field/scene-specific overlays and timed series. A colored parcel is not a raster heatmap. |
| `index.html:172-176`, `223-280` | Dates, cloud filter display and weather forecast are hardcoded; forecast rows are not populated by JavaScript. | Add real controls/resources or an explicitly unavailable panel. Historical POWER data cannot supply tomorrow's forecast. |
| `src/main.js:580-619`, `1289-1317` | Soil submission marks itself verified and substitutes today's date; pH/EC/carbon/nutrients have fallbacks. | Add sample/report metadata and a server validation workflow; submission and laboratory verification are different states. |
| `src/main.js:609-614`, `src/services/storageService.js:79-85`, `209-215` | Water yield is labelled inches; one supposed hourly irrigation cost is described as an annual area-based cess. | Preserve reported text and actual quantity basis. Neither value can be normalized into flow or hourly cost by assuming a unit. |
| `src/main.js:982-996`, `1180-1192`, `index.html:648-670` | Category is shown but never saved; objective HTML enums differ from storage comments; language is stored but not edited. | Map all profile fields, save category, and use the actual UI objective enums. Do not infer objectives from obsolete labels. |
| `src/main.js:623-833`, `src/services/recommendationEngine.js:15-236` | Browser assumes every crop has three financial scenarios, applies undocumented multipliers, and sorts by profit. | Separate agronomic assessment from financial availability; persist inputs, scenario rules and results on the server. |
| `src/main.js:838-892`, `src/data/marketData.js:79-146`, `index.html:517-537` | UI needs MSP, trend, arrivals and farm-gate deductions, not only a modal price. Mandi filter IDs are hardcoded. | Include market directory, policy prices, itemized costs and derived outputs. Replace filter pills from returned IDs. |
| `src/main.js:1319-1406` | Plan creation recalculates financials and loses the recommendation run; dates are formatted strings. | Send references, area and real intended dates; store a versioned server snapshot and return ISO dates. |
| `src/main.js:5-9`, `src/data/agriZones.js`, `mandyaData.js`, `sensorStations.js` | The last three data modules have no active imports in the audited source; imported `karnatakaMandis` is unused. | Do not create new endpoints solely for dormant modules; remove unused production datasets in frontend F10. |
| Backend `src/agri_data/__main__.py:1-21`, `pipeline/orchestration.py:27-141` | CLI and pipeline are tightly coupled to initialization, filesystem outputs, acquisition and persistence. No API app/routes were found in the audited `src` tree. | Extract services; do not run the CLI as an HTTP subprocess or blindly expose its return dictionary. |
| Backend `pipeline/acquisition.py:43-89`, `storage/database.py:45-117`, `config.py:37-40` | Live acquisition bypasses adapter retrieval, JSON is reserialized before storage, scientific catalog values are seeded, and SQLite is the default. | Unify adapters, preserve original bytes and isolate accepted PostGIS storage before exposing scientific results. |

The broad resources in the older plans are appropriate, but they are **not a tested wire contract**. The schemas and mappings below require frontend DTO adapters and deliberate UI corrections. Existing browser object shapes are not the database schema.

## 2. Approval decisions and dependency rules

These are proposals to make the plan actionable, not silent product decisions. S01 must obtain approval or record a replacement for each; do not implement a materially different choice without updating both branch contracts.

| ID | Proposed baseline | Blocks |
| --- | --- | --- |
| D01 Authentication/deployment | Server-side opaque sessions in a Secure, HttpOnly host-only cookie, CSRF protection, HTTPS and separate frontend/API hosts under the same site. Accounts are provisioned by an administrative CLI initially; no public registration. An existing session survives reload; expiry requires login. | S02 session schema and S04 authentication. Confirm actual origins, lifetime and account provisioning. Unrelated cross-site/Tailscale hostnames may require `SameSite=None` and encounter third-party-cookie blocking: approve and test an alternative bearer/OIDC design before freezing OpenAPI if that is the intended deployment. Do not default to localStorage tokens. |
| D02 Browser-record migration | Do not automatically upload, discard or delete existing local records. Offer an explicit user export and separately reviewed import of authentic user submissions; ignore legacy seeds in production. | Frontend first production migration. User approval is required before deleting browser data. Unproven records cannot become accepted laboratory evidence. |
| D03 Field/plan behavior | Require geometry to create a field; keep incomplete drawings locally only as unsaved UI state. Permit a persisted plan draft with valid field/crop/area/date but unavailable economics; archive instead of hard-delete. Do not impose a new multi-plan land-allocation optimizer. | Field form, plan schema, archive UX. Confirm this policy before coding; there is no geometry-less field or automatic plan allocation in the baseline. |
| D04 Scientific conventions | Separate water source from delivery method; use canonical soil units, explicit nutrient basis, server-computed area, ISO planned dates and explicit season year/date range. Retain unknown source metadata as unknown. | Relevant forms/normalizers. Scientific definitions/tolerances require sources, not a product vote; ambiguous reports block the affected variable. |
| D05 Acceptance inputs and sources | Select real KML/GeoJSON, sample reports, crop/cultivar roster, seasons, database namespace, market/forecast/cost products and two acceptance accounts. Record verified provenance/access and missing prerequisites. | Positive acceptance for each affected task, not independent DTO/client work. No claim of a usable market API, forecast feed or sensor until authentic access is demonstrated. |

S01 freezes schemas and a complete family inventory; it need not acquire every dataset first. Fully specify each domain's atomic variables, units, rules and bindings before implementing that domain. A skeleton registry never satisfies scientific completion. Final S11 still requires all children, sources and devices.

### Local implementation approval (2026-11-15)

The user approved D02-D04 behavior and authorized local service provisioning. Bind the frontend to `0.0.0.0:1080` and API to `0.0.0.0:8080`; these are listening addresses, not browser origins. Initially allow `http://localhost:1080` and `http://127.0.0.1:1080` explicitly. Use the same hostname for both services in a browser. LAN/Tailscale deployment needs its actual origin added to configuration; never allow wildcard credentialed CORS.

Use administrator-provisioned opaque cookie sessions for local development, with configurable expiry and local-only non-Secure cookies on HTTP. Production remains HTTPS-only with Secure cookies. Do not reuse this development exception for a remotely deployed production service. Docker is preferred when available; otherwise provision a real native PostgreSQL/PostGIS instance in ignored local directories.

The bundled KML was described as a test input, not verified authentic field evidence. It cannot pass real-data acceptance. Authenticate and retain provenance for actual boundaries submitted by the frontend; do not import its seeded demo polygons. D05 scientific-source/corpus acceptance remains blocked until such inputs and reports are available.

Frontend F01 may consume a **design-stage** OpenAPI artifact; authentic success responses are required only before the corresponding F03-F09 route is called ready. This resolves the old circular dependency in which frontend contract work required a finished backend but backend S01 required the finished frontend contract.

## 3. Wire conventions to freeze in S01

### 3.1 Transport, naming and errors

- `VITE_API_BASE_URL` is the API **origin only**, without `/api/v1`, query or fragment. The client strips a trailing slash and appends `/api/v1` exactly once. Public runtime configuration may override it if documented. Do not bake a particular machine's address into source.
- All routes in Section 5 are relative to `/api/v1`. Service liveness/readiness are `/health` and `/ready` at the origin root; readiness failure returns 503. They must not contact every external agricultural provider.
- JSON uses `snake_case`; identifiers are opaque strings. Application-created resource IDs use UUIDs; registered variable/feature/source codes and original provider identifiers remain separate fields. Frontend camelCase exists only in adapters.
- Successful single-resource responses are the resource object. Lists are `{items: T[], next_cursor: string|null, total_count: integer|null}`. `limit` defaults to 20 and is bounded to 100; reject out-of-range values with 422. Cursors bind filters and stable ordering; list contracts define their sort keys. Summary totals must not be computed from one page.
- `GET` and ordinary `PATCH` return 200; synchronous create returns 201 with `Location`; accepted jobs return 202 with a `Job` and `Location`; archive/logout returns 204 without JSON. A ready empty list returns `items: []`. Unsupported query keys and body fields are rejected, not silently ignored.
- Errors use `{error: {code: string, message: string, field_errors: [{path: string, code: string, message: string}], request_id: string}}`. Field paths use JSON Pointer. Standardize FastAPI request-validation errors into this envelope.
- Use 401 for unauthenticated, 403 for prohibited operations, 404 for inaccessible object IDs (no cross-owner existence leak), 409 for version/idempotency conflict, 413 for size limits, 415 for unsupported media, 422 for invalid input, 429 with `Retry-After` for rate limits, and 503 for unavailable infrastructure. Scientific missingness is a resource state, not a fake success value or automatically a 500.
- Every response includes `X-Request-ID` and `X-API-Schema-Version`. CORS exposes these plus `Location`, `Content-Disposition` and `Retry-After`. Allow only approved origins, methods and headers, including `Content-Type`, `X-CSRF-Token`, `Idempotency-Key` and `X-Request-ID` for the cookie baseline.
- Versioned updates require `version: integer` in the body; the server performs an atomic compare-and-update and increments it. Stale writes return 409 with stable code `version_conflict`. No last-writer-wins fallback.
- Require `Idempotency-Key` on creates/job submissions/confirmations, scoped by actor, route and normalized payload hash (including uploaded-byte checksum). Same key/payload replays the original status/resource; a different payload returns 409. Authentication bootstrap is excluded. Persist keys/results transactionally and document retention; expired keys are not a substitute for source-level deduplication.
- Timestamps are RFC 3339 with timezone. Civil dates such as sampling and planned sowing use `YYYY-MM-DD` and are not converted into midnight UTC. Unknown observation dates stay null; retrieval time is separate.
- Use JSON numbers for finite scientific values; no NaN/Infinity. Money is a decimal string plus ISO currency and quantity basis; frontend adapters format it without recalculating economics. Do not ship preformatted currency strings as numeric fields.
- GeoJSON uses longitude/latitude, EPSG:4326 semantics and no custom `crs` member. Leaflet conversion happens once, preferably through `L.geoJSON`; an interior representative point is a GeoJSON Point, not the old `[lat, lng]` array.

### 3.2 State vocabulary and common shapes

These are schema definitions, not fake response fixtures. `?` marks an optional request field. Response fields declared nullable must remain present as null; arrays may be empty. Write bodies cannot set server-owned IDs, ownership, scientific acceptance or calculated metrics.

| Shape | Required contract |
| --- | --- |
| `Metric<T>` | `value: T\|null`, `unit: string\|null`, `measurement_basis: string\|null`, `availability: Availability`, `reason: string\|null`, `evidence_type: EvidenceType\|null`, `validation_status: accepted\|unverified\|rejected\|not_evaluated`, `quality_flags: string[]`, `observed_at: timestamp\|null`, `period_start/period_end: date-or-timestamp\|null` with a required `temporal_support: instant\|civil_date_interval\|timestamp_interval\|unknown` discriminator, `reference_period: object\|null`, `source_refs: SourceRef[]`, `observation_ids: string[]`, `method_id: string\|null`, `spatial_support: string\|null`, `spatial_resolution_m: number\|null`, `uncertainty: object\|null`. Freeze structured reference-period/uncertainty schemas in S01, not unrestricted JSON. |
| `SourceRef` | `source_id`, `dataset_id`, `source_asset_id`, `source_record_locator`, `product_version: string\|null`; resolve details through the authorized provenance route. Never return local paths or provider secrets. |
| `Availability` | Exactly the backend Section 4.3 enum: `available`, `not_collected`, `not_available_from_source`, `outside_source_coverage`, `access_restricted`, `collection_failed`, `insufficient_inputs`, `insufficient_quality`, `not_applicable`, `below_detection_limit`. |
| `EvidenceType` | Backend Section 4.2 values, including distinct `forecast` and `projection`. A user submission is `surveyed`, never a verified laboratory measurement merely because a box was checked. |
| `Money` / `Quantity` | Money: `{amount: decimal-string, currency: string, per_quantity: number\|null, per_unit: string\|null}`. Quantity: `{value: number, unit: string}`. Use `Metric<Money>` for scientific/economic outputs; direct user budgets are separately labelled assumptions. |
| `Job` | `id`, `kind`, `status: queued\|running\|failed\|blocked\|complete`, `created_at`, `started_at/finished_at: timestamp\|null`, `progress: {completed: integer, total: integer\|null}`, `resource_refs: [{type,id}]`, `error: error-object\|null`, `blockers: [{code,reason,next_action}]`. Job state is not feature availability. |
| `Capability` | `resource`, `implementation_status: not_started\|in_progress\|blocked\|failed\|complete`, `reason: string\|null`, `next_action: string\|null`. Capabilities describe implementation, not provider freshness. |
| `Freshness` | `{status: current\|stale\|unknown, evaluated_at: timestamp, policy_id: string\|null, reason: string\|null}` accompanies market/forecast/history where appropriate; `stale` is not an extra Availability value. Historical data is not stale merely because it is old. |

An accepted metric has a correctly typed value, dimensions and lineage. An unavailable metric has null value and an actionable reason; zero is reserved for an authentic zero. Censored lab values require the Section 4.2 detection-limit fields and cannot be represented as a numeric zero. User submissions remain accessible in record/draft endpoints with `unverified` status, but accepted analysis excludes them until the relevant rules pass.

Transport state (`idle/loading/ready/empty/error`), implementation capability, job state, data availability, validation status and freshness are separate axes. An implemented resource with no accepted data returns its Metric/gap structure. A wholly unimplemented operation returns 503 `capability_unavailable` plus its capability entry; an empty array must not conceal lack of implementation.

## 4. Resource DTOs and form contracts

### 4.1 Session and profile

Under D01's cookie proposal, `GET /auth/csrf` returns a pre-authentication CSRF token tied to a short-lived server context; no user data. `POST /auth/session` accepts `{login, password}` with CSRF and Origin validation, rate limits and generic invalid-credential errors. Rotate session identity on login. `GET /auth/session` returns `{user: {id, login}, expires_at, csrf_token}` or 401. `DELETE /auth/session` revokes it and clears its cookie. Store only hashed opaque session tokens server-side. No auth token is exposed in URLs or persisted by the browser app.

Confirm D01 cookie lifetime/SameSite and deployment in S01; these routes and response DTOs must change before publication if bearer/OIDC is selected. CSRF protection applies to login and all state-changing cookie requests, not just profile updates. Exclude session/password responses from caches and logs.

`Profile` contains `id`, `version`, `created_at`, `updated_at` and the following nullable user-owned properties; `PATCH /me/profile` accepts a subset plus required `version`:

| Property | Type and rule |
| --- | --- |
| `name`, `kannada_name`, `phone`, `village`, `taluk`, `district`, `state` | Strings or null; phone is contact data, not proof of identity. No region/name defaults. |
| `soil_health_card_no` | String or null; a contact-level external reference, not a verified field sample or globally unique key. |
| `farmer_category` | `small_marginal\|medium\|large\|null`, as selected by the user; not automatically inferred from one field's area. |
| `preferred_language` | `en\|kn\|null`; UI locale preference, not agricultural evidence. |
| `risk_tolerance` | `conservative\|balanced\|progressive\|null`. |
| `primary_objective` | `profit_maximization\|low_water_risk\|household_security\|null`, matching actual HTML options. Legacy `food_security`/`low_risk` need explicit user-confirmed migration, not guessed equivalence. |

Provision an empty profile with the account so GET returns 200; it must not contain a demo farmer. Profile preferences affect a recommendation only if its documented method supports them; reject unsupported objectives rather than silently ignoring them.

### 4.2 Fields and two-stage imports

`FieldCreate` requires `{name, geometry: Polygon|MultiPolygon}` and may include `district?`, `taluk?`, `village?`, `survey_number?`, `reported_area?: Quantity`, `reported_context?: {water_source?, irrigation_method?, water_availability?, soil_description?, previous_crops_text?}`. Reported context is an auditable user submission, not accepted observations. S01 freezes lengths/category constraints; arbitrary scientific fields in the create body are forbidden.

`Field` returns `id`, `version`, `geometry_version`, `status: active|archived`, input name/location metadata, full `geometry`, `representative_point`, `bbox`, server-derived `area: {hectares, acres, guntas}`, `perimeter_m`, `area_method`, `validation_notes`, reported context, `created_at`, `updated_at`. The registered area converter uses 1 acre = 4046.8564224 square metres, 1 hectare = 10000 square metres and 40 guntas per acre; do not round stored area to whole guntas. `PATCH` accepts mutable input fields, optional `status` and required `version`; geometry changes create a boundary revision, never a new field ID. Reassess dependent results as stale without rewriting stored runs.

Fields are owned by the authenticated actor or an explicit role, not by geometry alone. An identical shape in another account must not merge or reveal records. Project context is server-resolved for this UI; do not invent a required project selector absent from the frontend. Authorize any later explicit project selection separately.

The old irrigation dropdown mixes **source** (`rainfed/borewell/canal`) and **method** (`drip/sprinkler`). Split it into two controls. Existing labels may be retained as reported text if source/method is not known; never infer reliable perennial water from `borewell`. Soil depth categories are descriptions, not sample-depth measurements.

Import lifecycle:

1. `POST /boundary-imports` accepts multipart `file` (KML/KMZ). Return a durable parsing job, not fields. Validate size, expanded archive size, paths, entry count, XML entities/external access and geometry limits using configured documented bounds.
2. `GET /boundary-imports/{id}` returns `{id, version, job_id, status: processing|ready|failed|blocked|confirmed, source_asset_id, candidates: [{id, name, original_geometry, proposed_geometry, repair_required, validation_notes, area}], field_ids, expires_at}`. Candidate IDs are stable within the immutable preview; `area` is server-derived. Never fetch remote KML links.
3. `POST /boundary-imports/{id}/confirm` accepts `{version, selections: [{candidate_id, name?, accept_repair: boolean}]}` and an idempotency key. Confirm only a ready, unexpired, owner-authorized preview. Commit selected fields/boundaries/roles atomically; response is `{import_id, fields: Field[]}` with 201. Preview is bounded; larger imports require an explicit batch limit/error, not silent truncation.
4. Any repair requires consent; even valid multi-field imports require selection/confirmation. Stale preview, already changed selection or expired preview returns 409; exact idempotent replay returns the original fields. No partial committed selection after failure.

### 4.3 Records and accepted analysis

`POST /fields/{id}/records` accepts `{kind: soil|water|management, reported_at, sample_date?, depth_top_cm?, depth_bottom_cm?, report_asset_id?, external_report_id?, laboratory_name?, measurements: [{variable_id, original_value, original_unit, measurement_basis?, method?, source_record_locator?}], context?}`. Validate `context` against a kind-specific schema; it is not arbitrary JSON. Accept an authorized report uploaded through `/record-assets`, or preserve the authenticated submission itself as immutable surveyed evidence.

Unknown metadata may allow an **unverified submission**, not an accepted observation. A laboratory-acceptance path additionally needs the real report/sample/collection metadata required by the variable registry. Add date, sample depth, report attachment and nutrient-method/basis inputs to the existing soil form. Never replace sample date with submission time, truncate decimal N/K values, or accept browser `hasSoilTest=true` as verification.

`Record` contains `id`, `version`, `field_id`, `kind`, original submission and asset references, `validation_status`, `validation_results`, `accepted_observation_ids`, `created_at`, `updated_at`. Corrections through `PATCH /records/{id}` create a new revision and preserve the original; ownership is checked through the field. A linked accepted observation is not mutated in place.

`FieldAnalysis` contains `field_id`, `geometry_version`, `as_of`, `soil`, `water`, `climate` and `feature_status`. Each mapped scientific property below is a `Metric<T>`, not an unqualified scalar. `soil` additionally has `record_id`, `laboratory_name`, `external_report_id`, `sample_date` and server-derived `verification_status`.

- `soil`: `texture`, `effective_depth`, `drainage`, `ph`, `electrical_conductivity`, `organic_carbon`, `available_nitrogen`, `available_phosphorus`, `available_potassium`; include published/validated interpretation separately from the value, with `method_id`.
- `water`: `source_description`, `reliability`, `borewell_depth`, `flow_rate`, `irrigation_cost`, `quality_summary`. Preserve ambiguous "inches" as reported text on its Record; return unavailable flow rate until a real flow measurement/basis exists.
- `climate`: `region_name`, `agro_zone`, `annual_rainfall`, `seasonal_rainfall`, `dry_spells`, `drought_classification`; each aggregate declares date/reference range and method. No district fallback or assumption that one year's data is a climate normal.
- `feature_status`: references the complete Section 4.3 records, including missing requirements. Paginate complete detail separately; do not inline an unlimited observation series.

Canonical carbon is g/kg; percent display is g/kg divided by 10 with the registered conversion. Preserve original report units. Nutrients remain available/total and elemental/oxide quantities as reported: mg/kg cannot become kg/ha without compatible depth/density and method. Borewell depth in metres may have an explicit server-supplied feet display conversion. Irrigation cost includes currency, observed date and actual per-hour/per-area/other basis; never relabel annual cess as hourly cost.

`GET /fields/{id}/observations` and `/feature-status` return complete paginated domain records conforming to backend Sections 4.2/4.3. Filters: `variable_id`, `source_binding_id`, `period_start`, `period_end`, `depth_top_cm`, `depth_bottom_cm`, `availability` where applicable. Results order by context time, variable and ID; cursor rules handle nullable times.

### 4.4 Scenes, charts and forecasts

`Scene` contains `id`, `field_id`, `geometry_version`, `provider_scene_id`, `satellite`, `acquired_at`, `spatial_resolution_m`, `cloud_cover_percent`, `valid_area_percent`, `source_refs`, `indices: {ndvi, ndmi}` as metrics, `canopy_interpretation` as a metric, and available overlay references. Scene metadata describes a real source asset even if its analytical values fail quality checks.

`GET /fields/{id}/scenes/{scene_id}/overlay?layer=ndvi|ndmi|truecolor` returns `{field_id, scene_id, geometry_version, layer, availability, reason, rendering: raster|field_summary|null, image_url: string|null, bounds: bbox|null, legend: object|null, expires_at: timestamp|null, source_refs}`. For v1, use a bounded server-rendered georeferenced image and authorized Blob fetch rather than designing a new tiled image server. A field-summary renderer must label itself as such and cannot claim intra-field raster variation. Provider basemap imagery remains unrelated to the selected analytical scene.

Overlay GET reads metadata for an existing asset; acquisition/processing jobs produce the image. If absent, return `not_collected` with no image URL rather than holding the request open to render it. `image_url` points to the relative route `/api/v1/fields/{id}/scenes/{scene_id}/overlay/image?layer=...`, which rechecks authorization and serves a bounded PNG with the same geometry/scene/layer version. Overlay legend/bounds schemas must be frozen before frontend F06.

The UI calls its layer "NDWI Canopy Moisture" but the source/product and formula are not specified. Under D04, use the explicitly registered canopy-moisture NDMI definition and rename the control; if retaining NDWI instead, register its exact bands/formula and separate variable ID. Never silently rename one index's values as another.

`GET /fields/{id}/vegetation-series` requires `period_start`, `period_end`, `index=ndvi|ndmi`; returns paginated points `{observed_at, scene_id, mean, median, minimum, maximum, cloud_cover_percent}` with each statistic a Metric, plus explicit `gaps`. Rainfall is a separate `/climate-series` response with `{period_start, period_end, precipitation}`. Plot both on actual time axes; do not invent rainfall at scene instants, connect across missing intervals, clip negative NDVI to zero, or index into an empty array. One valid point is a valid non-line chart state.

`GET /fields/{id}/forecast` returns `{field_id, availability, reason, issued_at: timestamp|null, provider_model: string|null, source_refs, freshness, intervals: [{valid_from, valid_to, temperature, wind_speed, precipitation, condition}]}`. Numeric and condition fields are metrics. Forecast products must have issue and validity times; a returned empty unavailable forecast cannot be labelled current weather. Current frontend static forecast text is a required migration target, not evidence of a working feed.

### 4.5 Crops and recommendations

`Crop` contains `id` (species), `name`, `kannada_name: string|null`, `scientific_name`, `category: string|null`, `cultivars: [{id,name}]`, `source_refs`, and applicable `requirements`, `risks`, `guidance`, `calendars` with versioned metrics/references. The old `ragi-gpu28`-style IDs conflate species/cultivar; migrate with an explicit lookup, not by parsing slugs or treating all popular varieties as the selected cultivar.

`RecommendationCreate` requires `{field_id, geometry_version, season: kharif|rabi|summer|any, season_year: integer, period_start: date, period_end: date, objective, risk_tolerance, price_delta_pct: number, cost_delta_pct: number}` and permits `crop_ids?`, `cultivar_ids?`, `cultivated_area?: Quantity`. Objective/risk enums match Profile. Current slider bounds are price [-30,30], cost [-25,25]; preserve these proposed input bounds, but keep step-size a UI detail. Require explicit values; zero is a user-selected no-adjustment control, not a fabricated price.

`POST /recommendation-runs` always queues a durable job. `GET /recommendation-runs/{id}` returns `id`, `job_id`, `field_id`, `geometry_version`, immutable `inputs`, `method_version`, `input_versions`, `created_at`, `evaluated_at`, `availability`, `reason`, `counts`, `suitable`, `excluded`, `unavailable`, and `freshness`. Each result item contains `id`, `crop_id`, `cultivar_id`, a crop summary, `agronomic_status`, nullable `rank/score`, `matches`, `warnings`, `exclusions`, `missing_inputs`, `source_refs`, and `financials`.

Do not force a 0-100 score or profit ordering without a validated method for the requested objective. Missing required inputs yield `unavailable`, not `excluded`. Fully evaluated unsuitable crops are excluded. An agronomically suitable crop can have unavailable economics; return that distinction. Freeze required inputs and objective behavior per method in S01/S07/S10; if unsupported, reject/mark blocked, never run a different objective silently.

`financials` contains `availability`, `reason`, `area`, `currency`, `cost_items`, and `scenarios: {expected, pessimistic, optimistic}`. Each scenario has availability/reason and metric-valued `yield_per_area`, `total_yield`, `price_per_quantity`, `cost_per_area`, `total_cost`, `gross_per_area`, `net_per_area`, `total_gross`, `total_net`, `benefit_cost_ratio`, with `assumption_refs` and `method_id`. Missing scenarios remain explicitly unavailable.

Cost-item codes cover the current UI's land preparation, seeds, manure, fertilizers, sowing/transplanting, weeding/intercultivation, plant protection, harvesting/threshing and post-harvest transport, plus any authentic additional items. Each item retains amount, currency, area/quantity basis, time and source. Totals and displayed breakdown must use the same adjusted inputs; do not display unadjusted crop-catalog costs beneath an adjusted total.

Slider changes are explicit sensitivity assumptions applied by a documented server method to existing accepted baselines; they cannot create missing baseline data. Debounce submission and ignore outdated jobs/responses. Do not port the old 1.08/0.8/1.2 multipliers or copy "-20% yield"/"+15% yield" captions unless supported by the returned scenario definition. A scenario is a conditional calculation, not an observed agricultural record or a promised yield.

### 4.6 Market resources and economics

`Market` contains `id`, `name`, nullable localized name, district/taluk/location and provider identities/provenance. `Commodity` contains its own `id`, names, source codes and explicit crop/cultivar/grade associations. A market commodity is not automatically a cultivar.

`MarketObservation` contains `id`, `market_id`, `commodity_id`, nullable `grade/variety`, `observed_on`, `published_at`, metric-valued `minimum_price`, `modal_price`, `maximum_price`, `arrivals`, plus `source_refs`, `freshness` and optional `trend` with compared record IDs/period/method. Each price declares currency/quantity basis. A missing trend is unknown, not stable.

`SupportPrice` contains `commodity_id`, `grade`, `policy_type`, `marketing_season`, `effective_from/to`, metric-valued `price` and `source_refs`. Preserve MSP versus other support/fair-remunerative-price schemes; do not label every commodity's policy price as MSP. Never use a policy price as an observed market price.

`POST /economic-scenarios` requires `{field_id, market_observation_id, cultivated_area: Quantity, cost_record_ids: string[], yield_observation_ids: string[], assumptions: object}` with a registered assumptions schema. It queues a job and returns a persisted `EconomicScenario` through GET: IDs/input versions, availability/reason, quantity/currency basis, `deductions`, `farm_gate_price`, financial scenario metrics and source/assumption lineage.

Each deduction identifies its method (percentage of which base or amount per quantity), source, applicable dates and fee category. Include bagging, weighing, cess, transport rate and actual distance only when authentic inputs support them. Do not use mandi-global farm-gate deductions for every field or infer freight distance from unverified coordinates. Without field/cost context, market observations remain viewable but farm-gate realization is unavailable.

### 4.7 Plans, summaries and exports

`PlanCreate` requires `{field_id, crop_id, cultivated_area: Quantity, planned_sowing_date: date}` and permits `cultivar_id?`, `planned_harvest_date?`, `recommendation_run_id?`, `recommendation_item_id?`, `economic_scenario_id?`, `irrigation_strategy?`, `notes?`, `user_budget?: Money`. No client-generated profit/yield is accepted. Run and item references must belong together and match the authorized field/crop/cultivar/area; a mismatched or changed-area scenario must be recalculated, not silently reused.

`Plan` returns the inputs plus `id`, `version`, `status: draft|planned|archived`, `geometry_version`, `field_name`, crop/cultivar names, `created_at`, `updated_at`, `assumptions`, `financial_snapshot`, metric-valued `water_requirement`, referenced `risks` and `freshness`. Unknown harvest timing is null; published sowing/harvest windows remain separate from the user's intended date. A draft can lack economics, but no plan may claim unavailable financial metrics as zero.

`PATCH /plans/{id}` accepts mutable plan inputs plus version and explicit `status`. Create as `draft`; an explicit user action may move a valid draft to `planned` even when its economics are unavailable. Status expresses user intent, not agronomic approval or guaranteed profitability. Either active state may be archived; an archived plan is read-only in v1. Archive preserves history and references. Validate positive area after exact unit conversion and area not exceeding the selected field; do not guess a default acre. Under D03, overlapping independent plans are not automatically rejected or described as an optimized allocation.

`GET /dashboard?field_id=...` returns authorized total field count/area, server-derived verified-laboratory field count, active-plan preview and a reference to the latest matching persisted recommendation run. Recommendation counts/top returns are metrics or explicit unavailable states; a dashboard GET never launches scientific work. `GET /plans/summary` returns totals for the declared filter/currency and contributor/missing counts. Partial financial totals must be labelled partial; do not sum different currencies or treat missing values as zero.

`POST /exports` requires `{field_ids: string[], format: geojson|kml|kmz|bundle, run_id?, filters?}`. Authorize every selected field/run and declare whether the request is complete or explicitly filtered. Create a durable job; `GET /exports/{id}` returns readiness, manifest/checksum metadata and a relative authorized download URL. `GET /exports/{id}/download` returns the bytes with safe filename, MIME and `Content-Disposition`; fetch a Blob with the configured authentication, not a raw link that bypasses it.

Full bundle export follows backend Section 4. A frontend profile summary must not be advertised as the complete dataset. Snapshot geometry/version and request filters when the export is queued; recheck authorization at download. Do not expose raw filesystem paths or create reusable unprotected download URLs.

## 5. Concrete route checklist

All application routes below are prefixed `/api/v1`; all except CSRF/login/system metadata require authentication. Read routes enforce scope/ownership as well as write routes. Authenticated shared catalog access does not grant access to farmer reports.

| Methods and path | Request/response contract | Owning step / frontend phase |
| --- | --- | --- |
| `GET /meta` | API/schema version, capabilities and configured public limits; no secrets | S04 / F02 |
| `GET /auth/csrf`; `POST`, `GET`, `DELETE /auth/session` | Section 4.1 session lifecycle; POST 200, DELETE 204 | S04 / F02-F03 |
| `GET`, `PATCH /me/profile` | Profile; PATCH version required | S04 / F03 |
| `GET`, `POST /fields`; `GET`, `PATCH /fields/{id}` | Fields/FieldCreate; archive through PATCH status with version | S04 / F04 |
| `POST /boundary-imports`; `GET /boundary-imports/{id}`; `POST /boundary-imports/{id}/confirm` | Section 4.2 multipart/preview/confirmation | S03-S04 / F04 |
| `POST /record-assets` | Bounded multipart original report; 201 `{id,sha256,media_type,byte_size}`; authorized opaque ID | S05/S09 / F05 |
| `GET`, `POST /fields/{id}/records`; `GET`, `PATCH /records/{id}` | Kind-specific submissions and versioned records | S05/S08/S09 / F05 |
| `GET /fields/{id}/analysis`; `GET /fields/{id}/observations`; `GET /fields/{id}/feature-status` | Section 4.3; analysis accepts explicit optional period filters, no invented baseline | S05-S09 / F05 |
| `GET /fields/{id}/scenes`; `GET /fields/{id}/scenes/{scene_id}/overlay`; `GET /fields/{id}/scenes/{scene_id}/overlay/image` | Scene list: period/cloud filters; metadata/image check field-scene-layer relationship | S06 / F06 |
| `GET /fields/{id}/vegetation-series`; `GET /fields/{id}/climate-series`; `GET /fields/{id}/forecast` | Section 4.4; climate requires period bounds and `interval=day\|month\|season` with explicit season dates | S05-S06 / F05-F06 |
| `GET /crops`; `GET /crops/{id}` | Crop DTO; list filters season, region and query text; unknown requirements stay unavailable | S07 / F07 |
| `POST /recommendation-runs`; `GET /recommendation-runs`; `GET /recommendation-runs/{id}` | Section 4.5; list filters field, season/year, objective and status | S10 / F07 |
| `GET /markets`; `GET /commodities`; `GET /market-observations`; `GET /support-prices` | Section 4.6; filters market/commodity/grade/region/date or marketing season as applicable | S10 / F08 |
| `POST /economic-scenarios`; `GET /economic-scenarios/{id}` | Section 4.6; 202 job then immutable output | S10 / F07-F09 |
| `GET`, `POST /plans`; `GET /plans/summary`; `GET`, `PATCH /plans/{id}` | Section 4.7; list/summary use field, status and date filters | S10 / F09 |
| `GET /dashboard` | Section 4.7; selected-field context is optional when there are no fields | S04/S10 / F05 |
| `POST /fields/{id}/acquisitions` | `{source_binding_ids, variable_ids, period_start, period_end, fresh}`; bounded authorized requests only, 202 Job; no arbitrary provider URLs/paths | S04-S09 / F05-F06 |
| `GET /jobs/{id}`; `GET /jobs/{id}/validation` | Job and paginated case evidence/coverage for its authorized subject | S04 onward / F02-F09 |
| `POST /exports`; `GET /exports/{id}`; `GET /exports/{id}/download` | Section 4.7; creation 202, metadata 200, download appropriate binary MIME | S04/S11 / F04 onward |
| `GET /provenance/assets/{id}` | Authorized publisher/product/version/checksum/record metadata; no local path or unrestricted original report access | S04 onward / F05-F09 |

Ordering: fields/plans/catalog/markets by `(created_at,id)` or a declared immutable `(name,id)` catalog key; observations/scenes/market records by `(context_time,id)`; runs/jobs by `(created_at,id)`. Freeze exact null/time and snapshot cursor handling in OpenAPI before client pagination. Register static `/plans/summary` before a dynamic ID route. Every optional filter listed here must have a schema; unimplemented filters are not ignored.

Durable jobs must be claimed by a separate worker using transactional database ownership/leases, heartbeats and bounded retries. Store request, actor, input versions and pending resource identity before returning 202; persist actual results when the worker produces them. Each 202 `resource_refs` contains the already-allocated import/run/scenario/export ID so the client can retrieve its pending state immediately; `Location` points to the job. A restarted API must still find both. Never rely solely on FastAPI in-process background tasks for source acquisition. Provider failure records the exact blocker; a partially successful required run is not `complete`. Readiness verifies local service/schema configuration, while worker health and source capabilities remain separately visible.

## 6. Frontend field-to-API mapping

These M IDs are the required S01/F01 audit checklist. Dotted properties are DTO properties from Section 4; adapt them to the old names only at the frontend boundary. Do not recreate seeded objects to satisfy unchanged render functions.

| ID / consumer | Existing fields / UI values | API source and required adaptation |
| --- | --- | --- |
| M01 Profile/header | `name`, `kannadaName`, `phone`, `soilHealthCardNo`, village/taluk/district/state, `farmerCategory`, `preferredLanguage`, `riskTolerance`, `primaryObjective` | Profile fields in 4.1. Save category; preserve language/state even if no editable control. Remove appended invented initials and region defaults. |
| M02 Field selector/parcel details | `id`, `name`, location, `surveyNumber`, `boundary`, `coordinates`, `areaAcre`, `areaHectares`, `areaGuntas` | Field ID, metadata, geometry, representative point and area. Replace first-ring map code; list pagination cannot hide owned fields. |
| M03 Add-field form | name/location/survey, acres, irrigation type, water availability, soil texture, previous-crop text | FieldCreate; acres are reported, not authoritative. Split source/method; retain user soil/crop text as surveyed context. Geometry required under D03; no generated district box. |
| M04 Soil form and lab badge | `hasSoilTest`, `cardNo`, `labName`, `testDate`, texture/depth/drainage | Record submission plus analysis verification/sample metadata. Add authentic collection date, depth, attachment, method and basis; no browser verification flag. |
| M05 Soil values/interpretations | `ph`, `electricalConductivity`, `organicCarbonPct`, `nitrogenKgHa`, `phosphorusKgHa`, `potassiumKgHa`, status labels, `waterHoldingCapacity` | Analysis metrics and feature detail. Units/basis cannot be assumed; interpretations and water-holding capacity require independent methods/evidence or unavailable display. |
| M06 Water audit | source/reliability, `borewellDepthFt`, `groundwaterYieldInches`, `irrigationCostPerHour`, `waterQuality` | Water analysis plus original Record. Correct ambiguous yield unit and cost basis; no default depth, flow, quality or cost. |
| M07 Climate analysis | district/agro-zone, annual/Kharif/Rabi rainfall, dry spells and drought | Climate analysis metrics with explicit reference period/season/region; never select the Tumakuru baseline for an unknown district. |
| M08 My Land scene/sidebar/overlay | pass ID/date/formatted date/satellite/resolution/cloud, NDVI/NDWI, canopy condition/interpretation/anomaly | Scenes and overlay. Date formatting is presentation; selected scene/geometry must match. Anomaly needs actual baseline lineage; NDWI decision per 4.4. |
| M09 Vegetation drawer | date/cloud, mean/median/min/max NDVI, rainfall bars | Vegetation and climate series with actual dates and intervals; retain gaps, negative valid NDVI and empty/single-point states. |
| M10 Static cockpit controls/forecast | fixed date range, "Max Cloud", weather condition, issue/valid times, temperature/wind | Implement controls using queried periods/cloud filter; forecast DTO. Remove static meteorological values from HTML. |
| M11 Crop selector/cards | crop ID, names/scientific name, popular varieties, category, season/duration/windows, soil/water/climate requirements, pest risks and local guidance | Crop/cultivar and versioned requirements/calendars/risks. Provenance mandatory; no first-variety default or unsourced advice. |
| M12 Recommendation ranking | plot context, season, suitable/disqualified counts, score, matches/warnings/disqualifiers, evaluated time | RecommendationRun groups and metrics; add unavailable outcomes, season year/dates, objective/risk inputs and run identity. Cancel stale render updates. |
| M13 Financial cards/sliders | price/cost delta, expected/pessimistic/optimistic yields/prices/costs/gross/net/BCR, itemized costs | Recommendation financials / EconomicScenario. Remove browser financial calculations, false scenario captions and guaranteed-profit language. |
| M14 Market grid/filter | commodity/crop name, mandi ID/name, min/modal/max price, arrivals, unit, data source, trend | Markets, commodities and market observations; pills use returned IDs; choose by declared observation date/order rather than `reports[0]`. |
| M15 Market support/farm-gate | MSP, cess percent, bagging/weighing, transport distance/rate, estimated farm-gate price | SupportPrice and EconomicScenario. Policy and observations separate; calculations require field-specific authentic inputs. Static HTML fee explanation must match returned method or be removed. |
| M16 Plan form/cards | plot/crop IDs/names, acreage, sowing/harvest, budget/gross/net/scenarios, water strategy, risks/status/created date | Plan DTO and immutable referenced financial snapshot. ISO intended dates, explicit cultivar/run/item, version conflicts and archive flow. Unknown economics remain null. |
| M17 Dashboard/plan totals | field count/area, verified count, suitable crops, top return, active previews, missing-soil alert, plan budget/profit/buffer | Dashboard and plan summary, not a sum of a paginated subset. Alert from real validation/availability; never claim "100% accurate" calibration. |
| M18 Exports and reset | browser GeoJSON/KML, generated filenames, reset-demo button, storage records | Export jobs/downloads; authorized complete geometry/lineage. Remove demo reset; D02 governs any user-data migration. |

Decorative icons/colors/layout/chart dimensions and labels may remain local. Fixed agricultural values in `index.html` are not harmless placeholders: replace them with empty/loading elements before API bootstrap so they cannot flash as real data. Static copyright or interface copy is not a scientific dataset.

## 7. Ordered branch handoff and acceptance

1. **S01 / frontend F01:** approve D01-D05; resolve first-slice DTO constraints and registry bindings; generate `docs/openapi.json` and `config/frontend_field_mapping.yaml` from this contract. The mapping records each M ID, consumer/property, operation/schema property, unit/derivation rule, availability policy and owning task. Commit the same versioned OpenAPI artifact on both branches, recording its checksum; no runtime shared filesystem is required. Do not invent sample success records.
2. **S02-S04 / F02-F04:** implement and connect session, profile, fields, real import preview/confirmation, jobs and exports. Provide authentic response evidence for these routes. Add login and no-fields screens. Gate unmigrated screens as unavailable; frontend F02's old instruction to retain seeded data applies to neither a production build nor acceptance.
3. **S05-S09 / F05-F07:** deliver individual accepted soil/weather/scene/crop slices through the same schemas. Each frontend screen is migrated only after its route is ready; missing scientific fields remain explicit. Implement forecast/market-specific sources rather than pretending existing scripts supply them.
4. **S10 / F07-F10:** implement accepted-input recommendations, economic scenarios, market resources, plans, then remove remaining data modules, synchronous storage and browser scientific rules. Keep financial pages blocked wherever source evidence is absent.
5. **S11-S12 / F11:** run actual API/browser/PostGIS acceptance and independent production build/deployment; reconcile all values and full exports. Report route readiness separately from complete scientific coverage.

For each operation: validate schema, authorization, actual database persistence, real positive data when applicable, unavailable state and defined failures. Include these concrete regressions alongside backend API/WEB cases:

| Regression | Existing failure to prevent | Evidence |
| --- | --- | --- |
| Zero owned fields; expired session | Current bootstrap and dashboards assume a plot exists | API-02/08/12, WEB-03/07/13 |
| Zero, negative index, null and missing data | `\|\|` substitutes real zeros; chart clips NDVI and assumes data length >=2 | API-08, WEB-07 |
| Field/scene change while requests finish | Global series and selected pass do not identify actual data | API-05/12, WEB-08; assert field/scene/geometry IDs |
| Holes/MultiPolygon and repair refusal | First-ring-only map/export and no import confirmation | API-06, GEO-07, WEB-06 |
| Soil submission without date/basis/report | Form falsely asserts laboratory verification | API-08, FEAT-01/06/09 |
| Profile category/objective roundtrip | Unsaved category and conflicting objective vocabulary | API-05/07, WEB-05 |
| Changed field area or scenario before plan commit | Stale run/area reuses unrelated economics | API-07/09, WEB-09/11 |
| Paginated fields/plans/markets | Current array sums and first-report selection misstate totals | API-10/11, WEB-10/11 |
| Forecast versus historic weather; MSP versus observed price | Plausible values have the wrong scientific meaning | Q04/Q17, API-08/10 |
| API/worker restart, repeated upload, stale confirmation | In-process tasks/duplicate POSTs cannot guarantee persistence | API-06/07/11, DB-03/06/07 |
| Separate origins, direct download and unauthorized asset IDs | CORS alone is not authentication or authorization | API-03/04, WEB-04/15 |
| Fresh browser before first response; backend offline | Static HTML or local seeds masquerade as real results | API-12, WEB-13/14 |

Use authentic agricultural records for positive/negative scientific cases. Do not manufacture readings, boundaries, missing observations or provider responses for tests; report unavailable authentic cases as blocked. Empty-resource, expired-session, invalid-input and transport tests may exercise real application state without fabricating agricultural data. Pure UI formatting and transport-state checks do not establish real-data acceptance.

The existing frontend has only `dev`, `build`, `preview`; it has no test command. Add test tooling with the phase that uses it. Run its current build when code changes, then the new focused client/adapter/browser selectors. Documentation review is not evidence that these future commands, routes, source products or authentication assumptions work.
