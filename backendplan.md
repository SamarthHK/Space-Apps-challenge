# Backend HTTP integration execution plan

Updated: 2026-11-15. Branch: `backend`. Status: foundation implementation started.

## Approved account-free first slice

The owner selected no accounts, shared Tailscale access, frontend port 1080 and
API port 8000. Contract `shared-workspace-1` supersedes the original per-user
auth/ownership tasks below: use getWorkspace, no login/session/token routes,
explicit configured project scope and no public binding. F03/B02 profile work
will be one shared profile, not private user profiles. Economics stays deferred.
Pending-record inspection and required polygon geometry are approved.
Where later historical task rows mention authentication/memberships, apply this
approved override; do not implement an account system without a new decision.

The foundation's executable instructions are in `docs/api-running.md`.

## Project commit policy

Commit each small, coherent implementation step only after rigorous tests for
the behavior and edge cases it changes pass, along with affected regression
checks. The committed snapshot must work without depending on uncommitted
files. Do not commit a failing or partially working step, stage unrelated user
work, or claim a test passed when it was skipped or blocked. Apply this policy
to this project only; record commands and results in the task handoff.

## 1. Read first and preserve existing work

1. Read `Plan.md`'s current acceptance override, `IMPLEMENTATION_STATUS.md`,
   this file and [the shared API contract](docs/api-contract.md).
2. Inspect `git status --short` and the current source. This checkout contains
   substantial staged/unstaged work; never reset, restore deleted prototype
   modules, amend migrations already applied, or stage unrelated changes.
3. Read `frontendplan.md` and `progress.md` on branch `frontend`. In the current
   workspace that checkout is `..\Space-Apps-challenge-frontend`; this location
   is a development convenience, never a runtime dependency.
4. Execute the next task whose dependencies are satisfied. Stop at its exit
   gate, record evidence/blockers, then hand off matching operation IDs.

`Plan.md` remains the data inventory/scientific contract. Its S01-S11 sequence
is not the HTTP backlog. This B-series introduces the application/API layer
without removing any of those requirements or claiming they are all fulfilled.
Pending scientific approval is not an engineering-health failure; it still
does not make pending records accepted or a model ready to train.

The contract is proposed. D01-D05 and incomplete later-resource schemas are
explicit decisions/gates, not permission for an implementing model to guess.

## 2. Audited baseline: reusable code versus missing product capabilities

| Evidence in current source | Reuse | Missing or restricted |
| --- | --- | --- |
| `src/agri_data/__main__.py` | CLI validation, health-check, acquisition/import and preparation commands | No serve command, FastAPI app, routes or OpenAPI artifact. FastAPI/uvicorn dependencies alone do not expose an API. |
| `contracts/postgres.py`, migrations 001-006 | Real psycopg/PostGIS sessions, checksum-checked migrations, typed observations | Acceptance-oriented DB identity/schema configuration; no users, memberships, profile CRUD, current-boundary pointer or optimistic concurrency. |
| `contracts/geography.py` | KML/KMZ parser, source identity, metadata, Polygon/MultiPolygon, holes, projected metrics | Polar/antimeridian handling rejected; broader authentic corpus not certified. Repair requires reviewed reference and tolerances, not a checkbox alone. |
| `contracts/boundary_import.py` | Immutable bytes, versioned geometry and GeoJSON/GPKG readback | Synchronous immediate persistence and partial imports; no preview/confirmation, HTTP upload or KML/KMZ exporter. |
| `contracts/observation.py`, `power.py` | Typed raw observations, seven POWER daily variables and explicit missing results | Pending scientific status; missing results live in proof reports, not a queryable feature-status service. No soil/water/vegetation summaries. |
| `contracts/canonical.py`, migration 005 | Canonical fields, reviewed aliases, canonical observations and evidence links | Reconciliation is specific to the official reference parcel; general owned-field ingestion/query policy is new. Canonical JSON is not the raw Observation schema. |
| `contracts/corpus.py`, `storage_proof.py`, `health.py` | Authentic PDOK/NASA reference acquisition and reproducibility evidence | Reference-specific orchestration, paths/projects and checks; not an arbitrary farmer-field acquisition API or a public health route. |
| `contracts/trials.py`, migration 006 | Woburn wheat/cultivar/trial/performance records and attribution | One UK empirical source, not a full crop catalog, Karnataka inference service or market feed. |
| `contracts/ml_dataset.py` | Candidate exports, lineage and leakage blockers | No trained recommendation/rotation model. |
| `Plan.md` Section 1.1 | Domain collection scope and explicit economics deferral | Markets, profitability, scenario policy, profiles and planting plans need new product work, not wrappers around deleted prototypes. |

