# Shared application state

Run the existing API and frontend as separate instances. This workspace-state
slice introduces no accounts, sessions, cookies or private-user profile migration.
Optional read-only reference inference is configured separately in
[api-running.md](api-running.md); it does not read or mutate workspace fields.
Every visitor permitted by the loopback/Tailscale configuration sees the same
profile. A soil-card reference is not verified laboratory evidence.

## Explicit setup

Keep the existing `AGRI_API_DATABASE_*`, `AGRI_API_SCHEMA`, and
`AGRI_API_PROJECT_IDS` settings for the read-only canonical repository.
Separately configure the following environment variables for application writes:

| Variable | Meaning |
|---|---|
| `AGRI_WORKSPACE_DATABASE_URL` | PostgreSQL connection URL; inject credentials securely |
| `AGRI_WORKSPACE_DATABASE_NAME` | Expected database identity |
| `AGRI_WORKSPACE_DATABASE_USER` | Expected database role |
| `AGRI_WORKSPACE_SCHEMA` | Separate `agri_*` application schema, e.g. `agri_workspace` |
| `AGRI_WORKSPACE_ID` | Stable operator-chosen ID, independent of project selection |

Run `python -m agri_data.workspace.admin provision` once under an authorized
setup role. This applies packaged, checksummed application migrations and creates
an empty shared profile. Repeating it does not reset values. GET never provisions
records. `python -m agri_data.workspace.admin check` fails if setup is incomplete
or migration checksums differ. The application ledger is independent of the
canonical scientific schema and its migrations.

Launch using `python -m agri_data.api` with `AGRI_ALLOWED_ORIGINS` and the existing
loopback/Tailscale host settings. Environment files are not implicitly loaded.
Keep database credentials out of frontend configuration and Git.

## Profile contract

`GET /api/v1/profile` returns the existing `{data,meta}` envelope and a strong
`ETag`. `PATCH /api/v1/profile` requires a configured `Origin`, JSON fields, and
that exact `If-Match` value. Missing preconditions return 428; a stale or foreign
profile ETag returns 412; malformed, weak, wildcard, and multiple ETags return
400. Body versions, unknown/server-owned fields, and empty patches return 422.
Omission leaves a value unchanged; explicit `null` clears it.

Updates increment the version and append an audit snapshot in one transaction.
Clients must retain unsuccessful edits and explicitly reload after conflicts or
ambiguous transport failures; they must not automatically retry writes. CORS
allows PATCH/Content-Type/If-Match and exposes ETag and X-Request-ID, without
credential support. Requests are bounded at 16 MiB.

The profile capability is independently `ready` or `blocked`; data-read readiness
does not imply writable application state. The existing read response bodies and
`shared-workspace-1` contract revision remain compatible.

## Relevant checks

`python -m pytest tests\api -q` includes actual PostgreSQL persistence, concurrent
updates, transaction rollback, process restart, origin/precondition validation,
and existing authentic canonical/evidence reads. Supply the prepared database
via `AGRI_TEST_DATABASE_URL`, `AGRI_TEST_DATABASE_NAME`, `AGRI_TEST_DATABASE_USER`,
`AGRI_TEST_SCHEMA`, and `AGRI_TEST_PROJECT_IDS`. Tests create uniquely named
application schemas and remove only those schemas; they do not seed scientific
observations or modify existing provider evidence.

For the real, separate-instance browser gate, run
`python scripts\workspace_browser_acceptance.py --frontend <frontend-checkout>`
with the same test data settings and installed Playwright Chromium. If browser
binaries live outside Playwright's default cache, set `PLAYWRIGHT_BROWSERS_PATH`.
The harness refuses occupied ports (defaults: API 18084, frontend 11084), copies
the scoped authentic reference rows into a separate canonical test schema,
creates an isolated application schema, builds to its own artifact directory, and
terminates only processes it started. It never replaces the normal frontend
build or stops existing services. Logs/results remain under the ignored
`.local\workspace-acceptance` directory.
Field mutations run only against that owned copy, never the original corpus.
The harness starts and verifies its own worker as well as the API/static server.
Write browser tests require its `TEST_WRITES_ISOLATED=1` guard.

## Versioned field writes

Re-run explicit provisioning after upgrading to apply additional migrations.
Field writes require the canonical and application schemas on the same
PostgreSQL endpoint/database, allowing one transaction across them. The workspace
writer needs canonical project/field reads, field INSERT/UPDATE, and boundary/
source-asset INSERT; it never writes scientific observations or validation.
Keep the canonical API connection read-only. Field-write readiness is independent
of profile readiness and checks these permissions.

`POST /api/v1/fields` accepts `project_id`, nullable `name`, and GeoJSON `geometry`.
It requires an `Idempotency-Key`; replaying the same input returns the saved
result, while using that key for different input returns 409. Only configured,
existing projects are writable. The server assigns field and boundary IDs.
Keys are workspace-wide, including across operations; receipts have no automatic
expiry. Original assets, jobs, revisions and exports likewise have no automatic
retention cleanup. Monitor database capacity and back up the application schema
with its canonical field/boundary dependencies.

