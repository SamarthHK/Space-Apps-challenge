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
uv run --no-sync python -m agri_data.services.database
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
