# Private accounts and plot ownership

The owner approved private accounts for the restored UI. The API and frontend
remain separate instances; no AI model is run by registration, drawing or import.
Shared compatibility is available only by explicitly choosing `AGRI_AUTH_MODE=shared`.

## Configuration and provisioning

Use the canonical and application database settings in `shared_workspace.md`.
Their schemas must differ, but their PostgreSQL endpoint/database must match.
For a new private deployment, dedicate both schemas rather than putting private
projects in a canonical schema served by another unauthenticated API. The local
release uses `agri_spaceapps_private_data` and `agri_spaceapps_private_workspace`.
Shared storage and the reference corpus remain separate and unchanged.
The canonical reader still starts read-only transactions. The application writer
also needs INSERT on canonical `projects` and SELECT/INSERT/UPDATE on the new
account/session/limit tables, in addition to the existing field/job permissions.

Back up the application schema together with its canonical project/field/asset
dependencies before upgrading. Run `python -m agri_data.workspace.admin provision`
under the authorized setup role to apply additive migration `004_accounts.sql`.
It creates no users, passwords or personally owned data. Existing shared profiles,
plots and donor private records are neither copied nor assigned to the first signup.

A fresh canonical schema can be prepared with `contracts.postgres.PostgresStore.migrate`
under the authorized setup role before application provisioning. This applies the
five packaged canonical migrations, including real foreign keys, but creates no
provider observations, plots or user accounts. Provisioning is not an API startup
side effect. Keep the base project allow-list narrow; authenticated requests and
the private worker replace it with each account's server-assigned project.

Set these values for both API and worker:

```powershell
$env:AGRI_AUTH_MODE = "accounts"
$env:AGRI_AUTH_COOKIE_SECURE = "false" # Only for HTTP inside loopback/Tailscale.
$env:AGRI_AUTH_SESSION_SECONDS = "43200"
$env:AGRI_API_HOST = (tailscale ip -4).Trim()
$env:AGRI_API_PORT = "8080"
$env:AGRI_ALLOWED_ORIGINS = "http://${env:AGRI_API_HOST}:1080"
```

Launch `python -m agri_data.api` and `python -m agri_data.workspace.worker` as
separate backend processes. The frontend receives only its public API origin,
`VITE_API_BASE_URL=http://<same-host>:8080`, and serves on 1080.
For local use, use `127.0.0.1` consistently on both sides, not `localhost` on one
and `127.0.0.1` on the other. Account mode rejects mismatched hostnames.

Cookies are HttpOnly, SameSite=Strict, host-only and scoped to `/api/v1`; their
names include a deployment fingerprint to avoid collisions. Cookies do not
isolate ports: every service on the same host remains part of the browser cookie
trust boundary. Use only the trusted local/tailnet deployment. Set Secure=true
with an appropriately configured HTTPS deployment; no public exposure is approved
by these settings. Origin/Host checks and disabled proxy-header trust remain.

## Session protocol

All JSON keeps `{data,meta}` / `{error,meta}`. Responses are never cacheable.

| Operation | Behavior |
| --- | --- |
| GET `/api/v1/auth/session` | Public mode discovery. Shared mode returns no user/cookie. In account mode, include credentials to read the current user, expiry and CSRF token; no/expired session returns `user: null`. |
| POST `/api/v1/auth/bootstrap` | Requires an allowed Origin; sets a ten-minute HttpOnly anonymous cookie and returns its CSRF token. |
| POST `/api/v1/auth/register` | Bootstrap cookie + X-CSRF-Token, JSON login/password. Creates an empty private scope atomically and returns 201 with a new session. |
| POST `/api/v1/auth/login` | Same bootstrap requirements; verifies Argon2id, consumes the bootstrap and rotates/revokes the previous browser session. |
| POST `/api/v1/auth/logout` | Authenticated CSRF-protected revocation; 204 and cookie removal. |

Logins normalize ASCII case/outer whitespace and require 3-100 identifier
characters (`a-z`, digits, `_ . @ + -`). Registration passwords are 12-1024
characters. Raw session tokens never appear in JSON or the database; only their
SHA-256 digests are stored. Passwords use Argon2id, including a dummy verification
path for unknown users. Password hashing has bounded concurrency.

