# 08. Implemented two-application release

The owner authorized Milestones **A and B**, with tested commits before moving
to subsequent implementation steps. They are implemented locally: an account-free
shared profile, preserved field/evidence reads, versioned field editing, durable
import preview/confirmation jobs and real geometry exports. Frontend and backend
remain independent applications. No AI/model, economics or donor authentication
runtime was merged.

This is an engineering handoff, not a claim of production deployment, complete
scientific acceptance or completion of every original planning gate.

## Exact release pair

| Component | Branch | Commit | Checkout relative to `D:\Code\SpaceApps` |
| --- | --- | --- | --- |
| Non-AI backend | `backend` | `973ac90a179e46f4e664358ad26b0f753d98c207` | `Space-Apps-challenge\.local\integration-backend` |
| Frontend | `frontend` | `622db9469f8404135dd9d34c1ffc2f12f029dbda` | `Space-Apps-challenge-frontend` |
| Coordination documents | `merger` | This documentation commit | `Space-Apps-challenge-merger` |

Contract revision: `shared-workspace-1`.
SHA-256 of the committed backend `docs\openapi.json` and frontend pin:

```text
195c2e33a57926c6b4f290c10311cba64e24f38180ae7baa4c24263ffc46eaf3
```

Frontend `contracts\source.json` records the exact backend commit and digest.
All 20 original strict read/error DTO schemas remain unchanged; additions use
new operations/DTOs and version headers, not extra properties in old read bodies.
Artifact generation/pinning uses stable LF bytes across checkout platforms.

### Why the backend is in a worktree

Concurrent work switched the original `Space-Apps-challenge` checkout to
`backend-ai`. Rather than switch it back, stage unrelated changes or rewrite
history, the non-AI branch was isolated in the worktree above with its own
locked `.venv`. Relevant non-AI canonical/geometry fixes from `f8e29f9` were
included; concurrent trial/model work was not.

Release-harness changes initially committed as `4d034f1` on that concurrently
advanced branch were copied to the non-AI branch as `e1ae768`. The original
checkout and its ongoing work remain intact. Do not mistake its current HEAD
for the release pinned by the frontend.

Nothing has been pushed. The authenticated B/P donor checkouts were not modified,
private profiles were not copied, and existing API/frontend/PostgreSQL listeners
were not replaced. No live shared workspace was automatically provisioned.

## Delivered behavior

| Plan tasks | Implemented result |
| --- | --- |
| T0-T1 baseline/pairing | Published canonical preparation prerequisites; independent API/static build; authentic scoped fields, observations and evidence retained |
| T2-T5 shared profile | Explicit workspace provisioning, nullable donor-field validation, shared-visibility notice, strong ETag/If-Match, atomic audit revisions, conflict-safe frontend form |
| T6 joined release | Separate-instance browser acceptance, packaged backend, pinned contract and write-disable recovery; live rollout and physical backup/restore remain operator work |
| T7 field writes | Scoped create/update/archive, explicit boundary versions, server metrics, retained original geometry/bytes, immutable history and idempotent POST receipts |
| T8 durable workflows | Raw KML/KMZ/GeoJSON preview, explicit candidate confirmation, leased/recoverable jobs and snapshot GeoJSON/KML/KMZ exports |
| T9 connected UI | Drawing and complex GeoJSON editing, visibly unsaved previews, reload-resumable job monitoring and actual Blob downloads |

The profile applies to one explicitly configured workspace; all permitted
visitors share it. No login, cookies, default user, localStorage authority,
private-profile auto-migration or second API is introduced.

Canonical observation/evidence reads remain read-only and scoped by configured
projects. New user geometry is not called surveyed or scientifically verified.
Archive hides normal field/evidence reads without deleting history. Multiple
legacy boundaries remain explicitly selectable; new writes identify the current
version. Failed/stale writes preserve drafts rather than silently overwriting.

POST idempotency keys are workspace-wide, include operation/input comparison,
and are persisted transactionally. Lost acknowledgments are resolved only by an
explicit retry of the frozen original request/key. Plain-HTTP Tailscale clients
use `crypto.getRandomValues`, not secure-context-only `crypto.randomUUID`.

The worker is backend infrastructure with durable PostgreSQL leases, atomic
result/field transactions, retry limits and readiness heartbeats. The page URL
retains its job ID for resume; polling does not resubmit writes. Imports do not
change canonical fields until explicit confirmation. Download content retains
all supported parts/holes and original altitude, with no invented elevations.

## Tested implementation increments

| Commit | Scope |
| --- | --- |
| Backend `173a6e9` | Reviewed canonical/identity/preparation prerequisite closure |
| Backend `5547688`, frontend `0e7efd6` | Shared profile storage, API, transport and UI |
| Backend `0d252e5` | Initial owned-process separate-instance browser harness |
| Backend `2163808` | Versioned field writes and archive behavior |
| Backend `a804cd2` | Durable import/confirmation/export jobs and worker |
| Backend `e1ae768` | Isolated mutating browser gate and write-disable recovery |
| Backend `60628ff` | Platform-stable OpenAPI artifact bytes |
| Backend `a062201` | LF/legacy-CRLF workspace migration compatibility without ledger rewrites |
| Backend `973ac90` | Multipart/hole/altitude probes through durable storage and all export formats |
| Frontend `622db94` | Field/workflow UI, binary transport, contract pin and browser regressions |

