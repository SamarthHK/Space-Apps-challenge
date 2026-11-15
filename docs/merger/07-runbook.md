# 07. Independent startup and integration runbook

**Historical shared-mode runbook.** The current private UI/KML deployment is
documented in [09-ui-restoration.md](09-ui-restoration.md). Do not use shared mode
as a fallback for private accounts. The deployment statements below describe
the earlier shared handoff, not the current hosted state.

This runbook describes the implemented release in
[08-implementation.md](08-implementation.md), not the authenticated donor pair.
The existing live services were not restarted or reconfigured. Provisioning
and normal deployment below remain deliberate operator actions.

## Source and prerequisites

| Application | Local checkout | Branch |
| --- | --- | --- |
| Backend API and worker | `D:\Code\SpaceApps\Space-Apps-challenge\.local\integration-backend` | `backend` |
| Independent frontend | `D:\Code\SpaceApps\Space-Apps-challenge-frontend` | `frontend` |

The original `Space-Apps-challenge` checkout is being used concurrently on
`backend-ai`; do not switch, reset or deploy it as this release. Its nested
integration worktree is a maintained source checkout, not disposable cache.
The named `Space-Apps-challenge-backend` and its nested frontend remain donors.
These local release commits have not been pushed to GitHub.

Each application also works from its own unrelated deployment directory or
machine. The paths above are examples, not runtime coupling. Backend needs its
own locked Python environment and prepared PostgreSQL/PostGIS data. Frontend
needs Node.js >=22 and its npm lock for building, but its deployed static
artifact does not require Python or access to the backend filesystem.

Restore missing backend dependencies with `uv sync --locked --extra dev` in an
integration-owned environment; restore missing frontend dependencies with
`npm ci`. Do not repair somebody else's active environment. The backend API
does not prepare canonical schemas, fetch providers or seed data at startup.
Use explicitly authorized prepared projects and actual DB/role/schema names.

Check port ownership before starting anything. A collision is not permission
to stop another process. Supply credentials through secure environment/PGPASSFILE
handling; never put passwords in Git, terminal examples or `VITE_*` variables.

## Backend configuration

Use a dedicated backend terminal. Replace every placeholder with actual
prepared identifiers; the example DSNs contain no password.

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge\.local\integration-backend'
$env:AGRI_API_HOST = '127.0.0.1'
$env:AGRI_API_PORT = '8000'
$env:AGRI_ALLOWED_ORIGINS = 'http://127.0.0.1:1080'

$env:AGRI_API_DATABASE_URL = 'postgresql://<reader-role>@127.0.0.1:<db-port>/<database>'
$env:AGRI_API_DATABASE_NAME = '<database>'
$env:AGRI_API_DATABASE_USER = '<reader-role>'
$env:AGRI_API_SCHEMA = '<prepared-agri_-schema>'
$env:AGRI_API_PROJECT_IDS = '<project-id-1>,<project-id-2>'

$env:AGRI_WORKSPACE_DATABASE_URL = 'postgresql://<writer-role>@127.0.0.1:<db-port>/<database>'
$env:AGRI_WORKSPACE_DATABASE_NAME = '<database>'
$env:AGRI_WORKSPACE_DATABASE_USER = '<writer-role>'
$env:AGRI_WORKSPACE_SCHEMA = 'agri_workspace'
$env:AGRI_WORKSPACE_ID = '<stable-workspace-id>'
```

Configure all five workspace values together, or none. Workspace ID is a stable
operator-selected identifier, not a user ID or a transient project list.
Canonical and application schemas must use the same PostgreSQL endpoint/database
for atomic field/job transactions, but separate roles and schemas are supported.
Canonical reads remain read-only. The writer needs the documented application
and field/boundary/source-asset privileges, not scientific-observation writes;
see backend `docs\shared_workspace.md`.

Under an authorized setup role, apply the additive workspace migrations and
provision an empty shared profile:

```powershell
& .\.venv\Scripts\python.exe -m agri_data.workspace.admin provision
& .\.venv\Scripts\python.exe -m agri_data.workspace.admin check
```

Repeat provisioning on upgrade to apply new migrations. It does not reset
existing values or copy private donor profiles. GET never provisions records.
Use the intended runtime role/settings when launching services:

```powershell
& .\.venv\Scripts\python.exe -m agri_data.api
```

In another backend terminal, supply the same workspace/canonical configuration
and its secure credentials, then run:

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge\.local\integration-backend'
& .\.venv\Scripts\python.exe -m agri_data.workspace.worker
```

