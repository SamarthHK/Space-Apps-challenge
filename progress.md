# Frontend implementation handoff

Integration update: restored private UI and drawn-KML workflows implemented locally. Branch: `frontend`.

## Current scope and decisions

The owner requested small commits only after rigorous affected tests pass.
This policy applies to this project. Preserve unrelated backend work.

Updated mode: private per-person accounts over Tailscale. Frontend port 1080,
API port 8080. Shared access remains compatibility-only, not a private-mode
fallback. Never publish through Funnel or a public proxy. Economics is
deferred; pending evidence stays labelled; fields require polygon geometry.

Read `frontendplan.md` and backend branch `backendplan.md`, `docs/api-contract.md`
and `docs/api-running.md`. Implemented private contract: `private-workspace-2`,
with `shared-workspace-1` compatibility.
The exact generated schema and source commit/hash are pinned under `contracts`.
The earlier account-free decision is superseded by the approved private UI plan.

## Completed increments

| Step | Commit / scope | Evidence |
| --- | --- | --- |
| API foundation | Backend `209da1d`: trusted-network config, health/workspace metadata, standard errors | 32 API/contract tests passed in exact staged snapshot |
| Scoped read API | Backend `c876655`: canonical fields/observations/evidence, explicit boundary selection, read-only DB, snapshot cursors | 41 API/contract tests passed in exact staged snapshot with authentic PostgreSQL evidence |
| Provider-time contract | Backend `92ed57a`: preserve POWER local timestamps without an invented UTC suffix | 38 API tests, including real evidence checked against OpenAPI formats |
| Frontend transport | Frontend `929b5b0`: origin/config, fetch client, response validation and race-safe resources | 8 unit/contract tests plus production build |
| Connected read slice | Current main/index/map/workspace: seven-view shell, scoped fields, stored boundaries, canonical records, evidence and filters | Unit/build and real-browser suite; final result recorded in implementation commit |
| Shared profile | Backend `5547688`, frontend `0e7efd6`: explicit workspace provisioning, ETag writes, audit history, safe shared form | Actual PostgreSQL concurrency/rollback/restart cases and cross-browser persistence |
| Field writes | Backend `2163808`: scoped create/update/archive, source bytes, explicit current boundary and immutable history | Actual PostGIS lifecycle, idempotency, concurrency and rollback cases |
| Durable workflows | Backend `a804cd2`: raw upload preview, explicit confirmation, leased worker and GeoJSON/KML/KMZ exports | Process recovery, atomic batch rollback/retry, version conflicts, scoped downloads and geometry roundtrips |
| Connected field workflows | This increment: map drawing, complex GeoJSON editing, imports, job resume and Blob downloads | 16 frontend unit tests, production build and 14 real-browser cases using isolated authentic records and explicitly labelled topology probes |
| Original UI restoration | Frontend `2f50c0f`: restore the `b59a73f` satellite cockpit, typography/cards, map toolbar, Earth view, direct drawing and responsive profile/tools layout | 16 units, production build and 15 browser cases, including actual satellite tile loading |
| Private accounts | Backend `711d1e1`, frontend `ca647d6`: themed sign-up/sign-in/logout, CSRF/owner-bound requests and private profile labels | 84 backend API cases; 18 frontend units, production build, 15 shared and 3 private browser journeys |
| Drawn KML and originals | Backend `e221e98`, current frontend increment: real KML preview/confirmation, byte-exact originals, retained rejected drafts and safe retry/resume controls | 61 affected backend API cases plus focused corruption/filename cases; 22 frontend units, production build, 16 shared and 4 private browser journeys |

The owner has now approved private per-person accounts/plot ownership and saving
drawn KML, with AI explicitly unavailable until its real input pipeline exists.
Account isolation, session UI and default drawn-KML submission are implemented.
The private browser journey captures actual uploaded KML, confirms it, reloads/
signs in again, and downloads the same original while a second account is denied.
Arbitrary-field AI is not implemented or represented as a queued analysis.

All new code is independent of unrelated uncommitted backend modules. Read
routes require a prepared canonical DB schema; they do not migrate it or call
CLI proof commands. Writes use server-resolved private scopes or explicitly shared application storage;
canonical observations and evidence remain read-only.

## Working behavior

- Bootstrap workspace and capability states from the configured API.
- List canonical fields only in the account's server-assigned project (or configured shared projects).
- Select a recorded boundary version when "current" is ambiguous; render
  stored GeoJSON with Leaflet and server-calculated metrics when available.
- Inspect canonical source values, units/basis, observation time/time standard,
  pending/accepted/rejected state, conflicts and original evidence.
- Paginate/filter records with race protection; handle changed snapshot,
  invalid filters, unavailable backend and reconnect without demo fallback.
- All seven navigation destinations remain accessible. Unimplemented screens
  display honest unavailable states, not old fictional recommendations/prices.
- No production import of legacy services/data modules; no authoritative
  localStorage, seeded profile or initial HTML scientific values.
- Profile saves preserve drafts on ordinary validation/conflict/transport failures.
  Logout or a revoked/changed identity clears private data and drafts instead.
- New field draws submit actual KML for preview and explicit confirmation.
  Name/geometry edits use conditional server versions and computed metrics;
  archived fields disappear without deleting their history or observations.
- Imports require a nonmutating preview and explicit selection. Raw bytes and
  source metadata survive; no implicit geometry repair or scientific approval.
- Jobs survive backend/worker restarts; the page URL permits monitoring/download
  resume after reload. Lost POST acknowledgments reuse the same submission key
  and original bytes only on explicit retry, including on plain-HTTP Tailscale
  origins. Acknowledged jobs resume through GET, not another POST. Rejected
  drawings retain editable input and corrected submissions receive fresh keys.
- Incompatible drafts/previews/jobs lock other writes and selection. Closing
  a preview/job releases local controls, not server files or running jobs.
- Preview originals and selected saved-version originals are byte-exact backend
  downloads. The original-file capability is independent of worker readiness;
  generated geometry exports remain a separate operation.
- GeoJSON/KML/KMZ downloads use checked MIME/attachment headers and binary bodies,
  not JSON envelope parsing. Worker-dependent actions remain blocked if no
  matching heartbeat is present.

The original seeded services/data files remain unused pending F10 cleanup.
The UI does not claim verified agronomy or that reference records describe
Karnataka. POWER reference evidence is from a Dutch parcel.

## Remaining work

The requested profile, field/import/export, private accounts and drawn-KML milestones are complete.
The new 1080/8080 private hosting release is next.
Still deferred: B05/F05 soil submissions/analysis, B06/F06 acquisition/satellite, B07/F07/F08 crop and
market services, B08/F09 planting plans, then cleanup and full deployment gates.
No full scientific or platform-completion claim: additional authentic geometry
contexts, later source schemas, operational scale and deferred domains remain open.
Pending scientific approval and training readiness are separate from the
passing engineering checks.

## Running and validating

See README for commands. `.env.local` holds local public host configuration
and is ignored by Git. No credentials belong there.
Backend PostgreSQL in this workspace required a different loopback port after
the old port became unavailable; use the actual configured port, not a hardcoded
assumption. Database and provider readiness must be rechecked after restarts.

`npm test` covers configuration, transport, schema and race behavior.
`npm run build` produces an independently hosted static artifact.
Use the backend's `scripts\workspace_browser_acceptance.py` for writes. It uses
owned schemas/processes and an isolated snapshot of actual scoped records,
not the live canonical corpus. Diagnostic topology/transport probes and simulated
user drawing are not represented as authentic provider or scientific evidence.
See README for contract pinning and the read-only browser selector.
