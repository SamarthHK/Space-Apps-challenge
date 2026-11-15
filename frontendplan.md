# Frontend integration execution plan

Updated: 2026-11-15. Branch: `frontend`. Status: implementation started.

## Approved account-free first slice

The owner selected no accounts and shared Tailscale access. Frontend port is
1080; API port is 8000. Contract `shared-workspace-1` supersedes the original
authentication/ownership requirements below: bootstrap getWorkspace, do not
create login/token/session UI, and constrain data to the server-configured
shared projects. All permitted tailnet clients share access. Profile work is a
shared profile, not per-user storage. Do not expose this mode publicly.
Pending source inspection/polygon-only fields are approved; economics is deferred.
Historical getSession references below mean getWorkspace under this override.
WEB-03/04 now test no-account operation and project scope, not nonexistent users.

## Project commit policy

Commit each small, coherent implementation step only after rigorous tests for
the changed behavior and edge cases, affected regressions and the production
build pass. The committed snapshot must work without uncommitted dependencies.
Do not commit a failing or partial step or include unrelated user changes.
This policy applies only to this project; record validation with each handoff.

## 1. Start here

1. Read `progress.md`, this plan and the shared contract on branch `backend`:
   `docs/api-contract.md`, revision `integration-draft-1`.
2. Read `backendplan.md` and `IMPLEMENTATION_STATUS.md` on branch `backend`.
   In this workspace the backend is `..\Space-Apps-challenge`; the
   [local contract](../Space-Apps-challenge/docs/api-contract.md) and
   [local backend plan](../Space-Apps-challenge/backendplan.md) are available.
   These relative links are workspace conveniences, not runtime dependencies.
3. Inspect `git status --short`, `index.html`, `src/main.js`, the two service
   modules and the data imports before editing. Line references below are
   navigation hints from this audit; find symbols if later edits shift lines.
4. Execute the next ready F-task. Check its B-task dependencies and acceptance
   gate before claiming completion. Keep blocked screens honest and continue
   only work independent of their blockers.

There is one API specification, not a second frontend route design. Copy the
agreed contract/OpenAPI artifacts into `contracts` during F01/F02 for independent
development, recording their source revision and SHA-256. On another machine,
obtain the exact backend artifact rather than assuming this sibling directory
exists. Documentation changes must be committed/shared before another model
can retrieve them from a remote branch.

The current README describes the original prototype, not verified integration.
The real `vite.config.js` uses port **8080**, not the README's 5173.
No existing server's running state is assumed.

## 2. What the code actually supports

The frontend is Vite + vanilla JavaScript + Leaflet, with seven screens.
`src/main.js:5-9` imports bundled domain data, localStorage persistence and a
browser recommendation engine. No API client, authentication or remote state
has been implemented. `package.json` currently offers dev/build/preview only;
test/lint scripts below are future work, not commands available today.

The backend has reusable CLI/database/geography code, not HTTP routes. It has
authentic Dutch reference-boundary/NASA POWER data paths and Woburn trial
imports. Those are not a Karnataka soil/water/satellite catalog or a crop
recommendation/market service. Scientific records remain pending when reported
as such; software health, scientific acceptance and training readiness differ.

First delivery is a narrow vertical slice:

**session/profile -> owned field list -> authoritative map geometry -> canonical
POWER source-record inspection, with pending/quality/provenance labels.**

Do not wait for a fully trained model to implement this slice. Do not claim that
it completes the dashboard's agronomic or financial features either. B04/F04
then adds field drawing, preview/confirmed imports and supported exports.

## 3. Non-negotiable frontend rules

- Frontend and backend build/deploy independently. Browser uses configured HTTP
  only, never Python modules, PostgreSQL or backend filesystem paths.
- Keep Leaflet/native fetch/vanilla JS. Do not introduce a framework rewrite or
  Axios merely to connect APIs.
- No production domain seeds, fallback scientific values, browser agronomic
  rules, fabricated geometry/IDs/soil cards or local financial forecasts.
