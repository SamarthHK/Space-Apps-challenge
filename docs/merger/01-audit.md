# 01. Restarted audit: what is actually built

Audited 2026-11-15 after the earlier merger plan. This revision supersedes its
claims that there is no API/client and that active screens use demo data.
It also removes its monorepo/prefix-move recommendation.

## Four source trees, two working pairs

All paths are under `D:\Code\SpaceApps`. Labels below are used in citations.

| Label / checkout | Inspected HEAD | Actual role |
| --- | --- | --- |
| A: `Space-Apps-challenge` | `92ed57ac87c73db22365578ce8e86a8e7e651ca3` | Shared, account-free field/canonical-observation/evidence API; preparation code has additional uncommitted changes |
| F: `Space-Apps-challenge-frontend` | `f60c327782269c15d40442d57a87a42b817182d7` | Current independently built shared-workspace frontend; matches A |
| B: `Space-Apps-challenge-backend` | `15d84f8400ec7ab1db9eca9bc54a8b6d69506b54` | Separate API with persistent login, sessions, per-user profiles and migrations; no field API |
| P: `Space-Apps-challenge-backend\.local\frontend` | `fe138f9fd600288a562ad73054564257fd524b6b` | Real Git worktree with built login/profile frontend; matches B, not F/A |

F, B and P were clean at the status checks. A was ahead of its remote with dirty
preparation/configuration/test files and untracked canonical/identity/migration
modules. Its manifest/lock and additional outcome/model files changed during
the audit. Those unrelated changes were not modified or followed into AI work.
The stable API files remained outside the reported dirty set.

All four trees belong to the same GitHub project, but **branch name `backend`
or `frontend` does not identify a single local implementation**. Local commits
are ahead of remote tracking branches. Fetching only the remote branch would
not reproduce all inspected work.

### Contract proof

Both APIs report OpenAPI application version `1.0.0`, but their contracts differ.

| Artifact | SHA-256 |
| --- | --- |
| A `docs\openapi.json` and F `contracts\openapi.json` | `7f76d4ca8e6931153663cb25ef132895952d76ca7386834c1b5c6c5a75c7041f` |
| B `docs\openapi.json` | `b25d96191b1cf1c1e5c6dd15ebf3e463f0f20cb3c7ea2ec415b4237c72d084b2` |

F `contracts\source.json` pins A's exact commit and `shared-workspace-1`
revision. P `docs\integration.md` records B's contract hash. F cannot be
connected to B merely by changing `VITE_API_BASE_URL`: `/workspace` is absent,
success/error envelopes differ, and F deliberately omits credentials.

## Implemented capability inventory

| Capability | A + F | B + P | Integration treatment |
| --- | --- | --- | --- |
| HTTP/client/config/error handling | Implemented, shared envelope, AJV snapshot validation | Implemented, different envelope/client signature | Keep A/F transport; adapt reusable behavior |
| Identity/access | No accounts; explicit project scope; loopback/Tailscale | Cookie sessions, CSRF, provisioned accounts | User confirmed shared access; do not import login |
| Profiles | Capability/placeholder only | Real versioned per-user persistence and form | Adapt domain validation/revisions/form to shared workspace |
| Fields/maps | Scoped canonical list/detail, recorded-boundary selection, Leaflet GeoJSON | Not implemented in application API | Preserve A/F, including ambiguous-boundary state |
| Evidence | Canonical values, pending/accepted/rejected, conflicts, paginated source records | Not implemented in application API | Preserve A/F and original provider time standards |
| KML/KMZ preparation | Backend parser/CLI/persistence/export helpers exist | Legacy pipeline helpers exist | Reuse A helpers; HTTP preview/confirm/durable jobs remain new work |
| Drawing/import/export HTTP | Not implemented | Not implemented | Later vertical slice, not a URL wiring task |
| Analysis/soil submissions | Inspection exists, derived summaries/submissions do not | Not implemented in application API | Separate later contracts; no inferred lab verification |
| Catalog/plans/market/forecast/model | Gated/unimplemented or deferred in UI/API | Gated/unimplemented in API/UI | Do not call these built user journeys |

