# 07. Independent startup and integration runbook

This runbook distinguishes **existing read-only interfaces** from future shared
profile work. It was not executed as a deployment during this planning task.
Use it after T0 delivers a reproducible approved backend environment and a
prepared, scoped PostgreSQL/PostGIS dataset.

## Current source choices

Frontend: F `Space-Apps-challenge-frontend`.
Backend: A `Space-Apps-challenge`.
B and its nested P frontend are profile donors, not services to start alongside
the final pair. Do not start both frontends on the same address/port.

Use one terminal/process environment per application. Each application should
also work from an arbitrary independent checkout on another machine.
The absolute paths below are local development examples, not runtime coupling.

## Before starting

1. Confirm approved source SHAs and clean prerequisite publication. A's current
   dirty worktree/partial `.venv` is not the reproducible release.
2. In a clean integration-owned backend checkout, restore the chosen locked
   development environment with the supported Python version. Current backend
   documented command is `uv sync --locked --extra dev`; do not run it over an
   active owner's environment without coordination.
3. Supply a prepared canonical database/schema and explicit project allow-list.
   The API does not initialize/migrate/seed or fetch providers on startup.
   Canonical views/tables and their actual preparation code must be available.
4. Inspect port availability before starting anything. Do not kill or reuse a
   listener merely because it occupies a documented port. Choose another
   configured test port or coordinate with its owner.
5. Keep credentials in process environment/secret handling such as PGPASSFILE.
   Do not print, commit or place them in Vite variables.

## Terminal 1: existing backend read API

From the selected backend checkout, with a working isolated environment:

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge'
$env:AGRI_API_HOST = '127.0.0.1'
$env:AGRI_API_PORT = '8000'
$env:AGRI_ALLOWED_ORIGINS = 'http://127.0.0.1:1080'

# Supply all five data settings together using actual prepared identifiers.
$env:AGRI_API_DATABASE_URL = 'postgresql://<reader-role>@127.0.0.1:<db-port>/<database>'
$env:AGRI_API_DATABASE_NAME = '<database>'
$env:AGRI_API_DATABASE_USER = '<reader-role>'
$env:AGRI_API_SCHEMA = '<prepared-agri_-schema>'
$env:AGRI_API_PROJECT_IDS = '<project-id-1>,<project-id-2>'

& .\.venv\Scripts\python.exe -m agri_data.api
```

Replace placeholders before running. The API verifies DB/user identity and
schema requirements; no wildcard projects. The DSN is plain PostgreSQL syntax,
not B's SQLAlchemy `postgresql+psycopg` setting.

A reads environment variables explicitly, not B's ignored `.env`. Its
`python -m agri_data.api` launcher supplies both network and data settings.
Do not substitute B's `uvicorn ...create_app --factory` command: A's factory
without `data_settings` does not automatically load the configured data scope.

For Tailscale, set API host to the actual permitted Tailscale IP and allow the
exact frontend browser origin. Configure F to that API origin. Current
validators allow loopback/Tailscale literal addresses, not arbitrary public,
LAN or MagicDNS hostnames. Do not use `0.0.0.0` as a bind/browser shortcut.

## Terminal 2: existing standalone frontend

Restore dependencies only when setting up the selected clean build environment
or they are missing. Current F requires Node >=22 and has an npm lock.

```powershell
Set-Location 'D:\Code\SpaceApps\Space-Apps-challenge-frontend'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
$env:FRONTEND_HOST = '127.0.0.1'

npm run build
npm run preview
```

Open `http://127.0.0.1:1080`. `npm run dev` is an alternative for development;
preview serves the built artifact. Changing an environment variable after a
build does not rewrite the bundled API origin. Rebuild deliberately.

Use consistent hostnames for deterministic Host/Origin checks, even without
cookies. The frontend/API may run on different machines; each gets its actual
host/origin configuration. Do not copy the other application's `.env`.

## Readiness and manual smoke journey

```powershell
curl.exe --fail-with-body --max-time 10 `
  -H 'Origin: http://127.0.0.1:1080' `
  'http://127.0.0.1:8000/api/v1/health'

curl.exe --fail-with-body --max-time 10 `
  -H 'Origin: http://127.0.0.1:1080' `
  'http://127.0.0.1:8000/api/v1/workspace'
```

Health must report the shared revision, but does not prove DB readiness.
Workspace must report intended project IDs and ready `fields`/`observations`;
503 or blocked state is a real prerequisite failure, not empty data.

In the browser: connect, list fields, explicitly select a boundary where
ambiguous, display stored geometry/metrics, filter canonical observations, open
source evidence, paginate, reconnect, and navigate all seven views. Pending
records remain labelled and unavailable domains remain unavailable.

During profile implementation, add a documented DB/schema readiness check for
the writer. Do not call B `/ready` against A or report all capabilities healthy
because one shared liveness request succeeds.

## Current focused validation interfaces

From F:

```powershell
npm test
npm run build
$env:TEST_API_ORIGIN = $env:VITE_API_BASE_URL
npm run test:browser
```

The existing browser runner starts its own preview on `127.0.0.1:1080` and
refuses reuse. Stop only a preview process you own or select a parameterized
test configuration after implementing it. API origins must allow the runner's
origin; the build and TEST_API_ORIGIN must agree. The browser suite requires
the prepared reference data. Install Chromium only if the runner reports it
missing; do not substitute fabricated provider fixtures.

From A, after its own environment is working:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests\api\test_foundation.py -q
& .\.venv\Scripts\python.exe -m pytest tests\api\test_data.py -q
```

Foundation tests expect no API data configuration in their temporary server
environment; use an isolated test process with `AGRI_API_DATABASE_*`,
`AGRI_API_SCHEMA` and `AGRI_API_PROJECT_IDS` unset for that selector.
Data tests take real prepared settings with `AGRI_TEST_` replacing `AGRI_API_`.
Missing data prerequisites fail rather than skip. Do not run mutating
engineering-health/proof/acquisition CLI commands just to make these GETs pass.

## Future shared-profile rollout

T3 must supply real workspace-schema migration/provisioning commands, writer
settings and diagnostics; none exists in A today. Do not run B
`agri_data.api.admin migrate` and assume it provisions a shared profile.

Deploy the additive `/profile` contract, verify storage and write preflight,
export/pin the artifact, then deploy F with the new profile component. Confirm
cross-browser save/read, stale If-Match conflict and unaffected field/evidence
journeys. Record the backend/frontend SHA pair and contract hash.

No login, session cookie, default user, second API service or backend-served
frontend build is required. Shut down only integration-owned processes by
their actual process/session IDs, leaving unrelated services and persistent
data intact.
