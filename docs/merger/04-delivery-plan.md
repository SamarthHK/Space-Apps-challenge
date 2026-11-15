# 04. Dependency-ordered implementation

This is a plan, not completed implementation. Owners below are roles to assign.
Work in separate frontend/backend branches and runtimes; the merger branch
holds the coordination documents only.

## Milestone A: combine the built solutions

Deliver a reproducible shared field/map/evidence UI plus persistent shared
profile through **one backend origin**, without login. Do not make field-write,
market/model or full scientific acceptance prerequisites for this milestone.

| Task / owner | Prerequisites | Exact work | Exit gate |
| --- | --- | --- | --- |
| T0 Pin the runnable baseline / backend owner | None; shared access confirmed | Publish A's required non-AI canonical/identity/migration/preparation closure; pin A/F/B/P donor SHAs; validate lock/runtime/package data in a fresh isolated backend checkout | Canonical schema/read API reproducible without untracked imports or another checkout's environment |
| T1 Prove current separate-instance pairing / both | T0 and prepared scoped corpus | Start A API and F static build independently using one configured origin; check workspace, field/boundary, canonical observation and evidence paths | Real API/browser read agreement, explicit pending labels, no account or shared source filesystem; preserve current behavior before adaptation |
| T2 Freeze shared-profile extension / both | T0; access decision confirmed | Define `/profile`, ProfileResponse/PATCH fields, ETag/If-Match/errors, capability behavior, workspace provisioning and privacy notice; generate actual contract with implementation, not placeholder routes | One reviewed contract; old read-response compatibility cases defined; donor field/validation mapping complete |
| T3 Implement profile storage/service/API / backend | T2 | New application-schema migration and workspace provisioning; adapt B field validation, atomic updates and revision history; add read/write repositories and thin routes to A | Real DB readback, two-client conflict, restart persistence; no users/sessions, no change to canonical data or read-only transactions |
| T4 Add write-aware frontend transport / frontend | T2; final artifact from T3 before acceptance | Extend F client with validated response metadata, PATCH, ETag, shared error details, no retries; preserve existing get/validation/cancellation semantics | Focused transport/contract tests including 412/428, preflight/header behavior and all existing read tests |
| T5 Integrate shared profile view / frontend | T3 and T4 | Extract P field definitions/form/payload behavior into F shell; capability-driven shared label, nullable data, validation and conflict UI; no login/logout/root replacement | Save/read across independent browser contexts while field selection/map/evidence stay functional; edits survive failed/stale save |
| T6 Release joined milestone / both | T1 and T5 | Unified read+profile browser suite, independent packaging/startup, deployment handoff, rollback rehearsal; correct stale plan/readme claims | A single static frontend and API release pair works from documented configuration; all Milestone A gates pass |

T1 and T2 can proceed independently after T0. T3 and frontend T4 implementation
can proceed against the approved contract in parallel, but T4 acceptance needs
the exported implemented artifact. Provider acquisition is not needed on each
profile test; the existing approved prepared corpus supports the read regression.

### File-level change map for Milestone A

Names of new files are proposed; keep modules focused rather than replacing an
entire donor directory.

| Source / destination | Action |
| --- | --- |
| A `contracts\canonical.py`, `identity.py`, `postgres.py`, migrations and transitive preparation helpers | Owner commits reviewed dependency closure; separate new trial/outcome/model scope |
| A `api\app.py` | Register profile router; add write CORS/headers and truthful profile capability; retain all seven reads |
| A `api\schemas.py` or new `api\profile_schemas.py` | Add shared envelope profile DTOs; retain existing strict read DTOs/provider-time schema |
| New A `api\profile.py` | Thin `/profile` GET/PATCH with Origin, precondition and shared-error mapping |
| New A workspace service/repository/migration package | Durable workspace/profile ownership, version checks, audit snapshots, narrow writer and explicit setup/readiness |
| B `api\schemas.py`, `services\identity.py`, `services\database.py` | Donor references for validation/revisions/checksummed migrations; remove session/user assumptions in adapted code |
| F `src\api\client.js`, `validation.js` | Add write/metadata support without changing existing `.get()` consumers; expose field error details safely |
| New F `src\views\profile.js` / profile adapter | Extract only P form/field/payload behavior; no P bootstrap import |
| F `src\views\workspace.js`, `index.html`, existing CSS | Activate profile via capability and integrate in current shell; preserve navigation/map/evidence state |
| A `docs\openapi.json`; F `contracts\openapi.json`, `source.json` | Generate and pin the same implemented extension with donor/release provenance |
| A `tests\api`; new workspace storage tests; F unit/browser tests | Add focused concurrency/persistence/write regressions and retain shared read tests |

