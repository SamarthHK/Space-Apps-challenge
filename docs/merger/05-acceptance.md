# 05. Audit evidence and integration acceptance

This document preserves evidence from the planning audit and its proposed
acceptance gates. For checks performed during implementation, their exact
scope, and remaining operational/scientific gaps, see
[the implementation handoff](08-implementation.md).

## Checks actually performed during this restarted audit

| Check | Result | What it establishes |
| --- | --- | --- |
| Read current source, generated schemas, Git/worktree status and selected build-artifact metadata | Completed | Four distinct trees/two compatible pairs; implementation and dirty prerequisites identified |
| Compare A OpenAPI with F pinned bytes/source metadata | Exact matching SHA-256 | F is pinned to A, not B |
| F `npm test` | 8 passed, 0 skipped | Current transport/configuration/resource-state/contract tests pass |
| B `.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\api\test_foundation.py tests\api\test_openapi.py -q` | 21 passed | Donor API foundation, profile DTO behavior and published schema agree; no DB fixture used |
| A native `.venv` invocation of `tests\api\test_foundation.py` | Failed before collection: missing `pluggy` | Existing local environment is not sufficient evidence of reproducible runtime/test setup |
| A foundation tests using B's existing Python 3.12.13 interpreter with `PYTHONPATH` explicitly set to A `src` | 30 passed | A source foundation and actual temporary loopback HTTP tests work in that environment; not proof of A's own lock/venv |

Both Python test runs that completed emitted an existing Starlette TestClient
deprecation warning. No dependency installation or environment repair was
performed. Temporary foundation HTTP helpers were scoped to the tests and
terminated by their fixtures.

No prepared-data DB suite, live provider acquisition, current production build,
current browser suite, private profile read or source-data migration was run.
Prior progress files report additional DB/browser checks; those are historical
evidence, not fresh passes from this audit. Artifact existence and passing
foundation tests do not establish field/evidence data readiness.

## Milestone A mandatory gates

| Gate | Scenario | Required result / evidence |
| --- | --- | --- |
| G01 Clean reproduction | Approved backend/frontend SHAs in separate clean checkouts, fresh isolated environments and prepared canonical schema | No untracked module/migration dependency, no cross-checkout Python environment; own lock/package data works |
| G02 Correct pairing | F connects to selected API origin; wrong B endpoint/schema deliberately selected in a controlled check | Shared revision/envelope accepted; incompatible backend produces clear error, not silent "empty" or guessed fallback |
| G03 Existing reads | Workspace -> fields -> explicit boundary -> observations -> evidence with authentic prepared records | Real browser/API/PostGIS/source agreement; preserve canonical IDs, geometry and source evidence |
| G04 Empty/dependency states | Empty project result, missing DB configuration/schema, invalid project scope, tile host outage | Empty versus blocked/failed distinct; unknown nested IDs inaccessible; basemap outage not a data failure |
| G05 No accounts | Fresh browser/context uses all implemented reads and shared profile with no cookies/tokens/login | Shared access is explicit; no requests to `/auth/*` or `/me/profile` |
| G06 Profile persistence | Save declared non-scientific input; reload API/browser; read from a second context and independent DB connection | Same shared resource, version and committed fields; no browser authority or private-profile auto-copy |
| G07 Profile concurrency | Two clients read same ETag and attempt divergent saves; missing/malformed preconditions | Exactly one accepted competing update; stale write 412, missing If-Match 428; no silent overwrite; one revision per successful update |
| G08 Input semantics | Omitted versus null, empty patch, invalid phone/enum, server-owned fields, markup as text | Donor validation preserved where intended; stable shared error details; safe rendering; no changed scientific state |
| G09 Transport/CORS | Real browser cross-origin GET/PATCH and OPTIONS; ETag read after GET/save; timeout or lost response | Headers accessible, credentials omitted, no blind retries, edits retained; denied origins stay denied |
| G10 Read/write isolation | Failed or rolled-back profile write while data reads run | Canonical transactions still reject writes; no change to observations/assets/aliases or profile revision after rollback |
| G11 UI coexistence | Navigate profile -> map -> evidence and save while read requests complete | Field/boundary/filter state not reset by imported bootstrap; late responses cannot update another context |
| G12 Schema compatibility | Backend-exported artifact, F pin/hash, actual read and profile responses | Same schema/operation shapes; strict additional-property and provider-time behavior retained; old read responses remain valid |
| G13 Independent deployment | Static frontend artifact on one origin/machine; backend/DB private elsewhere | No sibling paths/imports/filesystem dependency; one API origin; correct configured Host/Origin |
| G14 Recovery/handoff | Disable profile after failed rollout; restore compatible release in isolation | Reads remain available; data/revisions retained; no source resets or shared-service/volume deletion |

Do not make accepted scientific status a Milestone A requirement: inspecting
pending authentic evidence is the current approved behavior. Authentic geometry/
provider bytes are still required to claim a positive data roundtrip. A model,
forecast or recommendation is neither executed nor accepted here.

## Focused test additions

**Backend:** extend A `tests\api\test_foundation.py` for profile capability,
errors, mutation Origin checks and preflight. Add shared-profile API/storage
tests using an integration-owned application schema on real PostgreSQL.
Adapt relevant B tests for real atomic updates/revision rollback; do not reuse
session fixtures or call authenticated functions with a fabricated user.
Retain A data reconciliation tests and their read-only transaction assertion.

**Frontend:** retain current eight unit/contract tests. Add profile form/payload,
ETag/header access, 412/428, unknown/invalid response, network ambiguity and
capability tests. Keep `createResource` generation protection. Add combined
browser cases that use the actual prepared read API and real shared profile
persistence; do not run two separate passing suites as a substitute for a
single combined app journey.

Parameterize browser ports/origin and authentic corpus expectations. Current
tests assume 50 rows and no accepted records; make the test contract explicit
rather than silently relying on one mutable database snapshot. Authentication
donor tests remain donor regressions, not acceptance of the chosen access model.

Do not create fake agricultural records to prove provider/scientific success.
Pure client transport cases, invalid inputs and application-profile text are
not agricultural evidence and should be labelled accordingly.

## Later field/import/export gates

T7-T9 require real Polygon/MultiPolygon/holes, stable IDs across edits, explicit
boundary revisions, server metric agreement, refusal/approval of repair,
non-mutating preview, repeated/stale confirmations, durable retry/restart,
scoped download, 204/binary parsing and complete format roundtrip.

The current browser assertion of one Leaflet path is not sufficient proof that
all components/holes survived. Compare geometry content and independent area
checks for the chosen authentic cases. Existing geography helpers are reusable,
but missing authentic contexts remain blocked rather than passed.

## Commands and evidence policy

Use [runbook](07-runbook.md) for current runnable interfaces and prerequisites.
Do not claim future `/profile` or migration/setup commands exist before their
implementation. No configured lint script was found in the current frontend
manifest; use existing tests/build and add tooling only for a concrete need.

Each gate records source SHAs, artifact hash, exact command, environment,
`not_run/pass/fail/blocked`, and non-sensitive evidence references. Keep raw
farmer reports, contacts, passwords, DSNs and screenshots containing private
records out of commits. A failed/skipped/blocked required gate is not a pass.
