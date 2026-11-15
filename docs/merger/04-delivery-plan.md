# 04. Dependency-ordered delivery plan

These are future implementation tasks. None is completed by writing this plan.
Owners are roles to assign, not claims that someone has accepted the work.
Approve the [decision register](06-decisions.md) before consequential behavior
or schema changes. Every implementation change gets a focused regression check.

## Phases and actual prerequisites

| Phase / owner | Depends on | Bounded work and files | Exit gate |
| --- | --- | --- | --- |
| P0 Contract and baseline / integration + both maintainers | None | Approve baseline, deploy/auth and non-AI scope; commit source-plan handoffs; freeze DTOs/OpenAPI, units, state enums and mappings M01-M18; identify authentic acceptance inputs | Approved source SHAs, decisions, schema and capability map; blocked datasets recorded without blocking schema design |
| P1 Source consolidation / integration | P0 baseline decision | Prefix imports as in architecture document; reconcile path-sensitive configuration, ignore rules, Python manifest/lock and CI entry points | Both source histories retained, imported trees reconciled, independent builds/package discovery work; no application behavior changed in relocation commit |
| P2 Storage/auth/client foundation / backend + frontend | P0 contract; P1 | Backend migrations for users/sessions/profiles/ownership/assets/jobs, explicit PostGIS settings and app factory; frontend config/client/errors/state/adapters and login/profile UX | Profile survives API/browser restart; cross-account reads fail; no seeded profile or local domain authority; separate-origin session/CSRF roundtrip works |
| P3 Field/import/export vertical slice / both | P2 | Refactor geometry services and fix MultiGeometry parsing; add field/revision CRUD, durable worker, preview/confirm and authorized exports; replace browser plot CRUD/map/export paths | Real draw/import -> persistence -> fresh browser -> complete map/export; holes/components preserved; duplicate confirmation and repair refusal safe |
| P4 First evidence slice / backend data + frontend | P3; authentic soil/POWER input for respective positive cases | Shared adapters preserve original bytes; record submissions and acceptance, normalized observations, analysis/provenance/refresh APIs; migrate soil/climate UI | Display reconciles with raw record and DB, correct basis/depth/period, genuine missing/zero behavior; failed source does not fabricate results |
| P5 Catalog/manual plans/dashboard / both | P3; authentic crop references for plan acceptance | Species/cultivar catalog, versioned plan CRUD/archive and summaries; replace plan economics dependency and dashboard assumptions | Save/read/archive a plan without AI or profit estimates; totals cover all pages; missing economics not zero; area and ownership enforced |
| P6 Existing non-AI panels / source owners + frontend | P3 and the shared source/provenance harness from P4; individual authentic source access | Independent satellite/vegetation, forecast, and market slices; actual controls and authorized overlays; maintain explicit source/capability blockers | Each ready panel matches field/time/source; unavailable panels are deliberately labelled and cannot show seeds |
| P7 Integration release / both + reviewer | P4/P5 accepted; P6 panel acceptance OR approved unavailable behavior; no unreviewed blockers | Remove production legacy data imports/reset/default HTML, finish rendering/pagination/cancellation, contract checks, deployment/runbook and rollback rehearsal | All mandatory non-AI acceptance gates pass; unavailable optional capabilities disclosed; code consolidated and independently deployed |

P4 and P5 can proceed independently after P3. Within P6, market, forecast and
satellite sources do not depend on one another. A missing satellite credential
does not block profile/field/manual-plan persistence. A missing authentic crop
catalog blocks positive plan acceptance, not unrelated field work.

## Detailed first slice

1. Backend P2 extracts settings/session creation from module import side effects,
   introduces migrations and repositories, then exposes session/profile/meta.
   Standardize errors before adding consumers; initialize no demo data.
2. Frontend P2 replaces synchronous bootstrap with session -> profile/field state.
   Handle 204, timeout, abort, unauthorized, validation, conflict and invalid
   JSON. Keep request identity keyed by user/field/scene/filter; discard stale
   completions even when cancellation arrives too late.
3. Backend P3 persists field ownership and immutable geometry revisions, fixes
   the KML traversal before accepting uploads, and claims jobs through durable
   transactional leases. Bound uploads, expanded KMZ content and geometry size.
4. Frontend P3 preserves existing map/navigation styling but uses complete
   GeoJSON, explicit no-fields state and server area. Add import preview and
   repair acceptance UI; remove generated rectangles/IDs. Reload after a
   successful save from the API rather than a seeded storage repository.
5. Export P3 captures selected field/revision/filter at job creation, authorizes
   the artifact download and returns complete geometry. KML/KMZ writing is new
   backend work; current spatial exports only provide GeoJSON/GPKG/Parquet.
6. Only then connect source evidence and planning screens; do not use a passing
   static frontend build as evidence of a working vertical slice.

## Data migration and rollback

Do not automatically upload browser storage. Offer user-initiated export and a
reviewed import flow for authentic user records. Exclude seeded identities,
invented measurements and generated boundaries from accepted production data;
unknown provenance stays unknown. Preserve old local keys until explicit
deletion consent. Record legacy ID -> new resource ID mappings for reviewed
imports, with deduplication and transaction failure reporting.

Review any legacy SQLite database separately: inventory schema, provenance and
owner assignments; back it up; rehearse mapping into a separate PostGIS
namespace; reconcile counts, geometry and accepted observations. Do not copy an
entire unlabelled demo database into production or automatically claim ownership.

Use additive migrations while rolling out API/client versions together. Snapshot
DB/assets before a destructive migration, then verify restore in an isolated
environment. Rollback frontend/API to the last compatible contract; pause only
the integration's own worker if needed. Do not erase new user writes, run blind
downgrades, reset source branches or remove shared volumes. Prefer a forward fix
when data written by the new version prevents a safe rollback.

## Issue coverage / existing-plan crosswalk

| Our phase | Audit issues | Existing plan identifiers |
| --- | --- | --- |
| P0/P1 | I01, I15-I17, competing baselines | S01-S02; F01; D01-D05 |
| P2 | I01-I02, I08, I14, I18-I19 | S02/S04; F02-F03; M01 |
| P3 | I03-I05, I16, I18 | S03-S04; F04; M02-M03/M18 |
| P4 | I06-I08, I10-I11 | Selected S05/S09 tasks; F05; M04-M07 |
| P5 | I13-I14, I18, deferred portions of I20 | Selected S07/S10 tasks; F09; M11/M16-M17 |
| P6 | I09-I12 | Selected S05/S06/S10 tasks; F06/F08; M08-M10/M14-M15 |
| P7 | I17-I20, all integrated regressions | F10-F11; integration subset of S11-S12 |

M12/M13 (ranking/scenario calculation), model training/inference, and scientific
optimization are deferred. M15 farm-gate derivation is unavailable unless
separately approved with authentic inputs; displaying market observations is
independent. Do not mark full S05-S12 scientific acceptance complete based on
this smaller integration milestone.

## Suggested reviewable change sequence

Submit relocation, contract, storage/auth, client foundation, field geometry,
imports/exports, each evidence slice, manual plans, and release cleanup as
separate bounded commits/changes. Record source SHAs and contract checksum per
handoff. Each slice includes backend service/DTO, frontend adapter/view changes,
focused tests and its availability behavior; avoid a backend-only "done" followed
by an unbounded frontend rewrite.
