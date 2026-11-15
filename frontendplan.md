# Agriculture Intelligence Frontend — Backend Integration Plan

## 1. Goal and boundaries

Rewrite the existing Vite/Leaflet frontend so it remains an independently built and deployed web application while retrieving and mutating required data through the backend's versioned HTTP API.

The frontend and backend must remain separate instances:

- The frontend is a static Vite build deployable from its own host and port.
- The backend is a separately deployed API and PostgreSQL/PostGIS service.
- The frontend knows the backend only through a configured API base URL and a versioned OpenAPI contract.
- The frontend must not import backend Python modules, connect directly to PostgreSQL, read backend files, or require both repositories to share a filesystem.
- The backend must not serve as the frontend's source tree or build system. It may optionally serve the already-built static artifact in a combined deployment, but that is not the primary architecture and must not be required.

The rewrite preserves the current screens and interaction model where the underlying backend supports them: dashboard, My Land, land analysis, crop recommendations, market intelligence, planting plans and profile management.

## 2. Non-negotiable data rules

1. Remove production use of hardcoded farmer, plot, soil, water, satellite, climate, crop, market, recommendation and planting-plan values.
2. Do not fall back to plausible defaults when an API request fails or a field is missing. Render `loading`, `empty`, `unavailable`, `blocked`, `stale` or `error` explicitly.
3. Static interface copy, select-option labels, icons, colors and layout configuration may remain bundled. Scientific, geographical, financial and user-specific values must come from the backend.
4. Browser storage may hold non-sensitive UI preferences such as the selected tab or display language. It must not be the authoritative repository for profiles, fields, soil records, recommendations or plans.
5. The frontend may calculate presentation-only values such as formatting, chart coordinates and visible totals from API-provided records. Scientific normalization, field area, data validation, recommendations and financial outputs remain backend responsibilities.
6. Every displayed scientific or financial value must retain enough response metadata to expose its unit, observation/reference period, quality or availability state and source where the screen calls for it.
7. Never put provider credentials, database credentials, JWT signing keys or other backend secrets into Vite environment variables or the browser bundle.

## 3. Current hardcoded behavior to replace

| Current file/behavior | Required replacement |
| --- | --- |
| `src/services/storageService.js` seeds and persists farmer profiles, plots and planting plans in `localStorage`. | API repositories for profile, fields and planting plans. Keep only optional UI preferences in local storage. |
| `src/data/karnatakaCrops.js` contains crop requirements, risks, costs, yields and prices. | Crop/reference catalog endpoints with source and version metadata. Remove the production data module after all consumers migrate. |
| `src/data/marketData.js` contains mandi and commodity prices. | Market endpoints returning authentic observations, timestamps, currency, quantity basis, source and freshness. |
| `src/data/environmentalData.js` contains climate baselines, satellite passes and NDVI time series. | Field analysis, climate, satellite-scene and vegetation-series endpoints with quality and availability metadata. |
| `src/services/recommendationEngine.js` runs recommendations and financial scenarios locally. | Backend recommendation endpoints returning a persisted, versioned run with explanations and missing-input states. |
| `src/data/agriZones.js`, `mandyaData.js` and `sensorStations.js` contain additional bundled domain records. | Remove if unused; otherwise map each active UI consumer to an API resource before deleting the module. Do not leave dormant production datasets that can later be used accidentally. |
| `Date.now()` creates plot and plan IDs. | Backend-generated stable IDs returned by create requests. |
| `Math.random()` can create a soil-card number. | User-supplied or backend/imported external identifier. Never fabricate it. |
| New plots without drawn geometry receive a generated district rectangle. | Require geometry or create an explicit non-spatial draft supported by the backend. Never invent a field boundary. |
| Browser code estimates authoritative field area. | Use the browser estimate only while drawing and label it as provisional; replace it with the PostGIS-calculated area after saving. |
| Render functions use values such as `soil.ph || 6.6` and a Tumakuru climate fallback. | Null-safe view models and explicit unavailable components. Use nullish semantics only for display, never to inject a scientific value. |
| GeoJSON/KML exports are assembled entirely in the browser. | Request authorized backend exports so geometry versions, holes, MultiPolygons and provenance remain correct. |
| User-controlled strings are interpolated into `innerHTML`. | Safe DOM construction or a single audited escaping layer before rendering API/user content. |

Before implementation, use `rg` to produce a checked inventory of every literal domain value, `localStorage` call, data-module import, fallback expression, generated identifier and direct `innerHTML` interpolation. Keep this inventory in the migration checklist until each item is removed or explicitly classified as static UI configuration.

## 4. Target frontend architecture

Use native browser `fetch`; Axios is not required. Centralize transport behavior instead of calling `fetch` from render functions.

