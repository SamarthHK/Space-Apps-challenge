# Frontend implementation handoff

Updated: 2026-11-15. Branch: `frontend`.

## Current scope and decisions

The owner requested small commits only after rigorous affected tests pass.
This policy applies to this project. Preserve unrelated backend work.

Approved mode: no accounts, one shared Tailscale workspace. Frontend port 1080,
API port 8000. All devices permitted by tailnet rules share access. Never
publish this account-free mode through Funnel or a public proxy. Economics is
deferred; pending evidence stays labelled; fields require polygon geometry.

Read `frontendplan.md` and backend branch `backendplan.md`, `docs/api-contract.md`
and `docs/api-running.md`. Implemented contract: `shared-workspace-1`.
The exact generated schema and source commit/hash are pinned under `contracts`.
Legacy per-user authentication tasks in the original plan are superseded.

## Completed increments

| Step | Commit / scope | Evidence |
| --- | --- | --- |
| API foundation | Backend `209da1d`: trusted-network config, health/workspace metadata, standard errors | 32 API/contract tests passed in exact staged snapshot |
| Scoped read API | Backend `c876655`: canonical fields/observations/evidence, explicit boundary selection, read-only DB, snapshot cursors | 41 API/contract tests passed in exact staged snapshot with authentic PostgreSQL evidence |
| Provider-time contract | Backend `92ed57a`: preserve POWER local timestamps without an invented UTC suffix | 38 API tests, including real evidence checked against OpenAPI formats |
| Frontend transport | Frontend `929b5b0`: origin/config, fetch client, response validation and race-safe resources | 8 unit/contract tests plus production build |
| Connected read slice | Current main/index/map/workspace: seven-view shell, scoped fields, stored boundaries, canonical records, evidence and filters | Unit/build and real-browser suite; final result recorded in implementation commit |

All new code is independent of unrelated uncommitted backend modules. Read
routes require a prepared canonical DB schema; they do not migrate it or call
CLI proof commands. No writes are enabled.

## Working behavior

- Bootstrap workspace and capability states from the configured API.
- List canonical fields only in explicitly configured projects.
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

The original seeded services/data files remain unused pending F10 cleanup.
The UI does not claim verified agronomy or that reference records describe
Karnataka. POWER reference evidence is from a Dutch parcel.

## Remaining work

B02/F03 shared-profile persistence, B04/F04 field writes/import/export, B05/F05
soil submissions/analysis, B06/F06 acquisition/satellite, B07/F07/F08 crop and
market services, B08/F09 planting plans, then cleanup and full deployment gates.
No full F01/F04/B03 or WEB/API completion claim: property-level inventories,
additional authentic geometry contexts, writes and later schemas remain open.
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
`TEST_API_ORIGIN` points browser tests at a real prepared backend; no generated
agricultural fixtures are used. Browser network/malformed-response and inert-text
cases are explicit transport/UI tests, not scientific acceptance evidence.