- User declarations are allowed, but must stay distinguishable from measured or
  scientifically accepted records. A submitted card number is not verification.
- localStorage may hold UI preferences only. Never automatically upload legacy
  stored plots/profile/plans: they may be generated seeds. Any later migration
  requires explicit user review and a separately specified import flow.
- Null, zero, missing, rejected, pending, stale and blocked are not interchangeable.
  Do not replace missing values with zero, a district baseline or another field.
- Preserve units, basis, dates/time standard, quality, spatial support and source
  references. Do not turn POWER retrieval dates into observation dates.
- Do not port the browser recommendation engine into Python. Its hardcoded
  thresholds, yield/cost/price assumptions are not authenticated source evidence.
- Safe DOM construction is required for API/user values, including Leaflet
  popups, option elements, SVG labels and toasts. Do not trust arbitrary HTML.
- Secrets and authentication signing/provider credentials never enter Vite
  configuration or the bundle. D01 decides the session transport before F03.

## 4. Consumer inventory and operation mapping

This checked family-level inventory includes previously missed HTML/form paths.
F01 must expand it to one row per active displayed/input property; it is not
already a complete field-level mapping. Each row needs consumer/property,
classification, operation ID + DTO property, availability behavior, task and
status. Unmapped means blocked, not permission to invent an API property.

| Consumer / code location | Existing behavior to remove | Shared operation IDs / target |
| --- | --- | --- |
| Bootstrap/header, main.js initData/getActivePlot/renderHeaderControls | Seeded person/plots/plans and silent first-plot fallback | getSession, getProfile, listFields; listPlans only when ready. No field means explicit empty selection. |
| Dashboard, renderDashboard | Browser recommendation execution, seeded verified counts, net returns and misleading "100% accurate" text | listFields, getAnalysis, listRecommendations, getRecommendation, listPlans. Compose only available data; aggregate complete pages, not partial pages. |
| Map, initMap/renderMapActiveParcel | Seed center/NDVI color, legacy boundaries and popups | getField, getAnalysis, listScenes; true GeoJSON geometry, explicit unsupported overlays. Base-map configuration may remain static. |
| Add plot/drawing, finishDrawing/setupForms | Date.now IDs, default district rectangle, fabricated soil/water/NDVI and authoritative user area | createField, updateField; require drawn geometry, backend IDs/area/boundary version. User area can only be a separately labelled declaration if specified. |
| New KML/KMZ workflow | No existing upload/preview/confirmation flow | createBoundaryImport, getJob, getBoundaryImport, confirmBoundaryImport. Wait for B04, do not emulate by local-only save. |
| GeoJSON click handler/exportPlotAsKML | Browser-assembled exports; KML outer ring only | createExport, getJob, downloadExport. GeoJSON first; KML/KMZ disabled until supported. |
| My Land, renderMyLand/renderTimeSeriesSvg | Global hardcoded passes, mean/max NDVI and rainfall, assumed dates/scene ID | listScenes, getVegetationSeries; rain from identified climate records. Field/boundary/date scope, gaps and source labels retained. |
| Land analysis, renderLandAnalysis | Soil pH/EC/carbon/N/P/K/texture/depth/drainage, water quality/depth/yield/cost, annual/seasonal rain/dry spells/drought defaults | getAnalysis plus listObservations for pending source inspection. Freeze per-metric IDs and units in B05; unknown metrics stay blocked. |
| Soil modal, main.js:1118-1128 and setupForms | Fabricated card/lab/values, today's date treated as test date, immediate hasSoilTest=true | listSoilRecords, createSoilRecord. Ask actual sample date/origin; pending submission, no client verification. |
| Recommendations, renderCropRecommendations and dashboard | JS agronomic score, suitable/excluded lists, returns, BCR, budgets, risks, sowing/yield assumptions | listCrops, createRecommendation, getJob, listRecommendations, getRecommendation. Backend run and input versions required. |
| Markets, renderMarketIntelligence | Bundled mandi prices, MSP, arrivals, trends and farm-gate deductions | listMandis, listMarkets. Missing MSP/derived prices must remain unavailable independently of modal prices. |
| Plans, renderPlantingPlans/setupForms/openPlanModalWithCrop | Seeded CRUD, generated IDs, browser forecasts/default dates/crop fallback | listCrops, listPlans, createPlan, getPlan, updatePlan; archive, not destructive deletion. No computed financial payloads from browser. |
| Profile, renderProfile/saveProfileHandler | localStorage authority and seeded district/preferences | getProfile, updateProfile. Include farmer_category/preferred_language consistently; freeze mismatched objective codes. |
| index.html (including static body and form values) | Initial fake counts, scientific values, identity, dates and regional defaults before JS runs | Empty/loading placeholders, nullable form fields. Labels/options are static only if not asserted as a user's actual value. |
| storageService.js/recommendationEngine.js and data modules | Bundled production domain authority | Retire after consumer migration; never reactivate on network failure. |
| agriZones.js/mandyaData.js/sensorStations.js | No active imports found in audited application | Recheck consumers then remove dormant domain datasets; do not create endpoints just to preserve unused demo files. |