```text
src/
  api/
    client.js              # base URL, auth mode, timeout/abort, JSON parsing
    errors.js              # stable API error model
    profileApi.js
    fieldsApi.js
    analysisApi.js
    cropsApi.js
    recommendationsApi.js
    marketsApi.js
    plansApi.js
    exportsApi.js
  adapters/
    profileViewModel.js
    fieldViewModel.js
    analysisViewModel.js
    recommendationViewModel.js
    marketViewModel.js
    planViewModel.js
  state/
    appState.js            # data plus loading/error/request status per resource
    actions.js             # async orchestration and request cancellation
  views/                   # split current main.js render/event responsibilities
  map/                     # Leaflet setup, drawing and API geometry adapters
  config.js                # validated public runtime/build configuration
  main.js                  # application bootstrap only
```

This layout is a target boundary, not a requirement for one large rewrite. Move one vertical feature at a time while keeping the app buildable. Avoid introducing a UI framework solely for this migration unless a separate decision documents the benefit and conversion cost.

### 4.1 API client rules

- Read the base URL from `VITE_API_BASE_URL` or a documented runtime configuration file. Fail startup with a clear configuration screen if it is absent in a production build.
- Prefix application calls with `/api/v1`; never scatter full endpoint URLs through view code.
- Apply one authentication strategy consistently. For secure cross-origin cookies use `credentials: "include"`, backend allow-listed origins and CSRF protection as required. For bearer tokens, define secure acquisition, memory/storage, expiry and refresh behavior with the backend; do not improvise token storage in individual modules.
- Add an `AbortController` timeout and cancel superseded requests when the active field, season or filter changes.
- Retry only documented transient failures and only when the operation is safe or has an idempotency key. Never automatically retry an ambiguous create/update.
- Parse success, validation, authorization, conflict, rate-limit and server-error responses into stable frontend error objects.
- Attach/request a request ID for diagnostics without exposing secrets.
- Validate critical API response shapes at the boundary. Prefer generated OpenAPI types/client metadata or a small runtime schema layer; do not spread unchecked property access across render code.

### 4.2 State and rendering rules

Each remote resource stores data and status separately:

```js
{
  status: "idle" | "loading" | "ready" | "empty" | "error",
  data: null,
  error: null,
  receivedAt: null
}
```

Views must render all states deliberately. A previous successful response may remain visible during refresh only when clearly marked as refreshing or stale. Changing the active field must invalidate or refetch field-scoped resources so one field's analysis cannot appear under another field's name.

View-model adapters convert API resources into UI-ready structures but must not create missing scientific values. Formatting currency, units and dates is allowed; assigning a default pH, yield, price, NDVI or climate baseline is not.

## 5. API contract required by the frontend

Freeze exact paths and schemas with the backend OpenAPI artifact before migrating each screen. The following resource map defines required capabilities; exact paths may change once, during the contract step, but must then be versioned.

| Frontend journey | Required backend capability |
| --- | --- |
| Session bootstrap | Current authenticated user/session plus API/schema version. |
| Profile | Get and update the current farmer profile with validation and concurrency/version metadata. |
| Plot selector/dashboard | List owned fields with authoritative area, representative point, geometry summary, soil-status summary and available recommendation/alert counts. |
| Add/draw plot | Create a field from GeoJSON, return server ID and authoritative geometry metrics, and report validation/repair results. |
| KML/KMZ import | Multipart upload, import preview/validation and explicit confirmation if repair or multiple fields are involved. |
| My Land | Fetch full authorized field geometry, latest valid satellite summary, available scenes/passes and overlay metadata. |
| Land analysis | Fetch soil, water and climate summaries plus availability, source, unit, quality and observation/reference dates. |
| Vegetation chart | Fetch field-scoped NDVI/other index series with scene dates, cloud/quality flags, units/index definition and gaps. |
| Crop recommendations | Submit field, season and optional scenario inputs; retrieve suitable, excluded and unavailable results with explanations, input versions and recommendation-run ID. |
| Market intelligence | Query observations by crop/commodity, mandi/region and date; return min/modal/max price where authentic, arrivals, units, currency, source and freshness. |
| Planting plans | List, create, update and archive plans with server IDs, field/crop references, dates, acreage, recommendation reference, assumptions and version. |
| Exports | Download backend-generated GeoJSON, KML/KMZ or complete field profile with authorization and safe filename handling. |
| Jobs/refresh | Poll long-running import/acquisition/recommendation jobs and render queued, running, failed, blocked and complete states. |

Do not design screen-specific endpoints that return HTML. The API returns versioned data resources; the frontend owns presentation.

## 6. Implementation sequence