Source was inspected, not re-executed for this planning revision. Database
availability and fresh provider health are not claimed. Existing CLI evidence
does not pass any of the new API acceptance cases.

## 3. Architecture and implementation constraints

Proposed new boundaries (create only as needed by the current task):

```text
src/agri_data/
  api/
    app.py                 # app factory, middleware, route registration
    config.py              # explicit API deployment configuration
    schemas/               # request/response DTOs, not DB row dumps
    routes/                # auth/profile, fields, observations, jobs, etc.
    dependencies.py         # principal, scoped DB/session, authorization
  services/                # reusable transactions/orchestration
  repositories/            # owned resource reads/writes and projections
  contracts/               # retain current validated primitives and migrations
tests/api/                 # targeted real API/DB contract cases
docs/openapi.json           # generated, only after routes/schemas exist
```

Use existing FastAPI/Pydantic/psycopg dependencies rather than adding an ORM or
queue framework without a concrete need. Select a durable worker mechanism in
B04; document recovery and leases before enabling asynchronous submissions.
Refactor common persistence out of proof/report functions, retaining CLI tests.
Never run shell commands, `health-check`, `storage-proof` or migrations inside
an HTTP request. A route calls reusable services, not a CLI subprocess.

Add new migration versions; never alter applied 001-006. Account for existing
positional `INSERT ... VALUES` callers before extending their tables: either
use related tables or change dependent inserts to explicit column lists.
Separate deployment/migration roles from the limited application DB role.
Do not silently reuse the acceptance database as production storage.

First release slice: authenticated profile + explicitly owned existing fields
+ authoritative map geometry + paginated canonical POWER source observations.
This is source inspection, not a verified agronomic dashboard. No acquisition,
recommendations, markets or fictional seed fallback is required to demonstrate
this limited slice. B04 then enables drawing/import/export as a second slice.

## 4. Task sequence and exact gates

All tasks start `pending`; none is complete because this document exists.
Dependencies are mandatory, not inferred just from numeric order.

| Task | Depends on | Implement | Exit / frontend handoff |
| --- | --- | --- | --- |
| B01 Contract and decisions | None | Resolve D01/D02/D04/D05 for the first slice; inventory current UI fields with F01; specify auth routes, profile enums, errors, ETags, cursor and idempotency retention. Keep D03 unresolved if economics is deferred. | First-slice schema decisions recorded in shared contract; no guessed auth or field ownership; authentic response evidence identified. F01 can finish only after agreement. |
| B02 API shell, identity and profile | B01 | App factory/config, auth/session/logout, scoped DB access, membership/profile migrations, CORS/error handling. Add getHealth/getSession/deleteSession/getProfile/updateProfile plus agreed login routes. | API-01/02/03/04/08 for these operations; generated OpenAPI snapshot delivered to F02/F03. New profile is unset, not seeded. |
| B03 Owned fields and canonical reads | B02 | Ownership migration/backfill review, explicit current boundary/version, listFields/getField, listObservations/getObservation/listObservationEvidence. Paginate canonical rows and evidence separately. | API-03/05/06; no duplicate source snapshots in counts, no arbitrary boundary selection, no cross-user aliases. F04 read slice can pass. |
| B04 Field writes, jobs, imports and geometry exports | B03 | createField/updateField, durable Job, two-stage boundary imports, GeoJSON exports/download. Reuse parser/metrics, validate drawn GeoJSON, preserve versions, implement idempotency and archive behavior. | API-04/05/07; preview has no active-field writes; partial outcomes visible. F04 write/import/export slice enabled. KML/KMZ stay capability-blocked until implemented and tested. |
| B05 Soil submissions, gaps and analysis | B03 | Persist source missingness; add soil submission/history storage, source provenance and analysis projections. Freeze each visible metric/soil-form mapping; do not equate declarations with lab measurements. | API-06/08 and field-to-DTO inventory match. Pending source inspection remains possible; verified summaries only use eligible evidence. F05 enabled per supported section. |
| B06 General acquisition, satellite and remaining exports | B04; B05 for analysis output | Generalize supported providers to authorized field/boundary/date inputs. Add durable acquisition, actual scene/index adapters and series, KML/KMZ/profile exports individually. | API-05/06/07/09 per named provider/format; field-date coverage proven with real records. F06 enabled only for ready operations; one source does not certify others. |
| B07 Crop, recommendation and market services | B05; B04 jobs for asynchronous runs; B06 only for required inputs; D03/D04 | Freeze later DTOs and methods; expose authentic catalog, persisted recommendation runs, mandi/market observations. Separate unsupported financial outputs from any implemented suitability result. | API-09 with actual source/method/input lineage; no port of fabricated JS thresholds/yields/prices; F07/F08 enabled independently when their operations pass. |
| B08 Planting-plan persistence | B03; B07 catalog, plus recommendations only if referenced | Freeze PlanInput and area/date policies; implement list/create/read/update/archive, version conflicts and immutable run/financial references. Manual user decisions need not invent forecasts. | API-03/04/09; cross-process persistence and archived/stale references handled. F09 enabled. |
| B09 Independent deployment and handoff | All tasks included in release | Verify startup/config/migrations/worker, OpenAPI compatibility and separate-origin browser operation. Explicitly name any excluded blocked capability. | API-01 through API-10 for the declared release scope, corresponding WEB gates, preserved CLI behavior. Limited-slice release is not full-project completion. |

