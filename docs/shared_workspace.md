# Shared application state

Run the existing API and frontend as separate instances. No accounts, sessions,
cookies, private-user profile migration, or model inference are introduced.
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