Every phase ends with a build and its listed acceptance gate. Do not retain a hardcoded production fallback as a migration shortcut. If a backend capability is unavailable, keep that screen in an honest unavailable state until the contract is implemented.

### F01 — Freeze inventory and API contract

- Inventory all hardcoded/domain values and current consumers.
- Map every screen field to an API property, user-entered value, derived presentation value or static UI label.
- Obtain/commit the backend OpenAPI artifact and define versioning/error/availability conventions.
- Decide authentication and cross-origin deployment behavior.
- Define supported Node/npm versions and environment configuration.

Exit gate: no current data field is unmapped; sample authentic responses exist for each ready backend resource; missing backend capabilities are explicit blockers.

### F02 — Add transport, configuration and remote state foundations

- Implement `config.js`, the centralized API client, errors, authentication handling and resource-state helpers.
- Add global startup, unauthorized, offline and backend-unavailable experiences.
- Add request cancellation and stale-response protection.
- Keep current screens on existing data temporarily, but prohibit new direct data-module imports.

Exit gate: client tests cover success, validation error, unauthorized, conflict, timeout, abort, malformed response and unavailable backend; a production build points only to configured API origins.

### F03 — Migrate authentication and profile

- Bootstrap the session before user-specific requests.
- Replace `storageService.getProfile/saveProfile` with profile API actions.
- Handle save validation, unauthorized state and optimistic-concurrency conflicts.
- Render user text safely.

Exit gate: profile data survives refresh and a new browser process because it is read from the backend; no profile data is auto-seeded or persisted as the authority in `localStorage`.

### F04 — Migrate fields, drawing and geographical import/export

- Replace local plot reads/writes with field APIs.
- Send drawn GeoJSON to the backend and replace the provisional browser area with the authoritative response.
- Add KML/KMZ import flow with validation/repair feedback.
- Replace generated IDs and generated district rectangles.
- Replace local export assembly with backend downloads.
- Keep Leaflet as the map/rendering library and adapt backend GeoJSON to it.

Exit gate: create, read, update, archive, draw, import, select, refresh and export pass for Polygons, holes and MultiPolygons; cross-user field access is denied by the backend and handled by the UI.

### F05 — Migrate dashboard and land analysis

- Fetch dashboard summaries and field-scoped soil, water and climate resources.
- Replace all numeric fallback expressions with availability-aware components.
- Display unit, date/period, quality/source and stale state where relevant.
- Ensure active-field changes cancel or ignore older responses.

Exit gate: no dashboard or land-analysis scientific value comes from bundled modules or fallback constants; missing and rejected data cannot look verified.

### F06 — Migrate satellite/vegetation data

- Fetch scene/pass metadata and vegetation time series for the active field.
- Preserve gaps and quality/cloud flags in charts rather than interpolating them in the browser.
- Keep tile-layer configuration separate from analytical raster/index data.
- Render tile/font network failure separately from backend analytical-data failure.

Exit gate: selected scene, displayed overlay metadata and chart values reconcile with API responses after field and scene changes.

### F07 — Migrate crop catalog and recommendations

- Replace `karnatakaCrops.js` consumers with crop/reference APIs.
- Replace `recommendationEngine.js` execution with recommendation-run creation/retrieval.
- Render suitable, excluded and unavailable groups from backend results.
- Preserve explanations, input versions, uncertainty and run ID.
- Send sensitivity/scenario controls as explicit inputs; display backend-computed outputs only.

Exit gate: the browser contains no agronomic decision rules, default soil/climate inputs, yield assumptions, price assumptions or profitability calculations; a repeated run is traceable to the backend.

### F08 — Migrate market intelligence

- Replace `marketData.js` with filterable market API calls.
- Display observation time, source, currency, quantity basis and freshness.
- Distinguish no observation, stale observation and request failure.
- Do not recompute or label farm-gate prices unless the backend returns a traceable calculation and assumptions.

Exit gate: every displayed price and arrival value reconciles with an API record and stale/missing data cannot appear current.

### F09 — Migrate planting plans

- Replace local plan CRUD with backend plan APIs.
- Use server IDs, versions and field/crop references.
- Handle validation, stale-version conflict, archived state and deleted/changed referenced data.
- Preserve the recommendation run and financial assumptions used to create a plan.

Exit gate: plans persist across browsers/processes, concurrent updates cannot silently overwrite one another, and no plan depends on local seeded crop or financial data.

### F10 — Remove legacy data paths and split the application

- Remove production imports of `storageService.js`, `recommendationEngine.js` and migrated data modules.
- Remove reset-demo-data behavior from production.
- Remove random identifiers, generated soil cards, generated field rectangles and scientific fallback constants.
- Split the current `main.js` into API/state/view/map modules without changing behavior unnecessarily.
- Search the built bundle and source tree for retired seed names and representative hardcoded domain values.