Special semantic gaps: water discharge in "inches" has no defined flow basis;
profile objective codes disagree between HTML and seeds; canopy/soil quality
labels and climate sowing dates are not harmless layout copy. Resolve or disable
these fields explicitly rather than matching names to unrelated backend data.

## 5. Contract consumption and client/state boundaries

Use operation IDs and DTOs from `backend:docs/api-contract.md`. Do not introduce
`/plots`, `/recommendations` or a second convention independently. On the wire,
`field_id`, `boundary_id`, `plan_id`, `run_id` and snake_case remain unchanged.
Only adapters translate to a legacy view model while migrating.

Target layout, created incrementally:

```text
src/
  api/client.js              # URL/auth/error/timeout parsing, no view logic
  api/<resource>Api.js        # shared operation-ID implementations
  adapters/<resource>ViewModel.js
  state/appState.js
  state/actions.js
  views/                     # extracted only as each feature migrates
  map/                       # geometry, drawing, layers
  config.js
  main.js                    # eventually bootstrap only
contracts/                   # pinned contract/OpenAPI artifacts and source hash
```

Client requirements:

- Validate VITE_API_BASE_URL as an origin; append `/api/v1` exactly once.
  Follow D01 for credentials/CSRF or bearer behavior. No per-view auth storage.
- Parse the shared success/error envelopes, non-JSON failures and 204 correctly.
  Validate response shapes against pinned schemas at the boundary.
- Use AbortController and a request-generation check. Cancellation alone does
  not prevent a just-completed old response from overwriting a new selection.
- Reads may retry bounded documented transient errors. No ambiguous write
  retries without the same Idempotency-Key and the server's replay guarantee.
- Preserve ETag, send If-Match on PATCH; distinguish 409 conflicts from 412
  stale versions and 428 missing preconditions. Do not silently overwrite.
- Downloads follow the authenticated binary route, validate safe filenames and
  revoke browser object URLs. Never treat local backend paths as download URLs.
- Poll jobs using retry_after_seconds/Retry-After, stop for terminal states and
  on logout/navigation. Partial is a distinct terminal outcome.

Resource state:

```js
{
  status: "idle", // idle | loading | ready | empty | error
  data: null,
  error: null,
  requestKey: null,
  receivedAt: null,
  refreshing: false
}
```

Keep transport status separate from capability readiness, backend feature
availability, scientific validation, freshness and job state. A 200 response
containing pending records is not a "Verified Lab Record".
Cache/request keys include user, field, boundary, dates, season and filters as
applicable. Clear protected state on logout/session expiry. Field changes must
invalidate dependent data and never render the previous field under the new name.
Refresh may retain same-key data only with a visible refreshing/stale indicator.

## 6. Execution tasks and backend dependencies

All F-tasks start pending. Writing this plan did not implement them.

