# Backend progress and handoff

Updated: 2026-11-15. Branch: `backend`.

## Current objective

Provide the authentic agricultural data pipeline, PostgreSQL/PostGIS persistence and versioned HTTP API needed by an independently deployed Vite/Leaflet frontend. The binding requirements and acceptance gates are in [backendplan.md](backendplan.md). The frontend migration plan is `frontendplan.md` on the `frontend` branch; no shared checkout path is required. The revised wire contract and branch handoff are in [docs/frontend_api_contract.md](docs/frontend_api_contract.md).

## Earlier planning pass

- Revised and renamed `Plan.md` to `backendplan.md`, retaining the detailed feature inventory and scientific acceptance contract.
- Added the frontend dependency audit, application API and storage requirements, security and data provenance rules, stage S10 for API integration, and API-01–API-12 plus E2E-09 acceptance cases. The sequence now runs S01–S12.
- Updated `IMPLEMENTATION_GAP_ANALYSIS.md` references to the renamed plan.
- Inspected the backend dependency declarations: `pyproject.toml` and `requirements.txt` disagree and do not yet specify a single locked dependency graph. The plan records the missing or split runtime/test dependencies.
- Inspected frontend package declarations and build: Vite production build succeeded on 2026-11-15; no required frontend npm package was found missing for the current implementation.

## Current implementation status

- The earlier `IMPLEMENTATION_STATUS.md` documents a partial prototype, including imports and observation bundles. Its older completion tables do not establish compliance with the new plan.
- Backend API endpoints, user authentication, PostgreSQL/PostGIS acceptance, authentic source coverage and the full S01–S12 gates have not been verified in this planning pass. Existing synthetic fallback paths and example data must not be counted as accepted evidence.
- No backend application code was changed in this planning pass. No API, database or end-to-end acceptance case has been run here.

## Frontend-code audit and revised plan

- Read backend `5d53f6735d1ec1698cd98b7021b8a22efd8e1a4f` and frontend `da3b1c0120d99355c3f05dee3fb429877e34b07c`, including both plans, frontend HTML/forms/renderers/services and backend acquisition/storage paths.
- Revised S01–S12 into prerequisite-driven tasks with an early S04 profile/field API slice. A blocked scientific source no longer prevents independent application work; full acceptance still requires all evidence.
- Added `docs/frontend_api_contract.md`: proposed routes, DTOs, error/availability conventions, D01–D05 approval decisions, M01–M18 UI mappings and an explicit frontend-branch handoff.
- Corrected omitted scope for forecasts, market policy prices, costs/deductions and conditional economics; the inventory now has 306 feature families, 63 source categories and 14 instrument categories. These are inventory counts, not implemented totals.
- Marked the old gap-analysis roadmap as superseded. Frontend `frontendplan.md` still needs the documented F01/F02 contract and production-data corrections when work proceeds on that branch; it was inspected, not modified here.
- This audit changed documentation only. It did not generate OpenAPI, implement an endpoint, run a browser build or verify a database/provider connection.

## Next action

Start S01 with D01–D05 in the companion contract. Record approvals or blockers, generate typed first-slice schemas/OpenAPI and the M01–M18 mapping, then implement S02 storage and S03/S04 services. Do not wait for all scientific integrations to build profile/field CRUD, and do not use fabricated data to call any scientific resource ready.
