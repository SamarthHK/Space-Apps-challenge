# 02. Two-instance architecture and reuse

## Agreed target

Keep **one independently built frontend application and one independently
deployed backend application**. User-confirmed access mode: account-free shared
workspace; adapt profile persistence to it. Do not introduce login, a monorepo,
a second production UI, or feature-specific API origins.

```text
Frontend instance: existing Vite/Leaflet build (F), configured port 1080
                       |
                       | HTTP /api/v1, one configured API origin
                       | shared envelopes, no cookies/tokens
                       v
Backend instance: shared-workspace API (A), configured port 8000
    | existing scoped read repository      | new workspace-profile service
    | read-only transactions               | narrow versioned writes
    v                                      v
PostgreSQL/PostGIS: canonical data schema + separate workspace application schema
    ^
    | existing preparation path; later backend-owned job worker
    |
Private backend assets and source adapters
```

Database and a later worker are backend infrastructure, not additional
browser-facing backend applications. The first profile integration does not
need a worker. The frontend never imports backend code, reads backend paths,
connects to PostgreSQL, or requires a sibling source checkout at runtime.

## Source ownership and reuse

Use A as the backend code baseline because F already pins it and consumes real
field/evidence operations. Use B/P as donors for the completed profile slice.
Folder names do not override that compatibility evidence.

| Keep | Adapt with focused tests | Do not copy into the shared runtime |
| --- | --- | --- |
| A app/error/envelope/Host-Origin rules, DataStore and canonical read schemas | B profile fields, input validation, atomic version update and revision history | B login/password/session/CSRF services and per-user profile ownership |
| A canonical field/boundary/source identities, read-only transactions, explicit projects | B checksummed migration/rollback patterns in a separate workspace namespace | B identity migration or migrator run against the canonical schema |
| F client validation, resource generations/cancellation, map and evidence UI | P `profileApi.js` field labels/payload mapping and isolated profile form rendering | P whole bootstrap, root replacement, session client or second navigation shell |
| F package/contract pinning and production build | Write-aware transport with header/error detail access | Two `createClient` implementations or two `VITE_API_BASE_URL` values |
| A parser/provenance/geometry helpers after prerequisite handoff | Later HTTP preview/confirmation and worker orchestration | Direct HTTP invocation of `health-check`, `storage-proof`, or synchronous CLI imports |

Do not port the old browser recommendation engine or revive retired seed paths.
Scientific pending status is intentionally inspectable; it is not a failed UI
integration and must not be promoted to accepted to make a screen look complete.

## Workspace persistence without invented users

Introduce a stable, operator-configured workspace ID for profile ownership.
Its provisioning is an application setup operation; GET must not create records.
Do not derive it from the current project allow-list or browser values: changing
which projects are visible must not silently create a different profile.

Recommended application tables in a new schema such as `agri_workspace`:

- A profile record keyed by stable `workspace_id`, positive `version`, the existing
  nullable profile fields, and timestamps.
- Append-only profile revisions keyed by workspace/version, recording committed
  snapshots and request/audit metadata without claiming a per-person identity.
- Later idempotency/job/plan tables when their owning increment requires them.

Workspace visibility and writes are shared across permitted clients. Existing
private B profiles must not be automatically imported or exposed. Do not create
a hidden default user to reuse session-bound SQL. Provision an empty shared
profile and allow reviewed entry/import only.

## Database and migration boundary

Keep the existing canonical schema and identifiers unchanged. Introduce the
application schema with its own checksummed migration ledger. This avoids the
actual `version` versus `name` ledger conflict and keeps unrelated trial/model
migrations outside the new profile schema.

Use one configured PostgreSQL service for the target deployment where feasible,
with explicit schema and role configuration. Preserve the existing read-only
canonical transaction path and restricted reader role. Use a separate,
least-privilege writer connection for application records and a migration role
for setup. A failed profile write must not affect evidence reads.

Do not simply replace `READ ONLY` with read/write globally. Do not run migrations
on API startup or profile GET. Do not transfer B's entire database, users,
sessions, `.env`, or local PostgreSQL cluster into A.

If moving a prepared canonical dataset to another server, include schema
history, IDs/aliases, boundaries, observations/evidence links and controlled raw
assets. Preserve source hashes and validation state. Internal asset-path
relocation is an operator-controlled mapping, not a change to scientific
identity. Prove reconciliation before cutover.

## Contract and package ownership

Backend owns generated OpenAPI. Frontend pins a released copy plus source SHA,
contract revision and checksum; artifact exchange happens at development/build
time, not through runtime filesystem sharing.

Both Python implementations currently install as `agri-data` version `0.1.0`.
Do not install them together or merge their environments. Select one backend
release graph, validate its Python support, and resolve only needed donor
dependencies into that manifest/lock. Account-free profile work does not require
bringing Argon2/session packages solely because the donor used them.

Preserve F's npm build and standalone static artifact. Runtime API origin is
currently a Vite build-time setting: rebuild for a changed origin unless a
separate runtime configuration feature is deliberately implemented.

## Safe Git handoff

The `merger` branch remains documentation only. No source-prefix relocation or
frontend/backend root merge is needed.

1. Owners publish coherent, reviewed commits for A's required preparation
   closure. Pin them; a local dirty worktree is not the release artifact.
2. Preserve both divergent backend histories under unambiguous refs or bundles
   before integration. Do not force-push one local `backend` over the other.
3. Work from the approved A backend baseline in a clean backend integration
   branch/worktree. Selectively adapt B profile behavior with source-commit
   attribution; whole auth/storage commits are not drop-in cherry-picks.
4. Work from F in a separate frontend branch/worktree. Extract P profile form/
   DTO behavior without replacing F's app entry or map/evidence components.
5. Exchange a generated contract release; review and deploy backend/frontend
   artifacts independently. Record both release SHAs, not just branch labels.

The eventual directory name of the chosen backend checkout is operational, not
an architecture decision. If it must be `Space-Apps-challenge-backend`, prepare
a new clean destination and preserve the existing donor; never overwrite it.