Built artifacts were observed in F `dist`, P `dist` and B `dist` (a Python
wheel). Artifact presence is not proof of an end-to-end deployment or of every
feature mentioned in historical READMEs. No active database/provider/browser
readback was claimed by this audit.

## Current incompatibility register

Paths are relative to the labelled checkout. Abbreviated Python paths below
are relative to `src\agri_data`.

| ID / severity | Evidence | Actual mismatch or gap | Planned disposition |
| --- | --- | --- | --- |
| R01 / blocking | A `api\app.py:96-132`; B `api\app.py:137-162`; F `src\views\workspace.js:196-221` | F bootstraps `/workspace`; B exposes `/meta`. Capability keys/states differ. | A/F are the baseline; no generic URL swap or dual API routing. |
| R02 / blocking | A `api\schemas.py:27-79`; B `api\schemas.py:16-27`; F `src\api\client.js:37-57` | `{data,meta}` versus bare resource; error `details/retryable/meta` versus `field_errors/request_id` inside error. | Shared profile uses A's envelope; retain existing error format. |
| R03 / blocking | F `src\api\client.js:29-35`; P `src\api\client.js:29-39`; B `api\identity.py:123-140` | F omits credentials; B profile requires session and CSRF. This is an ownership difference, not only CORS. | Adapt to explicit workspace profile; do not fake a logged-in user or bypass auth routes. |
| R04 / blocking | A `api\data.py:53-65`; A `contracts\migrations\005_canonical_evidence.sql`; Git status | Read API requires canonical views/tables supplied by an untracked migration and preparation code. | Commit reviewed non-AI prerequisite closure and prove clean reproduction before release. |
| R05 / blocking | A `contracts\postgres.py:44-62`; B `services\database.py:60-88` | Both have `schema_migrations`, but A uses `version`, B `name`; schema contents differ. | Separate migration namespaces/ledgers; never run B's migrator over A's schema. |
| R06 / blocking | A `api\data.py:46-50`; B `services\identity.py:214-250` | A opens read-only transactions; profile writes need transactional persistence. B updates by authenticated `user_id`. | Separate narrowly scoped writer for a workspace-owned profile; keep evidence reads read-only. |
| R07 / blocking | A `api\config.py:46-72`, `api\data.py:28-46`; B `api\settings.py:11-27` | Environment-only `AGRI_API_*` and comma-separated origins versus `.env`/`AGRI_*`, JSON-list origins and a different DSN driver syntax. | Document one runtime setting scheme; translate intentionally, never copy B `.env`. |
| R08 / high | A `api\__main__.py:16-28`; B `docs\local_backend.md`; F `vite.config.js` | A CLI passes `DataSettings` and runs port 8000; B's factory/runbook uses 8080. A bare factory call without data settings leaves reads blocked. Both frontends use 1080. | Use A's actual launcher; run only F as the final UI. Parameterize test ports. |
| R09 / high | B `api\schemas.py:30-68`; B `services\identity.py:219-250`; A `docs\api-contract.md`, transport conventions | B PATCH uses body `version` and 409; shared planned writes require strong ETag/If-Match and 428/412. | Reuse atomic compare/update logic behind the agreed shared write contract; do not expose competing validators. |
| R10 / high | F `src\api\client.js:3-15`; P `src\api\client.js:3-16`; P `src\bootstrap.js:89-143` | Different `ApiError` constructors and callable client versus `.get()` object. P replaces the app root and gates every non-profile screen. | Extract profile-specific UI/payload code; do not copy P bootstrap/client over F. |
| R11 / high | A `api\app.py:36-43`; F `src\api\client.js:15-68` | Current CORS is GET-only and exposes only request ID; F has no writes, response-header access, multipart or binary handling. | Add PATCH/If-Match/ETag first, POST/idempotency/Blob later with exact preflight checks. |
| R12 / high | B `migrations\001_identity.sql:10-34`; A `api\schemas.py:65-70` | B profiles are private per-user records; A has only configured shared projects, no durable workspace identity/profile entity. | Explicit operator-owned workspace key and new shared profile/revision tables; no automatic private-data migration. |
| R13 / high | A `contracts\boundary_import.py:16-21`, `65-105`, `123-159` | Existing import mutates fields, migrates schema and writes proof/export files synchronously. It is not a non-mutating preview or crash-recoverable HTTP job. | Split parse/preview/confirm/service/worker boundaries; never expose the proof CLI as an endpoint. |
| R14 / high | A `contracts\identity.py:7-11`; A `api\data.py:119-143`; F `src\views\workspace.js:127-150` | Fields use source-namespace hashes; boundaries have independent IDs. Multiple versions intentionally have no assumed current geometry. | Preserve opaque IDs/aliases and explicit selection; no global UUID rewrite or latest-date guess. |
| R15 / high | A `api\schemas.py:13-23`, `139-146`; A `contracts\canonical.py:35-43` | Provider-local timestamps are valid without UTC suffix; canonical daily rainfall can be normalized while raw evidence retains provider units. | Keep canonical/evidence DTOs distinct, show units/time basis, never coerce to UTC or compare unlike units as corruption. |
| R16 / medium | A `api\data.py:148-167`; A `api\schemas.py:126-135` | Date filter operates only on `scientific_record.observed_at`; period-only records are omitted. `scientific_record` is weakly typed compared with evidence DTOs. | Specify interval-filter behavior and typed display adapter before broadening beyond the reference corpus. |
| R17 / medium | A `api\pagination.py:18-56`; A `api\data.py:84-89`, `169-173` | Collections are fully materialized/hash-snapshotted; detail scans all field observations. Cursor signing key is process-local. | Preserve 400/409 reset UX; single API worker for initial scope, SQL pagination/shared cursor policy before scaling. |
| R18 / high | A/B `pyproject.toml`; A local test invocation | Same `agri-data` name/version but different source contents, package-data rules, Python constraints and locks. A `.venv` lacked `pluggy`. | Independent environments/artifacts, supported runtime decision and clean lock reproduction; no installing both packages together. |
| R19 / medium | F `frontendplan.md:24-67`; B `README.md`, `progress.md`; P `README.md` | Plans/README sections still describe old ports, no client/API, or the other frontend. | Replace stale execution guidance with source-pinned handoffs; code/generated contracts outrank historical claims. |
| R20 / medium | F `tests\browser\workspace.spec.js:26-32`, `53-57`; F `playwright.config.js` | Browser suite assumes 50 reference rows, no accepted records, and fixed local port. B harness is account-specific. | Preserve relevant assertions, parameterize integration corpus/ports and add shared-profile cases without inventing data. |
| R21 / medium | F `src\main.js`, `index.html:107-122`; P `src\bootstrap.js:133-144` | Active UIs no longer run seeded services. Dormant files remain, and unsupported-screen text is hardcoded. | Do not repeat old active-demo findings; add capability-driven profile UI and keep seed removal a separate cleanup. |
| R22 / high | A `docs\api-running.md`; B `docs\local_backend.md` | Real clusters/configurations and readiness semantics differ; old port references are not current service discovery. A health is liveness only. | Explicit prepared DB/schema scope, operational readiness and isolated validation; never assume a listener is ours. |

## Dirty prerequisite fingerprints

These identify the bytes inspected, not a deployable commit. Have the owner
commit the required closure; do not harvest unrelated model work.

| A path | SHA-256 |
| --- | --- |
| `src\agri_data\contracts\canonical.py` | `b1fe4d3937243bbfeb46e99cc694eebd9695e3c1a51707a1e9e828279ce54526` |
| `src\agri_data\contracts\identity.py` | `f4fddd888d0422c6d5de8c0e24bbb5947ff57c92e08071b4a2f304adce8d330f` |
| `src\agri_data\contracts\postgres.py` | `77c552cf589573544ae63c1d24d7c3b3cc56ccb6fd80950993fde19d0846ec40` |
| `src\agri_data\contracts\migrations\005_canonical_evidence.sql` | `e37506d795d797b3bc5698607e1ec025dba0f61e66335c40a3da7069378accae` |

The existing newer migration files include trial/outcome work. Do not renumber,
delete or reuse their applied versions to make this integration smaller. Isolate
new application migrations and let the data owner publish a coherent data
release. No current parser/DB acceptance claim is inferred from these hashes.

Fresh focused checks and their limitations are recorded in
[acceptance](05-acceptance.md); runtime data readiness remains a release gate.