Do not install missing packages into someone else's active environment while
preparing the handoff. The audit's use of B's interpreter to check A source was
a diagnostic workaround, not the target deployment model.

## Milestone B: enable field mutations/import/export

This expands beyond simply joining the already built slices. It can start after
Milestone A's workspace/storage/write contract is stable; release it separately.

| Task / owner | Prerequisites | Work | Acceptance |
| --- | --- | --- | --- |
| T7 Field write contract and service / backend + frontend | T3/T4; explicit workspace/project mapping | GeoJSON create/update/archive, server-issued browser-field source identity, version/ETag; preserve imported IDs/aliases and boundary history | Real drawing survives reload; multiple boundaries stay explicit; no generated district rectangle or client area authority |
| T8 Durable import/export service / backend | T7 storage/identity and approved job schema | Split A parser from synchronous proof writes; immutable preview candidates, explicit selection/repair policy, transactional idempotent confirmation, durable jobs and export manifests | Preview creates no fields; duplicate/stale confirmation handled; process restart recovers; scoped download preserves geometry |
| T9 Import/export/drawing UI / frontend | T7/T8 API/artifact; write transport | Restore the useful interaction patterns without legacy seeds; upload/preview/confirm/poll/Blob download; distinguish unsupported formats | Real Polygon/MultiPolygon/holes through upload -> DB -> map -> export, no local-path API inputs |

Existing A parser already iterates all Polygon children, preserves holes,
rejects unapproved repair, and computes metric geometry. Do not rebuild it from
B's older first-polygon parser. Preserve its stronger repair preconditions:
authentic reference plus explicit tolerances; a browser checkbox alone does
not establish that repair is acceptable.

Current A import persistence runs migrations and writes output synchronously.
Refactor services before exposing them. New preview/confirmation/job state is
not equivalent to `boundary_imports.status` or extraction receipt records.

Support GeoJSON download first if it is the only verified HTTP export; keep
KML/KMZ disabled until genuine writers and complete roundtrip checks exist.
Do not label existing GeoPackage/proof bundles as implemented KML downloads.

## Milestone C: later non-AI product capabilities

After relevant field/write/source prerequisites, independently plan soil
submissions/analysis, authentic crop catalog and manual planting plans. Keep
source/time/depth/unit/validation metadata and explicit missingness. Manual
plans must not require a recommendation result or fabricated economics.

Satellite/forecast/market work remains deferred under the existing source/
economic decisions unless scope is reopened. Do not wait for these domains,
training data or a model to ship Milestone A. Do not count deferred capabilities
as completed simply because navigation remains available.

## Migration and rollback

- No automatic localStorage migration, demo-data upload, deletion of existing
  keys, private-profile publication or seed insertion.
- Provision an empty workspace profile. Any real B profile import requires an
  explicit reviewed selection and consent to shared visibility; retain original
  private records and credentials outside the new runtime.
- Keep source IDs, asset checksums, canonical/evidence relationships and pending
  status through data transfer. Never collapse duplicate evidence by dropping
  receipts or infer field aliases solely from overlapping geometry.
- Use additive application migrations and compatible read DTOs. Preserve a DB/
  asset backup and old release pair; verify restore in an isolated environment.
- If profile rollout fails, disable its capability/UI and roll back the
  compatible application artifacts, leaving shared reads and committed data
  intact. Do not drop the profile schema or downgrade over new user writes.

## Review-sized commits

Commit prerequisite publication, profile contract/storage, profile API, client
extension, profile view and combined acceptance as coherent tested steps.
Backend changes include real persistence checks where affected; frontend code
commits include focused tests and production build. Do not stage unrelated A
model work or rewrite shared migration history. Record the contract hash and
backend/frontend SHA pair with each handoff.
