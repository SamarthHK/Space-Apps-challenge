# 01. Implementation audit

## Scope and source snapshot

Inspected on 2026-11-15 under `D:\Code\SpaceApps`. This is a source-code and
configuration audit, not a running-service, provider-access, or database audit.
No original checkout, local database, or browser storage was modified.

| Checkout | Branch / committed revision | Role |
| --- | --- | --- |
| `Space-Apps-challenge-backend` | `backend` / `5d53f6735d1ec1698cd98b7021b8a22efd8e1a4f` | Primary backend implementation inspected |
| `Space-Apps-challenge-frontend` | `frontend` / `da3b1c0120d99355c3f05dee3fb429877e34b07c` | Primary frontend implementation inspected |
| `Space-Apps-challenge` | `backend`, substantial staged/unstaged/untracked work | Separate evolving backend rewrite; not silently substituted for the named backend checkout |
| `Space-Apps-challenge-merger` | `merger`, based on `origin/main` at `9cf7e2d963345e19d75c326aebbd90ed2d915527` | Fresh clone, planning destination |

All checkouts point to <https://github.com/SamarthHK/Space-Apps-challenge>.
Fresh-clone remote backend/frontend tips matched the primary source commits.
The backend had an edited `backendplan.md`; its local
`docs\frontend_api_contract.md` was untracked when status was recorded. During
inspection, frontend documentation also became modified (`README.md`,
`frontendplan.md`, `progress.md`). Treat those documents as live, uncommitted
design inputs, not reproducible content at the pinned revisions. Recheck status
and revisions before implementation; coordinate with whoever owns that work.

The original checkout's pending `contracts` modules and SQL migrations represent
an alternative implementation direction. Their completeness and compatibility
were not audited here. Choosing that rewrite requires a separate delta review
and an explicit committed handoff, not copying a dirty directory.

## Current system, not planned system

The frontend is native JavaScript + Vite + Leaflet, with synchronous browser
storage and bundled agricultural records. Its manifest contains only `dev`,
`build`, and `preview`. No application HTTP client was found in its source.

The backend is a Python CLI/batch pipeline with geospatial processing, normalized
observations, imports, SQLAlchemy storage, and filesystem exports. FastAPI and
Uvicorn dependencies exist, but no FastAPI application or router was found in
the inspected source tree. `run_pipeline()` returns Python/GeoPandas objects
and file paths, not a public JSON API.

Evidence prefixes below: **F** = pinned frontend checkout, **B** = pinned backend
checkout. Paths use checkout-relative locations; abbreviated backend module
paths (for example `storage\models.py`, `config.py` or `__main__.py`) are relative
to `src\agri_data`. Line numbers refer to inspected implementation files.
Findings are source-derived, not runtime reproductions.

## Inconsistency register

