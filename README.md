# Bhumi: frontend and backend together

One repository, **two application instances**: a Vite/Leaflet frontend and a
Python API, with a background import/export worker and PostgreSQL/PostGIS.
Use the `merged-app` branch. Both applications are included as ordinary files:
there are no submodules, sibling checkouts, local data copies or private services
that another machine must obtain from the original developer.

The app provides private sign-up/sign-in, profiles, a satellite Earth map,
polygon drawing, saved KML preview/confirmation, boundary history, original-file
downloads and GeoJSON/KML/KMZ exports. **AI analysis is unavailable.** The satellite
basemap is not NDVI or an agronomic result. New accounts have no seeded plots,
provider observations, passwords or recommendations.

## 1. Recommended: Docker Compose

Works with Linux containers on Windows, macOS and Linux, on x86-64 or ARM64.
Install [Git](https://git-scm.com/downloads) and either
[Docker Desktop](https://docs.docker.com/get-started/get-docker/) (Windows/macOS;
use Linux containers, with WSL 2 on Windows) or Docker Engine plus the
[Compose plugin](https://docs.docker.com/compose/install/) on Linux.
Use a current Compose release supporting health-based service dependencies.
Python, Node.js and PostgreSQL do not need to be installed on the host for this
option. The initial build needs internet access and several GB of disk space.

### Get the source

After the branch has been pushed:

```text
git clone --branch merged-app --single-branch https://github.com/SamarthHK/Space-Apps-challenge.git bhumi
cd bhumi
```

If you already have this branch checked out, start in its repository root.
All following commands run from that root unless stated otherwise.

### Configure your installation

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Open `.env` in your editor and set `POSTGRES_PASSWORD` to a **new, long random
database password**. A random alphanumeric value avoids shell/interpolation
surprises; quote values containing `$` or `#` with single quotes in this file.
Use literal values, not `${OTHER_VARIABLE}` references: the native launcher
intentionally does not expand variable references inside passwords.
There is deliberately no default password. Leave the other defaults for a
local-only installation. `.env` is ignored by Git and must not be shared.

This database password is **not** an application username/password. Create your
own application account in the browser after startup. The dummy account from
the original machine is not included.

### Build and start everything

These commands are the same in PowerShell, macOS and Linux terminals:

```text
docker compose up --build -d
docker compose ps -a
```

The `db` service creates PostgreSQL with PostGIS. The one-shot `init` service
applies the packaged canonical and private-workspace migrations, then exits
successfully. `api` and `worker` start after that; `frontend` waits for their
health checks. An `init` status of **Exited (0)** is expected, not a failure.
Existing recognized schemas are upgraded additively; unrelated schemas are
refused instead of overwritten.

Open **http://127.0.0.1:1080** and choose **Create an account**.
API health: **http://127.0.0.1:8080/api/v1/health**.
OpenAPI: **http://127.0.0.1:8080/api/v1/openapi.json**.
Use `127.0.0.1` consistently, not `localhost` for one instance and an IP for the
other: private cookies require the same hostname.

To save a plot: **My Land -> Draw Plot Boundary -> Finish boundary -> Save KML
for preview -> Confirm selected valid boundaries**. The backend retains the
original before confirmation, but creates no field until you confirm. Draw
around your actual parcel; no sample boundary is automatically generated.

### Services and ports

| Service | Purpose | Default host address |
| --- | --- | --- |
| `frontend` | Built static app, served by Nginx | `127.0.0.1:1080` |
| `api` | Private HTTP API | `127.0.0.1:8080` |
| `worker` | Durable KML preview/confirmation and exports | No published port |
| `init` | Explicit database/schema provisioning | No published port; exits after setup |
| `db` | PostgreSQL 17 plus PostGIS | `127.0.0.1:55432` |

The application containers use `db:5432` internally; the browser must use the
host addresses above, **not** Docker service names. Database credentials are
passed only to the database/backend services, never into the frontend image.
Containers can listen internally on all interfaces while Compose publishes only
the configured loopback/Tailscale address. API Host, Origin, CSRF and account
checks remain enforced; native wildcard/public binding is not enabled.

### Stop, restart and update

```text
docker compose logs --tail=100 init api worker frontend
docker compose down
docker compose up -d
```

`down` stops the installation but **retains the named PostgreSQL volume**.
Keep the same checkout/project name and `.env` when restarting. Moving/renaming
the Compose project can select a different volume and look like an empty
installation. Use `docker compose ls` to inspect projects.

After pulling source updates, back up the database, then run
`docker compose up --build -d`. Do not delete the volume to apply a migration.
`docker compose down --volumes` **permanently deletes this installation's
database**, including all users and uploaded originals; it is not a normal
restart command.

## 2. Native Python/Node setup

This option runs the API, worker and frontend directly on Windows, macOS or
Linux. Docker is optional: you may use it just for PostgreSQL/PostGIS.

Install:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python and
  locked dependencies. The commands below select **Python 3.12**; uv can download
  it if missing.
- [Node.js 22 or newer](https://nodejs.org/en/download) with npm.
- PostgreSQL 17 with PostGIS, either using the included `db` service or a native
  installation. On Windows, install the matching PostGIS package through
  Stack Builder; on Linux/macOS use your PostgreSQL/PostGIS packages.

Copy and edit the root `.env` as described above. Restore dependencies:

```text
uv sync --project backend --locked --python 3.12 --extra dev
npm --prefix frontend ci
```

For a Docker-hosted database only:

```text
docker compose up --build -d db
```

Do **not** also start the Compose API/frontend when using native services on the
same ports. With the database-only option, the root `.env` defaults
`DB_HOST=127.0.0.1` and `DB_PORT=55432` connect to that container.

For an existing native PostgreSQL installation, have an administrator create a
**dedicated empty database and role**, enable `CREATE EXTENSION postgis` in that
database, and grant the role ownership/schema-creation and application-write
permissions. Set `POSTGRES_DB`, `POSTGRES_USER`, `DB_HOST`, `DB_PORT` and the
database password in `.env` to match. The setup command does not install
PostgreSQL, create roles or enable server extensions. Native authentication can
also use a configured `PGPASSFILE` instead of `POSTGRES_PASSWORD`.

### Provision once, then run three terminals

Provision from the repository root:

```text
uv run --project backend --locked python -m agri_data.deployment init
```

Terminal 1, repository root:

```text
uv run --project backend --locked python -m agri_data.deployment api
```

Terminal 2, repository root:

```text
uv run --project backend --locked python -m agri_data.deployment worker
```

Terminal 3, repository root:

```text
uv run --project backend --locked python -m agri_data.deployment frontend
```

The native frontend command builds the app and serves it using Vite preview;
it is intended for this local/trusted-network setup, not public production.
It passes only public settings to Node, and sets both the API origin and
frontend port from the root `.env`. Re-run it after frontend changes.

Open **http://127.0.0.1:1080**. Keep all three terminals open; Ctrl+C stops the
service in that terminal, not the saved database. Starting the same service twice
fails on the occupied port instead of silently choosing another one.

Useful checks:

```text
uv run --project backend --locked python -m agri_data.deployment check storage
uv run --project backend --locked python -m agri_data.deployment check api
uv run --project backend --locked python -m agri_data.deployment check worker
```

`init` can be re-run for additive upgrades and does not reset profiles, accounts
or plots. The portable launcher always selects private account mode. The older
low-level backend supports shared compatibility, but is **not** the command to
use for this private installation.

## Configuration, storage and access

| Root `.env` setting | Default / purpose |
| --- | --- |
| `APP_HOST` | `127.0.0.1`; or the host machine's actual Tailscale IPv4 address |
| `FRONTEND_PORT`, `API_PORT` | `1080`, `8080`; must differ |
| `POSTGRES_DB`, `POSTGRES_USER` | `bhumi`, `bhumi`; fixed for the life of an initialized database unless migrated |
| `POSTGRES_PASSWORD` | Required for Docker, no default; use your own secret |
| `DB_HOST`, `DB_PORT` | Native endpoint `127.0.0.1:55432`; Compose uses `db:5432` inside the app containers |
| `CANONICAL_SCHEMA` | `agri_bhumi_data`; private projects, field geometry and canonical evidence structure |
| `WORKSPACE_SCHEMA` | `agri_bhumi_workspace`; accounts, password hashes, sessions, profiles, original bytes, jobs and revisions |
| `DEPLOYMENT_ID` | `bhumi`; stable identity for accounts and worker scope |
| `AUTH_SESSION_SECONDS` | `43200` (12 hours), with bounds 60-604800 |

Do not change schema/deployment names to recover a login: this selects another
scope, not an account reset. Changing `POSTGRES_PASSWORD` in `.env` does not
change the password of an already initialized PostgreSQL role; coordinate an
actual database password change before updating the configuration.

Data lives in PostgreSQL, not in Git, the browser, or the containers' disposable
filesystems. Back up the **entire application database**, including both schemas,
using PostgreSQL backup tools before migrations. Restoring only one schema can
break ownership and source links. Raw database directories must not be copied
while the server is running as a substitute for a proper backup.

For another device on your Tailscale network, set `APP_HOST` to this machine's
Tailscale IPv4 address and rebuild/restart both instances. Access both ports using
that same IP. This repository deliberately rejects public hosts, LAN wildcard
binding, mismatched cookie hostnames and unauthenticated private-mode fallback.
The HTTP setup is **local/tailnet-only**, not a public production deployment.
Cookies do not isolate ports; trust every service on the same hostname.
Do not use Tailscale Funnel or public port forwarding.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Compose says `POSTGRES_PASSWORD` is missing | Create the root `.env`, set a nonempty password, and run from the repository root. |
| A port is already allocated | Stop only your own old instance, or choose free `API_PORT`/`FRONTEND_PORT`/`DB_PORT` values. Rebuild the frontend after changing the API address. |
| `init` fails | Inspect `docker compose logs init db`. Confirm PostGIS, database identity, schema names and permissions. Do not erase the volume or bypass migration checks. |
| Login fails after a password/config change | Database credentials and application account passwords are different. Existing PostgreSQL passwords are not changed by editing `.env`. |
| Cross-origin/cookie error or signed-out loop | Use the exact same hostname for frontend/API; remove stale per-frontend `.env.local` overrides and use the root launcher. |
| Draw/import/export controls are disabled | Check the `worker` health and matching database/schema/deployment settings. API liveness alone does not establish worker readiness. |
| Blank satellite imagery but fields still load | Esri/OSM tiles require internet access. Try the street basemap; imagery availability is independent of saved geometry. |
| No observations or recommendations | Fresh accounts contain no acquired provider data. Saving KML does not execute an AI pipeline. Empty/unavailable is intentional, not a demo fallback. |
| Native geospatial dependency installation fails | Use the documented Python 3.12/uv lock and a supported x86-64/ARM64 OS; prefer Docker if compatible binary wheels are unavailable. |

There is currently no password-recovery UI, account administration, MFA or public
HTTPS deployment configuration. Keep your login credentials safe. Original
uploads and history are retained; account/file retention administration remains
future work.

## Development and verification

```text
npm --prefix frontend test
```

For backend unit/configuration tests, enter `backend` and run:

```text
uv run --locked --extra dev python -m pytest tests/test_deployment.py tests/api/test_foundation.py
```

For private browser acceptance on a fresh PostgreSQL/PostGIS database, first
restore dependencies and configure root `.env` as in native setup. Install
Playwright Chromium if it is not already available:

```text
npm --prefix frontend exec -- playwright install chromium
```

On Linux, Playwright may require its documented OS dependencies
(`playwright install --with-deps chromium` on a supported distribution).
Then, from the repository root, Windows PowerShell:

```powershell
uv run --project backend --locked python backend\scripts\workspace_browser_acceptance.py --frontend frontend --mode accounts --empty-private
```

macOS/Linux:

```bash
uv run --project backend --locked python backend/scripts/workspace_browser_acceptance.py --frontend frontend --mode accounts --empty-private
```

This starts separate owned services on 18084/11084, provisions fresh isolated
schemas using the actual portable startup command, exercises private accounts and
drawn KML in Chromium, then removes only its test schemas/processes. It does not
need the original developer's provider corpus or saved accounts, and it refuses
port collisions. Logs/screenshots remain under `backend/.local/workspace-acceptance`.
The database role must be allowed to create/drop these disposable test schemas.
The older shared/read-evidence suites require a separately prepared authentic
corpus and explicit `AGRI_TEST_*` configuration; do not substitute fabricated
science for those prerequisites.

The native code, source relocation, provisioning, cookie isolation and KML flows
are covered by targeted tests. The Compose configuration and x86-64/ARM64 base
image manifests were checked, but **container builds/startup were not executed
on the authoring machine because it has no Docker engine**. The Windows native
path was exercised; macOS/Linux runtime execution still needs platform testing.
These checks do not claim production or scientific readiness.

When changing API schemas, export `backend/docs/openapi.json`, commit the backend
change, then run from the repository root:

```text
node frontend/scripts/pin-contract.js backend
```

The pin records the committed artifact path/hash, including the nested backend
location. See `backend/docs/private_workspace.md` for protocol details and
`frontend/README.md` for UI behavior. Legacy scientific planning documents and
unused demo sources remain as history; the current app does not load demo
recommendations or seed the old sample KML.

## Source layout and provenance

```text
backend\       Python package, locked dependencies, API, worker, migrations, tests
frontend\      Vite/Leaflet app, pinned API schema, tests, static-server image
database\      PostgreSQL/PostGIS image and extension initialization
compose.yaml   Independent services and persistent database volume
.env.example   Secret-free configuration template
```

This branch combines backend `776a409` and frontend `d8d6275` while preserving
both Git histories. It does not incorporate concurrent model research changes,
the original machine's PostgreSQL cluster, private KML uploads, accounts or
credentials. Existing standalone branches and hosted services are not modified
by this combined checkout.