| Task | Depends on | Implementation scope | Exit gate |
| --- | --- | --- | --- |
| F01 Inventory and contract agreement | None; B01 cooperation | Expand Section 4 to property-level mapping; agree first-slice DTO/auth/ownership/evidence policy and preference codes. Obtain shared specification; pin exact OpenAPI once B02/B03 exports it. Record unresolved D03/later-resource blockers. | Every active field classified; first-slice properties agreed, no guessed endpoint. Authentic reference evidence identified; later missing capabilities listed, not treated as available. |
| F02 Transport, safe shell and remote state | F01; B02 shell/schema artifact | Add config/client/errors/schema validation/state, safe rendering primitives and startup/offline/unauthorized states. Remove HTML seed values. Stop initData seeding; gate every unmigrated view as not connected. | Client/state cases and independent build pass; failed/missing API never shows demo values. Existing legacy modules may remain unused until F10, not execute as fallback. |
| F03 Session and profile | F02; B02 auth/profile gates | Bootstrap session, clear protected state on expiry/logout, get/update profile, validation and ETag conflicts. Blank new profile; preserve real Unicode user text safely. | WEB-03/04/05/12 for profile, including new browser process. No profile localStorage authority. |
| F04 Fields and map, then writes/import/export | F03; B03 for reads; B04 for mutations | Migrate selectors/map and canonical source-record inspection first. Then draw/create/edit/archive, preview/confirm uploads, job states and supported exports. Respect current boundary and backend area. | Read slice: WEB-04/07/08 against owned canonical fields. Write slice: WEB-05/06/11/13. Each slice recorded separately; no full F04 completion until both pass. |
| F05 Dashboard, land analysis and soil submission | F04 read slice; B05; B07/B08 only for respective dashboard cards | Replace all soil/water/climate fallbacks, add metadata/pending inspection and soil submission/history. Dashboard shows field metrics immediately; recommendation/financial/plan cards remain capability-blocked until their own tasks. | WEB-07/08/12/13; no scientific defaults or automatic verified badge. Submitted sample date is actual, not receipt time. |
| F06 Satellite and vegetation | F04 read slice; B06 scene/series gates | Replace scene/date seeds and index/rain series; adapt actual overlays. Handle zero/one/multiple points, gaps and negative NDVI per definition, not a hardcoded 0..1 clamp. | WEB-07/08/13; selected scene/field/boundary reconcile with response. Base-map failure is distinct from analytical-data absence. |
| F07 Catalog and recommendations | F05; B07 catalog/recommendation gates; D03/D04 | Replace engine/catalog imports; submit explicit season year/date, field/boundary version and scenario inputs. Render stored suitable/excluded/unavailable results and metadata. | WEB-09; no agronomic or economic calculations in browser; no-results differs from blocked run. Activate dashboard recommendation cards only now. |
| F08 Markets | F03; B07 mandi/market gates and D03 | API filters, provenance, currency/quantity basis, freshness and optional MSP/trend/farm-gate metrics. | WEB-10/13; unsupported computed values stay unavailable. Independent of F07 if market contract is ready. |
| F09 Planting plans | F04 read slice; B08; F07 only when attaching a recommendation | Remote CRUD/archive, field/crop/run versions, area/date validation, immutable financial references and conflicts. Display nullable forecasts honestly. | WEB-05/11; persist across processes, preserve references and no partial-page financial totals presented as complete. Activate dashboard plan cards now. |
| F10 Remove legacy authority and finish module split | All implemented view migrations | Remove retired services/data modules, reset-demo behavior, fabricated IDs/cards/boundaries, seeded copy and dead imports. Finish bootstrap/view/state separation without unrelated UX redesign. | WEB-14 source + index.html + built bundle; backend off means honest errors. Remaining blocked screens have no legacy fallback. |
| F11 Independent deployment and release evidence | Tasks included in release; B09 cooperation | Browser tests, compatibility, exact environment/auth/CORS/tile/font documentation and static deployment against separate API origin. | WEB cases pass for stated release scope; excluded blocked capabilities listed. Full migration is not complete while required screens remain blocked. |

