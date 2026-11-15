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

No profiles, agricultural records or write operations are exposed by this first
increment. Unsupported capabilities remain `not_implemented`; no demo fallback.

Validation: `uv run --locked python -m pytest tests\api -q`.
These tests start a real loopback HTTP server, exercise origin/host checks,
request IDs, errors and metadata, and verify generated OpenAPI. No provider
responses or agricultural records are fabricated.

Export the implemented contract:

```powershell
uv run --locked python -m agri_data.api --export-openapi docs\openapi.json
```
