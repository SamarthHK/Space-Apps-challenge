# Local backend

Python 3.12 is selected in `.python-version`. `pyproject.toml` is authoritative;
`uv.lock` locks the graph and `requirements.txt` is generated, not edited separately.

```powershell
uv sync --locked --extra dev
uv run --no-sync pytest tests\api -q
uv run --no-sync uvicorn agri_data.api.app:create_app --factory --host 0.0.0.0 --port 8080
```

The API does not import the legacy demo pipeline. `/health` is liveness;
`/ready` checks a real PostgreSQL/PostGIS connection and checksummed migrations,
returning 503 if either is unavailable. `/api/v1/meta`
reports unavailable capabilities honestly. The old generated-data tests are not
scientific acceptance evidence and are not part of this new API test selector.

Use `.env.example` as configuration guidance, with secrets only in ignored `.env`
or process environment variables. Bind frontend development to port 1080, and
browse `http://localhost:1080` with API origin `http://localhost:8080`.
`0.0.0.0` is a bind address, not an allowed browser origin. Production requires
HTTPS origins, Secure cookies and an explicit PostgreSQL connection.

To update dependencies after editing the manifest:

```powershell
uv sync --extra dev
uv export --extra dev --no-hashes --no-emit-project --output-file requirements.txt
```

## Native Windows PostgreSQL

Docker was unavailable on the audited machine. Native PostgreSQL 17.12 and
PostGIS 3.6.2 run on `127.0.0.1:55432`, with binaries, data and credentials in
ignored `.local`. The newer PostGIS 3.7.0 Windows archive failed to load because
its native library chain lacked DLLs; no service acceptance was claimed for it.

Official archives used:

- PostgreSQL: `https://sbp.enterprisedb.com/getfile.jsp?fileid=1260667`
  (linked by `https://www.enterprisedb.com/download-postgresql-binaries`).
- PostGIS: `https://download.osgeo.org/postgis/windows/pg17/archive/postgis-bundle-pg17-3.6.2x64.zip`.

Extract PostgreSQL to `.local\postgresql` (containing `pgsql`) and PostGIS to
`.local\postgis-3.6.2` (containing `postgis-bundle-pg17-3.6.2x64`). Then, for a
**new** cluster only:

```powershell
uv run --no-sync python scripts\local_database.py prepare
```

Preparation restricts `.local` ACLs to the current Windows account, generates
random SCRAM credentials and refuses to replace an existing cluster. Start via
`pg_ctl`, which uses PostgreSQL's restricted-token launcher on Windows; launching
`postgres.exe` directly from an elevated terminal is refused.

```powershell
& .\.local\postgresql\pgsql\bin\pg_ctl.exe -D .\.local\pgdata -l .\.local\postgresql.log -o "-h 127.0.0.1 -p 55432" -w start
uv run --no-sync python scripts\local_database.py configure
uv run --no-sync python -m agri_data.api.admin migrate
uv run --no-sync pytest tests\api -q
```

Configure creates only the named local `agri_backend` database, non-superuser
`agri_app` role and PostGIS extension; it writes `.env` only when absent. Treat
`.local\database-admin.json` and `.env` as secrets. Migrations run as the app role
in `AGRI_DATABASE_SCHEMA` (default `agri_app`), never automatically at API startup.
Production should use a separately privileged migration role.

Database tests create a unique `acceptance_*` schema on the configured real
server and remove only that schema. They exercise application identity records,
not fabricated agricultural records, and fail rather than skip if PostgreSQL
is unavailable. The native server is not installed as a machine-wide service.

```powershell
& .\.local\postgresql\pgsql\bin\pg_ctl.exe -D .\.local\pgdata -w stop
```

## Sessions and profiles

Create an actual local login explicitly; no default accounts or passwords ship:

```powershell
uv run --no-sync python -m agri_data.api.admin create-user YOUR_LOGIN
uv run --no-sync python -m agri_data.api.admin revoke-sessions YOUR_LOGIN
```

Passwords are entered through a hidden prompt and stored using Argon2id. The API
uses hashed opaque server sessions, not browser localStorage credentials. Sessions
expire after 12 hours by default; pre-login CSRF contexts after 10 minutes.
Login and CSRF bootstrap are database-rate-limited; retries receive 429 with
`Retry-After`. Adjust `AGRI_LOGIN_ATTEMPT_LIMIT` / `AGRI_LOGIN_WINDOW_SECONDS`
deliberately for deployments with shared client IPs.

Browser flow, always using `credentials: "include"` and the same hostname:

1. `GET /api/v1/auth/csrf` with the allowed browser `Origin`; keep the returned
   `csrf_token` in memory. The browser receives a HttpOnly context cookie.
2. `POST /api/v1/auth/session` with JSON `{login, password}` and `X-CSRF-Token`.
   On success the context is consumed, the session cookie rotates and the response
   includes user identity, expiry and a new session CSRF token.
3. `GET /api/v1/auth/session` restores session state after refresh; 401 means login
   is required. `GET /api/v1/me/profile` returns the authenticated user's empty or
   saved profile, with no seeded personal data.
4. `PATCH /api/v1/me/profile` requires `version`, at least one mutable property,
   allowed Origin and session `X-CSRF-Token`. Omitted fields remain unchanged;
   explicit null clears a field. Stale writes return 409; revisions persist.
5. `DELETE /api/v1/auth/session` requires the same Origin/CSRF protection, revokes
   the session and returns 204. Revocation and account deactivation are checked
   against PostgreSQL on every request.

Only session/profile plus health/meta routes are operational. Fields, scientific
data, recommendations, markets and plans remain pending. The separate frontend
worktree at `.local\frontend` now integrates login/profile and gates other screens.
`docs\openapi.json` is generated from implemented routes, not the entire planned
surface. Regenerate and compare it when changing a route:

```powershell
uv run --no-sync python -m agri_data.api.admin openapi docs\openapi.json
uv run --no-sync pytest tests\api -q
```

For browser acceptance against the independent production frontend:

```powershell
uv run --no-sync python scripts\browser_acceptance.py --frontend .local\frontend
```

The harness requires the frontend npm graph and Playwright Chromium already
installed. It provisions a temporary account/schema and separate loopback API,
uses the production preview, then cleans up the acceptance-owned resources and
restores the normal frontend build. It does not contact scientific providers or
count generated boundaries as authentic field acceptance.