For any task: read exact code and current backend artifact -> implement one
vertical feature -> run its narrow tests/build -> reconcile UI/API/DB ->
record task evidence -> proceed. Never rewrite all main.js before one slice works.
Never expand a blocked capability by guessing what a future backend will return.

F04's read slice adds a source-record panel inside the existing Land Analysis
screen, not an eighth screen. Use listObservations for variable/value/unit/date/
validation rows and getObservation/listObservationEvidence for provenance detail.
Keep the existing verified-summary cards blocked until F05 has eligible metrics.

## 7. Validation and dependency plan

Current scripts: `npm run dev`, `npm run build`, `npm run preview`.
Use `npm ci` when dependencies need restoring for implementation/validation.
Do not install anything for this documentation-only revision.

F02 adds a unit/DOM harness (for example Vitest/jsdom) only when tests are added.
F04 adds a browser harness (for example Playwright) with its first browser cases.
Choose generated schema validation or a small runtime validator in F01/F02,
not both without need. Add dependencies with package.json/package-lock.json
together, declare supported engines, and document executable test scripts then.

Use real isolated backend accounts/DB and authentic provenance-checked records
for integration acceptance; no provider mocks/generated agricultural fixtures
as evidence. Synthetic transport-only error/HTML-safety inputs are not domain
data and must be explicitly isolated from scientific tests/acceptance. If a
required authentic geometry or provider context is missing, report that gate
blocked; do not fabricate it to make WEB-06/09/10 pass.

| Case | Assertion |
| --- | --- |
| WEB-01 Independent build | Static build needs no Python source/shared filesystem. |
| WEB-02 Configuration | Same source targets configured API origins; missing/invalid config fails clearly; actual dev port documented. |
| WEB-03 Authentication | Login/bootstrap/expiry/logout follow D01; no secrets/token persistence in bundle or browser storage. |
| WEB-04 Authorization | 401/403/unowned 404 cannot leak another user's state, nested evidence, imports, jobs or exports. |
| WEB-05 Persistence | Profile, field and plan mutations survive refresh/new browser process and match backend reads. |
| WEB-06 Geometry | Coordinate order, holes, MultiPolygons, version identity and area survive draw/import/read/export; preview has no active-field write. |
| WEB-07 Meaningful states | Pending/rejected/null/missing/zero/stale/blocked/below-detection values remain distinct and source-labelled. |
| WEB-08 Races and pagination | Rapid field/filter changes cannot overwrite current state; full totals do not use partial pages. |
| WEB-09 Recommendations | UI groups/scenarios/explanations match a persisted run and actual input versions; no local decision rules. |
| WEB-10 Markets | Prices/arrivals/units/source/freshness reconcile with records; missing derived economics do not appear current. |
| WEB-11 Conflicts and replay | If-Match/version conflicts visible; repeated submissions do not duplicate fields/plans/imports; archive preserves references. |
| WEB-12 Safe rendering | Profile/field/API text is inert in all views, SVG, popups, selectors and toasts. |
| WEB-13 Failures and jobs | Offline, timeout, malformed response, backend/provider failure and partial/blocked jobs are usable without fallback data. |
| WEB-14 Hardcode removal | Source, initial HTML, forms and bundle contain no production domain seeds or browser scientific/economic calculations. |
| WEB-15 Separate deployment | Static frontend and API work over documented independent origins with correct CORS/auth; no machine-specific IP in source. |

A limited first-slice release may pass its applicable cases while later tasks
remain blocked. Record that exact scope. Full frontend integration requires all
F-tasks, all required capabilities and WEB-01 through WEB-15, not merely a build.

## 8. Handoff format

Update `progress.md` after each implementation task:

`task_id | status | operation_ids | files | backend contract revision/hash |
commands/outcomes | evidence | blockers | next ready task`

Use pending/in_progress/blocked/failed/complete. Include B dependencies for
blocked work. Never say a planned endpoint, source feed, job or acceptance case
works without observed evidence. Keep completion concise and machine-followable.
