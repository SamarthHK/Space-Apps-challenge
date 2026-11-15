# Backend progress and handoff

Updated: 2026-11-15. Branch: `backend`.

## Current objective

Provide the authentic agricultural data pipeline, PostgreSQL/PostGIS persistence and versioned HTTP API needed by an independently deployed Vite/Leaflet frontend. The binding requirements and acceptance gates are in [backendplan.md](backendplan.md). The frontend migration plan is `frontendplan.md` on the `frontend` branch; no shared checkout path is required. The revised wire contract and branch handoff are in [docs/frontend_api_contract.md](docs/frontend_api_contract.md).

## Earlier planning pass

- Revised and renamed `Plan.md` to `backendplan.md`, retaining the detailed feature inventory and scientific acceptance contract.
- Added the frontend dependency audit, application API and storage requirements, security and data provenance rules, stage S10 for API integration, and API-01–API-12 plus E2E-09 acceptance cases. The sequence now runs S01–S12.
- Updated `IMPLEMENTATION_GAP_ANALYSIS.md` references to the renamed plan.
- The planning pass found divergent dependency declarations. Implementation has since reconciled them using the authoritative `uv.lock` and generated `requirements.txt`.
- Inspected frontend package declarations and build: Vite production build succeeded on 2026-11-15; no required frontend npm package was found missing for the current implementation.

## Current implementation status

- The earlier `IMPLEMENTATION_STATUS.md` documents a partial prototype, including imports and observation bundles. Its older completion tables do not establish compliance with the new plan.
- API foundation, persistent sessions, CSRF, administrator account provisioning and versioned owned profiles are implemented. See [local setup](docs/local_backend.md) and generated [OpenAPI](docs/openapi.json).
- Real local PostgreSQL 17/PostGIS 3.6, transactional checksummed migrations, independent-process persistence and profile revision/concurrency behavior have passed focused checks. This is not the full DB-01-09 authentic agricultural acceptance.
- The separate frontend branch now uses the HTTP session/profile API. Its production entry has no legacy seed-data imports; six unmigrated screens are explicitly unavailable. Existing browser records remain untouched.
- Latest verification: 44 backend tests, eight frontend client/DTO/contract tests, three Chromium production-browser journeys and the frontend build passed. There are no configured lint commands. The backend emits a Starlette TestClient deprecation warning; the inherited Vite toolchain reports two npm audit findings (one moderate, one high), not resolved in this slice.
- Full scientific acceptance, authentic source coverage, field/boundary CRUD, durable acquisition workers and S01-S12 completion remain pending. Existing synthetic fallbacks and example data are not accepted scientific evidence.
- Machine-readable bounded-task status is in [implementation ledger](config/implementation_ledger.yaml); the [frontend mapping](config/frontend_field_mapping.yaml) distinguishes active profile bindings from still-unimplemented M02-M18.

## Frontend-code audit and revised plan

- Read backend `5d53f6735d1ec1698cd98b7021b8a22efd8e1a4f` and frontend `da3b1c0120d99355c3f05dee3fb429877e34b07c`, including both plans, frontend HTML/forms/renderers/services and backend acquisition/storage paths.
- Revised S01–S12 into prerequisite-driven tasks with an early S04 profile/field API slice. A blocked scientific source no longer prevents independent application work; full acceptance still requires all evidence.
- Added `docs/frontend_api_contract.md`: proposed routes, DTOs, error/availability conventions, D01–D05 approval decisions, M01–M18 UI mappings and an explicit frontend-branch handoff.
- Corrected omitted scope for forecasts, market policy prices, costs/deductions and conditional economics; the inventory now has 306 feature families, 63 source categories and 14 instrument categories. These are inventory counts, not implemented totals.
- Marked the old gap-analysis roadmap as superseded. Frontend `frontendplan.md` now records the revised F01/F02 contract, independent deployment and production-data gates.
- The original audit changed documentation only. Subsequent implementation commits below supply the actual API/database/browser evidence; no provider connection is claimed.

## Tested implementation commits

| Branch | Commit | Bounded result |
| --- | --- | --- |
| backend | `6f648da` | Approved revised contracts and repository-only tested small-commit policy |
| backend | `c168f9f` | Isolated API/settings/error foundation |
| backend | `5115744` | Real PostGIS and transactional migrations |
| backend | `d458924` | Persistent auth/session and versioned profiles |
| frontend | `7b3f032` | Independent login/profile client and real browser journeys |
| backend | `31cc576` | Repeatable browser/API harness with isolated cleanup and occupied-port protection |

## Local service state

PostgreSQL was verified on loopback port 55432. Acceptance API/preview processes
are stopped after tests; no regular API/frontend service or default account was
created. Port 1080 has an existing listener on another interface; it was left
untouched. Do not kill or reuse it on the assumption it belongs to this checkout.
Use the setup commands to provision an account with a hidden password and start
services once the desired bind is available. Local credentials and database
files remain ignored.

## Next action

D01-D05 are approved. Complete the pending family/atomic registry work and build
the S02 field/boundary storage migration, S03 geometry service and S04 field API
as independently tested commits. Then connect frontend F04 with the same
real-process/browser approach. The bundled KML is only a test file; authentic
boundaries must come from the frontend and block final authentic-field
acceptance, not implementation of geometry validation and CRUD. Do not use
fabricated data to call any scientific resource ready.