B05 can proceed independently of B04. Catalog and market provider research can
proceed while recommendations are blocked, but their HTTP/DTO gates still apply.
Do not wait for the entire S01-S11 inventory to expose truthful, authorized
source records. Conversely, do not mark an S-step complete because a route works.

### B03/B04 persistence details not to overlook

- Existing fields have project_id/source_identifier/metadata but no owner.
  No default global user, overlap-based aliasing or automatic public-data claim.
- `field_boundaries` has no ordered current-version contract. Add explicit
  revision/current selection and backfill review; old records may lack metrics.
- Geometry edits keep field identity and append a new boundary. In-flight jobs,
  observations, recommendations and exports retain the requested boundary_id.
- `boundary_imports` and `extraction_jobs` are not a general queue. Add an owned
  job record with no source-asset prerequisite, idempotency result and restart
  recovery. Terminal partial/failed work is not retried as a new logical field.
- Stage uploads in server-chosen storage with byte/expanded-size limits and
  expiry. Do not accept a caller path, follow KML NetworkLinks, or extract KMZ
  member paths to the filesystem.
- Use server-scoped source namespaces/project identity for user imports. Treat
  caller provenance as a declaration, not proof of independent validation.
- General canonicalization must preserve original receipts and explicitly
  distinguish revisions; reference-only reconcile_reference is not a generic
  user-field registration service.

## 5. Validation and evidence policy

Run the smallest tests covering changed routes/services and affected CLI paths.
Use real isolated PostgreSQL/PostGIS schemas and authentic provenance-checked
geometry/provider records. Do not use SQLite or provider mocks as acceptance
evidence. Controlled transport/error tests must be explicitly separated from
scientific data tests; do not manufacture agricultural values in either.

The original strict inventory test is especially important if `Plan.md` changes:
`python -m pytest tests\contracts\test_plan_contract.py`. Its parser expects
297 feature rows, 59 sources, 14 instruments, 11 S-steps and 68 cases.
Keep new B/API tables here, not inside that parsed inventory.

Existing `health-check` is a bounded engineering check of PDOK/NASA/Woburn.
It performs fresh network requests and persistent writes; run it only when
validating those changed paths against explicitly configured owned resources,
not on every API request or every documentation change.
No test can promote pending observations, erase missingness or bypass ML leakage
checks to manufacture a success.

API tests and commands under `tests/api` are planned, not available today.
Each implementation task must add its executable selectors and exact startup
commands to the README when they first exist. Never document an unverified
uvicorn module path as an already-working command.

## 6. Per-task handoff record

Update `IMPLEMENTATION_STATUS.md` after implementation, not after merely writing
a plan. Use one concise entry containing:

`task_id | status | operation_ids | changed files | contract revision/hash |
commands/outcomes | evidence paths | blocker/next action`

Statuses: pending, in_progress, blocked, failed, complete.
Only mark complete when the task's exit gate passed. Report API readiness,
engineering health, scientific validation and training readiness separately.
No source/runtime changes were made by this planning revision.