| ID / priority | Evidence | Inconsistency and integration consequence | Resolution |
| --- | --- | --- | --- |
| I01 / P0 | F `src\main.js:1-59`; B `src\agri_data\__main__.py:1-21`, `pipeline\orchestration.py:27-141` | Browser loads local records; backend takes a KML path and writes files. There is no HTTP boundary to configure. | Shared services, versioned API, asynchronous client, and DTO adapters; never invoke the CLI from a request handler. |
| I02 / P0 | F `src\services\storageService.js:272-404`; B `storage\models.py`, classes `Field`, `Project`, `ManagementEvent` | Browser owns profiles/plans/plots. Backend has no user/session/profile/planting-plan models or field-owner link. Management events are not plans. | Add ownership, profile and plan repositories; authorize every lookup, mutation, job and export. |
| I03 / P0 | F `src\main.js:1238-1248`; B `pipeline\orchestration.py:47-48`, `geo\kml.py:151` | Browser timestamp IDs, parser sequence IDs, pipeline geometry/project hashes, and integer DB keys are different identities. Editing geometry changes the pipeline hash. | Stable server IDs, separate geometry revisions, explicit legacy-ID map; never deduplicate across owners by shape alone. |
| I04 / P0 | F `src\main.js:187-206`, `1433-1476`; B `geo\kml.py:33-65` | Frontend map/KML export uses the first ring only. Backend finds a descendant Polygon before MultiGeometry, so a normal multi-polygon placemark returns its first polygon early. Its later multi-polygon path also omits holes. | Repair parser traversal and preserve every component/ring; use `L.geoJSON` and server KML/KMZ exporters. |
| I05 / P0 | F `src\main.js:255-310`, `1215-1248`; B `geo\area.py:28-92`, `geo\kml.py:115-120` | Browser approximation/manual acreage can disagree with geometry; new fields invent district rectangles and use district centers even after drawing. Backend automatically repairs invalid shapes without consent. | Require real geometry, server area/representative point, preview-and-confirm repairs; browser drawing area is provisional only. |
| I06 / P0 | F `src\main.js:580-614`, `1289-1317`; B `config\variables.yaml:34-49`, `sources\soilgrids.py:112-161` | UI expects carbon percent and available N/P/K in kg/ha; backend has carbon and total nitrogen in g/kg with depths. A key rename would change scientific meaning. | Typed units/basis/depth and explicit conversion; never map total N to available N or invent missing P/K. |
| I07 / P0 | F `src\main.js:1119-1128`, `1289-1317`; B `storage\models.py`, class `Observation` | Soil form invents a card number, uses today as test date, and marks any submission verified. Provider modelled soil is not a lab result. | Auditable report submission, actual dates/methods, distinct evidence type and server validation; no client-owned verification flag. |
| I08 / P0 | F `src\main.js:599-614`; B `pipeline\acquisition.py:43-89` | UI turns null and real zero into defaults. Backend has `available/unavailable/unsupported/synthetic` plus `valid`; UI has no representation for these distinctions. Live water/satellite acquisition explicitly reports unavailable. | Separate transport, data availability, quality and capability; no plausible fallback values or false ready states. |
| I09 / P1 | F `src\main.js:161-184`, `455-575`; B `pipeline\acquisition.py:52-53`, `pipeline\extraction.py:35-38` | Scene selection does not change Esri imagery; NDVI series is global, not field-scoped. Parcel fill is not a raster. Chart clips negative NDVI and assumes at least two points. | Field/scene/geometry-scoped metadata and overlays, real time axes, gaps and empty/single-point handling; distinguish basemap from analysis. |
| I10 / P1 | F `index.html:172-176`, `223-280`; B `__main__.py:10-11`, `pipeline\extraction.py:25-33` | Static dates/cloud/forecast appear as current data. Backend historical daily weather and its fixed default year are not a forecast or climate normal. | Explicit periods, working filters, separately sourced forecast or unavailable panel; no historical-to-forecast relabeling. |
| I11 / P1 | F `src\main.js:609-614`; F `src\services\storageService.js:79-85`, `209-215` | Water yield in "inches" lacks a flow basis; an annual-area cess is stored under hourly irrigation cost. Source and delivery method share one irrigation enum. | Preserve reported text; require quantity basis, split water source/method, do not infer perennial supply from borewell. |
| I12 / P1 | F `src\main.js:838-892`; B `storage\models.py` | Market prices, support prices and deductions are bundled; no corresponding market persistence/API exists. First array report is treated as primary regardless of recency. | Real market/commodity IDs, dated observations, separate policy prices; gate farm-gate economics until inputs/method exist. |
| I13 / P0 | F `src\main.js:1319-1371`; B `storage\models.py` | Plans have client IDs, localized dates, seeded crop references and computed profits; no server plan persistence. | ISO civil dates, valid field/species/cultivar references, versioned drafts/archive, nullable economics; manual plans must not require AI. |
| I14 / P1 | F `index.html:648-670`, `src\main.js:1180-1195`; F `storageService.js:25-28` | Profile category is not saved; stored objective comments disagree with actual HTML values; human labels differ from enum IDs. | Contract uses actual form enums, persists category, and requires confirmation for ambiguous legacy values. |
| I15 / P0 | B `config.py:37-40`, `storage\models.py:37-38`, `storage\database.py:36-123` | Compose advertises PostGIS, but default runtime is SQLite and field geometry is WKT text. Initialization seeds scientific catalog/rotation defaults. | Explicit PostGIS URL, spatial migrations and reviewed reference imports; no production auto-seeding. |
| I16 / P0 | B `pipeline\orchestration.py:31-141`, `storage\models.py`, class `ExtractionJob` | Pipeline interleaves acquisition, DB writes and exports; its completion records are not an asynchronous durable queue. Returns expose internal paths and non-JSON objects. | Worker with durable jobs/retries/leases; service DTOs and authorized opaque artifact IDs. |
| I17 / P1 | B `pyproject.toml`, `requirements.txt`, `docker-compose.yml`; F `vite.config.js`, `package.json` | Python graphs differ (including parser/DB dependencies); Compose starts DB/admin only. No API origin, CORS/auth configuration, API worker or frontend test scripts. | One authoritative Python manifest/lock; separate builds/processes; explicit public origins and startup/readiness commands. |
| I18 / P1 | F `src\main.js:368-453`, `898-980`; F `storageService.js`, `getPlots/getPlans/getPlotById` | Empty stored arrays reseed demos; unknown IDs fall back to first plot; dashboard assumes a field; totals assume unpaginated local arrays. | Genuine empty state, no arbitrary field fallback, server summaries and complete pagination. |
| I19 / P1 | F `src\main.js:325`, `495-507`, `845-891`, `1199-1208` | API/user values would enter existing HTML interpolation; reset button overwrites domain state with seeds. | Safe text rendering, remove production reset, consent-based legacy export/import without destructive automatic migration. |
| I20 / P1 | F `src\services\recommendationEngine.js:15-236`; B `tests\test_acquisition_modes.py`, `tests\test_geo_and_processing.py` | Browser rankings/economics are rules over assumed inputs, not an integrated model. Existing backend tests include demo/generated inputs, unlike newer authentic-data acceptance plans. | Defer recommendation/model work; distinguish legacy regression tests from real-data integration acceptance, which needs provenance. |

## Existing plans: reconcile, do not duplicate

`frontendplan.md` already describes independent deployments and F01-F11.
The local backend plan/companion contract adds S01-S12, M01-M18, and D01-D05.
Those are designs, not implemented endpoints. In particular:

- F02's temporary seeded-screen instruction conflicts with a real-data production
  release. Gate unmigrated screens instead; do not silently leave demo fallbacks.
- Broad full-science/model completion is not a prerequisite for this requested
  non-AI merge milestone. Keep domain expansion tracked separately.
- The local companion API contract is the proposed starting point, not an
  approved/generated OpenAPI artifact. Preserve its authorship/history through
  a source commit before moving it into the consolidated repository.
- The separate original checkout may supersede parts of S02/S03. Do not mix its
  schema with the pinned legacy SQLAlchemy schema without an explicit decision.

See [delivery plan](04-delivery-plan.md) for issue-to-phase mapping and
[decisions](06-decisions.md) for unresolved ownership/product choices.