`GET /api/v1/fields/{id}` retains its existing JSON schema and now exposes an ETag
from the same read snapshot. `PATCH` accepts a name and/or replacement geometry
with `If-Match`. `DELETE` archives with `If-Match`; it never deletes boundary or
evidence history. Missing/stale preconditions return 428/412. Archived fields
are hidden from normal reads, including field-scoped observations.

Writes preserve all previous boundary versions and record an explicit current
boundary. Legacy ambiguous fields still require explicit selection. Polygons
and MultiPolygons preserve holes; unclosed, invalid, nonfinite, out-of-range,
mixed-dimension, polar/unwrapped-antimeridian, or over-10000-position geometries
are rejected without implicit repair. Measurements are recomputed by PostGIS in
the selected metric CRS. Original bytes and altitude-bearing geometry remain in
application storage; analysis uses the 2D footprint.

Small original uploads/GeoJSON are stored transactionally in PostgreSQL rather
than a browser-visible filesystem. Canonical source assets use opaque
`workspace-asset://` locators, not download URLs. User-supplied geometry is never
labelled a surveyed or scientifically verified measurement.

## Durable imports and exports

Run `python -m agri_data.workspace.worker` with the same workspace and canonical
project settings as the API. This is backend infrastructure, not another
browser-facing API. `--once` processes at most one queued job for operational
checks. Provisioning does not start a worker. Import/export capabilities require
a matching worker heartbeat from the last 30 seconds; job status remains readable
while workers are offline. Acquisition and field-recommendation capabilities
remain unavailable; optional reference suitability does not use this job worker.

Submit original bytes to `POST /api/v1/imports?filename=...&project_id=...&source_namespace=...`
with `Content-Type: application/octet-stream` and an `Idempotency-Key`.
Multipart bodies and browser filesystem paths are not accepted. KML, KMZ, and
GeoJSON FeatureCollections are supported. A namespace explicitly identifies the
source within the shared workspace; reuse it only when provider identifiers
should refer to the same fields. File names are not field identities.

Submissions return 202 and a job `Location`. Poll `GET /api/v1/jobs/{job_id}`.
After a successful preview, `GET /api/v1/imports/{import_id}` returns candidates,
source locators, geometry/metrics, create/update actions, expected versions, and
rejections. Preview changes no canonical field, boundary, or source-asset rows.
Confirm an explicit selection of up to 50 valid candidate IDs with its exact
`preview_hash` at `POST /api/v1/imports/{import_id}/confirm`, using a new submission
key. Rejected features are never silently included or repaired. If an existing
field changes after preview, the entire confirmation fails without partial writes;
create a fresh preview rather than overwriting that change.

Jobs use database leases, attempt counters, `FOR UPDATE SKIP LOCKED`, and atomic
result/field transactions. A dead worker's lease is reclaimable after 60 seconds.
Live processing holds the job lock; recovery cannot execute the same job
concurrently. Transient storage failures retry after two seconds, at most three
attempts; permanent validation/conflict failures do not retry. Queued input and
original uploads survive API/worker restarts. Failed exhausted work requires a
fresh explicit submission/preview after the underlying issue is resolved.

`POST /api/v1/exports` takes a format (`geojson`, `kml`, or `kmz`) and 1-50 explicit
`{field_id,boundary_id}` selections, plus an `Idempotency-Key`. It snapshots those
stored versions, not whatever boundary becomes current later. On job success,
`GET /api/v1/exports/{export_id}/download` returns real bytes with the correct
media type, attachment filename, and checksum ETag. Downloads recheck current
project scope and archival state; no arbitrary filesystem path is served.
Polygons, all MultiPolygon parts, holes, and retained original altitude roundtrip.
Legacy canonical 2D geometry is explicitly labelled; missing altitude is never
invented. Source metadata is retained in GeoJSON properties and structured KML
ExtendedData, with existing folder names.

Limits: 16 MiB uploads, 100 preview features, 100000 total KML positions, 10000
positions per field, 256 KMZ entries, 32 MiB expanded KML/output. External links,
entities/DTDs, unsafe archive paths, excessive nesting/compression, and encrypted
archives are rejected. There is no implicit geometry repair, provider acquisition,
scientific acceptance, or fabricated observation generation in these workflows.

## Staged rollout and write-disable recovery

Keep both applications independently deployed. In a controlled backend
environment, set the five `AGRI_WORKSPACE_*` values above, run provisioning,
start the API, and start the worker in another backend process with the same
settings. The frontend only receives `VITE_API_BASE_URL`; rebuild it after an
origin change. No frontend checkout or Node.js is needed by the running API.

If rollout must be paused, stop the owned worker and restart the current API
without the `AGRI_WORKSPACE_*` settings. Keep its `AGRI_API_*` canonical read
settings. Writes/profile/jobs become blocked, while field/evidence reads retain
explicit current boundaries and archival filtering. This mode is covered by a
real-PostgreSQL regression. Restore the original workspace settings to resume;
do not drop tables, reverse applied migrations, or overwrite newly saved data.
An older API predating archival filtering is not a safe rollback target.

The canonical reader's original strict JSON DTOs remain unchanged. Field
versioning is carried in GET headers and dedicated mutation responses, not
added to old read bodies. New upload endpoints deliberately use raw bytes
instead of multipart; exports accept explicit field/boundary lists at `/exports`.
These choices are recorded in the generated contract and the frontend pin.