Exit gate: the hardcoded inventory is empty except approved static UI configuration; disabling the backend yields honest unavailable/error screens rather than demo data.

### F11 — Test, secure and deploy independently

- Add unit tests for client, adapters, state transitions and safe rendering.
- Add OpenAPI compatibility checks.
- Add browser tests for all seven views and failure/empty/loading/conflict paths.
- Build the frontend independently and run it against a separately started backend URL.
- Document exact frontend origin(s), backend CORS allow-list, authentication transport, CSP and external tile/font requirements.
- Verify Tailscale/LAN access does not hardcode one machine's IP into the source or bundle.

Exit gate: all Section 8 cases pass from clean installs and separate processes; deployment requires only the static frontend artifact, public configuration and network access to the API/tile/font hosts.

## 7. Dependency plan

Current runtime/build dependencies are sufficient to render and build the present app: Leaflet and Vite resolve successfully. Do not add Axios merely to make HTTP requests.

Add dependencies only with the phase that uses them and commit `package.json` plus `package-lock.json` together:

- Add a unit/DOM test runner for F02 onward, such as Vitest with jsdom.
- Add a browser harness for F04 onward, such as Playwright.
- Add an OpenAPI client/type or compatibility tool if selected in F01.
- Add a small runtime schema validator only if generated contract validation does not cover the JavaScript boundary adequately.
- Add ESLint/security rules if adopted for unsafe DOM insertion and async error handling.
- Declare supported Node and npm versions using `engines` and, if chosen, `packageManager`.

Avoid adding a global state framework, UI framework, chart framework or HTTP package unless the existing vanilla modules become demonstrably insufficient. Every new package requires a documented purpose, lockfile entry, licence review, clean-install check and production-build check.

## 8. Acceptance tests

| Test ID | Required assertion |
| --- | --- |
| WEB-01 Independent build | `npm ci` and the production build succeed without backend source files or a shared filesystem. |
| WEB-02 Configured backend | The same frontend source can target documented backend environments through public configuration; missing/invalid configuration fails clearly. |
| WEB-03 Authentication | Protected data is unavailable before authentication; expiry/logout works; no backend secret appears in source maps, bundle or browser storage. |
| WEB-04 Authorization handling | Backend 401/403 responses clear or preserve state appropriately and never expose another user's cached field/profile/plan. |
| WEB-05 Remote persistence | Profile, field and plan changes survive refresh and a new browser process and match backend reads. |
| WEB-06 Geometry | Draw/import/read/export preserves coordinate order, holes and MultiPolygons; authoritative area comes from the backend. |
| WEB-07 Missing/quality states | Null, missing, rejected, stale and blocked records render distinctly without zero/default substitution. |
| WEB-08 Request races | Rapid field/season/filter changes cannot render a late response for the wrong selection. |
| WEB-09 Recommendations | Displayed recommendations, exclusions, explanations and scenarios match a stored backend run exactly. |
| WEB-10 Markets | Prices, arrivals, units, source and freshness match API records; stale/unavailable data is labelled correctly. |
| WEB-11 Plans/conflicts | Server IDs and versions are used; stale updates produce a visible conflict and cannot silently overwrite. |
| WEB-12 Safe rendering | Stored profile/field/API text cannot execute HTML or JavaScript through any view, tooltip or toast. |
| WEB-13 Failure handling | Offline, timeout, malformed response, validation error, provider failure and backend 5xx states remain usable and do not activate demo data. |
| WEB-14 Hardcode removal | Source and production bundle contain no retired seeded identities, plot records, agronomic values, market observations, generated IDs/boundaries or scientific fallbacks. |
| WEB-15 Separate deployment | A static frontend server and a separately started backend communicate through the configured origin with correct CORS/auth behavior over the intended LAN/Tailscale deployment. |

## 9. Definition of done

The frontend migration is complete only when:

- F01 through F11 pass their exit gates.
- All active screens obtain domain and user data through the versioned backend API.
- The frontend and backend build, start, configure and deploy independently.
- Production no longer imports or silently falls back to bundled demo/domain datasets.
- `localStorage` is not the authoritative source for profiles, fields, records, recommendations or plans.
- Loading, empty, unavailable, stale, blocked, unauthorized, conflict and error states are implemented and tested.
- API/UI values reconcile with backend records including IDs, geometry, units, dates, quality, source and availability.
- WEB-01 through WEB-15 pass from clean installs against separate frontend and backend processes.
- Setup documentation explains environment configuration, authentication/CORS, external map/font dependencies, tests and deployment without embedding one developer machine's address.

If a required backend route or authentic dataset is missing, report the corresponding phase and screen as blocked. Do not retain hardcoded production data to claim the migration is complete.
