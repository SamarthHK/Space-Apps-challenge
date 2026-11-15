# Running the shared-workspace API

No accounts are implemented by request. Every device permitted to reach this
service shares the same access. Tailscale access rules, not CORS, are the access
boundary. Do not publish it through Funnel, a public proxy or port forwarding.
The server refuses wildcard/public bind addresses and disables proxy-header trust.

Restore dependencies with `uv sync --locked --extra dev`. From the backend root:

```powershell
$env:AGRI_API_HOST = (tailscale ip -4).Trim()
$env:AGRI_API_PORT = "8000"
$env:AGRI_ALLOWED_ORIGINS = "http://${env:AGRI_API_HOST}:1080"
uv run --locked python -m agri_data.api
```

Use the actual Tailscale address in the browser, not `0.0.0.0`. HTTP on the
Tailscale interface travels within the encrypted tailnet. Public deployment
requires authentication and HTTPS; this account-free mode is not suitable.

For loopback-only development use `AGRI_API_HOST=127.0.0.1` and
`AGRI_ALLOWED_ORIGINS=http://localhost:1080`.
Configuration is explicit environment only; `.env` is not automatically read.

Implemented foundation:

- `GET /api/v1/health`: liveness and contract revision, not provider/DB health.
- `GET /api/v1/workspace`: shared access mode and truthful capability states.
- `GET /api/v1/openapi.json`: schema for implemented operations only.

The read increment also implements listFields/getField, listObservations/
getObservation/listObservationEvidence. Configure data access explicitly:

```powershell
$env:AGRI_API_DATABASE_URL = "postgresql://<role>@127.0.0.1:<port>/<database>"
$env:AGRI_API_DATABASE_NAME = "<database>"
$env:AGRI_API_DATABASE_USER = "<role>"
$env:AGRI_API_SCHEMA = "agri_contracts"
$env:AGRI_API_PROJECT_IDS = "public_reference"
# Configure PGPASSFILE through your secret store; never put passwords in source.
```

Use a prepared, provenance-verified database and an appropriate restricted
deployment role; no migration or acceptance acquisition is run by the API.
The canonical schema (including canonical_fields, canonical_observations and
observation_evidence) must already exist. Database preparation remains a
separate backend prerequisite. The API issues only read-only transactions,
checks database/user/schema identity and applies the project allow-list to
every field and nested evidence query. It does not expose all projects.
Absent configuration or schema returns a blocked capability and HTTP 503, not
an empty successful query. Profiles and all mutations remain unimplemented.

Multiple boundary versions require explicit selection through
`GET /api/v1/fields/{field_id}?boundary_id=...`. The API does not guess "current"
from hashes or retrieval dates; area stays null without recorded metric CRS.
Canonical observations include pending status, units, provider-local dates,
conflicting revisions and evidence counts; raw acquisition copies are not
presented as independent observations.

Collections accept `limit` (1-200) and opaque `cursor`. Cursors bind to the
filters and a hash of the complete response snapshot: a changed snapshot returns
409; filter changes/tampering/server restart return 400. Restart from page one.
Current pagination materializes each selected result in memory; this read slice
targets the small reference corpus, not unbounded production archives. SQL
keyset/snapshot pagination is required before scaling.

Foundation validation: `uv run --locked python -m pytest tests\api\test_foundation.py -q`.
These tests start a real loopback HTTP server, exercise origin/host checks,
request IDs, errors and metadata, and verify generated OpenAPI. No provider
responses or agricultural records are fabricated.

Data validation requires a real populated canonical corpus. Supply the same
data configuration with prefix `AGRI_TEST_` rather than `AGRI_API_`, then run
`uv run --locked python -m pytest tests\api -q`. Tests fail, not skip, when
authentic evidence/database prerequisites are absent. The data tests reconcile
API values with checksummed provider bytes and PostGIS, test forbidden project
access, pagination/filter errors and enforce read-only transactions.

Export the implemented contract:

```powershell
uv run --locked python -m agri_data.api --export-openapi docs\openapi.json
```