Default sessions last 12 hours, with no silent renewal; configurable bounds are
60 seconds to seven days. Persisted limits cover bootstrap creation (120/10 min),
registration (10/hour per peer), and login (12/15 min per account and 36/15 min
per peer). Limits survive process restarts and return 429/Retry-After. Peer
identity comes from the connection, not caller-supplied proxy headers.
Account request bodies are limited to 16 KiB; geometry upload limits are unchanged.

The browser keeps CSRF/user context only in memory, sends credentials only after
account-mode discovery, and attaches `X-CSRF-Token` to writes and `X-Account-ID`
to private resource requests. A changed account returns 409 `session_changed`
before any read/write runs. Clear previous identity, drafts and job URLs on
logout/session change; never reuse another account's editor state. An expired
session returns 401, not a successful empty workspace.

Authentication operations have no idempotency receipts. After a lost sign-up
acknowledgment, inspect the session or explicitly sign in; do not blindly create
another account. A bootstrap is consumed only by successful login/registration.

## Owner isolation and durable jobs

Registration creates one random account ID, one personal workspace/profile and
one canonical project in a single transaction. Unique logins are serialized so
concurrent registration creates only one scope. Partial storage failures roll
back the profile, audit revision, project and account together.

Each protected request derives WorkspaceSettings and DataSettings from its
current active session. The browser cannot supply a workspace owner. Field
project IDs are still explicit inputs but must equal the account's project.
Profiles, ETags, idempotency receipts, original bytes, import previews, jobs and
exports retain workspace scope; fields/evidence also retain project scope.
Pagination binds to account/workspace as well as filters/snapshot. Guessed foreign
resource IDs return 404. The historical `SharedProfile` DTO name is retained,
but its account-mode contents are private.

The account worker advertises a deployment/canonical-schema-specific heartbeat.
A shared worker cannot make private import/export capabilities ready. The private
worker discovers active account jobs dynamically, resolves the same ownership
mapping, and reuses existing leases, retries and transaction boundaries. Newly
registered accounts need no worker restart. Disabled accounts' queued work is
not processed. Already authorized, in-flight work may finish during revocation.

KML/KMZ/GeoJSON bytes and all original geometry remain durable in PostgreSQL.
Preview still creates no canonical field. Explicit confirmation is required.
Exports recheck ownership and archival state. No provider observations or model
results are fabricated.

Original uploads can be downloaded at `/api/v1/imports/{import_id}/download`.
Saved versions retain their source at
`/api/v1/fields/{field_id}/boundaries/{boundary_id}/original`. Both require the
same current owner/project scope and verify the stored checksum before returning
bytes. They never open legacy local source paths. Import history stays retained
after a field is archived; normal field/source access is hidden with the field.

The restored frontend sends new drawings as actual UTF-8 KML with stable placemark
IDs and source namespace `drawn`. It saves the original, displays the server
preview/measurements, and requires explicit confirmation. Rejected drawings remain
editable; uncertain upload acknowledgments retain the exact bytes and key. Once
a job is acknowledged, retries only monitor its existing identity. Conditional
PATCH still handles edits to saved fields. Saving KML does not invoke an AI model.

## Verification and remaining operations

`python -m pytest tests\api -q` includes eleven account cases alongside the existing
shared/read/geometry cases. They cover two-account isolation, actual KML bytes,
worker discovery, session rotation/expiry/revocation, account-switch guards,
persistent throttling, concurrent signup, genuine database-failure rollback and
unrelated shared-data preservation. Tests use owned disposable PostgreSQL schemas.

The frontend now integrates sign-up/sign-in/logout, private profile labels,
in-memory CSRF/owner context, revocation handling and cross-tab clearing.
Run `python scripts\workspace_browser_acceptance.py --frontend <checkout> --mode both`
to build once and exercise shared/private suites with owned schemas/processes.
The four private cases cover independent accounts, persistence, missed switch
notifications, server-side session revocation, real satellite drawing/KML capture,
and original download after re-login with foreign-account denials. The release
also passed those cases from its frozen wheel against newly migrated empty
canonical/application schemas, not just the copied reference-test schema.
`--mode accounts` runs only that browser suite; the default remains shared compatibility.

Account administration/recovery, MFA, session inventory, retention
operations, cross-host HTTPS configuration and public deployment remain future
work. Do not seed a password or publish an unauthenticated fallback to solve a
configuration problem. Stop the owned private services and repair their settings
instead of switching them to shared mode.
