# 06. Decisions, blockers and handoff

All rows below are **proposed / awaiting approval**, unless explicitly described
as scope of this documentation task. Planning does not imply permission to deploy,
change authentication, migrate user data, or replace another checkout.

| ID | Recommendation | Owner / decision needed | Blocks |
| --- | --- | --- | --- |
| D01 Backend baseline | Start from audited named backend checkout unless maintainers explicitly choose the original checkout's rewrite | Backend owner must commit/review rewrite delta and select one schema/service baseline | Source import, migrations and service refactor |
| D02 Source layout | One repository with `frontend`/`backend` prefixes, separate builds/runtime | Both maintainers approve consolidation and path changes | P1 |
| D03 Auth/deployment | Existing companion contract's same-site HTTPS, opaque cookie sessions, CSRF and provisioned accounts | Operator confirms actual origins, lifetime, provisioning and whether cross-site/Tailscale deployment requires another design | P2 auth/CORS and browser configuration |
| D04 Fields/plans | Geometry required, explicit repair consent, archive not hard delete; manual plans allow unavailable economics | Product owner approves draft behavior and version conflicts; no optimizer/overlap allocation in this milestone | P3/P5 form/schema behavior |
| D05 Legacy data | Consent-based export/review/import; no automatic seed upload or localStorage deletion | Data owner identifies authentic user submissions and legacy DB ownership | Production migration |
| D06 Scientific conventions | Registered units/basis/depth, server area with documented method/tolerance, separate source/method and precise vegetation index | Data/geometry owners supply definitions, not arbitrary UI defaults | P3 area acceptance; P4/P6 transforms |
| D07 Acceptance sources | Real approved boundaries/reports/crop references, isolated PostGIS namespace and two test accounts | Owners provide authorized inputs; operators validate source access and private evidence handling | Positive acceptance per affected capability |
| D08 Optional-source release | Ship unavailable satellite/forecast/market panels if authentic inputs/access are blocked | Product owner explicitly approves each unavailable panel, not a blanket omission | P7 release scope |
| D09 AI/economics boundary | Defer models, rankings, optimization and scenario generation; retain ordinary crop catalog/market records/manual plans | AI-model deferral is requested; explicit gating of dependent recommendation/economic UX is the proposed implementation | Contract capability flags and dependent screens |
| D10 Toolchain/operations | One Python lock, existing npm lock, migrations and independent worker; private backend assets | Maintainers choose compatible runtime versions and operator-owned limits | Reproducible build/deployment |

These IDs are local to this merger pack. Existing companion-contract D01-D05
remain their own identifiers: auth corresponds to D03 here, migration to D05,
field/plan policy to D04, scientific conventions to D06, and source inputs to D07.

## Known blockers and next concrete action

| Blocker | What is known | Next action |
| --- | --- | --- |
| No application API/client | Dependencies and plans exist; routes/client do not in audited code | Implement P2/P3 shared vertical slice before screen migration |
| Competing backend work | Original checkout contains substantial uncommitted rewrite; named backend contains live planning changes | Maintainers publish reviewed commits; re-audit changed interfaces only |
| No generated approved OpenAPI | Companion contract is local/untracked during audit | Commit agreed contract source, generate/version artifact, validate both consumers |
| Source readiness unproven | Live water/satellite paths explicitly unavailable; no provider access checked here | Identify authentic import/provider per panel, record exact failures/access requirements |
| Forecast/markets/catalog data | UI contains bundled records, not evidence of authentic backend integrations | Select authorized dated sources; catalog required for accepted manual-plan journey |
| DB/auth/job foundation absent | Current SQLite/WKT/seed path and batch job records are insufficient | Implement explicit PostGIS migrations, ownership, session and durable worker |
| Existing tests not acceptance | Backend tests include generated data; frontend has no tests | Add phase-specific checks and authentic corpus/evidence without calling old tests full acceptance |

## Model boundary

No model download, training, inference service, feature-dataset construction,
model evaluation, optimization, or automatic recommendation implementation is
part of this request. Do not relocate the browser rules into Python and describe
that as integrating AI.

Expose deferred capabilities through `/meta`; recommendation cards and scenario
sliders become an explicit unavailable experience. Dashboard and plans must no
longer require `evaluatePlot()` or `calculateCropFinancials()`. Allow manually
selected crop/date/area and labelled user budgets; never fabricate projected
profit or yield. Future model work can consume stable field/evidence IDs later
without changing authentication, geometry or plan persistence.

## Handoff package

This branch delivers an evidence register, architecture/Git strategy, proposed
wire contract, implementation sequence, acceptance gates and decision register.
It does not deliver merged application code or operational APIs.

Before implementation: approve the baseline and decisions, pin newly reviewed
source commits, assign phase owners, record accepted OpenAPI checksum, and
identify the real first field/report/crop acceptance inputs. Reconcile local
source-plan changes rather than overwriting them.

Publishing this local branch to GitHub is a separate action; creation of a local
branch or planning commit alone does not create a remote branch or pull request.