Workspace migrations are separately packaged as `001_profiles.sql`,
`002_fields.sql` and `003_jobs.sql`. They preserve existing migration rows;
only exact LF/CRLF representations are compatible, not arbitrary content drift.
Canonical migration history was not rewritten for this portability fix.

## Verification actually performed

| Command/check | Result and scope |
| --- | --- |
| `uv sync --locked --extra dev` in the isolated backend worktree | Fresh own environment restored after the initial test command reported missing pytest; Python 3.14.3 |
| `python -m pytest tests\api -q` | 73 passed after the migration-portability fix; actual PostgreSQL/PostGIS persistence, concurrency, rollback, restart, origins, preconditions, durable jobs and authentic read regressions |
| `python -m pytest tests\api\test_workspace_jobs.py -k topology -q` | 3 passed after extending those cases through preview, confirmation, PostGIS and each export format; these replace/strengthen existing cases, not 3 additional suite cases |
| Original strict DTO comparison against `92ed57a` | All 20 original read/error schemas unchanged |
| `node scripts\pin-contract.js <release-backend>` | Pinned committed bytes from `973ac90`; frontend checksum test passed |
| `python scripts\workspace_browser_acceptance.py --frontend <frontend>` | 16 frontend unit cases, isolated production build and 14 Chromium browser cases passed using the release worktree's own runtime |
| `uv build --wheel` plus archive inspection | Backend wheel built; API/worker and all three workspace SQL migrations included, concurrent model modules excluded |
| Staged Git whitespace checks | Passed before each release commit |

The last complete browser run used separate owned API, worker and static-preview
processes. It covered shared persistence across independent browser contexts,
stale/ambiguous writes, original evidence/navigation/race/failure/mobile flows,
drawing/edit/archive, nonmutating preview/confirmation, job resume, real KMZ
download equality, and complex geometry preserved through storage/map/export.
Owned processes and schemas were cleaned up; the normal frontend build and
original canonical corpus were not replaced.

Retained browser evidence is under the backend release worktree:

```text
.local\workspace-acceptance\4a8e47b4bd514299925030d4fb7143b0
```

The backend API suite emits a Starlette TestClient/httpx deprecation warning;
it is not a skipped or failed test. The API tests, not unrelated model or
whole-project scientific suites, are the reported backend scope. Frontend used
its existing dependencies and lock; a new clean frontend dependency installation
was not performed during this final gate.

### Authentic evidence versus diagnostic input

The prepared reference is one Dutch PDOK/RVO field with 2555 NASA POWER records
and three stored boundary versions. Those authentic geometries are 2D Polygons
with one ring. Actual source bytes/checksums, canonical records and PostGIS are
used; pending states and provider-local timestamps remain unchanged.

Multipart, holes and altitude are additionally exercised using explicitly
labelled topology-only input in disposable test schemas and simulated user
entry. Geometry content is compared through storage and exports; a Leaflet path
count is not the only assertion. These probes create no scientific observations
and are not presented as authentic agricultural/provider evidence.

Consequently, additional authentic multipart/3D geographic contexts, Karnataka
suitability and broad scientific acceptance are **not** marked passed merely
because engineering roundtrips pass.

## Deliberate implementation choices

| Choice | Reason / compatibility |
| --- | --- |
| Raw upload bodies, not multipart | Preserve original bytes with one bounded contract; no browser filesystem paths |
| Explicit `/exports` selection lists | Snapshot chosen field/boundary versions; real GeoJSON/KML/KMZ bytes, not renamed proof bundles |
| ETags and separate mutation responses | Add versions without breaking the existing strict read DTOs |
| Database-backed original assets | Atomic bytes/history/job persistence across separate application instances; opaque source locators |
| Independent application schema and writer | No shared-profile state or revisions placed into scientific observation tables |
| Write-disable recovery on the current API | Retain archive/current-boundary semantics; an old archive-unaware API is not a safe rollback |
| Isolated acceptance copies | Exercise writes without mutating the authentic canonical corpus or existing services |

Uploads are bounded at 16 MiB; preview supports 100 features, confirmation/export
up to 50 selected fields, and field geometry up to 10000 positions. Geometry
repair is not implicit. Application assets, receipts, jobs and revisions have no
automatic retention expiry; capacity and backup policies remain operator duties.
See backend `docs\shared_workspace.md` for the full limits and operating contract.

## Start, recover and remaining gates

Use [07-runbook.md](07-runbook.md) and the owning backend
`docs\shared_workspace.md` / frontend `README.md`. Operator setup must supply the
canonical project/database settings and all five `AGRI_WORKSPACE_*` values,
explicitly provision the application schema, start the API and worker, then build
the independent frontend with its public `VITE_API_BASE_URL`.

For recovery, stop only the owned worker and run the current API without workspace
settings while retaining canonical reads. Saved rows remain intact. This path
was exercised; a physical PostgreSQL backup/restore rehearsal was **not**.
Do not reverse migrations, delete shared volumes, overwrite saved data or revert
to an older API that can reveal archived fields.

Remaining operational gates include real deployment ownership/configuration,
backup/restore rehearsal, retention/capacity planning and larger-scale pagination.
Current reads still materialize records and cursor signing is process-local;
multiworker scaling is not claimed. Public exposure requires a separate
authentication/HTTPS design; tailnet policy, not CORS, controls shared access.

Soil submissions, acquisition/satellite, crop/market services, manual plans,
model training/inference, economics and broad scientific acceptance remain
deferred. Their UI states are unavailable, not simulated completed features.
