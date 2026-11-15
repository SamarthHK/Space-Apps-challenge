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
separate backend prerequisite. The canonical reader issues only read-only transactions,
checks database/user/schema identity and applies the project allow-list to
every field and nested evidence query. It does not expose all projects.
Absent configuration or schema returns a blocked capability and HTTP 503, not
an empty successful query.

Shared profiles, versioned field create/update/archive, durable import
preview/confirmation and GeoJSON/KML/KMZ exports are implemented separately.
See [shared_workspace.md](shared_workspace.md) for the five explicit workspace
database/ID settings, additive provisioning, writer permissions, worker command,
limits, browser acceptance harness, and safe write-disable recovery.
No users, authentication cookies or private-profile migration are introduced.
Optional reference-model execution is configured independently below. The API
never provisions application state on a GET.

Legacy ambiguous boundary versions require explicit selection through
`GET /api/v1/fields/{field_id}?boundary_id=...`. The API does not guess "current"
from hashes or retrieval dates. New field writes record an explicit current
boundary; older versions remain selectable. Area stays null without recorded metric CRS.
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
`uv run --locked python -m pytest tests\api\test_data.py -q`. The complete API
suite also needs the genuine model artifact and optional dependencies below.
Tests fail, not skip, when
authentic evidence/database prerequisites are absent. The data tests reconcile
API values with checksummed provider bytes and PostGIS, test forbidden project
access, pagination/filter errors and enforce read-only transactions.

Export the implemented contract:

```powershell
uv run --locked python -m agri_data.api --export-openapi docs\openapi.json
```

## Optional Indian reference model

This is **historical GAEZ reference suitability**, not a next-season field or
rotation recommendation. It uses saved native grid contexts for 1981-2000 or
2001-2020 and the trained crop/use vocabulary. It does not acquire data, retrain
weights, require PostgreSQL or attach reference cells to private fields.
The `reference_suitability` capability is independent of `recommendations`.

Use the existing separate ML environment rather than replacing the shared
default environment. If it needs restoration, install the declared extras:

```powershell
$env:UV_PROJECT_ENVIRONMENT = ".local\ml-env"
uv sync --locked --extra ml --extra dev --extra india --extra india-ml --python 3.12
```

For the retained, reviewed model bundle:

```powershell
$env:PYTHONPATH = "src"
$env:AGRI_API_HOST = "127.0.0.1"
$env:AGRI_API_PORT = "8000"
$env:AGRI_ALLOWED_ORIGINS = "http://localhost:1080"
$env:AGRI_REFERENCE_MODEL_DIR = (Resolve-Path "data\exports\india-reference-models-v1").Path
$env:AGRI_REFERENCE_MODEL_ID = "0696c370daa2825c79c43943daef090e8788e561f1c9f2dce7e2eda2493720c3"
& .local\ml-env\Scripts\python.exe -m agri_data.api
```

Select a free port or coordinate an existing server restart; do not terminate
another session's service. The directory and model ID must be configured
together. Choose an explicitly reviewed new model ID when upgrading; do not
accept a browser-supplied path or silently change the pinned model.
No model files are distributed through these endpoints.

From another PowerShell terminal, discover the real supported input before
scoring it:

```powershell
$base = "http://127.0.0.1:8000/api/v1"
$model = (Invoke-RestMethod "$base/reference-model").data
$contexts = Invoke-RestMethod "$base/reference-model/contexts?model_id=$($model.model_id)&period_id=HP0120&limit=5"
$body = $model.example_request | ConvertTo-Json -Depth 10
$result = Invoke-RestMethod "$base/reference-model/predictions" -Method Post `
  -Headers @{ Origin = "http://localhost:1080" } -ContentType "application/json" -Body $body
$result.data
```

The example is an actual saved context. To select another, copy its
`context_id`, `analysis_start` and `analysis_end` together from the contexts
response. Select only trained crop/system combinations from metadata;
up to 100 bounded candidate IDs are accepted. The POST is stateless and
returns 200, not a job or persisted recommendation; it needs the configured
Origin but no idempotency key. Unsupported crops are withheld, and no eligible
candidates produces a successful abstention rather than fallback scores.

The loader verifies the pinned model, caches it once and serves one model
operation at a time per API process, on CPU with two inference threads and a
shared-memory reserve. Overlapping operations receive retryable 503
`reference_model_busy`. Missing dependencies/artifacts or changed model files
return redacted 503 and block this capability; repair the setup and restart.
The rest of the API, including liveness, remains available. A stale client model
ID returns 409; unsupported reference intervals return 422.

Scores are GAEZ index points and softmax values are relative preferences, not
farming-success probabilities. Responses retain missing features, native
support, source IDs, untrained-category/extrapolation warnings and unassessed
soil/calendar/rotation requirements. Do not render reference suitability as
the unfinished field-recommendation feature.

Model/API checks use the authentic artifact and start/stop their own loopback
server without replacing an existing service:

```powershell
$env:AGRI_INDIA_MODELS = (Resolve-Path "data\exports\india-reference-models-v1").Path
& .local\ml-env\Scripts\python.exe -m pytest tests\api\test_reference.py -q
```

The contract additions are exported in `docs\openapi.json`. The separate
frontend still needs to adopt that snapshot and implement a reference-only
screen; no frontend integration is claimed by this backend increment.