PowerShell environment changes do not propagate into an unrelated terminal.
The worker is backend infrastructure, not a second browser-facing API.
Provisioning does not start it. A matching recent heartbeat enables import/
export capabilities; existing job status remains readable while it is offline.
`--once` processes at most one queued job, not a replacement for a running worker.
Python does not implicitly load `.env`; use the module launcher above, not the
authenticated donor's factory or migration commands.

## Independent frontend

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge-frontend'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
$env:FRONTEND_HOST = '127.0.0.1'
npm run build
npm run preview
```

Open `http://127.0.0.1:1080`. The API origin has no `/api/v1` suffix.
Changing the origin after a build requires rebuilding; the frontend receives
no DB connection settings. `npm run dev` is an alternative for development.

For Tailscale, use the actual permitted literal IPs and exact browser origin on
each machine. Validators permit loopback/Tailscale addresses, not arbitrary
public/LAN/MagicDNS hosts or wildcard binds. Do not expose account-free shared
access through Funnel or a public proxy. CORS is not authentication.

## Readiness and a manual journey

```powershell
curl.exe --fail-with-body --max-time 10 `
  -H 'Origin: http://127.0.0.1:1080' `
  'http://127.0.0.1:8000/api/v1/workspace'
```

Check actual capability readiness, not only `/health`: fields/observations need
prepared canonical data, profile needs provisioned application storage, field
writes need a compatible writer, and imports/exports need the matching worker.

Inspect a stored field/boundary and its canonical evidence, preserving pending
labels. Save a shared profile and read it from another browser. Draw or explicitly
enter geometry, save/reload, edit and archive without deleting history. Upload a
KML/KMZ/GeoJSON file, inspect the unsaved preview, explicitly select candidates,
confirm, reload while monitoring the job, and download a real geometry export.
Conflicts/lost responses retain drafts and require deliberate resolution; they
must not generate duplicate writes or invented observations.

## Repeatable isolated checks

In a dedicated backend test terminal, supply the five prepared-data settings:
`AGRI_TEST_DATABASE_URL`, `AGRI_TEST_DATABASE_NAME`, `AGRI_TEST_DATABASE_USER`,
`AGRI_TEST_SCHEMA`, and `AGRI_TEST_PROJECT_IDS`. Use an authorized test role
able to create/drop its own schemas. Do not inherit live API/workspace settings.

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge\.local\integration-backend'
& .\.venv\Scripts\python.exe -m pytest tests\api -q
& .\.venv\Scripts\python.exe scripts\workspace_browser_acceptance.py `
  --frontend 'D:\Code\SpaceApps\Space-Apps-challenge-frontend'
```

The browser harness runs frontend units/build/browser cases, copies authentic
scoped data into owned canonical/application schemas, and starts/verifies its
own API, worker and static server. It refuses occupied ports (18084/11084 by
default), does not replace the normal frontend build, and cleans up only its
schemas/processes. Logs remain under backend `.local\workspace-acceptance`.
Write specs require its `TEST_WRITES_ISOLATED=1` guard.

Use installed Playwright Chromium, with `PLAYWRIGHT_BROWSERS_PATH` if needed.
Install it only if the runner reports it missing. Do not run the full mutating
browser suite against live canonical data. For the read-only frontend suite
against a deliberately configured API/build, use
`npm run test:browser -- workspace.spec.js`; its preview port must also be free.

After a tested backend contract commit, pin from the correct release checkout:

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge-frontend'
node scripts\pin-contract.js 'D:\Code\SpaceApps\Space-Apps-challenge\.local\integration-backend'
```

This development command reads committed Git artifact bytes and records the
backend SHA/checksum; it is not needed by the deployed frontend.

## Recovery and remaining operational work

To pause writes, stop only the worker you own and restart the current API
without all `AGRI_WORKSPACE_*` settings, retaining its canonical read settings.
This blocks profile/mutations/jobs while preserving current-boundary and archive
filtering in reads. Restore the workspace settings to resume. Do not downgrade
to an older archive-unaware API or reverse migrations over saved writes.

Back up application assets/revisions/jobs together with canonical field/boundary
dependencies. A physical database backup/restore rehearsal and production-scale
capacity/retention checks remain operator gates, not checks already passed.
No automatic retention cleanup, public authentication rollout or scientific
acceptance is supplied by this release.
